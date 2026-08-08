# Backlog

Open bugs, debt, and enhancements. Add new entries with `- [ ]` and enough context to act on later.

---

## Bugs / Known Issues

- [ ] **Historical corpus is thin — 14.3M tokens.** Wikisource gives one occurrence =
  0.07 ppm, so the whole historical side rests on very few hits: 9,996 shortlist words
  (40%) sat on ≤2 occurrences before the 2026-08-08 rescore added `HIST_MIN_OCC`/
  `HIST_MIN_DOCS` floors. Those floors make the signal honest but they cannot create
  evidence — words genuinely used in 1880 but absent from Wikisource still read `absent`.
  This is now the largest remaining source of error. Options: more Romanian literature
  (archive.org, Gutenberg RO), the DLR/DLRLC literary citations already embedded in the
  dump's definition text (`GALAN,`, `CARAGIALE`, `DUMITRIU, N. 122` — a free, dated,
  in-repo citation corpus), or CoRoLa. The citation route is cheapest and worth costing
  first.

- [ ] **Variant detection only catches paradigm-sharing pairs.** `family_ratio` (see
  `make_shortlist.FAMILY_RATIO_VARIANT`) flags `politeță`/`politețe` and `uleu`/`ulei`
  because they share inflected forms. Phonetic respellings with unrelated paradigms —
  `vivliotică`/`bibliotecă`, `tăligraf`/`telegraf`, `sâroman`/`sărman` — are invisible to
  it, and are currently only kept out of the relevant seam by having no current
  dictionary. A phonological-correspondence matcher (`v→b`, `tăli→tele`, `î/â`) against
  corpus-alive lemmas would close the gap.

- [ ] **`oțios` sits in the `curiosity` seam.** Score 67: zero historical corpus
  attestation, 266 modern occurrences. Correct by the current rules, awkward for the
  project's namesake. Decide whether the naming question moves, or whether the
  no-corpus-signal (`dex_absent_highfreq`) class deserves its own treatment.

- [ ] **CLRE (clre.solirom.ro) spike — timeboxed.** 100 dictionaries aligned at entry and
  sense level, free access, from the "A. Philippide" institute. Deferred in the
  2026-08-08 audit because dexonline already yields 113 sources covering the same
  historical spine (Scriban, Șăineanu, CADE, DAR, DLR, DLRLC, MDA2), and `Source.year`
  supplies the recency signal CLRE would have been used for. Its unique value is
  *first-attestation dating* and dictionaries dexonline lacks (Lexiconul de la Buda 1825,
  Laurian–Massim 1871). No documented bulk export — check for one before building on it.

- [ ] **`extract_lexemes.py` still uses the lossy regex splitter.** `re.findall(r'\(([^)]+)\)')`
  drops rows containing a literal `)` in a quoted field. Measured impact is small — 33 of
  317,721 rows (0.01%), *not* the 13% first estimated from the AUTOINCREMENT high-water
  mark — so this is tidiness, not urgency. `dump_parser.parse_tuples` is the drop-in
  replacement and `extract_inflected_forms.py` already writes a complete `lexeme` table
  that could replace `lexemes.db` outright.

- [ ] **`create_curated_list.fetch_all_tags` misses root tags 6 (`rar`) and 239
  (`ieșit din uz`).** It walks parents `{1,17,41,42}` while
  `validate_diachronic.load_taxonomy` also catches `{6,17,239}`. So `dex_register` in the
  curated CSV is strictly narrower than in the diachronic one, which weakens
  `validate_with_wordfreq.py`'s archaic-register gate — it can never see two of the four
  markers in its own `ARCHAIC_REGISTER_MARKERS`.


- [ ] check why some words are still missing definitions even if found on dexonline. did scraping fail?

- [ ] `dreadnought` nu e marcat ca `marină` (Mar.) in our UI but it is in dexonline web

- [ ] **`rare_in_use` tier is polluted by modern loanwords + proper nouns** — the UI "rare" tab (`?word_tier=rare_in_use`) shows words that aren't rare: English borrowings (`screening`, `meeting`, `house`, `short`, `golden`, `dolby`, `wild`, `trend`, `scanner`, `cutter`), brand/variety names (`jonathan`), and proper nouns (`sioux`, `zulu`, `hagi`, `viking`). Two failing signals:
  1. **Low DEX `frequency` ≠ rare.** `create_curated_list.py:127-129` selects `0.01 < frequency < 1.0`; DEX `frequency` is editorial-coverage, not corpus frequency, so recent borrowings land in that band (`screening` 0.27, `meeting` 0.71, `house` 0.81) while still being everyday words.
  2. **Register gate too permissive** (`validate_with_wordfreq.py:151`): admits a word on `zipf < 4.5 AND dex_register non-empty` — *any* tag. Of 582 rows in `rare_words_wordfreq.csv` only ~124 are `învechit`; the rest are stylistic tags (`figurat` 172, `popular` 82, `familiar` 59, `livresc` 39) — exactly what colloquial loanwords carry. The gate was meant to require an *archaic* marker.

  Compounding: no loanword filter (some borrowings hit zipf 4.0–4.5, e.g. `house` 4.36, `jonathan` 4.25; `dex_etymology` is empty in the CSV so etymology filtering needs re-extraction); the proper-noun filter `create_curated_list.py:69-72` checks `word[0].isupper()` but the data is lowercased so it never fires; even `învechit` rows are noisy from homograph mismatches (`cannabis`→`învechit`, `listat`→`învechit`); 28 duplicate `word_no_accent` rows (e.g. `house` as `s.n.` and `adj.`). Loaded by `ui/app.py:122-144` (tier set at `app.py:142`). Sharpens enhancement #12. Fix options: (a) restrict the register gate to archaic markers (`învechit` + combos); (b) add a cross-lingual English-zipf loanword filter; (c) fix the proper-noun filter to run on cased DEX forms; (d) dedup by `word_no_accent`. Regenerating `rare_words_wordfreq.csv` means re-running `validate_with_wordfreq.py`. **Exploratory UI path added 2026-05-28** (see activity-history): the detail panel now shows zipf/en/dex/dict-names per word, and reversible filters (zipf range, dex range, hide-loanwords via `en_zipf`, hide-proper-nouns via DEX casing) let us triage interactively before deciding what to make permanent. Options (b) and (c) are now prototyped as UI toggles in `ui/app.py::_enrich_words` / `extract_dict_sources.py`.

  **Partially resolved 2026-06-07** — pipeline options (a) + (d) done in `validate_with_wordfreq.py`:
  - **(a) Register gate restricted to archaic markers.** New `ARCHAIC_REGISTER_MARKERS` (`învechit`, `arhaizant`, `rar`, `ieșit din uz`) + `has_archaic_register()`; the `rare_in_use` gate now requires one of these instead of *any* non-empty register. New `--rare-register {archaic,any}` flag (default `archaic`; `any` restores legacy behaviour). On the current curated CSV this cut `rare_in_use` from **582 → 113** and removed `screening`/`meeting`/`house`/`jonathan`/`sioux`/`zulu`/`viking` etc.
  - **(d) Dedup by `word_no_accent`.** New `--dedup` flag (default on) collapses same-headword rows that differ only by POS (e.g. `house` as `s.n.` + `adj.`); dropped 10,133 duplicate rows on the current input.
  - **Still open:** (b) cross-lingual loanword filter and (c) cased proper-noun filter remain *deliberately* as reversible UI toggles (per the 2026-05-28 triage note) rather than permanent pipeline filters — promoting them is a product decision. Residual noise in the archaic-gated rare list is now dominated by **sense-level homograph mismatches** (`cannabis`/`listat`/`spray`/`court`/`hagi` carry an `învechit` tag on a different sense than the modern one); these are caught today by the UI's `hide_loanwords` (en_zipf) and `hide_proper` toggles. Takes effect on next `validate_with_wordfreq.py` run.

- [ ] **P0 — Phase 2 candidate-set mismatch** (`process_corpus.py:56-67,187,292` vs `validate_forgotten_words.py:64-70`): `process_corpus.py` only counts tokens in `forgotten_words_curated.csv` (~1.9k words), but the validator queries `lexemes.db` with `frequency > 0.01 AND frequency < 0.60 AND LENGTH(form) > 3` (tens of thousands of lexemes). Words absent from the curated CSV silently get `total_occurrences = 0` and are classified as `confirmed_forgotten` with confidence ~0.99. The "159,543 validated, 1 false positive" headline in `docs/phase2-test-results.md` is an artefact. Fix: align the candidate source, or have `process_corpus.py` count every token.

- [x] **Three competing MySQL→SQLite paths** — Fixed. `extract_lexemes.py` is the sole canonical path; `convert_to_sqlite.sh` + `mysql_to_sqlite.py` moved to `archive/` (with `archive/README.md` explaining why). Note: `docs/scripts-guide.md` still documents `mysql_to_sqlite.py` as an "alternative approach" — left for a separate docs pass.

- [ ] **`explore_dex.py` is dead code** — imports `sqlite3` but never uses it; `__main__` points `db_path` at a `.sql` file that `sqlite3.connect()` cannot open. Content is narrative; move to `docs/` or delete.

