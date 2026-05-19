# Plan: Fix definition misalignment, then scrape what's still missing

## Context

**The two problems are linked.**

1. **Misalignment (the bigger problem, already in `BACKLOG.md:138`)** — the 10,703 definitions we DO have are largely paired with the wrong words. `abac` (abacus) is paired with a bacteremia definition; `abate` (to deviate / abbot) is paired with the definition of *abatize* (a defensive obstacle made of felled trees); `abis` is paired with the definition of *aborda*. The shape of the bug: each word seems to receive the definition of a nearby-but-different word. BACKLOG.md attributes this to "the extraction script joins on a row offset or integer key that doesn't stably map across tables."

2. **38.5% missing (already investigated, `docs/DEFINITIONS_ANALYSIS.md`)** — the DEX dump has 1.1M orphaned definition IDs and only 61,041 actual definition records. Some of "missing" may actually be misalignment victims with no surviving pairing.

**Both root causes must be addressed in order:** fixing extraction may both (a) realign existing definitions and (b) recover some currently-marked-as-missing words. Only after a clean re-extract is it correct to scrape "still missing."

**Note on the linked library:** [LearnRomanian/dexonline-scraper](https://github.com/LearnRomanian/dexonline-scraper) is TypeScript/Node.js. Not directly usable in this Python codebase, but it confirms the synthesis tab is the standard extraction target — we'll write a Python equivalent following the existing `search_wild.py` pattern.

**User-confirmed choices (already locked in):**
- For scraping: extract the **synthesis** (`sinteza definițiilor`) only, one row per word.
- For scraping: write a **CSV checkpoint** first, then merge into `definitions.db`.

---

## Phase A — Diagnose misalignment in `extract_definitions.py`

### A1. Inspect what we have

Run the existing definitions.db against dexonline.ro for ~15 spot-check words to characterise the bug:

- Known-bad examples from BACKLOG: `abac`, `vânzător`, `acătarii`, `drăngălău`, plus `abate`, `abis`, `aberativ`, `aberațiune` (from our earlier output).
- For each, compare `definitions.db` text against `dexonline.ro/definitie/{word}` synthesis.
- Record the pattern: is it always off-by-one? off-by-a-fixed-number? random?

### A2. Audit the join logic

Re-read `extract_definitions.py:81-160` against the DEX schema (already partially captured in our earlier investigation: `DefinitionSimple` columns are `(id, definition, lexicon, createDate, modDate, millShown, millGuessed)`).

Likely-suspect areas to verify:

1. **Lexeme column index for `formNoAccent`** (`extract_definitions.py:124`). The script claims `cols: id(0), form(1), formNoAccent(2)`, but a sample Lexeme row is `(1,'aa','aa','aa','aa',NULL,'',1,1,0.86,…)` with many columns. We must confirm against `CREATE TABLE Lexeme` from the dump whether `formNoAccent` really is column 2 or a different index. **If wrong, every word in the db is paired with the wrong key.**

2. **`_parse_values()` correctness** (`extract_definitions.py:22-66`) — confirm it handles every escape sequence in the dump (newlines inside strings, escaped quotes, NULL distinction). A misparse on one row would offset every subsequent row in a multi-VALUE INSERT.

3. **`setdefault` behaviour on duplicates** — for the same Lexeme.id appearing in multiple INSERTs, do we keep the first or last? Same for definition text. Inconsistency here could explain "wrong but near-right" pairings.

4. **`entryRank` / `definitionRank` tie-breaks** (`extract_definitions.py:131-139`). If the rank field is `''` (treated as 0 by `_rank`), and two entries tie at 0, the iteration order of the dump determines the winner — could be unstable and explain inconsistent results.

### A3. Build a verification harness

Single-purpose script `verify_definitions.py` (or inline cell):
- Pick 50 random words from `definitions.db`.
- Fetch each from dexonline.ro synthesis.
- Compute a similarity score (e.g., is any 6-gram of the stored definition present in the live synthesis?).
- Output a report: % matched / % mismatched / % both-empty.

This gives us a baseline of just how bad the misalignment is, and a regression check for the fix.

---

## Phase B — Fix `extract_definitions.py` and re-extract

Based on Phase A findings:

1. Patch the specific bug (most likely candidate: column-index error in one of the four `INSERT INTO` parsers).
2. Re-run `python extract_definitions.py` to regenerate `data/processed/definitions.db`.
3. Re-run `verify_definitions.py` against the new db. **Stop and reconsider if alignment rate isn't ≥ 95% on the sample.**
4. Re-count: how many shortlist words have definitions now? (We expect this to drop initially because we're rejecting the bad ones, then partially recover as correctly-paired words appear.)

---

## Phase C — Scrape what's still missing

### C1. New script: `scrape_definitions.py` (repo root)

Mirrors `search_wild.py:1-542`.

**Inputs**
- `data/processed/forgotten_words_shortlist.csv`
- `data/processed/definitions.db` (now clean, post-Phase-B) — used to identify what's still missing

**Output (checkpoint)**
- `data/processed/scraped_definitions.csv` with columns `word, definition, source_url, scraped_at, status`
  - `status ∈ {ok, not_found, error}` — kept rows let resume skip retries
- Append-mode per row (immediate flush) so Ctrl+C never loses progress

**Resume logic** (copy `search_wild.py:346-355`)
- Read existing checkpoint, build `set[str]` of processed words, skip them

**Target word selection**
- Shortlist words minus words already in `definitions.db` minus words already in scraping checkpoint

**HTTP fetch**
- `requests.Session()` with `User-Agent: "otios-scraper/0.1 (research project)"`
- URL: `https://dexonline.ro/definitie/{urlencoded_word}`
- Default `--delay 3.0` (dexonline.ro is community-run; be polite)
- Retry once on 429/503 after 30s backoff; log + skip on other errors
- Recognise "no result" page → `status=not_found`

**HTML parsing (BeautifulSoup + lxml)**
- Target the **synthesis** block. Selectors to confirm against a live page during test:
  - The Synthesis tab content lives in a `<div>` whose `id` / `class` will need to be verified by inspecting the page (likely `#tab-synthesis` or `.synthesis`).
  - Fall back to first `.def`/`.dex-definition` if synthesis is absent.
- Strip HTML tags, collapse whitespace, return plain text.

**CLI flags** (match `search_wild.py`)
```
--dry-run              Print URLs only
--limit N              Stop after N words (excluding checkpointed)
--delay SECONDS        Default 3.0
--input PATH           Default data/processed/forgotten_words_shortlist.csv
--output PATH          Default data/processed/scraped_definitions.csv
--definitions-db PATH  Default data/processed/definitions.db
--merge                After scraping, upsert ok rows into definitions.db
```

**Merge step (--merge or separate run)**
- `INSERT OR REPLACE INTO definitions (word, definition) VALUES (?, ?)` for `status='ok'`
- Print summary: N inserted/updated, skipped, failed

### C2. `requirements.txt`

Add `requests`, `beautifulsoup4`, `lxml` (none currently listed).

### C3. Docs

- `docs/BACKLOG.md` — close item at line 138 (misalignment) referencing the fix commit; close line 142 (`drăngălău` example) likewise; note coverage is now backed by `scrape_definitions.py`.
- `CLAUDE.md` — short paragraph under "End-to-end pipeline": when to run `scrape_definitions.py`, expected runtime (~5-7 hrs for ~6.7k words at 3s/req), where output lands, how to resume.

---

## Critical files

| Path | Phase | Action |
|---|---|---|
| `extract_definitions.py` | A, B | Read carefully (lines 81-160), then patch the misalignment bug |
| `verify_definitions.py` (new) | A | Temporary harness — spot-check stored vs. live |
| `data/processed/definitions.db` | B | Regenerated by re-running fixed extract script |
| `scrape_definitions.py` (new) | C | Built following `search_wild.py:1-542` |
| `requirements.txt` | C | Add `requests`, `beautifulsoup4`, `lxml` |
| `docs/BACKLOG.md` | C | Close items 138, 142 |
| `CLAUDE.md` | C | One-paragraph pipeline note |

**Reused patterns** (read before duplicating):
- `search_wild.py:346-355` — checkpoint loader
- `search_wild.py:424,451,467-468` — resume / append
- `search_wild.py:488` — KeyboardInterrupt handling
- `search_wild.py:494-512` — rate-limit + retry
- `extract_definitions.py:163-170` — `definitions.db` schema (unchanged; we upsert)
- `ui/app.py:115-120` — UI consumer; no changes required, picks up new rows on app restart

---

## Verification

**End of Phase A:** A report (`verify_definitions.py` output) characterising the misalignment. A specific code-change hypothesis. No code changes yet.

**End of Phase B:**
1. Re-run `verify_definitions.py` against the new `definitions.db`. ≥ 95% alignment on the random sample.
2. Manual spot-check in the UI: open the `abate`, `abis`, `drăngălău` detail panels — definitions should now match dexonline.ro.
3. Coverage count: report new shortlist coverage % (likely lower than the bogus 61.5%, but trustworthy).

**End of Phase C:**
1. Dry run: `python scrape_definitions.py --dry-run --limit 5` — prints 5 missing-word URLs.
2. Small live run: `python scrape_definitions.py --limit 3 --delay 3.0`. Inspect CSV — three rows, non-empty definitions. Manually verify one against dexonline.ro.
3. Resume test: re-run same command → "0 new words to scrape".
4. Merge test: `python scrape_definitions.py --limit 20 --delay 3.0 --merge` then restart `python ui/app.py`. Open one scraped word in UI — definition appears in the detail panel (`ui/templates/partials/detail.html:30-36`).
5. Full run: `python scrape_definitions.py --delay 3.0 --merge` to completion. Spot-check five formerly-missing words in UI.
