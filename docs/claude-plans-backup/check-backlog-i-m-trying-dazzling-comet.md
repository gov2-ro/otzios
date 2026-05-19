# Plan: Rare-in-Use Word Tier

## Context

The user wants to surface words like *oțios* that are technically still in use but extremely rare — not completely forgotten, but vanishingly uncommon. This should be a **separate list** so it doesn't contaminate the core "forgotten words" output. The idea is already noted in the backlog (BACKLOG.md line 208): *"The sweet spot might not be totally forgotten words, but let's see which are the rare words but still in use."*

One clarifying finding: *oțios* itself has **zero corpus signal** (zipf = 0.000, absent from both Wikisource and CulturaX), so it actually belongs in the "forgotten" tier, not the "rare-in-use" tier. The rare-in-use tier captures words that *do* appear — just rarely (low but non-zero Zipf).

## Recommendation

Extend `validate_with_wordfreq.py` with a three-tier classification and a separate output CSV for the rare-in-use tier.

### Classification tiers

| Tier | Zipf range | Meaning |
|------|-----------|---------|
| `forgotten` | < 3.0 | Current behavior — virtually absent from modern usage |
| `rare_in_use` | 3.0 – 4.5 | Still appears, but very infrequently (new tier) |
| `common` | ≥ 4.5 | Everyday usage — filtered out |

Zipf 4.5 is roughly 3 occurrences per million words; 3.0 is ~1 per million. The 3.0–4.5 band catches words that surface occasionally in text but would strike most speakers as archaic or elevated register.

## Files to change

- **`validate_with_wordfreq.py`** (primary change)
  - Add `--upper-threshold` CLI arg (default `4.5`)
  - Change `is_forgotten` boolean → `tier` string column (`forgotten` / `rare_in_use` / `common`)
  - When `--keep-all` is used, all rows get a tier label (no filtering)
  - When filtering (default mode): write two output files:
    - `data/processed/forgotten_words_validated_wordfreq.csv` — existing path, `tier=forgotten` rows only (backward-compatible)
    - `data/processed/rare_words_wordfreq.csv` — new, `tier=rare_in_use` rows only
  - Print summary counts for all three tiers at end

- **`docs/BACKLOG.md`**
  - Mark the line-208 item as addressed; add a note about the `--upper-threshold` default

## What stays the same

- Default invocation (`python validate_with_wordfreq.py`) produces identical forgotten-words output as before — no behavioral regression
- The `--threshold` arg (lower boundary, default 3.0) is unchanged
- Downstream scripts that read `forgotten_words_validated_wordfreq.csv` are unaffected (column rename from `is_forgotten` bool → `tier` string needs a one-time check)

## Column rename impact

`is_forgotten` (bool) → `tier` (string) is a breaking change for any script that reads the CSV. Quick grep needed before implementing:
- `search_wild.py` — reads validated CSV? Check.
- Any analysis/display scripts.

If downstream readers exist, either keep `is_forgotten` as an alias column or update them in the same PR.

## Verification

```bash
source ~/g2-dev/monitorulpreturilor/venv/bin/activate
python validate_with_wordfreq.py --keep-all --limit 200   # smoke test, check tier column
python validate_with_wordfreq.py                          # full run, check two output files
# Confirm forgotten_words_validated_wordfreq.csv has tier=forgotten rows only
# Confirm rare_words_wordfreq.csv exists and has tier=rare_in_use rows
# Spot-check a known rare word (e.g. "îmbrobodi") falls in rare_in_use tier
```
