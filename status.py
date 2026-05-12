#!/usr/bin/env python3
"""
At-a-glance pipeline status view.

Prints a formatted, human-readable summary of:
  1. Corpus runs           — from corpus_frequencies.db.processing_stats
  2. Pipeline artifacts    — which Phase 1/2/3 output files exist + size + mtime
  3. Process liveness      — PID + log freshness for each registered loop
  4. Recent audit reports  — run_history.jsonl tail + latest quality_*.json

Read-only: no DB writes, no log writes, no state mutations.

Usage:
    python status.py
"""

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from health_check import PROCESSES, _pid_alive, LOG_TAIL
from audit import FREQ_DB, HISTORY_LOG, LOGS_DIR

REPO_ROOT     = Path(__file__).parent
PROCESSED_DIR = REPO_ROOT / 'data/processed'
ALERTS_LOG    = LOGS_DIR / 'alerts.log'

ARTIFACTS = [
    ('Phase 1',  PROCESSED_DIR / 'lexemes.db'),
    ('Phase 1',  PROCESSED_DIR / 'forgotten_words_v1.csv'),
    ('Phase 1',  PROCESSED_DIR / 'forgotten_words_curated.csv'),
    ('Phase 2a', PROCESSED_DIR / 'forgotten_words_validated_wordfreq.csv'),
    ('Phase 2b', PROCESSED_DIR / 'corpus_frequencies.db'),
    ('Phase 2b', PROCESSED_DIR / 'forgotten_words_diachronic.csv'),
    ('Phase 3',  PROCESSED_DIR / 'forgotten_words_web_validated.csv'),
]

CSV_ROW_COUNT_MAX_BYTES = 200 * 1024 * 1024  # 200 MB


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _human_size(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024 or unit == 'TB':
            return f'{n:.1f} {unit}' if unit != 'B' else f'{n} B'
        n /= 1024
    return f'{n:.1f} TB'


def _human_count(n: int) -> str:
    if n >= 1_000_000_000:
        return f'{n / 1_000_000_000:.1f}B'
    if n >= 1_000_000:
        return f'{n / 1_000_000:.1f}M'
    return f'{n:,}'


def _relative_time(ts: datetime) -> str:
    delta = datetime.now() - ts
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return 'just now'
    if seconds < 3600:
        return f'{seconds // 60}m ago'
    if seconds < 86400:
        return f'{seconds // 3600}h ago'
    return f'{seconds // 86400}d ago'


def _human_duration(seconds: float) -> str:
    s = int(seconds)
    if s < 60:
        return f'{s}s'
    if s < 3600:
        return f'{s // 60}m {s % 60}s'
    h, rem = divmod(s, 3600)
    return f'{h}h {rem // 60}m'


def _parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.split('.', 1)[0])
    except (ValueError, TypeError):
        return None


def _file_mtime(p: Path) -> datetime:
    return datetime.fromtimestamp(p.stat().st_mtime)


def _csv_row_count(p: Path) -> int | None:
    if p.suffix.lower() != '.csv' or p.stat().st_size > CSV_ROW_COUNT_MAX_BYTES:
        return None
    with open(p, 'rb') as f:
        lines = sum(1 for _ in f)
    return max(lines - 1, 0)  # minus header


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def section_header() -> list[str]:
    return [
        f'Oțios status — {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'Repo: {REPO_ROOT}',
        '',
    ]


def section_corpus_runs() -> list[str]:
    lines = ['Corpus runs']
    if not FREQ_DB.exists():
        lines.append(f'  (no DB at {FREQ_DB})')
        lines.append('')
        return lines

    conn = sqlite3.connect(FREQ_DB)
    rows = conn.execute("""
        SELECT corpus_name, documents_processed, tokens_processed,
               unique_words_found, processing_time_seconds, completed_at, status
        FROM processing_stats
        WHERE id IN (SELECT MAX(id) FROM processing_stats GROUP BY corpus_name)
        ORDER BY corpus_name
    """).fetchall()

    if not rows:
        lines.append('  (no processing_stats rows)')
        conn.close()
        lines.append('')
        return lines

    for corpus, docs, tokens, words, duration, completed_at, status in rows:
        if status != 'completed':
            words = conn.execute(
                'SELECT COUNT(DISTINCT word) FROM corpus_word_frequency WHERE corpus_name=?',
                (corpus,),
            ).fetchone()[0]

        ts_str = (completed_at or '').split(' ', 1)[0] if completed_at else '—'
        lines.append(
            f'  {corpus:14s} {status:10s} '
            f'{_human_count(docs or 0):>14s} docs  '
            f'{_human_count(tokens or 0):>8s} tokens  '
            f'{_human_count(words or 0):>8s} words  '
            f'{ts_str}'
        )

        extras = []
        if duration:
            extras.append(f'duration {_human_duration(duration)}')

        if status != 'completed':
            # checkpoint freshness
            proc = next((p for p in PROCESSES if p['corpus_name'] == corpus), None)
            if proc and proc['checkpoint'].exists():
                age = _relative_time(_file_mtime(proc['checkpoint']))
                extras.append(f'checkpoint updated {age}')

        if extras:
            lines.append(f'  {"":14s} ' + '  '.join(extras))

    conn.close()
    lines.append('')
    return lines


