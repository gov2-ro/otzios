#!/usr/bin/env python3
"""
Extract Tag, ObjectTag, and EntryLexeme tables from the DEX MySQL dump into lexemes.db.
Run once after extract_lexemes.py; required before validate_diachronic.py emits taxonomy columns.

Usage:
    python extract_taxonomy.py
    python extract_taxonomy.py --sql data/dictionaries/dex-database.sql  # full dump
    python extract_taxonomy.py --sql data/dictionaries/dex-database-sample.sql --db data/processed/lexemes.db
"""

import argparse
import sqlite3
from extract_lexemes import parse_mysql_insert

TARGET_TABLES = {'Tag', 'ObjectTag', 'EntryLexeme'}

SCHEMAS = {
    'Tag': """
        CREATE TABLE IF NOT EXISTS Tag (
            id INTEGER PRIMARY KEY,
            parentId INTEGER,
            value TEXT,
            color INTEGER,
            icon TEXT,
            iconOnly INTEGER,
            tooltip TEXT,
            public INTEGER,
            isPos INTEGER,
            createDate INTEGER,
            modDate INTEGER
        )
    """,
    'ObjectTag': """
        CREATE TABLE IF NOT EXISTS ObjectTag (
            id INTEGER PRIMARY KEY,
            objectId INTEGER,
            objectType INTEGER,
            tagId INTEGER,
            createDate INTEGER,
            modDate INTEGER
        )
    """,
    'EntryLexeme': """
        CREATE TABLE IF NOT EXISTS EntryLexeme (
            id INTEGER PRIMARY KEY,
            entryId INTEGER,
            lexemeId INTEGER,
            entryRank INTEGER,
            lexemeRank INTEGER,
            main INTEGER,
            createDate INTEGER,
            modDate INTEGER
        )
    """,
}

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_objecttag_objectid ON ObjectTag(objectId)",
    "CREATE INDEX IF NOT EXISTS idx_objecttag_tagid    ON ObjectTag(tagId)",
    "CREATE INDEX IF NOT EXISTS idx_entrylexeme_lexid  ON EntryLexeme(lexemeId)",
    "CREATE INDEX IF NOT EXISTS idx_entrylexeme_entid  ON EntryLexeme(entryId)",
]

PLACEHOLDERS = {
    'Tag':        '(?,?,?,?,?,?,?,?,?,?,?)',
    'ObjectTag':  '(?,?,?,?,?,?)',
    'EntryLexeme':'(?,?,?,?,?,?,?,?)',
}


def extract(sql_path, db_path):
    print(f"Source: {sql_path}")
    print(f"Target: {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    for ddl in SCHEMAS.values():
        cur.execute(ddl)
    conn.commit()

    counts = {t: 0 for t in TARGET_TABLES}
    seen = set()

    with open(sql_path, encoding='utf-8') as fh:
        for lineno, line in enumerate(fh, 1):
            if lineno % 10_000 == 0:
                done = ', '.join(f'{t}: {counts[t]:,}' for t in TARGET_TABLES)
                print(f"  line {lineno:,}  [{done}]", end='\r', flush=True)

            table, records = parse_mysql_insert(line)
            if table not in TARGET_TABLES:
                continue

            seen.add(table)
            ph = PLACEHOLDERS[table]
            cur.executemany(f'INSERT OR REPLACE INTO {table} VALUES {ph}', records)
            counts[table] += len(records)

            # Commit in chunks to keep memory usage low
            if sum(counts.values()) % 50_000 == 0:
                conn.commit()

            if seen == TARGET_TABLES and lineno > 100_000:
                # All three tables seen; keep scanning in case rows are split across
                # multiple INSERT blocks (ObjectTag usually is)
                pass

    conn.commit()

    print()
    print()
    for table, n in counts.items():
        print(f"  {table}: {n:,} rows")

    print("\nBuilding indexes…")
    for idx in INDEXES:
        cur.execute(idx)
    conn.commit()
    print("  done")

    _sanity_check(conn)
    conn.close()


def _sanity_check(conn):
    print("\nSanity check — tags for 'isihie':")
    try:
        rows = conn.execute("""
            SELECT DISTINCT t.value, t.parentId
            FROM Lexeme l
            JOIN EntryLexeme el ON el.lexemeId = l.id
            JOIN ObjectTag ot ON ot.objectId = el.entryId
            JOIN Tag t ON t.id = ot.tagId
            WHERE lower(l.formNoAccent) = 'isihie'
              AND t.parentId IN (1, 41, 42)
        """).fetchall()
        if rows:
            for value, pid in rows:
                family = {1: 'etymology', 41: 'domain', 42: 'register'}.get(pid, f'pid={pid}')
                print(f"  [{family}] {value}")
        else:
            print("  (no taxonomy tags found — objectType join may need adjustment)")
            _debug_isihie(conn)
    except sqlite3.OperationalError as e:
        print(f"  query failed: {e}")


def _debug_isihie(conn):
    print("\n  Debug — entryIds for 'isihie':")
    rows = conn.execute("""
        SELECT el.entryId FROM Lexeme l
        JOIN EntryLexeme el ON el.lexemeId = l.id
        WHERE lower(l.formNoAccent) = 'isihie'
    """).fetchall()
    entry_ids = [r[0] for r in rows]
    print(f"  entryIds: {entry_ids}")
    if entry_ids:
        rows2 = conn.execute(
            f"SELECT objectId, objectType, tagId FROM ObjectTag WHERE objectId IN ({','.join('?'*len(entry_ids))})",
            entry_ids
        ).fetchall()
        print(f"  ObjectTag rows for those entryIds: {rows2}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract DEX taxonomy tables into lexemes.db')
    parser.add_argument('--sql', default='data/dictionaries/dex-database-sample.sql',
                        help='Path to DEX MySQL dump')
    parser.add_argument('--db', default='data/processed/lexemes.db',
                        help='Path to lexemes.db (must already exist with Lexeme table)')
    args = parser.parse_args()
    extract(args.sql, args.db)
