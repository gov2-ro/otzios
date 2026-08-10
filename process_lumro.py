#!/usr/bin/env python3
"""
Count DEX word occurrences in LUMRO (dated Romanian novels, 1845–1920).

A second historical panel beside Wikisource. Wikisource is broad but undated and
noisy; LUMRO is 175 novels by 111 authors with the publication year in every
filename, which is what makes it worth adding at only ~7.5M tokens:

    wikisource_ro   14.3M tokens, 12,921 documents, no dates
    lumro_ro         7.5M tokens,     175 documents, 1845–1920, author per document

Measured before ingesting (see docs/corpus-expansion-plan.md): 50.6% of shortlist
words take at least one LUMRO hit, and 1,327 words cross the
HIST_MIN_OCC/HIST_MIN_DOCS attestation bar they currently fail — all of them
presently `absent`, the verdict meaning "no evidence either way".

**The document unit is the novel**, so `document_count` here is out of 175, not out
of 12,921. Two distinct novels is a much stronger attestation than two Wikisource
pages; `validate_diachronic.HIST_MIN_DOCS` is applied to the combined historical
panel and that asymmetry is deliberate, not an oversight.

Source: https://github.com/upb-nlp/LUMRO (JSON per novel, `{chapter: [paragraph, …]}`).
Download once with:

    curl -sL -o data/raw/lumro.zip \
        https://codeload.github.com/upb-nlp/LUMRO/zip/refs/heads/main

Usage:
    python process_lumro.py --dry-run    # parse and count, write nothing
    python process_lumro.py              # full run (refuses if rows already exist)
    python process_lumro.py --wipe       # clear lumro_ro rows first, then run

Output: data/processed/corpus_frequencies.db  (corpus_name = 'lumro_ro')
"""

import argparse
import json
import re
import sqlite3
import sys
import time
import unicodedata
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

LEXEMES_DB  = Path('data/processed/lexemes.db')
FREQ_DB     = Path('data/processed/corpus_frequencies.db')
SOURCE_ZIP  = Path('data/raw/lumro.zip')
CORPUS_NAME = 'lumro_ro'

# "1855. Dimitrie Bolintineanu - Manoil.json" → year 1855, author Dimitrie Bolintineanu.
FILENAME_RE = re.compile(r'/(\d{4})\.\s*(.+?)\s+-\s+(.+)\.json$')


def normalize(text: str) -> str:
    """Same normalization as the other corpus processors — see dump_parser.normalize.

    LUMRO's diacritics are overwhelmingly cedilla-form (measured: `ş` 1,994 vs `ș` 13
    in one sampled novel), so this step is doing real work here rather than being a
    formality.
    """
    return unicodedata.normalize('NFC',
        text.lower().replace('ş', 'ș').replace('ţ', 'ț'))


def tokenize(text: str) -> list[str]:
    """Identical to process_wikisource.tokenize — the two panels must be counted the
    same way or their occurrence counts cannot be added together."""
    text = normalize(text)
    tokens = re.findall(r"[a-zăâîșț](?:[a-zăâîșț\-']*[a-zăâîșț])?", text)
    return [t for t in tokens if len(t) > 2 and not t.isdigit()]


def load_dex_words(lexemes_db: Path) -> set[str]:
    """The ~315k DEX lookup forms, on the same terms as process_wikisource."""
    conn = sqlite3.connect(lexemes_db)
    rows = conn.execute("""
        SELECT DISTINCT lower(formNoAccent)
        FROM Lexeme
        WHERE typeof(frequency) = 'real'
          AND frequency > 0.01
          AND LENGTH(formNoAccent) > 2
          AND (
            (description != '' AND description IS NOT NULL)
            OR modelType IN ('A','F','M','N','VT','VI','IL','PT','P')
          )
    """).fetchall()
    conn.close()
    return {normalize(r[0]) for r in rows}


