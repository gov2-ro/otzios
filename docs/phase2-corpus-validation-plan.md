# Phase 2: Corpus Validation Plan

**Goal**: Validate our 1,884 forgotten word candidates against modern Romanian text corpora to confirm they are truly rare/forgotten in contemporary usage.

**Status**: In Progress 🚧

---

## Approach

### Strategy Overview

We'll use a **hybrid approach** combining:
1. **Wikipedia RO** - High-quality, curated text (~1.2 GB)
2. **OSCAR Romanian subset** - Large web-crawled corpus (streaming from HuggingFace)
3. **Frequency counting** - Count occurrences of our forgotten words in modern text
4. **Validation scoring** - Compare DEX frequency vs real corpus frequency

### Why This Approach?

- **Wikipedia**: Represents formal, educated Romanian (encyclopedic)
- **OSCAR**: Represents diverse web content (blogs, news, forums)
- **Streaming**: Avoids downloading 39 GB - we sample what we need
- **Focused**: Only count our 1,884 candidate words (fast lookup)

---

## Storage Requirements

### Current Usage
- Project data: 1.9 GB
- Available space: 90 GB
- **We're good to go!**

### Expected Usage (Phase 2)
```
Wikipedia RO dump:           ~1.5 GB (compressed)
Wikipedia extracted text:    ~2.0 GB
OSCAR streaming cache:       ~3-5 GB (HuggingFace cache)
Processing workspace:        ~1 GB
Results database:            ~100 MB
Total estimate:              ~8-10 GB
```

---

## Implementation Steps

### Step 1: Download Wikipedia Romanian
```bash
# Download latest Romanian Wikipedia dump
# URL: https://dumps.wikimedia.org/rowiki/latest/
# File: rowiki-latest-pages-articles.xml.bz2 (~1.2 GB)
```

**Alternative**: Use HuggingFace `wikipedia` dataset (easier):
```python
from datasets import load_dataset
wiki_ro = load_dataset("wikipedia", "20220301.ro", split="train")
```

### Step 2: Set Up OSCAR Streaming
```python
from datasets import load_dataset

# Stream OSCAR Romanian (no full download needed)
oscar_ro = load_dataset(
    "oscar-corpus/OSCAR-2301",
    "ro",
    split="train",
    streaming=True  # Key: don't download everything!
)
```

### Step 3: Process Corpora
1. **Tokenize** Romanian text (handle diacritics)
2. **Create lookup set** from our 1,884 forgotten words
3. **Count occurrences** in Wikipedia + OSCAR sample
4. **Store results** in SQLite database

### Step 4: Validate Forgotten Words
Compare:
- **DEX frequency** (0.01-0.60) - dictionary usage
- **Corpus frequency** (counts in modern text) - real-world usage

**Validation categories**:
- ✅ **Truly forgotten**: Low DEX freq + Low/Zero corpus freq
- ⚠️ **Questionable**: Low DEX freq + High corpus freq (false positive)
- 🔄 **Regional/Technical**: Low overall but spikes in specific domains

---

## Technical Design

### Database Schema Extension

```sql
-- New table for corpus frequencies
CREATE TABLE corpus_word_frequency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    corpus_name TEXT NOT NULL,  -- 'wikipedia_ro', 'oscar_ro'
    occurrence_count INTEGER DEFAULT 0,
    document_count INTEGER DEFAULT 0,  -- How many docs contain the word
    frequency_per_million REAL,  -- Normalized frequency
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(word, corpus_name)
);

-- Index for fast lookup
CREATE INDEX idx_corpus_word ON corpus_word_frequency(word, corpus_name);

-- Extended validation results
CREATE TABLE word_validation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL UNIQUE,
    dex_frequency REAL,
    wikipedia_count INTEGER DEFAULT 0,
    oscar_count INTEGER DEFAULT 0,
    total_corpus_count INTEGER DEFAULT 0,
    validation_status TEXT,  -- 'confirmed', 'questionable', 'false_positive'
    confidence_score REAL,  -- 0-1, how confident we are it's forgotten
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Processing Pipeline

```
1. Load forgotten_words_curated.csv (1,884 words)
   ↓
