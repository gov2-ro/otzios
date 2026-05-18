# Marks Filter & Annotation Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `show_removed` checkbox with a `marks` dropdown that defaults to hiding all annotated words, and add emoji overlays on annotated word chips when they are visible.

**Architecture:** Backend gains a `marks` query param (default `unmarked`) that filters the word list by annotation state; a new `_is_marked()` helper centralises the "any annotation" check. Frontend gets a `tax-select` dropdown in the filter bar and an absolutely-positioned emoji overlay inside each word chip.

**Tech Stack:** Flask, Jinja2, htmx, vanilla JS, SQLite (in-memory + research.db)

---

## File Map

| File | Change |
|---|---|
| `ui/app.py` | Remove `show_removed`; add `marks` param + `_is_marked()`; expose `tags` list per word |
| `ui/templates/base.html` | Replace pill with `marks` select; update tax-select JS; swap `.annotated::after` CSS for `.ann-overlay` |
| `ui/templates/partials/word_row.html` | Remove `annotated` class logic; add `ann-overlay` span with emoji mapping |

---

## Task 1: Backend — `marks` filter + `tags` in word dict

**Files:**
- Modify: `ui/app.py`

- [ ] **Step 1: Add `_is_marked` helper above the `/search` route**

Find the `_bookmarks_map` function (around line 218). Add this immediately after it:

```python
def _is_marked(word: str, bmap: dict) -> bool:
    bm = bmap.get(word, {})
    return bool(
        bm.get('bookmarked')
        or (bm.get('note') or '').strip()
        or (bm.get('tags') or '').strip()
    )
```

- [ ] **Step 2: Replace `show_removed` with `marks` in the route parameters**

In `search()`, find these two lines (around line 238–239):

```python
bookmarked_only = request.args.get('bookmarked', '') == '1'
show_removed    = request.args.get('show_removed', '') == '1'
```

Replace with:

```python
bookmarked_only = request.args.get('bookmarked', '') == '1'
marks           = request.args.get('marks', 'unmarked').strip()
```

- [ ] **Step 3: Replace the filtering blocks**

Find the two filtering blocks after `bmap = _bookmarks_map()` and the SQL query (around lines 270–283):

```python
if bookmarked_only:
    all_rows = [r for r in all_rows if bmap.get(r['word'], {}).get('bookmarked')]

if not show_removed:
    removed = {
        w for w, bm in bmap.items()
        if 'remove' in [t.strip() for t in (bm.get('tags') or '').split(',') if t.strip()]
    }
    if removed:
        all_rows = [r for r in all_rows if r['word'] not in removed]
```

Replace with:

```python
if bookmarked_only:
    all_rows = [r for r in all_rows if bmap.get(r['word'], {}).get('bookmarked')]
else:
    if marks in ('', 'unmarked'):
        all_rows = [r for r in all_rows if not _is_marked(r['word'], bmap)]
    elif marks == 'marked':
        all_rows = [r for r in all_rows if _is_marked(r['word'], bmap)]
    elif marks == 'noted':
        all_rows = [r for r in all_rows
                    if (bmap.get(r['word'], {}).get('note') or '').strip()]
    elif marks.startswith('tag:'):
        tag_filter = marks[4:]
        all_rows = [r for r in all_rows
                    if tag_filter in [t.strip() for t in
                                      (bmap.get(r['word'], {}).get('tags') or '').split(',')
                                      if t.strip()]]
    # marks == 'all' → no filtering
```

- [ ] **Step 4: Replace `has_tags` with `tags` in the word dict loop**

Find the word dict building loop (around lines 288–295):

```python
    d['bookmarked'] = bool(bm.get('bookmarked'))
    d['has_note']   = bool((bm.get('note') or '').strip())
    d['has_tags']   = bool((bm.get('tags') or '').strip())
```

Replace with:

```python
    d['bookmarked'] = bool(bm.get('bookmarked'))
    d['has_note']   = bool((bm.get('note') or '').strip())
    d['tags']       = [t.strip() for t in (bm.get('tags') or '').split(',') if t.strip()]
```

