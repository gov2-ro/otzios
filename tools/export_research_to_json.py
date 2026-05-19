#!/usr/bin/env python3
"""Dump data/research.db to the localStorage JSON shape used by the PHP UI.

Usage:
    python tools/export_research_to_json.py > research_export.json

Then in the browser console on the PHP site:
    localStorage.setItem('otios.research', JSON.stringify(<paste JSON here>))
"""
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path('data/research.db')

if not DB_PATH.exists():
    sys.exit(f'Not found: {DB_PATH}')

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

words = {}
for row in conn.execute('SELECT * FROM bookmarks'):
    r = dict(row)
    tags_raw = (r.get('tags') or '').strip()
    tags = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []
    entry = {
        'bookmarked': bool(r.get('bookmarked')),
        'note':       r.get('note') or '',
        'tags':       tags,
        'updated_at': r.get('updated_at') or '',
    }
    if entry['bookmarked'] or entry['note'] or entry['tags']:
        words[r['word']] = entry

conn.close()

output = {'version': 1, 'words': words}
print(json.dumps(output, ensure_ascii=False, indent=2))
sys.stderr.write(f'Exported {len(words)} words\n')
