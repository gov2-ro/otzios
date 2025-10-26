#!/usr/bin/env python3
"""
Create a development sample of the DEX database.

Strategy:
1. Keep ALL schema (CREATE TABLE statements)
2. Keep CRITICAL tables at 100%: Lexeme, Entry, Abbreviation
3. Sample supporting tables at 10%
4. SKIP large tables we don't need: FullTextIndex (529 INSERTs × 1MB = 500MB!)
5. Result: ~200-300MB instead of 1.2GB

This gives us a working database for development without losing important data.
"""

import re
import sys

def create_sample_database(input_file, output_file, sample_rate=0.1):
    """
    Create a sampled version of the DEX database.

    Args:
        input_file: Path to full dex-database.sql
        output_file: Path to output sampled SQL file
        sample_rate: Fraction of records to keep for non-critical tables
    """

    # Tables we MUST keep 100% (critical for forgotten words)
    critical_tables = {
        'Lexeme',          # Word forms with frequency - ESSENTIAL!
        'Entry',           # Dictionary entries
        'Abbreviation',    # Markers like 'înv.' - ESSENTIAL!
        'EntryLexeme',     # Links entries to lexemes
        'Meaning',         # Word meanings
        'DefinitionSimple',# Simple definitions
        'Definition',      # Full definitions
    }

    # Tables we can skip entirely (not needed for forgotten words)
    skip_tables = {
        'FullTextIndex',   # 500MB+ of search index - rebuild later
        'CrawlerPhrase',   # Web crawler data
        'CrawlerUrl',      # Web crawler data
        'CrawlerIgnoredUrl', # Web crawler data
        'WikiArticle',     # Wikipedia integration
        'MillData',        # Unknown - seems large
        'RandomWord',      # Random word feature
    }

    print(f"Creating sample database:")
    print(f"  Input: {input_file}")
    print(f"  Output: {output_file}")
    print(f"  Critical tables (100%): {', '.join(sorted(critical_tables))}")
    print(f"  Skipped tables: {', '.join(sorted(skip_tables))}")
    print(f"  Sample rate for others: {sample_rate*100}%")
    print()

    current_table = None
    insert_count = 0
    kept_count = 0
    skipped_count = 0

    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:

        for line_num, line in enumerate(infile, 1):
            # Track current table from CREATE TABLE statements
            create_match = re.match(r'CREATE TABLE `(\w+)`', line)
            if create_match:
                current_table = create_match.group(1)
                print(f"Found table: {current_table}")

            # Always write schema (CREATE, DROP, comments, etc.)
            if not line.startswith('INSERT INTO'):
                outfile.write(line)
                continue

            # Parse INSERT INTO statement
            insert_match = re.match(r'INSERT INTO `(\w+)`', line)
            if not insert_match:
                outfile.write(line)
                continue

            table_name = insert_match.group(1)
            insert_count += 1

            # Decision: keep or skip this INSERT?
            if table_name in skip_tables:
                skipped_count += 1
                # Write comment instead
                outfile.write(f"-- SKIPPED: {line[:100]}...\n")
                if insert_count % 100 == 0:
                    print(f"  [{table_name}] Skipped {skipped_count} inserts so far...")
                continue

            if table_name in critical_tables:
                # Keep all critical data
                outfile.write(line)
                kept_count += 1
                if insert_count % 50 == 0:
                    print(f"  [{table_name}] Kept {kept_count} inserts (critical)")
            else:
                # Sample other tables
                if insert_count % int(1/sample_rate) == 0:
                    outfile.write(line)
                    kept_count += 1
                else:
                    outfile.write(f"-- SAMPLED: {line[:80]}...\n")
                    skipped_count += 1

            if line_num % 500 == 0:
                print(f"Progress: {line_num} lines, kept {kept_count} inserts, skipped {skipped_count}")

    print()
    print(f"✅ Sample database created!")
    print(f"  Total INSERT statements processed: {insert_count}")
    print(f"  Kept: {kept_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Reduction: ~{skipped_count/insert_count*100:.1f}%")

if __name__ == "__main__":
    input_sql = "data/dictionaries/dex-database.sql"
    output_sql = "data/dictionaries/dex-database-sample.sql"

    print("=" * 60)
    print("DEX Database Sampler")
    print("=" * 60)
    print()

    create_sample_database(input_sql, output_sql, sample_rate=0.1)

    print()
    print("Next steps:")
    print(f"  1. Check size: ls -lh {output_sql}")
    print(f"  2. Convert to SQLite: # (we'll do this next)")
    print(f"  3. Query forgotten words!")
