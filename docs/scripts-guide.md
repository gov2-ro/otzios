# Scripts Guide - Oțios Project

Complete documentation for all scripts in the Romanian Forgotten Words project.

---

## Overview

The project uses a multi-stage pipeline to identify forgotten Romanian words:

```
Raw MySQL Dump → Sample DB → SQLite Conversion → Analysis → Curated List
```

**Scripts execution order:**
1. `create_sample_db.py` - Create manageable sample (optional but recommended)
2. `mysql_to_sqlite.py` - Convert to SQLite (alternative approach)
3. `extract_lexemes.py` - Extract lexeme data to CSV/SQLite (recommended)
4. `analyze_forgotten_words.py` - Generate initial analysis
5. `create_curated_list.py` - Create final curated list

**Utility scripts:**
- `explore_dex.py` - Database structure documentation (reference only)

---

## Scripts Documentation

### 1. `explore_dex.py`

**Purpose**: Documentation and exploration of DEX Online database structure.

**Type**: Reference/Documentation

**Usage**:
```bash
python explore_dex.py
```

**What it does**:
- Documents the structure of the DEX Online database
- Lists key tables (Lexeme, Entry, Abbreviation, etc.)
- Shows important fields for forgotten word detection
- Displays sample data examples
- **Does not modify any files** - purely informational

**When to use**:
- When you need to understand the database schema
- As a reference for table structures and relationships
- Before writing custom queries

**Output**: Console output only (no files created)

---

### 2. `create_sample_db.py`

**Purpose**: Create a development-friendly sample of the large DEX database.

**Input**:
- `data/dictionaries/dex-database.sql` (1.2 GB MySQL dump)

**Output**:
- `data/dictionaries/dex-database-sample.sql` (~285 MB)

**Strategy**:
- Keeps 100% of critical tables (Lexeme, Entry, Abbreviation)
- Samples 10% of supporting tables
- Skips large unnecessary tables (FullTextIndex, CrawlerData)
- Preserves all schema (CREATE TABLE statements)

**Usage**:
```bash
python create_sample_db.py
```

**What it does**:
1. Reads the full 1.2 GB MySQL dump file
2. Identifies table types (critical/supporting/skip)
3. Selectively copies INSERT statements:
   - **100% retention**: Lexeme, Entry, Abbreviation (essential for forgotten words)
   - **10% sample**: Other supporting tables
   - **Skipped**: FullTextIndex (500+ MB of search indexes)
4. Creates a smaller but functional database

**Performance**:
- Processing time: 2-5 minutes
- Size reduction: 1.2 GB → ~285 MB (76% reduction)

**When to use**:
- First time setup (before any other scripts)
- When the full database is too large to work with
- For development and testing

**Critical tables kept at 100%**:
- `Lexeme` - Word forms with frequency data (essential!)
- `Entry` - Dictionary entries
- `Abbreviation` - Archaic markers like 'înv.'
- `EntryLexeme` - Links between entries and lexemes
- `Meaning` - Word meanings
- `Definition` - Full definitions

**Note**: If you have plenty of disk space and RAM, you can skip this and work with the full database.

---

### 3. `mysql_to_sqlite.py`

**Purpose**: Convert MySQL dump to SQLite database (alternative to extract_lexemes.py).

**Input**:
- `data/dictionaries/dex-database-sample.sql`

**Output**:
- `data/dictionaries/dex-sample.db` (SQLite database)

**Usage**:
```bash
python mysql_to_sqlite.py
```

**What it does**:
1. Reads MySQL SQL dump file
2. Converts MySQL syntax to SQLite:
   - Removes MySQL-specific commands (LOCK TABLES, SET)
   - Converts data types (int→INTEGER, varchar→TEXT)
   - Handles AUTO_INCREMENT → AUTOINCREMENT
   - Removes ENGINE, CHARSET clauses
3. Executes SQL statements in SQLite
4. Verifies data integrity
5. Shows sample forgotten word candidates

**Processing details**:
- Commits every 100 statements for performance
- Handles Romanian diacritics properly (UTF-8)
- Skips incompatible statements gracefully
- Progress indicators every 1000 lines

