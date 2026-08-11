#!/usr/bin/env python3
"""Add and populate words.editor_pick / editor_demote in an already-built ui.db.

The same step build_ui_db.py runs near the end of a build, applied in place so the
curator's marks can land without a full pipeline rebuild — which is the common case,
since re-reading the marks is cheap and re-running the pipeline is not.

Idempotent: apply_to_db() resets both columns to 0 before setting them, so a second
run produces the same values and a word whose mark was withdrawn loses the flag.

Run from repo root:
    python tools/migrate_ui_db_editorial.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from editorial import EDITORIAL_PATH, apply_to_db

UI_DB_PATH = Path('public/data/ui.db')

if not UI_DB_PATH.exists():
    sys.exit(f'Missing: {UI_DB_PATH}')

conn = sqlite3.connect(str(UI_DB_PATH))
for col in ('editor_pick', 'editor_demote'):
    try:
        conn.execute(f'ALTER TABLE words ADD COLUMN {col} INTEGER')
        print(f'Added column: {col}')
    except sqlite3.OperationalError:
        print(f'Column already exists: {col}')

try:
    conn.execute('CREATE INDEX IF NOT EXISTS idx_words_editor '
                 'ON words(editor_pick, editor_demote)')
except sqlite3.OperationalError as e:
    print(f'Index not created: {e}')

picks, demotes, missing = apply_to_db(conn, EDITORIAL_PATH)
conn.commit()
conn.close()

print(f'{picks} pick, {demotes} demote'
      + (f' ({missing} in {EDITORIAL_PATH} are not in this ui.db)' if missing else ''))
print('Done.')
