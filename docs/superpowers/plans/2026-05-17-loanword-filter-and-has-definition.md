# Loanword Exclusion Filter + has_definition Column — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `has_definition` boolean column flowing from `validate_diachronic.py` → `make_shortlist.py` → UI, and add configurable etymology-exclusion in both `make_shortlist.py` (CLI flag) and the research UI (new filter row).

**Architecture:** Four files change. `validate_diachronic.py` gains a helper that queries `definitions.db` and writes a `has_definition` column. `make_shortlist.py` passes that column through and gains `--exclude-etymology` to drop words at CSV-generation time. `ui/app.py` loads `has_definition` into the in-memory `words` table and adds `exclude_etym` multi-value filter logic. `base.html` adds a sixth filter row (checkbox pills, red active state).

**Tech Stack:** Python 3.12, Flask, HTMX, SQLite, pytest. Venv: `/Users/pax/devbox/envs/240826`.

> **Pre-existing test failures (ignore):** `test_search_default_sort_is_alpha` and `test_search_sort_declined` were already failing before this work. Do not treat them as regressions.

---

## File Map

| File | Change |
|------|--------|
| `validate_diachronic.py` | Add `_load_definition_words()`, add `has_definition` to results dict + `fields` list |
| `make_shortlist.py` | Add `has_definition` to `OUT_FIELDS`; add `--exclude-etymology` flag; update `classify()` |
| `ui/app.py` | Add `has_definition` to `CREATE TABLE` + INSERT; add `exclude_etym` getlist + NOT LIKE conditions in `/search` |
| `ui/templates/base.html` | Add `.pill-excl` CSS + Row 6 exclusion checkboxes |
| `tests/test_validate_diachronic.py` | New: tests for `_load_definition_words()` |
| `tests/test_make_shortlist.py` | New: tests for `classify()` with exclusion + `has_definition` in OUT_FIELDS |
| `tests/test_ui.py` | Update `SHORTLIST_COLS` + word fixtures; add tests for `has_definition` column and `exclude_etym` filter |

---

## Task 1 — has_definition column in validate_diachronic.py

**Files:**
- Modify: `validate_diachronic.py`
- Create: `tests/test_validate_diachronic.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_validate_diachronic.py`:

```python
import sqlite3
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import validate_diachronic as vd


def make_defs_db(path: Path, rows: list[tuple]) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute(
        'CREATE TABLE definitions (word TEXT PRIMARY KEY, definition TEXT)'
    )
    conn.executemany('INSERT INTO definitions VALUES (?,?)', rows)
    conn.commit()
    conn.close()


def test_load_definition_words_returns_words_with_content(tmp_path):
    db = tmp_path / 'defs.db'
    make_defs_db(db, [
        ('ajutoriu', 'Formă veche pentru ajutor.'),
        ('nombrilist', None),
        ('viți', ''),
    ])
    result = vd._load_definition_words(db)
    assert 'ajutoriu' in result
    assert 'nombrilist' not in result
    assert 'viți' not in result


def test_load_definition_words_missing_db_returns_empty(tmp_path):
    result = vd._load_definition_words(tmp_path / 'nonexistent.db')
    assert result == set()
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/test_validate_diachronic.py -v
```

Expected: `AttributeError: module 'validate_diachronic' has no attribute '_load_definition_words'`

- [ ] **Step 3: Add DEFINITIONS_DB path constant and _load_definition_words() to validate_diachronic.py**

After the existing path constants (around line 41), add:

```python
DEFINITIONS_DB = Path('data/processed/definitions.db')


def _load_definition_words(db_path: Path) -> set[str]:
    if not db_path.exists():
        return set()
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT word FROM definitions WHERE definition IS NOT NULL AND definition != ''"
    ).fetchall()
    conn.close()
    return {r[0] for r in rows}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/test_validate_diachronic.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Wire has_definition into main()**

In `main()`, after loading taxonomy (around line 231), add:

```python
    print('Loading definition index...')
    def_words = _load_definition_words(DEFINITIONS_DB)
    print(f'  {len(def_words):,} words with definitions')
```

In the `results.append({...})` block (around line 256), add the new key after `'dex_etymology'`:

```python
            'has_definition':   1 if word in def_words else 0,
