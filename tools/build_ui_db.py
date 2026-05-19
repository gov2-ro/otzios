#!/usr/bin/env python3
"""Build public/data/ui.db from pipeline CSV outputs + definitions.db.

Run from repo root:
    python tools/build_ui_db.py
"""
import csv
import sqlite3
import sys
from collections import Counter
from pathlib import Path

SHORTLIST_PATH  = Path('data/processed/forgotten_words_shortlist.csv')
RARE_PATH       = Path('data/processed/rare_words_wordfreq.csv')
WEB_PATH        = Path('data/processed/diachronic_shortlist_web_validated.csv')
DEFINITIONS_PATH = Path('data/processed/definitions.db')
OUT_PATH        = Path('public/data/ui.db')

_ETYM_JUNK = {'vezi', 'cf.', 'după', 'după unii', 'probabil', 'cuvânt',
              'necunoscută', 'de la', 'sau'}


def _float(v):
    try:
        return float(v) if v not in ('', None) else None
    except ValueError:
        return None


def _int(v):
    try:
        return int(v) if v not in ('', None) else None
    except ValueError:
        return None


def _bool(v):
    if v in ('true', 'True', '1'):
        return 1
    if v in ('false', 'False', '0'):
        return 0
    return None


def _normalize_sep(val):
    if not val:
        return None
    return val.replace('; ', '|').replace(';', '|')


def build(shortlist: Path, rare: Path, web: Path, defs: Path, out: Path) -> None:
    if not shortlist.exists():
        sys.exit(f'Missing: {shortlist}')

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    conn = sqlite3.connect(str(out))
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute("""
        CREATE TABLE words (
            word             TEXT PRIMARY KEY,
            dex_frequency    REAL,
            verdict          TEXT,
            confidence_tier  TEXT,
            log_ratio        REAL,
            hist_ppm         REAL,
            modern_ppm       REAL,
            dex_pos          TEXT,
            dex_register     TEXT,
            dex_domain       TEXT,
            dex_etymology    TEXT,
            is_forgotten     INTEGER,
            has_definition   INTEGER,
            total_results    INTEGER,
            in_wild          INTEGER,
            web_score        TEXT,
            top_url          TEXT,
            last_seen_approx TEXT,
            provider         TEXT,
            definition       TEXT,
            word_tier        TEXT DEFAULT 'forgotten'
        )
    """)

    print(f'Loading shortlist from {shortlist}…')
    with open(shortlist, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            conn.execute(
                """INSERT OR IGNORE INTO words
                   (word, dex_frequency, verdict, confidence_tier, log_ratio,
                    hist_ppm, modern_ppm, dex_pos, dex_register, dex_domain,
                    dex_etymology, is_forgotten, has_definition, word_tier)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row['word'],
                    _float(row.get('dex_frequency', '')),
                    row.get('verdict') or None,
                    row.get('confidence_tier') or None,
                    _float(row.get('log_ratio', '')),
                    _float(row.get('hist_ppm', '')),
                    _float(row.get('modern_ppm', '')),
                    _normalize_sep(row.get('dex_pos')),
                    _normalize_sep(row.get('dex_register')),
                    _normalize_sep(row.get('dex_domain')),
                    _normalize_sep(row.get('dex_etymology')),
                    _bool(row.get('is_forgotten', '')),
                    _bool(row.get('has_definition', '')),
                    'forgotten',
                ),
            )

    if rare.exists():
        print(f'Loading rare-in-use words from {rare}…')
        with open(rare, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                word_key = row.get('word_no_accent') or row.get('word', '')
                if not word_key:
                    continue
                conn.execute(
                    """INSERT OR IGNORE INTO words
                       (word, dex_frequency, dex_pos, dex_register, dex_domain,
                        dex_etymology, is_forgotten, word_tier)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        word_key,
                        _float(row.get('frequency', '')),
                        _normalize_sep(row.get('description')),
                        _normalize_sep(row.get('dex_register')),
                        _normalize_sep(row.get('dex_domain')),
                        _normalize_sep(row.get('dex_etymology')),
                        0,
                        'rare_in_use',
                    ),
                )
    else:
        print(f'  (rare-in-use file not found, skipping: {rare})')

    if web.exists():
        print(f'Merging web validation from {web}…')
        with open(web, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                conn.execute(
                    """UPDATE words SET
                       total_results=?, in_wild=?, web_score=?,
                       top_url=?, last_seen_approx=?, provider=?
                       WHERE word=?""",
                    (
                        _int(row.get('total_results', '')),
                        _bool(row.get('in_wild', '')),
                        row.get('web_score') or None,
                        row.get('top_url') or None,
                        row.get('last_seen_approx') or None,
                        row.get('provider') or None,
                        row['word'],
                    ),
                )
    else:
        print(f'  (web validation file not found, skipping: {web})')

    if defs.exists():
        print(f'Merging definitions from {defs}…')
        dconn = sqlite3.connect(str(defs))
        for word, definition in dconn.execute('SELECT word, definition FROM definitions'):
            conn.execute('UPDATE words SET definition=? WHERE word=?', (definition, word))
        dconn.close()
        # Reconcile has_definition to reflect actual definition presence.
        conn.execute('UPDATE words SET has_definition = (definition IS NOT NULL)')
    else:
        print(f'  (definitions DB not found, skipping: {defs})')

    # Build vocab table for dropdown options
    print('Building vocab table…')
    conn.execute("""
        CREATE TABLE vocab (
            kind  TEXT,
            value TEXT,
            count INTEGER
        )
    """)

    for kind, col, exclude in [
        ('register',  'dex_register',  None),
        ('domain',    'dex_domain',    None),
        ('etymology', 'dex_etymology', _ETYM_JUNK),
        ('pos',       'dex_pos',       None),
    ]:
        rows = conn.execute(
            f'SELECT {col} FROM words WHERE {col} IS NOT NULL'
        ).fetchall()
        counts: Counter = Counter()
        for (v,) in rows:
            for part in v.split('|'):
                p = part.strip()
                if p and (exclude is None or p not in exclude):
                    counts[p] += 1
        for value, count in counts.most_common():
            conn.execute(
                'INSERT INTO vocab (kind, value, count) VALUES (?,?,?)',
                (kind, value, count),
            )

    # Indexes
    conn.execute('CREATE INDEX idx_vocab_kind     ON vocab(kind)')
    conn.execute('CREATE INDEX idx_words_verdict  ON words(verdict)')
    conn.execute('CREATE INDEX idx_words_tier     ON words(confidence_tier)')
    conn.execute('CREATE INDEX idx_words_word_tier ON words(word_tier)')
    conn.execute('CREATE INDEX idx_words_word     ON words(word COLLATE NOCASE)')
    conn.execute('CREATE INDEX idx_words_modern   ON words(modern_ppm)')

    conn.commit()
    conn.close()

    total = sqlite3.connect(str(out)).execute('SELECT COUNT(*) FROM words').fetchone()[0]
    size_mb = out.stat().st_size / 1024 / 1024
    print(f'Done → {out}  ({total:,} words, {size_mb:.1f} MB)')


if __name__ == '__main__':
    build(SHORTLIST_PATH, RARE_PATH, WEB_PATH, DEFINITIONS_PATH, OUT_PATH)
