#!/usr/bin/env python3
"""One-time migration: add `sources` (dictionary membership) to public/data/ui.db.

Backfills the column from data/processed/dict_sources.db without a full rebuild
(a rebuild also recomputes zipf frequencies, which is slow). Idempotent — safe to
re-run.

Run from repo root:
    python tools/migrate_ui_db_sources.py
"""
import sqlite3
from pathlib import Path

from build_ui_db import DICT_SOURCES_PATH, merge_dict_sources

UI_DB_PATH = Path('public/data/ui.db')

conn = sqlite3.connect(str(UI_DB_PATH))

try:
    conn.execute('ALTER TABLE words ADD COLUMN sources TEXT')
    print('Added column: sources')
except sqlite3.OperationalError:
    print('Column already exists: sources')

merge_dict_sources(conn, DICT_SOURCES_PATH)

conn.commit()
conn.close()
print('Done.')
