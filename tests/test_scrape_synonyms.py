"""Parser tests for scrape_synonyms.py.

All offline — the strings below are real entry bodies copied from dexonline.ro, so the
parser can be changed without hitting a community-run site to find out what broke.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import scrape_synonyms as ss

CURAJOS = (
    'CURAJOS adj., adv. 1. adj. brav, cutezător, dârz, inimos, îndrăzneț, neînfricat, '
    'semeț, viteaz, (livr.) intrepid, petulant, temerar, (rar) bărbat, (înv. și pop.) '
    'voinic, (înv.) hrăbor, neînfricoșat. (Om ~.) 2. adj. bărbătesc, viteaz, vitejesc, '
    '(reg.) bărbătos. (Atitudine, faptă ~oasă.)'
)


def test_extracts_synonyms_in_order():
    out = ss.parse_word_list(CURAJOS, 'curajos')
    assert out[:4] == ['brav', 'cutezător', 'dârz', 'inimos']


def test_drops_register_markers_but_keeps_the_words_they_mark():
    out = ss.parse_word_list(CURAJOS, 'curajos')
    assert 'intrepid' in out and 'hrăbor' in out
    assert not any('livr' in w or 'înv' in w or 'rar' == w for w in out)


def test_drops_usage_examples():
    """`(Om ~.)` and `(Atitudine, faptă ~oasă.)` are examples, not synonyms."""
    out = ss.parse_word_list(CURAJOS, 'curajos')
    assert not any('~' in w for w in out)
    assert 'Om' not in out and 'Atitudine' not in out


def test_drops_the_headword_itself():
    assert 'curajos' not in [w.lower() for w in ss.parse_word_list(CURAJOS, 'curajos')]


def test_deduplicates_across_senses():
    out = ss.parse_word_list(CURAJOS, 'curajos')
    assert out.count('viteaz') == 1          # appears in senses 1 and 2


def test_strips_a_headword_that_the_markup_did_not_fence_off():
    """One page carries several entries and each opens with its own capitalised
    headword, sometimes without a separator: "ROZĂ     trandafir, rug"."""
    out = ss.parse_word_list('ROZĂ s. trandafir, rug, rujă. ROZ adj. trandafiriu', 'roză')
    assert 'trandafir' in out
    assert not any(w.isupper() for w in out)
    assert 'ROZĂ' not in out and 'ROZ' not in out


def test_drops_see_also_cross_references():
    """`v. rozetă` points at another entry; it is not a synonym."""
    assert ss.parse_word_list('ROZĂ s. v. rozetă.', 'roză') == []


def test_collapses_internal_whitespace():
    out = ss.parse_word_list('NĂDUȘI vb. a   înnăduși, gâtui', 'năduși')
    assert 'a înnăduși' in out


def test_multi_word_synonyms_survive_but_sentences_do_not():
    out = ss.parse_word_list(
        'X s. a-și da duhul, o expresie mult prea lungă ca să fie un sinonim real aici',
        'x')
    assert 'a-și da duhul' in out
    assert not any(len(w) > 40 for w in out)


def test_fold_ignores_case_diacritics_and_stress():
    assert ss._fold('ROZĂ') == ss._fold('roză') == 'roza'
    assert ss._fold('CURAJ Ó S'.replace(' ', '')) == 'curajos'


def test_entry_headword_reads_both_formats():
    assert ss._entry_headword('ROZĂ s. trandafir') == 'ROZĂ'
    assert ss._entry_headword('CELE ZECE PORUNCI decalogul') == 'CELE ZECE PORUNCI'
    # Antonime entries are ordinary case: "Curajos ≠ fricos, laș"
    assert ss._entry_headword('Curajos ≠ fricos, laș') == 'Curajos'


def test_delay_floor_is_enforced(monkeypatch, capsys):
    """dexonline.ro is community-run; the script must refuse to hammer it."""
    monkeypatch.setattr(sys, 'argv', ['scrape_synonyms.py', '--delay', '0.1'])
    assert ss.main() == 1
    assert 'Refusing' in capsys.readouterr().err
