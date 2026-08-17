"""Renderer tests for extract_dcr.py.

All offline — the meaning tuples below are the real rows the dump holds for
`abonament-legitimație` (traced 2026-08-17), so the renderer can be changed
without re-scanning a 1.65 GB dump to find out what broke.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import extract_dcr as ed

# (id, parentId, type, displayOrder, breadcrumb, text)
ABONAMENT_LEGITIMATIE = [
    (88684, 0, 0, 1, '1.',
     'Act, document personal eliberat de o autoritate și cu care cineva își '
     'dovedește identitatea.'),
    (476691, 88684, 0, 7, '1.2.',
     '$Abonament-legitimație$ = legitimație care, în schimbul unei sume de bani, '
     'permite posesorului să călătorească cu anumite mijloace de transport.'),
    (476692, 476691, 2, 8, '',
     '$I.T.B.-ul va pune în vânzare și noul tip de abonament-legitimație cu durată '
     'nelimitată (până la pierdere sau deteriorare).$ R.l. 12 X 77 p. 5.'),
    # the pointer twin that lives in the `abonament` tree — cross-tree parent,
    # bare headword text
    (476689, 6159, 0, 7, '1.2.', '$Abonament[476691]-legitimație[476691]$.'),
]


def test_drops_bare_cross_tree_pointers():
    """`$Abonament[476691]-legitimație[476691]$.` is a link, not definition text."""
    out = ed.render_meanings(ABONAMENT_LEGITIMATIE)
    assert 'legitimație care' in out
    # the pointer's text alone must not survive as a unit
    assert '1.2. Abonament-legitimație.' not in out
    assert out.count('Abonament-legitimație') == 1


def test_citations_attach_to_their_sense():
    out = ed.render_meanings(ABONAMENT_LEGITIMATIE)
    assert '◊ I.T.B.-ul va pune în vânzare' in out
    assert 'R.l. 12 X 77 p. 5.' in out


def test_senses_ordered_by_display_order():
    out = ed.render_meanings(ABONAMENT_LEGITIMATIE)
    i1 = out.find('Act, document personal')
    i2 = out.find('Abonament-legitimație = legitimație')
    assert i1 != -1 and i2 != -1 and i1 < i2


def test_cross_tree_parent_is_treated_as_top_level():
    """parentId 6159 is not in this tree; the meaning must still render as a unit."""
    out = ed.render_meanings(ABONAMENT_LEGITIMATIE)
    assert '1.2.' in out


def test_clean_strips_refs_underscores_and_markup():
    assert ed._clean('$Abonament[476691]-legitimație[476691]$.') == 'Abonament-legitimație.'
    assert ed._clean('Instituție __(de stat)__ @care@ #coordonează#.') == \
        'Instituție (de stat) care coordonează.'
