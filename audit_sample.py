#!/usr/bin/env python3
"""
Draw a stratified sample of words for the shortlist data-quality audit.

For each stratum (included tiers + excluded classes), randomly sample N words
and store them in the `audit_sample` table of `data/research.db`. The Flask
research UI's audit mode reads this table to scope the word list per stratum.

Strata are derived by re-running `make_shortlist.classify()` on every row of
`forgotten_words_diachronic.csv`, plus the rare-in-use words from
`rare_words_wordfreq.csv`.

Usage:
    python audit_sample.py                       # default: 100 per stratum
    python audit_sample.py --n 50                # smaller sample
    python audit_sample.py --reset               # wipe table and redraw
    python audit_sample.py --strata tier_a_extinct,rare_in_use
    python audit_sample.py --seed 42             # reproducible sample
    python audit_sample.py --stats                # print stratum sizes, do not write
"""

import argparse
import csv
import random
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from make_shortlist import classify, pos_excluded

DIACHRONIC_CSV = Path('data/processed/forgotten_words_diachronic.csv')
RARE_CSV       = Path('data/processed/rare_words_wordfreq.csv')
RESEARCH_DB    = Path('data/research.db')

# Mirror make_shortlist.py CLI defaults (not the classify() function defaults,
# which differ — function default is 0.70 but the CLI ships 0.85).
DEFAULT_ABSENT_PPM = 0.1
DEFAULT_DEX_FREQ   = 0.85

# Included strata: corpus_* and dex_* labels returned by make_shortlist.classify
TIER_TO_STRATUM = {
    'corpus_extinct':         'tier_a_extinct',
    'corpus_declining':       'tier_a_declining',
    'corpus_historical_only': 'tier_a_historical',
    'dex_invechit_absent':    'tier_b_invechit',
    'dex_absent_highfreq':    'tier_c_absent_highfreq',
}

STRATA_ORDER = [
    'tier_a_extinct',
    'tier_a_declining',
    'tier_a_historical',
    'tier_b_invechit',
    'tier_c_absent_highfreq',
    'rare_in_use',
    'excl_pos',
    'excl_absent_lowdex',
    'excl_stable_emerging',
    'excl_other',
]


def _excluded_stratum(row: dict) -> str:
    """Return the excluded-bucket name for a diachronic row that classify() rejected."""
    if pos_excluded(row.get('dex_pos', '') or ''):
        return 'excl_pos'
    verdict = row.get('verdict', '')
    if verdict in ('stable', 'emerging'):
        return 'excl_stable_emerging'
    if verdict == 'absent':
        # not picked up by tier B (no învechit) and not by tier C (low dex_frequency)
        return 'excl_absent_lowdex'
    return 'excl_other'


def collect_words_by_stratum(
    absent_ppm: float = DEFAULT_ABSENT_PPM,
    dex_freq: float = DEFAULT_DEX_FREQ,
) -> dict[str, list[str]]:
    by_stratum: dict[str, list[str]] = defaultdict(list)

    if not DIACHRONIC_CSV.exists():
        raise SystemExit(f'Missing: {DIACHRONIC_CSV} — run validate_diachronic.py first.')

    with DIACHRONIC_CSV.open(encoding='utf-8') as f:
        for row in csv.DictReader(f):
            word = row.get('word', '').strip()
            if not word:
                continue
            tier = classify(row, absent_ppm_threshold=absent_ppm, dex_freq_threshold=dex_freq)
            if tier is not None:
                stratum = TIER_TO_STRATUM.get(tier)
                if stratum:
                    by_stratum[stratum].append(word)
            else:
                by_stratum[_excluded_stratum(row)].append(word)

    if RARE_CSV.exists():
        with RARE_CSV.open(encoding='utf-8') as f:
            for row in csv.DictReader(f):
                # ui/app.py uses word_no_accent as the key for rare rows
                word = (row.get('word_no_accent') or row.get('word', '')).strip()
                if word:
                    by_stratum['rare_in_use'].append(word)

    # Dedupe pools while preserving first-seen order (stable across runs given fixed input).
    return {s: list(dict.fromkeys(words)) for s, words in by_stratum.items()}


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_sample (
            stratum    TEXT NOT NULL,
            word       TEXT NOT NULL,
            drawn_at   TEXT NOT NULL,
            PRIMARY KEY (stratum, word)
        )
    """)
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_audit_sample_stratum ON audit_sample(stratum)'
    )
    conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description='Draw stratified audit sample.')
    parser.add_argument('--n', type=int, default=100, help='Sample size per stratum (default: 100)')
    parser.add_argument('--reset', action='store_true', help='Wipe audit_sample table and redraw all strata')
    parser.add_argument('--strata', default='', help='Comma-separated stratum names to draw (default: all)')
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducibility')
    parser.add_argument('--stats', action='store_true', help='Print stratum pool sizes, do not write')
    parser.add_argument('--db', type=Path, default=RESEARCH_DB)
    parser.add_argument(
        '--absent-ppm-threshold', type=float, default=DEFAULT_ABSENT_PPM,
        help=f'Tier C ceiling for modern_ppm (default: {DEFAULT_ABSENT_PPM}, mirrors make_shortlist CLI)',
    )
    parser.add_argument(
        '--dex-freq-threshold', type=float, default=DEFAULT_DEX_FREQ,
        help=f'Tier C floor for dex_frequency (default: {DEFAULT_DEX_FREQ}, mirrors make_shortlist CLI)',
    )
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    requested = (
        [s.strip() for s in args.strata.split(',') if s.strip()]
        if args.strata else STRATA_ORDER
    )
    unknown = [s for s in requested if s not in STRATA_ORDER]
    if unknown:
        raise SystemExit(f'Unknown strata: {unknown}. Known: {STRATA_ORDER}')

    print('Reading sources …')
    pools = collect_words_by_stratum(
        absent_ppm=args.absent_ppm_threshold,
        dex_freq=args.dex_freq_threshold,
    )

    sizes = Counter({s: len(pools.get(s, [])) for s in STRATA_ORDER})
    print('\nPool sizes:')
    for s in STRATA_ORDER:
        print(f'  {s:<26} {sizes[s]:>8,}')

    if args.stats:
        return 0

    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(args.db))
    ensure_schema(conn)

    if args.reset:
        target_strata = requested
        placeholders = ','.join('?' * len(target_strata))
        conn.execute(
            f'DELETE FROM audit_sample WHERE stratum IN ({placeholders})',
            target_strata,
        )
        conn.commit()

    now = datetime.now(timezone.utc).isoformat()
    drawn_total = 0
    skipped_existing = 0

    for stratum in requested:
        existing = conn.execute(
            'SELECT COUNT(*) FROM audit_sample WHERE stratum = ?', (stratum,)
        ).fetchone()[0]
        if existing > 0 and not args.reset:
            print(f'  {stratum:<26} skip (already has {existing} rows; use --reset to redraw)')
            skipped_existing += 1
            continue

        pool = pools.get(stratum, [])
        if not pool:
            print(f'  {stratum:<26} empty pool, skipping')
            continue

        n = min(args.n, len(pool))
        sample = random.sample(pool, n)
        conn.executemany(
            'INSERT OR IGNORE INTO audit_sample (stratum, word, drawn_at) VALUES (?, ?, ?)',
            [(stratum, w, now) for w in sample],
        )
        drawn_total += n
        print(f'  {stratum:<26} drew {n}')

    conn.commit()
    conn.close()

    print(f'\nDrawn: {drawn_total} words across {len(requested) - skipped_existing} strata.')
    print(f'DB:    {args.db}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
