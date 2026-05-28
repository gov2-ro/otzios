#!/usr/bin/env python3
"""
Extract the set of source dictionaries each headword appears in, from the DEX dump.

The DEX MySQL dump's `Definition` table has (id, userId, sourceId, lexicon, ...),
where `lexicon` is the headword and `sourceId` points at the `Source` table. The
`Source` table maps that id to a human-readable `shortName` (e.g. "DEX '98", "DLR").

`validate_diachronic.py::_load_dict_counts` already streams the same dump to count
*how many* distinct dictionaries a word appears in; this script keeps the dictionary
*names* as well, so the UI can show "appears in: DEX, DLR, MDA" rather than just "3".

Single streaming pass (Definition is dumped before Source, so sourceIds are collected
first and resolved to names at the end). Never loads the 1.5 GB dump into memory.

Output: data/processed/dict_sources.db
Schema: dict_sources(word TEXT PRIMARY KEY, sources TEXT, dict_count INTEGER)
        `word`        — normalized headword (lower, ș/ț, NFC), matches the pipeline
        `sources`     — sorted shortNames, '|'-joined (e.g. "DEX '98|DLR|MDA")
        `dict_count`  — number of distinct dictionaries

Usage:
    python extract_dict_sources.py                                   # full dump
    python extract_dict_sources.py --dump data/dictionaries/dex-database-sample.sql --limit 5000
"""

import argparse
import sqlite3
import sys
import unicodedata
from pathlib import Path

DEX_SQL_PATH = Path('data/dictionaries/dex-database.sql')
OUTPUT_DB = Path('data/processed/dict_sources.db')

_DEF_PREFIX = "INSERT INTO `Definition` VALUES "
_SRC_PREFIX = "INSERT INTO `Source` VALUES "


def normalize(text: str) -> str:
    """Same normalization the rest of the pipeline uses (validate_diachronic.normalize)."""
    return unicodedata.normalize('NFC',
        text.lower().replace('ş', 'ș').replace('ţ', 'ț'))


def _read_quoted(s: str, i: int) -> tuple[str | None, int]:
    """Read a MySQL-escaped quoted string or NULL starting at s[i]. Returns (value, new_i)."""
    n = len(s)
    if i < n and s[i] == "'":
        i += 1
        buf: list[str] = []
        while i < n:
            c = s[i]
            if c == '\\' and i + 1 < n:
                nxt = s[i + 1]
                buf.append("'" if nxt == "'" else ('\\' if nxt == '\\' else nxt))
                i += 2
            elif c == "'":
                i += 1
                break
            else:
                buf.append(c)
                i += 1
        return ''.join(buf), i
    if s[i:i + 4] == 'NULL':
        return None, i + 4
    return None, i


def _read_unquoted(s: str, i: int) -> tuple[str, int]:
    """Read an unquoted field (integer/decimal) until ',' or ')'. Returns (value, new_i)."""
    n = len(s)
    start = i
    while i < n and s[i] not in (',', ')'):
        i += 1
    return s[start:i].strip(), i


def _skip_to_tuple_end(s: str, i: int) -> int:
    """From inside a tuple, advance past its matching ')'. Honors string escaping."""
    n = len(s)
    depth = 1
    in_str = False
    while i < n and depth > 0:
        c = s[i]
        if in_str:
            if c == '\\' and i + 1 < n:
                i += 2
            elif c == "'":
                in_str = False
                i += 1
            else:
                i += 1
        else:
            if c == "'":
                in_str = True
                i += 1
            elif c == '(':
                depth += 1
                i += 1
            elif c == ')':
                depth -= 1
                i += 1
            else:
                i += 1
    return i


def _strip_line_prefix(line: str, prefix: str) -> str:
    s = line[len(prefix):].rstrip('\n')
    if s.endswith(';'):
        s = s[:-1]
    return s


