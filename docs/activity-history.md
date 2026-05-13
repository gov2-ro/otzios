# Activity History

Chronological log of meaningful work. Add entries under `## YYYY-MM-DD — Short Title`.

---

## 2026-05-13 — Fixed load_dex_words() in corpus scripts; corpus re-run needed

`process_culturax.py` and `process_wikisource.py` both had `AND description != ''` in `load_dex_words()` — the same bug just fixed in `create_curated_list.py`. Words with empty DEX description but a valid `modelType` (N, F, A, VT…) were silently excluded from corpus tracking. The corrected filter (`description != '' OR modelType IN (…)`) expands the tracking set from ~15k to ~137k words, covering words like `jurnalism`, `ziar`, `lactoză`, `incompetență`. Both scripts updated identically. BACKLOG #15 added: corpus DB is stale and both runs must be redone on VPS.

## 2026-05-13 — Raised Phase 1 frequency cutoff; oțios now in pipeline

`create_curated_list.py`: raised DEX frequency ceiling from `< 0.60` to `< 1.0` (excludes only the 14,021 core-vocabulary entries at frequency = 1.0). Simultaneously fixed a second exclusion: words with empty `description` but a word-class `modelType` (e.g. `A` = adjective) are now accepted via `has_meaningful_description` fallback. Added `standard` rarity category (0.60–1.0).

