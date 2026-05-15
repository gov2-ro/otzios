import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, render_template, request

app = Flask(__name__)

SHORTLIST_PATH = Path('data/processed/forgotten_words_shortlist.csv')
WEB_PATH = Path('data/processed/diachronic_shortlist_web_validated.csv')
RESEARCH_DB_PATH = Path('data/research.db')

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


def load_words(shortlist_path: Path, web_path: Path) -> sqlite3.Connection:
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
            provider         TEXT
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
) -> None:
    global _words_db, _research_db
    _words_db = load_words(
        shortlist_path or SHORTLIST_PATH,
        web_path or WEB_PATH,
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


if __name__ == '__main__':
    init_app()
    app.run(debug=True, port=5000)