```

In the `fields` list (around line 278), add `'has_definition'` after `'dex_etymology'`:

```python
    fields = [
        'word', 'dex_frequency', 'description', 'rarity_category',
        'hist_occurrences', 'hist_documents', 'hist_ppm',
        'modern_occurrences', 'modern_documents', 'modern_ppm',
        'log_ratio', 'verdict',
        'dex_pos', 'dex_register', 'dex_domain', 'dex_etymology',
        'has_definition',
    ]
```

- [ ] **Step 6: Run all tests**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/ -v 2>&1 | tail -15
```

Expected: validate_diachronic tests pass; no new failures in test_ui.py.

- [ ] **Step 7: Commit**

```bash
git add validate_diachronic.py tests/test_validate_diachronic.py
git commit -m "feat(diachronic): add has_definition column to CSV output"
```

---

## Task 2 — has_definition flows through make_shortlist.py

**Files:**
- Modify: `make_shortlist.py`
- Create: `tests/test_make_shortlist.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_make_shortlist.py`:

```python
import csv
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import make_shortlist as ms


def make_diachronic_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        'word', 'dex_frequency', 'description', 'rarity_category',
        'hist_occurrences', 'hist_documents', 'hist_ppm',
        'modern_occurrences', 'modern_documents', 'modern_ppm',
        'log_ratio', 'verdict',
        'dex_pos', 'dex_register', 'dex_domain', 'dex_etymology',
        'has_definition',
    ]
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({f: row.get(f, '') for f in fields})


BASE_ROW = {
    'word': 'ajutoriu',
    'dex_frequency': '0.4',
    'description': 'adj.',
    'rarity_category': 'rare',
    'hist_occurrences': '5', 'hist_documents': '3', 'hist_ppm': '1.2',
    'modern_occurrences': '0', 'modern_documents': '0', 'modern_ppm': '0.0',
    'log_ratio': '3.5',
    'verdict': 'extinct',
    'dex_pos': 'adjectiv',
    'dex_register': '', 'dex_domain': '', 'dex_etymology': 'slavă',
    'has_definition': '1',
}


def test_has_definition_in_out_fields():
    assert 'has_definition' in ms.OUT_FIELDS


def test_has_definition_passes_through_to_output(tmp_path):
    inp = tmp_path / 'diachronic.csv'
    out = tmp_path / 'shortlist.csv'
    make_diachronic_csv(inp, [BASE_ROW])

    sys.argv = ['make_shortlist.py', '--input', str(inp), '--output', str(out)]
    ms.main()

    rows = list(csv.DictReader(out.open(encoding='utf-8')))
    assert len(rows) == 1
    assert rows[0]['has_definition'] == '1'
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/test_make_shortlist.py::test_has_definition_in_out_fields -v
```

Expected: `AssertionError: assert 'has_definition' in [...]`

- [ ] **Step 3: Add has_definition to OUT_FIELDS in make_shortlist.py**

In `make_shortlist.py`, find the `OUT_FIELDS` list (around line 44) and append `'has_definition'`:

```python
OUT_FIELDS = [
    'word', 'dex_frequency', 'description', 'dex_pos',
    'verdict', 'log_ratio', 'hist_ppm', 'modern_ppm',
    'dex_register', 'dex_domain', 'dex_etymology',
    'confidence_tier', 'is_forgotten', 'has_definition',
]
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/test_make_shortlist.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Run all tests**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/ -v 2>&1 | tail -10
```

Expected: no new failures.

- [ ] **Step 6: Commit**

```bash
git add make_shortlist.py tests/test_make_shortlist.py
git commit -m "feat(shortlist): pass has_definition column through to shortlist CSV"
```

---

## Task 3 — --exclude-etymology flag in make_shortlist.py

**Files:**
- Modify: `make_shortlist.py`
- Modify: `tests/test_make_shortlist.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_make_shortlist.py`:

