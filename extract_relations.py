#!/usr/bin/env python3
"""
Build the synonym/antonym/diminutive/augmentative relation graph from the DEX dump.

Why this exists: CLAUDE.md and scrape_synonyms.py both say synonyms "can't come from the
dump" — true only of `Definition.internalRep` for the three in-copyright Litera titles
(Sinonime, Sinonime82, Antonime), which the dump redacts to 23 characters. The dump's own
`Relation` table is a different artefact: dexonline's community-curated relation graph,
unredacted, 158,860 rows. See docs/sinonime/findings.md §1-2 for the full argument.

A row in `Relation` says: meaning M is related, by type t, to tree T. The source is a
*sense* (`Meaning`), the target is a *concept* (`Tree`). Resolving both ends to words:

    Relation.meaningId -> Meaning.treeId -> source Tree  ---\\
    Relation.treeId    -> target Tree ----------------------+-> TreeEntry -> EntryLexeme -> Lexeme

Six tables plus a register-tag join table are written here, self-contained, rather than
reusing `lexemes.db` (built by extract_lexemes.py's lossy regex splitter, which drops ~48k
of 365,869 Lexeme rows) or lexemes.db's copy of MeaningTree/TreeEntry/EntryLexeme/Tag (would
need re-joining anyway). One extra 15s pass over the dump removes the dependency entirely.

`meaning_tag` captures ObjectTag rows with objectType=3, which docs/sinonime/escalate.md §3
flagged as an unverified inference ("objectType=3 means Meaning"). Verified directly against
this dump before writing this script: of 193,466 objectType=3 rows, **100.0%** of their
objectId values are valid Meaning ids (0% would be expected of a false hypothesis at this
sample size); objectType=2 is the Lexeme-level tag type at the same 100.0% exactness. The
seemingly high cross-hit rates (87.5% / 59.4%) are id-range coincidence — Meaning and Lexeme
ids are both dense integer ranges that overlap heavily, so an unrelated id often lands inside
the other table's range by chance. The exact-match rate is what discriminates; it settles the
inference.

Lexeme's `description` column is at field index 6, not 5 as an earlier draft of
docs/sinonime/spec.md stated (Lexeme columns: id, form, formNoAccent, formUtf8General,
reverse, number, description, ...) -- `number` occupies index 5. Verified against
data/dictionaries/dex-schema.sql. modelType (14) was already correct. This only affects the
unused `lexeme.description` column carried for future debugging; nothing downstream reads it.

Output: data/processed/relations.db

    relation    (id, meaning_id, tree_id, type)
    tree        (id, description)
    meaning_tree(meaning_id PK, tree_id)
    tree_entry  (tree_id, entry_id, entry_rank)
    entry_lexeme(entry_id, lexeme_id, lexeme_rank, main)
    lexeme      (id PK, form_norm, model_type, description)
    meaning_tag (meaning_id, tag)         -- ObjectTag objectType=3 join Tag.value

Usage:
    python extract_relations.py                                       # full dump
    python extract_relations.py --dump data/dictionaries/dex-database-sample.sql
    python extract_relations.py --limit 100000                        # smoke test
"""

import argparse
import sqlite3
import sys
from pathlib import Path

from dump_parser import normalize, parse_tuples, strip_line_prefix

DEX_SQL_PATH = Path('data/dictionaries/dex-database.sql')
OUTPUT_DB = Path('data/processed/relations.db')
REFUSED_DUMP = Path('data/dictionaries/dex-sample-cleaned.sql')

BATCH = 50_000

_REL_PREFIX  = "INSERT INTO `Relation` VALUES "
_TREE_PREFIX = "INSERT INTO `Tree` VALUES "
_MEAN_PREFIX = "INSERT INTO `Meaning` VALUES "
_TE_PREFIX   = "INSERT INTO `TreeEntry` VALUES "
_EL_PREFIX   = "INSERT INTO `EntryLexeme` VALUES "
_LEX_PREFIX  = "INSERT INTO `Lexeme` VALUES "
_OT_PREFIX   = "INSERT INTO `ObjectTag` VALUES "
_TAG_PREFIX  = "INSERT INTO `Tag` VALUES "

