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

`validate_with_wordfreq.py` still exists as a standalone screen (see
`docs/wordfreq-recipe.md`) but **feeds nothing** — the `rare_in_use` tab it used to fill
was removed on 2026-08-11. Its list has no resolution at the low end: measured over 60,000
candidates, **99.6% score exactly 0.00** because wordfreq has never heard of them, so its
lowest real scores are ordinary words (`haz` 3.31, `bețiv` 3.22) while `zapciu`, `vornic`
and `logofăt` are all 0.00 and indistinguishable. A tier defined on that band could only
ever hold common words, at any threshold. Do not wire it back into `ui.db`. The legacy Wikipedia/OSCAR branch and `search_wild.py` are in `archive/`.

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
python tools/export_editorial.py --user N   # app.db marks → data/editorial.tsv (optional)
python tools/build_ui_db.py        # → public/data/ui.db
```

`export_editorial.py` is the one step that reads the *deployed* `app.db`, so it runs
wherever that file is. `--user` is required and never defaults — the dev `app.db` carries
hundreds of test-fixture users, and a default would publish a fixture's taste as the site's
editorial line. `--list-users` shows who has annotations; `--dry-run` prints the counts and
writes nothing. It refuses to shrink the picks by more than half without `--force`, because
a mistyped `--user` reads as "this curator marked nothing" and would blank the file.

`scrape_definitions.py --merge` fills definition gaps from dexonline.ro for words the dump
has no `DefinitionSimple` row for (keep `--delay ≥ 3`; the site is community-run).

**After any rebuild, check `git diff --numstat data/word_ids.tsv` shows additions only.**
That file is what makes `?w=` share links durable, and a renumbering breaks every link
ever shared, silently. `tests/test_rescore.py` asserts it too.

**Filling definition gaps — `scrape_definitions.py`:**

`extract_definitions.py` recovers ~4.6k of the 18.3k shortlist words from the DEX MySQL dump (the dump's `DefinitionSimple` table is the source of truth — its `lexicon` column is the headword, not a dictionary identifier). The remaining ~12.8k shortlist words have no entry there and must be scraped from dexonline.ro.

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

`corpus_name ∈ {wikisource_ro, lumro_ro, culturax_ro, subtitle_ro}`. The **historical panel
is `wikisource_ro` + `lumro_ro`** (`HIST_CORPORA`), aggregated separately and merged by
`merge_panels()` — documents are summed *across* corpora because a Wikisource page and a
LUMRO novel are different documents, but stay a max *within* one corpus. Merging the raw
surface counts first instead would push both through a single max and lose the documents
only the smaller corpus contributes.

**LUMRO's `document_count` is distinct authors (of 111), not novels (of 175).** `hist_docs`
is read as a claim about independence, and three novels by one novelist are one writer's
vocabulary — 638 of the 1,425 words LUMRO attests came from a single author before this,
`jupâneșică` at 47 occurrences all by V.A. Urechia among them. Occurrences still sum over
every novel; only the independence claim is corrected. Wikisource keeps counting pages
because it has no author metadata — the asymmetry follows what is knowable. Pinned by
`tests/test_process_lumro.py`, since "count novels" is the obvious simplification.

`corola_lemma_frequency` is a **separate table on purpose**: its counts are per-lemma, not
per-surface-form, so it must never go through `aggregate_by_family`. See the CoRoLa gotcha
below. Words are lowercased and
NFC-normalized. Sizes are wildly asymmetric — 14.3M vs 17.0B tokens — which is why nothing
downstream compares them in ppm.

## Seams

`make_shortlist.py` writes one CSV whose `seam` column splits it in two, because the
project is chasing two different things:

- **`relevant`** (3,499) — strong evidence of a word that was used and faded: historically
  attested, near-absent today, broadly covered by dictionaries, still in one published
  from 2005 on. **The default view is this seam minus the hide-flags below** (2,685).
- **`curiosity`** (14,771) — everything else that still qualifies as a candidate.

The split is a weighted score (`make_shortlist.score`), not a ladder of thresholds. The
signal that does the most work is **historical attestation strength**: `politeță` occurs
143 times in Wikisource, `celșag` 4. Without it the score rewards obscurity itself and the
top of the list fills with words that were never really in circulation.

### Score vs. flags — keep these apart

Four flags mark words most people will not want to see. They are **not** part of the
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
  DEX also lists the name `Gheb`. **No longer a browsing filter** — narrowing it to "only"
  left 2 words in the whole database (`sirius`, `weltanschauung`), so a default hide plus a
  toggle was a control that revealed nothing while quietly subtracting two rows. As of the
  2026-08-11 rebuild it marks **zero**: both of those words left the shortlist when the
  candidate list was regenerated, along with `chaise-longue`, `córdoba` and the other
  hyphenated compounds. The column still gates the word of the day (`index.php`) and quiz distractors
  (`api/quiz.php`), which is a different question from what a reader may browse.
- `archaic_spelling` — an obsolete *spelling* of a word that is entirely alive under a
  modern one: `situațiune`/`situație`, `sgomot`/`zgomot`, `advocat`/`avocat`. Not the same
  as `variant_like`, which keys on a shared inflectional paradigm and therefore cannot see
  a pair whose stems differ. `spelling_of` stores the modern twin, and the detail panel
  names it ("Grafie veche pentru *situație*") rather than silently dropping the row.

  **The rules are deliberately narrow and that is the design** — see
  `mark_archaic_spellings()` in `tools/build_ui_db.py` for the measured precision of each.
  Only `-țiune/-ziune/-siune → -ție/-zie/-sie`, `sb/sd/sg → zb/zd/zg`, `des+voiced → dez`
  and `adv → av` are used, each additionally requiring a named twin at least 20× more
  frequent in the modern corpus. The general-looking rules were measured and rejected:
  `e → ă` fires 2,300 times to find 69 twins and would equate `peți` with `păți`, which are
  different words. A hide-flag's false positives are invisible — the word simply is not
  there — so precision beats recall by a wide margin here. Catches 291 words, 107 of them
  in the default view.

  Do **not** widen this by flagging everything that "fell between CoRoLa and CulturaX":
  that population is 5,421 words and 61.6% of the default view, and it is full of genuine
  finds (`acaret`, `afion`, `agie`, `alișveriș`, `amploiat`). See
  `docs/corpus-expansion-plan.md`.

**The score says how good the evidence is; the flags say what you would rather not look
at.** Penalising a flag in the score as well is double-counting, and it makes the flag
unappealable: when regional words cost 25 points *and* were routed out of the seam, none
could reach the relevant list, so the UI's regionalisme control had nothing to reveal on
„cu" or „doar". As it stands the relevant seam holds 440 regional and 152 variant words,
hidden until asked for. The one score penalty that remains is for a *moderate* family ratio
(4–25×), which is an evidence problem rather than a preference — the lemma's count is
being propped up by its relatives.

- `editor_demote` — **the curator read this word and set it aside.** The only signal in the
  project that is a person's judgement rather than a measured property, and the only human
  signal allowed to *subtract*. It comes from `data/editorial.tsv` — tracked in git like
  `word_ids.tsv`, written by `tools/export_editorial.py --user N` from `app.db`, folded in
  by `build_ui_db.py` (or `tools/migrate_ui_db_editorial.py` for an existing `ui.db`).

  **A file rather than a live read of `app.db`, for two reasons that both matter.** The
  build runs on a laptop while `app.db` lives on the server outside the web root, so there
  is no moment at which the builder can see production annotations. And a signal that
  removes words from what every visitor sees has to be a diff with a git history and an
  obvious undo — as a live query it is one person's clicking silently reshaping the site,
  which is exactly the objection that deferred this feature for a year.

  `editor_pick` is its twin and subtracts from nothing: it drives the ★ chip and the
  „Alese" list on `liste.php`. **Neither is in `quality_score`**, for the same reason the
  four class flags are not — a scored-in opinion cannot be appealed.

  **Community marks never reach `ui.db`.** They are aggregated live from every user by
  `vote_counts_subquery()` (`api/_appdb.php`) and may only *reorder*, via the `populare`
  sort. Identity here is an anonymous device token, so N votes cost N cookie clears; if
  votes could subtract, hiding a word would be cheaper than publishing a list — the same
  reasoning that keeps auto-hide-after-N-reports out of list moderation. Pinned by
  `tests/test_editorial.js`.

`diminutive_like` is a fourth flag but not one of these three: it is **off by default**, so
it never subtracts from what you see until you ask. `mark_diminutives()`
(`tools/build_ui_db.py`) sets it from the DEX definition saying "Diminutiv al lui X" (as of the last build, 458 words in total) plus nine unambiguous suffixes whose stripped stem is a real lexeme.
`-iță` is deliberately excluded: as often a feminine agent (`păstoriță`, `vorniciță`) as a
diminutive. `tools/migrate_ui_db_diminutives.py` back-fills an existing `ui.db`.

### UI defaults

`build_word_filter()` (`public/api/_lib.php`) defaults to `seam=relevant`, hides four of
the five flagged classes, **demotes rather than hides the fifth**, and sorts by
`populare`. Every one is a visible control — `seam`, plus the five class rows — never a
silent exclusion, because the point of opening this up is to learn where the lines are
wrong.

**`editorial` is the one class that does not subtract.** Its states are `back` (default) /
`show` / `only`, and `back` is applied in the ORDER BY by `demote_order_sql()`, not as a
WHERE clause — a curator-demoted word sinks to the end instead of leaving the list. That
removed an asymmetry worth keeping removed: the curator's judgement used to be the only
human signal allowed to subtract, while the community's could only reorder. Now neither
subtracts. **Sinking is not self-explaining** — measured, the first demoted word lands at
position 2,556 of 2,682, page 11 — which is exactly why the three-state control stays:
without it there would be nothing to undo. Pinned by `test_editorial.js` §2c.

**Every option shows how many words it would return** — `facet_counts()` in `_lib.php`,
shipped to the sheet as one out-of-band `#facet-data` attribute and applied by
`applyFacetCounts()` in `app.js`. Two things to preserve:

- **Each group is counted with its own filter switched off**, via an explicit *neutral
  value*, not `unset()`. Removing a param reinstates its default, and most of these
  default to subtracting — `unset('seam')` counts curiozități against a relevante-only
  base and reports 0. Every group has to be actively neutralised.
- **One query per group, not per option.** Conditional aggregation counts every option of
  a group in one pass: eight scans of an 18k-row table, 12–40 ms, rather than forty.

`#facet-data` must exist in `index.php` as an empty placeholder — `hx-swap-oob` replaces an
element that is already in the DOM, and without it htmx drops the payload silently.

**Each filter section has a „?" that reveals a one-line explainer** (`fs_label()` in
`_lib.php`). A real button and paragraph rather than a `title=` tooltip: a title needs a
hover, and a phone has none — which would mean the explanation is missing on exactly the
device where an unfamiliar filter name is hardest to guess at.

**`sort=populare` blends the derived score with what people marked** —
`quality_score + 4·ln(1+votes)`, signed, rounded into bands (`VOTE_BOOST_SQL`). Bands
rather than `LN()` because SQLite's math functions are a compile-time option a shared host
may lack. **This is the default sort.** It was deliberately not, on the grounds that votes
come from anonymous device tokens — the argument that changed it is that votes can only
ever reorder, so making it the default costs at most a nudge in position, and the damping
keeps that nudge small. `search.php` falls back to `FALLBACK_SORT` when app.db cannot be
attached; that fallback matters more now that this is what a first-time visitor gets.
Two things to keep:

