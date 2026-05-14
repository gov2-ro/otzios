# Plan: Refreshing the diachronic validation output

## Context

The user noticed that `forgotten_words_validated.csv` (the legacy output) hasn't been regenerated since Oct 2025. After pulling the latest data from the VPS, the picture is clear: the **legacy path is superseded** — the diachronic pipeline has already run and produced current outputs. The task is to confirm whether a re-run of `validate_diachronic.py` is needed or if the existing output is sufficient.

---

## Current artifact state (post-VPS sync)

| File | Size | Date | Rows | Notes |
|---|---|---|---|---|
| `forgotten_words_validated.csv` | 9.5 MB | Oct 27 2025 | 159,543 | Legacy path — stale, **not worth regenerating** |
| `forgotten_words_diachronic.csv` | 75 KB | May 13 2026 | 1,077 | Diachronic — **fresh today** |
| `diachronic_shortlist_for_web.csv` | 3.4 KB | May 13 2026 | 48 | Shortlist for web validation — fresh |
| `diachronic_shortlist_web_validated.csv` | 7.0 KB | May 13 2026 | 48 | Phase 3 output — fresh |
| `corpus_frequencies.db` | 2.8 MB | May 13 2026 | 21,579 | Both corpora complete |
| `forgotten_words_curated.csv` | 84 KB | May 13 2026 | 1,884 | Phase 1 candidates — fresh |
| `forgotten_words_validated_wordfreq.csv` | 124 KB | Apr 28 2026 | 1,868 | Phase 2a wordfreq — recent |
| `lexemes.db` | 26 MB | Apr 28 2026 | 315,247 | DEX source — present |

### corpus_frequencies.db contents

```
wikisource_ro  → 12,921 docs · 14.3M tokens · 6,876 unique words  (completed Apr 28)
culturax_ro    → 40.3M docs  · 17B tokens   · 14,703 unique words (completed May 12)
```

No `wikipedia_ro` or `oscar_ro` data — the legacy pipeline's corpus has been replaced.

### Pipeline completion status

| Phase | Script | Output | Status |
|---|---|---|---|
| 1 — Dictionary | `create_curated_list.py` | `forgotten_words_curated.csv` | ✅ Done |
| 2a — wordfreq | `validate_with_wordfreq.py` | `validated_wordfreq.csv` | ✅ Done (Apr 28) |
| 2b — Diachronic | `validate_diachronic.py` | `forgotten_words_diachronic.csv` | ✅ Done (today) |
| 3 — Web | `search_wild.py` | `diachronic_shortlist_web_validated.csv` | ✅ Done (48 words, today) |

**The full pipeline is current.** `forgotten_words_validated.csv` is the legacy output and is not part of the active pipeline.

> **Why 1,077 diachronic rows vs 1,884 curated?** `validate_diachronic.py` appears to filter out words absent from both corpora. The 807 gap is words that don't appear in either `wikisource_ro` or `culturax_ro` at all.

---

## Two validation paths — which one matters

### Path A — Legacy (`validate_forgotten_words.py` → `forgotten_words_validated.csv`)

- **Status:** blocked. The script hardcodes corpus names `wikipedia_ro` / `oscar_ro`; neither exists in the db. Running it now would return zero corpus counts for everything.
- **To unblock:** re-run `process_corpus.py --full --wikipedia-only` (legacy path) to re-populate `wikipedia_ro` data in the db. This takes hours and has the known **P0 bug** (counts only ~1.9k curated words, then validates against full 315k-word lexeme table → most words show zero corpus occurrences → bogus "confirmed_forgotten" verdicts).
- **Output columns:** `word, dex_frequency, corpus_occurrences, frequency_per_million, validation_status, confidence_score, wikipedia_count, oscar_count`

### Path B — Diachronic (`validate_diachronic.py` → `forgotten_words_diachronic.csv`)

- **Status:** already done. `forgotten_words_diachronic.csv` is fresh (75 KB, today). Both upstream corpora are complete.
- **Output columns:** `word, dex_frequency, hist_ppm, modern_ppm, log_ratio, verdict`
- **Verdict buckets:** `extinct`, `declining`, `stable`, `emerging`, `historical_only`, `modern_only`, `absent`
- **No P0 bug.** Operates on the curated list, normalizes against actual token counts per corpus.

---

## Chosen approach: refresh the diachronic output

`forgotten_words_diachronic.csv` is already current (generated today from a complete `corpus_frequencies.db`), but re-running `validate_diachronic.py` is harmless and ensures the file reflects the latest db state.

### Step

```bash
source ~/devbox/envs/240826/bin/activate
python validate_diachronic.py
```

Takes seconds. Overwrites `data/processed/forgotten_words_diachronic.csv`.

### Files involved

| File | Role |
|---|---|
| `validate_diachronic.py` | Script to run |
| `data/processed/corpus_frequencies.db` | Input — wikisource_ro + culturax_ro (both complete) |
| `data/processed/lexemes.db` | Input — DEX dictionary |
| `data/processed/forgotten_words_curated.csv` | Input — 1,884 candidates |
| `data/processed/forgotten_words_diachronic.csv` | Output — will be overwritten |

### Verification

After running, check:
1. `forgotten_words_diachronic.csv` mtime is now and row count is ~1,884
2. `verdict` column contains expected categories (`extinct`, `declining`, `stable`, etc.)
3. Run `python status.py` — Phase 2b artifact should show updated timestamp
