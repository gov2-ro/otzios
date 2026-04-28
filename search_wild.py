#!/usr/bin/env python3
"""
Validate wordfreq-confirmed forgotten-word candidates against the live
Romanian web using the Google Custom Search JSON API.

For each candidate with is_forgotten='true', queries:
    "{word}" site:.ro -sinonim -dictionar -definitie -anagrame -rimeaza -site:dexonline.ro ...

Dictionary domains are excluded both by keyword (-dictionar etc.) and by domain
(-site:dexonline.ro etc.). The domain list defaults to DEFAULT_IGNORE_SITES in the
script and can be extended via data/ignore_sites.txt (one domain per line, # for comments).

Records estimated result count, first URL, approximate date of most recent
hit, and a web_score bucket (truly_extinct / nearly_extinct / marginal /
alive_rare). Supports resume: words already in the output file are skipped.

Requires env vars: GOOGLE_API_KEY, GOOGLE_CSE_ID
See the plan for setup instructions (Google Cloud Console + Programmable Search Engine).

Usage:
    python search_wild.py --dry-run --limit 5
    python search_wild.py --limit 100
    python search_wild.py --input path/in.csv --output path/out.csv
"""

import argparse
import csv
import os
import re
import sys
import time
import unicodedata
from pathlib import Path


NEW_COLUMNS = ['google_total_results', 'in_wild', 'web_score', 'top_url', 'last_seen_approx']

DEFAULT_INPUT = Path('data/processed/forgotten_words_validated_wordfreq.csv')
DEFAULT_OUTPUT = Path('data/processed/forgotten_words_web_validated.csv')
DEFAULT_IGNORE_FILE = Path('data/ignore_sites.txt')

# Known Romanian dictionary / reference domains excluded by default.
# Add more via data/ignore_sites.txt (one domain per line, # for comments).
DEFAULT_IGNORE_SITES = [
    'dexonline.ro',
    'dictionar.ro',
    'dictionare.ro',
    'sinonime.ro',
    'sinonim.ro',
    'antonime.ro',
    'definitii.ro',
    'webdex.ro',
    'dictionardeonline.com',
    'conjugare.ro',
]


def normalize_romanian(text: str) -> str:
    """Lowercase + cedilla→comma + NFC. Mirrors process_corpus.py:26-37."""
    return unicodedata.normalize(
        'NFC',
        text.lower().replace('ş', 'ș').replace('ţ', 'ț'),
    )


def clean_word_for_query(word: str) -> str:
    """Strip DEX stress-mark apostrophes (e.g. jălit'or → jălitor)."""
    return word.replace("'", '')


def load_ignore_sites(ignore_file: Path) -> list:
    """Return merged list of default + file-defined domains to exclude."""
    sites = list(DEFAULT_IGNORE_SITES)
    if ignore_file.exists():
        with ignore_file.open('r', encoding='utf-8') as f:
            for line in f:
                domain = line.strip()
                if domain and not domain.startswith('#') and domain not in sites:
                    sites.append(domain)
    return sites


def build_query(word: str, ignore_sites: list) -> str:
    clean = clean_word_for_query(word)
    site_exclusions = ' '.join(f'-site:{d}' for d in ignore_sites)
    return f'"{clean}" site:.ro -sinonim -dictionar -definitie -anagrame -rimeaza {site_exclusions}'


def classify_web_score(total: int) -> str:
    if total == 0:
        return 'truly_extinct'
    if total < 10:
        return 'nearly_extinct'
    if total < 100:
        return 'marginal'
    return 'alive_rare'


def extract_date_from_snippet(snippet: str) -> str:
    """Return the first recognisable date string from a Google snippet, or ''."""
    # ISO date (preferred)
    m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', snippet)
    if m:
        return m.group(1)
    # Romanian abbreviated month: "12 ian. 2023" or "12 ian 2023"
    ro_months = r'ian|feb|mar|apr|mai|iun|iul|aug|sep|oct|noi|nov|dec'
    m = re.search(
        rf'\b(\d{{1,2}}\s+(?:{ro_months})\w*\.?\s+\d{{4}})\b',
        snippet,
        re.IGNORECASE,
    )
    if m:
        return m.group(1)
    # Year-only fallback
    m = re.search(r'\b((?:19|20)\d{2})\b', snippet)
    if m:
        return m.group(1)
    return ''


def parse_response(response: dict) -> tuple:
    """Extract (total, in_wild, web_score, top_url, last_seen_approx) from API response."""
    info = response.get('searchInformation', {})
    # totalResults is a string in the API response; may be '' on some queries
    total = int(info.get('totalResults', '0') or '0')
    in_wild = str(total > 0).lower()
    web_score = classify_web_score(total)

    items = response.get('items', [])
    top_url = ''
    last_seen_approx = ''

    if items:
        first = items[0]
        top_url = first.get('link', '')

        # Prefer structured metadata over snippet regex
        metatags_list = first.get('pagemap', {}).get('metatags', [{}])
        metatags = metatags_list[0] if metatags_list else {}
        published = (
            metatags.get('article:published_time', '')
            or metatags.get('og:updated_time', '')
            or metatags.get('datePublished', '')
        )
        if published:
            last_seen_approx = published[:10]
        else:
            last_seen_approx = extract_date_from_snippet(first.get('snippet', ''))

    return total, in_wild, web_score, top_url, last_seen_approx


