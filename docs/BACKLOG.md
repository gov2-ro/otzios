# Backlog

Open bugs, debt, and enhancements. Add new entries with `- [ ]` and enough context to act on later.

---

## Bugs / Known Issues

- [ ] **P0 — Phase 2 candidate-set mismatch** (`process_corpus.py:56-67,187,292` vs `validate_forgotten_words.py:64-70`): `process_corpus.py` only counts tokens in `forgotten_words_curated.csv` (~1.9k words), but the validator queries `lexemes.db` with `frequency > 0.01 AND frequency < 0.60 AND LENGTH(form) > 3` (tens of thousands of lexemes). Words absent from the curated CSV silently get `total_occurrences = 0` and are classified as `confirmed_forgotten` with confidence ~0.99. The "159,543 validated, 1 false positive" headline in `docs/phase2-test-results.md` is an artefact. Fix: align the candidate source, or have `process_corpus.py` count every token.

- [ ] **Three competing MySQL→SQLite paths** — only `extract_lexemes.py` is wired into the canonical pipeline. `convert_to_sqlite.sh` mishandles multi-line MySQL directives (lines 31, 42-50); `mysql_to_sqlite.py:97` silently swallows AUTOINCREMENT errors. Archive the other two.

- [ ] **`explore_dex.py` is dead code** — imports `sqlite3` but never uses it; `__main__` points `db_path` at a `.sql` file that `sqlite3.connect()` cannot open. Content is narrative; move to `docs/` or delete.

- [ ] **Frequency-bin definitions disagree across scripts** — `analyze_forgotten_words.py` uses 0.25/0.50/0.70; `create_curated_list.py:131-138` uses 0.30/0.50 with a 0.60 ceiling; `validate_forgotten_words.py:67` filters 0.01–0.60. No shared `constants.py`. Changing one requires hunting down the others.

- [ ] **Regex probable typo in `create_curated_list.py:28-32`** — `r"^[a-z]+-[a-z]+'"` has a trailing apostrophe. Verify intent; likely a bug.

- [ ] **OSCAR auth fails silently** (`process_corpus.py:255-261`) — when `--full` is requested but the dataset is unreachable, the run silently skips OSCAR. Should fail loudly or warn clearly.

- [ ] **`download_wikipedia_ro.py` blocks on interactive `y/N`** — not scriptable without a `--yes` flag.

- [ ] **No CLI path overrides** — all scripts hardcode `data/dictionaries/` and `data/processed/`; `process_corpus.py` has `argparse` for mode only, not paths.

- [ ] **Confidence-score weights are unjustified** (`validate_forgotten_words.py:215`) — `dex×0.3 + corpus×0.5 + doc×0.2` was chosen ad hoc. Treat output as ordinal, not absolute.

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

- [ ] **#16 — [M, High] Enrich output CSVs with DEX taxonomy tags** — The DEX SQL dump has a `Tag` table (~460 entries, hierarchical) linked to entries via `ObjectTag`. Three tag families are valuable:

  - **Register** (`parentId=42`): `învechit`, popular, familiar, dialectal, livresc, poetic, argou, etc. A word already tagged `învechit` in DEX is direct editorial evidence of archaism — a gold-standard signal orthogonal to corpus frequency. Cross-referencing our `extinct` verdict with `dex_register=învechit` is the cleanest validation available.
  - **Domain** (`parentId=41`): muzică, medicină, drept, sport, informatică, etc. (50+ specialisms). Lets users exclude technical jargon from results — a domain-specific term being rare in a general corpus is expected, not "forgotten".
  - **Etymology** (`parentId=1`): grecism (tag 414), latinism (380), anglicism (320), turcism (300), slavonism (442), germanism (391), franțuzism (293), maghiarism (443), rusism (410), etc. Enables questions like: are Turkisms more likely to go extinct than Latinisms?

  POS is partially in `Lexeme.description` and `modelType`, but Tag has finer-grained forms (`substantiv feminin invariabil`, `verb intranzitiv`) via `isPos=1` tags.

  **Implementation sketch:**
  1. Extend `extract_lexemes.py` to parse and load `Tag`, `ObjectTag`, `EntryLexeme` into `lexemes.db`.
  2. Determine `objectType` integer values from sample rows in `ObjectTag` (likely 1=Entry, 2=Meaning).
  3. Join: `Lexeme → EntryLexeme → Entry → ObjectTag → Tag`, group by parentId family.
  4. Add columns to `forgotten_words_diachronic.csv`: `dex_register` (pipe-delimited), `dex_domain`, `dex_etymology`, `dex_pos_tag`.
  5. Words with multiple senses may have conflicting tags — take the union; flag conflicts.

- [ ] **#17 — [XS, Med] Flag words with no definition body** — Some DEX entries exist as a headword with POS and etymology but no actual meaning text (dexonline renders these as "[Fără definiție.]", e.g. *nombrilist*). In the `Meaning`/`DefinitionSimple` tables these have a null or empty `internalRep`. These words pass our Lexeme filter and appear in the candidate set, but their "forgotten" verdict rests purely on frequency with no semantic content to validate against. Two action items:

  1. Count them: `SELECT COUNT(DISTINCT l.form) FROM Lexeme l JOIN EntryLexeme el ... JOIN Meaning m ... WHERE m.internalRep IS NULL OR m.internalRep = ''` — gives the scale of the problem.
  2. Add a `has_definition` boolean column to `forgotten_words_diachronic.csv` (and the curated list) so they can be filtered out of final results or treated as a lower-confidence subcategory.

  Note: these words may still be worth keeping — a word documented only as a borrowing with no translation is itself a sign of marginal integration into Romanian.

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

## Misc

- [ ] see [260515 notes - missing oțios.md](260515 notes - missing oțios.md)