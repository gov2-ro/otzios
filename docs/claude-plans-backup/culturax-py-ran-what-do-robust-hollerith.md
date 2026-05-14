# Plan: Enrich output with DEX taxonomy metadata

## Context

The diachronic output CSVs identify forgotten words but carry minimal metadata beyond POS
abbreviation and DEX frequency. The DEX SQL dump contains a rich hierarchical Tag taxonomy
already used on dexonline.ro — domain labels (muz., med.), register labels (înv., pop.),
and etymology labels (grecism, latinism, anglicism). Surfacing these as explicit columns would
enable filtering ("archaic Greek loanwords") and research questions ("are turcisms more likely
forgotten?"). User asked for this to go into BACKLOG.md.

---

## What's in the DEX Tag table

Hierarchical tags with `parentId` grouping. Key parent categories:

| parentId | category | examples |
|---|---|---|
| 0 (root) | "etimologie" (id=1) | — |
| 1 | etymology origin | grecism (414), latinism (380), anglicism (320), germanism (391), turcism (300), franțuzism (293), slavonism (442), maghiarism (443), rusism (410), sârbism (444), italienism (372) |
| 0 (root) | "disciplină" (id=41) | — |
| 41 | domain | muzică (112), medicină (106), drept (316), biologie (28), botanică (38), sport (192), economie (313), informatică (19), teatru (389), militar (109), juridic (99)… 50+ |
| 0 (root) | "registru stilistic" (id=42) | — |
| 42 | register | **învechit** (8), popular (15), familiar (5), dialectal (184), livresc (187), poetic (242), argou (9), vulgar (13), arhaizant (145), peiorativ (7), ironic (186)… |
| 0 (root) | "parte de vorbire" (id=43), isPos=1 | — |
| 43 | POS | substantiv (49→m/f/n), adjectiv (45), verb (44), adverb (66), interjecție (68)… |

ObjectTag links these to objects via `objectId` + `objectType` (integer, meaning needs
verification: likely 1=Entry, 2=Meaning, 3=Definition).

Join path: `Lexeme.id → EntryLexeme.lexemeId → entryId → Entry.id` then
`Entry.id → ObjectTag(objectType=Entry?) → Tag.id`.

---

## Proposed backlog entry

```markdown
- [ ] **#16 — [M, High] Enrich output CSVs with DEX taxonomy tags** — The DEX SQL dump has
  a `Tag` table (~460 entries, hierarchical) linked to entries via `ObjectTag`. Three tag
  families are useful for filtering and analysis:

  - **Domain** (`parentId=41`): muzică, medicină, drept, sport, informatică, etc. (~50+
    specialisms). Lets users exclude technical jargon from "forgotten word" results.
  - **Register** (`parentId=42`): `învechit`, popular, familiar, dialectal, livresc, poetic,
    argou, etc. A word already tagged "învechit" in DEX is a known archaism — high-confidence
    signal that overlaps with (and validates) our diachronic verdict.
  - **Etymology** (`parentId=1`): grecism, latinism, anglicism, turcism, slavonism, germanism,
    maghiarism, rusism, etc. Enables research questions: are Greek loanwords more likely to
    become extinct than Latin ones? Are Turkisms clustering in a specific DEX frequency band?

  POS is already partially covered by `Lexeme.description` and `modelType`, but Tag has
  finer-grained POS (`substantiv feminin invariabil`, `verb intranzitiv`) via `isPos=1` tags.

  **Implementation sketch:**
  1. Extend `extract_lexemes.py` to also extract `Tag`, `ObjectTag`, `EntryLexeme` from
     the MySQL dump into `lexemes.db` (three new tables, straightforward parsing).
  2. Determine `objectType` integer values experimentally (check sample rows in ObjectTag
     against known entry IDs).
  3. Write `enrich_taxonomy.py` (or add to `validate_diachronic.py --enrich`) that joins:
     `Lexeme → EntryLexeme → Entry → ObjectTag → Tag` and groups tags by family.
  4. Add columns to `forgotten_words_diachronic.csv`:
     - `dex_register` — pipe-delimited list, e.g. `învechit|dialectal`
     - `dex_domain` — e.g. `muzică`
     - `dex_etymology` — e.g. `grecism`
     - `dex_pos_tag` — full-form POS from Tag (supplements existing `description`)
  5. A word can have multiple senses with different tags — aggregate across all senses
     (union of tags), or take the most common. Flag words where register tags conflict
     across senses.

  **Why high priority:** `dex_register=învechit` is direct DEX editorial evidence that a word
  was already recognized as archaic at time of writing — a gold-standard signal orthogonal to
  corpus frequency. Cross-referencing our `extinct` verdict with `dex_register=învechit` is
  the cleanest validation we have.
```

---

## Verification (post-implementation)

1. `python extract_lexemes.py` → check `sqlite3 data/processed/lexemes.db ".tables"` shows
   `Tag`, `ObjectTag`, `EntryLexeme`.
2. Spot-check: `SELECT t.value FROM Tag t JOIN ObjectTag ot ON t.id=ot.tagId JOIN EntryLexeme el ON ot.objectId=el.entryId JOIN Lexeme l ON el.lexemeId=l.id WHERE l.form='isihie'` — should return `grecism`, `învechit`.
3. Run `validate_diachronic.py --enrich`, inspect a few rows of the output CSV for non-empty
   `dex_register` and `dex_etymology`.
