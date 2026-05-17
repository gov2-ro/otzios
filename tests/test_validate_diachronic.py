import sqlite3
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import validate_diachronic as vd


def make_defs_db(path: Path, rows: list[tuple]) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute(
        'CREATE TABLE definitions (word TEXT PRIMARY KEY, definition TEXT)'
    )
    conn.executemany('INSERT INTO definitions VALUES (?,?)', rows)
    conn.commit()
    conn.close()


def test_load_definition_words_returns_words_with_content(tmp_path):
    db = tmp_path / 'defs.db'
    make_defs_db(db, [
        ('ajutoriu', 'Formă veche pentru ajutor.'),
        ('nombrilist', None),
        ('viți', ''),
    ])
    result = vd._load_definition_words(db)
    assert 'ajutoriu' in result
    assert 'nombrilist' not in result
    assert 'viți' not in result


def test_load_definition_words_missing_db_returns_empty(tmp_path):
    result = vd._load_definition_words(tmp_path / 'nonexistent.db')
    assert result == set()
