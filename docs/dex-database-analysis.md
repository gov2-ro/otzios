# DEX Online Database Analysis

**Date**: October 26, 2025
**Database**: dex-database.sql (1.2 GB MySQL dump)
**Location**: `data/dictionaries/dex-database.sql`

## Overview

The DEX Online database is a comprehensive Romanian dictionary with ~365,000 lexemes (word forms) and ~335,000 entries. It's a rich resource for identifying "forgotten" Romanian words.

## Key Database Tables

### 1. Lexeme (365,869 records)
**Primary table for word analysis**

Important fields:
- `form` - The actual word (e.g., "învechit", "aba")
- `formNoAccent` - Word without diacritics
- `frequency` (FLOAT, 0.0-1.0) - **CRITICAL for forgotten words!**
  - 0.99-1.0: Very common (e.g., "accent", "aburi")
  - 0.75-0.90: Moderately common
  - 0.50-0.75: Uncommon
  - <0.50: Rare/forgotten candidates
- `description` - Part of speech and markers (e.g., "adj.", "s.m.", "înv.")
- `modelType`, `modelNumber` - Morphological information
- `stopWord` - Boolean for common stop words

Example records:
```
form='aalenian', frequency=0.81, description='adj.'
form='aba', frequency=0.93, description='s.f.'
form='abject', frequency=0.94, description='adj.'
form='abițiune', frequency=0.69 ← Low frequency candidate!
```

### 2. Entry (335,611 records)
Dictionary entries with human-readable descriptions

Fields:
- `id` - Entry ID
- `description` - Human-readable entry name
- `structStatus` - Structure/curation status
- `createDate`, `modDate` - Timestamps

### 3. Abbreviation (Markers Table)
Contains linguistic markers - **KEY for identifying forgotten words!**

#### Archaic/Forgotten Word Markers:
- **`înv.` = învechit** (archaic) ⭐ PRIMARY MARKER
- **`arh.` = arhaizant** (archaizing)
- **`reg.` = regional** (regional usage only)
- **`pop.` = popular** (popular/folk usage)
- **`dial.` = dialectal** (dialectal)
- `livr.` = livresc (bookish)
- `rar` = rar (rare) - *may not be in abbreviations table*

#### Other useful markers:
- `fam.` = familiar
- `vulg.` = vulgar
- `bis.` = bisericesc (religious terms)
- Technical domains: `bot.`, `med.`, `jur.`, etc.

### 4. DefinitionSimple, Meaning
Definitions and semantic information (useful for context)

### 5. EntryDefinition
Links entries to definitions

## Forgotten Words Strategy

### Primary Approach: Frequency-Based

1. **Query Lexeme table** for words with:
   ```sql
   WHERE frequency < 0.75  -- Uncommon/rare threshold
   AND frequency > 0.0     -- Exclude zero-frequency (errors)
   AND form NOT IN (SELECT word FROM common_words)  -- Exclude wordfreq top 100k
   ```

2. **Marker-Based Enhancement**:
   ```sql
   WHERE description LIKE '%înv.%'   -- Archaic marker
   OR description LIKE '%arh.%'      -- Archaizing
   OR description LIKE '%reg.%'      -- Regional only
   ```

3. **Combined Scoring**:
   - Low frequency (<0.75): +50 points
   - Very low frequency (<0.50): +30 points
   - Marked 'înv.' (archaic): +80 points
   - Marked 'reg.' (regional): +40 points
   - Marked 'dial.' (dialectal): +30 points
   - Not in modern corpus (OSCAR/Wikipedia): +100 points

### Example Forgotten Word Candidates

From initial analysis:
- `abițiune` (frequency: 0.69) - Low freq candidate
- `acatist` (frequency: 0.90) - Moderate, but check corpus
- Words marked `înv.` regardless of frequency

## Next Steps

1. **Convert MySQL → SQLite**
   ```bash
   # Use mysql2sqlite or similar tool
   mysql2sqlite dex-database.sql | sqlite3 dex.db
   ```

2. **Create analysis queries**
   ```python
   # Query low-frequency words
   SELECT form, frequency, description
   FROM Lexeme
   WHERE frequency < 0.75
   ORDER BY frequency ASC
   LIMIT 1000;
   ```

3. **Cross-reference with modern corpora**
   - Load OSCAR Romanian corpus
   - Count word occurrences in Wikipedia RO
   - Compare frequencies

4. **Generate forgotten words list**
   - Export CSV with: word, frequency, markers, corpus_count, rarity_score
   - Categorize: archaic, regional, technical, neologism_failure

## Technical Notes

### Character Encoding
- Database uses `utf8mb4_romanian_ci` collation
- Properly handles: ă, â, î, ș, ț
- Use `formNoAccent` for diacritic-insensitive matching

### Data Quality
- Some technical/scientific terms have low frequency (normal)
- Need to filter proper nouns (`n. pr.` marker)
- Watch for variants (`var.` marker) - may duplicate counts

## Romanian-Specific Considerations

1. **Inflection**: Romanian is highly inflected
   - "frumoaselor" vs "frumos" (base form)
   - Need lemmatization for accurate counting

2. **Diacritic variants**:
   - Old: ş/ţ (cedilla)
   - New: ș/ț (comma below)
   - Database has both: use `formNoAccent` for matching

3. **Spelling reforms**:
   - î/â variations (1953, 1993 reforms)
   - Database includes historical variants

## Resources

- DEX Online API: https://dexonline.ro/api
- Database download: https://wiki.dexonline.ro/wiki/Informații#Descărcare
- GitHub: https://github.com/dexonline

---

**Status**: Initial analysis complete. Ready for database loading and query implementation.