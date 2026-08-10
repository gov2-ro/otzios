# Oțios - Romanian Forgotten Words Finder

<mark>[⚠️NOTE]</mark> Data still needs some finetunning and QA.

A computational linguistics tool to identify "forgotten" Romanian words - terms that exist in official dictionaries but have fallen out of modern usage.

**Status**: 📚 Definitions + 🔍 Phase 3 + 🌐 Web UI (PHP) — shortlist generated, definitions complete, web validation next

## What It Does

- Generates a list of the *least used* or forgotten words from Romanian dictionaries
- Compares official dictionaries (including archaisms) against usage frequency data
- Identifies linguistic "dark matter" - words that exist in dictionaries but have fallen out of active use
- Produces curated lists with rarity scores and linguistic metadata


![Oțios Interface](public/screenshot-otzios.png)

See exploratory UI prototype: [lab.gov2.ro/oțios](https://lab.gov2.ro/otios/)

---

Vezi și: [initial specs](docs/oțios-init-specs.docx.md) / [live](https://docs.google.com/document/d/1FTMIONmSylQDaV4YxFprd8jyHxREXpcL/) (google doc) 

## Pipeline

### End-to-end flow

```mermaid
flowchart TD
    DEX[("DEX Online dump<br/>1.65 GB MySQL")]

    subgraph P1["Phase 1 · Extraction"]
        C["extract_lexemes.py"] --> D[("lexemes.db<br/>317.7k lexemes")]
        D --> TAX["extract_taxonomy.py"] --> D
        IF["extract_inflected_forms.py"] --> IFDB[("inflected_forms.db<br/>2.27M forms → lemma")]
        DS["extract_dict_sources.py"] --> DSDB[("dict_sources.db<br/>113 dictionaries + years")]
        DEFS["extract_definitions.py"] --> DEFDB[("definitions.db")]
        D --> G["create_curated_list.py"] --> H[("forgotten_words_curated.csv<br/>~140k candidates")]
    end

    subgraph P2["Phase 2 · Corpora"]
        WS["process_wikisource.py<br/>historical · 14.3M tokens"]
        LU["process_lumro.py<br/>historical · 5.1M tokens<br/>175 novels, 1845–1920"]
        CX["process_culturax.py<br/>modern web · 17.0B tokens"]
        WS & LU & CX --> CORP[("corpus_frequencies.db")]
        CO["process_corola.py<br/>reference · 638M tokens<br/>loaded, not in any panel"] -.-> CORP
    end

    subgraph P3["Phase 3 · Verdicts, scoring, UI"]
        DIA["validate_diachronic.py<br/>paradigm-level counts<br/>occurrence thresholds"]
        DIA --> DIA_OUT[("forgotten_words_diachronic.csv<br/>130k rows")]
        DIA_OUT --> SL["make_shortlist.py<br/>composite score"]
        SL --> SL_OUT[("forgotten_words_shortlist.csv<br/>17,577 rows · 2 seams")]
        SL_OUT --> UI["tools/build_ui_db.py"] --> UIDB[("public/data/ui.db<br/>17,687 words")]
    end

    DEX --> C & IF & DS & DEFS
    H --> WS & LU & CX
    H --> DIA
    CORP --> DIA
    IFDB --> DIA
    DSDB --> DIA
    DEFDB --> DIA
    IFDB --> SL
    DSDB --> UI
    DEFDB --> UI
    UIDB --> PHP["public/ · PHP app"]
```

**Three things this diagram is built around:**

- **`inflected_forms.db` feeds `validate_diachronic.py`.** The corpus processors count raw
  tokens, so without the paradigm map a lemma is only ever credited with its citation form
  — `înmărmuri` scored 317 while `înmărmurit` alone is 5,846, and every verb drifted toward
  "extinct".
- **Thresholds are occurrence counts, never ppm.** Wikisource and CulturaX differ by
  1,187× in size, so a shared `0.1 ppm` floor meant "fewer than 1,697 modern hits" on one
  side and "at least 1.43 historical hits" on the other. They *are* rescaled when the
  modern panel itself grows (`scaled_modern_thresholds`), or adding a corpus would make
  every word look more alive.
- **Each side is a panel, not a corpus.** The historical side is Wikisource + LUMRO,
  aggregated separately and merged, so documents sum across corpora but stay a max within
  one. A corpus is only added after being measured: `subtitle_ro` is inert (≈1/6th of it is
  folk-music television) and `corola_ro` is loaded but in no panel (it spans 1945+, so
  presence in it is not evidence of *current* use). Both stories are in
  `docs/corpus-expansion-plan.md`.

`make_shortlist.py` splits its output into two seams via a `seam` column: **`relevant`**
(3,495) and **`curiosity`** (14,082). The default view is the `relevant` seam minus four
hide-flags — regional, paradigm variants, proper nouns and obsolete spellings — about 2,800
words, each flag a one-click toggle. See `CLAUDE.md` → Seams.

The legacy Wikipedia/OSCAR branch (`process_corpus.py`, `validate_forgotten_words.py`),
`search_wild.py` and the old Flask UI now live in `archive/` — see `archive/README.md`.

## Quick Start

### Prerequisites

```bash
# Activate virtual environment (adjust path to your venv)
source ~/devbox/envs/240826/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

### Phase 1: Extraction

Each of these streams the 1.65 GB dump once. The four extractors are independent, so
order does not matter between them.

```bash
python extract_lexemes.py          # → lexemes.csv + lexemes.db
python extract_taxonomy.py         # → Tag/ObjectTag/… into lexemes.db (register, domain)
python extract_inflected_forms.py  # → inflected_forms.db  (2.27M forms → lemma)
python extract_dict_sources.py     # → dict_sources.db     (names, years, in_current_dict)
python extract_definitions.py      # → definitions.db
python create_curated_list.py      # → forgotten_words_curated.csv
```

**Output**: `forgotten_words_curated.csv` (~140k candidates)

> `extract_inflected_forms.py` is not optional. Without it `validate_diachronic.py` falls
> back to citation-form counts and every verb in the list reads as extinct.

### Phase 2a: Quick frequency screen (wordfreq)

```bash
python validate_with_wordfreq.py
```

**Outputs two files:**
- `forgotten_words_validated_wordfreq.csv` — words with Zipf < 3.0 (`tier=forgotten`)
- `rare_words_wordfreq.csv` — words with Zipf 3.0–4.5 **and** a non-empty `dex_register` tag (`tier=rare_in_use`)

The `tier` column supersedes `is_forgotten` (kept for backward compatibility). Note: wordfreq's Romanian coverage is binary (0.000 or ≥ 3.0), so treat this as a rough first pass. The `rare_in_use` gate on `dex_register` prevents modern unmarked vocabulary (neurologie, cowboy…) from polluting the rare list.

### Phase 1b: Taxonomy extraction (run once after Phase 1)

Extracts `Tag`, `ObjectTag`, and `EntryLexeme` tables from the DEX dump into `lexemes.db`, enabling register/domain/etymology/POS columns in the diachronic output.

```bash
# Sample dump (fast, ~5% coverage)
python extract_taxonomy.py

# Full dump (recommended — ~990k ObjectTag rows, full coverage)
python extract_taxonomy.py --sql data/dictionaries/dex-database.sql
```

### Phase 2b: Corpus validation — diachronic (recommended)

Uses Wikisource RO and LUMRO (historical) against CulturaX RO (modern web) to compute
actual per-corpus frequencies. Designed to find words that appear in 19th-century
literature but are absent from modern text.

```bash
# LUMRO — 175 dated novels, 1845–1920. Download once, then a 3-second run.
curl -sL -o data/raw/lumro.zip \
    https://codeload.github.com/upb-nlp/LUMRO/zip/refs/heads/main
python process_lumro.py --dry-run     # parse and count, write nothing
python process_lumro.py               # → corpus_frequencies.db (lumro_ro)

# CoRoLa — reference corpus, 638M tokens. Loaded but in NO panel: it spans 1945+, so
# presence in it is not evidence of current use. CC BY-NC-ND, input only — no
# CoRoLa-derived number may be published. See docs/corpus-expansion-plan.md.
curl -sL -o data/raw/corola_frequencies.zip \
    "https://zenodo.org/records/7091535/files/corola_frequencies.zip?download=1"
python process_corola.py

# Wikisource — test run (500 docs, ~10s)
python process_wikisource.py --test

# Wikisource — full run (best on a VPS)
mkdir -p data/logs
nohup python process_wikisource.py --resume >> data/logs/wikisource.log 2>&1 &
echo $! > data/logs/wikisource.pid

# CulturaX — full run (64 parquet shards, ~40M docs; auto-restarts on network errors)
# Interactive (watch it run):
while true; do
    python -u process_culturax.py --resume
    [ $? -eq 0 ] && break
    echo "[$(date)] restarting in 15s..." && sleep 15
done

# Background (logs to file):
VENV=~/g2-dev/monitorulpreturilor/venv/bin/python
mkdir -p data/logs
nohup bash -c "while true; do $VENV -u process_culturax.py --resume; [ \$? -eq 0 ] && break; echo \"[\$(date)] restarting in 15s...\"; sleep 15; done" \
  >> data/logs/culturax.log 2>&1 &
echo $! > data/logs/culturax.pid
```

**Output**: `corpus_frequencies.db` with `corpus_name = 'wikisource_ro'` and `corpus_name = 'culturax_ro'`.

Note: `process_culturax.py` reads the 64 parquet shards directly via `HfFileSystem` + `pyarrow` and checkpoints at file + row-group level. This avoids the `datasets` streaming `ds.skip()` cycling bug that triggers when the checkpoint offset exceeds the dataset size.

### Phase 2b continued: diachronic comparison + shortlist

```bash
# Roll corpus counts up over inflection paradigms, assign verdicts from occurrence
# counts, add taxonomy + dictionary-year columns
python validate_diachronic.py
# Output: forgotten_words_diachronic.csv (130k rows)

# Score every candidate and split into the two seams
python make_shortlist.py --stats        # preview seam and tier counts
python make_shortlist.py                # → forgotten_words_shortlist.csv (16,203 rows)
python make_shortlist.py --min-score 88 # loosen/tighten the relevant seam

# Build the database the PHP app reads
python tools/build_ui_db.py             # → public/data/ui.db (16,315 words)
```

After a rebuild, check that `data/word_ids.tsv` gained lines and lost none:

```bash
git diff --numstat data/word_ids.tsv    # must read "<n>\t0"
```

That file is what makes `?w=` share links durable; a renumbering silently breaks every
link ever shared. `tests/test_rescore.py` asserts it too.

### Phase 2.5: Fill definition gaps from dexonline.ro

The DEX MySQL dump's `DefinitionSimple` table only covers ~4.6k of the 17.4k shortlist words. `scrape_definitions.py` fills the remaining gaps by extracting the synthesis (definition) from dexonline.ro for each missing word.

```bash
# Smoke test (5 words, no HTTP)
python scrape_definitions.py --dry-run --limit 5

# Small live run (test the scraper)
python scrape_definitions.py --limit 20 --delay 3.0

# Full run (all missing words, ~5–7 hours at 3s/request)
python scrape_definitions.py --delay 3.0 --merge

# Resume an interrupted run
python scrape_definitions.py --delay 3.0 --merge      # automatically skips already-scraped

# Just upsert checkpoint into DB (if scraping completed but merge wasn't run)
python scrape_definitions.py --merge-only
```

**Output**: `data/processed/scraped_definitions.csv` (checkpoint with columns: `word, definition, source_url, scraped_at, status`). With `--merge`, all `status=ok` rows are upserted into `definitions.db` immediately. Resume is safe — each row is flushed instantly; Ctrl+C stops cleanly.

### Phase 3: Web validation — retired

`search_wild.py` (DuckDuckGo / Google CSE) moved to `archive/` in August 2026. It had
reached 47 of 25,305 words (0.19%), and `build_ui_db.py` was reading a different file
than the one it wrote. With corpus counts now aggregated over paradigms, "is this word
still used?" is answered from 17B tokens of CulturaX without a daily quota.

## The web app

The site in `public/` is plain PHP + SQLite, no build step and no framework. It reads
`public/data/ui.db` (generated by `tools/build_ui_db.py` from the pipeline output) and
writes user data to `app.db`, which lives **outside** the web root.

### Running it locally

```bash
php -S localhost:8000 -t public/
```

That is the whole setup — the app is zero-config and creates `private/app.db` and
`private/secret.key` on first request.

Tests need the server running:

```bash
php -S localhost:8777 -t public/ &
node tests/test_lists_api.js
node tests/test_game_api.js
node tests/test_store_sync.js
OTIOS_ADMIN_TOKEN=<your local token> node tests/test_moderation.js
```

They write to the real `app.db`, so point `OTIOS_TEST_URL` at a dev instance, never
production.

### Configuration — `api/config.local.php`

Every setting is optional. Copy the template and edit:

```bash
cp public/api/config.local.example.php public/api/config.local.php
```

The file is **gitignored and per-install** — your laptop and the server each get their
own, with different values. `_appdb.php` loads it before deciding anything.

| Constant | What it does |
|---|---|
| `OTIOS_PRIVATE_DIR` | Where `app.db` and `secret.key` live. Defaults to `<parent of public/>/private`, which is wrong on a subfolder install — see CLAUDE.md |
| `OTIOS_ADMIN_TOKEN` | Unlocks `admin.php`. Undefined ⇒ the page 404s and there is no way in |
| `OTIOS_QUIZ_SECRET` | Overrides the auto-generated `secret.key`. Only needed across multiple web nodes |

> **Deploying:** never copy your local `config.local.php` over the server's.
> `rsync -av --exclude 'api/config.local.php' public/ you@host:~/site/`

### Moderation — `admin.php`

Public lists (`liste.php`) are written by visitors and are not pre-checked, so there is a
report → review path.

**Readers report.** A public list someone else owns carries a quiet *raportează lista*
link at the bottom of `lista.php`. One report per person per list; a reason is optional.

**You review** at `/admin.php`, a queue of reported lists, most-reported first, showing
who published it, how many reports, and what the reporters wrote. Three actions:

| Action | Effect |
|---|---|
| **depublică** | `is_public = 0`. Drops out of the directory and the shared link 404s for strangers — but the owner keeps the list and its words. This is the default: nothing of theirs is destroyed on a stranger's say-so |
| **respinge raportările** | The list was fine. Clears the reports, changes nothing else |
| **șterge definitiv** | Deletes the list and its items. The only irreversible action |

Reports queue for a human — there is deliberately **no auto-hide after N reports**.
Identity here is an anonymous device token, so "three different people reported this"
costs an abuser three cookie clears; a threshold would make censoring a list cheaper than
publishing one.

#### Generating the token

```bash
openssl rand -hex 24        # → 48 hex characters
```

Put it in `config.local.php`:

```php
define('OTIOS_ADMIN_TOKEN', '****}');
```

Keep it in a password manager — it is the only credential, with no username and no
account behind it. Anything under 16 characters is rejected, so a placeholder cannot
quietly become the password.

#### How the token works

Visit **once** with the token in the URL:

```
https://your-site/admin.php?token=a1b2c3d4e5f6...
```

The page compares it with `hash_equals()` (a constant-time compare — a plain `===`
short-circuits on the first differing byte, which leaks the prefix to anyone willing to
time the responses), then seals an 8-hour session into an HttpOnly cookie and redirects
to the bare `/admin.php`. After that first hit the token is out of the address bar, the
browser history, the server access log and any outbound `Referer`.

A wrong token — or none — returns **404, not 403**, so an install that never configured
moderation gives nothing away when probed. Rotating the token is just changing the value;
existing browser sessions are sealed with the app secret rather than the token, so they
survive until they expire. To cut them off immediately, delete `private/secret.key` too
(this also invalidates in-flight quiz tokens).

### Backups

`app.db` is the only irreplaceable file in a deploy — `ui.db` regenerates from the
pipeline, but annotations, lists, nicknames and the game log exist nowhere else.

```bash
php api/_backup.php              # snapshot + prune, keeping the newest 14
php api/_backup.php --keep 30    # keep more
php api/_backup.php --dir /mnt/x # write somewhere else
php api/_backup.php --list       # show what's there, write nothing
```

Nightly, from the deployed app folder:

```cron
17 3 * * * cd ~/lab.gov2.ro/oțios && php api/_backup.php >> ~/otios-private/backup.log 2>&1
```

It uses `VACUUM INTO` rather than a file copy (in WAL mode the committed data is split
across `app.db` and `app.db-wal`, so a copy can land mid-transaction), then reopens each
snapshot and runs `PRAGMA integrity_check` before pruning old ones. The script sits in
`public/api/` because only the contents of `public/` reach the server, and is CLI-only —
over HTTP it returns 404.

This is not an off-machine backup. A snapshot beside the original survives a bad
migration or a mistaken delete, not a lost disk.

## Monitoring

```mermaid
flowchart LR
    subgraph JOBS["Long-running corpus jobs"]
        J1["process_wikisource.py"]
        J2["process_culturax.py"]
    end

    subgraph LOGS["data/logs/"]
        L1["wikisource.log / .pid"]
        L2["culturax.log / .pid"]
        L3["run_history.jsonl"]
        L4["health_status.json"]
    end

    subgraph MON["Monitoring scripts"]
        ST["status.py\n(read-only · any time)"]
        HC["health_check.py\n(cron · every 30 min)"]
        AU["audit.py\n(cron · daily 02:00)"]
    end

    subgraph ALERT["Alert channels"]
        AW["webhook\nOTZIOS_ALERT_URL"]
        AE["email\nOTZIOS_ALERT_EMAIL"]
    end

    JOBS --> LOGS
    LOGS --> ST & HC & AU
    HC & AU --> AW & AE
```

`health_check.py`, `audit.py`, and `status.py` keep tabs on long-running corpus jobs. Run them manually or via cron (see CLAUDE.md for crontab lines).

```bash
python status.py                # at-a-glance summary — corpora, artifacts, loops, audit
python health_check.py          # check liveness, stalls, log errors, completion
python audit.py                 # snapshot run history + DB quality checks
python health_check.py --dry-run  # print without alerting or writing state
```

`status.py` is read-only — safe to run any time. `health_check.py` and `audit.py` write logs and may alert.

Set `OTZIOS_ALERT_URL` (webhook) or `OTZIOS_ALERT_EMAIL` to receive push alerts.

## Data notes

**Apostrophes in the `word` column** — DEX Online encodes syllable stress using apostrophes (e.g. `bucl'e`, `băt'ârn`). These are not real Romanian words; the clean form is in `word_no_accent`. The validated output from `validate_with_wordfreq.py` uses `word_no_accent` for all lookups and moves the raw `word` column to the end of the CSV for reference.

## Output files

All generated files live under `data/processed/`. Columns shared across files have the same meaning everywhere.

**How the files relate:**

```
forgotten_words_curated.csv    — 140k dictionary suspects (no corpus signal)
        ↓ validate_diachronic.py
forgotten_words_diachronic.csv — 130k rows with corpus frequencies + taxonomy
        ↓ make_shortlist.py
forgotten_words_shortlist.csv  — 16,203 scored words, split into 2 seams
        ↓ tools/build_ui_db.py
public/data/ui.db              — 16,315 words for the PHP app
```

### Shared columns

| Column | Description |
|---|---|
| `word` | Word form as it appears in DEX, including stress apostrophes (e.g. `bucl'e`). Use `word_no_accent` for lookups. |
| `word_no_accent` | Clean form with apostrophes removed — the canonical key for all frequency lookups. |
| `frequency` / `dex_frequency` | DEX frequency score, 0.0–1.0. **Lower = rarer.** `0.0` means the field was absent in DEX — treat it as missing data, not "rarest". |
| `rarity_category` | Bin derived from `dex_frequency`: `very_rare` (< 0.30), `rare` (0.30–0.50), `uncommon` (0.50–0.60), `standard` (0.60–1.0). `standard` means DEX considers the word canonical but corpus evidence may disagree. |
| `description` | Part-of-speech and register abbreviation from DEX (e.g. `s.n.` = neuter noun, `adj.` = adjective, `înv.` = archaic). |
| `model_type` | DEX inflection model code (e.g. `I`, `A1`). Identifies the paradigm used for conjugation/declension. |

---

### `forgotten_words_curated.csv` — Phase 1 candidates (dictionary only)

Every DEX entry with frequency < 1.0 that passes form filters (length, not a proper noun, has a word-class marker). No corpus evidence — these are *suspects*, not confirmed forgotten words. Currently ~140k rows.

| Column | Description |
|---|---|
| `notes` | Raw notes from the DEX entry (register markers, usage labels, etc.). |

---

### `forgotten_words_diachronic.csv` — Phase 2b validated output (corpus evidence)

One row per candidate from `forgotten_words_curated.csv`, enriched with measured frequencies from both corpora and a verdict. This is the file to use for any downstream analysis — it tells you *whether* each word is actually missing from modern text, and by how much.

| Column | Description |
|---|---|
| `hist_occurrences` | Raw occurrence count in the Wikisource RO corpus (historical literary baseline, ~14M tokens). |
| `hist_documents` | Number of distinct Wikisource documents containing the word. |
| `hist_ppm` | `hist_occurrences` normalised to **occurrences per million tokens** in Wikisource. |
| `modern_occurrences` | Raw occurrence count in the CulturaX RO corpus (modern web text, ~17B tokens). |
| `modern_documents` | Number of distinct CulturaX documents containing the word. |
| `modern_ppm` | `modern_occurrences` normalised to **occurrences per million tokens** in CulturaX. |
| `log_ratio` | `log₂((hist_ppm + S) / (modern_ppm + S))` where S = 0.1 per million (Laplace smoothing). **Positive = historically skewed; negative = more common today.** A value of 1.0 means the word is twice as frequent historically; −1.0 means twice as frequent now. |
| `verdict` | Categorical summary — see table below. |
| `dex_pos` | Full part-of-speech label from DEX Tag taxonomy (e.g. `substantiv neutru`, `adjectiv`, `verb`). Pipe-delimited if multiple. Empty until `extract_taxonomy.py` is run against the full dump. |
| `dex_register` | Stylistic register tags from DEX (e.g. `învechit`, `popular`, `dialectal`, `livresc`). Pipe-delimited. A word tagged `învechit` in DEX is direct editorial evidence of archaism, independent of corpus signal. |
| `dex_domain` | Subject domain tags (e.g. `muzică`, `chimie`, `medicină`, `drept`). Pipe-delimited. Useful for filtering out technical jargon. |
| `dex_etymology` | Etymology/origin tags (e.g. `grecism`, `latinism`, `anglicism`, `turcism`, `slavonism`). Pipe-delimited. |

**Verdict values:**

| Verdict | Condition |
|---|---|
| `extinct` | `hist_ppm ≥ 1.0` and `modern_ppm < 0.1` — well-attested historically, nearly absent today. |
| `declining` | `log_ratio ≥ 1.0` — at least 2× more frequent historically, but still has some modern presence. |
| `historical_only` | `hist_ppm ≥ 0.1` and `modern_ppm < 0.1` — appears in old texts but not in modern corpus. |
| `stable` | `|log_ratio| < 1.0` — similar frequency across both corpora. |
| `modern_only` | `modern_ppm ≥ 0.1` and `hist_ppm < 0.1` — not in historical texts but present today (likely a newer word or false positive). |
| `emerging` | `log_ratio ≤ −1.0` — at least 2× more frequent in modern corpus. |
| `absent` | Both `hist_ppm < 0.1` and `modern_ppm < 0.1` — too rare to appear meaningfully in either corpus. |

---

### `forgotten_words_shortlist.csv` — Phase 2.5 filtered shortlist

Generated by `make_shortlist.py` from the diachronic CSV. Three selection tiers, all with POS exclusions applied:

| Tier | `confidence_tier` value | Count | Criterion |
|---|---|---|---|
| A | `corpus_extinct` | 1,218 | `verdict=extinct`, `hist_ppm > 0` |
| A | `corpus_declining` | 3,228 | `verdict=declining` — attested historically, 500–1,999 modern occurrences |
| A | `corpus_historical_only` | 5,339 | `verdict=historical_only` — attested historically, under 500 modern |
| B | `dex_invechit_absent` | 3,333 | `verdict=absent` + `dex_register` contains `învechit` |
| C | `dex_absent_highfreq` | 4,233 | `verdict=absent`, `dex_frequency ≥ 0.85` |

Tier B: DEX editorial + absent from all corpora — two independent archaism signals. Tier C: highest DEX legitimacy but no corpus trace at all — the "most forgotten" words (e.g. *oțios*, dex_frequency=0.85). Tune Tier C with `--dex-freq-threshold` (default 0.85).

Every row also carries `quality_score`, `seam` (`relevant` / `curiosity`) and the three
hide-flags `regional_only`, `variant_like`, `proper_noun_like`. See `CLAUDE.md` → Seams
for how the score and the flags divide the work.

---

### `forgotten_words_web_validated.csv` — Phase 3 output *(retired)*

Produced by `search_wild.py`, now in `archive/`. Kept here because a stale copy of this
file is still merged by `build_ui_db.py` for 47 words.

| Column | Description |
|---|---|
| `total_results` | Approximate search result count returned by the provider for the word query. |
| `in_wild` | `true` if the provider returned at least one result — word still appears somewhere on the Romanian web. |
| `web_score` | Categorical bucket based on `total_results`. **DDG:** `0` / `alive_rare` (1–9) / `alive` (10–29) / `common` (30+). **Google:** `0` / `alive_rare` (1–9) / `alive` (10–99) / `common` (100+). |
| `top_url` | URL of the top-ranked search result, if any. |
| `last_seen_approx` | Best-effort approximate date the word was last seen on the web (parsed from result metadata; often empty). |
| `provider` | Search backend used: `ddg` (DuckDuckGo, no API key) or `google` (Google Custom Search, needs env vars). |

---

### `forgotten_words_validated_wordfreq.csv` — Phase 2a output

Quick frequency screen via the `wordfreq` library, without streaming any corpus.

| Column | Description |
|---|---|
| `lemma` | Base form produced by `simplemma.lemmatize(word, lang='ro')`. This is what gets looked up in wordfreq. |
| `zipf_frequency` | Zipf-scale frequency from wordfreq's Romanian model (roughly: 6 = very common, 3 = uncommon, 0 = not in wordfreq's list at all). **`0.0` does not mean "least common" — it means wordfreq has no signal for this word.** |
| `tier` | Classification: `forgotten` (zipf < 3.0) / `rare_in_use` (3.0 ≤ zipf < 4.5, non-empty `dex_register`) / `common` (≥ 4.5 or no register tag). |
| `is_forgotten` | `true` if `tier == 'forgotten'`. |

## Project Structure

```
otios/
├── data/
│   ├── dictionaries/       # DEX Online database (download separately)
│   └── processed/          # Generated lexeme data and results
├── docs/                   # Documentation and specifications
│   ├── scripts-guide.md    # Detailed script documentation
│   ├── romanian-forgotten-words-spec.md
│   └── results-summary.md
└── *.py                    # Processing scripts
```

## Documentation

- **[docs/scripts-guide.md](docs/scripts-guide.md)** - Comprehensive guide to all scripts
- **[docs/romanian-forgotten-words-spec.md](docs/romanian-forgotten-words-spec.md)** - Technical specification
- **[docs/results-summary.md](docs/results-summary.md)** - Analysis results and findings
- **[docs/oțios.docx.md](docs/oțios.docx.md)** - Initial brainstorming document
- more docs: PHASE2_COMPLETE.md; phase2-test-results.md; scripts-guide.md

## Sample Results

Top extinct words from the diachronic analysis (high historical frequency, near-zero modern):

| Word | Meaning | DEX freq | log₂ ratio | Register | Etymology |
|------|---------|----------|-----------|----------|-----------|
| **tibișir** | type of muslin fabric | 0.82 | 8.53 | — | franțuzism |
| **ghiftui** | to stuff oneself | 0.94 | 7.44 | — | franțuzism |
| **coșcodan** | monkey (archaic) | 0.77 | 7.15 | — | — |
| **bolboacă** | clay cooking pot | 0.94 | 6.65 | învechit | — |
| **stacan** | type of goblet | 0.90 | 7.04 | — | — |
| **ietac** | private chamber | 0.91 | 4.19 | învechit | — |

DEX-tagged archaic words with no corpus signal at all (Tier B — "dark matter"):

| Word | Meaning | DEX freq | Register |
|------|---------|----------|----------|
| **vece** | outhouse (from Ger. *Wasserklose*) | 0.99 | învechit |
| **alenă** | breath, exhalation | 0.97 | învechit |
| **hurducăi** | to jolt, to shake about | 0.95 | învechit |
| **pripoană** | tethering stake | 0.95 | învechit |

## Data Sources

- **DEX Online Database**: Official Romanian dictionary (1.2 GB MySQL dump)
  - Download: [dexonline.ro](https://wiki.dexonline.ro/wiki/Informa%C8%9Bii#Desc%C4%83rcare)
  - 315,247 lexemes with frequency data
  - Archaic markers and linguistic metadata

## Roadmap

### misc notes / tasks

- [ ] fix mysql import - try a llm assisted import
- [ ] create another sample db with max 3 inserts per table - for analytics

### Phase 1: Dictionary Analysis (Complete ✅)
- [x] Database setup and conversion
- [x] Lexeme extraction pipeline
- [x] Frequency-based analysis
- [x] Quality filtering and curation
- [x] CSV export with ~140k candidates (cutoff raised to DEX freq < 1.0)

**Output**: `forgotten_words_curated.csv` — ~140k candidates (dictionary suspects, corpus validation is the real gate)

### Phase 2: Corpus Validation (Complete ✅)
- [x] Wikisource RO corpus — 12,921 docs, 14.3M tokens (historical baseline)
- [x] CulturaX RO corpus — 40.3M docs, 17.0B tokens (modern web)
- [x] Diachronic comparison: log₂(hist_ppm / modern_ppm) per word
- [x] Taxonomy enrichment: `dex_pos`, `dex_register`, `dex_domain`, `dex_etymology`
- [x] Shortlist generation: 16,203 words across 5 confidence tiers, split into `relevant` (2,815) and `curiosity` (13,388) seams

**Output**: `forgotten_words_diachronic.csv` (130k rows) → `forgotten_words_shortlist.csv` (23k rows)

### Phase 3: Enhanced Metadata
- [ ] Extract full definitions from DEX database
- [ ] Join Definition and DefinitionSimple tables
- [x] Identify archaic markers (înv., arh., reg., dial.) — `dex_register` column via Tag taxonomy
- [x] Extract etymology information — `dex_etymology` column (grecism, latinism, turcism…)
- [x] Add part-of-speech tagging — `dex_pos` column (substantiv neutru, adjectiv, verb…)
- [ ] Flag words with no definition body ("Fără definiție." entries like *nombrilist*)
- [ ] Parse first attestation dates
- [ ] Temporal analysis (when words fell out of use)
- [ ] Link to word families and cognates

### Phase 4: Lemmatization & Advanced NLP
- [ ] Integrate Romanian lemmatizer (spaCy-ro or nlp-cube)
- [ ] Match inflected forms to base words
- [ ] Improve recall (find "frumoaselor" when searching "frumos")
- [ ] Named entity recognition for better filtering
- [ ] Semantic clustering of forgotten words

### Phase 3: Web Validation (Next 🔍)
- [ ] DDG triage pass on shortlist (~17k words, no quota)
- [ ] Google CSE pass on high-confidence subset (100/day free tier)
- [ ] Cross-reference: corpus verdict vs web presence

### Phase 5: User Interface & Visualization
- [x] Exploratory UI for browsing the shortlist (filter by tier, POS, etymology, domain, verdict, marks)
- [x] Word detail view: DEX definition, corpus stats, dexonline.ro link
- [x] PHP thin-API port — deployable on shared hosting (`public/`, `tools/build_ui_db.py`)
- [x] localStorage bookmarks / notes / quick-tags (no server-side auth needed)
- [x] Forgotten / rare-in-use toggle — browse two word tiers in both Flask and PHP UIs
- [ ] REST API for programmatic access
- [ ] Interactive visualizations
  - Frequency decay curves (hist_ppm vs modern_ppm scatter)
  - Etymological breakdown of extinct words
  - Word cloud weighted by log_ratio

### Future Enhancements
- [ ] Revival potential scoring algorithm
- [ ] Compare with other Romance languages
- [ ] Historical corpus analysis (Project Gutenberg)
- [ ] Machine translation of forgotten word contexts
- [ ] Crowdsourced validation platform
- [ ] Word-of-the-day feature
- [ ] Educational tools and quizzes
- [ ] Create a reverse, browse news and r/romania and find new words, used more than 3? times that are not in dictionary -> alternative dictionary

### Further enhancements, marketing
- tools: convert texts to archaic form - less used words. with a coeficient of uniqueness (bigger number, harder words)
- filter out uninteresting words. Too domain specific: medicine, biology etc
- one word a day game? quizz, guess what it means?

## Known Issues & Limitations

1. ~~**No lemmatization**~~ — fixed 2026-08-08. `extract_inflected_forms.py` maps 2.27M surface forms to lemmas and `validate_diachronic.aggregate_by_family` rolls corpus counts up over paradigms.
2. **POS tag noise** — some words get wrong POS tags due to the ObjectTag join occasionally pulling tags from adjacent dictionary entries. Supplementary metadata only; doesn't affect core analysis.
3. **Sparse etymology -ism tags** — many words store "limba franceză" not "franțuzism" in DEX. Both are captured but the vocabulary is inconsistent across DEX editors.
4. **Thin historical corpus** — Wikisource is 14.3M tokens, so one occurrence is 0.07 ppm. The `hist_occ ≥ 3` / `hist_docs ≥ 2` floors make the signal honest but cannot create evidence: a word genuinely used in 1880 but absent from Wikisource still reads `absent`. Largest remaining source of error — see `docs/BACKLOG.md`.

## Next Steps

```bash
# Tune where the relevant seam cuts, then rebuild the app database
python make_shortlist.py --stats --min-score 88
python make_shortlist.py --min-score 88 && python tools/build_ui_db.py

# Serve it locally
cd public && php -S 127.0.0.1:8899
```

See [Activity History](docs/activity-history.md) and [Backlog](docs/BACKLOG.md) for the changelong and open items / roadmap.

## Contributing

See [CLAUDE.md](CLAUDE.md) for development guidelines and project context.

 