#!/usr/bin/env python3
"""Add and populate words.diminutive_like in an already-built public/data/ui.db.

The same rule build_ui_db.py runs at the end of a build, applied in place so the
column can land without a full pipeline rebuild. Idempotent — re-running recomputes
the flag from scratch and produces the same result.

Run from repo root:
    python tools/migrate_ui_db_diminutives.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_ui_db import mark_diminutives

LEXEMES_PATH = Path('data/processed/lexemes.db')
UI_DB_PATH   = Path('public/data/ui.db')

if not UI_DB_PATH.exists():
    sys.exit(f'Missing: {UI_DB_PATH}')

conn = sqlite3.connect(str(UI_DB_PATH))
try:
    conn.execute('ALTER TABLE words ADD COLUMN diminutive_like INTEGER')
    print('Added column: diminutive_like')
except sqlite3.OperationalError:
    print('Column already exists: diminutive_like')

mark_diminutives(conn, LEXEMES_PATH)
conn.commit()
conn.close()
print('Done.')
