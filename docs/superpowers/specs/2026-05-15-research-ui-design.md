# Oțios Research UI — Design Spec

> **Status:** Approved for implementation (2026-05-15)

## Context

The pipeline produces a ~16,880-word shortlist (`forgotten_words_shortlist.csv`) plus a ~49-word web-validated set (`diachronic_shortlist_web_validated.csv`). Until now, exploration means running pandas one-offs or grepping CSVs. The goal is a fast, keyboard-driven local web app that lets you search/filter the shortlist, drill into individual word records, and bookmark words with optional notes and tags — supporting the research phase of deciding which words are genuinely "forgotten."

---

## Stack

- **Flask** (Python) — one file `ui/app.py`
- **HTMX 2.x** (CDN) — server-rendered fragments, no build step
- **Jinja2** (bundled with Flask) — templates in `ui/templates/`
- **SQLite** — two databases:
  - in-memory `words` table (rebuilt from CSVs each startup)
  - file-backed `data/research.db` (`bookmarks` table, persists restarts)

No npm, no build toolchain. Run with `python ui/app.py`.

---

## Data model

```sql
-- in-memory, rebuilt at startup from both CSVs merged on `word`
CREATE TABLE words (
  word             TEXT PRIMARY KEY,
  dex_frequency    REAL,
  verdict          TEXT,
  confidence_tier  TEXT,
  log_ratio        REAL,
  hist_ppm         REAL,
  modern_ppm       REAL,
  dex_pos          TEXT,
  dex_register     TEXT,
  dex_domain       TEXT,
  dex_etymology    TEXT,
  is_forgotten     INTEGER,
  -- web validation columns (NULL if word not yet web-validated)
  total_results    INTEGER,
  in_wild          INTEGER,
  web_score        INTEGER,
  top_url          TEXT,
  last_seen_approx TEXT,
  provider         TEXT
);

-- file-backed: data/research.db
CREATE TABLE bookmarks (
  word        TEXT PRIMARY KEY,
  bookmarked  INTEGER DEFAULT 0,
  note        TEXT    DEFAULT '',
  tags        TEXT    DEFAULT '',  -- comma-separated
  created_at  TEXT,
  updated_at  TEXT
);
```

---

## Routes

| Method | Path | Returns | Notes |
|--------|------|---------|-------|
| GET | `/` | Full page | Shell layout only |
| GET | `/search` | `#word-list` fragment | params: `q`, `verdict`, `tier`, `bookmarked`, `page` |
| GET | `/word/<word>` | `#detail-panel` fragment | Full word detail |
| POST | `/bookmark/<word>` | `#bookmark-btn` fragment | Toggle bookmark |
| POST | `/note/<word>` | `#note-status` fragment | Save note text |
| POST | `/tag/<word>` | `#tags-row` fragment | Add tag |
| DELETE | `/tag/<word>/<tag>` | `#tags-row` fragment | Remove tag |

---

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [/] Search...   [verdict ▾]  [tier ▾]  [☆ bookmarked]     │
├───────────────────────┬─────────────────────────────────────┤
│  word list            │  detail panel                       │
│                       │                                     │
│  ● acătării     rare  │  acătării                           │
│  ○ adăsta    extinct  │  ──────────────────────             │
│  ○ afurca  declining  │  verdict:    extinct                │
│  ...                  │  POS:        s.f.                   │
│                       │  register:   înv.                   │
│                       │  domain:     —                      │
│                       │  etymology:  slavă                  │
│                       │  ──────────────────────             │
│                       │  hist_ppm:   12.40                  │
│                       │  modern_ppm: 0.00                   │
│                       │  log_ratio:  -5.20                  │
│                       │  ──────────────────────             │
│                       │  web: ✗ not found (google)          │
│                       │  last_seen:  —                      │
│                       │  ──────────────────────             │
│                       │  [☆ bookmark]  [tag: înv. ×]        │
│                       │  note: ________________________     │
│                       │        (Enter to save)              │
├───────────────────────┴─────────────────────────────────────┤
│  16,880 words  ·  3 bookmarked  ·  j/k navigate  ·  / search│
└─────────────────────────────────────────────────────────────┘
```

---

## HTMX patterns

- **Search bar**: `hx-get="/search" hx-trigger="input changed delay:200ms" hx-target="#word-list" hx-include="#filter-form"`
- **Word row**: `hx-get="/word/WORD" hx-target="#detail-panel" hx-swap="innerHTML"`
- **Bookmark button**: `hx-post="/bookmark/WORD" hx-target="#bookmark-btn" hx-swap="outerHTML"`
- **Note save**: `hx-post="/note/WORD" hx-trigger="keydown[key=='Enter'] consume" hx-target="#note-status"`
- **Tag remove**: `hx-delete="/tag/WORD/TAG" hx-target="#tags-row" hx-swap="outerHTML"`

---

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `/` | Focus search |
| `Escape` | Blur search, return focus to list |
| `j` / `↓` | Next word |
| `k` / `↑` | Previous word |
| `b` | Toggle bookmark on selected word |
| `n` | Focus note field |
| `Enter` (in note) | Save note (HTMX handles) |
| `gg` | Jump to top |
| `G` | Jump to bottom |

JS sets `data-selected` on the active row and fires a synthetic click — JS owns focus state only, HTMX owns data fetching.

---

## File structure

```
ui/
  app.py
  templates/
    base.html
    partials/
      word_list.html
      word_row.html
      detail.html
      bookmark_btn.html
      tags_row.html
      note_status.html
tests/
  test_ui.py
data/
  research.db     # bookmarks (gitignored, created on first run)
```
