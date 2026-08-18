# Sinonime — the page

*The UI decisions `escalate.md` §1 reserved, taken 2026-08-14. Same contract as
[`spec.md`](spec.md): every number is stated inline so this can be executed without
re-deriving anything, and a number coming out wrong is a finding rather than a value to
adjust.*

Read [`findings.md`](findings.md) for the data, [`spec.md`](spec.md) for the build. This
document covers only what is on screen and how it is computed.

---

## The measurements this design rests on

Taken 2026-08-14 against `data/dictionaries/dex-database.sql`, on the word-level type-1
graph, symmetrised, `EntryLexeme.main = 1` on both sides — 61,736 words with ≥1 synonym.

| | |
|---|---|
| degree | mean 5.33 · median **2** · p75 6 · p90 12 · p95 18 · p99 40 · max **352** |
| words with degree 1 | **32.7%** · degree ≤2: **50.2%** |
| sense clusters/word | median **1** · p90 3 · p99 8 · max 122 — **72.3% have exactly one** |
| depth≤2 total nodes | median **16** · p75 63 · p90 **167** · p95 275 · p99 659 · max **2,400** |
| depth≤2 over 60 nodes | 25.7% · over 150: 11.1% · over 400: 2.6% |
| depth≤3 total nodes | median **101** · p75 598 · p90 **1,809** · p95 2,634 · max **10,217** |
| connectivity | 5,597 components; **the largest holds 46,729 words = 75.7%** |

<details><summary>Reproduce</summary>

Parse the dump exactly as `findings.md` §2 does, build the symmetrised type-1 adjacency,
then measure the degree quantiles, the BFS frontier sizes at depth 2 and 3 over a seeded
random sample, and the connected components. ~90 s, writes nothing.
</details>

Four consequences, and each one decides something below:

1. **Uncapped depth-3 is a crawl, not a view.** Three quarters of the graph is a single
   component, so "two steps further" reaches a median of 101 words and a p90 of 1,809.
2. **Uncapped depth-2 is not safe either** — a quarter of lookups exceed 60 nodes, and the
   worst draws 2,400.
3. **Half of all lookups have ≤2 synonyms.** For those, a graph is three dots.
4. **Sense clustering — the strongest argument for a graph — pays on 27.7% of words**, so
   it has to vanish gracefully rather than be the page's organising principle.

---

## Shape of the page

```
┌─────────────────────────────────────────────┐
│  oțios · sinonime        [ frumos       ]   │
├──────────────────────────┬──────────────────┤
│          ○ arătos        │  arătos    ▇▇▇▇  │
│     ○         │          │  chipeș    ▇▇▇   │
│  mândru ─── FRUMOS ─── ○ │  mândru    ▇▇▇   │
│     │         │   chipeș │  plăcut    ▇▇    │
│     ·      ○ plăcut      │  bididel   ·     │
│    · ·   ring 2, dim     │  boghet    ·     │
└──────────────────────────┴──────────────────┘
```

**Graph left, ranked list right, both always present.** Not a preference between two
renderings:

- The SVG is invisible to a screen reader, so the list has to exist as its text
  alternative. Given it exists, it should be the good one — and for the writing-aid task
  (scan, pick, use) a ranked list beats any diagram.
- 50.2% of lookups draw ≤2 direct synonyms. On those the graph is nearly empty and the list
  carries the page; on `frumos` the graph is the reason to be here. Neither can be the
  default alone.

The graph is a **map** — it shows the shape of the neighbourhood and the sense boundaries.
The list is the **result** — it is what you take a word from.

Below 900px the two stack, **list first**, with the graph in a collapsed `<details>` above
it. The graph has a fixed `viewBox`, so it scales rather than reflows and needs no
breakpoint arithmetic.

---

## Caps — the whole reason a graph is viable at all

| | |
|---|---|
| ring 1 | top **6** per sense, **≤12** total across all senses |
| ring 2 | top **4** per ring-1 node, **≤24** total |
| senses rendered | **4** (median 1, p90 3); the rest behind a `+N sensuri` link |
| **hard ceiling** | **37 nodes**, independent of the data |

