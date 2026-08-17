import sqlite3
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

import extract_definitions


def _q(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def _make_sql(tmp_path, def_simples=(), definitions=()):
    """Write a minimal SQL file with DefinitionSimple and/or Definition INSERTs.

    `definitions` rows are (id, userId, sourceId, lexicon, internalRep) tuples
    for the `Definition` table (the DEX '98/'96 top-up path).
    """
    lines = []
    if def_simples:
        vals = ','.join(f"({did},{_q(defn)},{_q(lex)})" for did, defn, lex in def_simples)
        lines.append(f"INSERT INTO `DefinitionSimple` VALUES {vals};")
    if definitions:
        vals = ','.join(
            f"({did},{uid},{sid},{_q(lex)},{_q(rep)})"
            for did, uid, sid, lex, rep in definitions
        )
        lines.append(f"INSERT INTO `Definition` VALUES {vals};")
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


# --- _clean_markup ---------------------------------------------------------

def test_clean_markup_unwraps_typographic_delimiters():
    rep = r"@ODAG'ACI@ #s. m.# @1.@ Plantă erbacee $(Saponaria officinalis).$"
    got = extract_definitions._clean_markup(rep)
    assert '@' not in got and '#' not in got and '$' not in got
    assert "ODAG'ACI" in got
    assert 'Plantă erbacee' in got


def test_clean_markup_strips_foreign_cognate_percent_wrapper():
    rep = r"@ABIT'IR@ #adv.# - #Cf.# #tc.# %beter% \"mai rău\"."
    got = extract_definitions._clean_markup(rep)
    assert '%' not in got
    assert 'beter' in got


def test_clean_markup_drops_homograph_number():
    got = extract_definitions._clean_markup(r"@A^1@ #s. m.# #invar.# Prima literă.")
    assert '^1' not in got and '^' not in got


def test_clean_markup_drops_editor_note_entirely():
    rep = r"@ADAPT'OR,@ $adaptoare,${{Am corectat forma de #pl.# (în DEX apare $adaptare$)./3}} #s. n.# Circuit."
    got = extract_definitions._clean_markup(rep)
    assert 'corectat' not in got
    assert 'Circuit' in got


def test_clean_markup_returns_none_for_null_after_cleaning():
    assert extract_definitions._clean_markup('NULL') is None


# --- _extract_dex9896_topup -------------------------------------------------

def test_topup_uses_only_dex98_and_dex96(tmp_path):
    sql = _make_sql(
        tmp_path,
        definitions=[
            (1, 2, 1, 'oaspăt', "@O'ASPĂT@ #s. m.# #v.# @oaspete.@"),
            (2, 2, 2, 'igliță', "@'IGLIȚĂ,@ #s. f.# Croșetă."),
            # sourceId 6 = Sinonime, truncated to a ~23-char stub in the real
            # dump — must never be picked up by the top-up.
            (3, 2, 6, 'oaspăt', 'stub, dimie, păn...'),
        ],
    )
    out = extract_definitions._extract_dex9896_topup(sql)
    assert set(out) == {'oaspăt', 'igliță'}
    assert 'dimie' not in out['oaspăt']


def test_topup_prefers_dex98_over_dex96_for_same_headword(tmp_path):
    sql = _make_sql(
        tmp_path,
        definitions=[
            (1, 2, 2, 'mers', "@MERS@ #s. n.# Din DEX 96."),
            (2, 2, 1, 'mers', "@MERS@ #s. n.# Din DEX 98."),
        ],
    )
    out = extract_definitions._extract_dex9896_topup(sql)
    assert 'DEX 98' in out['mers']


def test_topup_skips_empty_lexicon_or_internalrep(tmp_path):
    sql = _make_sql(
        tmp_path,
        definitions=[
            (1, 2, 1, '', "@X@ text"),
            (2, 2, 1, 'gol', 'NULL'),
        ],
    )
    out = extract_definitions._extract_dex9896_topup(sql)
    assert out == {}


# --- extract() end-to-end with the DEX '98/'96 top-up ----------------------

def test_extract_topup_fills_gap_not_in_definitionsimple(tmp_path):
    sql = _make_sql(
        tmp_path,
        def_simples=[(100, 'Deja acoperit.', 'acoperit')],
        definitions=[
            (1, 2, 1, 'nou', "@N'OU@ #adj.# Recent apărut."),
        ],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    rows = _read_db(out)
    assert rows['acoperit'] == 'Deja acoperit.'
    assert 'Recent apărut' in rows['nou']


def test_extract_topup_never_overrides_definitionsimple(tmp_path):
    # DefinitionSimple already has 'mers'; Definition's DEX '98 text for the
    # same headword must not replace it — DefinitionSimple stays authoritative
    # for anything it already covers.
    sql = _make_sql(
        tmp_path,
        def_simples=[(100, 'Text din DefinitionSimple.', 'mers')],
        definitions=[
            (1, 2, 1, 'mers', "@MERS@ #s. n.# Text din Definition."),
        ],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    assert _read_db(out)['mers'] == 'Text din DefinitionSimple.'


def test_extract_topup_ignores_truncated_non_academy_sources(tmp_path):
    # Only sourceId 1/2 carry real text in the dump; anything else (here 17 =
    # a stand-in for one of the ~100 truncated sources) must not surface even
    # when it's the only entry for a headword.
    sql = _make_sql(
        tmp_path,
        definitions=[(1, 2, 17, 'trunchiat', 'stub only, no re')],
    )
    out = tmp_path / 'defs.db'
    extract_definitions.extract(sql, out)
    assert _read_db(out) == {}
