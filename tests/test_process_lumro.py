"""Guards for the LUMRO ingest — chiefly its document unit.

`process_lumro` counts distinct **authors**, not novels, as the document count, because
`validate_diachronic.verdict()` reads `hist_docs >= 2` as "attested in more than one
place". Three novels by one novelist are one writer's vocabulary, not three independent
attestations. Measured when this was introduced: of the 1,425 shortlist words whose
attestation LUMRO supplies, 638 came from a single author.

The obvious "simplification" is to count novels. These tests exist to fail if it happens.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import process_lumro as pl

DEX = {'cuvânt', 'jupâneșică', 'altul'}


def novel(author, text, year=1890, title='T'):
    return (year, author, title, text)


def test_three_novels_by_one_author_are_one_document():
    """The case that motivated the whole choice: `jupâneșică` at 47 occurrences, every
    one of them V.A. Urechia, was reading as multi-document attestation."""
    novels = [
        novel('V.A. Urechia', 'jupâneșică jupâneșică'),
        novel('V.A. Urechia', 'jupâneșică'),
        novel('V.A. Urechia', 'jupâneșică'),
    ]
    c = pl.count_novels(novels, DEX)
    assert c.occurrences['jupâneșică'] == 4, 'occurrences still sum over every novel'
    assert c.documents['jupâneșică'] == 1, 'but three novels by one author are one source'
    assert c.novels_with['jupâneșică'] == 3, 'the novel count is still reported'


def test_distinct_authors_count_separately():
    novels = [novel('A. Unu', 'cuvânt'), novel('B. Doi', 'cuvânt'), novel('C. Trei', 'cuvânt')]
    c = pl.count_novels(novels, DEX)
    assert c.documents['cuvânt'] == 3


def test_unattributed_novels_do_not_merge_into_one_phantom_author():
    """Two files with no parseable author are two sources, not one — otherwise a
    filename-format change would quietly collapse independent evidence."""
    novels = [novel(None, 'cuvânt'), novel(None, 'cuvânt')]
    c = pl.count_novels(novels, DEX)
    assert c.documents['cuvânt'] == 2


def test_only_dex_forms_are_counted():
    c = pl.count_novels([novel('A. Unu', 'cuvânt necuvânt zzz')], DEX)
    assert set(c.occurrences) == {'cuvânt'}
    assert c.total_tokens == 3, 'tokens counts everything; only matches are kept'
    assert c.matched == 1


def test_cedilla_diacritics_are_normalized_before_lookup():
    """LUMRO is overwhelmingly cedilla-form (`ş` 1,994 vs `ș` 13 in one sampled novel),
    so a lookup against comma-form DEX entries fails entirely without this."""
    assert pl.normalize('JUPÂNEŞICĂ') == 'jupâneșică'
    c = pl.count_novels([novel('A. Unu', 'JUPÂNEŞICĂ')], DEX)
    assert c.occurrences.get('jupâneșică') == 1


def test_tokenizer_matches_the_wikisource_panel():
    """The two historical corpora are summed, so they must tokenize identically —
    short tokens dropped, hyphens kept inside a word."""
    assert pl.tokenize('a ab abc bine-cunoscut') == ['abc', 'bine-cunoscut']