2. Create fast lookup set (for O(1) checking)
   ↓
3. Stream Wikipedia RO:
   - Tokenize each article
   - Check if tokens in our set
   - Increment counters
   ↓
4. Stream OSCAR RO (sample 100k-500k documents):
   - Tokenize text
   - Check if tokens in our set
   - Increment counters
   ↓
5. Calculate validation metrics:
   - Frequency per million words
   - Document frequency
   - DEX vs Corpus comparison
   ↓
6. Generate validation report:
   - Confirmed forgotten words
   - False positives to remove
   - Updated curated list
```

---

## Script Design

### `download_wikipedia_ro.py`
**Purpose**: Download Wikipedia Romanian dataset
**Approach**: Use HuggingFace `datasets` library
**Output**: Cached dataset in `~/.cache/huggingface/`

### `process_corpus.py` ⭐ **Main Script**
**Purpose**: Count word occurrences in corpora
**Input**:
- `data/processed/forgotten_words_curated.csv`
- Wikipedia dataset (HuggingFace)
- OSCAR dataset (streaming)

**Output**:
- `data/processed/corpus_frequencies.db` (SQLite)
- Progress logs

**Features**:
- Streaming for large datasets
- Romanian tokenization (handles diacritics)
- Progress tracking
- Resume capability (checkpoint system)
- Fast lookup with sets

### `validate_forgotten_words.py`
**Purpose**: Cross-reference DEX frequency with corpus frequency
**Input**:
- `data/processed/lexemes.db` (DEX data)
- `data/processed/corpus_frequencies.db` (corpus data)

**Output**:
- `data/processed/forgotten_words_validated.csv` (final list)
- `data/processed/validation_report.txt` (analysis)
- `data/processed/false_positives.csv` (words to remove)

**Validation Logic**:
```python
def validate_word(word_data):
    dex_freq = word_data['dex_frequency']
    corpus_count = word_data['total_corpus_count']
    corpus_freq_per_million = word_data['frequency_per_million']

    # Thresholds
    if corpus_freq_per_million < 0.1:  # Less than 0.1 per million
        return 'confirmed_forgotten'
    elif corpus_freq_per_million < 1.0:
        return 'likely_forgotten'
    elif corpus_freq_per_million < 10.0:
        return 'uncommon'
    else:
        return 'false_positive'  # Actually common in modern usage!
```

---

## Romanian Tokenization

### Challenges
1. **Diacritics**: ă, â, î, ș, ț (must preserve)
2. **Legacy diacritics**: ş→ș, ţ→ț (convert)
3. **Case sensitivity**: "Țară" vs "țară"
4. **Punctuation**: "cuvânt," → "cuvânt"

### Implementation
```python
import re
import unicodedata

def normalize_romanian_text(text):
    """Normalize Romanian text for tokenization."""
    # Convert to lowercase
    text = text.lower()

    # Fix legacy diacritics
    text = text.replace('ş', 'ș').replace('ţ', 'ț')

    # Normalize Unicode (NFC form)
    text = unicodedata.normalize('NFC', text)

    return text

def tokenize_romanian(text):
    """Simple Romanian tokenizer."""
    text = normalize_romanian_text(text)

    # Split on whitespace and punctuation
    tokens = re.findall(r'\b[\w\-\']+\b', text)

    return tokens
```

---

## Performance Optimization

### For Wikipedia (~500k articles)
- **Streaming**: Process article by article
- **Batch commits**: Every 1000 articles
- **Estimated time**: 10-20 minutes
- **Memory usage**: <500 MB

### For OSCAR (sampling 250k documents)
- **Streaming**: Don't download full 39 GB
- **Sample size**: 250k documents (~3-5 GB text)
- **Progress tracking**: Every 10k documents
- **Estimated time**: 30-60 minutes
- **Memory usage**: <1 GB

### Fast Lookup
```python
# Create set from 1,884 words (O(1) lookup)
forgotten_words_set = set(df['word'].str.lower())

