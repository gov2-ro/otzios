# UI Enhancements (Definitions, Sort, Shortcuts) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add word definitions from the DEX dump, sortable search results, and a `?` keyboard shortcut popup to the Flask+HTMX research UI.

**Architecture:** Three independent changes. Definitions are extracted once from the 1.2 GB MySQL dump (`extract_definitions.py`) into `data/processed/definitions.db`, then merged into the in-memory `words` table at startup. Sort adds a safe allowlist dict in the search route. The shortcuts popup is pure HTML+CSS+JS in `base.html`.

**Tech Stack:** Flask, HTMX, SQLite, Jinja2, pytest. Venv: `/Users/pax/devbox/envs/240826`.

---

## File Map

| File | Change |
|---|---|
| `extract_definitions.py` | **New** — one-time extraction script |
| `ui/app.py` | Add `DEFINITIONS_DB_PATH`, `definition` column in `load_words()`, `SORT_OPTIONS` + `sort` param in `search()` |
| `ui/templates/base.html` | Add sort `<select>`, definition CSS, shortcuts modal HTML+CSS+JS |
| `ui/templates/partials/detail.html` | Add definition block |
| `tests/test_extract_definitions.py` | **New** — extraction script tests |
| `tests/test_ui.py` | Add tests for definition loading, sort, and definition in detail |

---

## Schema Notes (from actual DEX dump)

**`DefinitionSimple` columns** (col index → name):
- 0: `id` (int, auto-increment)
- 1: `definition` (longtext) — the full definition text
- 2: `lexicon` (varchar 100) — the headword, same format as `Lexeme.formNoAccent` (no stress marks, keeps Romanian diacritics like ă â î ș ț)

The `lexicon` field is the word the definition belongs to. The spec describes cross-referencing via EntryDefinition → Entry → Lexeme, but `DefinitionSimple.lexicon` directly holds the word — no cross-reference needed. First definition per word (lowest id) is used.

---

## Task 1: extract_definitions.py

**Files:**
- Create: `extract_definitions.py`
- Create: `tests/test_extract_definitions.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_extract_definitions.py`:

```python
import sqlite3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import extract_definitions


def test_extract_first_definition_per_word(tmp_path):
    sql = tmp_path / 'test.sql'
    sql.write_text(
        "INSERT INTO `DefinitionSimple` VALUES "
        "(1,'Def of word1','word1',0,0,0,0),"
        "(2,'Second def of word1','word1',0,0,0,0),"
        "(3,'Def of word2','word2',0,0,0,0);\n",
        encoding='utf-8',
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    conn = sqlite3.connect(str(out))
    rows = {r[0]: r[1] for r in conn.execute('SELECT word, definition FROM definitions')}
    conn.close()
    assert rows == {'word1': 'Def of word1', 'word2': 'Def of word2'}


def test_extract_skips_empty_lexicon(tmp_path):
    sql = tmp_path / 'test.sql'
    sql.write_text(
        "INSERT INTO `DefinitionSimple` VALUES "
        "(1,'def','',0,0,0,0),(2,'def2','word2',0,0,0,0);\n",
        encoding='utf-8',
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    conn = sqlite3.connect(str(out))
    count = conn.execute('SELECT COUNT(*) FROM definitions').fetchone()[0]
    conn.close()
    assert count == 1


def test_extract_handles_escaped_quote_in_definition(tmp_path):
    sql = tmp_path / 'test.sql'
    sql.write_text(
        "INSERT INTO `DefinitionSimple` VALUES (1,'It\\'s a test','word1',0,0,0,0);\n",
        encoding='utf-8',
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    conn = sqlite3.connect(str(out))
    row = conn.execute("SELECT definition FROM definitions WHERE word='word1'").fetchone()
    conn.close()
    assert row[0] == "It's a test"


def test_extract_handles_diacritics_in_word(tmp_path):
    sql = tmp_path / 'test.sql'
    sql.write_text(
        "INSERT INTO `DefinitionSimple` VALUES (1,'Vânzătoare.','acătării',0,0,0,0);\n",
        encoding='utf-8',
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    conn = sqlite3.connect(str(out))
    row = conn.execute("SELECT definition FROM definitions WHERE word='acătării'").fetchone()
    conn.close()
    assert row is not None
    assert row[0] == 'Vânzătoare.'
```

