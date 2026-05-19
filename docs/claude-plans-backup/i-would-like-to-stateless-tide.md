# UI fine-tuning: word grid polish + învechit marker

## Context

The word-list UI at `ui/templates/base.html` has two visible quality issues in production (see screenshots):

1. **`înv` marker bleeds into neighboring words.** The "învechit" badge under each archaic word is `position: absolute; bottom: 0; left: 7px` (base.html:355-363). Combined with the grid's `gap: 3px` (line 294), the italic serif glyphs visually collide with words in the row below — most obvious on dense rows. This is the "overlapping / noise" the user wants gone.

2. **The whole grid feels cramped.** `gap: 3px` is extreme even for an information-dense view, and the 19px bold word + 11px superscript sits very close to neighbors.

User intent: *fine-tuning only*, no structural changes. Bigger ideas go to `docs/BACKLOG.md`. The marker should stay attached to its own word (or integrate into it) — never bleed into a neighbor. User wants to *see* marker variants live in the browser and pick one.

## Files involved

- `ui/templates/base.html` — all CSS is inline here (lines 10–876); grid, word-card, înv-marker, freq-chip styles all live in this file
- `ui/templates/partials/word_row.html` — the word-card markup (13 lines)
- `ui/app.py` — Flask routes; we'll add **one** read-only demo route for marker preview (no DB changes)

## Plan

### Step 1 — Non-controversial fine-tuning (apply unconditionally)

Edits inside `base.html`'s `<style>` block:

- **Grid breathing room** (line 294): `gap: 3px` → `column-gap: 8px; row-gap: 12px`. Cures the overlap structurally and gives the page editorial spacing without sacrificing density.
- **Word-card padding** (line 303): `padding: 2px 7px 3px` → `padding: 3px 8px 4px`. One extra pixel below to keep ascenders/descenders off the row boundary.
- **Freq superscript polish** (lines 366-376): drop `vertical-align: super` (which makes it float oddly tall) in favor of `vertical-align: baseline` + `font-size: 10px` + `position: relative; top: -0.5em`. Slightly mute color to `var(--text-3)` at `opacity: .7` so the score reads as secondary metadata, not a co-equal label.
- **Hover background** (line 325): `#f0ece5` → `var(--accent-bg)` (`#eff6ff`) for a cooler, more obviously-interactive hover that doesn't clash with the warm body bg.
- **Bookmark redundancy** (lines 340-341): keep the amber underline, drop the trailing `★` glyph. The underline alone is enough; the star adds visual noise on dense bookmarked rows.
- **`.word-wide` threshold** (`word_row.html:1`): lower from `length >= 12` to `length >= 11` so words like `bogasieresc` (11), `panevghenie` (11), `protipendist` (12) get their full column instead of clipping their neighbor's space.

### Step 2 — Build demo page for înv-marker variants

Add a single route in `ui/app.py`:

```python
@app.route('/demo/marker')
def marker_demo():
    return render_template('marker_demo.html')
```

Create `ui/templates/marker_demo.html` — a standalone page (reuses the same `<style>` block as base.html via Jinja include or copy) that renders the same word sample 6 times, each as a labeled variant block. Sample words: pick ~30 real ones from the shortlist, including a mix of `învechit` and non-`învechit`, so the user can directly compare readability.

Variants to render side-by-side:

| ID | Approach | Sketch |
|----|----------|--------|
| **A** | Tiny inline italic pill after the freq number — what we had originally before the absolute override | `fost ⁹⁸ ᵢₙᵥ` |
| **B** | Dagger superscript (`†`) — editorial typography convention for "deceased / archaic" | `fost† ⁹⁸` |
| **C** | Red dotted underline on the word itself — quietest, no extra glyph | `f̤o̤s̤t̤ ⁹⁸` |
| **D** | Subtle red tint on the cell background (`var(--v-ext-bg)` at 40% alpha) — color-coded zone | `[█ fost ⁹⁸ █]` |
| **E** | Small filled red bullet (`●`) after the freq, baseline-aligned | `fost ⁹⁸ ●` |
| **F** | Emoji marker (`🪦` or `📜`) after the word — only for contrast; likely too playful | `fost 🪦 ⁹⁸` |

Each variant block: heading with variant name + 2-line rationale, then the grid sample. All variants share the same column-gap/row-gap from Step 1 so the comparison isn't confounded by spacing.

### Step 3 — Apply user's chosen marker variant

Once the user picks (via `127.0.0.1:5000/demo/marker`), apply that variant to `word_row.html` + `base.html` and remove the demo route + template. Single small commit.

### Step 4 — Backlog candidates (deferred per user)

Add to `docs/BACKLOG.md`:

- Verdict palette saturation review — four full-saturation colors (red/brown/blue/purple) compete; consider one dominant + three muted
- Bookmark visualization rethink (underline vs. star vs. row-edge marker)
- Mobile / narrow-viewport breakpoints (no media queries today)
- Extract inline CSS to `ui/static/app.css` (~870 lines inline)

## Critical files

- `ui/templates/base.html` — Steps 1, 2 (style block), 3
- `ui/templates/partials/word_row.html` — Step 1 (`word-wide` threshold), Step 3
- `ui/app.py` — Step 2 (one route, removed in Step 3)
- `ui/templates/marker_demo.html` — Step 2 (new, deleted in Step 3)
- `docs/BACKLOG.md` — Step 4

## Verification

1. **Run the app** with the existing venv:
   ```
   source ~/g2-dev/monitorulpreturilor/venv/bin/activate  # or /Users/pax/devbox/envs/240826
   cd /Users/pax/devbox/otios && python -m ui.app  # or whatever the existing entrypoint is — check app.py
   ```
2. Open `http://127.0.0.1:5000/` — confirm:
   - No `înv` text bleeding into neighbor rows
   - Visibly more space between rows
   - Freq superscript reads as quiet metadata, not as a competing label
   - Hover state feels intentional
   - All existing keyboard shortcuts (j/k/h/l, /, b, i/B/f/x, t, n, o, ?) still work — touch a few
3. Open `http://127.0.0.1:5000/demo/marker` — confirm all 6 variants render with realistic word density. User picks one.
4. After Step 3, reload `/` and confirm chosen variant looks identical to its preview.
5. After Step 3, confirm `/demo/marker` returns 404 (route removed).
