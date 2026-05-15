import csv
import pytest
import sqlite3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'ui'))

import app as ui_app


SHORTLIST_COLS = [
    'word', 'dex_frequency', 'verdict', 'confidence_tier',
    'log_ratio', 'hist_ppm', 'modern_ppm', 'dex_pos',
    'dex_register', 'dex_domain', 'dex_etymology', 'is_forgotten',
]
WEB_COLS = [
    'word', 'total_results', 'in_wild', 'web_score',
    'top_url', 'last_seen_approx', 'provider',
]


def make_shortlist(path: Path, rows: list[dict]) -> None:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=SHORTLIST_COLS)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def make_web(path: Path, rows: list[dict]) -> None:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=WEB_COLS)
        w.writeheader()
        for row in rows:
            w.writerow(row)


WORD_A = {
    'word': 'acătării', 'dex_frequency': '0.1', 'verdict': 'extinct',
    'confidence_tier': 'A', 'log_ratio': '-5.2', 'hist_ppm': '12.4',
    'modern_ppm': '0.0', 'dex_pos': 's.f.', 'dex_register': 'înv.',
    'dex_domain': '', 'dex_etymology': 'slavă', 'is_forgotten': '1',
}
WORD_B = {
    'word': 'adăsta', 'dex_frequency': '0.2', 'verdict': 'declining',
    'confidence_tier': 'A', 'log_ratio': '-3.1', 'hist_ppm': '8.0',
    'modern_ppm': '0.1', 'dex_pos': 'vb.', 'dex_register': '',
    'dex_domain': '', 'dex_etymology': '', 'is_forgotten': '1',
}
WEB_A = {
    'word': 'acătării', 'total_results': '0', 'in_wild': '0',
    'web_score': '0', 'top_url': '', 'last_seen_approx': '', 'provider': 'google',
}


@pytest.fixture()
def dbs(tmp_path):
    shortlist = tmp_path / 'shortlist.csv'
    web = tmp_path / 'web.csv'
    research = tmp_path / 'research.db'
    make_shortlist(shortlist, [WORD_A, WORD_B])
    make_web(web, [WEB_A])
    words_db = ui_app.load_words(shortlist, web)
    res_db = ui_app.open_research_db(research)
    return words_db, res_db


def test_load_words_count(dbs):
    words_db, _ = dbs
    count = words_db.execute('SELECT COUNT(*) FROM words').fetchone()[0]
    assert count == 2


def test_load_words_web_merge(dbs):
    words_db, _ = dbs
    row = words_db.execute(
        "SELECT provider, in_wild FROM words WHERE word = 'acătării'"
    ).fetchone()
    assert row['provider'] == 'google'
    assert row['in_wild'] == 0


def test_load_words_no_web_data(dbs):
    words_db, _ = dbs
    row = words_db.execute(
        "SELECT provider FROM words WHERE word = 'adăsta'"
    ).fetchone()
    assert row['provider'] is None


def test_open_research_db_creates_table(dbs):
    _, res_db = dbs
    tables = res_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    names = [t['name'] for t in tables]
    assert 'bookmarks' in names