# Check if word is in our set
if token in forgotten_words_set:
    word_counts[token] += 1
```

---

## Testing Strategy

### Phase 1: Sanity Test (5 minutes)
```python
# Test with 10 known words:
test_words = [
    'de',      # Should be VERY common (false positive test)
    'bucle',   # Should be rare (true forgotten word)
    'zzzzzz',  # Should be zero (non-existent word)
]
# Process 1000 Wikipedia articles only
# Verify: 'de' appears thousands of times, 'bucle' appears 0-5 times
```

### Phase 2: Sample Run (30 minutes)
- Process 50k Wikipedia articles
- Process 50k OSCAR documents
- Verify 100 random words from our list

### Phase 3: Full Run (2-3 hours)
- Process all Wikipedia Romanian
- Process 250k OSCAR documents
- Validate all 1,884 words

---

## Expected Outcomes

### Validation Results (Estimates)

From 1,884 candidates:
- **1,400-1,600** ✅ Confirmed forgotten (truly rare in modern text)
- **200-300** ⚠️ Questionable (somewhat rare, needs review)
- **100-200** ❌ False positives (actually common in corpora)

### False Positive Examples

Words that might appear in our "forgotten" list but are actually common:
- **Technical terms**: Used frequently in specific domains
- **Internet slang**: Rare in dictionaries, common online
- **Regional words**: Common in certain areas
- **Recent neologisms**: Not yet in DEX frequency data

---

## Output Files

### Generated by Phase 2

1. **`corpus_frequencies.db`** (~100 MB)
   - Word occurrence counts from each corpus
   - Document frequencies
   - Normalized frequency per million

2. **`forgotten_words_validated.csv`** ⭐ **FINAL OUTPUT**
   - Validated forgotten words (~1,400-1,600)
   - With corpus frequency data
   - Confidence scores

3. **`validation_report.txt`**
   - Summary statistics
   - Validation categories breakdown
   - Sample words from each category

4. **`false_positives.csv`**
   - Words to remove from forgotten list
   - Actual corpus frequencies
   - Reasons for removal

---

## Next Steps After Phase 2

### Phase 3: Enhanced Metadata
- Extract definitions from DEX
- Identify archaic markers (înv., arh., reg.)
- Add etymology information
- Map to word families

### Phase 4: Visualization
- Word frequency distribution charts
- Temporal analysis (if dated corpora available)
- Interactive web interface
- Word cloud of forgotten words

---

## Risk Mitigation

### Potential Issues

1. **Corpus Bias**: Web text may not represent spoken language
   - **Mitigation**: Use multiple corpora (Wikipedia + OSCAR)

2. **Technical Terms**: May appear rare but are actively used
   - **Mitigation**: Manual review of high-frequency outliers

3. **Spelling Variations**: Old vs new diacritics
   - **Mitigation**: Normalize all text to new diacritics

4. **Lemmatization**: "frumoaselor" won't match "frumos"
   - **Phase 2**: Accept this limitation
   - **Phase 3**: Add Romanian lemmatization (spaCy-ro)

5. **Download Issues**: Large files may fail
   - **Mitigation**: Use streaming, add resume capability

---

## Success Metrics

### Phase 2 Complete When:
- ✅ Wikipedia RO fully processed (500k articles)
- ✅ OSCAR RO sampled (250k documents minimum)
- ✅ All 1,884 words validated
- ✅ Confidence scores calculated
- ✅ Final validated list exported
- ✅ Validation report generated
- ✅ False positives identified and removed

### Quality Metrics
- Processing speed: >100 articles/minute
- Accuracy: Manual validation of 100 random words
- Coverage: >95% of corpora processed without errors

---

**Ready to implement!** 🚀

Next: Create `download_wikipedia_ro.py` and `process_corpus.py`
