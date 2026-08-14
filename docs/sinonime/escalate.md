# Sinonime — what to bring back to Opus

*For whoever implements [`spec.md`](spec.md) and [`ui.md`](ui.md). Everything here is a
decision those documents deliberately do not make. Stop and ask rather than pick a default
— each was either reserved by the project owner or is a judgement the measurements do not
settle.*

The rule of thumb: **the spec tells you what to build and what the numbers should be. If
a number comes out wrong, that is a finding, not a test to adjust.**

The first two sections were released on 2026-08-14 and are kept here, settled, rather than
deleted — so a reader who was told the UI was reserved can see that it no longer is, and
where the decision went.

---

## Released — settled 2026-08-14

### 1. The entire UI — **settled, see [`ui.md`](ui.md)**

Was held back by the project owner for a separate session. That session happened on
2026-08-14 and took every decision it named: layout (deterministic radial, graph and
ranked list side by side), sense clusters (angular sectors, shown), dimming (size and
opacity from `band`, never colour), the skins pass, the empty state, mobile, and the
landing state.

**It is now the opposite of reserved: do not improvise here.** `ui.md` states the
geometry as constants and formulas precisely so it can be executed without judgement, and
a value that comes out looking wrong is a finding to report, not one to nudge. What it
does leave open it collects under § Not in v1, and §6 below is the live one.

### 2. Where the tool is linked from — **settled**

**Not the top nav.** CLAUDE.md's header/footer section records that the bar takes exactly
three labelled entries and that a fourth broke it at phone widths — the `despre` chip
exists precisely because a fourth label would not fit.

The routes are a `vezi în sinonime →` link added to the explorer's `≡ sinonime` row
(`api/_partials/detail.php:104-115`, whose chips keep pointing at the explorer's own
`?q=`), and a line in `despre`.

---

## Stop-and-ask if the data disagrees

### 3. `ObjectTag.objectType = 3` is an inference, not a documented fact

The register metadata (`sense.reg`) rests on `objectType = 3` meaning `Meaning`. The
evidence is indirect: `regional` (8,022), `figurat` (9,949), `rar` (6,631), `învechit`
(5,836) and `cf.` are all type 3, while `substantiv feminin` (62,787) and `adjectiv` are
type 2, which reads as `Lexeme`.

**Verify before relying on it** — join `ObjectTag.objectId` against `Meaning.id` and check
the hit rate, then against `Lexeme.id` and compare. If type 3 is not `Meaning`, the whole
register design changes: it would be attaching sense-level tags to the wrong entity, which
is the exact failure CLAUDE.md records for `dex_pos` (`visternic` came out "substantiv
feminin" because the entry also covers `vistiernică`). Stop and report.

### 4. Coverage below 70% at bands 1k+

The measured floor is **72.4%** (`Relation` 67.0% plus `Tree` co-membership). If your
build lands under 70%, something in the merge is dropping edges — most likely the
symmetrisation (only 36% of stored pairs are reciprocal) or the `main = 1` filter applied
to the source side as well as the target. It is not that the data is thinner than
`findings.md` says. Report the number you got.

### 5. The `văz` cluster test failing

```
văz  ·  privire, vedere, văzut
     ·  captiva, orbi
     ·  concepție
```

If `concepție` lands in the same cluster as `privire`, the tree-expansion rule is wrong —
you are expanding a target `Tree` to every lexeme of every one of its entries, and 10,091
trees hold more than one. **Do not fix this by loosening the assertion.** It is the single
thing the sense-structured schema exists to preserve.

---

## Judgement calls that need a second opinion

### 6. Whether type-5 (`Tree`) edges are shown or merely stored

They buy 25,554 words their first synonym and +5.4 points on the 1k+ band, which is why
they are in the schema. But the sample is mixed — `pârpolatic`, `astatic`, `îhî`,
`părtie` — because tree-mates are sometimes spelling variants rather than synonyms.

The spec stores them with `src = 2` and `t = 5` so the question stays open. Before they
are shown by default, someone should review ~50 random pairs and decide whether they are
labelled ("din același cuib DEX"), ranked below type 1, or shown at all. That review is a
judgement about Romanian, not a measurement.

**Still open after the UI session.** `ui.md` § Not in v1 keeps them stored and unshown,
and reserves a treatment (a dashed edge in `--syn-tree`, ranked below every type-1 node in
the same sense) for the day the review happens. Having a treatment ready is not permission
to switch them on.

### 7. Any schema change

The size figures (~10–11 MB, ceiling 16 MB) were measured against exactly the DDL in
`spec.md`, by building it in `:memory:` with the real data. Changing a column type,
adding a string column, or dropping a `WITHOUT ROWID` invalidates them. If the schema
needs to change, say so and re-measure rather than quietly shipping a different number.

**One such change has already been made and its re-measure is outstanding.** The UI
session added `edge.rank` plus `ix_edge_rank` (`spec.md` build rule 9) so the page's node
ceiling holds by construction. Expect roughly +1.5–2 MB, which leaves room under the 16 MB
ceiling — but that is an estimate, not a measurement. **Report the built size**; do not
copy the ~10–11 MB figure forward.

### 8. Scaling the scrape

The dump redacts `Sinonime` / `Sinonime82` / `Antonime` **deliberately** — they are Seche,
published by Litera, and in copyright. Scraping 2,075 words as a supplement to a research
site is a different thing in scale from reconstructing 20k+ entries as a standalone
synonym product.

This was raised with the project owner and **the 21,489-word gap run (Phase 4) is
approved**. dexonline serves these publicly and attribution plus linking back is the
normal mitigation; both should be in the page. `ui.md` § Attribution makes that a build
requirement rather than a courtesy — a credit with a link, and a link to each word's own
dexonline page from its view.

**Going wider is a fresh decision.** `findings.md` §6 shows the scrape adds 59% new
tokens even on words `Relation` already covers, so there is a real argument for scraping
all ~83k — at ~69 h of requests against a community-run site. Do not start that on your
own initiative.

---

## Things that look like decisions but are not

For completeness, so they are not escalated unnecessarily. These are settled and the
reasoning is in `spec.md`:

- Sense structure is kept in storage even if the first UI renders flat.
- Dead words are ranked and dimmed, never hidden.
- One display string per word (`Lexeme.formNoAccent`); the folded search key lives in
  `key`, not in a second column.
- `band` is derived by paradigm rollup, never from a bare surface count.
- Search is exact → prefix → substring, no FTS5.
- The tool gets its own DB and its own lib file, and touches neither `app.db` nor auth.
- `v. X` cross-references were measured (513 pure, 400 new words) and rejected.
- **Pagefind was evaluated and rejected** — it indexes rendered HTML with BM25, which would
  mean generating 63,049 static pages and then overriding its ranking with `band`. Reasoning
  in `spec.md` § Search order, so it is not proposed again.
- **No force-directed graph layout**, and no d3. The layout is arithmetic, in PHP, so the
  drawing is deterministic and the page keeps its htmx-only load. `ui.md` § Layout.
- **No depth slider.** Depth 3 is reached by clicking a node, which recentres. The measured
  p90 at three hops is 1,809 words.
- **The graph is server-rendered SVG and every node is a real `<a href>`**, so it works with
  JavaScript off. The JSON island never re-lays-out the graph in the browser — that would
  put the geometry in two languages.
