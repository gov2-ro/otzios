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
WORD_C = {
    'word': 'afurca', 'dex_frequency': '0.05', 'verdict': 'extinct',
    'confidence_tier': 'corpus_extinct', 'log_ratio': '-8.0', 'hist_ppm': '5.0',
    'modern_ppm': '0.0', 'dex_pos': 'vb.', 'dex_register': '',
    'dex_domain': '', 'dex_etymology': '', 'is_forgotten': '1',
}
WEB_A = {
    'word': 'acătării', 'total_results': '12', 'in_wild': 'true',
    'web_score': 'alive_rare', 'top_url': 'https://example.com',
    'last_seen_approx': '', 'provider': 'ddg',
}


@pytest.fixture()
def dbs(tmp_path):
    shortlist = tmp_path / 'shortlist.csv'
    web = tmp_path / 'web.csv'
    research = tmp_path / 'research.db'
    make_shortlist(shortlist, [WORD_A, WORD_B])
    make_web(web, [WEB_A])
    words_db = ui_app.load_words(shortlist, web, tmp_path / 'no_defs.db')
    res_db = ui_app.open_research_db(research)
    yield words_db, res_db
    words_db.close()
    res_db.close()


def test_load_words_count(dbs):
    words_db, _ = dbs
    count = words_db.execute('SELECT COUNT(*) FROM words').fetchone()[0]
    assert count == 2


def test_load_words_web_merge(dbs):
    words_db, _ = dbs
    row = words_db.execute(
        "SELECT provider, in_wild, web_score FROM words WHERE word = 'acătării'"
    ).fetchone()
    assert row['provider'] == 'ddg'
    assert row['in_wild'] == 1
    assert row['web_score'] == 'alive_rare'


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


@pytest.fixture()
def client(dbs):
    words_db, res_db = dbs
    ui_app._words_db = words_db
    ui_app._research_db = res_db
    ui_app.app.config['TESTING'] = True
    with ui_app.app.test_client() as c:
        yield c


