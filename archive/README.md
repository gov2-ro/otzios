# archive/

Obsolete scripts kept for reference only. **Not part of the canonical pipeline
— do not run or import these.** See `docs/BACKLOG.md` (#3).

## Dump conversion (superseded by `extract_lexemes.py`)

The canonical MySQL→SQLite path is `extract_lexemes.py` (streams the DEX dump
straight into `lexemes.db`). The two scripts here were earlier, abandoned
attempts at the same job:

- **`mysql_to_sqlite.py`** — generic dump converter; `mysql_to_sqlite.py:97`
  (now relative to this file) silently swallows AUTOINCREMENT errors, so failures
  pass unnoticed. Superseded by the targeted `extract_lexemes.py`.
- **`convert_to_sqlite.sh`** — shell converter that mishandles multi-line MySQL
  directives, producing a corrupt schema.

## Retired in the 2026-08-07 data-quality rescore

Each of these had no consumer left. They were archived rather than deleted because
their docstrings record decisions worth being able to look up.

- **`analyze_forgotten_words.py`** — wrote `forgotten_words_v1.csv` and
  `statistics.txt`, which nothing read. Its rarity bins (0.25/0.50) also contradicted
  the canonical ones in `constants.py` (0.30/0.50/0.60), so keeping it live invited
  someone to tune the wrong constant.
- **`validate_forgotten_words.py`**, **`process_corpus.py`**,
  **`download_wikipedia_ro.py`** — the legacy Wikipedia/OSCAR Phase-2 branch, carrying
  the P0 candidate-set bug (`process_corpus.py` counted only the ~1.9k curated words
  while `validate_forgotten_words.py` queried tens of thousands, so almost everything
  read as "confirmed forgotten"). Superseded by `process_wikisource.py` /
  `process_culturax.py` → `validate_diachronic.py`.
- **`search_wild.py`** — web validation via DDG/Google CSE. It reached 47 of 25,305
  words (0.19%), and `build_ui_db.py` was reading a different, stale file than the one
  it wrote. With paradigm-level corpus counts now doing the "is this word still used"
  job properly, it adds nothing. The 23-domain dictionary-site ignore list in it is the
  part worth keeping if web checking is ever revived.
- **`ui/`** (Flask app, templates, and `test_app.py`) — a second implementation of the
  filter and sort layer that had drifted well behind the deployed PHP UI (no skins,
  lists, moderation or packed share URLs). Every threshold change had to be made twice.
  Its tests also read the real `data/processed/rare_words_wordfreq.csv` through a
  hardcoded fallback (`app.py:133`) instead of their fixtures, so they failed against
  any real data. `public/` is the only UI.
