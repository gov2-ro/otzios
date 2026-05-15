import sqlite3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import extract_definitions


def test_extract_first_definition_per_word(tmp_path):
    sql = tmp_path / 'test.sql'
    sql.write_text(
        "INSERT INTO `DefinitionSimple` VALUES "
        "(1,'Def of word1','word1',0,0,0,0),"
        "(2,'Second def of word1','word1',0,0,0,0),"
        "(3,'Def of word2','word2',0,0,0,0);\n",
        encoding='utf-8',
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    conn = sqlite3.connect(str(out))
    rows = {r[0]: r[1] for r in conn.execute('SELECT word, definition FROM definitions')}
    conn.close()
    assert rows == {'word1': 'Def of word1', 'word2': 'Def of word2'}


def test_extract_skips_empty_lexicon(tmp_path):
    sql = tmp_path / 'test.sql'
    sql.write_text(
        "INSERT INTO `DefinitionSimple` VALUES "
        "(1,'def','',0,0,0,0),(2,'def2','word2',0,0,0,0);\n",
        encoding='utf-8',
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    conn = sqlite3.connect(str(out))
    count = conn.execute('SELECT COUNT(*) FROM definitions').fetchone()[0]
    conn.close()
    assert count == 1


def test_extract_handles_escaped_quote_in_definition(tmp_path):
    sql = tmp_path / 'test.sql'
    sql.write_text(
        "INSERT INTO `DefinitionSimple` VALUES (1,'It\\'s a test','word1',0,0,0,0);\n",
        encoding='utf-8',
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    conn = sqlite3.connect(str(out))
    row = conn.execute("SELECT definition FROM definitions WHERE word='word1'").fetchone()
    conn.close()
    assert row[0] == "It's a test"


def test_extract_handles_diacritics_in_word(tmp_path):
    sql = tmp_path / 'test.sql'
    sql.write_text(
        "INSERT INTO `DefinitionSimple` VALUES (1,'Vânzătoare.','acătării',0,0,0,0);\n",
        encoding='utf-8',
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    conn = sqlite3.connect(str(out))
    row = conn.execute("SELECT definition FROM definitions WHERE word='acătării'").fetchone()
    conn.close()
    assert row is not None
    assert row[0] == 'Vânzătoare.'
