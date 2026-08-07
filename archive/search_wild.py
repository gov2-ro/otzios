#!/usr/bin/env python3
"""
Validate forgotten-word candidates against the live Romanian web.

Providers are pluggable. Two implementations ship today:

  - ddg     DuckDuckGo via the `ddgs` library. No API key. Capped at 30
            results per query; result counts are coarse. Useful as a quick
            prototype, but DDG's matching is fuzzy for rare archaic words
            (often returns cross-language hits or pages where the *form*
            matches but not the *word*). Treat counts as triage, not ground
            truth. Default.
  - google  Google Custom Search JSON API. Requires GOOGLE_API_KEY and
            GOOGLE_CSE_ID. Free tier 100 queries/day. Returns an estimated
            totalResults plus a top URL with structured metadata. Much
            better exact-match behavior than DDG.

For each candidate with is_forgotten='true', the provider runs:
    "{word}" site:.ro -dictionar -sinonim ...  (Google syntax)
    "{word}" -dictionar -sinonim ...           (DDG syntax — no site:.ro restriction;
                                                regional bias comes from region=ro-ro)

Dictionary domains are excluded both by keyword (-dictionar etc.) and by domain
(-site:dexonline.ro etc.). The domain list defaults to DEFAULT_IGNORE_SITES in this
file and can be extended via data/ignore_sites.txt (one domain per line, # for comments).

Output columns (added to the input):
    total_results, in_wild, web_score, top_url, last_seen_approx, provider

`web_score` buckets are provider-specific (DDG is capped at 10 results):
    google: 0 / <10 / <100 / 100+
    ddg:    0 / <3  / <10  / 10+

Resume is supported: rows already in the output CSV are skipped.

Usage:
    python search_wild.py --dry-run --limit 5                  # default provider (ddg)
    python search_wild.py --provider ddg --limit 50
    python search_wild.py --provider google --limit 100        # needs env vars
    python search_wild.py --input path/in.csv --output path/out.csv
"""

import argparse
import csv
import os
import re
import sys
import time
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


NEW_COLUMNS = ['total_results', 'in_wild', 'web_score', 'top_url', 'last_seen_approx', 'provider']

DEFAULT_INPUT       = Path('data/processed/forgotten_words_validated_wordfreq.csv')
DEFAULT_OUTPUT      = Path('data/processed/forgotten_words_web_validated.csv')
DEFAULT_IGNORE_FILE = Path('data/ignore_sites.txt')

DEFAULT_IGNORE_SITES = [
    'dexonline.ro',
    'dexonline.net',
    'dex.ro',
    'dictionar.ro',
    'dictionare.ro',
    'sinonime.ro',
    'sinonim.ro',
    'antonime.ro',
    'definitii.ro',
    'webdex.ro',
    'dictionardeonline.com',
    'conjugare.ro',
    'dexdefinitie.com',
    'context.reverso.net',
    'reverso.net',
    'en-academic.com',
    'romanian.en-academic.com',
    'glosbe.com',
    'educalingo.com',
    'lingvozone.com',
    'translated.net',
    'mymemory.translated.net',
    'archeus.ro',
]

DEFAULT_IGNORE_KEYWORDS = ['dictionar', 'sinonim', 'definitie', 'anagrame', 'rimeaza']


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def normalize_romanian(text: str) -> str:
    """Lowercase + cedilla→comma + NFC. Mirrors process_corpus.py:26-37."""
    return unicodedata.normalize(
        'NFC',
        text.lower().replace('ş', 'ș').replace('ţ', 'ț'),
    )


def clean_word_for_query(word: str) -> str:
    """Strip DEX stress-mark apostrophes (e.g. jălit'or → jălitor)."""
    return word.replace("'", '')


def load_ignore_sites(ignore_file: Path) -> list[str]:
    sites = list(DEFAULT_IGNORE_SITES)
    if ignore_file.exists():
        with ignore_file.open('r', encoding='utf-8') as f:
            for line in f:
                domain = line.strip()
                if domain and not domain.startswith('#') and domain not in sites:
                    sites.append(domain)
    return sites


