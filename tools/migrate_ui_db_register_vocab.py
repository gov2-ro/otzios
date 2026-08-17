#!/usr/bin/env python3
"""Refresh the 'register' options in an already-built public/data/ui.db.

build_ui_db.py used to exclude 34 usage-style dex_register tags (figurat, popular,
argou, vulgar, ...) from the register filter dropdown, keeping only archaic/geographic
markers. That exclusion is gone — see build_vocab_table() — so this backfills an
existing ui.db without a full pipeline rebuild. Idempotent: re-running recomputes the
same rows from scratch.

Run from repo root:
    python tools/migrate_ui_db_register_vocab.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_ui_db import build_vocab_table

UI_DB_PATH = Path('public/data/ui.db')

if not UI_DB_PATH.exists():
    sys.exit(f'Missing: {UI_DB_PATH}')

conn = sqlite3.connect(str(UI_DB_PATH))
before = conn.execute("SELECT COUNT(*) FROM vocab WHERE kind = 'register'").fetchone()[0]
build_vocab_table(conn, kinds={'register'})
after = conn.execute("SELECT COUNT(*) FROM vocab WHERE kind = 'register'").fetchone()[0]
conn.commit()
conn.close()
print(f'register vocab: {before} → {after} options')
