# Plan: Handle transient network errors in process_culturax.py

## Context

`process_culturax.py` streams 64 ~128 MB parquet shards from HuggingFace Hub's CDN via `HfFileSystem + pyarrow`. The CDN occasionally drops HTTP connections mid-transfer. This surfaces as `httpx.RemoteProtocolError: peer closed connection without sending complete message body` inside `pf.read_row_group(g)` at line 268.

The script has no error handling for this exception, so it propagates uncaught all the way to `main()` and crashes the process. The documented recovery path is an external restart loop (`while true; do python -u process_culturax.py --resume; …`), which works — but:

1. The crash is noisy (full 20-frame traceback written to stderr)
2. Up to COMMIT_EVERY-1 (≤ 4,999) in-flight doc counts are lost because the in-memory buffer was never flushed before the crash — those rows get re-processed on restart (harmless but wasteful)

HF hub's `http_backoff` does retry `ReadTimeout` automatically (visible in dump 2 for ro_part_00005), but does **not** retry `RemoteProtocolError` (connection closed after partial transfer), so that error always crashes.

## Root cause (confirmed)

`process_file` line 268: `texts = pf.read_row_group(g).column('text').to_pylist()` — no try/except. Any network failure here is fatal.

## Fix

Wrap the `read_row_group` call in a `try/except Exception`. On failure:

1. Flush the in-memory `word_counts`/`doc_counts` buffer to SQLite (saves up-to-now progress, not just last COMMIT_EVERY boundary)
2. Save checkpoint at `start_row + session_docs` (the exact row we reached)
3. Print a one-line warning with the error
4. Return `(session_docs, session_tokens, True)` — the `True` shutdown signal causes `main()` to `return 1`, which triggers the external restart loop

This keeps the restart-loop architecture intact, makes the exit clean (no traceback), and preserves more progress than the crash path.

## File to modify

**`/Users/pax/devbox/otios/process_culturax.py`** — lines 260–268 (the row-group loop, specifically the `read_row_group` call)

### Change

Replace:
```python
        for g in range(start_group, num_groups):
            if _shutdown:
                flush(conn, word_counts, doc_counts)
                cp['current_file_rows_done']   = start_row + session_docs
                cp['current_file_tokens_done'] = tokens_base + session_tokens
                save_checkpoint(cp)
                return session_docs, session_tokens, True

            texts = pf.read_row_group(g).column('text').to_pylist()
```

With:
```python
        for g in range(start_group, num_groups):
            if _shutdown:
                flush(conn, word_counts, doc_counts)
                cp['current_file_rows_done']   = start_row + session_docs
                cp['current_file_tokens_done'] = tokens_base + session_tokens
                save_checkpoint(cp)
                return session_docs, session_tokens, True

            try:
                texts = pf.read_row_group(g).column('text').to_pylist()
            except Exception as exc:
                flush(conn, word_counts, doc_counts)
                cp['current_file_rows_done']   = start_row + session_docs
                cp['current_file_tokens_done'] = tokens_base + session_tokens
                save_checkpoint(cp)
                print(f'  [{fname}] network error at group {g}: {exc}', flush=True)
                print(f'  checkpoint saved at {start_row + session_docs:,} rows — restart with --resume', flush=True)
                return session_docs, session_tokens, True
```

No new imports needed. The `flush()` and `save_checkpoint()` functions already handle the SQLite and JSON writes.

## Verification

- Run `python process_culturax.py --test` — should complete normally (no network errors expected at test scale)
- Review the change by reading lines 260–275 after editing
- Confirm the except block matches the shutdown block's structure (flush → checkpoint → print → return True)
