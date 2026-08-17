#!/usr/bin/env python3
"""
Scrape DCR2 and DCR3 definitions from CLRE (clre.solirom.ro), not dexonline.ro.

Separate source from scrape_dcr.py / dcr_definitions.db on purpose — see
docs/BACKLOG.md ("CLRE ... TDRG3 is a usable public-text source") for how this
was found. CLRE (Romanian Academy, Iași) publishes both editions as static
JSON+HTML on GitLab Pages, fully public, no auth, no rate limit observed:

- **DCR3**: 9,424 entries with real definition text and dated press citations
  (`AH1N1` cites `R.l. 9 X 09`, `G. 29 X 09`). dexonline.ro itself renders
  **no DCR3 definition text at all** (~183 entries indexed, none with a
  visible definition) — this is a genuine gap-filler, not a duplicate.
- **DCR2**: 5,770 entries, same shape. Close to but not identical to the
  5,807 `extract_dcr.py` already recovers from the DEX dump's `Meaning`
  table — likely redundant, but kept here as a faithful per-source copy
  (dexonline's own dump text is a merged sinteză across sources; this is
  DCR2 alone), same reasoning `scrape_dcr.py` already documents for its own
  DCR2 pass.

Word list: each edition publishes its own full headword→id index at
`indexes/text/cross-references.json` (`[[headword_with_markup, id], ...]`) —
no per-letter enumeration needed, unlike scrape_dcr.py's dexonline case,
where no such bulk index exists. Headword markup uses `HEADWORD||pos info`
or `HEADWORD|N|` (homonym number); the word is always the substring before
the first `|`.

Entry text: `texts/<edition>/text/<id>.html`, an XML fragment with a
`<style>` block (dropped) and the entry body. The id from cross-references.json
is used as-is — homonyms (`ATM|1|`, `ATM|2|`) share a normalized word but have
distinct ids, so the primary key here is (word, edition, entry_id), not
(word, edition) — collapsing homonyms the way scrape_dcr.py does would need
guessing which id "wins".

**Delay is much smaller than scrape_dcr.py's, deliberately.** This is
Fastly/Cloudflare-backed static Pages hosting, not dexonline.ro's community
server — 8 sequential fetches across random ids measured ~0.8s/request with
no throttling. `--delay` still exists and still defaults to a nonzero pause
(general courtesy, not because anything observed requires it), but there is
no dexonline-style "community-run, be gentle" reasoning behind the number,
and copying its 1.2s floor here would be superstition, not policy.

Output: data/processed/clre_dcr_definitions.csv
  word, edition, entry_id, definition, source_url, scraped_at, status
  edition ∈ {dcr2, dcr3}; status ∈ {ok, not_found, error}
--merge upserts ok rows into data/processed/clre_dcr_definitions.db
  clre_dcr_definitions(word, edition, entry_id, definition,
                        PRIMARY KEY(word, edition, entry_id))

Resume: re-running skips (word, edition, entry_id) triples already in the
checkpoint. Ctrl+C is safe — each row is flushed immediately.

Usage:
  python scrape_clre_dcr.py --dry-run
  python scrape_clre_dcr.py --limit 20
  python scrape_clre_dcr.py --editions dcr3 --merge
  python scrape_clre_dcr.py --merge --delay 0.3
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import os
import sqlite3
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from dump_parser import normalize

# Entry pages open with an `<?xml version="1.0"?>` prolog even though the body
# is HTML-shaped; bs4's default parser handles it fine and this warning would
# otherwise print once per entry (15k+ times) on a full run.
warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)

DEFAULT_OUTPUT   = Path('data/processed/clre_dcr_definitions.csv')
DEFAULT_DB       = Path('data/processed/clre_dcr_definitions.db')
EDITIONS         = ('dcr2', 'dcr3')
CROSSREF_TMPL    = 'https://solirom-clre.gitlab.io/texts/{}/text/indexes/text/cross-references.json'
ENTRY_TMPL       = 'https://solirom-clre.gitlab.io/texts/{}/text/{}.html'
USER_AGENT       = 'otios-scraper/0.1 (Romanian linguistic research)'
FIELDNAMES       = ['word', 'edition', 'entry_id', 'definition', 'source_url',
                     'scraped_at', 'status']

# Keyed on this host, separate from data/.dexonline.lock — a different site,
# with no reason to serialise against dexonline.ro scrapes or vice versa.
CLRE_LOCK = Path('data/.solirom-clre.lock')


# ---------------------------------------------------------------------------
# Word lists
# ---------------------------------------------------------------------------

def fetch_crossrefs(session: requests.Session, edition: str) -> list[tuple[str, str, str]]:
    """Return [(normalized_word, entry_id, raw_headword), ...] for one edition.

    One request gets the whole index — CLRE publishes it as a single JSON
    file, unlike dexonline.ro which has no bulk listing (scrape_dcr.py has to
    enumerate DCR3 one search page per letter for exactly that reason).
    """
    url = CROSSREF_TMPL.format(edition)
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    out = []
    for raw_headword, entry_id in resp.json():
        word = normalize(raw_headword.split('|')[0].strip())
        if word:
            out.append((word, entry_id, raw_headword))
    return out


# ---------------------------------------------------------------------------
# Page parsing
# ---------------------------------------------------------------------------

def parse_entry(html: str) -> str:
    """Plain-text definition body from one texts/<edition>/text/<id>.html fragment."""
    soup = BeautifulSoup(html, 'lxml')
    style = soup.select_one('style')
    if style is not None:
        style.decompose()
    article = soup.select_one('article') or soup
    article.smooth()
    return ' '.join(article.get_text(' ', strip=True).split())


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_entry(session: requests.Session, edition: str, entry_id: str) -> tuple[str, str | None]:
    """Fetch one entry page. Returns (status, html_or_None).

    status ∈ {ok, not_found, error}. Transient failures retry once after a
    10s backoff — much shorter than scrape_dcr.py's 30s, since this is a CDN,
    not a community server that might be genuinely struggling.
    """
    url = ENTRY_TMPL.format(edition, entry_id)
    for attempt in (1, 2):
        try:
            resp = session.get(url, timeout=20)
        except requests.RequestException as exc:
            if attempt == 1:
                print(f'  Network error ({type(exc).__name__}); retrying in 10s…')
                time.sleep(10)
                continue
            print(f'  Network error for "{entry_id}": {exc}. Skipping.')
            return 'error', None

        if resp.status_code == 404:
            return 'not_found', None
        if resp.status_code in (429, 503):
            if attempt == 1:
                print(f'  HTTP {resp.status_code}; sleeping 10s then retrying…')
                time.sleep(10)
                continue
            return 'error', None
        if resp.status_code != 200:
            return 'error', None
        return 'ok', resp.text

    return 'error', None


# ---------------------------------------------------------------------------
# Checkpoint / merge
# ---------------------------------------------------------------------------

def load_checkpoint(output_path: Path, retry_not_found: bool = False) -> set[tuple[str, str, str]]:
    if not output_path.exists():
        return set()
    done: set[tuple[str, str, str]] = set()
    with output_path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and 'word' in reader.fieldnames:
            for row in reader:
                if retry_not_found and row.get('status') == 'not_found':
                    continue
                done.add((row['word'], row['edition'], row['entry_id']))
    return done


def merge_into_db(csv_path: Path, db_path: Path) -> tuple[int, int]:
    """Upsert all status=ok rows from the scraping CSV into clre_dcr_definitions.db."""
    if not csv_path.exists():
        print(f'No checkpoint file at {csv_path}; nothing to merge.')
        return 0, 0
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        'CREATE TABLE IF NOT EXISTS clre_dcr_definitions '
        '(word TEXT NOT NULL, edition TEXT NOT NULL, entry_id TEXT NOT NULL, '
        ' definition TEXT NOT NULL, PRIMARY KEY (word, edition, entry_id))'
    )

    inserted = 0
    skipped = 0
    with csv_path.open('r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('status') != 'ok':
                skipped += 1
                continue
            conn.execute(
                'INSERT OR REPLACE INTO clre_dcr_definitions '
                '(word, edition, entry_id, definition) VALUES (?, ?, ?, ?)',
                (row['word'], row['edition'], row['entry_id'], row['definition']),
            )
            inserted += 1
    conn.commit()
    conn.close()
    return inserted, skipped


# ---------------------------------------------------------------------------
# Host lock
# ---------------------------------------------------------------------------

class LockHeld(Exception):
    """Another process is already scraping solirom-clre.gitlab.io."""


def acquire_host_lock(path: Path = CLRE_LOCK):
    """Serialise concurrent runs against this host. See scrape_dcr.py's
    acquire_host_lock for the full rationale (flock over a PID file, etc.);
    duplicated here per CLAUDE.md's copy-at-two-callers rule, and because
    this lock must NOT be the same file as data/.dexonline.lock — that one
    guards a different host with different (real) rate-limit stakes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open('a+', encoding='utf-8')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.seek(0)
        holder = handle.read().strip() or 'holder unknown'
        handle.close()
        raise LockHeld(holder) from None
    handle.seek(0)
    handle.truncate()
    handle.write(f'pid {os.getpid()} since '
                 f'{datetime.now(timezone.utc).isoformat(timespec="seconds")}\n')
    handle.flush()
    return handle


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Export DCR2/DCR3 definitions from CLRE (clre.solirom.ro).',
    )
    parser.add_argument('-o', '--output', type=Path, default=DEFAULT_OUTPUT,
                        help='Checkpoint CSV (default: %(default)s)')
    parser.add_argument('--db', type=Path, default=DEFAULT_DB,
                        help='Destination DB for --merge (default: %(default)s)')
    parser.add_argument('--delay', type=float, default=0.3,
                        help='Seconds between requests (default: %(default)s; '
                             'courtesy pause, not a rate-limit workaround — see module docstring)')
    parser.add_argument('--editions', default='dcr2,dcr3',
                        help='Comma-separated subset of {dcr2,dcr3} (default: %(default)s)')
    parser.add_argument('--limit', type=int, default=None, metavar='N',
                        help='Stop after N non-checkpointed entries')
    parser.add_argument('--dry-run', action='store_true',
                        help='Fetch the word indexes and print the plan; no entry pages fetched')
    parser.add_argument('--merge', action='store_true',
                        help='After scraping, upsert ok rows into clre_dcr_definitions.db')
    parser.add_argument('--merge-only', action='store_true',
                        help='Skip scraping; only run the merge step')
    parser.add_argument('--retry-not-found', action='store_true',
                        help='Re-queue (word, edition, entry_id) triples previously marked not_found')
    args = parser.parse_args()

    editions = [e.strip() for e in args.editions.split(',') if e.strip()]
    bad = [e for e in editions if e not in EDITIONS]
    if bad:
        print(f'Unknown edition(s) {bad!r}; choose from {EDITIONS!r}.', file=sys.stderr)
        return 1

    if args.merge_only:
        inserted, skipped = merge_into_db(args.output, args.db)
        print(f'Merged: {inserted:,} rows upserted, {skipped:,} skipped (non-ok).')
        return 0

    lock = None                                                       # noqa: F841
    if not args.dry_run:
        try:
            lock = acquire_host_lock()                                # noqa: F841
        except LockHeld as held:
            print(f'Another CLRE scrape is already running ({held}). '
                  f'Wait for it, or stop it first.', file=sys.stderr)
            return 1

    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})

    targets: list[tuple[str, str, str]] = []  # (word, edition, entry_id)
    for edition in editions:
        entries = fetch_crossrefs(session, edition)
        print(f'{edition}: {len(entries):,} entries in cross-references.json')
        for word, entry_id, _raw in entries:
            targets.append((word, edition, entry_id))

    checkpoint = load_checkpoint(args.output, retry_not_found=args.retry_not_found)
    plan = [t for t in targets if t not in checkpoint]
    if args.limit is not None:
        plan = plan[:args.limit]

    print(f'Output         : {args.output}')
    print(f'Mode           : {"DRY RUN (no entry fetches)" if args.dry_run else "LIVE"}')
    print(f'Delay          : {args.delay}s')
    print(f'Total entries  : {len(targets):,}')
    print(f'  checkpointed : {len(checkpoint):,}')
    print(f'To scrape      : {len(plan):,}')
    if args.limit:
        print(f'Limit          : {args.limit}')
    print()

    if not plan:
        print('Nothing to scrape.')
        if args.merge:
            inserted, skipped = merge_into_db(args.output, args.db)
            print(f'Merged: {inserted:,} rows upserted, {skipped:,} skipped (non-ok).')
        return 0

    if args.dry_run:
        for i, (word, edition, entry_id) in enumerate(plan, 1):
            print(f'[{i}/{len(plan)}] DRY RUN: {ENTRY_TMPL.format(edition, entry_id)}  ({word})')
        print(f'\nDone. {len(plan):,} URLs printed, 0 requests made.')
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_header = not args.output.exists()

    counts = {'ok': 0, 'not_found': 0, 'error': 0}

    with args.output.open('a', encoding='utf-8', newline='') as fout:
        writer = csv.DictWriter(fout, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
            fout.flush()

        for i, (word, edition, entry_id) in enumerate(plan, 1):
            url = ENTRY_TMPL.format(edition, entry_id)
            try:
                status, html = fetch_entry(session, edition, entry_id)
                definition = parse_entry(html) if status == 'ok' and html else ''
            except KeyboardInterrupt:
                print('\nInterrupted. Partial output retained for checkpoint resume.')
                break

            row_status = 'ok' if definition else ('not_found' if status == 'ok' else status)
            counts[row_status] += 1
            preview = (definition[:60] + '…') if len(definition) > 60 else definition
            print(f'[{i}/{len(plan)}] {word:25s} [{edition}] {entry_id} → {row_status:10s} {preview}')

            writer.writerow({
                'word':       word,
                'edition':    edition,
                'entry_id':   entry_id,
                'definition': definition,
                'source_url': url,
                'scraped_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'status':     row_status,
            })
            fout.flush()

            if i < len(plan):
                time.sleep(args.delay)

    print()
    print(f'Done. ok={counts["ok"]:,}  not_found={counts["not_found"]:,}  error={counts["error"]:,}')
    print(f'Output: {args.output}')

    if args.merge:
        inserted, skipped = merge_into_db(args.output, args.db)
        print(f'Merged: {inserted:,} rows upserted, {skipped:,} skipped (non-ok).')

    return 0


if __name__ == '__main__':
    sys.exit(main())
