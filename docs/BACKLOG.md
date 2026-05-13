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
