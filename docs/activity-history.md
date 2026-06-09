# Activity History

Chronological log of meaningful work. Add entries under `## YYYY-MM-DD — Short Title`.

---

## 2026-06-09 — Statistics page with sliceable filters

Built a full statistics dashboard (`public/stats.php`) that mirrors the main word list's filter UI. Users can slice statistics by the same dimensions: tier, POS, register, domain, etymology, dict_count, definition status, and DEX frequency ceiling (rare tab).

- **Refactored filter building**: Extracted `build_word_filter()` helper in `_lib.php` — shared by both `search.php` and the new `stats.php`, eliminates duplication and maintenance risk.
- **`parse_multi()` + `split_pipe()` helpers**: Moved to `_lib.php`, handle multi-value checkbox arrays (tier[], pos[]) and pipe-delimited fields (etymology, register, domain, POS).
- **API endpoint (`api/stats.php`)**: Single SQL scan per word, PHP-side aggregation: counts by confidence_tier (GROUP BY), then counts by etymology/register/domain/POS (split pipes, frequency maps). Generates top-15 etymologies, top-10 domains, all registers, top-8 POS.
- **Stats panels (`api/_partials/stats_panels.php`)**: HTML-only bar charts, inline `width: X%` styling, no JS library. Shows summary strip (total, definition coverage %), then 5 cards: etymology (full-width 2-column), tier, POS, register, domain — all color-coded per verdict/category.
- **CSS**: New `.stats-*` classes, grid layout for panels, mobile collapse of 2-column etymology to 1 on narrow screens.
- **Filter form**: Reuses the same tier/POS checkboxes, register/domain/etymology/dict_min selects, dex_max (rare-only). Inline JS handles DEX-rare visibility, tax-select active highlight, and form reset re-dispatch.
- **Navigation**: "📊 statistici" link in status bar, back-link ("← cuvinte") from stats page.

No changes needed to existing `search.php` behavior — all filter logic is now centralized in `build_word_filter()`.

## 2026-06-09 — Filter dedup, dict_count filter, URL deep-linking

- **Removed verdict pills** (extinct / declining / historical / absent) — they duplicated the tier labels (corp. extinct / corp. declining / corp. historical) since `confidence_tier` is derived from `verdict`. Tier is more informative (adds `dex. absent` path) so it's the one to keep.
- **Added missing `dex_absent_highfreq` tier** — 3,848 words had no tier pill to filter them until now.
- **`dict_count` filter** — new "dicts: any / ≥3 / ≥6 / ≥10 / ≥15" select in filter row 3. Filters `dict_count >= N` in SQLite. Works as a quality gate: words attested in more dictionaries are more firmly established.
- **URL deep-linking** — `applyUrlToForm()` reads `?q=&tier=&sort=…` on page load and pre-selects filters before HTMX fires its initial request. `syncUrlFromForm()` updates the URL (via `history.replaceState`) on every HTMX search, so every filter state is bookmarkable and shareable. Default values are omitted from the URL to keep links clean.

## 2026-06-09 — Reversible DEX-rare filter on the rare tab (Phase 1)

The rare tab still showed everyday words (credit, ecran, universitate, ceapă…). Root cause: the `rare_in_use` gate has no rarity requirement — it admits any `zipf ∈ [3.0, 4.5)` word with an archaic register tag, and DEX register tags are per-*headword*, so `învechit` fires on a long-dead *sense* of a common word. 112 of the 113 rare words are DEX `rarity_category = "standard"` (96% have `dex_frequency ≥ 0.80`).

Phase 1 (reversible, no pipeline re-run): added a `dex_max` filter to the PHP UI, scoped to the rare tab. `public/api/search.php` applies `dex_frequency BETWEEN 0.01 AND <ceiling>` only when `word_tier = rare_in_use` (0.01 floor drops `frequency = 0` missing data). `public/index.php` adds a select (DEX: all / ≤0.60 / ≤0.50 / ≤0.30, default ≤0.60); `public/assets/app.js` shows it only on the rare tab. Default ≤0.60 collapses the rare tab to **1 word (`listat`)** — confirming the pool is ~entirely DEX-standard and that a useful rare tier needs re-sourcing (Phase 2: rarity-first gate in `validate_with_wordfreq.py`, drop the archaic requirement, lower zipf ceiling 4.5→3.5, drop English loanwords). See plan `rare-list-still-shows-lucky-mitten.md`.

## 2026-06-07 — Archive dead MySQL→SQLite scripts (backlog #3)

`extract_lexemes.py` is the only MySQL→SQLite path wired into the canonical pipeline. Moved the two abandoned alternatives — `mysql_to_sqlite.py` (silently swallows AUTOINCREMENT errors) and `convert_to_sqlite.sh` (mishandles multi-line MySQL directives) — into a new `archive/` directory with a `README.md` warning not to run/import them. Confirmed no script imports either (only self-references + docs). Updated the CLAUDE.md gotcha. `docs/scripts-guide.md` still lists `mysql_to_sqlite.py` as an "alternative" — flagged in BACKLOG for a separate docs pass.

## 2026-06-07 — De-pollute the `rare_in_use` tier (archaic register gate + dedup)

Addressed the bulk of the "rare_in_use tier is polluted by modern loanwords + proper nouns" bug in `validate_with_wordfreq.py` (pipeline options (a) + (d)).

- **(a) Archaic register gate.** Added `ARCHAIC_REGISTER_MARKERS` (`învechit`, `arhaizant`, `rar`, `ieșit din uz`) + `has_archaic_register()`. The `rare_in_use` gate previously admitted any word with a *non-empty* `dex_register` — including stylistic tags (`figurat`, `popular`, `familiar`, `livresc`) that everyday loanwords carry. It now requires an archaic/rare marker. New `--rare-register {archaic,any}` flag (default `archaic`; `any` = legacy). Effect on the current curated CSV: `rare_in_use` 582 → 113; `screening`/`meeting`/`house`/`jonathan`/`sioux`/`zulu`/`viking` removed.
- **(d) Dedup by `word_no_accent`.** New `--dedup` (default on) keeps the first row per normalized headword, collapsing POS duplicates (`house` s.n. + adj.). Dropped 10,133 duplicate rows on the current input; surfaced in the run summary.
- **Verification.** `has_archaic_register()` unit-checked; ran new vs `--rare-register any --no-dedup` (legacy) side by side to confirm the 582→113 delta; spot-checked that 14/15 backlog noise words are gone. Residual noise is now sense-level homograph mismatches (`cannabis`/`spray`/`court`/`hagi` tagged `învechit` on a non-modern sense) — caught today by the UI `hide_loanwords`/`hide_proper` toggles; options (b)/(c) intentionally remain reversible UI toggles.
- No `data/` artifacts regenerated (verified via /tmp outputs); takes effect on next `validate_with_wordfreq.py` run.

