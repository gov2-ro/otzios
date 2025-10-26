# Romanian Forgotten Words Project
## Technical Specification Document

### Version 1.0 - January 2025

---

## 1. Executive Summary

### Project Overview
A computational linguistics tool to identify "forgotten" Romanian words - terms that exist in official dictionaries but have fallen out of modern usage. By comparing comprehensive dictionary entries against contemporary text corpora, this project aims to discover and catalog words that have effectively disappeared from active Romanian vocabulary.

---

## 2. Technical Architecture

### System Overview
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Data Sources   │────▶│  Processing      │────▶│    Analysis     │
├─────────────────┤     ├──────────────────┤     ├─────────────────┤
│ • DEX Online    │     │ • Tokenization   │     │ • Frequency     │
│ • OSCAR Corpus  │     │ • Lemmatization  │     │ • Rarity Score  │
│ • Wikipedia RO  │     │ • Normalization  │     │ • Temporal      │
│ • News Archives │     │ • Deduplication  │     │ • Categories    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │
                                ▼
                    ┌──────────────────┐
                    │   Data Storage   │
                    ├──────────────────┤
                    │ • SQLite (MVP)   │
                    │ • PostgreSQL (v2)│
                    └──────────────────┘
                                │
                                ▼
                    ┌──────────────────┐
                    │     Outputs      │
                    ├──────────────────┤
                    │ • CSV/JSON       │
                    │ • Web Interface  │
                    │ • API (future)   │
                    └──────────────────┘
