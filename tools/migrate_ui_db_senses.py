#!/usr/bin/env python3
"""Add and populate senses / sense_citations / words.dex_etymon in an existing ui.db.

The same merge build_ui_db.py runs during a build, applied in place so the tables can
land without re-running the whole pipeline. Idempotent — re-running clears and
repopulates both tables from scratch and produces the same result; that is also the
cheapest way to check the ordering rules in merge_senses() are deterministic (run twice,
diff the two files).

Reads data/processed/meanings.db (from extract_meanings.py); writes only to ui.db.

Run from repo root:
    python tools/migrate_ui_db_senses.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_ui_db import merge_senses

MEANINGS_PATH = Path('data/processed/meanings.db')
UI_DB_PATH    = Path('public/data/ui.db')

if not UI_DB_PATH.exists():
    sys.exit(f'Missing: {UI_DB_PATH}')

conn = sqlite3.connect(str(UI_DB_PATH))

conn.execute("""
    CREATE TABLE IF NOT EXISTS senses (
        word        TEXT    NOT NULL,
        ord         INTEGER NOT NULL,
        breadcrumb  TEXT    NOT NULL,
        depth       INTEGER NOT NULL,
        kind        TEXT    NOT NULL,
        text        TEXT    NOT NULL,
        tags        TEXT,
        synonyms    TEXT,
        PRIMARY KEY (word, ord)
    )
""")
conn.execute("""
    CREATE TABLE IF NOT EXISTS sense_citations (
        word       TEXT    NOT NULL,
        sense_ord  INTEGER NOT NULL,
        ord        INTEGER NOT NULL,
        text       TEXT    NOT NULL,
        PRIMARY KEY (word, sense_ord, ord)
    )
""")
print('Ensured tables: senses, sense_citations')

try:
    conn.execute('ALTER TABLE words ADD COLUMN dex_etymon TEXT')
    print('Added column: dex_etymon')
except sqlite3.OperationalError:
    print('Column already exists: dex_etymon')

try:
    conn.execute('ALTER TABLE senses ADD COLUMN synonyms TEXT')
    print('Added column: senses.synonyms')
except sqlite3.OperationalError:
    print('Column already exists: senses.synonyms')

merge_senses(conn, MEANINGS_PATH)

conn.commit()
conn.close()
print('Done.')
