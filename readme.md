# Oțios - Romanian Forgotten Words Finder

A computational linguistics tool to identify "forgotten" Romanian words - terms that exist in official dictionaries but have fallen out of modern usage.

**Status**: 🚧 Phase 2 In Progress - Corpus Validation Ready

## What It Does

- Generates a list of the *least used* or forgotten words from Romanian dictionaries
- Compares official dictionaries (including archaisms) against usage frequency data
- Identifies linguistic "dark matter" - words that exist in dictionaries but have fallen out of active use
- Produces curated lists with rarity scores and linguistic metadata

## Quick Start

### Prerequisites

```bash
# Activate virtual environment
source ~/devbox/envs/otzios/bin/activate

# Install required packages for Phase 2
pip install datasets
```

### Phase 1: Dictionary Analysis

```bash
# 1. Create sample database (reduces 1.2GB to 285MB)
python create_sample_db.py

# 2. Extract lexeme data (creates CSV + SQLite database)
python extract_lexemes.py

# 3. Generate analysis and statistics
python analyze_forgotten_words.py

# 4. Create final curated list
python create_curated_list.py
```

**Output**: `forgotten_words_curated.csv` (1,884 candidates)

### Phase 2: Corpus Validation (NEW!)

```bash
# 1. Test with small sample (2-5 min)
python process_corpus.py --test

# 2. Process full corpora (2-3 hours)
python process_corpus.py --full

# 3. Validate words
python validate_forgotten_words.py
```

**Output**: `forgotten_words_validated.csv` (~1,400-1,900 validated words)

## Project Structure

```
otios/
├── data/
│   ├── dictionaries/       # DEX Online database (download separately)
│   └── processed/          # Generated lexeme data and results
├── docs/                   # Documentation and specifications
│   ├── scripts-guide.md    # Detailed script documentation
│   ├── romanian-forgotten-words-spec.md
│   └── results-summary.md
└── *.py                    # Processing scripts
```

## Documentation

- **[docs/scripts-guide.md](docs/scripts-guide.md)** - Comprehensive guide to all scripts
- **[docs/romanian-forgotten-words-spec.md](docs/romanian-forgotten-words-spec.md)** - Technical specification
- **[docs/results-summary.md](docs/results-summary.md)** - Analysis results and findings
- **[docs/oțios.docx.md](docs/oțios.docx.md)** - Initial brainstorming document

## Sample Results

| Word | Type | Frequency | Category |
|------|------|-----------|----------|
| **bucle** | adj. | 0.030 | very_rare |
| **jălitor** | adj./s.m. | 0.070 | very_rare |
| **griere** | s.m. | 0.300 | rare |
| **celadon** | s.n. | 0.500 | uncommon |

## Data Sources

- **DEX Online Database**: Official Romanian dictionary (1.2 GB MySQL dump)
  - Download: [dexonline.ro](https://wiki.dexonline.ro/wiki/Informa%C8%9Bii#Desc%C4%83rcare)
  - 315,247 lexemes with frequency data
  - Archaic markers and linguistic metadata

## Roadmap

### Phase 1: MVP (Complete ✅)
- [x] Database setup and conversion
- [x] Lexeme extraction pipeline
- [x] Frequency-based analysis
- [x] Quality filtering and curation
- [x] CSV export with 1,884 words

### Phase 2: Corpus Validation 
- [ ] Download Romanian Wikipedia dump
- [ ] Sample OSCAR Romanian corpus
- [ ] Cross-reference with modern text corpora
- [ ] Validate "forgotten" status in contemporary usage

### Phase 3: Enhanced Metadata
- [ ] Extract definitions from DEX
- [ ] Identify archaic markers (înv., arh., reg.)
- [ ] Add etymology information
- [ ] Temporal analysis (when words fell out of use)

### Future
- [ ] Web interface for browsing words
- [ ] API for programmatic access
- [ ] Visualization dashboards
- [ ] Revival potential scoring

## Contributing

See [CLAUDE.md](CLAUDE.md) for development guidelines and project context.

## License

[License TBD]
