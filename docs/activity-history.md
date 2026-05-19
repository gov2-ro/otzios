# Activity History

Chronological log of meaningful work. Add entries under `## YYYY-MM-DD — Short Title`.

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
