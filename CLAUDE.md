# CLAUDE.md

Guidance for Claude (and humans) working in this repository.

## Project overview

Oțios identifies "forgotten" Romanian words: terms in DEX Online (the official dictionary) that have fallen out of modern usage. Pipeline runs in two phases:

- **Phase 1 — dictionary analysis.** Parse the 1.2 GB DEX Online MySQL dump → SQLite, filter by the `frequency` field, curate a ~1.9k candidate list.
- **Phase 2 — corpus validation.** Two paths:
  - **Preferred:** `validate_with_wordfreq.py` — uses `wordfreq` + `simplemma` for fast frequency lookup without streaming corpora. See `docs/wordfreq-recipe.md`.
  - **Legacy:** Stream Romanian Wikipedia via HuggingFace `datasets` (`process_corpus.py` → `validate_forgotten_words.py`). Has a P0 candidate-set bug — see `docs/BACKLOG.md`.
- **Phase 3 — web validation.** `search_wild.py` — queries each Phase-2-confirmed word against the Romanian web via Google Custom Search API, recording whether it still appears "in the wild" and when it was last seen.

For the methodological critique (what "forgotten" should mean, corpus options): `docs/conceptual-roadmap.md` first, then `docs/corpus-options.md`.

## Logs

Long-running scripts are logged to `~/g2-dev/logs/`. PIDs are saved as `<script-name>.pid` in the same directory. Check there when verifying background job status.

## Environment setup

The shared venv lives at `~/g2-dev/monitorulpreturilor/venv` — activate it before running any script:

```bash
source ~/g2-dev/monitorulpreturilor/venv/bin/activate
```

To set up from scratch:
```bash
python -m venv ~/g2-dev/monitorulpreturilor/venv && source ~/g2-dev/monitorulpreturilor/venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` covers both the legacy pipeline (`datasets`) and the preferred path (`wordfreq`, `simplemma`).

OSCAR-2301 is gated on HuggingFace — requires `huggingface-cli login` plus accepted terms. Without it, `process_corpus.py` silently skips OSCAR (`process_corpus.py:255-261`).

`search_wild.py` (Phase 3) needs two env vars:
```bash
export GOOGLE_API_KEY="AIza..."    # from Google Cloud Console → APIs & Services → Credentials
export GOOGLE_CSE_ID="017576..."   # from programmablesearchengine.google.com (set "Search entire web")
```
Free tier: 100 queries/day. Use `--limit 100` and re-run daily; checkpoint handles resume automatically.

## End-to-end pipeline

All scripts assume `cwd` is the repo root and `data/dictionaries/` + `data/processed/` exist.

**Phase 1:**
1. Download DEX MySQL dump to `data/dictionaries/dex-database.sql`
2. `python create_sample_db.py` → `data/dictionaries/dex-database-sample.sql`
3. `python extract_lexemes.py` → `data/processed/lexemes.csv` + `lexemes.db`
4. `python analyze_forgotten_words.py` → `data/processed/forgotten_words_v1.csv` + `statistics.txt`
5. `python create_curated_list.py` → `data/processed/forgotten_words_curated.csv`

**Phase 2 — preferred path:**
```bash
python validate_with_wordfreq.py
```
Output: `data/processed/forgotten_words_validated_wordfreq.csv` (adds `lemma`, `zipf_frequency`, `is_forgotten` columns; words with zipf < 3.0 are `is_forgotten=true`)

**Phase 3 — web validation:**
```bash
# Requires GOOGLE_API_KEY and GOOGLE_CSE_ID env vars
python search_wild.py --dry-run --limit 5   # preview queries, no API calls
python search_wild.py --limit 100            # live; resumable; 100/day = free-tier quota
```
Output: `data/processed/forgotten_words_web_validated.csv` (adds `google_total_results`, `in_wild`, `web_score`, `top_url`, `last_seen_approx`). `web_score` buckets: `truly_extinct` (0 results) / `nearly_extinct` (1–9) / `marginal` (10–99) / `alive_rare` (100+). See setup note below.

**Phase 2 — legacy path (has bugs, see BACKLOG):**
```bash
python download_wikipedia_ro.py          # interactive y/N prompt
python process_corpus.py --test|--sample|--full [--wikipedia-only|--oscar-only]
python validate_forgotten_words.py
```

## Key data contracts

### `lexemes.db` — `Lexeme` table (`extract_lexemes.py:124-150`)

Columns the pipeline reads:
- `form` — word as it appears in DEX
- `formNoAccent` — accent-stripped form
- `frequency` — DEX score 0.0–1.0. **Lower = more likely forgotten. Treat 0.0 as missing data, not "rarest".**
- `description` — part-of-speech / register (e.g. `s.f.`, `adj.`)
- `modelType`, `notes` — used by curation heuristics

### `forgotten_words_curated.csv` (`create_curated_list.py:166-189`)

```
word, word_no_accent, frequency, rarity_category, description, model_type, notes
```

`rarity_category ∈ {very_rare, rare, uncommon}`, bins at 0.30 and 0.50.

### `corpus_frequencies.db` (`process_corpus.py:69-105`)

```
corpus_word_frequency(id, word, corpus_name, occurrence_count, document_count, last_updated)
processing_stats(id, corpus_name, documents_processed, tokens_processed, ...)
```

`corpus_name ∈ {wikipedia_ro, oscar_ro}`. Words are lowercased and NFC-normalized.

## Gotchas

- **P0 bug:** `process_corpus.py` counts only words in the curated CSV (~1.9k), but `validate_forgotten_words.py` queries `lexemes.db` across tens of thousands. Most words are never observed → bogus "confirmed_forgotten" results. Full details + fix options in `docs/BACKLOG.md`.
- **Frequency bins disagree** across scripts (0.25/0.50/0.70 vs 0.30/0.50/0.60 vs 0.01–0.60). No shared constants file — changing one requires hunting down the others.
- **`explore_dex.py` is not a working script** — it's narrative documentation that can't run. Don't import or execute it.
- **`convert_to_sqlite.sh` and `mysql_to_sqlite.py` are not used** in the canonical pipeline. Use `extract_lexemes.py` instead.

## Conventions

- **One script per pipeline stage.** No package layout until 3+ modules share helpers.
- **Romanian normalization:** lowercase → cedilla-to-comma diacritics (`ş→ș`, `ţ→ț`) → `unicodedata.normalize('NFC', …)`. Canonical implementation: `process_corpus.py:26-37`.
- **Generated artifacts go under `data/`** (gitignored). Never commit `*.db`, `*.csv`, or `data/` contents.
- **`frequency = 0` means no data, not "rarest".** Filter with `frequency > 0` or `> 0.01`.

## Out of scope

- **Web UI / API** — mentioned in roadmap Phase 5; do not start without explicit go-ahead.
- **Database server** — SQLite is sufficient. No Postgres.
- **Embeddings / heavy ML** — pipeline is deliberately frequency-based and cheap to re-run.
- **PyPI packaging** — loose scripts are fine.

## Process notes

- When something needs follow-up, add a `- [ ]` entry to `docs/BACKLOG.md` with enough context to act on later.
- After meaningful work, add an entry to `docs/activity-history.md` under `## YYYY-MM-DD — Short Title`.