def section_artifacts() -> list[str]:
    lines = ['Pipeline artifacts']
    current_phase = None
    for phase, path in ARTIFACTS:
        if phase != current_phase:
            lines.append(f'  {phase}')
            current_phase = phase

        if path.exists():
            st = path.stat()
            size = _human_size(st.st_size)
            mtime = datetime.fromtimestamp(st.st_mtime)
            ts_str = mtime.strftime('%Y-%m-%d')
            rel = _relative_time(mtime)
            row_count = _csv_row_count(path)
            row_str = f'   {row_count:,} rows' if row_count is not None else ''
            lines.append(
                f'    [ok]      {path.name:42s} {size:>10s}   {rel} ({ts_str}){row_str}'
            )
        else:
            lines.append(f'    [missing] {path.name}')
    lines.append('')
    return lines


def section_liveness() -> list[str]:
    lines = ['Process liveness']
    for proc in PROCESSES:
        name = proc['name']
        pid_file = proc['pid_file']
        log_file = proc['log_file']

        if not pid_file.exists():
            lines.append(f'  {name:12s} no PID file (not running)')
            continue

        try:
            pid = int(pid_file.read_text().strip())
        except (ValueError, OSError) as e:
            lines.append(f'  {name:12s} PID file unreadable: {e}')
            continue

        alive = _pid_alive(pid)
        alive_str = f'PID {pid} alive' if alive else f'PID {pid} DEAD'

        bits = [alive_str]
        if log_file.exists():
            bits.append(f'log {_relative_time(_file_mtime(log_file))}')
            try:
                tail = log_file.read_text(errors='replace').splitlines()[-LOG_TAIL:]
                err_n = sum(
                    1 for l in tail if 'ERROR' in l or 'Traceback' in l or 'Error:' in l
                )
                bits.append(
                    f'{err_n} error line(s) in last {LOG_TAIL}'
                    if err_n else 'no recent errors'
                )
            except OSError:
                pass
        else:
            bits.append('no log file')

        lines.append(f'  {name:12s} ' + '    '.join(bits))
    lines.append('')
    return lines


def section_recent_audit() -> list[str]:
    lines = ['Recent audit']

    # run_history
    if HISTORY_LOG.exists() and HISTORY_LOG.stat().st_size > 0:
        tail_lines = HISTORY_LOG.read_text().splitlines()[-3:]
        lines.append(f'  run_history (last {len(tail_lines)}):')
        for raw in tail_lines:
            try:
                e = json.loads(raw)
                lines.append(
                    f'    {e.get("ts","?"):20s} {e.get("corpus","?"):14s} '
                    f'{e.get("status","?"):10s} '
                    f'docs={_human_count(e.get("docs") or 0):>10s}  '
                    f'words={_human_count(e.get("unique_words") or 0)}'
                )
            except (json.JSONDecodeError, ValueError):
                lines.append(f'    (unparseable line: {raw[:80]})')
    else:
        lines.append('  run_history: empty (audit hasn\'t run yet — try: python audit.py)')

    # quality
    quality_files = sorted(LOGS_DIR.glob('quality_*.json'))
    if quality_files:
        latest = quality_files[-1]
        try:
            report = json.loads(latest.read_text())
            date_str = latest.stem.replace('quality_', '')
            lines.append(f'  quality ({date_str}):')
            for corpus, data in report.get('corpora', {}).items():
                tally = {'pass': 0, 'warn': 0, 'fail': 0, 'skip': 0}
                for check in data.get('checks', {}).values():
                    if isinstance(check, dict):
                        v = check.get('verdict', 'skip')
                        tally[v] = tally.get(v, 0) + 1
                lines.append(
                    f'    {corpus:14s} {tally["pass"]} pass, '
                    f'{tally["warn"]} warn, {tally["fail"]} fail'
                    + (f', {tally["skip"]} skip' if tally['skip'] else '')
                )
            bc = report.get('both_complete', {})
            if bc:
                detail = f' — {bc["detail"]}' if bc.get('detail') else ''
                lines.append(f'    both_complete: {bc.get("verdict","?")}{detail}')
        except (json.JSONDecodeError, OSError) as e:
            lines.append(f'  quality:     unreadable {latest.name}: {e}')
    else:
        lines.append('  quality:     no reports yet')

    # alerts
    if ALERTS_LOG.exists() and ALERTS_LOG.stat().st_size > 0:
        try:
            raw = ALERTS_LOG.read_text(errors='replace').splitlines()
            # The first line of each alert is "[ts] subject"; separator is dashes.
            alert_headers = [l for l in raw if l.startswith('[') and ']' in l]
            recent = []
            cutoff = datetime.now() - timedelta(days=7)
            for h in alert_headers[-5:]:
                ts_str, _, subj = h.partition(']')
                ts = _parse_iso(ts_str.lstrip('['))
                if ts and ts >= cutoff:
                    recent.append(f'{ts.isoformat(timespec="seconds")}  {subj.strip()}')
            if recent:
                lines.append(f'  alerts (last 7d, last {len(recent)}):')
                for r in recent:
                    lines.append(f'    {r}')
            else:
                lines.append('  alerts:      none in last 7 days')
        except OSError as e:
            lines.append(f'  alerts:      unreadable: {e}')
    else:
        lines.append('  alerts:      none')

    lines.append('')
    return lines


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    out = []
    out += section_header()
    out += section_corpus_runs()
    out += section_artifacts()
    out += section_liveness()
    out += section_recent_audit()
    print('\n'.join(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
