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

Long-running scripts log to `data/logs/` inside the repo (gitignored by `data/*`). PIDs are saved as `<script-name>.pid` in the same directory.

```
data/logs/
  culturax.log / culturax.pid
  wikisource.log / wikisource.pid
  health_check.log      # cron output from health_check.py
  audit.log             # cron output from audit.py
  alerts.log            # every alert ever fired
  health_status.json    # alert dedup state
  run_history.jsonl     # one JSON line per audit run per corpus
  quality_YYYY-MM-DD.json
```

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

`search_wild.py` (Phase 3) ships two pluggable providers selected via `--provider`:

- `ddg` (default) — DuckDuckGo via the `ddgs` library. No API key. Noisy on rare archaic words (cross-language fuzzy matches), useful for prototyping.
- `google` — Google Custom Search JSON API. Needs two env vars; cleaner results.

```bash
export GOOGLE_API_KEY="AIza..."    # Google Cloud Console → APIs & Services → Credentials
export GOOGLE_CSE_ID="017576..."   # programmablesearchengine.google.com (set "Search entire web")
```
Google free tier: 100 queries/day. Use `--limit 100` and re-run daily; checkpoint handles resume automatically.

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
# Default provider is DDG (no env vars needed) — good for prototyping
python search_wild.py --dry-run --limit 5
python search_wild.py --provider ddg --limit 50 --delay 3

# Google CSE — cleaner results, needs env vars; 100/day free-tier quota
python search_wild.py --provider google --limit 100
```
Output: `data/processed/forgotten_words_web_validated.csv` (adds `total_results`, `in_wild`, `web_score`, `top_url`, `last_seen_approx`, `provider`). `web_score` buckets differ by provider — Google: 0 / <10 / <100 / 100+; DDG: 0 / <3 / <10 / 10+ (capped at 30).

**Filling definition gaps — `scrape_definitions.py`:**

`extract_definitions.py` recovers ~4.6k of the 17.4k shortlist words from the DEX MySQL dump (the dump's `DefinitionSimple` table is the source of truth — its `lexicon` column is the headword, not a dictionary identifier). The remaining ~12.8k shortlist words have no entry there and must be scraped from dexonline.ro.

```bash
python scrape_definitions.py --dry-run --limit 5         # smoke test, no HTTP
python scrape_definitions.py --limit 20 --delay 3.0      # small live run
python scrape_definitions.py --delay 3.0 --merge         # full run, ~5–7 hrs at 3s/req
python scrape_definitions.py --merge-only                # just upsert checkpoint into db
```

Output: `data/processed/scraped_definitions.csv` (columns: `word, definition, source_url, scraped_at, status`). `status ∈ {ok, not_found, error}`. With `--merge`, ok rows are `INSERT OR REPLACE`'d into `data/processed/definitions.db`. Resume is automatic: re-running skips words already in the checkpoint or in the definitions DB. Ctrl+C is safe — each row is flushed immediately. Be polite to dexonline.ro (community-run): keep `--delay ≥ 3`.

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

## Monitoring

Three scripts keep an eye on long-running corpus jobs:

- **`status.py`** — read-only, at-a-glance summary. Prints corpus run state, pipeline artifacts, loop liveness, and latest audit verdicts. Safe to run any time; never writes. First thing to run when checking on the project.
- **`health_check.py`** — checks loop liveness, checkpoint staleness, log errors, and corpus completion. Alerts once per new problem (no spam on repeat cron fires). Run every 30 min via cron.
- **`audit.py`** — snapshots run history to `data/logs/run_history.jsonl` and runs quality checks (cycling detection, token ratio sanity, word coverage). Run daily.

`health_check.py` and `audit.py` support `--dry-run`. Alerting backends (set env vars before running or in crontab):
```bash
export OTZIOS_ALERT_URL="https://ntfy.sh/your-topic"   # POST plain text — works with ntfy.sh, many webhooks
export OTZIOS_ALERT_EMAIL="you@example.com"             # sends via system mail
```

Cron entries (install with `crontab -e`):
```cron
*/30 * * * * cd /home/pax/g2-dev/otzios && /home/pax/g2-dev/monitorulpreturilor/venv/bin/python health_check.py >> data/logs/health_check.log 2>&1
0 2 * * *   cd /home/pax/g2-dev/otzios && /home/pax/g2-dev/monitorulpreturilor/venv/bin/python audit.py         >> data/logs/audit.log      2>&1
```

Update `VENV` to `.venv/bin/python` after the in-project venv migration.

### Venv migration (deferred — after culturax finishes)

```bash
cd /home/pax/g2-dev/otzios
python -m venv .venv
source .venv/bin/activate && pip install -r requirements.txt
# then update crontab VENV path and restart any loops
```

## Process notes

- When something needs follow-up, add a `- [ ]` entry to `docs/BACKLOG.md` with enough context to act on later.
- After meaningful work, add an entry to `docs/activity-history.md` under `## YYYY-MM-DD — Short Title`.
