# Backlog

Open bugs, debt, and enhancements. Add new entries with `- [ ]` and enough context to act on later.

---

## Bugs / Known Issues

- [ ] check why some words are still missing definitions even if found on dexonline. did scraping fail?

- [ ] `dreadnought` nu e marcat ca `marină` (Mar.) in our UI but it is in dexonline web

- [ ] **P0 — Phase 2 candidate-set mismatch** (`process_corpus.py:56-67,187,292` vs `validate_forgotten_words.py:64-70`): `process_corpus.py` only counts tokens in `forgotten_words_curated.csv` (~1.9k words), but the validator queries `lexemes.db` with `frequency > 0.01 AND frequency < 0.60 AND LENGTH(form) > 3` (tens of thousands of lexemes). Words absent from the curated CSV silently get `total_occurrences = 0` and are classified as `confirmed_forgotten` with confidence ~0.99. The "159,543 validated, 1 false positive" headline in `docs/phase2-test-results.md` is an artefact. Fix: align the candidate source, or have `process_corpus.py` count every token.

- [ ] **Three competing MySQL→SQLite paths** — only `extract_lexemes.py` is wired into the canonical pipeline. `convert_to_sqlite.sh` mishandles multi-line MySQL directives (lines 31, 42-50); `mysql_to_sqlite.py:97` silently swallows AUTOINCREMENT errors. Archive the other two.

- [ ] **`explore_dex.py` is dead code** — imports `sqlite3` but never uses it; `__main__` points `db_path` at a `.sql` file that `sqlite3.connect()` cannot open. Content is narrative; move to `docs/` or delete.

- [ ] **Frequency-bin definitions disagree across scripts** — `analyze_forgotten_words.py` uses 0.25/0.50/0.70; `create_curated_list.py:131-138` uses 0.30/0.50 with a 0.60 ceiling; `validate_forgotten_words.py:67` filters 0.01–0.60. No shared `constants.py`. Changing one requires hunting down the others.

- [ ] **Regex probable typo in `create_curated_list.py:28-32`** — `r"^[a-z]+-[a-z]+'"` has a trailing apostrophe. Verify intent; likely a bug.

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

- [ ] **#4 — [XS, Low] Delete `explore_dex.py`** — move any useful content to `docs/`.

- [ ] **#5 — [S, Med] Centralize frequency bins in `constants.py`** — eliminates the three-way disagreement.

- [ ] **#6 — [M, High] Add lemmatization with `simplemma`** — slots into `process_corpus.py:tokenize_romanian`; `bucle` would then match `buclele`.

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

- [ ] **#17 — [XS, Med] Flag words with no definition body** — Some DEX entries exist as a headword with POS and etymology but no actual meaning text (dexonline renders these as "[Fără definiție.]", e.g. *nombrilist*). In the `Meaning`/`DefinitionSimple` tables these have a null or empty `internalRep`. These words pass our Lexeme filter and appear in the candidate set, but their "forgotten" verdict rests purely on frequency with no semantic content to validate against. Two action items:

  1. Count them: `SELECT COUNT(DISTINCT l.form) FROM Lexeme l JOIN EntryLexeme el ... JOIN Meaning m ... WHERE m.internalRep IS NULL OR m.internalRep = ''` — gives the scale of the problem.
  2. Add a `has_definition` boolean column to `forgotten_words_diachronic.csv` (and the curated list) so they can be filtered out of final results or treated as a lower-confidence subcategory.

  Note: these words may still be worth keeping — a word documented only as a borrowing with no translation is itself a sign of marginal integration into Romanian.

- [ ] **#19 — [XS, Low] Annotation overlay overflow for heavily-annotated words** — Words with 4+ annotations (e.g. all quick tags + note + bookmark = `🙈💤😄❌📝⭐`) produce a ~48px emoji string in `.ann-overlay` that bleeds left over the word text. `letter-spacing: -1px` compresses it slightly but there is no max-width or clip. Either cap visible annotations at 3 and add a `+N` indicator, or accept the overlap as a cosmetic edge case.

