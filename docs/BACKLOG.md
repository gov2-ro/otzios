# Backlog

Open bugs, debt, and enhancements. Add new entries with `- [ ]` and enough context to act on later.

---

## Bugs / Known Issues

- [ ] check why some words are still missing definitions even if found on dexonline. did scraping fail?

- [ ] `dreadnought` nu e marcat ca `marină` (Mar.) in our UI but it is in dexonline web

- [ ] **`rare_in_use` tier is polluted by modern loanwords + proper nouns** — the UI "rare" tab (`?word_tier=rare_in_use`) shows words that aren't rare: English borrowings (`screening`, `meeting`, `house`, `short`, `golden`, `dolby`, `wild`, `trend`, `scanner`, `cutter`), brand/variety names (`jonathan`), and proper nouns (`sioux`, `zulu`, `hagi`, `viking`). Two failing signals:
  1. **Low DEX `frequency` ≠ rare.** `create_curated_list.py:127-129` selects `0.01 < frequency < 1.0`; DEX `frequency` is editorial-coverage, not corpus frequency, so recent borrowings land in that band (`screening` 0.27, `meeting` 0.71, `house` 0.81) while still being everyday words.
  2. **Register gate too permissive** (`validate_with_wordfreq.py:151`): admits a word on `zipf < 4.5 AND dex_register non-empty` — *any* tag. Of 582 rows in `rare_words_wordfreq.csv` only ~124 are `învechit`; the rest are stylistic tags (`figurat` 172, `popular` 82, `familiar` 59, `livresc` 39) — exactly what colloquial loanwords carry. The gate was meant to require an *archaic* marker.

  Compounding: no loanword filter (some borrowings hit zipf 4.0–4.5, e.g. `house` 4.36, `jonathan` 4.25; `dex_etymology` is empty in the CSV so etymology filtering needs re-extraction); the proper-noun filter `create_curated_list.py:69-72` checks `word[0].isupper()` but the data is lowercased so it never fires; even `învechit` rows are noisy from homograph mismatches (`cannabis`→`învechit`, `listat`→`învechit`); 28 duplicate `word_no_accent` rows (e.g. `house` as `s.n.` and `adj.`). Loaded by `ui/app.py:122-144` (tier set at `app.py:142`). Sharpens enhancement #12. Fix options: (a) restrict the register gate to archaic markers (`învechit` + combos); (b) add a cross-lingual English-zipf loanword filter; (c) fix the proper-noun filter to run on cased DEX forms; (d) dedup by `word_no_accent`. Regenerating `rare_words_wordfreq.csv` means re-running `validate_with_wordfreq.py`. **Exploratory UI path added 2026-05-28** (see activity-history): the detail panel now shows zipf/en/dex/dict-names per word, and reversible filters (zipf range, dex range, hide-loanwords via `en_zipf`, hide-proper-nouns via DEX casing) let us triage interactively before deciding what to make permanent. Options (b) and (c) are now prototyped as UI toggles in `ui/app.py::_enrich_words` / `extract_dict_sources.py`.

- [ ] **P0 — Phase 2 candidate-set mismatch** (`process_corpus.py:56-67,187,292` vs `validate_forgotten_words.py:64-70`): `process_corpus.py` only counts tokens in `forgotten_words_curated.csv` (~1.9k words), but the validator queries `lexemes.db` with `frequency > 0.01 AND frequency < 0.60 AND LENGTH(form) > 3` (tens of thousands of lexemes). Words absent from the curated CSV silently get `total_occurrences = 0` and are classified as `confirmed_forgotten` with confidence ~0.99. The "159,543 validated, 1 false positive" headline in `docs/phase2-test-results.md` is an artefact. Fix: align the candidate source, or have `process_corpus.py` count every token.

- [ ] **Three competing MySQL→SQLite paths** — only `extract_lexemes.py` is wired into the canonical pipeline. `convert_to_sqlite.sh` mishandles multi-line MySQL directives (lines 31, 42-50); `mysql_to_sqlite.py:97` silently swallows AUTOINCREMENT errors. Archive the other two.

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

- [ ] **#3 — [S, Med] Pick one MySQL→SQLite path; archive the others** — `extract_lexemes.py` is canonical; archive `convert_to_sqlite.sh` + `mysql_to_sqlite.py`.

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

- [ ] in info window show which dictionaries this word is found in (incl wikitionary)

- [x] desktop tooltip on hover with definition — floating `#def-tip` div populated from existing `data-def` attribute on `.word-row` via `mouseover`/`mouseout` on the word-list-container. Positioned below the chip (above if near bottom of viewport). No extra network requests.

