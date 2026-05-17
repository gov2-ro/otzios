# Taxonomy Filter Dropdowns — Design Spec

**Date:** 2026-05-18  
**Status:** Approved

---

## Background

The research UI filter bar has six rows. Rows 3–6 were pill-based filters for `dex_register`, `dex_domain`, `dex_etymology` (include), and `dex_etymology` (exclude). These rows were unreliable before the taxonomy join fix (2026-05-18). Now that the join is correct and `validate_diachronic.py` has been re-run, the data is trustworthy — but the pill layout doesn't scale:

- `dex_domain` has 101 distinct values; 15 pills is an arbitrary truncation
- `dex_etymology` has 58 distinct values, ~10 of which are parsing artifacts ("vezi", "cf.", "după", "probabil", "cuvânt") rather than language-of-origin labels
- `dex_register` has 42 distinct values; pills fit but the row is long

## Goal

Replace the four pill rows (register, domain, etymology include, etymology exclude) with a single compact row of three `<select>` dropdowns, reducing the filter bar from 6 rows to 3 rows while enabling full access to all taxonomy values.

---

## Changes

### 1. `ui/app.py`

**`_distinct_split()`** — add an optional `exclude` parameter (set of strings). Values in the exclusion set are dropped before returning. No change to callers that don't pass it.

```python
def _distinct_split(column, sep='|', limit=None, exclude=None):
```

**Etymology junk list** — define at module level:

```python
_ETYM_JUNK = {'vezi', 'cf.', 'după', 'după unii', 'probabil', 'cuvânt', 'necunoscută'}
```

**`index()` route** — update the three taxonomy `_distinct_split` calls:
- Remove `limit=` caps from all three (selects handle 100+ options; arbitrary truncation no longer needed)
- Pass `exclude=_ETYM_JUNK` to the etymology call
- Rename template variable `distinct_etymologies` → keep as-is (template already strips "limba " prefix via Jinja filter)

### 2. `ui/templates/base.html`

**Remove** filter rows 3, 4, 5, 6 (the four pill rows for register, domain, etymology, exclude-etymology).

**Add** a new row 3 — a `<select>`-based taxonomy row — between the tier/POS row and the end of `#filter-form`:

```html
<!-- Row 3: taxonomy selects -->
<div class="filter-row">
  <span class="flabel">filter</span>

  <select name="register" class="tax-select">
    <option value="">register: any</option>
    {% for r in distinct_registers %}
    <option value="{{ r }}">{{ r }}</option>
    {% endfor %}
  </select>

  <select name="domain" class="tax-select">
    <option value="">domain: any</option>
    {% for d in distinct_domains %}
    <option value="{{ d }}">{{ d }}</option>
    {% endfor %}
  </select>

  <select name="etymology" class="tax-select">
    <option value="">etymology: any</option>
    {% for e in distinct_etymologies %}
    <option value="{{ e }}">{{ e | replace('limba ', '') }}</option>
    {% endfor %}
  </select>

</div>
```

**CSS** — add `.tax-select` styles:
- Matches existing `.sort-select` appearance (height: `var(--chip-h)`, border, font, etc.)
- Active state: when the select has a non-empty value, border-color and color shift to `var(--accent)` — applied via a small JS snippet that listens for `change` events on `.tax-select` elements and toggles an `active` class, with CSS `.tax-select.active { border-color: var(--accent); color: var(--accent); font-weight: 700; }`

**Remove** the `pill-excl` CSS class and related exclude-etymology JS (the radio deselect-on-reclick JS remains, since verdict/tier/POS pills still use it).

**Option counts** — not included in the initial implementation. The full value set is available in the open dropdown; counts would require changes to `_distinct_split` return type. Defer to a follow-up if needed.

### 3. `ui/app.py` — `/search` route

No changes needed. The route already reads `register`, `domain`, and `etymology` from `request.args` and applies LIKE-based filtering. Removing `exclude_etym` from the template means it will always be an empty list — the existing `for val in exclude_etym` loop is a no-op but harmless. Clean it up while touching the file.

---

## What does not change

- Row 1 (search / sort / bookmarked / has_def)
- Row 2 (verdict / tier / POS pills)
- The HTMX wiring (`hx-get="/search" hx-trigger="change"`) — `<select>` change events bubble to the form and trigger the existing handler
- The `/search` route logic for register, domain, etymology (include)
- All other UI behaviour (keyboard shortcuts, detail panel, hover box, bookmarks, tags)

---

## Out of scope

- Exclude-etymology (dropped; can be revisited if research workflow needs it)
- Counts next to dropdown options (deferred)
- Collapsible filter rows (deferred)
