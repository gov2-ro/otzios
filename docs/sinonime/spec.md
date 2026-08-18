# Sinonime — implementation spec

*Build order, exact schemas, and the acceptance tests. Written so it can be executed
without re-deriving anything: every number you need to check your work against is stated
inline. Read [`findings.md`](findings.md) for where those numbers came from, and
[`escalate.md`](escalate.md) for what to stop and ask about.*

**What this builds:** a Romanian **writing aid** — type a word, get alternatives you could
actually use, ranked by how alive they are in modern Romanian. No definitions. Lives
alongside the oțios explorer, reusing its shell, but with its own database and no
dependency on `app.db` or user identity, so it can be lifted into its own deploy later.

---

## Decisions already taken — do not revisit

| | |
|---|---|
| **Keep DEX's sense structure** in storage | Flattening is lossy one-way. `findings.md` §7. |
| **Rank and dim dead words, never hide them** | An archaic synonym is sometimes what the writer wants, and a hidden word is an invisible false negative. |
| **Ship on the free sources, then scrape the gaps** | Schema is identical either side, so the scrape is a data refresh, not a rewrite. |
| **`Tree` co-membership is its own relation type** | Noisier than the `Relation` edges; keep it separable. |
| **Own DB, own lib file, no `app.db`/auth** | Public read-only tool; lifts out cleanly. |

Phase 3 stops at file structure. **All visual design is out of scope** — see
`escalate.md`.

---

## Phase 1 — `extract_relations.py`

New top-level extractor, house style. Template: **`extract_inflected_forms.py`** — copy
its shape (long docstring stating *why* with measured numbers, module-level path
constants, `argparse` with `--dump` / `--out` / `--limit`, `build()` returning a stats
dict, `main()` printing the counts to stderr, `PRAGMA journal_mode=OFF` +
`synchronous=OFF`, delete-and-rebuild the output file, `BATCH = 50_000` inserts).

**Use `dump_parser`** (`parse_tuples`, `strip_line_prefix`, `normalize`). Do **not** use
`parse_mysql_insert` from `extract_lexemes.py` — its regex splitter is documented as
dropping ~48k of 365,869 `Lexeme` rows and column-shifting 648 more.

### Output: `data/processed/relations.db`, self-contained

One pass over the dump, ~15 s warm. Six tables:

```sql
CREATE TABLE relation   (id INTEGER PRIMARY KEY, meaning_id INTEGER, tree_id INTEGER, type INTEGER);
CREATE TABLE tree       (id INTEGER PRIMARY KEY, description TEXT);
CREATE TABLE meaning_tree(meaning_id INTEGER PRIMARY KEY, tree_id INTEGER);
CREATE TABLE tree_entry (tree_id INTEGER, entry_id INTEGER, entry_rank INTEGER);
CREATE TABLE entry_lexeme(entry_id INTEGER, lexeme_id INTEGER, lexeme_rank INTEGER, main INTEGER);
CREATE TABLE lexeme     (id INTEGER PRIMARY KEY, form_norm TEXT, model_type TEXT, description TEXT);
CREATE TABLE meaning_tag(meaning_id INTEGER, tag TEXT);   -- ObjectTag objectType=3 ⋈ Tag.value

CREATE INDEX ix_rel_meaning  ON relation(meaning_id);
CREATE INDEX ix_te_tree      ON tree_entry(tree_id);
CREATE INDEX ix_el_entry     ON entry_lexeme(entry_id);
CREATE INDEX ix_mtag_meaning ON meaning_tag(meaning_id);
```

**Why self-contained rather than reusing `lexemes.db`.** `extract_taxonomy.py` already
puts `MeaningTree`, `TreeEntry`, `EntryLexeme`, `Tag` and `ObjectTag` there, and it is
tempting to read them. But `lexemes.db.Lexeme` was written by the lossy regex path — it
holds 317,688 rows against `inflected_forms.db`'s 317,721, and CLAUDE.md flags the gap.
One extra pass costs 15 seconds and removes the dependency entirely. Duplicating five
small tables is the cheaper mistake.

### Parsing notes, per table