- **The damping is the anti-abuse measure, not a curve preference.** The `relevant` seam
  spans 92–121 with 76% of its 3,499 words inside a ten-point band, so a linear weight of
  even 5/vote lets four votes carry a word from the median to the top forty. On the ladder,
  each *doubling* of the vote count is worth about two more points — measured: `barabor`
  carries 20 ★ votes (every one of them a test fixture) and the blend moves it 92 → 104,
  well short of `văz` at 121.
- **`search.php` joins the vote counts only for this sort**, and the subquery's key column
  is aliased `vote_word` — joined as `word` it would make every unqualified `word` in
  `build_word_filter()`'s conditions ambiguous, and those conditions are shared with the
  un-joined query.

**The five classes are one three-state control each.** Four read `hide` / `show` / `only`
(„fără / cu / doar") and all four default to `hide`. The fifth, `editorial`, reads
`back` / `show` / `only` („în spate / normal / doar") and defaults to `back`, because it
demotes rather than hides — see UI defaults below.

**`seam` is a checkbox group, not a radio.** The two seams are a partition, so both ticked
already *is* what „toate" used to be; the third radio was a name for a state the other two
could express and had to be kept in step with them. It reads through `parse_multi()` like
`verdict`/`tier`/`pos`. One consequence: its default is 1-of-2, not all-of-2, so
`groupIsDefault()` in `app.js` needs `URL_GROUP_DEFAULTS` — otherwise every URL carries
`?seam=relevant` and the chip bar claims a filter nobody set.

Adding the fifth was three lines in `app.js` rather than nine, because `CLASS_PARAMS` is
concatenated into both URL arrays *and* both tab guards. That is what the array is for;
keep new classes going through it rather than adding literals.

Two things to preserve when touching these:

1. **Class filters are radios, not checkboxes, and that is what makes them uniform.** As
   checkboxes the polarity *had* to differ per class: an unchecked box is not submitted, so
   a class hidden by default needed `show_x=1` while one shown by default needed
   `hide_x=1` — and the sheet ended up with three „arată X" rows and two „ascunde X" rows
   that read as one set of controls and were not. A radio always submits, so the default
   can move without the wording following it. Two consequences: each param needs an entry
   in `URL_PARAM_DEFAULTS`, and the legacy `show_*=1` / `hide_diminutives=1` links must
   keep mapping — in `build_word_filter()` **and** in `applyUrlToForm()`, since htmx
   searches from form state on load and a server-only mapping leaves an old link rendering
   as filtered while behaving as if it were not.
   **There are no tab-specific controls any more, and that is worth keeping.** There used
   to be two tabs, so three sections had to be shown or hidden on `word_tier` and gated in
   *three* places kept in step by hand. It was wrong in all three on any deep link —
   `applyUrlToForm()` changes the radios without dispatching `change`, and the gate ran at
   script-eval time, so `?word_tier=rare_in_use` rendered the other tab's controls. That
   is a fourth place nobody had listed: the **initial** state, as distinct from the change
   handler. Every filter added while that existed also had to decide whether it was
   tab-specific. One list needs none of it — do not reintroduce a tab without re-reading
   this paragraph.
2. **Every filter needs registering in `public/assets/app.js` too**, or it works but the
   URL never reflects it and the state is unshareable: add it to `AF_SPECS` (the chip) and
   to the read/write arrays in `applyUrlToForm` / the URL writer — **there are two arrays,
   one per direction, and missing the writer is the silent half**. A default value goes in
   `URL_PARAM_DEFAULTS` so it is omitted from the URL when unchanged.
3. **None of it applies to a playlist.** When `w=` (or legacy `words=`) is present,
   `search.php`, `random.php` and `feed.php` skip `build_word_filter()` entirely and filter
   on the word list alone — see `playlist_words()` / `playlist_condition()` in `_lib.php`.
   A playlist is a list someone curated by hand, and the defaults above would quietly
   subtract from it: a shared list of twenty words arriving as eleven, with nothing on the
   page to explain the gap. `q` and `marks` still apply — the reader typed those. The UI
   half is `setPlaylistMode()` in `app.js`, which marks the form `data-playlist` and sets
   `inert` (not `disabled`, so the values survive the playlist) on every section but sort.

### `modern_band` — how much life the word still has

`0` absent · `1` faint · `2` still in circulation. The `urme azi` control, and the
replacement for the deleted `rare_in_use` tab.

**Read the direction carefully: more modern usage is *better* material here.** The words
in band 2 are what the project is for — `zapciu`, `birjă`, `vechil`, `dorobanț`, `cocoană`,
`jupâneasă`, `ișlic`. Band 0 is dictionary ghosts that never really circulated — `celșag`,
`racaleț`, `oglavă`, `toroști`, `barabor`. This is the same trap `$SORT_OPTIONS` already
records for `sort=rare` ("put the most obscure regionalisms first — jbârc, barabor,
hâșăi — which is the opposite of what the list is for"). Pinned by
`test_modern_band_points_the_right_way`.

**A band, not a count, and the indirection is the point.** An occurrence count only means
something relative to how much modern text was read, so `mark_modern_band()`
(`tools/build_ui_db.py`) derives the edges from `validate_diachronic`'s own
`MODERN_RARE_OCC` / `MODERN_ALIVE_OCC` through `scaled_modern_thresholds()`, at build time.
A number in PHP would silently change meaning the first time a corpus is added — the drift
the `scaled_modern_thresholds` gotcha below already describes.

Three bands, not four: `alive_occ` is also `make_shortlist`'s eligibility ceiling, so
nothing above it is in the table (max `modern_occ` is 1,998 against a floor of 2,000) and a
fourth option would be a control with nothing behind it.

### `newest_dict_year` — last attestation

The newest dictionary that still prints a word, from `Source.year` via `dict_sources.db`.
97% coverage (17,806 of 18,270). Exposed as `sort=attested`, the `attested_before=<year>` /
`attested_after=<year>` filters (a band when both are set — `attested_after` is `>=`,
`attested_before` is `<`, so they never overlap at the shared boundary year), and the lead
chip in the detail panel's dictionary row.

**Both filters are `curiosity`-seam instruments.** The `relevant` seam requires
`in_current_dict` (2005+) to qualify, so `attested_after` is close to always true there and
`attested_before` close to always false — neither says much there by construction. On
`curiosity` both are sharp: 288 words were last printed before 1970, and that slice is
almost entirely pre-1953-reform orthography (`desbatere`, `sburătoare`, `răsvrătit`,
`vuet`); the ~13.8k at 2005+ are `attested_after`'s more ordinary end of the range.

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
below 1.2s is refused outright: dexonline.ro is community-run.

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
- **CoRoLa is loaded and deliberately not in any panel — because it spans 1945+, not
  because of its lemmas.** `process_corola.py` loads the **surface-form** lists (1,813,746
  forms, 637.8M tokens) into `corpus_word_frequency`, so DEX's own paradigms do the rollup.
  That solved the lemmatization problem completely: TTL's lists put 12,176 on `strugur` and
  724 on `strugure`, and our `aggregate_by_family` puts it back — 749 and 12,034. Never load
  its `corola_lemma_freq_*` lists; the fix was the input file, not a reconciliation
  algorithm.
  What blocks it is the **time span**. CoRoLa covers 1945 to the present, so presence in it
  is not evidence of *current* use. Against CulturaX per token: `condițiune` 112.8×,
  `comisiune` 49.6×, `dorobanț` 41.1×, `iscăli` 15.7× — the first two are pre-1953-reform
  spellings, which a 1945-onward corpus necessarily contains. Wired into `modern_occ` for
  one build, it removed 35 words from the **relevant** seam, `birjă`, `dorobanț`, `vechil`,
  `dijmă` and `cocoană` among them: the project's best material, gone from the default view.
  The frequency lists carry no dates, so no post-2000 slice can be taken. Using CoRoLa needs
  a third panel with its own meaning ("attested in the reference corpus"), not a term added
  to the modern one. Pinned by `test_corola_is_not_in_the_modern_panel`.
- **Modern occurrence thresholds scale with the panel** (`scaled_modern_thresholds`).
  `MODERN_RARE_OCC`/`MODERN_ALIVE_OCC` were sampled against CulturaX at
  `CALIBRATION_MODERN_TOKENS`; an absolute count only means something relative to how much
  modern text was read, so adding a corpus without rescaling makes every word look more
  alive and pushes everything within the growth margin over a threshold. Any test pinned to
  the bare constants breaks the moment a corpus is added — derive the floor the way
  `tests/test_rescore._rare_floor()` does.
- **`subtitle_ro` is not a modern-usage signal — ~1/6th of it is folk-music television.**
  `process_subtitles.py` calls it "Digi24 news content"; the news is real but so is a large
  body of folklore programming, and the archaic vocabulary in it comes from *sung traditional
  lyrics*. Measured: clips carrying ≥3 genre markers are 15.6% of tokens but 27.5% of all
  shortlist-word occurrences, and **444 of the 2,446 shortlist words it attests appear only in
  those clips**. Scoring subtitle presence as "alive today" would rescue precisely the words
  the project exists to find. Nothing reads `subtitle_ppm` today; keep it that way until the
  folk clips are filtered out (`clipId` is the document unit, so this is doable) or the signal
  is inverted into a traditional-song flag. See `docs/corpus-expansion-plan.md`.
- **In `aggregate_by_family`, documents are share-scaled like occurrences, and taken as a
  max rather than a sum.** Both halves matter. Summing double-counts a document holding two
  forms of the same lemma; crediting documents all-or-nothing (the old `share >= 0.5` rule)
  gave a lemma that never majority-claims any of its forms zero documents while it still
  accumulated occurrences — and since `verdict()` reads `hist_occ >= 3 AND hist_docs >= 2`,
  the docs half silently vetoed the occ half. `văz` sat at 96 occurrences / 0 documents and
  came out `absent` in the relevant seam; 170 shortlist rows were in that state.
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
- **Generated artifacts go under `data/`** (gitignored). Never commit `*.db`, `*.csv`, or `data/` contents — except `data/word_ids.tsv` and `data/editorial.tsv`, both tracked on purpose (durable share ids; curator marks).
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
  registru.css    # "Registru" — patronview.com homage, mono headwords, ~620 lines
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

### The Filtre rail is type only — no skin gets a fill there

`.fs-pill` and `.fs-label` carry **no background and no border**, in any state, in any
skin. Checked is said with colour, weight, and at most an underline; the tick and the
verdict swatch inside the pill already state on/off on their own.

This is not a stylistic preference, which is why it is a rule rather than a note in one
skin: **most of these pills are checked when you arrive.** A fill on a checked pill is
therefore not a highlight, it is the background of the rail — ~25 filled rectangles
stacked in a 280px column, louder than the words the rail exists to filter. app.css took
the fill off `.fs-pill` for exactly this reason (the comment is at its declaration), and
every skin then put one back independently: `brutal` inverted both the pills and the
labels to ink blocks, `tezaur` filled them with the accent, `govuk` with `--surface`, and
`registru` made the labels into §-tags. All four are fixed; the trap is that each one
looks reasonable while you are writing that skin alone.

`.seg-opt` is the exception and is **not** covered by this. It is a segmented control with
no tick and no swatch, so the inverted block is the only thing saying which option is
live — and it is app.css's own treatment, identical under every skin.

### `.dex-link` is a chip in the dictionary row, not a button

The dexonline link sits at the end of `.fp-dicts`, shaped off `.dict-chip` — one more
dictionary reference among the names, which is what it is. It used to be a full-width
filled block at the foot of the panel, and **every skin independently made it louder**:
beton a red accent slab with a drop shadow, govuk the green GDS action button, registru a
black rectangle in mono caps, tezaur a filled pill. The result was that the loudest element
in the detail panel — ahead of the headword and the definition — was a link off the site.

That is the same trap as the Filtre rail above, and it has the same cause: each skin looked
reasonable while you were writing it alone. A big filled button invites being styled like a
primary action, so the fix is the shape, not four more overrides. All four skins now add at
most a colour to it (`registru` re-grounds because `--accent` there is the page's own ink,
which says nothing on a chip among chips).

**`.fp-dicts` renders even when a word has no `sources`**, because the link lives in it now;
wrapping the row in `if ($sources)` would drop the link for exactly the words whose
dictionary coverage is thinnest. Verified at 4.5:1 or better in all five skins × both themes.

`govuk.css` was built partly to find where the contract runs out. It did: the black
masthead, the yellow focus state, square marks, dotless tags, the green button and the
inset rule all needed component rules. That list, and the two hooks worth adding if a
third skin wants them, is in `docs/BACKLOG.md`.

`registru.css` is the first skin to repoint `--serif` at a monospace, and that turned up
two things worth knowing before the next one does it:

- **`--word-col` moves with the display font.** It was measured against Source Serif 4;
  Plex Mono is ~25% wider per character, and leaving the token alone puts ordinary
  headwords into the ellipsis. Treat it as part of the type decision, not a layout one.
- **A skin whose `--accent` is the page's own ink has to re-ground anything that fills
  with it inside a dark masthead.** `.joc-mode.active` paints itself `--accent`, which
  under this skin is black — on a black bar the selected game mode simply disappeared.
  `govuk` re-grounds the bar's controls for the same reason, so the list of what lives up
  there is worth copying wholesale rather than rediscovering.

Skin files load with an mtime query string, so edits show on plain reload. A stored skin
whose file has since been deleted falls back to `DEFAULT_SKIN` (the valid list is baked
into the pre-paint boot script).

## App shells vs documents — `body.page-doc`

`app.css` styles `body` as the **explorer's** shell: `height: 100vh; overflow: hidden`, a
flex column whose `#word-list-container` scrolls inside itself. Every page that loads
app.css inherits that, and for a page that is simply prose it means **the page cannot be
scrolled at all**.

`liste.php`, `lista.php` and `despre.php` therefore set `class="page-doc"` on `<body>`,
which restores `height: auto; min-height: 100vh; overflow: visible`. `index.php`,
`joc.php` and `stats.php` are real shells and keep the default (`stats.php` says so with
its own inline style).

**This hid for months because it only broke on desktop.** The `max-width: 768px` block
already relaxes `body { overflow: visible }`, so narrowing the window made the page scroll
and made the bug look like a rendering quirk rather than a missing class. If a new page is
mostly text, it needs `page-doc`; check it at a *wide* viewport, because the mobile one
will lie to you.

## Document pages — `assets/doc.css` + `assets/doc.js`

`despre.php` and `metodologie.html` share a sticky table of contents and a side-figure
layout. They have separate stylesheets and separate token blocks, but the token *names*
match (`--text`, `--accent`, `--sans`, `--mono`), so one file styles both without either
owning it.

The layout is a three-column grid — **TOC · content · gutter** — above 1080px, collapsing
to one column below. The third column is not decoration: it is where figures go, so a
screenshot sits beside the prose it illustrates instead of interrupting it. Figures
`float: right` with a negative right margin rather than occupying a grid cell, because the
text has to wrap back under a short figure and a figure has to sit next to *its* paragraph
rather than at whatever row boundary the grid picks.

Three things to know before touching it:

- **`doc.js` has two modes.** `metodologie.html` ships a hand-written `<ol>` whose wording
  is editorial (it shortens „Faza 2 — Validare diacronică" to „Faza 2"), so that list is
  left alone and only gets scroll-spy. `despre.php` has no list, so one is built from its
  headings. The contract is the same either way: a container with
  `data-toc="<selector for the content>"`.
- **Scroll-spy tracks the last heading *past* the reading line, not the intersecting
  one.** Sections here run from two paragraphs to forty; "is visible" marks several at
  once and flickers on every scroll tick.
- **A page adopting this must raise its `max-width`.** `metodologie.html` capped `.article`
  at 760px for a single column; as a grid that cap squeezes every track, and the page went
  from 13.5k to 30k pixels tall before it was raised to 1240px. Same reason `.despre-wrap`
  is 1240px.

## Page shell — header and footer partials

All five pages (`index`, `stats`, `joc`, `lista`, `liste`) draw the same two partials.
Before them, each page rolled its own bar and `stats.php` had no brand at all.

```php
<?php $page = 'stats'; $brand_tag = 'statistici'; require __DIR__ . '/api/_partials/header.php'; ?>
...
<?php require __DIR__ . '/api/_partials/footer.php'; ?>
```

**Identity plus travel at the top as far as the width allows; the overflow and the display
preferences at the bottom.** `header.php` is brand, a top nav, and whatever is genuinely
page-specific (search, count, play, filters). `footer.php` is GitHub plus the
text-scale/skin/theme toggles, since those are the same on every page. `cuvinte` (index)
appears in neither — the brand mark already links home on every page, so a nav entry to the
same place was pure redundancy. The split exists at all because the explorer's top bar was
already carrying brand, search, count, play and filters, and a full five-entry nav plus
three toggles is what broke it; `index.php` had already put its counts and legend in the
bottom bar, which is also thumb-reachable on a phone.

**`despre.php` is the nav's third entry, and it replaced `statistici` + `metodologie`
rather than joining them.** Three labelled entries competing for a phone bar is the
measurement this header/footer split was built on; a fourth broke it again. Both pages are
linked from `despre` instead — and a reader who wants the method has nearly always read the
overview first. They stay in `NAV_ITEMS` so `$page` still marks them `aria-current`; the
two partials name the keys they draw rather than diffing the const, or a diff would put
them silently back.

**`despre` is rendered by *both* partials, and app.css shows exactly
one — the header from 901px up, the footer below it.** They carry `top-nav-item--wide` /
`nav-item--wide` and there is no width at which they appear twice or vanish. The two
statements this reconciles are both true and neither was negotiable: a phone bar cannot
take four labelled nav entries (measured — that is what produced this split in the first
place), and burying the two pages that *explain the project* in a footer under the display
toggles hid them from the desktop reader who would actually follow them. `joc` and `liste`
stay in the header at every width; they are the two places people jump to mid-browse.

901px is reused deliberately: it is already the footer nav's label/icon breakpoint, so
there is one crossover in `app.css` to keep in step rather than two that can drift.
**`.top-nav-item--wide` must stay declared *after* `.top-nav-item`** — both are one class,
so the cascade falls to source order, and above it the `display: none` silently loses and
all four entries render on a phone.

**Both partials now read `$page`**, so set it *before* requiring `header.php` (not only
before `footer.php` as it used to be) — it marks the matching entry `aria-current="page"` in
both the top nav and the footer nav. `lista.php` still deliberately leaves it unset: it is
not `liste.php`, so nothing in either nav should render as current and stop being clickable.

`header.php` takes five optional slots, all raw HTML strings, so a caller can build one with
`ob_start()` and keep writing ordinary markup: `$header_nav_extra` (appended inside the top
nav, after joc/liste — the explorer's `?` shortcuts/legend link, index-only), `$header_center`
(the explorer's collapsible search — a magnifier `.search-toggle-btn` that reveals `#search`
inside `.search-wrap`, see `openSearch()`/`closeSearchIfEmpty()` in `app.js`), `$header_tools`
(spinner + result count; joc's modes and score), `$header_after` (the filter button, which has
to stay last). `footer.php` takes `$footer_left` (the explorer's counts), `$footer_extra` (the
colour legend) and `$footer_tools` (the explorer's cloud/table view toggle — index-only,
everything else in the footer is universal) plus `$page`. The explorer's feed button
(`enterFeed()`) is currently `hidden` in the markup rather than wired to either bar — like
the dormant 🎲 `surpriseWord()` button beside it, it has no home yet, not no code.

Five things to preserve:

1. **`NAV_ITEMS` lives in `_lib.php`**, not in either partial — a `const` in an included
   file cannot be guarded against a second include, and it sits with `VERDICTS`/`TIERS`
   as the other list of user-facing strings drawn on every page. `header.php` loops the
   four keys it draws with their width class; `footer.php` loops
   `array_diff_key(NAV_ITEMS, array_flip(['index','joc','liste']))` and tags each one
   `nav-item--wide`. Both read path/icon/label from `NAV_ITEMS` rather than restating them.
2. **The current page stays an `<a>`** with `aria-current="page"` and an accent underline.
   As a `<span>` it stopped matching every skin's `#status-bar a` rule and needed its own
   colour — and `var(--text)` is a *page*-ground token, which on beton's ink footer meant
   near-black on black. Never give this bar a colour of its own.
3. **Every nav entry in either bar keeps an icon and a label.** Below 900px labels are
   hidden and the icons carry the bar alone, so an entry without one would vanish — which
   is also why the top nav is down to `joc` + `liste` there rather than shrinking four
   entries to fit. Above 901px all four keep icon *and* label; a bare glyph row beside the
   wordmark is the one thing that bar has space to avoid.
4. **On a phone, an open definition hides both bars.** `app.js` puts `detail-open` on
   `<body>` when the sheet opens and takes it off in `closePanel()`; only the ≤768px block
   acts on it, so a desktop window narrowed with the panel up lands in the right state with
   no resize listener. The backlog asked instead for the sheet capped at 40% — it is still
   60vh, because 40% of a phone does not hold a definition (measured: `poporanism` alone
   overflows it) and the definition is what you opened. The room comes from the bars: ~186px
   of a 812px screen, neither of which you can act on while reading. Visible list goes from
   ~139px to ~325px and the sheet keeps its height. **With the header gone, `.fp-close` is
   the only way out** — hence the second glyph in `detail.php`: a ✕ top-right on desktop, a
   ← in the top-left corner at a 44px target on a phone. Both are in the markup with app.css
   showing one, rather than a CSS `content` swap that assistive tech cannot see.
5. **`govuk` and `registru` force `.brand-bar` black in both themes**, so anything living in
   it needs on-bar re-grounding in those two skin files (`--gv-on-bar`/`--rg-on-bar`) —
   `.top-nav-item`, `.shortcuts-link` and `kbd` all needed it when they moved up from the
   footer, a page-ground surface neither skin forces dark. The reverse also holds: a
   control that moves *out* of `.brand-bar` (scale/skin/theme, feed/view-toggle, all now in
   the footer) should have its now-dead `.brand-bar`-scoped rules removed from both files,
   not left to rot — exactly the risk the skins section above already names for component
   rules in general.

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

**Marking advances to the next word — all four marks, the same way.** `advanceAfterMark()`
in `app.js`, called from both handlers in `store.js`. Three properties, each of which has a
reason someone will otherwise remove:

- **All four, not just the hiding ones.** The first cut advanced only on `meh`/`ascunde`, on
  the argument that `fav` and `lol` are stackable on one word. That was overruled and the
  reasoning is worth keeping: marking is a triage loop, one mark per word is the intended
  interaction, and a loop where three keys move you on and one does not is a loop you have to
  think about. Consistency beats the rare double-tag.
- **Applying advances; removing does not.** Un-favouriting is a correction — advancing would
  take you off the word you just came back to fix.
- **`removesRow` is the only branch.** `meh`/`ascunde` also pop the row out, so the next row
  must be resolved *before* the fade and re-found by element after it: resolving it later
  races the animation, and taking it by index earlier leaves `selectedIdx` off by one the
  moment the row goes — and that is the number `j`/`k` read. On the last row, fall back to
  the previous word when the row is being removed and stay put when it is not; never wrap to
  the top, which silently restarts the list.

Custom tags typed into `#tag-input` deliberately do not advance — it would pull focus out of
the field mid-typing.

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
