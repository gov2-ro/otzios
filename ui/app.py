import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from flask import Flask, render_template, request

app = Flask(__name__)

SHORTLIST_PATH = Path('data/processed/forgotten_words_shortlist.csv')
RARE_PATH = Path('data/processed/rare_words_wordfreq.csv')
WEB_PATH = Path('data/processed/diachronic_shortlist_web_validated.csv')
RESEARCH_DB_PATH = Path('data/research.db')
DEFINITIONS_DB_PATH = Path('data/processed/definitions.db')
DIACHRONIC_PATH = Path('data/processed/forgotten_words_diachronic.csv')

_words_db: sqlite3.Connection | None = None
_research_db: sqlite3.Connection | None = None


def _float(v: str) -> float | None:
    try:
        return float(v) if v not in ('', None) else None
    except ValueError:
        return None


def _int(v: str) -> int | None:
    try:
        return int(v) if v not in ('', None) else None
    except ValueError:
        return None


def _bool(v: str) -> int | None:
    if v in ('true', 'True', '1'):
        return 1
    if v in ('false', 'False', '0'):
        return 0
    return None


def load_words(
    shortlist_path: Path,
    web_path: Path,
    definitions_path: Path | None = None,
    rare_path: Path | None = None,
) -> sqlite3.Connection:
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    conn.row_factory = sqlite3.Row
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

    def _normalize_separators(val: str | None) -> str | None:
        if not val:
            return None
        return val.replace('; ', '|').replace(';', '|')

    with open(shortlist_path, newline='', encoding='utf-8') as f:
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
                    _normalize_separators(row.get('dex_pos')),
                    _normalize_separators(row.get('dex_register')),
                    _normalize_separators(row.get('dex_domain')),
                    _normalize_separators(row.get('dex_etymology')),
                    _bool(row.get('is_forgotten', '')),
                    _bool(row.get('has_definition', '')),
                    'forgotten',
                ),
            )

    _rare = rare_path if rare_path is not None else RARE_PATH
    if _rare.exists():
        with open(_rare, newline='', encoding='utf-8') as f:
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
                        _normalize_separators(row.get('description')),
                        _normalize_separators(row.get('dex_register')),
                        _normalize_separators(row.get('dex_domain')),
                        _normalize_separators(row.get('dex_etymology')),
                        0,
                        'rare_in_use',
                    ),
                )

    if web_path.exists():
        with open(web_path, newline='', encoding='utf-8') as f:
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

    defs_path = definitions_path if definitions_path is not None else DEFINITIONS_DB_PATH
    if defs_path.exists():
        dconn = sqlite3.connect(str(defs_path))
        for word, definition in dconn.execute('SELECT word, definition FROM definitions'):
            conn.execute('UPDATE words SET definition=? WHERE word=?', (definition, word))
        dconn.close()

    conn.commit()
    return conn


def open_research_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            word        TEXT PRIMARY KEY,
            bookmarked  INTEGER DEFAULT 0,
            note        TEXT    DEFAULT '',
            tags        TEXT    DEFAULT '',
            created_at  TEXT,
            updated_at  TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_sample (
            stratum    TEXT NOT NULL,
            word       TEXT NOT NULL,
            drawn_at   TEXT NOT NULL,
            PRIMARY KEY (stratum, word)
        )
    """)
    conn.commit()
    return conn


def _augment_with_audit_samples(words_conn: sqlite3.Connection,
                                research_conn: sqlite3.Connection,
                                diachronic_path: Path) -> int:
    """Pull audit-sample words missing from the words DB out of the diachronic CSV.

    Excluded-stratum samples (e.g. excl_pos, excl_absent_lowdex) are not in the
    shortlist, so the words table doesn't know about them. Without this, the
    detail panel 404s on those samples.
    """
    sample_words = {
        r['word'] for r in research_conn.execute('SELECT word FROM audit_sample').fetchall()
    }
    if not sample_words:
        return 0
    existing = {
        r[0] for r in words_conn.execute('SELECT word FROM words').fetchall()
    }
    missing = sample_words - existing
    if not missing or not diachronic_path.exists():
        return 0

    def _normalize_separators(val: str | None) -> str | None:
        if not val:
            return None
        return val.replace('; ', '|').replace(';', '|')

    inserted = 0
    with diachronic_path.open(encoding='utf-8') as f:
        for row in csv.DictReader(f):
            w = row.get('word', '')
            if w not in missing:
                continue
            words_conn.execute(
                """INSERT OR IGNORE INTO words
                   (word, dex_frequency, verdict, log_ratio, hist_ppm, modern_ppm,
                    dex_pos, dex_register, dex_domain, dex_etymology,
                    is_forgotten, has_definition, word_tier)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    w,
                    _float(row.get('dex_frequency', '')),
                    row.get('verdict') or None,
                    _float(row.get('log_ratio', '')),
                    _float(row.get('hist_ppm', '')),
                    _float(row.get('modern_ppm', '')),
                    _normalize_separators(row.get('dex_pos')),
                    _normalize_separators(row.get('dex_register')),
                    _normalize_separators(row.get('dex_domain')),
                    _normalize_separators(row.get('dex_etymology')),
                    _bool(row.get('is_forgotten', '')),
                    _bool(row.get('has_definition', '')),
                    'audit_only',
                ),
            )
            inserted += 1
    words_conn.commit()
    return inserted


