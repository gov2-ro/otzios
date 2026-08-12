#!/usr/bin/env python3
"""Add and populate words.deverbal_like / words.deverbal_of in an existing ui.db.

The same rule build_ui_db.py runs at the end of a build, applied in place so the columns
can land without re-running the pipeline. Idempotent.

**Run this after the other class migrations**, not before: the rule reads
`regional_only` / `variant_like` / `archaic_spelling` / `dex_variant` /
`diminutive_like` to check the base verb is visible before hiding its noun behind it, so
a column that is missing here reads as "not flagged" and lets a few extra nouns through.

Reads nothing but ui.db.

Run from repo root:
    python tools/migrate_ui_db_deverbal.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_ui_db import _HIDE_FLAGS, mark_deverbal_nouns

UI_DB_PATH = Path('public/data/ui.db')

if not UI_DB_PATH.exists():
    sys.exit(f'Missing: {UI_DB_PATH}')

conn = sqlite3.connect(str(UI_DB_PATH))
for col, decl in (('deverbal_like', 'INTEGER'), ('deverbal_of', 'TEXT')):
    try:
        conn.execute(f'ALTER TABLE words ADD COLUMN {col} {decl}')
        print(f'Added column: {col}')
    except sqlite3.OperationalError:
        print(f'Column already exists: {col}')

have = {r[1] for r in conn.execute('PRAGMA table_info(words)')}
missing = [c for c in _HIDE_FLAGS if c not in have]
if missing:
    print(f'  ! visibility check degraded — no such column: {", ".join(missing)}')

mark_deverbal_nouns(conn)
conn.commit()
conn.close()
print('Done.')
