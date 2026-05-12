# Oțios - Romanian Forgotten Words Finder

Vezi și: [initial specs](docs/oțios-init-specs.docx.md) / [live](https://docs.google.com/document/d/1FTMIONmSylQDaV4YxFprd8jyHxREXpcL/) (google doc) 

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

### Phase 2a: Quick frequency screen (wordfreq)

```bash
python validate_with_wordfreq.py
```

**Output**: `forgotten_words_validated_wordfreq.csv` — 1,868 candidates with Zipf < 3.0. Note: wordfreq's Romanian coverage is binary (a word is either in its top ~1,500 or returns 0.000), so treat this as a rough first pass, not a nuanced frequency measure.

### Phase 2b: Corpus validation — diachronic (recommended)

Uses Wikisource RO (historical literary baseline) and CulturaX RO (modern web) to compute actual per-corpus frequencies. Designed to find words that appear in 19th-century literature but are absent from modern text.

```bash
# Wikisource — test run (500 docs, ~10s)
python process_wikisource.py --test

# Wikisource — full run (best on a VPS)
mkdir -p data/logs
nohup python process_wikisource.py --resume >> data/logs/wikisource.log 2>&1 &
echo $! > data/logs/wikisource.pid

# CulturaX — full run (64 parquet shards, ~40M docs; auto-restarts on kill)
VENV=~/g2-dev/monitorulpreturilor/venv/bin/python
mkdir -p data/logs
nohup bash -c "while true; do $VENV -u process_culturax.py --resume; [ \$? -eq 0 ] && break; sleep 15; done" \
  >> data/logs/culturax.log 2>&1 &
echo $! > data/logs/culturax.pid
```

**Output**: `corpus_frequencies.db` with `corpus_name = 'wikisource_ro'` and `corpus_name = 'culturax_ro'`.

Note: `process_culturax.py` reads the 64 parquet shards directly via `HfFileSystem` + `pyarrow` and checkpoints at file + row-group level. This avoids the `datasets` streaming `ds.skip()` cycling bug that triggers when the checkpoint offset exceeds the dataset size.

## Monitoring

`health_check.py`, `audit.py`, and `status.py` keep tabs on long-running corpus jobs. Run them manually or via cron (see CLAUDE.md for crontab lines).

```bash
python status.py                # at-a-glance summary — corpora, artifacts, loops, audit
python health_check.py          # check liveness, stalls, log errors, completion
python audit.py                 # snapshot run history + DB quality checks
python health_check.py --dry-run  # print without alerting or writing state
```

`status.py` is read-only — safe to run any time. `health_check.py` and `audit.py` write logs and may alert.

Set `OTZIOS_ALERT_URL` (webhook) or `OTZIOS_ALERT_EMAIL` to receive push alerts.

## Data notes

**Apostrophes in the `word` column** — DEX Online encodes syllable stress using apostrophes (e.g. `bucl'e`, `băt'ârn`). These are not real Romanian words; the clean form is in `word_no_accent`. The validated output from `validate_with_wordfreq.py` uses `word_no_accent` for all lookups and moves the raw `word` column to the end of the CSV for reference.

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
- more docs: PHASE2_COMPLETE.md; phase2-test-results.md; scripts-guide.md

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

### misc notes / tasks

- [ ] fix mysql import - try a llm assisted import
- [ ] create another sample db with max 3 inserts per table - for analytics

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
- [ ] Create a reverse, browse news and r/romania and find new words, used more than 3? times that are not in dictionary -> alternative dictionary

### Further enhancements, marketing
- tools: convert texts to archaic form - less used words. with a coeficient of uniqueness (bigger number, harder words)
- filter out uninteresting words. Too domain specific: medicine, biology etc
- one word a day game? quizz, guess what it means?

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
