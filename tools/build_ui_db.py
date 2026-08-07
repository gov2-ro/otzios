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

try:
    from wordfreq import zipf_frequency as _zipf
except ImportError:
    _zipf = None

sys.path.insert(0, str(Path(__file__).parent))
from word_ids import apply_to_db as _apply_word_ids

SHORTLIST_PATH  = Path('data/processed/forgotten_words_shortlist.csv')
RARE_PATH       = Path('data/processed/rare_words_wordfreq.csv')
WEB_PATH        = Path('data/processed/diachronic_shortlist_web_validated.csv')
DEFINITIONS_PATH = Path('data/processed/definitions.db')
DICT_SOURCES_PATH = Path('data/processed/dict_sources.db')
OUT_PATH        = Path('public/data/ui.db')

_ETYM_JUNK = {'vezi', 'cf.', 'după', 'după unii', 'probabil', 'cuvânt',
              'necunoscută', 'de la', 'sau'}

# DEX register tags that describe usage style rather than archaic/rare status.
# Excluded from the register filter dropdown so it only shows meaningful archaic markers.
_REGISTER_USAGE_NOTES = {
    'figurat', 'adesea figurat', 'metaforic', 'popular', 'familiar', 'poetic',
    'literar', 'ironic', 'glumeț', 'depreciativ', 'peiorativ', 'neobișnuit',
    'în comparații / la comparativ', 'în superstiții', 'prin exagerare',
    'prin metonimie', 'eliptic', 'repetat', 'personificat', 'pleonastic',
    'impropriu', 'argou', 'argotic', 'eufemistic', 'hiperbolic', 'emfatic',
    'alegoric', 'augmentativ', 'corelativ', 'vulgar', 'jargon',
    'cu pronunțare regională', 'la vocativ', 'sens curent', 'personal',
    'cu valoare de singular', 'cu valoare verbală',
    'cu valoare de numeral cardinal', 'cu valoare de numeral distributiv',
}


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


_DIACRITIC_MAP = str.maketrans('țșţşăâî', 'tstsaai')


def _strip_diacritics(s: str) -> str:
    return s.lower().translate(_DIACRITIC_MAP)


