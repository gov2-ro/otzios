# Sinonime — findings

*Investigated 2026-08-14. Every number below was measured against
`data/dictionaries/dex-database.sql` (1,649,374,734 bytes, 17 May 2026) and the DBs in
`data/processed/`. The snippets that produced them are inline, so re-run rather than
trust.*

---

## 1. The premise we had wrong

`CLAUDE.md` (§ Synonyms), `docs/BACKLOG.md:313` and `scrape_synonyms.py`'s docstring all
say, in almost the same words, that synonyms **cannot come from the dump**. That claim is
true of exactly one thing and was generalised to the whole subject.

What is true: `Definition.internalRep` for the three Litera Internațional titles —
`Sinonime` (2002), `Sinonime82` (1982), `Antonime` (2002) — is redacted to 23 characters,
because those dictionaries are in copyright. `sourceId 6` has max length 23, mean 23,
`"@AB'A@ s. dimie, păn..."`. That is why `dict_count` knows a word appears in them and
not what they say, and it is why `scrape_synonyms.py` exists.

What is not true: that the dump has no synonym data. It has a **complete, structured,
unredacted relation graph** — dexonline's own community-curated one, in the `Relation`
table. No script or document in this repo has ever referenced it; `grep -rn "Relation"`
over `*.py` and `*.md` returned nothing before this investigation.

The redaction is about *the Seche dictionary's text*. The relation graph is a different
artefact by different authors, and it ships in full.

---

## 2. The graph

```sql
CREATE TABLE Relation (
  id int, meaningId int, treeId int, type int, createDate int, modDate int
)
```

A row says: **meaning M is related, by type t, to tree T.** The source is a *sense*
(`Meaning`), the target is a *concept* (`Tree`). Resolving both ends to words:

```
Relation.meaningId → Meaning.treeId → source Tree ─┐
Relation.treeId    → target Tree ──────────────────┴→ TreeEntry → EntryLexeme → Lexeme
```

**158,860 rows**, and the four `type` values are exactly the ones dexonline's own code
defines:

| type | meaning | rows |
|---|---|---|
| 1 | synonym | 152,023 |
| 2 | antonym | 5,216 |
| 3 | diminutive | 1,547 |
| 4 | augmentative | 74 |

Resolved to words (target expansion restricted to `EntryLexeme.main = 1`, forms
normalised via `dump_parser.normalize` over `Lexeme.formNoAccent`):

| | |
|---|---|
| undirected synonym pairs | **164,399** |
| distinct words | **63,049** |
| mean synonyms per word | 5.3 |
| median / p90 / max | 2 / 12 / 352 |
| antonym pairs / words | 4,368 / 4,890 |
| diminutive pairs / words | 1,899 / 3,116 |
| augmentative pairs / words | 95 / 160 |

**Only 36% of stored pairs are reciprocal** (54,093 of 149,058 directed tree-pairs), so
the graph must be symmetrised at build time. dexonline effectively does this when it
renders.

Build cost: **~15 s** for the full parse and join, no HTTP. Against ~4 hours of polite
scraping for 2,075 words.

<details><summary>Reproduce</summary>

```python
import sys, re, collections; sys.path.insert(0, '.')
from dump_parser import parse_tuples, strip_line_prefix, normalize
DUMP = 'data/dictionaries/dex-database.sql'
meaning_tree = {}; rel = []
te = collections.defaultdict(list); el = collections.defaultdict(list); lex = {}
relpat = re.compile(r'\((\d+),(\d+),(\d+),(\d+),\d+,\d+\)')
tepat  = re.compile(r'\((\d+),(\d+),(\d+),(\d+),(\d+),\d+,\d+\)')
elpat  = re.compile(r'\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+),\d+,\d+\)')
with open(DUMP, encoding='utf-8', errors='replace') as f:
    for line in f:
        if line.startswith('INSERT INTO `Meaning`'):
            for t in parse_tuples(strip_line_prefix(line, 'INSERT INTO `Meaning` VALUES '), 6):
                meaning_tree[int(t[0])] = int(t[6])
        elif line.startswith('INSERT INTO `Relation`'):
            for m in relpat.finditer(line):
                rel.append((int(m.group(2)), int(m.group(3)), int(m.group(4))))
        elif line.startswith('INSERT INTO `TreeEntry`'):
            for m in tepat.finditer(line): te[int(m.group(2))].append((int(m.group(5)), int(m.group(3))))
        elif line.startswith('INSERT INTO `EntryLexeme`'):
            for m in elpat.finditer(line): el[int(m.group(2))].append((int(m.group(5)), int(m.group(3)), int(m.group(6))))
        elif line.startswith('INSERT INTO `Lexeme`'):
            for t in parse_tuples(strip_line_prefix(line, 'INSERT INTO `Lexeme` VALUES '), 14):
                lex[int(t[0])] = normalize(t[2] or t[1])

def expand(tid):                      # tree -> its main lexeme forms
    out = []
    for _, eid in sorted(te.get(tid, ())):
        for _, lid, main in sorted(el.get(eid, ())):
            if main and lex.get(lid): out.append(lex[lid])
    return out
```
</details>

