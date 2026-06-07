# archive/

Obsolete scripts kept for reference only. **Not part of the canonical pipeline
— do not run or import these.** See `docs/BACKLOG.md` (#3).

The canonical MySQL→SQLite path is `extract_lexemes.py` (streams the DEX dump
straight into `lexemes.db`). The two scripts here were earlier, abandoned
attempts at the same job:

- **`mysql_to_sqlite.py`** — generic dump converter; `mysql_to_sqlite.py:97`
  (now relative to this file) silently swallows AUTOINCREMENT errors, so failures
  pass unnoticed. Superseded by the targeted `extract_lexemes.py`.
- **`convert_to_sqlite.sh`** — shell converter that mishandles multi-line MySQL
  directives, producing a corrupt schema.
