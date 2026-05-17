# Spec: Loanword Exclusion Filter + has_definition Column

**Date:** 2026-05-17
**Scope:** Backlog #12 (loanword exclusion) + Backlog #17 (flag no-definition words)

---

## Background

Two gaps remain after the etymology tag enrichment work (backlog #16):

1. **#17** — Words with no definition body in the DEX dump (e.g. *nombrilist* — dexonline renders these as "[Fără definiție.]") pass through the pipeline and appear in the shortlist. There is no column in the diachronic CSV or shortlist CSV that flags them; the UI `has_def` filter works at runtime but relies on `definitions.db` which may be incomplete.

2. **#12** — Modern loanwords (anglicisms, Gallicisms, etc.) inflate the false-positive rate. A word being a recent borrowing is a legitimate reason to deprioritize it as "forgotten" — it was never native to begin with. The `dex_etymology` column already carries the data; there is no mechanism to exclude these words.

---

## What is already done

- `#19` — UI filter rows for register, domain, etymology, has_def: **already implemented**.
- `#22` — One-key quick-tags (i/B/f/x), keyboard shortcuts, datalist autocomplete: **already implemented**.

---

## Design

### Part 1 — has_definition column (#17)

**`validate_diachronic.py`**

At startup, if `definitions.db` exists, load the set of words that have a non-empty definition:

```python
def _load_definition_words(db_path: Path) -> set[str]:
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT word FROM definitions WHERE definition IS NOT NULL AND definition != ''"
    ).fetchall()
    conn.close()
    return {r[0] for r in rows}
```

Add `has_definition` (integer 1/0) to the output CSV. Words not in the set, or when `definitions.db` is absent, get `0`. Column goes after `dex_etymology`.

**`make_shortlist.py`**

Add `has_definition` to `OUT_FIELDS` so it flows through to `forgotten_words_shortlist.csv`. No other logic changes needed — the column is already present in the diachronic CSV and `csv.DictReader` will pass it through via `row.get('has_definition', '')`.

**`ui/app.py` — load_words()**

`load_words()` uses a named-column INSERT, so `has_definition` must be added explicitly:
- Add `has_definition INTEGER` to the `CREATE TABLE words` schema
- Add `has_definition` to the INSERT column list and values tuple, reading `_bool(row.get('has_definition', ''))`

The existing runtime `definition IS NOT NULL` filter in `/search` is unaffected. The new column enables offline analysis of the CSV independently of `definitions.db`.

---

### Part 2 — Shortlist loanword exclusion (#12a)

**`make_shortlist.py`**

New CLI flag:

```
--exclude-etymology TAGS   Comma-separated etymology tags to exclude.
                           E.g. --exclude-etymology anglicism,franțuzism
                           Default: empty (no exclusion).
```

In `classify()`, add an early return:

```python
def classify(row: dict, exclude_etym: set[str]) -> str | None:
    etym_tags = {t.strip() for t in row['dex_etymology'].split('|') if t.strip()}
    if etym_tags & exclude_etym:
        return None
    ...
```

Pass `exclude_etym` (a `set[str]`) from `main()` into `classify()`. Stats output gets a new line: `Excluded (etymology) N`.

---

### Part 3 — UI exclusion filter row (#12b)

**`app.py`**

In `/search`, gather exclusion values:

```python
exclude_etym = request.args.getlist('exclude_etym')
```

For each value, add a NOT LIKE condition (reuses the same pipe-padding logic as the include filters):

```python
for val in exclude_etym:
    conditions.append("NOT ('|'||dex_etymology||'|' LIKE ?)")
    params.append(f'%|{val}|%')
```

The `index()` route already passes `distinct_etymologies` to the template — no change needed there.

**`base.html`**

Add a sixth filter row after the existing etymology row:

```html
<!-- Row 6: exclude etymologies (multi-select checkboxes) -->
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

CSS for `pill-excl:has(input:checked)` uses a red active state to distinguish from the blue include pills:

```css
.pill-excl:has(input:checked) {
  background: #fff1f0;
  color: #9a1313;
  font-weight: 700;
  border-color: #f87171;
  box-shadow: 0 0 0 1px #f87171;
}
```

The existing deselect-on-reclick JS block applies to `input[type=radio]` only, so no change needed for the new checkboxes.

**Edge case:** Selecting the same etymology in both include and exclude produces empty results (SQL: `WHERE dex_etymology LIKE '%|X|%' AND NOT dex_etymology LIKE '%|X|%'`). Self-correcting; no JS guard needed.

**Shortcuts modal:** No changes — the new row is purely filter UI.

---

## Data flow

```
validate_diachronic.py  →  forgotten_words_diachronic.csv  (+ has_definition column)
                                    ↓
                          make_shortlist.py --exclude-etymology ...
                                    ↓
                          forgotten_words_shortlist.csv  (+ has_definition column)
                                    ↓
                          ui/app.py  load_words()  (has_definition already in words table via CSV)
                                    ↓
                          /search  (exclude_etym conditions + existing has_def filter)
```

---

## Files changed

| File | Change |
|------|--------|
| `validate_diachronic.py` | Add `_load_definition_words()`, add `has_definition` column to CSV output |
| `make_shortlist.py` | Add `has_definition` to `OUT_FIELDS`; add `--exclude-etymology` flag; update `classify()` signature |
| `ui/app.py` | Add `has_definition` to table schema + INSERT; add `exclude_etym` getlist + NOT LIKE conditions in `/search` |
| `ui/templates/base.html` | Add filter row 6 (exclude checkboxes) + `.pill-excl` CSS |

---

## Out of scope

- Re-running `validate_diachronic.py` on the VPS (corpus re-runs are a separate backlog item).
- Changing the include etymology row from radio to checkbox (not requested).
- Persisting the exclusion set across sessions (filter state is not persisted for any filter today).
