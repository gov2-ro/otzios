#!/usr/bin/env python3
"""Add and populate words.dex_variant / words.dex_variant_of in an existing ui.db.

The same rule build_ui_db.py runs during a build, applied in place so the column can
land without re-running the pipeline. Idempotent — re-running recomputes both columns
from scratch and produces the same result.

Reads `EntryLexeme` from data/processed/lexemes.db, the modern corpus counts from
data/processed/corpus_frequencies.db and the paradigms from
data/processed/inflected_forms.db; writes only to ui.db.

Run from repo root:
    python tools/migrate_ui_db_dex_variants.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_ui_db import mark_deverbal_nouns, mark_dex_variants

LEXEMES_PATH   = Path('data/processed/lexemes.db')
FREQ_PATH      = Path('data/processed/corpus_frequencies.db')
INFLECTED_PATH = Path('data/processed/inflected_forms.db')
UI_DB_PATH     = Path('public/data/ui.db')

if not UI_DB_PATH.exists():
    sys.exit(f'Missing: {UI_DB_PATH}')

conn = sqlite3.connect(str(UI_DB_PATH))
for col, decl in (('dex_variant', 'INTEGER'), ('dex_variant_of', 'TEXT')):
    try:
        conn.execute(f'ALTER TABLE words ADD COLUMN {col} {decl}')
        print(f'Added column: {col}')
    except sqlite3.OperationalError:
        print(f'Column already exists: {col}')

# mark_dex_variants reads archaic_spelling to keep the two flags disjoint. On a db old
# enough not to have it, everything is fair game — which is the right answer, not a
# reason to fail.
try:
    conn.execute('SELECT archaic_spelling FROM words LIMIT 1').fetchone()
except sqlite3.OperationalError:
    conn.execute('ALTER TABLE words ADD COLUMN archaic_spelling INTEGER')
    print('Added column: archaic_spelling (was absent; left 0)')

mark_dex_variants(conn, LEXEMES_PATH, FREQ_PATH, INFLECTED_PATH)

# mark_deverbal_nouns reads every other flag to check a noun's base verb is still
# visible before hiding the noun behind it, so a run that changes dex_variant leaves it
# stale — a noun kept visible for a verb this pass has just hidden. Cheap and idempotent
# (one pass over the definitions), so it is re-run rather than reasoned about. It is
# skipped on a db built before the deverbal columns landed.
try:
    conn.execute('SELECT deverbal_like FROM words LIMIT 1').fetchone()
    mark_deverbal_nouns(conn)
except sqlite3.OperationalError:
    print('Skipping mark_deverbal_nouns: column deverbal_like is absent')

conn.commit()
conn.close()
print('Done.')
