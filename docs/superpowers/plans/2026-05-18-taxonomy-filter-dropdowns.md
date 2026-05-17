# Taxonomy Filter Dropdowns Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the four pill rows (register, domain, etymology include, etymology exclude) in the research UI filter bar with a single compact row of three `<select>` dropdowns.

**Architecture:** Two files change — `ui/app.py` for server-side data prep, `ui/templates/base.html` for the template and styles. The HTMX form wiring and `/search` filter logic are largely untouched; `<select>` change events bubble to the form and trigger the existing handler.

**Tech Stack:** Flask, Jinja2, HTMX, vanilla JS, SQLite in-memory

---

### Task 1: Server-side — add `_ETYM_JUNK`, update `_distinct_split`, clean up `/search`

**Files:**
- Modify: `ui/app.py`

No test suite exists in this project. Verification is via manual curl + browser (Task 3).

- [ ] **Step 1: Add `_ETYM_JUNK` constant just above `_distinct_split`**

  In `ui/app.py`, find the line `def _distinct_split(` (~line 201) and insert immediately before it:

  ```python
  _ETYM_JUNK = {'vezi', 'cf.', 'după', 'după unii', 'probabil', 'cuvânt', 'necunoscută'}
  ```

- [ ] **Step 2: Add `exclude` parameter to `_distinct_split`**

  Replace the existing function body (lines 201–212):

  ```python
  def _distinct_split(column: str, sep: str = '|', limit: int | None = None, exclude: set | None = None) -> list[str]:
      from collections import Counter
      rows = _words_db.execute(
          f'SELECT {column} FROM words WHERE {column} IS NOT NULL'
      ).fetchall()
      counts: Counter = Counter()
      for (v,) in rows:
          for part in v.split(sep):
              p = part.strip()
              if p and (exclude is None or p not in exclude):
                  counts[p] += 1
      return [v for v, _ in counts.most_common(limit)]
  ```

- [ ] **Step 3: Update `index()` — remove limits, pass exclude for etymology**

  In the `index()` route (~line 322), replace the three `_distinct_split` keyword arguments:

  ```python
  distinct_registers   = _distinct_split('dex_register'),
  distinct_domains     = _distinct_split('dex_domain'),
  distinct_etymologies = _distinct_split('dex_etymology', exclude=_ETYM_JUNK),
  ```

  The `limit=` keyword is gone from all three calls.

- [ ] **Step 4: Remove `exclude_etym` from `/search`**

  In the `search()` route (~line 226), remove this line:

  ```python
  exclude_etym    = request.args.getlist('exclude_etym')
  ```

  And remove this block (~line 258):

  ```python
  for val in exclude_etym:
      conditions.append("NOT ('|'||COALESCE(dex_etymology,'')||'|' LIKE ?)")
      params.append(f'%|{val}|%')
  ```

- [ ] **Step 5: Commit**

  ```bash
  git add ui/app.py
  git commit -m "feat(ui): compact taxonomy selects — server side"
  ```

---

### Task 2: Template — remove pill rows, add select row, add CSS + JS

**Files:**
- Modify: `ui/templates/base.html`

- [ ] **Step 1: Remove rows 3–6 (the four pill rows)**

  Delete everything from `<!-- Row 3: register -->` through the closing `</div>` of `<!-- Row 6: exclude etymologies ... -->` (lines 925–964). Leave `</form>` (line 966) in place.

  After deletion, the `</form>` tag should immediately follow the closing `</div>` of Row 2.

- [ ] **Step 2: Insert new Row 3 — taxonomy selects**

  Insert directly before `</form>`:

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

  </form>
  ```

- [ ] **Step 3: Add `.tax-select` CSS**

  In the `<style>` block, add after the `.sort-select` block (~line 153):

  ```css
  /* Taxonomy filter selects */
  .tax-select {
    height: var(--chip-h);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-2);
    padding: 0 6px;
    font-family: var(--sans);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: border-color .15s, color .15s, box-shadow .15s;
  }
  .tax-select:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(26,86,219,.15);
  }
  .tax-select:hover { background: #f4f1eb; color: var(--text); }
  .tax-select.active {
    border-color: var(--accent);
    color: var(--accent);
    font-weight: 700;
    box-shadow: 0 0 0 1px var(--accent);
  }
  ```

- [ ] **Step 4: Remove `.pill-excl` CSS**

  Delete the `.pill-excl` rule block (~line 249):

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

- [ ] **Step 5: Add active-state JS for `.tax-select`**

  In the `<script>` block, add before the closing `</script>` tag:

  ```javascript
  // Highlight tax-select when a non-"any" value is active
  document.querySelectorAll('.tax-select').forEach(function(sel) {
    function update() { sel.classList.toggle('active', sel.value !== ''); }
    sel.addEventListener('change', update);
    update();
  });
  ```

- [ ] **Step 6: Commit**

  ```bash
  git add ui/templates/base.html
  git commit -m "feat(ui): compact taxonomy selects — template, CSS, JS"
  ```

---

### Task 3: Verify end-to-end

**Files:** none

- [ ] **Step 1: Start the app**

  ```bash
  cd /Users/pax/devbox/otios
  source .venv/bin/activate
  cd ui && python app.py
  ```

  Expected: `* Running on http://127.0.0.1:5000`

- [ ] **Step 2: Verify the index route passes taxonomy variables**

  ```bash
  curl -s http://localhost:5000/ | grep -c 'tax-select'
  ```

  Expected: `3` (three `<select class="tax-select">` elements)

- [ ] **Step 3: Verify domain dropdown contains all options**

  ```bash
  curl -s http://localhost:5000/ | grep -o 'medicin\|botan\|chimie\|geolog' | wc -l
  ```

  Expected: `4` (all four terms found in the domain select)

- [ ] **Step 4: Verify etymology junk is absent**

  ```bash
  curl -s http://localhost:5000/ | grep -c '>vezi<\|>cf\.<\|>după<\|>probabil<'
  ```

  Expected: `0`

- [ ] **Step 5: Verify search filtering works**

  ```bash
  curl -s 'http://localhost:5000/search?domain=medicin%C4%83' | grep -c 'word-row'
  ```

  Expected: a positive integer (filtered word chips returned)

  ```bash
  curl -s 'http://localhost:5000/search?etymology=limba+franc%CC%A7uzeasc%C4%83' | grep -c 'word-row'
  ```

  Wait — etymology values are stored as "limba franceză" but displayed without "limba ". Verify the option `value` in the HTML source matches what `/search` expects (the full stored value, e.g. "limba franceză"), not the display label:

  ```bash
  curl -s http://localhost:5000/ | grep -A1 'etymology: any' | head -5
  ```

  Confirm `<option value="limba franceză">franceză</option>` — value is full stored string, label is stripped.

- [ ] **Step 6: Open browser and visually verify**

  Open http://localhost:5000 and confirm:
  - Filter bar has 3 rows (search row, verdict/tier/POS row, filter select row)
  - No pill rows for register/domain/etymology
  - Selecting "medicină" from the domain dropdown updates the word grid
  - The active select gets a blue border
  - Resetting to "domain: any" clears the blue border and shows all words

- [ ] **Step 7: Commit verification notes (optional)**

  If any bugs were found and fixed, commit the fixes with a descriptive message. Otherwise done.