def test_index_returns_200(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'Search' in resp.data
    assert b'word-list' in resp.data
    assert b'detail-panel' in resp.data


def test_search_returns_all_words(client):
    resp = client.get('/search')
    assert resp.status_code == 200
    assert 'acătării'.encode('utf-8') in resp.data
    assert 'adăsta'.encode('utf-8') in resp.data


def test_search_filters_by_query(client):
    resp = client.get('/search?q=acăt')
    assert 'acătării'.encode('utf-8') in resp.data
    assert 'adăsta'.encode('utf-8') not in resp.data


def test_search_filters_by_verdict(client):
    resp = client.get('/search?verdict=extinct')
    assert 'acătării'.encode('utf-8') in resp.data
    assert 'adăsta'.encode('utf-8') not in resp.data


def test_search_filters_by_bookmarked(client):
    client.post('/bookmark/acătării')
    resp = client.get('/search?bookmarked=1')
    assert 'acătării'.encode('utf-8') in resp.data
    assert 'adăsta'.encode('utf-8') not in resp.data


def test_word_detail_returns_fragment(client):
    resp = client.get('/word/acătării')
    assert resp.status_code == 200
    assert 'acătării'.encode('utf-8') in resp.data
    assert b'extinct' in resp.data
    assert b's.f.' in resp.data


def test_word_detail_missing_returns_404(client):
    resp = client.get('/word/nonexistent')
    assert resp.status_code == 404


def test_bookmark_toggle_on(client):
    resp = client.post('/bookmark/acătării')
    assert resp.status_code == 200
    assert '★'.encode('utf-8') in resp.data
    row = ui_app._research_db.execute(
        "SELECT bookmarked FROM bookmarks WHERE word='acătării'"
    ).fetchone()
    assert row['bookmarked'] == 1


def test_bookmark_toggle_off(client):
    client.post('/bookmark/acătării')
    resp = client.post('/bookmark/acătării')
    assert '☆'.encode('utf-8') in resp.data
    row = ui_app._research_db.execute(
        "SELECT bookmarked FROM bookmarks WHERE word='acătării'"
    ).fetchone()
    assert row['bookmarked'] == 0


def test_bookmark_missing_word_returns_404(client):
    resp = client.post('/bookmark/doesnotexist')
    assert resp.status_code == 404


def test_note_save(client):
    resp = client.post('/note/acătării', data={'note': 'interesting archaic form'})
    assert resp.status_code == 200
    assert b'saved' in resp.data
    row = ui_app._research_db.execute(
        "SELECT note FROM bookmarks WHERE word='acătării'"
    ).fetchone()
    assert row['note'] == 'interesting archaic form'


def test_note_save_missing_word_returns_404(client):
    resp = client.post('/note/nonexistent', data={'note': 'x'})
    assert resp.status_code == 404


def test_tag_add(client):
    resp = client.post('/tag/acătării', data={'tag': 'înv.'})
    assert resp.status_code == 200
    assert 'înv.'.encode('utf-8') in resp.data
    resp2 = client.get('/word/acătării')
    assert 'înv.'.encode('utf-8') in resp2.data


def test_tag_add_duplicate_ignored(client):
    client.post('/tag/acătării', data={'tag': 'înv.'})
    client.post('/tag/acătării', data={'tag': 'înv.'})
    row = ui_app._research_db.execute(
        "SELECT tags FROM bookmarks WHERE word='acătării'"
    ).fetchone()
    tags = [t for t in row['tags'].split(',') if t.strip()]
    assert tags.count('înv.') == 1


def test_tag_remove(client):
    client.post('/tag/acătării', data={'tag': 'înv.'})
    resp = client.delete('/tag/acătării/înv.')
    assert resp.status_code == 200
    assert 'înv.'.encode('utf-8') not in resp.data
    row = ui_app._research_db.execute(
        "SELECT tags FROM bookmarks WHERE word='acătării'"
    ).fetchone()
    tags = [t for t in (row['tags'] or '').split(',') if t.strip()]
    assert 'înv.' not in tags


def test_load_words_loads_definitions(tmp_path):
    shortlist = tmp_path / 'shortlist.csv'
    web = tmp_path / 'web.csv'
    make_shortlist(shortlist, [WORD_A, WORD_B])
    make_web(web, [])

    defs_db = tmp_path / 'defs.db'
    dconn = sqlite3.connect(str(defs_db))
    dconn.execute('CREATE TABLE definitions (word TEXT PRIMARY KEY, definition TEXT NOT NULL)')
    dconn.execute("INSERT INTO definitions VALUES ('acătării', 'Vânzătoare de acătări.')")
    dconn.commit()
    dconn.close()

    words_db = ui_app.load_words(shortlist, web, defs_db)
    row = words_db.execute(
        "SELECT definition FROM words WHERE word='acătării'"
    ).fetchone()
    assert row['definition'] == 'Vânzătoare de acătări.'
    row2 = words_db.execute(
        "SELECT definition FROM words WHERE word='adăsta'"
    ).fetchone()
    assert row2['definition'] is None
    words_db.close()


def test_load_words_no_definitions_db(tmp_path):
    shortlist = tmp_path / 'shortlist.csv'
    web = tmp_path / 'web.csv'
    make_shortlist(shortlist, [WORD_A, WORD_B])
    make_web(web, [])
    words_db = ui_app.load_words(shortlist, web, tmp_path / 'nonexistent.db')
    row = words_db.execute("SELECT definition FROM words WHERE word='acătării'").fetchone()
    assert row['definition'] is None
    words_db.close()


@pytest.fixture()
def client3(tmp_path):
    shortlist = tmp_path / 'shortlist.csv'
    web = tmp_path / 'web.csv'
    research = tmp_path / 'research.db'
    # WORD_A: log_ratio=-5.2, modern_ppm=0.0, dex_frequency=0.1
    # WORD_B: log_ratio=-3.1, modern_ppm=0.1, dex_frequency=0.2
    # WORD_C: log_ratio=-8.0, modern_ppm=0.0, dex_frequency=0.05
    make_shortlist(shortlist, [WORD_A, WORD_B, WORD_C])
    make_web(web, [])
    words_db = ui_app.load_words(shortlist, web, tmp_path / 'no_defs.db')
    res_db = ui_app.open_research_db(research)
    ui_app._words_db = words_db
    ui_app._research_db = res_db
    ui_app.app.config['TESTING'] = True
    with ui_app.app.test_client() as c:
        yield c
    words_db.close()
    res_db.close()


def test_search_default_sort_is_alpha(client3):
    resp = client3.get('/search')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert html.index('acătării') < html.index('adăsta') < html.index('afurca')


def test_search_sort_declined(client3):
    # WORD_C log_ratio=-8.0 (most declined DESC), then WORD_A -5.2, then WORD_B -3.1
    resp = client3.get('/search?sort=declined')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert html.index('afurca') < html.index('acătării') < html.index('adăsta')


def test_search_sort_rare(client3):
    # WORD_A modern_ppm=0.0, WORD_C modern_ppm=0.0, WORD_B modern_ppm=0.1
    # ASC: 0.0 words first — adăsta (0.1) should come last
    resp = client3.get('/search?sort=rare')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert html.index('adăsta') > html.index('acătării')


def test_search_sort_invalid_falls_back_to_alpha(client3):
    resp = client3.get('/search?sort=DROP+TABLE+words')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert html.index('acătării') < html.index('adăsta')


def test_base_has_sort_select(client):
    resp = client.get('/')
    assert b'name="sort"' in resp.data


def test_base_has_shortcuts_overlay(client):
    resp = client.get('/')
    assert b'shortcuts-overlay' in resp.data
    assert b'showShortcuts' in resp.data


def test_word_detail_shows_definition(dbs, client):
    # dbs and client share the same words_db (pytest fixture dedup)
    words_db, _ = dbs
    words_db.execute(
        "UPDATE words SET definition='Vânzătoare de acătări.' WHERE word='acătării'"
    )
    words_db.commit()
    resp = client.get('/word/acătării')
    assert 'Vânzătoare de acătări.'.encode('utf-8') in resp.data
    assert b'dexonline.ro' in resp.data


def test_word_detail_no_definition_still_shows_dex_link(client):
    resp = client.get('/word/acătării')
    assert b'definition-block' in resp.data
    assert b'dexonline.ro' in resp.data
    assert 'Vânzătoare de acătări.'.encode('utf-8') not in resp.data
