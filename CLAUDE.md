# CLAUDE.md

Guidance for Claude (and humans) working in this repository.

## Project overview

Oțios is a computational-linguistics tool that identifies "forgotten" Romanian
words: terms present in the official DEX Online dictionary that have fallen out
of modern usage. It runs in two phases:

- **Phase 1 — dictionary analysis.** Take the 1.2 GB DEX Online MySQL dump,
  produce a SQLite copy of the `Lexeme` table, filter by the DEX `frequency`
  field, and curate a candidate list (~1.9k words at the time of writing).
- **Phase 2 — corpus validation.** Stream Romanian Wikipedia (and optionally
  OSCAR-2301) via HuggingFace `datasets`, count occurrences of the candidates,
  and produce a validated/scored CSV.

The codebase is intentionally small: 9 standalone Python scripts at the repo
root, one shell helper, no package structure, and a single third-party
dependency (`datasets`).

For the methodological critique that sits *above* this codebase — what the
project is actually measuring, why Wikipedia alone isn't enough, what
"forgotten" should mean — read `docs/conceptual-roadmap.md` first, then
`docs/corpus-options.md` for the catalogue of larger, open Romanian corpora
that should replace the current Wikipedia-only setup.

## Repo layout

```
otzios/
├── readme.md                       # User-facing overview and roadmap
├── CLAUDE.md                       # This file
├── docs/                           # Specs, plans, results, conceptual notes
│   ├── conceptual-roadmap.md       # Methodological reframings (read first)
│   ├── corpus-options.md           # Corpus catalog beyond Wikipedia
│   ├── romanian-forgotten-words-spec.md
│   ├── scripts-guide.md
│   ├── results-summary.md
│   ├── dev-database-summary.md
│   ├── dex-database-analysis.md
│   ├── phase2-corpus-validation-plan.md
│   ├── phase2-test-results.md
│   ├── PHASE2_COMPLETE.md          # Historical: Phase 2 completion notes
│   └── oțios.docx.md
│
├── # Phase 1: dictionary pipeline
├── create_sample_db.py             # Subsample the 1.2 GB MySQL dump to ~285 MB
├── convert_to_sqlite.sh            # sed/grep MySQL→SQLite conversion (see "Known issues")
├── mysql_to_sqlite.py              # Python MySQL→SQLite converter (see "Known issues")
├── extract_lexemes.py              # Regex-extract the Lexeme table → CSV + SQLite
├── explore_dex.py                  # Narrative reference, NOT a working script (see "Known issues")
├── analyze_forgotten_words.py      # Frequency analysis → forgotten_words_v1.csv
├── create_curated_list.py          # Heuristic filter → forgotten_words_curated.csv
│
└── # Phase 2: corpus validation
    ├── download_wikipedia_ro.py    # Pre-fetch Wikipedia RO into HF cache
    ├── process_corpus.py           # Stream corpora, count candidate occurrences
    └── validate_forgotten_words.py # Score candidates, emit validated CSV + report
```

`data/` is **gitignored** and must be hydrated locally — see "Pipeline" below.
Generated CSVs (`forgotten_words_*.csv`), SQLite files (`*.db`), and
intermediate dumps live there.

## Environment setup

