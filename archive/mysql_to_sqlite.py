#!/usr/bin/env python3
"""
Convert MySQL dump to SQLite database with proper handling of Romanian diacritics.
Uses Python to avoid shell escaping issues.
"""

import sqlite3
import re
import sys

def clean_mysql_line(line):
    """Clean a line of MySQL SQL for SQLite compatibility."""
    # Skip MySQL-specific commands
    if line.startswith(('/*!', 'LOCK TABLES', 'UNLOCK TABLES', 'SET ')):
        return None

    # Remove ENGINE, CHARSET clauses
    line = re.sub(r' ENGINE=\S+', '', line)
    line = re.sub(r' DEFAULT CHARSET=\S+', '', line)
    line = re.sub(r' COLLATE=\S+', '', line)
    line = re.sub(r' CHARACTER SET \S+', '', line)

    # Fix AUTO_INCREMENT - only use AUTOINCREMENT with INTEGER PRIMARY KEY
    if 'AUTO_INCREMENT' in line and 'PRIMARY KEY' in line:
        line = line.replace('AUTO_INCREMENT', 'AUTOINCREMENT')
    else:
        line = line.replace('AUTO_INCREMENT', '')

    # Fix data types
    line = re.sub(r' int\(\d+\)', ' INTEGER', line)
    line = re.sub(r' tinyint\(\d+\)', ' INTEGER', line)
    line = re.sub(r' varchar\(\d+\)', ' TEXT', line)
    line = re.sub(r' text', ' TEXT', line, flags=re.IGNORECASE)
    line = re.sub(r' float', ' REAL', line)

    # Remove backticks
    line = line.replace('`', '')

    return line

def convert_mysql_to_sqlite(input_sql, output_db):
    """Convert MySQL dump to SQLite database."""

    print(f"Converting {input_sql} to {output_db}")
    print("This may take a few minutes...")
    print()

    # Connect to SQLite
    conn = sqlite3.connect(output_db)
    cursor = conn.cursor()

    # Read and execute SQL
    current_statement = []
    line_count = 0
    executed = 0
    skipped = 0

    with open(input_sql, 'r', encoding='utf-8') as f:
        for line in f:
            line_count += 1

            # Progress indicator
            if line_count % 1000 == 0:
                print(f"  Processed {line_count} lines ({executed} executed, {skipped} skipped)...")

            # Clean line
            cleaned = clean_mysql_line(line.strip())
            if cleaned is None:
                skipped += 1
                continue

            # Skip comment lines
            if cleaned.startswith('--'):
                skipped += 1
                continue

            # Empty line
            if not cleaned:
                continue

            # Build statement
            current_statement.append(cleaned)

            # Execute when we hit semicolon
            if cleaned.endswith(';'):
                statement = ' '.join(current_statement)
                try:
                    cursor.execute(statement)
                    executed += 1

                    # Commit every 100 statements
                    if executed % 100 == 0:
                        conn.commit()

                except sqlite3.Error as e:
                    # Log errors but continue
                    if 'near "AUTOINCREMENT"' not in str(e):
                        print(f"  Warning on line {line_count}: {str(e)[:100]}")
                    skipped += 1

                current_statement = []

    # Final commit
    conn.commit()

    print()
    print(f"✅ Conversion complete!")
    print(f"  Total lines: {line_count}")
    print(f"  Statements executed: {executed}")
    print(f"  Statements skipped: {skipped}")

    # Verify data
    print()
    print("Verifying database...")

    try:
        cursor.execute("SELECT COUNT(*) FROM Lexeme")
        lexeme_count = cursor.fetchone()[0]
        print(f"  ✅ Lexeme table: {lexeme_count:,} records")

        cursor.execute("SELECT COUNT(*) FROM Entry")
        entry_count = cursor.fetchone()[0]
        print(f"  ✅ Entry table: {entry_count:,} records")

        cursor.execute("SELECT form, frequency FROM Lexeme WHERE frequency < 0.7 LIMIT 5")
        print(f"\n  Sample forgotten word candidates:")
        for form, freq in cursor.fetchall():
            print(f"    - {form}: frequency={freq:.2f}")

    except sqlite3.Error as e:
        print(f"  ⚠️  Verification error: {e}")

    conn.close()
    print()
    print(f"Database saved to: {output_db}")

if __name__ == "__main__":
    input_sql = "data/dictionaries/dex-database-sample.sql"
    output_db = "data/dictionaries/dex-sample.db"

    print("=" * 60)
    print("MySQL → SQLite Converter")
    print("=" * 60)
    print()

    convert_mysql_to_sqlite(input_sql, output_db)
