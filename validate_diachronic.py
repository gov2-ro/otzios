#!/usr/bin/env python3
"""
Diachronic comparison: historical (Wikisource) vs modern (CulturaX) corpus frequencies.

For each DEX candidate, computes normalized frequencies in each corpus and a log
ratio (positive = historically skewed = likely forgotten).

    log_ratio = log2( (hist_ppm + S) / (modern_ppm + S) )

where S = smoothing constant (default 0.1 per million), hist_ppm / modern_ppm are
occurrences per million tokens in each corpus.

Verdicts:
  extinct          hist_ppm >= 1.0  AND  modern_ppm < 0.1
  declining        log_ratio >= 1.0 (at least 2× more historical than modern)
  stable           |log_ratio| < 1.0
  emerging         log_ratio <= -1.0 (at least 2× more modern)
  historical_only  hist_ppm >= 0.1  AND  modern_ppm < 0.1  (corpus run may be partial)
  modern_only      modern_ppm >= 0.1 AND  hist_ppm < 0.1
  absent           both < 0.1 (no corpus signal — run may be partial)

Usage:
    python validate_diachronic.py               # curated candidates only
    python validate_diachronic.py --all-dex     # every DEX word in either corpus
    python validate_diachronic.py --smoothing 0.5 --output path/out.csv
    python validate_diachronic.py --top 30      # print top-30 in summary

Requires that at least one of process_wikisource.py / process_culturax.py has been run.
"""

import argparse
import csv
import math
import sqlite3
import unicodedata
from pathlib import Path

LEXEMES_DB  = Path('data/processed/lexemes.db')
FREQ_DB     = Path('data/processed/corpus_frequencies.db')
CURATED_CSV = Path('data/processed/forgotten_words_curated.csv')
OUTPUT_CSV  = Path('data/processed/forgotten_words_diachronic.csv')

HIST_CORPUS   = 'wikisource_ro'
MODERN_CORPUS = 'culturax_ro'

SMOOTHING = 0.1   # per-million tokens; floor for log ratio

RARITY_BINS = [(0.30, 'very_rare'), (0.50, 'rare'), (1.01, 'uncommon')]


def normalize(text: str) -> str:
    return unicodedata.normalize('NFC',
        text.lower().replace('ş', 'ș').replace('ţ', 'ț'))


def rarity_category(freq: float) -> str:
    for ceiling, label in RARITY_BINS:
        if freq < ceiling:
            return label
    return 'uncommon'


def get_corpus_tokens(conn: sqlite3.Connection, corpus_name: str) -> int:
    """Return total tokens for the most complete run of a corpus."""
    row = conn.execute("""
        SELECT tokens_processed
        FROM processing_stats
        WHERE corpus_name = ? AND status = 'completed'
        ORDER BY documents_processed DESC, completed_at DESC
        LIMIT 1
    """, (corpus_name,)).fetchone()
    return row[0] if row else 0


def load_dex_candidates(lexemes_db: Path, curated_only: bool,
                        curated_csv: Path) -> dict[str, dict]:
    """Return {normalized_word: {dex_frequency, description, rarity_category}}."""
    if curated_only:
        if not curated_csv.exists():
            raise FileNotFoundError(f'Curated list not found: {curated_csv}')
        candidates: dict[str, dict] = {}
        with curated_csv.open(encoding='utf-8') as f:
            for row in csv.DictReader(f):
                w = normalize(row.get('word_no_accent') or row.get('word', ''))
                if not w:
                    continue
                candidates[w] = {
                    'dex_frequency': float(row.get('frequency') or 0),
                    'description': row.get('description', ''),
                    'rarity_category': row.get('rarity_category', ''),
                }
        return candidates

    conn = sqlite3.connect(lexemes_db)
    rows = conn.execute("""
        SELECT DISTINCT lower(formNoAccent), frequency, description
        FROM Lexeme
        WHERE frequency > 0.01
          AND LENGTH(formNoAccent) > 2
          AND description != ''
          AND description IS NOT NULL
    """).fetchall()
    conn.close()
    out = {}
    for r in rows:
        w = normalize(r[0])
        if not w:
            continue
        freq = float(r[1]) if r[1] not in (None, '') else 0.0
        out[w] = {
            'dex_frequency': freq,
            'description': r[2] or '',
            'rarity_category': rarity_category(freq),
        }
    return out


