# Has-Definition Filter — Design Spec

**Date:** 2026-05-15  
**Status:** Approved  
**Backlog:** #19 (partial — "Has definition toggle" bullet)

## Problem

Some DEX entries are headword stubs with no meaning text — inflected forms, bare infinitives, or entries dexonline renders as "[Fără definiție.]" (e.g. *abecedare*, *nombrilist*). These appear in the candidate list because they pass the Lexeme filter, but clicking them shows no local definition and the only useful action is opening dexonline.ro. Researchers need to audit this set and/or exclude it.

## Solution

Add a tri-state `<select>` to the filter bar: **all definitions** / **has definition** / **no definition**. Matches the existing verdict/tier dropdown pattern exactly.

## Architecture

### Backend — `ui/app.py`

In the `/search` route, read `has_def = request.args.get('has_def', '').strip()` and append to the existing `conditions` / `params` lists:

```python
if has_def == '1':
    conditions.append('definition IS NOT NULL')
elif has_def == '0':
    conditions.append('definition IS NULL')
```

No schema change. The `definition TEXT` column already exists in the in-memory `words` table and is `NULL` for words with no extracted definition.

### Frontend — `ui/templates/base.html`

Add one `<select>` to `#filter-form`, after the tier select:

```html
<select name="has_def"
        hx-get="/search"
        hx-trigger="change"
        hx-target="#word-list"
        hx-include="#filter-form">
  <option value="">all definitions</option>
  <option value="1">has definition</option>
  <option value="0">no definition</option>
</select>
```

## Scope

- **Files changed:** `ui/app.py` (~4 lines), `ui/templates/base.html` (~7 lines)
- **No new files, no CSS additions, no data pipeline changes**
- No new tests required — the existing filter pattern is already untested; adding a test here would be out of scope

## Out of scope

- Adding a `has_definition` column to the CSV files (BACKLOG #17 — separate task)
- Persisting filter state across page loads
- Any changes to how `extract_definitions.py` populates `definitions.db`
