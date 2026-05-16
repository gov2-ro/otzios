# Full-screen word grid + hover info box — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 50/50 split layout with a full-width word grid; hovering a word shows a compact info box in the top-right corner; clicking a word slides in a detail panel from the right as an overlay.

**Architecture:** All changes are confined to HTML templates — no Python changes needed. Data for the hover box is embedded as `data-*` attributes on each word chip at render time. The slide-in panel is `position: absolute` within `#app` (which gets `position: relative`); it gains class `.panel-open` via JS after HTMX swaps content into it.

**Tech Stack:** Jinja2 templates, CSS transitions, vanilla JS, htmx 2.0

---

### Task 1: Add data-* attributes to word chips

**Files:**
- Modify: `ui/templates/partials/word_row.html`
- Test: `tests/test_ui.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ui.py`:

```python
def test_search_word_row_has_data_attributes(client):
    resp = client.get('/search')
    body = resp.data.decode('utf-8')
    # WORD_A: verdict=extinct, dex_pos=s.f., dex_frequency=0.1 → freq=10
    assert 'data-verdict="extinct"' in body
    assert 'data-pos="s.f."' in body
    assert 'data-freq="10"' in body
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/pax/devbox/otios
source ~/g2-dev/monitorulpreturilor/venv/bin/activate
pytest tests/test_ui.py::test_search_word_row_has_data_attributes -v
```

Expected: FAIL with `AssertionError` (attributes not yet present).

- [ ] **Step 3: Update word_row.html**

Replace the entire contents of `ui/templates/partials/word_row.html` with:

```html
<div class="word-row verdict-{{ (w.verdict or 'unknown') | replace(' ', '_') }}{% if w.bookmarked %} bookmarked{% endif %}"
     data-verdict="{{ w.verdict or 'unknown' }}"
     data-pos="{{ (w.dex_pos or '').split('|')[0] }}"
     data-freq="{{ (w.dex_frequency * 100) | round | int if w.dex_frequency is not none else '' }}"
     data-def="{{ (w.definition or '')[:120] }}"
     hx-get="/word/{{ w.word | urlencode }}"
     hx-target="#detail-panel"
     hx-swap="innerHTML">
  <span class="word-text">{{ w.word }}</span>
  {% if w.dex_register and 'învechit' in w.dex_register %}<span class="chip-meta inv">înv</span>{% endif %}
  {% if w.dex_frequency is not none %}<span class="chip-freq">{{ (w.dex_frequency * 100) | round | int }}</span>{% endif %}
  {% if w.bookmarked %}<span class="star">★</span>{% endif %}
</div>
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_ui.py::test_search_word_row_has_data_attributes -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ui/templates/partials/word_row.html tests/test_ui.py
git commit -m "feat: embed verdict/pos/freq/def as data-attrs on word chips"
```

---

### Task 2: Full-width layout + sliding detail panel (CSS)

**Files:**
- Modify: `ui/templates/base.html` (CSS block only — lines 10–624)
- Test: `tests/test_ui.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ui.py`:

```python
def test_base_has_sliding_panel_css(client):
    resp = client.get('/')
    body = resp.data.decode('utf-8')
    assert 'panel-open' in body
    assert 'translateX' in body
    # word-list-container must not claim 50% width in CSS
    # (we check the new 100% isn't the old 50% split)
    assert 'width: 50%' not in body
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_ui.py::test_base_has_sliding_panel_css -v
```

Expected: FAIL (`width: 50%` is present, `panel-open` not present).

- [ ] **Step 3: Replace layout CSS in base.html**

In `ui/templates/base.html`, find and replace the `TWO-COLUMN BODY` section (the comment and everything through the `#detail-panel` rule). The old block looks like:

```css
    /* ══════════════════════════════════════════
       TWO-COLUMN BODY
    ══════════════════════════════════════════ */
    #app { display: flex; flex: 1; overflow: hidden; }

    /* ── Sidebar ── */
    #word-list-container {
      width: 50%;
      border-right: 1px solid var(--border);
      overflow-y: auto;
      flex-shrink: 0;
      background: var(--bg);
    }
```

Replace the `#app` rule and `#word-list-container` block and then the `#detail-panel` block with:

```css
    /* ══════════════════════════════════════════
       FULL-WIDTH WORD GRID + OVERLAY PANEL
    ══════════════════════════════════════════ */
    #app { display: flex; flex: 1; overflow: hidden; position: relative; }

    /* ── Word list — full width ── */
    #word-list-container {
      width: 100%;
      overflow-y: auto;
      background: var(--bg);
    }
```

Then find the old `#detail-panel` rule:

```css
    /* ── Detail panel ── */
    #detail-panel {
      flex: 1;
      overflow-y: auto;
      padding: 16px 20px;
      background: var(--surface);
    }
```

Replace it with:

```css
    /* ── Detail panel — fixed-width overlay, slides in from right ── */
    #detail-panel {
      position: absolute;
      right: 0;
      top: 0;
      height: 100%;
      width: 420px;
      overflow-y: auto;
      padding: 16px 20px;
      background: var(--surface);
      border-left: 1px solid var(--border);
      box-shadow: -4px 0 20px rgba(0,0,0,.10);
      transform: translateX(110%);
      transition: transform 200ms ease-out;
      z-index: 5;
    }
    #detail-panel.panel-open {
      transform: translateX(0);
    }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_ui.py::test_base_has_sliding_panel_css -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
pytest tests/test_ui.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add ui/templates/base.html tests/test_ui.py
git commit -m "feat: full-width word grid, detail panel becomes right-side overlay"
```

---

### Task 3: Close button + JS panel open/close

**Files:**
- Modify: `ui/templates/partials/detail.html` (add close button)
- Modify: `ui/templates/base.html` (CSS for close button, JS updates)
- Test: `tests/test_ui.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_ui.py`:

```python
def test_word_detail_has_close_button(client):
    resp = client.get('/word/acătării')
    assert b'panel-close' in resp.data

def test_base_has_close_panel_js(client):
    resp = client.get('/')
    body = resp.data.decode('utf-8')
    assert 'closePanel' in body
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ui.py::test_word_detail_has_close_button tests/test_ui.py::test_base_has_close_panel_js -v
```

Expected: both FAIL.

- [ ] **Step 3: Add close button to detail.html**

In `ui/templates/partials/detail.html`, add as the very first line (before `<h2>`):

```html
<button class="panel-close" onclick="closePanel()">✕</button>
```

- [ ] **Step 4: Add close button CSS to base.html**

In `ui/templates/base.html`, find the `/* scrollbar */` comment near the end of the `<style>` block. Insert this block immediately before it:

```css
    /* ── Panel close button ── */
    .panel-close {
      position: absolute;
      top: 10px;
      right: 12px;
      background: none;
      border: none;
      font-size: 16px;
      color: var(--text-3);
      cursor: pointer;
      padding: 2px 6px;
      border-radius: var(--radius);
      line-height: 1;
      transition: color .1s, background .1s;
    }
    .panel-close:hover { color: var(--text); background: #f0ece5; }

```

- [ ] **Step 5: Add closePanel() function to base.html JS**

In `ui/templates/base.html`, find the JS block. Near the top of the `<script>` tag where `showShortcuts` and `hideShortcuts` are defined, add `closePanel` right after them:

Old:
```javascript
    function showShortcuts() { document.getElementById('shortcuts-overlay').style.display = 'flex'; }
    function hideShortcuts() { document.getElementById('shortcuts-overlay').style.display = 'none'; }
```

New:
```javascript
    function showShortcuts() { document.getElementById('shortcuts-overlay').style.display = 'flex'; }
    function hideShortcuts() { document.getElementById('shortcuts-overlay').style.display = 'none'; }
    function closePanel() { document.getElementById('detail-panel').classList.remove('panel-open'); }
```

- [ ] **Step 6: Update the Escape key handler to close panel**

Find:
```javascript
      if (e.key === 'Escape') { hideShortcuts(); return; }
```

Replace with:
```javascript
      if (e.key === 'Escape') { hideShortcuts(); closePanel(); return; }
```

- [ ] **Step 7: Update htmx:afterSwap to open panel**

Find the existing htmx:afterSwap listener:
```javascript
    document.body.addEventListener('htmx:afterSwap', function(e) {
      if (e.detail.target.id === 'word-list') selectedIdx = -1;
    });
```

Replace with:
```javascript
    document.body.addEventListener('htmx:afterSwap', function(e) {
      if (e.detail.target.id === 'word-list') selectedIdx = -1;
      if (e.detail.target.id === 'detail-panel') {
        e.detail.target.classList.add('panel-open');
        var hb = document.getElementById('hover-box');
        if (hb) hb.classList.remove('visible');
      }
    });
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
pytest tests/test_ui.py::test_word_detail_has_close_button tests/test_ui.py::test_base_has_close_panel_js -v
```

Expected: both PASS.

- [ ] **Step 9: Run full test suite**

```bash
pytest tests/test_ui.py -v
```

Expected: all tests pass.

- [ ] **Step 10: Commit**

```bash
git add ui/templates/partials/detail.html ui/templates/base.html tests/test_ui.py
git commit -m "feat: panel open/close via JS; close button in detail header"
```

---

### Task 4: Hover info box (HTML + CSS + JS)

**Files:**
- Modify: `ui/templates/base.html` (HTML inside `#app`, CSS block, JS block)
- Test: `tests/test_ui.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_ui.py`:

```python
def test_base_has_hover_box(client):
    resp = client.get('/')
    body = resp.data.decode('utf-8')
    assert 'id="hover-box"' in body
    assert 'id="hb-word"' in body
    assert 'id="hb-def"' in body
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_ui.py::test_base_has_hover_box -v
```

Expected: FAIL.

- [ ] **Step 3: Add hover box HTML inside #app**

In `ui/templates/base.html`, find the `<div id="app">` opening tag and the `<div id="word-list-container">` that immediately follows it. Insert the hover box between them:

Old:
```html
  <div id="app">
    <div id="word-list-container">
```

New:
```html
  <div id="app">
    <div id="hover-box">
      <div id="hb-word"></div>
      <div id="hb-verdict-row">
        <span id="hb-verdict" class="verdict-badge"></span>
        <span id="hb-meta"></span>
      </div>
      <div id="hb-def"></div>
    </div>
    <div id="word-list-container">
```

- [ ] **Step 4: Add hover box CSS to base.html**

In the `<style>` block, immediately before the `/* scrollbar */` comment (after the `.panel-close` block from Task 3), add:

```css
    /* ── Hover info box ── */
    #hover-box {
      position: absolute;
      top: 8px;
      right: 8px;
      width: 260px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 6px;
      box-shadow: 0 4px 16px rgba(0,0,0,.10);
      padding: 12px 14px;
      pointer-events: none;
      opacity: 0;
      transform: translateY(-4px);
      transition: opacity 120ms ease, transform 120ms ease;
      z-index: 4;
    }
    #hover-box.visible {
      opacity: 1;
      transform: translateY(0);
    }
    #hb-word {
      font-family: var(--serif);
      font-size: 1.4em;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 6px;
      line-height: 1.1;
    }
    #hb-verdict-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }
    #hb-meta {
      font-size: 12px;
      color: var(--text-3);
      font-family: var(--mono);
    }
    #hb-def {
      font-family: var(--serif);
      font-style: italic;
      font-size: 12px;
      color: var(--text-2);
      line-height: 1.5;
      -webkit-mask-image: linear-gradient(to bottom, black 70%, transparent 100%);
      mask-image: linear-gradient(to bottom, black 70%, transparent 100%);
      max-height: 60px;
      overflow: hidden;
    }

```

- [ ] **Step 5: Add hover box JS to base.html**

At the end of the `<script>` block (before `</script>`), add:

```javascript
    // Hover info box — event delegation on document, no per-row listeners needed
    (function() {
      var box    = document.getElementById('hover-box');
      var hbWord = document.getElementById('hb-word');
      var hbVerd = document.getElementById('hb-verdict');
      var hbMeta = document.getElementById('hb-meta');
      var hbDef  = document.getElementById('hb-def');
      var panel  = document.getElementById('detail-panel');

      document.addEventListener('mouseover', function(e) {
        var row = e.target.closest('.word-row');
        if (!row || panel.classList.contains('panel-open')) return;
        var verdict = row.dataset.verdict || 'unknown';
        hbWord.textContent = row.querySelector('.word-text').textContent;
        hbVerd.textContent = verdict;
        hbVerd.className = 'verdict-badge vb-' + verdict.replace(/ /g, '_');
        var parts = [];
        if (row.dataset.pos)  parts.push(row.dataset.pos);
        if (row.dataset.freq) parts.push('dex ' + row.dataset.freq);
        hbMeta.textContent = parts.join(' · ');
        if (row.dataset.def) {
          hbDef.textContent = row.dataset.def;
          hbDef.style.display = '';
        } else {
          hbDef.style.display = 'none';
        }
        box.classList.add('visible');
      });

      document.addEventListener('mouseout', function(e) {
        var row = e.target.closest('.word-row');
        if (!row) return;
        var to = e.relatedTarget;
        if (to && row.contains(to)) return;
        box.classList.remove('visible');
      });
    })();
```

- [ ] **Step 6: Run test to verify it passes**

```bash
pytest tests/test_ui.py::test_base_has_hover_box -v
```

Expected: PASS.

- [ ] **Step 7: Run full test suite**

```bash
pytest tests/test_ui.py -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add ui/templates/base.html tests/test_ui.py
git commit -m "feat: hover info box — top-right compact word metadata on mouseover"
```

---

### Task 5: Manual smoke test in browser

- [ ] **Step 1: Start the dev server**

```bash
cd /Users/pax/devbox/otios
source ~/g2-dev/monitorulpreturilor/venv/bin/activate
python ui/app.py
```

- [ ] **Step 2: Verify full-width word grid**

Open `http://localhost:5000` in a browser. Confirm the word list spans the full viewport width with no right-side panel visible.

- [ ] **Step 3: Verify hover box**

Move the mouse over any word chip. Confirm the top-right info box appears showing the word name, verdict badge, POS, DEX frequency, and definition excerpt (if available). Confirm it disappears when the mouse leaves.

- [ ] **Step 4: Verify slide-in panel**

Click any word. Confirm the detail panel slides in from the right (overlaying the word grid). Confirm the `✕` button closes it. Confirm pressing `Escape` also closes it. Confirm clicking a different word loads new content while keeping the panel open.

- [ ] **Step 5: Verify hover box hides while panel is open**

With the panel open, move the mouse over word chips. Confirm the hover box does NOT appear.

- [ ] **Step 6: Verify existing keyboard shortcuts**

Test: `j`/`k` to navigate words, `/` to focus search, `b` to bookmark, `?` to show shortcuts modal. Confirm all still work.