```python
ANGLICISM_ROW = {
    **BASE_ROW,
    'word': 'sendviș',
    'dex_etymology': 'anglicism',
    'has_definition': '0',
}

ABSENT_ROW = {
    **BASE_ROW,
    'word': 'lăut',
    'verdict': 'absent',
    'hist_ppm': '0.0',
    'dex_register': 'învechit',
    'dex_etymology': '',
    'has_definition': '1',
}


def test_classify_excludes_matching_etymology():
    row = {**ANGLICISM_ROW}
    result = ms.classify(row, exclude_etym=frozenset({'anglicism'}))
    assert result is None


def test_classify_keeps_non_matching_etymology():
    row = {**BASE_ROW}  # dex_etymology='slavă'
    result = ms.classify(row, exclude_etym=frozenset({'anglicism'}))
    assert result is not None


def test_classify_empty_exclude_set_unchanged():
    row = {**ANGLICISM_ROW}
    result = ms.classify(row, exclude_etym=frozenset())
    # anglicism word with extinct verdict and hist_ppm>0 → should be classified
    assert result == 'corpus_extinct'


def test_exclude_etymology_cli_filters_output(tmp_path):
    inp = tmp_path / 'diachronic.csv'
    out = tmp_path / 'shortlist.csv'
    make_diachronic_csv(inp, [BASE_ROW, ANGLICISM_ROW])

    sys.argv = [
        'make_shortlist.py',
        '--input', str(inp),
        '--output', str(out),
        '--exclude-etymology', 'anglicism',
    ]
    ms.main()

    rows = list(csv.DictReader(out.open(encoding='utf-8')))
    words = [r['word'] for r in rows]
    assert 'ajutoriu' in words
    assert 'sendviș' not in words
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/test_make_shortlist.py::test_classify_excludes_matching_etymology -v
```

Expected: `TypeError: classify() takes 1 positional argument but 2 were given`

- [ ] **Step 3: Update classify() to accept exclude_etym**

In `make_shortlist.py`, replace the `classify()` function:

```python
def classify(row: dict, exclude_etym: frozenset = frozenset()) -> str | None:
    if pos_excluded(row['dex_pos']):
        return None
    if exclude_etym:
        etym_tags = {t.strip() for t in (row.get('dex_etymology') or '').split('|') if t.strip()}
        if etym_tags & exclude_etym:
            return None
    verdict = row['verdict']
    if verdict in TIER_A_VERDICTS and float(row['hist_ppm']) > 0:
        return f'corpus_{verdict}'
    if verdict == 'absent' and 'învechit' in (row.get('dex_register') or '').split('|'):
        return 'dex_invechit_absent'
    return None
```

- [ ] **Step 4: Add --exclude-etymology to argparse and wire it in main()**

In `main()`, add the new argument after the existing ones:

```python
    parser.add_argument(
        '--exclude-etymology', default='', metavar='TAGS',
        help='Comma-separated etymology tags to exclude. E.g. anglicism,franțuzism',
    )
```

After `args = parser.parse_args()`, build the exclusion set:

```python
    exclude_etym = frozenset(
        t.strip() for t in args.exclude_etymology.split(',') if t.strip()
    )
```

Add an `excluded_etym = 0` counter alongside `excluded_pos = 0`.

In the classification loop, replace `tier = classify(row)` with:

```python
        tier = classify(row, exclude_etym)
        if tier is None:
            if pos_excluded(row['dex_pos']):
                excluded_pos += 1
            elif exclude_etym:
                etym_tags = {t.strip() for t in (row.get('dex_etymology') or '').split('|') if t.strip()}
                if etym_tags & exclude_etym:
                    excluded_etym += 1
            continue
```

Remove the old `if tier is None: ... continue` block (it was only two lines; replace entirely with the above).

After the existing `print(f'  Excluded (POS) ...')` stats line, add:

```python
    if exclude_etym:
        print(f'  Excluded (etymology)         {excluded_etym:>6,}')
```

- [ ] **Step 5: Run all make_shortlist tests**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/test_make_shortlist.py -v
```

Expected: all pass.

- [ ] **Step 6: Run full test suite**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/ -v 2>&1 | tail -10
```

Expected: no new failures beyond the 2 pre-existing ones.

- [ ] **Step 7: Commit**

```bash
git add make_shortlist.py tests/test_make_shortlist.py
git commit -m "feat(shortlist): add --exclude-etymology flag to filter loanwords at CSV generation"
```

---

## Task 4 — has_definition in ui/app.py and test fixtures

