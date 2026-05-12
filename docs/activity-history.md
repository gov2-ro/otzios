# Activity History

Chronological log of meaningful work. Add entries under `## YYYY-MM-DD — Short Title`.

---

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
