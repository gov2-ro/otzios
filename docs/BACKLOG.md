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

- [ ] **#0 — [S, High] Full Wikisource + CulturaX corpus runs** — `process_wikisource.py` is written and tested (500 docs, 7s). Run full Wikisource on VPS (`nohup python process_wikisource.py > wikisource.log 2>&1 &`), then build an equivalent `process_culturax.py` for CulturaX RO. Once both are in `corpus_frequencies.db`, build the diachronic comparison (`log(freq_historical / freq_modern)`) in a new `validate_diachronic.py`. See `docs/corpus-options.md`.

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
