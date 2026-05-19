# Plan: metodologie.html for Oțios

## Context

The Oțios project has a Flask+HTMX word-explorer UI but no publicly readable methodology page. The user wants a standalone static HTML page — modelled structurally on an existing metodologie.html from another project (localhost:8081, "Cum ne numim străzile") — that explains the reasoning, pipeline, and project timeline for Oțios. Content comes from README.md, docs/activity-history.md, and git history. Design must mirror the existing Oțios design tokens, not the example's IBM Plex / dark-navy palette.

---

## Output file

**`ui/metodologie.html`** — standalone static HTML, no Flask dependency, can be opened directly in the browser or served as a static file.

---

## Design tokens (from `ui/templates/base.html`)

```css
--bg:        #ffffff / #fafaf8 (warm)
--surface:   #ffffff
--border:    #e6e2da
--text:      #18150f
--text-2:    #5c5550
--text-3:    #9c9590
--accent:    #1a56db
--v-ext:     #9a1313   /* extinct  — burgundy */
--v-dec:     #7a3208   /* declining — amber   */
--v-hist:    #15348f   /* historical — navy   */
--v-abs:     #581cb6   /* absent — violet     */
--sans:  'Inter Tight'
--serif: 'Lora'
--mono:  'JetBrains Mono'
```

Hero "dark band": use `#18150f` (--text) as background with warm off-white text. Gold accent: use `#c8a84b` (derive from verdict amber) for section numbers and stat labels.

---

## Page structure

### Nav bar
- Brand: `Oțios` (links to `/`)
- Links: `Cuvinte` → `/`, `Metodologie` → `metodologie.html` (current, gold underline)
- Top 3px gradient stripe — same as base.html's `body::before` verdict palette

### Hero (dark band, `#18150f` bg, white text)
- Eyebrow: `Metodologie · cum funcționează`
- H1: `De la dicționar la cuvinte uitate`
- Sub: project description (1–2 sentences)
- Stats row (4 items):
  - `315.247` — lexeme în DEX
  - `140.308` — candidați după Faza 1
  - `16.879` — pe scurtlistă (4 niveluri)
  - `17 miliarde` — tokens corpus modern (CulturaX)

### TOC (on-page, 2-column grid)
01 De ce acest proiect  
02 Sursa datelor  
03 Faza 1 — Analiza dicționarului  
04 Faza 2 — Validare diacronică  
05 Scurtlista  
06 Taxonomie și metadate  
07 Interfața de cercetare  
08 Validare web  
09 Limite și capcane  
10 Cronologie  
11 Cod și date  

### Article sections (max-width 760px, centered)

Each `<section>` has: `<h2><span class="num">01</span> Title</h2>`

**01 De ce acest proiect**  
Linguistic dark matter concept. Words that exist in dictionaries but have fallen out of all modern usage. Named after the word `oțios` itself — DEX frequency 0.85 (canonical) yet totally absent from both corpora.

**02 Sursa datelor**  
DEX Online MySQL dump (1.65 GB). The `Lexeme` table: 315,247 entries with a `frequency` field (0.0–1.0, lower = rarer in dictionary definitions, NOT corpus frequency — common gotcha). `frequency = 0` means missing data, not "rarest". Also covers the `Tag`/`ObjectTag` taxonomy tables and `DefinitionSimple`.

**03 Faza 1 — Analiza dicționarului**  
Pipeline: `extract_lexemes.py` → `lexemes.db` (315k rows) → `create_curated_list.py` → `forgotten_words_curated.csv` (140k candidates). Filters: excludes proper nouns, enforces word-class markers, applies rarity bins (`very_rare` < 0.30, `rare` 0.30–0.50, `uncommon` 0.50–0.60, `standard` 0.60–1.0). Key decision: cutoff raised to < 1.0 after `oțios` (freq=0.85) was excluded by the original < 0.60 ceiling.

**04 Faza 2 — Validare diacronică**  
Two corpora: Wikisource RO (14.3M tokens, historical literary baseline) vs CulturaX RO (17B tokens, modern web). Log ratio: `log₂((hist_ppm + 0.1) / (modern_ppm + 0.1))`. Verdicts table: extinct / declining / historical_only / stable / modern_only / emerging / absent. Include a callout about the CulturaX cycling bug (ds.skip() in datasets v4.8.5) and the fix (per-parquet checkpointing with pyarrow + HfFileSystem).

**05 Scurtlista**  
`make_shortlist.py` filters 130k diachronic rows → 16,879. Four confidence tiers:
| Tier | Criteriu | Count |
|------|---------|-------|
| corpus_extinct | verdict=extinct, hist_ppm > 0 | ~1,137 |
| corpus_declining | verdict=declining | ~5,668 |
| corpus_historical_only | verdict=historical_only | ~8,793 |
| dex_invechit_absent | verdict=absent + dex_register=învechit | ~1,281 |

Tier B = "materie întunecată": cuvinte cunoscute ca arhaice de editorii DEX, inexistente în orice corpus digitizat.

**06 Taxonomie și metadate**  
`extract_taxonomy.py` — parses Tag / ObjectTag / EntryLexeme / TreeEntry / MeaningTree from dump. Correct join chain: `Lexeme → EntryLexeme → TreeEntry → MeaningTree → ObjectTag(objectType=3) → Tag`. (objectType=3 links to Meaning IDs, not Entry IDs — a subtle but critical distinction fixed 2026-05-18). Four tag families: register (învechit, popular, dialectal), domain (muzică, medicină, chimie), etymology (grecism, latinism, anglicism), POS. Definitions: `DefinitionSimple` covers ~4.6k shortlist words; `scrape_definitions.py` fills remaining ~12.8k via dexonline.ro.

