# Corpus expansion — what to add, in what order

Date: 2026-08-10. Companion to `docs/corpus-options.md` (the older catalog, written when
Wikipedia was still the corpus) and to the two LLM reference reports in `docs/reference/`:
`260810 Grok - extend corpuses analysis.md` and `260810 Gemini - Romanian NLP Corpora and
Tools.md`.

This document exists because those two reports are useful but neither was checked against
the repo. Both make claims about what Oțios currently does that are wrong, and one of them
recommends the single practice this project has already been burned by. Everything below
that is stated as a number was measured today against the working tree, not quoted.

## Where the panel actually stands

From `corpus_frequencies.db`, `processing_stats`:

| corpus | documents | tokens | word types counted |
|---|---:|---:|---:|
| `culturax_ro` | 40,325,424 | 16,969,999,321 | 122,463 |
| `wikisource_ro` | 12,921 | 14,297,033 | 45,218 |
| `subtitle_ro` | 965 | 13,227,953 | 29,733 |

So the historical panel is one corpus of 14.3M tokens, and the modern panel is effectively
one corpus of 17.0B. That asymmetry is the project's defining constraint and is why
`validate_diachronic.py` compares occurrence counts and percentile ranks rather than rates.

## What the reference reports get wrong

Read both, but do not act on them unchecked. Four corrections, in descending importance:

**1. Gemini's core statistical recommendation is the bug this project already fixed.**
Its "Moving Beyond Raw Frequencies" section says frequencies "must be normalized, typically
expressed as occurrences per million … to allow for cross-corpus comparison". That is
exactly the practice that classified `zapciu` as extinct on 1,322 modern hits, and it is
documented as gotcha #1 in `CLAUDE.md` and again in a 12-line comment at
`validate_diachronic.py:190-211`. A shared 0.1 ppm floor means "< 1,697 occurrences" on
CulturaX and "≥ 1.43" on Wikisource. Ignore this recommendation entirely. Its Log-Likelihood
Ratio suggestion is a separate and better idea — LLR is scale-aware — but it is not a reason
to reintroduce ppm.

**2. Gemini's step 1 would empty the relevant seam.** It recommends "aggressively filtering
out entries explicitly marked by lexicographers with tags such as (Înv.), (Arh.), and
(Reg.)" to find undocumented forgotten words. That is a coherent goal but a different
project. Oțios deliberately keeps those words and treats `regional_only` as a *UI flag*
rather than a score or seam input — see the "Score vs. flags" section of `CLAUDE.md`, which
records that penalising regional words in the score *and* routing them out of the seam left
the "arată regionalisme" toggle with nothing to reveal. The relevant seam currently holds
~397 regional words on purpose.

**3. Grok's P0 is half wrong. `subtitle_ro` is already wired in — it just does not decide
anything.** The report says it "does not appear to drive the principal verdict", implying it
is unwired. In fact it is processed, family-aggregated (`subtitle_fam`,
`validate_diachronic.py:600`), written to the CSV as `subtitle_ppm`, and carried all the way
into `ui.db` (`tools/build_ui_db.py:326`). What is true is narrower and more actionable:

- `verdict()` takes `(hist_occ, hist_docs, modern_occ, rank_shift)` — no subtitle term.
- `make_shortlist.score()` reads `modern_occ`, `hist_occ`, `dex_frequency`, `dict_count`,
  `family_ratio` — no subtitle term.
- The family-aggregated `subtitle_occ` **is dropped at the shortlist boundary**. It is in
  `validate_diachronic.py`'s fieldnames but not in the shortlist CSV header, while
  `subtitle_ppm` — computed from the raw surface form at line 634, not the paradigm — does
  survive. So the number that reaches the UI is the un-rolled-up one, which is precisely
  what gotcha #2 in `CLAUDE.md` says never to judge a lemma on.

**4. Corpus size claims differ from ours and that is fine.** Gemini cites 39.6B tokens for
CulturaX-ro; we measure 16.97B over the same 40.3M documents. That is a tokenizer
difference, not a partial run — the document count matches the published figure exactly.

## Three things measured today

### LUMRO is real, dated, and worth ingesting

Downloaded and counted (`upb-nlp/LUMRO`, 175 JSON files, full text as
`{chapter: [paragraph, …]}`):

- **7,520,713 tokens**, 43.2M characters — 53% the size of Wikisource, a substantial
  addition rather than a rounding error.
- **111 authors, 1845–1920**, median year 1898, publication year in every filename.
  By decade: 1840s 2, 1850s 7, 1860s 11, 1870s 9, 1880s 20, 1890s 40, 1900s 38, 1910s 35,
  1920s 10. Three of 175 files do not parse a year from the filename.
- Diacritics are **overwhelmingly cedilla-form** (`ş` 1994 vs `ș` 13 in one sampled novel),
  which `dump_parser.normalize` already handles. No new normalization work.
- The text carries pre-reform orthography in exactly the register we want — the sampled page
  has `neâncetată`, `naturei`, `îndumnezeieşte`, `profumul`.