**When to use**:
- If you need the complete database structure (all tables)
- If you want to query beyond just Lexeme data
- For exploring table relationships

**Note**: Most users should use `extract_lexemes.py` instead, which is faster and more focused.

---

### 4. `extract_lexemes.py` ⭐ **Recommended**

**Purpose**: Fast extraction of Lexeme table to CSV and SQLite (recommended approach).

**Input**:
- `data/dictionaries/dex-database-sample.sql` (or full SQL dump)

**Output**:
- `data/processed/lexemes.csv` (~30 MB)
- `data/processed/lexemes.db` (~26 MB SQLite)

**Usage**:
```bash
# Activate virtual environment first!
source ~/devbox/envs/otzios/bin/activate

python extract_lexemes.py
```

**What it does**:
1. **Parses MySQL INSERT statements** directly (no database conversion needed)
2. **Extracts only Lexeme table** data (faster than full conversion)
3. **Creates CSV file** with all lexeme data
4. **Creates SQLite database** from CSV
5. **Verifies data** and shows sample forgotten words

**Why use this instead of mysql_to_sqlite.py?**
- Much faster (only processes Lexeme table)
- Smaller output (~26 MB vs full database)
- CSV export for easy inspection in spreadsheets
- Focused on forgotten words task

**Lexeme table columns**:
- `id` - Unique identifier
- `form` - Word with diacritics (e.g., "țară")
- `formNoAccent` - Word without diacritics
- `frequency` - Usage frequency (0.0-1.0) - **CRITICAL for forgotten words!**
- `description` - Part of speech (adj., s.m., vb., etc.)
- `modelType`, `modelNumber` - Morphological information
- And 15+ other metadata fields

**Sample output**:
```
Extracted 315,247 lexemes to data/processed/lexemes.csv
✅ Database created with 315,247 lexemes

Sample forgotten word candidates (low frequency):
  - bucle (adj.): frequency=0.030
  - poținel (adv.): frequency=0.030
  - precoace (adj.): frequency=0.030
```

**Performance**:
- Processing time: 1-3 minutes
- Memory usage: Low (<500 MB)
- Output size: CSV ~30 MB, DB ~26 MB

**When to use**:
- **Always use this as your primary data extraction method**
- First step after creating sample database
- When you need CSV export for analysis in Excel/pandas

---

### 5. `analyze_forgotten_words.py`

**Purpose**: Generate comprehensive analysis and initial forgotten words list.

**Input**:
- `data/processed/lexemes.db` (from extract_lexemes.py)

**Output**:
- `data/processed/forgotten_words_v1.csv` (~187k words - raw unfiltered)
- `data/processed/statistics.txt` (summary statistics)

**Usage**:
```bash
source ~/devbox/envs/otzios/bin/activate
python analyze_forgotten_words.py
```

**What it does**:
1. **Analyzes entire lexeme database** (315k words)
2. **Generates frequency distribution statistics**:
   - Very rare (0.01-0.25): 66k words
   - Rare (0.25-0.50): 69k words
   - Uncommon (0.50-0.70): 55k words
   - Common (0.70-0.85): 42k words
   - Very common (0.85-1.0): 45k words
3. **Part-of-speech distribution** for rare words
4. **Exports forgotten word candidates** (frequency < 0.70)
5. **Categorizes by rarity**
6. **Saves summary statistics** to text file

**Selection criteria**:
- Frequency > 0.01 (exclude zeros/errors)
- Frequency < 0.70 (rare/uncommon threshold)
- Word length > 2 characters (exclude abbreviations)

**Output format (CSV)**:
```csv
word,word_no_accent,frequency,category,description,model_type,create_date,mod_date
bucle,bucle,0.0300,very_rare,adj.,,1234567890,1234567890
griere,griere,0.3000,rare,s.m.,,1234567890,1234567890
```

**Statistics generated**:
- Total lexemes count
- Frequency distributions
- Part-of-speech breakdown
- Category counts (very_rare, rare, uncommon)

**When to use**:
- After extracting lexemes with `extract_lexemes.py`
- When you need comprehensive statistics
- To generate the initial unfiltered candidate list

