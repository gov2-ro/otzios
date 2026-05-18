# UI polish pass — design spec

**Status:** Approved 2026-05-18 · brainstorm session `88153-1779098654`
**Scope:** `ui/templates/base.html` + `ui/templates/partials/word_row.html`. No route changes. No structural changes to HTMX wiring, filter form, or keyboard navigation.

## Context

The word-grid UI works structurally but reads as a generic dashboard. Inter Tight is a default-of-defaults font, the four verdict colors compete at equal saturation, pure-white background feels harsh for a reading-heavy view, the freq superscript shouts as loud as the word, and hover/selected states reflow the grid. A non-structural polish pass to make the UI look like a *thing about old Romanian words*, not a Notion clone — while keeping the keyboard-first tool ethos.

Earlier in the same session a smaller "fine-tuning" pass already landed (grid gap 3px→8/12, freq superscript polish, redundant ★ removed, învechit changed to dotted-red-underline). This spec supersedes those edits where they conflict.

## Direction

**Tool** (chosen over Publication). Keyboard-first, dense, polished dashboard. Linear/Notion/Raycast lineage. Words are *rows in a list*, but each row deserves typographic care.

## Decisions (locked)

### Typography

| Token | Value | Notes |
|---|---|---|
| `--sans` | `'Mona Sans', -apple-system, system-ui, sans-serif` | Replaces Inter Tight. GitHub's open-source variable sans. More character than Inter, less institutional than IBM Plex. Variable width axis available if we want to compress later (out of scope). |
| `--mono` | `'JetBrains Mono', monospace` | Kept. Used for kbd hints + freq superscript. |
| `--serif` | `'Lora', Georgia, serif` | Kept, narrowed to placeholder italics + the `filter` label. Single editorial accent. |
| Word weight | `600` | Was 700. 700 + tight tracking crushed Romanian diacritics (ț, ș, ă). |
| Word size | `18px` | Was 19px. |
| Letter-spacing on word | `-0.005em` | Was `-0.02em`. Near-default tracking lets diacritics breathe. |
| Freq superscript | `10px / 500 / mono / opacity 0.6 / color #b3a99a` | Was `11px / 700 / sans / opacity 0.7 / color #9c9590`. Reads as metadata, not a label. |
| `kbd` (status bar) | `JetBrains Mono / 10px` | Kept. |

Google Fonts link must include Mona Sans + JetBrains Mono + Lora. Inter Tight removed.

### Color tokens

| Token | Before | After | Why |
|---|---|---|---|
| `--bg` | `#ffffff` | `#fcfbf7` | Warm off-white, ~2% warmth, sits between "pure white" and "parchment". |
| `--surface` (top/status bars) | `#ffffff` | `#fdfcf9` | Slightly brighter than `--bg` to separate chrome from canvas. |
| `--border` | `#e6e2da` | `#ece6d6` | Matches the warmer ground. |
| `--text` | `#18150f` | `#1a1812` | Marginal — kept dark charcoal. |
| `--text-2` | `#5c5550` | `#5c5550` | Kept. |
| `--text-3` | `#9c9590` | `#8a8378` | One step warmer to match new ground. |
| `--accent` | `#1a56db` | `#1a56db` | Kept. |
| `--accent-bg` | `#eff6ff` | `#d6e6ff` | Slightly bluer; used for hover. |
| `--v-ext` | `#9a1313` | `#b91c1c` | Cleaner red. The only loud color. |
| `--v-dec` | `#7a3208` | `#524035` | Charcoal-with-brown-hint. Subordinated. |
| `--v-hist` | `#15348f` | `#3d4763` | Charcoal-with-blue-hint. Subordinated. |
| `--v-abs` | `#581cb6` | `#4b3d5a` | Charcoal-with-purple-hint. Subordinated. |

The four verdict colors used to compete equally. New rule: **extinct shouts, the others whisper**. The user's eye lands on extinct first, then explores.

### Layout / density

| Element | Before | After |
|---|---|---|
| Grid `column-gap` | `8px` (fine-tuning pass) | `9px` |
| Grid `row-gap` | `12px` (fine-tuning pass) | `9px` |
| Grid `padding` | `14px 16px 16px` | `11px 13px` |
| `.word-row` `padding` | `3px 8px 4px` | `1px 5px 2px` |
| `.word-row` `justify-self` | (default `stretch`) | **`start`** — critical: makes hover/selected boxes hug the word, not the cell |
| Filter row `padding` | `4px 14px` (min-height 30px) | `4px 12px` |
| Status bar `padding` | as-is | `4px 12px` |