| dump table | how | expect |
|---|---|---|
| `Relation` | int-only tuples, a plain regex is safe: `\((\d+),(\d+),(\d+),(\d+),\d+,\d+\)` — columns are `id, meaningId, treeId, type` | **158,860** rows |
| `Tree` | `parse_tuples(body, 1)`; `description` is a quoted string | **226,424** rows |
| `Meaning` | `parse_tuples(body, 6)` — take only `id` (0) and `treeId` (6); `internalRep` is a longtext and `max_index` stops before it | **454,993** rows |
| `TreeEntry` | int-only regex; `id, treeId, entryId, treeRank, entryRank` | **240,011** rows |
| `EntryLexeme` | int-only regex; `id, entryId, lexemeId, entryRank, lexemeRank, main` | ~519k ids, ~322k rows |
| `Lexeme` | `parse_tuples(body, 14)` — `id` (0), `formNoAccent` (2), `description` (5), `modelType` (14) | **317,721** rows |
| `ObjectTag`, `Tag` | int-only / quoted; keep only `objectType = 3` | 196,888 kept |

`form_norm` is `dump_parser.normalize(formNoAccent or form)`.

### Acceptance for Phase 1

`relation` type counts must be exactly **152,023 / 5,216 / 1,547 / 74** for types
1 / 2 / 3 / 4. Anything else means the parse is wrong; do not proceed.

**Refuse `data/dictionaries/dex-sample-cleaned.sql`.** It has zero `INSERT INTO
\`Relation\`` lines and would silently produce an empty thesaurus. Exit non-zero with a
message naming the file. (`dex-database-sample.sql` does have them, and is fine for smoke
tests.)

---

## Phase 2 — `tools/build_syn_db.py` → `public/data/syn.db`

Reads `data/processed/relations.db`, `corpus_frequencies.db`, `inflected_forms.db` and
`synonyms.db`. **Must not read or write `ui.db`, `app.db`, or anything else in the
existing pipeline.**

### Schema — exact; changing it invalidates the measured sizes

```sql
CREATE TABLE word(
  id   INTEGER PRIMARY KEY,
  form TEXT    NOT NULL,      -- Lexeme.formNoAccent: the only display string
  pos  TEXT,                  -- from Lexeme.modelType
  band INTEGER NOT NULL       -- 0..7 modern currency; 0 means absent, and is a real value
);
CREATE TABLE key(             -- every spelling that should resolve to a headword
  k       TEXT    NOT NULL,   -- normalize_diacritics()-folded
  word_id INTEGER NOT NULL,
  PRIMARY KEY(k, word_id)
) WITHOUT ROWID;
CREATE TABLE sense(           -- one row per DEX Meaning carrying a relation
  id    INTEGER PRIMARY KEY,
  label TEXT,                 -- Tree.description
  reg   INTEGER NOT NULL DEFAULT 0    -- register bitmask, see below
);
CREATE TABLE sense_word(sid INTEGER, word_id INTEGER,
  PRIMARY KEY(sid, word_id)) WITHOUT ROWID;      -- the sense's own word(s)
CREATE TABLE edge(sid INTEGER, word_id INTEGER, t INTEGER, src INTEGER NOT NULL DEFAULT 0,
  rank INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(sid, word_id, t)) WITHOUT ROWID;   -- the related words
CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);   -- build date, source counts, band edges

CREATE INDEX ix_word_form    ON word(form);
CREATE INDEX ix_sense_word_w ON sense_word(word_id);
CREATE INDEX ix_edge_rank    ON edge(sid, t, rank);
```

`edge.t`: **1** synonym · **2** antonym · **3** diminutive · **4** augmentative ·
**5** tree co-membership.
`edge.src`: **0** `Relation` · **1** scraped (Seche) · **2** `Tree` co-membership.

`sense.reg` bitmask, from `meaning_tag`: bit 0 `regional` · 1 `învechit` · 2 `rar` ·
3 `familiar` · 4 `popular` · 5 `peiorativ` · 6 `figurat` · 7 `argou` · 8 `livresc`.

### Build rules — each has a measurement behind it

1. **Expand a tree to `EntryLexeme.main = 1` lexemes only, for *results*.** Unfiltered
   the join returns misspellings and variants: `veteaz`, `lace`, `tradafir`, `pociganie`.

2. **Non-main lexemes still become lookup keys.** `nalt` is filed under `înalt`; someone
   typing the variant has to land somewhere. That is ~44k rows in `key` beyond the 63,049
   headwords. **They are keys, never results** — a non-main form must not appear in
   `word`.

