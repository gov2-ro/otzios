import sqlite3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import extract_definitions


def _q(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _make_sql(tmp_path, def_simples=()):
    """Write a minimal SQL file containing only DefinitionSimple INSERTs.

    The current extractor reads `lexicon` from DefinitionSimple as the
    headword key and ignores the Lexeme / EntryLexeme / EntryDefinition
    tables, so only `def_simples` matters here.
    """
    lines = []
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


def test_extract_uses_lexicon_as_headword(tmp_path):
    sql = _make_sql(tmp_path, def_simples=[(100, 'Acțiunea de a merge.', 'mers')])
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    assert _read_db(out) == {'mers': 'Acțiunea de a merge.'}


def test_extract_keeps_first_definition_per_headword(tmp_path):
    # Two definitions for the same headword; the lower-id one wins (setdefault).
    sql = _make_sql(
        tmp_path,
        def_simples=[
            (100, 'First meaning.', 'verb'),
            (101, 'Second meaning.', 'verb'),
        ],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    assert _read_db(out) == {'verb': 'First meaning.'}


def test_extract_does_not_use_entry_join(tmp_path):
    # Even if Lexeme/EntryLexeme/EntryDefinition would have wired 'abate' to a
    # foreign definition (the original bug), the extractor must only use
    # DefinitionSimple.lexicon. Here the SQL contains no such tables — we just
    # confirm output is keyed strictly on the lexicon field.
    sql = _make_sql(
        tmp_path,
        def_simples=[
            (44, 'Dispozitiv de apărare făcut din copaci tăiați...', 'abatiză'),
            (36, 'Titlu dat superiorului unei abații.', 'abate'),
        ],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    rows = _read_db(out)
    assert rows['abate'].startswith('Titlu dat superiorului')
    assert rows['abatiză'].startswith('Dispozitiv de apărare')


def test_extract_skips_empty_text(tmp_path):
    sql = _make_sql(
        tmp_path,
        def_simples=[
            (1, '', 'gol'),
            (2, '   ', 'spațiu'),
            (3, 'Real text.', 'cuvânt'),
        ],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    assert _read_db(out) == {'cuvânt': 'Real text.'}


def test_extract_handles_escaped_quote_in_definition(tmp_path):
    sql = _make_sql(tmp_path, def_simples=[(100, "It's a test", 'test')])
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    assert _read_db(out) == {'test': "It's a test"}


def test_extract_handles_diacritics(tmp_path):
    sql = _make_sql(
        tmp_path,
        def_simples=[(100, 'Vânzătoare.', 'acătării')],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    assert _read_db(out) == {'acătării': 'Vânzătoare.'}
