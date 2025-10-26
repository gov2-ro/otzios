#!/bin/bash
# Convert MySQL dump to SQLite database
#
# This script cleans up MySQL-specific syntax and imports into SQLite

set -e  # Exit on error

INPUT_SQL="data/dictionaries/dex-database-sample.sql"
OUTPUT_DB="data/dictionaries/dex-sample.db"
TEMP_SQL="data/dictionaries/dex-sample-cleaned.sql"

echo "========================================="
echo "MySQL → SQLite Converter"
echo "========================================="
echo ""
echo "Input:  $INPUT_SQL"
echo "Output: $OUTPUT_DB"
echo ""

# Remove old database if exists
if [ -f "$OUTPUT_DB" ]; then
    echo "Removing old database..."
    rm "$OUTPUT_DB"
fi

echo "Cleaning SQL file for SQLite compatibility..."
# Clean up MySQL-specific syntax
cat "$INPUT_SQL" | \
    # Remove MySQL-specific commands
    grep -v "^/\*!" | \
    grep -v "^LOCK TABLES" | \
    grep -v "^UNLOCK TABLES" | \
    grep -v "^SET " | \
    # Convert AUTO_INCREMENT to AUTOINCREMENT (SQLite syntax)
    sed 's/AUTO_INCREMENT/AUTOINCREMENT/g' | \
    # Remove ENGINE and CHARSET clauses
    sed 's/ ENGINE=[^ ]*//g' | \
    sed 's/ DEFAULT CHARSET=[^ ]*//g' | \
    sed 's/ COLLATE=[^ ]*//g' | \
    sed 's/ CHARACTER SET [^ ]*//g' | \
    # Fix data types
    sed 's/ int([0-9]*) / INTEGER /g' | \
    sed 's/ tinyint([0-9]*) / INTEGER /g' | \
    sed 's/ varchar([0-9]*) / TEXT /g' | \
    sed 's/ text / TEXT /g' | \
    sed 's/ float / REAL /g' | \
    # Remove backticks (MySQL quote style)
    sed 's/`//g' | \
    # Keep only uncommented INSERT/CREATE/DROP statements and comments
    grep -v "^--" \
    > "$TEMP_SQL"

echo "Importing into SQLite..."
sqlite3 "$OUTPUT_DB" < "$TEMP_SQL"

echo ""
echo "✅ Conversion complete!"
echo ""
ls -lh "$OUTPUT_DB"
echo ""
echo "Database ready at: $OUTPUT_DB"
echo ""
echo "Test query:"
echo "  sqlite3 $OUTPUT_DB \"SELECT COUNT(*) FROM Lexeme;\""
echo "  sqlite3 $OUTPUT_DB \"SELECT form, frequency FROM Lexeme WHERE frequency < 0.7 LIMIT 10;\""
