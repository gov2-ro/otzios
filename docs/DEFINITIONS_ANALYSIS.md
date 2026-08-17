# Definitions Data Quality Investigation

## Correction (2026-08-17) — the "94.8% gap" below is wrong; the dump is not corrupted

Everything from here to **Conclusions** compared `EntryDefinition.definitionId` against
`DefinitionSimple.id` and found 94.8% of references dangling. That comparison used the
wrong table. `DefinitionSimple` (61,041 rows) is a small, unrelated table — short
plain-text strings alongside `millShown`/`millGuessed` telemetry columns, apparently the
answer key for dexonline's own quiz feature — not the destination of `EntryDefinition`
joins.

The real definitions table is `Definition` (`id, userId, sourceId, lexicon, internalRep,
…`), which the codebase already reads elsewhere for a different purpose
(`validate_diachronic._load_dict_counts()`, `extract_dict_sources.py`). Re-checked directly
against the current dump (`dex-database.sql`, 1.65 GB, May 2026):

| Check | Count |
|---|---|
| `EntryDefinition` rows | 1,379,043 |
| distinct `definitionId` referenced | 1,186,450 |
| `Definition` rows | 1,231,718 |
| referenced ids missing from `Definition` | **0 (0.00%)** |

Every `EntryDefinition` reference resolves. There is no dangling-reference bug and nothing
to report to the dexonline maintainers.

Words this doc's original run flagged as "missing despite being on dexonline.ro" turn out
to be in `Definition` after all, just not reachable through `DefinitionSimple`:

- `cfartal` — present as a "vezi cvartal"-style pointer entry (`†@CFART'AL@👉`), matching
  what the live site shows.
- `mofluzită` (the feminine form) — genuinely has no headword entry of its own; only
  `mofluz` does. That is ordinary dictionary behaviour (inflected/derived forms aren't
  separately defined), not missing data.

**Why `extract_definitions.py` ended up on `DefinitionSimple` in the first place is still
valid** (see below): the original `Lexeme → EntryLexeme → EntryDefinition → DefinitionSimple`
join really did misalign words, because `Entry` groups multiple related lexemes and a
rank-1 pick isn't necessarily about the lexeme being looked up. The fix that shipped
avoided the join by keying on a `lexicon` column directly — that part of the design was
right. It just picked the wrong table to apply it to: `Definition` has that same `lexicon`
column, 20× the rows, and (per the table above) no missing-reference problem to design
around at all. See `docs/BACKLOG.md` for the follow-up item to rebuild the extractor
against `Definition`.

## Summary (superseded by the correction above)

The DEX database dump has **massive data integrity issues** preventing extraction of definitions for 6,690 shortlist words (38.5% missing).

## Root Cause: Orphaned Definition IDs

**EntryDefinition → DefinitionSimple Join Broken:**

| Component | Count | Status |
|-----------|-------|--------|
| Definition IDs in EntryDefinition | 1,173,555 | Referenced |
| Definition records in DefinitionSimple | 61,041 | Actual |
| **Missing definitions** | **1,112,963** | **94.8% gap** |

**The DEX dump has dangling references:** The EntryDefinition table points to definition IDs that don't exist in DefinitionSimple. This is a corruption or incompleteness issue at the source.

## Extraction Pipeline Impact

```
315,279 lexemes in Lexeme table
    ↓ (linked via EntryLexeme)
173,307 entry IDs (141,972 unlinked)
    ↓ (linked via EntryDefinition)
83,609 definitions extracted ← only these match DefinitionSimple
    ├─ 61,041 with valid text (loaded into db_text dict)
    └─ 22,568+ with missing DefinitionSimple records
            ↓ (missing referenced definition IDs)
    1,112,963 orphaned references ← these fail text lookup
```

## Why Shortlist Words are Missing

The 6,690 shortlist words without definitions are likely linked to entry records that point to non-existent definition IDs in DefinitionSimple.

**Example:** A word might have:
- Lexeme entry ✓
- EntryLexeme linking to Entry ✓
- EntryDefinition pointing to Definition ID #999999 ✓
- **Definition ID #999999 in DefinitionSimple ✗ (doesn't exist)**

## Conclusions

1. **This is not a script bug** — our extraction logic is correct
2. **The DEX dump is corrupted/incomplete** — massive orphaned references
3. **Scraping dexonline.ro is necessary** to fill the gaps for these 6,690 words
4. The extraction successfully recovered the 10,703 definitions that DO exist in the dump (61.5% of shortlist)

## Recommendation (superseded — see the correction at the top)

**Implement Option 3 (Hybrid Approach):**
- Keep the 10,703 definitions extracted from the dump
- Scrape dexonline.ro for the 6,690 missing shortlist words
- This will achieve 100% coverage for the shortlist

Superseded by the 2026-08-17 correction: conclusions 2 above ("the DEX dump is
corrupted/incomplete") is wrong, and scraping is not the only path to closing the gap —
rebuilding the extractor against `Definition` should recover most of it directly from the
dump. Scraping remains the fallback for whatever `Definition` genuinely doesn't cover
(words with no headword entry of their own, etc.), just not the primary mechanism this doc
originally concluded it had to be.
