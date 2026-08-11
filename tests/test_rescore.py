"""Regression guards for the 2026-08-07 data-quality rescore.

Two kinds of test live here:

* **Unit** — the aggregation and verdict logic, on synthetic data. Always run.
* **Integration** — assertions against the built `public/data/ui.db`, skipped when it
  is absent so a fresh checkout still gets a green suite. These are the ones that would
  catch a threshold being retuned into nonsense, because they name actual words.

The control words come from `tests/fixtures/rescore_baseline.json`, captured before the
rescore. See docs/activity-history.md for the measurements behind each group.
"""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import validate_diachronic as vd

UI_DB = Path(__file__).parent.parent / 'public' / 'data' / 'ui.db'
BASELINE = Path(__file__).parent / 'fixtures' / 'rescore_baseline.json'


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


# ── Paradigm aggregation ──────────────────────────────────────────────────────

def test_aggregate_rolls_inflected_forms_into_the_lemma():
    """The bug this fixes: `înmărmuri` scored 317 while `înmărmurit` alone was 5,846."""
    freqs = {'înmărmuri': (317, 100), 'înmărmurit': (5846, 900)}
    form_lemma = {'înmărmuri': ['înmărmuri'], 'înmărmurit': ['înmărmuri']}
    out = vd.aggregate_by_family(freqs, form_lemma)
    assert out['înmărmuri'][0] == 317 + 5846


def test_aggregate_splits_a_shared_form_by_headword_prominence():
    """`veșcă` (sieve rim) must not inherit `veste`'s (news) 339k via their shared plural."""
    freqs = {'veste': (576766, 1000), 'veșcă': (264, 20), 'vești': (300000, 800)}
    form_lemma = {'veste': ['veste'], 'veșcă': ['veșcă'], 'vești': ['veste', 'veșcă']}
    out = vd.aggregate_by_family(freqs, form_lemma)
    assert out['veșcă'][0] < 1000        # keeps roughly its own count
    assert out['veste'][0] > 800_000     # takes essentially all of the shared form


def test_aggregate_documents_never_exceed_the_largest_contributing_form():
    """Documents are a max, not a sum — summing double-counts a document holding two
    forms of the same lemma."""
    freqs = {'a': (10, 7), 'b': (10, 3)}
    out = vd.aggregate_by_family(freqs, {'a': ['lemma'], 'b': ['lemma']})
    assert out['lemma'][1] == 7


def test_aggregate_credits_documents_to_a_non_dominant_claimant():
    """`văz` took 10.8% of a form seen in 392 documents and was credited 0 of them, because
    documents used to require a >= 50% share. With 96 occurrences and 0 documents it failed
    `verdict`'s `hist_docs >= 2` and came out `absent` while sitting in the relevant seam."""
    freqs = {'văz': (888, 392), 'vedea': (7000, 3000)}
    form_lemma = {'văz': ['văz', 'vedea']}
    out = vd.aggregate_by_family(freqs, form_lemma)
    assert out['văz'][1] > 0, 'a minority claimant still appears in documents'
    assert out['văz'][1] < out['vedea'][1], 'and in fewer of them than the dominant lemma'


def test_aggregate_document_share_matches_occurrence_share():
    """Documents and occurrences are split by the same share, so the two stay on the footing
    `verdict` compares them on."""
    freqs = {'shared': (1000, 500), 'big': (9000, 0), 'small': (0, 0)}
    out = vd.aggregate_by_family(freqs, {'shared': ['big', 'small']})
    # `small` carries only the smoothing prior, so it takes a tiny, equal slice of both.
    assert out['small'][0] / 1000 == pytest.approx(out['small'][1] / 500, rel=0.02)


def test_loose_aggregation_over_counts_on_purpose():
    """The loose/disambiguated ratio is the archaic-variant signal, so it must not
    do the splitting."""
    freqs = {'vești': (300000, 800)}
    form_lemma = {'vești': ['veste', 'veșcă']}
    loose = vd.aggregate_loose(freqs, form_lemma)
    assert loose['veste'] == loose['veșcă'] == 300000


def test_aggregate_without_a_map_is_a_passthrough():
    freqs = {'x': (5, 2)}
    assert vd.aggregate_by_family(freqs, {}) == freqs


# ── Verdict thresholds ────────────────────────────────────────────────────────

def test_verdict_uses_counts_not_ppm():
    """zapciu had 1,322 modern occurrences and was called `extinct`, because the shared
    0.1 ppm floor meant '< 1,697 hits' in a 17B-token corpus. At its paradigm count of
    1,747 it now reads `declining` — still on the list, but no longer called dead."""
    assert vd.verdict(hist_occ=41, hist_docs=21, modern_occ=1747,
                      rank_shift=0.07) == 'declining'
    assert vd.verdict(hist_occ=41, hist_docs=21, modern_occ=5000,
                      rank_shift=0.07) == 'alive'