Rolled up through `inflected_forms.db` with the same paradigm logic as
`aggregate_by_family`, against the current 16,203-row shortlist:

- **8,201 of 16,203 shortlist words (50.6%) get at least one LUMRO hit.**
- **1,327 words would cross the `HIST_MIN_OCC`/`HIST_MIN_DOCS` attestation bar** that they
  currently fail. Every one of them is presently `absent` — the verdict meaning "no
  historical footing, and not common now: we simply have no evidence."

That last number is the case for LUMRO on its own. `absent` is the verdict that says the
pipeline could not tell, and a 7.5M-token dated literary corpus converts 1,327 of those into
an actual judgement.

### But ~170 of those never needed a new corpus — `hist_docs` has a defect

While testing the above I hit words like `văz` carrying `hist_occ 96` with `hist_docs 0`.
That is not a corpus gap. In `aggregate_by_family` (`validate_diachronic.py:376-388`),
occurrences are credited to every claimant lemma proportionally, but documents are
all-or-nothing:

```python
share = w / total
occ[lemma] = occ.get(lemma, 0.0) + o * share
if share >= DOMINANT_SHARE:          # 0.5
    doc[lemma] = max(doc.get(lemma, 0), d)
```

A lemma that is never the majority claimant of *any* of its surface forms therefore
accumulates occurrences but exactly zero documents. Traced:

| word | form | form occ / docs | claimants | share | result |
|---|---|---:|---:|---:|---|
| `soli` | `soli` | 317 / 149 | 3 | 0.418 | `hist_occ` 132, `hist_docs` **0** |
| `văz` | `văz` | 888 / 392 | 2 | 0.108 | `hist_occ` 96, `hist_docs` **0** |
| `nalt` | `nalt` | 439 / 300 | 2 | 0.223 | `hist_occ` 98, `hist_docs` **0** |

The occurrence arithmetic is correct (0.108 × 888 = 96 ✓). The document count is the
problem, and `verdict()` then applies `hist_occ >= 3 AND hist_docs >= 2`, so the docs half
vetoes the occ half. Across the shortlist: **5,780 rows (35.7%) have `hist_docs == 0`, and
170 of those have `hist_occ >= 3`** — attested by the pipeline's own occurrence threshold but
forced to `absent`. `soli`, `nalt` and `văz` are all in the **relevant** seam, so this is
visible in the default view.

The docstring says documents are "a conservative lower bound". The intent is sound; the
effect is a hard zero for non-dominant lemmas feeding a threshold that assumes docs and occ
are on comparable footing. Worth fixing before adding corpora, because otherwise LUMRO
papers over a defect instead of adding evidence — and the fix is a few lines against
16k rows of output that would otherwise shift for the wrong reason.

I have not changed it. Flagging rather than fixing since it is outside what you asked for.

### `subtitle_ro` cannot serve as evidence of modern usage — it is 1/6th folk-music TV

Measured 2026-08-10, after this document first recommended wiring it into the verdict. That
recommendation was wrong, and the reason is worth keeping.

`process_subtitles.py:5-7` describes the corpus as "~13M pre-tokenised word tokens from 966
YouTube clips (Digi24 news content)". The news half is real. The rest is not: comparing
per-token rates against CulturaX — both modern corpora, so the comparison is legitimate —
the most over-represented words are not news vocabulary but folk-song vocabulary:

| word | subtitle occ / docs | CulturaX occ | over-representation |
|---|---:|---:|---:|
| `țurai` | 57 / 2 | 616 | 119× |
| `mândruliță` | 41 / 15 | 216 | 242× |
| `neicuță` | 26 / 7 | 273 | 122× |
| `bunuț` | 42 / 30 | 546 | 99× |
| `lai` | 3,226 / 65 | 12,467 | 332× |

Reconstructing the clips those words come from (the dump's `Subtitle` table keeps `clipId`,
so this is checkable locally) settles it — all seven sampled clips are folk-music
programming, and two are transcribed lyrics rather than speech:

- clip 59 — "festivalului Național de folclor Constantin Arvinte"
- clip 194 — "Doina Timișului … Drumul Lung și frumos al jocului popular"
- clip 318 — "regina muzicii populare românești Irina Loghin"
- clip 918 — "festivalului concurs național de muzică populară Ciocârlia", and the transcript
  is the song itself: *"nu te iubeam dorule dorule / Unde mă culcam Dormeam dorule…"*
- clip 342 — lyrics plus visible ASR damage: *"cine vărui Că nu câș degetul în mic i pișe
  soară cu soară"*

Sizing it by clip, counting genre-naming words (`folclor`, `taraf`, `lăutari`, `doină`,
`ansamblul`, … — programme billing, not lyrics):

| folk threshold | share of tokens | share of **shortlist-word** occurrences | enrichment |
|---|---:|---:|---:|
| ≥ 3 genre markers | 15.6% | 27.5% | 1.76× |
| ≥ 5 genre markers | 9.0% | 21.4% | 2.37× |

