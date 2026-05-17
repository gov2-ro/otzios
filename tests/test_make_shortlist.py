import csv
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import make_shortlist as ms


def make_diachronic_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        'word', 'dex_frequency', 'description', 'rarity_category',
        'hist_occurrences', 'hist_documents', 'hist_ppm',
        'modern_occurrences', 'modern_documents', 'modern_ppm',
        'log_ratio', 'verdict',
        'dex_pos', 'dex_register', 'dex_domain', 'dex_etymology',
        'has_definition',
    ]
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({f: row.get(f, '') for f in fields})


BASE_ROW = {
    'word': 'ajutoriu',
    'dex_frequency': '0.4',
    'description': 'adj.',
    'rarity_category': 'rare',
    'hist_occurrences': '5', 'hist_documents': '3', 'hist_ppm': '1.2',
    'modern_occurrences': '0', 'modern_documents': '0', 'modern_ppm': '0.0',
    'log_ratio': '3.5',
    'verdict': 'extinct',
    'dex_pos': 'adjectiv',
    'dex_register': '', 'dex_domain': '', 'dex_etymology': 'slavă',
    'has_definition': '1',
}


def test_has_definition_in_out_fields():
    assert 'has_definition' in ms.OUT_FIELDS


def test_has_definition_passes_through_to_output(tmp_path):
    inp = tmp_path / 'diachronic.csv'
    out = tmp_path / 'shortlist.csv'
    make_diachronic_csv(inp, [BASE_ROW])

    sys.argv = ['make_shortlist.py', '--input', str(inp), '--output', str(out)]
    ms.main()

    rows = list(csv.DictReader(out.open(encoding='utf-8')))
    assert len(rows) == 1
    assert rows[0]['has_definition'] == '1'


ANGLICISM_ROW = {
    **BASE_ROW,
    'word': 'sendviș',
    'dex_etymology': 'anglicism',
    'has_definition': '0',
}

ABSENT_ROW = {
    **BASE_ROW,
    'word': 'lăut',
    'verdict': 'absent',
    'hist_ppm': '0.0',
    'dex_register': 'învechit',
    'dex_etymology': '',
    'has_definition': '1',
}


def test_classify_excludes_matching_etymology():
    row = {**ANGLICISM_ROW}
    result = ms.classify(row, exclude_etym=frozenset({'anglicism'}))
    assert result is None


def test_classify_keeps_non_matching_etymology():
    row = {**BASE_ROW}  # dex_etymology='slavă'
    result = ms.classify(row, exclude_etym=frozenset({'anglicism'}))
    assert result is not None


def test_classify_empty_exclude_set_unchanged():
    row = {**ANGLICISM_ROW}
    result = ms.classify(row, exclude_etym=frozenset())
    # anglicism word with extinct verdict and hist_ppm>0 → should be classified
    assert result == 'corpus_extinct'


def test_exclude_etymology_cli_filters_output(tmp_path):
    inp = tmp_path / 'diachronic.csv'
    out = tmp_path / 'shortlist.csv'
    make_diachronic_csv(inp, [BASE_ROW, ANGLICISM_ROW])

    sys.argv = [
        'make_shortlist.py',
        '--input', str(inp),
        '--output', str(out),
        '--exclude-etymology', 'anglicism',
    ]
    ms.main()

    rows = list(csv.DictReader(out.open(encoding='utf-8')))
    words = [r['word'] for r in rows]
    assert 'ajutoriu' in words
    assert 'sendviș' not in words
