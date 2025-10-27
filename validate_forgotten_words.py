#!/usr/bin/env python3
"""
Validate forgotten words by cross-referencing DEX frequency with corpus frequency.

This script:
1. Loads DEX frequency data from lexemes.db
2. Loads corpus frequency data from corpus_frequencies.db
3. Cross-references to validate which words are truly forgotten
4. Calculates confidence scores
5. Generates validated list and report

Output:
- forgotten_words_validated.csv (final validated list)
- validation_report.txt (analysis and statistics)
- false_positives.csv (words to remove from forgotten list)
"""

import sqlite3
import csv
from collections import defaultdict
from datetime import datetime

DB_LEXEMES = "data/processed/lexemes.db"
DB_CORPUS = "data/processed/corpus_frequencies.db"
OUTPUT_VALIDATED = "data/processed/forgotten_words_validated.csv"
OUTPUT_REPORT = "data/processed/validation_report.txt"
OUTPUT_FALSE_POSITIVES = "data/processed/false_positives.csv"

def load_corpus_stats(corpus_conn):
    """Load overall corpus statistics."""
    cursor = corpus_conn.cursor()

    # Get total tokens processed per corpus
    cursor.execute('''
        SELECT corpus_name, tokens_processed
        FROM processing_stats
        WHERE status = 'completed'
    ''')

    corpus_stats = {}
    for corpus_name, tokens in cursor.fetchall():
        corpus_stats[corpus_name] = tokens

    return corpus_stats

def validate_words(lexeme_conn, corpus_conn, corpus_stats):
    """
    Validate forgotten words by comparing DEX vs corpus frequency.

    Returns:
        validated_words: list of (word, data_dict) tuples
    """

    print()
    print("=" * 70)
    print("VALIDATING FORGOTTEN WORDS")
    print("=" * 70)
    print()

    lexeme_cursor = lexeme_conn.cursor()
    corpus_cursor = corpus_conn.cursor()

    # Load forgotten words from curated list
    lexeme_cursor.execute('''
        SELECT form, frequency, description
        FROM Lexeme
        WHERE frequency > 0.01 AND frequency < 0.60
          AND LENGTH(form) > 3
        ORDER BY frequency ASC
    ''')

    candidates = lexeme_cursor.fetchall()
    print(f"Analyzing {len(candidates):,} forgotten word candidates...")
    print()

    validated_words = []
    category_counts = defaultdict(int)

    for idx, (word, dex_freq, description) in enumerate(candidates):
        if (idx + 1) % 500 == 0:
            print(f"  Progress: {idx + 1:,} / {len(candidates):,} words processed...")

        # Normalize word for corpus lookup
        word_normalized = word.lower()

        # Get corpus frequencies
        corpus_cursor.execute('''
            SELECT corpus_name, occurrence_count, document_count
            FROM corpus_word_frequency
            WHERE word = ?
        ''', (word_normalized,))

        corpus_data = corpus_cursor.fetchall()

        # Calculate total occurrences and documents
        total_occurrences = 0
        total_documents = 0
        corpus_details = {}

        for corpus_name, occ_count, doc_count in corpus_data:
            total_occurrences += occ_count
            total_documents += doc_count
            corpus_details[corpus_name] = {
                'occurrences': occ_count,
                'documents': doc_count
            }

        # Calculate frequency per million words
        total_corpus_tokens = sum(corpus_stats.values())
        freq_per_million = (total_occurrences / total_corpus_tokens * 1_000_000) if total_corpus_tokens > 0 else 0

        # Validation logic
        validation_status = determine_validation_status(
            dex_freq, total_occurrences, freq_per_million, total_documents
        )

        category_counts[validation_status] += 1

        # Calculate confidence score (0-1)
        confidence = calculate_confidence_score(
            dex_freq, total_occurrences, freq_per_million, total_documents
        )

        # Store validated word data
        word_data = {
            'word': word,
            'dex_frequency': dex_freq,
            'description': description,
            'total_occurrences': total_occurrences,
            'total_documents': total_documents,
            'frequency_per_million': freq_per_million,
            'validation_status': validation_status,
            'confidence_score': confidence,
            'corpus_details': corpus_details
        }

        validated_words.append(word_data)

    print()
    print("✅ Validation complete!")
    print()
    print("Validation Categories:")
    print("-" * 70)
    for category in ['confirmed_forgotten', 'likely_forgotten', 'uncommon', 'questionable', 'false_positive']:
        count = category_counts.get(category, 0)
        pct = (count / len(candidates) * 100) if len(candidates) > 0 else 0
        print(f"  {category:.<30} {count:>6,} ({pct:>5.1f}%)")

    return validated_words