def init_freq_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS corpus_word_frequency (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            word          TEXT NOT NULL,
            corpus_name   TEXT NOT NULL,
            occurrence_count  INTEGER DEFAULT 0,
            document_count    INTEGER DEFAULT 0,
            last_updated  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(word, corpus_name)
        );
        CREATE INDEX IF NOT EXISTS idx_corpus_word
            ON corpus_word_frequency(word, corpus_name);
        CREATE TABLE IF NOT EXISTS processing_stats (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            corpus_name             TEXT NOT NULL,
            documents_processed     INTEGER DEFAULT 0,
            tokens_processed        INTEGER DEFAULT 0,
            unique_words_found      INTEGER DEFAULT 0,
            processing_time_seconds REAL,
            completed_at            TIMESTAMP,
            status                  TEXT DEFAULT 'in_progress'
        );
    """)
    conn.commit()
    return conn


def wipe(conn: sqlite3.Connection) -> None:
    conn.execute('DELETE FROM corpus_word_frequency WHERE corpus_name = ?', (CORPUS_NAME,))
    conn.execute('DELETE FROM processing_stats     WHERE corpus_name = ?', (CORPUS_NAME,))
    conn.commit()
    print(f'Wiped existing {CORPUS_NAME} rows.')


def existing_rows(conn: sqlite3.Connection) -> int:
    return conn.execute(
        'SELECT COUNT(*) FROM corpus_word_frequency WHERE corpus_name = ?',
        (CORPUS_NAME,)).fetchone()[0]


def iter_novels(zip_path: Path):
    """Yield (year|None, author|None, title, text) per novel, in filename order."""
    with zipfile.ZipFile(zip_path) as z:
        names = sorted(n for n in z.namelist()
                       if n.endswith('.json') and 'Romanian_novels_JSON' in n)
        for name in names:
            m = FILENAME_RE.search(name)
            year   = int(m.group(1)) if m else None
            author = m.group(2)      if m else None
            title  = m.group(3)      if m else Path(name).stem
            data = json.loads(z.read(name))
            # {chapter_number: [paragraph, …]} — chapter keys are strings and their
            # order does not matter for counting.
            text = ' '.join(
                p for chapter in data.values()
                for p in (chapter if isinstance(chapter, list) else [str(chapter)])
            )
            yield year, author, title, text


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--source', type=Path, default=SOURCE_ZIP,
                    help=f'LUMRO repo zip (default: {SOURCE_ZIP})')
    ap.add_argument('--dry-run', action='store_true',
                    help='Parse and count, write nothing')
    ap.add_argument('--wipe', action='store_true',
                    help=f'Clear existing {CORPUS_NAME} rows before writing')
    args = ap.parse_args()

    if not args.source.exists():
        print(f'Missing: {args.source}\n'
              f'  curl -sL -o {args.source} '
              f'https://codeload.github.com/upb-nlp/LUMRO/zip/refs/heads/main',
              file=sys.stderr)
        return 1
    if not LEXEMES_DB.exists():
        print(f'Missing: {LEXEMES_DB} — run extract_lexemes.py first.', file=sys.stderr)
        return 1

    print('Loading DEX word list from lexemes.db...')
    dex_words = load_dex_words(LEXEMES_DB)
    print(f'  {len(dex_words):,} unique lookup forms\n')

    conn = None
    if not args.dry_run:
        conn = init_freq_db(FREQ_DB)
        if args.wipe:
            wipe(conn)
        elif existing_rows(conn):
            # The upsert accumulates, so a second run without --wipe would silently
            # double every count rather than fail — the kind of error that only shows
            # up as a corpus mysteriously twice its size.
            print(f'{CORPUS_NAME} already has {existing_rows(conn):,} rows in {FREQ_DB}.\n'
                  f'Re-running would add to them, not replace them. Pass --wipe to '
                  f'rebuild, or --dry-run to inspect.', file=sys.stderr)
            return 1

    started = time.time()
    occ: dict[str, int] = defaultdict(int)
    doc: dict[str, int] = defaultdict(int)
    total_tokens = docs = matched = 0
    years: list[int] = []
    authors: set[str] = set()

    for year, author, title, text in iter_novels(args.source):
        tokens = tokenize(text)
        total_tokens += len(tokens)
        docs += 1
        if year:
            years.append(year)
        if author:
            authors.add(author)
        seen = set()
        for t in tokens:
            if t in dex_words:
                occ[t] += 1
                matched += 1
                seen.add(t)
        for t in seen:
            doc[t] += 1

    elapsed = time.time() - started

    print(f'Novels            : {docs:,}')
    print(f'  with a year     : {len(years):,}'
          + (f'  ({min(years)}–{max(years)})' if years else ''))
    print(f'  distinct authors: {len(authors):,}')
    print(f'Tokens            : {total_tokens:,}')
    print(f'  matched to DEX  : {matched:,} ({matched/total_tokens:.1%})')
    print(f'Unique DEX words  : {len(occ):,}')

    if years:
        decades: dict[int, int] = defaultdict(int)
        for y in years:
            decades[(y // 10) * 10] += 1
        spread = '  '.join(f'{d}s:{n}' for d, n in sorted(decades.items()))
        print(f'By decade         : {spread}')

    if args.dry_run:
        print('\nDRY RUN — nothing written.')
        return 0

    ts = datetime.now().isoformat()
    conn.executemany("""
        INSERT INTO corpus_word_frequency
            (word, corpus_name, occurrence_count, document_count, last_updated)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(word, corpus_name) DO UPDATE SET
            occurrence_count = occurrence_count + excluded.occurrence_count,
            document_count   = document_count   + excluded.document_count,
            last_updated     = excluded.last_updated
    """, [(w, CORPUS_NAME, c, doc[w], ts) for w, c in occ.items()])
    conn.execute("""
        INSERT INTO processing_stats
            (corpus_name, documents_processed, tokens_processed, unique_words_found,
             processing_time_seconds, completed_at, status)
        VALUES (?, ?, ?, ?, ?, ?, 'completed')
    """, (CORPUS_NAME, docs, total_tokens, len(occ), elapsed, ts))
    conn.commit()
    conn.close()

    print(f'\nDone in {elapsed:.0f}s → {FREQ_DB}  (corpus_name = {CORPUS_NAME!r})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
