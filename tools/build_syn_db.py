#!/usr/bin/env python3
"""
Build public/data/syn.db, the Sinonime writing-aid database, from relations.db.

Reads data/processed/relations.db (extract_relations.py), data/processed/corpus_frequencies.db
(culturax_ro occurrence counts), data/processed/inflected_forms.db (form -> lemma rollup) and
data/processed/synonyms.db (the Seche/dexonline scrape). Writes nothing back to any of them,
and never touches public/data/ui.db or private/app.db — this tool has its own database and
its own lib file (public/api/_syn.php), per docs/sinonime/spec.md's "own DB, no app.db" rule.

Schema and build rules: docs/sinonime/spec.md, Phase 2. Measurements behind every rule:
docs/sinonime/findings.md. What follows implements the nine build rules, in this order:

  1-2. Expand a Tree to its EntryLexeme.main=1 lexemes for *results* (the `word` table);
       non-main lexemes in the same entry become `key` rows pointing at the entry's main
       word(s), never rows of their own in `word`.
  3.   Every key is inserted both folded (normalize_diacritics-style) and unfolded.
  4.   `word.form` is Lexeme.formNoAccent (already-normalized Romanian orthography).
  5.   `band` is the modern-corpus rollup, computed once for every word after the graph is
       built (see compute_bands()).
  6.   The Seche scrape (synonyms.db) is merged with provenance src=1, reusing
       scrape_synonyms.py's token-cleanliness rules.
  7.   Type-5 (Tree co-membership) edges are added last, only for word pairs that gained no
       type-1 edge from steps 1-6.
  8.   Symmetrisation is a *query-time* join (public/api/_syn.php's lookup_related()), not a
       build-time storage pass -- see the note on build_relation_graph() for why, including
       the 21-23 MB version this project rejected in favour of it.
  9.   edge.rank is computed last, once bands are known, per (sense, type) group.

Sense-graph shape, since the schema keeps DEX's structure rather than flattening to a
word<->word bag (findings.md §7): `sense.id` is the DEX `Meaning.id` for every
Relation-derived sense. `sense_word(sid, word)` holds the meaning's own tree, expanded;
`edge(sid, word, t)` holds the target tree, expanded -- literally what the schema comments
say, and what findings.md §8's reference sizes were measured against. A word's full
neighbourhood therefore needs two queries unioned (forward: sense_word -> edge; backward:
edge -> sense_word of the same sid), which is what makes the 64%-non-reciprocal Relation
data (rule 8) fully symmetric to a reader without doubling storage. See lookup_related().

Type-5 cliques get one synthetic sense per multi-entry Tree (id space 2,000,000,000 + tree_id,
disjoint from Meaning ids, which top out near 490,000). A clique's `sense_word` and `edge` are
both the *participating* members (those with at least one pair not already covered by type-1);
a member reached via one surviving pair currently also sees every other participant, including
ones it may already reach via type-1 through a different pair -- a documented approximation,
not a precision bug: v1 never renders type-5 (docs/sinonime/ui.md "Not in v1"), and the
coverage number that matters (words gaining a first synonym) is computed directly rather than
derived from clique membership.
"""

from __future__ import annotations

import argparse
import math
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dump_parser import normalize  # noqa: E402

RELATIONS_DB = Path('data/processed/relations.db')
CORPUS_DB    = Path('data/processed/corpus_frequencies.db')
INFLECTED_DB = Path('data/processed/inflected_forms.db')
SYNONYMS_DB  = Path('data/processed/synonyms.db')
OUTPUT_DB    = Path('public/data/syn.db')

BATCH = 50_000

SCRAPE_SENSE_BASE = 1_000_000_000   # synthetic sense ids for words with no DEX sense
TYPE5_SENSE_BASE   = 2_000_000_000   # synthetic sense ids for Tree co-membership cliques

REG_BITS = [
    (0, 'regional'), (1, 'învechit'), (2, 'rar'), (3, 'familiar'), (4, 'popular'),
    (5, 'peiorativ'), (6, 'figurat'), (7, 'argou'), (8, 'livresc'),
]

_FOLD_MAP = str.maketrans({'ț': 't', 'ș': 's', 'ţ': 't', 'ş': 's', 'ă': 'a', 'â': 'a', 'î': 'i'})


def fold(s: str) -> str:
    """Port of normalize_diacritics() in public/api/_lib.php:500-507, character for character."""
    return s.lower().translate(_FOLD_MAP)