Ranking within a sense is `band DESC, form ASC`, and it is **precomputed** into `edge.rank`
at build time (see `spec.md` Phase 2), so the request path does no ordering.

The cap is not a performance tuning knob, it is what makes the drawing bounded. Without it
the 352-degree hubs and the 2,400-node depth-2 tails are on screen. With it the ceiling
holds for every word in the database, including the worst one.

**There is deliberately no depth slider.** At three hops the p90 is 1,809 words; even capped
it is a field in which the query word is no longer findable. Depth 3 is reached by clicking
a ring-2 node, which recentres — bounded screen at every moment, unlimited depth by walking.
The graph *is* the walk.

**Ring 2 is subordinate and is not in the list.** Synonyms-of-synonyms are semantic drift
(`frumos` → `plăcut` → `comod`): worth exploring, wrong to hand a writer as a suggestion.
They render smaller, dimmer, on thinner edges, and the list beside the graph contains ring 1
only.

---

## Layout — deterministic radial, no simulation

**No force-directed layout.** It is nondeterministic (so untestable and unstable to
screenshot), it jitters, it hairballs on the hubs, and it needs d3-force — which breaks the
one hard line in `spec.md` Phase 3, that this page loads htmx + `prefs.js` and nothing else.

The layout below is arithmetic. It produces the same bytes every run, it renders as plain
SVG with **zero libraries**, and it is computed in PHP — which is what lets the whole graph
be server-rendered and therefore work with JavaScript off.

### Constants

```
viewBox      0 0 820 700          cx = 410   cy = 350
R1           130 + 6 × n1, clamped to [140, 180]      (n1 = ring-1 node count)
R2           R1 + 100
EDGE_START   18                   edges leave the centre outside the headword's halo
GAP          0.06 rad             shrunk off each end of a sense sector, only when S > 1
LABEL_PAD    6                    px between node edge and its label
```

`R1` grows with crowding so a 12-node ring is not packed onto the same circumference as a
3-node one. `R2 = R1 + 100` keeps the maximum extent at 280px, leaving 70px of the 350px
half-height for labels.

### Angles

1. Order senses by (max `band` in the sense DESC, `sense.id` ASC). Render at most **4**.
2. Weight each sense `w_i = n_i + 1`, where `n_i` is its ring-1 count after the cap.
   Share `share_i = w_i / Σw`. The `+1` is what stops a one-word sense claiming the same
   wedge as a six-word one without giving it nothing.
3. Sectors are laid out clockwise from `−π/2` (straight up). Sense *i* spans
   `[θ_i + GAP, θ_i + 2π·share_i − GAP)` when more than one sense is rendered, and the full
   circle when there is exactly one.
4. Ring-1 node *j* of *n* in a sector of width `W` starting at `θ`:
   `θ + (j + 0.5)·W/n`.
5. Ring-2 children of a ring-1 parent at angle `θ_p` with slot width `s = W/n`: they are
   centred on the parent inside `0.9·s`. Child *k* of *m*:
   `θ_p − 0.45·s + (k + 0.5)·0.9·s/m`.

Position is `(cx + R·cos θ, cy + R·sin θ)`.

### Ring-2 assignment — one parent, one edge

Walk ring-1 nodes in rank order, and each one's children in rank order. Skip any word that
is the centre, is already in ring 1, or has already been placed in ring 2.

Because ring 1 is `band`-ordered, first-seen **is** highest-band parent, and the drawing
comes out a tree. That is what makes it both deterministic and readable. Additional edges
between placed nodes may be drawn later as thin secondary strokes; they are not in v1.

### Node and label rendering

| | |
|---|---|
| node radius | `3.5 + 0.8 × band` → 3.5 at band 0, 9.1 at band 7 |
| node opacity | `0.38 + 0.088 × band` → 0.38 at band 0, 0.99 at band 7 |
| label size | 11px ring 1 · 9.5px ring 2 · 17px centre, weight 600 |
| label opacity | the node's, floored at **0.45** so a band-0 word stays readable |

