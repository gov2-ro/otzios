# UI Enhancements — Definitions, Sort, Shortcuts Popup

> **Status:** Approved for implementation (2026-05-15)

## Context

The research UI (Flask+HTMX, built in the previous session) shows word metadata but no actual dictionary definitions. Researchers want to see what a word meant, sort by how forgotten it is, and have a quick reference for keyboard shortcuts. Three additive changes, all independent.

---

## Feature 1: Word Definitions

### Data pipeline

**New script:** `extract_definitions.py`

Streams `data/dictionaries/dex-database.sql` line by line (never loads the full 1.2 GB into memory). Finds `INSERT INTO DefinitionSimple` rows, cross-references `EntryDefinition` → `Entry` → `Lexeme` to associate each definition with a `formNoAccent`. Writes one output file:

```
data/processed/definitions.db
```

Schema:
```sql
CREATE TABLE definitions (
  word       TEXT PRIMARY KEY,  -- matches Lexeme.formNoAccent
  definition TEXT NOT NULL
);
```

One row per word (first/primary definition only — DEX entries can have multiple). Run once; output is gitignored via existing `data/*` rule.

### App integration

`load_words()` in `ui/app.py`:
- Adds `definition TEXT` column to the `words` CREATE TABLE statement.
- After loading the shortlist CSV, if `data/processed/definitions.db` exists: opens it as a separate connection, fetches all `(word, definition)` rows, then runs `UPDATE words SET definition=? WHERE word=?` for each. SQLite ATTACH cannot be used here because the `words` DB is in-memory.
- Words with no definition keep `definition = NULL`.

`DEFINITIONS_DB_PATH = Path('data/processed/definitions.db')` added as a module-level constant.

### Display

`ui/templates/partials/detail.html` — definition block inserted between the metadata table and the corpus scores table:

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
```

CSS in `base.html`:
```css
.definition-block { background:#1f1f1f; border-left:2px solid #3a3a3a; padding:10px 14px; margin-bottom:12px; border-radius:2px; }
.definition-label { color:#666; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:6px; }
.definition-text { color:#c0c0c0; line-height:1.6; font-size:13px; }
.dex-link { color:#4a8fd4; font-size:11px; text-decoration:none; display:inline-block; margin-top:8px; }
```

---

## Feature 2: Sort by Scarcity

### Route change

`GET /search` in `ui/app.py` — new `sort` query param:

| `sort` value | SQL `ORDER BY` |
|---|---|
| `alpha` (default, empty string) | `word ASC` |
| `declined` | `log_ratio DESC NULLS LAST` |
| `rare` | `modern_ppm ASC NULLS LAST` |
| `dex_freq` | `dex_frequency ASC NULLS LAST` |

The `ORDER BY` is built from a safe allowlist dict — no user string interpolated directly:

```python
SORT_OPTIONS = {
    'declined': 'log_ratio DESC NULLS LAST',
    'rare':     'modern_ppm ASC NULLS LAST',
    'dex_freq': 'dex_frequency ASC NULLS LAST',
}

order_by = SORT_OPTIONS.get(sort, 'word ASC')
```

### Template change

`base.html` filter bar — sort `<select>` added between the tier select and the bookmark checkbox:

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

Same HTMX pattern as existing verdict/tier dropdowns — no new JS needed.

---

## Feature 3: Shortcuts Popup (? key)

### Modal HTML

Added to `base.html` just before `</body>`:

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

### CSS (added to base.html `<style>`)

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

### JS (added to existing keydown handler in base.html)

```javascript
function showShortcuts() {
  document.getElementById('shortcuts-overlay').style.display = 'flex';
}
function hideShortcuts() {
  document.getElementById('shortcuts-overlay').style.display = 'none';
}

// In the keydown handler, before inInput check:
if (e.key === '?') { e.preventDefault(); showShortcuts(); return; }

// In the inInput block, update Escape handler:
if (e.key === 'Escape') {
  hideShortcuts();
  document.activeElement.blur();
  return;
}

// Click-outside to close:
document.getElementById('shortcuts-overlay').addEventListener('click', function(e) {
  if (e.target === this) hideShortcuts();
});
```

Escape in the existing non-input handler also calls `hideShortcuts()`.

---

## File map

| File | Change |
|---|---|
| `extract_definitions.py` | **New** — one-time extraction script |
| `data/processed/definitions.db` | **Generated** — gitignored |
| `ui/app.py` | Add `definition` column + ATTACH join in `load_words()`; add `SORT_OPTIONS` + `sort` param to `GET /search` |
| `ui/templates/base.html` | Add sort `<select>`; add shortcuts modal HTML + CSS + JS |
| `ui/templates/partials/detail.html` | Add definition block |

---

## Verification

```bash
# 1. Extract definitions (one-time)
source /Users/pax/devbox/envs/240826/bin/activate
python extract_definitions.py
# Expected: data/processed/definitions.db created, ~N words with definitions

# 2. Run tests (should all still pass — no routes changed)
python -m pytest tests/test_ui.py -v

# 3. Start server and verify in browser
python ui/app.py
# open http://localhost:5000
# - click a word → definition block appears in detail panel (if word has definition)
# - change sort dropdown → word list reorders without page reload
# - press ? → shortcuts popup appears; Esc closes it; click outside closes it
```