def test_verdict_extinct_requires_zero_modern_occurrences():
    assert vd.verdict(10, 5, 0, 0.5) == 'extinct'
    assert vd.verdict(10, 5, 1, 0.5) == 'historical_only'


def test_verdict_ignores_single_document_attestation():
    """15 occurrences inside one Wikisource text is a quirk of that text, not evidence."""
    assert vd.verdict(hist_occ=15, hist_docs=1, modern_occ=3, rank_shift=0.5) == 'absent'
    assert vd.verdict(hist_occ=15, hist_docs=2, modern_occ=3, rank_shift=0.5) == 'historical_only'


def test_verdict_declining_band():
    lo, hi = vd.MODERN_RARE_OCC, vd.MODERN_ALIVE_OCC
    assert vd.verdict(50, 10, lo - 1, 0.2) == 'historical_only'
    assert vd.verdict(50, 10, lo, 0.2) == 'declining'
    assert vd.verdict(50, 10, hi, 0.2) == 'alive'


# ── Integration: the built database ───────────────────────────────────────────

def _rare_floor():
    """The `rare` floor the build actually used, not the unscaled constant.

    `MODERN_RARE_OCC` is calibrated against a modern panel of a particular size and
    `scaled_modern_thresholds()` rescales it when that panel grows, so a test pinned to
    the bare constant fails the moment a modern corpus is added — which is exactly what
    happened when CoRoLa was briefly wired in. Derive it the way the pipeline does.
    """
    freq_db = Path(__file__).parent.parent / 'data' / 'processed' / 'corpus_frequencies.db'
    if not freq_db.exists():
        return vd.MODERN_RARE_OCC
    conn = sqlite3.connect(f'file:{freq_db}?mode=ro', uri=True)
    try:
        tokens = sum(vd.get_corpus_tokens(conn, c) for c in vd.MODERN_CORPORA)
    finally:
        conn.close()
    return vd.scaled_modern_thresholds(tokens)[0]


def test_no_alive_word_is_labelled_forgotten(db):
    """Nothing in the list may carry an extinct/historical verdict while being common."""
    floor = _rare_floor()
    bad = db.execute(
        "SELECT word, modern_occ, verdict FROM words "
        " WHERE verdict IN ('extinct','historical_only') "
        "   AND modern_occ >= ?", (floor,)).fetchall()
    assert bad == [], [dict(r) for r in bad[:10]]


def test_modern_thresholds_scale_with_the_panel():
    """Adding a modern corpus must raise the bar in step, or every word within the
    growth margin of a threshold crosses it on arithmetic alone."""
    base = vd.CALIBRATION_MODERN_TOKENS
    assert vd.scaled_modern_thresholds(base) == (vd.MODERN_RARE_OCC, vd.MODERN_ALIVE_OCC)
    rare2, alive2 = vd.scaled_modern_thresholds(base * 2)
    assert (rare2, alive2) == (vd.MODERN_RARE_OCC * 2, vd.MODERN_ALIVE_OCC * 2)
    assert vd.scaled_modern_thresholds(0) == (vd.MODERN_RARE_OCC, vd.MODERN_ALIVE_OCC)


def test_corola_is_not_in_the_modern_panel():
    """CoRoLa spans 1945+, so presence in it is not evidence of *current* use: it
    over-represents `condițiune` 112x and `dorobanț` 41x against CulturaX, and wiring it
    in removed `birjă`, `dorobanț` and `vechil` from the relevant seam."""
    assert vd.COROLA_CORPUS not in vd.MODERN_CORPORA
    assert vd.COROLA_CORPUS not in vd.HIST_CORPORA


def test_extinct_words_have_no_modern_occurrences(db):
    bad = db.execute(
        "SELECT word, modern_occ FROM words WHERE verdict='extinct' AND modern_occ > 0"
    ).fetchall()
    assert bad == [], [dict(r) for r in bad[:10]]


def test_loose_count_is_never_below_the_disambiguated_one(db):
    bad = db.execute(
        'SELECT word, modern_occ, modern_occ_loose FROM words '
        ' WHERE modern_occ_loose IS NOT NULL AND modern_occ IS NOT NULL '
        '   AND modern_occ_loose < modern_occ').fetchall()
    assert bad == [], [dict(r) for r in bad[:10]]


def test_seams_are_disjoint_and_non_empty(db):
    seams = dict(db.execute(
        "SELECT seam, COUNT(*) FROM words WHERE word_tier='forgotten' GROUP BY seam"))
    assert seams.get('relevant', 0) > 0
    assert seams.get('curiosity', 0) > 0
    assert set(seams) <= {'relevant', 'curiosity'}


