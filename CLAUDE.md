# CLAUDE.md

Guidance for Claude (and humans) working in this repository.

## Project overview

Oțios identifies "forgotten" Romanian words: terms in DEX Online (the official dictionary) that have fallen out of modern usage.

- **Phase 1 — dictionary analysis.** Parse the 1.65 GB DEX Online MySQL dump into
  `lexemes.db`, `inflected_forms.db`, `dict_sources.db` and `definitions.db`, then curate
  candidates (`create_curated_list.py`).
- **Phase 2 — corpus comparison.** `process_wikisource.py` (historical) and
  `process_culturax.py` (modern) count tokens into `corpus_frequencies.db`;
  `validate_diachronic.py` rolls those counts up over inflection paradigms and assigns a
  verdict.
- **Phase 3 — scoring and split.** `make_shortlist.py` scores every candidate and splits
  the result into two seams (see **Seams** below); `tools/build_ui_db.py` builds
  `public/data/ui.db` for the PHP app.

`validate_with_wordfreq.py` still exists as a fast standalone screen (see
`docs/wordfreq-recipe.md`) and feeds the small `rare_in_use` tab, but it is not on the
main path. The legacy Wikipedia/OSCAR branch and `search_wild.py` are in `archive/`.

For the methodological critique (what "forgotten" should mean, corpus options): `docs/conceptual-roadmap.md` first, then `docs/corpus-options.md`.

### Two things that are easy to get backwards

1. **`Lexeme.frequency` is not a usage frequency.** It behaves like a literary-prominence
   score: `zapciu` (an obsolete Ottoman-era tax collector) is 0.96 while `internet` is
   0.88 and `pandemie` is 0.80. High values mean "well established in the written canon",
   which is why *high* DEX frequency plus corpus absence is the signature of a forgotten
   word, and *low* DEX frequency mostly means a neologism or an obscure regionalism.
2. **The two corpora differ by 1,187× in size** (Wikisource 14.3M tokens, CulturaX 17.0B).
   Any threshold expressed in per-million terms means something completely different on
   each side. Compare occurrence counts, or percentile ranks — never ppm across corpora.

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

`requirements.txt` covers the corpus path (`datasets`) and the frequency screen
(`wordfreq`, `simplemma`).

## End-to-end pipeline

All scripts assume `cwd` is the repo root and `data/dictionaries/` + `data/processed/` exist.

**Phase 1 — extract from the dump.** Each of these streams the 1.65 GB dump once; the
last three take a few minutes each and are independent, so they can run in any order.

```bash
python extract_lexemes.py          # → lexemes.csv + lexemes.db
python extract_taxonomy.py         # → Tag/ObjectTag/… into lexemes.db (register, domain, POS)
python extract_inflected_forms.py  # → inflected_forms.db   (2.27M forms → lemma)
python extract_dict_sources.py     # → dict_sources.db      (names, years, in_current_dict)
python extract_definitions.py      # → definitions.db
python create_curated_list.py      # → forgotten_words_curated.csv
```

**Phase 2 — corpora.** Long-running; see **Monitoring** below.

```bash
python process_wikisource.py       # historical  → corpus_frequencies.db
python process_culturax.py         # modern      → corpus_frequencies.db
```

**Phase 3 — verdicts, scoring, UI.**

```bash
python validate_diachronic.py      # → forgotten_words_diachronic.csv
python make_shortlist.py           # → forgotten_words_shortlist.csv (both seams)
python make_shortlist.py --stats   # dry run: seam and tier counts only
python tools/build_ui_db.py        # → public/data/ui.db
```

`scrape_definitions.py --merge` fills definition gaps from dexonline.ro for words the dump
has no `DefinitionSimple` row for (keep `--delay ≥ 3`; the site is community-run).

**After any rebuild, check `git diff --numstat data/word_ids.tsv` shows additions only.**
That file is what makes `?w=` share links durable, and a renumbering breaks every link
ever shared, silently. `tests/test_rescore.py` asserts it too.

**Filling definition gaps — `scrape_definitions.py`:**