**Files:**
- Modify: `ui/app.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Update test fixtures to include has_definition**

In `tests/test_ui.py`, update `SHORTLIST_COLS`:

```python
SHORTLIST_COLS = [
    'word', 'dex_frequency', 'verdict', 'confidence_tier',
    'log_ratio', 'hist_ppm', 'modern_ppm', 'dex_pos',
    'dex_register', 'dex_domain', 'dex_etymology', 'is_forgotten',
    'has_definition',
]
```

Update `WORD_A`, `WORD_B`, `WORD_C` to include the new field (add to each dict):

```python
WORD_A = {
    'word': 'acătării', 'dex_frequency': '0.1', 'verdict': 'extinct',
    'confidence_tier': 'A', 'log_ratio': '-5.2', 'hist_ppm': '12.4',
    'modern_ppm': '0.0', 'dex_pos': 's.f.', 'dex_register': 'înv.',
    'dex_domain': '', 'dex_etymology': 'slavă', 'is_forgotten': '1',
    'has_definition': '1',
}
WORD_B = {
    'word': 'adăsta', 'dex_frequency': '0.2', 'verdict': 'declining',
    'confidence_tier': 'A', 'log_ratio': '-3.1', 'hist_ppm': '8.0',
    'modern_ppm': '0.1', 'dex_pos': 'vb.', 'dex_register': '',
    'dex_domain': '', 'dex_etymology': '', 'is_forgotten': '1',
    'has_definition': '0',
}
WORD_C = {
    'word': 'afurca', 'dex_frequency': '0.05', 'verdict': 'extinct',
    'confidence_tier': 'corpus_extinct', 'log_ratio': '-8.0', 'hist_ppm': '5.0',
    'modern_ppm': '0.0', 'dex_pos': 'vb.', 'dex_register': '',
    'dex_domain': '', 'dex_etymology': '', 'is_forgotten': '1',
    'has_definition': '1',
}
```

- [ ] **Step 2: Write the failing test**

Add to `tests/test_ui.py`:

```python
def test_load_words_has_definition_column(dbs):
    words_db, _ = dbs
    row_a = words_db.execute(
        "SELECT has_definition FROM words WHERE word='acătării'"
    ).fetchone()
    assert row_a['has_definition'] == 1

    row_b = words_db.execute(
        "SELECT has_definition FROM words WHERE word='adăsta'"
    ).fetchone()
    assert row_b['has_definition'] == 0
```

- [ ] **Step 3: Run the failing test**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/test_ui.py::test_load_words_has_definition_column -v
```

Expected: `sqlite3.OperationalError: table words has no column named has_definition`

- [ ] **Step 4: Add has_definition to the words table schema and INSERT in ui/app.py**

In `load_words()`, update the `CREATE TABLE words` statement — add `has_definition INTEGER` after `is_forgotten`:

```python
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
            definition       TEXT
        )
    """)
```

Update the INSERT column list and VALUES tuple:

```python
            conn.execute(
                """INSERT OR IGNORE INTO words
                   (word, dex_frequency, verdict, confidence_tier, log_ratio,
                    hist_ppm, modern_ppm, dex_pos, dex_register, dex_domain,
                    dex_etymology, is_forgotten, has_definition)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
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
                ),
            )
```

- [ ] **Step 5: Run all UI tests**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/test_ui.py -v 2>&1 | tail -15
```

Expected: new test passes; no other regressions beyond the 2 pre-existing sort failures.

- [ ] **Step 6: Run full test suite**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/ -v 2>&1 | tail -10
```

- [ ] **Step 7: Commit**

```bash
git add ui/app.py tests/test_ui.py
git commit -m "feat(ui): add has_definition column to words table schema and INSERT"
```

---

## Task 5 — exclude_etym filter in ui/app.py /search

**Files:**
- Modify: `ui/app.py`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ui.py` (uses the `client` fixture which has WORD_A with `dex_etymology='slavă'` and WORD_B with `dex_etymology=''`):

```python
def test_search_exclude_etymology_hides_matching_word(client):
    resp = client.get('/search?exclude_etym=slav%C4%83')
    body = resp.data.decode('utf-8')
    assert 'acătării'.encode('utf-8') not in resp.data
    assert 'adăsta'.encode('utf-8') in resp.data


def test_search_exclude_etymology_multiple_values(client):
    # exclude both slavă and nothing — words with empty etymology (adăsta) should survive
    resp = client.get('/search?exclude_etym=slav%C4%83&exclude_etym=nonexistent')
    assert 'acătării'.encode('utf-8') not in resp.data
    assert 'adăsta'.encode('utf-8') in resp.data
