#!/usr/bin/env python3
"""
Audit corpus pipeline state: run history snapshot + data quality checks.

Part A — Run history:
  Reads corpus_frequencies.db and appends one JSON line per corpus to
  data/logs/run_history.jsonl. Safe to run repeatedly (appends, doesn't overwrite).

Part B — Quality checks:
  For each corpus in the DB, verifies counts are internally consistent.
  Writes a dated report to data/logs/quality_YYYY-MM-DD.json.
  If any check fails, sends an alert via health_check._alert().

Quality checks:
  no_cycling     — MAX(document_count) ≤ docs_processed for that corpus
  positive_counts — all occurrence_count > 0
  token_ratio    — avg tokens/doc between 50 and 2000
  word_coverage  — unique words ≥ 5,000 (if corpus is complete)
  both_complete  — both corpora have status='completed' (warns, not fails)

Usage:
    python audit.py              # full audit
    python audit.py --dry-run    # print report without writing files or alerting
"""

import argparse
import json
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

REPO_ROOT   = Path(__file__).parent
FREQ_DB     = REPO_ROOT / 'data/processed/corpus_frequencies.db'
LOGS_DIR    = REPO_ROOT / 'data/logs'
HISTORY_LOG = LOGS_DIR / 'run_history.jsonl'

EXPECTED_CORPORA = ['wikisource_ro', 'culturax_ro']
MIN_UNIQUE_WORDS = 5_000
TOKEN_RATIO_MIN  = 50
TOKEN_RATIO_MAX  = 2_000


def _alert(subject: str, body: str, dry_run: bool = False) -> None:
    # Re-use health_check's alert logic without importing the whole module
    from health_check import _alert as hc_alert
    hc_alert(subject, body, dry_run)


# ---------------------------------------------------------------------------
# Part A — Run history
# ---------------------------------------------------------------------------

def snapshot_run_history(conn: sqlite3.Connection, dry_run: bool) -> list[dict]:
    rows = conn.execute("""
        SELECT corpus_name, documents_processed, tokens_processed,
               unique_words_found, status, completed_at
        FROM processing_stats
        ORDER BY corpus_name, id DESC
    """).fetchall()

    # One entry per corpus: latest status
    seen = set()
    entries = []
    for corpus, docs, tokens, words, status, completed_at in rows:
        if corpus in seen:
            continue
        seen.add(corpus)

        # Live doc count from checkpoint if still in progress
        live_docs = docs
        if status != 'completed':
            wf_count = conn.execute(
                "SELECT COUNT(DISTINCT word) FROM corpus_word_frequency WHERE corpus_name=?",
                (corpus,)
            ).fetchone()[0]
        else:
            wf_count = words or 0

        entry = {
            'ts':           datetime.now().isoformat(timespec='seconds'),
            'corpus':       corpus,
            'status':       status,
            'docs':         live_docs,
            'tokens':       tokens,
            'unique_words': wf_count,
            'completed_at': completed_at,
        }
        entries.append(entry)

    if not dry_run and entries:
        with open(HISTORY_LOG, 'a') as f:
            for e in entries:
                f.write(json.dumps(e) + '\n')

    return entries


# ---------------------------------------------------------------------------
# Part B — Quality checks
# ---------------------------------------------------------------------------