```

### Technology Stack

#### MVP Stack (Phase 1)
- **Language**: Python 3.9+
- **Database**: SQLite
- **Text Processing**: NLTK, spaCy-ro
- **Data Pipeline**: pandas, datasets (HuggingFace)
- **Storage**: Local filesystem (~5-10GB)

#### Production Stack (Phase 2+)
- **Database**: PostgreSQL with full-text search
- **Cache**: Redis for frequency lookups
- **Queue**: Celery for batch processing
- **Deployment**: Docker + GitHub Actions
- **Web**: FastAPI + Svelte

---

## 3. Data Specifications

### Dictionary Sources

| Source | Size | Format |
|--------|------|--------|
| DEX Online | ~65k entries | XML/JSON API |


### Corpus Sources

| Source | Size | Documents |
|--------|------|-----------|
| Wikipedia RO | 1.2 GB | ~500k articles |
| OSCAR | 39 GB | ~5M docs |
| Romanian News | Variable |
| Reddit r/Romania | ~2 GB |
| Romanian Blogs | Variable |

### Database Schema

```sql
-- Core Tables
CREATE TABLE dictionary_words (
    id INTEGER PRIMARY KEY,
    word VARCHAR(100) UNIQUE NOT NULL,
    lemma VARCHAR(100),
    definition TEXT,
    etymology TEXT,
    first_attestation INTEGER,  -- year
    dictionary_source VARCHAR(50),
    pos VARCHAR(20),  -- part of speech
    is_archaic BOOLEAN DEFAULT FALSE,
    is_regional BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE corpus_frequencies (
    id INTEGER PRIMARY KEY,
    word VARCHAR(100),
    corpus_name VARCHAR(50),
    frequency INTEGER,
    document_count INTEGER,
    last_seen DATE,
    total_words_in_corpus BIGINT,
    UNIQUE(word, corpus_name)
);

CREATE TABLE forgotten_words (
    id INTEGER PRIMARY KEY,
    word_id INTEGER REFERENCES dictionary_words(id),
    rarity_score FLOAT,  -- 0-1, higher = more forgotten
    last_common_decade INTEGER,  -- e.g., 1960
    suggested_alternative VARCHAR(100),
    category VARCHAR(50),  -- 'archaic', 'regional', 'technical', etc
    revival_potential VARCHAR(20),  -- 'high', 'medium', 'low'
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for performance
CREATE INDEX idx_word_lookup ON dictionary_words(word, lemma);
CREATE INDEX idx_frequency_lookup ON corpus_frequencies(word, frequency);
CREATE INDEX idx_rarity ON forgotten_words(rarity_score DESC);
```

---

## 4. Processing Pipeline

### Phase 1: Data Ingestion
```python
# Pipeline stages
1. Dictionary Loading
   - Parse DEX Online dump/API
   - Extract word, definition, metadata
   - Handle special characters (ă, â, î, ș, ț)
   - Store in dictionary_words table

2. Wordfreq Filtering
   - Load top 100k Romanian words from wordfreq
   - Mark as "common" in database
   - Remove from forgotten candidates

3. Corpus Processing
   - Stream large corpora (OSCAR, mC4)
   - Tokenize and normalize text
   - Count word frequencies
   - Store in corpus_frequencies table
```

### Phase 2: Analysis
```python
# Forgotten word identification
1. Candidate Selection
   - Words in dictionary but not in wordfreq top 100k
   - Words with corpus frequency < threshold

2. Rarity Scoring
   - Frequency per billion words
   - Number of unique documents containing word
   - Temporal decay rate
   - Cross-corpus consistency

3. Categorization
   - Archaic (temporal decay)
   - Regional (geographic clustering)
   - Technical (domain-specific)
   - Neologism failures (recent but rare)
```

### Text Normalization Rules
- Convert старі-style diacritics: ş→ș, ţ→ț
- Handle î/â variations (Romanian spelling reforms)
- Remove punctuation for matching
- Preserve hyphenated words initially
- Case-insensitive matching (with case-preservation option)

---

## 5. Implementation Roadmap

### Phase 1: MVP (Weeks 1-4)
**Goal**: Proof of concept with basic forgotten word identification

#### Week 1: Foundation
- [x] Set up project structure
- [ ] Install dependencies
- [ ] Create SQLite database schema
- [ ] Write DEX Online data fetcher
- [ ] Load wordfreq Romanian common words

#### Week 2: Data Pipeline
- [ ] Implement Wikipedia Romanian processor
- [ ] Build basic tokenizer for Romanian
- [ ] Create frequency counter
- [ ] Store results in database
- [ ] Write comparison script (DEX - wordfreq - corpus)

#### Week 3: Analysis
- [ ] Generate first forgotten words list
- [ ] Implement rarity scoring algorithm
- [ ] Add basic categorization
- [ ] Create CSV export functionality
- [ ] Manual validation of 100 samples

#### Week 4: Refinement
- [ ] Handle Romanian diacritics properly
- [ ] Add OSCAR corpus sampling
- [ ] Improve tokenization (punctuation, hyphenation)
- [ ] Generate statistics and summary report
- [ ] Document findings

### Phase 2: Enhanced Analysis (Weeks 5-8)
**Goal**: Improve accuracy and add temporal analysis

- [ ] Implement lemmatization with spaCy-ro
- [ ] Add news corpus for recent language
- [ ] Build temporal decay analysis
- [ ] Create word revival potential scoring
- [ ] Add etymology and first attestation data
- [ ] Implement false positive detection
- [ ] Add more sophisticated categorization

### Phase 3: Scale & Performance (Weeks 9-12)
**Goal**: Process full corpora efficiently

- [ ] Migrate to PostgreSQL
- [ ] Implement parallel processing
- [ ] Add Redis caching layer
- [ ] Process full OSCAR corpus
- [ ] Add incremental update capability
- [ ] Optimize query performance
- [ ] Create data quality metrics

### Phase 4: User Interface (Weeks 13-16)
**Goal**: Make data accessible to researchers

- [ ] Build REST API with FastAPI
- [ ] Create web interface for browsing
- [ ] Add search and filter capabilities
- [ ] Implement data visualization
- [ ] Create word detail pages
- [ ] Add export functionality
- [ ] Deploy to cloud platform

---

## 6. Feature Specifications

### Core Features (MVP)

#### F1: Dictionary Ingestion
```python
def ingest_dex_dictionary():
    """
    Load and parse DEX Online dictionary
    - Handle multiple dictionary sources
    - Extract structured data
    - Normalize Romanian characters
    - Return: dict of {word: metadata}
    """
```

#### F2: Corpus Frequency Analysis
```python
def analyze_corpus_frequency(corpus_name, text_stream):
    """
    Count word frequencies in corpus
    - Tokenize Romanian text
    - Handle streaming for large files
    - Update frequency database
    - Return: frequency distribution
    """
```

#### F3: Forgotten Word Detection
```python
def identify_forgotten_words(
    min_dictionary_sources=1,
    max_corpus_frequency=0.1,  # per million
    min_rarity_score=0.7
):
    """
    Find words that exist in dictionaries but not in modern use
    - Apply thresholds
    - Calculate rarity scores
    - Categorize results
    - Return: list of ForgottenWord objects
    """
```

### Advanced Features (Future)

#### F4: Temporal Decay Analysis
- Track word usage over time using dated corpora
- Identify when words "died"
- Predict future obsolescence
- Generate decay curves

#### F5: Regional Analysis
- Map forgotten words to regions
- Identify dialectal extinctions
- Track urban/rural vocabulary differences

#### F6: Semantic Network Analysis
- Find forgotten concept clusters
- Identify semantic gaps in modern Romanian
- Suggest revival candidates based on semantic need

#### F7: Revival Potential Scoring
```python
def calculate_revival_potential(word):
    """
    Score how viable a word is for reintroduction
    Factors:
    - Semantic uniqueness (no good modern equivalent)
    - Phonological attractiveness
    - Morphological regularity
    - Cultural relevance
    """
```

#### F8: Comparative Linguistics
- Compare Romanian forgotten words with other Romance languages
- Identify pan-Romance vocabulary loss
- Track Slavic/Turkish/Hungarian loanword decay

---

## 7. API Specifications

### RESTful Endpoints (Future)

```python
# Search endpoints
GET /api/v1/forgotten-words
    ?rarity_min=0.7
    &category=archaic
    &limit=100
    &offset=0

GET /api/v1/forgotten-words/{word_id}
    Returns: detailed word information

# Analysis endpoints  
GET /api/v1/words/{word}/frequency
    Returns: frequency across all corpora

GET /api/v1/words/{word}/timeline
    Returns: historical usage data

GET /api/v1/statistics
    Returns: project-wide statistics

# Export endpoints
GET /api/v1/export/csv
    ?category=all
    &min_rarity=0.5

POST /api/v1/validate/{word_id}
    Body: {is_forgotten: true, notes: "..."}
```

### Response Format
```json
{
  "status": "success",
  "data": {
    "word": "norod",
    "definition": "mulțime de oameni; gloată",
    "rarity_score": 0.89,
    "last_common_decade": 1960,
    "frequency_per_billion": 0.23,
    "categories": ["archaic", "slavic_origin"],
    "revival_potential": "medium",
    "suggested_alternative": "mulțime",
    "etymology": "sl. narodŭ",
    "example_usage": "Norodul s-a adunat în piață"
  }
}
```

---

## 8. Testing Strategy

### Unit Tests
```python
# test_tokenization.py
def test_romanian_diacritics():
    assert tokenize("țară") == ["țară"]
    assert tokenize("ȚARĂ") == ["țară"]  # lowercase
    assert tokenize("tara") != ["țară"]  # preserve distinctness

# test_frequency.py
def test_frequency_calculation():
    corpus = "pisica pisica câine"
    freq = calculate_frequency(corpus)
    assert freq["pisica"] == 2
    assert freq["câine"] == 1
```

### Integration Tests
- Dictionary API connectivity
- Corpus streaming performance
- Database transaction integrity
- Full pipeline execution

### Validation Tests
- Sample 100 "forgotten" words
- Manual verification by Romanian speakers
- Cross-reference with linguistic literature
- Compare with Google Ngrams (if available)

---

## 9. Performance Targets

### MVP Performance
- Process 1GB corpus: < 10 minutes
- Identify forgotten words: < 1 minute
- Database queries: < 100ms
- Memory usage: < 2GB RAM

### Production Performance
- Process 40GB OSCAR: < 4 hours
- Support 100 concurrent API requests
- Cache hit rate: > 90%
- Database size: < 10GB

---

## 10. Future Enhancements

### Machine Learning Integration
- **Word Embeddings**: Use Romanian BERT to find semantic alternatives
- **Usage Prediction**: Predict which current words will become forgotten
- **Context Modeling**: Understand why certain words survive/die
- **Automatic Categorization**: ML-based category assignment

### Gamification Features
- **Word Revival Challenge**: Users try to revive forgotten words
- **Etymology Explorer**: Interactive word origin visualization
- **Time Travel Mode**: Show Romanian text from different eras
- **Vocabulary Richness Score**: Rate texts by rare word usage

### Academic Tools
- **Corpus Annotation**: Mark forgotten words in uploaded texts
- **Diachronic Analysis**: Track language change patterns
- **Cross-linguistic Comparison**: Compare with other languages
- **Publication Export**: Generate LaTeX tables for papers

### Creative Writing Tools
- **Forgotten Word Suggester**: Context-aware suggestions
- **Historical Authenticity Checker**: Verify period-appropriate vocabulary
- **Archaic Text Generator**: Create text in historical Romanian style
- **Word Substitution Tool**: Replace modern words with forgotten equivalents

---

## 11. Risks and Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| DEX API changes | High | Medium | Cache dictionary locally, version API calls |
| False positives (technical terms) | Medium | High | Add domain-specific corpus validation |
| Diacritic inconsistencies | Medium | High | Robust normalization layer |
| Corpus bias (urban/educated) | Medium | Medium | Add diverse sources (rural newspapers, folk texts) |
| Storage limitations | Low | Medium | Use streaming, cloud storage for large corpora |
| Performance bottlenecks | Medium | Low | Profile code, add caching, optimize queries |

---

## 12. Success Metrics

### Technical Metrics
- Dictionaries processed: 3+
- Corpora analyzed: 5+ sources, 1B+ words
- Forgotten words identified: 5,000+
- Processing speed: 1M words/minute
- Accuracy rate: >95% (human validated)

### User Metrics (Future)
- API requests/month: 10,000+
- Unique users: 500+
- Words revived in real usage: 10+
- Academic citations: 5+

### Research Outputs
- Forgotten words database (public release)
- Romanian language decay analysis paper
- Temporal word usage dataset
- Revival potential methodology

---

## 13. Development Guidelines

### Code Style
```python
# Follow PEP 8
# Type hints for all functions
def process_word(word: str, lemmatize: bool = True) -> Dict[str, Any]:
    """
    Process a single Romanian word.
    
    Args:
        word: Romanian word to process
        lemmatize: Whether to lemmatize
        
    Returns:
        Dictionary with word metadata
    """
```

### Git Workflow
```bash
main
  ├── develop
  │   ├── feature/dex-parser
  │   ├── feature/corpus-processor
  │   └── feature/analysis-engine
  └── releases/v1.0
```

### Documentation Standards
- README.md with quick start
- API documentation (Swagger/OpenAPI)
- Inline code comments for complex logic
- CHANGELOG.md for version tracking
- Academic paper draft in /docs

---

## 14. Appendix

### A. Sample Output

```csv
word,definition,rarity_score,last_common_decade,category,revival_potential
"norod","mulțime de oameni; gloată",0.89,1960,"archaic",medium
"ospăț","masă bogată; banchet",0.76,1980,"archaic",high
"năpastă","nenorocire mare",0.82,1970,"archaic",low
"zăbavă","întârziere; amânare",0.91,1950,"archaic",medium
"soroace","soartă; destin",0.94,1940,"regional",low
```

### B. Romanian-Specific Considerations

1. **Spelling Reforms**
   - 1953: Russian influence period
   - 1993: Return to â in word-middle position
   - Must handle both systems
 

3. **Diacritic Challenges**
   - cedilla vs comma: ş→ș, ţ→ț
   - â/î rules and exceptions
   - UTF-8 encoding critical

### C. External Resources

- DEX Online: https://wiki.dexonline.ro/wiki/Informa%C8%9Bii#Desc%C4%83rcare ; https://github.com/dexonline/dexonline/wiki/Database-Schema
- Romanian WordNet: https://github.com/dumitrescustefan/RoWordNet
- Romanian NLP Tools: https://github.com/nlp-unibuc
- CoRoLa Corpus: http://corola.racai.ro


 
---

**END OF SPECIFICATION DOCUMENT**

This specification provides a comprehensive roadmap from MVP to a full-featured linguistic analysis platform. Start with Phase 1 (MVP) and iterate based on findings and user needs. The modular architecture allows for gradual feature addition without major refactoring.


-----

# Misc / Prev notes

Check if they appear in historical texts (Project Gutenberg pre-1920)
Show surces - where these rarely used where seen. 
Where available note timestamps of sources. Word timelines, first/last seen?

### Linguistic Nuances:

- Some words survive only in specific regions or registers
- Technical terms might appear rare but are actively used in niches
- Distinguish between "dead" (no one knows) vs "dormant" (recognizable but unused)

### Ranking Methodology:

- Rarity Score: Inverse document frequency across corpus
- Dictionary Ubiquity: How many dictionaries include it (more = more "officially" recognized)
- Temporal Decay: Use Google Ngrams to identify when it fell from use
- Semantic Isolation: Words whose synonyms are also rare might be truly forgotten concepts

## Romanian Corpus Sources

### Large-Scale Corpora:

1. Common Crawl with Romanian Filter
    - Filter for ro language tags
    - Use pycld2 or langdetect to verify Romanian content
    - Massive scale but needs cleaning
2. OSCAR Corpus (Romanian subset)
    - Pre-filtered Common Crawl data for Romanian
    - Cleaner than raw Common Crawl
    - Available through Hugging Face: oscar-corpus/OSCAR-2301
3. CC-100
    - Facebook's cleaned Common Crawl for 100+ languages
    - Has Romanian subset
    - Well-processed and deduplicated
4. Leipzig Corpora Collection
    - Romanian news/web crawl data
    - Multiple years available
    - Download from: corpora.uni-leipzig.de
5. RoTenTen Corpus
    - Romanian web corpus from TenTen family
    - ~9.5 billion words
    - Available through Sketch Engine


### Specialized Romanian Sources:

1. CoRoLa (Corpus Computațional de Referință pentru Limba Română)
    - Official Romanian reference corpus
    - Balanced across genres
    - Access through: corola.racai.ro
2. Romanian Wikipedia Dump
    - Smaller but high quality
    - Easy to process
    - Monthly dumps available
3. Project Gutenberg Romanian
- Historical texts (good for comparison)
- See what words were used 100+ years ago


----

You could even create a "revival score" - which forgotten words are most worthy of reintroduction based on their semantic uniqueness and the absence of good modern alternatives. Words like "petrichor" have been successfully revived; your project could identify candidates for similar resurrection!


------


```
    import requests
    from datasets import load_dataset

    # Example: Load OSCAR Romanian
    dataset = load_dataset("oscar-corpus/OSCAR-2301", "ro", split="train")

    # Build frequency dictionary
    word_freq = {}
    for text in dataset['text']:
        # Need Romanian-aware tokenization
        words = tokenize_romanian(text.lower())
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

    # Compare with dictionary
    forgotten_words = []
    for word in potential_forgotten:
        if word not in word_freq or word_freq[word] < threshold:
            forgotten_words.append(word)
```


### Romanian-Specific Considerations

Morphological Challenges:
- Need lemmatization: "frumoaselor" → "frumos"
- Consider tools like spacy-ro or nlp-cube

Diacritical Variations:
- Many texts use î/â inconsistently
- ş/ș and ţ/ț variations (old vs new diacritics)
- Need normalization layer

Historical Spelling:
- Pre-1993 used "î" everywhere (now "â" in middle)
- Old texts might use "ĕ" or "ŭ"
- Slavonic-origin words with different spellings



## Quick Start Approach
1. Start with OSCAR + Romanian Wikipedia
    - These are easiest to access and process
    - Good coverage of modern Romanian
2. Use DEX Online dump
    - Can filter by markers like "învechit" (archaic), "regional", "rar" (rare) ?
3. Initial Test
    - Remove wordfreq words from DEX
    - Check remaining words against OSCAR
    - You'll likely find thousands of forgotten words immediately

### Medium-term Improvements
- Move to PostgreSQL if data gets big
- Add web interface to browse forgotten words
- Track when words "died" using historical texts
- Categories/tags for forgotten words


https://huggingface.co/docs/datasets
https://github.com/huggingface/datasets

- Downloads datasets automatically on first use
- Caches them locally (usually in ~/.cache/huggingface/)
- Streams large datasets so you don't need to download everything
- Use streaming to avoid downloading everything


### Recommended MVP Storage Plan

Minimal Approach (5 GB total)

    storage_plan_minimal = {
        'wikipedia_ro': '1.2 GB',      # Full download - it's small
        'oscar_sample': '2 GB',        # Stream 100k docs
        'leipzig_news': '300 MB',      # Recent news
        'wordfreq_data': '50 MB',      # Word frequency lists
        'dex_dictionary': '100 MB',    # Dictionary dump
        'working_space': '1 GB',       # Processing/output
    }
    # Total: ~5 GB


Balanced Approach (15 GB total)


    storage_plan_balanced = {
        'wikipedia_ro': '1.2 GB',      # Full 
        'oscar_sample': '5 GB',        # Stream 250k docs
        'cc100_sample': '3 GB',        # Stream sample
        'news_corpora': '1 GB',        # Various news
        'wordfreq_data': '50 MB',      
        'dex_dictionary': '100 MB',    
        'cache_overhead': '2 GB',      # HF cache overhead
        'working_space': '2 GB',       
    }
    # Total: ~15 GB


**Cache Management** - The Hugging Face cache can grow large

Size Breakdown by Use Case

Just Finding Forgotten Words (2-5 GB needed)
- Wikipedia Romanian: 1.2 GB
- 50k OSCAR samples: 1 GB
- DEX dictionary: 100 MB
- Wordfreq lists: 50 MB
- Perfect for laptop/local development

Deeper Analysis (10-15 GB needed)
- Add CC-100 samples
- More OSCAR documents
- News corpora
- Still manageable on most computers