def init_app(
    shortlist_path: Path | None = None,
    web_path: Path | None = None,
    research_path: Path | None = None,
    definitions_path: Path | None = None,
    rare_path: Path | None = None,
) -> None:
    global _words_db, _research_db
    _words_db = load_words(
        shortlist_path or SHORTLIST_PATH,
        web_path or WEB_PATH,
        definitions_path or DEFINITIONS_DB_PATH,
        rare_path or RARE_PATH,
    )
    _research_db = open_research_db(research_path or RESEARCH_DB_PATH)
    n = _augment_with_audit_samples(_words_db, _research_db, DIACHRONIC_PATH)
    if n:
        print(f'[audit] augmented words table with {n} excluded-sample words')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


PAGE_SIZE = 250

SORT_OPTIONS = {
    'rare':     'COALESCE(modern_ppm, -1) ASC',   # default — absent words first, then rarest
    'declined': 'log_ratio DESC NULLS LAST',
    'dex_freq': 'dex_frequency ASC NULLS LAST',
    'alpha':    'word ASC',
}

QUICK_TAGS = [
    ('ignore', 'i'),
    ('boring', 'B'),
    ('funny',  'f'),
    ('remove', 'x'),
]
QUICK_TAG_NAMES  = {t for t, _ in QUICK_TAGS}
QUICK_TAG_EMOJIS = {'ignore': '🙈', 'boring': '💤', 'funny': '😄', 'remove': '❌'}

# Audit-mode reserved keys. Same K on both included and excluded strata —
# the stratum decides the interpretation (keep vs should-be-in). Stored as
# audit:* tags in the same bookmarks.tags column.
AUDIT_TAGS_INCLUDED = [
    ('audit:keep',       'K', 'keep'),
    ('audit:inflection', 'I', 'inflection'),
    ('audit:variant',    'V', 'variant'),
    ('audit:loanword',   'L', 'loanword'),
    ('audit:dialect',    'D', 'dialect'),
    ('audit:jargon',     'J', 'jargon'),
    ('audit:no_def',     'M', 'no def'),
    ('audit:other',      'O', 'other'),
]
AUDIT_TAGS_EXCLUDED = [
    ('audit:keep',          'K', 'should be in'),
    ('audit:correctly_out', 'X', 'correctly out'),
    ('audit:no_def',        'M', 'no def'),
    ('audit:other',         'O', 'other'),
]
AUDIT_TAG_NAMES = {t for t, _, _ in (*AUDIT_TAGS_INCLUDED, *AUDIT_TAGS_EXCLUDED)}

STRATA_ORDER = [
    'tier_a_extinct',
    'tier_a_declining',
    'tier_a_historical',
    'tier_b_invechit',
    'tier_c_absent_highfreq',
    'rare_in_use',
    'excl_pos',
    'excl_absent_lowdex',
    'excl_stable_emerging',
    'excl_other',
]
STRATA_INCLUDED = set(STRATA_ORDER[:6])
STRATA_EXCLUDED = set(STRATA_ORDER[6:])


