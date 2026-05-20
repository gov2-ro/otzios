#!/usr/bin/env python3
"""
Aggregate audit labels into a prevalence report + per-cell word lists.

Reads `data/research.db` (audit_sample × bookmarks.tags), produces:
  - docs/audit/YYYY-MM-DD-summary.md  — stratum × label markdown table
  - data/audit/<stratum>_<label>.txt  — one file per cell with the words

A word with multiple `audit:*` tags contributes to every matching cell.
A word in a stratum's sample with no `audit:*` tag contributes to the
'_unlabeled' column.

Usage:
    python audit_report.py
    python audit_report.py --out-dir docs/audit --list-dir data/audit
    python audit_report.py --date 2026-05-20   # override report filename date
"""

import argparse
import sqlite3
from collections import defaultdict
from datetime import date
from pathlib import Path

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

# Display order of label columns in the report.
INCLUDED_LABELS = [
    'keep', 'inflection', 'variant', 'loanword',
    'dialect', 'jargon', 'no_def', 'other',
]
EXCLUDED_LABELS = ['keep', 'correctly_out', 'no_def', 'other']
ALL_LABELS = ['keep', 'inflection', 'variant', 'loanword',
              'dialect', 'jargon', 'correctly_out', 'no_def', 'other']

INCL_STRATA = set(STRATA_ORDER[:6])

UNLABELED = '_unlabeled'


def _short_label(tag: str) -> str:
    """audit:keep → keep, audit:no_def → no_def."""
    return tag.split(':', 1)[1] if tag.startswith('audit:') else tag


def load_labels(db: sqlite3.Connection) -> tuple[dict, dict]:
    """Return (sample_words_by_stratum, labels_by_stratum_label_to_words)."""
    sample = defaultdict(list)
    for r in db.execute('SELECT stratum, word FROM audit_sample').fetchall():
        sample[r['stratum']].append(r['word'])

    labels: dict[tuple[str, str], list[str]] = defaultdict(list)
    rows = db.execute("""
        SELECT s.stratum, s.word, b.tags
        FROM audit_sample s
        LEFT JOIN bookmarks b ON b.word = s.word
    """).fetchall()
    for r in rows:
        tags = [t.strip() for t in (r['tags'] or '').split(',') if t.strip()]
        audit_tags = [_short_label(t) for t in tags if t.startswith('audit:')]
        if not audit_tags:
            labels[(r['stratum'], UNLABELED)].append(r['word'])
        else:
            for lbl in audit_tags:
                labels[(r['stratum'], lbl)].append(r['word'])
    return sample, labels


def write_word_lists(labels: dict, list_dir: Path) -> int:
    list_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for (stratum, label), words in sorted(labels.items()):
        if label == UNLABELED or not words:
            continue
        fp = list_dir / f'{stratum}_{label}.txt'
        fp.write_text('\n'.join(sorted(words)) + '\n', encoding='utf-8')
        n += 1
    return n


def render_markdown(sample: dict, labels: dict, today: str) -> str:
    lines = [f'# Shortlist audit — {today}', '']
    lines.append(
        '`audit_report.py` output. Each cell shows count and percent of the '
        "stratum's sample. Empty cells = 0."
    )
    lines.append('')

    # --- Included tiers ---
    cols = INCLUDED_LABELS + [UNLABELED]
    header = ['stratum', 'n'] + cols
    lines.append('## Included tiers')
    lines.append('')
    lines.append('| ' + ' | '.join(header) + ' |')
    lines.append('|' + '|'.join(['---'] * len(header)) + '|')
    for s in [s for s in STRATA_ORDER if s in INCL_STRATA]:
        total = len(sample.get(s, []))
        if total == 0:
            continue
        cells = [s, str(total)]
        for c in cols:
            count = len(labels.get((s, c), []))
            cells.append(f'{count} ({100*count/total:.0f}%)' if count else '')
        lines.append('| ' + ' | '.join(cells) + ' |')
    lines.append('')

    # --- Excluded buckets ---
    cols = EXCLUDED_LABELS + [UNLABELED]
    header = ['stratum', 'n'] + cols
    lines.append('## Excluded buckets')
    lines.append('')
    lines.append('| ' + ' | '.join(header) + ' |')
    lines.append('|' + '|'.join(['---'] * len(header)) + '|')
    for s in [s for s in STRATA_ORDER if s not in INCL_STRATA]:
        total = len(sample.get(s, []))
        if total == 0:
            continue
        cells = [s, str(total)]
        for c in cols:
            count = len(labels.get((s, c), []))
            cells.append(f'{count} ({100*count/total:.0f}%)' if count else '')
        lines.append('| ' + ' | '.join(cells) + ' |')
    lines.append('')

    # --- Per-stratum coverage ---
    lines.append('## Coverage')
    lines.append('')
    lines.append('Fraction of each stratum with at least one `audit:*` label.')
    lines.append('')
    lines.append('| stratum | labeled | total | % |')
    lines.append('|---|---|---|---|')
    for s in STRATA_ORDER:
        words = sample.get(s, [])
        if not words:
            continue
        unl = len(labels.get((s, UNLABELED), []))
        labeled = len(words) - unl
        pct = 100 * labeled / len(words)
        lines.append(f'| {s} | {labeled} | {len(words)} | {pct:.0f}% |')
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description='Audit aggregation report.')
    parser.add_argument('--db', type=Path, default=Path('data/research.db'))
    parser.add_argument('--out-dir', type=Path, default=Path('docs/audit'))
    parser.add_argument('--list-dir', type=Path, default=Path('data/audit'))
    parser.add_argument('--date', default=date.today().isoformat(),
                        help='Date used in the report filename (default: today)')
    args = parser.parse_args()

    if not args.db.exists():
        raise SystemExit(f'No DB at {args.db}; run audit_sample.py first.')

    conn = sqlite3.connect(str(args.db))
    conn.row_factory = sqlite3.Row
    sample, labels = load_labels(conn)
    conn.close()

    if not sample:
        raise SystemExit('audit_sample is empty; run audit_sample.py first.')

    n_files = write_word_lists(labels, args.list_dir)
    md = render_markdown(sample, labels, args.date)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_file = args.out_dir / f'{args.date}-summary.md'
    out_file.write_text(md, encoding='utf-8')

    total_samples = sum(len(v) for v in sample.values())
    total_labeled = sum(len(words) for (_, lbl), words in labels.items() if lbl != UNLABELED)
    print(f'Strata:      {len(sample)}')
    print(f'Samples:     {total_samples}')
    print(f'Label events: {total_labeled}  (a word can carry multiple audit:* tags)')
    print(f'Report:      {out_file}')
    print(f'Word lists:  {n_files} files in {args.list_dir}/')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