---

## 3. Why build this rather than link to dexonline

**41.7% of the Romanian thesaurus is dead Romanian.** Rolling the 63,049 words up through
`inflected_forms.db.form_lemma` against `corpus_frequencies.db` `culturax_ro` (17.0B
tokens):

| modern occurrences | words | share |
|---|---|---|
| 0 | 9,651 | 15.3% |
| 1–9 | 6,907 | 11.0% |
| 10–99 | 9,725 | 15.4% |
| 100–999 | 10,185 | 16.2% |
| 1k–10k | 11,177 | 17.7% |
| 10k–100k | 9,357 | 14.8% |
| 100k–1M | 4,742 | 7.5% |
| >1M | 1,305 | 2.1% |

dexonline lists synonyms alphabetically and undifferentiated, so `frumos` offers
`acătării`, `bididel`, `boghet` and `brudiu` in the same breath as `arătos` and `chipeș`.
For a **writing aid** that is the central problem, and this project already owns the
corpus data that solves it.

**Ranking by modern currency is the product. Coverage is table stakes.** The direction
matters and is easy to get backwards — see CLAUDE.md's `modern_band` note, which records
the same trap for the main app: for *oțios*, high modern usage is the interesting signal;
for a thesaurus, it is the usable one.

---

## 4. Coverage

Headwords with at least one synonym, out of 235,598 DEX main headwords:

| modern occurrences | headwords | `Relation` | `+Tree` (§5) |
|---|---|---|---|
| >1M | 1,439 | 90.6% | 91.6% |
| 100k–1M | 5,671 | 83.2% | 85.9% |
| 10k–100k | 13,011 | 71.1% | 75.6% |
| 1k–10k | 18,974 | 57.7% | 64.8% |
| 100–999 | 22,441 | 44.3% | 52.2% |
| 10–99 | 25,843 | 36.5% | 45.3% |
| 0 | 123,695 | 7.7% | 21.4% |
| **1k and above** | **39,095** | **67.0%** | **72.4%** |

Overall it is 26.2% of all headwords, which sounds thin and is the wrong number to quote
— the untouched 123,695 are words nobody looks up. The number that matters for a writing
aid is the **1k+ band at 67%**, rising to 72.4% with §5. One lookup in four still comes
back empty; §6 is how that closes.

---

## 5. Free sources evaluated

### Accepted — multi-entry `Tree`s

A `Tree` groups the entries of one concept. **10,091 of 226,424 trees hold more than one
entry.** Treating co-membership as a relation adds **38,321 pairs** and gives **25,554
words** their first synonym: +5.4 points on the 1k+ band.

The sample is mixed, though — `pârpolatic`, `astatic`, `îhî`, `părtie` — because
tree-mates are sometimes *spelling variants* rather than synonyms. So this is worth
having and **not** worth merging into type 1. It goes in as its own type (5), where the
build can rank it below real synonyms and a later decision can label or demote it without
a rebuild.

### Rejected — `v. X` cross-references

`definitions.db` holds 70,472 definitions. Of those, **513** are a bare cross-reference
(`v. X`, `vezi X`) and 1,044 more contain one; they give **400** words a first synonym.
Not worth a build step. Recorded here with the number so it is not proposed again — and
note CLAUDE.md already makes the same finding from the other side, under `dex_variant`:
the definition text is what dexonline's *sinteză* merge destroys, which is why reading
relations beats reading prose.

---

## 6. The scrape is complementary, not redundant

This is the finding that reversed the plan. `Relation` is **not** a superset of what
`scrape_synonyms.py` already collected.

On the 1,542 words present in both sources:

| | |
|---|---|
| mean synonyms/word — scrape | 6.8 |
| mean synonyms/word — `Relation` | 6.2 |
| tokens in both | 4,318 |
| tokens only in the scrape | 6,191 |
| tokens only in `Relation` | 5,189 |
| **share of the scrape's tokens that are new** | **59%** |

On **353 of those 1,542** words the scrape adds more than `Relation` holds in total —
`ină` (`Relation` 1, scrape +86), `zizanie` (1, +74), `pâr` (3, +54), `prizărit` (9, +48).

And **524 of the 2,066 scraped words are absent from `Relation` entirely**: `poronci`,
`jeț`, `rumpe`, `soluțiune`, `antereu`, `coprins`, `becisnic`, `amploiat`, `celșag`,
`răzăș`, `iboste`, `daraveră`.

The pattern is clean and it makes sense from who wrote each source. **The
community-curated `Relation` graph is strong on modern vocabulary and weak on the archaic
layer; the Seche dictionary is the reverse.** They overlap by about a third. Merge both.

*Caveat on the sample:* the 2,066 scraped words are all from the forgotten-words
shortlist, so they are deliberately archaic. That biases *which* words the scrape uniquely
covers, but not the 59%-new-tokens figure, which is measured on words both sources hold.

**Remaining gap after `Relation` + `Tree` + the existing scrape: 21,489 words at 100+
modern occurrences with no synonym at all.** At the scraper's 3 s polite delay that is
**17.9 hours** — one resumable overnight run, not the prohibitive job BACKLOG:779 assumed.