- [ ] **#20 — [S, Low] Annotation overlay goes stale after in-panel mutations** — When the user toggles a bookmark or adds/removes a tag via the detail panel, the word chip in the grid is not re-rendered (HTMX only swaps the detail panel / tag row). The `ann-overlay` emoji stays stale until the next search trigger. Fix: add an HTMX OOB swap from `/bookmark/<word>` and `/tag/<word>/*` routes that re-renders the affected `.word-row`.

- [ ] **#18 — [L, Med] Extract per-document metadata from corpora for temporal and domain signals** — Currently both corpus scripts discard document-level metadata and only keep aggregate word counts. Two signals worth extracting:

  - **Temporal distribution (CulturaX)**: parquet files carry a `timestamp` field per document. Storing a year histogram per word (e.g. JSON column `year_dist` in `corpus_word_frequency`) would let us answer "when did this word last appear in web text" — a direct measure of *when* usage dropped off, richer than a single `modern_ppm` value. A word with 90% of hits before 2015 and nothing recent is differently forgotten than one that's uniformly rare.
  - **Source domain (CulturaX)**: classify document URLs by type (news, forum, academic, government, blog). A word that survives only in Wikipedia or legal text but never in news or social content is a different kind of relic.
  - **Historical period (Wikisource)**: documents have author/title/century metadata. Words clustering in 19th-century prose vs. spanning multiple centuries give a richer diachronic signal than raw `hist_ppm`.

  **Practical approach** — full reprocessing is expensive. Better: after identifying `extinct`/`declining` words via the current pipeline, run a targeted second-pass scan over CulturaX parquet files for just those ~few thousand words, collecting date and URL metadata. Wikisource period attribution is cheap (12k docs) and could be a side-table join without reprocessing.

  Schema sketch: add `year_dist` (JSON), `domain_dist` (JSON) to `corpus_word_frequency`, or a separate `word_temporal` table keyed on `(word, corpus_name, year)`.


- [ ] **#19 — [S, Med] Research UI: browse/filter by more metadata fields** — the filter bar currently exposes verdict, tier, and sort order. Useful additions:

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

- [ ] **#22 — [S, Med] Hybrid word-marking UX: reserved one-key tags + tag autocomplete** — research UI today supports bookmark (`b`) + free-form tags via the detail-panel input. Add (a) a reserved set of single-keystroke "verdict" tags so the common cases are zero-friction, and (b) `<datalist>` autocomplete on the free-form tag input from the union of tags used so far.

  - Reserved keys: `i` = ignore, `B` = boring (Shift+B avoids collision with `b` bookmark), `f` = funny, `x` = remove. Each toggles its tag on the current word via a new `POST /tag/<word>/toggle/<tag>` endpoint that returns the refreshed `tags_row` partial (idempotent: re-pressing the key removes the tag).
  - Reserved tags render as a dedicated row of toggle buttons at the top of `#tags-row` (visible state + clickable for mouse users) and are filtered out of the regular tag-pill list to avoid duplication. Treated as ordinary tags in storage — same `bookmarks.tags` column.
  - `t` focuses the free-form tag input. Input is bound to `<datalist id="tag-suggestions">` populated server-side from `/tags/suggest` (distinct tags across all bookmarks). Stale until reload acceptable for v1.
  - Update shortcuts modal + status bar with the new bindings.

- [ ] **#21 — [M, Med] Factor in dictionary coverage (how many dictionaries list a term)** — DEX Online aggregates entries from multiple source dictionaries (DEX '98, DEX '09, MDA, NODEX, DLRLC, Scriban, Șăineanu, etc.). A word appearing in only one source — especially an older or specialised one — is a different kind of rare than one that appears in every modern dictionary. Add a per-word `dict_count` (and optionally `dict_sources` list) column derived from the `Definition.sourceId` → `Source` join in `lexemes.db`, then surface it in the curated/diachronic CSVs and as a filter/sort in the research UI (#19). Likely useful as an additional axis in the "forgotten" verdict: low corpus frequency + low dictionary coverage = stronger signal than low corpus frequency alone.