```

- [ ] **Step 2: Run the failing test**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/test_ui.py::test_search_exclude_etymology_hides_matching_word -v
```

Expected: FAIL — `acătării` is present despite exclusion (filter not yet wired).

- [ ] **Step 3: Add exclude_etym to /search in ui/app.py**

In the `search()` function, after the existing filter params (around line 231), add:

```python
    exclude_etym    = request.args.getlist('exclude_etym')
```

After the existing pipe-separated column filter loop, add:

```python
    for val in exclude_etym:
        conditions.append("NOT ('|'||dex_etymology||'|' LIKE ?)")
        params.append(f'%|{val}|%')
```

- [ ] **Step 4: Run the new tests**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/test_ui.py::test_search_exclude_etymology_hides_matching_word tests/test_ui.py::test_search_exclude_etymology_multiple_values -v
```

Expected: both pass.

- [ ] **Step 5: Run full test suite**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/ -v 2>&1 | tail -10
```

Expected: no new failures beyond the 2 pre-existing ones.

- [ ] **Step 6: Commit**

```bash
git add ui/app.py tests/test_ui.py
git commit -m "feat(ui): add exclude_etym multi-value filter to /search"
```

---

## Task 6 — Exclusion row + CSS in base.html

**Files:**
- Modify: `ui/templates/base.html`
- Modify: `tests/test_ui.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ui.py`:

```python
def test_base_has_exclude_etymology_row(client):
    resp = client.get('/')
    body = resp.data.decode('utf-8')
    assert 'name="exclude_etym"' in body
    assert 'pill-excl' in body


def test_base_exclude_row_has_red_active_css(client):
    resp = client.get('/')
    body = resp.data.decode('utf-8')
    assert '.pill-excl:has(input:checked)' in body
```

- [ ] **Step 2: Run the failing tests**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/test_ui.py::test_base_has_exclude_etymology_row tests/test_ui.py::test_base_exclude_row_has_red_active_css -v
```

Expected: both FAIL.

- [ ] **Step 3: Add .pill-excl CSS to base.html**

In the `<style>` block, after the `.bm-pill:has(input:checked)` rule (around line 247), add:

```css
    /* Exclusion pill — red when checked (opposite of include) */
    .pill-excl:has(input:checked) {
      background: #fff1f0;
      color: #9a1313;
      font-weight: 700;
      border-color: #f87171;
      box-shadow: 0 0 0 1px #f87171;
    }
```

- [ ] **Step 4: Add exclusion filter row to base.html**

After the closing `</div>` of Row 5 (the etymology include row, around line 844), add:

```html
    <!-- Row 6: exclude etymologies (multi-select, red = excluded) -->
    <div class="filter-row">
      <span class="flabel">exclude</span>
      {% for e in distinct_etymologies %}
      <label class="pill pill-excl">
        <input type="checkbox" name="exclude_etym" value="{{ e }}">
        {{ e | replace('limba ', '') }}
      </label>
      {% endfor %}
    </div>
```

- [ ] **Step 5: Run new tests**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/test_ui.py::test_base_has_exclude_etymology_row tests/test_ui.py::test_base_exclude_row_has_red_active_css -v
```

Expected: both pass.

- [ ] **Step 6: Run full test suite**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/ -v 2>&1 | tail -10
```

Expected: no new failures beyond the 2 pre-existing ones.

- [ ] **Step 7: Commit**

```bash
git add ui/templates/base.html tests/test_ui.py
git commit -m "feat(ui): add exclusion filter row for etymology with red active state"
```

---

## Final verification

- [ ] **Start the UI and manually verify**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && cd /Users/pax/devbox/otios && python ui/app.py
```

Open `http://localhost:5000` and confirm:
1. Row 6 ("exclude") appears below the etymology row with red pills on selection
2. Selecting an exclusion etymology removes matching words from the list
3. Simultaneously selecting an include etymology (row 5) and the same exclude etymology yields empty results
4. `has_def ✓` filter still works correctly

- [ ] **Run full test suite one final time**

```bash
source /Users/pax/devbox/envs/240826/bin/activate && python -m pytest tests/ -v
```

Expected: 44 + new tests passing; only the 2 pre-existing sort failures remain.