**07 Interfața de cercetare**  
Flask+HTMX local web app (`ui/app.py`). Two-zone layout: chip word grid + compact footer drawer. Filter bar with verdict/tier/POS/register/domain/etymology pills and selects. Keyboard navigation (j/k/h/l, /, b, n, o). Bookmarks and notes persisted to `data/research.db`. Hover info box. 250 words/page.

**08 Validare web**  
`search_wild.py` — pluggable provider interface. DDG (no API key, noisy on rare archaic words) vs Google CSE (100/day free tier, cleaner). `web_score` buckets differ by provider. Output: `forgotten_words_web_validated.csv` with `total_results`, `in_wild`, `web_score`, `top_url`, `last_seen_approx`.

**09 Limite și capcane**  
- No lemmatization: `buclele` doesn't match `bucle`. `absent` verdict conflates "truly unused" with "only appears in inflected forms".
- `frequency = 0` is missing data, not "rarest".
- `absent` verdict covers 83k words — large ambiguous pool until lemmatization is added.
- POS tag noise: ObjectTag join can pull tags from adjacent dictionary entries.
- Etymology vocab inconsistent: "limba franceză" vs "franțuzism" both appear.

**10 Cronologie** (timeline component, styled with `::before` spine + gold dot nodes)

Milestones (chronological, distilled from activity-history.md):
- `2025-10-26` — Inițializare proiect. Commit inițial, repo gol.
- `2025-10-27` — **Faza 1 completă.** Pipeline DEX → 1,884 candidați inițiali (prag frecvență < 0.60).
- `2025-10-27` — Faza 2 legacy: corpus Wikipedia, bug P0 (candidate-set mismatch).
- `2026-04-27` — Critică metodologică: `conceptual-roadmap.md`, `corpus-options.md`. Pivotare spre abordare diacronică.
- `2026-04-28` — `validate_with_wordfreq.py` (calea rapidă). Descoperit: acoperirea wordfreq pentru română e binară — nu e semnal util sub top ~1.500 cuvinte.
- `2026-04-28` — `process_wikisource.py`. Corpus Wikisource RO: 14.3M tokens, bază istorică.
- `2026-04-29` — `validate_diachronic.py`. Formula log₂(hist_ppm / modern_ppm).
- `2026-05-05` — `process_culturax.py`: robustețe, loop de restart automat.
- `2026-05-12` — **Bug critic corectat.** `ds.skip()` din `datasets` ciclează la checkpoint > dimensiunea dataset-ului. Rescris pe parquet-uri individuale via `HfFileSystem` + `pyarrow`.
- `2026-05-12` — Rerulare curată: CulturaX 40.3M docs / 17B tokens. 245 extinct / 1.430 declining.
- `2026-05-12` — `search_wild.py`: interfață provider — DDG (fără cheie API) + Google CSE.
- `2026-05-12` — Monitoring: `health_check.py`, `audit.py`, `status.py`.
- `2026-05-13` — **Prag ridicat la freq < 1.0.** `oțios` (freq=0.85) era exclus din propria-i listă. Candidații cresc de la 1.884 la 140.308.
- `2026-05-15` — `extract_taxonomy.py`: register, domeniu, etimologie, POS din dumpul DEX.
- `2026-05-15` — **UI Flask+HTMX** — explorator de cuvinte cu navigare prin tastatură.
- `2026-05-16` — Redesign UI complet: filtre pills, temă caldă luminoasă, sidebar chip grid.
- `2026-05-17` — Dump DEX nou (1.65 GB). Investigat bug join taxonomie: `objectId` din `ObjectTag` pointează la Meaning IDs, nu Entry IDs — atribuiri random de domenii.
- `2026-05-17` — `scrape_definitions.py`: completare definiții lipsă din dexonline.ro (~12.8k cuvinte).
- `2026-05-18` — **Corecție join taxonomie.** Lanț corect: `Lexeme → EntryLexeme → TreeEntry → MeaningTree → ObjectTag`. Verificat: `antipapă → franceză`, `isihie → învechit + neogreacă`.

**11 Cod și date**  
- `README.md` — pipeline end-to-end, contracte de date, coloane
- `docs/BACKLOG.md` — probleme deschise P0–P3
- `docs/activity-history.md` — jurnal de sesiuni cu motivele din spatele deciziilor
- `docs/conceptual-roadmap.md` — critica metodologică, ce înseamnă "uitat"
- `docs/corpus-options.md` — catalog corpora românești disponibile

Footer: dark band matching hero, `Oțios · metodologie · Mai 2026`.

---

## Key implementation notes

1. **Self-contained CSS** — copy relevant tokens from base.html into a `<style>` block. No shared stylesheet.
2. **Fonts** — same Google Fonts link as base.html: Inter Tight + Lora + JetBrains Mono.
3. **Top stripe** — replicate `body::before` 3px verdict-gradient stripe from base.html.
4. **Timeline component** — vertical spine (`::before` on `<ol>`), gold dots (`::before` on `<li>`), date chips in JetBrains Mono on dark bg, `what` in bold, `why` in italic muted.
5. **Stats** — hardcode current values from activity log / README (not live from DB).
6. **Nav link to explorer** — href `/` (works when Flask is running) with a note that the page can be opened directly as a file.
7. **Romanian throughout** — all body text in Romanian (as shown in example page).

---

## Verification

1. Open `ui/metodologie.html` directly in browser (file://) — layout, fonts, colors render correctly.
2. Navigate to each TOC anchor — smooth scroll to correct section.
3. Start Flask app (`python ui/app.py`) — verify that opening `http://localhost:<PORT>/static/metodologie.html` or just navigating to the file both work.
4. Check timeline renders correctly: spine visible, dots aligned, dates readable.
5. Take a screenshot to confirm visual quality matches Oțios design tokens.
