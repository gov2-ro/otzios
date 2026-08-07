#!/usr/bin/env python3
"""
Process Romanian text corpora and count occurrences of forgotten words.

This script:
1. Loads forgotten words from curated list
2. Processes Wikipedia Romanian + OSCAR Romanian (streaming)
3. Counts word occurrences in modern text
4. Stores results in SQLite database

Usage:
    python process_corpus.py --test       # Test mode: 1000 articles only
    python process_corpus.py --sample     # Sample: 50k articles
    python process_corpus.py --full       # Full processing
"""

import sqlite3
import re
import unicodedata
import argparse
import time
from collections import defaultdict
from datetime import datetime
import csv

def normalize_romanian_text(text):
    """Normalize Romanian text for tokenization."""
    # Convert to lowercase
    text = text.lower()

    # Fix legacy diacritics (cedilla → comma)
    text = text.replace('ş', 'ș').replace('ţ', 'ț')

    # Normalize Unicode (NFC form - canonical composition)
    text = unicodedata.normalize('NFC', text)

    return text

def tokenize_romanian(text):
    """
    Simple Romanian tokenizer.

    Returns list of tokens (words) in lowercase with normalized diacritics.
    """
    text = normalize_romanian_text(text)

    # Split on whitespace and punctuation, keep word characters and hyphens
    # Romanian word chars: a-z + ăâîșț + hyphen + apostrophe
    tokens = re.findall(r'\b[\wăâîșț\-\']+\b', text)

    # Filter out very short tokens and pure numbers
    tokens = [t for t in tokens if len(t) > 2 and not t.isdigit()]

    return tokens

def load_forgotten_words(csv_path):
    """Load forgotten words from curated CSV."""
    words = set()

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize word for matching
            word = normalize_romanian_text(row['word'])
            words.add(word)

    return words