POS_OPTIONS = [
    ('substantiv feminin',  's.f.'),
    ('substantiv neutru',   's.n.'),
    ('substantiv masculin', 's.m.'),
    ('adjectiv',            'adj.'),
    ('verb',                'vb.'),
    ('adverb',              'adv.'),
    ('participiu',          'part.'),
    ('interjecție',         'interj.'),
]


_ETYM_JUNK = {'vezi', 'cf.', 'după', 'după unii', 'probabil', 'cuvânt', 'necunoscută', 'de la', 'sau'}


def _distinct_split(column: str, sep: str = '|', limit: int | None = None, exclude: set | None = None) -> list[str]:
    from collections import Counter
    rows = _words_db.execute(
        f'SELECT {column} FROM words WHERE {column} IS NOT NULL'
    ).fetchall()
    counts: Counter = Counter()
    for (v,) in rows:
        for part in v.split(sep):
            p = part.strip()
            if p and (exclude is None or p not in exclude):
                counts[p] += 1
    return [v for v, _ in counts.most_common(limit)]


def _bookmarks_map() -> dict[str, dict]:
    rows = _research_db.execute('SELECT * FROM bookmarks').fetchall()
    return {r['word']: dict(r) for r in rows}


def _is_audit(request_obj) -> bool:
    return request_obj.args.get('audit', '').strip() == '1'


def _audit_sample_words(stratum: str) -> list[str]:
    rows = _research_db.execute(
        'SELECT word FROM audit_sample WHERE stratum = ? ORDER BY word',
        (stratum,),
    ).fetchall()
    return [r['word'] for r in rows]


def _audit_progress() -> list[dict]:
    """Return per-stratum progress: total samples + count with any audit:* tag."""
    counts = dict(_research_db.execute(
        'SELECT stratum, COUNT(*) FROM audit_sample GROUP BY stratum'
    ).fetchall())

    rows = _research_db.execute("""
        SELECT s.stratum, COUNT(DISTINCT s.word) AS labeled
        FROM audit_sample s
        JOIN bookmarks b ON b.word = s.word
        WHERE b.tags LIKE 'audit:%' OR b.tags LIKE '%,audit:%'
        GROUP BY s.stratum
    """).fetchall()
    labeled = {r['stratum']: r['labeled'] for r in rows}

    out = []
    for s in STRATA_ORDER:
        total = counts.get(s, 0)
        if total == 0:
            continue
        out.append({
            'stratum':  s,
            'total':    total,
            'labeled':  labeled.get(s, 0),
            'kind':     'incl' if s in STRATA_INCLUDED else 'excl',
        })
    return out


def _audit_tags_for(stratum: str):
    return AUDIT_TAGS_EXCLUDED if stratum in STRATA_EXCLUDED else AUDIT_TAGS_INCLUDED


def _is_marked(word: str, bmap: dict) -> bool:
    bm = bmap.get(word, {})
    return bool(
        bm.get('bookmarked')
        or (bm.get('note') or '').strip()
        or (bm.get('tags') or '').strip()
    )


def _like_any(col: str, vals: list[str]):
    or_parts = [f"('|'||{col}||'|' LIKE ?)" for _ in vals]
    return '(' + ' OR '.join(or_parts) + ')', [f'%|{v}|%' for v in vals]