# Relation: (id, meaningId, treeId, type, createDate, modDate) -- purely integer tuples,
# so a plain regex is safe (dump_parser's quote-aware scanner is for tables with strings).
import re
_REL_RE = re.compile(r'\((\d+),(\d+),(\d+),(\d+),\d+,\d+\)')
# TreeEntry: (id, treeId, entryId, treeRank, entryRank, createDate, modDate)
_TE_RE = re.compile(r'\((\d+),(\d+),(\d+),(\d+),(\d+),\d+,\d+\)')
# EntryLexeme: (id, entryId, lexemeId, entryRank, lexemeRank, main, createDate, modDate)
_EL_RE = re.compile(r'\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+),\d+,\d+\)')
# ObjectTag: (id, objectId, objectType, tagId, createDate, modDate)
_OT_RE = re.compile(r'\((\d+),(\d+),(\d+),(\d+),\d+,\d+\)')

# Lexeme field indices (dex-schema.sql): id, form, formNoAccent, formUtf8General, reverse,
# number, description, noAccent, consistentAccent, frequency, ..., modelType(14)
_LX_ID, _LX_FORM_NO_ACCENT, _LX_DESCRIPTION, _LX_MODEL_TYPE = 0, 2, 6, 14
# Meaning: id, parentId, type, displayOrder, breadcrumb, userId, treeId(6), internalRep, ...
_MEAN_ID, _MEAN_TREE_ID = 0, 6
# Tree: id, description(1), descriptionSort, status, createDate, modDate
_TREE_ID, _TREE_DESC = 0, 1
# Tag: id, parentId, value(2), color, ...
_TAG_ID, _TAG_VALUE = 0, 2


