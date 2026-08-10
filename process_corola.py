#!/usr/bin/env python3
"""
Load CoRoLa lemma frequencies — a balanced modern reference beside CulturaX.

CulturaX is 17.0B tokens of web crawl, and that is the whole modern panel today. A
word can be alive in print, speech, law or fiction and thin on the open web, so
"absent from CulturaX" overstates death for exactly the registers this project
cares about. CoRoLa is the Romanian Academy's reference corpus: 1B+ tokens,
balanced across 71 sub-domains, with a spoken component — register diversity rather
than more crawl.

**These counts are per LEMMA, not per surface form.** That is the opposite of
`corpus_word_frequency`'s invariant (see CLAUDE.md, "Corpus counts are per surface
form"), which is why they live in their own table and must NOT be passed through
`validate_diachronic.aggregate_by_family`: the lists are already TTL-lemmatized, so
rolling them up a second time would credit a lemma with its relatives' counts.

**There are no document counts.** The published lists are frequency only. Nothing
may apply a document threshold to CoRoLa, and a missing lemma means "not in the
list", never "seen in zero documents" — the same trap as `frequency = 0` meaning
no data rather than rarest.

**Licence: CC BY-NC-ND 4.0.** Non-commercial is satisfied (this project is not
commercial). No-derivatives is why CoRoLa is an *input only*: it may inform a
verdict, but no CoRoLa-derived count may be republished — nothing here writes into
`public/data/ui.db`, and it should stay that way.

Source: https://zenodo.org/records/7091535  (corola_frequencies.zip, 114 MB, 24 lists)
Download once with:

    curl -sL -o data/raw/corola_frequencies.zip \
        "https://zenodo.org/records/7091535/files/corola_frequencies.zip?download=1"

Usage:
    python process_corola.py --dry-run    # parse and report, write nothing
    python process_corola.py              # load into corpus_frequencies.db
    python process_corola.py --wipe       # replace an existing load

Output: data/processed/corpus_frequencies.db, table `corola_lemma_frequency`.
"""

import argparse
import sqlite3
import sys
import time
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

FREQ_DB    = Path('data/processed/corpus_frequencies.db')
SOURCE_ZIP = Path('data/raw/corola_frequencies.zip')

# Lemma list, lowercased, diacritics kept. Lowercase because every lookup in this
# project is lowercase; diacritics kept because `casă`/`casa` are different words and
# the nodiacritics variants collapse exactly the distinctions we filter on.
MEMBER = 'corola_lemma_freq_all_lowercase.tsv'

CORPUS_NAME = 'corola_ro'


def normalize(text: str) -> str:
    return unicodedata.normalize('NFC',
        text.lower().replace('ş', 'ș').replace('ţ', 'ț'))


def init_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        -- Per-LEMMA counts, deliberately not in corpus_word_frequency: that table
        -- holds surface forms and everything downstream rolls it up over paradigms.
        -- No document_count column, because the published lists have none — an
        -- absent column cannot be misread as a zero.
        CREATE TABLE IF NOT EXISTS corola_lemma_frequency (
            lemma             TEXT PRIMARY KEY,
            occurrence_count  INTEGER NOT NULL,
            last_updated      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
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


def read_list(zip_path: Path, member: str) -> tuple[dict[str, int], int, int]:
    """Return ({lemma: count}, rows_read, malformed)."""
    freqs: dict[str, int] = {}
    rows = malformed = 0
    with zipfile.ZipFile(zip_path) as z:
        with z.open(member) as fh:
            for raw in fh:
                rows += 1
                parts = raw.decode('utf-8', errors='replace').rstrip('\n').split('\t')
                if len(parts) != 2:
                    malformed += 1
                    continue
                lemma, count = parts
                try:
                    n = int(count)
                except ValueError:
                    malformed += 1
                    continue
                lemma = normalize(lemma)
                if not lemma:
                    malformed += 1
                    continue
                # Normalization can collide two source rows (cedilla vs comma forms);
                # summing is right — they are the same lemma written two ways.
                freqs[lemma] = freqs.get(lemma, 0) + n
    return freqs, rows, malformed


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--source', type=Path, default=SOURCE_ZIP)
    ap.add_argument('--member', default=MEMBER, help=f'List inside the zip (default: {MEMBER})')
    ap.add_argument('--dry-run', action='store_true', help='Parse and report, write nothing')
    ap.add_argument('--wipe', action='store_true', help='Replace an existing load')
    args = ap.parse_args()

    if not args.source.exists():
        print(f'Missing: {args.source}\n'
              f'  curl -sL -o {args.source} '
              f'"https://zenodo.org/records/7091535/files/corola_frequencies.zip?download=1"',
              file=sys.stderr)
        return 1

    started = time.time()
    print(f'Reading {args.member} from {args.source}...')
    freqs, rows, malformed = read_list(args.source, args.member)
    total = sum(freqs.values())

    print(f'  rows read       : {rows:,}')
    print(f'  lemmas kept     : {len(freqs):,}')
    print(f'  malformed       : {malformed:,}')
    print(f'  total tokens    : {total:,}')
    print(f'  collisions      : {rows - malformed - len(freqs):,} '
          f'(source rows merged by normalization)')

    if args.dry_run:
        print('\nDRY RUN — nothing written.')
        return 0

    conn = init_db(FREQ_DB)
    existing = conn.execute('SELECT COUNT(*) FROM corola_lemma_frequency').fetchone()[0]
    if existing and not args.wipe:
        print(f'\ncorola_lemma_frequency already holds {existing:,} lemmas. '
              f'Pass --wipe to replace.', file=sys.stderr)
        return 1
    if args.wipe and existing:
        conn.execute('DELETE FROM corola_lemma_frequency')
        conn.execute('DELETE FROM processing_stats WHERE corpus_name = ?', (CORPUS_NAME,))
        print(f'Wiped {existing:,} existing lemmas.')

    ts = datetime.now().isoformat()
    conn.executemany(
        'INSERT OR REPLACE INTO corola_lemma_frequency '
        '(lemma, occurrence_count, last_updated) VALUES (?, ?, ?)',
        [(w, c, ts) for w, c in freqs.items()])
    elapsed = time.time() - started
    conn.execute("""
        INSERT INTO processing_stats
            (corpus_name, documents_processed, tokens_processed, unique_words_found,
             processing_time_seconds, completed_at, status)
        VALUES (?, 0, ?, ?, ?, ?, 'completed')
    """, (CORPUS_NAME, total, len(freqs), elapsed, ts))
    conn.commit()
    conn.close()

    print(f'\nDone in {elapsed:.0f}s → {FREQ_DB}  (table `corola_lemma_frequency`)')
    print('Reminder: input only. No CoRoLa-derived count goes into ui.db (CC BY-NC-ND).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
