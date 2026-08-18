"""Tests for extract_meanings.py, fixture-driven per CLAUDE.md/senses-plan.md §8.

The rows below are the real `Meaning` rows the dump holds for `bidinea`
(tree 5950) and `zapciu` (tree 61690), traced 2026-08-18, so the extractor can
change without a 1.65 GB rescan to find out what broke.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import extract_meanings as em

# (id, parentId, type, displayOrder, breadcrumb, userId, treeId, internalRep, createDate, modDate)
BIDINEA_TREE = 5950
BIDINEA_ROWS = [
    (20406, 0, 0, 1, '1.', 3, BIDINEA_TREE,
     'Pensulă mare, de obicei rotundă (cu coadă lungă), folosită pentru văruit.', 0, 0),
    (191407, 20406, 2, 2, '', 3, BIDINEA_TREE,
     '$Văruiau cîțiva inși cotețele găinilor – Vino încoa și pune mîna pe bidinea și tu! '
     'i-au poruncit.$ PAS, L. I 97.', 0, 0),
    (191408, 20406, 2, 3, '', 3, BIDINEA_TREE,
     '$În via părăginită iarba... acoperă răzoarele și îneacă cuprinsul într-o verdeață '
     'moale...: parc-ar fi scuturat cineva bidinele muiete în roșu, galben și albastru '
     'pe d-asupra cîmpiei.$ DELAVRANCEA, S. 221.', 0, 0),
    (472138, 20406, 2, 4, '', 3, BIDINEA_TREE, '$Barbe cît badanalele de mari.$ (CR.).', 0, 0),
    (472139, 0, 0, 5, '2.', 3, BIDINEA_TREE, 'Organ genital feminin.', 0, 0),
    (20407, 0, 1, 6, '', 3, BIDINEA_TREE, '@badana@', 0, 0),
]

ZAPCIU_TREE = 61690
ZAPCIU_ROWS = [
    (3988, 0, 0, 1, '1.', 3, ZAPCIU_TREE,
     'Cârmuitor al unei plăși, subordonat ispravnicului (și însărcinat cu strângerea '
     'dărilor).', 0, 0),
    (3990, 3988, 2, 2, '', 3, ZAPCIU_TREE,
     '$Degrabă el trămitea ispravnici, zapcii și pomojnici ca să ridice satele, să sape '
     'și să scormone sălașele de vechi cetăți.$ ODOBESCU, S. II 411.', 0, 0),
    (3991, 3988, 2, 3, '', 3, ZAPCIU_TREE,
     '[Guvernatorii] $tractau pe domnii noștri ca pe niște zapcii, le trimeteau ordine '
     'scrise și verbale și-apoi să nu le fi urmat.$ GHICA, s. A. 30.', 0, 0),
    (3992, 3988, 2, 4, '', 3, ZAPCIU_TREE,
     '$Ispravnicii și mai cu seamă zapciii... găsiră ocaziune a jefui poporul, luînd de '
     'la săteni însutit decît li se ordona.$ I. IONESCU, M. 253.', 0, 0),
    (3993, 3988, 2, 5, '', 3, ZAPCIU_TREE,
     '$Văd îndat-o copiliță, Oltencuță cu ochi viu, Numai zdrențe-a ei fotiță, Cum o bate '
     'un zapciu.$ BOLLIAC, O. 196.', 0, 0),
    (3994, 0, 0, 6, '2.', 3, ZAPCIU_TREE,
     'Grad în armată, echivalent cu cel de căpitan; persoană care avea acest grad.', 0, 0),
    (3995, 3994, 2, 7, '', 3, ZAPCIU_TREE,
     '$Avantgarda se compunea din:... vel-căpitan de dorobanți cu zapciii săi.$ FILIMON, '
     'C. 312.', 0, 0),
    (3996, 0, 0, 8, '3.', 3, ZAPCIU_TREE, 'Agent de poliție; sergent de stradă.', 0, 0),
    (3997, 3996, 2, 9, '', 3, ZAPCIU_TREE,
     '$De dimineață pompierii stropiseră podul, și la toate răspîntenile cîte un zapciu '
     'al agiei oprea carele să nu se vîre, pînă după trecerea alaiului.$ NEGRUZZI, S. I 29.',
     0, 0),
    (3989, 0, 1, 10, '', 3, ZAPCIU_TREE, '@zaptiye@', 0, 0),
]


# zăticni sense 1 ('1.') has empty internalRep in the dump — these are its real
# `Relation` rows (id, meaningId, treeId, type, createDate, modDate), traced 2026-08-18.
# Verified against dexonline's own rendering: it shows this sense's "definition" as the
# comma-joined synonym list, which is exactly the 9 target words below.
ZATICNI_SENSE1_ID = 176698
ZATICNI_SENSE2_ID = 176699
ZATICNI_RELATIONS = [
    (23158, ZATICNI_SENSE1_ID, 15926, 1, 0, 0),
    (23159, ZATICNI_SENSE1_ID, 67982, 1, 0, 0),
    (23160, ZATICNI_SENSE1_ID, 26855, 1, 0, 0),
    (23161, ZATICNI_SENSE1_ID, 29863, 1, 0, 0),
    (23162, ZATICNI_SENSE1_ID, 53937, 1, 0, 0),
    (23163, ZATICNI_SENSE1_ID, 54289, 1, 0, 0),
    (23164, ZATICNI_SENSE1_ID, 55245, 1, 0, 0),
    (23165, ZATICNI_SENSE1_ID, 58864, 1, 0, 0),
    (23173, ZATICNI_SENSE1_ID, 27568, 1, 0, 0),
    (23168, ZATICNI_SENSE2_ID, 68791, 1, 0, 0),
    (23169, ZATICNI_SENSE2_ID, 39344, 1, 0, 0),
]
# Tree rows (id, description, descriptionSort, status, createDate, modDate) for the
# targets above, plus one unrelated tree that pass_relation_targets() must ignore.
ZATICNI_SYNONYM_TREES = [
    (15926, 'deranja', 'deranja', 0, 0, 0),
    (67982, 'incomoda', 'incomoda', 0, 0, 0),
    (26855, 'împiedica', 'împiedica', 0, 0, 0),
    (29863, 'jena', 'jena', 0, 0, 0),
    (53937, 'stânjeni', 'stânjeni', 0, 0, 0),
    (54289, 'stingheri', 'stingheri', 0, 0, 0),
    (55245, 'supăra', 'supăra', 0, 0, 0),
    (58864, 'tulbura', 'tulbura', 0, 0, 0),
    (27568, 'încurca', 'încurca', 0, 0, 0),
    (68791, 'întrerupe', 'întrerupe', 0, 0, 0),
    (39344, 'opri', 'opri', 0, 0, 0),
    (99999999, 'cuvânt neinteresant', 'cuvânt neinteresant', 0, 0, 0),
]


def _as_meaning_line(rows: list[tuple]) -> str:
    """Render fixture rows into one `INSERT INTO \\`Meaning\\` VALUES (...)` line,
    the shape pass_meaning() reads off disk."""
    def q(v):
        if isinstance(v, str):
            return "'" + v.replace('\\', '\\\\').replace("'", "\\'") + "'"
        return str(v)

    tuples = ','.join('(' + ','.join(q(v) for v in row) + ')' for row in rows)
    return f'INSERT INTO `Meaning` VALUES {tuples};\n'


def _as_relation_line(rows: list[tuple]) -> str:
    tuples = ','.join('(' + ','.join(str(v) for v in row) + ')' for row in rows)
    return f'INSERT INTO `Relation` VALUES {tuples};\n'


def _as_tree_line(rows: list[tuple]) -> str:
    def q(v):
        if isinstance(v, str):
            return "'" + v.replace('\\', '\\\\').replace("'", "\\'") + "'"
        return str(v)

    tuples = ','.join('(' + ','.join(q(v) for v in row) + ')' for row in rows)
    return f'INSERT INTO `Tree` VALUES {tuples};\n'


def _run_pass_meaning(rows: list[tuple], tree_word: dict[int, str], tmp_path) -> list[tuple]:
    sql_path = tmp_path / 'dump.sql'
    sql_path.write_text(_as_meaning_line(rows), encoding='utf-8')
    orig = em.SQL_PATH
    em.SQL_PATH = sql_path
    try:
        return list(em.pass_meaning(tree_word))
    finally:
        em.SQL_PATH = orig


def test_bidinea_two_senses_with_citations_and_etymon(tmp_path):
    out = _run_pass_meaning(BIDINEA_ROWS, {BIDINEA_TREE: 'bidinea'}, tmp_path)
    senses = [r for r in out if r[4] == 0]
    assert len(senses) == 2
    sense2 = next(r for r in senses if r[5] == '2.')
    assert sense2[7] == 'Organ genital feminin.'

    sense1 = next(r for r in senses if r[5] == '1.')
    cites1 = [r for r in out if r[4] == 2 and r[3] == sense1[0]]
    cites2 = [r for r in out if r[4] == 2 and r[3] == sense2[0]]
    assert len(cites1) == 3
    assert len(cites2) == 0

    etym = [r for r in out if r[4] == 1]
    assert len(etym) == 1
    assert etym[0][7] == 'badana'


def test_zapciu_three_senses_six_citations_attached_correctly(tmp_path):
    out = _run_pass_meaning(ZAPCIU_ROWS, {ZAPCIU_TREE: 'zapciu'}, tmp_path)
    senses = {r[5]: r for r in out if r[4] == 0}
    assert set(senses) == {'1.', '2.', '3.'}

    cites = [r for r in out if r[4] == 2]
    assert len(cites) == 6
    by_parent: dict[int, int] = {}
    for c in cites:
        by_parent[c[3]] = by_parent.get(c[3], 0) + 1
    assert by_parent[senses['1.'][0]] == 4
    assert by_parent[senses['2.'][0]] == 1
    assert by_parent[senses['3.'][0]] == 1


def test_type3_comment_row_is_not_filtered_here(tmp_path):
    """extract_meanings.py writes a faithful copy; type=3 filtering is
    merge_senses()'s job, not the extractor's."""
    rows = ZAPCIU_ROWS + [
        (999999, 0, 3, 11, '', 3, ZAPCIU_TREE, 'Ac', 0, 0),
    ]
    out = _run_pass_meaning(rows, {ZAPCIU_TREE: 'zapciu'}, tmp_path)
    comments = [r for r in out if r[4] == 3]
    assert len(comments) == 1
    assert comments[0][7] == 'Ac'


def test_word_with_tree_and_no_meanings_yields_nothing(tmp_path):
    out = _run_pass_meaning([], {12345: 'nimicuță'}, tmp_path)
    assert out == []


def test_pass_meaning_ignores_trees_outside_the_shortlist(tmp_path):
    out = _run_pass_meaning(BIDINEA_ROWS, {999: 'altceva'}, tmp_path)
    assert out == []


def test_empty_text_sense_with_children_is_written_as_is(tmp_path):
    """extract_meanings.py does not drop empty-text senses — merge_senses() does,
    re-attaching their citations to the nearest non-empty ancestor. Here we only
    check the raw pass-through keeps the empty row."""
    rows = [
        (1, 0, 0, 1, '1.', 3, 42, '', 0, 0),          # empty top sense
        (2, 1, 0, 2, '1.1.', 3, 42, 'Un sens real.', 0, 0),
        (3, 1, 2, 3, '', 3, 42, '$O citație.$ X, Y 1.', 0, 0),
    ]
    out = _run_pass_meaning(rows, {42: 'exemplu'}, tmp_path)
    empty = [r for r in out if r[0] == 1]
    assert len(empty) == 1
    assert empty[0][7] == ''


def _run_relation_passes(relation_rows, tree_rows, sense_ids, tmp_path):
    sql_path = tmp_path / 'dump.sql'
    sql_path.write_text(_as_relation_line(relation_rows) + _as_tree_line(tree_rows),
                         encoding='utf-8')
    orig = em.SQL_PATH
    em.SQL_PATH = sql_path
    try:
        relations = list(em.pass_relation(sense_ids))
        target_tree_ids = {tid for _, _, tid in relations}
        target_word = em.pass_relation_targets(target_tree_ids)
        return relations, target_word
    finally:
        em.SQL_PATH = orig


def test_zaticni_sense1_synonyms_match_dexonlines_rendering(tmp_path):
    """Sense 1 has empty internalRep; dexonline shows its 'definition' as the
    9-word synonym list resolved here. This is the case that motivated the
    Relation pass — see the module docstring."""
    relations, target_word = _run_relation_passes(
        ZATICNI_RELATIONS, ZATICNI_SYNONYM_TREES,
        {ZATICNI_SENSE1_ID, ZATICNI_SENSE2_ID}, tmp_path)

    sense1_rels = sorted(r for r in relations if r[1] == ZATICNI_SENSE1_ID)
    words = [target_word[tid] for _, _, tid in sense1_rels]
    assert words == ['deranja', 'incomoda', 'împiedica', 'jena', 'stânjeni',
                      'stingheri', 'supăra', 'tulbura', 'încurca']

    sense2_rels = sorted(r for r in relations if r[1] == ZATICNI_SENSE2_ID)
    assert [target_word[tid] for _, _, tid in sense2_rels] == ['întrerupe', 'opri']

    # The unrelated tree (99999999) must never surface — pass_relation_targets()
    # only resolves ids pass_relation() actually asked for.
    assert 'cuvânt neinteresant' not in target_word.values()


def test_pass_relation_ignores_meanings_outside_scope(tmp_path):
    """A Relation row whose meaningId isn't in `sense_ids` (e.g. it belongs to a
    word outside this run's shortlist) must not be yielded."""
    relations, _ = _run_relation_passes(
        ZATICNI_RELATIONS, ZATICNI_SYNONYM_TREES, {ZATICNI_SENSE2_ID}, tmp_path)
    assert all(r[1] == ZATICNI_SENSE2_ID for r in relations)
    assert len(relations) == 2


def test_pass_relation_type_filter_excludes_non_synonym_relations(tmp_path):
    """Only `type=1` is treated as synonym; another type must be dropped even
    when its meaningId is in scope."""
    rows = ZATICNI_RELATIONS + [(99999, ZATICNI_SENSE1_ID, 15926, 2, 0, 0)]
    relations, _ = _run_relation_passes(
        rows, ZATICNI_SYNONYM_TREES, {ZATICNI_SENSE1_ID}, tmp_path)
    assert all(r[0] != 99999 for r in relations)
