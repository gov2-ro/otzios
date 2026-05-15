# Oțios Research UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a keyboard-driven local Flask+HTMX web app for exploring the Romanian forgotten-words shortlist, with search/filter, word detail, and bookmark/note/tag functionality.

**Architecture:** Flask serves server-rendered HTML fragments; HTMX swaps them in without page reloads. Two SQLite databases: an in-memory `words` table (merged from both CSVs at startup) and a file-backed `data/research.db` for user bookmarks/notes/tags.

**Tech Stack:** Python 3, Flask, HTMX 2.x (CDN), Jinja2, SQLite3 (stdlib), pytest

---

## File map

| File | Role |
|------|------|
| `ui/app.py` | Flask app — all routes, DB init, helper functions |
| `ui/templates/base.html` | Shell layout: filter bar, two-column body, status bar, keyboard JS, CSS |
| `ui/templates/partials/word_list.html` | `#word-list` fragment — list of word rows |
| `ui/templates/partials/word_row.html` | Single word row (included by word_list) |
| `ui/templates/partials/detail.html` | `#detail-panel` fragment — full word detail + actions |
| `ui/templates/partials/bookmark_btn.html` | `#bookmark-btn` fragment — bookmark toggle button |
| `ui/templates/partials/tags_row.html` | `#tags-row` fragment — tag pills + add input |
| `ui/templates/partials/note_status.html` | `#note-status` fragment — "saved ✓" confirmation |
| `tests/test_ui.py` | All route + DB tests |
| `requirements.txt` | Add `flask` |
| `.gitignore` or `data/` gitignore | Add `data/research.db` |

---

## Task 1: Setup — add Flask, scaffold dirs, write design doc

**Files:**
- Modify: `requirements.txt`
- Create: `ui/` directory tree
- Create: `tests/test_ui.py` (stub)
- Already done: `docs/superpowers/specs/2026-05-15-research-ui-design.md`

- [ ] **Step 1: Add flask to requirements.txt**

Append to `requirements.txt`:
```
# Research UI
flask
```

- [ ] **Step 2: Install flask into the active venv**

```bash
source ~/g2-dev/monitorulpreturilor/venv/bin/activate
pip install flask
```
Expected: `Successfully installed flask-...`

- [ ] **Step 3: Create directory structure**

```bash
mkdir -p ui/templates/partials tests
touch ui/__init__.py
touch ui/templates/base.html
touch ui/templates/partials/word_list.html
touch ui/templates/partials/word_row.html
touch ui/templates/partials/detail.html
touch ui/templates/partials/bookmark_btn.html
touch ui/templates/partials/tags_row.html
touch ui/templates/partials/note_status.html
touch tests/__init__.py
touch tests/test_ui.py
```

- [ ] **Step 4: Add research.db to gitignore**

Open `.gitignore` (or create it) and verify this line is present (the existing `data/*` rule already covers it — confirm):
```bash
grep 'data/\*\|research\.db' .gitignore
```
If neither matches, add:
```
data/research.db
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt ui/ tests/ docs/superpowers/
git commit -m "feat(ui): scaffold Flask+HTMX research UI"
```

---

## Task 2: DB init — load CSVs, open research.db

**Files:**
- Create: `ui/app.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing tests for DB init**

Write `tests/test_ui.py`:
```python
import csv
import pytest
import sqlite3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'ui'))

import app as ui_app


SHORTLIST_COLS = [
    'word', 'dex_frequency', 'verdict', 'confidence_tier',
    'log_ratio', 'hist_ppm', 'modern_ppm', 'dex_pos',
    'dex_register', 'dex_domain', 'dex_etymology', 'is_forgotten',
]
WEB_COLS = [
    'word', 'total_results', 'in_wild', 'web_score',
    'top_url', 'last_seen_approx', 'provider',
]


def make_shortlist(path: Path, rows: list[dict]) -> None:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=SHORTLIST_COLS)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def make_web(path: Path, rows: list[dict]) -> None:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=WEB_COLS)
        w.writeheader()
        for row in rows:
            w.writerow(row)