3. **`key.k` is diacritic-folded to match PHP exactly.** `_lib.php:500`:

   ```php
   mb_strtolower($s); str_replace(['ț','ș','ţ','ş','ă','â','î'], ['t','s','t','s','a','a','i'], $s);
   ```

   Port that mapping character-for-character, including both cedilla and comma variants,
   so `tanar` finds `tânăr` and the two halves never disagree. Insert **both** the folded
   form and the unfolded one as keys (the PK makes duplicates harmless).

4. **`word.form` is `Lexeme.formNoAccent`.** It is already correct Romanian orthography —
   it strips stress marks and keeps diacritics. Do not add a second string column; the
   search key lives in `key`.

5. **`band` is derived, never a bare surface count.** Roll `corpus_frequencies.db`
   `culturax_ro` `occurrence_count` up through `inflected_forms.db.form_lemma` by `lemma`,
   the way `validate_diachronic.aggregate_by_family` does, then
   `band = 0 if occ == 0 else min(7, 1 + floor(log10(occ)))`. `lăcrima` is 0 as a bare
   infinitive and 16,393 as a verb — the rollup is not optional. Write the band edges into
   `meta` so a later corpus addition is visibly a different build (the
   `scaled_modern_thresholds` drift CLAUDE.md warns about).

6. **Merge the scrape with provenance.** `synonyms.db` has 2,075 rows,
   `synonyms(word PK, synonyms, antonyms)`, comma+space-joined plain text. Split on `,`
   and trim. Attach to the word's lowest-id sense; if the word has no sense (524 of them
   do not), create one with `label = NULL`. Set `edge.src = 1`. The text is dirty in
   places — `potcă` ends with `HÎDOȘENlE`, `viorea` contains `viorele sălbatice =
   colțunii-popii` — so drop tokens that are still uppercase after trimming, contain `=`,
   exceed 40 characters, or are more than 4 words. `scrape_synonyms.py` already has this
   cleanup; reuse its rules rather than inventing new ones.

7. **Type-5 edges only where no type-1 edge already exists** for that pair. Emit from
   trees with ≥2 entries; expect ~38,321 pairs and 25,554 words gaining a first synonym.

8. **Symmetrise.** Only 36% of stored `Relation` pairs are reciprocal. Every edge is
   written in both directions.

9. **`edge.rank` is filled at build time, 0-based, ordered `band DESC, form ASC`** within
   each `(sid, t)`. The page reads a bounded `rank < K` slice and does no ordering per
   request — which is what makes the graph's node ceiling hold by construction rather than
   by luck (`ui.md`). Two things about it:

   - **Rank is per sense, not per word.** A sense's edges are shared by every word in its
     `sense_word` set, so the ordering is computed once per sense. Ranking per source word
     would store the same list once per member.
   - **A separate `neighbor` table was considered and rejected** — it would be a
     near-duplicate of `edge` with the same cardinality. One integer column plus one index
     is the smaller version of the same thing.

   **This invalidates the measured sizes below and they must be re-measured** — the ~10–11
   MB figure was taken against the DDL *without* this column, and `escalate.md` §7 requires
   a re-measure rather than a quiet reship. Expect roughly +1.5–2 MB; the 16 MB test
   ceiling has room, but confirm it rather than assume it.

### Expected output

| | |
|---|---|
| file size | **~10–11 MB** (test ceiling 16 MB) |
| build time | 15–25 s |
| `word` rows | ~63,049 |
| `key` rows | ~107,000 |
| `sense` rows | ~76,459 |
| `edge` rows | ~180,000 before type-5 and the scrape |
| coverage, bands 1k+ | **≥ 70%** (measured 72.4%) |

---

## Phase 3 — the page

**The visual design is settled and lives in [`ui.md`](ui.md)** — layout geometry, caps,
tokens, accessibility, empty state, attribution. This section covers the files and the
data path only; take every rendering decision from `ui.md` and do not re-derive one.

Five files.