def compute_reg(tags: list[str]) -> int:
    bitmask = 0
    for tag in tags:
        low = tag.lower()
        for bit, name in REG_BITS:
            if name in low:
                bitmask |= (1 << bit)
    return bitmask


def is_dirty_scrape_token(tok: str) -> bool:
    """Mirrors scrape_synonyms.py's parse_word_list() cleanliness rules (spec.md rule 6),
    applied a second time here because the merged CSV still carries leftovers that slipped
    past the scraper's own filter -- e.g. potcă's list ends in the OCR-mangled 'HÎDOȘENlE',
    which has one lowercase letter and so survives a naive str.isupper() check. Majority-
    uppercase-of-alpha-chars catches it without a false positive on ordinary lowercase words.
    """
    if '=' in tok:
        return True
    if len(tok) > 40 or len(tok.split()) > 4:
        return True
    alpha = [c for c in tok if c.isalpha()]
    if alpha and sum(1 for c in alpha if c.isupper()) / len(alpha) > 0.5:
        return True
    return False


class Graph:
    def __init__(self) -> None:
        self.word_id_of: dict[str, int] = {}
        self.word_form: dict[int, str] = {}
        self.word_pos: dict[int, str | None] = {}
        self._next_word_id = 1

        self.entry_main_cache: dict[int, list[int]] = {}
        self.tree_main_cache: dict[int, list[int]] = {}
        self.keys: set[tuple[str, int]] = set()
        self.key_to_words: dict[str, set[int]] = defaultdict(set)

        self.sense_word: dict[int, set[int]] = defaultdict(set)
        self.word_to_senses: dict[int, set[int]] = defaultdict(set)  # incremental index
        self.sense_label: dict[int, str | None] = {}
        self.sense_reg: dict[int, int] = {}
        # (sid, type) -> {word_id: src}
        self.edge: dict[tuple[int, int], dict[int, int]] = defaultdict(dict)

    def add_to_sense(self, sid: int, wid: int) -> None:
        self.sense_word[sid].add(wid)
        self.word_to_senses[wid].add(sid)

    # ── word / key registry ─────────────────────────────────────────────
    def get_or_create_word(self, form: str, pos: str | None) -> int:
        wid = self.word_id_of.get(form)
        if wid is None:
            wid = self._next_word_id
            self._next_word_id += 1
            self.word_id_of[form] = wid
            self.word_form[wid] = form
            self.word_pos[wid] = pos
        elif pos and not self.word_pos.get(wid):
            self.word_pos[wid] = pos
        return wid

    def add_key(self, form: str, wid: int) -> None:
        if not form:
            return
        self.keys.add((form, wid))
        self.key_to_words[form].add(wid)
        folded = fold(form)
        self.keys.add((folded, wid))
        self.key_to_words[folded].add(wid)

    def resolve_or_create_word(self, form: str, pos: str | None) -> int:
        """Like get_or_create_word(), but checks the graph's own key index first: a form
        the DEX entry structure already classified as a non-main variant (rule 2 -- 'nalt
        is filed under înalt') must resolve to that variant's word, not mint a new one.
        Without this, merge_scrape() (which knows nothing about main/non-main) creates a
        first-class 'nalt' word purely because it happens to also be a scraped headword."""
        wid = self.word_id_of.get(form)
        if wid is not None:
            if pos and not self.word_pos.get(wid):
                self.word_pos[wid] = pos
            return wid
        targets = self.key_to_words.get(form)
        if targets:
            return min(targets)
        return self.get_or_create_word(form, pos)

    def word_senses(self, wid: int) -> list[int]:
        # O(1) index lookup, not a scan -- see add_to_sense(). Sorted because callers
        # want "the word's lowest-id sense" (spec.md rule 6).
        return sorted(self.word_to_senses.get(wid, ()))

    def ensure_sense_for_word(self, wid: int) -> int:
        existing = self.word_senses(wid)
        if existing:
            return existing[0]
        sid = self._next_scrape_sid
        self._next_scrape_sid += 1
        self.sense_label[sid] = None
        self.sense_reg[sid] = 0
        self.add_to_sense(sid, wid)
        return sid

    _next_scrape_sid = SCRAPE_SENSE_BASE