- [ ] top filter, the posibility to remove one attribute - now we can just select.

- [ ] create statistics by metadata. in the limited corpus and later in whole dexonline

- [x] hide terms marked as `remove` — hidden by default; "show removed" pill in filter bar re-shows them. **Open question**: what's the semantic difference between `ignore` and `remove`? Clarify and add tooltip/docs so users know which to use.

- [x] make .flabel bolder (negative). remove distance between .flabel and choices. Use narrow font for the filter bar — switched to mono 11px bold var(--text-2), removed min-width/excess padding.

- [x] load more words when page scrolled to bottom — replaced "load more" button with HTMX `intersect once` sentinel; auto-loads as you scroll.

- [x] if I click a word with the mouse the focus doesn't move there. Keyboard and mouse choice is not synced — delegated click listener on word-list-container now sets selectedIdx on mouse click.

- [x] longer words break in the info box, make left panel responsive / flexible width — fp-word changed from fixed 170px to auto (min 140px, max 240px).

- [ ] mark words that have attached notes or tags/flags. Filter words by tags — dot indicator done (blue ::after on .annotated); filter-by-tags in the filter bar still open.

- [x] select word by typing — type-ahead navigation: unbound printable chars accumulate in a 1.2s buffer, jumping to the first visible word whose normalized text starts with the buffer. Diacritic-insensitive (ț→t etc). Documented in shortcuts modal.

- [ ] search bar also accepts metadata - filters. Later / nice to have enhancement: fancy search, like in gmail with autocomplete and style options. Search box also accepts filtering attributes.

- [x] **Diacritic-insensitive search** — searching `otios` should find `oțios`; `stramosesc` should find `strămoșesc`. Normalize both the query and the indexed word by stripping diacritics before matching (ț→t, ș→s, ă→a, â→a, î→i). Implement in the SQL WHERE clause using a pre-computed `word_normalized` column in the `words` table (populated at build time), or a SQLite custom function. Both PHP and Flask search endpoints need updating.

- [ ] later show extended definition. everything in dexonline but compact

- [ ] exploratory interface. to the point of screensaver. or like tiktok / Tinder feed, but limit per day

- [ ] **Verdict palette saturation review** — four full-saturation colors (red/brown/blue/purple) in the word grid compete equally for attention; consider one dominant verdict color + three muted, or shift to a single-hue density encoding. Out of scope for the 2026-05-18 fine-tuning pass.

- [x] **Bookmark + învechit underline conflict** — switched `.inv .word-text` from `text-decoration: underline dotted` to `border-bottom: 1.5px dotted`. The two indicators now coexist: amber `text-decoration` for bookmark + red dotted `border-bottom` for inv.

- [ ] **Mobile / narrow-viewport breakpoints** — `ui/templates/base.html` has no media queries; the 3-row filter bar and word grid are desktop-only. Add breakpoints for tablet (collapse filter rows into a single overflow menu) and phone (single column word grid, slide-up detail panel from bottom).

- [ ] **Filter bar tooltips** — add `title` attributes (or custom CSS tooltips) to all controls in the filter bar: the uitate/rare toggle, verdict pills, tier pills, POS pills, sort select, marks select, def toggle, and taxonomy selects. Especially useful for the uitate/rare switch and the verdict color-coding which are non-obvious to new users.

- [ ] **URL-encoded filter state** — encode all active filter values (word_tier, verdict, tier, sort, pos, register, domain, etymology, has_def, marks, q) into the URL query string on every filter change, so that the current view is bookmarkable and shareable. Use `history.replaceState` (no page reload) to update the URL as HTMX triggers fire; parse and restore from `window.location.search` on page load to pre-select the right controls. Both PHP and Flask apps should support this.

- [ ] **Extract inline CSS to `ui/static/app.css`** — `ui/templates/base.html` carries ~870 lines of inline styles. Move to a static stylesheet so it can be cached + edited without touching templates. Set up Flask's static directory if not already wired.

- [ ] do we actually need the word search bar? Does word search add any overhead? Word exploration/discovery should be done by categories, this is not a dictionary. Maybe turn it into attribute search bar. 

- [ ] final list of words, mark some, then pass through llm to filter some more.

- [ ] Meta tags, Open Graph fields, description og image etc

- [ ] web ui: follow schema.org for appropriate entities - add to claude.md maybe?

- [ ] SEO Audit. Including `/llms.txt` 

## Misc

- [x] create methodology, including activity log, look at activity log and commit history

