#!/usr/bin/env python3
"""
Extract the full sense tree — senses, sub-senses, citations, etymology,
comments, compounds and expressions — for shortlist words from the DEX MySQL
dump. No HTTP.

The chain is `Tree.description --normalize()--> the headword`, `Tree.id ->
Meaning.treeId`. No `Entry`/`EntryDefinition` hop is needed — unlike
extract_dcr.py, which starts from a `Definition.sourceId` and has to walk
`Definition -> EntryDefinition -> TreeEntry -> Meaning`, this starts from the
word and `Tree.description` *is* the word.

Four passes over the 1.65 GB dump, in this order:

  Pass 1  `Tree`      ->  {tree_id: word}, restricted to shortlist words
  Pass 2  `Meaning`   ->  rows whose treeId is one of those tree ids
  Pass 3  `Relation`  ->  type=1 rows whose meaningId is a sense (type=0) this
                          run kept — the synonym set dexonline shows under a
                          sense, and the ONLY content a sense has when its own
                          `internalRep` is empty (see below)
  Pass 4  `Tree`      ->  {tree_id: word} again, this time for the synonym
                          targets found in pass 3 — almost never shortlist
                          words themselves, so pass 1's restricted map can't
                          resolve them

`Meaning` is 454,993 rows; restricting to the ~13,700 trees shortlist words
own before reading it is why passes 1/2 run in that order rather than one
combined pass. Passes 3/4 are the same trick one level out: `Relation` is
162,237 rows and only worth scanning after pass 2 has named which meaningIds
are in scope.

**`Relation.type = 1` is "synonym"**, verified rather than assumed: `zăticni`
sense 1 has empty `internalRep` in the dump, and its 9 `type=1` Relation rows
resolve (via this pass 4) to exactly the 9 words dexonline lists under that
sense's "sinonime:" line — `deranja, incomoda, jena, stânjeni, stingheri,
supăra, tulbura, împiedica, încurca`. dexonline composes that sense's visible
"definition" text from the same list when `internalRep` is empty; this
extractor keeps the list as data (`meaning_synonyms`) rather than fabricating
a prose sentence from it, and leaves rendering the fallback to `merge_senses()`.
Other `Relation.type` values are unverified and out of scope here — see
`docs/BACKLOG.md`'s "per-sense synonyms" entry for what a fuller pass (values
beyond 1, `senses.tags` vs. a `sense_relations` table) would need to settle
first.

Ordering, empty-sense dropping, and homonym merging are not done here — they
are `merge_senses()`'s job in tools/build_ui_db.py, which reads this file's
raw output. This script writes a faithful copy of every Meaning row attached
to a shortlist word's tree(s), text included even when empty (a numbered node
whose content lives entirely in its children, or — since pass 3/4 landed — in
its synonym relations; the consumer needs to see it to decide, and throwing
it away here would make the decision un-revisitable without another scan).

Output: data/processed/meanings.db
  meanings(meaning_id PK, word, tree_id, parent_id, type, breadcrumb,
           display_order, text)
  meaning_tags(meaning_id, tag) — from lexemes.db's ObjectTag(objectType=3),
           already loaded by extract_taxonomy.py; left empty if lexemes.db
           is missing rather than failing the build.
  meaning_synonyms(meaning_id, ord, word) — `Relation.type=1` targets, in
           relation-id order (the dump's own insertion order; not claimed to
           match dexonline's own display order, which isn't stored anywhere
           we can read). Restricted to `type=0` (sense) meanings — compounds
           and expressions can carry Relations too, but that's unread here.

Usage:
  python extract_meanings.py                 # full run, ~3 min, no HTTP
  python extract_meanings.py --limit 200     # first N shortlist words, smoke test
  python extract_meanings.py --stats         # counts only, write nothing
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

from extract_dcr import _row_walker, _clean
from extract_definitions import SQL_PATH
from dump_parser import normalize

OUT_PATH = Path('data/processed/meanings.db')
SHORTLIST_PATH = Path('data/processed/forgotten_words_shortlist.csv')
LEXEMES_PATH = Path('data/processed/lexemes.db')

_TREE_PREFIX = 'INSERT INTO `Tree` VALUES '
_MEANING_PREFIX = 'INSERT INTO `Meaning` VALUES '
_RELATION_PREFIX = 'INSERT INTO `Relation` VALUES '
_SYNONYM_RELATION_TYPE = 1


def load_shortlist(path: Path) -> set[str]:
    words: set[str] = set()
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            w = row.get('word')
            if w:
                words.add(normalize(w))
    return words


def pass_tree(shortlist: set[str]) -> dict[int, str]:
    """Tree.id -> normalized word, restricted to `shortlist`.

    Guard on `len(row) >= 2`: Tree rows are (id, description, descriptionSort,
    status, createDate, modDate) and only id(0)/description(1) are read.
    """
    tree_word: dict[int, str] = {}
    line_count = 0
    with open(SQL_PATH, encoding='utf-8', errors='replace') as f:
        for line in f:
            line_count += 1
            if line_count % 200_000 == 0:
                print(f'  {line_count:,} lines — trees matched: {len(tree_word):,}')
            if not line.startswith(_TREE_PREFIX):
                continue
            for row in _row_walker(line, _TREE_PREFIX):
                if len(row) < 2:
                    continue
                word = normalize(row[1])
                if word in shortlist:
                    tree_word[int(row[0])] = word
    return tree_word


def pass_meaning(tree_word: dict[int, str]):
    """Yield (meaning_id, word, tree_id, parent_id, type, breadcrumb,
    display_order, text) for every Meaning row whose treeId is in tree_word.

    Guard on `len(row) >= 8`: Meaning rows are (id, parentId, type,
    displayOrder, breadcrumb, userId, treeId, internalRep, createDate,
    modDate) and index 7 (internalRep) is the deepest one read.
    """
    line_count = 0
    kept = 0
    with open(SQL_PATH, encoding='utf-8', errors='replace') as f:
        for line in f:
            line_count += 1
            if line_count % 200_000 == 0:
                print(f'  {line_count:,} lines — meanings kept: {kept:,}')
            if not line.startswith(_MEANING_PREFIX):
                continue
            for row in _row_walker(line, _MEANING_PREFIX):
                if len(row) < 8:
                    continue
                tree_id = int(row[6])
                word = tree_word.get(tree_id)
                if word is None:
                    continue
                rep = row[7]
                text = _clean(rep) if rep and rep != 'NULL' else ''
                kept += 1
                yield (
                    int(row[0]),        # meaning_id
                    word,
                    tree_id,
                    int(row[1]),        # parent_id
                    int(row[2]),        # type
                    row[4] or '',       # breadcrumb
                    int(row[3]),        # display_order
                    text,
                )


def pass_relation(sense_ids: set[int]):
    """Yield (relation_id, meaning_id, target_tree_id) for every `type=1`
    (synonym) Relation row whose meaningId is one of `sense_ids`.

    Guard on `len(row) >= 4`: Relation rows are (id, meaningId, treeId, type,
    createDate, modDate) and index 3 (type) is the deepest one read.
    """
    line_count = 0
    kept = 0
    with open(SQL_PATH, encoding='utf-8', errors='replace') as f:
        for line in f:
            line_count += 1
            if line_count % 200_000 == 0:
                print(f'  {line_count:,} lines — synonym relations kept: {kept:,}')
            if not line.startswith(_RELATION_PREFIX):
                continue
            for row in _row_walker(line, _RELATION_PREFIX):
                if len(row) < 4:
                    continue
                if int(row[3]) != _SYNONYM_RELATION_TYPE:
                    continue
                meaning_id = int(row[1])
                if meaning_id not in sense_ids:
                    continue
                kept += 1
                yield (int(row[0]), meaning_id, int(row[2]))


def pass_relation_targets(tree_ids: set[int]) -> dict[int, str]:
    """Tree.id -> normalized word, restricted to `tree_ids` — the synonym
    targets found by pass_relation(). Unlike pass_tree(), not restricted to
    the shortlist: a sense's synonym is almost never a shortlist word itself.
    """
    tree_word: dict[int, str] = {}
    with open(SQL_PATH, encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith(_TREE_PREFIX):
                continue
            for row in _row_walker(line, _TREE_PREFIX):
                if len(row) < 2:
                    continue
                tid = int(row[0])
                if tid in tree_ids:
                    tree_word[tid] = normalize(row[1])
    return tree_word


def load_meaning_tags(lexemes_db: Path, meaning_ids: set[int]) -> dict[int, list[str]]:
    """{meaning_id: [tag, ...]} from ObjectTag(objectType=3), restricted to
    the meanings this run kept. Empty (not an error) if lexemes.db is missing
    or predates extract_taxonomy.py loading these tables.
    """
    if not lexemes_db.exists():
        print(f'  (lexemes DB not found, meaning_tags left empty: {lexemes_db})')
        return {}
    conn = sqlite3.connect(f'file:{lexemes_db}?mode=ro', uri=True)
    try:
        rows = conn.execute(
            'SELECT ot.objectId, t.value FROM ObjectTag ot '
            'JOIN Tag t ON t.id = ot.tagId WHERE ot.objectType = 3'
        ).fetchall()
    except sqlite3.OperationalError:
        print('  (no ObjectTag/Tag tables in lexemes DB, meaning_tags left empty)')
        return {}
    finally:
        conn.close()
    out: dict[int, list[str]] = {}
    for meaning_id, tag in rows:
        if meaning_id in meaning_ids:
            out.setdefault(meaning_id, []).append(tag)
    return out


def extract(shortlist_path: Path, limit: int | None, stats_only: bool) -> None:
    print(f'Loading shortlist from {shortlist_path}…')
    shortlist = load_shortlist(shortlist_path)
    if limit:
        shortlist = set(sorted(shortlist)[:limit])
    print(f'  {len(shortlist):,} words')

    print('Pass 1/4 — Tree…')
    tree_word = pass_tree(shortlist)
    words_with_tree = set(tree_word.values())
    print(f'  trees found: {len(tree_word):,} for {len(words_with_tree):,} words')

    print('Pass 2/4 — Meaning…')
    rows = list(pass_meaning(tree_word))
    print(f'  meanings kept: {len(rows):,}')

    print('Pass 3/4 — Relation (synonyms)…')
    sense_ids = {r[0] for r in rows if r[4] == 0}
    relations = list(pass_relation(sense_ids))
    target_tree_ids = {tid for _, _, tid in relations}
    print(f'  {len(relations):,} synonym relations, {len(target_tree_ids):,} target trees')

    print('Pass 4/4 — Tree (synonym targets)…')
    target_word = pass_relation_targets(target_tree_ids)
    print(f'  {len(target_word):,} / {len(target_tree_ids):,} targets resolved')

    # Group by meaning, order by relation id (the dump's own insertion order —
    # see the module docstring for why this isn't claimed to match dexonline's
    # own display order). A target tree id that failed to resolve (dangling
    # reference) is dropped rather than left as a blank entry.
    synonyms_by_meaning: dict[int, list[str]] = {}
    for rel_id, meaning_id, tid in sorted(relations):
        word = target_word.get(tid)
        if word:
            synonyms_by_meaning.setdefault(meaning_id, []).append(word)

    words_with_meaning = {r[1] for r in rows}
    sense_counts: dict[str, int] = {}
    for r in rows:
        if r[4] == 0 and r[7]:   # type=0 sense, non-empty text
            sense_counts[r[1]] = sense_counts.get(r[1], 0) + 1
    words_with_2plus = {w for w, c in sense_counts.items() if c >= 2}
    citation_rows = [r for r in rows if r[4] == 2]
    words_with_citations = {r[1] for r in citation_rows}
    empty_text_senses = sum(1 for r in rows if r[4] == 0 and not r[7])
    empty_rescued = sum(1 for r in rows if r[4] == 0 and not r[7] and r[0] in synonyms_by_meaning)

    print()
    print(f'Trees found:            {len(tree_word):,}')
    print(f'Meanings kept:          {len(rows):,}')
    print(f'Words with ≥1 Meaning row: {len(words_with_meaning):,}')
    print(f'Words with ≥2 senses:   {len(words_with_2plus):,}')
    print(f'Words with citations:   {len(words_with_citations):,} / {len(citation_rows):,} quotes')
    print(f'Empty-text senses:      {empty_text_senses:,}')
    print(f'  …with a synonym relation (kept via fallback): {empty_rescued:,}')
    print(f'  …with neither (still dropped by merge_senses): {empty_text_senses - empty_rescued:,}')

    if stats_only:
        print('\n--stats: nothing written.')
        return

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if OUT_PATH.exists():
        OUT_PATH.unlink()
    conn = sqlite3.connect(str(OUT_PATH))
    conn.execute("""
        CREATE TABLE meanings (
            meaning_id     INTEGER PRIMARY KEY,
            word           TEXT    NOT NULL,
            tree_id        INTEGER NOT NULL,
            parent_id      INTEGER NOT NULL,
            type           INTEGER NOT NULL,
            breadcrumb     TEXT    NOT NULL DEFAULT '',
            display_order  INTEGER NOT NULL,
            text           TEXT    NOT NULL
        )
    """)
    conn.execute('CREATE INDEX idx_meanings_word ON meanings(word)')
    conn.execute('CREATE INDEX idx_meanings_tree ON meanings(tree_id)')
    conn.execute("""
        CREATE TABLE meaning_tags (
            meaning_id  INTEGER NOT NULL,
            tag         TEXT    NOT NULL,
            PRIMARY KEY (meaning_id, tag)
        )
    """)
    conn.execute("""
        CREATE TABLE meaning_synonyms (
            meaning_id  INTEGER NOT NULL,
            ord         INTEGER NOT NULL,
            word        TEXT    NOT NULL,
            PRIMARY KEY (meaning_id, ord)
        )
    """)
    conn.executemany(
        'INSERT INTO meanings VALUES (?,?,?,?,?,?,?,?)',
        ((r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]) for r in rows),
    )
    conn.executemany(
        'INSERT INTO meaning_synonyms VALUES (?,?,?)',
        ((mid, i, w) for mid, words in synonyms_by_meaning.items() for i, w in enumerate(words)),
    )

    print('\nLoading meaning tags from lexemes.db…')
    tags = load_meaning_tags(LEXEMES_PATH, {r[0] for r in rows})
    tag_rows = [(mid, tag) for mid, tlist in tags.items() for tag in tlist]
    conn.executemany('INSERT OR IGNORE INTO meaning_tags VALUES (?,?)', tag_rows)
    print(f'  {len(tag_rows):,} meaning tags for {len(tags):,} meanings')

    conn.commit()
    conn.close()
    size_mb = OUT_PATH.stat().st_size / 1024 / 1024
    print(f'\nDone → {OUT_PATH} ({len(rows):,} meanings, {size_mb:.1f} MB)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Extract DEX sense trees for shortlist words from the dump.')
    parser.add_argument('--shortlist', type=Path, default=SHORTLIST_PATH,
                        help='CSV with a `word` column (default: the shortlist)')
    parser.add_argument('--limit', type=int, default=None, metavar='N',
                        help='First N shortlist words only, for a smoke test')
    parser.add_argument('--stats', action='store_true',
                        help='Print counts only; write nothing')
    args = parser.parse_args()
    extract(args.shortlist, args.limit, args.stats)
