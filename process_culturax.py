#!/usr/bin/env python3
"""
Count DEX word occurrences in CulturaX Romanian (modern web corpus).

CulturaX is cleaned+deduplicated CC + mC4 across 167 languages. Romanian
subset (~10B+ tokens) provides modern usage baseline for diachronic comparison
against Wikisource (historical literary baseline).

Usage:
    python process_culturax.py              # full run (hours to days)
    python process_culturax.py --test       # first 1000 documents
    python process_culturax.py --limit 100000  # process first 100k docs
    python process_culturax.py --resume     # skip already-processed docs

Output: data/processed/corpus_frequencies.db (same schema as process_wikisource.py)
        corpus_name = 'culturax_ro'
"""

import argparse
import gc
import json
import re
import signal
import sqlite3
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

_progress = {'docs_done': 0, 'skip': 0}

def _handle_signal(sig, frame):
    total = _progress['skip'] + _progress['docs_done']
    print(f'\n[{datetime.now()}] Received signal {sig} — exiting at doc {total:,}', flush=True)
    sys.exit(1)

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGHUP, _handle_signal)

LEXEMES_DB   = Path('data/processed/lexemes.db')
FREQ_DB      = Path('data/processed/corpus_frequencies.db')
CHECKPOINT   = Path('data/processed/culturax_checkpoint.json')
CORPUS_NAME  = 'culturax_ro'
COMMIT_EVERY = 5000   # documents between DB commits (larger corpus)


def normalize(text: str) -> str:
    return unicodedata.normalize('NFC',
        text.lower().replace('ş', 'ș').replace('ţ', 'ț'))


def tokenize(text: str) -> list[str]:
    text = normalize(text)
    tokens = re.findall(r"[a-zăâîșț](?:[a-zăâîșț\-']*[a-zăâîșț])?", text)
    return [t for t in tokens if len(t) > 2 and not t.isdigit()]