def test_relevant_seam_is_a_reviewable_size(db):
    """It is the default view and the thing markers work through. If a retune blows it
    past a few thousand, the point of the split has been lost."""
    n = db.execute(
        "SELECT COUNT(*) FROM words WHERE word_tier='forgotten' AND seam='relevant'"
    ).fetchone()[0]
    assert 1000 <= n <= 4000, n


def test_relevant_seam_contains_hideable_words(db):
    """The seam is decided by score alone, and regional/variant words carry no score
    penalty — so the relevant seam must hold some of each. Otherwise the UI's
    `regional` / `variants` class controls have nothing to reveal on „cu" or „doar",
    which is exactly the bug this arrangement replaced. (`proper_noun_like` went the
    other way: it narrowed to 2 words, so it stopped being a default hide at all.)
    """
    regional, variant = db.execute(
        "SELECT SUM(regional_only = 1), SUM(variant_like = 1) "
        "  FROM words WHERE seam='relevant' AND word_tier='forgotten'").fetchone()
    assert regional > 0, 'no regional words in the relevant seam — toggle is dead'
    assert variant > 0, 'no variant words in the relevant seam — toggle is dead'


def test_default_view_hides_them_anyway(db):
    """Hiding is the UI's job, and the default is still a clean list."""
    total, visible = db.execute(
        "SELECT COUNT(*),"
        "       SUM(COALESCE(regional_only,0)=0 AND COALESCE(variant_like,0)=0"
        "           AND COALESCE(archaic_spelling,0)=0)"
        "  FROM words WHERE seam='relevant' AND word_tier='forgotten'").fetchone()
    assert 1000 <= visible <= 4000, visible
    assert visible < total, 'nothing is being hidden — the toggles would be pointless'


def test_pos_covers_almost_everything(db):
    """`dex_pos` came from meaning-level taxonomy tags and covered 2.9% of the list, so
    every option in the POS filter matched a handful of words or none at all. It is
    derived from `Lexeme.modelType` now."""
    covered, total = db.execute(
        "SELECT SUM(dex_pos IS NOT NULL AND dex_pos != ''), COUNT(*) FROM words"
    ).fetchone()
    assert covered / total > 0.95, f'{covered}/{total}'


@pytest.mark.parametrize('pos', [
    'substantiv feminin', 'substantiv masculin', 'substantiv neutru',
    'adjectiv', 'verb',
])
def test_every_main_pos_option_matches_a_useful_number(db, pos):
    """Each of these returned 0–13 words before the fix; `verb` returned zero."""
    n = db.execute(
        "SELECT COUNT(*) FROM words WHERE word_tier='forgotten' AND seam='relevant'"
        "   AND ('|' || dex_pos || '|') LIKE ?", (f'%|{pos}|%',)).fetchone()[0]
    assert n > 100, f'{pos}: {n}'


def test_pos_prefers_the_inflection_model_over_meaning_tags(db):
    """`visternic` is modelType M. The DEX entry also covers the feminine `vistiernică`,
    and the meaning-level tag bled across, labelling the word "substantiv feminin"."""
    row = word(db, 'visternic')
    if row is None:
        pytest.skip('visternic not in the shortlist')
    assert 'substantiv masculin' in (row['dex_pos'] or '')
    assert 'substantiv feminin' not in (row['dex_pos'] or '')


def test_the_rare_tier_is_gone(db):
    """The `rare_in_use` tab was decided by wordfreq's Romanian list, which scores 99.6%
    of our candidates at exactly 0.00 — so its lowest real scores were ordinary words
    (`haz`, `bețiv`) while `zapciu` and `vornic` were indistinguishable at zero. No
    threshold could fix that, and all 219 rows were words this pipeline had already
    measured against 17B tokens and correctly called still-used."""
    n = db.execute(
        "SELECT COUNT(*) FROM words WHERE word_tier='rare_in_use'").fetchone()[0]
    assert n == 0, n


def test_modern_band_points_the_right_way(db):
    """**More modern usage is better material here, not worse.**

    This is the one property of `modern_band` that is easy to invert by accident, because
    it reads backwards: the words with a couple of thousand modern occurrences are the
    ones people recognise as forgotten, while the words at zero are dictionary ghosts
    that never really circulated. Sorting on rarity alone puts the ghosts first — the
    same mistake `$SORT_OPTIONS` records for `sort=rare`.
    """
    if word(db, 'zapciu') is None or 'modern_band' not in word(db, 'zapciu').keys():
        pytest.skip('modern_band not in this ui.db')

    for w in ('zapciu', 'birjă', 'vechil'):
        row = word(db, w)
        if row is None:
            continue
        assert row['modern_band'] == 2, f'{w} should be in the top band, got {row["modern_band"]}'

    for w in ('celșag', 'barabor', 'racaleț'):
        row = word(db, w)
        if row is None:
            continue
        assert row['modern_band'] == 0, f'{w} should be band 0, got {row["modern_band"]}'