def build(dump_path: Path, out_path: Path, limit: int | None) -> dict[str, int]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    conn = sqlite3.connect(str(out_path))
    conn.execute('PRAGMA journal_mode = OFF')
    conn.execute('PRAGMA synchronous = OFF')
    conn.executescript("""
        CREATE TABLE relation    (id INTEGER PRIMARY KEY, meaning_id INTEGER, tree_id INTEGER, type INTEGER);
        CREATE TABLE tree        (id INTEGER PRIMARY KEY, description TEXT);
        CREATE TABLE meaning_tree(meaning_id INTEGER PRIMARY KEY, tree_id INTEGER);
        CREATE TABLE tree_entry  (tree_id INTEGER, entry_id INTEGER, entry_rank INTEGER);
        CREATE TABLE entry_lexeme(entry_id INTEGER, lexeme_id INTEGER, lexeme_rank INTEGER, main INTEGER);
        CREATE TABLE lexeme      (id INTEGER PRIMARY KEY, form_norm TEXT, model_type TEXT, description TEXT);
        CREATE TABLE meaning_tag (meaning_id INTEGER, tag TEXT);
    """)

    stats = {
        'relation': 0, 'tree': 0, 'meaning_tree': 0, 'tree_entry': 0,
        'entry_lexeme': 0, 'lexeme': 0, 'meaning_tag': 0,
        'rel_type_1': 0, 'rel_type_2': 0, 'rel_type_3': 0, 'rel_type_4': 0,
    }
    batches: dict[str, list] = {k: [] for k in
        ('relation', 'tree', 'meaning_tree', 'tree_entry', 'entry_lexeme', 'lexeme')}
    tag_values: dict[int, str] = {}
    # meaning_tag rows need Tag.value, but Tag and ObjectTag both stream past once —
    # ObjectTag rows are buffered by (meaning_id, tag_id) and resolved to values at the end,
    # the same deferred-join shape build() already uses for meaning_tree via meaning_ids.
    objtag3_pending: list[tuple[int, int]] = []

    def flush() -> None:
        if batches['relation']:
            conn.executemany('INSERT INTO relation VALUES (?,?,?,?)', batches['relation'])
            batches['relation'].clear()
        if batches['tree']:
            conn.executemany('INSERT OR IGNORE INTO tree VALUES (?,?)', batches['tree'])
            batches['tree'].clear()
        if batches['meaning_tree']:
            conn.executemany('INSERT OR IGNORE INTO meaning_tree VALUES (?,?)', batches['meaning_tree'])
            batches['meaning_tree'].clear()
        if batches['tree_entry']:
            conn.executemany('INSERT INTO tree_entry VALUES (?,?,?)', batches['tree_entry'])
            batches['tree_entry'].clear()
        if batches['entry_lexeme']:
            conn.executemany('INSERT INTO entry_lexeme VALUES (?,?,?,?)', batches['entry_lexeme'])
            batches['entry_lexeme'].clear()
        if batches['lexeme']:
            conn.executemany('INSERT OR IGNORE INTO lexeme VALUES (?,?,?,?)', batches['lexeme'])
            batches['lexeme'].clear()

    with open(dump_path, encoding='utf-8', errors='replace') as f:
        for lineno, line in enumerate(f, 1):
            if line.startswith(_REL_PREFIX):
                for m in _REL_RE.finditer(line):
                    rid, mid, tid, typ = (int(m.group(i)) for i in (1, 2, 3, 4))
                    batches['relation'].append((rid, mid, tid, typ))
                    stats['relation'] += 1
                    if typ in (1, 2, 3, 4):
                        stats[f'rel_type_{typ}'] += 1

            elif line.startswith(_TREE_PREFIX):
                body = strip_line_prefix(line, _TREE_PREFIX)
                for t in parse_tuples(body, _TREE_DESC):
                    if len(t) <= _TREE_DESC or not t[_TREE_ID]:
                        continue
                    batches['tree'].append((int(t[_TREE_ID]), t[_TREE_DESC]))
                    stats['tree'] += 1

            elif line.startswith(_MEAN_PREFIX):
                body = strip_line_prefix(line, _MEAN_PREFIX)
                for t in parse_tuples(body, _MEAN_TREE_ID):
                    if len(t) <= _MEAN_TREE_ID or not t[_MEAN_ID] or not t[_MEAN_TREE_ID]:
                        continue
                    batches['meaning_tree'].append((int(t[_MEAN_ID]), int(t[_MEAN_TREE_ID])))
                    stats['meaning_tree'] += 1

            elif line.startswith(_TE_PREFIX):
                for m in _TE_RE.finditer(line):
                    _id, tree_id, entry_id, _tree_rank, entry_rank = (int(m.group(i)) for i in (1, 2, 3, 4, 5))
                    batches['tree_entry'].append((tree_id, entry_id, entry_rank))
                    stats['tree_entry'] += 1

            elif line.startswith(_EL_PREFIX):
                for m in _EL_RE.finditer(line):
                    _id, entry_id, lexeme_id, _entry_rank, lexeme_rank, main = (
                        int(m.group(i)) for i in (1, 2, 3, 4, 5, 6))
                    batches['entry_lexeme'].append((entry_id, lexeme_id, lexeme_rank, main))
                    stats['entry_lexeme'] += 1

            elif line.startswith(_LEX_PREFIX):
                body = strip_line_prefix(line, _LEX_PREFIX)
                for t in parse_tuples(body, _LX_MODEL_TYPE):
                    if len(t) <= _LX_MODEL_TYPE or not t[_LX_ID]:
                        continue
                    form = t[_LX_FORM_NO_ACCENT]
                    batches['lexeme'].append((
                        int(t[_LX_ID]),
                        normalize(form) if form else None,
                        t[_LX_MODEL_TYPE],
                        t[_LX_DESCRIPTION],
                    ))
                    stats['lexeme'] += 1

            elif line.startswith(_OT_PREFIX):
                for m in _OT_RE.finditer(line):
                    obj_id, obj_type, tag_id = (int(m.group(i)) for i in (2, 3, 4))
                    if obj_type == 3:
                        objtag3_pending.append((obj_id, tag_id))

            elif line.startswith(_TAG_PREFIX):
                body = strip_line_prefix(line, _TAG_PREFIX)
                for t in parse_tuples(body, _TAG_VALUE):
                    if len(t) <= _TAG_VALUE or not t[_TAG_ID]:
                        continue
                    tag_values[int(t[_TAG_ID])] = t[_TAG_VALUE] or ''

            if len(batches['relation']) >= BATCH or len(batches['lexeme']) >= BATCH \
                    or len(batches['tree_entry']) >= BATCH or len(batches['entry_lexeme']) >= BATCH \
                    or len(batches['tree']) >= BATCH or len(batches['meaning_tree']) >= BATCH:
                flush()
            if limit is not None and stats['relation'] >= limit:
                break

            if lineno % 500_000 == 0:
                print(f'  ...{lineno:,} lines · {stats["relation"]:,} relations · '
                      f'{stats["tree"]:,} trees · {stats["lexeme"]:,} lexemes', file=sys.stderr)

    flush()

    print('  resolving meaning_tag from ObjectTag(objectType=3) x Tag ...', file=sys.stderr)
    mt_batch = []
    for meaning_id, tag_id in objtag3_pending:
        val = tag_values.get(tag_id)
        if val:
            mt_batch.append((meaning_id, val))
            if len(mt_batch) >= BATCH:
                conn.executemany('INSERT INTO meaning_tag VALUES (?,?)', mt_batch)
                mt_batch.clear()
    if mt_batch:
        conn.executemany('INSERT INTO meaning_tag VALUES (?,?)', mt_batch)
    stats['meaning_tag'] = len(objtag3_pending)

    conn.commit()

    print('  indexing ...', file=sys.stderr)
    conn.executescript("""
        CREATE INDEX ix_rel_meaning  ON relation(meaning_id);
        CREATE INDEX ix_te_tree      ON tree_entry(tree_id);
        CREATE INDEX ix_el_entry     ON entry_lexeme(entry_id);
        CREATE INDEX ix_mtag_meaning ON meaning_tag(meaning_id);
    """)
    conn.commit()
    conn.close()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dump', type=Path, default=DEX_SQL_PATH,
                        help='DEX MySQL dump path (default: %(default)s)')
    parser.add_argument('--out', type=Path, default=OUTPUT_DB,
                        help='output SQLite DB (default: %(default)s)')
    parser.add_argument('--limit', type=int, default=None,
                        help='cap Relation rows processed (smoke test)')
    args = parser.parse_args()

    if not args.dump.exists():
        print(f'Dump not found: {args.dump}', file=sys.stderr)
        return 1

    # dex-sample-cleaned.sql comments out whole tables including `Relation` (CLAUDE.md's
    # "sampled dump" gotcha) -- building against it would silently produce an empty
    # thesaurus rather than failing loudly.
    if args.dump.resolve() == REFUSED_DUMP.resolve():
        print(f'{REFUSED_DUMP} has no INSERT INTO `Relation` lines (sampled/commented out). '
              f'Use dex-database-sample.sql for a smoke test, or the full dex-database.sql.',
              file=sys.stderr)
        return 1

    print(f'Streaming {args.dump} ...', file=sys.stderr)
    stats = build(args.dump, args.out, args.limit)

    print(f'  relation      : {stats["relation"]:,} '
          f'(type 1={stats["rel_type_1"]:,} 2={stats["rel_type_2"]:,} '
          f'3={stats["rel_type_3"]:,} 4={stats["rel_type_4"]:,})', file=sys.stderr)
    print(f'  tree          : {stats["tree"]:,}', file=sys.stderr)
    print(f'  meaning_tree  : {stats["meaning_tree"]:,}', file=sys.stderr)
    print(f'  tree_entry    : {stats["tree_entry"]:,}', file=sys.stderr)
    print(f'  entry_lexeme  : {stats["entry_lexeme"]:,}', file=sys.stderr)
    print(f'  lexeme        : {stats["lexeme"]:,}', file=sys.stderr)
    print(f'  meaning_tag   : {stats["meaning_tag"]:,}', file=sys.stderr)

    if args.limit is None and args.dump.resolve() == DEX_SQL_PATH.resolve():
        expect = {'rel_type_1': 152_023, 'rel_type_2': 5_216, 'rel_type_3': 1_547, 'rel_type_4': 74}
        for k, v in expect.items():
            if stats[k] != v:
                print(f'WARNING: {k} = {stats[k]:,}, expected {v:,} — parse may be wrong. '
                      f'Do not proceed to Phase 2 without investigating.', file=sys.stderr)
        if stats['tree'] != 226_424:
            print(f'WARNING: tree = {stats["tree"]:,}, expected 226,424.', file=sys.stderr)

    print(f'Wrote {args.out}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