- [ ] also have a look at [wiktionary](https://ro.wiktionary.org/)



## UI

- [x] make space for columns a bit wider — grid minmax raised to 120px.

- [x] bring superscript count badge closer to word — margin-left 3px → 1px.

- [x] make definition text larger — bumped to 15px; removed inline 11.5px override in detail.html.

- [x] keyboard nav, after focusing on searchbar and filtering words it's hard to get focus back on the term list — Esc from search now restores selectedIdx via selectRow(noClick=true).

- [x] optimize for mobile

- [x] mobile, when scrolling, hide definition drawer. after focus moves on the list

- [ ] in info window show which dictionaries this word is found in (incl wikitionary)

- [ ] desktop tooltip on hover with definition

- [ ] create statistics by metadata. in the limited corpus and later in whole dexonline

- [x] hide terms marked as `remove` — hidden by default; "show removed" pill in filter bar re-shows them. **Open question**: what's the semantic difference between `ignore` and `remove`? Clarify and add tooltip/docs so users know which to use.

- [x] make .flabel bolder (negative). remove distance between .flabel and choices. Use narrow font for the filter bar — switched to mono 11px bold var(--text-2), removed min-width/excess padding.

- [x] load more words when page scrolled to bottom — replaced "load more" button with HTMX `intersect once` sentinel; auto-loads as you scroll.

- [x] if I click a word with the mouse the focus doesn't move there. Keyboard and mouse choice is not synced — delegated click listener on word-list-container now sets selectedIdx on mouse click.

- [x] longer words break in the info box, make left panel responsive / flexible width — fp-word changed from fixed 170px to auto (min 140px, max 240px).

- [ ] mark words that have attached notes or tags/flags. Filter words by tags — dot indicator done (blue ::after on .annotated); filter-by-tags in the filter bar still open.

- [ ] select word by typing

- [ ] search bar also accepts metadata - filters. Later / nice to have enhancement: fancy search, like in gmail with autocomplete and style options. Search box also accepts filtering attributes.

- [ ] later show extended definition. everything in dexonline but compact

- [ ] exploratory interface. to the point of screensaver. or like tiktok / Tinder feed, but limit per day

- [ ] **Verdict palette saturation review** — four full-saturation colors (red/brown/blue/purple) in the word grid compete equally for attention; consider one dominant verdict color + three muted, or shift to a single-hue density encoding. Out of scope for the 2026-05-18 fine-tuning pass.

- [ ] **Bookmark + învechit underline conflict** — both are rendered as `text-decoration: underline` on `.word-text`. When a word is both bookmarked and `învechit`, the bookmark's solid amber wins and the dotted red `învechit` indicator is invisible. Today's compromise: bookmark precedence (set in `ui/templates/base.html`, comment "wins over inv when both true"). Fix later by stacking a second indicator — e.g., a thin red dotted `box-shadow` below the amber underline, or move bookmarks to a non-underline visual (left-edge marker, subtle bg tint).

- [ ] **Mobile / narrow-viewport breakpoints** — `ui/templates/base.html` has no media queries; the 3-row filter bar and word grid are desktop-only. Add breakpoints for tablet (collapse filter rows into a single overflow menu) and phone (single column word grid, slide-up detail panel from bottom).

- [ ] **Extract inline CSS to `ui/static/app.css`** — `ui/templates/base.html` carries ~870 lines of inline styles. Move to a static stylesheet so it can be cached + edited without touching templates. Set up Flask's static directory if not already wired.

- [ ] Meta tags, Open Graph fields, description og image etc

- [ ] web ui: follow schema.org for appropriate entities - add to claude.md maybe?

- [ ] SEO Audit. INcluding `/llms.txt` 

## Misc

- [x] create methodology, including activity log, look at activity log and commit history

- [ ] tune parameters until it includes `oțios` – maybe use a flag to hide these other, second tier words (new words beyond  current list/limits). What we would also like to surface would be words that are rarely used, but worth attention. The sweet spot might not be totally forgotten words, but let's see which are the rare words but still in use. For the UI we could use a global switch flag. Which corpus to browse, forgotten or rarely used terms?

- [ ] handle in browser curration - choices saved in browser memory and can be exported as json

- [ ] publish favorites, custom lists even to a web server. make it a collaborative experience. Eventually publish these currated lists and showcase popular words on the main website.

- [ ] metadata navigator - add wordfreq and scarcity - the result of this project. 

- [ ] try a super dorpdown navigator, where it can reach all metadata options, witih contextual keyboard shortcuts. or just search by visible terms. but how can we select more or exclude, to make it crazy good? With streer count in brackets?

- [x] **New DEX dump intake** — downloaded `dex-database.sql` (1.65 GB); old dump renamed `dex-database-1.sql` (1.27 GB). Schema is nearly identical (one new index on `Lexeme.pronunciations`). Data growth: Lexeme +3,774, Entry +3,469, ObjectTag +38,074, Meaning +13,367, TreeEntry +5,404; DefinitionSimple unchanged. Four new tables: `Subtitle` (13 M rows — individual Romanian words from 966 YouTube clips, confirmed Digi24 news content, good modern-Romanian corpus candidate), `VideoClip` (966 rows, YouTube IDs), `OCR_stats`, `student`. Actions taken: re-ran `extract_lexemes.py` and `extract_taxonomy.py` against new dump to refresh `lexemes.db`. `validate_diachronic.py` not re-run (waiting for taxonomy join fix above). Subtitle corpus: see #XX backlog entry.

- [x] **definitions.db has severe word→definition misalignment** — `abac` (abacus) is paired with a bacteremia definition; `vânzător` gets a paranasal osteoma definition; `acătarii` has no entry at all despite dexonline showing one. The DB has 83,609 rows so the content is present, but the word↔text association is broken. Likely cause: the extraction script joins on a row offset or integer key that doesn't stably map across tables (e.g. `Lexeme.id` vs `Meaning.entryId` vs `Entry.id` — a multi-hop join gone wrong). Fix: re-examine the extraction query against the DEX MySQL schema; spot-check 10–20 words against dexonline.ro to confirm the join path. Related: the existing `drăngălău` note below.
  - **Resolved**: root cause was a misunderstood schema, not a join error. `DefinitionSimple.lexicon` is the headword (despite the misleading column name), not a dictionary identifier. The old code joined `Lexeme → EntryLexeme → EntryDefinition → DefinitionSimple` and picked the rank-1 definition for each Entry, but Entry records group multiple related-but-distinct words, so the rank-1 definition is often about a *different* word. Fixed by reading `DefinitionSimple.lexicon` directly as the headword key. See commit 8113dbf and `docs/DEFINITIONS_ANALYSIS.md`. Gaps still in the dump are filled by `scrape_definitions.py` (synthesis tab from dexonline.ro).

- [ ] **Garbled definitions from DEX dump extraction** — ~46k definitions loaded from `DefinitionSimple` via `extract_definitions.py` contain malformed text with spurious whitespace and embedded markup artifacts, e.g. `"Acțiunea den       a ( se ) abaten         n       și rezultatul ei."` The dump's `internalRep`-style markup (word references, verb forms) wasn't stripped cleanly. Scraped definitions (from `scrape_definitions.py`) are clean. Fix options: (1) re-run `extract_definitions.py` with better markup stripping; (2) prefer scraped definition over dump definition when both exist for the same word. Check scale: `SELECT COUNT(*) FROM definitions WHERE definition LIKE '%  %'`.

- [ ] **domain taxonomy contains compound nodes with semicolons** — some DEX `dex_domain` values are compound strings from the source taxonomy: `'mineralogie; minerit'`, `'cinema; cinematografie'`, `'fonetică; fonologie'`, `'farmacie; farmacologie'`. These are stored and filtered as single pipe-delimited tokens (which is correct for exact-match filtering), but the UI dropdown shows the full compound string. Two open questions: (1) should the filter split on `;` to allow filtering by `mineralogie` alone? (2) are these compound nodes semantically intentional in DEX, or are they artifacts of how the tag hierarchy was imported? Check the `Tag` table: if `'mineralogie; minerit'` is a single row with that literal name, it's intentional; if it's two rows joined somewhere, the extraction is concatenating them incorrectly.

- [ ] **domain filter matches on any sub-sense, not primary meaning** — `dex_domain` is set at the word level by aggregating all per-meaning domain tags from DEX. This means a word like *simpatie* (meaning: emotional affinity) appears under medicină because DEX tags one secondary sense as medicină ("legătură între organe simetrice" = sympathetic nerve link); *scaon* appears because DEX tags the compound *scaun rulant* (wheelchair) as medicină; *pipăi* appears for its medical sense of "to palpate". The tags are correct in the source data — this is how DEX models domains. The UI filter is therefore "has at least one medicina meaning" rather than "is primarily a medical word", which can be confusing. Options: (1) show per-word domain count in the word card so the user can judge; (2) add a "strict" domain mode that only matches words whose *only* domain tag is the selected one; (3) document this in a filter tooltip. Related: compound-semicolon entry above.

- [x] definitions have some bugs, `drăngălău` has the `constituent structural al oțelurilor călite și revenite` definition but on the web it doesn't have it https://dexonline.ro/definitie/dr%C3%A2ng%C4%83l%C4%83u/definitii — **resolved** by the same fix as the misalignment item above; `drăngălău` now reads from `scrape_definitions.py` because the DEX dump has no `DefinitionSimple.lexicon='drăngălău'` row.

- [ ] see [260515 notes - missing oțios.md](260515 notes - missing oțios.md)

- [ ] **[Upstream] Report DefinitionSimple truncation to dexonline developers** — both the old dump (`dex-database-1.sql`, 1.2 GB, Oct 2025) and the new dump (`dex-database.sql`, 1.5 GB, May 2026) contain only **61,041 rows** in `DefinitionSimple`, while `EntryDefinition` references **1,379,043** definition IDs — a 94.8% gap of dangling references. This means ~12.8k of our ~17.4k shortlist words have no extractable definition from the dump and must be scraped from dexonline.ro instead. The issue is not a bug in our extraction: `DefinitionSimple.lexicon` correctly identifies headwords; the referenced definition records simply are not present. Worth filing a bug or opening a discussion on the dexonline GitHub/forum so future dump consumers don't hit the same wall. Include: table row counts, the orphaned-reference count, and the impact (scraping as workaround).

- [ ] track synonyms. count synonyms

- [ ] also filter by: masculin, feminin, neutru.

- [ ] I also see on dexoline the tag 'rar' but in our interface filters I only see 'învechit' see [săhăstricesc](https://dexonline.ro/definitie/săhăstricesc)

- [ ] **Subtitle corpus from new DEX dump** — `Subtitle` table in `dex-database.sql` has 13 M pre-tokenised Romanian word tokens from 966 YouTube clips (Digi24 news). Quick sample: 89k tokens → 11,240 unique types; top words are normal function words. Estimated 1.4% shortlist word coverage in sample (scales to ~20% at full 13M tokens). Too small to replace CulturaX as primary corpus, but valuable as a modern spoken-register spot-check. To use: write `process_subtitles.py` that extracts `SELECT word, COUNT(*) FROM Subtitle GROUP BY word` via `extract_lexemes.parse_mysql_insert` (or a dedicated streaming extractor) and loads into `corpus_frequencies.db` under `corpus_name='subtitle_ro'`. VideoClip table links clipId → YouTube videoId (11-char IDs) if metadata is needed.

- [ ] create presentation video. With PLaywright and a scenario, subtitles and generated voiceover. Create youtube account / channel.

## Post launch

- [ ] traffic analytics
- [ ] SEO webmasters registrations

## 260519 Data Audit

- [ ] some terms still lack definitions, although they are present (the definitions) on dexonline. Ex: 
  - `mofluzită`, `libovnică`, `ischiuzară` - so _genul feminin_, feminine versions of words.
  - `cfartal` - is a different spelling of `cvartal` – dexonline has the url (https://dexonline.ro/definitie/cfartal), but the word in dexonline is `cvartal`. Same with `prijuni` --> `sprijini' (https://dexonline.ro/definitie/prijuni)
  -  `murea` (form of `a muri`), `abecedare` (plural of `abecedar`)
  - other examples: `ospătător`, `săhăstricesc`, `bașfir`, `aeresc`, `gad`, `pestitor` 
  - analyze and figure out the cases where definitions are missing – even after our initial dexonline scraping attempt.  
  - do these also mess with our statistics?
  - differently spelled variations shouldn't be listed, it poisons word exploration - or listed separately?

- [ ] why does the list contain `fost` -- this is a form of a very popular verb, `a fi` ?