def extract_date_from_snippet(snippet: str) -> str:
    """Return the first recognisable date string from a snippet, or ''."""
    m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', snippet)
    if m:
        return m.group(1)
    ro_months = r'ian|feb|mar|apr|mai|iun|iul|aug|sep|oct|noi|nov|dec'
    m = re.search(
        rf'\b(\d{{1,2}}\s+(?:{ro_months})\w*\.?\s+\d{{4}})\b',
        snippet,
        re.IGNORECASE,
    )
    if m:
        return m.group(1)
    m = re.search(r'\b((?:19|20)\d{2})\b', snippet)
    if m:
        return m.group(1)
    return ''


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------

@dataclass
class SearchResult:
    total_results:    int
    in_wild:          str   # 'true' / 'false'
    web_score:        str
    top_url:          str
    last_seen_approx: str


class SearchProvider(ABC):
    name: str = ''

    @property
    def required_env_vars(self) -> list[str]:
        return []

    def connect(self) -> None:
        """Initialise the underlying client. Override if needed."""
        return

    @abstractmethod
    def build_query(self, word: str, ignore_sites: list[str]) -> str: ...

    @abstractmethod
    def classify_web_score(self, total: int) -> str: ...

    @abstractmethod
    def search(self, query: str, ignore_sites: list[str] | None = None) -> SearchResult: ...


# ---------------------------------------------------------------------------
# Google CSE provider
# ---------------------------------------------------------------------------

class GoogleCSEProvider(SearchProvider):
    name = 'google'

    @property
    def required_env_vars(self) -> list[str]:
        return ['GOOGLE_API_KEY', 'GOOGLE_CSE_ID']

    def connect(self) -> None:
        try:
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError
        except ImportError as e:
            raise SystemExit(
                'google-api-python-client not installed. Run: pip install -r requirements.txt'
            ) from e
        self._HttpError = HttpError
        self._cse_id = os.environ['GOOGLE_CSE_ID']
        self._service = build('customsearch', 'v1', developerKey=os.environ['GOOGLE_API_KEY'])

    def build_query(self, word: str, ignore_sites: list[str]) -> str:
        clean = clean_word_for_query(word)
        excl_kw   = ' '.join(f'-{k}' for k in DEFAULT_IGNORE_KEYWORDS)
        excl_site = ' '.join(f'-site:{d}' for d in ignore_sites)
        return f'"{clean}" site:.ro {excl_kw} {excl_site}'

    def classify_web_score(self, total: int) -> str:
        if total == 0:   return 'truly_extinct'
        if total < 10:   return 'nearly_extinct'
        if total < 100:  return 'marginal'
        return 'alive_rare'

    def search(self, query: str, ignore_sites: list[str] | None = None) -> SearchResult:
        # Google honors -site: operators reliably; ignore_sites is accepted only
        # for interface symmetry with DuckDuckGoProvider.
        del ignore_sites
        response = self._service.cse().list(
            q=query,
            cx=self._cse_id,
            lr='lang_ro',
            num=1,
            fields='searchInformation/totalResults,items(link,snippet,pagemap)',
        ).execute()

        info  = response.get('searchInformation', {})
        total = int(info.get('totalResults', '0') or '0')

        items = response.get('items', [])
        top_url = ''
        last_seen = ''
        if items:
            first = items[0]
            top_url = first.get('link', '')
            metatags_list = first.get('pagemap', {}).get('metatags', [{}])
            metatags = metatags_list[0] if metatags_list else {}
            published = (
                metatags.get('article:published_time', '')
                or metatags.get('og:updated_time', '')
                or metatags.get('datePublished', '')
            )
            if published:
                last_seen = published[:10]
            else:
                last_seen = extract_date_from_snippet(first.get('snippet', ''))

        return SearchResult(
            total_results    = total,
            in_wild          = 'true' if total > 0 else 'false',
            web_score        = self.classify_web_score(total),
            top_url          = top_url,
            last_seen_approx = last_seen,
        )

    # Exposed so the orchestrator can recognise Google-specific HTTP errors.
    @property
    def HttpError(self):
        return self._HttpError


# ---------------------------------------------------------------------------
# DuckDuckGo provider (via `ddgs` library)
# ---------------------------------------------------------------------------