## 2026-06-07 — Flag "[Fără definiție.]" placeholder entries (backlog #17)

Closed the remaining gap in #17. The `has_definition` column already existed (in `forgotten_words_diachronic.csv` and the UI), and DEX headwords with no extractable definition already showed `has_definition=0` by being absent from `definitions.db`. The leak: dexonline's "[Fără definiție.]" placeholder rows (entry exists, only usage citations follow) counted as real definitions.

- **`validate_diachronic.py`** — added `is_placeholder_definition(text)`: placeholder when text is missing/blank or "[Fără definiț…" *leads* the string. `_load_definition_words()` now excludes those, so the CSV `has_definition` is accurate. Mid-text placeholders in multi-sense words (`perină`, `spectacul`) correctly still count.
- **`ui/app.py`** — definition load skips placeholder rows (matching inline check) so the `has_def` filter (`definition IS NULL`) and the panel text agree; placeholder words still appear in the list and link out to dexonline.
- **Scale / verification** — predicate unit-checked (None/blank/leading/embedded/normal); against the live `definitions.db` (70,472 rows) it flags exactly 7 placeholder-only words: `animaltecă`, `apastop`, `fibrinactiv`, `magnetodiaflux`, `narcorublă`, `perfluorbutilamină`, `relin`. Both modules import cleanly. No `data/` artifacts regenerated — takes effect on next `validate_diachronic.py` run / `ui.db` rebuild.

## 2026-06-07 — Centralize frequency thresholds in `constants.py` (backlog #5)

