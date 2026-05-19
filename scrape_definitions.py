#!/usr/bin/env python3
"""
Scrape definitions from dexonline.ro for shortlist words missing from
the local DEX dump.

The DEX MySQL dump has data-integrity gaps (see docs/DEFINITIONS_ANALYSIS.md);
many shortlist words have no entry in DefinitionSimple. This script fills
those gaps by fetching the "sinteză" (synthesis) section directly from
dexonline.ro.

Output: data/processed/scraped_definitions.csv with columns
  word, definition, source_url, scraped_at, status

`status ∈ {ok, not_found, error}` — failed rows are retained so resume
runs can skip them. Pass --merge to upsert ok rows into definitions.db.

Resume: re-running the script reads existing checkpoint rows and only
scrapes words not already there. KeyboardInterrupt is safe.

Usage:
  python scrape_definitions.py --dry-run --limit 5
  python scrape_definitions.py --limit 20 --delay 3.0
  python scrape_definitions.py --delay 3.0 --merge
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

DEFAULT_INPUT       = Path('data/processed/forgotten_words_shortlist.csv')
DEFAULT_OUTPUT      = Path('data/processed/scraped_definitions.csv')
DEFAULT_DEFS_DB     = Path('data/processed/definitions.db')
DEXONLINE_URL_TMPL  = 'https://dexonline.ro/definitie/{}'
USER_AGENT          = 'otios-scraper/0.1 (Romanian linguistic research)'
FIELDNAMES          = ['word', 'definition', 'source_url', 'scraped_at', 'status']


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------

def parse_synthesis(html: str) -> str | None:
    """Return the synthesis (`sinteză`) definition text, or None if absent.

    The synthesis lives in `#tab_2 .tree-body`. Each top-level meaning is
    `li.type-meaning > .meaningContainer .tree-def`. We exclude the
    etymology block (`.etymology .tree-def`).

    When a word has multiple top-level meanings, we join them with " | ".
    """
    soup = BeautifulSoup(html, 'lxml')

    # If the search returned no results, the page contains the literal
    # "Niciun rezultat" headline and no synthesis container.
    body = soup.select_one('#tab_2 .tree-body')
    if body is None:
        return None

    # `.tree-def` lives inside both .type-meaning and .type-etymology rows.
    # Restrict to .type-meaning to avoid pulling etymology text.
    parts: list[str] = []
    for el in body.select('li.type-meaning .meaningContainer .tree-def'):
        text = el.get_text(' ', strip=True)
        # Collapse internal whitespace
        text = ' '.join(text.split())
        if text:
            parts.append(text)

    if not parts:
        return None
    return ' | '.join(parts)


def _norm_headword(text: str) -> str:
    """Normalise a DEX headword for comparison.

    Strips leading * / ❍ markers and trailing punctuation, removes stress
    accent marks (acute/grave on base Latin letters — not Romanian ă/â/î/ș/ț),
    collapses internal whitespace, and lowercases.
    """
    text = text.lstrip('*❍').rstrip(',.;:()').strip()
    # Remove only combining ACUTE and GRAVE accents (used for stress marks in
    # some dictionaries) by NFC-decomposing, stripping those two categories,
    # then recomposing. Romanian-specific diacritics (ă, â, î, ș, ț) are
    # NOT affected because their combining characters are cedilla / breve.
    nfd = unicodedata.normalize('NFD', text)
    stripped = ''.join(
        ch for ch in nfd
        if unicodedata.category(ch) != 'Mn'
        or unicodedata.name(ch, '').split()[0] not in ('COMBINING',)
        or unicodedata.name(ch, '') not in (
            'COMBINING ACUTE ACCENT', 'COMBINING GRAVE ACCENT',
        )
    )
    return unicodedata.normalize('NFC', stripped).lower()


def parse_tab0_defs(html: str, word: str) -> str | None:
    """Fallback for words with no synthesis panel: scan #tab_0 .defWrapper entries.

    Matches .defWrapper headwords case-insensitively against `word`.
    Returns the first 3 matching raw-dictionary definition texts joined by " | ".
    Headwords in DEX HTML sometimes have individual characters in separate
    spans; we join them without separators to reconstruct the word.
    """
    soup = BeautifulSoup(html, 'lxml')
    tab0 = soup.select_one('#tab_0')
    if not tab0:
        return None
    word_norm = _norm_headword(word)
    results: list[str] = []
    for wrapper in tab0.select('.defWrapper'):
        b = wrapper.select_one('.def b')
        if not b:
            continue
        # Join with no separator to handle per-character spans.
        hw_raw = ''.join(b.strings).strip()
        hw = _norm_headword(hw_raw)
        if hw == word_norm:
            span = wrapper.select_one('.def')
            if span:
                clean = ' '.join(span.get_text(' ', strip=True).split())
                if clean:
                    results.append(clean)
    if not results:
        return None
    return ' | '.join(results[:3])


def parse_lemma_fallback(word: str, defs_db: Path) -> str | None:
    """Fallback for inflected forms with empty synthesis.

    Uses simplemma to derive the base lemma, then looks it up in definitions.db.
    Returns a prefixed definition string, or None if the lemma matches the word
    (simplemma couldn't lemmatize) or has no definition.
    """
    try:
        import simplemma
        lemma = simplemma.lemmatize(word, lang='ro')
    except Exception:
        return None
    if lemma == word or not defs_db.exists():
        return None
    conn = sqlite3.connect(str(defs_db))
    try:
        row = conn.execute('SELECT definition FROM definitions WHERE word=?', (lemma,)).fetchone()
        return f'[formă a lui {lemma}] {row[0]}' if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

def load_checkpoint(output_path: Path, retry_not_found: bool = False) -> set[str]:
    """Read existing output CSV, return set of words already attempted.

    When retry_not_found is True, words with status=not_found are excluded
    from the done set so they get re-queued.
    """
    if not output_path.exists():
        return set()
    done: set[str] = set()
    with output_path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and 'word' in reader.fieldnames:
            for row in reader:
                if retry_not_found and row.get('status') == 'not_found':
                    continue
                done.add(row['word'])
    return done


def load_already_defined(db_path: Path) -> set[str]:
    """Read definitions.db, return set of words that already have a definition."""
    if not db_path.exists():
        return set()
    conn = sqlite3.connect(str(db_path))
    try:
        return {row[0] for row in conn.execute('SELECT word FROM definitions')}
    finally:
        conn.close()


def load_shortlist(input_path: Path) -> list[str]:
    with input_path.open('r', encoding='utf-8') as f:
        return [row['word'] for row in csv.DictReader(f) if row.get('word')]


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

def fetch_synthesis(
    session: requests.Session, word: str, defs_db: Path
) -> tuple[str, str | None, str]:
    """Fetch one word. Returns (status, definition_or_None, source_url).

    status ∈ {ok, not_found, error}. On a transient HTTP error we retry
    once after a 30s backoff.

    Fallback chain when synthesis is absent:
      1. parse_tab0_defs  — raw dictionary entries in #tab_0
      2. parse_lemma_fallback — base-lemma lookup via simplemma
    """
    url = DEXONLINE_URL_TMPL.format(quote(word, safe=''))

    for attempt in (1, 2):
        try:
            resp = session.get(url, timeout=20)
        except requests.RequestException as exc:
            if attempt == 1:
                print(f'  Network error ({type(exc).__name__}); retrying in 30s…')
                time.sleep(30)
                continue
            print(f'  Network error for "{word}": {exc}. Skipping.')
            return 'error', None, url

        if resp.status_code in (429, 503):
            if attempt == 1:
                print(f'  HTTP {resp.status_code}; sleeping 30s then retrying…')
                time.sleep(30)
                continue
            return 'error', None, url

        if resp.status_code != 200:
            return 'error', None, url

        definition = parse_synthesis(resp.text)
        if definition is None:
            definition = parse_tab0_defs(resp.text, word)
        if definition is None:
            definition = parse_lemma_fallback(word, defs_db)
        if definition:
            return 'ok', definition, url
        return 'not_found', None, url

    return 'error', None, url


# ---------------------------------------------------------------------------
# Merge into definitions.db
# ---------------------------------------------------------------------------

def merge_into_db(csv_path: Path, db_path: Path) -> tuple[int, int]:
    """Upsert all status=ok rows from the scraping CSV into definitions.db.

    Returns (inserted_or_replaced, skipped).
    """
    if not csv_path.exists():
        print(f'No checkpoint file at {csv_path}; nothing to merge.')
        return 0, 0
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        'CREATE TABLE IF NOT EXISTS definitions '
        '(word TEXT PRIMARY KEY, definition TEXT NOT NULL)'
    )

    inserted = 0
    skipped = 0
    with csv_path.open('r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('status') != 'ok':
                skipped += 1
                continue
            conn.execute(
                'INSERT OR REPLACE INTO definitions (word, definition) VALUES (?, ?)',
                (row['word'], row['definition']),
            )
            inserted += 1
    conn.commit()
    conn.close()
    return inserted, skipped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Scrape dexonline.ro synthesis for shortlist words missing from definitions.db.',
    )
    parser.add_argument('-i', '--input', type=Path, default=DEFAULT_INPUT,
                        help='Shortlist CSV (default: %(default)s)')
    parser.add_argument('-o', '--output', type=Path, default=DEFAULT_OUTPUT,
                        help='Checkpoint CSV (default: %(default)s)')
    parser.add_argument('--definitions-db', type=Path, default=DEFAULT_DEFS_DB,
                        help='Existing definitions DB used to skip already-covered words (default: %(default)s)')
    parser.add_argument('--delay', type=float, default=3.0,
                        help='Seconds between requests (default: %(default)s)')
    parser.add_argument('--limit', type=int, default=None, metavar='N',
                        help='Stop after N non-checkpointed words')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print URLs only; no HTTP requests, no output written')
    parser.add_argument('--merge', action='store_true',
                        help='After scraping, upsert ok rows into definitions.db')
    parser.add_argument('--merge-only', action='store_true',
                        help='Skip scraping; only run the merge step')
    parser.add_argument('--retry-not-found', action='store_true',
                        help='Re-queue words previously marked not_found (tries new fallbacks)')
    args = parser.parse_args()

    if args.merge_only:
        inserted, skipped = merge_into_db(args.output, args.definitions_db)
        print(f'Merged: {inserted:,} rows upserted, {skipped:,} skipped (non-ok).')
        return 0

    if not args.input.exists():
        print(f'Input not found: {args.input}', file=sys.stderr)
        return 1

    shortlist = load_shortlist(args.input)
    already_defined = load_already_defined(args.definitions_db)
    checkpoint = load_checkpoint(args.output, retry_not_found=args.retry_not_found)

    shortlist_in_db = sum(1 for w in shortlist if w in already_defined)
    targets = [w for w in shortlist
               if w not in already_defined and w not in checkpoint]
    if args.limit is not None:
        targets = targets[:args.limit]

    print(f'Input          : {args.input}')
    print(f'Output         : {args.output}')
    print(f'Definitions DB : {args.definitions_db}')
    print(f'Mode           : {"DRY RUN (no HTTP, no writes)" if args.dry_run else "LIVE"}')
    print(f'Delay          : {args.delay}s')
    print(f'Shortlist size : {len(shortlist):,}')
    print(f'  in db        : {shortlist_in_db:,} (have definitions)')
    print(f'  checkpointed : {len(checkpoint):,} (already attempted)')
    print(f'To scrape      : {len(targets):,}')
    if args.limit:
        print(f'Limit          : {args.limit}')
    print()

    if not targets:
        print('Nothing to scrape.')
        if args.merge:
            inserted, skipped = merge_into_db(args.output, args.definitions_db)
            print(f'Merged: {inserted:,} rows upserted, {skipped:,} skipped (non-ok).')
        return 0

    if args.dry_run:
        for i, word in enumerate(targets, 1):
            print(f'[{i}/{len(targets)}] DRY RUN: {DEXONLINE_URL_TMPL.format(quote(word, safe=""))}')
        print(f'\nDone. {len(targets):,} URLs printed, 0 requests made.')
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_header = not args.output.exists()
    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})

    counts = {'ok': 0, 'not_found': 0, 'error': 0}

    with args.output.open('a', encoding='utf-8', newline='') as fout:
        writer = csv.DictWriter(fout, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
            fout.flush()

        for i, word in enumerate(targets, 1):
            try:
                status, definition, url = fetch_synthesis(session, word, args.definitions_db)
            except KeyboardInterrupt:
                print('\nInterrupted. Partial output retained for checkpoint resume.')
                break

            counts[status] += 1
            preview = (definition[:60] + '…') if definition and len(definition) > 60 else (definition or '')
            print(f'[{i}/{len(targets)}] {word:25s} → {status:10s} {preview}')

            writer.writerow({
                'word':       word,
                'definition': definition or '',
                'source_url': url,
                'scraped_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'status':     status,
            })
            fout.flush()

            if i < len(targets):
                time.sleep(args.delay)

    print()
    print(f'Done. ok={counts["ok"]:,}  not_found={counts["not_found"]:,}  error={counts["error"]:,}')
    print(f'Output: {args.output}')

    if args.merge:
        inserted, skipped = merge_into_db(args.output, args.definitions_db)
        print(f'Merged: {inserted:,} rows upserted, {skipped:,} skipped (non-ok).')

    return 0


if __name__ == '__main__':
    sys.exit(main())
