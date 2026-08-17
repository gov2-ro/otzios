"""Parser tests for scrape_dcr.py.

All offline — the HTML below mirrors the real structure of dexonline word pages
(copied from /definitie/computer on 2026-08-17), so the parser can be changed
without hitting a community-run site to find out what broke.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
import scrape_dcr as sd


PAGE = '''
<div class="defWrapper">
  <p class="mb-2 read-more" data-read-more-lines="15">
    <span class="def" title="Clic pentru a naviga la acest cuvânt">
      <b>comp<span class="tonic-accent">u</span>ter</b>
      <abbr class="abbrev">s.</abbr> <abbr class="abbrev">n.</abbr>, <abbr class="abbrev">s.</abbr>
      <abbr class="abbrev">m.</abbr> Aparat electronic dotat cu memorie ◊ „Aceste aspecte...”
    </span>
  </p>
  <div class="defDetails small text-muted">
    <ul class="list-inline mb-0">
      <li class="list-inline-item"> sursa:
        <a class="ref" href="/sursa/dcr2" title="Dicționar de cuvinte recente, ediția a II-a, 1997">DCR2 (1997)</a>
      </li>
    </ul>
  </div>
</div>
<div class="defWrapper">
  <p class="mb-2 read-more">
    <span class="def">
      <b>ROZ</b> adj. invar. De culoarea trandafirului.
    </span>
  </p>
  <div class="defDetails small text-muted">
    <ul class="list-inline mb-0">
      <li class="list-inline-item"> sursa:
        <a class="ref" href="/sursa/dex" title="Dicționarul explicativ al limbii române, ediția a II-a, 1998">DEX '98 (1998)</a>
      </li>
    </ul>
  </div>
</div>
'''


def test_picks_the_dcr_wrapper_by_its_sursa_link():
    """The source is read from each wrapper's footer link, never from the headword."""
    out = sd.parse_dcr_defs(PAGE)
    assert set(out) == {'dcr2'}
    assert len(out['dcr2']) == 1


def test_tonic_accent_span_is_unwrapped_without_splitting_the_word():
    """`comp<span class=tonic-accent>u</span>ter` must read `computer`, not `comp u ter`.

    This is the regression the .tonic-accent unwrap + smooth() exists for: with a
    space separator, get_text(' ') lands between a word's own letters whenever the
    page splits them across accent spans.
    """
    text = sd.parse_dcr_defs(PAGE)['dcr2'][0]
    assert text.startswith('computer s. n.')
    assert 'Aparat electronic' in text
    assert 'comp u ter' not in text


def test_ignores_wrappers_from_other_sources():
    """A page renders every entry dexonline considers related; only DCR text is exported."""
    out = sd.parse_dcr_defs(PAGE)
    assert all('ROZ' not in t and 'dex' not in ed for ed, parts in out.items() for t in parts)


def test_dcr2_and_dcr3_collected_when_both_present():
    page = PAGE + '''
    <div class="defWrapper">
      <p class="mb-2 read-more">
        <span class="def"><b>biot</b> s. m. Unitate de curent.</span>
      </p>
      <div class="defDetails small text-muted">
        <ul class="list-inline mb-0">
          <li class="list-inline-item"> sursa:
            <a class="ref" href="/sursa/dcr3" title="Dicționar de cuvinte recente, ediția a III-a, 2013">DCR3 (2013)</a>
          </li>
        </ul>
      </div>
    </div>'''
    out = sd.parse_dcr_defs(page)
    assert set(out) == {'dcr2', 'dcr3'}
    assert out['dcr3'] == ['biot s. m. Unitate de curent.']


def test_wrapper_without_sursa_footer_is_ignored():
    page = '''
    <div class="defWrapper">
      <p class="mb-2 read-more">
        <span class="def"><b>fantomă</b> ceva fără sursă.</span>
      </p>
      <div class="defDetails small text-muted">
        <ul class="list-inline mb-0">
          <li class="list-inline-item"> adăugată de <a href="/utilizator/x">x</a></li>
        </ul>
      </div>
    </div>'''
    assert sd.parse_dcr_defs(page) == {}
