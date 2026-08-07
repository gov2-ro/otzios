#!/usr/bin/env python3
"""One-time migration: add `word_id` (permanent share-URL id) to public/data/ui.db.

Backfills the column from data/word_ids.tsv without a full rebuild (a rebuild
also recomputes zipf frequencies, which is slow). Creates the registry on first
run. Idempotent — safe to re-run, and re-running must never change an existing
id; see tools/word_ids.py for why that matters.

Run from repo root:
    python tools/migrate_ui_db_word_ids.py
"""
import sqlite3
from pathlib import Path

from word_ids import apply_to_db

UI_DB_PATH = Path('public/data/ui.db')

conn = sqlite3.connect(str(UI_DB_PATH))

try:
    conn.execute('ALTER TABLE words ADD COLUMN word_id INTEGER')
    print('Added column: word_id')
except sqlite3.OperationalError:
    print('Column already exists: word_id')

print(f'{apply_to_db(conn)} rows carry a word_id')

conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_words_word_id ON words(word_id)')

conn.commit()
conn.close()
print('Done.')
