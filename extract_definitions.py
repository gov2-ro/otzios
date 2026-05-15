#!/usr/bin/env python3
"""
Extract first definition per Lexeme form from DEX MySQL dump.

Joins Lexeme → EntryLexeme → EntryDefinition → DefinitionSimple so that
every word form in the shortlist (including inflected forms like plurals and
case endings) maps to its entry's primary definition, not just headwords.

Streams line by line — never loads the full 1.2 GB into memory.
Output: data/processed/definitions.db
Schema: definitions(word TEXT PRIMARY KEY, definition TEXT NOT NULL)
"""
import sqlite3
from pathlib import Path

SQL_PATH = Path('data/dictionaries/dex-database.sql')
OUT_PATH = Path('data/processed/definitions.db')

_TARGET = frozenset({'Lexeme', 'EntryLexeme', 'EntryDefinition', 'DefinitionSimple'})


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


def _rank(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def extract(sql_path: Path, out_path: Path) -> int:
    """Join Lexeme → EntryLexeme → EntryDefinition → DefinitionSimple.

    For each Lexeme.formNoAccent, follows the chain to its entry's primary
    definition (lowest definitionRank). When a lexeme belongs to multiple
    entries, the entry with the lowest entryRank is used.

    Returns number of words written.
    """
    # lexeme_id → formNoAccent
    lex_form: dict[str, str] = {}
    # lexeme_id → (entry_id, entryRank)  — keep lowest entryRank per lexeme
    lex_entry: dict[str, tuple[str, int]] = {}
    # entry_id → (definition_id, definitionRank)  — keep lowest definitionRank
    entry_def: dict[str, tuple[str, int]] = {}
    # definition_id → text
    def_text: dict[str, str] = {}

    prefixes = {t: f"INSERT INTO `{t}` VALUES " for t in _TARGET}

    print("Streaming dump (this takes a few minutes)…")
    line_count = 0
    with open(sql_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line_count += 1
            if line_count % 200_000 == 0:
                print(f"  {line_count:,} lines — "
                      f"lexemes:{len(lex_form):,}  "
                      f"lex→entry:{len(lex_entry):,}  "
                      f"entry→def:{len(entry_def):,}  "
                      f"defs:{len(def_text):,}")

            line = line.rstrip('\n')
            for table, prefix in prefixes.items():
                if not line.startswith(prefix):
                    continue
                values_str = line[len(prefix):]
                if values_str.endswith(';'):
                    values_str = values_str[:-1]

                for row in _parse_values(values_str):
                    if table == 'Lexeme':
                        # cols: id(0), form(1), formNoAccent(2)
                        if len(row) >= 3 and row[0] and row[2]:
                            lex_form[row[0]] = row[2]

                    elif table == 'EntryLexeme':
                        # cols: id(0), entryId(1), lexemeId(2), entryRank(3)
                        if len(row) >= 4 and row[1] and row[2]:
                            lid, eid, rank = row[2], row[1], _rank(row[3])
                            if lid not in lex_entry or rank < lex_entry[lid][1]:
                                lex_entry[lid] = (eid, rank)

                    elif table == 'EntryDefinition':
                        # cols: id(0), entryId(1), definitionId(2), entryRank(3), definitionRank(4)
                        if len(row) >= 5 and row[1] and row[2]:
                            eid, did, rank = row[1], row[2], _rank(row[4])
                            if eid not in entry_def or rank < entry_def[eid][1]:
                                entry_def[eid] = (did, rank)

                    elif table == 'DefinitionSimple':
                        # cols: id(0), definition(1)
                        if len(row) >= 2 and row[0] and row[1]:
                            def_text.setdefault(row[0], row[1])
                break  # only one table prefix matches per line

    print(f"Joining {len(lex_form):,} lexemes…")
    seen: dict[str, str] = {}
    for lid, form in lex_form.items():
        if not form or form in seen:
            continue
        entry = lex_entry.get(lid)
        if not entry:
            continue
        defn = entry_def.get(entry[0])
        if not defn:
            continue
        text = def_text.get(defn[0])
        if text:
            seen[form] = text

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
