#!/usr/bin/env python3
"""Export one curator's annotations from app.db into data/editorial.tsv.

    python tools/export_editorial.py --user 1 --dry-run    # counts only, writes nothing
    python tools/export_editorial.py --user 1

``--user`` is required and never defaults. The development app.db carries hundreds of
users created by tests/test_lists_api.js and tests/test_moderation.js — `tester`,
`owner-mod-test`, `pluto` — and a default would quietly export a test fixture's taste
as the site's editorial line. Use --list-users to find the right id.

The marks:  ★ bookmarked → pick     ⚠️ meh → demote

`lol` is not exported. It is expressive rather than evaluative, and it does count as a
community vote (see vote_counts_subquery() in public/api/_appdb.php) — but it is not a
reason to hide a word or to call it one of the best.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from editorial import DEMOTE, EDITORIAL_PATH, PICK, load_marks, write_marks

DEFAULT_APP_DB = Path('private/app.db')


def fetch_marks(db: Path, user_id: int) -> dict[str, str]:
    """Read one user's picks and demotes.

    A pick wins over a demote on the same word: the ★ is the more deliberate of the
    two, and a word marked both ways should stay visible rather than disappear.
    """
    conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    try:
        rows = conn.execute(
            """SELECT word, bookmarked, tags
                 FROM annotations
                WHERE user_id = ? AND deleted = 0""",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    marks: dict[str, str] = {}
    for word, bookmarked, tags in rows:
        # tags is a JSON array of strings; the surrounding quotes make the match exact,
        # the same way annotated_words_subquery() does it in PHP.
        if bookmarked:
            marks[word] = PICK
        elif '"meh"' in (tags or ''):
            marks[word] = DEMOTE
    return marks


def list_users(db: Path) -> None:
    conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    try:
        rows = conn.execute(
            """SELECT u.id, COALESCE(NULLIF(u.nickname, ''), '(anonim)'), COUNT(a.word)
                 FROM users u
                 LEFT JOIN annotations a ON a.user_id = u.id AND a.deleted = 0
                GROUP BY u.id
               HAVING COUNT(a.word) > 0
                ORDER BY COUNT(a.word) DESC"""
        ).fetchall()
    finally:
        conn.close()

    print(f'{"id":>6}  {"nickname":<20} adnotări')
    for uid, nick, n in rows:
        print(f'{uid:>6}  {nick:<20} {n}')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--user', type=int, help='curator user id in app.db (required)')
    ap.add_argument('--db', type=Path, default=DEFAULT_APP_DB, help=f'default {DEFAULT_APP_DB}')
    ap.add_argument('--out', type=Path, default=EDITORIAL_PATH, help=f'default {EDITORIAL_PATH}')
    ap.add_argument('--list-users', action='store_true', help='show who has annotations, then exit')
    ap.add_argument('--dry-run', action='store_true', help='print the summary, write nothing')
    ap.add_argument('--force', action='store_true',
                    help='write even when the export would drop more than half the picks')
    args = ap.parse_args()

    if not args.db.exists():
        sys.exit(f'Missing: {args.db}')

    if args.list_users:
        list_users(args.db)
        return 0

    if args.user is None:
        sys.exit('--user is required (try --list-users). It is never defaulted: the dev '
                 'app.db is full of test fixtures.')

    marks = fetch_marks(args.db, args.user)
    picks   = sum(1 for m in marks.values() if m == PICK)
    demotes = sum(1 for m in marks.values() if m == DEMOTE)

    existing = load_marks(args.out)
    was_picks = sum(1 for m in existing.values() if m == PICK)

    print(f'user {args.user}: {picks} pick, {demotes} demote  →  {args.out}')
    if existing:
        print(f'  (was {was_picks} pick, {len(existing) - was_picks} demote)')

    # A mistyped --user reads as "this curator marked nothing" and would blank the file.
    # Losing picks is the visible half — the ★ list empties — so that is what we guard.
    if was_picks and picks < was_picks / 2 and not args.force:
        sys.exit(f'Refusing: picks would drop {was_picks} → {picks}. Wrong --user? '
                 f'Re-run with --force if this is intended.')

    if args.dry_run:
        print('  (dry run, nothing written)')
        return 0

    write_marks(marks, args.out)
    print(f'Wrote {len(marks)} rows. Now run: python tools/build_ui_db.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