**Note**: This produces ~187k candidates including proper nouns, technical terms, compounds. Use `create_curated_list.py` for filtered results.

---

### 6. `create_curated_list.py` ⭐ **Final Output**

**Purpose**: Create high-quality, filtered list of forgotten Romanian words.

**Input**:
- `data/processed/lexemes.db`

**Output**:
- `data/processed/forgotten_words_curated.csv` (1,884 high-quality words)

**Usage**:
```bash
source ~/devbox/envs/otzios/bin/activate
python create_curated_list.py
```

**What it does**:
1. **Queries low-frequency words** (frequency < 0.60)
2. **Applies quality filters**:
   - ✅ Has meaningful linguistic description
   - ✅ Not a proper noun (excludes "București", "Einstein")
   - ✅ Traditional Romanian vocabulary (excludes Latin phrases)
   - ✅ Not a compound/multi-word phrase
   - ✅ Minimum length > 3 characters
3. **Categorizes by rarity**:
   - Very rare (0.01-0.30): 413 words
   - Rare (0.30-0.50): 543 words
   - Uncommon (0.50-0.60): 928 words
4. **Exports curated list** with metadata

**Quality filters in detail**:

**Proper noun filter**:
- Removes: "București", "Einstein", "Paris"
- Keeps: "bucle", "griere", "jălitor"

**Romanian word filter**:
- Removes: Multi-word Latin phrases, foreign terms
- Removes: Strange hyphenation patterns
- Keeps: Traditional Romanian vocabulary

**Meaningful description filter**:
- Requires: adj., s.m., s.f., vb., adv., interj.
- Requires: Or archaic markers (înv., reg., arh.)
- Removes: Empty descriptions, pure model codes

**Output format (CSV)**:
```csv
word,word_no_accent,frequency,rarity_category,description,model_type,notes
bucle,bucle,0.0300,very_rare,adj.,,
băt'ârn,bat'arn,0.0500,very_rare,adj./s.m.,,
jălitor,jalitor,0.0700,very_rare,adj./s.m.,,
```

**Final counts**:
- Initial candidates: ~187k
- Filtered out proper nouns: 1,278
- Filtered out foreign/technical: 1
- Filtered out no description: 2,743
- **Final curated list: 1,884 words**

**When to use**:
- **Final step in the pipeline**
- When you need the highest quality forgotten words list
- For publication, research, or presentation

**This is the primary output of the MVP!**

---

## Complete Workflow

### Quick Start (Recommended Path)

```bash
# 1. Activate virtual environment
source ~/devbox/envs/otzios/bin/activate

# 2. Create sample database (optional but recommended)
python create_sample_db.py

# 3. Extract lexeme data
python extract_lexemes.py

# 4. Generate analysis
python analyze_forgotten_words.py

# 5. Create curated list (FINAL OUTPUT)
python create_curated_list.py
```

### Full Database Path (Alternative)

If you want to work with the complete database:

```bash
source ~/devbox/envs/otzios/bin/activate

# Skip sampling, work with full database
python extract_lexemes.py  # Use full SQL file

# Or convert full database
python mysql_to_sqlite.py

# Then continue with analysis
python analyze_forgotten_words.py
python create_curated_list.py
```

---

## Output Files Summary

### Generated Files

| File | Size | Description | Script |
|------|------|-------------|--------|
| `dex-database-sample.sql` | 285 MB | Sampled MySQL dump | `create_sample_db.py` |
| `dex-sample.db` | Varies | Full SQLite conversion | `mysql_to_sqlite.py` |
| `lexemes.csv` | 30 MB | Lexeme data in CSV | `extract_lexemes.py` |
| `lexemes.db` | 26 MB | Lexeme SQLite database | `extract_lexemes.py` |
| `forgotten_words_v1.csv` | Large | Raw unfiltered list (187k) | `analyze_forgotten_words.py` |
| `statistics.txt` | Small | Summary statistics | `analyze_forgotten_words.py` |
| `forgotten_words_curated.csv` | Small | **FINAL LIST** (1,884 words) ⭐ | `create_curated_list.py` |

### Key Output