def quality_checks(conn: sqlite3.Connection) -> dict:
    corpora = [r[0] for r in conn.execute(
        "SELECT DISTINCT corpus_name FROM corpus_word_frequency"
    ).fetchall()]

    report = {'checked_at': datetime.now().isoformat(timespec='seconds'), 'corpora': {}}

    for corpus in corpora:
        checks  = {}
        stats   = conn.execute(
            "SELECT documents_processed, tokens_processed, status "
            "FROM processing_stats WHERE corpus_name=? ORDER BY id DESC LIMIT 1",
            (corpus,),
        ).fetchone()
        docs_processed = stats[0] if stats else None
        tokens_proc    = stats[1] if stats else None
        status         = stats[2] if stats else 'unknown'

        # no_cycling: max document_count per word must not exceed total docs in corpus
        max_doc_count = conn.execute(
            "SELECT MAX(document_count) FROM corpus_word_frequency WHERE corpus_name=?",
            (corpus,),
        ).fetchone()[0] or 0

        if docs_processed and max_doc_count > docs_processed:
            checks['no_cycling'] = {
                'verdict': 'fail',
                'detail':  f'MAX(document_count)={max_doc_count:,} > docs_processed={docs_processed:,}',
            }
        else:
            checks['no_cycling'] = {'verdict': 'pass'}

        # positive_counts: no word should have occurrence_count <= 0
        zero_count = conn.execute(
            "SELECT COUNT(*) FROM corpus_word_frequency "
            "WHERE corpus_name=? AND occurrence_count <= 0",
            (corpus,),
        ).fetchone()[0]
        checks['positive_counts'] = {
            'verdict': 'fail' if zero_count else 'pass',
            'detail':  f'{zero_count} words with occurrence_count ≤ 0' if zero_count else None,
        }

        # token_ratio: avg tokens per doc
        if docs_processed and docs_processed > 0 and tokens_proc:
            ratio = tokens_proc / docs_processed
            if ratio < TOKEN_RATIO_MIN or ratio > TOKEN_RATIO_MAX:
                checks['token_ratio'] = {
                    'verdict': 'warn',
                    'detail':  f'avg tokens/doc={ratio:.1f} (expected {TOKEN_RATIO_MIN}–{TOKEN_RATIO_MAX})',
                }
            else:
                checks['token_ratio'] = {'verdict': 'pass', 'detail': f'{ratio:.1f} tokens/doc'}
        else:
            checks['token_ratio'] = {'verdict': 'skip', 'detail': 'no processing_stats row'}

        # word_coverage: only meaningful if completed
        if status == 'completed':
            unique = conn.execute(
                "SELECT COUNT(DISTINCT word) FROM corpus_word_frequency WHERE corpus_name=?",
                (corpus,),
            ).fetchone()[0]
            checks['word_coverage'] = {
                'verdict': 'fail' if unique < MIN_UNIQUE_WORDS else 'pass',
                'detail':  f'{unique:,} unique words (min {MIN_UNIQUE_WORDS:,})',
            }

        report['corpora'][corpus] = {'status': status, 'checks': checks}

    # both_complete check
    completed = {
        c for c in corpora
        if conn.execute(
            "SELECT 1 FROM processing_stats WHERE corpus_name=? AND status='completed'",
            (c,)
        ).fetchone()
    }
    missing = set(EXPECTED_CORPORA) - completed
    report['both_complete'] = {
        'verdict': 'pass' if not missing else 'warn',
        'detail':  f'not yet complete: {sorted(missing)}' if missing else None,
    }

    return report


def _has_failures(report: dict) -> bool:
    for corpus_data in report.get('corpora', {}).values():
        for check in corpus_data.get('checks', {}).values():
            if isinstance(check, dict) and check.get('verdict') == 'fail':
                return True
    return False


def _report_summary(report: dict) -> str:
    lines = [f"Audit {report['checked_at']}"]
    for corpus, data in report.get('corpora', {}).items():
        lines.append(f'\n  {corpus} [{data["status"]}]')
        for check, result in data.get('checks', {}).items():
            verdict = result.get('verdict', '?')
            detail  = result.get('detail', '')
            lines.append(f'    {verdict:5s}  {check}' + (f': {detail}' if detail else ''))
    bc = report.get('both_complete', {})
    lines.append(f'\n  both_complete: {bc.get("verdict")}' +
                 (f' — {bc["detail"]}' if bc.get('detail') else ''))
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true',
                        help='Print report without writing files or alerting')
    args = parser.parse_args()

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    if not FREQ_DB.exists():
        print(f'DB not found: {FREQ_DB}', file=sys.stderr)
        return 1

    conn = sqlite3.connect(FREQ_DB)

    # Part A
    entries = snapshot_run_history(conn, args.dry_run)
    print('Run history snapshot:')
    for e in entries:
        print(f'  {e["corpus"]:20s} {e["status"]:12s} '
              f'docs={e["docs"] or 0:>12,}  words={e["unique_words"]:>6,}')
    if not args.dry_run and entries:
        print(f'  → appended {len(entries)} line(s) to {HISTORY_LOG}')

    # Part B
    report   = quality_checks(conn)
    conn.close()
    summary  = _report_summary(report)
    print(f'\n{summary}')

    quality_file = LOGS_DIR / f'quality_{date.today()}.json'
    if not args.dry_run:
        quality_file.write_text(json.dumps(report, indent=2))
        print(f'\n→ {quality_file}')

    if _has_failures(report):
        _alert('Audit quality failures', summary, args.dry_run)
        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
