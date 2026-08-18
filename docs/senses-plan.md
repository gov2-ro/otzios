# Full definitions — the `sinteză` tree, from the dump

**Status:** built 2026-08-18, the same day this was written. Per-sense synonyms (scoped
out below, §"Out") followed the same day, once a real gap (`zăticni` sense `1.`, no free
text, dropped entirely) showed the `Relation.type` question was worth settling rather than
deferring. See `docs/BACKLOG.md` ("Enhancements") for what shipped and what's still open
(`MeaningSource` attribution).
**Goal:** show every sense of a word, not just the first — plus its citations,
sub-senses, expressions and etymon — the way dexonline's „sinteza definițiilor" tab does.

Read `CLAUDE.md` first. This plan touches `build_ui_db.py`, `ui.db` and the detail
panel, all of which have invariants recorded there.

---

## 1. The problem, in one word

`bidinea` on voroave.ro reads:

> Pensulă mare, de obicei rotundă ( cu coadă lungă), pentru văruit.

`bidinea` on dexonline reads that, **plus** three Delavrancea/Pas/Creangă citations,
**plus** a second sense („2. *vulgar* Organ genital feminin."), **plus** the etymon
(turkish *badana*). We ship sense 1 of *n* and nothing else.

This is not a scraping gap. It is a **discard**: the text is in the dump and we already
stream past it.

---

## 2. What the dump actually holds — verified, do not re-derive

`data/dictionaries/dex-database.sql`, measured 2026-08-18.

### The chain

```
Tree.description  ──normalize()──►  the headword
Tree.id           ──►  Meaning.treeId
```

That is the whole join. **No `Entry`/`EntryDefinition` hop is needed** — unlike
`extract_dcr.py`, which starts from a `Definition.sourceId` and therefore has to walk
`Definition → EntryDefinition → TreeEntry → Meaning`. Here we start from the word, and
`Tree.description` *is* the word.

### Column order (from `data/dictionaries/dex-schema.sql`)

```
Tree     :  id(0)  description(1)  descriptionSort(2)  status(3)  createDate(4)  modDate(5)
Meaning  :  id(0)  parentId(1)  type(2)  displayOrder(3)  breadcrumb(4)
            userId(5)  treeId(6)  internalRep(7)  createDate(8)  modDate(9)
```

### `Meaning.type`

Matches dexonline's own `Meaning::TYPE_*` constants. Counts are **over the 13,712 trees
belonging to shortlist words**, not the whole table.

| type | meaning | rows | example |
|---|---|---|---|
| 0 | sense | 18,459 | `bc='2.'` „Organ genital feminin." |
| 1 | etymology (the etymon itself) | 11,602 | `badana`, `zaptiye`, `eccum-*hacce` |
| 2 | citation | 16,843 | „…Vino încoa și pune mîna pe bidinea… PAS, L. I 97." |
| 3 | comment | 182 | `Ac`, `cl`, `q` — short, mostly noise |
| 4 | compound | 240 | „(Mai ales la pl.) Grăunte mărunt de plumb…" |
| 5 | expression | 809 | „Păr pergamut = varietate de păr cu fructe galbene…" |

### Coverage over the 18,270 shortlist words

| | words |
|---|---|
| have a `Tree` row | 13,324 |
| have ≥1 `Meaning` row | 10,800 |
| of those, already have a `definitions.db` entry | 10,482 |
| of those, have **no** `definitions.db` entry (pure gain) | 318 |
| **have ≥2 senses** (`type=0`, any depth, non-empty) | **3,394** |
| have citations | 6,856 words / 16,843 quotes |
| `Tree` row but zero meanings | 2,524 |
| no `Tree` row at all | 4,946 |

**7,470 words end up with no senses and must keep today's flat `definition`.** That is
41% of the list — the two-shapes case is the normal case, not an edge case.

### The real `bidinea` rows

Keep these; they are the fixture for the renderer test.

```
id=20406   parent=0       type=0  bc='1.'  Pensulă mare, de obicei rotundă (cu coadă lungă), folosită pentru văruit.
id=191407  parent=20406   type=2  bc=''    Văruiau cîțiva inși cotețele găinilor – Vino încoa și pune mîna pe bidinea și tu! i-au poruncit. PAS, L. I 97.
id=191408  parent=20406   type=2  bc=''    În via părăginită iarba... acoperă răzoarele... DELAVRANCEA, S. 221.
id=472138  parent=20406   type=2  bc=''    Barbe cît badanalele de mari. (CR.).
id=20407   parent=0       type=1  bc=''    badana
id=20406   parent=0       type=0  bc='1.'  ← (see above)
id=472139  parent=0       type=0  bc='2.'  Organ genital feminin.
```

Note `type=2` citations hang off the **sense's** id via `parentId`, and the etymon
(`type=1`) hangs off the tree root (`parentId=0`).

### Meaning-level tags — already extracted

`ObjectTag.objectType = 3` keys on `Meaning.id`. **`extract_taxonomy.py` already loads
this**, so `lexemes.db` has it today:

```sql
-- lexemes.db
SELECT t.value
  FROM ObjectTag ot JOIN Tag t ON t.id = ot.tagId
 WHERE ot.objectType = 3 AND ot.objectId = :meaning_id;
```

196,888 rows. Top values: `limba franceză` 47,334 · `figurat` 9,949 · `limba latină`
9,568 · `vezi` 8,589 · `regional` 8,022 · `rar` 6,631 · `învechit` 5,836 · `cf.` 5,651.
This is where the `vulgar` chip on `bidinea`'s sense 2 comes from.

**Do not confuse these with `words.dex_register`.** CLAUDE.md's `dex_pos` gotcha says
meaning-level tags „cover ~3% of the list and bleed across variants" — true *as a
word-level* signal, which is why POS comes from `Lexeme.modelType`. Attached to the
sense they came from, they are exactly right. Keep them per-sense; never roll them up
onto the word.

---

## 3. Scope

**In:**

- `extract_meanings.py` → `data/processed/meanings.db` (new script, no HTTP)
- `senses` + `sense_citations` tables in `ui.db`, filled by `tools/build_ui_db.py`
- `tools/migrate_ui_db_senses.py` — back-fill an existing `ui.db`
- detail-panel rendering of the tree, with the flat fallback
- `tests/test_extract_meanings.py`, `tests/test_senses.js`

**Out — do not do these in this pass:**

- **Anything over HTTP.** The whole point is that this is free and local.
- **Per-sense synonyms.** The `Relation` table (162,237 rows, `meaningId → treeId`) is
  what draws „sinonime: meseleu mătură perie…" under sense 1. Its `type` codes are
  **unverified**. `words.synonyms` already exists from `scrape_synonyms.py` and is
  word-level; wiring a second, sense-level source is its own decision.
- **Touching `words.definition`.** See §7.
- **Per-source attribution.** `MeaningSource` (924,628 rows) could label each sense with
  the dictionary it came from. Interesting, not needed to render the tree.
- **Non-shortlist words.** `ui.db` holds the 18,270; keep it that way.

---

## 4. Phase 1 — `extract_meanings.py`

New top-level script, beside `extract_definitions.py` and `extract_dcr.py`. One script
per pipeline stage (CLAUDE.md conventions).

### Reuse, don't rewrite

```python
from extract_dcr import _row_walker, _clean
from extract_definitions import SQL_PATH, _clean_markup, _read_quoted_or_null
from dump_parser import normalize
```

- `_row_walker(line, prefix)` — the quote-aware multi-row `INSERT` scanner. It filters
  `None` out of the field list, so **always guard on `len(row)`** before indexing
  (`>= 2` for `Tree`, `>= 8` for `Meaning`). Verified index-stable across all 454,993
  `Meaning` rows; empty strings survive as `''` and a bare `NULL` arrives as the string
  `'NULL'`.
- `_clean(text)` — `_clean_markup` plus: strips `[123]` cross-tree pointers and `__`
  render artifacts, collapses whitespace. Already correct for this data.

### Two passes, in this order

Two, not one: `Meaning` is 454,993 rows and holding all of it in memory to filter
afterwards is wasteful when pass 1 gives us the 13,712 tree ids we care about.

```
Pass 1  INSERT INTO `Tree` VALUES        →  {normalize(description): [tree_id]}
                                            restricted to shortlist words
Pass 2  INSERT INTO `Meaning` VALUES     →  rows whose treeId is in that set
```

Each pass is ~90s over the 1.65 GB dump. Print progress every 200k lines, the way
`extract_definitions.py` does.

Input word list: `data/processed/forgotten_words_shortlist.csv`, column `word`,
normalized through `dump_parser.normalize`. Take `--shortlist` as a flag with that
default.

### Output — `data/processed/meanings.db`

```sql
CREATE TABLE meanings (
    meaning_id     INTEGER PRIMARY KEY,
    word           TEXT    NOT NULL,   -- normalize(Tree.description)
    tree_id        INTEGER NOT NULL,
    parent_id      INTEGER NOT NULL,   -- 0 = attached to the tree root
    type           INTEGER NOT NULL,   -- 0 sense 1 etym 2 citation 3 comment 4 compound 5 expression
    breadcrumb     TEXT    NOT NULL DEFAULT '',
    display_order  INTEGER NOT NULL,
    text           TEXT    NOT NULL    -- _clean()'d; may be ''
);
CREATE INDEX idx_meanings_word ON meanings(word);
CREATE INDEX idx_meanings_tree ON meanings(tree_id);

CREATE TABLE meaning_tags (
    meaning_id  INTEGER NOT NULL,
    tag         TEXT    NOT NULL,
    PRIMARY KEY (meaning_id, tag)
);
```

`meaning_tags` is filled in a third step from **`lexemes.db`**, not the dump — the join
is already there (§2). If `lexemes.db` is missing, warn and leave the table empty
rather than failing; the senses are the deliverable, the chips are garnish.

Write **rows with empty `text` too.** They are structural (§5) and the consumer needs
to see them to decide; throwing them away in the extractor would make the decision
un-revisitable without another 3-minute scan.

### CLI

```bash
python extract_meanings.py                 # full run, ~3 min, no HTTP
python extract_meanings.py --limit 200     # first N shortlist words, for a smoke test
python extract_meanings.py --stats         # counts only, write nothing
```

Print at the end: trees found, meanings kept, words with ≥1 sense, words with ≥2 senses,
words with citations, and the count of empty-text senses. Those numbers are the
regression check — they should match §2.

---

## 5. Phase 2 — `senses` in `ui.db`

### Ordering: parse the breadcrumb, do not sort it as text

Every `type=0` row has a non-empty breadcrumb (`1.`, `1.1.`, `2.`, `1.1.1.` — verified,
0 exceptions). It is the display number **and** the tree position, so `parentId` is not
needed for ordering senses.

```python
def bc_key(bc: str) -> tuple[int, ...]:
    return tuple(int(p) for p in bc.strip('.').split('.') if p.isdigit())
```

Sorting `'10.'` as a string puts it between `'1.'` and `'2.'`. Depth is
`len(bc_key(bc))`, so `1.` is depth 1 and `1.2.` is depth 2.

Compounds (`type=4`) and expressions (`type=5`) have **empty** breadcrumbs. They sort
after all senses, ordered by `display_order`, and carry their own `kind`.

### Empty senses: drop the row, keep the subtree

3,627 of 18,459 `type=0` rows have `internalRep = ''`. They are placeholders — a
numbered node whose text was never written, whose children hold the content. Rule:

- A sense with empty text is **not emitted**.
- Its sub-senses are emitted normally; their own breadcrumbs (`1.1.`, `1.2.`) still read
  correctly on their own, so a gap at `1.` is invisible to the reader.
- Its citations (`type=2` children) are **re-attached to the nearest non-empty
  ancestor**; if there is none, dropped. Never orphan a quote onto the word as a whole —
  a citation with no sense above it reads as an example of the wrong meaning.

### Homonyms: 388 words have two trees

In every sample checked the second tree has **zero** meanings (`broatec` 6/0, `afiniș`
4/0, `hăldan` 2/0) — an unstructured duplicate entry. Rule: merge all of a word's trees,
ordered by `tree_id`, and number `ord` sequentially across them. Breadcrumbs may then
repeat (`1.` twice) if both trees turn out non-empty. **Print how many words that
actually happens to** at build time; if it is more than a handful, come back and decide
properly rather than patching it silently.

### Schema

```sql
CREATE TABLE senses (
    word        TEXT    NOT NULL,
    ord         INTEGER NOT NULL,   -- 0-based display order
    breadcrumb  TEXT    NOT NULL,   -- '1.', '1.1.', '' for compound/expression
    depth       INTEGER NOT NULL,   -- 1 for '1.', 2 for '1.1.'; 1 for kind != 'sense'
    kind        TEXT    NOT NULL,   -- 'sense' | 'compound' | 'expression'
    text        TEXT    NOT NULL,
    tags        TEXT,               -- pipe-delimited, per CLAUDE.md's taxonomy convention
    PRIMARY KEY (word, ord)
);

CREATE TABLE sense_citations (
    word       TEXT    NOT NULL,
    sense_ord  INTEGER NOT NULL,
    ord        INTEGER NOT NULL,
    text       TEXT    NOT NULL,
    PRIMARY KEY (word, sense_ord, ord)
);
```

Two tables rather than a `\n`-joined column: citations are the bulk of the payload and
the panel collapses them, so the query that renders the senses should not have to carry
them. `type=3` (comment, 182 rows) is **not** emitted — it is `Ac`, `cl`, `q`.

### The etymon → one new column on `words`

`type=1` rows hold the actual source word (`badana`, `zaptiye`). `words.dex_etymology`
already exists and holds the *language* (`limba turcă`), from the taxonomy tags. Add:

```sql
dex_etymon TEXT   -- pipe-delimited; 'badana' for bidinea
```

The panel already renders an etymology chip; this gives it something to say beyond the
language name. One column, not a table — the counts are small and it is word-level.

### Where it goes in `build()`

`tools/build_ui_db.py`, in this order:

1. After `merge_synonyms(conn, SYNONYMS_PATH)` — so senses land with the other merges.
2. **Before every `mark_*` step.** They read `words.definition`, which this pass does
   not touch, so strictly it does not matter — but keeping merges before marks is the
   file's existing shape and `mark_deverbal_nouns()` must stay last regardless.

New function, mirroring `merge_synonyms`'s signature:

```python
def merge_senses(conn: sqlite3.Connection, meanings_db: Path) -> None:
```

If `meanings.db` is absent: print `  (meanings DB not found, skipping: …)` and return.
The build must not require it — same contract every other optional merge in that file
has.

### Migration

`tools/migrate_ui_db_senses.py`, following `tools/migrate_ui_db_dex_variants.py`:
`CREATE TABLE IF NOT EXISTS`, `ALTER TABLE words ADD COLUMN dex_etymon` guarded on
`PRAGMA table_info`, then the same `merge_senses()` imported from `build_ui_db`.
**Idempotent** — a second run must produce a byte-identical file. That is the cheapest
check that the ordering rules are deterministic.

### Size

~18k sense rows + ~17k citation rows ≈ 4–6 MB on a 20 MB `ui.db`. Measure and report it;
if it lands materially above that, say so before shipping — `public/data/ui.db` is
served by Apache behind a `.htaccess` deny and is downloaded on every deploy.

---

## 6. Phase 3 — rendering

### `api/word.php`

Two extra queries after the `words` row, both keyed on `word`:

```php
$senses = db()->prepare('SELECT * FROM senses WHERE word = ? ORDER BY ord');
$cites  = db()->prepare('SELECT * FROM sense_citations WHERE word = ? ORDER BY sense_ord, ord');
```

Group the citations by `sense_ord` in PHP and pass both into `render('detail.php', …)`.
Guard both in a `try`/`catch` or a table-exists check: a deployed `ui.db` built before
this change has neither table, and the panel must still open. **`api/word.php` stays a
bare `WHERE word = ?` with no filter anywhere near it** — that is the invariant
`tests/test_share_view.js` §1 pins.

### `public/api/_partials/detail.php`

Today:

```php
<?php if ($w['definition']): ?>
<div class="definition-text"><?= e($w['definition']) ?></div>
```

Becomes: **if `$senses` is non-empty render the tree; otherwise fall back to
`$w['definition']` exactly as now.** 7,470 words take the fallback — it is not a
degraded path, it is half the site.

Shape:

- An ordered list. `breadcrumb` is the visible number (it is already `1.` / `1.1.`, so
  print it, don't regenerate it). Indent by `depth` with a CSS custom property, not a
  class per level.
- Per-sense `tags` render as the existing `.detail-tag` chips, inline before the text —
  that is where dexonline puts `vulgar` and where the reader expects it.
- `kind = 'expression'` and `kind = 'compound'` get a visually distinct block after the
  senses, since they are phrases rather than meanings of the headword alone.
- Citations render small and italic under their sense, collapsed behind a `<details>`
  when there is more than one. **Keep the trailing attribution** („PAS, L. I 97.") — it
  is what makes a quote evidence rather than decoration. This is the opposite of
  `share_excerpt()`, which strips it *for a 160-character preview*; both are right for
  their surface.

### Skins — three rules from CLAUDE.md that apply directly

1. **The disclosure is a *state*.** If `<details>`/`<summary>` gets an open/closed
   appearance, style it at ≥ (0,3,0) — e.g. `.fp-senses .sense-cites[open] > summary` —
   or `[data-skin="x"] summary` will silently repaint it. This is the fourth instance of
   the pattern documented at `.fp-btns .qt-btn.active`; read that section before
   styling.
2. **Colours in both theme blocks.** Anything new (the citation's muted ink, the sense
   number) is a token declared under `:root` *and* the dark block, or it disappears at
   night in whichever skin you were not looking at.
3. **Screenshot all six skins.** `paper`, `beton`, `guvern`, `registru`, `tezaur`,
   `velin`, in both themes. The failure mode named all over CLAUDE.md is that each skin
   looks reasonable while you are writing it alone.

Also check the phone: `.fp-body` scrolls inside a 60vh sheet, and `zapciu` with 3 senses
and 6 quotes is the longest thing that panel has ever held. It should scroll, not clip —
verify, don't assume.

---

## 7. Invariants — break any of these and something else breaks silently

1. **`words.definition` is not touched, not reformatted, not replaced.** Three flag
   rules pattern-match on it — `mark_diminutives` (`_DIMINUTIVE_DEF_RE.search`),
   `pointer_target` (`_POINTER_DEF.match`, anchored) and `mark_deverbal_nouns`
   (`_DEVERBAL_DEF_RE.match(definition.split('|')[0])`) — and `share_meta()` /
   `share_excerpt()` build every link preview from it. Senses are **additive**. If they
   ever replace it, all four have to be re-measured, and the „vezi X" carve-out under
   the `dex_variant` flag has to be re-argued from scratch.
2. **`share_excerpt()` keeps reading `definition`,** so previews stay one sentence. A
   preview is 160 characters; a three-sense entry is not a preview.
3. **The tree is the *entry* tree.** It merges every dictionary that defines the word —
   the caveat `extract_dcr.py`'s docstring already states, and the same bleed CLAUDE.md
   records for `scrape_definitions.py` under `dex_variant` („`sofragerie` arrives
   carrying `sufragerie`'s full DLRLC entry"). More senses makes it *more* visible, not
   less. The detail panel already names the living twin for a flagged variant; that line
   must render **above** the senses, not below them.
4. **Meaning-level tags stay on their sense.** Never merge them into
   `words.dex_register` — see the `dex_pos` gotcha.
5. **`public/data/ui.db` is rebuilt from scratch every time**, so `data/word_ids.tsv`
   must still show additions only afterwards: `git diff --numstat data/word_ids.tsv`.
   Nothing here touches the `words` row set, so it should be a no-op — check anyway.

---

## 8. Tests

### `tests/test_extract_meanings.py` — offline, fixture-driven

Follow `tests/test_extract_dcr.py`: hardcode the real rows so the renderer can change
without a 1.65 GB rescan. Use the `bidinea` rows in §2 verbatim.

- `bidinea` → 2 senses; sense 2's text is exactly `Organ genital feminin.`; sense 1
  carries 3 citations, sense 2 carries none; the etymon is `badana`.
- `zapciu` → 3 senses, ≥6 citations, all attached to the right sense
  (4 → `1.`, 1 → `2.`, 1 → `3.`).
- `bc_key` sorts `1.`, `2.`, `9.`, `10.`, `1.1.` correctly — pin `10.` after `9.`
  explicitly, it is the one a string sort gets wrong.
- An empty-text sense with children is dropped, its sub-senses survive, its citations
  re-attach to the nearest non-empty ancestor.
- A `type=3` comment row is not emitted.
- A word with a `Tree` row and no meanings yields nothing and does not raise.

### `tests/test_senses.js` — against a running server

Follow `tests/test_share_view.js` (`OTIOS_TEST_URL`, sample words read out of the API
rather than hardcoded where possible).

- `?word=bidinea` renders 2 numbered senses and a `vulgar` chip on the second.
- A word with no senses (pick one from the API, do not hardcode — a rebuild reflags
  words) renders the flat `.definition-text` and no empty `<ol>`.
- `api/word.php` still answers 200 with a `ui.db` that has no `senses` table.
- The panel does not overflow horizontally at 320px.

### Regression

`python -m pytest tests/` and the existing js suites — in particular
`tests/test_share_meta.js` and `tests/test_rescore.py`, which are the two that would
catch a `definition` column that moved when it should not have.

---

## 9. Order of work

1. `extract_meanings.py` + `tests/test_extract_meanings.py`. Run it; check the printed
   counts against §2. **Stop here and report the numbers** — if they disagree with §2,
   something changed in the dump and the rest of the plan needs re-reading.
2. `merge_senses()` in `build_ui_db.py` + `tools/migrate_ui_db_senses.py`. Migrate a
   copy of the current `ui.db`, run the migration twice, diff the two outputs — they
   must be byte-identical.
3. `api/word.php` + `detail.php` + `app.css`. Screenshot 6 skins × 2 themes ×
   {desktop, 390px}.
4. Full rebuild, `git diff --numstat data/word_ids.tsv`, report the `ui.db` size delta.
5. CLAUDE.md: a section under **Key data contracts** for `meanings.db` and the `senses`
   tables, and the §7 invariants. Per **Process notes**: an entry in
   `docs/activity-history.md`, and anything deferred (per-sense synonyms, `MeaningSource`
   attribution) into `docs/BACKLOG.md`.

---

## 10. A side effect worth knowing about

`docs/BACKLOG.md`'s largest open item is the thin historical corpus, and one of the
options it lists is *"the DLR/DLRLC literary citations already embedded in the dump's
definition text (`GALAN,`, `CARAGIALE`, `DUMITRIU, N. 122`) — a free, dated, in-repo
citation corpus."*

Those citations do not need mining out of prose. **`Meaning.type = 2` rows *are* them**,
one per row, attribution intact — 16,843 for shortlist words alone, and the full table
is much larger. `extract_meanings.py` produces them as a by-product.

Do not act on that here. Two things have to be settled first, and both are corpus
questions rather than UI ones:

- The quotes are **selected because they attest the headword**, so counting the headword
  in its own citations is circular. Their value is as evidence for the *other* words in
  the sentence.
- The attribution is an abbreviation (`PAS, L. I 97.`), not a date. Turning it into one
  needs a lookup table over DLR's source sigla.

Logged separately in `docs/BACKLOG.md` under **Enhancements**.