- [x] **Frequency-bin definitions disagree across scripts** — Fixed. Added `constants.py` as the single source of truth: `MIN_FREQUENCY`, `MIN_FORM_LENGTH`, the canonical rarity-bin edges (`VERY_RARE_MAX`/`RARE_MAX`/`UNCOMMON_MAX`) + a `rarity_category()` helper, plus the per-stage candidate ceilings (`CURATED_FREQ_CEILING`, and the clearly-marked legacy `ANALYZE_FREQ_THRESHOLD`/`VALIDATION_FREQ_CEILING`). `create_curated_list.py` now bins via `rarity_category()` (removed two duplicated inline binning blocks); `analyze_forgotten_words.py` and `validate_forgotten_words.py` import their floors/ceilings. Boundary-tested: new binning matches the old logic exactly at every edge. Legacy display histogram bins in `analyze_forgotten_words.py` are coupled to its 0.70 candidate threshold and left script-local (documented as intentional in `constants.py`).

- [x] **Regex probable typo in `create_curated_list.py:28-32`** — Fixed: removed trailing apostrophe from `r"^[a-z]+-[a-z]+'"` so the hyphenation filter now actually fires. Was dead code (matched 0 words in the shortlist).

- [ ] **OSCAR auth fails silently** (`process_corpus.py:255-261`) — when `--full` is requested but the dataset is unreachable, the run silently skips OSCAR. Should fail loudly or warn clearly.

- [ ] **`download_wikipedia_ro.py` blocks on interactive `y/N`** — not scriptable without a `--yes` flag.

- [ ] **No CLI path overrides** — all scripts hardcode `data/dictionaries/` and `data/processed/`; `process_corpus.py` has `argparse` for mode only, not paths.

- [ ] **Confidence-score weights are unjustified** (`validate_forgotten_words.py:215`) — `dex×0.3 + corpus×0.5 + doc×0.2` was chosen ad hoc. Treat output as ordinal, not absolute.

- [x] **`load_taxonomy()` join is wrong — domain/register/etymology columns are noise** — Fixed. `extract_taxonomy.py` now extracts `TreeEntry(id, treeId, entryId)` and `MeaningTree(meaning_id, tree_id)` into `lexemes.db`. Both `load_taxonomy()` in `validate_diachronic.py` and `fetch_all_tags()` in `create_curated_list.py` use the corrected join chain `Lexeme → EntryLexeme → TreeEntry → MeaningTree → ObjectTag(objectType=3)`. Verified: `pretutindeni` now has no tags (correct), `antipapă` → français etymology (correct), `isihie` → `învechit` register + neogreacă etymology (correct). **Re-run `validate_diachronic.py` to regenerate the shortlist CSV with accurate taxonomy columns.**

---

## Enhancements

Ranked by impact-per-effort. Effort: XS / S / M / L.

- [ ] **#0 — [S, High] Full Wikisource + CulturaX corpus runs** — `process_wikisource.py` done (14.3M tokens in DB). `process_culturax.py` rewritten 2026-05-12 to use per-parquet-file checkpointing (bypasses `datasets` streaming entirely; no `ds.skip()` cycling bug). Fresh CulturaX run started 2026-05-12; ~40M docs across 64 shards. `validate_diachronic.py` written — computes log2(hist_ppm / modern_ppm) per word, outputs `forgotten_words_diachronic.csv` with verdict (extinct/declining/stable/emerging). Meaningful results require both corpus runs to be complete. See `docs/corpus-options.md`.

- [x] **#0 (old) — wordfreq as primary filter** — tried and found too coarse for Romanian: signal is binary (0.000 or ≥ 3.0, nothing in between). `validate_with_wordfreq.py` remains useful as a rough first pass but cannot replace corpus-based validation. Superseded by Wikisource/CulturaX approach above.

- [x] **#1 — Fix Phase 2 candidate-set mismatch** — fixed in `process_wikisource.py`: loads all ~15k quality DEX forms from `lexemes.db` (frequency > 0.01, description not empty, length > 2) instead of the 1.9k curated CSV. `process_corpus.py` remains unfixed (legacy, low priority).

- [ ] **#2 — [XS, Med] `pyproject.toml` with PEP 621 metadata** — `requirements.txt` exists but no install metadata.

- [x] **#3 — [S, Med] Pick one MySQL→SQLite path; archive the others** — Done. `extract_lexemes.py` is canonical; `convert_to_sqlite.sh` + `mysql_to_sqlite.py` moved to `archive/`.

- [x] **#4 — [XS, Low] Delete `explore_dex.py`** — Deleted. Content was narrative documentation that couldn't run; the useful structural notes are covered by `docs/conceptual-roadmap.md` and `CLAUDE.md`.

- [x] **#5 — [S, Med] Centralize frequency bins in `constants.py`** — Done. Single source of truth for `MIN_FREQUENCY`, `MIN_FORM_LENGTH`, the canonical rarity bins + `rarity_category()` helper, and per-stage candidate ceilings. Canonical `create_curated_list.py` fully driven by it; legacy scripts import their floors/ceilings. Behaviour preserved (boundary-tested).

- [x] **#6 — [M, High] Add lemmatization with `simplemma`** — implemented as a post-classification dedup step in `make_shortlist.py` (2026-05-28). Collapsed 1,571 inflected/derived forms into their canonical lemmas (e.g. `abecedare`→`abecedar`, `murea` removed when alone). Shortlist: 26,788 → 25,217 words. **Remaining gap:** Romanian verb-derived nouns and participial adjectives (`bleui`/`bleuire`/`bleuit`) are not reduced by simplemma and still appear as separate entries. Full corpus-level lemmatization (`bucle`→`buclă` matching) still outstanding.

- [ ] **#7 — [M, High] `tests/` with `pytest` + `ruff` + GitHub Actions CI** — cover normalization and curation heuristics at minimum.

- [ ] **#8 — [S, High] Re-run Phase 2 after fixing #1** — overwrite `docs/phase2-test-results.md` with honest numbers.

- [ ] **#9 — [M, Med] Parallelize tokenization** with `multiprocessing.Pool`.

- [ ] **#10 — [XS, Low] `--yes` flag on `download_wikipedia_ro.py`** — makes it scriptable.

- [ ] **#11 — [S, Med] Calibrate confidence-score weights** — document methodology or at least test sensitivity.

- [ ] **#12 — [M, Med] Filter modern borrowings** — English/French loanwords and brand names inflate false-positive rate.

- [ ] **#13 — [S, Low] Structured logging + `--quiet` flag** — replace decorative banners with levelled output.

- [ ] **#15 — [L, High] Re-run both corpus scripts after load_dex_words() fix**

  `process_culturax.py` and `process_wikisource.py` both had `AND description != ''` in `load_dex_words()`, mirroring the bug fixed in `create_curated_list.py`. Words with empty DEX description but a valid word-class `modelType` (N, F, M, A, VT, VI…) — e.g. `jurnalism`, `ziar`, `lactoză`, `incompetență` — were silently excluded from corpus tracking, so their occurrences were never counted even across 40M CulturaX documents. Both scripts now use the corrected filter (description OR modelType). The corpus DB is stale until both runs complete.

  - **Wikisource re-run**: fast (~minutes on VPS). Wipe `wikisource_ro` rows from `corpus_word_frequency` and `processing_stats`, then `python process_wikisource.py --resume` (checkpoint will be ignored since the word set changed — better to delete `wikisource_checkpoint.json` and run clean).
  - **CulturaX re-run**: long (~hours on VPS). Same procedure: delete `culturax_checkpoint.json`, wipe `culturax_ro` rows, restart. The tracking set grew from ~15k to ~137k words so a full re-scan is necessary.

  Until re-run: `absent` verdict in `forgotten_words_diachronic.csv` conflates "truly unused" with "not tracked by old filter" — results for words with empty DEX description are unreliable.

- [ ] **#14 — [S, Med] Re-evaluate `absent` words for web validation** — after the Phase 1 cutoff was raised to `< 1.0`, the diachronic output now has ~124k `absent` entries (no corpus signal in either Wikisource or CulturaX). Words like `oțios` land here: DEX-canonical but unattested in any corpus. A web validation pass on a filtered `absent` subset (e.g. DEX freq ≥ 0.70, model_type A/N/VT, no loanword markers) could surface genuinely forgotten words that never made it into digitised text.

- [x] **#16 — [M, High] Enrich output CSVs with DEX taxonomy tags** — Done. `Tag` (410 rows), `ObjectTag` (461 k rows), and `EntryLexeme` were already in `lexemes.db`. `create_curated_list.py` now bulk-fetches tags via both join paths (objectType=2 direct, objectType=3 via entry) and writes three new columns to `forgotten_words_curated.csv`:

  - **`dex_register`** (parentId=42 + 17): `învechit`, dialectal, popular, arhaizant, livresc, regional sub-tags (Banat, Moldova, Transilvania…) — 7,642 words covered
  - **`dex_domain`** (parentId=41): botanică, medicină, informatică, chimie, etc. — 3,405 words covered
  - **`dex_etymology`** (parentId=1): limba maghiară, germanism, slavonism, franțuzism, etc. — 35,120 words covered

  Columns flow through `validate_with_wordfreq.py` automatically (DictReader/DictWriter preserves extra fields).