def _search_audit(stratum: str, q: str):
    """Render the word list scoped to a single audit-sample stratum.

    Most filter controls are ignored in audit mode — the sample is the unit.
    Only the search box (substring filter) is honored. Labeled words sink to
    the bottom so unlabeled ones are easier to reach.
    """
    sample_words = _audit_sample_words(stratum)
    if not sample_words:
        return render_template(
            'partials/word_list.html',
            words=[], total=0, page=1, page_size=PAGE_SIZE,
            next_page_url=None, suppress_emoji='',
        )

    placeholders = ','.join('?' * len(sample_words))
    sql = f'SELECT * FROM words WHERE word IN ({placeholders})'
    params: list = list(sample_words)
    if q:
        sql += ' AND word LIKE ?'
        params.append(f'%{q}%')

    rows = _words_db.execute(sql, params).fetchall()
    by_word = {r['word']: r for r in rows}

    bmap = _bookmarks_map()

    def is_labeled(w: str) -> bool:
        tags = (bmap.get(w, {}).get('tags') or '')
        return any(t.strip() in AUDIT_TAG_NAMES for t in tags.split(','))

    # Order: unlabeled first (in sample order), then labeled, both in sample order
    ordered_words = [w for w in sample_words if w in by_word]
    ordered_words.sort(key=lambda w: (is_labeled(w), sample_words.index(w)))

    words = []
    for w in ordered_words:
        row = by_word[w]
        d = dict(row)
        bm = bmap.get(w, {})
        d['bookmarked'] = bool(bm.get('bookmarked'))
        d['has_note']   = bool((bm.get('note') or '').strip())
        d['tags']       = [t.strip() for t in (bm.get('tags') or '').split(',') if t.strip()]
        d['audit_labeled'] = is_labeled(w)
        words.append(d)

    return render_template(
        'partials/word_list.html',
        words=words,
        total=len(words),
        page=1,
        page_size=len(words) or 1,
        next_page_url=None,
        suppress_emoji='',
        audit_mode=True,
    )


@app.route('/audit/strata')
def audit_strata():
    return render_template('partials/audit_strata.html',
                           progress=_audit_progress(),
                           current=request.args.get('stratum', '').strip())


@app.route('/search')
def search():
    audit_mode = _is_audit(request)
    stratum    = request.args.get('stratum', '').strip()
    q          = request.args.get('q', '').strip()

    if audit_mode and stratum in set(STRATA_ORDER):
        return _search_audit(stratum, q)

    word_tier       = request.args.get('word_tier', 'forgotten').strip()
    verdict         = request.args.get('verdict', '').strip()
    tier            = request.args.get('tier', '').strip()
    register        = request.args.get('register', '').strip()
    domain          = request.args.get('domain', '').strip()
    etym            = request.args.get('etymology', '').strip()
    pos             = request.args.get('pos', '').strip()
    has_def = request.args.get('has_def', '').strip()
    marks   = request.args.get('marks', 'all').strip()
    sort            = request.args.get('sort', '').strip()
    page   = max(1, int(request.args.get('page', 1) or 1))
    offset = (page - 1) * PAGE_SIZE

    conditions: list[str] = ['word_tier = ?']
    params: list = [word_tier if word_tier in ('forgotten', 'rare_in_use') else 'forgotten']
    if q:
        conditions.append('word LIKE ?')
        params.append(f'%{q}%')
    if verdict:
        conditions.append('verdict = ?')
        params.append(verdict)
    if tier:
        conditions.append('confidence_tier = ?')
        params.append(tier)
    # pipe-separated columns: match the selected value anywhere in the field
    for col, val in [('dex_register', register), ('dex_domain', domain),
                     ('dex_etymology', etym), ('dex_pos', pos)]:
        if val:
            conditions.append(f"('|'||{col}||'|' LIKE ?)")
            params.append(f'%|{val}|%')
    if has_def == '1':
        conditions.append('definition IS NOT NULL')
    elif has_def == '0':
        conditions.append('definition IS NULL')

    where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''
    order_by = SORT_OPTIONS.get(sort, SORT_OPTIONS['rare'])
    bmap = _bookmarks_map()

    all_rows = _words_db.execute(
        f'SELECT * FROM words {where} ORDER BY {order_by}', params
    ).fetchall()

    if marks == 'unmarked':
        all_rows = [r for r in all_rows if not _is_marked(r['word'], bmap)]
    elif marks == 'marked':
        all_rows = [r for r in all_rows if _is_marked(r['word'], bmap)]
    elif marks == 'bookmarked':
        all_rows = [r for r in all_rows if bmap.get(r['word'], {}).get('bookmarked')]
    elif marks == 'noted':
        all_rows = [r for r in all_rows
                    if (bmap.get(r['word'], {}).get('note') or '').strip()]
    elif marks.startswith('tag:') and marks[4:].strip():
        tag_filter = marks[4:].strip()
        all_rows = [r for r in all_rows
                    if tag_filter in [t.strip() for t in
                                      (bmap.get(r['word'], {}).get('tags') or '').split(',')
                                      if t.strip()]]
    # marks == 'all' or unrecognised → no filtering

    total = len(all_rows)
    page_rows = all_rows[offset: offset + PAGE_SIZE]

    words = []
    for r in page_rows:
        d = dict(r)
        bm = bmap.get(r['word'], {})
        d['bookmarked'] = bool(bm.get('bookmarked'))
        d['has_note']   = bool((bm.get('note') or '').strip())
        d['tags']       = [t.strip() for t in (bm.get('tags') or '').split(',') if t.strip()]
        words.append(d)

    next_page_url = None
    if page * PAGE_SIZE < total:
        args = dict(request.args)
        args['page'] = str(page + 1)
        next_page_url = '/search?' + urlencode(args, doseq=True)

    if marks == 'bookmarked':
        suppress_emoji = '⭐'
    elif marks == 'noted':
        suppress_emoji = '📝'
    elif marks.startswith('tag:') and marks[4:].strip():
        suppress_emoji = QUICK_TAG_EMOJIS.get(marks[4:].strip(), '🏷️')
    else:
        suppress_emoji = ''

    return render_template(
        'partials/word_list.html',
        words=words,
        total=total,
        page=page,
        page_size=PAGE_SIZE,
        next_page_url=next_page_url,
        suppress_emoji=suppress_emoji,
    )


