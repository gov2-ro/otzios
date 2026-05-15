#!/usr/bin/env python3
"""
Extract first definition per word from DEX MySQL dump.
Streams line by line — never loads the full 1.2 GB into memory.
Output: data/processed/definitions.db
Schema: definitions(word TEXT PRIMARY KEY, definition TEXT NOT NULL)
"""
import sqlite3
from pathlib import Path

SQL_PATH = Path('data/dictionaries/dex-database.sql')
OUT_PATH = Path('data/processed/definitions.db')

_PREFIX = "INSERT INTO `DefinitionSimple` VALUES "


def _parse_values(values_str: str) -> list[list]:
    """Parse MySQL multi-value VALUES clause into list of value lists.

    Handles quoted strings with \\' and \\\\ escapes, and ) inside strings.
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
    """Collect first definition per lexicon from sql_path, write to out_path.

    Returns number of words written.
    """
    seen: dict[str, str] = {}  # word → first definition

    with open(sql_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line.startswith(_PREFIX):
                continue
            values_str = line[len(_PREFIX):]
            if values_str.endswith(';'):
                values_str = values_str[:-1]
            for row in _parse_values(values_str):
                if len(row) < 3:
                    continue
                definition = row[1]   # col 1: definition text
                word = row[2]         # col 2: lexicon (the word)
                if word and definition and word not in seen:
                    seen[word] = definition

    out_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(out_path))
    conn.execute('DROP TABLE IF EXISTS definitions')
    conn.execute(
        'CREATE TABLE definitions (word TEXT PRIMARY KEY, definition TEXT NOT NULL)'
    )
    conn.executemany('INSERT INTO definitions VALUES (?, ?)', seen.items())
    conn.commit()
    conn.close()
    print(f"Wrote {len(seen)} definitions to {out_path}")
    return len(seen)


if __name__ == '__main__':
    extract(SQL_PATH, OUT_PATH)