class DuckDuckGoProvider(SearchProvider):
    name = 'ddg'
    MAX_RESULTS = 30  # cap; post-filtering may reduce the kept count

    def connect(self) -> None:
        try:
            from ddgs import DDGS
        except ImportError as e:
            raise SystemExit(
                'ddgs not installed. Run: pip install -r requirements.txt'
            ) from e
        self._DDGS = DDGS

    def build_query(self, word: str, ignore_sites: list[str]) -> str:
        # DDG doesn't reliably honor -site: and chokes on very long queries.
        # We keep only keyword exclusions; ignored domains are dropped in post-filter.
        clean = clean_word_for_query(word)
        excl_kw = ' '.join(f'-{k}' for k in DEFAULT_IGNORE_KEYWORDS)
        del ignore_sites
        return f'"{clean}" {excl_kw}'

    def classify_web_score(self, total: int) -> str:
        # max_results=30; buckets tuned for that cap.
        if total == 0:   return 'truly_extinct'
        if total < 3:    return 'nearly_extinct'
        if total < 10:   return 'marginal'
        return 'alive_rare'

    def _filter_results(self, results: list[dict], ignore_sites: list[str]) -> list[dict]:
        """Drop results whose hostname matches any ignored domain (suffix match)."""
        from urllib.parse import urlparse
        kept = []
        for r in results:
            href = r.get('href', '') or ''
            host = urlparse(href).hostname or ''
            host = host.lower().lstrip('.')
            if any(host == d or host.endswith('.' + d) for d in ignore_sites):
                continue
            kept.append(r)
        return kept

    def search(self, query: str, ignore_sites: list[str] | None = None) -> SearchResult:
        try:
            raw = self._DDGS().text(
                query=query,
                region='ro-ro',
                safesearch='off',
                max_results=self.MAX_RESULTS,
            ) or []
        except Exception as e:
            # ddgs raises DDGSException("No results found.") for zero-hit queries
            # — that's a valid (and informative) outcome for us, not an error.
            if 'No results found' in str(e):
                raw = []
            else:
                raise
        results = self._filter_results(raw, ignore_sites or []) if ignore_sites else raw
        total = len(results)

        top_url = ''
        last_seen = ''
        if results:
            first = results[0]
            top_url = first.get('href', '')
            last_seen = extract_date_from_snippet(first.get('body', ''))

        return SearchResult(
            total_results    = total,
            in_wild          = 'true' if total > 0 else 'false',
            web_score        = self.classify_web_score(total),
            top_url          = top_url,
            last_seen_approx = last_seen,
        )


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

PROVIDERS = {
    DuckDuckGoProvider.name: DuckDuckGoProvider,
    GoogleCSEProvider.name:  GoogleCSEProvider,
}


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

