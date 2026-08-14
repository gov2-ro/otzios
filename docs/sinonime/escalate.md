# Sinonime — what to bring back to Opus

*For whoever implements [`spec.md`](spec.md). Everything here is a decision the spec
deliberately does not make. Stop and ask rather than pick a default — each of these was
either reserved by the project owner or is a judgement the measurements do not settle.*

The rule of thumb: **the spec tells you what to build and what the numbers should be. If
a number comes out wrong, that is a finding, not a test to adjust.**

---

## Reserved outright

### 1. The entire UI

Explicitly held back by the project owner for a separate session. Phase 3 stops at file
structure — four filenames, which library each loads, and the search order.

Not yours to decide: layout, how sense clusters are presented (or whether v1 shows them
at all), how "dimmed" is rendered, chips versus lists, colour, the skins pass, empty
states, mobile treatment, whether the page has a landing state or opens on a search box.

Build the endpoint so it returns the data; leave the markup minimal and unstyled rather
than inventing a design that then has to be argued with.

### 2. Where the tool is linked from

**Not the top nav.** CLAUDE.md's header/footer section records that the bar takes exactly
three labelled entries and that a fourth broke it at phone widths — the `despre` chip
exists precisely because a fourth label would not fit. Candidate routes are the
explorer's `≡ sinonime` row in `api/_partials/detail.php:109-115` (whose chips currently
point at `?q=`) and a link from `despre`. Part of the UI conversation.

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

### 7. Any schema change

The size figures (~10–11 MB, ceiling 16 MB) were measured against exactly the DDL in
`spec.md`, by building it in `:memory:` with the real data. Changing a column type,
adding a string column, or dropping a `WITHOUT ROWID` invalidates them. If the schema
needs to change, say so and re-measure rather than quietly shipping a different number.

### 8. Scaling the scrape

The dump redacts `Sinonime` / `Sinonime82` / `Antonime` **deliberately** — they are Seche,
published by Litera, and in copyright. Scraping 2,075 words as a supplement to a research
site is a different thing in scale from reconstructing 20k+ entries as a standalone
synonym product.

This was raised with the project owner and **the 21,489-word gap run (Phase 4) is
approved**. dexonline serves these publicly and attribution plus linking back is the
normal mitigation; both should be in the page.

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