- [ ] **Step 5: Start the app and confirm it loads without errors**

```bash
cd /Users/pax/devbox/otios
source ~/g2-dev/monitorulpreturilor/venv/bin/activate
python -c "from ui.app import init_app, app; init_app(); print('OK')"
```

Expected: `OK` with no tracebacks.

- [ ] **Step 6: Commit**

```bash
git add ui/app.py
git commit -m "feat(ui): marks filter — backend param + _is_marked helper"
```

---

## Task 2: Filter bar — replace `show removed` pill with `marks` select

**Files:**
- Modify: `ui/templates/base.html`

- [ ] **Step 1: Replace the `show removed` pill**

Find this block in `base.html` Row 1 (around line 900):

```html
      <label class="pill" title="Show words tagged 'remove'">
        <input type="checkbox" name="show_removed" value="1">
        show removed
      </label>
```

Replace with:

```html
      <select name="marks" class="tax-select" data-default="unmarked" aria-label="Marks filter">
        <option value="unmarked">unmarked only</option>
        <option value="all">all words</option>
        <option value="marked">marked only</option>
        <option value="noted">has note</option>
        {% for t, _ in quick_tags %}
        <option value="tag:{{ t }}">tag: {{ t }}</option>
        {% endfor %}
        {% for t in tag_suggestions %}
        <option value="tag:{{ t }}">tag: {{ t }}</option>
        {% endfor %}
      </select>
```

- [ ] **Step 2: Update the tax-select JS to respect `data-default`**

Find this JS block near the bottom of `base.html` (around line 1197):

```javascript
    document.querySelectorAll('.tax-select').forEach(function(sel) {
      function update() { sel.classList.toggle('active', sel.value !== ''); }
      sel.addEventListener('change', update);
      sel.form && sel.form.addEventListener('reset', update);
      update();
    });
```

Replace with:

```javascript
    document.querySelectorAll('.tax-select').forEach(function(sel) {
      var dflt = sel.dataset.default !== undefined ? sel.dataset.default : '';
      function update() { sel.classList.toggle('active', sel.value !== dflt); }
      sel.addEventListener('change', update);
      sel.form && sel.form.addEventListener('reset', update);
      update();
    });
```

- [ ] **Step 3: Verify in browser**

Start the app:
```bash
cd /Users/pax/devbox/otios
source ~/g2-dev/monitorulpreturilor/venv/bin/activate
python ui/app.py
```

Open `http://localhost:5000`. Check:
- Row 1 shows a `marks` dropdown where `show removed` was
- Default selection is `unmarked only`
- Selecting `all words` highlights the dropdown with the `.active` accent style
- Switching back to `unmarked only` removes the highlight
- The existing register/domain/etymology selects still highlight correctly when non-empty

- [ ] **Step 4: Commit**

```bash
git add ui/templates/base.html
git commit -m "feat(ui): marks filter — dropdown replaces show-removed pill"
```

---

## Task 3: CSS — swap `.annotated::after` dot for `.ann-overlay`

**Files:**
- Modify: `ui/templates/base.html`

- [ ] **Step 1: Remove the `.annotated::after` CSS block**

Find this CSS block (around line 346):

```css
    /* Annotated dot — word has a note or tag */
    .word-row.annotated::after {
      content: '';
      position: absolute;
      top: 2px;
      right: 2px;
      width: 4px;
      height: 4px;
      border-radius: 50%;
      background: var(--accent);
      opacity: .55;
    }
    .word-row[data-selected].annotated::after { background: rgba(255,255,255,.85); opacity: 1; }
```

Delete it entirely.

- [ ] **Step 2: Add `.ann-overlay` CSS**

Directly after the `.chip-freq` block (around line 374), add:

```css
    /* Annotation emoji overlay — absolute, hugs top-right corner of chip */
    .ann-overlay {
      position: absolute;
      top: 1px;
      right: 2px;
      font-size: 9px;
      line-height: 1;
      letter-spacing: -1px;
      pointer-events: none;
      user-select: none;
    }
```

- [ ] **Step 3: Commit**

```bash
git add ui/templates/base.html
git commit -m "feat(ui): ann-overlay CSS replaces annotated dot"
```