def load_checkpoint(output_path: Path) -> set:
    """Return the set of word values already written to output_path."""
    if not output_path.exists():
        return set()
    done = set()
    with output_path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and 'word' in reader.fieldnames:
            for row in reader:
                done.add(row['word'])
    return done


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Check forgotten-word candidates against the Romanian web via Google Custom Search.',
    )
    parser.add_argument(
        '-i', '--input',
        type=Path,
        default=DEFAULT_INPUT,
        help='Wordfreq-validated candidates CSV (default: %(default)s)',
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
        help='Seconds to sleep between API calls (default: %(default)s)',
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

    # --- Check env vars up front (skip in dry-run) ---
    api_key = os.environ.get('GOOGLE_API_KEY', '')
    cse_id = os.environ.get('GOOGLE_CSE_ID', '')
    if not args.dry_run:
        if not api_key:
            print('GOOGLE_API_KEY env var is not set.', file=sys.stderr)
            return 1
        if not cse_id:
            print('GOOGLE_CSE_ID env var is not set.', file=sys.stderr)
            return 1

    # --- Import API client (skip in dry-run) ---
    service = None
    HttpError = None
    if not args.dry_run:
        try:
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError
            service = build('customsearch', 'v1', developerKey=api_key)
        except ImportError:
            print(
                'google-api-python-client not installed. Run: pip install -r requirements.txt',
                file=sys.stderr,
            )
            return 1

    if not args.input.exists():
        print(f'Input not found: {args.input}', file=sys.stderr)
        return 1

    # --- Ignore sites ---
    ignore_sites = load_ignore_sites(args.ignore_file)

    # --- Checkpoint ---
    checkpoint = load_checkpoint(args.output)

    print(f'Input  : {args.input}')
    print(f'Output : {args.output}')
    print(f'Mode   : {"DRY RUN (no API calls, no output written)" if args.dry_run else "LIVE"}')
    print(f'Delay  : {args.delay}s')
    print(f'Ignoring {len(ignore_sites)} domains (default + {args.ignore_file})')
    if args.limit:
        print(f'Limit  : {args.limit}')
    if checkpoint:
        print(f'Loaded : {len(checkpoint):,} words from checkpoint')
    print()

    # --- Read and filter input ---
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

    # --- Dry-run: just print queries and exit ---
    if args.dry_run:
        for i, row in enumerate(candidates, 1):
            print(f'[{i}/{total_words}] DRY RUN: {build_query(row["word"], ignore_sites)}')
        print(f'\nDone. {total_words:,} queries printed, 0 API calls made.')
        return 0

    # --- Live run ---
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
            word = row['word']
            query = build_query(word, ignore_sites)

            google_total = 0
            in_wild = 'false'
            web_score = 'truly_extinct'
            top_url = ''
            last_seen = ''
            skip = False

            try:
                response = service.cse().list(
                    q=query,
                    cx=cse_id,
                    lr='lang_ro',
                    num=1,
                    fields='searchInformation/totalResults,items(link,snippet,pagemap)',
                ).execute()
                google_total, in_wild, web_score, top_url, last_seen = parse_response(response)

            except HttpError as exc:
                status = exc.resp.status
                if status == 429:
                    print(f'  Rate limited. Sleeping 60s then retrying...')
                    time.sleep(60)
                    try:
                        response = service.cse().list(
                            q=query,
                            cx=cse_id,
                            lr='lang_ro',
                            num=1,
                            fields='searchInformation/totalResults,items(link,snippet,pagemap)',
                        ).execute()
                        google_total, in_wild, web_score, top_url, last_seen = parse_response(response)
                    except HttpError:
                        print(f'  Retry failed for "{word}". Skipping.')
                        errors += 1
                        skip = True
                elif status == 403:
                    print(f'\nQuota exhausted (403). Stopping early.')
                    print(f'Re-run with --limit to continue from checkpoint.')
                    break
                else:
                    print(f'  HTTP {status} for "{word}": {exc}. Skipping.')
                    errors += 1
                    skip = True

            except Exception as exc:
                print(f'  Unexpected error for "{word}": {exc}. Skipping.')
                errors += 1
                skip = True

            if not skip:
                url_preview = f'  | {top_url[:70]}' if top_url else ''
                print(f'[{i}/{total_words}] {word} → {google_total} results → {web_score}{url_preview}')

                row['google_total_results'] = google_total
                row['in_wild'] = in_wild
                row['web_score'] = web_score
                row['top_url'] = top_url
                row['last_seen_approx'] = last_seen
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