- [ ] **Step 2: Run to confirm failure**

```bash
source /Users/pax/devbox/envs/240826/bin/activate
python -m pytest tests/test_extract_definitions.py -v
```
Expected: `ModuleNotFoundError: No module named 'extract_definitions'`

- [ ] **Step 3: Write extract_definitions.py**

`DefinitionSimple` INSERT lines are very long (multi-value, all on one line). The existing `parse_mysql_insert()` in `extract_lexemes.py` uses a regex `r'\(([^)]+)\)'` that breaks when `)` appears inside a quoted string — definition text often contains parentheses. Use the state-machine parser below instead.

Create `extract_definitions.py`:

```python
#!/usr/bin/env python3
"""
Extract first definition per word from DEX MySQL dump.
Streams line by line — never loads the full 1.2 GB into memory.
Output: data/processed/definitions.db
Schema: definitions(word TEXT PRIMARY KEY, definition TEXT NOT NULL)
"""
import sqlite3
from pathlib import Path

SQL_PATH = Path('data/dictionaries/dex-database.sql')
OUT_PATH = Path('data/processed/definitions.db')

_PREFIX = "INSERT INTO `DefinitionSimple` VALUES "


def _parse_values(values_str: str) -> list[list]:
    """Parse MySQL multi-value VALUES clause into list of value lists.

    Handles quoted strings with \\'  and \\\\ escapes, and ) inside strings.
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


def extract(sql_path: Path, out_path: Path) -> int:
    """Collect first definition per lexicon from sql_path, write to out_path.

    Returns number of words written.
    """
    seen: dict[str, str] = {}  # word → first definition

    with open(sql_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line.startswith(_PREFIX):
                continue
            values_str = line[len(_PREFIX):]
            if values_str.endswith(';'):
                values_str = values_str[:-1]
            for row in _parse_values(values_str):
                if len(row) < 3:
                    continue
                definition = row[1]   # col 1: definition text
                word = row[2]         # col 2: lexicon (the word)
                if word and definition and word not in seen:
                    seen[word] = definition

    out_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(out_path))
    conn.execute('DROP TABLE IF EXISTS definitions')
    conn.execute(
        'CREATE TABLE definitions (word TEXT PRIMARY KEY, definition TEXT NOT NULL)'
    )
    conn.executemany('INSERT INTO definitions VALUES (?, ?)', seen.items())
    conn.commit()
    conn.close()
    print(f"Wrote {len(seen)} definitions to {out_path}")
    return len(seen)


if __name__ == '__main__':
    extract(SQL_PATH, OUT_PATH)
```

- [ ] **Step 4: Run tests to confirm pass**

```bash
python -m pytest tests/test_extract_definitions.py -v
```
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add extract_definitions.py tests/test_extract_definitions.py
git commit -m "feat: extract_definitions.py — stream DEX dump, write first definition per word"
```

---

## Task 2: load_words() definition column

**Files:**
- Modify: `ui/app.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing tests**

Add these two tests to `tests/test_ui.py` (place near the other `test_load_words_*` tests). They also need `import sqlite3` at the top — it's already imported.