WORD_A = {
    'word': 'acătării', 'dex_frequency': '0.1', 'verdict': 'extinct',
    'confidence_tier': 'A', 'log_ratio': '-5.2', 'hist_ppm': '12.4',
    'modern_ppm': '0.0', 'dex_pos': 's.f.', 'dex_register': 'înv.',
    'dex_domain': '', 'dex_etymology': 'slavă', 'is_forgotten': '1',
}
WORD_B = {
    'word': 'adăsta', 'dex_frequency': '0.2', 'verdict': 'declining',
    'confidence_tier': 'A', 'log_ratio': '-3.1', 'hist_ppm': '8.0',
    'modern_ppm': '0.1', 'dex_pos': 'vb.', 'dex_register': '',
    'dex_domain': '', 'dex_etymology': '', 'is_forgotten': '1',
}
WEB_A = {
    'word': 'acătării', 'total_results': '0', 'in_wild': '0',
    'web_score': '0', 'top_url': '', 'last_seen_approx': '', 'provider': 'google',
}


@pytest.fixture()
def dbs(tmp_path):
    shortlist = tmp_path / 'shortlist.csv'
    web = tmp_path / 'web.csv'
    research = tmp_path / 'research.db'
    make_shortlist(shortlist, [WORD_A, WORD_B])
    make_web(web, [WEB_A])
    words_db = ui_app.load_words(shortlist, web)
    res_db = ui_app.open_research_db(research)
    return words_db, res_db


def test_load_words_count(dbs):
    words_db, _ = dbs
    count = words_db.execute('SELECT COUNT(*) FROM words').fetchone()[0]
    assert count == 2


def test_load_words_web_merge(dbs):
    words_db, _ = dbs
    row = words_db.execute(
        "SELECT provider, in_wild FROM words WHERE word = 'acătării'"
    ).fetchone()
    assert row['provider'] == 'google'
    assert row['in_wild'] == 0


def test_load_words_no_web_data(dbs):
    words_db, _ = dbs
    row = words_db.execute(
        "SELECT provider FROM words WHERE word = 'adăsta'"
    ).fetchone()
    assert row['provider'] is None