def load_corpus_freqs(conn: sqlite3.Connection,
                      corpus_name: str) -> dict[str, tuple[int, int]]:
    """Return {word: (occurrence_count, document_count)} for one corpus."""
    rows = conn.execute("""
        SELECT word, occurrence_count, document_count
        FROM corpus_word_frequency
        WHERE corpus_name = ?
    """, (corpus_name,)).fetchall()
    return {r[0]: (r[1], r[2]) for r in rows}


def load_taxonomy(lexemes_db: Path) -> dict:
    """Return {word_lower: {register, domain, etymology, pos}} from Tag/ObjectTag/EntryLexeme.
    Returns empty dict with a warning if tables are absent (run extract_taxonomy.py first)."""
    conn = sqlite3.connect(lexemes_db)
    try:
        rows = conn.execute("""
            SELECT lower(l.formNoAccent), t.parentId, t.isPos, t.value
            FROM Lexeme l
            JOIN EntryLexeme el ON el.lexemeId = l.id
            JOIN ObjectTag ot ON ot.objectId = el.entryId AND ot.objectType = 3
            JOIN Tag t ON t.id = ot.tagId
            WHERE t.parentId IN (1, 41, 42) OR t.isPos = 1
        """).fetchall()
    except sqlite3.OperationalError:
        print("  [taxonomy] Tag tables not found — run extract_taxonomy.py to enable taxonomy columns")
        return {}
    finally:
        conn.close()

    parent_to_family = {1: 'etymology', 41: 'domain', 42: 'register'}
    taxonomy: dict = {}
    for word, parent_id, is_pos, tag_value in rows:
        entry = taxonomy.setdefault(word, {'register': set(), 'domain': set(), 'etymology': set(), 'pos': set()})
        if is_pos:
            entry['pos'].add(tag_value)
        else:
            family = parent_to_family.get(parent_id)
            if family:
                entry[family].add(tag_value)
    return taxonomy