`extract_definitions.py` recovers ~4.6k of the 17.4k shortlist words from the DEX MySQL dump (the dump's `DefinitionSimple` table is the source of truth — its `lexicon` column is the headword, not a dictionary identifier). The remaining ~12.8k shortlist words have no entry there and must be scraped from dexonline.ro.

```bash
python scrape_definitions.py --dry-run --limit 5         # smoke test, no HTTP
python scrape_definitions.py --limit 20 --delay 3.0      # small live run
python scrape_definitions.py --delay 3.0 --merge         # full run, ~5–7 hrs at 3s/req
python scrape_definitions.py --merge-only                # just upsert checkpoint into db
```

Output: `data/processed/scraped_definitions.csv` (columns: `word, definition, source_url, scraped_at, status`). `status ∈ {ok, not_found, error}`. With `--merge`, ok rows are `INSERT OR REPLACE`'d into `data/processed/definitions.db`. Resume is automatic: re-running skips words already in the checkpoint or in the definitions DB. Ctrl+C is safe — each row is flushed immediately. Be polite to dexonline.ro (community-run): keep `--delay ≥ 3`.

## Key data contracts

### `lexemes.db` — `Lexeme` table (`extract_lexemes.py:124-150`)

Columns the pipeline reads:
- `form` — word as it appears in DEX
- `formNoAccent` — accent-stripped form (stress marks only; diacritics are kept)
- `frequency` — DEX score 0.0–1.0. **A literary-prominence score, not a usage frequency**
  (`zapciu` 0.96 > `internet` 0.88). Treat 0.0 as missing data, not "rarest".
- `description` — part-of-speech / register (e.g. `s.f.`, `adj.`)
- `modelType`, `notes` — used by curation heuristics

### `inflected_forms.db` (`extract_inflected_forms.py`)

```
lexeme(lexeme_id PK, lemma, frequency)          317,721 rows — complete
inflected(form, lexeme_id)                      2,269,003 rows
form_lemma(form, lemma, lexeme_id, n_lemmas)    1,633,231 rows
```

The corpus processors count raw tokens, and Romanian is heavily inflected, so without this
map a lemma is only ever credited with its citation form (`înmărmuri` 317, while
`înmărmurit` alone is 5,846). `n_lemmas` is how many lemmas claim a surface form — 12% are
shared, and `validate_diachronic.aggregate_by_family` splits those by headword prominence
rather than crediting each claimant in full.

### `dict_sources.db` (`extract_dict_sources.py`)

```
dict_sources(word PK, sources, dict_count, newest_dict_year, oldest_dict_year, in_current_dict)
sources_meta(source_id PK, short_name, year, normative)
```

113 dictionaries, 108 with a usable year. `in_current_dict` = appears in something
published from `CURRENT_DICT_YEAR` (2005) on — the line between "dropped out of the
normative lexicon" and "still official Romanian, just unused". Note `normative` is set for
only 2 sources (the DOOM editions), so use `year`, not that flag.

### `forgotten_words_curated.csv` (`create_curated_list.py:166-189`)

```
word, word_no_accent, frequency, rarity_category, description, model_type, notes
```

`rarity_category ∈ {very_rare, rare, uncommon}`, bins at 0.30 and 0.50.

### `data/word_ids.tsv` — permanent share-URL ids (`tools/word_ids.py`)

`id<TAB>word`, 1-based, **append-only**. Tracked in git on purpose (`.gitignore` negates it
out of the blanket `data/*` rule) because it is the only file that makes `?w=` links
durable: `ui.db` is deleted and rebuilt on every data refresh, so an id derived from row
order or a rowid would silently repoint every link ever shared.

Three rules, all load-bearing:

1. **Never renumber.** Ids are assigned once and keep their word forever.
2. **Never remove.** A word that drops out of a later shortlist keeps its id, so old links
   to it still resolve.
3. **Only append.** `build_ui_db.py` calls `word_ids.apply_to_db()` at the end of a build,
   which numbers unseen words (sorted, for a reproducible file) and writes `words.word_id`.

`tools/migrate_ui_db_word_ids.py` backfills an already-built `ui.db` without a full rebuild.
Both are idempotent — a second run must produce a byte-identical file, and that is the
cheapest way to check the invariant holds.

The codec is `pack_words()` / `unpack_words()` in `api/_lib.php` (`"1.4z.1f2"` — version
prefix, then base36 ids, order preserved), exposed as `api/pack.php` so the browser never
carries the dictionary. `search.php` accepts `w=` and still honours the legacy plaintext
`words=`.

### `corpus_frequencies.db` (`process_corpus.py:69-105`)

```
corpus_word_frequency(id, word, corpus_name, occurrence_count, document_count, last_updated)
processing_stats(id, corpus_name, documents_processed, tokens_processed, ...)
```

`corpus_name ∈ {wikisource_ro, culturax_ro, subtitle_ro}`. Words are lowercased and
NFC-normalized. Sizes are wildly asymmetric — 14.3M vs 17.0B tokens — which is why nothing
downstream compares them in ppm.

## Seams

`make_shortlist.py` writes one CSV whose `seam` column splits it in two, because the
project is chasing two different things:

- **`relevant`** (~2.8k) — strong evidence of a word that was used and faded: historically
  attested, near-absent today, broadly covered by dictionaries, still in one published
  from 2005 on. **The default view is this seam minus the hide-flags below** (~2.3k).
- **`curiosity`** (~13.4k) — everything else that still qualifies as a candidate.

The split is a weighted score (`make_shortlist.score`), not a ladder of thresholds. The
signal that does the most work is **historical attestation strength**: `politeță` occurs
143 times in Wikisource, `celșag` 4. Without it the score rewards obscurity itself and the
top of the list fills with words that were never really in circulation.

### Score vs. flags — keep these apart

Three flags mark words most people will not want to see. They are **not** part of the
score and they do **not** decide the seam:

- `regional_only` — a DEX regional/dialectal tag *without* also being tagged old.
  `regional|învechit` is a word that died; plain `regional` is a local term.
- `variant_like` — `family_ratio ≥ 25`, where `family_ratio` is the undivided word-family
  count over the disambiguated per-lemma one. `tinereță` sits at 298×, `veșcă` at 938×,
  while a genuinely isolated rare word sits at 1×. It catches only variants that *share an
  inflectional paradigm* — phonetic respellings like `vivliotică`/`bibliotecă` have
  unrelated paradigms and are caught instead by having no current dictionary.
- `proper_noun_like` — DEX knows this spelling **only** as a capitalised headword. It must
  stay "only": flagging every collision hid ordinary words like `gheb` ("cocoașă") because
  DEX also lists the name `Gheb`.

**The score says how good the evidence is; the flags say what you would rather not look
at.** Penalising a flag in the score as well is double-counting, and it makes the flag
unappealable: when regional words cost 25 points *and* were routed out of the seam, none
could reach the relevant list, so the UI's "arată regionalisme" toggle had nothing to
reveal. As it stands the relevant seam holds ~397 regional and ~77 variant words, hidden
until asked for. The one score penalty that remains is for a *moderate* family ratio
(4–25×), which is an evidence problem rather than a preference — the lemma's count is
being propped up by its relatives.

### UI defaults

`build_word_filter()` (`public/api/_lib.php`) defaults to `seam=relevant`, hides all three
flagged classes, and sorts by `quality_score DESC`. Every one is a visible one-click
toggle — `seam`, `show_regional`, `show_variants`, `show_proper` — never a silent
exclusion, because the point of opening this up is to learn where the lines are wrong.

Two things to preserve when touching these:

1. **Toggles are `show_*`, not `hide_*`.** An unchecked checkbox is not submitted, so a
   default-on `hide_*` could never be switched off.
2. **Every filter needs registering in `public/assets/app.js` too**, or it works but the
   URL never reflects it and the state is unshareable: add it to `AF_SPECS` (the chip) and
   to the read/write arrays in `applyUrlToForm` / the URL writer — **there are two arrays,
   one per direction, and missing the writer is the silent half**. A default value goes in
   `URL_PARAM_DEFAULTS` so it is omitted from the URL when unchanged.

### `newest_dict_year` — last attestation

The newest dictionary that still prints a word, from `Source.year` via `dict_sources.db`.
97% coverage (15,862 of 16,315). Exposed as `sort=attested`, the `attested_before=<year>`
filter, and the lead chip in the detail panel's dictionary row.

**It is a `curiosity`-seam instrument.** The `relevant` seam requires `in_current_dict`
(2005+) to qualify, so it is 2,806 words at 2010+ and 9 below — the filter says almost
nothing there by construction. On `curiosity` it is sharp: 225 words were last printed
before 1970, and that slice is almost entirely pre-1953-reform orthography (`desbatere`,
`sburătoare`, `răsvrătit`, `vuet`).

Rows with no year are excluded when a ceiling is set, and sort last. "Unknown" means the
dictionary is unnamed or unmatched — it is not evidence that a word is old.

## Synonyms

`words.synonyms` / `words.antonyms` come from `scrape_synonyms.py`, not from the dump.
dexonline distributes `Definition.internalRep` in full only for the Academy dictionaries;
the Litera titles are redacted to 23 characters:

```
sourceId 1 (DEX '98)   max 15,039 chars   mean 201
sourceId 6 (Sinonime)  max     23 chars   mean  23   "@AB'A@ s. dimie, păn..."
```

So `dict_count` knows a word appears in `Sinonime`/`Sinonime82`/`Antonime`, but not what
they say. The rendered page has it.

```bash
python scrape_synonyms.py --dry-run --seam relevant     # count + ETA, no requests
python scrape_synonyms.py --seam relevant --merge       # the default-view words
python scrape_synonyms.py --merge-only                  # re-merge an existing checkpoint
python tools/build_ui_db.py                             # fold into ui.db
```

Resume is automatic and Ctrl+C is safe — each row is flushed as it arrives. `--delay`
below 3s is refused outright: dexonline.ro is community-run.

**One scrape at a time, enforced.** `--delay` is a per-process guard, so two copies each
waiting 3s hit the site every 1.5s — which happened on 2026-08-08. `acquire_host_lock()`
takes an exclusive `flock` on `data/.dexonline.lock` before any request; a second run
exits 1 and names the holder. Three properties worth keeping:

- **It is keyed on the host, not the script.** `scrape_definitions.py` talks to the same
  site, and adopting the same two lines makes it interlock with this one. A per-script
  lock would permit exactly the doubling this prevents.
- **`flock`, not a PID file.** The kernel drops it when the process dies, so a `kill -9`
  cannot strand a lock that someone has to `rm` by hand. The pid written inside is only
  read back to name the holder in the error message.
- **`--dry-run` never takes it.** Inspecting the queue while a scrape runs is legitimate;
  it makes no requests.

Two things the parser has to get right, both learned from real output:

1. **A page renders every entry dexonline considers related, not just the one asked
   for.** `/definitie/roză` also carries `ROZ` (the colour). Entries are matched on
   headword — without it `roză` picks up *trandafiriu, rozatic, pembe*. When nothing
   matches, all entries are used, because archaic spellings are the point here and
   dexonline normalises them (`/definitie/poronci` returns only `PORUNCĂ`/`PORUNCI`).
2. **Each entry opens with its own capitalised headword**, sometimes mid-token because
   the markup does not fence it off (`"ROZĂ     trandafir, rug"`). Leading capital runs
   are stripped and still-uppercase tokens dropped: synonyms are lowercase, headwords
   are not. Antonime entries are the exception — ordinary case, `Curajos ≠ fricos, laș` —
   so their headword is read from before the `≠`.

## Gotchas

- **Never compare the two corpora in ppm.** They differ 1,187× in size, so a shared
  `0.1 ppm` floor meant "< 1,697 occurrences" on the modern side and "≥ 1.43" on the
  historical one. That single line classified `zapciu` (1,322 modern hits) as extinct and
  put `vapor`, `fluviu` and `cioban` in "declining".
- **Corpus counts are per surface form.** Always roll them up through
  `inflected_forms.db` before judging a lemma, or every verb reads as extinct.
- **`dex_pos` comes from `Lexeme.modelType`, not from taxonomy tags.** The meaning-level
  tags cover ~3% of the list and bleed across variants — `visternic` (modelType `M`) came
  out "substantiv feminin" because the entry also covers `vistiernică`. `modelType` is on
  all 317,721 lexemes and gives 99.5% coverage. `T` and `IL` are inflected forms rather
  than headwords and `I` means invariable, so those fall back to `description`.
- **Derive `dex_pos` before building `vocab`**, or the POS dropdown lists values that
  almost nothing matches.
- **Frequency bins disagree** across scripts (0.30/0.50/0.60 in `constants.py` vs
  0.30/0.50/1.01 in `validate_diachronic.py`). `constants.py` is canonical.
- **The sampled dump comments out whole tables** (`-- SAMPLED: INSERT INTO \`Source\``),
  so `extract_dict_sources.py` against it yields no names or years. It warns; heed it.
- **`explore_dex.py` is not a working script** — narrative documentation that can't run.
- **`archive/` is reference only** — the legacy Wikipedia/OSCAR branch, `search_wild.py`
  and the old Flask UI live there. Don't run or import them; see `archive/README.md`.

## Conventions

- **One script per pipeline stage.** No package layout until 3+ modules share helpers.
  `dump_parser.py` is the one shared helper — three extractors use its quote-aware scanner.
- **Romanian normalization:** lowercase → cedilla-to-comma diacritics (`ş→ș`, `ţ→ț`) → `unicodedata.normalize('NFC', …)`. Canonical implementation: `dump_parser.normalize`.
- **Generated artifacts go under `data/`** (gitignored). Never commit `*.db`, `*.csv`, or `data/` contents — except `data/word_ids.tsv`, which is tracked on purpose.
- **`frequency = 0` means no data, not "rarest".** Filter with `frequency > 0` or `> 0.01`.

## Visual skins

The UI has two independent axes on `<html>`: `data-theme` (light/dark) and `data-skin`.
A skin is a plain CSS file in `public/assets/skins/` — drop one in and it appears in the
dropdown on the next request. There is no registry, no build step, and no PHP to edit.

```
public/assets/skins/
  _template.css   # copy this; underscore-prefixed files are skipped by the scanner
  brutal.css      # "Beton"  — the full brutalist skin, ~1080 lines
  govuk.css       # "Guvern" — GOV.UK Design System homage, ~330 lines
  tezaur.css      # "Tezaur" — thesaurus.com homage, tinted word pills, ~210 lines
  velin.css       # "Velin"  — worked example, tokens only, ~70 lines
```

Discovery lives in `public/api/_skins.php` (required from `_lib.php`, so all four pages
get it). Three rules:

1. **The filename is the id.** `sepia.css` → every rule scoped under `[data-skin="sepia"]`.
   Ids must match `^[a-z0-9][a-z0-9_-]*$`; anything else is ignored rather than
   half-working.
2. **Scope everything.** All skin files load on every page — the attribute decides which
   applies. An unscoped rule leaks into every skin, including `paper`.
3. **Name it** with an `@skin <label>` tag in a comment near the top, or the filename is
   used as the label.

`paper` is the built-in null skin: `app.css` with nothing on top. It has no file.
`DEFAULT_SKIN` in `_skins.php` sets what a first-time visitor gets.

### What "token" means here

A **token** is one of the ~40 CSS custom properties declared on `:root` at the top of
`app.css`. They are the skinnable surface. `app.css` never hardcodes a colour, font or
radius in a component rule — it says `background: var(--surface)`, never `background:
#F4EFE5`. So redeclaring `--surface` inside `[data-skin="x"]` repaints every rail, card
and sunken area across all four pages without the skin ever naming `.filter-sheet`.

They are named for the **role**, not the value — `--surface`, not `--warm-grey`. That is
the whole trick: a token can take any value in any skin because nothing downstream
assumes what it looks like.

The four groups:

| group | tokens | notes |
|---|---|---|
| surfaces / text | `--bg --surface --surface-2 --border --border-2 --text --text-2 --text-3 --text-4` | `--text-4` is real 9px text (the freq superscript), so it needs 4.5:1 — not a throwaway |
| accent / status | `--accent --accent-bg --on-accent --badge-bg --star --success* --error*` | `--on-accent` must flip to ink in dark blocks, where accents are light |
| verdicts | `--v-{ext,dec,hist,abs}` × `{"" ,-bg,-bd,-tx}`, plus optional `-word` | `-word` only if the skin colours the headword instead of the dot |
| type / metrics | `--sans --serif --mono --radius --bar-h --chip-h --statusbar-h` | `govuk` points all three fonts at one Arial stack and sets `--radius: 0` |

The contrast is a **component rule** — `[data-skin="brutal"] .word-row { … }`. Those
target one element on one page and break if the markup moves. Tokens are cheap and
durable; component rules are neither. This is why `velin.css` is 68 lines and
`brutal.css` is over a thousand: same site, opposite ends of that trade.

Colours that differ between light and dark must be tokens declared in **both** blocks;
hardcoding one is the most common way a skin ends up unreadable at night.

`govuk.css` was built partly to find where the contract runs out. It did: the black
masthead, the yellow focus state, square marks, dotless tags, the green button and the
inset rule all needed component rules. That list, and the two hooks worth adding if a
third skin wants them, is in `docs/BACKLOG.md`.

Skin files load with an mtime query string, so edits show on plain reload. A stored skin
whose file has since been deleted falls back to `DEFAULT_SKIN` (the valid list is baked
into the pre-paint boot script).

## Page shell — header and footer partials

All five pages (`index`, `stats`, `joc`, `lista`, `liste`) draw the same two partials.
Before them, each page rolled its own bar and `stats.php` had no brand at all.

```php
<?php $brand_tag = 'statistici'; require __DIR__ . '/api/_partials/header.php'; ?>
...
<?php $page = 'stats';          require __DIR__ . '/api/_partials/footer.php'; ?>
```

**Identity at the top, travel at the bottom.** `header.php` is brand + display
preferences (scale, skin, theme); `footer.php` is the one navigation bar. Nav is *not* in
the header on purpose — the explorer's top bar already carries brand, search, count, play,
view and filters, and five more links is what breaks it. The bottom bar is also
thumb-reachable on a phone, and `index.php` had already put nav there.

`header.php` takes three optional slots, all raw HTML strings, so a caller can build one
with `ob_start()` and keep writing ordinary markup: `$header_center` (the explorer's
search box), `$header_tools` (count/play/view; joc's modes and score), `$header_after`
(the filter button, which has to stay last). `footer.php` takes `$footer_left` and
`$footer_extra` (the explorer's counts and colour legend) plus `$page`.

Three things to preserve:

1. **`NAV_ITEMS` lives in `_lib.php`**, not in the partial — a `const` in an included
   file cannot be guarded against a second include, and it sits with `VERDICTS`/`TIERS`
   as the other list of user-facing strings drawn on every page.
2. **The current page stays an `<a>`** with `aria-current="page"` and an accent underline.
   As a `<span>` it stopped matching every skin's `#status-bar a` rule and needed its own
   colour — and `var(--text)` is a *page*-ground token, which on beton's ink footer meant
   near-black on black. Never give this bar a colour of its own.
3. **Every nav entry keeps an icon and a label.** Below 900px labels are hidden and the
   icons carry the bar alone, so an entry without one would vanish.

`lista.php` sets `$brand_tag` but deliberately no `$page`: it is not `liste.php`, so
nothing in the nav should render as current and stop being clickable.

## Lists

**The four buckets are the lists.** `fav` / `lol` / `ascunde` / `meh` (declared once in
`LIST_BUCKETS`, `api/_appdb.php`) are derived from `app.db.annotations` on every request via
`bucket_words()` — never stored, so they cannot drift out of date. `liste.php` shows them
alongside your published lists and a directory of everyone's.

A row in the `lists` table is a **published snapshot** of a bucket. `lists.source_tag`
records which one:

- `POST {action:'publish_bucket', bucket}` — create-or-reuse the caller's list for that
  bucket and fill it from their own annotations. One list per bucket per user. The client
  never sends the words.
- `POST {action:'refresh', id}` — re-read the bucket. Words already present keep their
  `position` so a re-sync doesn't reshuffle a list someone has already read.
- `source_tag = ''` means hand-assembled — every list created through `create` + `add`,
  which still work unchanged. Those cannot be refreshed.

This is why there is no per-word "add to list", no grid multi-select and no inline list
editing: you curate by marking words while browsing, and publishing is one button.

### Moderation

The public directory (`GET api/lists.php?public=1`) has a report/takedown path:

- `POST {action:'report', slug, reason?}` — anyone can flag a **public** list that isn't
  theirs. Addressed by slug, because a reporter is a reader. A private or missing list
  both answer `404`, so the endpoint can't be used to probe which slugs exist. One report
  per user per list (`idx_reports_once`); re-reporting is a silent no-op that returns the
  same success, so a reporter learns nothing about whether their first one landed.
- **`public/admin.php`** — the queue, grouped by list, most-reported first. Unpublish
  (`is_public = 0`, reports → `removed`), dismiss (→ `dismissed`), or delete outright.
  Unpublish is the default action and leaves the owner's data intact; delete is the only
  irreversible one.

Access is a shared token in `api/config.local.php`:

```php
define('OTIOS_ADMIN_TOKEN', '<48+ random hex chars>');   // openssl rand -hex 24
```

Two things about that page worth not undoing:

1. **No token defined, or a wrong one, means `404` — not `403`.** An install that never
   configured moderation gives nothing away when probed.
2. **The token is passed once as `?token=`, then sealed into a cookie** (`seal_token()`,
   8h) and the page redirects to the bare URL, so it leaves the address bar, history,
   access log and any Referer. This is also why the page sets `referrer: same-origin`
   rather than `no-referrer` — `no-referrer` serializes `Origin` as `null`, which is
   exactly what `require_post_same_origin()` rejects, and its own forms POST back to it.

**There is deliberately no auto-hide-after-N-reports rule.** Identity here is an anonymous
device token, so "three different users reported this" costs an abuser three cookie
clears — a report threshold would be a cheaper way to censor a list than to publish one.
Reports queue for a human.

`liste.php` is still `noindex`; lifting that is now a product decision rather than a
blocker.

### Backing up `app.db`

`private/app.db` is the only irreplaceable file in a deploy — `ui.db` regenerates from the
pipeline, but annotations, lists, nicknames and the game log exist nowhere else.

```bash
php api/_backup.php              # snapshot + prune, keeping the newest 14
php api/_backup.php --keep 30    # keep more
php api/_backup.php --dir /mnt/x # write somewhere else (an external mount)
php api/_backup.php --list       # show what's there, write nothing
```

Nightly, from the deployed app folder:

```cron
17 3 * * * cd ~/lab.gov2.ro/oțios && php api/_backup.php >> ~/otios-private/backup.log 2>&1
```

It lives in `public/api/` because **only the contents of `public/` are deployed** — a
script anywhere else in the repo is not on the server. It is CLI-only: `PHP_SAPI !== 'cli'`
returns 404 before any include, so it is inert over HTTP. It uses `VACUUM INTO` rather
than `copy()`, because in WAL mode the committed data is split across `app.db` and
`app.db-wal` and a file copy can land mid-transaction; every snapshot is then reopened and
`PRAGMA integrity_check`ed before old ones are pruned.

This does not replace an off-machine backup. A snapshot beside the original survives a bad
migration or a mistaken delete, not a lost disk.

## Deploying to a subfolder

The app runs at any URL depth. `BASE` (`api/_lib.php:8-13`) is derived by subtracting
`DOCUMENT_ROOT` from the real path of the app folder, and everything — assets, links,
htmx endpoints, `OTIOS_BASE` for JS — is prefixed with it.

Copy the **contents of `public/`** into the target folder:

```
~/lab.gov2.ro/            ← document root
└── oțios/                ← contents of public/   →  lab.gov2.ro/oțios/
    ├── index.php  api/  assets/  data/ui.db
    └── api/config.local.php
~/otios-private/          ← OUTSIDE the web root
└── app.db
```

Five things that bite:

1. **Never deploy the repo itself**, only `public/`. With the repo mounted, `private/app.db`,
   `.git/config` and the docs are all straight downloads — measured.
2. **`app.db` defaults to inside the web root** on this layout. `OTIOS_PRIVATE_DIR` is one
   level up from the app folder, which here is the document root. Copy
   `api/config.local.example.php` → `api/config.local.php` (gitignored; `_appdb.php:18`
   loads it if present) and set:
   ```php
   define('OTIOS_PRIVATE_DIR', '/home/you/otios-private');
   ```
3. **Never overwrite the server's `config.local.php` with yours.** It is per-install, and
   local dev has one too — different private dir, different admin token. Always exclude it:
   ```bash
   rsync -av --exclude 'api/config.local.php' public/ you@host:~/lab.gov2.ro/oțios/
   ```
   The file being gitignored protects the repo, not a careless `rsync`.
4. **No `Alias`, no symlinks.** `__DIR__` resolves symlinks and `DOCUMENT_ROOT` does not, so
   the subtraction silently produces garbage rather than failing — an Apache `Alias` was
   measured yielding `BASE = "blic"`. The folder must sit physically inside the docroot.
   Verify by viewing source and checking `var OTIOS_BASE`.
5. **On nginx**, add `location ~ \.(db|db-wal|db-shm|sqlite3?)$ { deny all; }`. The
   `public/data/.htaccess` that hides the 20 MB `ui.db` is Apache-only.

Non-ASCII folder names work (`/oțios/`), but see `cookie_base_path()` in `_auth.php` for
why the cookie path has to be percent-encoded — the cookie *is* the account, and a Path the
request URI can't match means a new anonymous user on every request.

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