def determine_validation_status(dex_freq, total_occ, freq_per_million, doc_count):
    """
    Determine validation status based on corpus frequency.

    Categories:
    - confirmed_forgotten: Very rare in modern text (< 0.1 per million)
    - likely_forgotten: Rare in modern text (< 1.0 per million)
    - uncommon: Somewhat rare (< 10.0 per million)
    - questionable: Not that rare (< 50.0 per million)
    - false_positive: Actually common (>= 50.0 per million)
    """

    if freq_per_million < 0.1:
        return 'confirmed_forgotten'
    elif freq_per_million < 1.0:
        return 'likely_forgotten'
    elif freq_per_million < 10.0:
        return 'uncommon'
    elif freq_per_million < 50.0:
        return 'questionable'
    else:
        return 'false_positive'

def calculate_confidence_score(dex_freq, total_occ, freq_per_million, doc_count):
    """
    Calculate confidence score (0-1) for forgotten word classification.

    Higher score = more confident it's truly forgotten

    Factors:
    - Low DEX frequency (good indicator)
    - Low corpus frequency (confirms it)
    - Low document count (not just concentrated in few docs)
    """

    # Start with DEX frequency (inverted - lower is better)
    # DEX freq 0.01 → 0.99, DEX freq 0.60 → 0.40
    dex_score = 1.0 - dex_freq

    # Corpus frequency score (lower is better)
    if freq_per_million < 0.1:
        corpus_score = 1.0
    elif freq_per_million < 1.0:
        corpus_score = 0.8
    elif freq_per_million < 10.0:
        corpus_score = 0.5
    elif freq_per_million < 50.0:
        corpus_score = 0.2
    else:
        corpus_score = 0.0

    # Document spread score (appearing in few docs is better)
    if doc_count == 0:
        doc_score = 1.0
    elif doc_count < 5:
        doc_score = 0.9
    elif doc_count < 20:
        doc_score = 0.7
    elif doc_count < 100:
        doc_score = 0.4
    else:
        doc_score = 0.1

    # Weighted average (corpus frequency most important)
    confidence = (dex_score * 0.3 + corpus_score * 0.5 + doc_score * 0.2)

    return round(confidence, 3)