def init_database(db_path):
    """Initialize SQLite database for corpus frequencies."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create corpus_word_frequency table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS corpus_word_frequency (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            corpus_name TEXT NOT NULL,
            occurrence_count INTEGER DEFAULT 0,
            document_count INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(word, corpus_name)
        )
    ''')

    # Create index for fast lookup
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_corpus_word
        ON corpus_word_frequency(word, corpus_name)
    ''')

    # Create processing stats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processing_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            corpus_name TEXT NOT NULL,
            documents_processed INTEGER DEFAULT 0,
            tokens_processed INTEGER DEFAULT 0,
            unique_words_found INTEGER DEFAULT 0,
            processing_time_seconds REAL,
            completed_at TIMESTAMP,
            status TEXT DEFAULT 'in_progress'
        )
    ''')

    conn.commit()
    return conn

def update_word_counts(cursor, word_counts, doc_counts, corpus_name):
    """Update database with word counts."""

    for word, count in word_counts.items():
        doc_count = doc_counts[word]

        cursor.execute('''
            INSERT INTO corpus_word_frequency (word, corpus_name, occurrence_count, document_count, last_updated)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(word, corpus_name)
            DO UPDATE SET
                occurrence_count = occurrence_count + ?,
                document_count = document_count + ?,
                last_updated = ?
        ''', (word, corpus_name, count, doc_count, datetime.now(),
              count, doc_count, datetime.now()))

def process_wikipedia(forgotten_words, conn, limit=None, verbose=True):
    """Process Wikipedia Romanian dataset."""

    print()
    print("=" * 70)
    print("Processing Wikipedia Romanian")
    print("=" * 70)

    try:
        from datasets import load_dataset
    except ImportError:
        print("❌ Error: 'datasets' package not installed")
        print("   Run: pip install datasets")
        return

    print("Loading Wikipedia dataset...")
    # Use the newer Wikimedia/wikipedia dataset
    try:
        dataset = load_dataset("wikimedia/wikipedia", "20231101.ro", split="train")
    except Exception as e:
        print(f"⚠️  Note: Using alternative Wikipedia loading method")
        # Fallback: try legacy format or direct download
        dataset = load_dataset("graelo/wikipedia", "20230901.ro", split="train")

    if limit:
        print(f"Processing first {limit:,} articles (test mode)")
    else:
        print(f"Processing all {len(dataset):,} articles")

    print()

    cursor = conn.cursor()
    word_counts = defaultdict(int)
    doc_counts = defaultdict(int)

    total_tokens = 0
    total_docs = len(dataset) if not limit else limit
    start_time = time.time()

    for idx, article in enumerate(dataset):
        if limit and idx >= limit:
            break

        # Progress indicator
        if (idx + 1) % 1000 == 0 or (idx + 1) == total_docs:
            elapsed = time.time() - start_time
            rate = (idx + 1) / elapsed if elapsed > 0 else 0
            print(f"  Progress: {idx + 1:,} / {total_docs:,} articles "
                  f"({rate:.1f} articles/sec) - "
                  f"Found {len(word_counts)} forgotten words")

        # Tokenize article text
        text = article.get('text', '')
        tokens = tokenize_romanian(text)
        total_tokens += len(tokens)

        # Track which forgotten words appear in this document
        doc_words = set()

        for token in tokens:
            if token in forgotten_words:
                word_counts[token] += 1
                doc_words.add(token)

        # Update document counts
        for word in doc_words:
            doc_counts[word] += 1

        # Commit every 1000 articles
        if (idx + 1) % 1000 == 0:
            update_word_counts(cursor, word_counts, doc_counts, 'wikipedia_ro')
            conn.commit()
            # Reset counters after commit
            word_counts.clear()
            doc_counts.clear()

    # Final commit
    if word_counts:
        update_word_counts(cursor, word_counts, doc_counts, 'wikipedia_ro')
        conn.commit()

    elapsed = time.time() - start_time

    # Save processing stats
    cursor.execute('''
        INSERT INTO processing_stats
        (corpus_name, documents_processed, tokens_processed, unique_words_found,
         processing_time_seconds, completed_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('wikipedia_ro', idx + 1, total_tokens, len(word_counts),
          elapsed, datetime.now(), 'completed'))

    conn.commit()

    print()
    print("✅ Wikipedia processing complete!")
    print(f"   Articles processed: {idx + 1:,}")
    print(f"   Total tokens: {total_tokens:,}")
    print(f"   Processing time: {elapsed:.1f} seconds")
    print(f"   Rate: {(idx + 1) / elapsed:.1f} articles/sec")
    print()

def process_oscar_sample(forgotten_words, conn, sample_size=100000, verbose=True):
    """Process OSCAR Romanian dataset (streaming sample)."""

    print()
    print("=" * 70)
    print("Processing OSCAR Romanian (Streaming Sample)")
    print("=" * 70)

    try:
        from datasets import load_dataset
    except ImportError:
        print("❌ Error: 'datasets' package not installed")
        return

    print(f"Streaming {sample_size:,} documents from OSCAR...")
    print("Note: This may take 30-60 minutes for full sample")
    print()

    # Stream OSCAR dataset (don't download everything)
    try:
        dataset = load_dataset(
            "oscar-corpus/OSCAR-2301",
            "ro",
            split="train",
            streaming=True  # Streaming mode - crucial for large datasets
        )
    except Exception as e:
        print()
        print(f"⚠️  OSCAR dataset unavailable: {str(e)[:100]}")
        print("   OSCAR is a gated dataset - requires HuggingFace authentication")
        print("   Skipping OSCAR processing")
        print()
        return

    cursor = conn.cursor()
    word_counts = defaultdict(int)
    doc_counts = defaultdict(int)

    total_tokens = 0
    docs_processed = 0
    start_time = time.time()

    for idx, document in enumerate(dataset):
        if idx >= sample_size:
            break

        # Progress indicator
        if (idx + 1) % 5000 == 0 or (idx + 1) == sample_size:
            elapsed = time.time() - start_time
            rate = (idx + 1) / elapsed if elapsed > 0 else 0
            print(f"  Progress: {idx + 1:,} / {sample_size:,} documents "
                  f"({rate:.1f} docs/sec) - "
                  f"Found {len(word_counts)} forgotten words")

        # Get text from document
        text = document.get('text', '')
        tokens = tokenize_romanian(text)
        total_tokens += len(tokens)

        # Track which forgotten words appear in this document
        doc_words = set()

        for token in tokens:
            if token in forgotten_words:
                word_counts[token] += 1
                doc_words.add(token)

        # Update document counts
        for word in doc_words:
            doc_counts[word] += 1

        docs_processed += 1

        # Commit every 5000 documents
        if (idx + 1) % 5000 == 0:
            update_word_counts(cursor, word_counts, doc_counts, 'oscar_ro')
            conn.commit()
            # Reset counters
            word_counts.clear()
            doc_counts.clear()

    # Final commit
    if word_counts:
        update_word_counts(cursor, word_counts, doc_counts, 'oscar_ro')
        conn.commit()

    elapsed = time.time() - start_time

    # Save processing stats
    cursor.execute('''
        INSERT INTO processing_stats
        (corpus_name, documents_processed, tokens_processed, unique_words_found,
         processing_time_seconds, completed_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('oscar_ro', docs_processed, total_tokens, len(word_counts),
          elapsed, datetime.now(), 'completed'))

    conn.commit()

    print()
    print("✅ OSCAR processing complete!")
    print(f"   Documents processed: {docs_processed:,}")
    print(f"   Total tokens: {total_tokens:,}")
    print(f"   Processing time: {elapsed:.1f} seconds")
    print(f"   Rate: {docs_processed / elapsed:.1f} docs/sec")
    print()

def show_results(conn):
    """Display top results from corpus processing."""

    cursor = conn.cursor()

    print()
    print("=" * 70)
    print("CORPUS PROCESSING RESULTS")
    print("=" * 70)

    # Overall stats
    cursor.execute('''
        SELECT corpus_name, SUM(occurrence_count) as total_occurrences,
               COUNT(DISTINCT word) as unique_words
        FROM corpus_word_frequency
        GROUP BY corpus_name
    ''')

    print()
    print("Corpus Statistics:")
    print("-" * 70)
    for corpus, occurrences, unique in cursor.fetchall():
        print(f"  {corpus:.<30} {occurrences:>10,} occurrences, {unique:>6} unique words")

    # Top forgotten words found
    print()
    print("Top 20 Forgotten Words Found in Corpora:")
    print("-" * 70)

    cursor.execute('''
        SELECT word, SUM(occurrence_count) as total_count,
               SUM(document_count) as doc_count
        FROM corpus_word_frequency
        GROUP BY word
        ORDER BY total_count DESC
        LIMIT 20
    ''')

    print(f"{'Word':<30} {'Occurrences':>12} {'Documents':>12}")
    print("-" * 70)
    for word, count, doc_count in cursor.fetchall():
        print(f"{word:<30} {count:>12,} {doc_count:>12,}")

    # Words with zero occurrences (truly forgotten!)
    cursor.execute('''
        SELECT COUNT(DISTINCT word) FROM corpus_word_frequency
    ''')
    words_found = cursor.fetchone()[0]

    print()
    print(f"Summary:")
    print(f"  Forgotten words with corpus matches: {words_found}")
    print(f"  Remaining words (zero occurrences): (calculated in validation step)")
    print()

def main():
    parser = argparse.ArgumentParser(description='Process Romanian corpora for forgotten words validation')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: process 1000 Wikipedia articles only')
    parser.add_argument('--sample', action='store_true',
                        help='Sample mode: process 50k Wikipedia + 50k OSCAR')
    parser.add_argument('--full', action='store_true',
                        help='Full mode: process all Wikipedia + 250k OSCAR')
    parser.add_argument('--wikipedia-only', action='store_true',
                        help='Process only Wikipedia (skip OSCAR)')
    parser.add_argument('--oscar-only', action='store_true',
                        help='Process only OSCAR (skip Wikipedia)')

    args = parser.parse_args()

    # Default to test mode if nothing specified
    if not any([args.test, args.sample, args.full]):
        args.test = True
        print("No mode specified, defaulting to --test mode")

    print("=" * 70)
    print("Romanian Corpus Processor")
    print("=" * 70)
    print()

    # Paths
    FORGOTTEN_WORDS_CSV = "data/processed/forgotten_words_curated.csv"
    DB_PATH = "data/processed/corpus_frequencies.db"

    # Load forgotten words
    print("Loading forgotten words from curated list...")
    forgotten_words = load_forgotten_words(FORGOTTEN_WORDS_CSV)
    print(f"✅ Loaded {len(forgotten_words):,} forgotten words")

    # Initialize database
    print("Initializing database...")
    conn = init_database(DB_PATH)
    print(f"✅ Database ready: {DB_PATH}")

    # Determine processing parameters
    if args.test:
        wiki_limit = 1000
        oscar_limit = 1000
        mode_name = "TEST"
    elif args.sample:
        wiki_limit = 50000
        oscar_limit = 50000
        mode_name = "SAMPLE"
    else:  # full
        wiki_limit = None  # All articles
        oscar_limit = 250000
        mode_name = "FULL"

    print(f"\nMode: {mode_name}")
    print(f"  Wikipedia: {'All articles' if wiki_limit is None else f'{wiki_limit:,} articles'}")
    print(f"  OSCAR: {oscar_limit:,} documents")

    start_time = time.time()

    # Process Wikipedia
    if not args.oscar_only:
        process_wikipedia(forgotten_words, conn, limit=wiki_limit)

    # Process OSCAR
    if not args.wikipedia_only:
        process_oscar_sample(forgotten_words, conn, sample_size=oscar_limit)

    # Show results
    show_results(conn)

    total_time = time.time() - start_time

    print("=" * 70)
    print("✅ CORPUS PROCESSING COMPLETE")
    print("=" * 70)
    print(f"Total processing time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    print()
    print("Next steps:")
    print("  1. Run: python validate_forgotten_words.py")
    print("  2. Review: data/processed/forgotten_words_validated.csv")
    print()

    conn.close()

if __name__ == "__main__":
    main()
