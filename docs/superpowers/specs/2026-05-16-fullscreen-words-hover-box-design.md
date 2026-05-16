# Full-screen word grid + hover info box

**Date:** 2026-05-16
**Status:** approved

## Summary

Replace the 50/50 split layout (word list | detail panel) with a full-width word grid.
A compact info box appears in the top-right corner on hover.
Clicking a word opens a fixed-position detail panel that slides in from the right as an overlay (word grid stays full-width underneath).

---

## Layout

### Default state
- `#word-list-container` expands to 100% of `#app` width (remove the `width: 50%` and `border-right`).
- `#app` gets `position: relative` so child panels can anchor to it.
- `#detail-panel` is `position: absolute; right: 0; top: 0; height: 100%; width: 420px` with `transform: translateX(100%)` (hidden off-screen to the right). This automatically sits within the space between the filter bar and status bar — no pixel calculations needed.
- No visible change to the filter bar or status bar.

### Panel-open state
- Clicking a word chip triggers the existing `hx-get="/word/…"` → `hx-target="#detail-panel"`.
- After the HTMX swap, JS adds class `.panel-open` to `#app` (or directly to `#detail-panel`).
- `#detail-panel` transitions to `transform: translateX(0)` with a ~200 ms ease-out CSS transition.
- A close button (`✕`) in the detail panel removes the class and slides the panel back off-screen.
- Words underneath the open panel may be partially obscured — this is acceptable; the user can scroll or close the panel.

### Closing the panel
- `✕` button click.
- Pressing `Escape` (already handled in keydown listener).
- Clicking a new word re-loads content but keeps the panel open.

---

## Hover info box

### Appearance
- `position: absolute; top: 8px; right: 8px` within `#app` (which is `position: relative`). Stays anchored to the top-right of the word area without needing to know filter bar height.
- Width: 260px.
- Background: `var(--surface)`, border: `1px solid var(--border)`, box-shadow, border-radius 6px.
- Hidden when `#detail-panel` has class `.panel-open` (they would overlap in the same corner).

### Content (top to bottom)
1. Word name — large serif (Lora), verdict color, ~1.4em.
2. Verdict badge — existing `.verdict-badge` styles.
3. Metadata row — POS abbreviation · DEX frequency (e.g. `s.f. · 34`).
4. Definition excerpt — first ~120 chars, italic serif, color `var(--text-2)`, fades with `-webkit-mask-image` gradient if truncated.

### Data source
Data is embedded as `data-*` attributes on each `.word-row` chip (no network call on hover):
- `data-pos` — first pipe-segment of `w.dex_pos` (e.g. if `dex_pos` is `s.f.|adj.`, emit `s.f.`; blank if null)
- `data-freq` — `w.dex_frequency * 100 | round | int` (blank if null)
- `data-def` — first 120 characters of `w.definition` (blank if no definition)
- `data-verdict` — `w.verdict` (already available via CSS class, but explicit attr simplifies JS)

### Show/hide behavior
- `mouseenter .word-row` → populate hover box from `data-*` attrs → set `opacity: 1; transform: translateY(0)`.
- `mouseleave .word-row` → set `opacity: 0; transform: translateY(-4px)`.
- CSS transition: `opacity 120ms ease, transform 120ms ease`.
- Hover box is hidden (`display: none` or `pointer-events: none; opacity: 0`) while `.panel-open` is active.

---

## Implementation scope

### Files to change
| File | Change |
|---|---|
| `ui/templates/base.html` | Layout CSS (full-width word list, fixed detail panel, hover box element + CSS + JS) |
| `ui/templates/partials/word_row.html` | Add `data-pos`, `data-freq`, `data-def`, `data-verdict` attributes |
| `ui/templates/partials/detail.html` | Add `✕` close button; JS hook to add `.panel-open` after HTMX swap |

### Not in scope
- Filter bar, status bar, keyboard shortcuts — unchanged.
- HTMX routing (`/word/<word>` endpoint) — unchanged.
- Mobile/responsive layout — not addressed.