**The primary output is**: `data/processed/forgotten_words_curated.csv`

This contains 1,884 high-quality forgotten Romanian words with:
- Low frequency scores (< 0.60)
- Meaningful linguistic descriptions
- Filtered to remove proper nouns and technical terms
- Categorized by rarity level

---

## Troubleshooting

### Virtual Environment Issues

**Problem**: `command not found: python3` or missing modules

**Solution**:
```bash
# Always activate virtual environment first
source ~/devbox/envs/otzios/bin/activate

# Verify it's activated (should show venv path)
which python
```

### File Not Found Errors

**Problem**: `FileNotFoundError: data/dictionaries/dex-database.sql`

**Solution**:
- Ensure you've downloaded the DEX database to `data/dictionaries/`
- Check the file path in the script matches your setup
- Run scripts from project root directory

### Memory Issues

**Problem**: Script crashes with memory error

**Solution**:
- Use `create_sample_db.py` to reduce database size first
- Use `extract_lexemes.py` instead of `mysql_to_sqlite.py` (more efficient)
- Close other applications to free RAM

### Encoding Issues

**Problem**: Romanian diacritics appear corrupted

**Solution**:
- All scripts use UTF-8 encoding by default
- Ensure your terminal supports UTF-8
- Check input files are UTF-8 encoded

### Empty Results

**Problem**: No forgotten words found

**Solution**:
- Verify `lexemes.db` has data: `sqlite3 data/processed/lexemes.db "SELECT COUNT(*) FROM Lexeme;"`
- Check frequency threshold settings in scripts
- Ensure database was created successfully

---

## Data Quality Notes

### Frequency Score Interpretation

The `frequency` field (0.0-1.0) represents usage in DEX's internal corpus:

- **0.85-1.0**: Very common everyday words (de, a, și, cu)
- **0.70-0.85**: Common words (known to most speakers)
- **0.50-0.70**: Uncommon but recognized
- **0.25-0.50**: Rare - candidates for forgotten words
- **0.01-0.25**: Very rare - likely forgotten
- **< 0.01**: Extremely rare or data errors

### Limitations

1. **Frequency is DEX-internal**: Not based on modern Romanian corpora
2. **No temporal data**: Can't determine when words fell out of use
3. **No definitions yet**: Need to join with Definition table (future work)
4. **Technical terms**: Some may slip through filters
5. **Regional variations**: May include valid dialectal words

### Next Steps (Phase 2)

To improve accuracy:
- Download modern Romanian corpora (Wikipedia, OSCAR)
- Cross-reference DEX frequency with corpus frequency
- Extract definition text from database
- Identify archaic markers in definitions
- Add temporal analysis using historical texts

---

## Script Development Notes

### Adding New Filters

To add custom filters in `create_curated_list.py`:

```python
def my_custom_filter(word_data):
    """Add your filter logic here."""
    form, frequency, description = word_data[0], word_data[2], word_data[3]
    # Your filter logic
    return True  # or False to filter out

# Add to filtering loop:
if not my_custom_filter(word_data):
    continue
```

### Custom Queries

To write custom SQL queries against the database:

```bash
sqlite3 data/processed/lexemes.db

# Example queries:
SELECT form, frequency FROM Lexeme WHERE description LIKE '%înv%' LIMIT 10;
SELECT COUNT(*) FROM Lexeme WHERE frequency < 0.5;
SELECT description, COUNT(*) FROM Lexeme GROUP BY description LIMIT 20;
```

### Performance Optimization

- Use streaming for large files
- Commit SQLite transactions in batches (every 100 records)
- Use CSV as intermediate format for inspection
- Index frequently queried columns

---

## Additional Resources

- **Database schema**: See [docs/dex-database-analysis.md](dex-database-analysis.md)
- **Project spec**: See [docs/romanian-forgotten-words-spec.md](romanian-forgotten-words-spec.md)
- **Results summary**: See [docs/results-summary.md](results-summary.md)
- **DEX Online wiki**: https://wiki.dexonline.ro/
- **GitHub schema docs**: https://github.com/dexonline/dexonline/wiki/Database-Schema

---

**Last updated**: October 2025