def verdict(hist_ppm: float, modern_ppm: float, log_ratio: float) -> str:
    if hist_ppm >= 1.0 and modern_ppm < 0.1:
        return 'extinct'
    if hist_ppm >= 0.1 and modern_ppm < 0.1:
        return 'historical_only'
    if modern_ppm >= 0.1 and hist_ppm < 0.1:
        return 'modern_only'
    if hist_ppm < 0.1 and modern_ppm < 0.1:
        return 'absent'
    if log_ratio >= 1.0:
        return 'declining'
    if log_ratio <= -1.0:
        return 'emerging'
    return 'stable'


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Diachronic comparison: Wikisource vs CulturaX frequency ratio.')
    parser.add_argument('--all-dex', action='store_true',
                        help='Include all DEX words (default: curated candidates only)')
    parser.add_argument('--smoothing', type=float, default=SMOOTHING,
                        help=f'Per-million smoothing for log ratio (default: {SMOOTHING})')
    parser.add_argument('-o', '--output', type=Path, default=OUTPUT_CSV)
    parser.add_argument('--top', type=int, default=20,
                        help='Print top N historically-skewed words in summary')
    args = parser.parse_args()

    for p, label in [(LEXEMES_DB, 'lexemes.db'), (FREQ_DB, 'corpus_frequencies.db')]:
        if not p.exists():
            print(f'Missing: {p}  — run the Phase 1 and corpus pipeline first.')
            return 1

    freq_conn = sqlite3.connect(FREQ_DB)

    hist_tokens   = get_corpus_tokens(freq_conn, HIST_CORPUS)
    modern_tokens = get_corpus_tokens(freq_conn, MODERN_CORPUS)

    if hist_tokens == 0 and modern_tokens == 0:
        print('No completed corpus runs found in corpus_frequencies.db.')
        print(f'  Run process_wikisource.py and/or process_culturax.py first.')
        freq_conn.close()
        return 1

    print(f'Corpus sizes:')
    if hist_tokens:
        print(f'  {HIST_CORPUS:<20} {hist_tokens:>15,} tokens')
    else:
        print(f'  {HIST_CORPUS:<20}  (no completed run)')
    if modern_tokens:
        print(f'  {MODERN_CORPUS:<20} {modern_tokens:>15,} tokens')
    else:
        print(f'  {MODERN_CORPUS:<20}  (no completed run)')

    curated_only = not args.all_dex
    print(f'\nLoading DEX candidates ({"curated list" if curated_only else "all DEX"})...')
    try:
        candidates = load_dex_candidates(LEXEMES_DB, curated_only, CURATED_CSV)
    except FileNotFoundError as e:
        print(e)
        return 1
    print(f'  {len(candidates):,} words')

    print('Loading corpus frequencies...')
    hist_freqs   = load_corpus_freqs(freq_conn, HIST_CORPUS)   if hist_tokens   else {}
    modern_freqs = load_corpus_freqs(freq_conn, MODERN_CORPUS) if modern_tokens else {}
    freq_conn.close()

    print('Loading DEX taxonomy...')
    taxonomy = load_taxonomy(LEXEMES_DB)
    print(f'  {len(taxonomy):,} words with taxonomy tags')

    # Restrict to candidates that appear in at least one corpus (unless --all-dex)
    if args.all_dex:
        universe = candidates.keys() | hist_freqs.keys() | modern_freqs.keys()
    else:
        universe = candidates.keys()

    S = args.smoothing
    hist_scale   = 1_000_000 / hist_tokens   if hist_tokens   else 0.0
    modern_scale = 1_000_000 / modern_tokens if modern_tokens else 0.0

    results = []
    for word in universe:
        meta = candidates.get(word, {'dex_frequency': 0.0, 'description': '', 'rarity_category': ''})

        h_occ, h_doc = hist_freqs.get(word,   (0, 0))
        m_occ, m_doc = modern_freqs.get(word, (0, 0))

        hist_ppm   = h_occ * hist_scale   if hist_scale   else 0.0
        modern_ppm = m_occ * modern_scale if modern_scale else 0.0

        log_ratio = math.log2((hist_ppm + S) / (modern_ppm + S))

        tax = taxonomy.get(word, {})
        results.append({
            'word':             word,
            'dex_frequency':    f"{meta['dex_frequency']:.4f}",
            'description':      meta['description'],
            'rarity_category':  meta['rarity_category'],
            'hist_occurrences': h_occ,
            'hist_documents':   h_doc,
            'hist_ppm':         f'{hist_ppm:.4f}',
            'modern_occurrences': m_occ,
            'modern_documents':   m_doc,
            'modern_ppm':       f'{modern_ppm:.4f}',
            'log_ratio':        f'{log_ratio:.4f}',
            'verdict':          verdict(hist_ppm, modern_ppm, log_ratio),
            'dex_pos':          '|'.join(sorted(tax.get('pos',       set()))),
            'dex_register':     '|'.join(sorted(tax.get('register',  set()))),
            'dex_domain':       '|'.join(sorted(tax.get('domain',    set()))),
            'dex_etymology':    '|'.join(sorted(tax.get('etymology', set()))),
        })

    results.sort(key=lambda r: float(r['log_ratio']), reverse=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        'word', 'dex_frequency', 'description', 'rarity_category',
        'hist_occurrences', 'hist_documents', 'hist_ppm',
        'modern_occurrences', 'modern_documents', 'modern_ppm',
        'log_ratio', 'verdict',
        'dex_pos', 'dex_register', 'dex_domain', 'dex_etymology',
    ]
    with args.output.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    print(f'\nWrote {len(results):,} rows → {args.output}')

    # Verdict summary
    from collections import Counter
    counts = Counter(r['verdict'] for r in results)
    print('\nVerdict breakdown:')
    for v in ('extinct', 'declining', 'historical_only', 'stable',
              'modern_only', 'emerging', 'absent'):
        n = counts.get(v, 0)
        if n:
            print(f'  {v:<20} {n:>6,}')

    # Top N most historically-skewed
    top = [r for r in results if float(r['hist_ppm']) > 0][:args.top]
    if top:
        print(f'\nTop {len(top)} historically-skewed (highest log_ratio, hist_ppm > 0):')
        print(f'  {"word":<22} {"log_ratio":>10} {"hist_ppm":>10} {"modern_ppm":>11}  verdict')
        for r in top:
            print(f'  {r["word"]:<22} {float(r["log_ratio"]):>10.2f} '
                  f'{float(r["hist_ppm"]):>10.4f} {float(r["modern_ppm"]):>11.4f}  {r["verdict"]}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
