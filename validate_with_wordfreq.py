#!/usr/bin/env python3
"""
Validate DEX forgotten-word candidates against wordfreq's aggregated
Romanian frequency table.

For each candidate, lemmatize with simplemma and look up the lemma's Zipf
frequency in wordfreq. Words at or above the threshold (default 3.0,
wordfreq's reliability floor for the Romanian small list) have a modern
usage signal across multiple corpora and are filtered out as not
forgotten. Words below threshold (or absent / Zipf 0) are kept.

See docs/wordfreq-recipe.md for the design rationale.

Usage:
    python validate_with_wordfreq.py
    python validate_with_wordfreq.py --threshold 2.5 --keep-all
    python validate_with_wordfreq.py -i path/in.csv -o path/out.csv
"""

import argparse
import csv
import sys
import unicodedata
from pathlib import Path


def normalize_romanian(text: str) -> str:
    """Lowercase + cedilla→comma + NFC. Mirrors process_corpus.py:26-37."""
    return unicodedata.normalize(
        'NFC',
        text.lower().replace('ş', 'ș').replace('ţ', 'ț'),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Filter DEX forgotten-word candidates with wordfreq.',
    )
    parser.add_argument(
        '-i', '--input',
        type=Path,
        default=Path('data/processed/forgotten_words_curated.csv'),
        help='Curated candidates CSV (default: %(default)s)',
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=Path('data/processed/forgotten_words_validated_wordfreq.csv'),
        help='Output CSV (default: %(default)s)',
    )
    parser.add_argument(
        '-t', '--threshold',
        type=float,
        default=3.0,
        help='Zipf threshold; rows with zipf >= threshold are filtered '
             'out (default: %(default)s, wordfreq Romanian small-list floor)',
    )
    parser.add_argument(
        '--keep-all',
        action='store_true',
        help='Annotate every row instead of filtering (useful for inspection)',
    )
    parser.add_argument(
        '--lemmatize',
        action=argparse.BooleanOptionalAction,
        default=True,
        help='Lemmatize candidates before lookup (default: enabled)',
    )
    args = parser.parse_args()

    try:
        from wordfreq import zipf_frequency
    except ImportError:
        print('wordfreq not installed. Run: pip install wordfreq', file=sys.stderr)
        return 1

    lemmatize_fn = None
    if args.lemmatize:
        try:
            import simplemma
            lemmatize_fn = lambda w: simplemma.lemmatize(w, lang='ro')
        except ImportError:
            print('simplemma not installed. Run: pip install simplemma '
                  '(or pass --no-lemmatize)', file=sys.stderr)
            return 1

    if not args.input.exists():
        print(f'Input not found: {args.input}', file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)

    rows_in = 0
    rows_kept = 0
    zero_zipf = 0

    with args.input.open('r', encoding='utf-8') as fin, \
         args.output.open('w', encoding='utf-8', newline='') as fout:
        reader = csv.DictReader(fin)
        if not reader.fieldnames or 'word' not in reader.fieldnames:
            print(f'Input has no "word" column: {args.input}', file=sys.stderr)
            return 1
        out_fields = list(reader.fieldnames) + [
            'lemma', 'zipf_frequency', 'is_forgotten',
        ]
        writer = csv.DictWriter(fout, fieldnames=out_fields)
        writer.writeheader()

        for row in reader:
            rows_in += 1
            word = normalize_romanian(row.get('word', ''))
            if not word:
                continue
            lemma = lemmatize_fn(word) if lemmatize_fn else word
            zipf = zipf_frequency(lemma, 'ro')
            is_forgotten = zipf < args.threshold
            if zipf == 0.0:
                zero_zipf += 1

            row['lemma'] = lemma
            row['zipf_frequency'] = f'{zipf:.3f}'
            row['is_forgotten'] = str(is_forgotten).lower()

            if args.keep_all or is_forgotten:
                writer.writerow(row)
                if is_forgotten:
                    rows_kept += 1

    pct = (rows_kept / rows_in * 100) if rows_in else 0.0
    print(f'Read     : {rows_in:,} candidates')
    print(f'Kept     : {rows_kept:,} ({pct:.1f}%) with zipf < {args.threshold}')
    print(f'Zero Zipf: {zero_zipf:,} (no signal in any wordfreq source)')
    print(f'Output   : {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
