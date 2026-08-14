"""Guards for `dex_variant` — DEX's own variant relation as a hide-flag.

`mark_archaic_spellings()` infers the same thing from the spelling and has to stay
narrow to stay precise: the rule that would catch `sofragerie → sufragerie` is `o → u`,
which fires 1,984 times to find 124 twins. This flag reads the answer out of
`EntryLexeme.main` instead, so no spelling rule is involved at all.

Unit tests run always. The integration ones name real words and skip when
`public/data/ui.db` has not been built.
"""

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))
sys.path.insert(0, str(Path(__file__).parent.parent))
from build_ui_db import (  # noqa: E402
    TWIN_RATIO, _edit_distance, load_dex_variants, load_paradigm_modern,
    mark_dex_variants, pointer_target,
)

UI_DB = Path(__file__).parent.parent / 'public' / 'data' / 'ui.db'


@pytest.fixture(scope='module')
def db():
    if not UI_DB.exists():
        pytest.skip(f'{UI_DB} not built')
    conn = sqlite3.connect(f'file:{UI_DB}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def word(db, w):
    return db.execute('SELECT * FROM words WHERE word = ?', (w,)).fetchone()


# ── The relation itself ───────────────────────────────────────────────────────

def _fake_lexemes(tmp_path, rows):
    """rows: [(entryId, form, main)] → a lexemes.db with just what the loader reads."""
    p = tmp_path / 'lexemes.db'
    c = sqlite3.connect(str(p))
    c.execute('CREATE TABLE Lexeme (id INTEGER PRIMARY KEY, formNoAccent TEXT)')
    c.execute('CREATE TABLE EntryLexeme (entryId INT, lexemeId INT, main INT)')
    for i, (entry, form, main) in enumerate(rows, 1):
        c.execute('INSERT INTO Lexeme VALUES (?,?)', (i, form))
        c.execute('INSERT INTO EntryLexeme VALUES (?,?,?)', (entry, i, main))
    c.commit()
    c.close()
    return p


def test_a_non_main_lexeme_is_a_variant_of_its_entry_head(tmp_path):
    heads_of, all_heads = load_dex_variants(
        _fake_lexemes(tmp_path, [(1, 'sufragerie', 1), (1, 'sofragerie', 0)]))
    assert heads_of['sofragerie'] == {'sufragerie'}
    assert all_heads == {'sufragerie'}


def test_lexeme_forms_are_normalized_before_matching(tmp_path):
    """Dump forms keep their original case and cedilla diacritics; shortlist words do
    not. Without normalize() on both sides the relation silently matches nothing."""
    heads_of, _ = load_dex_variants(
        _fake_lexemes(tmp_path, [(1, 'Şedinţă', 1), (1, 'Şedinţe', 0)]))
    assert heads_of['ședințe'] == {'ședință'}


def test_a_form_that_heads_its_own_entry_is_left_alone(tmp_path):
    """Restriction 1. `momiță` is a variant of `maimuță` in one entry and the word for a
    sweetbread in another; `partită` of `partidă` and also the musical form. Admitting
    that group adds ~1,000 words at a measured ~5% error rate, and a hide-flag's false
    positives are invisible."""
    lex = _fake_lexemes(tmp_path, [
        (1, 'maimuță', 1), (1, 'momiță', 0),
        (2, 'momiță', 1),
    ])
    heads_of, all_heads = load_dex_variants(lex)
    assert heads_of['momiță'] == {'maimuță'}      # the relation still records it…
    assert 'momiță' in all_heads                  # …and the caller must skip it


# ── Which head gets named ─────────────────────────────────────────────────────

def test_the_named_head_is_the_nearest_spelling_not_the_commonest():
    """`lăcrăma`'s entry has two heads: `lăcrima` and `reclama`. Ranking by frequency
    names `reclama`, because `lăcrima` has zero occurrences as a bare infinitive."""
    heads = {'lăcrima', 'reclama'}
    assert min(heads, key=lambda h: _edit_distance('lăcrăma', h)) == 'lăcrima'


# ── The two sides of the ratio are measured differently, on purpose ────────────

def test_the_head_is_measured_over_its_whole_paradigm(tmp_path):
    """A verb's citation form is not its usage. `lăcrima` is 0 in CulturaX as an
    infinitive and 16,393 across its paradigm; gating on the surface count throws the
    real head out and leaves the variant labelled after whatever co-head the corpus
    happened to be able to count."""
    p = tmp_path / 'inflected.db'
    c = sqlite3.connect(str(p))
    c.execute('CREATE TABLE lexeme (lexeme_id INTEGER PRIMARY KEY, lemma TEXT)')
    c.execute('CREATE TABLE inflected (form TEXT, lexeme_id INT)')
    c.execute("INSERT INTO lexeme VALUES (1, 'lăcrima')")
    c.executemany('INSERT INTO inflected VALUES (?, 1)',
                  [('lăcrima',), ('lăcrimează',), ('lăcrimau',)])
    c.commit()
    c.close()
    fam = load_paradigm_modern(p, {'lăcrima': 0, 'lăcrimează': 9000, 'lăcrimau': 7393})
    assert fam['lăcrima'] == 16393


def _ui(tmp_path, words):
    """words: [(word, archaic_spelling)] or [(word, archaic_spelling, definition)]."""
    p = tmp_path / 'ui.db'
    c = sqlite3.connect(str(p))
    c.execute('CREATE TABLE words (word TEXT PRIMARY KEY, archaic_spelling INT, '
              'definition TEXT, dex_variant INT, dex_variant_of TEXT)')
    c.executemany('INSERT INTO words (word, archaic_spelling, definition) VALUES (?,?,?)',
                  [(w + (None,))[:3] for w in words])
    c.commit()
    return c


def _freqs(tmp_path, counts):
    p = tmp_path / 'freq.db'
    c = sqlite3.connect(str(p))
    c.execute('CREATE TABLE corpus_word_frequency '
              '(word TEXT, corpus_name TEXT, occurrence_count INT)')
    c.executemany("INSERT INTO corpus_word_frequency VALUES (?, 'culturax_ro', ?)",
                  list(counts.items()))
    c.commit()
    c.close()
    return p


def _empty_inflected(tmp_path):
    p = tmp_path / 'infl.db'
    c = sqlite3.connect(str(p))
    c.execute('CREATE TABLE lexeme (lexeme_id INTEGER PRIMARY KEY, lemma TEXT)')
    c.execute('CREATE TABLE inflected (form TEXT, lexeme_id INT)')
    c.execute("INSERT INTO lexeme VALUES (1, 'zzz')")
    c.execute("INSERT INTO inflected VALUES ('zzz', 1)")
    c.commit()
    c.close()
    return p


def test_the_variant_is_measured_by_its_surface_count(tmp_path):
    """The counterpart of the test above, and the reason the two sides differ.

    What is being judged about the variant is a *spelling*, which is one surface form.
    Summing its paradigm instead credits it with its own head's usage, because a variant
    shares nearly every inflected form with the word it varies from — `tinereță` comes
    out at 227,445 against `tinerețe`'s 227,064 and reads as alive.
    """
    lex = _fake_lexemes(tmp_path, [(1, 'tinerețe', 1), (1, 'tinereță', 0)])
    conn = _ui(tmp_path, [('tinereță', 0)])
    freq = _freqs(tmp_path, {'tinereță': 381, 'tinerețe': 227064})
    mark_dex_variants(conn, lex, freq, _empty_inflected(tmp_path))
    row = conn.execute('SELECT dex_variant, dex_variant_of FROM words').fetchone()
    assert row == (1, 'tinerețe')


def test_a_head_that_is_also_forgotten_does_not_hide_the_variant(tmp_path):
    """Restriction 2, and the one that protects the project's own material. Without the
    ratio gate this hides the pairs where *both* forms are dead — `antereu/anteriu`,
    `amploiat/amploaiat`, `zalhana/zahana` — 53 of them in the default view."""
    lex = _fake_lexemes(tmp_path, [(1, 'anteriu', 1), (1, 'antereu', 0)])
    conn = _ui(tmp_path, [('antereu', 0)])
    freq = _freqs(tmp_path, {'antereu': 167, 'anteriu': 1031})   # 6x, under TWIN_RATIO
    mark_dex_variants(conn, lex, freq, _empty_inflected(tmp_path))
    assert conn.execute('SELECT dex_variant FROM words').fetchone()[0] == 0


# ── „vezi X" — the one thing that overrides restriction 1 ─────────────────────

@pytest.mark.parametrize('text,target', [
    ('vezi voluntar',    'voluntar'),
    ('vezi băjenar.',    'băjenar'),
    ('Vezi Nor',         'nor'),          # normalized, like every other form here
    ('vezi bălsămat',    'bălsămat'),
    ('Faptul de a vezi', None),           # not at the start
    ('vezi voluntar, ostaș', None),       # two targets is not a bare pointer
    ('vezi voluntar. Soldat înrolat.', None),
    ('', None),
    (None, None),
])
def test_pointer_target_reads_only_a_bare_pointer(text, target):
    """All 175 pointer rows in the build are exactly „vezi X" with an optional full
    stop. A looser pattern starts reading the first line of definitions that merely
    cross-reference something, and those are real definitions."""
    assert pointer_target(text) == target


def test_a_pointer_definition_beats_restriction_one(tmp_path):
    """`volintir` heads an entry of its own, so restriction 1 keeps it visible — and its
    entire definition is „vezi voluntar". A self-heading form is left alone because it
    carries a sense DEX files separately; an entry whose whole text is a pointer is the
    dictionary saying it does not. 66 words were in that state."""
    lex = _fake_lexemes(tmp_path, [(1, 'volintir', 1)])          # heads its own entry
    conn = _ui(tmp_path, [('volintir', 0, 'vezi voluntar')])
    freq = _freqs(tmp_path, {'volintir': 398, 'voluntar': 1384416})
    mark_dex_variants(conn, lex, freq, _empty_inflected(tmp_path))
    assert conn.execute('SELECT dex_variant, dex_variant_of FROM words').fetchone() \
        == (1, 'voluntar')


def test_a_pointer_needs_no_relation_row_at_all(tmp_path):
    """The prose names the head, so the pair does not have to be linked by EntryLexeme
    for the flag to fire — `țignal · vezi semnal` shares no spelling rule either."""
    lex = _fake_lexemes(tmp_path, [(1, 'țignal', 1), (2, 'semnal', 1)])
    conn = _ui(tmp_path, [('țignal', 0, 'vezi semnal.')])
    freq = _freqs(tmp_path, {'țignal': 347, 'semnal': 2594728})
    mark_dex_variants(conn, lex, freq, _empty_inflected(tmp_path))
    assert conn.execute('SELECT dex_variant_of FROM words').fetchone()[0] == 'semnal'


def test_a_pointer_does_not_waive_the_twin_ratio(tmp_path):
    """The carve-out above is what makes restriction 2 load-bearing rather than
    redundant. „vezi X" says the word has no sense of its own; it does not say X is
    alive. Gated, the 99 unflagged pointers split 31/68, and the 68 all point at a word
    as dead as themselves — `bejănar → băjenar` is 138 occurrences against 8."""
    lex = _fake_lexemes(tmp_path, [(1, 'bejănar', 1), (2, 'băjenar', 1)])
    conn = _ui(tmp_path, [('bejănar', 0, 'vezi băjenar.')])
    freq = _freqs(tmp_path, {'bejănar': 8, 'băjenar': 138})
    mark_dex_variants(conn, lex, freq, _empty_inflected(tmp_path))
    assert conn.execute('SELECT dex_variant FROM words').fetchone()[0] == 0


def test_a_dead_pointer_target_falls_back_to_the_relation(tmp_path):
    """`uiet · vezi huiet` names a twin nobody writes either — but its entry's own head
    is the living `vuiet`. Reading only the prose loses a variant the relation had
    right, which is why the pointer is preferred rather than exclusive."""
    lex = _fake_lexemes(tmp_path, [(1, 'vuiet', 1), (1, 'uiet', 0)])
    conn = _ui(tmp_path, [('uiet', 0, 'vezi huiet')])
    freq = _freqs(tmp_path, {'uiet': 30, 'huiet': 40, 'vuiet': 60000})
    mark_dex_variants(conn, lex, freq, _empty_inflected(tmp_path))
    assert conn.execute('SELECT dex_variant, dex_variant_of FROM words').fetchone() \
        == (1, 'vuiet')


def test_a_pointer_to_itself_is_ignored(tmp_path):
    lex = _fake_lexemes(tmp_path, [(1, 'nor', 1)])
    conn = _ui(tmp_path, [('nor', 0, 'vezi nor')])
    freq = _freqs(tmp_path, {'nor': 261196})
    mark_dex_variants(conn, lex, freq, _empty_inflected(tmp_path))
    assert conn.execute('SELECT dex_variant FROM words').fetchone()[0] == 0


def test_archaic_spelling_gets_first_claim_on_the_overlap(tmp_path):
    """The two flags are separate controls, so they must be disjoint: otherwise
    „grafii vechi: cu" uncovers 127 words that the other row is still hiding."""
    lex = _fake_lexemes(tmp_path, [(1, 'condiție', 1), (1, 'condițiune', 0)])
    conn = _ui(tmp_path, [('condițiune', 1)])                    # already archaic
    freq = _freqs(tmp_path, {'condițiune': 10, 'condiție': 999999})
    mark_dex_variants(conn, lex, freq, _empty_inflected(tmp_path))
    assert conn.execute('SELECT dex_variant FROM words').fetchone()[0] == 0


def test_it_is_idempotent(tmp_path):
    lex = _fake_lexemes(tmp_path, [(1, 'sufragerie', 1), (1, 'sofragerie', 0)])
    conn = _ui(tmp_path, [('sofragerie', 0)])
    freq = _freqs(tmp_path, {'sofragerie': 0, 'sufragerie': 50000})
    infl = _empty_inflected(tmp_path)
    mark_dex_variants(conn, lex, freq, infl)
    first = conn.execute('SELECT * FROM words').fetchall()
    mark_dex_variants(conn, lex, freq, infl)
    assert conn.execute('SELECT * FROM words').fetchall() == first


# ── Against the built database ────────────────────────────────────────────────

@pytest.mark.parametrize('w,head', [
    ('sofragerie', 'sufragerie'),   # the word that started this; `o → u`, no rule can see it
    ('octomvre',   'octombrie'),
    ('stomah',     'stomac'),
    ('țeară',      'țară'),
    ('lăcrăma',    'lăcrima'),      # the nearest head, not the commonest
    ('tinereță',   'tinerețe'),     # surface count, or its own paradigm hides it
])
def test_known_variants_are_flagged_and_named(db, w, head):
    row = word(db, w)
    if row is None:
        return                       # dropped from the shortlist entirely is also fine
    assert row['dex_variant'] == 1, f'{w} is not flagged'
    assert row['dex_variant_of'] == head


@pytest.mark.parametrize('w,head', [
    ('volintir',    'voluntar'),    # heads its own entry; „vezi voluntar" overrides that
    ('țignal',      'semnal'),      # no spelling rule and no relation row links these
    ('contimporan', 'contemporan'),
    ('nuor',        'nor'),
    ('acoperemânt', 'acoperământ'),
])
def test_pointer_definitions_are_flagged_and_named(db, w, head):
    row = word(db, w)
    if row is None:
        return
    assert row['dex_variant'] == 1, f'{w} is not flagged — its definition is only a pointer'
    assert row['dex_variant_of'] == head


def test_no_pointer_definition_survives_with_a_living_target(db):
    """The reader-facing property this is all for: nothing in the default view has „vezi
    X" for a definition while X is an ordinary modern word. What may survive is a pointer
    to a word as forgotten as itself — `desag → desagă`, `flăcăuaș → flăcăiaș` — which is
    two finds, not a dead end. Measured at 8 on the 2026-08-14 build."""
    rows = db.execute(
        "SELECT word FROM words"
        "  WHERE LOWER(TRIM(definition)) GLOB 'vezi *' AND seam = 'relevant'"
        "    AND COALESCE(regional_only, 0) = 0 AND COALESCE(variant_like, 0) = 0"
        "    AND COALESCE(archaic_spelling, 0) = 0 AND COALESCE(dex_variant, 0) = 0"
        "    AND COALESCE(deverbal_like, 0) = 0").fetchall()
    assert len(rows) <= 12, [r['word'] for r in rows]


@pytest.mark.parametrize('w', [
    'antereu', 'amploiat', 'zalhana', 'lighioaie', 'pătlăgea', 'stacan', 'malacof',
    'bejănar', 'jălbar', 'flăcăuaș',   # pointer definitions whose target is dead too
])
def test_variants_of_a_dead_head_stay_visible(db, w):
    row = word(db, w)
    if row is None:
        return
    assert not row['dex_variant'], f'{w} was hidden — its own twin is forgotten too'


def test_the_two_flags_never_both_fire(db):
    n = db.execute('SELECT COUNT(*) FROM words '
                   ' WHERE dex_variant = 1 AND COALESCE(archaic_spelling, 0) = 1'
                   ).fetchone()[0]
    assert n == 0, f'{n} words carry both flags — one control cannot reveal them'


def test_it_flags_a_lot_but_not_the_whole_list(db):
    """Sanity band. It found 1,926 of 18,270 at TWIN_RATIO=20; an order of magnitude
    either way means the relation or the gate broke, not that DEX changed its mind."""
    flagged, total = db.execute(
        'SELECT SUM(COALESCE(dex_variant, 0)), COUNT(*) FROM words').fetchone()
    assert 500 <= flagged <= 4000, flagged
    assert flagged < total / 4


def test_every_flagged_word_names_its_head(db):
    """`dex_variant_of` is what the detail panel prints instead of silently dropping a
    row, so a flag without one is a word hidden with no explanation."""
    n = db.execute("SELECT COUNT(*) FROM words WHERE dex_variant = 1 "
                   "  AND (dex_variant_of IS NULL OR dex_variant_of = '')").fetchone()[0]
    assert n == 0, n


def test_the_default_view_survives_it(db):
    """The point is a cleaner default list, not an empty one."""
    visible = db.execute(
        "SELECT COUNT(*) FROM words WHERE seam = 'relevant'"
        "   AND COALESCE(regional_only, 0) = 0 AND COALESCE(variant_like, 0) = 0"
        "   AND COALESCE(archaic_spelling, 0) = 0 AND COALESCE(dex_variant, 0) = 0"
    ).fetchone()[0]
    assert 1500 <= visible <= 4000, visible


def test_twin_ratio_is_shared_with_the_spelling_rules(db):
    """Both flags answer the same question — is the head overwhelmingly more alive —
    so they must not drift to two different thresholds."""
    assert TWIN_RATIO == 20