def _all_used_tags() -> list[str]:
    rows = _research_db.execute(
        "SELECT tags FROM bookmarks WHERE tags IS NOT NULL AND tags != ''"
    ).fetchall()
    seen: set[str] = set()
    for r in rows:
        for t in (r['tags'] or '').split(','):
            t = t.strip()
            if t and t not in QUICK_TAG_NAMES and not t.startswith('audit:'):
                seen.add(t)
    return sorted(seen)


@app.route('/')
def index():
    audit_mode = _is_audit(request)
    total  = _words_db.execute("SELECT COUNT(*) FROM words WHERE word_tier='forgotten'").fetchone()[0]
    bcount = _research_db.execute('SELECT COUNT(*) FROM bookmarks WHERE bookmarked=1').fetchone()[0]
    return render_template('base.html',
        total=total,
        bookmark_count=bcount,
        pos_options          = POS_OPTIONS,
        distinct_registers   = _distinct_split('dex_register'),
        distinct_domains     = _distinct_split('dex_domain'),
        distinct_etymologies = _distinct_split('dex_etymology', exclude=_ETYM_JUNK),
        tag_suggestions      = _all_used_tags(),
        quick_tags           = QUICK_TAGS,
        audit_mode           = audit_mode,
        audit_progress       = _audit_progress() if audit_mode else [],
    )


@app.route('/word/<word>')
def word_detail(word: str):
    row = _words_db.execute(
        'SELECT * FROM words WHERE word = ?', (word,)
    ).fetchone()
    if row is None:
        return 'Not found', 404
    bm = _research_db.execute(
        'SELECT * FROM bookmarks WHERE word = ?', (word,)
    ).fetchone()
    w = dict(row)
    w['bookmarked'] = bool(bm and bm['bookmarked'])
    w['note'] = (bm and bm['note']) or ''
    w['tags'] = [t.strip() for t in ((bm and bm['tags']) or '').split(',') if t.strip()]

    audit_mode = _is_audit(request)
    audit_tags = None
    if audit_mode:
        stratum_row = _research_db.execute(
            'SELECT stratum FROM audit_sample WHERE word = ?', (word,)
        ).fetchone()
        if stratum_row:
            audit_tags = _audit_tags_for(stratum_row['stratum'])

    return render_template(
        'partials/detail.html',
        w=w,
        quick_tags=QUICK_TAGS,
        audit_mode=audit_mode,
        audit_tags=audit_tags,
    )


