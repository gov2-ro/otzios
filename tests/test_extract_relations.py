"""Acceptance tests for extract_relations.py, per docs/sinonime/spec.md Phase 1.

Run: source ~/g2-dev/monitorulpreturilor/venv/bin/activate && pytest tests/test_extract_relations.py -q
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RELATIONS_DB = ROOT / 'data' / 'processed' / 'relations.db'
SAMPLE_CLEANED = ROOT / 'data' / 'dictionaries' / 'dex-sample-cleaned.sql'


@pytest.fixture(scope='module')
def conn():
    if not RELATIONS_DB.exists():
        pytest.skip(f'{RELATIONS_DB} not built -- run extract_relations.py first')
    c = sqlite3.connect(str(RELATIONS_DB))
    yield c
    c.close()


def test_relation_type_distribution_is_exact(conn):
    counts = dict(conn.execute('SELECT type, COUNT(*) FROM relation GROUP BY type'))
    assert counts.get(1) == 152_023
    assert counts.get(2) == 5_216
    assert counts.get(3) == 1_547
    assert counts.get(4) == 74


def test_relation_and_tree_row_counts(conn):
    assert conn.execute('SELECT COUNT(*) FROM relation').fetchone()[0] == 158_860
    assert conn.execute('SELECT COUNT(*) FROM tree').fetchone()[0] == 226_424


def test_refuses_the_sampled_and_commented_out_dump(tmp_path):
    if not SAMPLE_CLEANED.exists():
        pytest.skip(f'{SAMPLE_CLEANED} not present')
    out = tmp_path / 'relations_smoke.db'
    result = subprocess.run(
        [sys.executable, str(ROOT / 'extract_relations.py'),
         '--dump', str(SAMPLE_CLEANED), '--out', str(out)],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode != 0
    assert not out.exists()