Resolved the long-standing three-way disagreement on frequency bins (CLAUDE.md gotcha + BACKLOG #5).

- **New `constants.py`** — single source of truth: `MIN_FREQUENCY` (0.01) and `MIN_FORM_LENGTH` (3) shared across stages; canonical rarity-bin edges `VERY_RARE_MAX` (0.30) / `RARE_MAX` (0.50) / `UNCOMMON_MAX` (0.60) plus a `rarity_category(freq)` helper; per-stage candidate ceilings `CURATED_FREQ_CEILING` (1.0) and the explicitly-marked legacy `ANALYZE_FREQ_THRESHOLD` (0.70) / `VALIDATION_FREQ_CEILING` (0.60).
- **`create_curated_list.py`** (canonical) — candidate WHERE clause now parameterized from constants; the two duplicated inline binning blocks (categorization + CSV write) both collapse to `rarity_category()`.
- **`analyze_forgotten_words.py`** / **`validate_forgotten_words.py`** (legacy) — import their floors/ceilings instead of hardcoding. Legacy display histogram bins left script-local (coupled to the 0.70 candidate threshold; documented as intentional in `constants.py`).
- **Verification** — `rarity_category()` matches the old inline logic at every boundary (0.0/0.01/0.29/0.30/0.49/0.50/0.59/0.60/0.99); all four modules import cleanly. No `data/` artifacts regenerated — behaviour is unchanged, so existing CSVs remain valid.

## 2026-05-28 — Richer detail panel + reversible UI filters for triage

Follow-up to the rare-tab diagnosis: rather than baking filters into the pipeline, surface all
per-word evidence in the UI and add reversible filter knobs so the data can be explored before
committing to any permanent filter.

- **New `extract_dict_sources.py`** — streams the DEX dump (mirrors `validate_diachronic.py::_load_dict_counts`), joining `Definition.sourceId → Source.shortName` to record the *names* of the dictionaries each headword appears in. Output `data/processed/dict_sources.db` (`dict_sources(word, sources, dict_count)`). Full run: 301,439 headwords, 113 sources (e.g. `meeting` → DEX '98|DLRLC|Scriban|Șăineanu; `criptare` → Neoficial).
- **`ui/app.py::load_words`** — added a `_enrich_words()` pass: wordfreq Zipf for `ro` and `en` (recomputed uniformly; also restores the rare tier's zipf, which the CSV load drops), a `proper_noun_like` flag recovered from `lexemes.db` casing (the CSVs are lowercased, so the old `word[0].isupper()` filter was dead), and `dict_sources` joined by normalized headword. New columns: `zipf_frequency`, `en_zipf`, `proper_noun_like`, `dict_sources`.
- **Detail panel (`partials/detail.html`)** — now shows zipf / en / dex band alongside hist/mod/sub/ratio, the dictionary-names list, web-validation signals (score/results/in-wild/provider/last-seen/top-url), and a proper-noun flag. The DEX-frequency superscript (the small number on each grid word = `dex_frequency × 100`) is now also rendered next to the word title in the panel.
- **Legend popup (`base.html`)** — an "ⓘ legend" footer link opens a glossary modal (modeled on the shortcuts overlay) explaining every number and tag: the superscript/DEX band, zipf, en, hist/mod/sub/ratio, dict-count + source short-names, web signals, verdicts, and common DEX register tags.
- **Four reversible filters** (`/search` + `base.html` row 4): zipf range, DEX-frequency range, hide-likely-loanwords (`en_zipf ≥ LOANWORD_EN_ZIPF`, default 4.0), exclude proper-noun-like. Server-side, applied only when present, preserved across pagination.

Verified end-to-end (curl + browser screenshot): `hide_loanwords` drops `meeting`/`house`, `hide_proper` drops `jonathan`, `zipf_max=3.0` narrows to sub-floor words; detail panel renders all signals. No `data/` artifacts regenerated. wordfreq import is optional (graceful degrade).

---

## 2026-05-28 — Diagnosed rare-tab pollution (no code changes)

Investigated why the UI "rare" tab (`?word_tier=rare_in_use`) shows non-rare words: English loanwords (`screening`, `meeting`, `house`, `short`, `golden`, `dolby`, `wild`, `trend`), variety/brand names (`jonathan`), and proper nouns (`sioux`, `zulu`, `hagi`, `viking`).

Root cause: the `rare_in_use` tier rests on two failing signals. (1) Low DEX `frequency` is editorial-coverage, not corpus frequency, so recent borrowings sit in the `0.01–1.0` candidate band (`create_curated_list.py:127-129`) while still being everyday words. (2) The register gate in `validate_with_wordfreq.py:151` admits a word on `zipf < 4.5 AND dex_register non-empty` — *any* tag — but of 582 rows in `rare_words_wordfreq.csv` only ~124 are `învechit`; the rest are stylistic tags (`figurat`, `popular`, `familiar`, `livresc`) that colloquial loanwords carry. Compounding: no loanword filter, a dead proper-noun filter (`create_curated_list.py:69-72` checks `word[0].isupper()` on lowercased data), homograph mismatches (`cannabis`/`listat`→`învechit`), and 28 duplicate rows.

Diagnose-only at the user's request; logged as a Bugs/Known-Issues entry in `docs/BACKLOG.md` (sharpens enhancement #12) with fix options for later.

---

## 2026-05-28 — Lemma dedup in shortlist (backlog #6)

Added simplemma-based inflected-form deduplication to `make_shortlist.py`. After the classification loop, each word is lemmatized via `simplemma.lemmatize(word, lang='ro')` and grouped by lemma. Groups with multiple shortlist entries keep one canonical representative (the word whose form equals the lemma, else the highest-tier/highest-dex_frequency entry); the rest are dropped. Added `--no-dedup` flag to opt out.

Result: 1,571 inflected forms collapsed, shortlist 26,788 → 25,217 words. Concrete improvements: `abecedare` dropped (→ `abecedar` kept); `murea` dropped (lemma `muri` not in shortlist, so it was alone in its group and correctly removed).

Known remaining gap: simplemma does not reduce Romanian verb-derived nouns or participial adjectives (`bleui`/`bleuire`/`bleuit` stay as three separate entries). Corpus-level lemmatization (so `buclele` counts toward `buclă`) remains outstanding.

Rebuilt `tools/build_ui_db.py`: 25,685 words in `ui.db`.

---

## 2026-05-28 — Data audit: corpus merge, Tier A guards, register filter cleanup

**Corpus merge:** Fresh CulturaX run from VPN contained only `culturax_ro` (122,463 words). Merged `wikisource_ro` (45,218 words) and `subtitle_ro` (29,733 words) from the previous complete DB into the new `corpus_frequencies.db`. All three corpora now present and correct.

**Tier A common-word guards (`make_shortlist.py`):** Tier A (`corpus_extinct`, `corpus_declining`, `corpus_historical_only`) now requires two additional conditions: `modern_ppm <= 5.0` (word is not still actively used in modern text) and `dex_frequency < 1.0` (not DEX core vocabulary). Without these guards, words like `lui` (2,750 ppm), `casă` (200 ppm), `dumnezeu` (562 ppm), `miel` (10 ppm) were passing because Wikisource (19th-century literary) simply uses these proportionally more than modern web text, triggering a "declining" verdict. 612 words removed from Tier A (993 by ppm, 133 by dex_frequency, some overlap). New `TIER_A_MODERN_PPM_MAX = 5.0` constant at module level. Legitimate archaic words in the 1–5 ppm range (e.g. `dară` 1.2 ppm, `sosi` 4.97 ppm `rar|învechit`) are kept.

**Register dropdown cleanup (`tools/build_ui_db.py`, `ui/app.py`):** Added `_REGISTER_USAGE_NOTES` exclusion set (39 tags) shared between both apps. DEX register tags that describe usage style (`figurat`, `popular`, `familiar`, `metaforic`, `în comparații / la comparativ`, `ironic`, `argou`, etc.) are excluded from the register filter dropdown. The `dex_register` column in the DB is unchanged — these tags are still available as metadata on each word, they just don't appear as filter options. Register dropdown reduced from 52 noisy values to 17 true archaic/regional markers: `învechit`, `regional`, `rar`, `livresc`, `Moldova`, `ieșit din uz`, `arhaizant`, `Țara Românească`, `Transilvania`, `Țările Române`, `dialectal`, `Bucovina`, `Muntenia`, `Banat`, `Maramureș`, `Oltenia`.

**Pipeline rebuilt:** `validate_diachronic.py` → `make_shortlist.py` → `tools/build_ui_db.py`. Shortlist: 26,788 words (was ~27,400 before guards). Verified: egregious common words gone, `oțios`/`tibișir`/`eleșteu` present, register dropdown clean.

**Remaining 260519 audit items (not tackled today):**
- Inflected/derived forms as separate entries (bleuit/bleuire/bleui, murea, abecedare) — requires lemmatization (backlog #6).
- Missing definitions for feminine forms and spelling variants (mofluzită, cfartal etc.) — separate investigation needed.
- `Maramureș` on `biodiversitate` — likely taxonomy artifact; re-check after pipeline rerun.

---

## 2026-05-27 — Regex fix, dead code removal, BACKLOG housekeeping

Fixed dead regex in `create_curated_list.py:80`: `r"^[a-z]+-[a-z]+'"` had a trailing apostrophe that caused the hyphenated-word filter to match zero words. Removed the apostrophe so compound/multi-word entries (chaise-longue, mai-mare, calea-valea, etc.) are now correctly excluded from the curated candidate list. Re-ran pipeline (`validate_diachronic.py` → `make_shortlist.py` → `build_ui_db.py`).

Deleted `explore_dex.py` (dead code: connects sqlite3 to a `.sql` file; content is narrative documentation, now redundant with `CLAUDE.md`).

Marked completed BACKLOG items: regex typo, #4 (explore_dex.py), #20 (OOB swap for stale overlay), #21 (dict_count).

---

## 2026-05-27 — Type-ahead word navigation; annotation overflow cap

**Type-ahead navigation:** Pressing any unbound printable character (when not focused on an input) accumulates in a 1.2s buffer and jumps to the first visible word whose text starts with the buffer (diacritic-insensitive: ț→t, ș→s, ă→a, â→a, î→i). Multi-character sequences narrow the match. Documented in the shortcuts modal as "a–z: jump to matching word".

**Annotation overflow cap:** Words with 4+ emoji annotations (quick tags + note + bookmark) now cap at 3 emoji + a muted "+N" superscript. Template refactored from string concatenation to a `_ov.items` list, sliced at [:3].

---

## 2026-05-27 — Definition hover tooltip in word grid

Added a lightweight hover tooltip to word chips in the grid. The `data-def` attribute was already populated (first 120 chars of definition) on each `.word-row`. A single floating `#def-tip` div is appended to `<body>` and shown/hidden via `mouseover`/`mouseout` delegation on `#word-list-container`. Positioned below the chip; flips above if within 120px of viewport bottom. No network requests. Tooltips also work after HTMX-loaded pages.

---

## 2026-05-27 — Garbled definitions fix, rar/regional/ieșit-din-uz taxonomy tags

**Garbled definitions fix:** Root cause: `_parse_values` in `extract_definitions.py` handled `\'` and `\\` but not `\n`/`\r`/`\t` — these appeared as literal `n` + surrounding dump indentation spaces (e.g. `"Acțiunea den       a ( se ) abaten         n       și rezultatul ei."`). Fix: complete escape table in the parser + `re.sub(r'\s+', ' ', ...)` whitespace normalization in `_clean`. Re-ran `extract_definitions.py` (50,678 headwords from DefinitionSimple) then `scrape_definitions.py --merge-only` (19,835 scraped rows on top). Garbled count in `definitions.db`: 3,152 → 0.

**New register tags — rar, regional, ieșit din uz:** Three semantically important DEX tags (ids 6, 17, 239) have `parentId=0` (root level) and were silently missed by `load_taxonomy()` which filtered only `parentId IN (1, 41, 42)`. Extended the SQL `WHERE` clause and `parent_to_family` map to include them and their children (Banat, Moldova, Transilvania, etc. as sub-tags of `regional`). Result in register vocab: `regional` 3,202 words, `rar` 2,463, `ieșit din uz` 95. All now available in the register filter dropdown. Re-ran full pipeline: `validate_diachronic.py` → `make_shortlist.py` → `build_ui_db.py`.

---

## 2026-05-27 — Definition scrape completion, dictionary coverage count (#21)

**Definition scrape completion:** Pass 3 scraped 21,110 words (started 26 May, finished overnight). Merged 19,157 ok rows into `definitions.db`. Rebuilt `ui.db` → 26,279 words now have definitions.

**Dictionary coverage count (`dict_count`):** New field counts how many distinct DEX source dictionaries contain a headword. Extracted from `Definition.sourceId` in the MySQL dump via a new `_load_dict_counts()` function in `validate_diachronic.py` (streams 125 INSERT lines, ~12s). Propagated through the full pipeline: `validate_diachronic.py` → `make_shortlist.py` → `build_ui_db.py` → `ui/app.py` (in-memory schema + INSERT) → `detail.html` (`dicts N` stat chip). Range: 0–47 dicts per word (e.g. `oțios` → 11, `arie` → 28). Rebuilt `ui.db` with new shortlist.

---

## 2026-05-23 — Corpus refresh: subtitle corpus, Wikisource re-run, CulturaX merge, subtitle signal in diachronic

**Definition scrape completion:** Ran two-pass scrape (`scrape_definitions.py --merge` then `--retry-not-found`). Pass 1: 1,810 new definitions from 1,839 unchecked words. Pass 2: 5 more recovered. Definition coverage: 98.5% for forgotten tier (was ~79%). Rebuilt `ui.db`.

**Subtitle corpus (`process_subtitles.py`):** New script streams `dex-database.sql` for `Subtitle` INSERT rows (13.2M pre-tokenised tokens from 966 Digi24 YouTube clips). Filters against `load_dex_words()`, writes to `corpus_frequencies.db` under `corpus_name='subtitle_ro'`. 29,733 unique DEX forms found. Runs in ~13s locally.

**Wikisource re-run:** Wiped stale `wikisource_ro` data and re-ran `process_wikisource.py` with the corrected `load_dex_words()` filter (141k lookup forms vs 16k before). Found 45,218 unique forms (up from 44,756 — small delta confirms new words are modern vocabulary absent from 19th-century literary text, as expected). Fixed cosmetic display bug: progress line printed `len(word_counts)+1` after flush had already cleared the dict; now captures count before flush.

**CulturaX re-run (VPS):** Re-ran `process_culturax.py` on VPS with corrected filter. Uploaded `lexemes.db` (91 MB); pulled updated `process_culturax.py` via git. Result: 122,463 unique words, 40.3M docs, completed. Downloaded `corpus_frequencies2.db`, merged only `culturax_ro` rows into local DB (preserving fresh wikisource + subtitle data), deleted temp file.

**Pipeline rebuilt:** `validate_diachronic.py` → `make_shortlist.py` → `build_ui_db.py`. Shortlist grew from 23,112 → 27,410 words (+4,300 with real CulturaX signal). `ui.db`: 27,829 words, 17.6 MB. `fost` correctly absent from results now.

**Subtitle signal in diachronic:** Added `subtitle_ppm`, `subtitle_occurrences`, `subtitle_documents` columns to `validate_diachronic.py` output, passed through `make_shortlist.py` and `build_ui_db.py`. 8,737 shortlist words have subtitle signal — identifies words forgotten in written text but surviving in broadcast Romanian.

---

## 2026-05-21 — Diacritic-insensitive search in Flask and PHP apps

Added `word_normalized` column (ț→t, ș→s, ţ→t, ş→s, ă→a, â→a, î→i) to the words table in both the Flask in-memory DB and the PHP on-disk DB. Searching "otios" now finds "oțios"; "stramosesc" finds "strămoșesc". Both the normal word-list search and the audit-mode search respect the normalized form. PHP app updated in `_lib.php` (`normalize_diacritics()`) and `public/api/search.php`. Flask app updated in `ui/app.py` (`_strip_diacritics()`, registered as a SQLite custom function). `tools/build_ui_db.py` updated to populate the column and add an index.

---

## 2026-05-21 — Audit pipeline: stratified sampling, labeling UI, report

Added a full data-quality audit workflow to measure shortlist precision and recall across strata.

**`audit_sample.py`** — draws a stratified random sample (default 100 words/stratum) from all 10 strata: included tiers (tier_a_extinct, tier_a_declining, tier_a_historical, tier_b_invechit, tier_c_absent_highfreq, rare_in_use) and excluded buckets (excl_pos, excl_absent_lowdex, excl_stable_emerging, excl_other). Sample stored in `data/research.db:audit_sample`. CLI: `--n`, `--seed`, `--reset`, `--strata`, `--stats`.

**`audit_report.py`** — aggregates `audit:*` tags from labeled words into a stratum × label markdown table (`docs/audit/YYYY-MM-DD-summary.md`) and per-cell word lists (`data/audit/<stratum>_<label>.txt`). Counts `keep`, `inflection`, `variant`, `loanword`, `dialect`, `jargon`, `no_def`, `other` for included tiers; `keep`/`correctly_out`/`no_def`/`other` for excluded buckets. Coverage table shows labeled/total per stratum.

**Flask audit mode** (`?audit=1`) — orange audit bar replaces the normal filter row with 10 stratum radio-pills (A·extinct, B·invechit, ✗·pos, etc.) each showing labeled/total progress. Selecting a stratum scopes the word list to that sample; unlabeled words sort first. Detail panel gains a row of one-key verdict buttons: K/I/V/L/D/J/M/O for included strata, K/X/M/O for excluded. Keyboard shortcuts fire via `htmx:configRequest` injection of `?audit=1` on every `/word/` request. After each label, auto-advance moves to the next unlabeled word and refreshes the stratum counter via `/audit/strata`. Words from excluded strata (not in the shortlist) are pulled from `forgotten_words_diachronic.csv` at startup so the detail panel doesn't 404. Audit tags are stored in `bookmarks.tags` as `audit:*` entries and are filtered out of the normal tag display.

---

## 2026-05-19 — Add Tier C to shortlist; fix rare list quality

Two pipeline fixes to address the 260519 Data Audit:

**Tier C — `dex_absent_highfreq`** added to `make_shortlist.py`. Captures words that are fully absent from all corpora (`hist_ppm=0`, `modern_ppm < 0.1`) but are well-documented in DEX (`dex_frequency ≥ 0.85`). These are the "most forgotten" words — DEX-canonical but never seen in digitised text. Threshold was initially set at 0.70 (too many inflected/derived forms: ~20k words), then tuned to 0.85 (~3,332 words). oțios (dex_frequency=0.85) is right at the boundary and now appears in the UI. New CLI args: `--absent-ppm-threshold` (default 0.1) and `--dex-freq-threshold` (default 0.85). Sort key shared with Tier B: by dex_frequency descending.

**Rare-in-use filter** tightened in `validate_with_wordfreq.py`: `rare_in_use` classification now requires non-empty `dex_register`. Words with Zipf 3.0–4.5 but no register tag (modern unmarked vocabulary like `neurologie`, `cowboy`, `manipulat`) fall through to `common` and are excluded from both output files. Rare list: 11,668 → 469 words.

Pipeline rebuilt: shortlist 19,780 → 23,112 forgotten words (Tier A: 16,786, Tier B: 2,994, Tier C: 3,332) + 469 rare-in-use. DB: 23,581 words total.

---

## 2026-05-19 — Add forgotten/rare-in-use toggle to both Flask and PHP apps

Added a segmented `uitate | rare` toggle to both UIs, backed by a new `word_tier` column in `ui.db`.

**`tools/build_ui_db.py`**: loads `forgotten_words_shortlist.csv` with `word_tier='forgotten'` and `rare_words_wordfreq.csv` with `word_tier='rare_in_use'`; adds `word_tier TEXT DEFAULT 'forgotten'` column and `idx_words_word_tier` index; DB grew to 28,447 words (19,780 forgotten + 8,667 rare at the time).

**`public/api/search.php`** and **`public/index.php`**: `word_tier` filter applied to every query (allowlisted: `forgotten`/`rare_in_use`); segmented radio toggle in Row 1 of the filter bar; initial status-bar count uses `WHERE word_tier='forgotten'`.

**`ui/app.py`**: same changes mirrored — `load_words()` accepts `rare_path`; `/search` validates and applies `word_tier`; in-memory schema includes `word_tier`.

---

## 2026-05-19 — Add rare-in-use word tier to wordfreq validation

Extended `validate_with_wordfreq.py` with a three-tier Zipf classification alongside the existing binary forgotten/not-forgotten output.

**New `tier` column:** `forgotten` (zipf < 3.0) / `rare_in_use` (3.0 ≤ zipf < 4.5) / `common` (≥ 4.5). The existing `is_forgotten` bool is preserved for backward compatibility with `search_wild.py` and `build_ui_db.py`.

**New CLI args:** `--upper-threshold` (default 4.5) and `--output-rare` (default `data/processed/rare_words_wordfreq.csv`). In default mode the script produces two output files — the existing forgotten-words CSV (127,886 rows) and a new rare-in-use CSV (11,668 rows). `--keep-all` writes all tiers to the main output as before.

Calibration: `oțios` itself has zero corpus signal (zipf=0.000) so it lands in `forgotten`, not `rare_in_use`. The rare-in-use tier catches words like `bucle` (zipf 3.42) that do still appear in Romanian text but very infrequently.

BACKLOG item (line 208) marked resolved on the pipeline side; UI global switch (browse forgotten vs rare-in-use list) remains open.

---

## 2026-05-19 — Data audit: missing definitions root cause + scraper fallbacks

Investigated the Data Audit backlog item: 4,065 shortlist words (20.6%) had no definition in `ui.db` despite dexonline.ro having entries for them.

**Root causes found:**
- **2,703 words** never attempted — scraper was run with `--limit` or interrupted before reaching them. All tested examples (`mofluzită`, `ospătător`, `aeresc`, `cfartal`, `prijuni` etc.) parse fine with the existing synthesis selector; they just need a scrape run.
- **1,370 words stuck as `not_found`** — scraper ran but found no synthesis. Sampling showed ~95% have no `.tree-body` in `#tab_2` (dexonline hasn't curated a synthesis for them yet), while ~5% are inflected/derived forms where dexonline explicitly says "Nu avem definiții" for that form.
- **Side issue**: 3,530 words were flagged `has_definition=0` in the shortlist but had actual definitions in `definitions.db` — the flag was stale.

**Fixes in `scrape_definitions.py`:**
- `parse_tab0_defs(html, word)` — fallback for the ~95% case. Scans `#tab_0 .defWrapper` entries, matches headwords case-insensitively (handling per-character span markup and stress-accent diacritics like `márgă` → `margă`), returns first 3 matching raw-dictionary definitions.
- `parse_lemma_fallback(word, defs_db)` — fallback for inflected forms. Lemmatizes via `simplemma('ro')` and looks up the base form's definition in `definitions.db`. Prefixes the result with `[formă a lui {lemma}]`.
- `--retry-not-found` flag — re-queues `not_found` checkpoint entries without wiping the full checkpoint.

**Fix in `tools/build_ui_db.py`:** after merging definitions, reconciles `has_definition` to reflect actual definition presence.

**Next:** run `python scrape_definitions.py --delay 2.0 --merge` (pass 1, 2,703 words) then `python scrape_definitions.py --retry-not-found --delay 2.0 --merge` (pass 2, 1,370 words), then rebuild `ui.db`.

---

## 2026-05-19 — PHP thin-API port for shared hosting

Ported the Flask research UI to a PHP + SQLite stack deployable on any shared host. Flask app is kept intact for local pipeline work.

- **`tools/build_ui_db.py`** — one-shot build script that merges `forgotten_words_shortlist.csv` + `diachronic_shortlist_web_validated.csv` + `definitions.db` into `public/data/ui.db` (~11 MB). Adds a `vocab` table for dropdown options and four search indexes.
- **`public/api/search.php`** — port of Flask `/search`. Marks filter is now client-driven: JS sends `marked_words` (comma list from localStorage) so the server does `WHERE word IN (…)` / `NOT IN (…)` without touching any server-side user state.
- **`public/api/word.php`**, **`_lib.php`**, **`_partials/`** — word detail endpoint, shared PDO helpers, PHP equivalents of the three Jinja partials.
- **`public/assets/app.js`** — localStorage research store (`otios.research` key); `hydrateRows` / `hydrateDetail` run on `htmx:afterSwap`; bookmark/tag/note handlers replace the five dropped HTMX POST routes; keyboard shortcuts retargeted at localStorage; `htmx:configRequest` hook injects `marked_words` before search requests.
- **`public/assets/app.css`** — extracted verbatim from `base.html`.
- **`public/index.php`** — page chrome with server-rendered vocab dropdowns; bookmark count filled by JS.
- **`public/metodologie.html`** — static copy.
- **`tools/export_research_to_json.py`** — dumps `data/research.db` to the localStorage JSON shape for one-time console import.
- Verified locally: word grid, search, live filter, detail panel, bookmark/tag/note (localStorage), marks filter, infinite scroll, zero console errors.

---

## 2026-05-19 — Marks filter + annotation overlay + UI refinements

Unified annotation filtering and word-chip decoration in the research UI.

- **`marks` dropdown.** Replaced the `show_removed` pill + `bookmarked` checkbox with a single `<select name="marks">`. Options: `all words` (default), `unmarked only`, `marked only`, `☆ bookmarked`, `has note`, and one entry per quick-tag. Backend: new `_is_marked()` helper; flat filter chain handles each variant. Default changed from `unmarked` → `all`.
- **Emoji overlay on word chips.** Each chip now shows a compact emoji badge (`ann-overlay`) assembled by a Jinja2 namespace accumulator: per-tag emoji from `QUICK_TAG_EMOJIS`, `📝` if has note, `⭐` if bookmarked. `w.tags` list (from `bmap`) replaces the old `has_tags` bool.
- **Suppress active-filter emoji.** In `bookmarked` mode the `⭐` is hidden on every chip (it's redundant — the filter already guarantees they're all bookmarked). Same for `📝` in `noted` mode and the relevant tag emoji in `tag:X` mode. Implemented via `suppress_emoji` template var and `| default('')` guard.
- **`.flabel` inverted.** Filter labels now render as dark pills (`color: var(--bg); background: var(--text-2)`) so they read as labels, not body text.
- **Metodologie footer link.** Status bar now includes an `<a href="/metodologie">` link. Template moved from `ui/metodologie.html` → `ui/templates/metodologie.html` (Flask template resolution fix).
- **BACKLOG.** Added #19 (overlay overflow for 4+ emoji), #20 (stale overlay after in-panel mutations — needs htmx OOB swap).

---

## 2026-05-18 — UI polish pass v4 (typography + verdict palette + interaction states)

Second, deeper UI revision after the morning's fine-tuning pass. Brainstormed direction with the visual-companion server, picked **Tool** over Publication. Spec at `docs/superpowers/specs/2026-05-18-ui-polish-pass-design.md`.

- **Typography.** Inter Tight → Mona Sans (variable). Word weight 700→600, size 19→18px, tracking `-0.02em`→`-0.005em` so Romanian diacritics (ț, ș, ă) breathe. Lora kept as italic accent on the filter label + placeholder. JetBrains Mono kept.
- **Color tokens.** Warm off-white ground (`--bg #fcfbf7`, `--surface #fdfcf9`, `--border #ece6d6`). Verdict palette flipped from "four equal-saturation colors" to **one hero, three muted**: `--v-ext` cleaner red `#b91c1c`, the other three become charcoal-with-hue (`--v-dec #524035`, `--v-hist #3d4763`, `--v-abs #4b3d5a`). Extinct now reads first; the eye explores from there.
- **Density.** Grid `column-gap: 9px; row-gap: 9px; padding: 11px 13px`; word-row padding `1px 5px 2px`. Denser than the morning pass but still readable.
- **Hover.** Cool blue tint `rgba(214,230,255,0.9)` + 1px inset border, hugs the word.
- **Selected.** `transform: scale(1.06)` lift, dark-charcoal 90%-opacity bg, subtle two-layer shadow, `z-index: 5`. Neighbors don't reflow — one unambiguous "this is selected" signal replaces the old verdict-tinted bg + outsized shadow combo.
- **Critical CSS fix.** Grid items default to `justify-self: stretch`; added `justify-self: start` on `.word-row` so hover/selected boxes hug the word's width instead of stretching to the cell.
- **Stripped chrome.** Removed `body::before` top accent stripe (advertised the palette we're toning down). Status bar's 8-kbd inline legend collapsed to `<kbd>?</kbd> shortcuts` (modal already exists).

Verified in browser: Mona Sans 600/18px on warm ground, `transform: matrix(1.06,…)` + `background: rgba(26,24,18,0.9)` on selected, hover box ≈ word width.

## 2026-05-18 — UI word-grid fine-tuning

Polished `ui/templates/base.html` + `ui/templates/partials/word_row.html` to fix visual noise in the word list. No structural changes — same routes, markup shape, keyboard shortcuts.

- **Grid breathing room.** `gap: 3px` → `column-gap: 8px; row-gap: 12px`. Outer padding bumped to 14/16. The tight 3px row-gap was the root structural cause of the `înv` overlap.
- **învechit marker.** Replaced the absolute-positioned `<span class="chip-meta inv">înv</span>` (which sat at `bottom: 0; left: 7px` and bled into the row below) with a red dotted `text-decoration` underline on `.word-text` itself. Word row gets `class="inv"` and `title="învechit"` when applicable; the chip-meta span and its CSS are gone. Bookmark+învechit conflict: bookmark amber wins, logged in BACKLOG.
- **Superscript freq.** Switched from `vertical-align: super` (oddly tall, competed with the word) to `vertical-align: baseline; position: relative; top: -0.55em` at 10px/600 weight/0.7 opacity. Reads as quiet metadata now.
- **Hover.** Tan `#f0ece5` → cool `var(--accent-bg)` `#eff6ff` so hover doesn't visually merge with the warm body bg.
- **Bookmarks.** Dropped the trailing `★` glyph; the amber underline alone is enough indicator.
- **Wide-word threshold.** `length >= 12` → `length >= 11` in `word_row.html` so 11-char words like `bogasieresc`, `panevghenie` get a 2-col span and stop crowding their neighbors.

Variant chosen via a temporary `/demo/marker` route that rendered six marker treatments side-by-side over the same word sample; demo route + `marker_demo.html` template removed after selection. Logged 4 follow-ups in BACKLOG (verdict palette, bookmark+învechit stacking, mobile breakpoints, extract CSS to static file).

## 2026-05-18 — Fix taxonomy join (load_taxonomy, fetch_all_tags)

`ObjectTag.objectId` where `objectType=3` holds Meaning IDs (max ~503k), but both `load_taxonomy()` in `validate_diachronic.py` and `fetch_all_tags()` in `create_curated_list.py` were joining on `el.entryId` (max ~339k) — different ID spaces, producing random tag assignments. Fixed by:

1. Updating `extract_taxonomy.py` to also extract `TreeEntry(id, treeId, entryId)` and `MeaningTree(meaning_id, tree_id)` from the dump. `Meaning` rows contain a `longtext` `internalRep` field that breaks `parse_mysql_insert`'s `[^)]+` regex, so a dedicated `_MEANING_PATTERN` regex extracts only the two needed integer columns. Re-ran against the full dump: 240,023 TreeEntry rows + 454,993 MeaningTree rows.

2. Rewiring both join sites to use `Lexeme → EntryLexeme → TreeEntry → MeaningTree → ObjectTag(objectType=3) → Tag`.

Verified: `pretutindeni` (no tags — correct), `antipapă` (francesa etymology — correct), `isihie` (`învechit` register + neogreacă etymology — correct). Previous wrong results: `pretutindeni→botanică`, `antipapă→medicină`, `aist→medicină`.

Next step: re-run `validate_diachronic.py` to regenerate `forgotten_words_diachronic.csv` with accurate taxonomy columns.

---

## 2026-05-17 — DEX dump DefinitionSimple gap confirmed + backlog entry

Investigated why `scrape_definitions.py` is needed despite having the full DEX MySQL dump. Verified against both dumps: `DefinitionSimple` contains exactly **61,041 rows** in both old (Oct 2025, 1.2 GB) and new (May 2026, 1.5 GB) dumps, while `EntryDefinition` references **1,379,043** definition IDs — 94.8% are dangling references with no corresponding record. The gap is unchanged between dump versions, confirming this is a structural omission in the public export, not a regression. Added backlog entry (#Upstream) to report the issue to dexonline developers with counts and workaround context.

---

## 2026-05-17 — New DEX dump intake + domain tag root-cause investigation

**Investigated domain filter bug**: user reported that filtering by domain = "medicină" showed words with no medicina association in the detail panel. Two issues found:

1. **Missing UI chip** (fixed in `detail.html`): `dex_domain` chips were never rendered in the footer detail panel — `dex_pos`, `dex_register`, `dex_etymology` were all present but `dex_domain` was omitted. One-line fix.

2. **`load_taxonomy()` join is fundamentally wrong** (tracked in backlog): confirmed via data archaeology that `ObjectTag.objectId` where `objectType=3` holds **Meaning IDs** (max ~503k in new dump), not Entry IDs (max ~339k). The existing join `ot.objectId = el.entryId` maps two different ID spaces together, producing random domain/register/etymology assignments. Evidence: `pretutindeni` (adverb "everywhere") → `botanică`; `antipapă` (antipope) → `medicină`; `aist` (dialectal "this") → `medicină`. Fix requires extracting `TreeEntry` + `Meaning(id, treeId)` tables and rewriting the join chain to `Lexeme → EntryLexeme → TreeEntry → Meaning → ObjectTag(objectType=3)`. Tracked in backlog with full context.

**New DEX dump intake**: new dump (`dex-database.sql`, 1.65 GB) replaces old one (renamed `dex-database-1.sql`, 1.27 GB). Key differences: mostly data growth (~1–4% per table), one new index on `Lexeme.pronunciations`, four new tables (`Subtitle`, `VideoClip`, `OCR_stats`, `student`). Notable: `Subtitle` has 13 M pre-tokenised Romanian word tokens from 966 YouTube clips (Digi24 news) — potential spoken-register corpus. Re-ran `extract_lexemes.py` and `extract_taxonomy.py` against new dump; `lexemes.db` now has 317,688 Lexeme rows and 496k ObjectTag rows. `validate_diachronic.py` not re-run (waiting for taxonomy join fix).

**extract_lexemes.py hardening**: added `--sql/--csv/--db` argparse args (defaulting to full dump path); made Lexeme table drop+recreate on re-run for idempotency; added skip logic for 7 malformed rows where apostrophes in the `form` field break CSV column count.

---

## 2026-05-17 — Definition extraction fix + dexonline.ro scraping pipeline

**Fixed definition misalignment** (commit 8113dbf): `extract_definitions.py` was joining through Entry tables to pair Lexeme→Definition, but Entry groups multiple related words, so rank-1 definitions were paired with wrong lexemes (e.g. `abate` getting the `abatize` definition). Root cause: misunderstood schema. `DefinitionSimple.lexicon` column *is* the headword, not a dictionary identifier. Rewrote to read `DefinitionSimple.lexicon` directly as the headword key, eliminating all join ambiguity. Coverage jumped from 26% to 83,609 definitions.

**Built scrape_definitions.py** (commit 4519a7a): New script to fill the remaining ~12,778 shortlist words missing from the DEX dump. Mirrors `search_wild.py` pattern:
- Inputs: `forgotten_words_shortlist.csv`, `definitions.db` (to identify missing words)
- Output: `scraped_definitions.csv` checkpoint (word, definition, source_url, scraped_at, status ∈ {ok, not_found, error})
- HTTP: BeautifulSoup extracts synthesis block from `https://dexonline.ro/definitie/{word}`, 3s/request delay
- Resume: reads existing checkpoint, skips already-processed words
- Merge: `--merge` flag upserts ok rows into `definitions.db` for immediate UI availability
- Flags: `--dry-run`, `--limit N`, `--delay SECONDS`, `--merge`, `--merge-only`
- Safe interrupts: each row flushed immediately, Ctrl+C preserves checkpoint

**Verification**: 6-word test run (commit 4519a7a) confirms scraper finds definitions, parses HTML correctly, and appends to checkpoint CSV properly.

**Started full run**: `python scrape_definitions.py --delay 3.0 --merge` to complete remaining ~12,778 definitions (expected 5–7 hours).

---

## 2026-05-16 — Rich UI redesign: tag filters, chip sidebar, light theme

Complete UI overhaul in three passes:

**Pass 1 — Granular tag filters + wider sidebar**: replaced all four `<select>` dropdowns with
always-visible pill tags (checkboxes). Filter bar now has 3 rows: search/utilities, verdict+tier,
register+domain+etymology. `app.py` gained `_distinct_split()` for frequency-ordered tag values,
multi-select `getlist()` for verdict/tier (OR within group), and `LIKE`-based filtering for
pipe-separated columns. Sidebar widened to 50%, word list changed to `flex-wrap` chip layout.
`PAGE_SIZE` raised from 50 to 150.

**Pass 2 — Domain-tagged words in shortlist**: `make_shortlist.py` previously excluded all
`dex_domain`-tagged words (technical jargon heuristic). Removed that exclusion — 514 domain-tagged
words now appear in the shortlist; UI filter dropdowns allow excluding them post-hoc.

**Pass 3 — Light theme**: Switched from dark (#1a1a1a) to warm parchment light theme. Typography:
`Lora` serif for headings/labels/definitions; `JetBrains Mono` for word chips and data. Verdict
colors adapted to light (burgundy extinct, amber declining, navy historical, violet absent) with
pill active states, chip left-border tints, selected chip verdict-background highlights. Status bar
shows keyboard shortcuts as inline `<kbd>` elements. `detail.html` updated with verdict badge
classes and inline tag pills for register/domain/etymology values.

**Pass 4 — Intersection filtering + POS + richer chips**: Switched all filter inputs from
checkboxes (OR-within-group) to radios (single-select-per-group, AND-across-groups). Click an
active pill again to deselect — JS captures the pre-click state on the label's `mousedown`
(inputs are `display:none` so don't see the mousedown themselves) and clears + fires a form-level
`change` so HTMX requests fresh results. Added a POS filter row with 8 abbreviated linguistic
categories (`s.f.`, `s.n.`, `s.m.`, `adj.`, `vb.`, `adv.`, `part.`, `interj.`) using LIKE matching
against the pipe-padded `dex_pos` column. Default sort changed from `word ASC` to
`COALESCE(modern_ppm, -1) ASC` — rarest-first ordering, with corpus-absent words at the top.
Word chips now surface more metadata inline: `dex_frequency` as a tabular-nums secondary number,
and a red italic `înv` marker for words tagged `învechit`.

## 2026-05-16 — Tag enrichment in curated list (backlog #16)

Investigated how `data-bs-content` abbreviation popovers on dexonline.ro map to the dump:
values come from `Abbreviation.internalRep` via `#abbrev#` markup in `Definition.internalRep`.
Separately, `Tag`/`ObjectTag`/`EntryLexeme` were already present in `lexemes.db` but unused.

Added `fetch_all_tags()` to `create_curated_list.py` — bulk-fetches taxonomy tags via two join
paths (objectType=2 direct, objectType=3 via entry) and writes three new columns to
`forgotten_words_curated.csv`: `dex_register`, `dex_domain`, `dex_etymology`. Coverage:
7,642 register tags, 3,405 domain tags, 35,120 etymology tags across 140,308 curated words.
Columns flow through `validate_with_wordfreq.py` automatically. Marked #16 done;
added #20 (metadata navigator with statistics view and CLI browse commands).

## 2026-05-15 — UI enhancements: definitions, sort by scarcity, shortcuts popup

Built three additive features on top of the Flask+HTMX research UI:

- **Word definitions** — `extract_definitions.py` streams the 1.2 GB DEX MySQL dump, joins Lexeme → EntryLexeme → EntryDefinition → DefinitionSimple to map every inflected form (not just headwords) to its entry's primary definition, and writes `data/processed/definitions.db`. `load_words()` in `ui/app.py` now loads definitions at startup. The detail panel shows a DEX block with the definition text and a link to dexonline.ro.
- **Sort by scarcity** — `/search` accepts a `sort` param (`declined`, `rare`, `dex_freq`) resolved through a safe allowlist dict (`SORT_OPTIONS`) so no user string is ever interpolated into SQL. A sort `<select>` in the filter bar uses the same HTMX pattern as the existing verdict/tier dropdowns.
- **Shortcuts popup** — pressing `?` opens a modal overlay listing all keyboard shortcuts; Esc or click-outside closes it.

Initial extraction hit only 26% coverage (DefinitionSimple.lexicon stores headwords only). Rewrote to join through EntryLexeme — coverage jumped to 83,609 definitions across 315,279 lexemes streamed.

---

## 2026-05-15 — Research UI: Flask+HTMX word explorer

Built a keyboard-driven local web app (`ui/app.py`) for exploring the forgotten-words shortlist:

- Two-column layout: word list (left) + detail panel (right), no page reloads
- Search with 200ms debounce, verdict/tier/bookmarked filters, pagination (50/page)
- Word detail: metadata table, corpus scores, web-validation results, bookmark toggle, notes, tag pills
- Bookmarks/notes/tags persisted to `data/research.db` (SQLite, survives restarts)
- Keyboard shortcuts: `/` focus search, `j`/`k` navigate, `b` bookmark, `n` note, `gg`/`G` jump
- Full test suite (`tests/test_ui.py`) covering all routes and HTMX fragment responses

Stack: Flask 3.0.3, HTMX 2.0.4, Jinja2, SQLite (in-memory words + file-backed bookmarks).

---

## 2026-05-15 — DEX taxonomy enrichment: extract_taxonomy.py + diachronic CSV new columns

Confirmed CulturaX run completed cleanly (40.3M docs / 17.0B tokens / 120,345 unique words, duration 15m 10s). `forgotten_words_diachronic.csv` needed a re-run since it was generated before CulturaX finished; `validate_diachronic.py` now also emits four new taxonomy columns.

**`extract_taxonomy.py`** (new script): parses the DEX MySQL dump for `Tag`, `ObjectTag`, and `EntryLexeme` tables and loads them into `lexemes.db` with indexes. The `Tag` table contains ~460 hierarchical tags organised into families: register (parentId=42: `învechit`, popular, dialectal, livresc…), domain (parentId=41: muzică, medicină, chimie, drept…), etymology (parentId=1: grecism, latinism, anglicism, turcism, slavonism…), and POS (isPos=1: substantiv feminin, substantiv neutru, adjectiv, verb…). `ObjectTag` links these to dictionary entries via `EntryLexeme`. On the sample dump: 410 Tag rows, 47k ObjectTag rows, 315k EntryLexeme rows.

**`validate_diachronic.py`**: added `load_taxonomy(lexemes_db)` function that joins `Lexeme → EntryLexeme → ObjectTag → Tag` and returns per-word tag sets. Graceful fallback (warning + empty strings) if taxonomy tables absent. Four new columns in `forgotten_words_diachronic.csv`: `dex_pos`, `dex_register`, `dex_domain`, `dex_etymology` (pipe-delimited for multi-value). On sample dump: 22,129 words with any taxonomy tag; highlights include `bolboacă` (verdict=extinct, dex_register=învechit) — direct DEX editorial confirmation cross-validated by corpus signal.

Backlog additions: #16 (taxonomy enrichment — now implemented), #17 (flag words with no definition body, e.g. *nombrilist* shows "[Fără definiție.]"), #18 (extract per-document temporal/domain metadata from corpora for "when did this word fall out of use" signal).

Next step on VPS: run `python extract_taxonomy.py --sql data/dictionaries/dex-database.sql` against the full 1.2GB dump (~990k ObjectTag rows) then re-run `validate_diachronic.py`.

## 2026-05-14 — Handled transient network errors in process_culturax.py

HuggingFace Hub CDN occasionally drops HTTP connections mid-stream while reading parquet row groups, raising `httpx.RemoteProtocolError`. This was uncaught, crashing the script with a noisy traceback and losing up to COMMIT_EVERY-1 (≤ 4,999) in-flight doc counts. Fixed by wrapping `pf.read_row_group()` in a try/except that flushes the in-memory buffer, saves checkpoint at the exact current row, prints a clean one-line warning, and returns a shutdown signal so `main()` exits with code 1 and the restart loop picks it up. README updated with a readable interactive loop form alongside the existing nohup one-liner.

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