---

## 6b. What this does for the main app

Not the point of the exercise, but it falls out for free and it unblocks a standing
BACKLOG item. Against `public/data/ui.db`'s 18,270 words:

| source | covered | share |
|---|---|---|
| `Relation` type 1 only | 10,233 | 56.0% |
| + `Tree` co-membership | 11,027 | 60.4% |
| + the existing 2,066 scraped | **11,517** | **63.0%** |
| still uncovered | 6,753 | 37.0% |

Against 2,066 (11.3%) today, and — the part that matters for `syn_count` — including the
`curiosity` seam, which currently has **zero** coverage because the scrape only ever ran
with `--seam relevant`.

*Measurement note:* an earlier pass put this at 13,978 (76.5%) by counting non-main
lexeme forms as covered headwords. Those are lookup keys, not results; the strict figure
is the one above. A second pass inflated it again by reading a `defaultdict` inside the
type-5 loop, which silently creates an empty entry for every word tested. Both are easy
mistakes to repeat — count with a plain dict and with `EntryLexeme.main = 1` on both sides.

---

## 7. Sense structure — why the schema keeps it

Flattening the graph to a `word ↔ word` bag is lossy in one direction only, and the loss
is visible immediately. Flattened, `văz` gives:

```
privire, vedere, văzut, concepție, orbi, captiva, myosotis, saxifraga, troglodytes
```

Three unrelated senses and three Latin binomials. Grouped by source `Meaning`, which is
how the data is actually shaped:

```
văz  ·  privire, vedere, văzut
     ·  captiva, orbi
     ·  concepție
```

The noise comes from expanding a target `Tree` to every lexeme of every one of its
entries — the same 10,091 multi-entry trees from §5, read the other way. Restricting the
expansion to the tree's *first* entry cuts `văz` from 13 synonyms to 9 and drops the worst
of it, but does not fix the underlying problem, which is that a word-level bag has nowhere
to put the sense boundary.

Rendering sense clusters flat later is trivial. Un-flattening is impossible. So the
storage keeps senses even if the first UI does not show them.

---

## 8. Size

Each schema was built in `:memory:` with the real data and measured as
`page_count × page_size` after `VACUUM`.

| schema | rows | size |
|---|---|---|
| words + flat pairs, no metadata | 63,049 w · 170,626 pairs | **6.4 MB** |
| + POS, register byte, currency band | same | **8.6 MB** |
| sense-clustered + metadata + labels | 63,049 w · 76,459 senses · 179,894 edges | **9.3 MB** |
| the above + variant/fold lookup table | + ~44k keys | **~10–11 MB** |

`public/data/ui.db` is 17.2 MB for comparison, so the whole range is smaller than what is
already shipped.

**Two things this measurement settled:**

- **The scalar metadata is free; the strings are not.** POS + register + band is 3 bytes
  per word, 190 KB in total. The 2.2 MB jump from the first row to the second is almost
  entirely a second *string* column plus its index. So there is no lean-versus-rich
  tradeoff to agonise over — take all the metadata.
- **One display string per word, not two.** `Lexeme.formNoAccent` is already correct
  Romanian orthography: it strips stress marks and keeps diacritics (CLAUDE.md's `Lexeme`
  contract says so). The diacritic-folded search key does not need a column of its own —
  it belongs in the lookup table that has to exist anyway for variant spellings.

---

## 9. Metadata available at no extra cost

| field | source | coverage |
|---|---|---|
| `pos` | `Lexeme.modelType` | 99.5% — **not** taxonomy tags; see CLAUDE.md's `dex_pos` gotcha |
| `band` | `culturax_ro` rolled up through `form_lemma` | 100% (0 is a real value here, meaning absent) |
| sense label | `Tree.description` | e.g. `'monitor (periodic, aparat, program)'`, `'piuneză / pioneză'` |
| register | `ObjectTag` where `objectType = 3`, joined to `Tag.value` | 196,888 rows |

The register tags are the interesting one. `objectType = 3` appears to be **`Meaning`** —
the evidence is that `regional` (8,022), `figurat` (9,949), `rar` (6,631), `învechit`
(5,836) and `cf.` are all type 3, while `substantiv feminin` (62,787) and `adjectiv` are
type 2 (`Lexeme`). If that holds, register attaches at *sense* granularity, which is
exactly where our sense rows live.

That is **not** the same situation as CLAUDE.md's `dex_pos` warning. There, meaning-level
tags were being used to label a *word*, and they bled across variants (`visternic` came
out "substantiv feminin" because the entry also covers `vistiernică`). Here the tag stays
on the sense it was written for. **Verify the `objectType` mapping before relying on it**
— it is an inference from the tag names, not something the dump states.

---

## 10. What this does not answer

- Whether type-5 (`Tree`) edges are good enough to *show* rather than merely store. Needs
  a review of ~50 random pairs.
- Anything about the UI.
- Whether scraping the gap at 20k+ words is the right thing to do at all, given the
  redaction is deliberate. See `escalate.md`.

Specification: [`spec.md`](spec.md) · Escalation points: [`escalate.md`](escalate.md)
