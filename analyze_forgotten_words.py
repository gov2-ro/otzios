#!/usr/bin/env python3
"""
Analyze the DEX lexeme database and generate a list of forgotten Romanian words.

Strategy:
1. Query low-frequency words (< 0.70 threshold)
2. Filter out technical/compound/modern words
3. Generate statistics
4. Export to CSV with metadata
"""

import sqlite3
import csv
from collections import Counter
from datetime import datetime

DB_PATH = "data/processed/lexemes.db"
OUTPUT_CSV = "data/processed/forgotten_words_v1.csv"
STATS_FILE = "data/processed/statistics.txt"

# Thresholds
FREQUENCY_THRESHOLD = 0.70  # Words below this are candidates
MIN_FREQUENCY = 0.01  # Exclude zero/near-zero (likely errors)

def analyze_database(db_path):
    """Analyze the lexeme database and generate forgotten words list."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=" * 70)
    print("Romanian Forgotten Words Analyzer")
    print("=" * 70)
    print()

    # Overall statistics
    print("DATABASE STATISTICS")
    print("-" * 70)

    cursor.execute("SELECT COUNT(*) FROM Lexeme")
    total_lexemes = cursor.fetchone()[0]
    print(f"Total lexemes in database: {total_lexemes:,}")

    cursor.execute("SELECT COUNT(*) FROM Lexeme WHERE frequency > 0")
    with_frequency = cursor.fetchone()[0]
    print(f"Lexemes with frequency data: {with_frequency:,}")

    cursor.execute(f"SELECT COUNT(*) FROM Lexeme WHERE frequency > 0 AND frequency < {FREQUENCY_THRESHOLD}")
    rare_count = cursor.fetchone()[0]
    print(f"Rare words (freq < {FREQUENCY_THRESHOLD}): {rare_count:,}")

    print()
    print("FREQUENCY DISTRIBUTION")
    print("-" * 70)

    cursor.execute("""
        SELECT
            CASE
                WHEN frequency = 0 THEN 'No data (0.0)'
                WHEN frequency < 0.25 THEN 'Very rare (0.01-0.25)'
                WHEN frequency < 0.50 THEN 'Rare (0.25-0.50)'
                WHEN frequency < 0.70 THEN 'Uncommon (0.50-0.70)'
                WHEN frequency < 0.85 THEN 'Common (0.70-0.85)'
                ELSE 'Very common (0.85-1.0)'
            END as category,
            COUNT(*) as count
        FROM Lexeme
        GROUP BY category
        ORDER BY MIN(frequency)
    """)

    for category, count in cursor.fetchall():
        pct = (count / total_lexemes) * 100
        print(f"  {category:.<30} {count:>8,} ({pct:>5.1f}%)")

    print()
    print("PART OF SPEECH DISTRIBUTION (Rare Words)")
    print("-" * 70)

    cursor.execute(f"""
        SELECT description, COUNT(*) as count
        FROM Lexeme
        WHERE frequency > {MIN_FREQUENCY} AND frequency < {FREQUENCY_THRESHOLD}
        GROUP BY description
        ORDER BY count DESC
        LIMIT 15
    """)

    for desc, count in cursor.fetchall():
        print(f"  {desc:.<30} {count:>8,}")

    print()
    print("GENERATING FORGOTTEN WORDS LIST")
    print("-" * 70)

    # Query forgotten words
    cursor.execute(f"""
        SELECT
            form,
            formNoAccent,
            frequency,
            description,
            modelType,
            createDate,
            modDate
        FROM Lexeme
        WHERE frequency > {MIN_FREQUENCY}
          AND frequency < {FREQUENCY_THRESHOLD}
          AND LENGTH(form) > 2  -- Exclude very short words
        ORDER BY frequency ASC, form ASC
    """)

    forgotten_words = cursor.fetchall()
    print(f"Found {len(forgotten_words):,} forgotten word candidates")

    # Categorize by frequency
    categories = {
        'very_rare': [],      # 0.01-0.25
        'rare': [],           # 0.25-0.50
        'uncommon': []        # 0.50-0.70
    }

    for word_data in forgotten_words:
        freq = word_data[2]
        if freq < 0.25:
            categories['very_rare'].append(word_data)
        elif freq < 0.50:
            categories['rare'].append(word_data)
        else:
            categories['uncommon'].append(word_data)

    print()
    print("CATEGORIZATION")
    print("-" * 70)
    print(f"  Very rare (0.01-0.25):  {len(categories['very_rare']):>8,}")
    print(f"  Rare (0.25-0.50):       {len(categories['rare']):>8,}")
    print(f"  Uncommon (0.50-0.70):   {len(categories['uncommon']):>8,}")

    # Sample from each category
    print()
    print("SAMPLE WORDS BY CATEGORY")
    print("-" * 70)

    for cat_name, cat_words in categories.items():
        print(f"\n{cat_name.upper().replace('_', ' ')} (first 10):")
        for form, _, freq, desc, _, _, _ in cat_words[:10]:
            print(f"  {form:.<30} {desc:.<15} freq={freq:.3f}")

    # Export to CSV
    print()
    print("EXPORTING TO CSV")
    print("-" * 70)
    print(f"Output file: {OUTPUT_CSV}")

    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            'word',
            'word_no_accent',
            'frequency',
            'category',
            'description',
            'model_type',
            'create_date',
            'mod_date'
        ])

        # Write all words with category
        for word_data in forgotten_words:
            form, form_no_accent, freq, desc, model_type, create_date, mod_date = word_data

            # Determine category
            if freq < 0.25:
                category = 'very_rare'
            elif freq < 0.50:
                category = 'rare'
            else:
                category = 'uncommon'

            writer.writerow([
                form,
                form_no_accent,
                f"{freq:.4f}",
                category,
                desc,
                model_type,
                create_date,
                mod_date
            ])

    print(f"✅ Exported {len(forgotten_words):,} words to CSV")

    # Save statistics to file
    print()
    print("SAVING STATISTICS")
    print("-" * 70)

    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Romanian Forgotten Words - Statistics\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"\n")
        f.write(f"Total lexemes: {total_lexemes:,}\n")
        f.write(f"With frequency data: {with_frequency:,}\n")
        f.write(f"Forgotten candidates (freq < {FREQUENCY_THRESHOLD}): {len(forgotten_words):,}\n")
        f.write(f"\n")
        f.write(f"Very rare (< 0.25): {len(categories['very_rare']):,}\n")
        f.write(f"Rare (0.25-0.50): {len(categories['rare']):,}\n")
        f.write(f"Uncommon (0.50-0.70): {len(categories['uncommon']):,}\n")

    print(f"✅ Statistics saved to {STATS_FILE}")

    conn.close()

    print()
    print("=" * 70)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 70)
    print()
    print(f"Next steps:")
    print(f"  1. Review: {OUTPUT_CSV}")
    print(f"  2. Check stats: {STATS_FILE}")
    print(f"  3. Cross-reference with modern corpora (Wikipedia, OSCAR)")
    print(f"  4. Download wordfreq data to filter common words")
    print()

if __name__ == "__main__":
    analyze_database(DB_PATH)