def _parse_source_line(s: str, id_to_name: dict[str, str]) -> None:
    """Parse `Source` tuples: col0 = id, col1 = shortName."""
    i, n = 0, len(s)
    while i < n:
        while i < n and s[i] != '(':
            i += 1
        if i >= n:
            break
        i += 1  # skip '('
        sid, i = _read_unquoted(s, i)
        if i < n and s[i] == ',':
            i += 1
        short_name, i = _read_quoted(s, i)
        if sid and short_name:
            id_to_name[sid] = short_name
        i = _skip_to_tuple_end(s, i)


def _parse_definition_line(s: str, word_sources: dict[str, set], state: dict) -> None:
    """Parse `Definition` tuples: cols 0,1 = id,userId; col2 = sourceId; col3 = lexicon."""
    i, n = 0, len(s)
    while i < n:
        while i < n and s[i] != '(':
            i += 1
        if i >= n:
            break
        i += 1  # skip '('
        # skip col0 (id) and col1 (userId)
        for _ in range(2):
            _, i = _read_unquoted(s, i)
            if i < n and s[i] == ',':
                i += 1
        source_id, i = _read_unquoted(s, i)  # col2
        if i < n and s[i] == ',':
            i += 1
        lexicon, i = _read_quoted(s, i)       # col3
        if lexicon and source_id:
            norm = normalize(lexicon)
            srcs = word_sources.get(norm)
            if srcs is None:
                srcs = set()
                word_sources[norm] = srcs
            srcs.add(source_id)
            state['tuples'] += 1
        i = _skip_to_tuple_end(s, i)


def extract(dump_path: Path, limit: int | None) -> tuple[dict[str, set], dict[str, str]]:
    word_sources: dict[str, set] = {}
    id_to_name: dict[str, str] = {}
    state = {'tuples': 0}
    def_done = False

    with open(dump_path, encoding='utf-8', errors='replace') as f:
        for lineno, line in enumerate(f, 1):
            if not def_done and line.startswith(_DEF_PREFIX):
                if limit is None or state['tuples'] < limit:
                    _parse_definition_line(_strip_line_prefix(line, _DEF_PREFIX),
                                           word_sources, state)
                    if limit is not None and state['tuples'] >= limit:
                        def_done = True
            elif line.startswith(_SRC_PREFIX):
                _parse_source_line(_strip_line_prefix(line, _SRC_PREFIX), id_to_name)
            if lineno % 500_000 == 0:
                print(f'  ...{lineno:,} lines, {len(word_sources):,} headwords, '
                      f'{len(id_to_name)} sources', file=sys.stderr)

    return word_sources, id_to_name


def write_db(out_path: Path, word_sources: dict[str, set], id_to_name: dict[str, str]) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    conn = sqlite3.connect(str(out_path))
    conn.execute("""
        CREATE TABLE dict_sources (
            word       TEXT PRIMARY KEY,
            sources    TEXT,
            dict_count INTEGER
        )
    """)
    rows = []
    for word, sids in word_sources.items():
        names = sorted({id_to_name.get(sid, f'#{sid}') for sid in sids})
        rows.append((word, '|'.join(names), len(sids)))
    conn.executemany('INSERT INTO dict_sources VALUES (?,?,?)', rows)
    conn.commit()
    conn.close()
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dump', type=Path, default=DEX_SQL_PATH,
                        help='DEX MySQL dump path (default: %(default)s)')
    parser.add_argument('--out', type=Path, default=OUTPUT_DB,
                        help='output SQLite DB (default: %(default)s)')
    parser.add_argument('--limit', type=int, default=None,
                        help='cap Definition tuples processed (smoke test)')
    args = parser.parse_args()

    if not args.dump.exists():
        print(f'Dump not found: {args.dump}', file=sys.stderr)
        return 1

    print(f'Streaming {args.dump} ...', file=sys.stderr)
    word_sources, id_to_name = extract(args.dump, args.limit)
    print(f'Sources resolved : {len(id_to_name)}', file=sys.stderr)
    print(f'Headwords        : {len(word_sources):,}', file=sys.stderr)
    n = write_db(args.out, word_sources, id_to_name)
    print(f'Wrote {n:,} rows → {args.out}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