- [x] tune parameters until it includes `oțios` – maybe use a flag to hide these other, second tier words (new words beyond  current list/limits). What we would also like to surface would be words that are rarely used, but worth attention. The sweet spot might not be totally forgotten words, but let's see which are the rare words but still in use. For the UI we could use a global switch flag. Which corpus to browse, forgotten or rarely used terms?
  - **Resolved (pipeline side)**: `validate_with_wordfreq.py` now emits a `tier` column (`forgotten` / `rare_in_use` / `common`) alongside the existing `is_forgotten` bool. Default thresholds: `--threshold 3.0` (lower, forgotten floor) / `--upper-threshold 4.5` (upper, common cutoff). Rare-in-use words (3.0 ≤ zipf < 4.5) are written to a separate `data/processed/rare_words_wordfreq.csv` so they don't contaminate the forgotten list. Note: `oțios` itself has zero corpus signal (zipf=0.000) so it lands in `forgotten`, not `rare_in_use`.
  - **Still open (UI side)**: add a global switch in the web UI to toggle between the forgotten-words list and the rare-in-use list.

- [ ] maybe we should also look in the dictionaries themselves. Are we including really old dictionaries? We could make a page with per dictionary `diff`? Does dexonline dump cover all dictionaries listed here: https://clre.solirom.ro/  https://clre.solirom.ro/content/ro/list-of-lexicographical-works.html https://clre.solirom.ro/content/ro/statistics.html 

- [ ] handle in browser curration - choices saved in browser memory and can be exported as json

- [ ] publish favorites, custom lists even to a web server. make it a collaborative experience. Eventually publish these currated lists and showcase popular words on the main website.

- [ ] metadata navigator - add wordfreq and scarcity - the result of this project. 

- [ ] try a super dorpdown navigator, where it can reach all metadata options, witih contextual keyboard shortcuts. or just search by visible terms. but how can we select more or exclude, to make it crazy good? With streer count in brackets?

- [x] **New DEX dump intake** — downloaded `dex-database.sql` (1.65 GB); old dump renamed `dex-database-1.sql` (1.27 GB). Schema is nearly identical (one new index on `Lexeme.pronunciations`). Data growth: Lexeme +3,774, Entry +3,469, ObjectTag +38,074, Meaning +13,367, TreeEntry +5,404; DefinitionSimple unchanged. Four new tables: `Subtitle` (13 M rows — individual Romanian words from 966 YouTube clips, confirmed Digi24 news content, good modern-Romanian corpus candidate), `VideoClip` (966 rows, YouTube IDs), `OCR_stats`, `student`. Actions taken: re-ran `extract_lexemes.py` and `extract_taxonomy.py` against new dump to refresh `lexemes.db`. `validate_diachronic.py` not re-run (waiting for taxonomy join fix above). Subtitle corpus: see #XX backlog entry.

- [x] **definitions.db has severe word→definition misalignment** — `abac` (abacus) is paired with a bacteremia definition; `vânzător` gets a paranasal osteoma definition; `acătarii` has no entry at all despite dexonline showing one. The DB has 83,609 rows so the content is present, but the word↔text association is broken. Likely cause: the extraction script joins on a row offset or integer key that doesn't stably map across tables (e.g. `Lexeme.id` vs `Meaning.entryId` vs `Entry.id` — a multi-hop join gone wrong). Fix: re-examine the extraction query against the DEX MySQL schema; spot-check 10–20 words against dexonline.ro to confirm the join path. Related: the existing `drăngălău` note below.
  - **Resolved**: root cause was a misunderstood schema, not a join error. `DefinitionSimple.lexicon` is the headword (despite the misleading column name), not a dictionary identifier. The old code joined `Lexeme → EntryLexeme → EntryDefinition → DefinitionSimple` and picked the rank-1 definition for each Entry, but Entry records group multiple related-but-distinct words, so the rank-1 definition is often about a *different* word. Fixed by reading `DefinitionSimple.lexicon` directly as the headword key. See commit 8113dbf and `docs/DEFINITIONS_ANALYSIS.md`. Gaps still in the dump are filled by `scrape_definitions.py` (synthesis tab from dexonline.ro).

- [x] **Garbled definitions from DEX dump extraction** — Root cause: `_parse_values` parsed `\n` as the literal letter `n`, leaving dump indentation spaces in the output. Fixed: added full escape table (`\n`, `\r`, `\t`) + `re.sub(r'\s+', ' ')` normalization in `_clean`. Re-ran `extract_definitions.py` + `--merge-only`. Garbled count: 3,152 → 0.