**Band is carried by size and opacity, never by colour.** Colour is a skin's to define and
the site has six of them; an ordinal 0–7 maps to opacity identically under all of them and
in both themes. Colour is reserved for edge *type*.

**The centre is text, not a circle** — the headword at `(cx, cy)`, `text-anchor="middle"`,
`dominant-baseline="middle"`, in `--accent`. A circle plus a label there collides with
every edge leaving it; text with a halo does not, which is why edges start at
`EDGE_START = 18`.

**Every label gets a halo**: `paint-order="stroke"`, `stroke="var(--surface)"`,
`stroke-width="4"`. Labels cross edges at some angles in every layout; the halo is what
keeps them legible instead of requiring collision avoidance.

**Labels stay horizontal at every angle** — never rotated to the radius. `text-anchor` is
`start` when `cos θ ≥ 0` (label at `x + r + LABEL_PAD`) and `end` otherwise (at
`x − r − LABEL_PAD`); `dominant-baseline="middle"` in both cases. Rotating labels to follow
the spokes is the single most common way a radial diagram becomes unreadable, and it looks
correct while you are drawing it.

Truncate a label over **16 characters** to 15 plus `…`, with the full form in the node's
`<title>`.

**Draw order is load-bearing: all edges, then all nodes, then all labels.** SVG has no
z-index, so painting a node's label immediately after its own circle puts the *next* node's
edge on top of it and the halo masks nothing. Emitting the three groups in order is what
makes the halo work at all.

The box fits by arithmetic and it is worth checking after any constant changes: the maximum
extent is `R2 + node radius` = 280 + 9.1 = 289.1, against a half-height of 350; horizontally
a 16-character label at 9.5px adds ~85px, so 289 + 9 + 6 + 85 = 389 against a half-width of
410. Both have margin, neither has much.

---

## Markup, accessibility, and what works without JavaScript

**Every node is a real link.** `<a href="?q=<word>">` wrapping the circle and its label,
inside the SVG. So the graph is tabbable, has real hover targets, opens in a new tab on
middle-click, and **is fully navigable with JavaScript disabled**. That is what makes
server-rendering the SVG worth doing rather than a purity exercise.

