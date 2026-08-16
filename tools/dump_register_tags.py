#!/usr/bin/env python3
"""
Dump words carrying DEX's own "registru stilistic" usage-style tags — vulgar, argou,
peiorativ, depreciativ, jargon, popular, familiar, ironic, glumeț, eufemistic, ieșit din
uz — one CSV from the full dexonline dump, one restricted to our shortlist.

Not a filter: these are exploratory dumps for manual review, per the register-tag table
discussed. See CLAUDE.md "Two things that are easy to get backwards" and the taxonomy
note in validate_diachronic.load_taxonomy() for how the tag path works.

Usage:
    python tools/dump_register_tags.py
"""

import csv
import sqlite3
from pathlib import Path

LEXEMES_DB = Path('data/processed/lexemes.db')
SHORTLIST_CSV = Path('data/processed/forgotten_words_shortlist.csv')

OUT_FULL = Path('data/processed/register_tags_dex_full.csv')
OUT_SHORTLIST = Path('data/processed/register_tags_shortlist.csv')

# The "tab above" — DEX's usage-style register tags (children of tag 42, "registru
# stilistic"), plus 239 "ieșit din uz" which sits at root level but was included in the
# same word-count table.
TAG_IDS = {
    5: 'familiar',
    7: 'peiorativ',
    9: 'argou; argotic',
    11: 'glumeț',
    13: 'vulgar',
    15: 'popular',
    183: 'depreciativ',
    186: 'ironic',
    239: 'ieșit din uz',
    342: 'jargon',
    426: 'eufemistic',
}


def dump_full():
    conn = sqlite3.connect(str(LEXEMES_DB))
    rows = conn.execute(f"""
        SELECT DISTINCT l.form, l.formNoAccent, t.value
        FROM Lexeme l
        JOIN EntryLexeme el ON el.lexemeId = l.id
        JOIN TreeEntry te ON te.entryId = el.entryId
        JOIN MeaningTree m ON m.tree_id = te.treeId
        JOIN ObjectTag ot ON ot.objectId = m.meaning_id AND ot.objectType = 3
        JOIN Tag t ON t.id = ot.tagId
        WHERE t.id IN ({','.join(str(i) for i in TAG_IDS)})
        ORDER BY t.value, l.formNoAccent
    """).fetchall()
    conn.close()

    OUT_FULL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FULL, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['word', 'word_no_accent', 'register_tag'])
        w.writerows(rows)
    print(f'{OUT_FULL}: {len(rows):,} rows (word, tag) from the full dexonline dump')


def dump_shortlist():
    if not SHORTLIST_CSV.exists():
        print(f'  [skip] {SHORTLIST_CSV} not found — run make_shortlist.py first')
        return

    wanted = set(TAG_IDS.values())
    out_rows = []
    with open(SHORTLIST_CSV, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            tags = {t.strip() for t in (row.get('dex_register') or '').split('|') if t.strip()}
            hit = tags & wanted
            if not hit:
                continue
            for tag in sorted(hit):
                out_rows.append({
                    'word': row['word'],
                    'register_tag': tag,
                    'seam': row.get('seam'),
                    'verdict': row.get('verdict'),
                    'dex_pos': row.get('dex_pos'),
                    'quality_score': row.get('quality_score'),
                    'hist_occ': row.get('hist_occ'),
                    'modern_occ': row.get('modern_occ'),
                    'dex_register': row.get('dex_register'),
                })

    out_rows.sort(key=lambda r: (r['register_tag'], r['word']))

    OUT_SHORTLIST.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_SHORTLIST, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['word', 'register_tag', 'seam', 'verdict', 'dex_pos',
                      'quality_score', 'hist_occ', 'modern_occ', 'dex_register']
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)
    print(f'{OUT_SHORTLIST}: {len(out_rows):,} rows (word, tag) from the shortlist')


if __name__ == '__main__':
    dump_full()
    dump_shortlist()
