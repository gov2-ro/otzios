#!/usr/bin/env python3
"""
Monitor long-running corpus scripts and alert on problems.

Checks performed for each registered process (culturax, wikisource):
  - PID alive       — loop PID file exists but process is dead
  - Progress stall  — checkpoint file not updated in > STALL_HOURS while PID is alive
  - Log errors      — last LOG_TAIL lines of the log contain ERROR or Traceback
  - Completion      — processing_stats shows status='completed' (one-time success alert)
  - DB accessible   — can open corpus_frequencies.db

Alerts fire only on state *transitions* to avoid cron spam.
State is persisted in data/logs/health_status.json.

Alerting backends (configure via env vars):
  OTZIOS_ALERT_URL    — HTTP POST plain-text body (ntfy.sh, Slack/Discord webhooks, etc.)
  OTZIOS_ALERT_EMAIL  — recipient address, sent via system `mail` command

Both can be set simultaneously. All alerts always append to data/logs/alerts.log.

Usage:
    python health_check.py              # run all checks
    python health_check.py --dry-run    # print what would be alerted, no side effects
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT    = Path(__file__).parent
FREQ_DB      = REPO_ROOT / 'data/processed/corpus_frequencies.db'
LOGS_DIR     = REPO_ROOT / 'data/logs'
STATUS_FILE  = LOGS_DIR / 'health_status.json'
ALERTS_LOG   = LOGS_DIR / 'alerts.log'

STALL_HOURS  = 2      # hours without checkpoint update before "stalled" alert
LOG_TAIL     = 100    # lines to scan for errors

PROCESSES = [
    {
        'name':       'culturax',
        'pid_file':   LOGS_DIR / 'culturax.pid',
        'log_file':   LOGS_DIR / 'culturax.log',
        'checkpoint': REPO_ROOT / 'data/processed/culturax_checkpoint.json',
        'corpus_name': 'culturax_ro',
    },
    {
        'name':       'wikisource',
        'pid_file':   LOGS_DIR / 'wikisource.pid',
        'log_file':   LOGS_DIR / 'wikisource.log',
        'checkpoint': REPO_ROOT / 'data/processed/wikisource_checkpoint.json',
        'corpus_name': 'wikisource_ro',
    },
]


# ---------------------------------------------------------------------------
# Alerting
# ---------------------------------------------------------------------------

def _alert(subject: str, body: str, dry_run: bool = False) -> None:
    ts  = datetime.now().isoformat(timespec='seconds')
    msg = f'[{ts}] {subject}\n{body}'.strip()

    if dry_run:
        print(f'[DRY-RUN] ALERT: {subject}')
        print(body)
        return

    # Always log
    with open(ALERTS_LOG, 'a') as f:
        f.write(msg + '\n' + '-' * 60 + '\n')

    url = os.environ.get('OTZIOS_ALERT_URL')
    if url:
        try:
            import urllib.request
            req = urllib.request.Request(
                url,
                data=msg.encode(),
                headers={'Content-Type': 'text/plain'},
                method='POST',
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f'Warning: alert POST failed: {e}', file=sys.stderr)

    email = os.environ.get('OTZIOS_ALERT_EMAIL')
    if email:
        try:
            subprocess.run(
                ['mail', '-s', f'[otzios] {subject}', email],
                input=body.encode(),
                timeout=10,
                check=False,
            )
        except Exception as e:
            print(f'Warning: alert email failed: {e}', file=sys.stderr)


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def _load_status() -> dict:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text())
        except (json.JSONDecodeError, ValueError):
            pass
    return {}


def _save_status(status: dict) -> None:
    STATUS_FILE.write_text(json.dumps(status, indent=2))


def _process_state(status: dict, name: str) -> dict:
    if name not in status:
        status[name] = {
            'loop_died_alerted_at':  None,
            'stall_alerted_at':      None,
            'error_alerted_at':      None,
            'completed_alerted_at':  None,
            'last_check':            None,
        }
    return status[name]


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def check_process(proc: dict, status: dict, dry_run: bool) -> list[str]:
    name      = proc['name']
    pid_file  = proc['pid_file']
    log_file  = proc['log_file']
    ckpt      = proc['checkpoint']
    corpus    = proc['corpus_name']
    state     = _process_state(status, name)
    issues    = []
    now       = datetime.now()

    state['last_check'] = now.isoformat(timespec='seconds')

    # Skip entirely if PID file doesn't exist (process was never started)
    if not pid_file.exists():
        return issues

    pid = int(pid_file.read_text().strip())
    alive = _pid_alive(pid)

    # 1. Loop liveness
    if not alive:
        if state['loop_died_alerted_at'] is None:
            _alert(
                f'{name} loop died',
                f'PID {pid} from {pid_file} is no longer running.\n'
                f'Restart with the loop command in CLAUDE.md.',
                dry_run,
            )
            state['loop_died_alerted_at'] = now.isoformat(timespec='seconds')
            issues.append('loop_died')
    else:
        # Process is alive — clear the died-alert so it fires again if it dies later
        state['loop_died_alerted_at'] = None

        # 2. Progress stall
        if ckpt.exists():
            age = now - datetime.fromtimestamp(ckpt.stat().st_mtime)
            if age > timedelta(hours=STALL_HOURS):
                if state['stall_alerted_at'] is None:
                    _alert(
                        f'{name} stalled',
                        f'Checkpoint {ckpt.name} last updated {age} ago (PID {pid} is alive).\n'
                        f'Check {log_file} for errors.',
                        dry_run,
                    )
                    state['stall_alerted_at'] = now.isoformat(timespec='seconds')
                    issues.append('stall')
            else:
                state['stall_alerted_at'] = None

    # 3. Log error scan (regardless of alive state — errors may be in log before death)
    if log_file.exists():
        try:
            lines = log_file.read_text(errors='replace').splitlines()[-LOG_TAIL:]
            error_lines = [l for l in lines if 'ERROR' in l or 'Traceback' in l or 'Error:' in l]
            if error_lines and state['error_alerted_at'] is None:
                excerpt = '\n'.join(error_lines[:10])
                _alert(
                    f'{name} log errors detected',
                    f'Found {len(error_lines)} error line(s) in last {LOG_TAIL} log lines:\n\n{excerpt}',
                    dry_run,
                )
                state['error_alerted_at'] = now.isoformat(timespec='seconds')
                issues.append('log_errors')
            elif not error_lines:
                state['error_alerted_at'] = None
        except OSError:
            pass

    # 4. Completion check (DB)
    if state['completed_alerted_at'] is None and FREQ_DB.exists():
        try:
            conn = sqlite3.connect(FREQ_DB)
            row = conn.execute(
                "SELECT documents_processed, tokens_processed, completed_at "
                "FROM processing_stats WHERE corpus_name=? AND status='completed' "
                "ORDER BY completed_at DESC LIMIT 1",
                (corpus,),
            ).fetchone()
            conn.close()
            if row:
                docs, tokens, completed_at = row
                _alert(
                    f'{name} completed ✓',
                    f'corpus_name={corpus}\ndocs={docs:,}  tokens={tokens:,}\ncompleted_at={completed_at}',
                    dry_run,
                )
                state['completed_alerted_at'] = now.isoformat(timespec='seconds')
                issues.append('completed')
        except sqlite3.Error as e:
            _alert('DB unreadable', str(e), dry_run)
            issues.append('db_error')

    return issues


def check_db(status: dict, dry_run: bool) -> None:
    if not FREQ_DB.exists():
        return
    try:
        conn = sqlite3.connect(FREQ_DB)
        conn.execute("SELECT COUNT(*) FROM corpus_word_frequency LIMIT 1")
        conn.close()
    except sqlite3.Error as e:
        _alert('DB unreadable', f'{FREQ_DB}: {e}', dry_run)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true',
                        help='Print alerts without sending or writing state')
    args = parser.parse_args()

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    status = _load_status()
    all_issues = []

    check_db(status, args.dry_run)

    for proc in PROCESSES:
        issues = check_process(proc, status, args.dry_run)
        all_issues.extend(issues)
        name = proc['name']
        state = status.get(name, {})
        print(f'{name}: {", ".join(issues) if issues else "ok"}'
              f'  (last_check={state.get("last_check", "-")})')

    if not args.dry_run:
        _save_status(status)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
