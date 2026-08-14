# Sinonime

A second tool, separate from the oțios explorer: a Romanian **writing aid**. Type a word,
get alternatives you could actually use, ranked by how alive each one is in modern
Romanian. No definitions.

**Status (2026-08-14): documented, not built.** Branch `sinonime` carries these three
documents and nothing else. The UI is a deliberately separate conversation.

| document | what it is |
|---|---|
| [`findings.md`](findings.md) | What was measured, with the snippets that produced each number. Start here. |
| [`spec.md`](spec.md) | Build order, exact schemas, acceptance tests. Written to be executed without re-deriving anything. |
| [`escalate.md`](escalate.md) | The decisions the implementer must **not** make alone. |

## The one-paragraph version

The DEX dump has contained a complete synonym graph all along — dexonline's own
community-curated `Relation` table, 158,860 rows, unredacted, never read by anything in
this repo. It yields **164,399 word-level synonym pairs over 63,049 words in ~15 seconds**
with no HTTP, against ~4 hours of scraping for 2,075 words. Our own note saying synonyms
"can't come from the dump" was true only of the Litera dictionaries' *definition text*,
which is redacted for copyright, and got generalised to the whole subject in three places.

The reason to build on it rather than link to dexonline: **41.7% of the Romanian
thesaurus is dead**, and this project already owns the corpus rollup that says which 41.7%.
dexonline lists synonyms alphabetically, so `frumos` offers `bididel` and `boghet` beside
`arătos`. Ranking by modern currency is the product; coverage is table stakes.

The scraper stays. Measured, the two sources overlap by about a third and **59% of the
scrape's tokens are new information** — `Relation` is strong on modern vocabulary and weak
on the archaic layer, Seche is the reverse. It gets pointed at the remaining gap (21,489
words, ~18 h) instead of at everything.