def load_checkpoint(output_path: Path) -> set[str]:
    if not output_path.exists():
        return set()
    done: set[str] = set()
    with output_path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and 'word' in reader.fieldnames:
            for row in reader:
                done.add(row['word'])
    return done


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Check forgotten-word candidates against the Romanian web.',
    )
    parser.add_argument(
        '-p', '--provider',
        choices=sorted(PROVIDERS.keys()),
        default='ddg',
        help='Search backend (default: %(default)s)',
    )
    parser.add_argument(
        '-i', '--input',
        type=Path,
        default=DEFAULT_INPUT,
        help='Candidates CSV with is_forgotten column (default: %(default)s)',
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=DEFAULT_OUTPUT,
        help='Output CSV (default: %(default)s)',
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Seconds to sleep between calls (default: %(default)s)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print queries without calling the API or writing output',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        metavar='N',
        help='Process at most N non-checkpointed words',
    )
    parser.add_argument(
        '--ignore-file',
        type=Path,
        default=DEFAULT_IGNORE_FILE,
        help='File of domains to exclude, one per line (default: %(default)s)',
    )
    args = parser.parse_args()

    provider: SearchProvider = PROVIDERS[args.provider]()

    if not args.dry_run:
        missing = [v for v in provider.required_env_vars if not os.environ.get(v)]
        if missing:
            print(f'Missing required env vars for {provider.name}: {missing}', file=sys.stderr)
            return 1
        provider.connect()

    if not args.input.exists():
        print(f'Input not found: {args.input}', file=sys.stderr)
        return 1

    ignore_sites = load_ignore_sites(args.ignore_file)
    checkpoint = load_checkpoint(args.output)

    print(f'Provider : {provider.name}')
    print(f'Input    : {args.input}')
    print(f'Output   : {args.output}')
    print(f'Mode     : {"DRY RUN (no API calls, no output written)" if args.dry_run else "LIVE"}')
    print(f'Delay    : {args.delay}s')
    print(f'Ignoring : {len(ignore_sites)} domains (default + {args.ignore_file})')
    if args.limit:
        print(f'Limit    : {args.limit}')
    if checkpoint:
        print(f'Loaded   : {len(checkpoint):,} words from checkpoint')
    print()

    with args.input.open('r', encoding='utf-8') as fin:
        reader = csv.DictReader(fin)
        if not reader.fieldnames or 'word' not in reader.fieldnames:
            print(f'Input has no "word" column: {args.input}', file=sys.stderr)
            return 1
        if 'is_forgotten' not in reader.fieldnames:
            print(f'Input has no "is_forgotten" column: {args.input}', file=sys.stderr)
            return 1
        out_fields = list(reader.fieldnames) + NEW_COLUMNS

        candidates = [
            row for row in reader
            if row.get('is_forgotten') == 'true'
            and row.get('word') not in checkpoint
        ]

    if args.limit is not None:
        candidates = candidates[:args.limit]

    total_words = len(candidates)
    print(f'Processing {total_words:,} words ({len(checkpoint):,} already checkpointed)\n')

    if args.dry_run:
        for i, row in enumerate(candidates, 1):
            print(f'[{i}/{total_words}] DRY RUN: {provider.build_query(row["word"], ignore_sites)}')
        print(f'\nDone. {total_words:,} queries printed, 0 API calls made.')
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    file_exists_with_data = args.output.exists() and bool(checkpoint)
    mode = 'a' if file_exists_with_data else 'w'

    processed = 0
    errors = 0

    with args.output.open(mode, encoding='utf-8', newline='') as fout:
        writer = csv.DictWriter(fout, fieldnames=out_fields)
        if not file_exists_with_data:
            writer.writeheader()

        for i, row in enumerate(candidates, 1):
            word  = row['word']
            query = provider.build_query(word, ignore_sites)

            result: SearchResult | None = None
            skip = False

            try:
                result = provider.search(query, ignore_sites)
            except KeyboardInterrupt:
                print('\nInterrupted. Partial output retained for checkpoint resume.')
                break
            except Exception as exc:
                # Google rate-limit / quota handling (provider-specific)
                if isinstance(provider, GoogleCSEProvider) and isinstance(exc, provider.HttpError):
                    status = exc.resp.status
                    if status == 429:
                        print('  Rate limited. Sleeping 60s then retrying...')
                        time.sleep(60)
                        try:
                            result = provider.search(query, ignore_sites)
                        except Exception as exc2:
                            print(f'  Retry failed for "{word}": {exc2}. Skipping.')
                            errors += 1
                            skip = True
                    elif status == 403:
                        print('\nQuota exhausted (403). Stopping early.')
                        print('Re-run with --limit to continue from checkpoint.')
                        break
                    else:
                        print(f'  HTTP {status} for "{word}": {exc}. Skipping.')
                        errors += 1
                        skip = True
                else:
                    print(f'  Error for "{word}": {type(exc).__name__}: {exc}. Skipping.')
                    errors += 1
                    skip = True

            if not skip and result is not None:
                url_preview = f'  | {result.top_url[:70]}' if result.top_url else ''
                print(f'[{i}/{total_words}] {word} → {result.total_results} results '
                      f'→ {result.web_score}{url_preview}')

                row['total_results']    = result.total_results
                row['in_wild']          = result.in_wild
                row['web_score']        = result.web_score
                row['top_url']          = result.top_url
                row['last_seen_approx'] = result.last_seen_approx
                row['provider']         = provider.name
                writer.writerow(row)
                processed += 1

            if i < total_words:
                time.sleep(args.delay)

    print()
    print(f'Done. {processed:,} processed, {errors:,} errors, '
          f'{len(checkpoint):,} skipped (checkpoint).')
    print(f'Output : {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