@app.route('/bookmark/<word>', methods=['POST'])
def bookmark(word: str):
    exists = _words_db.execute(
        'SELECT 1 FROM words WHERE word = ?', (word,)
    ).fetchone()
    if not exists:
        return 'Not found', 404

    current = _research_db.execute(
        'SELECT bookmarked FROM bookmarks WHERE word = ?', (word,)
    ).fetchone()
    new_val = 0 if (current and current['bookmarked']) else 1
    now = _now()

    if current is None:
        _research_db.execute(
            'INSERT INTO bookmarks (word, bookmarked, created_at, updated_at) VALUES (?,?,?,?)',
            (word, new_val, now, now),
        )
    else:
        _research_db.execute(
            'UPDATE bookmarks SET bookmarked=?, updated_at=? WHERE word=?',
            (new_val, now, word),
        )
    _research_db.commit()

    return render_template(
        'partials/bookmark_btn.html',
        word=word,
        bookmarked=bool(new_val),
    )


@app.route('/note/<word>', methods=['POST'])
def save_note(word: str):
    exists = _words_db.execute(
        'SELECT 1 FROM words WHERE word = ?', (word,)
    ).fetchone()
    if not exists:
        return 'Not found', 404

    note = request.form.get('note', '')
    now = _now()
    current = _research_db.execute(
        'SELECT 1 FROM bookmarks WHERE word = ?', (word,)
    ).fetchone()

    if current is None:
        _research_db.execute(
            'INSERT INTO bookmarks (word, note, created_at, updated_at) VALUES (?,?,?,?)',
            (word, note, now, now),
        )
    else:
        _research_db.execute(
            'UPDATE bookmarks SET note=?, updated_at=? WHERE word=?',
            (note, now, word),
        )
    _research_db.commit()
    return render_template('partials/note_status.html')


def _get_tags(word: str) -> list[str]:
    row = _research_db.execute(
        'SELECT tags FROM bookmarks WHERE word = ?', (word,)
    ).fetchone()
    if not row or not row['tags']:
        return []
    return [t.strip() for t in row['tags'].split(',') if t.strip()]


def _set_tags(word: str, tags: list[str]) -> None:
    now = _now()
    current = _research_db.execute(
        'SELECT 1 FROM bookmarks WHERE word = ?', (word,)
    ).fetchone()
    tag_str = ','.join(tags)
    if current is None:
        _research_db.execute(
            'INSERT INTO bookmarks (word, tags, created_at, updated_at) VALUES (?,?,?,?)',
            (word, tag_str, now, now),
        )
    else:
        _research_db.execute(
            'UPDATE bookmarks SET tags=?, updated_at=? WHERE word=?',
            (tag_str, now, word),
        )
    _research_db.commit()


def _render_tags_row(word: str, tags: list[str]):
    return render_template(
        'partials/tags_row.html', word=word, tags=tags, quick_tags=QUICK_TAGS
    )


@app.route('/tag/<word>', methods=['POST'])
def add_tag(word: str):
    if not _words_db.execute('SELECT 1 FROM words WHERE word=?', (word,)).fetchone():
        return 'Not found', 404
    tag = request.form.get('tag', '').strip()
    if not tag:
        return 'Bad request', 400
    tags = _get_tags(word)
    if tag not in tags:
        tags.append(tag)
    _set_tags(word, tags)
    return _render_tags_row(word, tags)


@app.route('/tag/<word>/<tag>', methods=['DELETE'])
def remove_tag(word: str, tag: str):
    if not _words_db.execute('SELECT 1 FROM words WHERE word=?', (word,)).fetchone():
        return 'Not found', 404
    tags = [t for t in _get_tags(word) if t != tag]
    _set_tags(word, tags)
    return _render_tags_row(word, tags)


@app.route('/tag/<word>/toggle/<tag>', methods=['POST'])
def toggle_tag(word: str, tag: str):
    if not _words_db.execute('SELECT 1 FROM words WHERE word=?', (word,)).fetchone():
        return 'Not found', 404
    tag = tag.strip()
    if not tag:
        return 'Bad request', 400
    tags = _get_tags(word)
    if tag in tags:
        tags = [t for t in tags if t != tag]
    else:
        tags.append(tag)
    _set_tags(word, tags)
    return _render_tags_row(word, tags)


@app.route('/tags/suggest')
def tags_suggest():
    return render_template('partials/tag_options.html', options=_all_used_tags())


@app.route('/metodologie')
def metodologie():
    return render_template('metodologie.html')


if __name__ == '__main__':
    init_app()
    app.run(debug=True, port=5000)
