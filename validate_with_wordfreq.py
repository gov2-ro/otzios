#!/usr/bin/env python3
"""
Validate DEX forgotten-word candidates against wordfreq's aggregated
Romanian frequency table.

For each candidate, lemmatize with simplemma and look up the lemma's Zipf
frequency in wordfreq. Words are classified into three tiers:

  forgotten   — zipf < threshold (default 3.0): virtually absent from modern usage
  rare_in_use — threshold ≤ zipf < upper_threshold (default 4.5): still appears
                but very infrequently — a separate output file is written for these
  common      — zipf ≥ upper_threshold: everyday vocabulary, filtered out

The 'is_forgotten' column (true/false) is preserved for backward compatibility
with search_wild.py and build_ui_db.py. The 'tier' column is the richer label.

See docs/wordfreq-recipe.md for the design rationale.

Usage:
    python validate_with_wordfreq.py
    python validate_with_wordfreq.py --threshold 2.5 --upper-threshold 4.0
    python validate_with_wordfreq.py --keep-all
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
        help='Output CSV for forgotten words (default: %(default)s)',
    )
    parser.add_argument(
        '--output-rare',
        type=Path,
        default=Path('data/processed/rare_words_wordfreq.csv'),
        help='Output CSV for rare-in-use words; ignored with --keep-all '
             '(default: %(default)s)',
    )
    parser.add_argument(
        '-t', '--threshold',
        type=float,
        default=3.0,
        help='Lower Zipf threshold; rows with zipf < threshold are "forgotten" '
             '(default: %(default)s, wordfreq Romanian small-list floor)',
    )
    parser.add_argument(
        '--upper-threshold',
        type=float,
        default=4.5,
        help='Upper Zipf threshold; rows with zipf >= this are filtered as '
             'common. Between threshold and upper-threshold = "rare_in_use" '
             '(default: %(default)s)',
    )
    parser.add_argument(
        '--keep-all',
        action='store_true',
        help='Annotate every row with tier and write to main output instead '
             'of filtering (useful for inspection; --output-rare is ignored)',
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
    counts = {'forgotten': 0, 'rare_in_use': 0, 'common': 0}
    zero_zipf = 0

    def _run(fout, frare):
        nonlocal rows_in, zero_zipf
        reader = csv.DictReader(fin)
        if not reader.fieldnames or 'word' not in reader.fieldnames:
            print(f'Input has no "word" column: {args.input}', file=sys.stderr)
            return 1
        # Move 'word' (DEX stress-marked form, e.g. bucl'e) to the end —
        # word_no_accent is the clean lookup key used throughout.
        other_fields = [f for f in reader.fieldnames if f != 'word']
        out_fields = other_fields + ['lemma', 'zipf_frequency', 'tier', 'is_forgotten', 'word']
        writer = csv.DictWriter(fout, fieldnames=out_fields)
        writer.writeheader()
        if frare is not None:
            writer_rare = csv.DictWriter(frare, fieldnames=out_fields)
            writer_rare.writeheader()
        else:
            writer_rare = None

        for row in reader:
            rows_in += 1
            # Prefer word_no_accent: DEX's `form` field uses apostrophes for
            # stress markers (e.g. bucl'e) that wordfreq won't recognize.
            raw = row.get('word_no_accent') or row.get('word', '')
            word = normalize_romanian(raw)
            if not word:
                continue
            lemma = lemmatize_fn(word) if lemmatize_fn else word
            zipf = zipf_frequency(lemma, 'ro')
            if zipf == 0.0:
                zero_zipf += 1

            if zipf < args.threshold:
                tier = 'forgotten'
            elif zipf < args.upper_threshold:
                tier = 'rare_in_use'
            else:
                tier = 'common'

            counts[tier] += 1
            row['lemma'] = lemma
            row['zipf_frequency'] = f'{zipf:.3f}'
            row['tier'] = tier
            row['is_forgotten'] = str(tier == 'forgotten').lower()

            if args.keep_all:
                writer.writerow(row)
            elif tier == 'forgotten':
                writer.writerow(row)
            elif tier == 'rare_in_use' and writer_rare is not None:
                writer_rare.writerow(row)

        return 0

    with args.input.open('r', encoding='utf-8') as fin, \
         args.output.open('w', encoding='utf-8', newline='') as fout:
        if args.keep_all:
            rc = _run(fout, frare=None)
        else:
            args.output_rare.parent.mkdir(parents=True, exist_ok=True)
            with args.output_rare.open('w', encoding='utf-8', newline='') as frare:
                rc = _run(fout, frare)

    if rc != 0:
        return rc

    pct_forgotten = (counts['forgotten'] / rows_in * 100) if rows_in else 0.0
    pct_rare = (counts['rare_in_use'] / rows_in * 100) if rows_in else 0.0
    print(f'Read        : {rows_in:,} candidates')
    print(f'Forgotten   : {counts["forgotten"]:,} ({pct_forgotten:.1f}%) zipf < {args.threshold}')
    print(f'Rare in use : {counts["rare_in_use"]:,} ({pct_rare:.1f}%) '
          f'{args.threshold} ≤ zipf < {args.upper_threshold}')
    print(f'Common      : {counts["common"]:,} filtered out')
    print(f'Zero Zipf   : {zero_zipf:,} (no signal in any wordfreq source)')
    print(f'Output      : {args.output}')
    if not args.keep_all:
        print(f'Rare output : {args.output_rare}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
