#!/usr/bin/env python3
"""Generic "list of words in, sitemap out" builder — kept separate from
tools/export_sitemap_words.py so a bigger or differently-sourced word list can be
pointed at this later with no code change (docs/reference/llm/plans-archive/
let-s-talk-a-bit-polymorphic-pine.md).

    python tools/build_sitemap.py --dry-run       # counts + skipped words, writes nothing
    python tools/build_sitemap.py                 # → public/sitemap.xml

Each word is checked against the live ui.db and skipped (with a warning) if it no
longer appears there — a curated word can drop out of a later rescore, and a sitemap
entry pointing at a page that 404s is worse than a shorter sitemap. No <lastmod>: for
a hand-curated list there is no honest per-word timestamp to report.
"""
import argparse
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

DEFAULT_WORDS_FILE = Path('data/sitemap_words.tsv')
DEFAULT_DB = Path('public/data/ui.db')
DEFAULT_OUT = Path('public/sitemap.xml')
DEFAULT_BASE_URL = 'https://voroave.ro'


def read_words(path: Path) -> list[str]:
    words = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            word, _, _bucket = line.partition('\t')
            if word:
                words.append(word)
    return words


def existing_words(db: Path, words: list[str]) -> set[str]:
    if not words:
        return set()
    conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    try:
        placeholders = ','.join('?' for _ in words)
        rows = conn.execute(
            f'SELECT word FROM words WHERE word IN ({placeholders})', words
        ).fetchall()
    finally:
        conn.close()
    return {w for (w,) in rows}


def render(words: list[str], base_url: str) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for word in words:
        loc = f'{base_url}/?word={quote(word, safe="")}'
        lines.append(f'  <url><loc>{escape(loc)}</loc></url>')
    lines.append('</urlset>')
    return '\n'.join(lines) + '\n'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--words-file', type=Path, default=DEFAULT_WORDS_FILE, help=f'default {DEFAULT_WORDS_FILE}')
    ap.add_argument('--db', type=Path, default=DEFAULT_DB, help=f'default {DEFAULT_DB}')
    ap.add_argument('--out', type=Path, default=DEFAULT_OUT, help=f'default {DEFAULT_OUT}')
    ap.add_argument('--base-url', default=DEFAULT_BASE_URL, help=f'default {DEFAULT_BASE_URL}')
    ap.add_argument('--dry-run', action='store_true', help='print the summary, write nothing')
    args = ap.parse_args()

    if not args.words_file.exists():
        sys.exit(f'Missing: {args.words_file} (run tools/export_sitemap_words.py first)')
    if not args.db.exists():
        sys.exit(f'Missing: {args.db} (run tools/build_ui_db.py first)')

    words = read_words(args.words_file)
    live = existing_words(args.db, words)
    kept = [w for w in words if w in live]
    dropped = [w for w in words if w not in live]

    print(f'{len(kept)} of {len(words)} words are in {args.db} → {args.out}')
    for w in dropped:
        print(f'  skip (not in ui.db): {w}')

    if args.dry_run:
        print('  (dry run, nothing written)')
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(kept, args.base_url.rstrip('/')), encoding='utf-8')
    print(f'Wrote {len(kept)} URLs.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
