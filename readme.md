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

### Phase 1: Dictionary Analysis (Complete ✅)
- [x] Database setup and conversion
- [x] Lexeme extraction pipeline
- [x] Frequency-based analysis
- [x] Quality filtering and curation
- [x] CSV export with 1,884 candidates

**Output**: `forgotten_words_curated.csv` - 1,884 forgotten word candidates

### Phase 2: Corpus Validation (In Progress 🚧)
- [x] Implement corpus processing pipeline
- [x] Wikipedia Romanian integration (HuggingFace)
- [x] Romanian tokenization with diacritic handling
- [x] Word frequency counting system
- [x] Cross-reference validation algorithm
- [x] Confidence scoring system
- [x] False positive detection
- [x] Test run (1,000 articles) - **Successful!**
- [ ] Full Wikipedia processing (~500k articles)
- [ ] OSCAR Romanian corpus (requires auth setup)
- [ ] Additional corpora (news, social media)

**Current Status**: Test run complete, ready for full processing
**Output**: `forgotten_words_validated.csv` - Cross-referenced with modern text

#### Phase 2 Test Results (Oct 2025)
✅ **Processed**: 1,001 Wikipedia articles (1M tokens)
✅ **Validated**: 159,543 words
✅ **False positives detected**: 1 ("online" - correctly flagged)
✅ **Performance**: 2,351 articles/second

See [docs/phase2-test-results.md](docs/phase2-test-results.md) for details.

### Phase 3: Enhanced Metadata
- [ ] Extract full definitions from DEX database
- [ ] Join Definition and DefinitionSimple tables
- [ ] Identify archaic markers (înv., arh., reg., dial.)
- [ ] Extract etymology information
- [ ] Parse first attestation dates
- [ ] Temporal analysis (when words fell out of use)
- [ ] Link to word families and cognates
- [ ] Add part-of-speech tagging improvements

### Phase 4: Lemmatization & Advanced NLP
- [ ] Integrate Romanian lemmatizer (spaCy-ro or nlp-cube)
- [ ] Match inflected forms to base words
- [ ] Improve recall (find "frumoaselor" when searching "frumos")
- [ ] Named entity recognition for better filtering
- [ ] Semantic clustering of forgotten words

### Phase 5: User Interface & Visualization
- [ ] Web interface for browsing words
  - Search and filter by frequency, category
  - Word detail pages with definitions
  - Corpus occurrence examples
- [ ] REST API for programmatic access
- [ ] Interactive visualizations
  - Frequency distribution charts
  - Word cloud of forgotten words
  - Temporal decay graphs
  - Etymological origin breakdowns
- [ ] Export functionality (JSON, PDF, LaTeX)

### Future Enhancements
- [ ] Revival potential scoring algorithm
- [ ] Compare with other Romance languages
- [ ] Historical corpus analysis (Project Gutenberg)
- [ ] Machine translation of forgotten word contexts
- [ ] Crowdsourced validation platform
- [ ] Word-of-the-day feature
- [ ] Educational tools and quizzes

## Known Issues & Limitations

### Current Limitations
1. **No lemmatization**: Only exact word matching (misses inflected forms)
2. **OSCAR access**: Requires HuggingFace authentication (gated dataset)
3. **Small test corpus**: Only 1k articles tested so far
4. **No definitions yet**: Metadata not extracted from DEX database
5. **False positives**: Modern borrowings (burger, online) need better filtering

### Planned Improvements
1. **Filter refinement**:
   - Add modern borrowing detection (English/French loanwords)
   - Improve proper noun filtering
   - Better compound word handling
   - Technical term detection

2. **Corpus expansion**:
   - Full Wikipedia processing (500k articles)
   - OSCAR Romanian (250k documents)
   - Romanian news archives
   - Social media (Reddit r/Romania)
   - Historical texts for temporal analysis

3. **Performance optimization**:
   - Parallel processing for corpus streaming
   - Batch tokenization
   - Index optimization for large-scale queries

## Next Steps

### Immediate (Ready to Run)
```bash
# Process full Wikipedia corpus
python process_corpus.py --full --wikipedia-only

# Validate with full dataset
python validate_forgotten_words.py
```

### Short-term (Next Sprint)
1. Run full Wikipedia validation
2. Set up HuggingFace authentication for OSCAR
3. Extract definitions from DEX database
4. Manual review of questionable words
5. Improve filtering rules based on findings

### Medium-term (Next Month)
1. Integrate Romanian lemmatizer
2. Add more corpora sources
3. Extract full metadata (etymology, attestation dates)
4. Create basic web interface prototype
5. Write academic paper on findings

## Contributing

See [CLAUDE.md](CLAUDE.md) for development guidelines and project context.

## License

[License TBD]
