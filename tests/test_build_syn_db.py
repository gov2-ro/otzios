"""Acceptance tests for tools/build_syn_db.py, per docs/sinonime/spec.md.

Run: source ~/g2-dev/monitorulpreturilor/venv/bin/activate && pytest tests/test_build_syn_db.py -q
(or the project's current venv -- see CLAUDE.md § Python environment)

These assert against the *built* public/data/syn.db, not the build script's own printed
stats, because the real contract is "what a query against this file returns" -- see
lookup_related() below, which is the same two-way (forward + backward) join
public/api/_syn.php's version must use. A word only ever stored as an edge *target*
(64% of Relation pairs are not reciprocal, per findings.md §2) has no sense_word row of
its own; only the backward half of the union finds it.
"""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SYN_DB = ROOT / 'public' / 'data' / 'syn.db'
RELATIONS_DB = ROOT / 'data' / 'processed' / 'relations.db'
CORPUS_DB = ROOT / 'data' / 'processed' / 'corpus_frequencies.db'
INFLECTED_DB = ROOT / 'data' / 'processed' / 'inflected_forms.db'


@pytest.fixture(scope='module')
def conn():
    if not SYN_DB.exists():
        pytest.skip(f'{SYN_DB} not built -- run tools/build_syn_db.py first')
    c = sqlite3.connect(str(SYN_DB))
    c.execute('PRAGMA query_only = ON')
    yield c
    c.close()


def word_id(conn, form):
    row = conn.execute('SELECT id FROM word WHERE form = ?', (form,)).fetchone()
    return row[0] if row else None


def sense_clusters(conn, form, t=1):
    """sid -> set(related word_id), unioning the forward and backward halves of lookup --
    the same shape public/api/_syn.php's lookup_related() must produce for the page."""
    wid = word_id(conn, form)
    if wid is None:
        return {}
    clusters: dict[int, set[int]] = {}
    for (sid,) in conn.execute('SELECT sid FROM sense_word WHERE word_id = ?', (wid,)):
        for (rwid,) in conn.execute('SELECT word_id FROM edge WHERE sid = ? AND t = ?', (sid, t)):
            if rwid != wid:
                clusters.setdefault(sid, set()).add(rwid)
    for (sid,) in conn.execute('SELECT sid FROM edge WHERE word_id = ? AND t = ?', (wid, t)):
        for (rwid,) in conn.execute('SELECT word_id FROM sense_word WHERE sid = ?', (sid,)):
            if rwid != wid:
                clusters.setdefault(sid, set()).add(rwid)
    return clusters


def test_file_size_under_ceiling():
    assert SYN_DB.stat().st_size < 16 * 1024 * 1024