def test_open_research_db_creates_table(dbs):
    _, res_db = dbs
    tables = res_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    names = [t['name'] for t in tables]
    assert 'bookmarks' in names
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
cd /Users/pax/devbox/otios
source ~/g2-dev/monitorulpreturilor/venv/bin/activate
pytest tests/test_ui.py -v
```
Expected: `ImportError: No module named 'app'` or `AttributeError: module 'app' has no attribute 'load_words'`

- [ ] **Step 3: Write ui/app.py with DB init**

Create `ui/app.py`:
```python
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
            web_score        INTEGER,
            top_url          TEXT,
            last_seen_approx TEXT,
            provider         TEXT
        )
    """)

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
                    _int(row.get('is_forgotten', '')),
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
                        _int(row.get('in_wild', '')),
                        _int(row.get('web_score', '')),
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


if __name__ == '__main__':
    init_app()
    app.run(debug=True, port=5000)
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_ui.py -v
```
Expected:
```
test_ui.py::test_load_words_count PASSED
test_ui.py::test_load_words_web_merge PASSED
test_ui.py::test_load_words_no_web_data PASSED
test_ui.py::test_open_research_db_creates_table PASSED
```

- [ ] **Step 5: Commit**

```bash
git add ui/app.py tests/test_ui.py
git commit -m "feat(ui): DB init — load CSVs into memory, open research.db"
```

---

## Task 3: Shell route GET / + base.html

**Files:**
- Modify: `ui/app.py` (add route + fixture for testing)
- Modify: `tests/test_ui.py` (add client fixture + shell test)
- Create: `ui/templates/base.html`

- [ ] **Step 1: Write failing test**

Append to `tests/test_ui.py`:
```python
@pytest.fixture()
def client(dbs, tmp_path):
    words_db, res_db = dbs
    ui_app._words_db = words_db
    ui_app._research_db = res_db
    ui_app.app.config['TESTING'] = True
    with ui_app.app.test_client() as c:
        yield c


def test_index_returns_200(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'Search' in resp.data
    assert b'word-list' in resp.data
    assert b'detail-panel' in resp.data
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
pytest tests/test_ui.py::test_index_returns_200 -v
```
Expected: `FAILED` — `404` or template not found.

- [ ] **Step 3: Add index route to ui/app.py**

Add after `_now()` function, before `if __name__ == '__main__':`:
```python
@app.route('/')
def index():
    total = _words_db.execute('SELECT COUNT(*) FROM words').fetchone()[0]
    bcount = _research_db.execute(
        'SELECT COUNT(*) FROM bookmarks WHERE bookmarked=1'
    ).fetchone()[0]
    return render_template('base.html', total=total, bookmark_count=bcount)
```

- [ ] **Step 4: Write ui/templates/base.html**

```html
<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="utf-8">
  <title>Oțios Research</title>
  <script src="https://unpkg.com/htmx.org@2.0.4" integrity="sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+" crossorigin="anonymous"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: monospace; height: 100vh; display: flex; flex-direction: column; background: #1a1a1a; color: #e0e0e0; font-size: 14px; }

    /* Filter bar */
    #filter-form { display: flex; gap: 8px; padding: 6px 12px; background: #111; border-bottom: 1px solid #333; align-items: center; flex-shrink: 0; }
    #search { flex: 1; background: #222; border: 1px solid #444; color: #e0e0e0; padding: 4px 8px; font-family: monospace; font-size: 13px; }
    #search:focus { outline: 1px solid #4a8fd4; border-color: #4a8fd4; }
    select { background: #222; border: 1px solid #444; color: #e0e0e0; padding: 4px 6px; font-family: monospace; font-size: 13px; cursor: pointer; }
    label.bookmark-filter { display: flex; align-items: center; gap: 4px; cursor: pointer; color: #aaa; font-size: 13px; white-space: nowrap; }

    /* Two-column body */
    #app { display: flex; flex: 1; overflow: hidden; }
    #word-list-container { width: 260px; border-right: 1px solid #333; overflow-y: auto; flex-shrink: 0; }
    #word-list { display: flex; flex-direction: column; }
    #detail-panel { flex: 1; overflow-y: auto; padding: 20px; }

    /* Word rows */
    .word-row { display: flex; justify-content: space-between; align-items: center; padding: 5px 10px; cursor: pointer; border-bottom: 1px solid #1f1f1f; gap: 6px; }
    .word-row:hover { background: #242424; }
    .word-row[data-selected] { background: #1a3050; }
    .word-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .word-row.bookmarked .word-text { color: #f0c040; }
    .star { color: #f0c040; font-size: 11px; }

    /* Verdict badges */
    .verdict-badge { font-size: 11px; padding: 1px 5px; border-radius: 3px; white-space: nowrap; flex-shrink: 0; }
    .verdict-extinct { background: #5c1a1a; color: #ff9090; }
    .verdict-declining { background: #3a2800; color: #ffb840; }
    .verdict-historical_only { background: #1a2a3a; color: #80b0ff; }
    .verdict-absent { background: #2a1a3a; color: #c080ff; }
    .verdict-unknown { background: #262626; color: #888; }

    /* Detail panel */
    #detail-panel h2 { font-size: 1.3em; margin-bottom: 14px; letter-spacing: 0.02em; }
    #detail-panel hr { border: none; border-top: 1px solid #2a2a2a; margin: 12px 0; }
    .detail-table { width: 100%; border-collapse: collapse; margin-bottom: 4px; }
    .detail-table th { text-align: right; padding: 3px 12px 3px 0; color: #666; width: 110px; font-weight: normal; vertical-align: top; }
    .detail-table td { color: #d0d0d0; }
    .detail-table a { color: #4a8fd4; text-decoration: none; }
    .placeholder { color: #555; padding: 20px 0; }

    /* Actions */
    .actions { display: flex; gap: 8px; align-items: flex-start; flex-wrap: wrap; margin-bottom: 10px; }
    #bookmark-btn { background: #222; border: 1px solid #444; color: #e0e0e0; padding: 4px 10px; cursor: pointer; font-family: monospace; font-size: 13px; }
    #bookmark-btn:hover { background: #2a2a2a; border-color: #666; }

    /* Tags */
    #tags-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
    .tag { background: #2a2a2a; border: 1px solid #3a3a3a; padding: 2px 7px; font-size: 12px; display: inline-flex; align-items: center; gap: 4px; border-radius: 2px; }
    .tag button { background: none; border: none; color: #666; cursor: pointer; padding: 0; font-size: 11px; line-height: 1; }
    .tag button:hover { color: #ccc; }
    #tag-input { background: #1a1a1a; border: 1px solid #333; color: #e0e0e0; padding: 2px 6px; font-family: monospace; font-size: 12px; width: 90px; }
    #tag-input:focus { outline: 1px solid #4a4a4a; }

    /* Note */
    .note-section { margin-top: 14px; }
    .note-section label { display: block; color: #666; margin-bottom: 4px; font-size: 12px; }
    #note-input { width: 100%; background: #1f1f1f; border: 1px solid #2f2f2f; color: #d0d0d0; padding: 8px; font-family: monospace; font-size: 13px; min-height: 60px; resize: vertical; }
    #note-input:focus { outline: 1px solid #3a3a3a; border-color: #3a3a3a; }
    #note-status { display: inline-block; margin-top: 4px; font-size: 12px; color: #70a870; min-height: 16px; }
    @keyframes fadeout { 0% { opacity: 1; } 80% { opacity: 1; } 100% { opacity: 0; } }
    .saved-notice { animation: fadeout 2s ease-in forwards; }

    /* Status bar */
    #status-bar { padding: 3px 12px; background: #0e0e0e; border-top: 1px solid #282828; font-size: 11px; color: #555; flex-shrink: 0; }

    /* HTMX loading indicator */
    .htmx-indicator { opacity: 0; transition: opacity 200ms; }
    .htmx-request .htmx-indicator { opacity: 1; }
  </style>
</head>
<body>
  <form id="filter-form">
    <input id="search" type="text" name="q" placeholder="/ to search..."
           hx-get="/search"
           hx-trigger="input changed delay:200ms"
           hx-target="#word-list"
           hx-include="#filter-form"
           autocomplete="off">
    <select name="verdict"
            hx-get="/search"
            hx-trigger="change"
            hx-target="#word-list"
            hx-include="#filter-form">
      <option value="">all verdicts</option>
      <option value="extinct">extinct</option>
      <option value="declining">declining</option>
      <option value="historical_only">historical only</option>
      <option value="absent">absent</option>
    </select>
    <select name="tier"
            hx-get="/search"
            hx-trigger="change"
            hx-target="#word-list"
            hx-include="#filter-form">
      <option value="">all tiers</option>
      <option value="A">Tier A</option>
      <option value="B">Tier B</option>
    </select>
    <label class="bookmark-filter">
      <input type="checkbox" name="bookmarked" value="1"
             hx-get="/search"
             hx-trigger="change"
             hx-target="#word-list"
             hx-include="#filter-form">
      ☆ bookmarked
    </label>
  </form>

  <div id="app">
    <div id="word-list-container">
      <div id="word-list"
           hx-get="/search"
           hx-trigger="load"
           hx-swap="innerHTML">
        <span class="htmx-indicator">loading…</span>
      </div>
    </div>
    <div id="detail-panel">
      <p class="placeholder">Select a word to see details.</p>
    </div>
  </div>

  <div id="status-bar">
    {{ total }} words · {{ bookmark_count }} bookmarked · j/k navigate · / search · b bookmark · n note
  </div>

  <script>
    let selectedIdx = -1;
    let gPressed = false;

    function rows() {
      return Array.from(document.querySelectorAll('.word-row'));
    }

    function selectRow(idx) {
      const all = rows();
      if (all.length === 0) return;
      selectedIdx = Math.max(0, Math.min(idx, all.length - 1));
      all.forEach(r => r.removeAttribute('data-selected'));
      const r = all[selectedIdx];
      if (r) {
        r.setAttribute('data-selected', '');
        r.scrollIntoView({ block: 'nearest' });
        r.click();
      }
    }

    document.addEventListener('keydown', function(e) {
      const tag = document.activeElement.tagName;
      const inInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';

      if (inInput) {
        if (e.key === 'Escape') { document.activeElement.blur(); }
        return;
      }

      if (e.key === '/') {
        e.preventDefault();
        document.getElementById('search').focus();
        return;
      }

      if (e.key === 'j' || e.key === 'ArrowDown') {
        e.preventDefault();
        selectRow(selectedIdx + 1);
        gPressed = false;
        return;
      }
      if (e.key === 'k' || e.key === 'ArrowUp') {
        e.preventDefault();
        selectRow(selectedIdx - 1);
        gPressed = false;
        return;
      }
      if (e.key === 'G') {
        e.preventDefault();
        selectRow(rows().length - 1);
        gPressed = false;
        return;
      }
      if (e.key === 'g') {
        if (gPressed) { selectRow(0); gPressed = false; }
        else { gPressed = true; setTimeout(() => { gPressed = false; }, 400); }
        return;
      }
      if (e.key === 'b') {
        const btn = document.getElementById('bookmark-btn');
        if (btn) { e.preventDefault(); btn.click(); }
        return;
      }
      if (e.key === 'n') {
        const note = document.getElementById('note-input');
        if (note) { e.preventDefault(); note.focus(); }
        return;
      }
    });

    document.body.addEventListener('htmx:afterSwap', function(e) {
      if (e.detail.target.id === 'word-list') {
        selectedIdx = -1;
      }
    });
  </script>
</body>
</html>
```

- [ ] **Step 5: Run test — confirm it passes**

```bash
pytest tests/test_ui.py::test_index_returns_200 -v
```
Expected: `PASSED`

- [ ] **Step 6: Commit**

```bash
git add ui/app.py ui/templates/base.html tests/test_ui.py
git commit -m "feat(ui): shell route and base layout"
```

---

## Task 4: Search route GET /search

**Files:**
- Modify: `ui/app.py`
- Modify: `tests/test_ui.py`
- Create: `ui/templates/partials/word_list.html`
- Create: `ui/templates/partials/word_row.html`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ui.py`:
```python
def test_search_returns_all_words(client):
    resp = client.get('/search')
    assert resp.status_code == 200
    assert b'acătării' in resp.data
    assert b'adăsta' in resp.data


def test_search_filters_by_query(client):
    resp = client.get('/search?q=acăt')
    assert b'acătării' in resp.data
    assert b'adăsta' not in resp.data


def test_search_filters_by_verdict(client):
    resp = client.get('/search?verdict=extinct')
    assert b'acătării' in resp.data
    assert b'adăsta' not in resp.data


def test_search_filters_by_bookmarked(client):
    # bookmark acătării
    client.post('/bookmark/acătării')
    resp = client.get('/search?bookmarked=1')
    assert b'acătării' in resp.data
    assert b'adăsta' not in resp.data
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_ui.py::test_search_returns_all_words -v
```
Expected: `FAILED` — 404

- [ ] **Step 3: Add search route to ui/app.py**

Add after the index route:
```python
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
```

Remove the placeholder `_get_words_with_bookmarks` and `_count_words` stubs entirely. The above is the final implementation.

- [ ] **Step 4: Write ui/templates/partials/word_list.html**

```html
{% for w in words %}
  {% include 'partials/word_row.html' %}
{% endfor %}
{% if not words %}
<p style="color:#555;padding:12px;">No words match.</p>
{% endif %}
```

- [ ] **Step 5: Write ui/templates/partials/word_row.html**

```html
<div class="word-row{% if w.bookmarked %} bookmarked{% endif %}"
     hx-get="/word/{{ w.word | urlencode }}"
     hx-target="#detail-panel"
     hx-swap="innerHTML">
  <span class="word-text">{{ w.word }}</span>
  <span class="verdict-badge verdict-{{ (w.verdict or 'unknown') | replace(' ', '_') }}">{{ w.verdict or '—' }}</span>
  {% if w.bookmarked %}<span class="star">★</span>{% endif %}
</div>
```

- [ ] **Step 6: Run tests — confirm they pass**

```bash
pytest tests/test_ui.py -k "search" -v
```
Expected: all 4 search tests PASSED.

- [ ] **Step 7: Commit**

```bash
git add ui/app.py ui/templates/partials/word_list.html ui/templates/partials/word_row.html tests/test_ui.py
git commit -m "feat(ui): search route with filter, pagination, bookmark filter"
```

---

## Task 5: Detail route GET /word/\<word\>

**Files:**
- Modify: `ui/app.py`
- Modify: `tests/test_ui.py`
- Create: `ui/templates/partials/detail.html`

- [ ] **Step 1: Write failing test**

Append to `tests/test_ui.py`:
```python
def test_word_detail_returns_fragment(client):
    resp = client.get('/word/acătării')
    assert resp.status_code == 200
    assert 'acătării'.encode() in resp.data
    assert b'extinct' in resp.data
    assert b's.f.' in resp.data


def test_word_detail_missing_returns_404(client):
    resp = client.get('/word/nonexistent')
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_ui.py::test_word_detail_returns_fragment tests/test_ui.py::test_word_detail_missing_returns_404 -v
```
Expected: `FAILED` — 404

- [ ] **Step 3: Add detail route to ui/app.py**

Add after the search route:
```python
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
```

- [ ] **Step 4: Write ui/templates/partials/detail.html**

```html
<h2>{{ w.word }}</h2>

<table class="detail-table">
  <tr><th>verdict</th><td><span class="verdict-badge verdict-{{ (w.verdict or 'unknown') | replace(' ', '_') }}">{{ w.verdict or '—' }}</span></td></tr>
  <tr><th>tier</th><td>{{ w.confidence_tier or '—' }}</td></tr>
  <tr><th>POS</th><td>{{ w.dex_pos or '—' }}</td></tr>
  <tr><th>register</th><td>{{ w.dex_register or '—' }}</td></tr>
  <tr><th>domain</th><td>{{ w.dex_domain or '—' }}</td></tr>
  <tr><th>etymology</th><td>{{ w.dex_etymology or '—' }}</td></tr>
</table>

<hr>

<table class="detail-table">
  <tr><th>hist_ppm</th><td>{{ "%.2f" | format(w.hist_ppm) if w.hist_ppm is not none else '—' }}</td></tr>
  <tr><th>modern_ppm</th><td>{{ "%.2f" | format(w.modern_ppm) if w.modern_ppm is not none else '—' }}</td></tr>
  <tr><th>log_ratio</th><td>{{ "%.2f" | format(w.log_ratio) if w.log_ratio is not none else '—' }}</td></tr>
  <tr><th>dex_freq</th><td>{{ "%.3f" | format(w.dex_frequency) if w.dex_frequency is not none else '—' }}</td></tr>
</table>

{% if w.provider %}
<hr>
<table class="detail-table">
  <tr><th>web</th><td>{% if w.in_wild %}✓ found{% else %}✗ not found{% endif %} ({{ w.provider }})</td></tr>
  <tr><th>results</th><td>{{ w.total_results }}</td></tr>
  {% if w.last_seen_approx %}<tr><th>last seen</th><td>{{ w.last_seen_approx }}</td></tr>{% endif %}
  {% if w.top_url %}<tr><th>top URL</th><td><a href="{{ w.top_url }}" target="_blank" rel="noopener">{{ w.top_url[:60] }}{% if w.top_url|length > 60 %}…{% endif %}</a></td></tr>{% endif %}
</table>
{% endif %}

<hr>

<div class="actions">
  {% set word = w.word %}
  {% set bookmarked = w.bookmarked %}
  {% include 'partials/bookmark_btn.html' %}
  {% set tags = w.tags %}
  {% include 'partials/tags_row.html' %}
</div>

<div class="note-section">
  <label for="note-input">note (Enter to save)</label>
  <textarea id="note-input" name="note"
            hx-post="/note/{{ w.word | urlencode }}"
            hx-trigger="keydown[key=='Enter'] consume"
            hx-target="#note-status"
            hx-swap="innerHTML">{{ w.note }}</textarea>
  <div id="note-status"></div>
</div>
```

- [ ] **Step 5: Write placeholder partials (needed for detail.html to render)**

`ui/templates/partials/bookmark_btn.html`:
```html
<button id="bookmark-btn"
        hx-post="/bookmark/{{ word | urlencode }}"
        hx-target="#bookmark-btn"
        hx-swap="outerHTML">
  {% if bookmarked %}★ bookmarked{% else %}☆ bookmark{% endif %}
</button>
```

`ui/templates/partials/tags_row.html`:
```html
<div id="tags-row">
  {% for tag in tags %}
  <span class="tag">{{ tag }}
    <button hx-delete="/tag/{{ word | urlencode }}/{{ tag | urlencode }}"
            hx-target="#tags-row"
            hx-swap="outerHTML">×</button>
  </span>
  {% endfor %}
  <input id="tag-input" type="text" name="tag" placeholder="add tag…"
         hx-post="/tag/{{ word | urlencode }}"
         hx-trigger="keydown[key=='Enter'] consume"
         hx-target="#tags-row"
         hx-swap="outerHTML"
         hx-include="#tag-input">
</div>
```

`ui/templates/partials/note_status.html`:
```html
<span class="saved-notice">saved ✓</span>
```

- [ ] **Step 6: Run tests — confirm they pass**

```bash
pytest tests/test_ui.py::test_word_detail_returns_fragment tests/test_ui.py::test_word_detail_missing_returns_404 -v
```
Expected: both PASSED.

- [ ] **Step 7: Commit**

```bash
git add ui/app.py ui/templates/partials/ tests/test_ui.py
git commit -m "feat(ui): detail route and fragment templates"
```

---

## Task 6: Bookmark toggle POST /bookmark/\<word\>

**Files:**
- Modify: `ui/app.py`
- Modify: `tests/test_ui.py`

(bookmark_btn.html already written in Task 5)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ui.py`:
```python
def test_bookmark_toggle_on(client):
    resp = client.post('/bookmark/acătării')
    assert resp.status_code == 200
    assert '★'.encode() in resp.data
    row = ui_app._research_db.execute(
        "SELECT bookmarked FROM bookmarks WHERE word='acătării'"
    ).fetchone()
    assert row['bookmarked'] == 1


def test_bookmark_toggle_off(client):
    client.post('/bookmark/acătării')  # on
    resp = client.post('/bookmark/acătării')  # off
    assert '☆'.encode() in resp.data
    row = ui_app._research_db.execute(
        "SELECT bookmarked FROM bookmarks WHERE word='acătării'"
    ).fetchone()
    assert row['bookmarked'] == 0


def test_bookmark_missing_word_returns_404(client):
    resp = client.post('/bookmark/doesnotexist')
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_ui.py -k "bookmark" -v
```
Expected: `FAILED` — 404 or 405

- [ ] **Step 3: Add bookmark route to ui/app.py**

Add after the detail route:
```python
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
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_ui.py -k "bookmark" -v
```
Expected: all 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add ui/app.py tests/test_ui.py
git commit -m "feat(ui): bookmark toggle route"
```

---

## Task 7: Note save POST /note/\<word\>

**Files:**
- Modify: `ui/app.py`
- Modify: `tests/test_ui.py`

(note_status.html already written in Task 5)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ui.py`:
```python
def test_note_save(client):
    resp = client.post('/note/acătării', data={'note': 'interesting archaic form'})
    assert resp.status_code == 200
    assert b'saved' in resp.data
    row = ui_app._research_db.execute(
        "SELECT note FROM bookmarks WHERE word='acătării'"
    ).fetchone()
    assert row['note'] == 'interesting archaic form'


def test_note_save_missing_word_returns_404(client):
    resp = client.post('/note/nonexistent', data={'note': 'x'})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_ui.py -k "note" -v
```
Expected: `FAILED` — 404 or 405

- [ ] **Step 3: Add note route to ui/app.py**

Add after the bookmark route:
```python
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
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_ui.py -k "note" -v
```
Expected: both PASSED.

- [ ] **Step 5: Commit**

```bash
git add ui/app.py tests/test_ui.py
git commit -m "feat(ui): note save route"
```

---

## Task 8: Tag add/remove

**Files:**
- Modify: `ui/app.py`
- Modify: `tests/test_ui.py`

(tags_row.html already written in Task 5)

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ui.py`:
```python
def test_tag_add(client):
    resp = client.post('/tag/acătării', data={'tag': 'înv.'})
    assert resp.status_code == 200
    assert 'înv.'.encode() in resp.data
    row = ui_app._research_db.execute(
        "SELECT tags FROM bookmarks WHERE word='acătății'"
    ).fetchone()
    # check via detail route instead — tags_row renders from word context
    resp2 = client.get('/word/acătării')
    assert 'înv.'.encode() in resp2.data


def test_tag_add_duplicate_ignored(client):
    client.post('/tag/acătării', data={'tag': 'înv.'})
    client.post('/tag/acătării', data={'tag': 'înv.'})
    row = ui_app._research_db.execute(
        "SELECT tags FROM bookmarks WHERE word='acătării'"
    ).fetchone()
    tags = [t for t in row['tags'].split(',') if t.strip()]
    assert tags.count('înv.') == 1


def test_tag_remove(client):
    client.post('/tag/acătării', data={'tag': 'înv.'})
    resp = client.delete('/tag/acătării/înv.')
    assert resp.status_code == 200
    assert 'înv.'.encode() not in resp.data
    row = ui_app._research_db.execute(
        "SELECT tags FROM bookmarks WHERE word='acătării'"
    ).fetchone()
    tags = [t for t in (row['tags'] or '').split(',') if t.strip()]
    assert 'înv.' not in tags
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
pytest tests/test_ui.py -k "tag" -v
```
Expected: `FAILED`

- [ ] **Step 3: Add tag routes to ui/app.py**

Add after the note route:
```python
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
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
pytest tests/test_ui.py -k "tag" -v
```
Expected: all 3 PASSED.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/test_ui.py -v
```
Expected: all tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add ui/app.py tests/test_ui.py
git commit -m "feat(ui): tag add/remove routes"
```

---

## Task 9: Manual smoke test

No automated test covers the full browser experience — this must be done manually.

- [ ] **Step 1: Start the server**

```bash
source ~/g2-dev/monitorulpreturilor/venv/bin/activate
cd /Users/pax/devbox/otios
python ui/app.py
```
Expected: `Running on http://127.0.0.1:5000`

- [ ] **Step 2: Open browser and verify layout**

Open `http://localhost:5000`. Confirm:
- Filter bar visible at top
- Word list loads on the left (should show ~16,880 words via HTMX on page load)
- Detail panel shows placeholder text on the right
- Status bar at bottom shows correct word count

- [ ] **Step 3: Test search**

Type in the search box. Confirm the word list updates without a page reload (HTMX working). Try filtering by verdict dropdown.

- [ ] **Step 4: Test detail panel**

Click a word. Confirm detail panel loads with word metadata. Click another word — panel should update in place.

- [ ] **Step 5: Test keyboard navigation**

Press `/` — search should focus. Press `Escape` — focus should return. Press `j`/`k` — selected row should move and detail panel should update. Press `gg` — should jump to top. Press `G` — should jump to bottom.

- [ ] **Step 6: Test bookmark**

Select a word. Press `b` — button should toggle to "★ bookmarked". Press `b` again — should toggle back. Restart the server and confirm the bookmark persisted.

- [ ] **Step 7: Test note**

Select a word. Press `n` — note textarea should focus. Type a note, press `Enter` — "saved ✓" should appear briefly. Restart server, re-select word — note should still be there.

- [ ] **Step 8: Test tag**

In the detail panel, type a tag name in the tag input, press `Enter` — tag pill should appear. Click the `×` on the tag — pill should disappear.

- [ ] **Step 9: Commit smoke test sign-off**

```bash
git commit --allow-empty -m "test(ui): smoke test passed — all interactions verified"
```

---

## Verification summary

```bash
# Run all automated tests
cd /Users/pax/devbox/otios
source ~/g2-dev/monitorulpreturilor/venv/bin/activate
pytest tests/test_ui.py -v

# Start and manually test
python ui/app.py
# open http://localhost:5000
```
