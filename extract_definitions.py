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

Second pass — `Definition` top-up (added 2026-08-17, see
docs/DEFINITIONS_ANALYSIS.md). `EntryDefinition.definitionId` actually
resolves against `Definition.id`, not `DefinitionSimple.id` — an earlier
investigation compared it to the wrong table and concluded (wrongly) that
94.8% of references were dangling. They aren't; `DefinitionSimple` is just a
separate, much smaller table (61k rows, no `sourceId` column — looks like the
answer key for dexonline's own quiz feature) that happens to share the
`lexicon`-as-headword shape. `Definition` has 1.23M rows across ~100
dictionary sources, but only sourceId 1 (DEX '98) and 2 (DEX '96) ship
untruncated `internalRep` text in this dump — every other source, including
other Academy dictionaries like DEX '84/'75, is truncated to a ~23-char stub.
So the top-up reads `Definition` restricted to those two ids, renders their
markup to plain text (`_clean_markup`), and fills in any headword
`DefinitionSimple` doesn't already cover. Measured against the current
shortlist: 1,786 words had no definition after the first pass; 660 of those
(37%) are recovered by this top-up. The rest have no untruncated entry under
either headword-matching scheme and still need `scrape_definitions.py`.

Streams line by line — never loads the full 1.2 GB into memory.
Output: data/processed/definitions.db
Schema: definitions(word TEXT PRIMARY KEY, definition TEXT NOT NULL)
"""
import re as _re
import sqlite3
from pathlib import Path

SQL_PATH = Path('data/dictionaries/dex-database.sql')
OUT_PATH = Path('data/processed/definitions.db')

_PREFIX = 'INSERT INTO `DefinitionSimple` VALUES '
_DEF_PREFIX = 'INSERT INTO `Definition` VALUES '
_DEX9896_SOURCE_IDS = ('1', '2')  # DEX '98, DEX '96 — the only untruncated sources


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
                    _ESC = {"'": "'", '\\': '\\', 'n': '\n', 'r': '\r', 't': '\t'}
                    field.append(_ESC.get(nxt, nxt))
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
    v = _re.sub(r'\s+', ' ', v).strip()
    return None if v == 'NULL' else v or None


# `internalRep` markup: @bold@ (headwords, etymology roots, "vezi X" pointer
# targets), #italic# (POS/register abbreviations), $underline$ (inflected
# forms, pronunciation syllables), %foreign-cognate% — all four are purely
# typographic and Romanian prose never uses these characters literally, so
# "rendering" them to plain text is just deleting the delimiters. ^N is a
# homograph number (A^1, A^2, …) with no equivalent in the DefinitionSimple
# plain-text style this merges into, so it's dropped rather than kept.
# {{...}} is an inline dexonline editor's correction note (e.g. "{{Am
# corectat forma de pl. ...}}"), not definition content, so it's removed
# entirely rather than unwrapped.
_MARKUP_CHARS = str.maketrans('', '', '@#$%')
_HOMOGRAPH_RE = _re.compile(r'\^\d+')
_EDITOR_NOTE_RE = _re.compile(r'\{\{.*?\}\}')


def _clean_markup(rep: str) -> str | None:
    rep = _EDITOR_NOTE_RE.sub('', rep)
    rep = rep.translate(_MARKUP_CHARS)
    rep = _HOMOGRAPH_RE.sub('', rep)
    return _clean(rep)


def _skip_int(s: str, i: int, n: int) -> int:
    while i < n and s[i] not in (',', ')'):
        i += 1
    return i


def _read_quoted_or_null(s: str, i: int, n: int) -> tuple[str | None, int]:
    """Read a quoted string or NULL starting at s[i]. Returns (value, index-after)."""
    if i < n and s[i] == "'":
        i += 1
        buf: list[str] = []
        while i < n:
            c = s[i]
            if c == '\\' and i + 1 < n:
                nxt = s[i + 1]
                buf.append({'n': '\n', 'r': '\r', 't': '\t'}.get(nxt, nxt))
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


def _skip_tuple_rest(s: str, i: int, n: int) -> int:
    """Advance past the remaining columns of the current tuple to just after ')'."""
    depth = 1
    in_str = False
    while i < n and depth > 0:
        c = s[i]
        if in_str:
            if c == '\\' and i + 1 < n:
                i += 2
                continue
            if c == "'":
                in_str = False
            i += 1
            continue
        if c == "'":
            in_str = True
        elif c == ')':
            depth -= 1
        i += 1
    return i


def _extract_dex9896_topup(sql_path: Path) -> dict[str, str]:
    """Second pass: read `Definition`, restricted to DEX '98 / DEX '96, for
    headwords `DefinitionSimple` doesn't cover.

    Columns: id(0), userId(1), sourceId(2), lexicon(3), internalRep(4), ...
    sourceId is checked before lexicon/internalRep are parsed, so the ~94% of
    rows from other (truncated) sources are skipped without allocating their
    text — full quote-aware parsing only runs on the ~71k DEX '98/'96 rows.

    Returns {headword: cleaned_text}, DEX '98 preferred over DEX '96 when a
    headword appears in both.
    """
    out: dict[str, tuple[str, str]] = {}  # headword -> (sourceId, text)
    n_prefix = len(_DEF_PREFIX)

    if not sql_path.exists():
        return {}

    with open(sql_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.startswith(_DEF_PREFIX):
                continue
            s = line[n_prefix:].rstrip('\n')
            if s.endswith(';'):
                s = s[:-1]
            i, n = 0, len(s)
            while i < n:
                while i < n and s[i] != '(':
                    i += 1
                if i >= n:
                    break
                i += 1  # skip '('

                i = _skip_int(s, i, n)  # id
                if i < n and s[i] == ',':
                    i += 1
                i = _skip_int(s, i, n)  # userId
                if i < n and s[i] == ',':
                    i += 1
                sid_start = i
                i = _skip_int(s, i, n)  # sourceId
                source_id = s[sid_start:i].strip()
                if i < n and s[i] == ',':
                    i += 1

                if source_id not in _DEX9896_SOURCE_IDS:
                    i = _skip_tuple_rest(s, i, n)
                    continue

                headword, i = _read_quoted_or_null(s, i, n)
                if i < n and s[i] == ',':
                    i += 1
                rep, i = _read_quoted_or_null(s, i, n)
                i = _skip_tuple_rest(s, i, n)

                if not headword or not rep:
                    continue
                text = _clean_markup(rep)
                if not text:
                    continue
                prev = out.get(headword)
                if prev is None or (prev[0] != '1' and source_id == '1'):
                    out[headword] = (source_id, text)

    return {w: t for w, (_, t) in out.items()}


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

    print("\nStreaming dump again for Definition (DEX '98 / DEX '96 top-up)…")
    topup = _extract_dex9896_topup(sql_path)
    added = 0
    for headword, text in topup.items():
        if headword not in seen:
            seen[headword] = text
            added += 1
    print(f"  ✓ DEX '98/'96 headwords found: {len(topup):,}")
    print(f"  ✓ new headwords added (not already in DefinitionSimple): {added:,}")
    print(f"  ✓ total headwords: {len(seen):,}")

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