| file | notes |
|---|---|
| `public/sinonime.php` | Served at `/sinonime` by the existing `.htaccess` `$uri.php` rewrite — **no new rewrite rule needed**. Head template: `stats.php` (164 lines). Loads `app.css` + `assets/lib/htmx-2.0.4.min.js` + `prefs.js` + `assets/syn.js` **only** — never `app.js` or `store.js`, which are explorer/quiz-specific. Sets `$brand_tag` and requires `api/_partials/header.php` and `footer.php`. Reads `?q=` and **server-renders the whole result region**, so a shared link is complete, indexable, and works with JS off. `class="page-doc"` on `<body>` — it is a single scrolling result page, not the explorer's fixed shell; **check that at a wide viewport**, since the mobile block hides the bug. |
| `public/api/_syn.php` | `syn_db()`: own PDO singleton over `public/data/syn.db`, `PRAGMA query_only = ON`, copying `_lib.php:488-498` exactly. Requires `_lib.php` for `BASE` / `e()` / `normalize_diacritics()` (`_lib.php:499`) / skins. **Never requires `_appdb.php` or `_auth.php`** — a public read must not mint a device identity for every passing crawler, the guard `colectii.php` already documents. Holds the lookup and search functions, the band/POS/register label tables, and the two emitters: `syn_layout()` (pure arithmetic → node and edge positions) and `syn_svg()`. |
| `public/api/syn.php` | htmx endpoint returning an **HTML fragment**, shaped like `api/search.php`. `?q=` returns the result region; `?ac=` returns the autocomplete list only. |
| `public/assets/syn.js` | ~80 lines, **progressive enhancement only** — hover cross-highlighting between node and list row, a hover card off the JSON island, and `mouseenter` prefetch of the target fragment. The page is complete without it. |
| `public/data/syn.db` | Built by Phase 2. Covered by the existing `public/data/.htaccess` deny rule (Apache); nginx needs the `location ~ \.(db\|db-wal\|db-shm\|sqlite3?)$ { deny all; }` block the deploy section already requires. |

**`syn_layout()` stays pure** — inputs are the capped node lists, output is coordinates. No
database access, no HTML. That is what makes the geometry in `ui.md` testable and what
keeps `syn_svg()` a formatter.

**Layout is computed in PHP and nowhere else.** The JSON island exists for hover
cross-highlighting and hover cards; it must not re-lay-out the graph in the browser, or the
geometry lives in two languages and they drift. Recentring is an htmx swap with
`hx-push-url`, made to feel immediate by the prefetch.

### Search order: exact → prefix → substring

All three against `key.k`, folded. Prefix (`k LIKE 'abc%'`) is index-backed; a writing aid
nearly always knows the spelling, so unlike `api/search.php`'s leading-wildcard `LIKE`
this stays fast at ~107k keys. Fall through to substring only when the first two return
nothing. **No FTS5** — there is none in `ui.db` either, and prefix matching makes it
unnecessary.

**Pagefind was evaluated and rejected**, so it is not proposed again. It indexes *rendered
HTML* and ranks it with BM25 over prose: using it means generating 63,049 static pages to
feed its crawler and rsyncing them (only `public/` is deployed), then overriding its
ranking with `band` — which is the entire product. It also puts a WASM runtime on a page
this section restricts to htmx. The query here is a known-item lookup over ~107k keys, not
a full-text search, and SQLite answers it off `key(k, word_id)` in well under a
millisecond. The one transferable idea — sharding a static index by prefix so the client
fetches only what it needs — is worth revisiting **only** if the autocomplete below is ever
judged too slow.

### Autocomplete

Server-side and debounced: `hx-trigger="keyup changed delay:150ms"` against `?ac=`, prefix
match on `key.k`, index-backed, capped at 8 suggestions ordered `band DESC, form ASC`. One
code path with the real search, no second copy of the key table to keep in sync.

### Ranking

Within a sense cluster, order by `band DESC`, then `form` alphabetically — precomputed into
`edge.rank` by build rule 9, so the request path does no ordering. Bands 0–1 are rendered
as *available but dimmed* — never filtered out.

### htmx notes

