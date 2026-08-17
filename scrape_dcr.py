#!/usr/bin/env python3
"""
Scrape the DCR definitions that are NOT in the DEX MySQL dump.

DCR2 (1997) is in the dump in full — as structured text in the `Meaning` table —
and `extract_dcr.py` exports it (no HTTP). This script covers the rest:

- **DCR3 (2013)** — zero rows in the dump and only partially digitized on the
  site so far (~183 entries, mostly abbreviations and symbols — `c` = carbon,
  circa, sută). Its word list is enumerated from the per-source search pages
  (/definitie-dcr3/<letter>/definitii, one request per letter) and cached.
- **DCR2 words the extractor missed** — the rare word whose meaning tree is
  empty; the DCR2 word list (dcr2_words.txt, written by extract_dcr.py) is in
  the queue so a run can pick those up too.
- **A faithful per-source DCR2 copy** if the merged-tree caveat of
  extract_dcr.py ever matters — same mechanism, just scrape the full list.

DCR (1982, the first edition) is not a source on dexonline.ro — only an
abbreviation cited inside DCR2's own entries.

Word lists are cached under data/processed/ (dcr2_words.txt written by
extract_dcr.py; dcr3_words.txt enumerated here, regenerated with
--refresh-words). --dry-run reads the caches and makes no requests, so it stays
safe to run while another scrape holds the lock.

On a word page the per-dictionary view is a .defWrapper whose .defDetails
carries a "sursa:" link (/sursa/dcr2 or /sursa/dcr3). Selecting on that link
rather than on the headword is what makes multi-entry pages safe: /definitie/roză
also renders ROZ. Each word is fetched once and every edition asked for it is
extracted from that one page. Within an entry, .tonic-accent spans are unwrapped
and the tree is smoothed before get_text(' '), otherwise the separator lands
between a word's own letters (`comp u ter`).

Output: data/processed/dcr_definitions.csv
  word, edition, definition, source_url, scraped_at, status
  edition ∈ {dcr2, dcr3}; status ∈ {ok, not_found, error}
--merge upserts ok rows into data/processed/dcr_definitions.db
  dcr_definitions(word, edition, definition, PRIMARY KEY(word, edition))

Resume: re-running skips (word, edition) pairs already in the checkpoint.
Ctrl+C is safe — each row is flushed immediately. --delay below 1.2s is
refused: dexonline.ro is community-run.

Usage:
  python scrape_dcr.py --dry-run
  python scrape_dcr.py --limit 20 --delay 1.2
  python scrape_dcr.py --delay 1.5 --merge
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote

import requests
from bs4 import BeautifulSoup

from dump_parser import normalize

DEFAULT_OUTPUT   = Path('data/processed/dcr_definitions.csv')
DEFAULT_DB       = Path('data/processed/dcr_definitions.db')
DCR2_WORDS_FILE  = Path('data/processed/dcr2_words.txt')
DCR3_WORDS_FILE  = Path('data/processed/dcr3_words.txt')
EDITIONS         = ('dcr2', 'dcr3')
DCR3_LETTERS     = 'aăâbcdefghiîjklmnopqrsștțuvwxyz'
DEXONLINE_URL_TMPL  = 'https://dexonline.ro/definitie/{}'
DCR3_SEARCH_TMPL    = 'https://dexonline.ro/definitie-dcr3/{}/definitii'
USER_AGENT          = 'otios-scraper/0.1 (Romanian linguistic research)'
FIELDNAMES          = ['word', 'edition', 'definition', 'source_url', 'scraped_at', 'status']
MIN_DELAY           = 1.2

# The same path scrape_definitions.py / scrape_synonyms.py lock. Keyed on the
# host rather than on the script, so the three scrapers interlock; a per-script
# lock would permit exactly the doubling this prevents. **This path is the
# contract** — the helper below is duplicated rather than imported (per
# CLAUDE.md: copy at two callers, lift to a shared module at three), so if it
# ever drifts the scrapers stop interlocking silently.
DEXONLINE_LOCK = Path('data/.dexonline.lock')


# ---------------------------------------------------------------------------
# Word lists
# ---------------------------------------------------------------------------

def _read_word_file(path: Path) -> list[str]:
    with path.open('r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def _write_word_file(path: Path, words: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        for w in words:
            f.write(w + '\n')


def load_dcr2_words() -> list[str]:
    """DCR2 headwords, read from the cache written by extract_dcr.py.

    The dump scan lives in extract_dcr.py (the DCR2 extractor) on purpose: its
    word list is the canonical one, and the scrape must not rescan the dump with
    a second parser that could drift. Run `python extract_dcr.py` once if the
    cache is missing.
    """
    if not DCR2_WORDS_FILE.exists():
        print(f'{DCR2_WORDS_FILE} is missing — run `python extract_dcr.py` first, '
              f'it writes the canonical DCR2 word list while extracting.',
              file=sys.stderr)
        return []
    return _read_word_file(DCR2_WORDS_FILE)


def _enumerate_dcr3_words(session: requests.Session, delay: float) -> list[str]:
    """Union of DCR3 search results over every first letter.

    The per-source search page lists entries under #tab_0 as /intrare/<word>/<id>
    links; one request per letter covers the whole source (measured: the largest
    letter, `x`, holds 53 entries and none are truncated). Words are unquoted
    from the URL and normalized like every other word in the repo.
    """
    words: set[str] = set()
    misses: list[str] = []
    for letter in DCR3_LETTERS:
        url = DCR3_SEARCH_TMPL.format(quote(letter))
        try:
            resp = session.get(url, timeout=20)
        except requests.RequestException as exc:
            print(f'  network error on {url}: {exc}; '
                  f'words for {letter!r} NOT collected', file=sys.stderr)
            misses.append(letter)
            continue
        if resp.status_code != 200:
            print(f'  HTTP {resp.status_code} on {url}; '
                  f'words for {letter!r} NOT collected', file=sys.stderr)
            misses.append(letter)
            continue
        soup = BeautifulSoup(resp.text, 'lxml')
        tab = soup.select_one('#tab_0') or soup.select_one('.tab-pane.active')
        if tab is None:
            misses.append(letter)
            continue
        for a in tab.select('a[href^="/intrare/"]'):
            words.add(normalize(unquote(a['href'].split('/')[-2])))
        time.sleep(delay)

    if misses:
        print(f'WARNING: no words collected for letters {misses!r}; '
              f'rerun with --refresh-words once the site responds', file=sys.stderr)
    return sorted(words)


def load_dcr3_words(session: requests.Session, refresh: bool, delay: float) -> list[str]:
    """DCR3 headwords, enumerated live and cached (see _enumerate_dcr3_words)."""
    if DCR3_WORDS_FILE.exists() and not refresh:
        return _read_word_file(DCR3_WORDS_FILE)
    words = _enumerate_dcr3_words(session, delay)
    _write_word_file(DCR3_WORDS_FILE, words)
    print(f'  DCR3 entries enumerated: {len(words):,} (cached at {DCR3_WORDS_FILE})')
    return words


# ---------------------------------------------------------------------------
# Page parsing
# ---------------------------------------------------------------------------

def parse_dcr_defs(html: str) -> dict[str, list[str]]:
    """Map edition -> list of entry texts from one /definitie/ page.

    A page renders every entry dexonline considers related, so the source is
    read from each wrapper's "sursa:" link, never guessed from the headword.
    """
    soup = BeautifulSoup(html, 'lxml')
    out: dict[str, list[str]] = {}
    for wrapper in soup.select('.defWrapper'):
        details = wrapper.select_one('.defDetails')
        if details is None:
            continue
        edition = next((ed for ed in EDITIONS
                        if details.select_one(f'a.ref[href="/sursa/{ed}"]')), None)
        if edition is None:
            continue
        span = wrapper.select_one('.def')
        if span is None:
            continue
        # Tonic accents are per-letter spans (`comp<span…>u</span>ter`); unwrap
        # them, then smooth() merges the adjacent text nodes so get_text(' ')
        # separates only real elements and never a word's own letters.
        for s in span.select('.tonic-accent'):
            s.unwrap()
        span.smooth()  # bs4 ≥ 4.9
        text = ' '.join(span.get_text(' ', strip=True).split())
        if text:
            out.setdefault(edition, []).append(text)
    return out


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_page(session: requests.Session, word: str) -> tuple[str, str | None]:
    """Fetch one word page. Returns (status, html_or_None).

    status ∈ {ok, error}. Transient failures (network, 429/503) retry once
    after a 30s backoff.
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
            return 'error', None

        if resp.status_code in (429, 503):
            if attempt == 1:
                print(f'  HTTP {resp.status_code}; sleeping 30s then retrying…')
                time.sleep(30)
                continue
            return 'error', None

        if resp.status_code != 200:
            return 'error', None
        return 'ok', resp.text

    return 'error', None