def test_modern_band_covers_every_scored_word(db):
    """A NULL band would silently drop the row from every one of the filter's options,
    which looks like the word not being a candidate rather than a gap in the column."""
    n = db.execute(
        'SELECT COUNT(*) FROM words WHERE modern_occ IS NOT NULL AND modern_band IS NULL'
    ).fetchone()[0]
    assert n == 0, n


def test_proper_noun_flag_does_not_catch_ordinary_words(db):
    """`gheb` ("cocoașă") was hidden because DEX also lists the surname `Gheb`. The flag
    now means "DEX knows this *only* as a capitalised headword"."""
    row = word(db, 'gheb')
    if row is None:
        pytest.skip('gheb not in the shortlist')
    assert row['proper_noun_like'] == 0


@pytest.mark.parametrize('w', [
    # Common words the old thresholds called extinct or declining.
    'vapor', 'fluviu', 'cioban', 'palid', 'viclean', 'colac', 'corabie',
])
def test_common_words_left_the_list(db, w):
    assert word(db, w) is None, f'{w} is still in the shortlist'


@pytest.mark.parametrize('w', [
    # Genuinely faded, well attested, no common relative — the target profile.
    'livede', 'arșic', 'loitră', 'ghizd', 'olat', 'veleat', 'jiganie', 'pogace',
])
def test_target_words_are_present(db, w):
    row = word(db, w)
    assert row is not None, f'{w} dropped out of the shortlist'
    assert row['verdict'] in ('extinct', 'historical_only', 'declining', 'absent')


@pytest.mark.parametrize('w', [
    'jbârc', 'nejid', 'hâșăi', 'zăplad',   # tagged regional or popular-only
    'politeță', 'tinereță', 'veșcă',       # archaic spelling of a word still in use
])
def test_noise_words_are_out_of_the_default_view(db, w):
    """Out of the *default view* — which is the seam plus the three hide-flags, not the
    seam alone. A word may legitimately score into `relevant` and still be hidden."""
    row = word(db, w)
    if row is None:
        return                                        # dropped entirely is also fine
    hidden = (row['seam'] == 'curiosity'
              or row['regional_only'] == 1
              or row['variant_like'] == 1
              or row['archaic_spelling'] == 1)
    assert hidden, f'{w} is visible in the default view'


def test_untagged_obscurities_rank_below_well_attested_words(db):
    """`barabor` carries no register tag at all, so neither the regional nor the variant
    penalty touches it, and it does reach the relevant seam. That is defensible — it is
    genuinely extinct — but on 11 historical occurrences it must sit near the bottom,
    not at the top where the old modern_ppm sort put it.
    """
    row = word(db, 'barabor')
    if row is None:
        pytest.skip('barabor not in the shortlist')
    rank, total = db.execute(
        "SELECT (SELECT COUNT(*) FROM words w2 "
        "          WHERE w2.seam='relevant' AND w2.word_tier='forgotten'"
        "            AND w2.quality_score > w.quality_score) + 1,"
        "       (SELECT COUNT(*) FROM words"
        "          WHERE seam='relevant' AND word_tier='forgotten')"
        "  FROM words w WHERE w.word = 'barabor'").fetchone()
    assert rank > total / 2, f'barabor ranks {rank} of {total}'


def test_baseline_fixture_still_describes_the_same_words():
    """Guards the fixture itself: if it is regenerated from post-rescore data the
    before/after comparison in the docs silently stops meaning anything."""
    data = json.loads(BASELINE.read_text(encoding='utf-8'))
    groups = data['groups']
    assert groups['must_leave_extinct_declining']['vapor']['verdict'] == 'declining'
    assert groups['must_leave_default_view']['barabor']['verdict'] == 'historical_only'


# ── Share-link durability ─────────────────────────────────────────────────────

def test_word_ids_are_unique_and_complete(db):
    total, with_id, distinct = db.execute(
        'SELECT COUNT(*), COUNT(word_id), COUNT(DISTINCT word_id) FROM words').fetchone()
    assert total == with_id == distinct


def test_word_ids_file_is_append_only():
    """The one irreversible thing in a rebuild: `?w=` links break silently if an id is
    ever renumbered. tools/word_ids.py must only ever append."""
    import subprocess
    repo = Path(__file__).parent.parent
    head = subprocess.run(['git', 'show', 'HEAD:data/word_ids.tsv'],
                          capture_output=True, text=True, cwd=repo)
    if head.returncode != 0:
        pytest.skip('data/word_ids.tsv not in HEAD')
    old = head.stdout.splitlines()
    new = (repo / 'data' / 'word_ids.tsv').read_text(encoding='utf-8').splitlines()
    assert new[:len(old)] == old, 'existing word ids changed — shared links would break'
