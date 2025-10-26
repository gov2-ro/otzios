#!/usr/bin/env python3
"""
Explore the DEX Online database structure and extract sample data.
This script connects to the SQL database and examines key tables.
"""

import sqlite3
import sys

def explore_database(db_path):
    """Explore the DEX database structure."""

    # Note: We'll need to convert MySQL dump to SQLite first
    # For now, let's document what we found from examining the SQL file

    print("=== DEX Online Database Structure ===\n")

    print("Key Tables Found:")
    print("-" * 50)
    print("1. Entry - Dictionary entries (~335,611 entries)")
    print("   - id, description, structStatus, createDate, modDate")
    print("")

    print("2. Lexeme - Word forms (~365,869 lexemes)")
    print("   - id, form, formNoAccent, description")
    print("   - frequency (float) - IMPORTANT for forgotten words!")
    print("   - modelType, modelNumber (morphological info)")
    print("   - Example: 'învechit' would be marked here")
    print("")

    print("3. DefinitionSimple - Simplified definitions")
    print("")

    print("4. Meaning - Word meanings/senses")
    print("")

    print("5. Abbreviation - Markers like 'înv.' (învechit=archaic)")
    print("   Found markers:")
    print("   - 'înv.' = învechit (archaic)")
    print("   - 'reg.' = regional")
    print("   - 'pop.' = popular")
    print("   - 'arh.' = arhaizant (archaizing)")
    print("   - 'dial.' = dialectal")
    print("")

    print("=== Important Fields for Forgotten Words ===")
    print("-" * 50)
    print("1. Lexeme.frequency - Frequency in corpus (0.0-1.0)")
    print("2. Lexeme.form - The actual word")
    print("3. Lexeme.description - Often contains markers like 'adj.', 's.m.'")
    print("4. Entry.description - Human-readable entry name")
    print("")

    print("=== Next Steps ===")
    print("-" * 50)
    print("1. Convert MySQL dump to SQLite for easier querying")
    print("2. Query Lexeme table for words marked 'înv.' or with low frequency")
    print("3. Cross-reference with modern corpora (OSCAR, Wikipedia)")
    print("4. Generate forgotten words list")
    print("")

    print("=== Sample Lexeme Data (from SQL file) ===")
    print("-" * 50)
    print("Word: 'aalenian', frequency: 0.81, description: 'adj.'")
    print("Word: 'aba', frequency: 0.93, description: 's.f.'")
    print("Word: 'abatis', frequency: 0.69 - LOWER frequency = potentially forgotten!")
    print("Word: 'accent', frequency: 0.99 - HIGH frequency = common word")
    print("")

    print("Low frequency words (< 0.75) are candidates for 'forgotten words'")

if __name__ == "__main__":
    db_path = "data/dictionaries/dex-database.sql"
    explore_database(db_path)