```python
def test_load_words_loads_definitions(tmp_path):
    shortlist = tmp_path / 'shortlist.csv'
    web = tmp_path / 'web.csv'
    make_shortlist(shortlist, [WORD_A, WORD_B])
    make_web(web, [])

    defs_db = tmp_path / 'defs.db'
    dconn = sqlite3.connect(str(defs_db))
    dconn.execute('CREATE TABLE definitions (word TEXT PRIMARY KEY, definition TEXT NOT NULL)')
    dconn.execute("INSERT INTO definitions VALUES ('acătării', 'Vânzătoare de acătări.')")
    dconn.commit()
    dconn.close()

    words_db = ui_app.load_words(shortlist, web, defs_db)
    row = words_db.execute(
        "SELECT definition FROM words WHERE word='acătării'"
    ).fetchone()
    assert row['definition'] == 'Vânzătoare de acătări.'
    row2 = words_db.execute(
        "SELECT definition FROM words WHERE word='adăsta'"
    ).fetchone()
    assert row2['definition'] is None
    words_db.close()


def test_load_words_no_definitions_db(tmp_path):
    shortlist = tmp_path / 'shortlist.csv'
    web = tmp_path / 'web.csv'
    make_shortlist(shortlist, [WORD_A, WORD_B])
    make_web(web, [])
    words_db = ui_app.load_words(shortlist, web, tmp_path / 'nonexistent.db')
    row = words_db.execute("SELECT definition FROM words WHERE word='acătării'").fetchone()
    assert row['definition'] is None
    words_db.close()
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_ui.py::test_load_words_loads_definitions tests/test_ui.py::test_load_words_no_definitions_db -v
```
Expected: `TypeError: load_words() takes 2 positional arguments but 3 were given`

- [ ] **Step 3: Update ui/app.py**

**a) Add constant** after `RESEARCH_DB_PATH`:
```python
DEFINITIONS_DB_PATH = Path('data/processed/definitions.db')
```

**b) Update `load_words` signature and CREATE TABLE**:

Change signature from `def load_words(shortlist_path: Path, web_path: Path) -> sqlite3.Connection:` to:
```python
def load_words(
    shortlist_path: Path,
    web_path: Path,
    definitions_path: Path | None = None,
) -> sqlite3.Connection:
```

Add `definition TEXT` to the CREATE TABLE statement (append after `provider TEXT`):
```sql
            provider         TEXT,
            definition       TEXT
```

**c) Add definition loading** — insert this block at the end of `load_words`, just before `conn.commit()`:
```python
    defs_path = definitions_path if definitions_path is not None else DEFINITIONS_DB_PATH
    if defs_path.exists():
        dconn = sqlite3.connect(str(defs_path))
        for word, definition in dconn.execute('SELECT word, definition FROM definitions'):
            conn.execute('UPDATE words SET definition=? WHERE word=?', (definition, word))
        dconn.close()
```

**d) Update `init_app`** — add `definitions_path` parameter and pass it through:
```python
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
```

**e) Update the `dbs` fixture** in `tests/test_ui.py` — pass a non-existent definitions path so tests are isolated from any `data/processed/definitions.db` the developer may have generated:

```python
@pytest.fixture()
def dbs(tmp_path):
    shortlist = tmp_path / 'shortlist.csv'
    web = tmp_path / 'web.csv'
    research = tmp_path / 'research.db'
    make_shortlist(shortlist, [WORD_A, WORD_B])
    make_web(web, [WEB_A])
    words_db = ui_app.load_words(shortlist, web, tmp_path / 'no_defs.db')
    res_db = ui_app.open_research_db(research)
    yield words_db, res_db
    words_db.close()
    res_db.close()
```

