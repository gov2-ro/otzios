#!/usr/bin/env python3
"""Curator marks — the one signal allowed to subtract from the default view.

Two flags per word, both set by hand while reading:

``pick``    the curator favourited it. Feeds the ★ badge and the „alese" list.
``demote``  the curator marked it ⚠️ meh. Hidden by default behind the „respinse"
            three-state control, exactly like the other four special classes.

Why a tracked file rather than a live read of ``app.db``:

1. **The build cannot see production.** ``build_ui_db.py`` runs on a laptop while
   ``app.db`` lives on the server, outside the web root. There is no moment at which
   the builder and the annotations are on the same machine.
2. **Subtraction has to be reviewable.** These marks remove words from what every
   visitor sees. As a tracked TSV that is a diff with a git history and an obvious
   undo; as a live query it would be one person's clicking silently reshaping the
   site, which is the objection that deferred this feature in the first place
   (``docs/BACKLOG.md``, entry "Publish top faves list").

Community marks are deliberately *not* here. They are aggregated live from every
user and may only reorder — see ``vote_counts_subquery()`` in
``public/api/_appdb.php``. Forging votes buys rank; only the curator can hide.
"""
from pathlib import Path

EDITORIAL_PATH = Path('data/editorial.tsv')

PICK   = 'pick'
DEMOTE = 'demote'
MARKS  = (PICK, DEMOTE)

HEADER = (
    '# Curator marks. word<TAB>mark, mark ∈ {pick, demote}. Sorted, one word per line.\n'
    '# Written by tools/export_editorial.py; read by tools/build_ui_db.py.\n'
)


def load_marks(path: Path = EDITORIAL_PATH) -> dict[str, str]:
    """Read word → mark. Returns {} when the file does not exist yet.

    A missing file is the correct empty state, not an error: an install that has
    never curated anything gets no picks and hides nothing.
    """
    marks: dict[str, str] = {}
    if not path.exists():
        return marks

    with open(path, encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            word, _, mark = line.partition('\t')
            if not word or mark not in MARKS:
                raise ValueError(
                    f'{path}:{lineno}: expected "<word>\\t{"|".join(MARKS)}", got {line!r}'
                )
            marks[word] = mark
    return marks


def write_marks(marks: dict[str, str], path: Path = EDITORIAL_PATH) -> None:
    """Write word → mark, sorted, so a re-export is a readable diff rather than a
    reshuffle."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(HEADER)
        for word in sorted(marks):
            f.write(f'{word}\t{marks[word]}\n')


def apply_to_db(conn, path: Path = EDITORIAL_PATH) -> tuple[int, int, int]:
    """Set words.editor_pick / editor_demote from the registry.

    Shared by build_ui_db.py (full rebuild) and migrate_ui_db_editorial.py (backfill
    of an already-built ui.db), so both go through the same file. Idempotent: every
    row is reset to 0 first, so a word that lost its mark loses the flag too.

    Returns (picks, demotes, missing) — `missing` counts words in the file that this
    ui.db does not have. That is expected rather than an error: the shortlist changes
    between rebuilds, and a curator mark on a word that dropped out is simply inert
    until it comes back.
    """
    marks = load_marks(path)

    conn.execute('UPDATE words SET editor_pick = 0, editor_demote = 0')
    if not marks:
        return (0, 0, 0)

    known = {w for (w,) in conn.execute('SELECT word FROM words')}
    picks   = [(w,) for w, m in marks.items() if m == PICK   and w in known]
    demotes = [(w,) for w, m in marks.items() if m == DEMOTE and w in known]
    missing = sum(1 for w in marks if w not in known)

    conn.executemany('UPDATE words SET editor_pick = 1 WHERE word = ?', picks)
    conn.executemany('UPDATE words SET editor_demote = 1 WHERE word = ?', demotes)

    return (len(picks), len(demotes), missing)
