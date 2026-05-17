#!/usr/bin/env python3
"""
Extract one definition per headword from DEX MySQL dump.

The DEX dump's `DefinitionSimple` table has columns
(id, definition, lexicon, createDate, modDate, millShown, millGuessed).
Despite the field name, `lexicon` is the *headword* the definition belongs
to — not a dictionary source. We use it directly as the join key.

A previous version of this script joined Lexeme → EntryLexeme →
EntryDefinition → DefinitionSimple. That chain produced systematically
misaligned pairings (e.g. `abate` matched to a definition of `abatiză`)
because Entry records group multiple related-but-distinct words and the
"primary" rank-1 definition for an Entry is not necessarily about its
primary Lexeme. The lexicon column avoids the chain entirely.

Streams line by line — never loads the full 1.2 GB into memory.
Output: data/processed/definitions.db
Schema: definitions(word TEXT PRIMARY KEY, definition TEXT NOT NULL)
"""
import sqlite3
from pathlib import Path

SQL_PATH = Path('data/dictionaries/dex-database.sql')
OUT_PATH = Path('data/processed/definitions.db')

_PREFIX = 'INSERT INTO `DefinitionSimple` VALUES '


def _parse_values(values_str: str) -> list[list]:
    """Parse MySQL multi-value VALUES clause into list of value lists.

    Handles quoted strings with \\' and \\\\ escapes, and ) inside strings.
    All INSERT rows in this dump are on a single line in multi-value format.
    Returns list of rows; each row is a list of str|None values (quotes stripped).
    """
    rows = []
    i = 0
    n = len(values_str)
    while i < n:
        if values_str[i] != '(':
            i += 1
            continue
        i += 1  # skip opening '('
        row: list = []
        field: list[str] = []
        in_str = False
        while i < n:
            c = values_str[i]
            if in_str:
                if c == '\\' and i + 1 < n:
                    nxt = values_str[i + 1]
                    field.append("'" if nxt == "'" else ('\\' if nxt == '\\' else nxt))
                    i += 2
                    continue
                elif c == "'":
                    in_str = False
                else:
                    field.append(c)
            else:
                if c == "'":
                    in_str = True
                elif c == ',':
                    row.append(_clean(''.join(field)))
                    field = []
                elif c == ')':
                    row.append(_clean(''.join(field)))
                    rows.append(row)
                    break
                else:
                    field.append(c)
            i += 1
        i += 1  # advance past ')'
    return rows


def _clean(v: str) -> str | None:
    v = v.strip()
    return None if v == 'NULL' else v


def extract(sql_path: Path, out_path: Path) -> int:
    """Read DefinitionSimple, keep the first definition per headword.

    Rows arrive in id order; `setdefault` therefore keeps the lowest-id
    definition for each headword, which serves as a stable proxy for the
    "primary" definition.

    Returns number of words written.
    """
    seen: dict[str, str] = {}
    rows_total = 0
    rows_skipped_empty = 0

    print("Streaming dump (this takes a minute)…")
    line_count = 0
    with open(sql_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line_count += 1
            if line_count % 200_000 == 0:
                print(f"  {line_count:,} lines — headwords:{len(seen):,}")

            if not line.startswith(_PREFIX):
                continue

            values_str = line[len(_PREFIX):].rstrip('\n')
            if values_str.endswith(';'):
                values_str = values_str[:-1]

            for row in _parse_values(values_str):
                # cols: id(0), definition(1), lexicon=headword(2), ...
                if len(row) < 3:
                    continue
                rows_total += 1
                headword = row[2]
                text = row[1]
                if not headword or not text or not text.strip():
                    rows_skipped_empty += 1
                    continue
                seen.setdefault(headword, text)

    print(f"\nDefinitionSimple rows scanned: {rows_total:,}")
    print(f"  ✗ skipped (empty headword or text): {rows_skipped_empty:,}")
    print(f"  ✓ unique headwords kept: {len(seen):,}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(out_path))
    conn.execute('DROP TABLE IF EXISTS definitions')
    conn.execute(
        'CREATE TABLE definitions (word TEXT PRIMARY KEY, definition TEXT NOT NULL)'
    )
    conn.executemany('INSERT INTO definitions VALUES (?, ?)', seen.items())
    conn.commit()
    conn.close()
    print(f"Wrote {len(seen):,} definitions to {out_path}")
    return len(seen)


if __name__ == '__main__':
    extract(SQL_PATH, OUT_PATH)