# ---------------------------------------------------------------------------
# Checkpoint / merge
# ---------------------------------------------------------------------------

def load_checkpoint(output_path: Path, retry_not_found: bool = False) -> set[tuple[str, str]]:
    """Read existing output CSV, return set of (word, edition) already attempted.

    When retry_not_found is True, rows with status=not_found are excluded from
    the done set so they get re-queued.
    """
    if not output_path.exists():
        return set()
    done: set[tuple[str, str]] = set()
    with output_path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and 'word' in reader.fieldnames:
            for row in reader:
                if retry_not_found and row.get('status') == 'not_found':
                    continue
                done.add((row['word'], row['edition']))
    return done


def merge_into_db(csv_path: Path, db_path: Path) -> tuple[int, int]:
    """Upsert all status=ok rows from the scraping CSV into dcr_definitions.db."""
    if not csv_path.exists():
        print(f'No checkpoint file at {csv_path}; nothing to merge.')
        return 0, 0
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        'CREATE TABLE IF NOT EXISTS dcr_definitions '
        '(word TEXT NOT NULL, edition TEXT NOT NULL, definition TEXT NOT NULL, '
        ' PRIMARY KEY (word, edition))'
    )

    inserted = 0
    skipped = 0
    with csv_path.open('r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('status') != 'ok':
                skipped += 1
                continue
            conn.execute(
                'INSERT OR REPLACE INTO dcr_definitions (word, edition, definition) '
                'VALUES (?, ?, ?)',
                (row['word'], row['edition'], row['definition']),
            )
            inserted += 1
    conn.commit()
    conn.close()
    return inserted, skipped


# ---------------------------------------------------------------------------
# Host lock
# ---------------------------------------------------------------------------

class LockHeld(Exception):
    """Another process is already making requests to dexonline.ro."""


def acquire_host_lock(path: Path = DEXONLINE_LOCK):
    """
    Serialise every process that makes requests to dexonline.ro.

    `--delay` is a *per-process* guard, so two copies each politely waiting 3s still
    hit a community-run site every 1.5s — which is what happened on 2026-08-08 with
    two `scrape_synonyms.py` runs. The lock makes the delay mean what it says.

    Keyed on the **host**, not on this script, so the three scrapers exclude each
    other rather than each holding a private lock and doubling the rate between them.

    `flock`, not a PID file: the kernel releases it when the process dies, so a
    SIGKILLed run cannot strand a stale lock that someone has to `rm` by hand. The
    pid written inside is only ever read back to name the holder in the error.

    Returns the open handle — **keep a reference for the duration of the run**,
    since closing it releases the lock.
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
        description='Export all DCR2/DCR3 definitions from dexonline.ro.',
    )
    parser.add_argument('-o', '--output', type=Path, default=DEFAULT_OUTPUT,
                        help='Checkpoint CSV (default: %(default)s)')
    parser.add_argument('--db', type=Path, default=DEFAULT_DB,
                        help='Destination DB for --merge (default: %(default)s)')
    parser.add_argument('--delay', type=float, default=1.2,
                        help='Seconds between requests (default: %(default)s; '
                             f'refused below {MIN_DELAY})')
    parser.add_argument('--limit', type=int, default=None, metavar='N',
                        help='Stop after N non-checkpointed words')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print plan only; no HTTP requests, no output written')
    parser.add_argument('--merge', action='store_true',
                        help='After scraping, upsert ok rows into dcr_definitions.db')
    parser.add_argument('--merge-only', action='store_true',
                        help='Skip scraping; only run the merge step')
    parser.add_argument('--refresh-words', action='store_true',
                        help='Rescan the dump / re-enumerate DCR3 instead of '
                             'using the cached word lists')
    parser.add_argument('--retry-not-found', action='store_true',
                        help='Re-queue (word, edition) pairs previously marked not_found')
    args = parser.parse_args()

    if args.delay < MIN_DELAY:
        print(f'Refusing --delay below {MIN_DELAY}s: dexonline.ro is community-run.',
              file=sys.stderr)
        return 1

    if args.merge_only:
        inserted, skipped = merge_into_db(args.output, args.db)
        print(f'Merged: {inserted:,} rows upserted, {skipped:,} skipped (non-ok).')
        return 0

    # Taken before the queue is planned, so a second run hears why it is stopping
    # instead of a plan it will not carry out. `--dry-run` makes no requests and so
    # stays lock-free: inspecting the queue while a scrape is going is legitimate,
    # and `--merge-only` has already returned above for the same reason.
    # Held for the rest of the run — `lock` looks unused, but closing it unlocks.
    lock = None                                                       # noqa: F841
    if not args.dry_run:
        try:
            lock = acquire_host_lock()                                # noqa: F841
        except LockHeld as held:
            print(f'Another dexonline scrape is already running ({held}).\n'
                  f'Two at once halve the interval between requests, which is the '
                  f'one thing --delay exists to prevent. Wait for it, or stop it '
                  f'first.', file=sys.stderr)
            return 1

    session = requests.Session()
    session.headers.update({'User-Agent': USER_AGENT})

    dcr2 = load_dcr2_words()
    if args.dry_run:
        if DCR3_WORDS_FILE.exists():
            dcr3 = _read_word_file(DCR3_WORDS_FILE)
        else:
            dcr3 = []
            print('DCR3 word cache missing — run once without --dry-run to build it '
                  '(31 requests, one per letter).')
    else:
        dcr3 = load_dcr3_words(session, args.refresh_words, args.delay)

    targets: dict[str, set[str]] = {}
    for w in dcr2:
        targets.setdefault(w, set()).add('dcr2')
    for w in dcr3:
        targets.setdefault(w, set()).add('dcr3')

    checkpoint = load_checkpoint(args.output, retry_not_found=args.retry_not_found)
    plan_words = [w for w in sorted(targets)
                  if any((w, ed) not in checkpoint for ed in targets[w])]
    plan_pairs = sum(len([ed for ed in targets[w] if (w, ed) not in checkpoint])
                     for w in plan_words)
    if args.limit is not None:
        plan_words = plan_words[:args.limit]

    print(f'Output         : {args.output}')
    print(f'Mode           : {"DRY RUN (no HTTP, no writes)" if args.dry_run else "LIVE"}')
    print(f'Delay          : {args.delay}s')
    print(f'DCR2 words     : {len(dcr2):,}')
    print(f'DCR3 words     : {len(dcr3):,}')
    print(f'Union          : {len(targets):,} words, {plan_pairs:,} pairs')
    print(f'  checkpointed : {len(checkpoint):,} pairs')
    print(f'To scrape      : {len(plan_words):,} words')
    if args.limit:
        print(f'Limit          : {args.limit}')
    print()

    if not plan_words:
        print('Nothing to scrape.')
        if args.merge:
            inserted, skipped = merge_into_db(args.output, args.db)
            print(f'Merged: {inserted:,} rows upserted, {skipped:,} skipped (non-ok).')
        return 0

    if args.dry_run:
        for i, word in enumerate(plan_words, 1):
            eds = ','.join(sorted(ed for ed in targets[word]
                                  if (word, ed) not in checkpoint))
            print(f'[{i}/{len(plan_words)}] DRY RUN: '
                  f'{DEXONLINE_URL_TMPL.format(quote(word, safe=""))}  ({eds})')
        print(f'\nDone. {len(plan_words):,} URLs printed, 0 requests made.')
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_header = not args.output.exists()

    counts = {'ok': 0, 'not_found': 0, 'error': 0}

    with args.output.open('a', encoding='utf-8', newline='') as fout:
        writer = csv.DictWriter(fout, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
            fout.flush()

        for i, word in enumerate(plan_words, 1):
            url = DEXONLINE_URL_TMPL.format(quote(word, safe=''))
            try:
                status, html = fetch_page(session, word)
                parsed = parse_dcr_defs(html) if html else {}
            except KeyboardInterrupt:
                print('\nInterrupted. Partial output retained for checkpoint resume.')
                break

            for ed in sorted(ed for ed in targets[word] if (word, ed) not in checkpoint):
                definition = ' | '.join(parsed.get(ed, [])) if status == 'ok' else ''
                row_status = ('ok' if definition else 'not_found') if status == 'ok' else status
                counts[row_status] += 1
                preview = (definition[:60] + '…') if len(definition) > 60 else definition
                print(f'[{i}/{len(plan_words)}] {word:25s} [{ed}] → {row_status:10s} {preview}')

                writer.writerow({
                    'word':       word,
                    'edition':    ed,
                    'definition': definition,
                    'source_url': url,
                    'scraped_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                    'status':     row_status,
                })
                fout.flush()

            if i < len(plan_words):
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
