# Plan: New DEX dump intake + domain-fix backlog entry

## Context

Two tasks triggered by the new DEX dump download:

1. **Backlog entry** — we proved that `load_taxonomy()` in `validate_diachronic.py` has a wrong join: it joins `ObjectTag.objectId` (which holds Meaning IDs) against `EntryLexeme.entryId` (Entry IDs). These are different ID spaces, causing random domain/register/etymology assignments. The fix needs new tables extracted (`Meaning`, `TreeEntry`) and a corrected join chain. Tracked separately, not implemented now.

2. **New dump intake** — `dex-database.sql` (1.65 GB) replaces `dex-database-1.sql` (1.27 GB). Differences are mostly data growth; the schema is nearly identical. The notable addition is a `Subtitle` table (13M rows, individual Romanian words from 966 YouTube clips) which is a potential Phase 2 corpus.

---

## Step 1 — Add backlog entry

Edit `docs/BACKLOG.md`. The existing entry (lines 27-28) describes a related but shallower symptom ("cross-sense contamination"). Clarify it with the root cause we found:

> - [ ] **Fix `load_taxonomy()` join** (`validate_diachronic.py:146-153`, `extract_taxonomy.py`) — `ObjectTag.objectId` where `objectType=3` holds **Meaning IDs** (max ~489k), not Entry IDs (max ~339k). The current join against `EntryLexeme.entryId` hits a different ID space entirely, producing random domain/register/etymology assignments (e.g. `pretutindeni`→botanică, `antipapă`→medicină). Fix: extract `TreeEntry` and `Meaning(id, treeId)` tables from the dump into `lexemes.db`, then rewrite the query as `Lexeme → EntryLexeme → TreeEntry → Meaning → ObjectTag(objectType=3)`. Also see approach 3 (parse domain from `Meaning.internalRep` text as cross-check). Requires re-running `validate_diachronic.py` to regenerate the shortlist after the fix.

Keep the existing entry text as a footnote or remove the duplicate — whichever reads cleanly.

---

## Step 2 — Re-run extraction scripts against the new dump

The new dump has meaningfully more data. Run these two scripts (they're idempotent — they overwrite `lexemes.db`):

```bash
source ~/g2-dev/monitorulpreturilor/venv/bin/activate
python extract_lexemes.py          # reads dex-database.sql by default
python extract_taxonomy.py         # reads dex-database-sample.sql by default → pass --sql flag
```

Check defaults in each script:
- `extract_lexemes.py` — verify it reads `data/dictionaries/dex-database.sql` (the new file).
- `extract_taxonomy.py` — add `--sql data/dictionaries/dex-database.sql` if its default still points to the sample.

Expected outcome after re-extraction:
- `lexemes.db` Lexeme table: ~369k rows (was ~365k)
- `lexemes.db` Tag/ObjectTag/EntryLexeme/TreeEntry tables: refreshed counts matching new dump

After re-extraction, **do not** re-run `validate_diachronic.py` yet — the taxonomy join is still wrong and would regenerate bad domain data. Wait for the fix tracked in Step 1's backlog entry.

---

## Step 3 — Investigate Subtitle table as a Phase 2 corpus (recommended, not blocking)

The `Subtitle` table is 13 M rows of individual Romanian words from 966 YouTube video clips (sample shows Digi24 news content). Schema:

```
Subtitle(id, clipId, word, start)   -- `word` is a single token per row
VideoClip(id, videoId)              -- videoId = YouTube 11-char ID
```

This is pre-tokenised modern Romanian — exactly the right register for detecting whether words are still in contemporary use.

**To evaluate it as a corpus:**
1. Extract word-frequency counts: `SELECT word, COUNT(*) FROM Subtitle GROUP BY word ORDER BY 2 DESC`
2. Compare top-N vocabulary and coverage against CulturaX and Wikipedia counts already in `corpus_frequencies.db`
3. Assess: does it add signal beyond what we already have, given only 966 clips (~13M tokens)?

If coverage looks useful, write a `process_subtitles.py` script (parallel to `process_culturax.py`) that loads counts into `corpus_frequencies.db` under corpus name `subtitle_ro`. Add a backlog entry for this work.

---

## Files touched

| File | Change |
|------|--------|
| `docs/BACKLOG.md` | Add/update taxonomy join fix entry |
| `data/processed/lexemes.db` | Rebuilt by re-running extraction scripts |
| (no code changes in this plan) | |

---

## Verification

- After Step 1: `grep "load_taxonomy\|Meaning ID\|objectType=3" docs/BACKLOG.md` shows the new entry.
- After Step 2: `sqlite3 data/processed/lexemes.db "SELECT COUNT(*) FROM Lexeme"` returns ~369k; `SELECT COUNT(*) FROM ObjectTag` returns ~1,033k.
- After Step 3 (if pursued): query `corpus_frequencies.db` for `corpus_name='subtitle_ro'` and compare vocabulary size to other corpora.