Trigger: `oțios` (the project's namesake) was excluded despite being a confirmed forgotten word — DEX frequency 0.85 put it above the old ceiling, and its empty description field would have blocked it even after raising the cutoff.

Outcome: curated list grew from 1,884 → 140,308 candidates. After `validate_diachronic.py` re-run: 245 extinct / 1,430 declining / 1,026 historical_only (up from 6/2/40). `oțios` itself lands as `absent` — no occurrences in either Wikisource or CulturaX, confirming it is truly unused in written Romanian.

BACKLOG #14 added: consider a targeted web-validation pass on `absent` words with high DEX freq.

## 2026-05-12 — DDG baseline sweep of diachronic shortlist (48 words)

Ran `search_wild.py --provider ddg --limit 48 --delay 4` against `diachronic_shortlist_for_web.csv` (6 extinct + 2 declining + 40 historical_only). Baseline for the eventual Google A/B.

Distribution: `truly_extinct` 1, `marginal` 14, `alive_rare` 33. The high-end bucket is dominated by cross-language false matches (Sheffield uni Romanian course pages, German/English Wikipedia for non-Romanian homographs, foreign-language blogs), so `alive_rare` from DDG is unreliable signal on its own.

Useful findings under DDG's `< 10 hits` floor:
- `fărămat` — 0 hits, no top URL. Archaic of *fărâmat*; web-extinct.
- `lăut` — 4 hits. Only one of the 6 diachronic `extinct` verdicts that DDG also reads as rare.
- 14 of the 40 `historical_only` words land at `< 10 DDG hits` — a useful pre-filter for the "really dead" subset.

Cross-tab: of the 6 diachronic `extinct`, only `lăut` got DDG `marginal`; the other 5 (`ajutoriu`, `viți`, `jălit`, `jăluit`, `puțân`) all got fuzzy 10–18-hit matches that aren't real usage. Reinforces that DDG is triage-only on archaic Romanian; Google is the real validator.

Output retained at `data/processed/diachronic_shortlist_web_validated.csv` for direct row-level diff against a future `--provider google` run on the same input.

## 2026-05-12 — search_wild.py: pluggable provider interface (DDG + Google)

Refactored `search_wild.py` to support multiple search backends via a `SearchProvider` abstract base class. Two providers ship: `GoogleCSEProvider` (existing logic, preserves env-var requirement) and `DuckDuckGoProvider` (new, via the `ddgs` library — no API key). Provider selected via `--provider {ddg,google}`; default `ddg` for prototyping.

Output schema changed: column `google_total_results` → `total_results`, plus new `provider` column to disambiguate mixed-provider CSVs. `web_score` buckets are provider-specific (Google: 0/<10/<100/100+; DDG: 0/<3/<10/10+ capped at 30).

Notes on DDG: very noisy on rare archaic Romanian words — its auto backend rotates engines, `-site:` operators aren't always honored, and "exact-match" quotes fall back to fuzzy/related forms. Resolved partially with (a) post-filtering hits on the ignored-domain hostname list (since `-site:` is unreliable), (b) dropping `-site:` from the DDG query entirely (too long, kept hitting truncation), and (c) treating `DDGSException("No results found.")` as a valid 0-result outcome rather than an error. Expanded `DEFAULT_IGNORE_SITES` (added dex.ro, reverso, en-academic, glosbe, educalingo, archeus, etc.) for both providers.

Live smoke-test on 8 diachronic-shortlist words: `lăut` 4 results / `pribegit` 6 / `jălit` 9 — bottom of the range matches our extinct/declining verdicts. But top results are often false positives (Sheffield uni Romanian course, German Wikipedia for "Víti", Indonesian blog for "lăut"). Treat DDG as triage; plan to re-run with Google for ground truth.

`requirements.txt`: added `ddgs`; kept `google-api-python-client`.

## 2026-05-12 — Re-run validate_diachronic.py against clean CulturaX

Now that CulturaX has completed cleanly (40.3M docs / 17.0B tokens / 14,703 unique words, no cycling), regenerated the diachronic comparison. The previous `forgotten_words_diachronic.csv` (2026-04-29) was meaningless — produced when CulturaX data was either zero or ~6,600× inflated by the `ds.skip()` cycling bug, so every word fell into `historical_only` or `absent`. Preserved as `forgotten_words_diachronic.stale-2026-04-29.csv` for comparison.

Steps: regenerated `forgotten_words_curated.csv` from `lexemes.db` (1,884 rows → 1,077 unique after normalize() dedup), then ran `validate_diachronic.py` default mode.

Corpus sizes used: wikisource_ro 14,297,033 tokens, culturax_ro 16,969,999,321 tokens (1,187× larger).

Verdict breakdown (1,077 candidates):
- `extinct` 6, `declining` 2, `historical_only` 40, `stable` 7, `modern_only` 98, `emerging` 7, `absent` 917.

Top historically-skewed words (`hist_ppm > 0`, ordered by log_ratio): `ajutoriu`, `viți`, `pribegit`, `jălit`, `jăluit`, `puțân`, `lăut`, `substanțialist`, `jăcuit`, `bonsoar`, `estras`, `acufundat`, `alâm`, `jecuit`, `pohtit`, `adăogit`, `schopenhauerian`, `bergsonian`, `daleu`, `histeric` — all plausible 19th-century / pre-reform Romanian forms (`ajutoriu`/`pribegit`/`pohtit`/`puțân` are pre-modern spellings; `bergsonian`/`schopenhauerian` are dated philosophical adjectives).

Phase 2b diachronic output now reflects real signal; ready to feed into Phase 3 (`search_wild.py`) when desired.

## 2026-05-12 — Add status.py: at-a-glance pipeline summary

Added `status.py`, a read-only summary command. Prints five sections: header, corpus runs (from `processing_stats`, with checkpoint freshness for in-progress runs), pipeline artifacts (Phase 1/2/3 outputs with size, mtime, CSV row counts), process liveness (reuses `health_check.PROCESSES` and `_pid_alive()`), and recent audit (tail of `run_history.jsonl`, latest `quality_*.json` tally, last 7d of `alerts.log`). No flags, no writes, no alerts — just `python status.py`.

First run confirmed both corpora completed: culturax_ro 40.3M docs / 17.0B tokens / 14,703 unique words (duration 44m 27s, 421 tokens/doc); wikisource_ro 12,921 docs / 14.3M tokens / 6,876 words. All four quality checks pass for both. Stale `culturax.pid` correctly flagged as `DEAD` (loop exited cleanly when the run completed).

## 2026-05-12 — Add monitoring layer: health_check.py, audit.py, data/logs/

Added lightweight infrastructure for watching long-running corpus scripts:

- **`health_check.py`** — cron script (every 30 min) that checks loop PID liveness, checkpoint staleness (> 2 h without update = stalled), recent log errors, and corpus completion. Fires one alert per new problem via configurable backend (`OTZIOS_ALERT_URL` for webhooks, `OTZIOS_ALERT_EMAIL` for system mail). Alert state persisted in `data/logs/health_status.json` to prevent cron spam.
- **`audit.py`** — daily cron script that snapshots run history to `data/logs/run_history.jsonl` and runs quality checks: cycling detection (`MAX(document_count) ≤ docs_processed`), token-ratio sanity, word coverage floor, both-corpora-complete status. Writes dated `data/logs/quality_YYYY-MM-DD.json`; alerts on any `fail`.
- **`data/logs/`** — new canonical log/PID directory inside the repo (gitignored except `.gitkeep`). Updated CLAUDE.md, readme.md, and documentation to point here instead of `~/g2-dev/logs/`. Current culturax run PID copied to new location and log symlinked for immediate monitoring.
- **Cron installed** — both entries added to crontab.

Venv migration (to in-project `.venv`) deferred until the current culturax run completes. Steps documented in CLAUDE.md `## Monitoring` section.

## 2026-05-12 — process_culturax.py: fix cycling bug, rewrite to per-parquet checkpointing

Discovered that the existing `ds.skip(N)` approach had been cycling through the dataset repeatedly. Root cause: `SkipExamplesIterable._iter_arrow()` in `datasets` v4.8.5 contains a bug — when `skip(N)` is called with N greater than the dataset size, it sets `skipped = N` on the first batch (yielding an empty slice), then falls through a missing `continue`/`elif` to yield all remaining batches in full. Since the Romanian CulturaX shard is ~40M docs (64 parquet files × 630K rows) but the checkpoint had grown past 40M through successive restarts, every subsequent restart re-processed files 2–64 from near the beginning while advancing the checkpoint by ~67K each time. After ~6,600 bad restarts the checkpoint read 484M (12× the true dataset size) and occurrence counts were inflated ~6,600× non-uniformly.

Remediation:
- Wiped all `corpus_name = 'culturax_ro'` rows from `corpus_frequencies.db` and deleted the corrupted checkpoint.
- Rewrote `process_culturax.py` to bypass HuggingFace streaming entirely: lists the 64 parquet shards via `HfFileSystem`, reads each with `pyarrow.ParquetFile`, and checkpoints at the parquet-file + row-group level. On each restart the script opens the in-progress file, reads only the footer metadata to locate the right row group, and resumes with zero skip overhead. SIGTERM/SIGHUP flush the current batch cleanly before exit.
- Fixed the restart loop to `break` when the Python script exits 0 (all files done) rather than always restarting.

Fresh run started 2026-05-12; expected ~40M docs, ~8–16 hours total depending on SIGKILL frequency.

## 2026-05-05 — process_culturax.py: robustness fixes + auto-restart loop

Debugged repeated silent kills of `process_culturax.py` during resume runs. Root cause: SIGKILL (likely memory pressure from co-running `fetch_prices.py`) killing the process every ~50-75k docs. Fixes applied:
- Replaced manual skip loop with `ds.skip()` (IterableDataset native method) to avoid loading 190k+ docs into Python during resume
- Added `gc.collect()` after skip to free memory before processing begins
- Added SIGTERM/SIGHUP signal handler that logs exit point
- Added try/except with traceback around the main loop
- Switched to `python -u` (unbuffered) so log output isn't lost on hard kill
- Fixed progress print to flush immediately

Since SIGKILL can't be caught, launched a bash auto-restart loop (`nohup bash -c 'while true; do python -u process_culturax.py --resume; sleep 15; done'`) so the script resumes automatically from checkpoint after each kill. Checkpoint at 345k docs / ~100M tokens as of session end.

Also updated CLAUDE.md: added `## Logs` section documenting `~/g2-dev/logs/` and correct shared venv path (`~/g2-dev/monitorulpreturilor/venv`).

## 2026-04-29 — validate_diachronic.py: diachronic comparison script

Built `validate_diachronic.py`, the final piece of Enhancement #0. Joins `wikisource_ro` (historical literary) and `culturax_ro` (modern web) frequencies from `corpus_frequencies.db`. Normalizes both by corpus size (occurrences per million tokens), computes `log2((hist_ppm + 0.1) / (modern_ppm + 0.1))`, and assigns verdicts: `extinct`, `declining`, `stable`, `emerging`, `historical_only`, `modern_only`, `absent`. Output: `forgotten_words_diachronic.csv`, ranked by log ratio descending.

Tested against the existing 14.3M-token Wikisource run (CulturaX not yet run, so all modern_ppm = 0 — results are placeholder until CulturaX full run completes). Next step: run `process_culturax.py` on VPS.

---

## 2026-04-28 — Wikisource corpus pipeline; wordfreq limitations discovered

- Fixed `validate_with_wordfreq.py`: now uses `word_no_accent` for wordfreq lookups (DEX `form` field encodes stress with apostrophes, e.g. `bucl'e`); moved raw `word` column to end of output CSV. Added Data notes to README explaining the apostrophe convention.
- Investigated DEX `frequency` field: it measures lexicographic importance (how central a word is in dictionary definitions), not corpus frequency. `oțios` scores 0.85 in DEX but 0.000 in wordfreq — meaning DEX filters it out in Phase 1 despite being absent from all corpora.
- Found wordfreq's Romanian coverage to be binary: every tested word returns either 0.000 or ≥ 3.0, with nothing in between. Wordfreq is not a useful frequency signal for Romanian beyond identifying the top ~1,500 most common words.
- Pivoted Phase 2 strategy to diachronic corpus approach per `docs/corpus-options.md`: Wikisource RO as historical literary baseline ("then"), CulturaX RO as modern web baseline ("now"). Goal: compute log(freq_historical / freq_modern) to identify genuinely forgotten words.
- Wrote `process_wikisource.py`: fixes P0 bug from `process_corpus.py` (loads ~15k DEX forms from `lexemes.db` rather than 1.9k curated words); streams Wikisource RO from HuggingFace; checkpointing/resume; outputs to `corpus_frequencies.db` with `corpus_name = 'wikisource_ro'`. Test run: 500 docs, 1.4M tokens in 7 seconds.

---

## 2026-04-28 — Merge review-and-document branch into main

Merged the `review-and-document` feature branch back to `main`. Branch contained the methodological documentation, wordfreq tooling, and CLAUDE.md work from 2026-04-27/28.

---

## 2026-04-28 — Added initial project specs doc and updated readme

Added `docs/oțios-init-specs.docx.md` (converted from the original Google Docs spec). Updated `readme.md` with current status and links.

---

## 2026-04-28 — wordfreq/simplemma path: validate_with_wordfreq.py + requirements.txt

Added `validate_with_wordfreq.py` as a proof-of-concept for the pragmatic alternative to Phase 2's custom corpus pipeline. The script uses `wordfreq` frequency lookups + `simplemma` lemmatization to score candidates directly, bypassing the Wikipedia/OSCAR streaming setup entirely. Also added `requirements.txt` covering both the legacy pipeline (`datasets`) and the new path (`wordfreq`, `simplemma`).

Decision: flag `wordfreq` path as the recommended primary approach in documentation; demote full corpus streaming to a reranker role for rare candidates that fall below Zipf-3.

---

## 2026-04-27 — Methodological critique: conceptual roadmap, corpus catalog, methodology-v2

Added three new docs reflecting a deeper review of what the project is actually measuring:
- `docs/conceptual-roadmap.md` — reframes what "forgotten" should mean; critiques frequency-only approach; outlines Phase 3+ thinking
- `docs/corpus-options.md` — catalog of open Romanian corpora beyond Wikipedia (OSCAR, CoRoLa, CC-100, etc.) with access notes
- `docs/methodology-v2.md` — proposed revised methodology using wordfreq as primary signal
- `docs/wordfreq-recipe.md` — concrete implementation recipe for the wordfreq path

Also updated `docs/corpus-options.md` with additional corpus details, and moved `PHASE2_COMPLETE.md` from root to `docs/`.

---

## 2026-04-27 — CLAUDE.md: initial project review and enhancement backlog

Added `CLAUDE.md` with a full codebase review: pipeline documentation, data contracts, 10 known issues, and a ranked enhancement backlog. Updated `.gitignore`. This was the first formal AI-oriented documentation pass after the October 2025 implementation work.

---

## 2025-10-27 — Phase 2 complete: corpus validation pipeline

Built and tested the full Phase 2 pipeline in a single session:
- `download_wikipedia_ro.py` — pre-fetches Romanian Wikipedia via HuggingFace `datasets`
- `process_corpus.py` — streams Wikipedia (and optionally OSCAR-2301), counts candidate word occurrences, writes `corpus_frequencies.db`
- `validate_forgotten_words.py` — cross-references corpus frequencies with DEX candidates, produces `forgotten_words_validated.csv`, `false_positives.csv`, and `validation_report.txt`

Test run: 1,001 Wikipedia articles, 2,351 articles/sec, 1,007,108 tokens in 0.4s.

Note: the "159,543 confirmed forgotten" result from this test is misleading — the candidate-set mismatch bug (see `docs/BACKLOG.md`) means most words were never looked up in the corpus. Results need to be re-run after fixing that bug.

Also added `docs/phase2-corpus-validation-plan.md`, `docs/phase2-test-results.md`, and updated `docs/results-summary.md` and `readme.md`.

---

## 2025-10-27 — Phase 1 complete: DEX pipeline, analysis, curation

Built all Phase 1 scripts:
- `create_sample_db.py` — subsamples the 1.2 GB MySQL dump to ~285 MB
- `extract_lexemes.py` — regex-extracts the `Lexeme` table directly from the dump → `lexemes.csv` + `lexemes.db`
- `analyze_forgotten_words.py` — frequency analysis → `forgotten_words_v1.csv` + `statistics.txt`
- `create_curated_list.py` — heuristic filter → `forgotten_words_curated.csv` (~1,884 candidates)
- `mysql_to_sqlite.py`, `convert_to_sqlite.sh` — alternate conversion paths (not used in canonical pipeline)
- `explore_dex.py` — narrative exploration script (not a working pipeline step)

Also added initial `docs/` (database analysis, results summary, scripts guide, spec) and `readme.md`.

---

## 2025-10-26 — Project initialized

Repository created. Empty initial commit.