The grid is denser than the fine-tuning pass but still readable. The `justify-self: start` is the load-bearing fix for the user's main complaint about hover/selected being cell-wide.

### Interaction states

**Hover** (`.word-row:hover`):
```css
background: rgba(214, 230, 255, 0.9);
box-shadow: 0 0 0 1px rgba(112, 158, 235, 0.5) inset;
```
Hugs the word's width (via `justify-self: start`). 90% opacity so the warm ground bleeds through 10%.

**Selected** (`.word-row[data-selected]`):
```css
background: rgba(26, 24, 18, 0.9);
color: #fff;
transform: scale(1.06);
transform-origin: center;
box-shadow:
  0 3px 10px rgba(26, 24, 18, 0.16),
  0 1px 3px rgba(26, 24, 18, 0.10);
position: relative;
z-index: 5;
transition: transform .14s ease, box-shadow .14s ease, background .12s ease;
```

Lifts above the grid via `z-index: 5` + `position: relative` on the word only — does **not** reflow neighbors. Subtle shadow (~60% softer than the typical default), 90% bg opacity, 1.06x scale. The `transform: scale` replaces the old verdict-tinted bg + outsized shadow + competing-signals confusion. One unambiguous signal: this word is selected.

Inside `[data-selected]` the freq superscript becomes `color: #c4beb1` and the învechit dotted underline becomes `rgba(255,255,255,0.85)` so they remain visible on the dark bg.

### Removed

- **Top accent stripe** (`body::before` 3px multi-color verdict gradient): removed. Decorative, and it advertises the rainbow palette we're toning down.
- **Inline keyboard legend in status bar** (8 kbd badges): collapsed to a single `<kbd>?</kbd> shortcuts` on the right side. The shortcuts modal already exists.
- **Star glyph `★` on bookmarked words**: already removed in fine-tuning pass. Kept removed.

### Kept

- HTMX wiring (search, filters, detail panel)
- All keyboard shortcuts (j/k/h/l, /, b, i/B/f/x, t, n, o, ?)
- The shortcuts modal (`#shortcuts-overlay`)
- Învechit red dotted underline (locked in earlier this session)
- Word-wide threshold of 11 chars (locked in earlier)
- Detail panel structure and slide-up behavior
- Filter pills, verdict pills, tier pills, POS pills, taxonomy selects

### Bookmark + învechit underline conflict — out of scope

Both currently render as `text-decoration: underline`, so only one wins. Already tracked in `docs/BACKLOG.md` under the UI section. Not addressed in this spec — implementation keeps the current behavior (bookmark amber wins when both true). Revisit when the user has more than a handful of bookmarked words and the conflict matters.

## Files to modify

- `ui/templates/base.html` — `<style>` block lines ~10–876, plus the Google Fonts `<link>` at line 8. Update CSS tokens, body/font-family, grid CSS, word-row CSS, hover/selected states, status bar markup, remove `body::before`.
- `ui/templates/partials/word_row.html` — no markup change (already updated for `inv` class + `title` attribute and freq superscript removed).
- No changes to: `ui/app.py`, route handlers, partials other than `word_row.html`.

## Out of scope (deferred to BACKLOG)

These came up during brainstorming but are bigger than polish:

- Mobile / narrow-viewport breakpoints
- Extract inline CSS to `ui/static/app.css`
- Variable-width font axis tuning on `Mona Sans` (could compress for narrow viewports)
- Replacing the freq superscript with a sparkline or hover-revealed treatment
- Hover/selected interaction on the detail panel itself

## Verification

1. **Reload** `http://127.0.0.1:5000/` after edits (Flask debug auto-reload).
2. **Visual** — match the right pane of `.superpowers/brainstorm/88153-1779098654/content/integrated-preview-v4.html`. Specifically:
   - Words render in Mona Sans 600/18px on warm off-white background
   - Extinct (red) pops; declining/historical/absent read as charcoal-with-hue
   - Hover on any word: 4-letter words have 4-letter-wide blue tint, not cell-wide
   - Click any word: it lifts 1.06x with a soft shadow, neighbors don't move
   - No top accent stripe
   - Status bar shows `19,780 words · 2 bookmarked` on the left, `? shortcuts` on the right
3. **Interaction** — verify keyboard shortcuts still work: `j/k/h/l` navigation, `/` focus search, `b` bookmark, `?` opens modal
4. **Învechit underline** — filter for `tier = dex_invechit_absent`, confirm dotted-red underlines on words
5. **Bookmark interaction** — bookmark an *învechit* word, verify both signals are visible
6. **Computed style check** via DevTools — `getComputedStyle(document.querySelector('.word-row')).fontFamily` returns `'Mona Sans', …`