def load_dex_words(lexemes_db: Path) -> set[str]:
    conn = sqlite3.connect(lexemes_db)
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT lower(formNoAccent)
        FROM Lexeme
        WHERE frequency > 0.01
          AND LENGTH(formNoAccent) > 2
          AND description != ''
          AND description IS NOT NULL
    """)
    words = {normalize(r[0]) for r in c.fetchall()}
    conn.close()
    return words


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


def flush(conn: sqlite3.Connection, word_counts: dict, doc_counts: dict) -> None:
    ts = datetime.now()
    conn.executemany("""
        INSERT INTO corpus_word_frequency
            (word, corpus_name, occurrence_count, document_count, last_updated)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(word, corpus_name) DO UPDATE SET
            occurrence_count = occurrence_count + excluded.occurrence_count,
            document_count   = document_count   + excluded.document_count,
            last_updated     = excluded.last_updated
    """, [(w, CORPUS_NAME, c, doc_counts[w], ts) for w, c in word_counts.items()])
    conn.commit()
    word_counts.clear()
    doc_counts.clear()


def save_checkpoint(docs_done: int, tokens_done: int) -> None:
    CHECKPOINT.write_text(json.dumps({'docs_processed': docs_done, 'tokens_processed': tokens_done}))


def load_checkpoint() -> tuple[int, int]:
    if CHECKPOINT.exists():
        data = json.loads(CHECKPOINT.read_text())
        return data.get('docs_processed', 0), data.get('tokens_processed', 0)
    return 0, 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--test',   action='store_true', help='First 1000 documents only')
    parser.add_argument('--limit',  type=int, help='Process first N documents')
    parser.add_argument('--resume', action='store_true', help='Skip already-processed docs')
    args = parser.parse_args()

    limit  = args.limit or (1000 if args.test else None)
    if args.resume:
        skip, prev_tokens = load_checkpoint()
    else:
        skip, prev_tokens = 0, 0

    if args.resume and skip:
        print(f'Resuming from document {skip:,}')

    print('Loading DEX word list from lexemes.db...')
    dex_words = load_dex_words(LEXEMES_DB)
    print(f'  {len(dex_words):,} unique lookup forms')

    conn = init_freq_db(FREQ_DB)

    print('Loading CulturaX Romanian dataset (streaming)...')
    try:
        from datasets import load_dataset
    except ImportError:
        print('datasets not installed — run: pip install datasets')
        return 1

    try:
        ds = load_dataset('uonlp/CulturaX', 'ro',
                          split='train', streaming=True, trust_remote_code=False)
    except Exception as e:
        print(f'Failed to load dataset: {e}')
        return 1

    word_counts: dict = defaultdict(int)
    doc_counts:  dict = defaultdict(int)
    total_tokens = 0
    docs_done    = 0
    start        = time.time()
    _progress['skip'] = skip

    mode = "test (1000 docs)" if args.test else (f"limit {limit:,} docs" if limit else "full")
    print(f'Processing {mode}...\n')

    if skip:
        print(f'  Fast-forwarding past {skip:,} documents via ds.skip()...')
        ds = ds.skip(skip)
        gc.collect()
        print(f'  Resuming at document {skip:,}\n')

    try:
        for doc in ds:
            if limit and docs_done >= limit:
                break

            tokens = tokenize(doc.get('text', ''))
            total_tokens += len(tokens)

            doc_words: set = set()
            for tok in tokens:
                if tok in dex_words:
                    word_counts[tok] += 1
                    doc_words.add(tok)
            for w in doc_words:
                doc_counts[w] += 1

            docs_done += 1
            _progress['docs_done'] = docs_done

            if docs_done % COMMIT_EVERY == 0:
                flush(conn, word_counts, doc_counts)
                save_checkpoint(skip + docs_done, prev_tokens + total_tokens)
                elapsed = time.time() - start
                rate = docs_done / elapsed
                print(f'  {docs_done:,} docs | {total_tokens:,} tokens | '
                      f'{rate:.1f} docs/s', flush=True)
    except Exception as e:
        print(f'\n[{datetime.now()}] ERROR after {skip + docs_done:,} docs: {e}', flush=True)
        import traceback
        traceback.print_exc()
        flush(conn, word_counts, doc_counts)
        save_checkpoint(skip + docs_done, prev_tokens + total_tokens)
        raise

    flush(conn, word_counts, doc_counts)
    save_checkpoint(skip + docs_done, prev_tokens + total_tokens)

    elapsed = time.time() - start
    total_docs_all  = skip + docs_done
    total_tokens_all = prev_tokens + total_tokens
    conn.execute("""
        INSERT INTO processing_stats
            (corpus_name, documents_processed, tokens_processed, unique_words_found,
             processing_time_seconds, completed_at, status)
        VALUES (?, ?, ?, ?, ?, ?, 'completed')
    """, (CORPUS_NAME, total_docs_all, total_tokens_all,
          conn.execute("SELECT COUNT(DISTINCT word) FROM corpus_word_frequency WHERE corpus_name=?",
                       (CORPUS_NAME,)).fetchone()[0],
          elapsed, datetime.now()))
    conn.commit()

    print(f'\nDone: {total_docs_all:,} docs, {total_tokens_all:,} tokens in {elapsed:.0f}s ({elapsed/3600:.1f}h)')
    print(f'Results in {FREQ_DB}  (corpus_name = {CORPUS_NAME!r})')

    # Quick summary
    rows = conn.execute("""
        SELECT word, occurrence_count, document_count
        FROM corpus_word_frequency
        WHERE corpus_name = ?
        ORDER BY occurrence_count DESC
        LIMIT 20
    """, (CORPUS_NAME,)).fetchall()
    if rows:
        print('\nTop 20 DEX words in CulturaX RO:')
        print(f'  {"word":<25} {"occurrences":>12} {"documents":>10}')
        for w, oc, dc in rows:
            print(f'  {w:<25} {oc:>12,} {dc:>10,}')

    conn.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
