# Oțios: Infra Improvements Plan

## Context

The project has two long-running scripts (`process_culturax.py`, `process_wikisource.py`) that run as looped background processes on a VPS. Right now there is no structured way to know if they are alive, making progress, or silently stuck. Logs and PIDs live in a shared `~/g2-dev/logs/` directory outside the project. There is no venv in-project. This plan tidies those up and adds a lightweight monitoring layer.

User answers:
- **Alerting**: abstract endpoint (URL/email TBD) — keep pluggable
- **Audit**: both run-history log and DB quality checks
- **Logs**: move to `data/logs/` (already gitignored by `data/*`)
- **Venv**: migrate after the current culturax run finishes

---

## Work items (ordered by dependency)

### 1. Log migration — `data/logs/`

**What changes:**
- Create `data/logs/.gitkeep` and add `!data/logs/.gitkeep` to `.gitignore` so the directory is committed.
- Update CLAUDE.md `## Logs` section: change path from `~/g2-dev/logs/` to `data/logs/` inside the repo.
- Update `readme.md` restart loop commands to point logs and PIDs at `data/logs/`.
- `process_culturax.py` and `process_wikisource.py` don't hardcode log paths (they're set in the shell loop), so no Python changes needed there — just documentation and the next loop invocations.

**Files touched:** `.gitignore`, `CLAUDE.md`, `readme.md`

---

### 2. `health_check.py` — process liveness + stall detection + alerting

Single script, runs as a cron every 30 minutes. Checks each long-running process and alerts once per new problem (state tracked in `data/logs/health_status.json` so repeat cron fires don't spam).

**Checks:**
| Check | Trigger |
|---|---|
| Loop PID alive | `data/logs/culturax.pid` exists but PID is dead → alert "culturax loop died" |
| Progress not stalled | checkpoint mtime > 2 h old while PID is alive → alert "culturax stalled" |
| Log errors | last 100 lines of `data/logs/culturax.log` contain `ERROR` or `Traceback` → alert with excerpt |
| Corpus completed | `processing_stats` row with `status='completed'` just appeared → alert "culturax done ✓" |
| DB accessible | SQLite connection fails → alert "DB unreadable" |

Same checks repeated for `wikisource` if its PID file exists.

**Alerting backend (`_alert(subject, body)`):**
- Always appends to `data/logs/alerts.log`
- If `OTZIOS_ALERT_URL` env var set: HTTP POST the message (plain text body → works with ntfy.sh, Discord, Slack webhooks, custom endpoints)
- If `OTZIOS_ALERT_EMAIL` env var set: sends via system `mail` command
- Both can be set simultaneously

**State file** `data/logs/health_status.json`:
```json
{
  "culturax": {
    "loop_died_alerted_at": null,
    "stall_alerted_at": null,
    "completed_alerted_at": null,
    "last_check": "2026-05-12T13:00:00"
  }
}
```
Alert is only fired when a state *transitions* (dead→alive suppresses further dead alerts; completing once sets `completed_alerted_at` permanently).

**File:** `health_check.py` (new, ~150 lines)

---

### 3. `audit.py` — run history + DB quality checks

Meant to be run once daily (cron) or manually after a corpus run completes.

**Part A — run history log:**
- Reads `corpus_word_frequency` and `processing_stats` from `corpus_frequencies.db`
- Appends one JSON line per corpus to `data/logs/run_history.jsonl`:
  ```json
  {"ts": "2026-05-12T14:00:00", "corpus": "culturax_ro", "status": "in_progress",
   "docs": 1200000, "tokens": 506000000, "unique_words": 10234}
  ```

**Part B — data quality checks:**
Each check emits a pass/warn/fail verdict:

| Check | Condition |
|---|---|
| No cycling | `MAX(document_count) ≤ docs_processed` for that corpus |
| Positive counts | All `occurrence_count > 0` (should always hold given UPSERT logic) |
| Expected corpora | Both `wikisource_ro` and `culturax_ro` rows exist when status = completed |
| Token ratio sanity | `tokens / docs` between 50 and 2000 (plausible average doc length) |
| Word coverage | Unique words found ≥ 5,000 (sanity floor) |

Writes `data/logs/quality_YYYY-MM-DD.json`. If any check is `fail`, calls `_alert()` with the summary.

**File:** `audit.py` (new, ~120 lines)

---

### 4. Cron setup

Two crontab entries to add to the VPS (documented in CLAUDE.md):

```cron
# Otzios health check every 30 minutes
*/30 * * * * cd /home/pax/g2-dev/otzios && /home/pax/g2-dev/monitorulpreturilor/venv/bin/python health_check.py >> data/logs/health_check.log 2>&1

# Otzios daily audit at 02:00
0 2 * * * cd /home/pax/g2-dev/otzios && /home/pax/g2-dev/monitorulpreturilor/venv/bin/python audit.py >> data/logs/audit.log 2>&1
```

(Venv path will be updated to `.venv/bin/python` once the venv migration happens.)
Document the cron lines in CLAUDE.md under a new `## Monitoring` section.

---

### 5. Venv migration (deferred — after culturax finishes)

Steps (documented here so they're not forgotten):
1. `python -m venv .venv` in project root
2. `source .venv/bin/activate && pip install -r requirements.txt`
3. Add `.venv/` to `.gitignore`
4. Update CLAUDE.md environment section
5. Update readme.md quick-start
6. Restart any loops using the new path: `.venv/bin/python`

This is **not implemented now** — only the documentation note above.

---

## Files to create / modify

| File | Action |
|---|---|
| `health_check.py` | Create |
| `audit.py` | Create |
| `data/logs/.gitkeep` | Create |
| `.gitignore` | Add `!data/logs/.gitkeep` |
| `CLAUDE.md` | Update `## Logs`, add `## Monitoring` section |
| `readme.md` | Update restart loop log paths; mention monitoring |
| `docs/activity-history.md` | Add entry |

## Verification

- `python health_check.py` with no env vars set: should complete without error, write `data/logs/health_status.json`, append to `data/logs/alerts.log`
- `python audit.py`: should write `data/logs/run_history.jsonl` and a `data/logs/quality_YYYY-MM-DD.json`
- Manually kill the culturax PID, run `health_check.py`: should write an alert to `alerts.log`
- `crontab -l` to confirm entries are installed
