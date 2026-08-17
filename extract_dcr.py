#!/usr/bin/env python3
"""
Extract DCR2 definitions from the DEX MySQL dump — no HTTP.

The dump's `Definition.internalRep` is truncated to ~23 chars for every source
except DEX '98/'96, so the raw DCR2 entries are not in it. But DCR2 was
digitized *structured* (`Definition.structured = 1` on all 5,807 rows), and the
structured text — the site's meaning trees — ships in full in the `Meaning`
table: senses, sub-senses and citations with their attestations
(`$I.T.B.-ul va pune în vânzare…$ R.l. 12 X 77 p. 5.`).

Chain: `Definition(sourceId=30).id → EntryDefinition.definitionId → entryId →
TreeEntry.entryId → treeId → Meaning.treeId` rows, rendered in displayOrder with
their breadcrumbs. One definition can attach to several entries (a compound like
`abonament-legitimație` attaches to both `abonament` and `legitimație`); the
union of their trees is rendered and meanings are deduplicated by id, so the
pointer in one tree and the text in the other come out as the text only.

The trees are the *entry* trees — the site's sinteză — which merge every
dictionary that defines a word. For a word only DCR2 defines, the tree IS DCR2's
entry; for shared words the `source_ids` column lists the other sources and the
text may mix them. The faithful per-source copy is `scrape_dcr.py`'s job; this
is the free, local complement.

Output: data/processed/dcr_definitions_dump.csv
  word, edition, definition, n_sources, source_ids, status
  status ∈ {ok, no_entry, no_tree, no_meanings, no_text}

Usage:
  python extract_dcr.py
  python extract_dcr.py --limit 20
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

from extract_definitions import (
    SQL_PATH,
    _DEF_PREFIX,
    _clean_markup,
    _read_quoted_or_null,
)
from dump_parser import normalize

OUT_PATH = Path('data/processed/dcr_definitions_dump.csv')
DCR2_WORDS_FILE = Path('data/processed/dcr2_words.txt')
DCR2_SOURCE_ID = '30'
EDITION = 'dcr2'

_REF_RE = re.compile(r'\[\d+\]')   # [476691] cross-tree pointers — site links, not text
_UNDER_RE = re.compile(r'__')      # __(de stat)__ — render artifact of the structured view


def _clean(text: str) -> str:
    out = _clean_markup(text)
    if not out:
        return ''
    out = _REF_RE.sub('', out)
    out = out.replace('__', '')
    return ' '.join(out.split())


# ---------------------------------------------------------------------------
# Dump passes
# ---------------------------------------------------------------------------

def _row_walker(line: str, prefix: str):
    """Yield field lists from one multi-value INSERT line."""
    s = line[len(prefix):].rstrip('\n')
    if s.endswith(';'):
        s = s[:-1]
    i, n = 0, len(s)
    while i < n:
        while i < n and s[i] != '(':
            i += 1
        if i >= n:
            break
        i += 1
        fields: list[str | None] = []
        while i < n:
            if s[i] == "'":
                v, i = _read_quoted_or_null(s, i, n)
                fields.append(v)
            elif s[i] == ')':
                break
            elif s[i] == ',':
                fields.append(None)
            else:
                j = i
                while j < n and s[j] not in ',)':
                    j += 1
                fields.append(s[i:j].strip() or None)
                i = j - 1
            i += 1
            if i >= n:
                break
        yield [f for f in fields if f is not None]
        i += 1


def pass_dcr2_definitions() -> dict[str, str]:
    """Definition → {id: lexicon} for the DCR2 rows (sourceId 30)."""
    dcr2: dict[str, str] = {}
    with open(SQL_PATH, encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith(_DEF_PREFIX):
                continue
            for row in _row_walker(line, _DEF_PREFIX):
                # cols: id, userId, sourceId, lexicon, internalRep, ...
                if len(row) < 4:
                    continue
                if str(row[2]) == DCR2_SOURCE_ID and row[3]:
                    dcr2[str(row[0])] = row[3]
    return dcr2


def pass_lexicon_sources(lexicons: set[str]) -> dict[str, set[str]]:
    """Definition → {lexicon: set(sourceIds)} for the given lexicons.

    A separate pass from pass_dcr2_definitions: the DCR2 rows sit at the end of
    the table (high ids), so a single scan would miss the earlier rows of every
    shared word and under-report its other sources.
    """
    sources: dict[str, set[str]] = defaultdict(set)
    with open(SQL_PATH, encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith(_DEF_PREFIX):
                continue
            for row in _row_walker(line, _DEF_PREFIX):
                if len(row) < 4:
                    continue
                lexicon = row[3]
                if lexicon in lexicons:
                    sources[lexicon].add(str(row[2]))
    return sources


def pass_entry_definition(def_ids: set[str]) -> dict[str, list[tuple[int, int]]]:
    """EntryDefinition → {definitionId: [(entryRank, entryId)]}."""
    out: dict[str, list[tuple[int, int]]] = defaultdict(list)
    prefix = 'INSERT INTO `EntryDefinition` VALUES '
    with open(SQL_PATH, encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith(prefix):
                continue
            for row in _row_walker(line, prefix):
                # cols: id, entryId, definitionId, entryRank, definitionRank, ...
                if len(row) < 3 or str(row[2]) not in def_ids:
                    continue
                out[str(row[2])].append((int(row[3]), int(row[1])))
    return out


def pass_tree_entry(entry_ids: set[int]) -> dict[int, list[int]]:
    """TreeEntry → {entryId: [treeIds]}."""
    out: dict[int, list[int]] = defaultdict(list)
    prefix = 'INSERT INTO `TreeEntry` VALUES '
    with open(SQL_PATH, encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith(prefix):
                continue
            for row in _row_walker(line, prefix):
                # cols: id, treeId, entryId, treeRank, entryRank, ...
                if len(row) < 3 or int(row[2]) not in entry_ids:
                    continue
                out[int(row[2])].append(int(row[1]))
    return out


def pass_meaning(tree_ids: set[int]) -> dict[int, list[tuple]]:
    """Meaning → {treeId: [(id, parentId, type, displayOrder, breadcrumb, text)]}."""
    out: dict[int, list[tuple]] = defaultdict(list)
    prefix = 'INSERT INTO `Meaning` VALUES '
    with open(SQL_PATH, encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith(prefix):
                continue
            for row in _row_walker(line, prefix):
                # cols: id, parentId, type, displayOrder, breadcrumb, userId, treeId, internalRep, ...
                if len(row) < 8:
                    continue
                tree_id = int(row[6])
                if tree_id not in tree_ids:
                    continue
                out[tree_id].append((
                    int(row[0]),          # id
                    int(row[1]),          # parentId
                    int(row[2]),          # type
                    int(row[3]),          # displayOrder
                    row[4] or '',         # breadcrumb
                    row[7] or '',         # internalRep
                ))
    return out


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_meanings(meanings: list[tuple]) -> str:
    """Render one tree's meanings into a plain-text definition.

    Senses (type 0/4/5) become units joined with ' | '; citations (type 2) and
    etymologies (type 1) attach to their parent sense as ' ◊ ' / ' – '. Units
    whose whole text is a single word are cross-tree pointers
    (`$Abonament[476691]-legitimație[476691]$.`) and are dropped.
    """
    by_id = {m[0]: m for m in meanings}
    units: list[list[tuple]] = []  # each unit: [sense] + attachments in order
    unit_of: dict[int, list] = {}
    # index children by parent
    children: dict[int, list] = defaultdict(list)
    for m in meanings:
        children[m[1]].append(m)
    for lst in children.values():
        lst.sort(key=lambda m: (m[3], m[0]))

    def emit(parent: tuple, seen: set) -> None:
        """Emit the parent sense unit, then its sub-senses recursively."""
        uid = parent[0]
        if uid in seen:
            return
        seen.add(uid)
        unit: list[tuple] = [parent]
        for child in children.get(uid, []):
            ctype = child[2]
            if ctype in (2, 1):        # citation / etymology attach inline
                unit.append(child)
        units.append(unit)
        unit_of[uid] = unit
        for child in children.get(uid, []):
            if child[2] in (0, 4, 5):  # sub-sense — its own unit
                emit(child, seen)

    seen: set[int] = set()
    for m in sorted(meanings, key=lambda m: (m[3], m[0])):
        if m[2] in (0, 4, 5) and m[1] not in by_id:   # top-level sense
            emit(m, seen)
    # any sense never reached (parent outside the tree) — emit as top-level
    for m in sorted(meanings, key=lambda m: (m[3], m[0])):
        if m[2] in (0, 4, 5) and m[0] not in seen:
            emit(m, seen)

    parts: list[str] = []
    for unit in units:
        sense = unit[0]
        breadcrumb = (sense[4] + ' ') if sense[4] else ''
        text = _clean(sense[5]) if sense[5] else ''
        body = (breadcrumb + text).strip()
        # drop bare cross-tree pointers: a sense whose whole text is one word
        if sense[2] == 0 and text and ' ' not in text:
            continue
        for att in unit[1:]:
            atext = _clean(att[5]) if att[5] else ''
            if not atext:
                continue
            sep = ' – ' if att[2] == 1 else ' ◊ '
            body += sep + atext
        if body:
            parts.append(body)
    return ' | '.join(parts)


def extract(limit: int | None = None) -> None:
    print('Pass 1/5 — Definition (DCR2 rows)…')
    dcr2 = pass_dcr2_definitions()
    print(f'  DCR2 definition ids: {len(dcr2):,}')
    # canonical word list — also read by scrape_dcr.py, so the scrape never
    # rescans the dump with a different parser
    word_list = sorted({normalize(w) for w in dcr2.values()})
    DCR2_WORDS_FILE.write_text('\n'.join(word_list) + '\n', encoding='utf-8')
    print(f'  distinct headwords: {len(word_list):,} → {DCR2_WORDS_FILE}')
    if limit:
        dcr2 = dict(list(dcr2.items())[:limit])

    print('Pass 2/5 — Definition (other sources for these words)…')
    sources = pass_lexicon_sources(set(dcr2.values()))
    print(f'  words also defined by other sources: '
          f'{sum(1 for s in sources.values() if len(s) > 1):,}')

    print('Pass 3/5 — EntryDefinition…')
    def_to_entries = pass_entry_definition(set(dcr2))
    linked = {d for d, es in def_to_entries.items() if es}
    print(f'  linked to ≥1 entry: {len(linked):,}')

    print('Pass 4/5 — TreeEntry…')
    entry_ids = {e for es in def_to_entries.values() for _, e in es}
    entry_to_trees = pass_tree_entry(entry_ids)
    trees = {t for e in entry_ids for t in entry_to_trees.get(e, [])}
    print(f'  entries: {len(entry_ids):,} → trees: {len(trees):,}')

    print('Pass 5/5 — Meaning…')
    tree_meanings = pass_meaning(trees)
    print(f'  trees with meanings: {len(tree_meanings):,}')

    # assemble per word
    rows = []
    misses: dict[str, str] = {}
    stats = {'ok': 0, 'no_entry': 0, 'no_tree': 0, 'no_meanings': 0, 'no_text': 0}
    for def_id, lexicon in sorted(dcr2.items(), key=lambda kv: kv[1]):
        entries = def_to_entries.get(def_id, [])
        if not entries:
            stats['no_entry'] += 1
            misses[normalize(lexicon)] = 'no_entry'
            continue
        word_trees = {t for _, e in entries for t in entry_to_trees.get(e, [])}
        if not word_trees:
            stats['no_tree'] += 1
            misses[normalize(lexicon)] = 'no_tree'
            continue
        meanings = []
        seen_ids: set[int] = set()
        for t in word_trees:
            for m in tree_meanings.get(t, []):
                if m[0] not in seen_ids:
                    seen_ids.add(m[0])
                    meanings.append(m)
        if not meanings:
            stats['no_meanings'] += 1
            misses[normalize(lexicon)] = 'no_meanings'
            continue
        text = render_meanings(meanings)
        if not text:
            stats['no_text'] += 1
            misses[normalize(lexicon)] = 'no_text'
            continue
        src_ids = ','.join(sorted(sources.get(lexicon, {DCR2_SOURCE_ID}), key=int))
        rows.append({
            'word': normalize(lexicon),
            'edition': EDITION,
            'definition': text,
            'n_sources': len(sources.get(lexicon, {DCR2_SOURCE_ID})),
            'source_ids': src_ids,
            'status': 'ok',
        })
        stats['ok'] += 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['word', 'edition', 'definition',
                                               'n_sources', 'source_ids', 'status'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f'\nDone: {stats}')
    for word, why in sorted(misses.items()):
        print(f'  missed: {word:30} ({why})')
    print(f'Output: {OUT_PATH} ({len(rows):,} rows)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract DCR2 definitions from the DEX dump.')
    parser.add_argument('--limit', type=int, default=None, metavar='N',
                        help='Stop after N DCR2 words (for smoke runs)')
    args = parser.parse_args()
    extract(args.limit)