def export_validated_words(validated_words, corpus_stats):
    """Export validated words to CSV."""

    print()
    print("=" * 70)
    print("EXPORTING RESULTS")
    print("=" * 70)
    print()

    # Separate by validation status
    confirmed = [w for w in validated_words if w['validation_status'] == 'confirmed_forgotten']
    likely = [w for w in validated_words if w['validation_status'] == 'likely_forgotten']
    uncommon = [w for w in validated_words if w['validation_status'] == 'uncommon']
    questionable = [w for w in validated_words if w['validation_status'] == 'questionable']
    false_positives = [w for w in validated_words if w['validation_status'] == 'false_positive']

    # Export validated list (confirmed + likely + uncommon)
    validated_list = confirmed + likely + uncommon

    print(f"Exporting {len(validated_list):,} validated forgotten words...")

    with open(OUTPUT_VALIDATED, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)

        writer.writerow([
            'word',
            'dex_frequency',
            'description',
            'corpus_occurrences',
            'corpus_documents',
            'frequency_per_million',
            'validation_status',
            'confidence_score',
            'wikipedia_count',
            'oscar_count'
        ])

        for word_data in sorted(validated_list, key=lambda x: x['confidence_score'], reverse=True):
            wiki_count = word_data['corpus_details'].get('wikipedia_ro', {}).get('occurrences', 0)
            oscar_count = word_data['corpus_details'].get('oscar_ro', {}).get('occurrences', 0)

            writer.writerow([
                word_data['word'],
                f"{word_data['dex_frequency']:.4f}",
                word_data['description'],
                word_data['total_occurrences'],
                word_data['total_documents'],
                f"{word_data['frequency_per_million']:.6f}",
                word_data['validation_status'],
                word_data['confidence_score'],
                wiki_count,
                oscar_count
            ])

    print(f"✅ Validated list saved to: {OUTPUT_VALIDATED}")

    # Export false positives
    if false_positives:
        print(f"Exporting {len(false_positives):,} false positives...")

        with open(OUTPUT_FALSE_POSITIVES, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)

            writer.writerow([
                'word',
                'dex_frequency',
                'corpus_occurrences',
                'frequency_per_million',
                'reason'
            ])

            for word_data in sorted(false_positives, key=lambda x: x['frequency_per_million'], reverse=True):
                writer.writerow([
                    word_data['word'],
                    f"{word_data['dex_frequency']:.4f}",
                    word_data['total_occurrences'],
                    f"{word_data['frequency_per_million']:.2f}",
                    'Too common in modern corpora'
                ])

        print(f"✅ False positives saved to: {OUTPUT_FALSE_POSITIVES}")

    # Generate validation report
    print(f"Generating validation report...")

    with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("FORGOTTEN WORDS VALIDATION REPORT\n")
        f.write("=" * 70 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("\n")

        f.write("CORPUS STATISTICS\n")
        f.write("-" * 70 + "\n")
        for corpus_name, tokens in corpus_stats.items():
            f.write(f"  {corpus_name}: {tokens:,} tokens processed\n")
        f.write(f"  Total corpus size: {sum(corpus_stats.values()):,} tokens\n")
        f.write("\n")

        f.write("VALIDATION RESULTS\n")
        f.write("-" * 70 + "\n")
        f.write(f"  Total candidates analyzed: {len(validated_words):,}\n")
        f.write(f"\n")
        f.write(f"  Confirmed forgotten:       {len(confirmed):>6,} (< 0.1 per million)\n")
        f.write(f"  Likely forgotten:          {len(likely):>6,} (< 1.0 per million)\n")
        f.write(f"  Uncommon:                  {len(uncommon):>6,} (< 10.0 per million)\n")
        f.write(f"  Questionable:              {len(questionable):>6,} (< 50.0 per million)\n")
        f.write(f"  False positives:           {len(false_positives):>6,} (>= 50.0 per million)\n")
        f.write(f"\n")
        f.write(f"  ✅ VALIDATED FORGOTTEN WORDS: {len(validated_list):,}\n")
        f.write("\n")

        # Top confirmed forgotten words
        f.write("TOP 30 CONFIRMED FORGOTTEN WORDS (Zero corpus occurrences)\n")
        f.write("-" * 70 + "\n")
        zero_occ = [w for w in confirmed if w['total_occurrences'] == 0][:30]
        for word_data in zero_occ:
            f.write(f"  {word_data['word']:.<30} {word_data['description']:.<20} "
                   f"DEX freq: {word_data['dex_frequency']:.3f}\n")
        f.write("\n")

        # Top false positives (words that looked forgotten but aren't)
        f.write("TOP 20 FALSE POSITIVES (Actually common in modern usage)\n")
        f.write("-" * 70 + "\n")
        top_false = sorted(false_positives, key=lambda x: x['frequency_per_million'], reverse=True)[:20]
        for word_data in top_false:
            f.write(f"  {word_data['word']:.<30} "
                   f"Corpus freq: {word_data['frequency_per_million']:>8.2f} per million, "
                   f"Occurrences: {word_data['total_occurrences']:>6,}\n")
        f.write("\n")

        f.write("=" * 70 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 70 + "\n")

    print(f"✅ Validation report saved to: {OUTPUT_REPORT}")
    print()

def main():
    print("=" * 70)
    print("Forgotten Words Validator")
    print("=" * 70)
    print()

    # Connect to databases
    print("Connecting to databases...")
    lexeme_conn = sqlite3.connect(DB_LEXEMES)
    corpus_conn = sqlite3.connect(DB_CORPUS)
    print("✅ Connected")

    # Load corpus statistics
    print("Loading corpus statistics...")
    corpus_stats = load_corpus_stats(corpus_conn)
    print(f"✅ Corpus stats loaded")
    print(f"   Total tokens: {sum(corpus_stats.values()):,}")

    # Validate words
    validated_words = validate_words(lexeme_conn, corpus_conn, corpus_stats)

    # Export results
    export_validated_words(validated_words, corpus_stats)

    # Close connections
    lexeme_conn.close()
    corpus_conn.close()

    print("=" * 70)
    print("✅ VALIDATION COMPLETE")
    print("=" * 70)
    print()
    print("Output files:")
    print(f"  1. {OUTPUT_VALIDATED}")
    print(f"  2. {OUTPUT_REPORT}")
    print(f"  3. {OUTPUT_FALSE_POSITIVES}")
    print()
    print("Next steps:")
    print("  - Review validation report")
    print("  - Analyze false positives")
    print("  - Use validated list for further research")
    print()

if __name__ == "__main__":
    main()
