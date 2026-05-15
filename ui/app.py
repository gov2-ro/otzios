import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, render_template, request

app = Flask(__name__)

SHORTLIST_PATH = Path('data/processed/forgotten_words_shortlist.csv')
WEB_PATH = Path('data/processed/diachronic_shortlist_web_validated.csv')
RESEARCH_DB_PATH = Path('data/research.db')
DEFINITIONS_DB_PATH = Path('data/processed/definitions.db')

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
            total_results    INTEGER,
            in_wild          INTEGER,
            web_score        TEXT,
            top_url          TEXT,
            last_seen_approx TEXT,
            provider         TEXT,
            definition       TEXT
        )
    """)

    with open(shortlist_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            conn.execute(
                """INSERT OR IGNORE INTO words
                   (word, dex_frequency, verdict, confidence_tier, log_ratio,
                    hist_ppm, modern_ppm, dex_pos, dex_register, dex_domain,
                    dex_etymology, is_forgotten)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    row['word'],
                    _float(row.get('dex_frequency', '')),
                    row.get('verdict') or None,
                    row.get('confidence_tier') or None,
                    _float(row.get('log_ratio', '')),
                    _float(row.get('hist_ppm', '')),
                    _float(row.get('modern_ppm', '')),
                    row.get('dex_pos') or None,
                    row.get('dex_register') or None,
                    row.get('dex_domain') or None,
                    row.get('dex_etymology') or None,
                    _bool(row.get('is_forgotten', '')),
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
    conn.commit()
    return conn


def init_app(
    shortlist_path: Path | None = None,
    web_path: Path | None = None,
    research_path: Path | None = None,
    definitions_path: Path | None = None,
) -> None:
    global _words_db, _research_db
    _words_db = load_words(
        shortlist_path or SHORTLIST_PATH,
        web_path or WEB_PATH,
        definitions_path or DEFINITIONS_DB_PATH,
    )
    _research_db = open_research_db(research_path or RESEARCH_DB_PATH)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


PAGE_SIZE = 50


def _bookmarks_map() -> dict[str, dict]:
    rows = _research_db.execute('SELECT * FROM bookmarks').fetchall()
    return {r['word']: dict(r) for r in rows}


@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    verdict = request.args.get('verdict', '').strip()
    tier = request.args.get('tier', '').strip()
    bookmarked_only = request.args.get('bookmarked', '') == '1'
    page = max(1, int(request.args.get('page', 1) or 1))
    offset = (page - 1) * PAGE_SIZE

    conditions: list[str] = []
    params: list = []
    if q:
        conditions.append('word LIKE ?')
        params.append(f'%{q}%')
    if verdict:
        conditions.append('verdict = ?')
        params.append(verdict)
    if tier:
        conditions.append('confidence_tier = ?')
        params.append(tier)

    where = ('WHERE ' + ' AND '.join(conditions)) if conditions else ''
    bmap = _bookmarks_map()

    all_rows = _words_db.execute(
        f'SELECT * FROM words {where} ORDER BY word', params
    ).fetchall()

    if bookmarked_only:
        all_rows = [r for r in all_rows if bmap.get(r['word'], {}).get('bookmarked')]

    total = len(all_rows)
    page_rows = all_rows[offset: offset + PAGE_SIZE]

    words = []
    for r in page_rows:
        d = dict(r)
        bm = bmap.get(r['word'], {})
        d['bookmarked'] = bool(bm.get('bookmarked'))
        words.append(d)

    return render_template(
        'partials/word_list.html',
        words=words,
        total=total,
        page=page,
        page_size=PAGE_SIZE,
    )


@app.route('/')
def index():
    total = _words_db.execute('SELECT COUNT(*) FROM words').fetchone()[0]
    bcount = _research_db.execute(
        'SELECT COUNT(*) FROM bookmarks WHERE bookmarked=1'
    ).fetchone()[0]
    return render_template('base.html', total=total, bookmark_count=bcount)


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
    return render_template('partials/detail.html', w=w)


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
    return render_template('partials/tags_row.html', word=word, tags=tags)


@app.route('/tag/<word>/<tag>', methods=['DELETE'])
def remove_tag(word: str, tag: str):
    if not _words_db.execute('SELECT 1 FROM words WHERE word=?', (word,)).fetchone():
        return 'Not found', 404
    tags = [t for t in _get_tags(word) if t != tag]
    _set_tags(word, tags)
    return render_template('partials/tags_row.html', word=word, tags=tags)


if __name__ == '__main__':
    init_app()
    app.run(debug=True, port=5000)
