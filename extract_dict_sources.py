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

`Source` also carries `year` and `normative`, which give each word a *dictionary
recency* signal for free: the newest dictionary a word still appears in separates
"dropped out of the normative lexicon" from "still officially Romanian, just unused".
That distinction is what splits the two seams in `make_shortlist.py`.

Output: data/processed/dict_sources.db
Schema: dict_sources(word PK, sources, dict_count, newest_dict_year, oldest_dict_year,
                     in_current_dict)
        `word`             — normalized headword (lower, ș/ț, NFC), matches the pipeline
        `sources`          — sorted shortNames, '|'-joined (e.g. "DEX '98|DLR|MDA")
        `dict_count`       — number of distinct dictionaries
        `newest_dict_year` — max Source.year across the word's dictionaries
        `oldest_dict_year` — min, i.e. roughly first attestation
        `in_current_dict`  — 1 if it appears in a dictionary from CURRENT_DICT_YEAR on
        sources_meta(source_id PK, short_name, year, normative)

Usage:
    python extract_dict_sources.py                                   # full dump
    python extract_dict_sources.py --dump data/dictionaries/dex-database-sample.sql --limit 5000
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path

from dump_parser import normalize, parse_tuples, strip_line_prefix

DEX_SQL_PATH = Path('data/dictionaries/dex-database.sql')
OUTPUT_DB = Path('data/processed/dict_sources.db')

_DEF_PREFIX = "INSERT INTO `Definition` VALUES "
_SRC_PREFIX = "INSERT INTO `Source` VALUES "

# Definition: (id, userId, sourceId, lexicon, internalRep, ...) — stop at lexicon so the
# internalRep longtext is skipped rather than decoded.
_DEF_SOURCE_ID, _DEF_LEXICON = 2, 3
# Source: (id, shortName, urlName, name, author, publisher, year, sourceTypeId, managerId,
#          importType, reformId, remark, hidden, link, courtesyLink, courtesyText,
#          canModerate, normative, ...)
_SRC_ID, _SRC_SHORT_NAME, _SRC_YEAR, _SRC_NORMATIVE = 0, 1, 6, 17

# A word appearing in a dictionary from this year on is still in the current lexicon.
# 2005 sits after DEX '98 / NODEX '02 and before DEX '09 / DOOM 2 '05, so it selects the
# genuinely current layer without depending on a hand-maintained list of sigla.
CURRENT_DICT_YEAR = 2005

_YEAR_RE = re.compile(r'(1[5-9]\d{2}|20\d{2})')


def parse_year(raw: str | None) -> int | None:
    """Source.year is free text ('1998', '1955-1957', 'f.a.'). Take the latest year in it."""
    if not raw:
        return None
    years = _YEAR_RE.findall(raw)
    return max(int(y) for y in years) if years else None


def _parse_source_line(s: str, sources: dict[str, dict]) -> None:
    for t in parse_tuples(s, max_index=_SRC_NORMATIVE):
        if len(t) <= _SRC_SHORT_NAME:
            continue
        sid, short_name = t[_SRC_ID], t[_SRC_SHORT_NAME]
        if not sid or not short_name:
            continue
        year = parse_year(t[_SRC_YEAR]) if len(t) > _SRC_YEAR else None
        normative = t[_SRC_NORMATIVE] if len(t) > _SRC_NORMATIVE else None
        sources[sid] = {
            'short_name': short_name,
            'year': year,
            'normative': int(normative) if (normative or '').isdigit() else 0,
        }


def _parse_definition_line(s: str, word_sources: dict[str, set], state: dict) -> None:
    for t in parse_tuples(s, max_index=_DEF_LEXICON):
        if len(t) <= _DEF_LEXICON:
            continue
        source_id, lexicon = t[_DEF_SOURCE_ID], t[_DEF_LEXICON]
        if not lexicon or not source_id:
            continue
        norm = normalize(lexicon)
        srcs = word_sources.get(norm)
        if srcs is None:
            srcs = set()
            word_sources[norm] = srcs
        srcs.add(source_id)
        state['tuples'] += 1


def extract(dump_path: Path, limit: int | None) -> tuple[dict[str, set], dict[str, dict]]:
    word_sources: dict[str, set] = {}
    sources: dict[str, dict] = {}
    state = {'tuples': 0}
    def_done = False

    with open(dump_path, encoding='utf-8', errors='replace') as f:
        for lineno, line in enumerate(f, 1):
            if not def_done and line.startswith(_DEF_PREFIX):
                if limit is None or state['tuples'] < limit:
                    _parse_definition_line(strip_line_prefix(line, _DEF_PREFIX),
                                           word_sources, state)
                    if limit is not None and state['tuples'] >= limit:
                        def_done = True
            elif line.startswith(_SRC_PREFIX):
                _parse_source_line(strip_line_prefix(line, _SRC_PREFIX), sources)
            if lineno % 500_000 == 0:
                print(f'  ...{lineno:,} lines, {len(word_sources):,} headwords, '
                      f'{len(sources)} sources', file=sys.stderr)

    return word_sources, sources


def write_db(out_path: Path, word_sources: dict[str, set], sources: dict[str, dict]) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    conn = sqlite3.connect(str(out_path))
    conn.execute("""
        CREATE TABLE dict_sources (
            word             TEXT PRIMARY KEY,
            sources          TEXT,
            dict_count       INTEGER,
            newest_dict_year INTEGER,
            oldest_dict_year INTEGER,
            in_current_dict  INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE sources_meta (
            source_id  INTEGER PRIMARY KEY,
            short_name TEXT,
            year       INTEGER,
            normative  INTEGER
        )
    """)
    conn.executemany('INSERT INTO sources_meta VALUES (?,?,?,?)', [
        (int(sid), meta['short_name'], meta['year'], meta['normative'])
        for sid, meta in sources.items() if sid.isdigit()
    ])

    rows = []
    for word, sids in word_sources.items():
        names = sorted({sources.get(sid, {}).get('short_name') or f'#{sid}' for sid in sids})
        years = [sources.get(sid, {}).get('year') for sid in sids]
        years = [y for y in years if y]
        newest = max(years) if years else None
        oldest = min(years) if years else None
        rows.append((word, '|'.join(names), len(sids), newest, oldest,
                     1 if (newest or 0) >= CURRENT_DICT_YEAR else 0))
    conn.executemany('INSERT INTO dict_sources VALUES (?,?,?,?,?,?)', rows)
    conn.execute('CREATE INDEX idx_dict_current ON dict_sources(in_current_dict)')
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
    word_sources, sources = extract(args.dump, args.limit)
    dated = sum(1 for m in sources.values() if m['year'])
    print(f'Sources resolved : {len(sources)} ({dated} with a year)', file=sys.stderr)
    print(f'Headwords        : {len(word_sources):,}', file=sys.stderr)
    if not sources:
        # The sampled dump comments this table out ("-- SAMPLED: INSERT INTO `Source`"),
        # which would silently produce '#<id>' names and no years at all.
        print('WARNING: no Source rows found — dictionary names and years will be '
              'missing. Is this the sampled dump?', file=sys.stderr)
    n = write_db(args.out, word_sources, sources)
    print(f'Wrote {n:,} rows → {args.out}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