- [ ] **domain taxonomy contains compound nodes with semicolons** — some DEX `dex_domain` values are compound strings from the source taxonomy: `'mineralogie; minerit'`, `'cinema; cinematografie'`, `'fonetică; fonologie'`, `'farmacie; farmacologie'`. These are stored and filtered as single pipe-delimited tokens (which is correct for exact-match filtering), but the UI dropdown shows the full compound string. Two open questions: (1) should the filter split on `;` to allow filtering by `mineralogie` alone? (2) are these compound nodes semantically intentional in DEX, or are they artifacts of how the tag hierarchy was imported? Check the `Tag` table: if `'mineralogie; minerit'` is a single row with that literal name, it's intentional; if it's two rows joined somewhere, the extraction is concatenating them incorrectly.

- [ ] **domain filter matches on any sub-sense, not primary meaning** — `dex_domain` is set at the word level by aggregating all per-meaning domain tags from DEX. This means a word like *simpatie* (meaning: emotional affinity) appears under medicină because DEX tags one secondary sense as medicină ("legătură între organe simetrice" = sympathetic nerve link); *scaon* appears because DEX tags the compound *scaun rulant* (wheelchair) as medicină; *pipăi* appears for its medical sense of "to palpate". The tags are correct in the source data — this is how DEX models domains. The UI filter is therefore "has at least one medicina meaning" rather than "is primarily a medical word", which can be confusing. Options: (1) show per-word domain count in the word card so the user can judge; (2) add a "strict" domain mode that only matches words whose *only* domain tag is the selected one; (3) document this in a filter tooltip. Related: compound-semicolon entry above.

- [x] definitions have some bugs, `drăngălău` has the `constituent structural al oțelurilor călite și revenite` definition but on the web it doesn't have it https://dexonline.ro/definitie/dr%C3%A2ng%C4%83l%C4%83u/definitii — **resolved** by the same fix as the misalignment item above; `drăngălău` now reads from `scrape_definitions.py` because the DEX dump has no `DefinitionSimple.lexicon='drăngălău'` row.

- [ ] see [260515 notes - missing oțios.md](260515 notes - missing oțios.md)

- [ ] **[Upstream] Report DefinitionSimple truncation to dexonline developers** — both the old dump (`dex-database-1.sql`, 1.2 GB, Oct 2025) and the new dump (`dex-database.sql`, 1.5 GB, May 2026) contain only **61,041 rows** in `DefinitionSimple`, while `EntryDefinition` references **1,379,043** definition IDs — a 94.8% gap of dangling references. This means ~12.8k of our ~17.4k shortlist words have no extractable definition from the dump and must be scraped from dexonline.ro instead. The issue is not a bug in our extraction: `DefinitionSimple.lexicon` correctly identifies headwords; the referenced definition records simply are not present. Worth filing a bug or opening a discussion on the dexonline GitHub/forum so future dump consumers don't hit the same wall. Include: table row counts, the orphaned-reference count, and the impact (scraping as workaround).

- [ ] track synonyms. count synonyms

- [ ] also filter by: masculin, feminin, neutru.

- [ ] Meta: suggest versions, note in both activity log, chronology and readme.

- [x] I also see on dexoline the tag 'rar' but in our interface filters I only see 'învechit' see [săhăstricesc](https://dexonline.ro/definitie/săhăstricesc) — Fixed: `rar` (id=6), `regional` (id=17), `ieșit din uz` (id=239) were root-level DEX tags missed by the `parentId IN (1,41,42)` filter. Extended taxonomy loader to capture them and their children (Banat, Moldova, etc.). `rar`: 2,463 words; `regional`: 3,202; `ieșit din uz`: 95.

- [ ] **Subtitle corpus from new DEX dump** — `Subtitle` table in `dex-database.sql` has 13 M pre-tokenised Romanian word tokens from 966 YouTube clips (Digi24 news). Quick sample: 89k tokens → 11,240 unique types; top words are normal function words. Estimated 1.4% shortlist word coverage in sample (scales to ~20% at full 13M tokens). Too small to replace CulturaX as primary corpus, but valuable as a modern spoken-register spot-check. To use: write `process_subtitles.py` that extracts `SELECT word, COUNT(*) FROM Subtitle GROUP BY word` via `extract_lexemes.parse_mysql_insert` (or a dedicated streaming extractor) and loads into `corpus_frequencies.db` under `corpus_name='subtitle_ro'`. VideoClip table links clipId → YouTube videoId (11-char IDs) if metadata is needed.

- [ ] create presentation video. With PLaywright and a scenario, subtitles and generated voiceover. Create youtube account / channel.

## Post launch

- [ ] traffic analytics
- [ ] SEO webmasters registrations
- [ ] write scientific paper(s). 1. method, 2. conclusions – co-publish with academic?
- [ ] write articles, scena9 or such

### Extend

- quizzes
- flash cards

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