def merge_dict_sources(conn: sqlite3.Connection, sources_db: Path) -> None:
    """Populate words.sources (pipe-delimited dictionary names) from dict_sources.db.

    Matches on the exact headword first; for the ~2% of UI words with no exact
    headword (mostly feminine / inflected forms), falls back to a diacritic-stripped
    match — but only when that normalized form maps to a single dict_sources entry,
    to avoid pulling in the wrong headword's dictionary list.
    """
    if not sources_db.exists():
        print(f'  (dict sources DB not found, skipping: {sources_db})')
        return
    print(f'Merging dictionary sources from {sources_db}…')
    sconn = sqlite3.connect(str(sources_db))
    exact: dict[str, str] = {}
    norm_index: dict[str, str] = {}
    norm_dupes: set[str] = set()
    for word, srcs in sconn.execute('SELECT word, sources FROM dict_sources'):
        if not word or not srcs:
            continue
        exact[word] = srcs
        n = _strip_diacritics(word)
        if n in norm_index:
            norm_dupes.add(n)
        else:
            norm_index[n] = srcs
    sconn.close()

    updated = 0
    for (w,) in conn.execute('SELECT word FROM words').fetchall():
        srcs = exact.get(w)
        if srcs is None:
            n = _strip_diacritics(w)
            if n not in norm_dupes:
                srcs = norm_index.get(n)
        if srcs is not None:
            conn.execute('UPDATE words SET sources=? WHERE word=?', (srcs, w))
            updated += 1
    print(f'  {updated} words matched to dictionary sources')


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
            word_normalized  TEXT,
            dex_frequency    REAL,
            verdict          TEXT,
            confidence_tier  TEXT,
            log_ratio        REAL,
            hist_ppm         REAL,
            modern_ppm       REAL,
            subtitle_ppm     REAL,
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
            word_tier        TEXT DEFAULT 'forgotten',
            dict_count       INTEGER,
            zipf_frequency   REAL,
            en_zipf          REAL,
            proper_noun_like INTEGER,
            sources          TEXT,
            word_id          INTEGER
        )
    """)

    print(f'Loading shortlist from {shortlist}…')
    with open(shortlist, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            conn.execute(
                """INSERT OR IGNORE INTO words
                   (word, dex_frequency, verdict, confidence_tier, log_ratio,
                    hist_ppm, modern_ppm, subtitle_ppm,
                    dex_pos, dex_register, dex_domain,
                    dex_etymology, is_forgotten, has_definition, word_tier,
                    dict_count)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row['word'],
                    _float(row.get('dex_frequency', '')),
                    row.get('verdict') or None,
                    row.get('confidence_tier') or None,
                    _float(row.get('log_ratio', '')),
                    _float(row.get('hist_ppm', '')),
                    _float(row.get('modern_ppm', '')),
                    _float(row.get('subtitle_ppm', '')),
                    _normalize_sep(row.get('dex_pos')),
                    _normalize_sep(row.get('dex_register')),
                    _normalize_sep(row.get('dex_domain')),
                    _normalize_sep(row.get('dex_etymology')),
                    _bool(row.get('is_forgotten', '')),
                    _bool(row.get('has_definition', '')),
                    'forgotten',
                    _int(row.get('dict_count', '')),
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

    merge_dict_sources(conn, DICT_SOURCES_PATH)

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
        ('register',  'dex_register',  _REGISTER_USAGE_NOTES),
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

    conn.create_function('strip_diacritics', 1, _strip_diacritics)
    conn.execute('UPDATE words SET word_normalized = strip_diacritics(word)')

    # Populate zipf_frequency + en_zipf using wordfreq (optional)
    if _zipf is not None:
        print('Computing zipf frequencies…')
        rows = conn.execute('SELECT word FROM words').fetchall()
        batch = [(_zipf(r[0], 'ro'), _zipf(r[0], 'en'), r[0]) for r in rows]
        conn.executemany('UPDATE words SET zipf_frequency=?, en_zipf=? WHERE word=?', batch)
        print(f'  {len(batch)} rows updated')
    else:
        print('wordfreq not available — zipf_frequency/en_zipf left NULL')

    # Populate proper_noun_like from lexemes.db (optional)
    lexemes_path = Path('data/processed/lexemes.db')
    if lexemes_path.exists():
        print('Computing proper_noun_like…')
        lconn = sqlite3.connect(str(lexemes_path))
        caps = {r[0].lower() for r in lconn.execute(
            "SELECT DISTINCT formNoAccent FROM Lexeme WHERE formNoAccent GLOB '[A-Z]*'"
        ).fetchall()}
        lconn.close()
        conn.execute('UPDATE words SET proper_noun_like = 0')
        if caps:
            ph = ','.join('?' * len(caps))
            conn.execute(
                f'UPDATE words SET proper_noun_like = 1 WHERE word IN ({ph})', list(caps)
            )
        print(f'  {len(caps)} proper-noun candidates marked')
    else:
        print('lexemes.db not found — proper_noun_like left NULL')

    # Permanent word ids for the compact ?w= share URLs. Runs last, so every
    # insert path (shortlist + rare-in-use) has landed and no word is missed.
    print('Assigning permanent word ids…')
    print(f'  {_apply_word_ids(conn)} rows carry a word_id')

    # Indexes
    conn.execute('CREATE UNIQUE INDEX idx_words_word_id ON words(word_id)')
    conn.execute('CREATE INDEX idx_vocab_kind      ON vocab(kind)')
    conn.execute('CREATE INDEX idx_words_verdict   ON words(verdict)')
    conn.execute('CREATE INDEX idx_words_tier      ON words(confidence_tier)')
    conn.execute('CREATE INDEX idx_words_word_tier ON words(word_tier)')
    conn.execute('CREATE INDEX idx_words_word      ON words(word COLLATE NOCASE)')
    conn.execute('CREATE INDEX idx_words_modern    ON words(modern_ppm)')
    conn.execute('CREATE INDEX idx_words_normalized ON words(word_normalized)')
    conn.execute('CREATE INDEX idx_words_zipf       ON words(zipf_frequency)')

    conn.commit()
    conn.close()

    total = sqlite3.connect(str(out)).execute('SELECT COUNT(*) FROM words').fetchone()[0]
    size_mb = out.stat().st_size / 1024 / 1024
    print(f'Done → {out}  ({total:,} words, {size_mb:.1f} MB)')


if __name__ == '__main__':
    build(SHORTLIST_PATH, RARE_PATH, WEB_PATH, DEFINITIONS_PATH, OUT_PATH)