- [x] **#17 — [XS, Med] Flag words with no definition body** — Done. The `has_definition` column already existed in `forgotten_words_diachronic.csv` (and flows into the UI via `validate_diachronic._load_definition_words` → `ui.db.words.has_definition`), and DEX headwords with no extractable definition already land as `has_definition=0` simply by being absent from `definitions.db`. The remaining leak: dexonline's "[Fără definiție.]" placeholder rows (where the entry exists but only usage citations follow) were counted as real definitions. Fixed with `is_placeholder_definition()` in `validate_diachronic.py` — a definition is a placeholder when missing/blank or when "[Fără definiț…" *leads* the text (mid-text occurrences in multi-sense words like *perină*/*spectacul* still count). Mirrored in `ui/app.py` definition load so the UI `has_def` filter and panel text stay consistent (placeholder words still appear, just with no local definition body, linking out to dexonline). Scale in the current `definitions.db`: 7 placeholder-only words (`animaltecă`, `apastop`, `fibrinactiv`, `magnetodiaflux`, `narcorublă`, `perfluorbutilamină`, `relin`). Takes effect on the next `validate_diachronic.py` run / `ui.db` rebuild.

  Note: these words are kept, not dropped — a word documented only as a borrowing with no translation is itself a sign of marginal integration into Romanian.

- [x] **#19 — [XS, Low] Annotation overlay overflow for heavily-annotated words** — Capped at 3 emojis + `+N` superscript in muted mono for the remainder. Template now builds `_ov.items` list instead of string; slices `[:3]` and appends `<span class="ann-more">+N</span>`.

- [x] **#20 — [S, Low] Annotation overlay goes stale after in-panel mutations** — Fixed via HTMX OOB swap: `/bookmark/<word>` and `/tag/<word>/*` routes now re-render the affected `.word-row` partial alongside the detail panel swap so the overlay emoji stays current without a search trigger.

- [ ] **#18 — [L, Med] Extract per-document metadata from corpora for temporal and domain signals** — Currently both corpus scripts discard document-level metadata and only keep aggregate word counts. Two signals worth extracting:

  - **Temporal distribution (CulturaX)**: parquet files carry a `timestamp` field per document. Storing a year histogram per word (e.g. JSON column `year_dist` in `corpus_word_frequency`) would let us answer "when did this word last appear in web text" — a direct measure of *when* usage dropped off, richer than a single `modern_ppm` value. A word with 90% of hits before 2015 and nothing recent is differently forgotten than one that's uniformly rare.
  - **Source domain (CulturaX)**: classify document URLs by type (news, forum, academic, government, blog). A word that survives only in Wikipedia or legal text but never in news or social content is a different kind of relic.
  - **Historical period (Wikisource)**: documents have author/title/century metadata. Words clustering in 19th-century prose vs. spanning multiple centuries give a richer diachronic signal than raw `hist_ppm`.

  **Practical approach** — full reprocessing is expensive. Better: after identifying `extinct`/`declining` words via the current pipeline, run a targeted second-pass scan over CulturaX parquet files for just those ~few thousand words, collecting date and URL metadata. Wikisource period attribution is cheap (12k docs) and could be a side-table join without reprocessing.

  Schema sketch: add `year_dist` (JSON), `domain_dist` (JSON) to `corpus_word_frequency`, or a separate `word_temporal` table keyed on `(word, corpus_name, year)`.


- [x] **#19 — [S, Med] Research UI: browse/filter by more metadata fields** — the filter bar currently exposes verdict, tier, and sort order. Useful additions:

  - **Domain filter** (`dex_domain` column) — already loaded in the `words` table. A `<select>` populated from distinct non-null domain values would let researchers exclude technical jargon (e.g. medicină, drept, informatică) from results, since a domain-specific word being rare in a general corpus is expected, not "forgotten".
  - **Etymology filter** (`dex_etymology`) — filter by language family (slavă, turcă, latină, franceză, engleză, etc.) to answer questions like "are Turkisms more likely to go extinct than Latinisms?"
  - **Register filter** (`dex_register`) — surface all words already tagged `înv.` / `înv` in DEX as a gold-standard archaism set; or exclude them if you want to find words that *aren't* already labelled archaic.
  - **Has definition toggle** — filter to only words with a local definition (definition IS NOT NULL) to avoid clicking through words where the only option is the dexonline link.

  Implementation: each filter is a `<select>` using the same HTMX pattern as the existing verdict/tier dropdowns; `/search` adds a WHERE clause from a safe allowlist. Distinct values for the dropdowns can be computed once at startup from the in-memory `words` table and passed to the template via `g` or a route argument.

- [ ] **#20 — [L, Med] Metadata navigator** — Dedicated tool for browsing the word list by taxonomy and computing metadata statistics. Complements #19 (web UI filters) with deeper analytical access.

  **Statistics view** — aggregate counts and cross-tabulations across the three tag families:
  - Words per register tag (`înv.`: N, `dialectal`: N, …) and per domain tag
  - Etymology breakdown (how many words per source language; which languages contribute most to the "extinct" vs "stable" pools)
  - Co-occurrence matrix: e.g. "how many maghiarisms are also dialectal?", "what fraction of botanică terms are `înv.`?"
  - Frequency distribution (histogram of DEX `frequency` values) within each tag bucket

  **Browse view** — filter and page the curated/diachronic CSV by any combination of tags, with optional sort by verdict or frequency.

  **Implementation sketch** — standalone `browse_metadata.py` reading from any enriched CSV:
  ```
  python browse_metadata.py stats                    # aggregate counts table
  python browse_metadata.py list --register=înv.    # words with that register tag
  python browse_metadata.py cross register etymology # co-occurrence matrix
  ```
  Input: any CSV with `dex_register`, `dex_domain`, `dex_etymology` columns (output of `create_curated_list.py` or `validate_diachronic.py`). See also #19 for web UI filter dropdowns using the same columns.

- [x] **#22 — [S, Med] Hybrid word-marking UX: reserved one-key tags + tag autocomplete** — Done. `i`/`B`/`f`/`x` keydown shortcuts toggle tags via `/tag/<word>/toggle/<tag>`; quick-tags render as a dedicated button row in `tags_row.html` (filtered out of regular pill list); `t` focuses tag input; `<datalist id="tag-suggestions">` backed by `/tags/suggest`; shortcuts modal updated.

- [x] **#21 — [M, Med] Factor in dictionary coverage (how many dictionaries list a term)** — Done. `dict_count` (distinct `sourceId`s per headword) streamed from DEX MySQL dump in `validate_diachronic.py:_load_dict_counts()` (~12s for 301k headwords). Column flows through `make_shortlist.py` → `build_ui_db.py` → UI `words` table; displayed as a `<em>dicts</em>N` chip in `detail.html`.

