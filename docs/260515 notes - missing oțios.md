**Oțios is missing**
Short answer: probably according to the approach it doesn't belong — "oțios" is still used in formal and  written Romanian (newspapers, essays), so wordfreq likely gives it a zipf score ≥ 3.0 (the current cutoff for is_forgotten=true). 

The irony is baked in: the project is named after a word that isn't forgotten enough by its own criteria. 

Parameters you could tune: 

1. zipf threshold (currently 3.0 in validate_with_wordfreq.py) — lowering it to e.g. 2.5 would widen the  net to include words that are rare but not completely absent. This is the most direct lever. Trade-off:  more false positives (words that are rare but not diachronically declining). 
2. DEX frequency bins — the 0.30/0.50 cuts in the curated list affect what enters the candidate pool before wordfreq even runs. If oțios has a DEX frequency above the upper bin, it's filtered out before Phase 2. 
3. wordfreq language model — wordfreq uses large web corpora. You could substitute a specifically historical Romanian corpus comparison (the conceptual-roadmap idea), which would better capture diachronic decline rather than raw modern frequency. 

The honest answer: if oțios has a zipf ≥ 3.0 in wordfreq, it's because it genuinely appears enough in modern Romanian text that the frequency-based approach classifies it as alive. You could manually curate  it in, but that's methodologically inconsistent with how you're defining "forgotten." The approach measures corpus presence, not cultural salience — a word can feel archaic and elevated while still appearing in enough formal writing to pass the threshold. 

If you want oțios specifically, a curated override list is the cleanest solution rather than bending the  thresholds. 

------

Ranked options after that:

  1. [XS, VPS] Run extract_taxonomy.py --sql dex-database.sql + validate_diachronic.py on the VPS —  completes today's taxonomy work with full coverage instead of 5% sample.
  2. [XS] Mark backlog #0 and #15 as done — both corpus re-runs completed successfully with the expanded   word set (120k words vs old 15k).
  3. [XS→S] Implement #17 (flag words with no definition body) — quick win, adds has_definition column.
  4. [S, narrative milestone] Run search_wild.py on the extinct/declining shortlist —   forgotten_words_web_validated.csv is the one missing Phase 3 artifact. Moves from corpus signal to  real-world confirmation.
  5. [M, High] Lemmatization (#6) — buclele currently doesn't match bucle. Would meaningfully improve recall   but requires re-running both corpora.
  6. [M, quick layering] Use dex_etymology to filter modern borrowings (#12) — anglicism/franțuzism tags we  just added can immediately down-rank false positives without any re-processing.