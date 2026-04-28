# Development Database - Summary

**Created**: October 27, 2025
**Status**: ✅ Working

## What We Built

Successfully created a development-ready SQLite database from the 1.2GB DEX Online MySQL dump.

### Files Created:

1. **`data/dictionaries/dex-database-sample.sql`** (285 MB)
   - Sampled version of full database
   - Kept 100% of critical tables (Lexeme, Entry, Abbreviation)
   - Skipped 77% of data (mainly FullTextIndex, crawlers, etc.)

2. **`data/processed/lexemes.csv`** (30 MB)
   - 315,253 lexeme records extracted
   - Pure CSV format for easy processing

3. **`data/processed/lexemes.db`** (26 MB) ⭐ **MAIN DATABASE**
   - SQLite database ready for queries
   - 315,247 records (6 malformed lines skipped)
   - All Romanian diacritics preserved

## Database Schema

```sql
CREATE TABLE Lexeme (
    id INTEGER PRIMARY KEY,
    form TEXT NOT NULL,              -- The actual word
    formNoAccent TEXT,                -- Without diacritics
    formUtf8General TEXT,
    reverse TEXT,
    number INTEGER,
    description TEXT,                 -- Part of speech, markers
    noAccent INTEGER,
    consistentAccent INTEGER,
    frequency REAL,                   -- ⭐ KEY FIELD: 0.0-1.0
    hyphenations TEXT,
    pronunciations TEXT,
    stopWord INTEGER,
    compound INTEGER,
    modelType TEXT,
    modelNumber TEXT,
    restriction TEXT,
    staleParadigm INTEGER,
    notes TEXT,
    hasApheresis INTEGER,
    hasApocope INTEGER,
    createDate INTEGER,
    modDate INTEGER
);
```

## Sample Forgotten Words (frequency < 0.15)

| Word | Frequency | Type | Meaning Hint |
|------|-----------|------|--------------|
| bucle | 0.03 | adj. | (archaic adjective) |
| precoace | 0.03 | adj. | (archaic adjective) |
| băt'ârn | 0.05 | s.m./adj. | (rare masculine noun) |
| bețivlean | 0.05 | adj./s.m. | (rare, related to drunkenness?) |
| jălit'or | 0.07 | adj./s.m. | (archaic, possibly "mournful") |
| jântuit'or | 0.07 | adj./s.m. | (archaic) |
| evacuat'oriu | 0.09 | adj. | (rare Latin-derived) |
| adăugăt'oriu | 0.13 | s.m. | (archaic, "additive"?) |
| adet'oriu | 0.14 | adj./s.m. | (archaic) |

## Quick Queries

### Count words by frequency range:
```sql
SELECT
    CASE
        WHEN frequency < 0.5 THEN 'Rare (<0.5)'
        WHEN frequency < 0.75 THEN 'Uncommon (0.5-0.75)'
        ELSE 'Common (>0.75)'
    END as category,
    COUNT(*) as count
FROM Lexeme
WHERE frequency > 0
GROUP BY category;
```

### Find forgotten adjectives:
```sql
SELECT form, frequency, description
FROM Lexeme
WHERE frequency < 0.60
  AND description LIKE '%adj%'
  AND form NOT LIKE '%-%'
ORDER BY frequency ASC
LIMIT 50;
```

### Find words with specific markers (when we add them):
```sql
-- Note: markers like 'înv.' are in the description field
SELECT form, frequency, description
FROM Lexeme
WHERE description LIKE '%înv.%'  -- archaic marker
   OR description LIKE '%reg.%'  -- regional marker
ORDER BY frequency ASC;
```

## Next Steps

1. **Download wordfreq Romanian top 100k**
   - Filter out common modern words
   - Focus on dictionary-only words

2. **Corpus analysis**
   - Count occurrences in Wikipedia RO
   - Count occurrences in OSCAR Romanian
   - Cross-reference frequencies

3. **Rarity scoring algorithm**
   - Combine DEX frequency + corpus frequency
   - Add markers (înv., reg., dial.)
   - Generate final forgotten words list

4. **Export results**
   - CSV with full metadata
   - JSON for web interface
   - Statistics and visualizations

## Scripts Created

- `create_sample_db.py` - Creates 285MB sample from 1.2GB dump
- `extract_lexemes.py` - Extracts Lexeme table to CSV + SQLite
- `mysql_to_sqlite.py` - (backup method, not fully working)

## Tools & Commands

### Query the database:
```bash
sqlite3 data/processed/lexemes.db
```

### Sample queries:
```bash
# Count total
sqlite3 data/processed/lexemes.db "SELECT COUNT(*) FROM Lexeme;"

# Low frequency words
sqlite3 data/processed/lexemes.db "
SELECT form, frequency FROM Lexeme
WHERE frequency < 0.6 AND frequency > 0
ORDER BY frequency LIMIT 20;
"

# Frequency distribution
sqlite3 data/processed/lexemes.db "
SELECT
    ROUND(frequency, 1) as freq_bucket,
    COUNT(*) as count
FROM Lexeme
WHERE frequency > 0
GROUP BY freq_bucket
ORDER BY freq_bucket;
"
```

---

**Status**: ✅ Development database ready!
**Size**: 26 MB (vs 1.2 GB original)
**Records**: 315,247 lexemes
**Ready for**: Forgotten words analysis