**And 444 of the 2,446 shortlist words with any subtitle evidence (18%) appear *only* in folk
clips.** For those, "attested in modern broadcast media" means "sung in a traditional song on
television" — which is close to the definition of archaic, and the exact opposite of what the
signal would have been read as saying. Wiring subtitle presence into `verdict()` as evidence
of modern life would have rescued precisely the words the project exists to find.

So: **do not score it, and do not surface it as a modern-usage signal.** Two honest uses
remain, both optional:

1. **Filter and re-run.** `clipId` is already the document unit, so dropping clips above a
   genre-marker threshold and re-running `process_subtitles.py` yields ~11M tokens of
   actual broadcast news. That corpus *could* carry a modern-usage signal.
2. **Invert it.** "Occurs only in folk-music broadcast" is a genuine and interesting
   register signal — a *traditional-song* flag, close in spirit to `regional_only`. That is
   a feature, not a fix, and belongs behind a UI toggle like the other flags.

Nothing consumes the column today — `subtitle_ppm` is written into `ui.db` and no PHP or JS
reads it — so there is no live harm, only a trap for whoever wires it up next.

### CoRoLa's pre-computed frequency lists are downloadable — with a licence catch

Zenodo record 7091535 is real and open: `corola_frequencies.zip`, **114.1 MB**, 24 files —
12 word-based and 12 lemma-based lists, each in original / lowercase / no-diacritics /
both. Largest list 2.26M entries. Underlying corpus is 1B+ tokens, balanced across 71
sub-domains, including a spoken component.

This is the best value on either report's list: a balanced billion-token modern reference
requiring **no corpus processing at all** — a download and a join on lemma, against a
pipeline that already has lemmas. It directly attacks the panel's weakest point, which is
that "modern" currently means one web crawl.

**The catch is the licence: CC BY-NC-ND 4.0.** Non-commercial is fine here. *No-derivatives*
is the question, and it bears on a public site. Using the lists internally to compute a
verdict and publishing only the verdict is a defensible read; republishing the frequency
numbers themselves, or shipping them inside `ui.db`, is not. Decide that before wiring it to
anything user-facing — I would keep CoRoLa strictly as an input to `verdict`/`score` and
never surface a CoRoLa-derived count in the UI.

## Recommended order

Ranked by evidence gained per unit of work. The first three need no new corpus processing.

1. **Fix `hist_docs` in `aggregate_by_family`** (S). Credit documents proportionally, or take
   the max-share claimant rather than requiring ≥ 0.5. Recovers 170 words from a false
   `absent` and removes a confound from every measurement that follows.
2. ~~**Stop dropping `subtitle_occ` at the shortlist boundary, and use it**~~ — **withdrawn
   2026-08-10**, see the `subtitle_ro` section above. The corpus is ~1/6th folk-music
   television, 18% of the shortlist words it attests appear *only* in those clips, and
   scoring it would have rescued exactly the words the project is looking for. The plumbing
   defects are real (the paradigm-rolled `subtitle_occ` is dropped while the surface-form
   `subtitle_ppm` survives into `ui.db`) but nothing reads either, so fixing the plumbing on
   a signal that must not be used would be churn. Either filter the folk clips and re-run, or
   invert it into a traditional-song register flag — both are decisions, not chores.
3. **Ingest CoRoLa frequency lists** (S–M, licence decision first). Download, join on lemma,
   add as a second modern signal. No streaming, no GPU, no multi-day run.
4. **Ingest LUMRO** (M). 7.5M tokens, 175 files, trivial to parse. The real prize is the
   per-decade and per-author metadata: it makes "attested by ≥ 2 independent authors" and
   per-decade decline curves possible for the first time. Do not double-count its ELTeC
   overlap.
5. **Preserve CulturaX `timestamp` / `url` / `source`** (L — deferred). `process_culturax.py`
   currently keeps none of it; confirmed, the only metadata references in that file are
   parquet row-group internals. Grok is right that this would separate 2013 evidence from
   2023, and hundreds of independent hosts from one mirrored dictionary page. But it means
   re-running 40.3M documents, which is the most expensive single item available. Do items
   1–4 first; they are cheaper and several will change what you want out of this one.

Not recommended now: FuLG / OSCAR / CC-100 (more Common Crawl, not an independent sample);
MARCELL and other domain corpora (useful later as *controls* that produce a
`specialist_alive` status, not as general evidence); the "Who Wants to Be a Millionaire?"
dataset (too small and topically structured for frequency, though a fair validation set).

## Open questions

- Does the relevant seam survive contact with CoRoLa? A balanced billion-token modern corpus
  may show that words CulturaX misses are alive in registers the web underrepresents. That
  is the point, but it will move the shortlist, and `data/word_ids.tsv` must stay
  append-only through it.
- Is `absent` doing too much work? It currently absorbs both "genuinely no evidence" and the
  `hist_docs` defect above. Once item 1 lands, re-count it before deciding whether the
  historical panel is really too thin.
