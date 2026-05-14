#!/usr/bin/env python3
"""
Build a curated shortlist of forgotten Romanian words for web validation.

Reads forgotten_words_diachronic.csv (output of validate_diachronic.py) and
selects two tiers:

  Tier A — corpus evidence: verdict in (extinct, declining, historical_only)
            with hist_ppm > 0, no domain tag, no excluded POS
  Tier B — DEX editorial: verdict == absent AND dex_register contains 'învechit'
            with no domain tag, no excluded POS

Output is compatible with search_wild.py (has 'word' and 'is_forgotten' columns).

Usage:
    python make_shortlist.py                    # write shortlist
    python make_shortlist.py --stats            # dry run, print counts only
    python make_shortlist.py --limit 100        # cap output rows
    python make_shortlist.py --input path/to/diachronic.csv --output path/to/out.csv
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

INPUT_CSV  = Path('data/processed/forgotten_words_diachronic.csv')
OUTPUT_CSV = Path('data/processed/forgotten_words_shortlist.csv')

TIER_A_VERDICTS = ('extinct', 'declining', 'historical_only')

EXCLUDED_POS = {
    'prefix', 'sufix', 'element de compunere',
    'nume propriu', 'siglă', 'abreviere', 'non-lexem',
}

TIER_ORDER = {
    'corpus_extinct':          0,
    'corpus_declining':        1,
    'corpus_historical_only':  2,
    'dex_invechit_absent':     3,
}

OUT_FIELDS = [
    'word', 'dex_frequency', 'description', 'dex_pos',
    'verdict', 'log_ratio', 'hist_ppm', 'modern_ppm',
    'dex_register', 'dex_domain', 'dex_etymology',
    'confidence_tier', 'is_forgotten',
]


def pos_excluded(dex_pos: str) -> bool:
    tags = {t.strip() for t in dex_pos.split('|') if t.strip()}
    return bool(tags & EXCLUDED_POS)


def classify(row: dict) -> str | None:
    verdict = row['verdict']
    has_domain = bool(row['dex_domain'])
    bad_pos = pos_excluded(row['dex_pos'])

    if has_domain or bad_pos:
        return None

    if verdict in TIER_A_VERDICTS and float(row['hist_ppm']) > 0:
        return f'corpus_{verdict}'

    if verdict == 'absent' and 'învechit' in row['dex_register'].split('|'):
        return 'dex_invechit_absent'

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description='Build forgotten-words shortlist for web validation')
    parser.add_argument('--input',  type=Path, default=INPUT_CSV)
    parser.add_argument('--output', type=Path, default=OUTPUT_CSV)
    parser.add_argument('--limit',  type=int,  default=None, help='Cap total output rows')
    parser.add_argument('--stats',  action='store_true', help='Print stats only, do not write')
    args = parser.parse_args()

    if not args.input.exists():
        print(f'Missing: {args.input}  — run validate_diachronic.py first.')
        return 1

    rows = list(csv.DictReader(args.input.open(encoding='utf-8')))
    print(f'Read {len(rows):,} rows from {args.input}')

    # Classify every row
    selected: list[dict] = []
    excluded_domain = 0
    excluded_pos = 0

    for row in rows:
        tier = classify(row)
        if tier is None:
            if row['dex_domain']:
                excluded_domain += 1
            elif pos_excluded(row['dex_pos']):
                excluded_pos += 1
            continue
        out = {f: row.get(f, '') for f in OUT_FIELDS}
        out['confidence_tier'] = tier
        out['is_forgotten'] = 'true'
        selected.append(out)

    # Sort: Tier A by log_ratio desc, Tier B by dex_frequency desc
    def sort_key(r: dict):
        order = TIER_ORDER.get(r['confidence_tier'], 99)
        if r['confidence_tier'] == 'dex_invechit_absent':
            return (order, -float(r['dex_frequency'] or 0))
        return (order, -float(r['log_ratio'] or 0))

    selected.sort(key=sort_key)

    if args.limit:
        selected = selected[:args.limit]

    # Stats
    tier_counts = Counter(r['confidence_tier'] for r in selected)
    print()
    for tier in sorted(tier_counts, key=lambda t: TIER_ORDER.get(t, 99)):
        print(f'  {tier:<28} {tier_counts[tier]:>6,}')
    print(f'  {"—"*35}')
    print(f'  {"Total":<28} {len(selected):>6,}')
    print(f'  Excluded (domain tag)        {excluded_domain:>6,}')
    print(f'  Excluded (POS)               {excluded_pos:>6,}')

    if args.stats:
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(selected)

    print(f'\nWritten → {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