---

## Task 4: Word row template — emoji overlay

**Files:**
- Modify: `ui/templates/partials/word_row.html`

- [ ] **Step 1: Replace the entire template**

The current file is 14 lines. Replace it in full with:

```html
{% set _is_inv = w.dex_register and 'învechit' in w.dex_register %}
{% set _emoji = {'ignore': '🙈', 'boring': '💤', 'funny': '😄', 'remove': '❌'} %}
{% set _ov = namespace(s='') %}
{% for t in (w.tags or []) %}{% set _ov.s = _ov.s + _emoji.get(t, '🏷️') %}{% endfor %}
{% if w.has_note %}{% set _ov.s = _ov.s + '📝' %}{% endif %}
{% if w.bookmarked %}{% set _ov.s = _ov.s + '⭐' %}{% endif %}
<div class="word-row verdict-{{ (w.verdict or 'unknown') | replace(' ', '_') }}{% if w.word | length >= 11 %} word-wide{% endif %}{% if w.bookmarked %} bookmarked{% endif %}{% if _is_inv %} inv{% endif %}"
     data-verdict="{{ w.verdict or 'unknown' }}"
     data-pos="{{ (w.dex_pos or '').split('|')[0] }}"
     data-freq="{{ (w.dex_frequency * 100) | round | int if w.dex_frequency is not none else '' }}"
     data-def="{{ (w.definition or '')[:120] }}"
     {% if _is_inv %}title="învechit"{% endif %}
     hx-get="/word/{{ w.word | urlencode }}"
     hx-target="#detail-panel"
     hx-swap="innerHTML">
  <span class="word-text">{{ w.word }}</span>
  {% if w.dex_frequency is not none %}<span class="chip-freq">{{ (w.dex_frequency * 100) | round | int }}</span>{% endif %}
  {% if _ov.s %}<span class="ann-overlay">{{ _ov.s }}</span>{% endif %}
</div>
```

Key changes from previous version:
- `_annotated` variable and `annotated` CSS class removed
- `has_tags` reference removed (uses `w.tags` list instead)
- Emoji mapping dict `_emoji` for quick tags; falls back to `🏷️` for custom tags
- Note adds `📝`, bookmark adds `⭐` after tag emojis
- `ann-overlay` span rendered only when `_ov.s` is non-empty

- [ ] **Step 2: Verify in browser**

With the app running at `http://localhost:5000`:

1. Select `all words` from the marks dropdown — the full word list appears
2. Words that have been bookmarked, tagged, or noted should show a tiny emoji in their top-right corner (e.g. `❌` for remove-tagged, `⭐` for bookmarked, `📝` for noted)
3. Switch back to `unmarked only` — annotated words disappear; no overlays visible since no annotated words remain
4. Select `marked only` — only annotated words, all with overlays
5. Select `has note` — only words with notes, each showing at least `📝`
6. Select `tag: remove` — only remove-tagged words, each showing `❌`
7. Open a word detail, add a tag, close — re-trigger the filter; the overlay should reflect the new tag

- [ ] **Step 3: Commit**

```bash
git add ui/templates/partials/word_row.html
git commit -m "feat(ui): emoji annotation overlay on word chips"
```

---

## Self-review checklist (executor: skip this section)

- `marks` dropdown: ✓ Task 2  
- Default hides annotated words: ✓ Task 1 Step 3 (`unmarked` branch)  
- Show all / marked only / noted / tag:* modes: ✓ Task 1 Step 3  
- `bookmarked=1` bypasses marks filter: ✓ Task 1 Step 3 (if/else structure)  
- Emoji overlay on annotated chips: ✓ Task 4  
- Overlay position (absolute, no width extension): ✓ Task 3 + Task 4  
- Remove `.annotated::after` dot: ✓ Task 3 Step 1  
- Remove `has_tags` from word dict: ✓ Task 1 Step 4  
- `data-default` JS extension for tax-select active state: ✓ Task 2 Step 2  
- Custom tags from `tag_suggestions` in dropdown: ✓ Task 2 Step 1  
