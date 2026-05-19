# Plan: Fix missing definitions for shortlist words

## Context

The `## 260519 Data Audit` backlog item reports that some words in the UI lack definitions even though dexonline.ro shows them. We investigated all 13 cited examples plus the broader `not_found` pool (1,370 shortlist words).

Root cause is **not** a selector bug — `#tab_2 .tree-body li.type-meaning .meaningContainer .tree-def` works correctly on raw HTML for all tested words. The real problem is two structural cases that the current scraper doesn't handle.

---

## Findings

### Coverage gaps

| Bucket | Count |
|---|---|
| Shortlist words with no definitions.db entry, not yet scraped | **2,703** |
| Shortlist words stuck as `not_found` in checkpoint | **1,370** |
| Total needing attention | **~4,073** |

The 11 backlog examples that were simply never scraped (`ospătător`, `mofluzită`, `cfartal`, `prijuni`, `murea`, `aeresc`, `săhăstricesc`, `bașfir`, `pestitor`, `libovnică`, `ischiuzară`) all parse fine with the existing selector — they're in the 2,703 unscraped bucket.

### Root cause A: No synthesis panel (~95% of `not_found` words)

Words like `gad`, `margă`, `rusască`, `flaimuc` — `#tab_2` loads but has **no `.tree-body`** at all. Dexonline hasn't curated a synthesis for these words yet.

Definitions **do** exist in `#tab_0` as `.defWrapper > p.mb-2 > span.def` elements. Each `.defWrapper` has a bolded headword (`<b><i>word</i></b>` or `<b>word</b>`). We can match the target word case-insensitively (strip `*`, `❍` prefixes and trailing `,` or `.`).

**Verified via Playwright** for `gad`: 3 `.defWrapper` entries with matching headword `gad`.

### Root cause B: Empty synthesis — inflected/derived forms (~5% of `not_found`)

Words like `abecedare` (plural of `abecedar`) — `#tab_2` has `.tree-body` but dexonline displays "Nu avem definiții în sursele actuale pentru această formă." The word is an inflected form; definitions exist only under the base lemma.

`#tab_0` headwords don't match the inflected form. Fix: use `simplemma` (already in venv) to get the base lemma, then look up the lemma's definition from `definitions.db`.

---

## Implementation plan

### Step 1 — Extend `scrape_definitions.py`

**File:** `scrape_definitions.py`

Add two new functions and wire them into `fetch_synthesis`:

```python
def parse_tab0_defs(html: str, word: str) -> str | None:
    """Fallback for words with no synthesis: scan #tab_0 .defWrapper entries."""
    soup = BeautifulSoup(html, 'lxml')
    tab0 = soup.select_one('#tab_0')
    if not tab0:
        return None
    word_norm = word.lower()
    results = []
    for wrapper in tab0.select('.defWrapper'):
        b = wrapper.select_one('.def b')
        if not b:
            continue
        hw = b.get_text(' ', strip=True).lstrip('*❍').rstrip(',.').strip().lower()
        if hw == word_norm or hw == word_norm.upper().lower():
            text = wrapper.select_one('.def')
            if text:
                clean = ' '.join(text.get_text(' ', strip=True).split())
                if clean:
                    results.append(clean)
    return ' | '.join(results[:3]) if results else None


def parse_lemma_fallback(word: str, defs_db: Path) -> str | None:
    """For empty-synthesis inflected forms: look up the base lemma's definition."""
    import simplemma
    lemma = simplemma.lemmatize(word, lang='ro')
    if lemma == word or not defs_db.exists():
        return None
    conn = sqlite3.connect(str(defs_db))
    try:
        row = conn.execute('SELECT definition FROM definitions WHERE word=?', (lemma,)).fetchone()
        return f'[formă a lui {lemma}] {row[0]}' if row else None
    finally:
        conn.close()
```

Update `fetch_synthesis` to try fallbacks before returning `not_found`:

```python
# After definition = parse_synthesis(resp.text) returns None:
if definition is None:
    definition = parse_tab0_defs(resp.text, word)
if definition is None:
    definition = parse_lemma_fallback(word, defs_db_path)  # pass as param
```

`fetch_synthesis` needs `defs_db` path added as a parameter (pass `DEFAULT_DEFS_DB` from `main`).

### Step 2 — Add `--retry-not-found` flag

In `load_checkpoint`, current logic returns all words ever attempted (so `not_found` are skipped forever). Add a flag:

```python
parser.add_argument('--retry-not-found', action='store_true',
    help='Re-queue words previously marked not_found')
```

When set, `checkpoint = {row['word'] for row in ... if row['status'] != 'not_found'}`.

When re-running, append to the CSV (same as now). The last row per word wins — merge step uses `INSERT OR REPLACE`.

### Step 3 — Run the scraper

```bash
source ~/g2-dev/monitorulpreturilor/venv/bin/activate

# Pass 1: scrape the 2,703 never-attempted words
python scrape_definitions.py --delay 2.0 --merge

# Pass 2: re-try the 1,370 stuck not_found words with new fallbacks
python scrape_definitions.py --retry-not-found --delay 2.0 --merge
```

### Step 4 — Rebuild ui.db

```bash
python tools/build_ui_db.py
```

### Step 5 — Statistics impact check

Run this query against `ui.db` before and after to measure:

```sql
SELECT
  COUNT(*) FILTER (WHERE definition IS NULL) AS no_definition,
  COUNT(*) FILTER (WHERE definition IS NOT NULL) AS has_definition,
  COUNT(*) AS total
FROM words;
```

Also check if `has_definition` column in the shortlist CSV is used anywhere for filtering in the UI — grep `has_definition` in `public/`. If the PHP reads it from `ui.db` (where it comes from the shortlist), it may be stale. After this fix, update the shortlist CSV's `has_definition` column or derive it from `definitions.db` in `build_ui_db.py` instead.

---

## Files changed

- `scrape_definitions.py` — `parse_tab0_defs`, `parse_lemma_fallback`, `--retry-not-found` flag, pass `defs_db` into `fetch_synthesis`

---

## Verification

1. Dry-run: `python scrape_definitions.py --dry-run --limit 5` — no errors
2. Spot-check 5 words: `gad`, `margă`, `abecedare`, `mofluzită`, `ospătător` should all get definitions
3. `sqlite3 public/data/ui.db "SELECT word, definition FROM words WHERE word IN ('gad','mofluzită','ospătător') LIMIT 10"` — all three have non-null definitions
4. Open UI in browser, search those words, confirm definitions appear
