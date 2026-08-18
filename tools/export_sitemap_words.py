#!/usr/bin/env python3
"""Export one curator's ★fav/🤣lol marks from app.db into data/sitemap_words.tsv — the
seed word list for the sitemap (docs/reference/llm/plans-archive/let-s-talk-a-bit-
polymorphic-pine.md).

    python tools/export_sitemap_words.py --user 1 --dry-run    # counts only, writes nothing
    python tools/export_sitemap_words.py --user 1

Mirrors tools/export_editorial.py's shape deliberately: ``--user`` required with no
default (the dev app.db carries hundreds of test-fixture users), ``--list-users``,
``--dry-run``. That script exports *judgement* (pick/demote, feeding a hide-flag);
this one exports *discovery bait* — a word worth a search-engine landing page — which
is a different question with the same "don't publish a test fixture's taste" risk.

fav wins on overlap with lol, same precedence export_editorial.py gives pick over
demote: a word marked both ways keeps the stronger of the two signals rather than
being written twice or dropped.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

DEFAULT_APP_DB = Path('private/app.db')
OUT_PATH = Path('data/sitemap_words.tsv')

FAV = 'fav'
LOL = 'lol'
BUCKETS = (FAV, LOL)

HEADER = (
    '# Seed words for the sitemap. word<TAB>bucket, bucket ∈ {fav, lol}. Sorted.\n'
    '# Written by tools/export_sitemap_words.py; read by tools/build_sitemap.py.\n'
)


def fetch_words(db: Path, user_id: int) -> dict[str, str]:
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

    words: dict[str, str] = {}
    for word, bookmarked, tags in rows:
        if bookmarked:
            words[word] = FAV
        elif '"lol"' in (tags or ''):
            words[word] = LOL
    return words


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


def write_words(words: dict[str, str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(HEADER)
        for word in sorted(words):
            f.write(f'{word}\t{words[word]}\n')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--user', type=int, help='curator user id in app.db (required)')
    ap.add_argument('--db', type=Path, default=DEFAULT_APP_DB, help=f'default {DEFAULT_APP_DB}')
    ap.add_argument('--out', type=Path, default=OUT_PATH, help=f'default {OUT_PATH}')
    ap.add_argument('--list-users', action='store_true', help='show who has annotations, then exit')
    ap.add_argument('--dry-run', action='store_true', help='print the summary, write nothing')
    args = ap.parse_args()

    if not args.db.exists():
        sys.exit(f'Missing: {args.db}')

    if args.list_users:
        list_users(args.db)
        return 0

    if args.user is None:
        sys.exit('--user is required (try --list-users). It is never defaulted: the dev '
                 'app.db is full of test fixtures.')

    words = fetch_words(args.db, args.user)
    favs = sum(1 for m in words.values() if m == FAV)
    lols = sum(1 for m in words.values() if m == LOL)

    print(f'user {args.user}: {favs} fav, {lols} lol  →  {args.out}')

    if args.dry_run:
        print('  (dry run, nothing written)')
        return 0

    write_words(words, args.out)
    print(f'Wrote {len(words)} rows. Now run: python tools/build_sitemap.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
