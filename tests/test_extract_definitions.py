import sqlite3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import extract_definitions


def _q(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _make_sql(tmp_path, *, lexemes=(), entry_lexemes=(), entry_defs=(), def_simples=()):
    lines = []
    if lexemes:
        vals = ','.join(f"({lid},{_q(form)},{_q(fna)})" for lid, form, fna in lexemes)
        lines.append(f"INSERT INTO `Lexeme` VALUES {vals};")
    if entry_lexemes:
        vals = ','.join(f"({i},{eid},{lid},{rank})" for i, eid, lid, rank in entry_lexemes)
        lines.append(f"INSERT INTO `EntryLexeme` VALUES {vals};")
    if entry_defs:
        vals = ','.join(f"({i},{eid},{did},{er},{dr})" for i, eid, did, er, dr in entry_defs)
        lines.append(f"INSERT INTO `EntryDefinition` VALUES {vals};")
    if def_simples:
        vals = ','.join(f"({did},{_q(defn)},{_q(lex)})" for did, defn, lex in def_simples)
        lines.append(f"INSERT INTO `DefinitionSimple` VALUES {vals};")
    sql = tmp_path / 'test.sql'
    sql.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return sql


def _read_db(out):
    conn = sqlite3.connect(str(out))
    rows = {r[0]: r[1] for r in conn.execute('SELECT word, definition FROM definitions')}
    conn.close()
    return rows


def test_extract_basic_join(tmp_path):
    sql = _make_sql(
        tmp_path,
        lexemes=[(1, 'mers', 'mers')],
        entry_lexemes=[(1, 10, 1, 0)],
        entry_defs=[(1, 10, 100, 0, 0)],
        def_simples=[(100, 'Acțiunea de a merge.', 'mers')],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    assert _read_db(out) == {'mers': 'Acțiunea de a merge.'}


def test_extract_inflected_form_maps_to_same_definition(tmp_path):
    # Two Lexemes (headword + plural) belong to the same Entry → both get the definition
    sql = _make_sql(
        tmp_path,
        lexemes=[(1, 'plapumă', 'plapumă'), (2, 'plapume', 'plapume')],
        entry_lexemes=[(1, 10, 1, 0), (2, 10, 2, 1)],
        entry_defs=[(1, 10, 100, 0, 0)],
        def_simples=[(100, 'Cuvertură groasă.', 'plapumă')],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    rows = _read_db(out)
    assert rows == {'plapumă': 'Cuvertură groasă.', 'plapume': 'Cuvertură groasă.'}


def test_extract_multiple_definitions_uses_lowest_rank(tmp_path):
    # Entry has two definitions; the one with lower definitionRank wins
    sql = _make_sql(
        tmp_path,
        lexemes=[(1, 'verb', 'verb')],
        entry_lexemes=[(1, 10, 1, 0)],
        entry_defs=[(1, 10, 100, 0, 2), (2, 10, 101, 0, 1)],
        def_simples=[(100, 'Second meaning.', 'verb'), (101, 'First meaning.', 'verb')],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    assert _read_db(out) == {'verb': 'First meaning.'}


def test_extract_multiple_entries_uses_lowest_entry_rank(tmp_path):
    # Lexeme belongs to two entries via EntryLexeme; lowest entryRank wins
    sql = _make_sql(
        tmp_path,
        lexemes=[(1, 'cap', 'cap')],
        entry_lexemes=[(1, 10, 1, 2), (2, 20, 1, 1)],
        entry_defs=[(1, 10, 100, 0, 0), (2, 20, 101, 0, 0)],
        def_simples=[(100, 'Def from entry 10.', 'cap'), (101, 'Def from entry 20.', 'cap')],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    assert _read_db(out) == {'cap': 'Def from entry 20.'}


def test_extract_lexeme_with_no_entry_skipped(tmp_path):
    # Lexeme exists but has no EntryLexeme row → no output
    sql = _make_sql(
        tmp_path,
        lexemes=[(1, 'orphan', 'orphan')],
        entry_defs=[(1, 10, 100, 0, 0)],
        def_simples=[(100, 'Some definition.', 'orphan')],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    assert _read_db(out) == {}


def test_extract_handles_escaped_quote_in_definition(tmp_path):
    sql = _make_sql(
        tmp_path,
        lexemes=[(1, 'test', 'test')],
        entry_lexemes=[(1, 10, 1, 0)],
        entry_defs=[(1, 10, 100, 0, 0)],
        def_simples=[(100, "It's a test", 'test')],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    assert _read_db(out) == {'test': "It's a test"}


def test_extract_handles_diacritics(tmp_path):
    sql = _make_sql(
        tmp_path,
        lexemes=[(1, 'acătării', 'acătării')],
        entry_lexemes=[(1, 10, 1, 0)],
        entry_defs=[(1, 10, 100, 0, 0)],
        def_simples=[(100, 'Vânzătoare.', 'acătării')],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    assert _read_db(out) == {'acătării': 'Vânzătoare.'}
