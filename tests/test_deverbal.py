"""Guards for `deverbal_like` — the noun that is its own verb, twice.

`zăhăială` is defined in full as "Faptul de a (se) zăhăi", and `zăhăi` is on the same
list. The flag is about that duplication, not about word formation, which is the whole
reason the base verb has to be present *and visible*.

Unit tests always run; the integration ones name real words and skip without ui.db.
"""

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))
sys.path.insert(0, str(Path(__file__).parent.parent))
from build_ui_db import _HIDE_FLAGS, mark_deverbal_nouns  # noqa: E402

UI_DB = Path(__file__).parent.parent / 'public' / 'data' / 'ui.db'


@pytest.fixture(scope='module')
def db():
    if not UI_DB.exists():
        pytest.skip(f'{UI_DB} not built')
    conn = sqlite3.connect(f'file:{UI_DB}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def _ui(tmp_path, rows):
    """rows: [(word, definition, seam, **flags)] as dicts."""
    p = tmp_path / 'ui.db'
    c = sqlite3.connect(str(p))
    cols = ', '.join(f'{f} INT' for f in _HIDE_FLAGS)
    c.execute(f'CREATE TABLE words (word TEXT PRIMARY KEY, definition TEXT, seam TEXT, '
              f'{cols}, deverbal_like INT, deverbal_of TEXT)')
    for r in rows:
        flags = [r.get(f, 0) for f in _HIDE_FLAGS]
        c.execute(
            f"INSERT INTO words (word, definition, seam, {', '.join(_HIDE_FLAGS)}) "
            f"VALUES (?,?,?,{','.join('?' * len(_HIDE_FLAGS))})",
            [r['word'], r.get('definition'), r.get('seam', 'relevant'), *flags])
    c.commit()
    return c


def flag(conn, word):
    return conn.execute('SELECT deverbal_like, deverbal_of FROM words WHERE word = ?',
                        (word,)).fetchone()


def test_the_noun_is_hidden_when_its_verb_is_on_the_list(tmp_path):
    conn = _ui(tmp_path, [
        {'word': 'zăhăială', 'definition': 'Faptul de a (se) zăhăi.'},
        {'word': 'zăhăi',    'definition': 'A zăpăci, a deranja.'},
    ])
    mark_deverbal_nouns(conn)
    assert flag(conn, 'zăhăială') == (1, 'zăhăi')
    assert flag(conn, 'zăhăi')[0] == 0, 'the verb is the thing being kept'


def test_the_noun_stays_when_its_verb_is_not_on_the_list(tmp_path):
    """563 of the 729 deverbal definitions are in this state. Hiding them would be a
    rule about word formation rather than about duplication, and `pospăială` without
    `pospăi` is the only place a reader ever meets that root."""
    conn = _ui(tmp_path, [{'word': 'pospăială', 'definition': 'Faptul de a pospăi.'}])
    mark_deverbal_nouns(conn)
    assert flag(conn, 'pospăială')[0] == 0


@pytest.mark.parametrize('flagname', _HIDE_FLAGS)
def test_the_noun_stays_when_its_verb_is_itself_hidden(tmp_path, flagname):
    """The measured failure: on the naive rule, 10 of the 25 nouns removed from the
    default view had a verb that was not in the default view either — `împământeni` is
    regional_only, `pospăi` is in the curiosity seam. There the noun is the only member
    of the pair anyone can see, so hiding it is deletion, not deduplication."""
    conn = _ui(tmp_path, [
        {'word': 'dărăpănare', 'definition': 'Acțiunea de a se dărăpăna și rezultatul ei.'},
        {'word': 'dărăpăna',   'definition': 'A se ruina.', flagname: 1},
    ])
    mark_deverbal_nouns(conn)
    assert flag(conn, 'dărăpănare')[0] == 0, f'hidden behind a verb that is {flagname}'


def test_a_curiosity_verb_does_not_hide_a_relevant_noun(tmp_path):
    conn = _ui(tmp_path, [
        {'word': 'moleșire', 'definition': 'Faptul de a (se) moleși.', 'seam': 'relevant'},
        {'word': 'moleși',   'definition': 'A slăbi.',                 'seam': 'curiosity'},
    ])
    mark_deverbal_nouns(conn)
    assert flag(conn, 'moleșire')[0] == 0


def test_a_relevant_verb_does_hide_a_curiosity_noun(tmp_path):
    """The other direction is fine — the verb is *more* visible than the noun."""
    conn = _ui(tmp_path, [
        {'word': 'jeluire', 'definition': 'Acțiunea de a (se) jelui.', 'seam': 'curiosity'},
        {'word': 'jelui',   'definition': 'A se plânge.',              'seam': 'relevant'},
    ])
    mark_deverbal_nouns(conn)
    assert flag(conn, 'jeluire') == (1, 'jelui')


@pytest.mark.parametrize('definition,verb', [
    ('Faptul de a (se) zăhăi.',                    'zăhăi'),
    ('Acțiunea de a scăpăra și rezultatul ei.',    'scăpăra'),
    ('Acțiunea de a se dărăpăna .',                'dărăpăna'),
    ('Faptul de a noroci .',                       'noroci'),
    ('Actiunea de a jelui',                        'jelui'),   # cedilla spelling
    ('faptul de a (se) năduși',                    'năduși'),  # lowercased
])
def test_the_definition_shapes_it_reads(tmp_path, definition, verb):
    conn = _ui(tmp_path, [{'word': 'nnn', 'definition': definition},
                          {'word': verb, 'definition': 'A face ceva.'}])
    mark_deverbal_nouns(conn)
    assert flag(conn, 'nnn') == (1, verb)


def test_only_the_first_segment_counts(tmp_path):
    """A word whose *later* sense happens to be phrased this way still has a definition
    of its own in front of it, so it is not a bare nominalization."""
    conn = _ui(tmp_path, [
        {'word': 'nnn',  'definition': 'Unealtă de tâmplărie. | Faptul de a bate.'},
        {'word': 'bate', 'definition': 'A lovi.'},
    ])
    mark_deverbal_nouns(conn)
    assert flag(conn, 'nnn')[0] == 0


def test_a_word_never_hides_behind_itself(tmp_path):
    conn = _ui(tmp_path, [{'word': 'jelui', 'definition': 'Acțiunea de a jelui.'}])
    mark_deverbal_nouns(conn)
    assert flag(conn, 'jelui')[0] == 0


def test_it_is_idempotent(tmp_path):
    rows = [{'word': 'zăhăială', 'definition': 'Faptul de a (se) zăhăi.'},
            {'word': 'zăhăi',    'definition': 'A zăpăci.'}]
    conn = _ui(tmp_path, rows)
    mark_deverbal_nouns(conn)
    first = conn.execute('SELECT * FROM words ORDER BY word').fetchall()
    mark_deverbal_nouns(conn)
    assert conn.execute('SELECT * FROM words ORDER BY word').fetchall() == first


def test_a_missing_flag_column_degrades_rather_than_aborting(tmp_path):
    """The migration adds these columns one at a time; the visibility check should
    weaken, not raise."""
    p = tmp_path / 'ui.db'
    c = sqlite3.connect(str(p))
    c.execute('CREATE TABLE words (word TEXT PRIMARY KEY, definition TEXT, seam TEXT, '
              'deverbal_like INT, deverbal_of TEXT)')
    c.executemany("INSERT INTO words (word, definition, seam) VALUES (?,?,'relevant')",
                  [('zăhăială', 'Faptul de a (se) zăhăi.'), ('zăhăi', 'A zăpăci.')])
    mark_deverbal_nouns(c)
    assert flag(c, 'zăhăială') == (1, 'zăhăi')


# ── Against the built database ────────────────────────────────────────────────

@pytest.mark.parametrize('noun,verb', [
    ('zăhăială', 'zăhăi'), ('opintire', 'opinti'), ('nădușeală', 'năduși'),
])
def test_known_pairs_are_flagged(db, noun, verb):
    row = db.execute('SELECT deverbal_like, deverbal_of FROM words WHERE word = ?',
                     (noun,)).fetchone()
    if row is None:
        return
    assert row['deverbal_like'] == 1
    assert row['deverbal_of'] == verb


def test_every_flagged_noun_has_a_verb_that_is_actually_visible(db):
    """The whole invariant, asserted against the real table rather than a fixture."""
    flags = ' OR '.join(f'COALESCE(v.{f}, 0) = 1' for f in _HIDE_FLAGS)
    bad = db.execute(
        f"""SELECT n.word, n.deverbal_of FROM words n
              LEFT JOIN words v ON v.word = n.deverbal_of
             WHERE n.deverbal_like = 1
               AND (v.word IS NULL OR ({flags})
                    OR (v.seam != n.seam AND v.seam != 'relevant'))"""
    ).fetchall()
    assert bad == [], [tuple(r) for r in bad]


def test_every_flagged_noun_names_its_verb(db):
    n = db.execute("SELECT COUNT(*) FROM words WHERE deverbal_like = 1 "
                   "  AND (deverbal_of IS NULL OR deverbal_of = '')").fetchone()[0]
    assert n == 0, n


def test_it_stays_a_small_flag(db):
    """149 on the 2026-08-12 build, 15 of them in the default view. This is a tidy-up,
    not a filter — an order of magnitude means the rule stopped requiring the verb."""
    flagged = db.execute('SELECT COALESCE(SUM(deverbal_like), 0) FROM words').fetchone()[0]
    assert 20 <= flagged <= 600, flagged