There is currently **no `requirements.txt` or `pyproject.toml`** (see
"Enhancement backlog" #2). The actual dependency surface is:

- Standard library only for Phase 1 (`re`, `sqlite3`, `csv`, `argparse`,
  `unicodedata`, `collections`, `datetime`, `time`, `sys`).
- `datasets` (HuggingFace) for Phase 2.

Quick start:

```bash
python -m venv .venv && source .venv/bin/activate
pip install datasets
```

The project's original `readme.md` references `~/devbox/envs/otzios/`; that's
the maintainer's path, not a project convention.

OSCAR-2301 is a **gated** HuggingFace dataset; without `huggingface-cli login`
plus accepted terms, `process_corpus.py` will silently skip it
(`process_corpus.py:255-261`).

## End-to-end pipeline

All scripts assume the working directory is the repo root and that
`data/dictionaries/` and `data/processed/` already exist.

1. Download the DEX MySQL dump from
   [dexonline.ro](https://wiki.dexonline.ro/wiki/Informa%C8%9Bii#Desc%C4%83rcare)
   to `data/dictionaries/dex-database.sql`.
2. `python create_sample_db.py` → `data/dictionaries/dex-database-sample.sql`
3. `python extract_lexemes.py` → `data/processed/lexemes.csv` and
   `data/processed/lexemes.db` (regex-extracts the `Lexeme` table directly from
   the dump; the alternate `convert_to_sqlite.sh` / `mysql_to_sqlite.py` paths
   are not used downstream — see "Known issues").
4. `python analyze_forgotten_words.py` → `data/processed/forgotten_words_v1.csv`
   and `statistics.txt`.
5. `python create_curated_list.py` → `data/processed/forgotten_words_curated.csv`.
6. `python download_wikipedia_ro.py` (interactive `y/N`) primes the HF cache.
7. `python process_corpus.py --test|--sample|--full [--wikipedia-only|--oscar-only]`
   → `data/processed/corpus_frequencies.db`.
8. `python validate_forgotten_words.py` →
   `data/processed/forgotten_words_validated.csv`,
   `false_positives.csv`, and `validation_report.txt`.

## Key data contracts

### `lexemes.db` — `Lexeme` table

Defined in `extract_lexemes.py:124-150`. 23 columns; the ones the rest of the
pipeline actually reads are:

- `form` — the word as it appears in DEX
- `formNoAccent` — accent-stripped form
- `frequency` — DEX frequency score, `0.0` (no data) to `1.0` (very common).
  **Lower = more likely forgotten.** Treat `0.0` as missing data, not "rarest".
- `description` — short part-of-speech / register marker (e.g. `s.f.`, `adj.`)
- `modelType`, `notes` — used by the curation heuristics

### `forgotten_words_curated.csv`

Written by `create_curated_list.py:166-189`. Columns:

```
word, word_no_accent, frequency, rarity_category, description, model_type, notes
```

`rarity_category ∈ {very_rare, rare, uncommon}`, with bin edges 0.30 and 0.50
(see `create_curated_list.py:131-138`). Note these bins do **not** match the
ones used in `analyze_forgotten_words.py` — see "Known issues".

### `corpus_frequencies.db` — schema in `process_corpus.py:69-105`

```
corpus_word_frequency(
  id PK, word, corpus_name, occurrence_count, document_count, last_updated,
  UNIQUE(word, corpus_name)
)
processing_stats(
  id PK, corpus_name, documents_processed, tokens_processed,
  unique_words_found, processing_time_seconds, completed_at, status
)
```

`corpus_name` is one of `wikipedia_ro`, `oscar_ro`. Words stored here are
already lowercased and NFC-normalized.

## Known issues to be aware of when editing

These are real and known; do not assume the current behavior is correct.

1. **Phase 2 candidate-set mismatch (correctness bug, P0).**
   `process_corpus.py:56-67,187,292` only increments counts for tokens present
   in `forgotten_words_curated.csv` (~1.9k words). But
   `validate_forgotten_words.py:64-70` selects candidates from `lexemes.db`
   using `frequency > 0.01 AND frequency < 0.60 AND LENGTH(form) > 3`, which
   covers tens of thousands of lexemes. Words in that broader set but absent
   from the curated CSV are never observed in the corpus, so they fall through
   `validate_forgotten_words.py` with `total_occurrences = 0` and get
   classified as `confirmed_forgotten` with confidence ~0.99. The headline
   "159,543 validated, 1 false positive" in `docs/phase2-test-results.md` is a
   consequence of this bug, not evidence that validation works. Either source
   the validator from the curated CSV, or have `process_corpus.py` count every
   token and let validation join the same broader band.

2. **Three competing MySQL→SQLite paths.** Only `extract_lexemes.py` is wired
   into the canonical pipeline. `convert_to_sqlite.sh` mishandles MySQL
   directives that span lines and naively rewrites types (lines 31, 42-50);
   `mysql_to_sqlite.py:97` silently swallows errors that look AUTOINCREMENT-ish.
   Prefer `extract_lexemes.py`; the other two should be archived.

3. **`explore_dex.py` is dead code.** Imports `sqlite3` but never uses it; the
   `__main__` block points its `db_path` at a `.sql` file that
   `sqlite3.connect()` cannot open. The content is narrative documentation —
   move it to `docs/` if you find it useful, otherwise delete.

4. **Frequency-bin definitions disagree across scripts.**
   `analyze_forgotten_words.py` reports bins at 0.25 / 0.50 / 0.70.
   `create_curated_list.py:131-138` uses 0.30 / 0.50 with a 0.60 ceiling.
   `validate_forgotten_words.py:67` filters 0.01–0.60. There is no shared
   `constants.py`; if you change one, hunt down the others.

5. **No CLI overrides for paths.** Every script hardcodes
   `data/dictionaries/...` or `data/processed/...` and assumes `cwd` is the
   repo root. `process_corpus.py` has `argparse` but only for mode selection,
   not paths.

6. **Tokenizer has no lemmatization** (already in `readme.md`'s "Known
   limitations"). `bucle` will not match `buclele`. `simplemma` would slot in
   at `process_corpus.py:tokenize_romanian` with minimal disruption.

7. **`create_curated_list.py:28-32`** has a regex `r"^[a-z]+-[a-z]+'"` whose
   trailing apostrophe looks like a typo. Verify intent before relying on the
   filter.

8. **OSCAR auth fails silently** (`process_corpus.py:255-261`). For automation
   you probably want to fail loudly when `--full` is requested but OSCAR is
   unreachable.

9. **`download_wikipedia_ro.py` blocks on interactive `y/N`** with no `--yes`
   flag — not scriptable as-is.

10. **Confidence-score weights are unjustified.**
    `validate_forgotten_words.py:215` uses `dex×0.3 + corpus×0.5 + doc×0.2`
    with no calibration. Treat the score as ordinal, not absolute.

## Conventions

- **One script per pipeline stage.** New stages get a new top-level script;
  resist the urge to introduce a package layout until there are at least 3
  modules sharing helpers.
- **Romanian normalization** for any new corpus or matching code: lowercase,
  cedilla→comma diacritics (`ş→ș`, `ţ→ț`), then `unicodedata.normalize('NFC', …)`.
  `process_corpus.py:26-37` is the canonical implementation; reuse it rather
  than rewriting.
- **Generated artifacts go under `data/`** and are gitignored. Do not commit
  `*.db`, `*.csv`, or anything from `data/`.
- **Don't import `explore_dex.py`** — it's documentation, not a module.
- **DEX `frequency = 0` means "no data", not "never occurs".** Existing scripts
  filter it out with `frequency > 0` or `> 0.01`; new code should do the same.

## Enhancement backlog

Open items, ranked by impact-per-effort. Effort is XS/S/M/L (rough).

| #   | Enhancement                                                              | Effort | Impact |
| --- | ------------------------------------------------------------------------ | ------ | ------ |
| 1   | Fix the Phase 2 candidate-set mismatch (see "Known issues" #1)           | S      | High   |
| 2   | Add `requirements.txt` (or `pyproject.toml` with PEP 621 metadata)       | XS     | Med    |
| 3   | Pick one MySQL→SQLite path; archive `convert_to_sqlite.sh` + `mysql_to_sqlite.py` | S | Med |
| 4   | Move `explore_dex.py` content to `docs/`; delete the script              | XS     | Low    |
| 5   | Centralize frequency bins / thresholds in a shared `constants.py`        | S      | Med    |
| 6   | Add lemmatization (`simplemma` is a one-line dep) at tokenization        | M      | High   |
| 7   | `tests/` with `pytest` covering normalization + curation heuristics; add `ruff` and a GitHub Actions CI | M | High |
| 8   | Re-run Phase 2 after #1 and overwrite `docs/phase2-test-results.md`      | S      | High   |
| 9   | Parallelize tokenization with `multiprocessing.Pool`                     | M      | Med    |
| 10  | `--yes` flag on `download_wikipedia_ro.py`                               | XS     | Low    |
| 11  | Calibrate / document the confidence-score weights                        | S      | Med    |
| 12  | Filter modern borrowings (English/French loanwords, brand names)         | M      | Med    |
| 13  | Optional structured logging + `--quiet` flag (replace decorative banners)| S      | Low    |

The `readme.md` "Roadmap" section captures longer-horizon work
(Phases 3–5: full DEX metadata, web UI, etc.) and supersedes nothing here.

## Out of scope / non-goals

- **Web UI / API server.** The roadmap mentions one for Phase 5; do not start
  it without an explicit go-ahead. The current value of the project is the
  data, not the interface.
- **A database server.** SQLite is sufficient and trivially portable. Don't
  introduce Postgres unless a concrete requirement (concurrent writers,
  full-text search at scale) demands it.
- **Heavy ML / embeddings.** The pipeline is deliberately frequency-based and
  cheap to re-run. Embedding-based "semantic forgottenness" is a research
  detour; keep it out of the main pipeline.
- **Packaging for PyPI.** Loose scripts are fine for the current scope.
