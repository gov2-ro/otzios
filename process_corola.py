#!/usr/bin/env python3
"""
Load CoRoLa lemma frequencies — a balanced modern reference beside CulturaX.

CulturaX is 17.0B tokens of web crawl, and that is the whole modern panel today. A
word can be alive in print, speech, law or fiction and thin on the open web, so
"absent from CulturaX" overstates death for exactly the registers this project
cares about. CoRoLa is the Romanian Academy's reference corpus: 1B+ tokens,
balanced across 71 sub-domains, with a spoken component — register diversity rather
than more crawl.

**This loads the WORD list, not the lemma list, and that is the whole design.**

The first version of this script read `corola_lemma_freq_*`, and it could not be used:
those lists are lemmatized by TTL, whose chosen headword is often the form this
project holds as the *archaic variant*. `strugur` carried 12,176 against `strugure`'s
724, `gherghină` 3,658 against `gheorghină`'s 2. Joining on the headword string handed
the modern word's whole count to its obsolete spelling — marking exactly the words
this project hunts for as alive.

The fix is not to reconcile someone else's lemmas. It is to take the **surface-form**
lists and let the existing machinery do the rollup, because that machinery already
solves this problem: `strugur` and `strugure` share `struguri`, `strugurii` and
`strugurilor`, so `validate_diachronic.aggregate_by_family` splits those forms between
them by headword prominence — the same `veșcă`/`veste` disambiguation used for every
other corpus. Counts therefore land on DEX's lemma inventory, computed from DEX's own
paradigms, rather than on TTL's.

So these rows go in `corpus_word_frequency` like Wikisource, LUMRO and CulturaX, and
are counted exactly the same way downstream.

**There are no document counts** — the published lists are frequency only, so
`document_count` is 0 for every row. This is safe *only because CoRoLa is a modern
panel*: `verdict()` reads `hist_occ`, `hist_docs` and `modern_occ`, and never a modern
document count. **Never add this corpus to `HIST_CORPORA`** — there its zero documents
would silently veto attestation, which is precisely the `hist_docs` bug fixed on
2026-08-10.

**A missing word means "not in the list", never "seen zero times"** — the same trap as
`frequency = 0` meaning no data rather than rarest.

**The list is legal-skewed.** Against CulturaX, `alin` is over-represented ~5,000,000×,
`anexă` 178×, `prevedere` 175×, `articol` 18×, while everyday vocabulary sits at
0.2–3×. That is worth knowing before reading any CoRoLa-driven verdict change: a word
that survives only in legislation will look alive here, which is closer to right than
calling it extinct but is not the same as general currency.

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

# Surface-form list — see the docstring for why not the lemma list. Lowercased because
# every lookup in this project is lowercase; diacritics kept because `casă`/`casa` are
# different words and the nodiacritics variants collapse exactly what we filter on.
MEMBER = 'corola_word_freq_all_lowercase.tsv'

CORPUS_NAME = 'corola_ro'


def normalize(text: str) -> str:
    return unicodedata.normalize('NFC',
        text.lower().replace('ş', 'ș').replace('ţ', 'ț'))


def init_db(db_path: Path) -> sqlite3.Connection:
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


def read_list(zip_path: Path, member: str) -> tuple[dict[str, int], int, int]:
    """Return ({surface_form: count}, rows_read, malformed)."""
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
                word, count = parts
                try:
                    n = int(count)
                except ValueError:
                    malformed += 1
                    continue
                word = normalize(word)
                if not word:
                    malformed += 1
                    continue
                # Normalization can collide two source rows (cedilla vs comma forms);
                # summing is right — they are the same word written two ways.
                freqs[word] = freqs.get(word, 0) + n
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
    print(f'  surface forms   : {len(freqs):,}')
    print(f'  malformed       : {malformed:,}')
    print(f'  total tokens    : {total:,}')
    print(f'  collisions      : {rows - malformed - len(freqs):,} '
          f'(source rows merged by normalization)')

    if args.dry_run:
        print('\nDRY RUN — nothing written.')
        return 0

    conn = init_db(FREQ_DB)

    # The first version of this script wrote a per-lemma table. That approach was
    # abandoned (see the docstring), and leaving the table behind would leave a
    # plausible-looking source of TTL-lemmatized counts for someone to join against.
    if conn.execute("SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='corola_lemma_frequency'").fetchone():
        conn.execute('DROP TABLE corola_lemma_frequency')
        print('Dropped the superseded corola_lemma_frequency table.')

    existing = conn.execute(
        'SELECT COUNT(*) FROM corpus_word_frequency WHERE corpus_name = ?',
        (CORPUS_NAME,)).fetchone()[0]
    if existing and not args.wipe:
        print(f'\n{CORPUS_NAME} already holds {existing:,} rows. Pass --wipe to replace.',
              file=sys.stderr)
        return 1
    if args.wipe and existing:
        conn.execute('DELETE FROM corpus_word_frequency WHERE corpus_name = ?', (CORPUS_NAME,))
        conn.execute('DELETE FROM processing_stats     WHERE corpus_name = ?', (CORPUS_NAME,))
        print(f'Wiped {existing:,} existing rows.')

    ts = datetime.now().isoformat()
    # document_count is 0 throughout: the published lists carry no document counts.
    # Safe only because CoRoLa is a modern panel and verdict() never reads a modern
    # document count — see the docstring's warning about HIST_CORPORA.
    conn.executemany("""
        INSERT INTO corpus_word_frequency
            (word, corpus_name, occurrence_count, document_count, last_updated)
        VALUES (?, ?, ?, 0, ?)
        ON CONFLICT(word, corpus_name) DO UPDATE SET
            occurrence_count = excluded.occurrence_count,
            last_updated     = excluded.last_updated
    """, [(w, CORPUS_NAME, c, ts) for w, c in freqs.items()])
    elapsed = time.time() - started
    conn.execute("""
        INSERT INTO processing_stats
            (corpus_name, documents_processed, tokens_processed, unique_words_found,
             processing_time_seconds, completed_at, status)
        VALUES (?, 0, ?, ?, ?, ?, 'completed')
    """, (CORPUS_NAME, total, len(freqs), elapsed, ts))
    conn.commit()
    conn.close()

    print(f'\nDone in {elapsed:.0f}s → {FREQ_DB}  (corpus_name = {CORPUS_NAME!r})')
    print('Reminder: input only. No CoRoLa-derived count goes into ui.db (CC BY-NC-ND).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
