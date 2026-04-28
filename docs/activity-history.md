# Activity History

Chronological log of meaningful work. Add entries under `## YYYY-MM-DD — Short Title`.

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