The only change is `load_words(shortlist, web, tmp_path / 'no_defs.db')` — the third arg is a path that doesn't exist, so `defs_path.exists()` is False and no definitions are loaded. Without this fix, tests that assert a word has no definition would fail on any machine where the developer has already run `python extract_definitions.py`.

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/test_ui.py -v
```
Expected: all tests PASS (existing 19 + 2 new = 21 tests).

- [ ] **Step 5: Commit**

```bash
git add ui/app.py tests/test_ui.py
git commit -m "feat(ui): add definition column to words table, load from definitions.db on startup"
```

---

## Task 3: Sort param in /search

**Files:**
- Modify: `ui/app.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ui.py`. Place `WORD_C` constant near `WORD_A`/`WORD_B`:

```python
WORD_C = {
    'word': 'afurca', 'dex_frequency': '0.05', 'verdict': 'extinct',
    'confidence_tier': 'corpus_extinct', 'log_ratio': '-8.0', 'hist_ppm': '5.0',
    'modern_ppm': '0.0', 'dex_pos': 'vb.', 'dex_register': '',
    'dex_domain': '', 'dex_etymology': '', 'is_forgotten': '1',
}
```

Add a fixture and tests:

```python
@pytest.fixture()
def client3(tmp_path):
    shortlist = tmp_path / 'shortlist.csv'
    web = tmp_path / 'web.csv'
    research = tmp_path / 'research.db'
    # WORD_A: log_ratio=-5.2, modern_ppm=0.0, dex_frequency=0.1
    # WORD_B: log_ratio=-3.1, modern_ppm=0.1, dex_frequency=0.2
    # WORD_C: log_ratio=-8.0, modern_ppm=0.0, dex_frequency=0.05
    make_shortlist(shortlist, [WORD_A, WORD_B, WORD_C])
    make_web(web, [])
    words_db = ui_app.load_words(shortlist, web)
    res_db = ui_app.open_research_db(research)
    ui_app._words_db = words_db
    ui_app._research_db = res_db
    ui_app.app.config['TESTING'] = True
    with ui_app.app.test_client() as c:
        yield c
    words_db.close()
    res_db.close()


def test_search_default_sort_is_alpha(client3):
    resp = client3.get('/search')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert html.index('acătării') < html.index('adăsta') < html.index('afurca')


def test_search_sort_declined(client3):
    # WORD_C log_ratio=-8.0 (most declined DESC), then WORD_A -5.2, then WORD_B -3.1
    resp = client3.get('/search?sort=declined')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert html.index('afurca') < html.index('acătării') < html.index('adăsta')


def test_search_sort_rare(client3):
    # WORD_A modern_ppm=0.0, WORD_C modern_ppm=0.0, WORD_B modern_ppm=0.1
    # ASC: 0.0 words first, then 0.1 — adăsta should come last
    resp = client3.get('/search?sort=rare')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert html.index('adăsta') > html.index('acătării')


def test_search_sort_invalid_falls_back_to_alpha(client3):
    resp = client3.get('/search?sort=DROP+TABLE+words')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert html.index('acătării') < html.index('adăsta')
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_ui.py::test_search_sort_declined -v
```
Expected: FAIL — afurca comes after acătarii alphabetically, but `sort=declined` isn't applied yet.

- [ ] **Step 3: Update ui/app.py**

**a) Add SORT_OPTIONS** — after `PAGE_SIZE = 50`:
```python
SORT_OPTIONS = {
    'declined': 'log_ratio DESC NULLS LAST',
    'rare':     'modern_ppm ASC NULLS LAST',
    'dex_freq': 'dex_frequency ASC NULLS LAST',
}
```

**b) Update `search()`** — add `sort` param and use `SORT_OPTIONS` for ORDER BY:

```python
@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    verdict = request.args.get('verdict', '').strip()
    tier = request.args.get('tier', '').strip()
    bookmarked_only = request.args.get('bookmarked', '') == '1'
    sort = request.args.get('sort', '').strip()
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
    order_by = SORT_OPTIONS.get(sort, 'word ASC')
    bmap = _bookmarks_map()

    all_rows = _words_db.execute(
        f'SELECT * FROM words {where} ORDER BY {order_by}', params
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

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/test_ui.py -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ui/app.py tests/test_ui.py
git commit -m "feat(ui): add sort param to /search with SORT_OPTIONS allowlist"
```

---

## Task 4: base.html — sort select, definition CSS, shortcuts modal

**Files:**
- Modify: `ui/templates/base.html`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ui.py`:

```python
def test_base_has_sort_select(client):
    resp = client.get('/')
    assert b'name="sort"' in resp.data


def test_base_has_shortcuts_overlay(client):
    resp = client.get('/')
    assert b'shortcuts-overlay' in resp.data
    assert b'showShortcuts' in resp.data
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_ui.py::test_base_has_sort_select tests/test_ui.py::test_base_has_shortcuts_overlay -v
```
Expected: both FAIL.

- [ ] **Step 3: Update ui/templates/base.html**

**a) Sort select** — insert between the closing `</select>` for tier (line 109) and the `<label class="bookmark-filter">` (line 110):