def test_schema_has_no_ui_db_or_app_db_reference(conn):
    schema = '\n'.join(row[0] or '' for row in
                        conn.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"))
    assert 'ui.db' not in schema
    assert 'app.db' not in schema
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {'word', 'key', 'sense', 'sense_word', 'edge', 'meta'}


def test_nalt_resolves_through_key_but_has_no_word_row(conn):
    assert word_id(conn, 'nalt') is None
    rows = conn.execute('SELECT word_id FROM key WHERE k = ?', ('nalt',)).fetchall()
    assert rows, 'nalt should resolve via key'
    target = conn.execute('SELECT form FROM word WHERE id = ?', (rows[0][0],)).fetchone()
    assert target is not None


def test_tanar_resolves_to_tanar_through_folded_key(conn):
    rows = conn.execute('SELECT word_id FROM key WHERE k = ?', ('tanar',)).fetchall()
    assert rows
    forms = {conn.execute('SELECT form FROM word WHERE id = ?', (wid,)).fetchone()[0]
              for (wid,) in rows}
    assert 'tânăr' in forms


def test_vaz_has_at_least_three_sense_clusters(conn):
    clusters = sense_clusters(conn, 'văz', t=1)
    non_empty = {sid: words for sid, words in clusters.items() if words}
    assert len(non_empty) >= 3, (
        f'văz has {len(non_empty)} sense clusters, expected >=3 -- if this is 1, the '
        f'tree-expansion rule is flattening senses (docs/sinonime/escalate.md §5); '
        f'do not loosen this assertion, investigate build_relation_graph() instead.')


def test_concepite_not_merged_with_privire_cluster(conn):
    """The flattening regression, stated concretely: a naive word<->word bag puts privire,
    vedere, captiva, orbi and concepție all in văz's one synonym list (findings.md §7).
    concepție must land in its own sense cluster, never sharing one with privire."""
    clusters = sense_clusters(conn, 'văz', t=1)
    concept_wid = word_id(conn, 'concepție')
    privire_wid = word_id(conn, 'privire')
    if concept_wid is None or privire_wid is None:
        pytest.skip('concepție or privire not in this build -- data may have shifted upstream')
    for sid, words in clusters.items():
        contains_concept = concept_wid in words
        contains_privire = privire_wid in words
        assert not (contains_concept and contains_privire), (
            f'sense {sid} contains both concepție and privire -- senses are flattening')


def _rollup_occurrences(conn_corpus, lemmas: set[str]) -> dict[str, int]:
    conn_corpus.execute('DROP TABLE IF EXISTS temp.want_lemma')
    conn_corpus.execute('CREATE TEMP TABLE want_lemma (lemma TEXT PRIMARY KEY)')
    conn_corpus.executemany('INSERT INTO want_lemma VALUES (?)', [(l,) for l in lemmas])
    rows = conn_corpus.execute("""
        SELECT fl.lemma, SUM(cwf.occurrence_count)
          FROM infl.form_lemma fl
          JOIN corpus_word_frequency cwf ON cwf.word = fl.form AND cwf.corpus_name = 'culturax_ro'
          JOIN want_lemma w ON w.lemma = fl.lemma
         GROUP BY fl.lemma
    """).fetchall()
    return {lemma: (occ or 0) for lemma, occ in rows}


def test_coverage_at_1k_occurrences_is_at_least_70_percent(conn):
    """Measured against the *full* DEX main-headword universe (every EntryLexeme.main=1
    lexeme in relations.db), not just words that made it into syn.db's word table -- the
    latter would be circular (a graph node trivially has edges). findings.md §4 measured
    67.0% from Relation alone, 72.4% with Tree co-membership; this asserts the spec's
    floor, not the exact figure (escalate.md §4: report what you get, don't force a match)."""
    if not (RELATIONS_DB.exists() and CORPUS_DB.exists() and INFLECTED_DB.exists()):
        pytest.skip('relations.db / corpus_frequencies.db / inflected_forms.db not present')

    rel = sqlite3.connect(str(RELATIONS_DB))
    headwords = {form for (form,) in rel.execute("""
        SELECT DISTINCT l.form_norm
          FROM entry_lexeme el JOIN lexeme l ON l.id = el.lexeme_id
         WHERE el.main = 1 AND l.form_norm IS NOT NULL
    """)}
    rel.close()

    corp = sqlite3.connect(str(CORPUS_DB))
    corp.execute(f"ATTACH DATABASE '{INFLECTED_DB}' AS infl")
    occ_by_form = _rollup_occurrences(corp, headwords)
    corp.close()

    at_1k = {form for form in headwords if occ_by_form.get(form, 0) >= 1000}
    assert at_1k, 'no headwords at 1k+ occurrences -- corpus rollup likely broken'

    covered_word_ids: set[int] = {wid for (wid,) in conn.execute('SELECT DISTINCT word_id FROM sense_word')}
    covered_word_ids |= {wid for (wid,) in conn.execute('SELECT DISTINCT word_id FROM edge')}
    covered_forms = {form for (form,) in conn.execute(
        f"SELECT form FROM word WHERE id IN ({','.join('?' * len(covered_word_ids))})",
        list(covered_word_ids))} if covered_word_ids else set()

    hit = len(at_1k & covered_forms)
    pct = 100 * hit / len(at_1k)
    print(f'\ncoverage @1k+: {hit}/{len(at_1k)} = {pct:.1f}%')
    assert pct >= 70.0, f'coverage {pct:.1f}% is under the 70% floor'