- `<svg role="img">` with an `aria-label` summarising the neighbourhood in words
  („frumos: 6 sinonime în 2 sensuri").
- The `<ol>` beside it is the graph's text alternative and carries the same links, in the
  same order, with the band stated in text as well as in the meter.
- The depth-2 data ships as `<script type="application/json" id="syn-data">`, not as a data
  attribute on an element.

`assets/syn.js` is **progressive enhancement only**, ~80 lines, and the page is complete
without it: hover cross-highlighting between a node and its list row, a hover card showing
a node's own top synonyms off the JSON island, and `mouseenter` prefetch of the target
fragment.

**The JSON island must not re-lay-out the graph in the browser.** That would put the
geometry above in two languages, and they would drift. Recentring is an htmx swap with
`hx-push-url`; prefetch on hover is what makes it feel immediate.

---

## The list

Ring 1 only. Grouped by sense **when more than one sense is rendered**, with `sense.label`
(`Tree.description`) as the group heading; ungrouped otherwise, which is 72.3% of words.

Each row: the word as a link that recentres, a band meter, `pos`, the sense's register tags
decoded from `sense.reg`, and a copy button at the row end. **The row link and the copy
button are separate targets** — a row that both navigates and copies depending on where you
click is a row nobody can predict.

Rows at band 0–1 are dimmed and still selectable, never filtered out. An archaic synonym is
sometimes exactly what the writer wants, and a hidden word is an invisible false negative.

---

## The empty state is a first-class screen

`findings.md` §4 measures 67.0% coverage in the 1k+ band, rising to 72.4% with type-5. **One
lookup in four in the band people actually search comes back with nothing**, so this screen
is common, not an edge case.

It shows: the word, its band and POS (we know those even with no edges), a plain statement
that our sources have no synonym for it, the nearest prefix and substring matches from the
search fallback, and a link to the word's page on dexonline. It must not look like an error
and must not look like the word is unknown to us.

---

## Landing state

A centred search box, and beneath it a small set of one-click examples chosen to teach the
tool in a single click rather than in a paragraph:

- **`frumos`** — a hub whose synonyms include dead ones (`bididel`, `boghet`), so the
  band dimming explains itself.
- **`văz`** — three sense clusters, the case the graph exists for.
- **`repede`** — an ordinary, fully-alive lookup.

The 41.7%-dead figure is the product's whole argument and it is much better shown than
stated.

---

## Skins

Three rules, all lifted from CLAUDE.md rather than rediscovered.

**1. The graph names no colour.** Four tokens on `:root` in `app.css`, so a skin repoints
them without ever naming `.syn-node`:

```css
--syn-node: var(--text-2);    /* node fill */
--syn-edge: var(--border-2);  /* type-1 edge */
--syn-ant:  var(--error);     /* type-2 edge */
--syn-tree: var(--text-4);    /* reserved for type-5, see below */
```

Declare them in **both** theme blocks if a skin's values differ between light and dark —
hardcoding one is the most common way a skin ends up unreadable at night.

**2. The active state must be out of a skin's reach.** Write it
`.syn-graph .syn-node.is-active` at (0,3,0). A skin's own `[data-skin="x"] .syn-node` is
(0,2,0) and loads after `app.css`, so at (0,2,0) a skin restyling the resting node silently
repaints the active one to match — with no rule anywhere naming `.is-active`. This is the
fourth instance of the pattern CLAUDE.md records at `.fp-btns .qt-btn.active`, and it fails
invisibly while you are writing any one skin.

**3. Screenshot all six skins × both themes.** The graph floats on `--surface`; a skin whose
surface and node colours are close gives a diagram with no contrast, and — as with the
detail panel — the failure is only visible when you compare.

Two skins need checking specifically: `govuk` (which sets `--radius: 0` and forces the
masthead black) and `registru` (whose `--accent` is the page's own ink, so anything filled
with `--accent` inside a dark region disappears — the `.joc-mode.active` bug, one component
over).

---

## Not in v1

**Type-5 (`Tree` co-membership) edges are stored and not shown.** `escalate.md` §6 requires
a review of ~50 random pairs first — they are sometimes spelling variants rather than
synonyms (`pârpolatic`, `astatic`, `îhî`, `părtie`). The visual treatment is reserved for
when that review happens: a **dashed edge in `--syn-tree`**, ranked below every type-1 node
in the same sense, labelled „din același cuib DEX". Do not enable them without the review.

Also out: additional (non-tree) edges between placed nodes, animation, a depth control, and
anything that writes.

---

## Attribution

`escalate.md` §8 makes this a requirement rather than a courtesy: the relation graph is
dexonline's own community-curated work, and the gap scrape reads their pages. The page
carries a credit to dexonline.ro with a link, and every word view links to that word's page
there.

---

## Where the tool is linked from

**Not the top nav.** CLAUDE.md's header/footer section records that the bar takes exactly
three labelled entries and that a fourth broke it at phone widths.

- The explorer's `≡ sinonime` row in `api/_partials/detail.php:104-115` gains a single
  `vezi în sinonime →` link. Its chips keep pointing at the explorer's own `?q=`.
- A line in `despre`.

---

## Acceptance — additions to `spec.md`'s `tests/test_sinonime.js`

- **The node ceiling holds.** For `frumos`, `mare`, and the maximum-degree word, the
  response contains **≤37** `.syn-node` elements.
- **The layout is byte-stable.** The same query twice returns an identical SVG.
- **The graph works with no JavaScript.** Every node is an `<a href>` resolving to
  `?q=<word>`; the count of node links equals the count of nodes.
- **A band-0 word is present and marked**, in both the graph and the list.
- **A word with no synonyms renders the empty state**, not an error and not a blank graph.
- **`văz` renders more than one sense sector** and its sectors do not overlap — the UI-side
  form of `spec.md`'s flattening regression test. If it fails, the fault is in the build,
  not the layout; see `escalate.md` §5 and do not loosen it.
- **No `Set-Cookie` for the device token** on any response from this page.