Copy `api/search.php`'s fragment shape. **`hx-include` is inherited in htmx**, so anything
placed in the form is sent by every child element's own request too — the bug CLAUDE.md
records under the share-pin (`#word-list` rows picked up an empty `word=` from the form
and every definition 400'd). Check any new form field's name against what the result rows
themselves send.

**Here that check is specifically against the graph's node links**, which are `?q=<word>`
— the same param the search box uses. A node link that inherits the form's `q` gets two
`q=` values, PHP keeps the last, and **every node navigates to whatever is in the search
box instead of to itself**. The graph is inside the swapped region, so it is exactly the
shape of the outage above. Either scope `hx-include` so it cannot reach the SVG, or make
the node links plain navigations rather than htmx requests; `test_sinonime.js` asserts a
node link's resolved URL with the form present.

---

## Phase 4 — the gap scrape (after v1 ships, not before)

Add a selection mode to `scrape_synonyms.py` that reads the gap words from `syn.db`
instead of `--seam` from the shortlist: words with `band >= 3` and no type-1 or type-5
edge. **21,489 words, 17.9 h at `--delay 3.0`.**

Everything difficult already exists and is correct — do not reimplement it:
`acquire_host_lock()` on `data/.dexonline.lock` (host-keyed, `flock`, interlocks with
`scrape_definitions.py`), automatic resume from the CSV checkpoint, per-row flush so
Ctrl+C is safe, the ≥1.2 s floor. Keep `--delay 3.0`; dexonline.ro is community-run.

Then re-run Phase 2. **No schema change** — this is a data refresh.

---

## Acceptance tests

Conventions in this repo are unusual and there is no runner:

- **`tests/test_*.py` are pytest**, against the venv at
  `~/g2-dev/monitorulpreturilor/venv`. No `conftest.py`, no config file.
- **`tests/test_*.js` are plain `node` scripts** — each defines its own `check()`, uses
  global `fetch`, reads `process.env.OTIOS_TEST_URL`, and ends
  `process.exit(failures ? 1 : 0)`. Run one at a time against a live server.
  `tests/test_search_scope.js` is the closest model.

### `tests/test_extract_relations.py`

- type distribution is exactly 152,023 / 5,216 / 1,547 / 74
- `tree` has 226,424 rows, `relation` 158,860
- running against `dex-sample-cleaned.sql` exits non-zero rather than writing an empty DB

### `tests/test_build_syn_db.py`

- **`văz` has ≥3 distinct sense clusters, and `concepție` is not in the same one as
  `privire`.** This is the flattening regression and the single most important assertion
  in the suite. If it fails, the tree-expansion rule is wrong — see `escalate.md`; do not
  loosen the assertion.
- coverage at bands 1k+ is **≥ 70%**
- `nalt` resolves through `key` but has no row in `word`
- `tanar` resolves to `tânăr` through `key`
- file size < 16 MB
- no table in `syn.db` references `ui.db` or `app.db`

### `tests/test_sinonime.js`

- exact, prefix and folded search each return results (`tanar` → `tânăr`,
  `sofragerie` → `sufragerie`)
- a band-0 word is **present in the response and marked**, not absent
- `/sinonime` resolves through the rewrite (200, not 404)
- the page opens no connection to `app.db` — assert no `Set-Cookie` for the device token

**Plus the UI assertions in [`ui.md`](ui.md) § Acceptance** — the 37-node ceiling, layout
byte-stability, every node being an `<a href>` that resolves to its own word with the form
present, the empty state, and `văz` rendering more than one sense sector.

---

## Verification

```bash
source ~/g2-dev/monitorulpreturilor/venv/bin/activate

python extract_relations.py            # expect 158,860 relations, 226,424 trees, ~15 s
python tools/build_syn_db.py           # expect ~10-11 MB, 15-25 s
ls -la public/data/syn.db

pytest tests/test_extract_relations.py tests/test_build_syn_db.py -q

php -S 127.0.0.1:8011 -t public tools/dev-router.php &
OTIOS_TEST_URL=http://127.0.0.1:8011 node tests/test_sinonime.js
```

`tools/dev-router.php` is required for local dev — `php -S` ignores `.htaccess`, so
`/sinonime` would 404 without it.

Then look at `frumos`, `repede`, `mare`, `văz` and `celșag` by hand. `văz` is the one that
tells you whether the sense clustering survived; `celșag` is the empty state.

Finally screenshot `frumos` and `văz` across all six skins × both themes, per `ui.md`
§ Skins. A skin flattening the active node state or losing the graph against its own
surface fails invisibly while you are looking at any one skin.

---

## Documentation to update on the same branch

- **`CLAUDE.md` § Synonyms** — narrow the "not from the dump" claim to
  `Definition.internalRep` for the Litera titles, and add a Sinonime section pointing here.
- **`docs/BACKLOG.md:313`** — same correction on the `[x] synonyms data` entry.
- **`docs/BACKLOG.md`, the `also count synonyms!` item** — unblocked. Its stated
  precondition (~4.5 h of scraping before `syn_count` means anything on `curiosity`) is
  obsolete: the `Relation` graph covers 13,978 of `ui.db`'s 18,270 words at zero cost.
- **`docs/activity-history.md`** — a `## 2026-08-14` entry, per CLAUDE.md's process note.
- **`scrape_synonyms.py`'s docstring** — the "Why this can't come from the dump" heading
  is the origin of the misreading; narrow it.