```html
    <select name="sort"
            hx-get="/search"
            hx-trigger="change"
            hx-target="#word-list"
            hx-include="#filter-form">
      <option value="">↕ alphabetical</option>
      <option value="declined">↓ most declined</option>
      <option value="rare">↓ rarest modern</option>
      <option value="dex_freq">↓ DEX frequency</option>
    </select>
```

**b) Definition CSS** — add to the `<style>` block, after the `.htmx-indicator` rule:

```css
    .definition-block { background:#1f1f1f; border-left:2px solid #3a3a3a; padding:10px 14px; margin-bottom:12px; border-radius:2px; }
    .definition-label { color:#666; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px; }
    .definition-text { color:#c0c0c0; line-height:1.6; font-size:13px; }
    .dex-link { color:#4a8fd4; font-size:11px; text-decoration:none; display:inline-block; margin-top:8px; }
```

**c) Shortcuts CSS** — add to the `<style>` block, after definition CSS:

```css
    #shortcuts-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:center; z-index:100; }
    #shortcuts-modal { background:#1e1e1e; border:1px solid #333; border-radius:4px; padding:20px 28px; min-width:360px; box-shadow:0 8px 32px rgba(0,0,0,0.6); }
    .shortcuts-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; color:#e0e0e0; font-size:14px; font-weight:bold; }
    .shortcuts-esc { color:#555; font-size:12px; font-weight:normal; }
    .shortcuts-table { width:100%; border-collapse:collapse; font-size:12px; }
    .shortcuts-table td { padding:2px 0; color:#ccc; }
    .shortcuts-table td:first-child { padding-right:16px; white-space:nowrap; }
    .shortcuts-group { padding:8px 0 4px; color:#666; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; }
    kbd { background:#2a2a2a; border:1px solid #444; border-radius:3px; padding:1px 5px; color:#e0e0e0; font-family:monospace; font-size:11px; }
```

**d) Shortcuts modal HTML** — add just before `</body>`:

```html
  <div id="shortcuts-overlay" style="display:none">
    <div id="shortcuts-modal">
      <div class="shortcuts-header">
        <span>Keyboard shortcuts</span>
        <span class="shortcuts-esc">Esc to close</span>
      </div>
      <table class="shortcuts-table">
        <tr><td colspan="2" class="shortcuts-group">Navigation</td></tr>
        <tr><td><kbd>j</kbd> / <kbd>k</kbd></td><td>Next / previous word</td></tr>
        <tr><td><kbd>g</kbd><kbd>g</kbd></td><td>Jump to top</td></tr>
        <tr><td><kbd>G</kbd></td><td>Jump to bottom</td></tr>
        <tr><td colspan="2" class="shortcuts-group">Search</td></tr>
        <tr><td><kbd>/</kbd></td><td>Focus search</td></tr>
        <tr><td><kbd>Esc</kbd></td><td>Blur / close popup</td></tr>
        <tr><td colspan="2" class="shortcuts-group">Actions</td></tr>
        <tr><td><kbd>b</kbd></td><td>Toggle bookmark</td></tr>
        <tr><td><kbd>n</kbd></td><td>Focus note field</td></tr>
        <tr><td><kbd>?</kbd></td><td>Show / hide this popup</td></tr>
      </table>
    </div>
  </div>
```

**e) Shortcuts JS** — update the `<script>` block:

Add these two functions before `document.addEventListener('keydown', ...)`:

```javascript
    function showShortcuts() {
      document.getElementById('shortcuts-overlay').style.display = 'flex';
    }
    function hideShortcuts() {
      document.getElementById('shortcuts-overlay').style.display = 'none';
    }
```

Replace the existing `keydown` handler with this updated version (changes marked with comments):

```javascript
    document.addEventListener('keydown', function(e) {
      const tag = document.activeElement.tagName;
      const inInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';

      // ? works everywhere — intercept before inInput check
      if (e.key === '?') { e.preventDefault(); showShortcuts(); return; }

      if (inInput) {
        if (e.key === 'Escape') {
          hideShortcuts();
          document.activeElement.blur();
        }
        return;
      }

      if (e.key === 'Escape') { hideShortcuts(); return; }

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
```

Add click-outside handler after the existing `htmx:afterSwap` listener:

```javascript
    document.getElementById('shortcuts-overlay').addEventListener('click', function(e) {
      if (e.target === this) hideShortcuts();
    });
```

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/test_ui.py -v
```
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ui/templates/base.html tests/test_ui.py
git commit -m "feat(ui): add sort select, definition CSS, and shortcuts popup to base.html"
```

---

## Task 5: detail.html — definition block

**Files:**
- Modify: `ui/templates/partials/detail.html`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ui.py`:

```python
def test_word_detail_shows_definition(dbs, client):
    # dbs and client share the same words_db instance (pytest fixture dedup)
    words_db, _ = dbs
    words_db.execute(
        "UPDATE words SET definition='Vânzătoare de acătări.' WHERE word='acătării'"
    )
    words_db.commit()
    resp = client.get('/word/acătării')
    assert 'Vânzătoare de acătări.'.encode('utf-8') in resp.data
    assert b'dexonline.ro' in resp.data


def test_word_detail_no_definition_hides_block(client):
    resp = client.get('/word/acătării')
    assert b'definition-block' not in resp.data
```

- [ ] **Step 2: Run to confirm failure**

```bash
python -m pytest tests/test_ui.py::test_word_detail_shows_definition tests/test_ui.py::test_word_detail_no_definition_hides_block -v
```
Expected: `test_word_detail_shows_definition` FAILS (definition text not in HTML); `test_word_detail_no_definition_hides_block` PASSES.

- [ ] **Step 3: Update ui/templates/partials/detail.html**

Insert the definition block between the closing `</table>` of the metadata table (line 10) and the first `<hr>` (line 12). The current file has:

```
</table>

<hr>

<table class="detail-table">
  <tr><th>hist_ppm</th>
```

Replace the blank line + `<hr>` with:

```html
{% if w.definition %}
<hr>
<div class="definition-block">
  <div class="definition-label">DEX</div>
  <div class="definition-text">{{ w.definition }}</div>
  <a class="dex-link"
     href="https://dexonline.ro/definitie/{{ w.word | urlencode }}"
     target="_blank" rel="noopener">↗ dexonline.ro</a>
</div>
{% endif %}

<hr>
```

The second `<hr>` (before the corpus scores table) is kept regardless of whether there's a definition.

- [ ] **Step 4: Run all tests**

```bash
python -m pytest tests/ -v
```
Expected: all tests across all test files PASS.

- [ ] **Step 5: Commit**

```bash
git add ui/templates/partials/detail.html tests/test_ui.py
git commit -m "feat(ui): add DEX definition block to word detail panel"
```

---

## Verification

After all tasks:

```bash
# Full test suite
source /Users/pax/devbox/envs/240826/bin/activate
python -m pytest tests/ -v

# Extract definitions (one-time, ~5–10 min for 1.2 GB)
python extract_definitions.py
# Expected: "Wrote N definitions to data/processed/definitions.db"

# Start server
python ui/app.py
# open http://localhost:5000
# - click a word → definition block appears (if word has a definition)
# - change sort dropdown → word list reorders without page reload
# - press ? → shortcuts popup appears; Esc closes it; click outside closes it
```
