#!/usr/bin/env python3
"""One-time migration: add zipf_frequency, en_zipf, proper_noun_like to public/data/ui.db.

Run from repo root:
    python tools/migrate_ui_db_explore.py
"""
import sqlite3
from pathlib import Path

LEXEMES_PATH  = Path('data/processed/lexemes.db')
UI_DB_PATH    = Path('public/data/ui.db')
LOANWORD_EN_ZIPF = 4.0

try:
    from wordfreq import zipf_frequency
except ImportError:
    zipf_frequency = None
    print('wordfreq not available — zipf_frequency and en_zipf will remain NULL')

conn = sqlite3.connect(str(UI_DB_PATH))

for col, coltype in [
    ('zipf_frequency', 'REAL'),
    ('en_zipf',        'REAL'),
    ('proper_noun_like', 'INTEGER'),
]:
    try:
        conn.execute(f'ALTER TABLE words ADD COLUMN {col} {coltype}')
        print(f'Added column: {col}')
    except sqlite3.OperationalError:
        print(f'Column already exists: {col}')

if zipf_frequency is not None:
    print('Computing zipf frequencies (this may take a minute)…')
    rows = conn.execute('SELECT word FROM words WHERE zipf_frequency IS NULL').fetchall()
    batch = [
        (zipf_frequency(r[0], 'ro'), zipf_frequency(r[0], 'en'), r[0])
        for r in rows
    ]
    conn.executemany('UPDATE words SET zipf_frequency=?, en_zipf=? WHERE word=?', batch)
    print(f'Updated {len(batch)} rows with zipf data')
else:
    print('Skipping zipf population (wordfreq not available)')

if LEXEMES_PATH.exists():
    print('Computing proper_noun_like from lexemes…')
    lconn = sqlite3.connect(str(LEXEMES_PATH))
    caps = {r[0].lower() for r in lconn.execute(
        "SELECT DISTINCT formNoAccent FROM Lexeme WHERE formNoAccent GLOB '[A-Z]*'"
    ).fetchall()}
    lconn.close()
    conn.execute('UPDATE words SET proper_noun_like = 0')
    if caps:
        ph = ','.join('?' * len(caps))
        conn.execute(f'UPDATE words SET proper_noun_like = 1 WHERE word IN ({ph})', list(caps))
    print(f'Marked {len(caps)} proper-noun candidates')
else:
    print(f'lexemes.db not found at {LEXEMES_PATH}, skipping proper_noun_like')

try:
    conn.execute('CREATE INDEX idx_words_zipf ON words(zipf_frequency)')
    print('Created index idx_words_zipf')
except sqlite3.OperationalError:
    print('Index idx_words_zipf already exists')

conn.commit()
conn.close()
print('Done.')