- [ ] also have a look at [wiktionary](https://ro.wiktionary.org/)

- [ ] go for root semantics fro definitions like _"Acțiunea de a (se) spârcui și rezultatul ei."_



## UI

- [x] make space for columns a bit wider — grid minmax raised to 120px.

- [x] bring superscript count badge closer to word — margin-left 3px → 1px.

- [x] make definition text larger — bumped to 15px; removed inline 11.5px override in detail.html.

- [x] keyboard nav, after focusing on searchbar and filtering words it's hard to get focus back on the term list — Esc from search now restores selectedIdx via selectRow(noClick=true).

- [x] optimize for mobile

- [x] mobile, when scrolling, hide definition drawer. after focus moves on the list

- [x] in info window show which dictionaries this word is found in — `sources` column added to `ui.db` from `dict_sources.db` (98.2% of words matched, exact + diacritic-normalized fallback); rendered as a "📚 N dicționare" chip list in the detail panel. Build: `tools/build_ui_db.py merge_dict_sources()`; one-time backfill: `tools/migrate_ui_db_sources.py`. (Wiktionary membership not yet a data source — separate task.)

- [x] desktop tooltip on hover with definition — floating `#def-tip` div populated from existing `data-def` attribute on `.word-row` via `mouseover`/`mouseout` on the word-list-container. Positioned below the chip (above if near bottom of viewport). No extra network requests.

- [x] top filter, the posibility to remove one attribute - now we can just select. — added an "active filters" chip bar (`#active-filters`) that lists each non-default filter (search, taxonomy selects, ranges, hide toggles, partial verdict/tier/POS groups) with an individual ✕ to clear just that one, plus a "resetează tot". See `renderActiveFilters()` in `app.js`.

- [ ] create statistics by metadata. in the limited corpus and later in whole dexonline

- [x] shareable word viewer url - focus on the word — `?word=<word>` already encoded in URL when panel opens (`syncUrlFromForm`). On page load: panel re-opens via HTMX (`/api/word.php`); after the word list swaps in, `htmx:afterSwap` now also calls `selectRow(idx, true)` to scroll to and highlight the word in the grid.

- [x] hide terms marked as `remove` — hidden by default; "show removed" pill in filter bar re-shows them. ~~**Open question**: what's the semantic difference between `ignore` and `remove`?~~ Resolved: documented as *ignore = not interesting to you (skip)* vs *remove = not a genuinely forgotten word (exclude)*; tooltips added to the quick-tag buttons and the shortcuts modal.

- [x] make .flabel bolder (negative). remove distance between .flabel and choices. Use narrow font for the filter bar — switched to mono 11px bold var(--text-2), removed min-width/excess padding.

- [x] load more words when page scrolled to bottom — replaced "load more" button with HTMX `intersect once` sentinel; auto-loads as you scroll.

- [x] if I click a word with the mouse the focus doesn't move there. Keyboard and mouse choice is not synced — delegated click listener on word-list-container now sets selectedIdx on mouse click.

- [x] longer words break in the info box, make left panel responsive / flexible width — fp-word changed from fixed 170px to auto (min 140px, max 240px).

- [x] mark words that have attached notes or tags/flags. Filter words by tags — dot indicator done; quick-tag filter options (ignore/boring/funny/remove) already in marks select. Custom tags (user-defined via tag input) now also dynamically added to the marks `<select>` via `populateTagFilterOptions()` — called at init and whenever a custom tag is added or deleted.

- [x] select word by typing — type-ahead navigation: unbound printable chars accumulate in a 1.2s buffer, jumping to the first visible word whose normalized text starts with the buffer. Diacritic-insensitive (ț→t etc). Documented in shortcuts modal.

- [ ] search bar also accepts metadata - filters. Later / nice to have enhancement: fancy search, like in gmail with autocomplete and style options. Search box also accepts filtering attributes.

- [x] **Diacritic-insensitive search** — searching `otios` should find `oțios`; `stramosesc` should find `strămoșesc`. Normalize both the query and the indexed word by stripping diacritics before matching (ț→t, ș→s, ă→a, â→a, î→i). Implement in the SQL WHERE clause using a pre-computed `word_normalized` column in the `words` table (populated at build time), or a SQLite custom function. Both PHP and Flask search endpoints need updating.

- [x] **synonyms data** — done 2026-08-08. `scrape_synonyms.py` → `synonyms.db` → `words.synonyms`/`words.antonyms`, rendered as linked chips in the detail panel. Not available from the dump: the Litera dictionaries (`Sinonime`, `Sinonime82`, `Antonime`) are redacted to 23 characters in `Definition.internalRep`, so `dict_count` knows a word is in them but not what they say.

- [ ] **UI redesign** — fresh-identity, mobile-first redesign spec written for a designer in `docs/design-brief.md` (covers table view, filter-bar redesign, calmer verdict palette, play modes, shared-word landing). Hand off when ready.

- [ ] later show extended definition. everything in dexonline but compact

- [x] exploratory interface. to the point of screensaver. or like tiktok / Tinder feed, but limit per day — shipped as **feed / swipe mode** (`📇 feed` button): one word-card at a time, keep (→ / swipe right → bookmark) or skip (← / swipe left), respects current filters, with a soft daily count (`FEED_DAILY_LIMIT`). Endpoint `api/feed.php`. Further "screensaver"-style auto-advance is a possible enhancement.

- [ ] **Verdict palette saturation review** — four full-saturation colors (red/brown/blue/purple) in the word grid compete equally for attention; consider one dominant verdict color + three muted, or shift to a single-hue density encoding. Out of scope for the 2026-05-18 fine-tuning pass.

- [x] **Bookmark + învechit underline conflict** — switched `.inv .word-text` from `text-decoration: underline dotted` to `border-bottom: 1.5px dotted`. The two indicators now coexist: amber `text-decoration` for bookmark + red dotted `border-bottom` for inv.

- [ ] **Mobile / narrow-viewport breakpoints** — `ui/templates/base.html` has no media queries; the 3-row filter bar and word grid are desktop-only. Add breakpoints for tablet (collapse filter rows into a single overflow menu) and phone (single column word grid, slide-up detail panel from bottom).

- [x] **Filter bar tooltips** — `title` attributes added to all filter bar controls: uitate/rare toggle, verdict pills (with per-verdict explanations), tier pills (with corpus/DEX logic notes), POS pills (full Romanian name as title), sort select, marks select, def toggle, domain/register/etymology/dict_min selects (domain tooltip flags the "any-sense" matching caveat), reset button.

- [ ] **URL-encoded filter state** — encode all active filter values (word_tier, verdict, tier, sort, pos, register, domain, etymology, has_def, marks, q) into the URL query string on every filter change, so that the current view is bookmarkable and shareable. Use `history.replaceState` (no page reload) to update the URL as HTMX triggers fire; parse and restore from `window.location.search` on page load to pre-select the right controls. Both PHP and Flask apps should support this.

- [ ] **Extract inline CSS to `ui/static/app.css`** — `ui/templates/base.html` carries ~870 lines of inline styles. Move to a static stylesheet so it can be cached + edited without touching templates. Set up Flask's static directory if not already wired.

- [ ] do we actually need the word search bar? Does word search add any overhead? Word exploration/discovery should be done by categories, this is not a dictionary. Maybe turn it into attribute search bar. 

- [ ] final list of words, mark some, then pass through llm to filter some more.

- [ ] Meta tags, Open Graph fields, description og image etc

- [ ] web ui: follow schema.org for appropriate entities - add to claude.md maybe?

- [ ] SEO Audit. Including `/llms.txt` 

#### joc.php
- [ ] filter out too easy queries - word part/segment that repeats in definition
- [ ] one word can have multiple definitions, include within the choices?
- [ ] mark words as unworthym, too simple 
- [ ] add bookmarking, favorites, add to list here - by using the game we create an audit tool

## Misc

- [x] create methodology, including activity log, look at activity log and commit history

- [x] tune parameters until it includes `oțios` – maybe use a flag to hide these other, second tier words (new words beyond  current list/limits). What we would also like to surface would be words that are rarely used, but worth attention. The sweet spot might not be totally forgotten words, but let's see which are the rare words but still in use. For the UI we could use a global switch flag. Which corpus to browse, forgotten or rarely used terms?
  - **Resolved (pipeline side)**: `validate_with_wordfreq.py` now emits a `tier` column (`forgotten` / `rare_in_use` / `common`) alongside the existing `is_forgotten` bool. Default thresholds: `--threshold 3.0` (lower, forgotten floor) / `--upper-threshold 4.5` (upper, common cutoff). Rare-in-use words (3.0 ≤ zipf < 4.5) are written to a separate `data/processed/rare_words_wordfreq.csv` so they don't contaminate the forgotten list. Note: `oțios` itself has zero corpus signal (zipf=0.000) so it lands in `forgotten`, not `rare_in_use`.
  - **Still open (UI side)**: add a global switch in the web UI to toggle between the forgotten-words list and the rare-in-use list.

- [ ] maybe we should also look in the dictionaries themselves. Are we including really old dictionaries? We could make a page with per dictionary `diff`? Does dexonline dump cover all dictionaries listed here: https://clre.solirom.ro/  https://clre.solirom.ro/content/ro/list-of-lexicographical-works.html https://clre.solirom.ro/content/ro/statistics.html 

- [x] handle in browser curration - choices saved in browser memory and can be exported as json — **partly done**: annotations now sync to `private/app.db` via `api/sync.php`, so curation survives a browser wipe and follows the user across devices on the same account. localStorage remains the offline-first cache. A JSON *export* button is still missing; the data is reachable at `api/sync.php` with `{"since":0}`.

- [x] publish favorites, custom lists even to a web server. make it a collaborative experience. Eventually publish these currated lists and showcase popular words on the main website. — named lists (`api/lists.php`) with a public page at `lista.php?l=<slug>`, plus a streak leaderboard (`api/leaderboard.php`). Identity is an anonymous device token; a display name is requested only when publishing. **Showcasing done 2026-08-07**: `liste.php` carries a *Liste publice* directory — every `is_public` list with at least one word, newest first, with its owner's nickname (`GET api/lists.php?public=1`). Publishing itself moved server-side: `POST {action:'publish_bucket', bucket}` reads the words from the caller's own annotations, so the client no longer uploads the list it is publishing, and `{action:'refresh', id}` re-syncs a published list from its `source_tag` bucket. **Still open**: aggregating which words are most-bookmarked *across* users (a per-word popularity signal, distinct from per-user lists).

- [ ] metadata navigator - add wordfreq and scarcity - the result of this project. 

- [ ] try a super dorpdown navigator, where it can reach all metadata options, witih contextual keyboard shortcuts. or just search by visible terms. but how can we select more or exclude, to make it crazy good? With streer count in brackets?

- [x] **New DEX dump intake** — downloaded `dex-database.sql` (1.65 GB); old dump renamed `dex-database-1.sql` (1.27 GB). Schema is nearly identical (one new index on `Lexeme.pronunciations`). Data growth: Lexeme +3,774, Entry +3,469, ObjectTag +38,074, Meaning +13,367, TreeEntry +5,404; DefinitionSimple unchanged. Four new tables: `Subtitle` (13 M rows — individual Romanian words from 966 YouTube clips, confirmed Digi24 news content, good modern-Romanian corpus candidate), `VideoClip` (966 rows, YouTube IDs), `OCR_stats`, `student`. Actions taken: re-ran `extract_lexemes.py` and `extract_taxonomy.py` against new dump to refresh `lexemes.db`. `validate_diachronic.py` not re-run (waiting for taxonomy join fix above). Subtitle corpus: see #XX backlog entry.

- [x] **definitions.db has severe word→definition misalignment** — `abac` (abacus) is paired with a bacteremia definition; `vânzător` gets a paranasal osteoma definition; `acătarii` has no entry at all despite dexonline showing one. The DB has 83,609 rows so the content is present, but the word↔text association is broken. Likely cause: the extraction script joins on a row offset or integer key that doesn't stably map across tables (e.g. `Lexeme.id` vs `Meaning.entryId` vs `Entry.id` — a multi-hop join gone wrong). Fix: re-examine the extraction query against the DEX MySQL schema; spot-check 10–20 words against dexonline.ro to confirm the join path. Related: the existing `drăngălău` note below.
  - **Resolved**: root cause was a misunderstood schema, not a join error. `DefinitionSimple.lexicon` is the headword (despite the misleading column name), not a dictionary identifier. The old code joined `Lexeme → EntryLexeme → EntryDefinition → DefinitionSimple` and picked the rank-1 definition for each Entry, but Entry records group multiple related-but-distinct words, so the rank-1 definition is often about a *different* word. Fixed by reading `DefinitionSimple.lexicon` directly as the headword key. See commit 8113dbf and `docs/DEFINITIONS_ANALYSIS.md`. Gaps still in the dump are filled by `scrape_definitions.py` (synthesis tab from dexonline.ro).

- [x] **Garbled definitions from DEX dump extraction** — Root cause: `_parse_values` parsed `\n` as the literal letter `n`, leaving dump indentation spaces in the output. Fixed: added full escape table (`\n`, `\r`, `\t`) + `re.sub(r'\s+', ' ')` normalization in `_clean`. Re-ran `extract_definitions.py` + `--merge-only`. Garbled count: 3,152 → 0.

- [ ] turn filters from the first row into checkboxes. all selected at first. so we can combine

- [ ] create a statistics page. guide yourself by existing filters options. Maybe the statistics page could keep the existing filters - to create dynamic / sliceable statistics?

- [x] **domain taxonomy contains compound nodes with semicolons** — resolved. `_normalize_sep()` in `build_ui_db.py` converts `'; '` → `'|'` before writing `dex_domain` to the DB; the `vocab` table then splits on `|` when counting. Result: `'mineralogie; minerit'` in the raw CSV becomes two separate vocab entries (`mineralogie`, `minerit`) and is filterable individually. Verified in current `ui.db`: no compound strings remain in vocab or in the `dex_domain` column.

- [ ] **domain filter matches on any sub-sense, not primary meaning** — `dex_domain` is set at the word level by aggregating all per-meaning domain tags from DEX. This means a word like *simpatie* (meaning: emotional affinity) appears under medicină because DEX tags one secondary sense as medicină ("legătură între organe simetrice" = sympathetic nerve link); *scaon* appears because DEX tags the compound *scaun rulant* (wheelchair) as medicină; *pipăi* appears for its medical sense of "to palpate". The tags are correct in the source data — this is how DEX models domains. The UI filter is therefore "has at least one medicina meaning" rather than "is primarily a medical word", which can be confusing. Options: (1) show per-word domain count in the word card so the user can judge; (2) add a "strict" domain mode that only matches words whose *only* domain tag is the selected one; (3) document this in a filter tooltip. Related: compound-semicolon entry above.

- [x] definitions have some bugs, `drăngălău` has the `constituent structural al oțelurilor călite și revenite` definition but on the web it doesn't have it https://dexonline.ro/definitie/dr%C3%A2ng%C4%83l%C4%83u/definitii — **resolved** by the same fix as the misalignment item above; `drăngălău` now reads from `scrape_definitions.py` because the DEX dump has no `DefinitionSimple.lexicon='drăngălău'` row.

- [ ] see [260515 notes - missing oțios.md](260515 notes - missing oțios.md)

- [ ] **[Upstream] Report DefinitionSimple truncation to dexonline developers** — both the old dump (`dex-database-1.sql`, 1.2 GB, Oct 2025) and the new dump (`dex-database.sql`, 1.5 GB, May 2026) contain only **61,041 rows** in `DefinitionSimple`, while `EntryDefinition` references **1,379,043** definition IDs — a 94.8% gap of dangling references. This means ~12.8k of our ~17.4k shortlist words have no extractable definition from the dump and must be scraped from dexonline.ro instead. The issue is not a bug in our extraction: `DefinitionSimple.lexicon` correctly identifies headwords; the referenced definition records simply are not present. Worth filing a bug or opening a discussion on the dexonline GitHub/forum so future dump consumers don't hit the same wall. Include: table row counts, the orphaned-reference count, and the impact (scraping as workaround).

- [ ] track synonyms. count synonyms

- [ ] also filter by: masculin, feminin, neutru.

- [ ] Meta: suggest versions, note in both activity log, chronology and readme.

- [x] I also see on dexoline the tag 'rar' but in our interface filters I only see 'învechit' see [săhăstricesc](https://dexonline.ro/definitie/săhăstricesc) — Fixed: `rar` (id=6), `regional` (id=17), `ieșit din uz` (id=239) were root-level DEX tags missed by the `parentId IN (1,41,42)` filter. Extended taxonomy loader to capture them and their children (Banat, Moldova, etc.). `rar`: 2,463 words; `regional`: 3,202; `ieșit din uz`: 95.

- [ ] **Subtitle corpus from new DEX dump** — `Subtitle` table in `dex-database.sql` has 13 M pre-tokenised Romanian word tokens from 966 YouTube clips (Digi24 news). Quick sample: 89k tokens → 11,240 unique types; top words are normal function words. Estimated 1.4% shortlist word coverage in sample (scales to ~20% at full 13M tokens). Too small to replace CulturaX as primary corpus, but valuable as a modern spoken-register spot-check. To use: write `process_subtitles.py` that extracts `SELECT word, COUNT(*) FROM Subtitle GROUP BY word` via `extract_lexemes.parse_mysql_insert` (or a dedicated streaming extractor) and loads into `corpus_frequencies.db` under `corpus_name='subtitle_ro'`. VideoClip table links clipId → YouTube videoId (11-char IDs) if metadata is needed.

- [ ] create presentation video. With Playwright and a scenario, subtitles and generated voiceover. Create youtube account / channel.

- [ ] link to [straturi.mariuscomper.uk](https://straturi.mariuscomper.uk/) / [proiecte/?topic=language](https://mariuscomper.uk/proiecte/?topic=language)

- [x] sharing word lists, can we make them (the url) more compact? compress list of ascii, incl separators? see [gemini](https://share.gemini.google/cHCYz4WpYBrK), [chatgpt](https://chatgpt.com/share/6a746c7a-4150-83ec-96ca-771dc2e47cfa) (both saved under `docs/reference/`) — Done 2026-08-07 via **dictionary indexing**, the option both conversations converge on for a fixed vocabulary. `?words=școală,învățământ,…` became `?w=1.4z.1f2.…`: a version prefix plus one base36 word id per word. Measured 11 chars for 3 words vs 44, 38 vs ~120 for a whole-URL comparison. Neither LZ-string nor gzip was used — with a 25k closed vocabulary, ids beat generic compression and need no library on either side.

  The ids come from `data/word_ids.tsv` (`tools/word_ids.py`), which is **append-only and force-tracked in git** despite the blanket `data/*` ignore. That is the load-bearing part: `ui.db` is deleted and rebuilt on every data refresh, so an id derived from row order would silently repoint every link ever shared. Words are never renumbered and never removed — a word dropped from a later shortlist keeps its id. `build_ui_db.py` assigns ids to new words at the end of a build; `tools/migrate_ui_db_word_ids.py` backfills an already-deployed `ui.db`.

  Codec is `pack_words()` / `unpack_words()` in `api/_lib.php`, exposed to the browser as `api/pack.php` so the client never carries the dictionary. `search.php` accepts `w=` and still honours the old `words=`, so links shared before this keep working. A `w=` that decodes to nothing (mangled, or a future version) yields an empty grid rather than falling through to all 25k words.

- [ ] also count synonyms! - filter by the number of synonyms.

- [ ] filter words that appear in only a few dictionaries? – but maybe those words are not interesting as the main scope of the project – we could use a separate db for ancient words?

- [ ] feed, does it hide words in the mainlist? - it should show all tagging options too. and up favorites. down = lol - or show more info?

- [x] top bar, show links to lists (favs, lol, more) fav, the rest are dropdowns if more than 1 — Done 2026-08-07, as a page rather than a dropdown. `📋 liste` in the status bar (and in `joc.php`'s nav, and on `lista.php`) now goes to **`liste.php`**, which lists all four buckets — `fav` / `lol` / `ascunde` / `meh` — with counts, an "open in explorer" link and a publish button each. The `#lists-overlay` modal it replaces was deleted along with ~125 lines of `app.js` and its CSS in `app.css`/`brutal.css`.

  The framing that made this simple: **the buckets *are* the lists.** They are derived from `app.db.annotations` on every request (via the existing `annotated_words_subquery()`), never stored, so they cannot drift. A row in the `lists` table is a *published snapshot* of one — which is why publishing is one button and there is no list-building UI, no per-word "add to list", and no inline list editing.

  - [ ] allow users to submit / post lists - but use captcha? - implement but not activate, as a honeytrap?

  - [ ] then maybe allow users to submit examples of rare words in the wild? - provide gSearch query - then let them submit

- [ ] caută un cuvânt - what good is this for? - hide it at least under a magnifying icon

- [ ] make initial view a grid, split by columns? and the table view, also on 2 or 3 colums on desktop?

- [ ] infinte scrolling ok, but update the url bar each say, 100 words, so one can pick up from there - besides the filters?

- [ ] mode in each selected words are hidden - for exploration

- [ ] make a list with _*-ațiune_


## Post launch

- [ ] traffic analytics
- [ ] SEO webmasters registrations
- [ ] write scientific paper(s). 1. method, 2. conclusions – co-publish with academic?
- [ ] write articles, scena9 or such

### Extend

- [x] quizzes — multiple-choice quiz (definition → pick the word, 4 same-POS choices, target word masked in the prompt) on `joc.php`, with streak/record in localStorage. Endpoint `api/quiz.php`.
- [x] flash cards — word → reveal definition card on `joc.php` (shares `api/quiz.php`), with "păstrează" to bookmark. Button removed from the mode bar 2026-08-01; still reachable at `joc.php?mode=flash`.
- [x] sensuri — reverse quiz (word → pick among 4 definitions) on `joc.php`, now the default mode. `api/quiz.php` returns an `options[]` array of `{word, definition}`; definitions are cleaned server-side (first segment before `|`, ≤200 chars) and low-quality entries are filtered out of the pool.

## 260519 Data Audit

- [ ] some terms still lack definitions, although they are present (the definitions) on dexonline. Ex: 
  - `mofluzită`, `libovnică`, `ischiuzară`, `consumatoare` - so _genul feminin_, feminine versions of words.
  - `cfartal` - is a different spelling of `cvartal` – dexonline has the url (https://dexonline.ro/definitie/cfartal), but the word in dexonline is `cvartal`. Same with `prijuni` --> `sprijini' (https://dexonline.ro/definitie/prijuni)
  -  `murea` (form of `a muri`), `abecedare` (plural of `abecedar`)
  - other examples: `ospătător`, `săhăstricesc`, `bașfir`, `aeresc`, `gad`, `pestitor` 
  - analyze and figure out the cases where definitions are missing – even after our initial dexonline scraping attempt.  
  - do these also mess with our statistics?
  - differently spelled variations shouldn't be listed, it poisons word exploration - or listed separately?

- [ ] why does the list contain `fost` -- this is a form of a very popular verb, `a fi`? See also other common words: `eleșteu`, `văr`, `nepot`, `coproducție`
  - **Partially resolved**: `fost` and `coproducție` removed by the `modern_ppm > 5.0` Tier A guard (2026-05-28). `eleșteu` is correct — it's a genuine archaic word (fishpond, modern_ppm=0.055). `văr` (1.4 ppm) and `nepot` (3.1 ppm) remain as borderline cases; their inflected nature would be addressed by lemmatization (backlog #6).

- [x] cuvinte rare has waay too many common words: manipulat, mediere, adițională, agravat, neurologie, organizatoare, cowboy, spitalizare – but still **not** `oțios`?!
  - **Resolved**: `validate_with_wordfreq.py` now gates `rare_in_use` on non-empty `dex_register` — words with Zipf 3.0–4.5 but no register tag fall to `common`. Rare list: 11,668 → 469. `oțios` addressed by Tier C in `make_shortlist.py` (`dex_absent_highfreq`, threshold dex_frequency ≥ 0.85); now appears in UI.

- [ ] all forms of terms listed, ex: `bleuit`, `bleuire`, `bleui` – could we just show one entry (as a bundle)? Also `blehui`, `blehuire`, `blehuit` – root word, `bleau`. IF root word not in list we should also remove references? Most words in rare --> filter --> popular. 

- [x] `cimbru` appears at `rare` / filter: `în comparații / la comparativ`. — **Fixed**: `în comparații / la comparativ` removed from register filter dropdown via `_REGISTER_USAGE_NOTES` exclusion set (2026-05-28). `cimbru` itself correctly stays in `rare_in_use`.

- [x] `uitate` / filter: `în comparații / la comparativ` - words that don't seem to have anything with comparații -- can you backtrack on how did that end-up there? — **Fixed**: `în comparații / la comparativ` is a DEX usage-context note (word can be used in comparative phrases), not an archaic register. Removed from register filter dropdown via `_REGISTER_USAGE_NOTES` (2026-05-28). 38 other usage-style tags cleaned up at the same time.

- [ ] rare / Filter: `Maramureș` lists 'biodiversitate'

- [ ] remove _diminutive_, maybe?

- [ ] how come psihoanaliză be a dex 4

- [ ] remove old spellings, `giudecător` – can we check pronountiation - if it's too close to a popular word, flag it for removal

- [ ] sort reverse 

### UI follow-ups (2026-08-01)

- [ ] 🎲 "la întâmplare" — hidden in the brand bar pending a manual-selection design (pick from the current filter set rather than pure random). `surpriseWord()` + `r` shortcut still live; unhide the button in `index.php` when the design lands.

- [x] Cmd/Ctrl+R hijacked by the `r` shortcut — global keydown handlers now ignore events carrying meta/ctrl/alt (`app.js`, `joc.php`).

- [ ] Note textarea: Enter saves, so Shift+Enter can't insert a newline (`app.js` capture-phase handler on `#note-input`). Decide whether multi-line notes matter; if so, save on Cmd/Ctrl+Enter or blur instead.


## Server-side accounts — follow-ups (2026-08-02)

- [ ] **Account claiming via Google OAuth** — the device token is the account today, so clearing cookies loses it and one person on two devices is two users. Schema is ready: `users.auth_provider` / `auth_subject` / `email` are nullable and `devices.user_id` is re-pointable, so this is ~120 lines of vanilla PHP plus a device-merge query, no migration.
- [ ] **Spaced repetition off `game_events`** — every answer is logged with word, correctness and response time. Enough to resurface words a user got wrong, and to compute a real per-word difficulty score (which is also a research signal: which "forgotten" words are genuinely unrecognisable).
- [ ] **Word difficulty stats** — aggregate `game_events` by word to show a global correct-rate. Feeds the stats page and could rank the shortlist by how forgotten a word actually is in practice, not just by corpus frequency.
- [ ] **JSON export button** — the data is already reachable via `api/sync.php` with `{"since":0}`; only a download button is missing. Closes the older "exported as json" item properly.
- [x] **Moderation for public lists** — Done 2026-08-07. `reports` table (app.db `user_version = 3`), `POST api/lists.php {action:'report', slug, reason?}`, a report link on `lista.php`, and `public/admin.php` as the review queue (unpublish / dismiss / delete) behind `OTIOS_ADMIN_TOKEN` in `config.local.php`. Covered by `tests/test_moderation.js`. See the "Moderation" section of CLAUDE.md for the two properties worth not undoing (404-not-403 for a bad token; token sealed into a cookie and redirected out of the URL).

  Two decisions recorded here because they'll look like omissions later:
  - **No auto-hide after N reports.** Identity is an anonymous device token, so N distinct reporters costs an abuser N cookie clears — a threshold would make censoring a list cheaper than publishing one. Reports queue for a human.
  - **`lista.php` does not check list ownership before showing the report button**, because that would mean calling `current_user()` on every public view and minting an identity for every passing crawler. The API rejects `own_list` and the button surfaces that.

  Still open: `liste.php` remains `noindex` — lifting it is now a product decision, not a blocker.
- [x] **Backups for `private/app.db`** — Done 2026-08-07. `php api/_backup.php` takes a `VACUUM INTO` snapshot into `<private>/backups/`, integrity-checks it, and prunes to the newest `--keep N` (default 14). CLI-only (`PHP_SAPI !== 'cli'` → 404 before any include), and it lives in `public/api/` because only the contents of `public/` reach the server. Cron line in CLAUDE.md.

  - [ ] **Still open: get a copy off the machine.** A snapshot beside the original survives a bad migration or a mistaken delete, not a lost disk. Either confirm the host's own backup covers `~/otios-private/`, or add an rsync/rclone step after the cron line.
- [ ] **Verify WAL on the production host** — `app_db()` falls back to `journal_mode=TRUNCATE` when WAL is unavailable, which some NFS-backed shared hosts require. Check which mode is actually active after deploy: `PRAGMA journal_mode`.
- [ ] **`feed_decisions` is written by nobody yet** — the table exists for the swipe game's keep/skip record, but `app.js` `feedKeep()`/`feedSkip()` still only set a bookmark. Wire it up to get a second signal (explicit rejection) distinct from "never seen".

## UI/UX findings from the "beton" skin pass (2026-08-06)

Collected while building the brutalist skin (`feat/brutalist-skin`). Everything here is
*beyond* visual styling — the skin itself is done, these are the structural things it
kept bumping into. Roughly in order of how much they cost a first-time visitor.

### Content and language

- [x] **The `verdict` enum is rendered raw to users.** Fixed 2026-08-07. `VERDICTS` and
  `TIERS` in `api/_lib.php` are now the single source for label, abbreviation, tooltip and
  (for tiers) bar-fill class, consumed by `verdict_label()` / `verdict_abbr()` /
  `tier_label()`. Replaced **three** duplicated copies of the tier map (`index.php`,
  `stats.php`, `stats_panels.php`) and the hard-coded verdict list in `index.php`'s pill
  loop. The hover box was also printing the raw enum client-side; `word_row.php` now emits
  `data-vlabel` so `app.js` reads the label instead of mapping it a second time. Verified
  no enum survives in the visible text of `index` / `stats` / `joc` / the detail panel.
  `tier_label()` returns `''` for an unmapped key rather than the key itself — a bare enum
  on the page is worse than no chip.

  <details><summary>original report</summary>

  `_partials/detail.php:26` prints
  `historical_only` / `dex_absent_highfreq` / `corpus_historical_only` verbatim into the
  verdict badge and the `confidence_tier` chip, in an otherwise fully-Romanian UI.
  `index.php:166-171` already carries the human labels for exactly these four verdicts
  (`dispărut din uz`, `în declin`, `doar istoric`, `absent`) — they're just trapped in the
  filter-pill markup. Fix: one `verdict_label()` / `tier_label()` pair in `api/_lib.php`,
  consumed by the filter pills, the detail badge, the hover box and `word_row.php`'s
  `EXT`/`DEC`/`IST`/`ABS` abbreviations, so there's a single place to translate them.
  Deliberately *not* fixed in the skin branch — it's copy, and the wording is the owner's
  call. Note the brutal skin makes it more conspicuous: the badge is now a solid colour
  block, so a raw enum sits second in the visual hierarchy after the headword itself.

  </details>

  Labels used are the ones already written in `index.php`'s filter pills (`dispărut din
  uz` / `în declin` / `doar istoric` / `absent`); the three previously-English tier labels
  became `corp. dispărut` / `corp. în declin` / `corp. doar istoric`, keeping the existing
  `corp.` / `dex.` prefix pattern. No new copy was invented — see the `stats.php` entry
  below for the strings that were left alone precisely because they would need some.

- [ ] **`stats.php` is half-English.** `register: any`, `domain: any`, `etymology: any`,
  `dicts: any`, `TIER`, `POS`, `FILTER`, `reset`, `def ✓`, `loading…`, plus
  `stats_panels.php`'s `no data` and `No words match the selected filters.` The index
  page's equivalent rail is fully Romanian. (`word_list.php`'s two English strings were
  fixed on this branch; the rest were left alone for the same copy-ownership reason.)

### Navigation and information architecture

- [ ] **There is no shared header, and no consistent way to move between the four pages.**
  `index.php` puts navigation in the *bottom* status bar; `joc.php` has its own `.joc-nav`
  in a top bar; `stats.php` has **no brand or title at all** — you land on a bare filter
  strip with no indication you're still in Oțios; `lista.php` has a lone `← Oțios` link.
  A single `_partials/header.php` carrying brand + nav + the three preference toggles
  would fix identity, navigation and the toggle duplication in one move.

- [ ] **`metodologie.html` is a separate product.** It links neither `app.css` nor
  `prefs.js`, loads a *different* font stack (Inter Tight + JetBrains Mono vs the app's
  Public Sans + IBM Plex Mono + Source Serif 4), and carries its own hand-copied theme and
  text-scale JS. It will not follow the skin toggle at all, so switching skins on the app
  and then clicking "metodologie" lands you somewhere visibly unrelated. Either fold it
  into the shared stylesheet or convert it to `metodologie.php` using the shared header.

### Filters

- [ ] **Every filter box starts checked, so the rail reads as a wall of "on".** With all
  verdicts, all five tiers and all eight parts of speech pre-selected, the selected state
  carries no information — you cannot tell at a glance what is *filtering* versus what is
  merely *available*, and the brutal skin's solid-ink checked pills make the wall literal.
  Worth considering: treat "all selected" as an implicit unfiltered state rendered
  neutrally, and only paint pills once the set is genuinely narrowed.

- [ ] **No "solo" or "none" affordance on the pill groups.** Isolating a single part of
  speech means unchecking seven boxes one at a time. A click-to-solo (like soloing a
  layer) plus a "none/all" control per group would turn the rail's most common task from
  seven clicks into one.

- [ ] **Filter state is invisible from the keyboard.** `?` documents navigation and the
  quick-tags but not the filter drawer; there's no shortcut to open/collapse the rail even
  though `toggleFilterDrawer()` already exists and the desktop rail is collapsible.

### Detail panel and reading flow

- [ ] **On mobile there is no way to preview a definition without committing.** Desktop
  gets `#hover-box` with a truncated preview; touch has no hover, so scanning 25k words
  means open → read → close → open. The arrow keys already move selection and the panel
  already follows it, so a compact "peek" row under each selected word — or making the
  bottom sheet a short peek that expands on drag — would make browsing far cheaper.

- [x] **Dead UI surface: notes and custom tags.** Partly fixed 2026-08-07 — the *notes*
  half was genuinely dead and is now gone end to end: `.fp-note textarea` and
  `#note-status` removed from `app.css`, and the `cu notă` option removed from the `marks`
  filter. Nothing could create a note and nothing displayed one, so filtering to "cu notă"
  showed words whose notes you couldn't read.

  **The tags half was not dead and was left alone**, which the original entry got wrong:
  `store.js:117` still renders `.tag custom-tag` chips for users who created custom tags
  before the input was removed, so that CSS is load-bearing. The `tag: …` options in the
  `marks` select are all live too — they come from `$QUICK_TAGS` (`ascunde`/`lol`/`meh`),
  which the quick-tag buttons still produce, plus `populateTagFilterOptions()` for legacy
  custom tags. Only `#tag-input`'s own rules are strictly orphaned, and they were kept
  since restoring the input is still an open option.

  Note server-side note storage is untouched: `sync.php` still round-trips `note`, so
  nobody's existing data was dropped — it is just no longer surfaced.

- [ ] **`ascunde` and `meh` are two buttons for one behaviour** (both hide the word and
  both exclude it from quiz rotation — see the quick-tag entry below). Known and
  deliberate, but it costs a button and an explainer paragraph; worth revisiting once
  there's data on which one people actually press.

### Accessibility

- [x] **`maximum-scale=1` blocks pinch-zoom on all four pages** — Fixed 2026-08-07.
  Removed from `index.php`, `joc.php` and `stats.php`; `lista.php` and `liste.php` never
  had it, so all five now agree. The in-app A−/A+ stepper stays as an addition to browser
  zoom, not a replacement.

- [ ] **Word rows are non-focusable `<div>`s.** `word_row.php` emits a `div` with a click
  handler — no `tabindex`, no `role`, no keyboard activation outside the app's private
  `j`/`k` handler. To a screen reader the main content is an undifferentiated pile of
  divs. `<button>` (or at minimum `role="button"` + `tabindex="0"` + Enter/Space) would
  fix keyboard access and expose the list properly.

- [ ] **Toggle buttons don't expose their state.** The view/theme/skin/scale groups use
  `role="group"` and communicate the active option purely through a CSS class; none set
  `aria-pressed`. Several icon-only buttons (`⊞ ≡ ☀ ☾ A− A+ ▤ ▩`) rely on `title` alone
  with no `aria-label`.

- [ ] **In cloud view, verdict is encoded only as colour.** The square is the sole signal;
  table view additionally shows `EXT`/`DEC`/`IST`/`ABS`. Colour-blind users get nothing in
  the default view.

### Mobile

- [ ] **The brand bar carries too much.** Brand + search + play + view + scale + skin +
  theme + filters. Scale, skin and theme are all set-once preferences that could collapse
  behind one "⚙" sheet, leaving the bar for the three things people actually use while
  browsing (search, view, filters). The 320px overflow fixed on this branch was the
  symptom; the cause is that the bar is a settings panel wearing a toolbar's clothes.

- [ ] **The filter sheet's drag handle is decorative.** `.fs-handle` looks draggable and
  sits exactly where a sheet gesture belongs, but nothing listens for touch — the sheet
  only opens and closes via the button. Either wire it up or stop drawing it.

- [ ] **No end-of-list affordance.** Infinite scroll (`hx-trigger="intersect once"`) has no
  "that's all" state and no way to jump — with 25,217 words there is no pagination, no
  alphabet index, and no scroll position indicator beyond the browser's own scrollbar.

## Skin ideas (2026-08-06)

Each is one file in `public/assets/skins/` — see the "Visual skins" section of CLAUDE.md
and copy `_template.css`. `velin.css` shows that a skin can be tokens only, ~70 lines.

- [x] **GOV.UK** — done 2026-08-06 as `govuk.css` ("Guvern"). Answered the question it was
  picked for: tokens got the palette, the radius and the fonts, but not the black masthead,
  the yellow focus state, the square marks, the dotless tags, the green button's 2px edge,
  the always-underlined links or the inset rule. Only one of those looks like a missing
  token (a dot/mark radius, separate from `--radius`); the rest are genuinely
  component-shaped. So the contract is about as complete as it can usefully be.
- [ ] **monitorul.ai** — house style; useful for a family resemblance across the projects.
- [x] **dictionary.com / thesaurus.com** — done 2026-08-06 as `tezaur.css` ("Tezaur").
  Tinted synonym pills, rounded, big serif headword, POS in italic. The pill fill replaces
  the verdict dot. Was indeed the most usable of the set.
- [ ] **Urban Dictionary** — bold sans, heavy blue links, that hard yellow accent, thumbs.
  A joke skin that's also a good stress test: it wants a much denser, more cramped layout
  than the tokens currently allow.
- [ ] **Wikipedia** — Vector 2022: Linux Libertine headings, sans body, hairline rules, the
  pale blue link colour, generous white. Very close to `paper`, so mostly a type exercise.
- [ ] **Genius.com** — dark by default, the yellow-on-near-black, annotation highlights over
  text. The annotation-highlight idea maps unusually well onto this project, where words
  already carry marks (`inv`, `bookmarked`, quick-tags).

Two of these (Urban Dictionary, Genius) will probably need component rules and not just
tokens; if several skins end up reaching for the same missing hooks, that is a signal to
add tokens for those rather than to let each skin restate them.

Two hooks both new skins reached for, worth watching for a third taker:

- [ ] **A radius token for round marks**, separate from `--radius`. The verdict dot, the
  filter dot, the legend swatch and the checkbox are all hardcoded `50%` / `2px` in
  `app.css`; `govuk` squares all four by hand. Cheap to add once a second skin wants it.
- [ ] **Brand-bar-on-a-dark-ground tokens.** Both `brutal` (ink footer) and `govuk` (black
  masthead) had to restate every control in the bar because `--surface` / `--border` /
  `--text-*` are page-ground values. A `--bar-bg` / `--on-bar` pair would collapse ~25
  lines in each. Note the trap: `.skin-select` draws its caret with two `background-image`
  gradients, so anything touching it must set `background-color`, not `background`.

## stats.php chart colours are hardcoded (2026-08-06)

The TIER chart's bars pick up the verdict tokens and reskin correctly, but the
`parte de vorbire` (indigo) and `domeniu` (green) bars are fixed hex in `stats.php` and
stay the same under every skin. Noticed while checking `govuk`, which is otherwise
strictly black/white/blue. Low priority — the page reads fine — but it is the one place a
skin visibly does not reach.

## Filter by dictionary — which one, and how recent (2026-08-06)

Counting dictionaries is already done: `dict_min` in the filter rail offers ≥3 / ≥6 /
≥10 / ≥15, backed by the `sources` column (pipe-separated) and `dict_count`. What's
missing is *which* dictionary and *how recent* — and the second is the more interesting
signal this project has not yet used.

Measured against `public/data/ui.db`: **73 distinct dictionaries**. The head is broad
(MDA2 23,235 words · DEX '09 18,097 · DOR 17,279 · DEX '98 16,740 · Ortografic 16,621 ·
DOOM 2 16,158 · DOOM 3 16,092 · DLRLC 15,934) and there is a long tail — roughly 30
dictionaries appear in fewer than 200 words each (DGL 2, Șăineanu ed. I 1, DEX '16 1).

- [ ] **Filter by specific dictionary.** A multi-select over the ~15 head dictionaries,
  with the tail collapsed or excluded. "Words in Șăineanu but not in DEX '09" is close to
  a definition of *forgotten* and the data already supports it — no new columns needed,
  just `sources LIKE` or a normalised join table. A join table is worth building at this
  point anyway: 73 values × 25k words is small, and `LIKE '%DEX '09%'` will mis-hit
  (`DEX '09` is a substring of nothing here, but `DOOM` is a prefix of `DOOM 2`/`DOOM 3`,
  and `MDA` of `MDA2`).

- [ ] **Most-recent-attestation filter — needs a year map that does not exist yet.** This
  is the valuable one: a word whose newest dictionary is Șăineanu (1929) is far more
  forgotten than one still in DOOM 3 (2021), and that is a lexicographic signal entirely
  independent of the corpus-frequency work in Phase 2. Blocker: **no year metadata
  anywhere.** `dict_sources.db` is only `(word, sources, dict_count)`. Some names embed a
  year (`DEX '09`, `DEX '98`, `DRAM 2021`, `MDN '00`, `Sinonime82`, `DEX '75`) but most do
  not (`MDA2`, `DOR`, `Ortografic`, `DLRLC`, `Scriban`, `Șăineanu, ed. VI`, `NODEX`). Needs
  a hand-curated `dictionary → publication year` table — 73 rows, one-off, and the head 15
  cover the overwhelming majority of words. Once it exists it yields a `last_attested_year`
  per word, which is sortable, filterable, and probably a better headline number than the
  DEX frequency score currently in the superscript.

- [ ] **Consider surfacing `last_attested_year` in the UI once it exists.** The detail
  panel already lists the dictionaries a word appears in; adding "ultima atestare: 1929"
  would be a stronger and more legible claim than `zipf0.0 … ratio3.12`.

## Typographic pass — remaining findings (2026-08-06)

Found while driving the pages through Playwright at 2× and measuring computed style
rather than eyeballing screenshots. The table-column drift, the tracking scale and the
colour emoji were fixed on this branch; these were measured or seen but left alone
because they are content/data decisions, not styling.

- [x] **Debug metrics are shipping to users.** Fixed 2026-08-07 by labelling rather than
  hiding: `zipf ro` / `zipf en` / `istoric` / `modern` / `raport`, each with a Romanian
  `title` explaining what it measures (ppm against which corpus, what the ratio is a ratio
  of). `.fp-stats em` margin went 1px → 4px, which was the "no space between label and
  value" half of the complaint. Kept visible rather than put behind a dev flag: this is a
  research tool and the numbers are the point — they were just unreadable.

- [ ] **Raw enum values reach the page in three more places.** Beyond the `verdict` badge
  already noted above: `corpus_historical_only` and `dex_invechit_absent` render as
  literal chips in the detail panel. The beton skin makes this louder, not quieter —
  these became solid blocks — but the fix is a label map, not CSS.

- [x] **`SINONIME — ÎN CURÂND` is a placeholder in production.** Dropped 2026-08-07, along
  with `.fp-syns-placeholder` in `app.css` and `brutal.css`. The synonyms work itself is
  still open — see the "synonyms data" entry under UI; the row comes back when there is
  data to put in it.

- [ ] **Definitions repeat verbatim.** `barabor` shows the same Ștețco 1990 citation three
  times in one panel, because sources are concatenated on `|` and near-duplicate entries
  aren't collapsed. Reads as a rendering bug even though it's a data-merge issue.

- [ ] **The joc play area is mostly void at desktop width.** The card is bottom-heavy in a
  tall empty column — roughly a third of the viewport is unused below it, with the card
  top-anchored. Needs a vertical centring decision, or a second element (progress, streak,
  the word's register) to justify the height.

- [ ] **The filter rail states the same control two different ways.** `NIVEL` is five
  full-width solid bars; `CATEGORIE` is a grid of small chips. Both are checkbox
  multi-selects. Since every box also starts checked, `NIVEL` reads as a wall of solid
  black that carries no information. Making them one control type would calm the rail
  more than any colour change.

- [ ] **`definiție` breaks the rail's label pattern.** Every other group has an uppercase
  mono tab above it; this one is a lowercase inline label beside its buttons, so the last
  row of the rail doesn't align with the twelve above it.

## Quick-tag redesign (2026-08-06)

- [x] **Collapse quick-tags to `fav / ascunde / lol / meh`, one row** — prompted by noticing `ignore`, `remove`, and `simple` all serve the same "shouldn't be in the list" goal. Analysis: today only `simple` has real backend behavior (excludes a word from quiz rotation, `quiz.php:102`); `ignore`, `remove`, `boring`, `funny` are free-form labels with no differentiated logic, even though an earlier backlog resolution (line ~179 above) assigned `ignore`/`remove` distinct *meanings* (not interesting to you / not genuinely forgotten) that were never actually enforced in code — i.e. they're functionally identical today.

  The quick-tags conflate two separate goals (per discussion): **(1) a corpus-quality signal** to fine-tune the shortlist — too common, or a bad/wrong entry — feeding back into curation; and **(2) a personal-favorites signal**, meant to be shareable, which is the project's viral hook (a "my favorite forgotten words" list). Recommendation was to split these into two small groups rather than one flat row of 5, but the user opted to keep it simple for now: one row of four — `[★] fav` (bookmark, existing) / `ascunde` (consolidates ignore+remove+simple — "uninteresting, too well known") / `lol` (renamed from `funny`) / `meh` (renamed from `boring`). Custom tag input + notes hidden for now — no clear consumer yet.

  **Open question raised while drafting the explainer copy**: draft text said words tagged `ascunde` **or `lol`** disappear from the list — but `lol` = "amuzant" is a positive vibe tag, so that reads like a typo for `meh` (whose own definition was written as "ascunde, said differently"). Resolved: `ascunde` + `meh` are the two hide/quality tags, `fav` + `lol` are the two keep/vibe tags.

  **Implemented 2026-08-06**: `ascunde`/`lol`/`meh` replace the old five quick-tags everywhere — `_lib.php` (`$QUICK_TAGS`, `$QUICK_TAG_EMOJIS`), `store.js` (`QUICK_TAG_EMOJIS`, `qtKeyToTag`), the quick-tag buttons in `detail.php`, the shortcuts legend and keyboard handler (`a`/`f`/`m`, freed up from the retired `ignore`/`boring`/`remove`/`simple` keys — `f` deliberately carried over from the old `funny` binding since `lol` is its direct descendant). `quiz.php`'s quiz-exclusion filter now excludes on `tag:ascunde` OR `tag:meh` (previously `tag:simple` only). Custom tag input + note textarea removed from the detail panel (still functional server-side/in `sync.php` for existing data, just no longer exposed in the UI). A dismissable `#qt-explainer` banner explains the four tags on first view, persisted via `localStorage['otios.qtExplainerDismissed']`; every quick-tag button also carries a `title` tooltip with the same explanation for after it's dismissed. `ascunde`+`meh` both get the stronger red "extinct" active color in `app.css` (was `remove`-only) to visually flag the hide action; `lol` keeps the default amber "tagged" color.
