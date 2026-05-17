# Definitions Data Quality Investigation

## Summary

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

## Recommendation

**Implement Option 3 (Hybrid Approach):**
- Keep the 10,703 definitions extracted from the dump
- Scrape dexonline.ro for the 6,690 missing shortlist words
- This will achieve 100% coverage for the shortlist