def load_relations(db_path: Path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = None

    meaning_tree = dict(conn.execute('SELECT meaning_id, tree_id FROM meaning_tree'))

    tree_entries: dict[int, list[int]] = defaultdict(list)
    for tree_id, entry_id in conn.execute(
            'SELECT tree_id, entry_id FROM tree_entry ORDER BY tree_id, entry_rank'):
        tree_entries[tree_id].append(entry_id)

    entry_lexemes: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for entry_id, lexeme_id, main in conn.execute(
            'SELECT entry_id, lexeme_id, main FROM entry_lexeme ORDER BY entry_id, lexeme_rank'):
        entry_lexemes[entry_id].append((lexeme_id, main))

    lexeme_form: dict[int, str | None] = {}
    lexeme_pos: dict[int, str | None] = {}
    for lid, form_norm, model_type in conn.execute('SELECT id, form_norm, model_type FROM lexeme'):
        lexeme_form[lid] = form_norm
        lexeme_pos[lid] = model_type or None

    tree_desc = dict(conn.execute('SELECT id, description FROM tree'))

    meaning_tags: dict[int, list[str]] = defaultdict(list)
    for meaning_id, tag in conn.execute('SELECT meaning_id, tag FROM meaning_tag'):
        meaning_tags[meaning_id].append(tag)

    relations = conn.execute('SELECT meaning_id, tree_id, type FROM relation').fetchall()

    conn.close()
    return dict(
        meaning_tree=meaning_tree, tree_entries=tree_entries, entry_lexemes=entry_lexemes,
        lexeme_form=lexeme_form, lexeme_pos=lexeme_pos, tree_desc=tree_desc,
        meaning_tags=meaning_tags, relations=relations,
    )


def process_entry(g: Graph, data, entry_id: int) -> list[int]:
    """Register an entry's main lexemes as words (and keys), non-main ones as keys only.
    Memoized: each entry is only processed once no matter how many trees reference it."""
    cached = g.entry_main_cache.get(entry_id)
    if cached is not None:
        return cached

    mains: list[int] = []
    main_forms: list[str] = []
    nonmain_forms: list[str] = []
    for lex_id, main in data['entry_lexemes'].get(entry_id, ()):
        form = data['lexeme_form'].get(lex_id)
        if not form:
            continue
        if main:
            wid = g.get_or_create_word(form, data['lexeme_pos'].get(lex_id))
            mains.append(wid)
            main_forms.append(form)
        else:
            nonmain_forms.append(form)

    for wid, form in zip(mains, main_forms):
        g.add_key(form, wid)
    for form in nonmain_forms:
        for wid in mains:
            g.add_key(form, wid)

    g.entry_main_cache[entry_id] = mains
    return mains


def expand_main(g: Graph, data, tree_id: int | None) -> list[int]:
    if tree_id is None:
        return []
    cached = g.tree_main_cache.get(tree_id)
    if cached is not None:
        return cached
    out: list[int] = []
    seen: set[int] = set()
    for entry_id in data['tree_entries'].get(tree_id, ()):
        for wid in process_entry(g, data, entry_id):
            if wid not in seen:
                seen.add(wid)
                out.append(wid)
    g.tree_main_cache[tree_id] = out
    return out


def build_relation_graph(g: Graph, data) -> None:
    """Rules 1-2. Each Relation row gives a source tree (the meaning's own, via meaning_tree)
    and a target tree (Relation.treeId); both expand to main-lexeme word sets SW and TW.
    `sense_word` gets SW ("the sense's own word(s)", per the schema comment) and `edge` gets
    TW ("the related words") -- kept literally separate, one direction per row, which is what
    the reference sizes in findings.md §8 (179,894 edges for this step) were measured against.

    Symmetrisation (rule 8) is NOT a second storage pass here. findings.md measured only 36%
    of stored Relation pairs as reciprocal, i.e. 64% of the time B has no Relation row pointing
    back at A -- but that is a fact about dexonline's authoring, not about whether the *query*
    "what is related to B" can find A. It can, via a query that also looks in the other
    direction: "which senses list B as a *target* (an edge row), and what are those senses'
    *own* words" -- see lookup_related() in public/api/_syn.php, which unions the forward
    query (word is a sense_word -> read its edges) with this backward one (word is an edge ->
    read that sense's sense_word) rather than materializing both directions at build time.

    An earlier version of this function stored SW|TW (the union) in both tables so a single
    forward query would already be symmetric. It worked and passed every acceptance test
    (văz's three sense clusters included -- distinctness only depends on meaning_id staying
    the sid, which neither version changes), but it also roughly doubled `edge`'s row count
    for no semantic gain over the two-way query, and pushed the database to 21-23 MB against
    spec.md's 16 MB ceiling. Splitting the work between build-time (this function, literal
    per the schema comments) and query-time (lookup_related()) is what makes the database
    small AND the lookup symmetric; picking only one of those was the size problem, not
    symmetry itself."""
    for meaning_id, tree_id, typ in data['relations']:
        if typ not in (1, 2, 3, 4):
            continue
        src_tree = data['meaning_tree'].get(meaning_id)
        sw = expand_main(g, data, src_tree)
        tw = expand_main(g, data, tree_id)
        if not sw or not tw:
            continue
        sid = meaning_id
        for w in sw:
            g.add_to_sense(sid, w)
        if sid not in g.sense_label:
            g.sense_label[sid] = data['tree_desc'].get(src_tree)
        if sid not in g.sense_reg:
            g.sense_reg[sid] = compute_reg(data['meaning_tags'].get(meaning_id, []))
        d = g.edge[(sid, typ)]
        for w in tw:
            d.setdefault(w, 0)   # src=0: Relation


def merge_scrape(g: Graph, db_path: Path) -> dict[str, int]:
    stats = {'words': 0, 'new_sense': 0, 'syn_edges': 0, 'ant_edges': 0, 'dropped_tokens': 0}
    if not db_path.exists():
        return stats
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute('SELECT word, synonyms, antonyms FROM synonyms').fetchall()
    conn.close()

    for word, syn_text, ant_text in rows:
        word = normalize(word or '')
        if not word:
            continue
        wid = g.resolve_or_create_word(word, None)
        g.add_key(word, wid)
        stats['words'] += 1

        existing = g.word_senses(wid)
        if existing:
            sid = existing[0]
        else:
            sid = g._next_scrape_sid
            g._next_scrape_sid += 1
            g.sense_label[sid] = None
            g.sense_reg[sid] = 0
            g.add_to_sense(sid, wid)
            stats['new_sense'] += 1

        for text, typ, counter_key in ((syn_text, 1, 'syn_edges'), (ant_text, 2, 'ant_edges')):
            if not text:
                continue
            d = g.edge[(sid, typ)]
            for raw in text.split(','):
                tok = raw.strip()
                if not tok:
                    continue
                if is_dirty_scrape_token(tok):
                    stats['dropped_tokens'] += 1
                    continue
                tok_norm = normalize(tok)
                twid = g.resolve_or_create_word(tok_norm, None)
                g.add_key(tok_norm, twid)
                if twid not in d:
                    d[twid] = 1   # src=1: scraped
                    stats[counter_key] += 1
    return stats


def add_type5(g: Graph, data) -> dict[str, int]:
    """Rule 7. One synthetic sense per multi-entry Tree, only for pairs with no type-1 edge."""
    type1_pairs: set[frozenset[int]] = set()
    for (sid, typ), targets in g.edge.items():
        if typ != 1:
            continue
        for sw in g.sense_word.get(sid, ()):
            for tw in targets:
                if sw != tw:
                    type1_pairs.add(frozenset((sw, tw)))

    # A word already has *some* type1-4 edge iff it is a member of a sense that carries a
    # type1-4 edge dict, or is itself an edge target somewhere.
    has_edge: set[int] = set()
    for (sid, typ), targets in g.edge.items():
        if typ not in (1, 2, 3, 4):
            continue
        for sw in g.sense_word.get(sid, ()):
            if targets:
                has_edge.add(sw)
        has_edge.update(targets)

    stats = {'cliques': 0, 'pairs': 0, 'words_gaining_first': 0}
    for tree_id, entries in data['tree_entries'].items():
        if len(set(entries)) < 2:
            continue
        members = expand_main(g, data, tree_id)
        if len(members) < 2:
            continue
        pairs_needed = []
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                if frozenset((a, b)) not in type1_pairs:
                    pairs_needed.append((a, b))
        if not pairs_needed:
            continue
        sid = TYPE5_SENSE_BASE + tree_id
        g.sense_label[sid] = data['tree_desc'].get(tree_id)
        g.sense_reg.setdefault(sid, 0)
        participants: set[int] = set()
        for a, b in pairs_needed:
            participants.add(a)
            participants.add(b)
        for w in participants:
            g.add_to_sense(sid, w)
        d = g.edge[(sid, 5)]
        for w in participants:
            d[w] = 2   # src=2: Tree co-membership
        stats['cliques'] += 1
        stats['pairs'] += len(pairs_needed)
        stats['words_gaining_first'] += len(participants - has_edge)

    return stats


def compute_bands(word_form: dict[int, str]) -> tuple[dict[int, int], dict[str, int]]:
    """Rule 5. band = 0 if occ==0 else min(7, 1+floor(log10(occ))), occ rolled up through
    inflected_forms.db.form_lemma against corpus_frequencies.db's culturax_ro counts."""
    lemmas = sorted(set(word_form.values()))
    conn = sqlite3.connect(str(CORPUS_DB))
    conn.execute(f"ATTACH DATABASE '{INFLECTED_DB}' AS infl")
    conn.execute('CREATE TEMP TABLE want_lemma (lemma TEXT PRIMARY KEY)')
    conn.executemany('INSERT INTO want_lemma VALUES (?)', [(l,) for l in lemmas])
    rows = conn.execute("""
        SELECT fl.lemma, SUM(cwf.occurrence_count)
          FROM infl.form_lemma fl
          JOIN corpus_word_frequency cwf ON cwf.word = fl.form AND cwf.corpus_name = 'culturax_ro'
          JOIN want_lemma w ON w.lemma = fl.lemma
         GROUP BY fl.lemma
    """).fetchall()
    conn.close()

    occ_by_lemma = {lemma: (occ or 0) for lemma, occ in rows}
    bands: dict[int, int] = {}
    for wid, form in word_form.items():
        occ = occ_by_lemma.get(form, 0)
        bands[wid] = 0 if occ <= 0 else min(7, 1 + int(math.floor(math.log10(occ))))
    return bands, occ_by_lemma


def write_db(g: Graph, bands: dict[int, int], out_path: Path, meta: dict[str, str]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    conn = sqlite3.connect(str(out_path))
    conn.execute('PRAGMA journal_mode = OFF')
    conn.execute('PRAGMA synchronous = OFF')
    conn.executescript("""
        CREATE TABLE word(
          id   INTEGER PRIMARY KEY,
          form TEXT    NOT NULL,
          pos  TEXT,
          band INTEGER NOT NULL
        );
        CREATE TABLE key(
          k       TEXT    NOT NULL,
          word_id INTEGER NOT NULL,
          PRIMARY KEY(k, word_id)
        ) WITHOUT ROWID;
        CREATE TABLE sense(
          id    INTEGER PRIMARY KEY,
          label TEXT,
          reg   INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE sense_word(sid INTEGER, word_id INTEGER,
          PRIMARY KEY(sid, word_id)) WITHOUT ROWID;
        CREATE TABLE edge(sid INTEGER, word_id INTEGER, t INTEGER, src INTEGER NOT NULL DEFAULT 0,
          rank INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY(sid, word_id, t)) WITHOUT ROWID;
        CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
    """)

    def batched_insert(sql: str, rows_iter):
        batch = []
        for row in rows_iter:
            batch.append(row)
            if len(batch) >= BATCH:
                conn.executemany(sql, batch)
                batch.clear()
        if batch:
            conn.executemany(sql, batch)

    batched_insert('INSERT INTO word VALUES (?,?,?,?)',
        ((wid, form, g.word_pos.get(wid), bands.get(wid, 0)) for wid, form in g.word_form.items()))

    batched_insert('INSERT OR IGNORE INTO key VALUES (?,?)', iter(g.keys))

    batched_insert('INSERT INTO sense VALUES (?,?,?)',
        ((sid, g.sense_label.get(sid), g.sense_reg.get(sid, 0)) for sid in g.sense_word))

    batched_insert('INSERT INTO sense_word VALUES (?,?)',
        ((sid, wid) for sid, words in g.sense_word.items() for wid in words))

    # Rule 9: rank is computed per (sid, type) group, ordered band DESC, form ASC.
    def edge_rows():
        for (sid, typ), targets in g.edge.items():
            ordered = sorted(targets.items(),
                key=lambda kv: (-bands.get(kv[0], 0), g.word_form.get(kv[0], '')))
            for rank, (wid, src) in enumerate(ordered):
                yield (sid, wid, typ, src, rank)

    batched_insert('INSERT INTO edge VALUES (?,?,?,?,?)', edge_rows())

    conn.executemany('INSERT INTO meta VALUES (?,?)', list(meta.items()))
    conn.commit()

    print('  indexing ...', file=sys.stderr)
    conn.executescript("""
        CREATE INDEX ix_word_form    ON word(form);
        CREATE INDEX ix_sense_word_w ON sense_word(word_id);
        CREATE INDEX ix_edge_rank    ON edge(sid, t, rank);
    """)
    conn.commit()
    # findings.md §8 measured every size figure post-VACUUM (page_count * page_size after
    # compaction) -- skipping this step measures B-tree page-split fragmentation from
    # insertion order, not the database's actual size, and the two differed by several MB.
    print('  vacuuming ...', file=sys.stderr)
    conn.execute('VACUUM')
    conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--relations', type=Path, default=RELATIONS_DB)
    ap.add_argument('--out', type=Path, default=OUTPUT_DB)
    args = ap.parse_args()

    if not args.relations.exists():
        print(f'{args.relations} not found -- run extract_relations.py first.', file=sys.stderr)
        return 1

    t0 = time.time()
    print(f'Loading {args.relations} ...', file=sys.stderr)
    data = load_relations(args.relations)
    print(f'  {len(data["relations"]):,} relations, {len(data["tree_entries"]):,} trees, '
          f'{len(data["lexeme_form"]):,} lexemes', file=sys.stderr)

    g = Graph()
    print('Building relation graph (type 1-4) ...', file=sys.stderr)
    build_relation_graph(g, data)
    print(f'  words so far: {len(g.word_form):,}  senses so far: {len(g.sense_word):,}',
          file=sys.stderr)

    print(f'Merging scrape from {SYNONYMS_DB} ...', file=sys.stderr)
    scrape_stats = merge_scrape(g, SYNONYMS_DB)
    print(f'  {scrape_stats}', file=sys.stderr)

    print('Adding type-5 (Tree co-membership) edges ...', file=sys.stderr)
    t5_stats = add_type5(g, data)
    print(f'  {t5_stats}', file=sys.stderr)

    print(f'Total words: {len(g.word_form):,}  senses: {len(g.sense_word):,}  '
          f'keys: {len(g.keys):,}', file=sys.stderr)

    print('Computing modern-usage bands ...', file=sys.stderr)
    bands, occ_by_lemma = compute_bands(g.word_form)
    band_hist = defaultdict(int)
    for b in bands.values():
        band_hist[b] += 1
    print(f'  band histogram: {dict(sorted(band_hist.items()))}', file=sys.stderr)

    total_edge_rows = sum(len(t) for t in g.edge.values())
    # A word is "covered" if either direction of lookup_related()'s two-way query would find
    # something: it is a sense_word member of a sense with edges (forward), or it appears as
    # an edge target somewhere (backward, via that sense's own sense_word). Checking only the
    # forward half undercounts -- it was the first thing that looked like a regression here.
    edge_targets: set[int] = set()
    for targets in g.edge.values():
        edge_targets.update(targets)
    has_neighbor: set[int] = set(edge_targets)
    for sid, words in g.sense_word.items():
        if any(g.edge.get((sid, t)) for t in (1, 2, 3, 4, 5)):
            has_neighbor.update(words)
    coverage_1k = sum(1 for wid, form in g.word_form.items()
        if occ_by_lemma.get(form, 0) >= 1000 and wid in has_neighbor)
    total_1k = sum(1 for form in g.word_form.values() if occ_by_lemma.get(form, 0) >= 1000)

    meta = {
        'build_date': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'source_relations_rows': str(len(data['relations'])),
        'source_scrape_words': str(scrape_stats['words']),
        'band_formula': 'band = 0 if occ==0 else min(7, 1+floor(log10(occ)))',
        'band_source': 'corpus_frequencies.db culturax_ro, rolled up via inflected_forms.db.form_lemma',
        'word_count': str(len(g.word_form)),
        'sense_count': str(len(g.sense_word)),
        'edge_row_count': str(total_edge_rows),
        'key_count': str(len(g.keys)),
    }

    print(f'Writing {args.out} ...', file=sys.stderr)
    write_db(g, bands, args.out, meta)

    size = args.out.stat().st_size
    print(f'\nDone in {time.time()-t0:.1f}s', file=sys.stderr)
    print(f'  word    : {len(g.word_form):,}', file=sys.stderr)
    print(f'  key     : {len(g.keys):,}', file=sys.stderr)
    print(f'  sense   : {len(g.sense_word):,}', file=sys.stderr)
    print(f'  edge    : {total_edge_rows:,}', file=sys.stderr)
    print(f'  size    : {size:,} bytes ({size/1024/1024:.1f} MB)', file=sys.stderr)
    if total_1k:
        print(f'  coverage @1k+ occ: {coverage_1k:,}/{total_1k:,} = '
              f'{100*coverage_1k/total_1k:.1f}%', file=sys.stderr)
    if size > 16 * 1024 * 1024:
        print('WARNING: exceeds the 16 MB test ceiling in spec.md.', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
