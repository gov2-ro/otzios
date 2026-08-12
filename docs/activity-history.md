# Activity History

Chronological log of meaningful work. Add entries under `## YYYY-MM-DD — Short Title`.

---

## 2026-08-12 — The quiz: `joc.php` → `ghici.php`, spoilers withheld, marks on every option

The whole `jocuri` block from `## Soft-launch`, plus joc's mobile compaction. New test:
`tests/test_ghici.js`.

**Three names, all different on purpose.** Nav label `quiz`, URL `/ghici`, `NAV_ITEMS` key
`ghici`. `/joc` and `/joc.php` 301 to it — in `.htaccess` *and* in `tools/dev-router.php`,
without which the rename reads as working locally right up until an old link is followed in
production. It is the one redirect in that file and safe for exactly the reason the note
beside it says the general case is not: no API endpoint ever answered at `/joc`, so there is
no POST for a browser to turn into a GET.

**`?game=` is the public spelling; `mode` stays internal.** `sensuri|grila|carduri` maps to
`sense|quiz|flash` in one table; `api/quiz.php`, `api/game.php`, `leaderboard.php`,
`localStorage['otios.quiz']` and the server's per-mode stats all keep the old words, because
renaming them re-keys stored state — the same argument that kept the device cookie `otios_dev`
this morning. `?mode=` still resolves. `replaceState`, not `pushState`.

**The part of speech was the spoiler nobody had listed.** The definition was already withheld
in `sensuri`; „s.f." beside the headword eliminates every option phrased as a verb, which on a
four-option round is most of the work. `.joc-spoiler` on the card's `.joc-pos`, the pane's
`.fp-pos-line` and its `.definition-text`, lifted by `revealSpoilers()` when the verdict lands.

**A race found while writing it, not in the note.** `showWordDetail()` is a fetch, so a fast
answer can land while the pane is in flight — the pane then resolved *after* the reveal and
re-hid the definition the verdict had just uncovered, leaving „✅ corect!" above an empty
panel. Hence `roundDecided`, separate from `answered`: one means the verdict is on screen, the
other that a choice was clicked.

**Marks beside every grilă option, and deliberately not detail.php's markup.** `#bookmark-btn`
and `#tags-row` are addressed by *id* in store.js's delegated handler, so four copies on one
screen would be four elements sharing one id with one answering for the rest.
`.joc-mark[data-joc-word][data-joc-tag]` instead, on the same `getWord`/`updateWord` store.
They are siblings of the option button, never children — `.joc-choice` is a `<button>`, and a
button inside a button is invalid markup parsers recover from by dropping the inner one, so
the failure would look like "the marks vanished" rather than like an error.

**Auto-advance on correct answers only**, and any pointer/key/wheel/touch event cancels it —
that cancel is what makes 1s safe rather than rushed, since the pane is live even on a win.
`load()` cancels too, so a manual „următoarea" cannot leave a timer running into the next
question and skip it. The countdown is a draining bar on the button itself: the thing that
counts is the thing you press to stop waiting.

**„avoid meh words from games" was already done** — `api/quiz.php` excludes `tag:meh` and
`tag:ascunde` from targets and distractors alike. Verified on real data rather than taken from
the comment: user 1 has 192 such marks and their pool goes 16,484 → 16,307.

**Centring the game controls was a slot change, not a CSS one.** They moved from
`$header_tools`, which lands inside `.brand-right` and is pinned right by `margin-left: auto`,
to `$header_center`, a flex child that can take the leftover width. `.landing-tagline` is
hidden on this page — it is the other `flex: 1` child, and two of them each centre in their
own half.

**On a phone this page hides the footer and drops its nav labels**, both `body.page-ghici`
-scoped. `--statusbar-h` has to go to 0 with the footer or its height stays behind as dead
space (`body`'s padding and the sheet's `bottom` both read it). The nav labels going is a
deliberate exception to this morning's pass that put them back: measured at 390px the bar
wanted ~460px, and this is the one bar also carrying a mode switch, a score and a leaderboard
button.

**`tests/test_ghici.js`** is the first test here to need something off-disk (`jsdom`) — the
page's behaviour is DOM behaviour and none of it is reachable by asserting on raw HTML. It
skips cleanly when jsdom is absent. Two things it cost to get right: jsdom ships no `fetch`,
so without a polyfill the page loads and simply never renders a card; and the correct-answer
branch cannot be reached on demand (which option is right is sealed in the `qid`), so it plays
rounds until it wins one and asserts both branches as they come up.

---

## 2026-08-12 — Soft-launch pass: nav labels on mobile, single-option toggles, self-hosted assets, Voroave

Eight of the open `## Soft-launch` items in `docs/BACKLOG.md`, all shell-level. The jocuri
block and joc's mobile compaction are untouched.

**The mobile nav labels were a scoping bug, not a decision.** `.nav-label` is the same class
in both bars, and `@media (max-width: 900px) { .nav-label { display: none } }` was written
for the footer's `.site-nav` — it silently stripped the labels off `.top-nav` too, leaving
the header a row of bare emoji on a phone, which is exactly what the comment above
`.top-nav-item` says that bar exists to avoid. Now `.site-nav .nav-label`. The room came
from the two controls flanking it, as the note asked: „legendă" is visually-hidden for good
and `.shortcuts-link kbd` is exempted from the blanket `kbd { display: none }` (so the link
is its own `?` cap, 18px instead of 52), and „filtre" is a `.filter-btn-label` span hidden
below 768px. Both keep their accessible name in `title` / `aria-label`.

**Both two-state toggles now draw only the option you can switch *to*.** Theme keys off
`:root[data-theme]` — set by the pre-paint boot script — rather than the `tg-active` class
`prefs.js` adds on load, which would have flashed both caps; view can use the class because
`#btn-cloud` ships with `vt-active` in index.php's markup. **The `+` separator had to be
deleted rather than reset**: it still matches a `display:none` sibling, so the survivor drew
a left border against nothing, and no reset could win — brutal restates the rule at (0,3,0)
and again at (1,3,0) under `#status-bar`, both loading after app.css. With one visible
button per group it is dead code, so it left `brutal.css` too. `.scale-btn` keeps its.

**Marks are 30px on desktop, 40px on a phone** (were 22/28). They are the site's primary
verb and were the smallest interactive thing on the page. On mobile the height comes out of
the key caps, which are hidden there anyway.

**Fonts and htmx are in the repo — no third-party request on any page load.**
`assets/lib/htmx-2.0.4.min.js` (`lib`, not `vendor`: a global gitignore eats `vendor/`) and
`assets/fonts/{app,doc}-fonts.css` plus 20 woff2, 796 KB. htmx is verified rather than just
downloaded — the sha384 of the unpkg file matches the `integrity=` already in the pages, so
it is bit-for-bit what the CDN served. Only the `latin` and `latin-ext` cuts are kept (ă â î
ș ț live in latin-ext); variable axes survive intact. Two stylesheets because metodologie
wants Inter Tight / JetBrains Mono and the app pages do not — one shared file would put 130
KB of Inter Tight on the explorer for nothing. `tools/fetch_fonts.sh` regenerates them.
Simple Analytics stays external on purpose: self-hosting a tracker measures nothing, so
that is a product decision about whether it stays at all.

**`DEFAULT_SKIN` is `govuk`.** Two places, and the second is easy to miss: `despre.html` is
static since earlier today and carries a hand-copied boot script with the skin list and the
default inside it. Left alone it would have been the one page in the site opening in beton.

**Renamed to Voroave — surface only.** Titles, `og:`/`twitter:` and visible marks across
stats, joc, liste, lista, admin, despre, metodologie. The internal identifiers stay `otios`
deliberately: the `otios_dev` cookie *is* the account, so renaming it hands every visitor a
new one and orphans their marks; `otios.theme` / `otios.skin` / `otios.textscale` would
reset preferences; `OTIOS_BASE` / `OTIOS_PRIVATE_DIR` / `OTIOS_ADMIN_TOKEN` are per-install
server config. Left for the author: metodologie's paragraph explaining the *Oțios* name was
about the name, so it could not be left untouched — rewritten to the minimum true version
(Voroave now, Oțios before, the story of the word kept whole), timeline entries left as
historical record.

**The new `.landing-tagline` is centred with `flex: 1` + `text-align: center`**, not
absolute positioning — it centres in the gap the two clusters leave and cannot end up
underneath them when the bar tightens; it ellipses rather than pushing the controls, and
hides below 901px. It needed re-grounding in `govuk` and `registru`, which force
`.brand-bar` black in both themes while `--text-3` is a *page*-ground token. That is the
list CLAUDE.md already keeps for anything living in that bar, and it matters more now that
govuk is the default.

Pre-existing and untouched: `tests/test_store_sync.js` fails at „sync watermark stored" and
then throws on `JSON.parse(undefined)`. Verified against the committed `store.js` — it fails
identically there, so it is not from this pass.

---

## 2026-08-12 — Colecții, marked tags that show as marked, static despre, no facet counts

**Renamed to „Colecții" in the UI only.** Page title, `<h1>`, section headings, the
`liste.php` toasts, the despre section and admin's back-link. The table, the endpoint, the
`/liste` URL and `lists.source_tag` are untouched — `/liste` is a shared-link surface and
the rest is stored data. `NAV_ITEMS`' label was already changed in the working tree.
despre's „Cele două liste" stays: it names the *seams*, a different sense of the word.

**`ascunde` retired as a bucket — three, not four.** Removed from `LIST_BUCKETS`, which is
the single declaration point, so `liste.php`, `publish_bucket` and `refresh` all follow.
The tag itself still works: `api/quiz.php` reads `tag:ascunde` literally and old
annotations still resolve. Its bullet is gone from despre's mark list. `index.php`'s
shortcut table still lists the `a` key — pre-existing, left alone.

**„Alese" removed** from `liste.php` as duplicating „Colecțiile mele" for the reader who is
also the curator. `editor_pick` still drives the ★ chip; it just has no card here. The
`ui.db` query, `$featured_packed` and the `.list-card--featured` / `.featured-words` CSS
went with it.

**„Publicate de mine" folded into the bucket cards.** The same collection used to appear
twice under two names — „favorite" above and „favorite — pax1" below — with its actions
split between them. A published row is a *state* of the bucket, so each card now carries
both: `actualizează` / `fă privată` / `șterge` when published, `publică` when not, and a
quiet line naming the published title with a link to its page. Three details:

- **`publică` is always `publish_bucket`,** including re-publishing something made private
  — it reuses the row *and* refills it, so it cannot serve a stale snapshot. `toggle-public`
  now only ever goes the other way.
- **The card shows the live bucket count** and names the published one separately when they
  differ, which is the only thing that makes „actualizează" legible as an action.
- **`șterge` says which of the two it removes** — the snapshot goes, the marks stay.

**„Alte liste" added** for anything with no bucket to fold into: hand-assembled lists and
ones published from `ascunde` before it was retired. Hidden when empty. Without it, the
section that used to show them was the only way to reach them.

**A marked word's tag now shows as marked in the detail panel.** The logic was never
missing — `hydrateDetail()` has toggled `.active` on `.qt-btn` and `#bookmark-btn` all
along. Two skins were flattening it in CSS: as bare `.qt-btn.active` the rule is (0,2,0),
the same weight as `[data-skin="x"] .qt-btn`, which loads after `app.css` and won. So
`brutal` and `registru` repainted the pressed button to match the resting one without any
rule naming `.active` — brutal's own comment promised "the pressed one is filled solid"
while its only `.active` rule set a border colour the base rule had already set. Since
pressing an applied tag *removes* it, the panel was inviting you to un-tag by accident.

Fixed by shape rather than by two more overrides: the active rules carry `.fp-btns` (0,3,0)
so a skin's base rule cannot reach them, and being token-driven they give any future skin a
visible marked state in its own palette for free. `brutal` and `registru` then got
deliberate inverted-block treatments matching what each already says with `.seg-opt`. Also
mirrored into `aria-pressed` — the state was colour-only. Verified with headless Chrome
across all six skins × light and dark; the third instance of this pattern, so it is written
up in CLAUDE.md beside the Filtre rail and `.dex-link` notes.

**`despre.php` → `despre.html`.** Once the live counts from `ui.db` were cut from the copy,
the only PHP left was the shell — a database dependency for a page that prints nothing from
it. `/despre` resolves with no rewrite change: `.htaccess` and `tools/dev-router.php` both
try `$uri.php` then `$uri.html`. Built from the actual rendered output rather than by
hand-editing, so nothing was missed. Four things are now hand-maintained and the file's
header comment names all four: the baked skin list and `DEFAULT_SKIN` in the pre-paint boot
script, the inlined copy of the header nav, relative paths in place of `BASE` (which is what
keeps the /oțios/ subfolder deploy working — do not "tidy" them to absolute), and a relative
`og:image` with `og:url` dropped, since `otios_abs_url()` derived the host from the request
and a static file has none. Verified against all five skins via the boot script and rendered
at 1100px.

**Per-option facet counts removed.** The filter sheet showed, beside each option, how many
words it would return given everything else set. Correct, and cut anyway: only a few groups
were ever wired, so the sheet read as half-instrumented, and the numbers cost a row —
„listă" wrapped to two lines because `relevante 2.682` and `curiozități 12.860` no longer fit
side by side. Gone: `facet_counts()` + `facet_predicate_is_usable()` (`_lib.php`), the
`$facets` call site in `search.php`, the `#facet-data` OOB payload in `word_list.php` and its
placeholder in `index.php`, `applyFacetCounts()` in `app.js`, the `.fs-count` CSS, and every
`data-facet` / `data-label` hook. CLAUDE.md keeps the two properties a future implementation
would need (neutral value per group, one query per group) and the rule that it comes back for
all groups or none.

**Identity model assessed, not built** — `docs/BACKLOG.md`, under "Server-side accounts".
Short version: browser fingerprinting is the wrong instrument (false merges give strangers
each other's data, false splits happen on every UA change, and it collapses the two distinct
users `test_moderation.js` needs); a short-lived single-use link code is the right one, and
`devices.user_id` already supports N devices per user — 858 users have exactly one device
each only because no endpoint can add a second.

**The duplicate public lists were test fixtures, not a bug.** 49 public rows, 49 distinct
`user_id`s, zero (user, source_tag) duplicates — the per-user constraint holds.
`tests/test_lists_api.js` (nickname `tester`) and `tests/test_moderation.js`
(`owner-mod-test`) each mint fresh anonymous users per run and leave their lists behind, as
their own headers say. Only the dev `app.db` is affected.

Verified against a copy of `app.db` with a device token minted for the real user, so the
published/stale/orphan states all rendered with real data. `test_lists_api.js`,
`test_moderation.js` and `test_editorial.js` pass; `test_store_sync.js` fails identically
on a stashed tree, so it is unrelated.

---

## 2026-08-11 — clean URLs, and only portrait figures float

Two corrections to the morning's document layout.

**Figures come back inside the content column, and only portrait ones float.** Pushing
every figure out into a gutter left the prose narrow and the right edge ragged, and a
landscape screenshot squeezed to a quarter width is unreadable anyway. So the rule is now
orientation rather than size: portrait floats right at 25% with the text wrapping beside
it, landscape stays in the flow at full width. The third grid column is gone and both
pages sit at 1110px (200 TOC + 44 gap + 820 text). `despre.php` measures 3,023px — up from
2,243 when everything was tiny and out in the margin, down from 5,565 before any of this.

**`/despre` instead of `/despre.php`.** Two rewrites in a new `public/.htaccess`, each
firing only when the path is not already a real file and the extension-ful version exists.
No `RewriteBase` — the conditions test `%{REQUEST_FILENAME}`, so it works at any URL depth,
which this app needs.

The interesting decision is what is *not* there: **no redirect from `/despre.php` back to
the slug.** It would look tidier and it would break the app. Every API call goes to an
explicit `api/*.php`, and `sync`, `lists`, `profile` and `game` are POSTs — a 301 on a POST
is not required to preserve the method, and browsers historically turn it into a GET, so
the write silently becomes a read. Excluding `/api/` would work but makes the file a list
of exceptions the next endpoint has to remember to join. Both spellings resolve; canonical
tags name the slug.

**`php -S` ignores `.htaccess` entirely**, which is exactly the shape of gap where a broken
link ships because nobody could see it locally. `tools/dev-router.php` mirrors the two
rules so dev matches production; it lives outside `public/` because anything in there is
deployed and would be reachable over HTTP. Verified with it: every slug, both legacy
spellings, all assets, and a POST to `api/sync.php` — zero failed requests across all six
pages.

## 2026-08-11 — sticky contents and side figures on the document pages

Asked for smaller screenshots pushed out of the text column, and a documentation-style
sticky table of contents on both `despre.php` and `metodologie.html`.

Shared as `assets/doc.css` + `assets/doc.js`, which works because the two pages use
different stylesheets but the same token *names*. Layout is a three-column grid —
TOC · content · gutter — above 1080px. The gutter exists to hold the figures: they
`float: right` into it with a negative margin rather than taking a grid cell, because text
has to wrap back under a short figure and a figure has to sit beside *its* paragraph rather
than at a row boundary the grid chose. Screenshots are ~24–31% of the block width, capped
at 340px tall, and click through to full size — the point of shrinking them is that the
detail stays reachable.

Measured effect on `despre.php`: **5,565px → 2,243px** of page at desktop width.

`doc.js` runs in two modes. `metodologie.html` already had a hand-written TOC whose wording
is editorial — it shortens „Faza 2 — Validare diacronică" to „Faza 2" — so that list is left
exactly as written and only gains scroll-spy; `despre.php` has none, so one is built from
its headings. Scroll-spy tracks the last heading *past* the reading line rather than the
intersecting one, because sections here run from two paragraphs to forty and "is visible"
marks several at once and flickers.

One trap worth recording: **`metodologie.html` capped `.article` at 760px**, which was right
for one column and squeezes every track of a three-column grid. The page went from 13.5k to
**30k** pixels tall before the cap was raised — taller on desktop than on mobile, which is
the tell.

## 2026-08-11 — the document pages could not be scrolled on desktop

Reported against `despre.php`: no scrolling at desktop width, fine once the window was
narrowed. That last part is the whole diagnosis — the `max-width: 768px` block already
relaxes `body { overflow: visible }`, so the bug existed **only** on desktop, which is
also why it had gone unnoticed.

`app.css` styles `body` as the explorer's app shell — `height: 100vh; overflow: hidden`, a
flex column whose `#word-list-container` scrolls inside itself. Every page loading app.css
inherits it, and for a page that is just prose that means no scrolling at all. Measured:
`despre.php` had 5,565px of content in an 800px window with `overflow: hidden`.

**`liste.php` had the same bug** — 2,418px of content, same lock. So this was pre-existing
and the new page merely inherited it; `lista.php` (a shared word list, and the page most
likely to arrive from someone else's link) is in the same family and was fixed with them.

Fix is a `body.page-doc` opt-out restoring `height: auto; min-height: 100vh; overflow:
visible`. Shells keep the default: verified after the change that `#word-list-container`
still scrolls internally on the explorer, and that stats/index/joc still hold their fixed
viewport.

## 2026-08-11 — a Despre page, and the tag explainer finally stays dismissed

**The explainer bug was not where it looked.** `dismissQtExplainer()` wrote to
localStorage correctly and `hydrateDetail()` read it correctly — verified both. What
happened is that the detail panel is re-rendered when you open the next word, and the
fresh `#qt-explainer` arrives with no inline style, so the banner came back on every word
while localStorage still said dismissed. (The giveaway: hydrateDetail *did* set
`display:none`, and a moment later the computed style was `flex` with the inline value
gone — a different element.) Fixed by moving the state to a `.qt-dismissed` class on
`<html>` with CSS doing the hiding: a root class cannot be lost when the element under it
is replaced. The storage was never the problem; re-applying an inline style after every
render was.

**Caught while screenshotting: the explainer copy had gone stale by my own hand.** It said
`meh` „dispare din listă", which stopped being true earlier the same day when meh became a
demote. Copy that describes a filter as removing something it no longer removes is worse
than no copy.

**`despre.php`** replaces `statistici` + `metodologie` in the nav rather than joining them
— three labelled entries competing for a phone bar is the measurement that split this nav
between header and footer in the first place. Both are linked from the new page. They stay
in `NAV_ITEMS` so `$page` still marks them current, and both partials now name the keys
they draw instead of diffing the const, which would have put them back silently.

The page carries its own og/twitter card and a canonical, via a new `otios_abs_url()` that
reads `X-Forwarded-Proto`/`Host` first so it stays right behind a proxy. Its counts come
from `ui.db` rather than being typed in, so it cannot drift from the data. Four cropped
screenshots in `public/assets/despre/`, captured with Playwright.

Also: the sort dropdown gained a „?" inline with the select, and all nine question marks
now right-align in one column. That needed `width: 100%` on `.fs-label` — `.fs-section` is
a flex column, so the heading was shrinking to its text and taking the „?" with it — and
the auto-margin rule had to move *after* `.fs-help`'s own `margin-left`, same specificity,
source order deciding.

Loose end noticed and not fixed: the detail panel still prints `zipf ro 0.0 / zipf en 0.0`
for essentially every word, which is the same dead wordfreq data the explore filter was
removed for.

## 2026-08-11 — the filter sheet grows numbers, explainers, and one fewer way to hide

Six changes to the sheet, two of which were questions.

**`meh` now demotes instead of hiding, and I think that is right.** It removes an asymmetry
that had been nagging: the curator's marks were the only human signal allowed to *subtract*
from the default view, while the community's could only reorder. Now neither subtracts —
`editor_demote` moved from a WHERE clause into a leading ORDER BY term
(`demote_order_sql()`).

But the control stays, and the measurement says why: under the default order the first
demoted word lands at **position 2,556 of 2,682 — page 11**. Sinking is hiding, in every
practical sense. The difference is that „normal" brings them straight back, where a WHERE
clause with no control would leave nothing to undo. Pinned by `test_editorial.js` §2c,
which fails the moment someone turns it back into a filter.

**Per-option counts, and yes they recalculate.** `facet_counts()` runs one query *per
group* rather than per option — conditional aggregation counts every option of a group in
a single pass, so it is eight scans of an 18k-row table (12–40 ms), not forty. The subtle
part is that each group must be counted with its own filter **actively neutralised**, not
merely unset: removing a param reinstates its *default*, and most of these default to
subtracting, so `unset('seam')` counted curiozități against a relevante-only base and
reported 0. They travel to the sheet as one out-of-band attribute, which needs a
placeholder `#facet-data` in the markup — `hx-swap-oob` replaces an element that already
exists, and drops the payload silently otherwise.

**`populare` is now the default sort.** I had argued against this on the grounds that
identity is an anonymous device token. What changed my mind is that votes can only ever
reorder — nothing in that path removes a word — so the cost of being wrong is a nudge in
position, bounded by the damping. Worth knowing: `barabor`'s 20 votes are still all test
fixtures, so the local front page looks stranger than production will.

**`seam` became a checkbox group and lost „toate".** The seams are a partition, so both
ticked already is „toate"; the third radio was a second name for a state the other two
could express. One wrinkle it introduced: its default is 1-of-2 where every other checkbox
group defaults to all-of-N, so `groupIsDefault()` / `URL_GROUP_DEFAULTS` had to exist —
without them the URL carried `?seam=relevant` on every page and the chip bar claimed a
filter nobody had set.

**Diminutives now default to „fără"**, and every section gained a „?" that reveals a
one-line explainer — a real button and paragraph rather than a `title=`, because a title
needs a hover and a phone has none. That is the device where an unfamiliar filter name is
hardest to guess at, so hover-only help is missing exactly where it is most needed.

## 2026-08-11 — clearing the open items: two removed, two closed won't-fix

Triage of what today's work left behind, with the two questionable ones measured first
rather than guessed.

**Removed the `zipf` explore filter.** wordfreq scored 17,533 of 17,577 words at exactly
`0.00`, so any floor above zero left 44 rows out of 18,270. It was the last place wordfreq
touched the UI, and the same resolution problem that got the „rare" tab deleted. Same call
as `hide_loanwords` and `proper_noun_like`-as-a-browsing-filter: a control that reveals
nothing is worse than no control.

**Fixed `.fav-star` at 3:1, not 4.5:1, and that distinction is the fix.** I had filed this
as needing a palette decision because 4.5:1 turns the gold brown (`#D4A017` → `#8E6B0F`).
That bar was wrong: the ★ sits *inside a button that says the word „fav" beside it*, so the
colour carries no information and it is a graphical mark (WCAG 1.4.11), not text. At 3:1
the gold survives — `#AE8313`, `#B38105`, `#AB7617`.

Worth noting how the first attempt was still wrong: I computed against the *row* ground
when the button has its own background, which left paper at 2.83 and velin at 2.87 —
"fixed" and still failing. Re-measured against the real ground in-browser; all six skins ×
both themes now clear 3:1.

**Closed won't-fix, both measured:** inflected forms as headwords is 80 words, *none* in
the `relevant` seam, and most are legitimate nominalised infinitives (`zimbire`,
`trândăvire`, `dormire`) — the real offenders went with the deleted tier. And dropping the
inert `en_zipf` column would be a schema migration for zero benefit; the rule that matters
is written down instead.

Also: `docs/wordfreq-recipe.md` now carries a status banner saying the screen feeds
nothing, and the editorial marks were re-exported (13 pick / 191 demote in `app.db`, of
which 12 and 176 exist in the rebuilt shortlist).

## 2026-08-11 — the main list picks up 706 words the stale candidate file was hiding

The unfinished half of the morning's stale-file fix. `create_curated_list.py` had been
re-run, taking the candidate list from 140,308 to 145,358 words, but `validate_diachronic.py`
reads that file as its candidate set and had not been re-run — so the shortlist was still
built from the old, smaller one.

Re-ran the phase: **17,577 → 18,270 words, +706 added, 13 removed.** `word_ids.tsv` +706
with zero deletions, so every shared link still resolves. Only 5 of the new words land in
`relevant` (`boboni`, `brodărie`, `bulucbașa`, `bâț`, `bălăi`); the other 701 are
`curiosity`, and they are exactly the obscure end — `alergaci`, `alnicie`, `amăgie`,
`arcășel`, `baistruc`, `baraboiște`.

The 13 that left are all junk the old candidate list had been carrying: `chaise-longue`,
`córdoba`, `balneo-climatic`, `calea-valea`, `mai-mare`, `brânzeturi`, `viscere`,
`neogreacă`, `paciuli` — hyphenated compounds, foreign phrases and plurals. Two of them
were `sirius` and `weltanschauung`, which is why `proper_noun_like` now marks **zero**
words rather than two. That flag was already documented as no longer a browsing filter for
exactly that reason; it is now empty.

Worth recording separately, because it looked like a crisis and was not: **the main list's
taxonomy was never affected by the stale file.** `validate_diachronic` calls its own
`load_taxonomy()` against `lexemes.db` with the corrected join, so the curated CSV only
ever supplied *which words to consider*, not their tags. `visternic` reads
`figurat|rar|învechit` throughout. The deleted rare tier was the only thing that read the
stale taxonomy columns.

Counts refreshed across CLAUDE.md: relevant 3,499, curiosity 14,771, default view 2,685,
`newest_dict_year` coverage 17,806 of 18,270, archaic spellings 107 in the default view,
440 regional words in the relevant seam.

Also found while checking what was still actionable: **the `zipf` explore filter is dead**
on the main list — 17,533 of 17,577 words score exactly 0.00, so `zipf_min` above zero
leaves 44 words. Same wordfreq resolution problem as the deleted tab, in the last place
wordfreq still touches the UI. Filed rather than removed.

## 2026-08-11 — the „rare" tab is deleted, and `urme azi` takes its place

Three fixes to that tab in one day and it still showed `bețiv`, `haz`, `ocoli`, `haiduc`.
Asked to explain rather than patch again, and the explanation was the answer: **I had been
tuning thresholds on an instrument that has no resolution in the range being measured.**

wordfreq's Romanian list, over 60,000 of our candidates: **59,785 score exactly 0.00** —
never heard of them — and 215 score anything at all. Its lowest real values are ordinary
words. `casă` 5.25, `haz` 3.31, and `zapciu`/`vornic`/`logofăt`/`ispravnic` all 0.00,
indistinguishable from each other and from every word it does not know. A tier defined on
"3.0–3.5" could only ever fill with common words. No threshold fixes that, which is why
three of them in a row did not.

Two more facts made the decision easy. The tab had **zero overlap** with the shortlist:
every one of its 219 rows was a word this pipeline had already measured against 17 billion
tokens and correctly called still-used — `haz` has 62,021 modern occurrences. And the idea
the tab was reaching for already had a population inside the main list.

So the tab is gone and the idea is a filter: **`urme azi`**, three buckets over
`modern_band`. The direction is the interesting part and it reads backwards — *more*
modern usage means *better* material. Band 2 is `zapciu`, `birjă`, `vechil`, `dorobanț`,
`cocoană`, `jupâneasă`, `ișlic`, `iscăli`; band 0 is `celșag`, `racaleț`, `oglavă`,
`toroști`, `fistău`, `barabor` — dictionary ghosts that never circulated. The same trap
`$SORT_OPTIONS` already records for `sort=rare`. Pinned by a test, because inverting it
would look plausible.

Bands rather than raw counts, and the edges come from `validate_diachronic`'s own
`MODERN_RARE_OCC` / `MODERN_ALIVE_OCC` through `scaled_modern_thresholds()` at build time —
a number in PHP would silently change meaning the first time a corpus is added. Three
bands, not four: `alive_occ` is also the shortlist's eligibility ceiling, so a fourth is
unreachable by construction (max `modern_occ` is 1,998 against a floor of 2,000) and would
be a control with nothing behind it.

**What went with the tab:** the tier switch, `dex_max`, `hide_loanwords`,
`#dex-rare-control`, and the entire tab-gating apparatus — three sections kept in step by
hand across three places, wrong in all three on any deep link. That machinery existed only
because there was a second tab, and every filter added while it existed had to decide
whether it was tab-specific. Old `?word_tier=rare_in_use` links land on the list now rather
than returning nothing.

The generalisable bit: **check that your measuring instrument has resolution in the range
you care about, before tuning anything against it.** One histogram at the start would have
replaced three rounds of threshold work.

## 2026-08-11 — the rare tier judged verbs by their infinitive

Pushed back on: the tier was still full of common words after the morning's fix, and the
relevante/curiozități control did nothing on that tab. Both were right, and the first
diagnosis had been wrong.

**I had blamed meaning-level tag bleed and called it unfixable.** That is real but it was
not the main cause. The main cause is that wordfreq measures *surface strings*, and
Romanian verbs are heavily inflected, so a citation form is systematically rarer than the
verb: `mărturisi` 3.41 against `mărturisit` 4.01, `asemăna` 3.11 against `aseamănă` 3.79,
`păți` 3.08 against `pățit` 3.87. Judging a lemma by its infinitive calls every common
verb rare — **the exact mistake CLAUDE.md already names for the corpus side**, where the
rule is "always roll them up through `inflected_forms.db`, or every verb reads as
extinct". The rare branch never got that rollup; the main pipeline has had it for months.

The giveaway was words *above* the ceiling sitting inside the tier: `secret` 4.75,
`dor` 4.50, `greșit` 4.67, `ceartă` 4.00. Those are the second failure — the gate ran on
simplemma's lemma, and the lemmatizer picks homograph verbs (`secret` → `secreta` "to
secrete" 3.15, `dor` → `durea`, `greșit` → `greși`). It was testing a different word.

One fix covers both: `paradigm_zipf()` takes the max Zipf over the headword's whole DEX
paradigm, keyed on the **surface form** so no lemmatizer can redirect it. Max rather than
sum, because the question is "is any form of this in current use?" and Zipf is a log scale.
Lazy, so it costs 17s over 145k candidates rather than walking the paradigm table for
every row. 299 → 219.

**The second complaint was a real UI bug and older than any of this.** `applyUrlToForm()`
sets the radios without dispatching `change`, and the tab gating ran at script-evaluation
time with `word_tier` still at its markup default. So any deep link or reload of
`?word_tier=rare_in_use` left all three tab-specific sections in the *other* tab's state —
seam and classes visible where they do nothing, and the DEX ceiling hidden on the one tab
where it works. Clicking the tab was always correct, which is exactly why nobody saw it.
Fixed by re-running the gate after the URL is applied. `seam` was also missing from
`activeFilterChips()`'s tab guard, so a stale `seam=curiosity` chipped „listă: curiozități"
over a list that had never been filtered by it.

CLAUDE.md's "three places" rule for tab-specific controls turns out to have a fourth: the
*initial* state, as distinct from the change handler.

Residue is now narrow and named: archaic nouns homographic with common verb forms
(`judec`, `leg`, `ucid` — DEX nouns, so the `T`/`IL` filter misses them), plus the tag
bleed. Neither is separable without sense-level frequency data.

## 2026-08-11 — the rare tier was running on a three-month-old bug

Asked why `credit`, `ecran`, `universitate`, `ceapă`, `pian`, `cannabis` were showing up
as "rare". Three stacked causes, and the first is the kind worth writing down.

**`forgotten_words_curated.csv` was dated 2026-05-16. The taxonomy join fix landed
2026-05-19.** `rare_words_wordfreq.csv` was regenerated on 9 June — *after* the fix, which
is what made it look innocent — but it was generated *from* the stale curated CSV, so it
inherited the pre-fix `dex_register` column that the backlog already called noise. The fix
commit's own instruction ("re-run `validate_diachronic.py`") was followed for the
shortlist; `create_curated_list.py` was not, and nothing downstream could tell. Recomputing
the gate against the current join: only **18 of the 110** kept an archaic tag at all.

The lesson is about *dating artifacts against the commits that fix their inputs*, not
about the join. A regenerated file three weeks after a fix still carries the bug if its own
input predates it.

Re-running the phase also filled `dex_etymology`, empty until now and named in the backlog
as what blocked etymology filtering.

**Cause two is not fixable and is now documented as such.** DEX register tags are
per-meaning, and the extraction flattens them onto the headword: `atac` carries
`articulat`, `fonetică; fonologie`, `limba franceză`, `limba turcă`, `muzică`, `popular`,
`regional` and `învechit` simultaneously. Nothing is both French and Turkish — that is
every sense of every entry collapsed. One archaic sense makes the whole word `învechit`.
This is the same bleed CLAUDE.md records for `dex_pos`, which escaped it by switching to
`Lexeme.modelType`; `dex_register` has no equivalent.

Measured and rejected on the way: requiring the archaic marker to be the *only* register
tag. 593 → 318 words, and the top of the list is unchanged — `tehnologie`, `tren`,
`statut`, `consiliu`, `bloc`, `ambulanță` all carry `învechit` as their sole tag. It costs
recall and buys no precision, so it is not in.

**Cause three: `--upper-threshold 4.5` was never a rarity bound**, admitting 13–32
occurrences per million. Now 3.5 (≈3/million), as the script default so a re-run
reproduces it. The ceiling is the only lever that works, because zipf is a usage
measurement where the register tag is an editorial note about one sense.

Tier 110 → **290**, larger because the broken join produced false negatives too. The low
end is what the tier exists for (`răgea`, `sfetnic`, `zidire`, `tină`, `braniște`,
`baltag`); the top still carries residual bleed (`dor`, `oaste`, `poruncă`), which is cause
two and is now written down rather than papered over. `word_ids.tsv`: +141, 0 deletions.

Two further findings filed rather than fixed: the tier is decided on *lemma* zipf but the
UI displays *surface* zipf, so 15 of the 290 show `0.0` in a tier defined as `≥ 3.0`; and
`create_curated_list.py` emits inflected forms as headwords (`țipând`, `citarea`,
`patinoare`), which `inflected_forms.db` already has the map to catch.

## 2026-08-11 — editorial picks and community votes

The year-old backlog item („Publish top faves list, hide/demote meh words for everyone
else") shipped, with its own objection designed around rather than waived. That objection
was: one person's taste silently rewriting everyone's default view, on an identity model
where N votes cost N cookie clears.

The resolution is that **the two signals are separate and only one may subtract.** Curator
marks come from `data/editorial.tsv` — tracked in git like `word_ids.tsv`, exported from
`app.db` by `tools/export_editorial.py --user N` — and become `words.editor_pick` /
`editor_demote`. They can hide, through a fifth `fără/cu/doar` control („respinse", default
`fără`). Community marks never touch `ui.db`: they are aggregated live by
`vote_counts_subquery()` and may only reorder, through a new `populare` sort. Forging votes
buys rank, never removal.

A file rather than a live read of `app.db` for two reasons that both hold independently:
the build runs on a laptop while `app.db` is on the server, so they never see each other;
and a signal that removes words from what every visitor sees has to be a reviewable diff.

Two measurements shaped the blend. First, `quality_score` is far more compressed than it
looks — the whole `relevant` seam is 3,495 words between 92 and 121, with 76% inside a
ten-point band, so a linear weight of 5/vote would let four votes carry a word from the
median to the top forty. Hence `4·ln(1+votes)` rounded into bands (`VOTE_BOOST_SQL`; bands
because SQLite's `LN()` is a compile-time option): **each doubling of the votes is worth
about two more points.**

Second, and this is the part worth remembering: **the sockpuppet scenario had already
happened by accident.** `barabor` carried 20 distinct-user ★ votes, `subdialect` 19,
`jbârc` 13 — and every single voter was a test-suite fixture account (`tester`,
`owner-mod-test`, `pluto`), created by `test_lists_api.js` and `test_moderation.js` runs.
`_lib.php` already recorded that `jbârc`/`barabor`/`hâșăi` at the top is "the opposite of
what the list is for", so a naive vote sort would have reproduced exactly the wrong list,
from the test suite, with no attacker involved. Under the shipped blend `barabor` goes
92 → 104: real movement, well short of `văz` at 121. `subdialect` would have reached 124
and topped the list — it is `editor_demote`, so the curator's veto held.

Also: „Alese" on `liste.php`, rendered from `ui.db` with no `lists` row, so it exists on an
install with zero users; deliberately unfiltered by seam, since 4 of the 11 picks sit in
`curiosity` and that is the signal that the threshold is arguable. ★ chip on picked rows in
both views. `tests/test_editorial.js` pins the two invariants; `APP_DB_VERSION` 4 adds
`idx_annotations_word`, without which the vote aggregate full-scans on every request.

**The ★ chip started on `--star` and moved to `--accent`, for two reasons found in the
Playwright pass.** Contrast: `--star` measures **2.22:1 on paper light and 1.98:1 on
tezaur light** against the word row, where `--accent` clears 4.5:1 in all six skins ×
both themes (worst case brutal light, 4.55:1) — and at 10px this is small text, the bar
CLAUDE.md already sets for the `--text-4` freq superscript. Meaning: gold already says
"*you* favourited this" (`.fav-star`, same token), and a curator pick is a different
claim. Both problems had the same fix.

That measurement also turns up a **pre-existing** finding filed to the backlog: `.fav-star`
uses `--star` at the same failing ratios, so the user's own favourite marker is below AA in
light mode on two skins. Not touched here — darkening the token ripples through the palette
and that is a design decision, not a bug fix.

Visual pass driven by Playwright rather than by eye (`npx playwright`, headless Chromium):
five class rows render in all six skins, the „doar"/„cu"/„fără" round-trip writes *and
clears* `?editorial=` (the writer half is the one that silently breaks), the chip reads
„DOAR RESPINSE", and carrying „doar" onto the rare tab returns 110 words rather than 0 with
the class section correctly hidden.

Left open: each test run still leaves a fresh anonymous user in the dev `app.db`, and those
users are the entire vote signal there.

## 2026-08-11 — is this worth a paper?

Asked and answered in `docs/publication-assessment.md`, written to be picked at later
rather than acted on. Verdict: yes, but not the paper that exists today.

Three things are genuinely publishable — the paradigm rollup as a *method* (DEX's own 2.27M
inflected forms in place of a lemmatizer, with the `strugur`/`strugure` 12,176→749 receipt),
the four measured negative results (ppm across a 1,187× size gap; CoRoLa's 1945+ span
disqualifying it as a modern signal; `subtitle_ro`'s folk-music sixth, where 444 of 2,446
attested shortlist words appear only in those clips; LUMRO's 111 authors vs 175 novels), and
the 16,941-word resource itself. The negative results are the strongest material and the
part nobody else publishes.

The blocker is one thing and it is not new: `conceptual-roadmap.md` §2 named it and it is
still open — no evaluation against any ground truth, `ARCHAIC_TAGS` being a feature rather
than held-out labels. Backlog entry under "Publishing a paper (2026-08-11)" carries the
two ~one-day steps that would settle it, which are worth doing whether or not a paper
follows: they are the only way to know whether the corpus half beats DEX `frequency` alone.

Also recorded: the historical panel's ~7.25M counted occurrences make zero counts
statistically empty (roadmap §5), and dataset licensing has three different answers across
the DEX dump, CulturaX and the LUMRO novels.

## 2026-08-11 — the class filters become one three-state control each

The Filtre sheet carried six checkboxes for the flag classes, and two of them did nothing.
Measured against the current `ui.db` before touching anything:

| toggle | default view | anywhere |
|---|---|---|
| `hide_loanwords` | 0 | 6 words, all `rare_in_use`; **zero** in the 17,577-word `forgotten` tier |
| `show_proper` | 0 | 2 words in the whole DB (`sirius`, `weltanschauung`), both `curiosity` |
| `hide_diminutives` | −124 | 138 relevant / 317 curiosity |
| `show_regional` | +431 | live |
| `show_variants` | +143 | live |
| `show_spellings` | +110 | live |

**Three states, not two.** `regional` / `variants` / `spellings` / `diminutives` are now one
segmented row each — `fără / cu / doar` — replacing five checkboxes. The reason is not the
extra „doar" mode so much as the polarity: an unchecked checkbox is not submitted, so a
class hidden by default *had* to be spelled `show_x=1` and one shown by default `hide_x=1`,
and the sheet ended up with three „arată X" rows and two „ascunde X" rows that looked like
one set of controls and behaved like two. A radio always submits, so all four read
identically and only the default moves (diminutives default to `cu`, the rest to `fără`).

`only` on several classes means their **union**, and a class left on `hide` is still
subtracted from it — measured: `regional=only` is 431, `regional=only&variants=show` is 440,
the nine words that are both. The flags are near-disjoint (23 rows in the relevant seam
carry two), which is what makes „doar" coherent as a mode at all.

Legacy `show_*=1` / `hide_diminutives=1` links keep working, and the mapping is in **two**
places on purpose: `build_word_filter()` for direct/API requests, and `applyUrlToForm()`
because htmx searches from *form* state on load — a server-only mapping would leave an old
shared link rendering as filtered while behaving as if it were not.

**`hide_loanwords` moved into `#dex-rare-control`**, beside `dex_max`, so it appears only on
the „rare" tab where it matches anything. Checking the result in a browser turned up that
the new `clase` section has the mirror-image problem — none of the 110 rare words carries
any of the four flags — so it is now hidden on that tab too, alongside `#seam-control`,
which was already handled this way.

Tab-gating a control takes **three** changes, and the third is the one that bites: the
section's `display`, the chip in `activeFilterChips()` (the inputs stay in the form while
the section is hidden), and the *server* ignoring the param on the wrong tab. Without the
third, switching to „rare" with „doar regionalisme" set returned 0 words — and the control
that would explain why was hidden on that tab. `seam` had that guard already; the classes
now do too.

**`proper_noun_like` stopped being a default hide.** It was one when the flag caught 447
words; narrowing it to "DEX knows this spelling *only* as a capitalised headword" — the fix
that stopped `gheb` being hidden by the surname `Gheb` — left 2 words. A default hide is
only worth its toggle if the toggle reveals something, and this one revealed nothing while
quietly subtracting two rows. The column still gates the word of the day and quiz
distractors, which is a different question from what a browsing reader may see.

Also: the two `ultima atestare` selects both read „ultima atestare: oricând" when unset and
were indistinguishable in the rail — now „ultima atestare (după)" and „(înainte)".

Verified end-to-end against `ui.db` through `build_word_filter()` and a live `search.php`:
default 2,802 unchanged, `regional=only` 431, `variants=only` 143, `spellings=only` 110,
`diminutives=only` 124, all three `show` 3,495 (the full relevant seam), an invalid mode
falling back to the default, and the rare tab 110 → 104 with `hide_loanwords=1`. Rendering and interaction checked under
Playwright rather than by eye: the four rows fit and right-align in the 288px docked rail
(labels 58–77px, segs 107px, 253px of row) and in the 390px mobile drawer, in light/paper
and dark/beton; clicking „doar" writes `?regional=only`, chips „doar regionalisme", survives
a reload, and `?show_regional=1` lands on the „cu" radio with 3,233 words.
`tests/test_rescore.py` updated where it described the default view
as including `proper_noun_like` (55 pass); `tests/test_lists_api.js` switched to the new
param name. Full suite 105 pass.

Also in this pass, and unrelated to the filters: the readme's screenshot block. The main
`public/screenshot-otzios.png` is refreshed to the current explorer, the old one is kept as
`docs/screenshots/screenshot-otzios-v0.png` (commented out in the readme, not deleted — it
is the only picture of what v0 looked like), and `joc` in both modes plus `statistici` are
now shown, since three of the five pages had no image anywhere. The prototype link moved
above the images so it is not stranded below them. The two readme paragraphs describing the
hide-flags were corrected in the same edit: `proper_noun_like` is no longer one of them.

---

## 2026-08-10 — corpus expansion: verified the two LLM reports, measured LUMRO, found a `hist_docs` defect

Turned the two reference reports (`docs/reference/260810 Grok …`, `260810 Gemini …`) into a
checked plan: `docs/corpus-expansion-plan.md`. Neither report had been validated against the
repo, and both describe the pipeline incorrectly in ways that matter.

Corrections to the reports:

- **Gemini recommends normalising to ppm for cross-corpus comparison** — the exact practice
  that classified `zapciu` extinct on 1,322 modern hits, documented as gotcha #1 in
  `CLAUDE.md` and at `validate_diachronic.py:190-211`. Its LLR suggestion is separate and good.
- **Gemini's step 1 would empty the relevant seam**: it wants `(Înv.)`/`(Arh.)`/`(Reg.)` words
  filtered out at lexicon generation. Oțios keeps them and treats `regional_only` as a UI flag;
  the relevant seam holds ~397 regional words on purpose.
- **Grok's P0 is half wrong.** `subtitle_ro` is not unwired — it is processed,
  family-aggregated, and carried into `ui.db`. What is true is narrower: it enters neither
  `verdict()` nor `score()`, and the paradigm-rolled `subtitle_occ` is dropped at the shortlist
  boundary while the surface-form `subtitle_ppm` survives into the UI.

Measured, not quoted:

- **LUMRO**: 175 novels, **7,520,713 tokens**, 111 authors, 1845–1920 (median 1898), year in
  every filename, cedilla diacritics already handled by `dump_parser.normalize`. 50.6% of the
  shortlist takes at least one hit; **1,327 words would cross the historical-attestation bar
  they currently fail**, all of them presently `absent`.
- **CoRoLa frequency lists** (Zenodo 7091535) are real and openly downloadable — 114.1 MB, 24
  lists over a balanced 1B+ token corpus, no processing required. Licence is **CC BY-NC-ND**,
  so it can feed `verdict`/`score` but no CoRoLa-derived number may be published in the UI.

**Defect found while testing the above.** In `aggregate_by_family`
(`validate_diachronic.py:376-388`) occurrences are split proportionally between claimant
lemmas but documents are all-or-nothing (`if share >= DOMINANT_SHARE`, 0.5). A lemma that
never majority-claims any of its forms accumulates occurrences and exactly zero documents,
and `verdict()`'s `hist_occ >= 3 AND hist_docs >= 2` then vetoes it. Across the shortlist:
5,780 rows (35.7%) have `hist_docs == 0`, 170 of them with `hist_occ >= 3` — `soli` (132
occ, 0.418 share), `nalt` (98, 0.223) and `văz` (96, 0.108) are all in the **relevant** seam.
Logged in `docs/BACKLOG.md`; not fixed, since it was outside the request.

Recommended order (first three need no new corpus processing): fix `hist_docs` → use
`subtitle_occ` → CoRoLa lists → LUMRO → CulturaX metadata (deferred; 40.3M documents).

**Item 1 landed the same day** — see the next entry.

---

## 2026-08-11 — `archaic_spelling`: hide obsolete spellings of living words, narrowly

The CoRoLa three-point experiment surfaced a population of shortlist entries that are not
forgotten words but obsolete *spellings* of words in daily use — `situațiune` for
`situație`, `sgomot` for `zgomot`, `advocat` for `avocat`. `variant_like` cannot see them:
it keys on a shared inflectional paradigm, and these pairs have different stems.

**A correction to the previous entry's framing.** That entry called the 5,421-word bucket
"dominated by obsolete spellings" on the strength of its top 14 by historical rank. That
sample was biased toward common words, and common words are exactly the ones whose spelling
was modernized while the word survived. Further down, the bucket is full of genuine finds —
`acaret`, `afion`, `agie`, `alișveriș`, `amploiat`, `acioaie`, `adamască`. Measured: those
5,421 words include **1,861 of the 3,022 then in the default view, 61.6%**. A flag built on
that signal would have gutted the site and hidden much of its best material.

So the shipped flag is deliberately narrow. Each rule was measured for precision (twins
found per rule firing) and only the clean ones kept:

| rule | fires | twins | kept |
|---|---:|---:|---|
| `-țiune → -ție` | 313 | 298 (95%) | yes |
| `sb/sd/sg → zb/zd/zg` | 26 | 26 (100%) | yes |
| `des`+voiced `→ dez` | 26 | 24 (92%) | yes |
| `-ziune/-siune` | 34 | 25 (74%) | yes |
| `adv → av` | 5 | 3 | yes |
| `-ea → -a` | 209 | 25 (12%) | **no** — `zaharea`→`zahara` are different words |
| `e → ă` | 2,300 | 69 (3%) | **no** — `peți`→`păți` likewise |
| `iu → i` | 1,037 | 88 (8%) | **no** — `albiu`→`albi` likewise |
| `o → u` | 1,984 | 124 (6%) | **no** — right answers buried in noise |

Every rule additionally requires a *named* twin at least 20× more frequent in CulturaX, so
two live spellings never qualify. A hide-flag's false positives are invisible — the word
simply is not there — which is why precision beats recall here, and why `proper_noun_like`
once had to be narrowed after it hid `gheb`.

Result: **291 words flagged, 110 of them in the default view** (2,912 → 2,802). All 47
non-`-iune` hits were audited by hand — `desbate`→`dezbate`, `sgomot`→`zgomot`,
`advocat`→`avocat` — with no visible false positives; several DEX definitions print the
modern form themselves.

`spelling_of` stores the twin and the detail panel names it ("Grafie veche pentru
*situație*") rather than dropping the row silently, so the flag informs instead of just
subtracting. UI wiring follows the existing contract: a `show_spellings` toggle (`show_*`,
never `hide_*`, since an unchecked box submits nothing), registered in `AF_SPECS` and in
**both** URL arrays in `app.js` — the writer is the half that fails silently. `.fp-spelling`
is tokens-only, so every skin inherits it with no component rule.

Verified end to end on a clean `php -S`: `situațiune` absent by default, present with
`show_spellings=1`, and the panel note rendering only for flagged words. The long-running
dev server on :8000 was serving stale PHP throughout and needs a restart. Python suite 105
passes; the three JS API suites pass against a live server; `test_store_sync` still fails on
the pre-existing bug already logged in the backlog.

Still open, and needing something other than suffix rules: the irregular vowel
correspondences — `strein`/`străin`, `țeară`/`țară`, `poroncă`/`poruncă`, `biurou`/`birou`.

---

## 2026-08-11 — CoRoLa: the lemma problem solved, the corpus still not usable as "modern"

Set out to reconcile CoRoLa's TTL lemmas to DEX's. The reconciliation turned out not to
need an algorithm, and the corpus turned out to be blocked by something else entirely.

**The lemma fix was the other input file.** The archive also ships surface-form lists
(`corola_word_freq_*`). Those match `corpus_word_frequency`'s per-surface-form invariant,
so the existing `aggregate_by_family` does the rollup with DEX's paradigms and DEX's
prominence split — and `strugur`/`strugure` genuinely share `struguri`, `strugurii`,
`strugurilor`, which is exactly the `veșcă`/`veste` case that machinery was built for.

| pair | TTL lemma list | our rollup |
|---|---:|---:|
| `strugur` / `strugure` | **12,176** / 724 | 749 / **12,034** |
| `gherghină` / `gheorghină` | **3,658** / 2 | 63 / **98** |
| `cadră` / `cadru` | 51,181 / 73,660 | **103** / 119,496 |

`process_corola.py` now loads the word list (1,813,746 forms, 637.8M tokens) into
`corpus_word_frequency` and drops the superseded `corola_lemma_frequency` table, so nobody
finds a plausible-looking source of TTL lemmas to join against.

**Then it was wired into the modern panel for one build, and reverted.** The blocker is
neither the lemmatization nor the legal skew: **CoRoLa spans 1945 to the present**, so it
is a reference corpus of the last eighty years, not a picture of current usage. Per token
against CulturaX: `condițiune` 112.8×, `comisiune` 49.6×, `dorobanț` 41.1×, `poemă` 23.3×,
`iscăli` 15.7×, `dijmă` 8.3×. The first two are pre-1953-reform spellings — a corpus
starting in 1945 necessarily carries them.

The build effect was 686 words off the shortlist and **35 out of the `relevant` seam**,
including `birjă`, `dorobanț`, `vechil`, `dijmă`, `cocoană` and `iscăli` — the project's
best material disappearing from the default view because it appears in mid-century
literature. The drops were real register signal rather than arithmetic (median CoRoLa
contribution 37.7% against 3.8% panel growth; the biggest gainers were legal-style deverbal
nouns — `rămânere`, `ajungere`, `discutare`, `analizare`), but "alive in eighty years of
published Romanian" is a different claim from "alive now". Using CoRoLa needs a third panel
with its own meaning, not a term added to the modern one; the lists carry no dates, so no
post-2000 slice is available.

**One real bug fixed along the way, and kept.** `MODERN_RARE_OCC`/`MODERN_ALIVE_OCC` are
absolute counts calibrated against CulturaX at one size, and nothing rescaled them when the
panel grew — so adding any modern corpus made every word look more alive and pushed
everything within the growth margin over a threshold. `scaled_modern_thresholds()` rescales
both bars by actual panel size against `CALIBRATION_MODERN_TOKENS`. This is latent for any
future modern corpus, so it stays even though CoRoLa was reverted. It also broke
`test_no_alive_word_is_labelled_forgotten`, which was pinned to the bare constant; that test
now derives the floor the way the pipeline does.

A correction to my own reading during this pass: I first called the drop cluster at
`modern_occ` 1991–1998 evidence of calibration drift. It was an artifact of sorting the
dropped words by `modern_occ` descending — the shortlist excludes anything above the alive
floor, so the top of that sort necessarily sits just under it. The distribution is normal
(1–3 words per value). The rescaling is still correct on its own merits.

Suite 103 → 105, adding a guard that the thresholds scale and that CoRoLa is in neither
panel. Pipeline output is byte-for-byte back to the pre-CoRoLa state: shortlist 17,577,
seams relevant 3,495 / curiosity 14,082, `ui.db` 17,687 words. `data/word_ids.tsv` gained 23
ids from the experimental build and keeps them — ids are never withdrawn, so words that
briefly appeared stay resolvable.

---

## 2026-08-10 — corpus panel: LUMRO ingested and wired in; CoRoLa loaded and deliberately not

Two new corpus processors, one of which is now driving verdicts and one of which is not.

**`process_lumro.py` — 175 dated Romanian novels, wired into the historical panel.**
5,072,239 tokens by the pipeline's own tokenizer (an earlier estimate of 7.52M came from a
looser throwaway regex; 36.1% of tokens match a DEX form against Wikisource's 37.9%, which
is the check that the two panels are counted the same way). 111 authors, 1845–1920, year in
every filename, cedilla diacritics already handled by the shared normalizer.

`HIST_CORPORA` is now `wikisource_ro` + `lumro_ro`. Each corpus is aggregated on its own and
the results merged by a new `merge_panels()`, **not** merged as raw surface counts and
aggregated once: documents are summed across corpora because a Wikisource page and a novel
are different documents, but stay a max within a corpus. Merging first would push both
through a single max and silently drop the documents only the smaller corpus contributes.

Rebuild:

- **381 words crossed the historical-attestation bar**, all previously `absent`
- **509 words promoted `curiosity` → `relevant`, none demoted**
- shortlist 16,557 → 17,594; words with zero historical occurrences 5,209 → 4,887
- seams now relevant 3,608 / curiosity 14,096; `ui.db` 17,704 words
- `data/word_ids.tsv`: **464 added, 0 deleted**, first 26,479 lines byte-identical

The earlier prediction was 1,327, not 381. Both numbers are right: the prediction was made
against the pre-`hist_docs`-fix shortlist, and that fix had already rescued most of the same
words. Two fixes aimed at one population do not add.

**LUMRO's document unit is the author, not the novel.** Added after the first ingest, on a
measurement: `hist_docs >= 2` is a claim about *independence*, and of the 1,425 shortlist
words whose attestation LUMRO supplies, **638 (44.8%) came from a single author** —
`jupâneșică` at 47 occurrences, every one V.A. Urechia; `campament` 19, all
N. Radulescu-Niger. Several were in the `relevant` seam. So `document_count` is now distinct
authors (of 111) rather than novels (of 175); occurrences still sum over every novel, so
only the independence claim changes. Wikisource keeps counting pages — it has no author
metadata, and the stricter unit belongs where it is knowable.

**The measured effect is small and that is worth recording**: only 315 words appear in more
than one novel by the same author, so only those can move. The rescore gave 10 verdict
changes (all `historical_only` → `absent`), 3 words out of the relevant seam, 17 off the
shortlist; `data/word_ids.tsv` unchanged. The principle is the point — it stops one
novelist's idiolect reading as circulation, a failure mode that grows with any further
single-author-heavy corpus.

The counting loop was extracted to `count_novels()` and pinned by a new
`tests/test_process_lumro.py` (6 tests), because "just count novels" is the obvious
simplification and nothing else in the tree would catch it. Suite now 103.

Final figures after this pass: shortlist 17,577; seams relevant 3,495 / curiosity 14,082;
`ui.db` 17,687 words.

**`process_corola.py` — 1,457,518 lemmas, 665.9M tokens, loaded and connected to nothing.**
Licence settled with the owner: non-commercial, nothing redistributed, so CC BY-NC-ND allows
it as an input; no CoRoLa-derived number goes into `ui.db`, and the script says so on every
run. It lives in its own table `corola_lemma_frequency` because its counts are per-lemma,
the opposite of `corpus_word_frequency`'s per-surface-form invariant.

81.3% of shortlist words get a CoRoLa count, and it still cannot be used yet:

1. **TTL's lemma inventory is not DEX's**, and its chosen headword is often the form we hold
   as the archaic variant — `strugur` 12,176 vs `strugure` 724, `gherghină` 3,658 vs
   `gheorghină` 2, `republicat` 107,074. A string join hands the modern word's whole count
   to its obsolete spelling, marking exactly the words this project hunts as alive. The
   1,333 words that look "extinct in CulturaX but ≥50 in CoRoLa" are mostly this artefact.
2. **The distributed list is legal-skewed**, not the balanced corpus advertised: vs CulturaX,
   `alin` ~5M×, `anexă` 178×, `prevedere` 175×, `articol` 18× (0.4% of all tokens), while
   everyday vocabulary sits at 0.2–3×.

Fixing it means reconciling lemmas through `inflected_forms.db` and treating the legal
register as `specialist_alive` — both worth doing, neither a chore.

**Found in passing: `modelType 'V'` is missing from the corpus lookup allow-list.**
`load_dex_words()` allows `'VT'` and `'VI'` but not plain `'V'`, so 3,184 verbs with no
description are counted by no corpus at all — `râde`, at DEX frequency 0.99, is absent from
the `culturax_ro` table entirely. Measured shortlist impact is one word (`țepeni`), so it is
logged rather than fixed. The allow-list is also inconsistent with itself: `'T'` is excluded
as an inflected form while `'IL'`, equally inflected, is included.

---

## 2026-08-10 — dexonline host lock for `scrape_definitions.py`; `subtitle_ro` found unusable as a modern-usage signal

Two backlog items, one shipped and one deliberately not.

**`scrape_definitions.py` now takes the host lock.** `acquire_host_lock()` and the `LockHeld`
branch, guarded on `not args.dry_run` (`--merge-only` returns before it), on the same
`data/.dexonline.lock` path `scrape_synonyms.py` uses. Verified cross-script rather than in
isolation: with the synonyms scraper holding the lock, a live definitions run exits 1 and
names the holder, while `--dry-run` still prints its queue and makes no requests. Duplicated
rather than imported, per the two-callers convention — **the lock path is the contract**, and
a drift there makes the two stop interlocking silently. This mattered now because two scrapes
are queued behind it (746 missing definitions, ~14.2k synonyms).

**`subtitle_ro` will not be wired into the verdict, and the earlier recommendation to do so
is withdrawn.** `process_subtitles.py` describes it as 966 Digi24 news clips; comparing
per-token rates against CulturaX shows the most over-represented words are folk-song
vocabulary, not news — `lai` 332×, `mândruliță` 242×, `neicuță` 122×, `țurai` 119×.
Reconstructing the source clips from the dump's `Subtitle` table (`clipId` is retained) makes
it unambiguous: all seven sampled clips are folklore programming — "festivalul Național de
folclor Constantin Arvinte", "regina muzicii populare Irina Loghin", "festivalul de muzică
populară Ciocârlia" — and two are transcribed lyrics rather than speech, one with visible ASR
damage.

Sized by clip, using genre-naming words as the marker:

- clips with ≥ 3 markers: **15.6% of tokens but 27.5% of all shortlist-word occurrences** (1.76×)
- clips with ≥ 5 markers: 9.0% of tokens, 21.4% of occurrences (2.37×)
- **444 of the 2,446 shortlist words it attests appear *only* in folk clips** — for those,
  "attested in modern broadcast" means "sung in a traditional song on television"

So scoring subtitle presence as evidence of modern life would have rescued precisely the
words the project exists to find. Nothing reads `subtitle_ppm` today (no PHP, no JS), so
there is no live harm — the plumbing defects are real but fixing them on a signal that must
not be used is churn. Two honest routes recorded instead, both decisions rather than chores:
filter the folk clips by `clipId` and re-run for ~11M tokens of actual news, or invert the
signal into a traditional-song register flag alongside `regional_only`.

Also ticked a stale backlog entry: "also advance on fav / lol" was already delivered in
`eb11974` (`store.js:161` / `:187`) — an unticked child under a ticked parent saying the same
thing. Added the `subtitle_ro` finding to the `CLAUDE.md` gotchas.

---

## 2026-08-10 — fix: share-scaled document counts in `aggregate_by_family`, and rescore

Documents in `aggregate_by_family` are now scaled by the same share that splits a form's
occurrences (`d * share`), still combined with `max` across a lemma's forms rather than a
sum. `DOMINANT_SHARE` is gone. The old rule credited a form's documents only to a claimant
winning ≥ 50% of it, so a lemma that never majority-claims any of its forms accumulated
occurrences and exactly zero documents — and `verdict()`'s `hist_occ >= 3 AND hist_docs >= 2`
then let the docs half veto the occ half.

Two regression tests added to `tests/test_rescore.py`: a non-dominant claimant must still be
credited documents, and the document share must track the occurrence share. The existing
`test_aggregate_documents_never_exceed_the_largest_contributing_form` uses unambiguous forms
(share 1.0) and is unaffected. Full suite: 97 passed.

Rescore (`validate_diachronic.py` → `make_shortlist.py` → `tools/build_ui_db.py`):

- **`hist_docs == 0 AND hist_occ >= 3`: 170 → 0.** The false-`absent` population is gone.
- 189 verdict changes, 185 of them `absent` → `historical_only`; 2 `absent` → `extinct`.
- 77 words promoted `curiosity` → `relevant`, 2 demoted.
- Shortlist 16,203 → 16,557 rows (375 new, 21 dropped); `ui.db` 16,667 words.
- Seams now relevant 3,015 / curiosity 13,652; default view 2,381.
- `văz` 0 → 42 documents (392 × 0.108), `soli` → 62, `nalt` → 67 — all three `absent` →
  `historical_only`, all three in the relevant seam.

Two words moved the other way: `arestui` and `barbetă`, both `hist_occ` 3 with documents
2 → 1. They sat exactly on the noise floor, and proportional attribution cuts both ways.
Correct behaviour rather than a new defect.

**`data/word_ids.tsv`: 141 added, 0 deleted.** The first 26,338 lines are byte-identical to
the pre-rescore file, so no id was renumbered or removed and every `?w=` link ever shared
still resolves. A second `build_ui_db.py` run produced a byte-identical file, so the
idempotency invariant holds too.

Stale figures in `CLAUDE.md` refreshed against the new build (seam sizes, regional/variant
counts in the relevant seam, `newest_dict_year` coverage, the pre-1970 and 2005+ slices,
the diminutive count), and the share-scaling rule added to the gotchas so it is not
"simplified" back into an all-or-nothing threshold.

---

## 2026-08-10 — soft-launch UI pass: dexonline chip, desktop nav, mobile sheet, auto-advance

Five items off `docs/BACKLOG.md` → **Soft-launch**. Verified in headless Chrome over CDP at
390×844 and 1440×900 (`--headless=new` with `Emulation.setDeviceMetricsOverride`; the old
`--headless` screenshot mode reports desktop layout at a mobile window size and produced one
false overflow report before I switched).

**`dexonline ↗` is a chip, not a button.** It moved from a full-width filled block at the
foot of the detail panel into the end of the dictionary row (`.fp-dicts`), shaped off
`.dict-chip`. The reason it needed a shape change rather than a colour change: **all four
skins had independently made it louder** — beton a red accent slab with a drop shadow, govuk
the green GDS action button, registru a black mono-caps rectangle, tezaur a filled pill — so
the loudest element in the panel, ahead of the headword, was a link off the site. A big
filled button invites being styled as a primary action. Each skin now adds at most a colour;
`registru` re-grounds to the attestation border because its `--accent` is the page's own ink,
which says nothing on a chip among chips. `.fp-dicts` now renders even without `sources`,
since wrapping it in that condition would drop the link for exactly the words with the
thinnest dictionary coverage. Contrast measured at ≥4.5:1 across 5 skins × 2 themes (worst
4.52, govuk/dark).

**`statistici` + `metodologie` in the top nav, desktop only.** Both partials render them and
app.css shows exactly one — header from 901px up, footer below — via `top-nav-item--wide` /
`nav-item--wide`. No width shows them twice or not at all. This does not undo the 260809
header/footer split: a phone bar still cannot take four labelled entries, which is the
measurement that split was built on. What changed is that on a desktop the bar has the room,
and the two pages that explain the project were buried under the display toggles. 901px is
the footer nav's existing label/icon breakpoint, reused so there is one crossover to keep in
step rather than two that can drift. All four entries measured ≥5.27:1 on the bar in every
skin (govuk and registru force it black; their existing `.brand-bar .top-nav-item` rules
cover the new entries for free).

*Caught in verification, not in writing:* `.top-nav-item--wide { display: none }` declared
**before** `.top-nav-item { display: inline-flex }` loses on source order — both are one
class — and all four entries rendered on a phone. Moved below it.

**Mobile: an open definition hides both bars.** `body.detail-open`, set in `app.js` on panel
open and cleared in `closePanel()`; only the ≤768px block acts on it, so a desktop window
narrowed with the panel up lands right without a resize listener. The backlog asked for the
sheet capped at 40% instead — it stays 60vh, because 40% of a phone does not hold a
definition (`poporanism` alone overflows it) and the definition is what you opened. The room
comes from the bars: ~186px of an 812px screen, neither actionable while reading. **Visible
list 139px → 325px**, sheet keeps its height. `.fp-close` becomes a 44px back arrow in the
top-left — with the header gone it is the only exit. Two glyphs in the markup with CSS
showing one, rather than a `content` swap assistive tech cannot see.

`joc.php` was the page actually short of room: a 121px header, because `corecte: 0 · ratate:
0` is 158px of a 362px bar and pushed the trophy to a third row. Below 768px the tally reads
`✓ 0 · ✗ 0` → **87px**. Card padding 28px → 16px takes the line length from 285px to ~325px
on a 375px phone, for a card whose whole job is four definitions you read and compare.

**Auto-advance on every mark** — fav, lol, meh and ascunde alike. Marking is a triage loop,
and a loop where three keys move you on and one does not is a loop you have to think about;
one mark per word is the intended interaction, so the ability to stack a second on the same
word is not worth four controls that behave differently. (Built first as `meh`/`ascunde`
only, precisely to keep fav+lol stackable — changed the same day on the owner's call:
convenience and consistency win over the rare double-tag.)

**Only applying a mark advances; removing one does not.** Un-favouriting is a correction, and
advancing would take you off the word you just came back to fix. Verified: fav on a word
moves to the next, returning to it and clicking again un-favs in place.

`removesRow` is the sole difference between the two cases — `meh`/`ascunde` also pop the row
out of the grid. `advanceAfterMark()` resolves the next row *before* the fade and re-finds it
by element afterwards; resolving after would race the animation, and selecting by index
before would leave `selectedIdx` off by one the moment the row is removed — the number `j`/`k`
read. On the last row: fall back to the previous one when the row is being removed, and stay
put when it is not, rather than wrapping to the top and silently restarting the list. Custom
tags typed into `#tag-input` do not advance — that would pull focus out of the field.

**Two smaller things.** `marks` now reads `nemarcate` / `marcate` (the old label also
misspelled `annotate`); values stay `unmarked`/`marked`, which are URL state. And `marks` was
in both URL arrays but missing from `AF_SPECS`, so it filtered the grid without ever showing
a chip — the same one-directional registration gap the CLAUDE.md filter rule names, on the
chip side. Added.

**Already done, ticked not built:** "mobile, search input is always shown" — the magnifier
work had already fixed it. Measured at 390×844, `#search` is `display:none` on load and the
brand bar is a single 51px row. The backlog screenshot predates it or had an active query.

**Deferred with the reasoning recorded in the backlog**, so they don't read as omissions:
publishing top faves + demoting `meh` globally (221 annotations from 44 users, 106 of them
one person's, 41 `meh` total — one person's taste silently reshaping everyone's default,
against the visible-toggle rule, and gameable for the price of a cookie clear); the synonym
count filter (2,066 of 16,315 scraped, zero in `curiosity` — decided it ships excluding
unscraped words rather than counting them as 0); and "another data quality run", folded into
the existing 260519 Data Audit section.

*Pre-existing, untouched:* `tests/test_store_sync.js` fails at "sync watermark stored" and
then throws on the next step. Confirmed against the committed `store.js` — not from this
pass. `test_lists_api`, `test_game_api` and `test_moderation` all pass.

## 2026-08-09 — diminutive filter, playlists ignore filters, the two frequencies explained

**`ascunde diminutive`.** New `words.diminutive_like` (403 words, 96 of them in the default
view), computed by `mark_diminutives()` in `tools/build_ui_db.py` and back-filled into an
existing `ui.db` by `tools/migrate_ui_db_diminutives.py`. Two signals, unioned:

- **DEX says so** (345) — the definition opens with *Diminutiv al lui X*, matched at the
  start of a meaning and allowing one short parenthetical, so `(Ca termen de adresare)
  Diminutiv al lui văr` counts. Requiring the *al/a/ale/lui/de la* is what keeps out
  `alintare`, whose definition merely quotes a sentence about another word being a
  diminutive. This is also the only signal that survives an alternation the spelling
  hides: `vătășel` → `vătaf`, `cărucioară` → `căruță`.
- **Unambiguous suffix + a base DEX knows** (58 more) — `-uleț -uliță -ișor -ișoară
  -cioară -uț -uță -șor -șoară`, and only when the stripped stem is a real lexeme
  (`noruleț` → `nor`). Measured before choosing the set: adding `-iță -ic -ică -el -ea
  -aș` took it to ~740 but dragged in `păstoriță`, `boieriță`, `semitic`, `mastică`,
  `livrea`, `birtaș` — the wrong trade for a control people switch on to *stop* seeing
  things. `-iță` alone is ~90 words and would need the base's gender to disambiguate.

Filter is `hide_diminutives=1`, off by default — a `hide_` rather than the `show_` form
`CLAUDE.md` argues for, and correctly so: it only ever subtracts, so "unchecked submits
nothing" is exactly the state it should mean, same as `hide_loanwords`. Registered in all
three places a filter needs (`AF_SPECS`, both URL arrays).

**A playlist is no longer filtered again.** Opening a shared list in the explorer ran it
through the default filters, which hide the whole `curiosity` seam plus regionalisms, old
variants and proper nouns — so a shared list of twenty words could arrive showing eleven,
with nothing on the page saying why. `search.php`, `random.php` and `feed.php` now skip
`build_word_filter()` entirely when `w=`/`words=` is present (new `playlist_words()` /
`playlist_condition()` in `_lib.php`); `q` and `marks` still apply, since those are things
the reader just typed rather than defaults they never chose. Client half: `setPlaylistMode()`
marks the form `data-playlist`, sets `inert` on every section but sort, shows the reason in
the sheet, and stops the chip bar claiming filters are live. `inert`, not `disabled`, so the
values survive and exiting the playlist hands back the view you had. New case in
`tests/test_lists_api.js` packs a `curiosity` word with a visible one and asserts both
survive an explicit `seam=relevant`.

**Metodologie: the two frequencies.** New `#frecvente` subsection in 05 — a comparison
table (source, what it measures, scale, what 0 means), then the DEX half (prominence, not
usage; the superscript is the same score ×100) and the Zipf half (wordfreq, `log10` per
billion, the figure-skating aggregation, the value table). The point worth keeping:
**16,178 of 16,203 shortlist words sit at Zipf 0**, because Romanian only has wordfreq's
small list and its reliability floor is Zipf 3. The Zipf filter therefore doesn't grade
forgottenness — it catches the handful of words that were never rare (`ridicată` 4.62,
`jumătăți` 3.70, `brânzeturi` 3.47), mostly inflected forms that slipped in as lemmas.

Two labels stating the opposite of that were fixed on the way past: the shortcuts legend
said the DEX number meant "cu cât e mai mic, cu atât e mai rar", and the detail panel's
Zipf tooltip said "sub 3,0 înseamnă ieșit din uz" (it means below wordfreq's floor). The
legend now links to `#frecvente`. Also normalized 49 lines of cedilla `ş/ţ` in
`metodologie.html` to the comma forms the rest of the page and the pipeline use.

---

## 2026-08-09 — `attested_after`, the other half of the last-attestation filter

`attested_before=<year>` (last attestation older than Y) existed; its counterpart didn't,
so there was no way to isolate the *other* end of `curiosity` — words that faded relatively
recently rather than centuries ago. Added `attested_after=<year>` (`newest_dict_year >= ?`,
vs. `attested_before`'s `< ?`, so the two never overlap at a shared boundary year and
compose into a band when both are set). New select in `index.php` beside the existing one,
`_lib.php`'s `build_word_filter()` gets the mirrored condition, and `app.js` gets the third
registration every filter needs: `AF_SPECS` (chip reads `atestat ≥1990`), the
`applyUrlToForm` read list, and the `syncUrlFromForm` write list.

Sanity-checked against the live `curiosity` seam rather than trusting the SQL by eye:
12,046 total, 11,368 at `attested_after=2005` (most of the seam is unremarkable-recent, as
expected), 206 at `attested_before=1970` (close to `CLAUDE.md`'s already-documented 225),
118 in the `1990–2005` band — strictly narrower than either bound alone, confirming the two
conditions actually AND together rather than one silently overriding the other.

---

## 2026-08-09 — joc/liste to top nav, footer decluttered, word-cloud contrast + layout fixes

Follow-up to the previous session's header/footer reshuffle, from screenshot feedback.

**Top nav.** `joc` and `liste` moved out of `footer.php`'s nav loop into a new `.top-nav`
in `header.php`, right after the brand mark — reachable in one click from every page instead
of a scroll to the bottom bar. `index.php`'s `?` shortcuts/legend link followed them up
(`$header_nav_extra`, index-only — the shortcuts modal doesn't exist on the other four
pages). `header.php` now needs `$page` too, so every caller sets it before that require
rather than only before `footer.php`'s. `footer.php`'s loop is
`array_diff_key(NAV_ITEMS, array_flip(['index','joc','liste']))`: `cuvinte` is dropped
outright rather than moved, since the brand mark already links home on every page.

**Feed hidden.** The 📇 feed button in `index.php`'s footer got a `hidden` attribute,
matching the dormant 🎲 `surpriseWord()` button beside it — the feature and its markup stay,
it just has no bar to live in right now. Unlike 🎲 it has no keyboard shortcut, so it is
genuinely unreachable until it gets a new home; noted in `CLAUDE.md` rather than silently
left.

**Two skins needed the on-bar treatment again.** `govuk` and `registru` force `.brand-bar`
black in both themes; `.top-nav-item`, `.shortcuts-link` and `kbd` all rendered low-contrast
or invisible there until given the same `--gv-on-bar`/`--rg-on-bar` re-grounding as
`.search-toggle-btn` got last session. Exactly the same category of bug, same fix shape —
now called out as a standing rule in `CLAUDE.md` rather than something to rediscover a third
time.

**Word cloud: three related bugs from one root cause, plus one unrelated one.**

- `#word-list` is a CSS grid (`auto-fill, minmax(var(--word-col), 1fr)`), and a grid item
  stretches to fill its track by default. `.word-row` never opted out, so the hover/selected
  background and the `.ann-overlay` annotation emoji (`position: absolute; right: 2px`,
  anchored to the row's own box) both extended to the *column's* edge instead of the word's —
  a black bar spanning the full card width, and a 🙈/😂/📝 emoji stranded far from the word
  it annotates. One `justify-self: start` on `.word-row` fixed both: the row now hugs its
  content (word + freq superscript), so the background and the overlay's anchor point both
  shrink to match. Confirmed harmless in table view, where `#word-list.word-list-table` is
  `display: block` (not a grid), so `.word-row` is not a grid item there at all and this rule
  has no effect — table rows keep their explicit `width: 100%`.
- Separately: a selected word's text stayed in its verdict colour instead of switching to
  `var(--bg)`, i.e. dark-on-dark whenever that verdict colour was tuned dark (Beton, GOV.UK —
  both pick dark verdict colours for contrast against their *light* page ground). Root cause
  was a CSS specificity bug the code already carried a comment claiming didn't exist:
  `#word-list .word-row[data-selected] .word-text` is (1,3,0), but
  `#word-list:not(.word-list-table) .word-row.verdict-X .word-text` is (1,4,0) — the verdict
  rule is more specific and silently won regardless of source order, despite the old comment
  asserting the opposite. Fixed with `!important` rather than another round of specificity
  arithmetic, since "selected always wins over verdict colour" has no exception to design
  around.

Verified via headless Chromium (`playwright`, still no Chrome-extension session) across all
five pages, the word-cloud selected state in paper/brutal/govuk × light/dark, and the emoji
overlay by writing a tagged word straight into `localStorage`'s research store and
re-running `hydrateRows()`.

---

## 2026-08-08 — Dict-name tooltip, collapsible search, header controls move to footer

Four UI changes, all in the shared partials so they apply everywhere at once.

**Synonyms live.** The `--seam relevant` scrape finished (2,292 rows merged into
`data/processed/synonyms.db` at 12:16), but `public/data/ui.db` was still the 02:28
build. Reran `tools/build_ui_db.py` — 2,075 words now carry `synonyms`/`antonyms`.
`data/word_ids.tsv` diff is empty (no new words), so the append-only invariant holds
trivially.

**Dictionary names collapse into a click tooltip.** `.fp-dicts` in `detail.php` used to
print one `.dict-chip` per source inline — a word in 18 dictionaries meant 18 chips in
the panel body. The "📚 în N dicționare" label is now a `<button class="fp-dicts-toggle">`
and the chips live in a `.dict-tooltip`, `hidden` by default. Handled in `store.js`
(delegated on `document.body`, same pattern as the bookmark/tag buttons) rather than
`app.js`, because `detail.php` renders on both `index.php` (htmx swap) and `joc.php`
(plain fetch), and only `store.js` loads on both — `app.js` is index-only.

One real bug found via a headless-Playwright check (no Chrome-extension session this
session, so `playwright` stood in for the browser tool): `.fp-dicts` sits inside
`.fp-body`, which scrolls, and an `absolute`-positioned popover is clipped by its
scrolling ancestor's overflow instead of floating above it — the tooltip rendered as a
1px sliver. Fixed by switching to `position: fixed` and computing `top`/`left` in JS from
the toggle's own `getBoundingClientRect()`, clamped so it can't run past the right edge.
A capturing `scroll` listener on `document` closes it, since `.fp-body`'s scroll doesn't
bubble.

**Search collapses behind a magnifier.** `#search` in `index.php` was always-visible,
`flex:1`, up to 360px wide. Now wrapped in `.search-wrap` with a `.search-toggle-btn`
(magnifier SVG) in front of it; the input is `display:none` until `.search-wrap` gets
`.is-open` (click, the `/` shortcut, or already-open on load if the URL carried `q` —
`applyUrlToForm()` still fills the value first). `onblur` collapses it back if empty, and
the filter-form's `reset` handler does the same.

**Scale/skin/theme moved from the brand bar to the footer.** They were pasted into
`header.php`'s `.brand-right` on all five pages; now they render in `footer.php`'s
`.status-right`, once, using the `--sm` control variants that were already sized for it.
`index.php`'s feed button and cloud/table view toggle followed them into a new
`$footer_tools` slot (index-only — `header.php` keeps only the spinner and result count).
Freed up enough header width that the collapsed search icon has room to sit next to the
brand mark on a 375px phone, which it didn't before.

This nearly doubled what the footer carries, and the fixed-position mobile status bar
doesn't grow with its content — it clips. Swept widths 320–768px with a headless-browser
height probe (temporarily forcing `#status-bar{position:static;height:auto}` and reading
`getBoundingClientRect()`) and found two bands where the wrapped content (69px at
500–700px, 86px at 320–440px) exceeded the existing `--statusbar-h` (44px / 62px): the nav
row was rendering 5–14px below the viewport, unreachable. Added a `≤710px` tier
(`--statusbar-h: 76px`) and raised the existing `≤480px` tier from 62px to 96px — sized
for the worse of the two sub-cases in that range (86px, three lines) rather than adding a
fourth breakpoint for the 445–480px band that measures better (61px) but few real phones
land in.

**Two skins needed a follow-up patch.** `govuk.css` and `registru.css` force their
`.brand-bar` to black in both themes and had component rules re-grounding every control
that used to live there (`.view-toggle`, `.theme-toggle`, `.scale-stepper`, `.play-btn`,
`.skin-select`) against `--gv-on-bar`/`--rg-on-bar` instead of the page-ground tokens that
would vanish on black. Moving those controls to the footer — a page-ground surface in both
skins, not a forced-black masthead — left that re-grounding dead code, harmlessly (verified
both skins' footers in light and dark: default app.css styling already reads fine there).
But the new `.search-toggle-btn` stayed behind in `.brand-bar`, unstyled by either skin, and
rendered as a barely-visible white square on black. Removed the dead selectors and added
`.search-toggle-btn` to the surviving on-bar rule (alongside `.filter-toggle-btn`, the only
other control still in the bar) in both files — this is the exact "component rules break if
the markup moves" risk `CLAUDE.md`'s skins section already names, just encountered rather
than theoretical this time.

Verified in a headless Chromium via `playwright` (no Chrome-extension session available)
across index/joc/liste/stats at desktop, 700px, and 390px widths, the dict-tooltip on both
`index.php` and `joc.php`, and all six skins' header/footer in both themes.

## 2026-08-08 — Filtre rail goes type-only in every skin

app.css stripped the fill off `.fs-pill` a while back — text over nothing, with weight and
an underline for checked — and every skin had since put one back on its own: `brutal`
inverted both the pills and the section labels into ink blocks, `tezaur` filled checked
pills with the accent, `govuk` with `--surface`, and `registru` turned `.fs-label` into
filled §-tags. Reported as "too loud", correctly.

All four are now type only, in both themes. The checkbox-inversion rules that `brutal` and
`tezaur` carried (white tick on the pill's own dark fill) went with them, since app.css's
plain `--text`-filled tick works once there is no coloured ground to invert off of.

The reason this kept happening is worth keeping: **most of these pills are checked when
you arrive**, so a fill on a checked pill is not a highlight, it is the rail's background.
Each skin looked fine while being written alone. Written up as a rule in `CLAUDE.md` under
the skins section.

`.seg-opt` was deliberately left alone — it is a segmented control with no tick and no
swatch, so its inverted block is the only mark saying which option is live, and it is
app.css's own treatment rather than anything a skin added.

---

## 2026-08-08 — "Registru" skin, after patronview.com

New skin at `public/assets/skins/registru.css` (~620 lines), built from the design system
in `docs/reference/design-systems/context.dev patronview.com-design.md`. (The
`design-extractor.com` file beside it documents a Cloudflare interstitial the extractor
hit instead of the site; its dark palette is still the only documented one PatronView has,
so the dark block is built from that.)

The adaptation, in short: black masthead, IBM Plex Mono for anything that names or labels,
Public Sans for prose, zero radius, zero shadow, and one saturated blue reserved for the
active-filter chips. `--serif` points at Plex Mono, so headwords, panel titles and the
game's prompt read as records in an index; rule 8 of the file sends definitions and other
running prose back to the sans.

Substitutions, all forced and all noted in the file: Libre Franklin → Public Sans (a fork
of it, and already loaded — skins cannot add a `<link>`); no weight 700 anywhere, because
the pages load Plex Mono at 400/500/600 only; `--surface` is a whisper-grey rather than
the reference's pure white, because hover, the rail and the status bar are all painted
with it and white-on-white erases every one.

Two findings folded back into `CLAUDE.md`:

- `--word-col` was measured against Source Serif 4 and has to move with the display font —
  Plex Mono is ~25% wider per character.
- `.joc-mode.active` fills itself with `--accent`, which under this skin is black; on the
  black masthead the selected game mode vanished. Anything in the bar that fills with
  `--accent` needs re-grounding, the same list `govuk` already re-grounds.

`stats.php`'s two hardcoded chart hexes (indigo POS, emerald domain) are patched to ink in
the skin file, and the existing backlog entry now records that a second skin has needed
the workaround.

---

## 2026-08-08 — Verdict dots retired, Filtre pills go minimal

Two skin-system changes across all five skins (paper, brutal, govuk, tezaur, velin),
prompted by a screenshot of Beton's Filtre panel: a wall of solid-black checkbox bars and
bordered pills, "too loud."

**Verdict dots.** Every skin now hides the per-word `.verdict-dot` in the cloud view and
paints the headword itself instead — previously only brutal did this ("deliberately
skin-scoped: paper keeps its dots, so the two can be compared"). Moved the component rule
into `app.css` unscoped, keyed off `var(--v-*-word, var(--v-*-tx))`: skins that define
their own `-word` ramp (brutal, tezaur) keep it verbatim; skins that don't (paper, govuk,
velin) fall back to the existing badge-text ramp, which turned out to already clear real
contrast on a plain ground (6.5–14:1 measured across all three). Brutal's own `-word`
tokens stay — its badge is a solid fill with white/black `-tx`, meaningless reused as
running text, which is why that ramp was hand-tuned in the first place. Also matched the
inv/bookmarked underline colour to `currentColor` in cloud view everywhere (previously
brutal-only), since a fixed `--v-ext` red underline reads as a second, contradictory
verdict once the word itself carries a colour. Table view is untouched — it already states
the verdict in the IST/EXT badge.

**Filtre pills.** `.fs-pill` (VERDICT/NIVEL/CATEGORIE/explore toggles) lost its default
border and background in `app.css` — text over nothing until checked, dimmed to
`--text-3`. Checked state diverges by skin: paper/velin/brutal get an underline (no
fill — a solid ink block per pill, all checked by default in NIVEL/CATEGORIE, was
literally the wall of boxes this was fixing); govuk gets a flat `govuk-tag`-style grey
fill instead of underlining a non-link; tezaur keeps its existing accent-coloured fill,
already the right shape for "background only when selected." `.fs-check` stopped
inverting off the pill's own background (which no longer exists) and now fills straight
in `--text`/`--bg`, independent of skin. Brutal's and govuk's now-redundant per-skin
copies of the dot-hiding/word-colouring rules were deleted rather than left duplicated.

Verified headless via Playwright (no interactive browser session available) — computed
`.verdict-dot` display, `.word-text` color per verdict class with contrast ratios, and
`.fs-pill` checked/unchecked computed styles across all 5 skins × 2 themes, plus visual
screenshots of the Filtre rail and table view.

---

## 2026-08-08 — `scrape_synonyms.py` delay floor lowered to 1.2s

Weekend, one-off run, `relevant` seam only (~2.8k words) — traded some of the politeness
margin for speed. Floor moved from `--delay >= 3` to `--delay >= 1.2` in the refusal
check, the `--delay` default, and both docstring/usage mentions; `CLAUDE.md`'s Synonyms
section updated to match. `scrape_definitions.py` was left at its `--delay 3.0` default —
that one runs unattended for hours, not requested to change.

Killed the in-flight run (still at the old 3s pace, pid 47112) and restarted it under the
same `data/logs/synonyms.log` / `synonyms.pid` convention so it resumes from the existing
checkpoint rather than re-scraping. `acquire_host_lock()` still applies unchanged — it
guards against concurrent processes regardless of what `--delay` is set to.

---

## 2026-08-08 — Shared page shell, last-attestation signal, keyboard access

Backlog pass. Four items, one of which turned out to be already-paid-for work nobody had
spent.

### Two scrapers were running at once

`ps` showed two `scrape_synonyms.py --seam relevant --merge` processes started three
minutes apart, sharing one checkpoint CSV and hitting dexonline.ro every ~1.5s between
them. `--delay >= 3` is refused below 3s at the argument level, but it is a *per-process*
guard, so N copies divide it by N.

Fixed with `acquire_host_lock()` — an exclusive `flock` on `data/.dexonline.lock` taken
before the queue is even planned, so a second run hears why it is stopping instead of a
plan it will not execute. Keyed on the host rather than the script so `scrape_definitions.py`
interlocks by adopting the same two lines; `flock` rather than a PID file so `kill -9`
cannot strand it; `--dry-run` exempt because it makes no requests. Two tests cover
exclusion and release. Both processes were stopped and one restarted — resume is
checkpoint-based, so nothing was lost.

The `--seam relevant` scrape was left running at commit time: **1,418 of 2,815 words
done** (1,133 ok, 285 `not_found`), logging to `data/logs/synonyms.log` with its pid in
`data/logs/synonyms.pid`. It resumes on its own if interrupted; run
`python tools/build_ui_db.py` afterwards to fold the results into `ui.db`.

### The last-attestation blocker was gone and nobody had noticed

The backlog said this needed "a hand-curated `dictionary → publication year` table — 73
rows" because there was "no year metadata anywhere". Since that was written,
`extract_dict_sources.py` learned to read `Source.year`, and `newest_dict_year` had been
flowing all the way into `ui.db` — **97% coverage, 15,862 of 16,315 words** — where a
`grep` over `public/` found exactly zero uses of it.

Shipped without a pipeline run or a new column: `sort=attested`, an `attested_before=<year>`
filter (registered in `AF_SPECS` and both URL arrays, so it is shareable), and "ultima
atestare 1929" as the lead chip in the detail panel.

The caveat that matters: `relevant` requires `in_current_dict` (2005+) to qualify, so it
is 2,806 words at 2010+ and 9 below — this is a `curiosity`-seam instrument. There it is
sharp. 225 curiosity words were last printed before 1970 and that slice is a clean sweep
of pre-1953-reform orthography: `desbatere`, `sburătoare`, `răsvrătit`, `orândueală`,
`vuet`, `zeciueală`.

### One page shell instead of five

`stats.php` had no brand or title at all — you landed on a bare filter strip. `index.php`
put nav in the bottom status bar, `joc.php` in a top `.joc-nav`, `lista`/`liste` in a
`.lista-nav`, and the three display toggles were pasted into all five.

Split into `_partials/header.php` (brand + three `ob_start()` slots + preferences) and
`_partials/footer.php` (the one nav bar) — **identity at the top, travel at the bottom**.
Nav deliberately did not go in the header: the explorer's top bar already carries nine
controls and "the brand bar carries too much" is a live backlog entry. `.joc-head`,
`.joc-title`, `.joc-nav` and `.lista-nav` are gone from the pages and from `brutal.css` /
`govuk.css`.

Beton caught the one real bug. Rendering the current page as a `<span>` stopped it
matching every skin's `#status-bar a` rule, so it needed a colour of its own — and
`var(--text)` is a *page*-ground token, which on beton's ink footer is near-black on
black. Keeping it an `<a>` with `aria-current="page"` and an accent underline means every
skin's existing link rule applies for free. Verified across five skins × two themes.

### Keyboard access to the word list

Rows were click-handling `<div>`s. Made the list a **listbox with a roving tabindex**
rather than putting `tabindex="0"` on every row — with infinite scroll, the literal fix
would have meant tabbing through thousands of words to reach the footer. Tab enters once
and lands on the selected word; `j`/`k`/arrows carry focus, but only when focus was
already on a row, so a `?word=` link on page load doesn't yank the caret; Enter and Space
activate, with Space `preventDefault`ed so it doesn't scroll instead. The mouse path now
routes through `selectRow()` too — it used to set `data-selected` by hand, which would
have left the tab stop behind. `aria-pressed` added to the view and theme toggles.

Two things found on the way: `app.css` defined **no `:focus-visible` at all** (only
`brutal.css` did), so the moment rows became focusable there was a caret nobody could
see; and `kbd { display: none }` below 768px had left the `?` link a **zero-width tap
target** on mobile — which is the only route to the colour legend on a phone, since the
footer legend hides below 1280px.

### Still open, deliberately

The visual half of "verdict is colour-only in cloud view" is a design decision, not an
accessibility patch — shape-coding the dot does nothing in beton (which drops the dot),
and showing `EXT`/`DEC` changes the density of the main view. The screen-reader half is
fixed via the row's `aria-label`. Also logged: the index sort `<select>` is four English
strings, which belongs in one pass with the `stats.php` copy list.

`tests/test_store_sync.js` fails on `main` as well — pre-existing, untouched here.

## 2026-08-08 — Data-quality audit: paradigm-aware verdicts and two seams

Audit before opening the site to markers. The selection logic had three compounding
bugs that made verdicts wrong rather than merely noisy, and the default ranking surfaced
exactly the words the project least wants.

### What was wrong

1. **ppm compared across a 1,187× size gap.** `validate_diachronic.py` applied the same
   `0.1 ppm` floor to Wikisource (14.3M tokens) and CulturaX (17.0B). "Absent from modern
   Romanian" therefore meant *fewer than 1,697 web hits*: `zapciu` had 1,322 and was
   `extinct`. `extinct` topped out at exactly `modern_ppm = 0.0999` — the tier was capped
   by the threshold, not by absence.
2. **Counts were per surface form.** Romanian is heavily inflected, so a lemma was only
   credited with its citation form: `înmărmuri` 317 while `înmărmurit` alone was 5,846;
   `moleși` 310 vs a 9,205 paradigm; `cătrăni` 59 vs 1,825. Every verb drifted toward
   `extinct`.
3. **`declining` measured literary register, not decline.** `log_ratio >= 1.0` means
   "twice as common in 19th-c. Wikisource as on the modern web", which is true of most of
   the literary lexicon. 2,602 of 5,998 `corpus_declining` words had ≥ 8,500 modern hits —
   `vapor`, `fluviu`, `cioban`, `palid`, `viclean`, `colac`.

Also measured: `dex_pos` populated for 3.5% of rows, `zipf_frequency` non-zero for 5.8%,
`web_score` for 0.19%. And `Lexeme.frequency` is not a usage frequency — `zapciu` 0.96 vs
`internet` 0.88 — so the default `modern_ppm ASC` sort ranked the list upside down, with
`vivliotică`, `tăligraf`, `sâroman` (archaic respellings of *bibliotecă*, *telegraf*,
*sărman*) scoring as the "most forgotten".

### What changed

- **`extract_inflected_forms.py`** (new) — `InflectedForm` + `Lexeme` in one pass via the
  new quote-aware `dump_parser.py`. 2,269,003 forms → 1,633,231 form→lemma pairs covering
  317,718 of 317,721 lexemes.
- **`extract_dict_sources.py`** — now also reads `Source.year` / `Source.normative`, adding
  `newest_dict_year`, `oldest_dict_year` and `in_current_dict` (published 2005+). 113
  dictionaries, 108 dated. `normative` is set for only the 2 DOOM editions, so `year` is
  the usable signal.
- **`validate_diachronic.py`** — `aggregate_by_family` rolls counts over paradigms;
  ambiguous forms (12% of the map) are split between claimant lemmas in proportion to each
  lemma's own headword count. Two earlier attempts failed and are recorded in the
  docstring: crediting every claimant in full gave `veșcă` (sieve rim) all 339,710 of
  `veste` (news) via their shared plural; weighting by "forms only one lemma claims" gave
  the opposite error, because a noun's citation form is frequently shared too (`veste` is
  claimed by both `veste` and `vestă`). `aggregate_loose` keeps the undivided total on
  purpose — the loose/disambiguated ratio is the archaic-variant detector.
  Verdicts now use occurrence floors (`MODERN_RARE_OCC` 500, `MODERN_ALIVE_OCC` 2000,
  `HIST_MIN_OCC` 3 + `HIST_MIN_DOCS` 2) and `rank_shift`, a percentile-rank difference
  that is scale-free.
- **`make_shortlist.py`** — `classify()`'s first-match-wins ladder replaced by a weighted
  score, and the 0.70-in-signature / 0.85-on-CLI threshold mismatch collapsed to one
  constant. Output splits into `relevant` (2,346) and `curiosity` (13,857). The five
  `confidence_tier` names are unchanged so the UI's `TIERS` map and `--v-*` CSS tokens
  still work.
- **UI** — default sort is `quality_score DESC`; defaults hide regional-only, variant-like
  and proper-noun words; `seam` selector added. Toggles are `show_*` rather than `hide_*`
  because an unchecked checkbox is not submitted, so a default-on `hide_*` can never be
  turned off.

### Calibration

Thresholds were set by sampling bands, not guessed. Disambiguated modern counts:
`0` hărățire/zalisi/berbelâc · `1–19` scoborâre/cârcioc/zapcierie · `20–199`
madmoazelă/gheșeftar/evhologhion · `200–999` jiliște/civilizațiune/docar/calabalâc ·
`1k–3k` lehuzie/arhaism/stăvilar · `3k+` despotic/verișoară/călăreț. `family_ratio` over
the 8,879-word candidate pool: 86% sit at 1×, and 25× is where "this verb has a common
participle" (pardosi, teși, 4–10×) turns into "this is an old spelling of a live word"
(justeță, acurateță, datoriu, uleu).

Adding historical attestation to the score was the single biggest quality change. Without
it the top of the relevant seam was `potricală`, `țarțam`, `sărciner` — rare, but never in
circulation. With it: `poronci`, `jeț`, `jiganie`, `iznoavă`, `tibișir`, `vorovi`,
`potcă`, `ciocoism`, `prepelicar`, `spoliație`, `poetastru`.

### Corrections to the audit's own claims

- The "~48k lost Lexeme rows (13%)" in the plan was **wrong**. `AUTOINCREMENT=365,869` is
  a high-water mark, not a row count. The dump holds 317,721 `Lexeme` tuples and the old
  regex parser reads 317,688 — a real loss of **33 rows (0.01%)**. Verified by counting
  top-level tuples independently.
- The 648 "column-shifted" rows are not a parse failure either: the new quote-aware parser
  reads the same 648 as empty. It is a data quirk (no frequency value). Storing them as
  NULL rather than an empty string that sorts above 1.0 is still an improvement.

### Retired

`analyze_forgotten_words.py`, `validate_forgotten_words.py`, `process_corpus.py`,
`download_wikipedia_ro.py`, `search_wild.py` and the whole Flask `ui/` moved to
`archive/`. The Flask tests had been failing against real data for a while — `app.py:133`
falls back to the real `rare_words_wordfreq.csv` instead of the fixture, so
`test_load_words_count` asserted `115 == 2`. Suite is now 70 tests in 4s.

### Verification

`data/word_ids.tsv` grew by 1,033 lines with **zero removals** and no existing id
changed, so every `?w=` link shared to date still resolves. Default view measured through
the running app at 2,273 words (9 pages of 250 + 23), matching the DB predicate exactly;
`gheb` (proper noun) hidden by default and visible with `show_proper=1`.

### Follow-up fixes after review of the running app

Three bugs, all found by looking at the actual UI rather than the API:

1. **The new toggles never reached the URL.** `hide_loanwords` round-tripped but
   `show_proper` / `show_regional` / `show_variants` / `seam` did not, so the state was
   unshareable and lost on reload. Filters have to be registered in
   `public/assets/app.js` as well as PHP — `AF_SPECS` for the chip, plus the read/write
   arrays in `applyUrlToForm` and the URL writer, plus `URL_PARAM_DEFAULTS`. Now noted in
   CLAUDE.md, because nothing about adding a PHP filter suggests you also owe the JS.
2. **`proper_noun_like` was hiding ordinary words.** It flagged any word colliding with a
   capitalised DEX headword, so `gheb` ("cocoașă") was hidden because DEX also lists the
   name `Gheb`. Harmless while the filter was opt-in; a real loss once it became the
   default. Now flags only words DEX knows *exclusively* as capitalised: 447 marked → 2.
   Also switched the test from `GLOB '[A-Z]*'` to `str.isupper()`, which was ASCII-only
   and missed Ș/Ă/Î.
3. **"arată regionalisme" and "arată variante vechi" were dead controls.** Regional and
   variant words were penalised 25/35 points in the score *and* routed out of the seam,
   so the relevant list contained none of them and the toggles had nothing to reveal —
   the checkbox visibly ticked and the count never moved. The penalties are gone: the
   score now measures evidence quality only, and the three flags are purely the UI's to
   act on. The relevant seam holds 397 regional and 77 variant words, hidden by default,
   and the toggles move the count (2,345 → 2,738 → 2,815). The 4–25× family-ratio penalty
   stays, since that is an evidence problem rather than a preference.

The default view is unchanged in size (2,345) and content; what changed is that the
excluded classes are now reachable.

### Second review pass — the filter sheet

Three more, all from the same neglected column:

4. **The CATEGORIE (POS) filter matched nothing.** `dex_pos` was built from meaning-level
   taxonomy tags: 480 of 16,315 words (2.9%), and the values were mostly `locuțiune
   adverbială`, not the eight options the filter offers. Selecting `vb.` returned zero
   words; `s.m.` returned one. Rebuilt from `Lexeme.modelType`, the inflection model DEX
   actually conjugates with — present on all 317,721 lexemes. Coverage **2.9% → 99.5%**,
   and the options now return 924 / 400 / 480 / 402 / 277 for the four noun-adjective
   classes and verbs. Mapping verified by sampling high-frequency words per model:
   `F/M/N` nouns, `A/AF/AM/AN` adjective, `V/VT/VI` verb, `PT` participle, `P` pronoun,
   `SP` proper noun; `T` (strămoși, cii) and `IL` (contrare, militare) are inflected forms
   rather than headwords, and `I` is invariable, so those fall back to `description`.
   The derivation has to run *before* the `vocab` table is built or the dropdown keeps
   listing the old values.
5. **`visternic` was labelled "substantiv feminin".** Same cause: its `modelType` is `M`,
   but the DEX entry also covers the feminine `vistiernică` and the meaning tag bled
   across. Correct now, and guarded by a test.
6. **The rare tab showed one word out of 112.** `dex_max` defaulted to a 0.60 DEX-frequency
   ceiling — which made sense only under the old reading of that column. Since DEX
   frequency is literary prominence, a rare word sitting at 0.9 is ordinary, not a
   contradiction. Default is now no ceiling. The seam control is also hidden on that tab:
   those 112 words come from `validate_with_wordfreq.py` and are all stored `relevant`, so
   "curiozități" was a live-looking button that could only ever return the same list.
   `dex_max` had exactly this treatment already; the seam control now shares it.

### Synonyms piped in

`scrape_synonyms.py` + `synonyms.db` + chips in the detail panel, closing the backlog
item that had been waiting on data.

The data is **not in the dump**, which is worth recording because it looks like it should
be: dexonline distributes `Definition.internalRep` in full only for the Academy
dictionaries. The Litera titles are redacted to 20 characters plus an ellipsis —
`sourceId 6 (Sinonime)` has `max_len=23, mean=23` against `sourceId 1 (DEX '98)`'s
`max_len=15,039, mean=201`. So `dict_count` has always known a word appears in
`Sinonime`/`Sinonime82`/`Antonime` without being able to say what they contain.

Two parser corrections, both from reading real output rather than trusting the first
version:

- A dexonline page renders every entry it considers related. `/definitie/roză` also
  carries `ROZ` (the colour), so the first run gave `roză` nine synonyms of which six
  — *trandafiriu, rozatic, roziu, pembe, rozosin, rumen* — belong to a different word.
  Matching on headword cuts it to the correct three. The fallback when nothing matches
  is deliberate: `/definitie/poronci` returns entries headed `PORUNCĂ` and `PORUNCI` and
  none headed `PORONCI`, so a strict match would return nothing for precisely the
  archaic spellings this project exists to find.
- Each entry opens with its own capitalised headword, sometimes inside a token because
  the markup does not separate it (`"ROZĂ     trandafir, rug"`). One run gave
  `CELE ZECE PORUNCI     decalogul` as a single "synonym".

A unit test also caught that single-letter headwords (`A`, `Î`, `O` are real DEX entries)
survived the capital-stripping pattern, which required 2+ capitals.

Hit rate on the 12-word live test: 9 ok, 3 not_found. `jeț` → *fotoliu, șezău*;
`jiganie` → *dihanie, fiară, jivină, lighioană, sălbăticiune*; `modru` → *chip, fel,
formă, gen, manieră, metodă, mijloc, mod*.

### Not a regression

The `SINONIME — ÎN CURÂND` slot was removed in the previous session, not this one —
`docs/BACKLOG.md:689` records it as dropped 2026-08-07 ("along with…"), and
`activity-history.md:141` says the same. The synonym *data* was never there;
`docs/BACKLOG.md:244` still tracks scraping it from dexonline's `Sinonime`/`Sinonime82`.
Those dictionaries are intact in `sources` for 7,946 words and show as chips in the
detail panel.

### Docs brought in line

`README.md` (pipeline diagram, Phase 1/2b/3, the CSV contracts, the tier table, the
limitations list), `public/metodologie.html` (sections 04, 05, 08 and the timeline) and
`CLAUDE.md`. The methodology page had been describing the ppm log-ratio formula and the
old seven-verdict ladder, both of which no longer exist.

One thing worth noting as a near-miss: a global replace of the old shortlist figure
`23.112` also rewrote a **2026-05-19 timeline entry** that legitimately recorded the count
as it was on that date. Caught in review and restored — a changelog that silently updates
its own history is worse than one that is out of date.

### Open

`oțios` itself now lands in the **curiosity** seam (score 67): zero historical corpus
attestation and 266 modern occurrences. Defensible, but worth a decision before the
naming question is settled.

---

## 2026-08-07 — Raw enums out of the UI, and the two launch blockers

Two batches. The first was everything a visitor could see and shouldn't; the second was
the pair of items the backlog itself named as prerequisites to promoting the site.

**One home for the classification labels.** `verdict` and `confidence_tier` are English
identifiers written by the pipeline, and they were reaching the page verbatim —
`historical_only` sat second in the visual hierarchy of the detail panel, right after the
headword, in an otherwise fully-Romanian UI. The labels already existed, trapped in
`index.php`'s filter-pill markup. `VERDICTS` and `TIERS` in `api/_lib.php` now hold label,
abbreviation, tooltip and bar-fill class together, read through `verdict_label()` /
`verdict_abbr()` / `tier_label()`.

What made this worth doing properly rather than patching the one badge: the tier map
existed in **three** places (`index.php`, `stats.php`, `stats_panels.php`), each with its
own wording, and the hover box was mapping the enum a *fourth* time in JavaScript. That
last one is why `word_row.php` now emits `data-vlabel` — the label is rendered server-side
into the row and `app.js` just reads it, instead of keeping a parallel copy that can drift.
Only three English strings needed translating (`corp. extinct` → `corp. dispărut`, and its
two siblings); everything else reused copy the owner had already written. Verified by
stripping tags from `index` / `stats` / `joc` / the detail panel and grepping: no enum
survives in visible text.

Alongside it: pinch-zoom unblocked on all three pages that still set `maximum-scale=1` (a
WCAG 1.4.4 failure, and an unkind one on a site made of unfamiliar words); the debug
metrics footer labelled in Romanian with real tooltips rather than hidden behind a flag,
since on a research tool the numbers are the point and were merely unreadable
(`zipf0.0 en0.0 hist0.77` → `zipf ro 0.0 · zipf en 0.0 · istoric 0.77`); and the
`SINONIME — ÎN CURÂND` placeholder dropped until there is data for it.

The "dead UI surface" cleanup turned out to be **half wrong in the backlog**, which is
worth recording. Notes were genuinely dead — nothing created one, nothing displayed one,
and the `marks` filter still offered "cu notă", which selected words whose notes you could
not read. Gone. But the tag CSS is *not* orphaned: `store.js:117` still renders
`.tag custom-tag` chips for anyone who made custom tags before the input was removed, and
every `tag:` option in the filter is still produceable. Deleting it would have broken
existing users' data display. Server-side note storage was left untouched, so nothing was
destroyed — just no longer surfaced.

**Moderation, the blocker the directory shipped without.** `reports` table (app.db
`user_version = 3`), `POST api/lists.php {action:'report', slug, reason?}`, a deliberately
quiet report link at the bottom of `lista.php`, and `public/admin.php` as the queue.

Three decisions that will look like omissions later, so: **no auto-hide after N reports** —
identity here is an anonymous device token, so "three different people reported this" costs
an abuser three cookie clears, and a threshold would make censoring a list cheaper than
publishing one. **A private or missing list both answer 404** to a report, so the endpoint
can't be walked to discover which slugs exist. And **`lista.php` doesn't check ownership
before drawing the report button**, because that would mean calling `current_user()` on
every public view and minting an identity for every passing crawler — a property the page
was explicitly built to have; the API rejects `own_list` and the button says so.

The admin page is 404 rather than 403 without a valid token, so an install that never
configured moderation gives nothing away when probed. The token is passed once as
`?token=`, sealed into an 8-hour cookie via the existing `seal_token()`, and redirected
out of the URL. That forced one non-obvious choice: the page sets `referrer: same-origin`,
not `no-referrer`, because `no-referrer` serializes `Origin` as `null` and
`require_post_same_origin()` rejects exactly that — the page's own forms POST back to it.
Unpublish, not delete, is the default action: nothing of the owner's is destroyed on a
stranger's say-so.

**Backups.** `php api/_backup.php` — `VACUUM INTO` (not `copy()`: in WAL mode the
committed data is split across `app.db` and `app.db-wal`, so a file copy can land
mid-transaction and produce a torn file), then reopen the snapshot and
`PRAGMA integrity_check` it before pruning to `--keep N`. It lives in `public/api/`
because only the contents of `public/` reach the server, and it is CLI-only —
`PHP_SAPI !== 'cli'` returns 404 before any include, verified over HTTP. What this does
*not* do is get a copy off the machine; that stays open in the backlog.

Verified with a new `tests/test_moderation.js` (18 checks: the report rules, the 404
symmetry, token handling, and unpublish removing a list from the directory and the shared
link while leaving the owner's copy intact), plus the three existing suites still passing
(23 + 13 + 16). Browser-level visual confirmation wasn't possible — the Chrome extension
wasn't connected — so the UI checks were made against rendered HTML rather than pixels.

---

## 2026-08-07 — Lists hub, bucket publishing, packed share URLs

Interactivity pass on lists: creating them, seeing them, sharing them. Three things were
broken, and the fix for the first one made the other two much smaller than expected.

**The lists already existed — we just weren't calling them that.** People fill four buckets
while browsing (`fav`, `lol`, `ascunde`, `meh`) and those *are* their lists. Nothing was
built on top of that: the only fill path was `+ adaugă favoritele`, which read
`bookmarkedWords()` out of localStorage and POSTed the whole array — to a server that
already held the same annotations. `lol`, `ascunde` and `meh` could not be published at all.

So a list is now a **published snapshot of a bucket**. `lists.source_tag` records which one,
`POST {action:'publish_bucket', bucket}` reads the words server-side from
`annotated_words_subquery()` (the function `search.php`'s marks filter already used), and
`{action:'refresh', id}` re-reads them later — keeping `position` for words that stayed, so
re-syncing doesn't reshuffle a list someone has already read. The client never uploads, or
even holds, the list it is publishing. That framing removed most of the planned work:
no per-word "add to list", no grid multi-select, no inline list editing.

**Seeing them: `liste.php`.** The buckets with counts and a publish button, your published
lists, and a *Liste publice* directory of everyone's. The buckets are derived per request,
never stored, so they cannot go stale. The `#lists-overlay` modal it replaces is gone, with
~125 lines of `app.js` and its rules in `app.css` and `brutal.css`.

**Sharing: `?words=` → `?w=`.** Romanian diacritics percent-encode to six characters each
(`ă` → `%C4%83`), so a shared playlist was mostly escape sequences. Both reference
conversations in `docs/reference/` land on dictionary indexing for a fixed vocabulary, and
that is what shipped: a version prefix plus one base36 word id per word. Three words went
from 44 characters to 11.

The load-bearing part is not the codec, it is **`data/word_ids.tsv`** — append-only, and
force-tracked in git against the blanket `data/*` ignore. `ui.db` is deleted and rebuilt on
every data refresh, so an id derived from row order or a rowid would silently repoint every
link ever shared. Words are never renumbered and never removed; a word that drops out of a
later shortlist keeps its id so old links to it still resolve. Tracking the file means an
accidental renumbering shows up as a 25k-line diff instead of as broken links six months
later. `tools/word_ids.py` owns assignment, `build_ui_db.py` calls it at the end of a build,
`tools/migrate_ui_db_word_ids.py` backfilled the deployed database (25,305 ids, no gaps or
duplicates, byte-identical on a second run).

`pack_words()`/`unpack_words()` live in `api/_lib.php` and are exposed as `api/pack.php`, so
the browser never carries the 25k dictionary. Old `?words=` links still work. A `w=` that
decodes to nothing — mangled, or a version this build doesn't know — returns an empty grid
rather than falling through to all 25,305 words, which would have read as a bug.

**Deliberately deferred.** The public directory shipped with no report/takedown path, which
`docs/BACKLOG.md` had flagged as a blocker; the owner chose discovery first. Two hedges,
neither a substitute: the page is `noindex`, and it says the lists are unverified. The
backlog entry is now marked more urgent rather than closed.

Verified with `tests/test_lists_api.js` (22 checks: pack round-trip, `search.php?w=`,
publishing an empty bucket, refresh after unbookmarking, cross-user visibility, directory
filtering) plus a Playwright pass over the browser-only paths — bookmarking, the share
button, the playlist banner, publish, and the page in both the `beton` and `govuk` skins.
`test_game_api.js` and `test_store_sync.js` still pass; `app.db` migrated to
`user_version = 2`.

---

## 2026-08-07 — Subfolder deployment, and the cookie path bug it exposed

First deployment to a subfolder: `lab.gov2.ro/oțios/`, served from `~/lab.gov2.ro/oțios`
with the contents of `public/` copied in. It works — `BASE` is derived correctly and every
asset, link and htmx endpoint follows it — but two things came out of doing it for real.

**`app.db` defaults to inside the web root.** `OTIOS_PRIVATE_DIR` is one level up from the
app folder, which on this layout is the document root itself, so `app.db` was a 364 KB
download at `/private/app.db`. Fixed on the server with `api/config.local.php` pointing at
`~/otios-private` — the override `_appdb.php:18` already supports. Nothing to change in
the code, but it is the first thing to check on any subfolder install.

**The device cookie never came back.** `_auth.php` set the cookie's `Path` to `BASE . '/'`,
which for this install is `/oțios/` — raw UTF-8. A cookie `Path` is matched as a byte
prefix of the request-URI, and browsers send that percent-encoded (`/o%C8%9Bios/`), so the
two never matched. The cookie was set on every response and returned on none, and since
the cookie *is* the account (`_auth.php:6`), **every request minted a fresh anonymous
user**. Answers were being written — one each, scattered across hundreds of throwaway
accounts — and the leaderboard then created another new user with no `game_stats` row, so
it reported "Niciun scor încă" on a database that was filling up.

`BASE` is now percent-encoded per segment for the cookie path (`cookie_base_path()`).
ASCII installs are byte-identical to before. Verified in a real browser against both an
ASCII and a diacritic install: identity held across four answered questions, `total` reached
4, and the leaderboard returned the caller's standing.

Worth recording how this was nearly missed. An earlier pass had already tested the
diacritic path and passed it — BASE resolution, asset loading, htmx, all four pages, no
console errors. All of that passes because browsers percent-encode those URLs
transparently. The cookie round-trip was the one path that surfaced the raw bytes, and it
was the only thing not exercised. The diagnostic that actually pointed at identity rather
than at writes was a *negative* observation: the screenshot lacked the "Seria ta cea mai
lungă … locul N dacă te înscrii" line that `joc.php:490` renders whenever a caller has a
score but no nickname, so `you` had to be null — no stats row at all, not a filtered one.

Notes for the next deploy are in CLAUDE.md: copy `public/`'s contents (never the repo —
`.git/`, `private/` and the docs are all fetchable otherwise), keep the folder physically
inside the document root (an `Alias` or symlink breaks the `BASE` subtraction, silently —
measured one producing `BASE = "blic"`), and on nginx add a `deny` rule for `*.db`, since
the bundled `.htaccess` guarding the 20 MB `ui.db` is Apache-only.

## 2026-08-06 — Two skins from the backlog: Guvern (GOV.UK) and Tezaur (thesaurus)

Built the two skin ideas most worth having, and used the first to test how far the token
contract actually reaches.

**`govuk.css` — "Guvern".** Palette, radius and type all came from tokens: the published
GDS colour list, `--radius: 0`, and all three font tokens pointed at one Arial stack (GDS
Transport is licensed to gov.uk only; GDS itself specifies Arial for everyone else, and a
single family everywhere is the look). What tokens could *not* express, and so needed
component rules: the black masthead with its 10px blue rule and every control in the bar
re-tuned for a dark ground; the yellow focus state; square dots, swatches and checkboxes;
tags without their leading dot; the green button's 2px sunken edge; always-underlined
links thickening on hover; the definition as `govuk-inset-text`. Of those, only the square
marks look like a missing token. Two deviations, both recorded in the file: GDS brown
#b58840 is 2.86:1 on their own light-grey, under the 3:1 floor for an 8px dot, so it is
darkened to #946218; and GOV.UK has no dark mode, so that block is invented.

**`tezaur.css` — "Tezaur".** An homage to thesaurus.com/dictionary.com, no brand asset
reproduced. The idea worth stealing was the tinted synonym pill: the cloud is already a
dense field of words, so a tint per verdict is both recognisably that reference and a
stronger encoding than a 6px dot — which the skin hides. Weak-match tint rather than
strong-match solid fill, because several hundred saturated pills is a wall. The verdict
colour goes on `.word-row`, not `.word-text`, so the freq superscript inherits it and
stays legible on the tint instead of sitting there in `--text-4`.

**Found a real bug that predates both.** `--on-accent` was declared in `app.css` and never
once used — the two places that need it, `.fs-apply` and `.filter-count-badge`, hardcoded
`white`. Dark accents are light, so the apply button's label was 3.06:1 in `paper`, 3.16:1
in `velin` and 2.23:1 in `tezaur`. Fixed at the source (both call sites now read the token,
and `:root[data-theme="dark"]` sets it to ink); verified across all five skins × both
themes, worst case now 4.92:1.

Everything was measured rather than eyeballed, via Playwright + computed style: all four
verdicts forced into view under both skins and both themes (the default sort shows only
two of the four); the 10px blue rule; every rail pill state; `joc`/`stats`/`lista` for
skin application and horizontal overflow. Two defects of my own turned up that way — the
`govuk` focus rule lost to `#status-bar a` on specificity and left a focused link light
blue on yellow, and `tezaur` had no focus ring at all.

Also documented the token contract properly. `_template.css` had never listed the font or
metric tokens, or `--on-accent`'s dark-mode trap; CLAUDE.md now defines what a token *is*
and why it differs from a component rule, since that distinction is the whole reason a
skin can be 68 lines or 1000.

## 2026-08-06 — Footer legend; the collapsible rail already existed

Added a legend to the status bar covering everything the cloud encodes without a label:
the four verdict colours, the dotted underline (`învechit`), the solid underline
(favourite) and the superscript (DEX frequency, 0–100, lower = rarer). The two underline
samples reuse the real mark declarations rather than approximating them.

The swatches could not simply reuse the values the words are painted in. The footer is
ink and the cloud is bone, and beton's `-word` ramp is fitted for 8.5:1 against bone —
against ink it collapses to **1.8:1**, four near-black squares. Measured, then switched to
the brighter badge colours for the footer only: same hues rendered for a dark ground,
which is the honest mapping rather than a different one. Absent lands at 2.97:1, a hair
under the 3:1 for non-text UI, and the bone hairline round each swatch carries the shape
independently of its fill.

The swatch colours moved from inline `style=` to classes (`.lg-sw-ext` etc.) so a skin can
restate them for its own background without `!important`. They resolve
`var(--v-ext-word, var(--v-ext))`, so a tokens-only skin like `velin` or `paper` falls back
to its dot colour and needs no legend rules at all — verified in all three.

Breakpoint set by measurement, not by guess: the legend needs 576px and the rest of the bar
603px, so at the first-chosen 1200px it was clipped mid-word. It shows from **1280** up;
below that the `?` modal carries the same legend.

**The collapsible filter rail already existed** and was left alone. `toggleFilterDrawer()`
has handled the docked case since before this branch — the brand bar's "filtre" button
collapses and expands the rail, the state persists to `otios.rail`, and it defaults to
open. Verified rather than assumed: the toggle takes the rail 288px → 0, the preference
round-trips, and sampling the rail's width every 25ms through a collapsed reload shows no
flash of the open rail before JS applies the class.

Skin ideas (GOV.UK, monitorul.ai, dictionary.com, Urban Dictionary, Wikipedia, Genius) are
in `docs/BACKLOG.md` with a note on which of them will need component rules rather than
tokens alone.

---

## 2026-08-06 — Skins become a folder: drop in a CSS file, get a dropdown entry

The two-button `▤`/`▩` toggle is replaced by a `<select>` whose options are discovered
from `public/assets/skins/*.css`. Adding a style is now one file — no registry, no build
step, no PHP to edit.

`public/api/_skins.php` does the discovery and is required from `_lib.php`, so all four
pages get it. `skin-brutal.css` moved to `assets/skins/brutal.css` (`git mv`, so history
follows) and the filename is now the id it scopes under. A skin declares its label with an
`@skin <label>` tag near the top; without one the filename is used. Underscore-prefixed
files are skipped, which is how `_template.css` can live in the same folder.

This also killed four copies of the pre-paint boot script, four hardcoded `<link>` tags
and four copies of the toggle markup — the skin machinery had been pasted into every page
`<head>`, and adding a dropdown by hand would have multiplied that by three.

Decisions worth recording:

- **Every skin file loads on every page**, each inert until its attribute matches. Emitting
  only the active skin's `<link>` needs either a cookie round-trip or a JS-injected
  stylesheet, and the latter reintroduces exactly the flash the boot script exists to
  prevent. The files are small; if the folder grows past a handful, revisit.
- **Ids are validated, not trusted** (`^[a-z0-9][a-z0-9_-]*$`) — the id lands in a data
  attribute, a CSS attribute selector and a URL. `Bad Name.css` and `UPPER.css` are
  ignored rather than half-working; both were tested.
- **`<link>`s carry `?v=<mtime>`** so editing a skin shows up on a plain reload. This
  folder exists to be fiddled with.
- **The valid skin list is baked into the boot script**, so a stored skin whose file has
  been deleted falls back to the default instead of leaving `<html>` pointing at a
  stylesheet that no longer exists.

Added `velin.css` ("Velin — pergament") as a worked example: ~70 lines, tokens only, no
component rules at all, proving that redeclaring the custom properties restyles the whole
site. Delete it if it's not wanted.

Verified: all three skins render; a deleted skin falls back cleanly; invalid filenames are
skipped; `_template.css` never appears; no horizontal overflow at 320/360/390/480/768 —
the select is wider than the toggle it replaced, so that needed re-checking on mobile.

---

## 2026-08-06 — Verdict as colour on the word itself, and a legend for the cloud

The verdict dot cost 8px of square plus a 5px gap on every word. Replaced in the beton
skin by colouring the headword instead — measured effect: **13px saved per word, 125 →
138 words fully visible per 1440×900 screen (+10%), and 27 rows instead of 30 for the
same 200 words.** Paper keeps its dots, so the two can be compared live with the ▤/▩
toggle. Table view is untouched: it hides the dot already and states the verdict in the
IST/EXT badge, so colouring there would say it twice.

Getting the colours right took three passes, and the first two were wrong in instructive
ways.

1. **Reusing the badge palette failed WCAG.** As a fill behind a badge these colours only
   had to clear 3:1; as 23px text on bone they need 4.5:1. Extinct was 4.09:1 and
   declining was **2.36:1** — the orange was effectively unreadable as a headword.
2. **Fixing contrast alone was still wrong.** At ~4.6:1 against ink's 15.5:1 the coloured
   words were visibly *lighter* than black ones, so verdict was encoded as weight as well
   as hue. Worse, `historical_only` is 41.8% of the corpus and the default sort surfaces
   it almost exclusively — so a screen of hyperlink-blue words read as "everything here
   is a link".
3. **Making the plurality plain ink was also wrong** — tried it, and the landing view then
   carried no verdict encoding at all.

Settled on fitting all four to a common **~8.5:1**: one family distinguished by hue alone,
close enough to ink that a page made entirely of any one of them still reads as a page of
words. `#841009 / #663300 / #073C8D / #5313AC`. Dark mode needed no refit — every colour
already clears 4.5:1 on near-black — but the hover wash did: at `#4A4200` the brighter
verdicts dropped to 3.0–3.4:1 against it, so it went to `#241F00`, where all four clear
4.5:1 and bone text improves from 8.97 to 14.61. Hover is still legible as a state because
beton draws a bone border on it; the wash was never carrying that alone.

Removing the dots makes verdict colour-only in the cloud, so the cloud now needs a key:

- The rail's four verdict swatches are repainted in the same `-word` ramp. Showing the
  brighter badge fill next to a darker word would make the key wrong.
- A **Legendă** block was added to the `?` modal covering both the verdict colours and the
  superscript number, which had never been explained anywhere: it is the DEX frequency
  score, 0–100, lower = rarer. The superscript also gained a `title`.
- That made the modal a legend as well as a shortcut list, so its heading — still the only
  English string on the page, next to entirely Romanian content — became
  "Legendă și scurtături".

Verified by measurement, not by eye: at one point a screenshot looked like the old bright
blue and the computed value was `rgb(7, 60, 141)` — a saturated navy at 2× just reads
brighter than it is.

Also written up in `docs/BACKLOG.md`: filtering by *which* dictionary and by most-recent
attestation. Counting them is already built (`dict_min`); the recency signal is blocked on
a `dictionary → year` map that exists nowhere — `dict_sources.db` is only `(word, sources,
dict_count)`, and while some of the 73 dictionary names embed a year, most do not.

---

## 2026-08-06 — Typographic pass: real columns, one tracking scale, ink emoji

Follow-up to the beton skin, on the same branch. The ask was "good taste" — rhythm,
type fine-tuning, alignment — so this pass was driven by measurement rather than by
looking at screenshots, using a Playwright harness that scripts 30 states (4 pages ×
2 skins × 2 themes × desktop/mobile, plus the drawer, feed overlay and both modals,
which had never actually been opened).

**Table view had no columns.** The one view whose entire purpose is a scannable list
was laying out under flex with `.chip-meta { flex: 1 }` as the only growing item. A row
that happened to carry a POS/register pushed its badges to the far right edge; a row
without one collapsed them against the word. Measured: the verdict badge took 8 distinct
left positions across 14 consecutive rows, a **1007px swing**. Replaced with a four-column
grid, each chip pinned to an explicit `grid-column` because the freq/meta/dict chips are
all conditionally rendered by `word_row.php` and auto-placement would reintroduce the
drift whenever one was missing. Re-measured: **1 position, 0px spread**. Fixed in
`app.css`, so the paper skin gets it too — it was never a skin-specific problem.

**Tracking was seven values doing one job.** `0.04 / 0.06 / 0.08 / 0.10 / 0.12 / 0.14 /
0.16em` scattered across uppercase mono micro-type at similar sizes, plus three separate
negative values on display sans. Collapsed to three tokens assigned by optical size —
`--tk-eyebrow` (9px uppercase labels), `--tk-ui` (10–12px uppercase UI), `--tk-display`
(sans headwords). All 26 declarations now resolve through them.

**Colour emoji drained to ink.** About a dozen (📚 📋 🎮 📊 🧐 🎲 📇 🔤 ❓ ✅ ❌) sit in
markup. In a bone/ink/two-accent skin a full-colour cartoon is the loudest thing on the
page, and one of them was decorating a dictionary count. Fixed with `filter: grayscale(1)`
scoped to the skin rather than by editing seven templates — paper keeps them, where they
read as warm rather than as noise. `grayscale()` alone, no brightness/contrast, so each
element's colour still resolves from the theme and dark mode stays correct.

Checked, not assumed: `.chip-freq { line-height: 0 }` looked like a bug and is a
deliberate superscript technique — left alone. The wider tracking makes the mobile status
bar wrap to three lines one breakpoint earlier than paper (≤390px vs ≤360px); measured at
54px of content in a 62px box, so it fits and nothing clips. No horizontal overflow at
320/360/390/480/768 on any of the three main pages.

Remaining findings — debug metrics (`zipf0.0 en0.0 hist0.77…`) and raw enums reaching the
page, a shipped `SINONIME — ÎN CURÂND` placeholder, triplicated definitions, the joc void,
and the filter rail stating one control two different ways — are in `docs/BACKLOG.md`
under "Typographic pass — remaining findings". They are content and data decisions, not
styling, so they were written up rather than changed.

Still not done: no real-device pass. The four interactive states are now verified in a
real Chrome via Playwright, but only at synthetic viewports.

---

## 2026-08-06 — "Beton": a brutalist skin, switchable against the existing look

Branch `feat/brutalist-skin`. Asked for a fresher, bolder, more brutalist UI, delivered as a
CSS switch rather than a replacement — the original editorial look is untouched and one click
away.

**The switch.** A second axis, `data-skin` on `<html>`, orthogonal to the existing
`data-theme`: `paper` (plain `app.css`, exactly as before) and `brutal` (`app.css` plus the
new `assets/skin-brutal.css`, every rule scoped under `[data-skin="brutal"]`). Both skins
define their own light *and* dark, so the two axes give four looks. Stored in
`localStorage['otios.skin']` and applied by the existing pre-paint boot script in each
`<head>`, so switching never flashes. `data-skin="brutal"` is also hardcoded on the `<html>`
element, which makes beton the default and the correct fallback when localStorage throws or
JS is off. Toggle sits next to the light/dark one on index, joc and stats (`▤` / `▩`), and
was added to `lista.php` too — a shared list is often a visitor's first page on the site, and
without it they'd be stuck with whatever the defaults happen to be.

**The skin.** Bone paper, ink rules, one vermilion for actions and one electric yellow that
behaves like a highlighter pen — hover washes a word in it, selection is a solid ink block
casting a hard yellow shadow. Nothing rounded, nothing blurred, every shadow a hard offset.
Two blunt global rules carry the invariants (`border-radius: 0 !important` on everything;
soft shadows explicitly zeroed) rather than chasing every radius across `app.css` and the
four pages that carry their own `<style>` blocks — that also means new components inherit the
skin for free. Verdict dots become squares; verdict badges become solid blocks of colour;
filter section labels become inverted index tabs; the status bar becomes a solid ink footer
that inverts with the theme. The type hierarchy is deliberately flipped against `app.css`:
grotesque (Public Sans 800) for headwords, serif for definitions — a type-specimen sheet
rather than a magazine. Public Sans is now requested as a `400..800` variable range across
all four pages to get the heavier weights.

**Contrast trap worth remembering.** The first dark-mode pass put `--ink` on the highlighter
yellow. `--ink` inverts (near-black by day, bone by night) but the yellow does not, so every
yellow surface — the quick-tag explainer, active-filter chips, `kbd`, the WOTD/playlist
banners, `.list-pub`, `.board-you` — turned into cream-on-yellow at night. Fixed with a
dedicated `--on-hl` token that stays dark in both themes; same reasoning applied to `#fff`
hardcoded on `--accent` surfaces, now `var(--on-accent)`.

**Bugs found and fixed along the way** (all pre-existing, surfaced by looking hard at every
screen):

- **`stats.php`'s entire filter strip had no CSS.** `.filter-row`, `.flabel`, `.pill`,
  `.fsep`, `.reset-btn` and the `.filter-row .tax-select` sizing existed in the markup but
  matched no rule anywhere — the page shipped with raw browser checkboxes and unstyled
  selects. Added to `app.css`, scoped under `.filter-row` specifically so `.tax-select`
  (which stats shares with the index rail's `.fs-select`) can't reach across and clobber the
  rail's `width: 100%`.
- **The filter pills' checkmark was drawn invisible.** `.fs-pill:has(input:checked) .fs-check`
  fills the box with `--bg` and the tick inside it was also `--bg`, so a ticked pill read as
  an empty pale square. Ticks are now `--text`.
- **`hx-swap-oob` was stripping a class and leaking English.** `word_list.php` re-rendered
  `#result-count` without its `.result-count` class, so the brand-bar counter lost its mono
  micro-styling on the first search; both OOB spans also appended "words" next to the
  Romanian noun already in the status bar ("25217 words cuvinte"). Now they emit just the
  number, and `#result-count` keeps its class. The list's empty state was English too.
- **Horizontal overflow on small phones.** Measured with a throwaway iframe probe at
  320/360/390/480: at 360px `.status-right` ran ~24px past the viewport and, being in a fixed
  bar, clipped silently rather than scrolling; at 320px `.brand-right` overflowed by ~21px
  because the base rule pins it to `flex-shrink: 0`, so it never narrowed enough for its own
  `flex-wrap` to engage. Fixed by letting `.brand-right` shrink on mobile and by stacking the
  status bar into two centred rows below 480px. The three magic numbers that had to agree on
  the bar's height (body padding, detail-sheet offset, toast offset) now read a new
  `--statusbar-h` token instead of each repeating `44px`/`52px`.

**Cleanup.** `setTheme`/`stepTextScale` and friends existed in three near-identical copies
(`app.js`, plus inline blocks in `joc.php` and `stats.php`) that had already started to
drift; they're now one `assets/prefs.js` linked by every page, which is also where `setSkin`
lives. `stats.php`'s status-bar links dropped their inline `style` attributes and
`onmouseover`/`onmouseout` colour-swapping in favour of the CSS that already existed.

Verified: `php -l` on all four pages, `node --check` on `prefs.js`/`app.js`, and headless
Chrome screenshots of index (cloud + detail panel open), joc and stats in beton-light,
beton-dark and paper-light, plus the overflow probe at four phone widths. The Chrome
extension wasn't available this session, so **no real-device or interactive pass was done** —
recommend a manual check of the filter drawer on touch, the feed overlay, and the two modals
(liste, clasament) in beton before merging. Non-visual UI/UX findings collected during the
pass are in `docs/BACKLOG.md` under "UI/UX findings from the beton skin pass".

---

## 2026-08-06 — Quick-tag redesign: fav / ascunde / lol / meh

Collapsed the five quick-tags (`ignore`/`boring`/`funny`/`remove`/`simple`) into four: `fav` (the existing bookmark star), `ascunde`, `lol`, `meh`. Prompted by noticing `ignore`/`remove`/`simple` all did the same job — confirmed in code that only `simple` had real backend behavior (`quiz.php` exclusion), the other three were free-form labels with no differentiated logic despite an earlier backlog note assigning them distinct meanings. Full analysis in `docs/BACKLOG.md` under "Quick-tag redesign (2026-08-06)".

- **Split into two axes**: `ascunde`+`meh` are two flavors of the same hide/quality signal (word is too common or not worth quizzing), `fav`+`lol` are the keep/vibe signal (the project's shareable-favorites hook). Renamed rather than dropped where there was a direct descendant (`funny`→`lol`, `boring`→`meh`).
- **`quiz.php`** exclusion now checks `tag:ascunde` OR `tag:meh` (was `tag:simple` only) — loops `annotated_words_subquery()` per tag and ANDs the `NOT IN` clauses.
- **Custom tag input + note textarea removed from the detail panel** (`detail.php`) per the "keep it simple for now" call — still fully functional server-side (`sync.php`, `private/app.db`) for any already-stored data, just not exposed in the UI. The now-orphaned `#tag-suggestions` datalist was also removed from `index.php`.
- **Dismissable explainer**: new `#qt-explainer` banner in `detail.php`, shown once and dismissed via `localStorage['otios.qtExplainerDismissed']` (`store.js`: `qtExplainerDismissed()`/`dismissQtExplainer()`, wired into `hydrateDetail()` and the shared click-delegation handler). Every quick-tag button also carries a `title` tooltip with the same explanation, for after the banner's gone.
- **`app.css`**: the strong red "extinct" active color (previously `remove`-only) now applies to both `ascunde` and `meh`, visually distinguishing the hide pair from `lol`'s default amber "tagged" color.

**Follow-up, same day — shortcuts remapped to `f`/`a`/`l`/`m`, star restyled.** Keyboard shortcuts changed to mirror each tag's own first letter: `f`=fav (was `b`), `a`=ascunde, `l`=lol (was `f`), `m`=meh — updated in `app.js`'s keydown handler, `_lib.php`'s `$QUICK_TAGS`, and `store.js`'s `qtKeyToTag`. This meant resolving a real collision: bare `l` was already vim-style "move right" in the word grid, checked earlier in the same keydown handler, so it would have shadowed the `lol` toggle. Fixed by dropping `l` as a grid-nav alias and keeping `ArrowRight` only — `h`/`j`/`k` remain letter shortcuts, right is now arrow-only. `index.php`'s shortcuts legend updated to match (Navigare row now shows `→` instead of `l`, with a note that `l` is freed for `lol`). Bookmark button now reads "★ fav" as a static label (`detail.php`) instead of toggling between `★`/`☆` glyphs — `hydrateDetail()` in `store.js` no longer overwrites the button's `textContent`, just toggles the `.active` class. New `--star` CSS variable (`#D4A017` light / `#F2C230` dark) colors just the star glyph via a `.fav-star` span, independent of the "fav" text and the button's existing active/hover border-and-background styling.

**Second follow-up, same day — `[f]` key badge on the fav button.** The three quick-tag buttons show their shortcut letter as a small `.qt-key` badge before the label (`[a] ascunde`); the fav button didn't. Reused the same `.qt-key` span in front of the star (`<span class="qt-key">f</span><span class="fav-star">★</span> fav`) for visual parity, and gave `#bookmark-btn` the same `display: inline-flex; gap: 4px` layout `.qt-btn` already uses so the badge/star/label space out consistently.

Verified: `php -l` on every touched PHP file, `node --check` on `store.js`/`app.js`, and a `curl` against `api/word.php?word=barabor` on a local `php -S` server to confirm the rendered panel HTML matches (buttons, tooltips, explainer markup, star and key-badge markup all present). No Chrome extension available this session for an in-browser click-through — recommend a manual pass (toggle each tag, confirm quiz exclusion, confirm banner dismiss persists across reload, confirm the yellow star and key badge render correctly in both themes) before considering this fully closed.

---

## 2026-08-05 — quiz.php: tighten reveals_word() stem match

The stem-cut in `reveals_word()` (`public/api/quiz.php`) required a candidate
token to literally start with a fixed-length prefix of the headword. That
missed Romanian's regular vowel-alternation inflections, e.g. `purcică` vs.
the idiom `purceaua de coadă` — both share the root `purc-`, but the cut used
5 characters (`purci`) while the token diverges after 4 (`purce...`), so the
question shipped with the answer's own root sitting in the correct option's
text. Replaced the fixed-length-prefix check with a common-prefix comparison
that tolerates up to ~3 trailing characters of divergence relative to the
shorter of word/token, scaling stricter for longer words. Applies uniformly
to both game modes (sense/quiz) since both route through the same
`pick_sense()`/`reveals_word()` pair — no mode-specific change needed.
Verified against the reported case plus `mătura`/`bolovan` (previously
caught) and an unrelated pair (`cartof` vs. its real definition, not
flagged) with a standalone PHP snippet — no automated test harness for
`quiz.php` exists yet.

---

## 2026-08-05 — joc.php: quality-filtered questions, multi-sense quiz, "simple" tag, in-game curation panel

The two games are also the main tool for auditing word-list quality, but the audit signal was noisy and one-way: some questions were trivially easy because the correct definition literally reused a stem of the headword (`mătura` → "...cu mătura"), `quiz.php` always used the first `|`-segment of `definition` even though DEX entries often pack several distinct senses into that column (`bolovan` has ~5, interleaved with citations), and none of the existing per-device annotation tooling (bookmark/note/`ignore`/`boring`/`funny`/`remove` tags, synced via `store.js` + `private/app.db`) was reachable from the game.

- **`api/quiz.php`** — replaced `clean_def()` with `reveals_word()` (stem-overlap check via the existing `normalize_diacritics()`) and `pick_sense()` (picks one usable, non-self-revealing sense at random from *every* pipe segment, not just the first, rejecting citations/cross-references/headers). Applied uniformly to the target and every distractor. Reworked the `RANDOM() LIMIT n` queries into over-fetch-and-filter (`LIMIT 20`, retry at `40`) since a real chunk of rows now legitimately fail the check — verified empirically (82% pass rate within the existing SQL pre-filter; 0/500 simulated `LIMIT 20` samples came up empty).
- **New quick-tag `simple`** ("too simple / not worth quizzing"), added alongside `ignore`/`boring`/`funny`/`remove` (`_lib.php`, `detail.php`, `app.js`, `index.php`'s legend/marks-filter — the last two picked it up for free since they already loop `$QUICK_TAGS`/key off `data-qtkey`). Unlike the other four (informational-only), this one is enforced: `quiz.php` excludes a player's `simple`-tagged words from their own pool via `attach_app_db()` + `annotated_words_subquery('tag:simple', ...)`, the same pattern `search.php`'s marks filter already used.
- **Word-detail panel in the game.** Moved the generic annotation-editing logic (`hydrateDetail()`, `QUICK_TAG_EMOJIS`, the bookmark/tag/note click handlers) from `app.js` into `store.js`, since it was identical logic `joc.php` now needed too — handlers look up the nearest `.word-detail-panel` ancestor instead of a hardcoded id, so the same code drives index.php's sliding panel and joc.php's pane. Guarded the handler registration on `document.body` existing, since `tests/test_store_sync.js` runs `store.js` in a Node `vm` stub without one.
- **Panel is always visible, not opened on demand** (follow-up, same day) — first shipped as a button-triggered modal, then changed to a permanent pane: stacked below the game card on mobile, a 380px side column on desktop (`≥900px`), mirroring index.php's own layout. Populated immediately in `sense`/`flash` (word known up front) or after grading in `quiz` (server withholds the answer pre-grade by design) — same security rule as before, just no button gating it.
- **Two more per-mode refinements** (same day) — in `sense` mode the pane now hides its own `.definition-text`/`.fp-nodef`, since that's the exact answer among the four choices; in `grilă` mode, a wrong guess now shows the correct word's full widget *plus* a read-only "ai ales „X”" comparison card with the definition of the word actually picked (fetched via the same `word.php` endpoint, summary text pulled out client-side rather than rendering a second full widget, which would collide on `detail.php`'s element ids).

Verified with `tests/test_game_api.js` (40-iteration streak loop confirms the over-fetch rework doesn't starve) and `tests/test_store_sync.js` (confirms the `store.js` move didn't break the vm-stub load), plus manual `curl` checks that a `simple`-tagged word stops appearing as both target and distractor.

---

## 2026-08-02 — Server-side accounts: synced annotations, graded game results, word lists, leaderboard

Everything a user produced lived in browser localStorage, so clearing a browser destroyed months of curation, and the quiz kept only `{streak, best}` — no answer log, therefore no basis for a leaderboard. Added a writable SQLite store alongside the read-only `ui.db`, with no login wall: a server-issued anonymous device token *is* the account, and a display name is asked for only when a user opts into something public.

**Storage.** New `private/app.db` (WAL, `PRAGMA user_version` migrations that run on connect, since a shared host may have no usable CLI). Kept **outside the web root** deliberately: `ui.db` is regenerated by `tools/build_ui_db.py` and re-uploaded, so user data stored there would be destroyed, and `public/data/` is directly fetchable over HTTP. Added `public/data/.htaccess` denying `.db` fetches — `ui.db` was a 20 MB open download.

- **`api/_appdb.php`** — `app_db()` (separate connection; `db()` is `query_only`), migrations, sealed tokens, rate limiting, `filter_existing_words()` so the API can't be used as arbitrary key-value storage.
- **`api/_auth.php`** — device identity. Only the SHA-256 of the token is stored, so a leaked database hands out no working sessions. `users.auth_provider/auth_subject/email` are nullable and `devices.user_id` is re-pointable, so adding Google sign-in later merges devices with no migration.

**Annotations sync (`api/sync.php`, `assets/store.js`).** Writes stay local-first — localStorage first, then a queued push — so the UI is instant and survives an outage. `store.js` also removes real duplication: `app.js` and an inline block in `joc.php` were two implementations writing the same key. One-time migration pushes existing localStorage on first load.

**Game results (`api/quiz.php`, `api/game.php`).** `quiz.php` no longer returns `answer`; options are opaque `{id, text}` and masking moved server-side. Restructuring was necessary, not cosmetic: in *grilă* the target word **is** the answer, and in *sensuri* each option carried its own `word`, so dropping one field would have hidden nothing. Every answer is appended to `game_events`; `game_stats` is a rebuildable cache.

**Lists + leaderboard.** `api/lists.php`, public `lista.php?l=<slug>` (server-rendered so links preview and work without JS), `api/leaderboard.php`, `api/profile.php`. Private lists 404 for everyone but the owner — an unguessable slug is not access control.

**Marks filter → SQL join.** The filter shipped the entire bookmark list as a `marked_words` parameter. Measured: 800 bookmarks produced a 7,352-character URL, so it would have broken outright somewhere past ~900. Now a subquery against the attached `app.db` — the same request is 32 characters. `marked_words` is still honoured before a client's first sync.

**Three bugs found and fixed while testing**, all of which would have shipped silently:

1. **Sync cursor lost edits.** `gmdate()` cannot render sub-second precision (`v` always gives `000`), so `updated_at` had 1-second resolution and the `updated_at > since` cursor skipped any change made in the same second as the previous sync. The cursor is now a per-user monotonic `seq`; wall-clock time only decides last-write-wins.
2. **Same-second edits dropped.** `clean_ts()` used `strtotime()` + `gmdate()`, truncating every client timestamp to the second — a 500 ms-later edit lost the LWW comparison and vanished. Now `DateTimeImmutable` throughout.
3. **Streak permanently zero.** PDO binds parameters as strings and SQLite evaluates `'1' = 1` as false (no affinity between two expressions), so `CASE WHEN :ok = 1` never fired while `correct + :ok` worked. Counters are now computed in PHP.

**Tests.** `tests/test_store_sync.js` runs the real `store.js` in a stubbed browser against a live server (migration, cross-device propagation, tombstones, offline queueing). `tests/test_game_api.js` covers payload secrecy, replay rejection, forged tokens and 40 rounds of counter invariants. Both need `php -S localhost:8777 -t public/`. Note: the first version of the sync test asserted only *local* state and passed while the server had silently rejected the push — bug 2 was found by adding a third clean device to verify server state.

---

## 2026-08-01 — Fix: Cmd/Ctrl+R picked a random word instead of reloading

"Each time I refresh the page I get a random word selected." The cause was not the reload path at all — the global keydown handler in `app.js` matched `e.key === 'r'` with no modifier check, so **Cmd+R** (and Ctrl+R) hit the `r` shortcut, called `e.preventDefault()`, and ran `surpriseWord()`. The page never reloaded: a random word opened and `?word=…` appeared in the address bar. Reproduced with Playwright — three Cmd+R presses gave three different words while `performance.getEntriesByType('navigation')[0].type` stayed `navigate`.

- **`app.js`** — the global shortcut handler now returns early on `e.metaKey || e.ctrlKey || e.altKey`.
- **`joc.php`** — same guard on the quiz handler, where Cmd+1…4 could answer a question.

Verified: Cmd+R no longer touches `openWord` or the URL; plain `r`, `/`, `j`/`k` and joc's `1`–`4` all still work; no console errors. Also re-confirmed the earlier reload behaviour is intact — a real reload leaves you on the plain list with a clean URL, and clicking a word still writes `?word=…`.

---

## 2026-08-01 — Joc: reverse quiz mode („sensuri"), carduri hidden

Made the game harder and more instructive by flipping the quiz: show the rare word, offer four candidate definitions. It is now the default view on `joc.php`.

- **`api/quiz.php`** — now returns `options[]` (`{word, definition}` for all four candidates) alongside the existing `choices[]` word list, so both quiz directions share one endpoint. Added `clean_def()`: keeps the first segment before `|` (DEX appends citations after pipes) and truncates at a word boundary to 200 chars. Distractors are held to the same quality bar as the target (`proper_noun_like`, `dict_count >= 3`), plus new filters that drop definitions unusable as an option — under 12 chars, bare cross-references (`vezi jeț`), truncated headers (`Compus:`) and unparsed DEX entries (`FLAIM U C sm. Tont…`). All filters test the cleaned first segment, not the raw column. Pool: 18.8k of 20.9k words survive.
- **`joc.php`** — new `renderSense()` mirroring `renderQuiz()`; reuses `maskWord()` so a definition mentioning the target can't give it away, and reuses `answer()` for scoring/highlighting, so streak and record are shared across both quiz modes. Mode is readable from `?mode=`.
- **carduri** — button removed from the mode bar; `renderFlash()`, the bookmark helpers and the flash keyboard branch are retained, reachable at `joc.php?mode=flash`.

Verified with Playwright (system Chrome): default mode, wrong/correct answer flow, keys 1–4 and Enter, streak persistence, grilă unchanged, flash mode + ★ bookmark still working, `?mode=` sync, light/dark, and no horizontal overflow at 1100px or 390px. API contract checked over 30 consecutive requests. No console errors.

**Verdict contrast** — colour alone was too subtle, so answered choices now carry ✅/❌ markers (a `::before` on the flex-row button, so the emoji sits at the top-left of multi-line definitions), a 2px inset ring on top of the border, bold text, a strikethrough on the wrong pick, and 40% opacity on the choices nobody marked. The feedback line uses the same emoji. Applies to both quiz modes.

---

## 2026-08-01 — Desktop: filters docked as a persistent left rail

The filter form was a bottom drawer at every width. On desktop that meant `toggleFilterDrawer()` locking body scroll and dimming the list behind a backdrop — you changed a pill and couldn't see the result without closing the sheet — and seven groups of controls hidden behind one button, which is bad for both discoverability and play.

- **`index.php`** — new `.layout-row` wrapper holding the filter form plus `.word-area`; the `<form id="filter-form">` moved into it, ahead of the word area. No change to the form's internals or htmx wiring: `hx-include="#filter-form"` follows the form, and `#search` binds via `form="filter-form"` from the brand bar.
- **`app.css`** — at ≥1024px the sheet becomes `position:static`, a 288px flex column with a right border, and the drawer-only chrome (drag handle, apply footer, ✕, backdrop) is hidden. Below that width, the drawer is untouched. `.rail-collapsed` animates flex-basis to 0.
- **`app.js`** — `toggleFilterDrawer()` branches on `matchMedia('(min-width: 1024px)')`: docked, it collapses the rail and persists to `otios.rail`; as a drawer, the old behaviour. A `change` listener on the media query resets state when crossing the breakpoint. New `syncFilterToggleBtn()` keeps `aria-expanded` and the button's active styling honest.
- **Play modes** — 🎲 la întâmplare and 📇 feed moved out of the sheet's last section into the brand bar, always reachable; labels collapse to emoji under 1024px. Dead `.fs-play-btn` CSS removed. 🎲 is then `hidden` pending a manual-selection design (`.play-btn[hidden]` needed explicitly, since the class sets `display`); `surpriseWord()` and the `r` shortcut still work.
- **Cuvântul zilei disabled** — `SHOW_WOTD = false` in `index.php` guards both the query and the banner markup; `openWotd`/`dismissWotd`/`initWotd` stay in `app.js`, so flipping the flag brings it back.
- **Refresh no longer re-opens the last word** — clicking a word still writes `?word=…` via `syncUrlFromForm()` (that stayed; the address bar is how you copy a link to a word). What changed is the load-time rehydrate: it checks `performance.getEntriesByType('navigation')[0].type` and, on a **reload**, clears `openWord`, strips the param and leaves you on the plain list. Following a `?word=…` link is a `navigate`, so shared links still open the panel with the param intact. (A first attempt simply stopped writing the param — wrong: it broke word-sharing *and* still re-opened the panel on refresh, just with a clean-looking URL, so the panel and the highlighted row disagreed.)

Verified with Playwright: rail docked at x=0 with the list beside it, filtering live with no scroll lock, collapse persisting across reload, feed + surprise from the brand bar, detail panel coexisting as a third column, and at 420px the drawer still opening with backdrop, scroll lock and apply button. Rail body scrolls to the explore section at 1024×760. Light and dark, no overflow, no console errors.

---

## 2026-06-26 — Beta-prep UX pass: dictionaries, play modes, design brief

A UX-polish phase to get the app ready to share with friends as beta testers. Two tracks: durable, data-backed detail features + play/exploration mechanics (built now), and a written redesign brief (handed off later). Sharing/virality infrastructure and data-quality work were explicitly deferred to their own phases.

**Detail panel (durable wins):**
- **Dictionaries-in-info**: new `sources` column in `ui.db`, merged from `data/processed/dict_sources.db` (exact + diacritic-normalized fallback, 98.2% of words matched). Added `merge_dict_sources()` to `tools/build_ui_db.py` and a one-time backfill `tools/migrate_ui_db_sources.py`. Rendered as a "📚 N dicționare" chip list in `_partials/detail.php`.
- **Synonyms placeholder**: "Sinonime: în curând" slot wired in the detail panel, ready for a future `synonyms` data source (none exists yet).
- **Larger definition box**: detail drawer raised 130px → 210px (desktop), definition bumped to 16px/1.65.
- **Shared-word focus**: opening `?word=X` now adds a `share-focus` class so the panel opens tall (50vh desktop / 80vh mobile) — the definition is the hero, the list secondary.

**Usability:**
- **Active-filter chips** (`#active-filters`): every non-default filter shows as a removable chip with an individual ✕ (plus "resetează tot"). `renderActiveFilters()` in `app.js`.
- **ignore vs remove** clarified with tooltips + shortcuts-modal copy (ignore = not interesting to you; remove = not genuinely forgotten).

**Play / exploration:**
- **🎲 surprise** (`r`): random word respecting current filters — `api/random.php`.
- **Cuvântul zilei**: deterministic daily word over a quality subset, dismissible banner, once/day via localStorage.
- **📇 feed / swipe mode**: one-card-at-a-time keep/skip explorer (keyboard + touch swipe, soft daily count) — `api/feed.php`.
- **🎮 joc** (`joc.php`): flashcards (word → reveal meaning) + multiple-choice quiz (meaning → pick the word, same-POS distractors, masked target), streak/record in localStorage — `api/quiz.php`.

**Redesign brief:** `docs/design-brief.md` — fresh-identity, mobile-first spec for a designer, covering the table view, filter-bar redesign, calmer verdict palette, play modes, and the shared-word landing state.

Verified end-to-end with Playwright (system Chrome): word list, surprise, active-filter add/remove, feed keep/advance/close, shared-word focus, and the joc flashcard + quiz flows all pass with no console errors from app code.

## 2026-06-09 — Statistics page with sliceable filters

Built a full statistics dashboard (`public/stats.php`) that mirrors the main word list's filter UI. Users can slice statistics by the same dimensions: tier, POS, register, domain, etymology, dict_count, definition status, and DEX frequency ceiling (rare tab).

- **Refactored filter building**: Extracted `build_word_filter()` helper in `_lib.php` — shared by both `search.php` and the new `stats.php`, eliminates duplication and maintenance risk.
- **`parse_multi()` + `split_pipe()` helpers**: Moved to `_lib.php`, handle multi-value checkbox arrays (tier[], pos[]) and pipe-delimited fields (etymology, register, domain, POS).
- **API endpoint (`api/stats.php`)**: Single SQL scan per word, PHP-side aggregation: counts by confidence_tier (GROUP BY), then counts by etymology/register/domain/POS (split pipes, frequency maps). Generates top-15 etymologies, top-10 domains, all registers, top-8 POS.
- **Stats panels (`api/_partials/stats_panels.php`)**: HTML-only bar charts, inline `width: X%` styling, no JS library. Shows summary strip (total, definition coverage %), then 5 cards: etymology (full-width 2-column), tier, POS, register, domain — all color-coded per verdict/category.
- **CSS**: New `.stats-*` classes, grid layout for panels, mobile collapse of 2-column etymology to 1 on narrow screens.
- **Filter form**: Reuses the same tier/POS checkboxes, register/domain/etymology/dict_min selects, dex_max (rare-only). Inline JS handles DEX-rare visibility, tax-select active highlight, and form reset re-dispatch.
- **Navigation**: "📊 statistici" link in status bar, back-link ("← cuvinte") from stats page.

No changes needed to existing `search.php` behavior — all filter logic is now centralized in `build_word_filter()`.

## 2026-06-09 — Filter dedup, dict_count filter, URL deep-linking

- **Removed verdict pills** (extinct / declining / historical / absent) — they duplicated the tier labels (corp. extinct / corp. declining / corp. historical) since `confidence_tier` is derived from `verdict`. Tier is more informative (adds `dex. absent` path) so it's the one to keep.
- **Added missing `dex_absent_highfreq` tier** — 3,848 words had no tier pill to filter them until now.
- **`dict_count` filter** — new "dicts: any / ≥3 / ≥6 / ≥10 / ≥15" select in filter row 3. Filters `dict_count >= N` in SQLite. Works as a quality gate: words attested in more dictionaries are more firmly established.
- **URL deep-linking** — `applyUrlToForm()` reads `?q=&tier=&sort=…` on page load and pre-selects filters before HTMX fires its initial request. `syncUrlFromForm()` updates the URL (via `history.replaceState`) on every HTMX search, so every filter state is bookmarkable and shareable. Default values are omitted from the URL to keep links clean.

## 2026-06-09 — Reversible DEX-rare filter on the rare tab (Phase 1)

The rare tab still showed everyday words (credit, ecran, universitate, ceapă…). Root cause: the `rare_in_use` gate has no rarity requirement — it admits any `zipf ∈ [3.0, 4.5)` word with an archaic register tag, and DEX register tags are per-*headword*, so `învechit` fires on a long-dead *sense* of a common word. 112 of the 113 rare words are DEX `rarity_category = "standard"` (96% have `dex_frequency ≥ 0.80`).

Phase 1 (reversible, no pipeline re-run): added a `dex_max` filter to the PHP UI, scoped to the rare tab. `public/api/search.php` applies `dex_frequency BETWEEN 0.01 AND <ceiling>` only when `word_tier = rare_in_use` (0.01 floor drops `frequency = 0` missing data). `public/index.php` adds a select (DEX: all / ≤0.60 / ≤0.50 / ≤0.30, default ≤0.60); `public/assets/app.js` shows it only on the rare tab. Default ≤0.60 collapses the rare tab to **1 word (`listat`)** — confirming the pool is ~entirely DEX-standard and that a useful rare tier needs re-sourcing (Phase 2: rarity-first gate in `validate_with_wordfreq.py`, drop the archaic requirement, lower zipf ceiling 4.5→3.5, drop English loanwords). See plan `rare-list-still-shows-lucky-mitten.md`.

## 2026-06-07 — Archive dead MySQL→SQLite scripts (backlog #3)

`extract_lexemes.py` is the only MySQL→SQLite path wired into the canonical pipeline. Moved the two abandoned alternatives — `mysql_to_sqlite.py` (silently swallows AUTOINCREMENT errors) and `convert_to_sqlite.sh` (mishandles multi-line MySQL directives) — into a new `archive/` directory with a `README.md` warning not to run/import them. Confirmed no script imports either (only self-references + docs). Updated the CLAUDE.md gotcha. `docs/scripts-guide.md` still lists `mysql_to_sqlite.py` as an "alternative" — flagged in BACKLOG for a separate docs pass.

## 2026-06-07 — De-pollute the `rare_in_use` tier (archaic register gate + dedup)

Addressed the bulk of the "rare_in_use tier is polluted by modern loanwords + proper nouns" bug in `validate_with_wordfreq.py` (pipeline options (a) + (d)).

- **(a) Archaic register gate.** Added `ARCHAIC_REGISTER_MARKERS` (`învechit`, `arhaizant`, `rar`, `ieșit din uz`) + `has_archaic_register()`. The `rare_in_use` gate previously admitted any word with a *non-empty* `dex_register` — including stylistic tags (`figurat`, `popular`, `familiar`, `livresc`) that everyday loanwords carry. It now requires an archaic/rare marker. New `--rare-register {archaic,any}` flag (default `archaic`; `any` = legacy). Effect on the current curated CSV: `rare_in_use` 582 → 113; `screening`/`meeting`/`house`/`jonathan`/`sioux`/`zulu`/`viking` removed.
- **(d) Dedup by `word_no_accent`.** New `--dedup` (default on) keeps the first row per normalized headword, collapsing POS duplicates (`house` s.n. + adj.). Dropped 10,133 duplicate rows on the current input; surfaced in the run summary.
- **Verification.** `has_archaic_register()` unit-checked; ran new vs `--rare-register any --no-dedup` (legacy) side by side to confirm the 582→113 delta; spot-checked that 14/15 backlog noise words are gone. Residual noise is now sense-level homograph mismatches (`cannabis`/`spray`/`court`/`hagi` tagged `învechit` on a non-modern sense) — caught today by the UI `hide_loanwords`/`hide_proper` toggles; options (b)/(c) intentionally remain reversible UI toggles.
- No `data/` artifacts regenerated (verified via /tmp outputs); takes effect on next `validate_with_wordfreq.py` run.

## 2026-06-07 — Flag "[Fără definiție.]" placeholder entries (backlog #17)

Closed the remaining gap in #17. The `has_definition` column already existed (in `forgotten_words_diachronic.csv` and the UI), and DEX headwords with no extractable definition already showed `has_definition=0` by being absent from `definitions.db`. The leak: dexonline's "[Fără definiție.]" placeholder rows (entry exists, only usage citations follow) counted as real definitions.

- **`validate_diachronic.py`** — added `is_placeholder_definition(text)`: placeholder when text is missing/blank or "[Fără definiț…" *leads* the string. `_load_definition_words()` now excludes those, so the CSV `has_definition` is accurate. Mid-text placeholders in multi-sense words (`perină`, `spectacul`) correctly still count.
- **`ui/app.py`** — definition load skips placeholder rows (matching inline check) so the `has_def` filter (`definition IS NULL`) and the panel text agree; placeholder words still appear in the list and link out to dexonline.
- **Scale / verification** — predicate unit-checked (None/blank/leading/embedded/normal); against the live `definitions.db` (70,472 rows) it flags exactly 7 placeholder-only words: `animaltecă`, `apastop`, `fibrinactiv`, `magnetodiaflux`, `narcorublă`, `perfluorbutilamină`, `relin`. Both modules import cleanly. No `data/` artifacts regenerated — takes effect on next `validate_diachronic.py` run / `ui.db` rebuild.

## 2026-06-07 — Centralize frequency thresholds in `constants.py` (backlog #5)

Resolved the long-standing three-way disagreement on frequency bins (CLAUDE.md gotcha + BACKLOG #5).

- **New `constants.py`** — single source of truth: `MIN_FREQUENCY` (0.01) and `MIN_FORM_LENGTH` (3) shared across stages; canonical rarity-bin edges `VERY_RARE_MAX` (0.30) / `RARE_MAX` (0.50) / `UNCOMMON_MAX` (0.60) plus a `rarity_category(freq)` helper; per-stage candidate ceilings `CURATED_FREQ_CEILING` (1.0) and the explicitly-marked legacy `ANALYZE_FREQ_THRESHOLD` (0.70) / `VALIDATION_FREQ_CEILING` (0.60).
- **`create_curated_list.py`** (canonical) — candidate WHERE clause now parameterized from constants; the two duplicated inline binning blocks (categorization + CSV write) both collapse to `rarity_category()`.
- **`analyze_forgotten_words.py`** / **`validate_forgotten_words.py`** (legacy) — import their floors/ceilings instead of hardcoding. Legacy display histogram bins left script-local (coupled to the 0.70 candidate threshold; documented as intentional in `constants.py`).
- **Verification** — `rarity_category()` matches the old inline logic at every boundary (0.0/0.01/0.29/0.30/0.49/0.50/0.59/0.60/0.99); all four modules import cleanly. No `data/` artifacts regenerated — behaviour is unchanged, so existing CSVs remain valid.

## 2026-05-28 — Richer detail panel + reversible UI filters for triage

Follow-up to the rare-tab diagnosis: rather than baking filters into the pipeline, surface all
per-word evidence in the UI and add reversible filter knobs so the data can be explored before
committing to any permanent filter.

- **New `extract_dict_sources.py`** — streams the DEX dump (mirrors `validate_diachronic.py::_load_dict_counts`), joining `Definition.sourceId → Source.shortName` to record the *names* of the dictionaries each headword appears in. Output `data/processed/dict_sources.db` (`dict_sources(word, sources, dict_count)`). Full run: 301,439 headwords, 113 sources (e.g. `meeting` → DEX '98|DLRLC|Scriban|Șăineanu; `criptare` → Neoficial).
- **`ui/app.py::load_words`** — added a `_enrich_words()` pass: wordfreq Zipf for `ro` and `en` (recomputed uniformly; also restores the rare tier's zipf, which the CSV load drops), a `proper_noun_like` flag recovered from `lexemes.db` casing (the CSVs are lowercased, so the old `word[0].isupper()` filter was dead), and `dict_sources` joined by normalized headword. New columns: `zipf_frequency`, `en_zipf`, `proper_noun_like`, `dict_sources`.
- **Detail panel (`partials/detail.html`)** — now shows zipf / en / dex band alongside hist/mod/sub/ratio, the dictionary-names list, web-validation signals (score/results/in-wild/provider/last-seen/top-url), and a proper-noun flag. The DEX-frequency superscript (the small number on each grid word = `dex_frequency × 100`) is now also rendered next to the word title in the panel.
- **Legend popup (`base.html`)** — an "ⓘ legend" footer link opens a glossary modal (modeled on the shortcuts overlay) explaining every number and tag: the superscript/DEX band, zipf, en, hist/mod/sub/ratio, dict-count + source short-names, web signals, verdicts, and common DEX register tags.
- **Four reversible filters** (`/search` + `base.html` row 4): zipf range, DEX-frequency range, hide-likely-loanwords (`en_zipf ≥ LOANWORD_EN_ZIPF`, default 4.0), exclude proper-noun-like. Server-side, applied only when present, preserved across pagination.

Verified end-to-end (curl + browser screenshot): `hide_loanwords` drops `meeting`/`house`, `hide_proper` drops `jonathan`, `zipf_max=3.0` narrows to sub-floor words; detail panel renders all signals. No `data/` artifacts regenerated. wordfreq import is optional (graceful degrade).

---

## 2026-05-28 — Diagnosed rare-tab pollution (no code changes)

Investigated why the UI "rare" tab (`?word_tier=rare_in_use`) shows non-rare words: English loanwords (`screening`, `meeting`, `house`, `short`, `golden`, `dolby`, `wild`, `trend`), variety/brand names (`jonathan`), and proper nouns (`sioux`, `zulu`, `hagi`, `viking`).

Root cause: the `rare_in_use` tier rests on two failing signals. (1) Low DEX `frequency` is editorial-coverage, not corpus frequency, so recent borrowings sit in the `0.01–1.0` candidate band (`create_curated_list.py:127-129`) while still being everyday words. (2) The register gate in `validate_with_wordfreq.py:151` admits a word on `zipf < 4.5 AND dex_register non-empty` — *any* tag — but of 582 rows in `rare_words_wordfreq.csv` only ~124 are `învechit`; the rest are stylistic tags (`figurat`, `popular`, `familiar`, `livresc`) that colloquial loanwords carry. Compounding: no loanword filter, a dead proper-noun filter (`create_curated_list.py:69-72` checks `word[0].isupper()` on lowercased data), homograph mismatches (`cannabis`/`listat`→`învechit`), and 28 duplicate rows.

Diagnose-only at the user's request; logged as a Bugs/Known-Issues entry in `docs/BACKLOG.md` (sharpens enhancement #12) with fix options for later.

---

## 2026-05-28 — Lemma dedup in shortlist (backlog #6)

Added simplemma-based inflected-form deduplication to `make_shortlist.py`. After the classification loop, each word is lemmatized via `simplemma.lemmatize(word, lang='ro')` and grouped by lemma. Groups with multiple shortlist entries keep one canonical representative (the word whose form equals the lemma, else the highest-tier/highest-dex_frequency entry); the rest are dropped. Added `--no-dedup` flag to opt out.

Result: 1,571 inflected forms collapsed, shortlist 26,788 → 25,217 words. Concrete improvements: `abecedare` dropped (→ `abecedar` kept); `murea` dropped (lemma `muri` not in shortlist, so it was alone in its group and correctly removed).

Known remaining gap: simplemma does not reduce Romanian verb-derived nouns or participial adjectives (`bleui`/`bleuire`/`bleuit` stay as three separate entries). Corpus-level lemmatization (so `buclele` counts toward `buclă`) remains outstanding.

Rebuilt `tools/build_ui_db.py`: 25,685 words in `ui.db`.

---

## 2026-05-28 — Data audit: corpus merge, Tier A guards, register filter cleanup

**Corpus merge:** Fresh CulturaX run from VPN contained only `culturax_ro` (122,463 words). Merged `wikisource_ro` (45,218 words) and `subtitle_ro` (29,733 words) from the previous complete DB into the new `corpus_frequencies.db`. All three corpora now present and correct.

**Tier A common-word guards (`make_shortlist.py`):** Tier A (`corpus_extinct`, `corpus_declining`, `corpus_historical_only`) now requires two additional conditions: `modern_ppm <= 5.0` (word is not still actively used in modern text) and `dex_frequency < 1.0` (not DEX core vocabulary). Without these guards, words like `lui` (2,750 ppm), `casă` (200 ppm), `dumnezeu` (562 ppm), `miel` (10 ppm) were passing because Wikisource (19th-century literary) simply uses these proportionally more than modern web text, triggering a "declining" verdict. 612 words removed from Tier A (993 by ppm, 133 by dex_frequency, some overlap). New `TIER_A_MODERN_PPM_MAX = 5.0` constant at module level. Legitimate archaic words in the 1–5 ppm range (e.g. `dară` 1.2 ppm, `sosi` 4.97 ppm `rar|învechit`) are kept.

**Register dropdown cleanup (`tools/build_ui_db.py`, `ui/app.py`):** Added `_REGISTER_USAGE_NOTES` exclusion set (39 tags) shared between both apps. DEX register tags that describe usage style (`figurat`, `popular`, `familiar`, `metaforic`, `în comparații / la comparativ`, `ironic`, `argou`, etc.) are excluded from the register filter dropdown. The `dex_register` column in the DB is unchanged — these tags are still available as metadata on each word, they just don't appear as filter options. Register dropdown reduced from 52 noisy values to 17 true archaic/regional markers: `învechit`, `regional`, `rar`, `livresc`, `Moldova`, `ieșit din uz`, `arhaizant`, `Țara Românească`, `Transilvania`, `Țările Române`, `dialectal`, `Bucovina`, `Muntenia`, `Banat`, `Maramureș`, `Oltenia`.

**Pipeline rebuilt:** `validate_diachronic.py` → `make_shortlist.py` → `tools/build_ui_db.py`. Shortlist: 26,788 words (was ~27,400 before guards). Verified: egregious common words gone, `oțios`/`tibișir`/`eleșteu` present, register dropdown clean.

**Remaining 260519 audit items (not tackled today):**
- Inflected/derived forms as separate entries (bleuit/bleuire/bleui, murea, abecedare) — requires lemmatization (backlog #6).
- Missing definitions for feminine forms and spelling variants (mofluzită, cfartal etc.) — separate investigation needed.
- `Maramureș` on `biodiversitate` — likely taxonomy artifact; re-check after pipeline rerun.

---

## 2026-05-27 — Regex fix, dead code removal, BACKLOG housekeeping

Fixed dead regex in `create_curated_list.py:80`: `r"^[a-z]+-[a-z]+'"` had a trailing apostrophe that caused the hyphenated-word filter to match zero words. Removed the apostrophe so compound/multi-word entries (chaise-longue, mai-mare, calea-valea, etc.) are now correctly excluded from the curated candidate list. Re-ran pipeline (`validate_diachronic.py` → `make_shortlist.py` → `build_ui_db.py`).

Deleted `explore_dex.py` (dead code: connects sqlite3 to a `.sql` file; content is narrative documentation, now redundant with `CLAUDE.md`).

Marked completed BACKLOG items: regex typo, #4 (explore_dex.py), #20 (OOB swap for stale overlay), #21 (dict_count).

---

## 2026-05-27 — Type-ahead word navigation; annotation overflow cap

**Type-ahead navigation:** Pressing any unbound printable character (when not focused on an input) accumulates in a 1.2s buffer and jumps to the first visible word whose text starts with the buffer (diacritic-insensitive: ț→t, ș→s, ă→a, â→a, î→i). Multi-character sequences narrow the match. Documented in the shortcuts modal as "a–z: jump to matching word".

**Annotation overflow cap:** Words with 4+ emoji annotations (quick tags + note + bookmark) now cap at 3 emoji + a muted "+N" superscript. Template refactored from string concatenation to a `_ov.items` list, sliced at [:3].

---

## 2026-05-27 — Definition hover tooltip in word grid

Added a lightweight hover tooltip to word chips in the grid. The `data-def` attribute was already populated (first 120 chars of definition) on each `.word-row`. A single floating `#def-tip` div is appended to `<body>` and shown/hidden via `mouseover`/`mouseout` delegation on `#word-list-container`. Positioned below the chip; flips above if within 120px of viewport bottom. No network requests. Tooltips also work after HTMX-loaded pages.

---

## 2026-05-27 — Garbled definitions fix, rar/regional/ieșit-din-uz taxonomy tags

**Garbled definitions fix:** Root cause: `_parse_values` in `extract_definitions.py` handled `\'` and `\\` but not `\n`/`\r`/`\t` — these appeared as literal `n` + surrounding dump indentation spaces (e.g. `"Acțiunea den       a ( se ) abaten         n       și rezultatul ei."`). Fix: complete escape table in the parser + `re.sub(r'\s+', ' ', ...)` whitespace normalization in `_clean`. Re-ran `extract_definitions.py` (50,678 headwords from DefinitionSimple) then `scrape_definitions.py --merge-only` (19,835 scraped rows on top). Garbled count in `definitions.db`: 3,152 → 0.

**New register tags — rar, regional, ieșit din uz:** Three semantically important DEX tags (ids 6, 17, 239) have `parentId=0` (root level) and were silently missed by `load_taxonomy()` which filtered only `parentId IN (1, 41, 42)`. Extended the SQL `WHERE` clause and `parent_to_family` map to include them and their children (Banat, Moldova, Transilvania, etc. as sub-tags of `regional`). Result in register vocab: `regional` 3,202 words, `rar` 2,463, `ieșit din uz` 95. All now available in the register filter dropdown. Re-ran full pipeline: `validate_diachronic.py` → `make_shortlist.py` → `build_ui_db.py`.

---

## 2026-05-27 — Definition scrape completion, dictionary coverage count (#21)

**Definition scrape completion:** Pass 3 scraped 21,110 words (started 26 May, finished overnight). Merged 19,157 ok rows into `definitions.db`. Rebuilt `ui.db` → 26,279 words now have definitions.

**Dictionary coverage count (`dict_count`):** New field counts how many distinct DEX source dictionaries contain a headword. Extracted from `Definition.sourceId` in the MySQL dump via a new `_load_dict_counts()` function in `validate_diachronic.py` (streams 125 INSERT lines, ~12s). Propagated through the full pipeline: `validate_diachronic.py` → `make_shortlist.py` → `build_ui_db.py` → `ui/app.py` (in-memory schema + INSERT) → `detail.html` (`dicts N` stat chip). Range: 0–47 dicts per word (e.g. `oțios` → 11, `arie` → 28). Rebuilt `ui.db` with new shortlist.

---

## 2026-05-23 — Corpus refresh: subtitle corpus, Wikisource re-run, CulturaX merge, subtitle signal in diachronic

**Definition scrape completion:** Ran two-pass scrape (`scrape_definitions.py --merge` then `--retry-not-found`). Pass 1: 1,810 new definitions from 1,839 unchecked words. Pass 2: 5 more recovered. Definition coverage: 98.5% for forgotten tier (was ~79%). Rebuilt `ui.db`.

**Subtitle corpus (`process_subtitles.py`):** New script streams `dex-database.sql` for `Subtitle` INSERT rows (13.2M pre-tokenised tokens from 966 Digi24 YouTube clips). Filters against `load_dex_words()`, writes to `corpus_frequencies.db` under `corpus_name='subtitle_ro'`. 29,733 unique DEX forms found. Runs in ~13s locally.

**Wikisource re-run:** Wiped stale `wikisource_ro` data and re-ran `process_wikisource.py` with the corrected `load_dex_words()` filter (141k lookup forms vs 16k before). Found 45,218 unique forms (up from 44,756 — small delta confirms new words are modern vocabulary absent from 19th-century literary text, as expected). Fixed cosmetic display bug: progress line printed `len(word_counts)+1` after flush had already cleared the dict; now captures count before flush.

**CulturaX re-run (VPS):** Re-ran `process_culturax.py` on VPS with corrected filter. Uploaded `lexemes.db` (91 MB); pulled updated `process_culturax.py` via git. Result: 122,463 unique words, 40.3M docs, completed. Downloaded `corpus_frequencies2.db`, merged only `culturax_ro` rows into local DB (preserving fresh wikisource + subtitle data), deleted temp file.

**Pipeline rebuilt:** `validate_diachronic.py` → `make_shortlist.py` → `build_ui_db.py`. Shortlist grew from 23,112 → 27,410 words (+4,300 with real CulturaX signal). `ui.db`: 27,829 words, 17.6 MB. `fost` correctly absent from results now.

**Subtitle signal in diachronic:** Added `subtitle_ppm`, `subtitle_occurrences`, `subtitle_documents` columns to `validate_diachronic.py` output, passed through `make_shortlist.py` and `build_ui_db.py`. 8,737 shortlist words have subtitle signal — identifies words forgotten in written text but surviving in broadcast Romanian.

---

## 2026-05-21 — Diacritic-insensitive search in Flask and PHP apps

Added `word_normalized` column (ț→t, ș→s, ţ→t, ş→s, ă→a, â→a, î→i) to the words table in both the Flask in-memory DB and the PHP on-disk DB. Searching "otios" now finds "oțios"; "stramosesc" finds "strămoșesc". Both the normal word-list search and the audit-mode search respect the normalized form. PHP app updated in `_lib.php` (`normalize_diacritics()`) and `public/api/search.php`. Flask app updated in `ui/app.py` (`_strip_diacritics()`, registered as a SQLite custom function). `tools/build_ui_db.py` updated to populate the column and add an index.

---

## 2026-05-21 — Audit pipeline: stratified sampling, labeling UI, report

Added a full data-quality audit workflow to measure shortlist precision and recall across strata.

**`audit_sample.py`** — draws a stratified random sample (default 100 words/stratum) from all 10 strata: included tiers (tier_a_extinct, tier_a_declining, tier_a_historical, tier_b_invechit, tier_c_absent_highfreq, rare_in_use) and excluded buckets (excl_pos, excl_absent_lowdex, excl_stable_emerging, excl_other). Sample stored in `data/research.db:audit_sample`. CLI: `--n`, `--seed`, `--reset`, `--strata`, `--stats`.

**`audit_report.py`** — aggregates `audit:*` tags from labeled words into a stratum × label markdown table (`docs/audit/YYYY-MM-DD-summary.md`) and per-cell word lists (`data/audit/<stratum>_<label>.txt`). Counts `keep`, `inflection`, `variant`, `loanword`, `dialect`, `jargon`, `no_def`, `other` for included tiers; `keep`/`correctly_out`/`no_def`/`other` for excluded buckets. Coverage table shows labeled/total per stratum.

**Flask audit mode** (`?audit=1`) — orange audit bar replaces the normal filter row with 10 stratum radio-pills (A·extinct, B·invechit, ✗·pos, etc.) each showing labeled/total progress. Selecting a stratum scopes the word list to that sample; unlabeled words sort first. Detail panel gains a row of one-key verdict buttons: K/I/V/L/D/J/M/O for included strata, K/X/M/O for excluded. Keyboard shortcuts fire via `htmx:configRequest` injection of `?audit=1` on every `/word/` request. After each label, auto-advance moves to the next unlabeled word and refreshes the stratum counter via `/audit/strata`. Words from excluded strata (not in the shortlist) are pulled from `forgotten_words_diachronic.csv` at startup so the detail panel doesn't 404. Audit tags are stored in `bookmarks.tags` as `audit:*` entries and are filtered out of the normal tag display.

---

## 2026-05-19 — Add Tier C to shortlist; fix rare list quality

Two pipeline fixes to address the 260519 Data Audit:

**Tier C — `dex_absent_highfreq`** added to `make_shortlist.py`. Captures words that are fully absent from all corpora (`hist_ppm=0`, `modern_ppm < 0.1`) but are well-documented in DEX (`dex_frequency ≥ 0.85`). These are the "most forgotten" words — DEX-canonical but never seen in digitised text. Threshold was initially set at 0.70 (too many inflected/derived forms: ~20k words), then tuned to 0.85 (~3,332 words). oțios (dex_frequency=0.85) is right at the boundary and now appears in the UI. New CLI args: `--absent-ppm-threshold` (default 0.1) and `--dex-freq-threshold` (default 0.85). Sort key shared with Tier B: by dex_frequency descending.

**Rare-in-use filter** tightened in `validate_with_wordfreq.py`: `rare_in_use` classification now requires non-empty `dex_register`. Words with Zipf 3.0–4.5 but no register tag (modern unmarked vocabulary like `neurologie`, `cowboy`, `manipulat`) fall through to `common` and are excluded from both output files. Rare list: 11,668 → 469 words.

Pipeline rebuilt: shortlist 19,780 → 23,112 forgotten words (Tier A: 16,786, Tier B: 2,994, Tier C: 3,332) + 469 rare-in-use. DB: 23,581 words total.

---

## 2026-05-19 — Add forgotten/rare-in-use toggle to both Flask and PHP apps

Added a segmented `uitate | rare` toggle to both UIs, backed by a new `word_tier` column in `ui.db`.

**`tools/build_ui_db.py`**: loads `forgotten_words_shortlist.csv` with `word_tier='forgotten'` and `rare_words_wordfreq.csv` with `word_tier='rare_in_use'`; adds `word_tier TEXT DEFAULT 'forgotten'` column and `idx_words_word_tier` index; DB grew to 28,447 words (19,780 forgotten + 8,667 rare at the time).

**`public/api/search.php`** and **`public/index.php`**: `word_tier` filter applied to every query (allowlisted: `forgotten`/`rare_in_use`); segmented radio toggle in Row 1 of the filter bar; initial status-bar count uses `WHERE word_tier='forgotten'`.

**`ui/app.py`**: same changes mirrored — `load_words()` accepts `rare_path`; `/search` validates and applies `word_tier`; in-memory schema includes `word_tier`.

---

## 2026-05-19 — Add rare-in-use word tier to wordfreq validation

Extended `validate_with_wordfreq.py` with a three-tier Zipf classification alongside the existing binary forgotten/not-forgotten output.

**New `tier` column:** `forgotten` (zipf < 3.0) / `rare_in_use` (3.0 ≤ zipf < 4.5) / `common` (≥ 4.5). The existing `is_forgotten` bool is preserved for backward compatibility with `search_wild.py` and `build_ui_db.py`.

**New CLI args:** `--upper-threshold` (default 4.5) and `--output-rare` (default `data/processed/rare_words_wordfreq.csv`). In default mode the script produces two output files — the existing forgotten-words CSV (127,886 rows) and a new rare-in-use CSV (11,668 rows). `--keep-all` writes all tiers to the main output as before.

Calibration: `oțios` itself has zero corpus signal (zipf=0.000) so it lands in `forgotten`, not `rare_in_use`. The rare-in-use tier catches words like `bucle` (zipf 3.42) that do still appear in Romanian text but very infrequently.

BACKLOG item (line 208) marked resolved on the pipeline side; UI global switch (browse forgotten vs rare-in-use list) remains open.

---

## 2026-05-19 — Data audit: missing definitions root cause + scraper fallbacks

Investigated the Data Audit backlog item: 4,065 shortlist words (20.6%) had no definition in `ui.db` despite dexonline.ro having entries for them.

**Root causes found:**
- **2,703 words** never attempted — scraper was run with `--limit` or interrupted before reaching them. All tested examples (`mofluzită`, `ospătător`, `aeresc`, `cfartal`, `prijuni` etc.) parse fine with the existing synthesis selector; they just need a scrape run.
- **1,370 words stuck as `not_found`** — scraper ran but found no synthesis. Sampling showed ~95% have no `.tree-body` in `#tab_2` (dexonline hasn't curated a synthesis for them yet), while ~5% are inflected/derived forms where dexonline explicitly says "Nu avem definiții" for that form.
- **Side issue**: 3,530 words were flagged `has_definition=0` in the shortlist but had actual definitions in `definitions.db` — the flag was stale.

**Fixes in `scrape_definitions.py`:**
- `parse_tab0_defs(html, word)` — fallback for the ~95% case. Scans `#tab_0 .defWrapper` entries, matches headwords case-insensitively (handling per-character span markup and stress-accent diacritics like `márgă` → `margă`), returns first 3 matching raw-dictionary definitions.
- `parse_lemma_fallback(word, defs_db)` — fallback for inflected forms. Lemmatizes via `simplemma('ro')` and looks up the base form's definition in `definitions.db`. Prefixes the result with `[formă a lui {lemma}]`.
- `--retry-not-found` flag — re-queues `not_found` checkpoint entries without wiping the full checkpoint.

**Fix in `tools/build_ui_db.py`:** after merging definitions, reconciles `has_definition` to reflect actual definition presence.

**Next:** run `python scrape_definitions.py --delay 2.0 --merge` (pass 1, 2,703 words) then `python scrape_definitions.py --retry-not-found --delay 2.0 --merge` (pass 2, 1,370 words), then rebuild `ui.db`.

---

## 2026-05-19 — PHP thin-API port for shared hosting

Ported the Flask research UI to a PHP + SQLite stack deployable on any shared host. Flask app is kept intact for local pipeline work.

- **`tools/build_ui_db.py`** — one-shot build script that merges `forgotten_words_shortlist.csv` + `diachronic_shortlist_web_validated.csv` + `definitions.db` into `public/data/ui.db` (~11 MB). Adds a `vocab` table for dropdown options and four search indexes.
- **`public/api/search.php`** — port of Flask `/search`. Marks filter is now client-driven: JS sends `marked_words` (comma list from localStorage) so the server does `WHERE word IN (…)` / `NOT IN (…)` without touching any server-side user state.
- **`public/api/word.php`**, **`_lib.php`**, **`_partials/`** — word detail endpoint, shared PDO helpers, PHP equivalents of the three Jinja partials.
- **`public/assets/app.js`** — localStorage research store (`otios.research` key); `hydrateRows` / `hydrateDetail` run on `htmx:afterSwap`; bookmark/tag/note handlers replace the five dropped HTMX POST routes; keyboard shortcuts retargeted at localStorage; `htmx:configRequest` hook injects `marked_words` before search requests.
- **`public/assets/app.css`** — extracted verbatim from `base.html`.
- **`public/index.php`** — page chrome with server-rendered vocab dropdowns; bookmark count filled by JS.
- **`public/metodologie.html`** — static copy.
- **`tools/export_research_to_json.py`** — dumps `data/research.db` to the localStorage JSON shape for one-time console import.
- Verified locally: word grid, search, live filter, detail panel, bookmark/tag/note (localStorage), marks filter, infinite scroll, zero console errors.

---

## 2026-05-19 — Marks filter + annotation overlay + UI refinements

Unified annotation filtering and word-chip decoration in the research UI.

- **`marks` dropdown.** Replaced the `show_removed` pill + `bookmarked` checkbox with a single `<select name="marks">`. Options: `all words` (default), `unmarked only`, `marked only`, `☆ bookmarked`, `has note`, and one entry per quick-tag. Backend: new `_is_marked()` helper; flat filter chain handles each variant. Default changed from `unmarked` → `all`.
- **Emoji overlay on word chips.** Each chip now shows a compact emoji badge (`ann-overlay`) assembled by a Jinja2 namespace accumulator: per-tag emoji from `QUICK_TAG_EMOJIS`, `📝` if has note, `⭐` if bookmarked. `w.tags` list (from `bmap`) replaces the old `has_tags` bool.
- **Suppress active-filter emoji.** In `bookmarked` mode the `⭐` is hidden on every chip (it's redundant — the filter already guarantees they're all bookmarked). Same for `📝` in `noted` mode and the relevant tag emoji in `tag:X` mode. Implemented via `suppress_emoji` template var and `| default('')` guard.
- **`.flabel` inverted.** Filter labels now render as dark pills (`color: var(--bg); background: var(--text-2)`) so they read as labels, not body text.
- **Metodologie footer link.** Status bar now includes an `<a href="/metodologie">` link. Template moved from `ui/metodologie.html` → `ui/templates/metodologie.html` (Flask template resolution fix).
- **BACKLOG.** Added #19 (overlay overflow for 4+ emoji), #20 (stale overlay after in-panel mutations — needs htmx OOB swap).

---

## 2026-05-18 — UI polish pass v4 (typography + verdict palette + interaction states)

Second, deeper UI revision after the morning's fine-tuning pass. Brainstormed direction with the visual-companion server, picked **Tool** over Publication. Spec at `docs/superpowers/specs/2026-05-18-ui-polish-pass-design.md`.

- **Typography.** Inter Tight → Mona Sans (variable). Word weight 700→600, size 19→18px, tracking `-0.02em`→`-0.005em` so Romanian diacritics (ț, ș, ă) breathe. Lora kept as italic accent on the filter label + placeholder. JetBrains Mono kept.
- **Color tokens.** Warm off-white ground (`--bg #fcfbf7`, `--surface #fdfcf9`, `--border #ece6d6`). Verdict palette flipped from "four equal-saturation colors" to **one hero, three muted**: `--v-ext` cleaner red `#b91c1c`, the other three become charcoal-with-hue (`--v-dec #524035`, `--v-hist #3d4763`, `--v-abs #4b3d5a`). Extinct now reads first; the eye explores from there.
- **Density.** Grid `column-gap: 9px; row-gap: 9px; padding: 11px 13px`; word-row padding `1px 5px 2px`. Denser than the morning pass but still readable.
- **Hover.** Cool blue tint `rgba(214,230,255,0.9)` + 1px inset border, hugs the word.
- **Selected.** `transform: scale(1.06)` lift, dark-charcoal 90%-opacity bg, subtle two-layer shadow, `z-index: 5`. Neighbors don't reflow — one unambiguous "this is selected" signal replaces the old verdict-tinted bg + outsized shadow combo.
- **Critical CSS fix.** Grid items default to `justify-self: stretch`; added `justify-self: start` on `.word-row` so hover/selected boxes hug the word's width instead of stretching to the cell.
- **Stripped chrome.** Removed `body::before` top accent stripe (advertised the palette we're toning down). Status bar's 8-kbd inline legend collapsed to `<kbd>?</kbd> shortcuts` (modal already exists).

Verified in browser: Mona Sans 600/18px on warm ground, `transform: matrix(1.06,…)` + `background: rgba(26,24,18,0.9)` on selected, hover box ≈ word width.

## 2026-05-18 — UI word-grid fine-tuning

Polished `ui/templates/base.html` + `ui/templates/partials/word_row.html` to fix visual noise in the word list. No structural changes — same routes, markup shape, keyboard shortcuts.

- **Grid breathing room.** `gap: 3px` → `column-gap: 8px; row-gap: 12px`. Outer padding bumped to 14/16. The tight 3px row-gap was the root structural cause of the `înv` overlap.
- **învechit marker.** Replaced the absolute-positioned `<span class="chip-meta inv">înv</span>` (which sat at `bottom: 0; left: 7px` and bled into the row below) with a red dotted `text-decoration` underline on `.word-text` itself. Word row gets `class="inv"` and `title="învechit"` when applicable; the chip-meta span and its CSS are gone. Bookmark+învechit conflict: bookmark amber wins, logged in BACKLOG.
- **Superscript freq.** Switched from `vertical-align: super` (oddly tall, competed with the word) to `vertical-align: baseline; position: relative; top: -0.55em` at 10px/600 weight/0.7 opacity. Reads as quiet metadata now.
- **Hover.** Tan `#f0ece5` → cool `var(--accent-bg)` `#eff6ff` so hover doesn't visually merge with the warm body bg.
- **Bookmarks.** Dropped the trailing `★` glyph; the amber underline alone is enough indicator.
- **Wide-word threshold.** `length >= 12` → `length >= 11` in `word_row.html` so 11-char words like `bogasieresc`, `panevghenie` get a 2-col span and stop crowding their neighbors.

Variant chosen via a temporary `/demo/marker` route that rendered six marker treatments side-by-side over the same word sample; demo route + `marker_demo.html` template removed after selection. Logged 4 follow-ups in BACKLOG (verdict palette, bookmark+învechit stacking, mobile breakpoints, extract CSS to static file).

## 2026-05-18 — Fix taxonomy join (load_taxonomy, fetch_all_tags)

`ObjectTag.objectId` where `objectType=3` holds Meaning IDs (max ~503k), but both `load_taxonomy()` in `validate_diachronic.py` and `fetch_all_tags()` in `create_curated_list.py` were joining on `el.entryId` (max ~339k) — different ID spaces, producing random tag assignments. Fixed by:

1. Updating `extract_taxonomy.py` to also extract `TreeEntry(id, treeId, entryId)` and `MeaningTree(meaning_id, tree_id)` from the dump. `Meaning` rows contain a `longtext` `internalRep` field that breaks `parse_mysql_insert`'s `[^)]+` regex, so a dedicated `_MEANING_PATTERN` regex extracts only the two needed integer columns. Re-ran against the full dump: 240,023 TreeEntry rows + 454,993 MeaningTree rows.

2. Rewiring both join sites to use `Lexeme → EntryLexeme → TreeEntry → MeaningTree → ObjectTag(objectType=3) → Tag`.

Verified: `pretutindeni` (no tags — correct), `antipapă` (francesa etymology — correct), `isihie` (`învechit` register + neogreacă etymology — correct). Previous wrong results: `pretutindeni→botanică`, `antipapă→medicină`, `aist→medicină`.

Next step: re-run `validate_diachronic.py` to regenerate `forgotten_words_diachronic.csv` with accurate taxonomy columns.

---

## 2026-05-17 — DEX dump DefinitionSimple gap confirmed + backlog entry

Investigated why `scrape_definitions.py` is needed despite having the full DEX MySQL dump. Verified against both dumps: `DefinitionSimple` contains exactly **61,041 rows** in both old (Oct 2025, 1.2 GB) and new (May 2026, 1.5 GB) dumps, while `EntryDefinition` references **1,379,043** definition IDs — 94.8% are dangling references with no corresponding record. The gap is unchanged between dump versions, confirming this is a structural omission in the public export, not a regression. Added backlog entry (#Upstream) to report the issue to dexonline developers with counts and workaround context.

---

## 2026-05-17 — New DEX dump intake + domain tag root-cause investigation

**Investigated domain filter bug**: user reported that filtering by domain = "medicină" showed words with no medicina association in the detail panel. Two issues found:

1. **Missing UI chip** (fixed in `detail.html`): `dex_domain` chips were never rendered in the footer detail panel — `dex_pos`, `dex_register`, `dex_etymology` were all present but `dex_domain` was omitted. One-line fix.

2. **`load_taxonomy()` join is fundamentally wrong** (tracked in backlog): confirmed via data archaeology that `ObjectTag.objectId` where `objectType=3` holds **Meaning IDs** (max ~503k in new dump), not Entry IDs (max ~339k). The existing join `ot.objectId = el.entryId` maps two different ID spaces together, producing random domain/register/etymology assignments. Evidence: `pretutindeni` (adverb "everywhere") → `botanică`; `antipapă` (antipope) → `medicină`; `aist` (dialectal "this") → `medicină`. Fix requires extracting `TreeEntry` + `Meaning(id, treeId)` tables and rewriting the join chain to `Lexeme → EntryLexeme → TreeEntry → Meaning → ObjectTag(objectType=3)`. Tracked in backlog with full context.

**New DEX dump intake**: new dump (`dex-database.sql`, 1.65 GB) replaces old one (renamed `dex-database-1.sql`, 1.27 GB). Key differences: mostly data growth (~1–4% per table), one new index on `Lexeme.pronunciations`, four new tables (`Subtitle`, `VideoClip`, `OCR_stats`, `student`). Notable: `Subtitle` has 13 M pre-tokenised Romanian word tokens from 966 YouTube clips (Digi24 news) — potential spoken-register corpus. Re-ran `extract_lexemes.py` and `extract_taxonomy.py` against new dump; `lexemes.db` now has 317,688 Lexeme rows and 496k ObjectTag rows. `validate_diachronic.py` not re-run (waiting for taxonomy join fix).

**extract_lexemes.py hardening**: added `--sql/--csv/--db` argparse args (defaulting to full dump path); made Lexeme table drop+recreate on re-run for idempotency; added skip logic for 7 malformed rows where apostrophes in the `form` field break CSV column count.

---

## 2026-05-17 — Definition extraction fix + dexonline.ro scraping pipeline

**Fixed definition misalignment** (commit 8113dbf): `extract_definitions.py` was joining through Entry tables to pair Lexeme→Definition, but Entry groups multiple related words, so rank-1 definitions were paired with wrong lexemes (e.g. `abate` getting the `abatize` definition). Root cause: misunderstood schema. `DefinitionSimple.lexicon` column *is* the headword, not a dictionary identifier. Rewrote to read `DefinitionSimple.lexicon` directly as the headword key, eliminating all join ambiguity. Coverage jumped from 26% to 83,609 definitions.

**Built scrape_definitions.py** (commit 4519a7a): New script to fill the remaining ~12,778 shortlist words missing from the DEX dump. Mirrors `search_wild.py` pattern:
- Inputs: `forgotten_words_shortlist.csv`, `definitions.db` (to identify missing words)
- Output: `scraped_definitions.csv` checkpoint (word, definition, source_url, scraped_at, status ∈ {ok, not_found, error})
- HTTP: BeautifulSoup extracts synthesis block from `https://dexonline.ro/definitie/{word}`, 3s/request delay
- Resume: reads existing checkpoint, skips already-processed words
- Merge: `--merge` flag upserts ok rows into `definitions.db` for immediate UI availability
- Flags: `--dry-run`, `--limit N`, `--delay SECONDS`, `--merge`, `--merge-only`
- Safe interrupts: each row flushed immediately, Ctrl+C preserves checkpoint

**Verification**: 6-word test run (commit 4519a7a) confirms scraper finds definitions, parses HTML correctly, and appends to checkpoint CSV properly.

**Started full run**: `python scrape_definitions.py --delay 3.0 --merge` to complete remaining ~12,778 definitions (expected 5–7 hours).

---

## 2026-05-16 — Rich UI redesign: tag filters, chip sidebar, light theme

Complete UI overhaul in three passes:

**Pass 1 — Granular tag filters + wider sidebar**: replaced all four `<select>` dropdowns with
always-visible pill tags (checkboxes). Filter bar now has 3 rows: search/utilities, verdict+tier,
register+domain+etymology. `app.py` gained `_distinct_split()` for frequency-ordered tag values,
multi-select `getlist()` for verdict/tier (OR within group), and `LIKE`-based filtering for
pipe-separated columns. Sidebar widened to 50%, word list changed to `flex-wrap` chip layout.
`PAGE_SIZE` raised from 50 to 150.

**Pass 2 — Domain-tagged words in shortlist**: `make_shortlist.py` previously excluded all
`dex_domain`-tagged words (technical jargon heuristic). Removed that exclusion — 514 domain-tagged
words now appear in the shortlist; UI filter dropdowns allow excluding them post-hoc.

**Pass 3 — Light theme**: Switched from dark (#1a1a1a) to warm parchment light theme. Typography:
`Lora` serif for headings/labels/definitions; `JetBrains Mono` for word chips and data. Verdict
colors adapted to light (burgundy extinct, amber declining, navy historical, violet absent) with
pill active states, chip left-border tints, selected chip verdict-background highlights. Status bar
shows keyboard shortcuts as inline `<kbd>` elements. `detail.html` updated with verdict badge
classes and inline tag pills for register/domain/etymology values.

**Pass 4 — Intersection filtering + POS + richer chips**: Switched all filter inputs from
checkboxes (OR-within-group) to radios (single-select-per-group, AND-across-groups). Click an
active pill again to deselect — JS captures the pre-click state on the label's `mousedown`
(inputs are `display:none` so don't see the mousedown themselves) and clears + fires a form-level
`change` so HTMX requests fresh results. Added a POS filter row with 8 abbreviated linguistic
categories (`s.f.`, `s.n.`, `s.m.`, `adj.`, `vb.`, `adv.`, `part.`, `interj.`) using LIKE matching
against the pipe-padded `dex_pos` column. Default sort changed from `word ASC` to
`COALESCE(modern_ppm, -1) ASC` — rarest-first ordering, with corpus-absent words at the top.
Word chips now surface more metadata inline: `dex_frequency` as a tabular-nums secondary number,
and a red italic `înv` marker for words tagged `învechit`.

## 2026-05-16 — Tag enrichment in curated list (backlog #16)

Investigated how `data-bs-content` abbreviation popovers on dexonline.ro map to the dump:
values come from `Abbreviation.internalRep` via `#abbrev#` markup in `Definition.internalRep`.
Separately, `Tag`/`ObjectTag`/`EntryLexeme` were already present in `lexemes.db` but unused.

Added `fetch_all_tags()` to `create_curated_list.py` — bulk-fetches taxonomy tags via two join
paths (objectType=2 direct, objectType=3 via entry) and writes three new columns to
`forgotten_words_curated.csv`: `dex_register`, `dex_domain`, `dex_etymology`. Coverage:
7,642 register tags, 3,405 domain tags, 35,120 etymology tags across 140,308 curated words.
Columns flow through `validate_with_wordfreq.py` automatically. Marked #16 done;
added #20 (metadata navigator with statistics view and CLI browse commands).

## 2026-05-15 — UI enhancements: definitions, sort by scarcity, shortcuts popup

Built three additive features on top of the Flask+HTMX research UI:

- **Word definitions** — `extract_definitions.py` streams the 1.2 GB DEX MySQL dump, joins Lexeme → EntryLexeme → EntryDefinition → DefinitionSimple to map every inflected form (not just headwords) to its entry's primary definition, and writes `data/processed/definitions.db`. `load_words()` in `ui/app.py` now loads definitions at startup. The detail panel shows a DEX block with the definition text and a link to dexonline.ro.
- **Sort by scarcity** — `/search` accepts a `sort` param (`declined`, `rare`, `dex_freq`) resolved through a safe allowlist dict (`SORT_OPTIONS`) so no user string is ever interpolated into SQL. A sort `<select>` in the filter bar uses the same HTMX pattern as the existing verdict/tier dropdowns.
- **Shortcuts popup** — pressing `?` opens a modal overlay listing all keyboard shortcuts; Esc or click-outside closes it.

Initial extraction hit only 26% coverage (DefinitionSimple.lexicon stores headwords only). Rewrote to join through EntryLexeme — coverage jumped to 83,609 definitions across 315,279 lexemes streamed.

---

## 2026-05-15 — Research UI: Flask+HTMX word explorer

Built a keyboard-driven local web app (`ui/app.py`) for exploring the forgotten-words shortlist:

- Two-column layout: word list (left) + detail panel (right), no page reloads
- Search with 200ms debounce, verdict/tier/bookmarked filters, pagination (50/page)
- Word detail: metadata table, corpus scores, web-validation results, bookmark toggle, notes, tag pills
- Bookmarks/notes/tags persisted to `data/research.db` (SQLite, survives restarts)
- Keyboard shortcuts: `/` focus search, `j`/`k` navigate, `b` bookmark, `n` note, `gg`/`G` jump
- Full test suite (`tests/test_ui.py`) covering all routes and HTMX fragment responses

Stack: Flask 3.0.3, HTMX 2.0.4, Jinja2, SQLite (in-memory words + file-backed bookmarks).

---

## 2026-05-15 — DEX taxonomy enrichment: extract_taxonomy.py + diachronic CSV new columns

Confirmed CulturaX run completed cleanly (40.3M docs / 17.0B tokens / 120,345 unique words, duration 15m 10s). `forgotten_words_diachronic.csv` needed a re-run since it was generated before CulturaX finished; `validate_diachronic.py` now also emits four new taxonomy columns.

**`extract_taxonomy.py`** (new script): parses the DEX MySQL dump for `Tag`, `ObjectTag`, and `EntryLexeme` tables and loads them into `lexemes.db` with indexes. The `Tag` table contains ~460 hierarchical tags organised into families: register (parentId=42: `învechit`, popular, dialectal, livresc…), domain (parentId=41: muzică, medicină, chimie, drept…), etymology (parentId=1: grecism, latinism, anglicism, turcism, slavonism…), and POS (isPos=1: substantiv feminin, substantiv neutru, adjectiv, verb…). `ObjectTag` links these to dictionary entries via `EntryLexeme`. On the sample dump: 410 Tag rows, 47k ObjectTag rows, 315k EntryLexeme rows.

**`validate_diachronic.py`**: added `load_taxonomy(lexemes_db)` function that joins `Lexeme → EntryLexeme → ObjectTag → Tag` and returns per-word tag sets. Graceful fallback (warning + empty strings) if taxonomy tables absent. Four new columns in `forgotten_words_diachronic.csv`: `dex_pos`, `dex_register`, `dex_domain`, `dex_etymology` (pipe-delimited for multi-value). On sample dump: 22,129 words with any taxonomy tag; highlights include `bolboacă` (verdict=extinct, dex_register=învechit) — direct DEX editorial confirmation cross-validated by corpus signal.

Backlog additions: #16 (taxonomy enrichment — now implemented), #17 (flag words with no definition body, e.g. *nombrilist* shows "[Fără definiție.]"), #18 (extract per-document temporal/domain metadata from corpora for "when did this word fall out of use" signal).

Next step on VPS: run `python extract_taxonomy.py --sql data/dictionaries/dex-database.sql` against the full 1.2GB dump (~990k ObjectTag rows) then re-run `validate_diachronic.py`.

## 2026-05-14 — Handled transient network errors in process_culturax.py

HuggingFace Hub CDN occasionally drops HTTP connections mid-stream while reading parquet row groups, raising `httpx.RemoteProtocolError`. This was uncaught, crashing the script with a noisy traceback and losing up to COMMIT_EVERY-1 (≤ 4,999) in-flight doc counts. Fixed by wrapping `pf.read_row_group()` in a try/except that flushes the in-memory buffer, saves checkpoint at the exact current row, prints a clean one-line warning, and returns a shutdown signal so `main()` exits with code 1 and the restart loop picks it up. README updated with a readable interactive loop form alongside the existing nohup one-liner.

## 2026-05-13 — Fixed load_dex_words() in corpus scripts; corpus re-run needed

`process_culturax.py` and `process_wikisource.py` both had `AND description != ''` in `load_dex_words()` — the same bug just fixed in `create_curated_list.py`. Words with empty DEX description but a valid `modelType` (N, F, A, VT…) were silently excluded from corpus tracking. The corrected filter (`description != '' OR modelType IN (…)`) expands the tracking set from ~15k to ~137k words, covering words like `jurnalism`, `ziar`, `lactoză`, `incompetență`. Both scripts updated identically. BACKLOG #15 added: corpus DB is stale and both runs must be redone on VPS.

## 2026-05-13 — Raised Phase 1 frequency cutoff; oțios now in pipeline

`create_curated_list.py`: raised DEX frequency ceiling from `< 0.60` to `< 1.0` (excludes only the 14,021 core-vocabulary entries at frequency = 1.0). Simultaneously fixed a second exclusion: words with empty `description` but a word-class `modelType` (e.g. `A` = adjective) are now accepted via `has_meaningful_description` fallback. Added `standard` rarity category (0.60–1.0).

Trigger: `oțios` (the project's namesake) was excluded despite being a confirmed forgotten word — DEX frequency 0.85 put it above the old ceiling, and its empty description field would have blocked it even after raising the cutoff.

Outcome: curated list grew from 1,884 → 140,308 candidates. After `validate_diachronic.py` re-run: 245 extinct / 1,430 declining / 1,026 historical_only (up from 6/2/40). `oțios` itself lands as `absent` — no occurrences in either Wikisource or CulturaX, confirming it is truly unused in written Romanian.

BACKLOG #14 added: consider a targeted web-validation pass on `absent` words with high DEX freq.

## 2026-05-12 — DDG baseline sweep of diachronic shortlist (48 words)

Ran `search_wild.py --provider ddg --limit 48 --delay 4` against `diachronic_shortlist_for_web.csv` (6 extinct + 2 declining + 40 historical_only). Baseline for the eventual Google A/B.

Distribution: `truly_extinct` 1, `marginal` 14, `alive_rare` 33. The high-end bucket is dominated by cross-language false matches (Sheffield uni Romanian course pages, German/English Wikipedia for non-Romanian homographs, foreign-language blogs), so `alive_rare` from DDG is unreliable signal on its own.

Useful findings under DDG's `< 10 hits` floor:
- `fărămat` — 0 hits, no top URL. Archaic of *fărâmat*; web-extinct.
- `lăut` — 4 hits. Only one of the 6 diachronic `extinct` verdicts that DDG also reads as rare.
- 14 of the 40 `historical_only` words land at `< 10 DDG hits` — a useful pre-filter for the "really dead" subset.

Cross-tab: of the 6 diachronic `extinct`, only `lăut` got DDG `marginal`; the other 5 (`ajutoriu`, `viți`, `jălit`, `jăluit`, `puțân`) all got fuzzy 10–18-hit matches that aren't real usage. Reinforces that DDG is triage-only on archaic Romanian; Google is the real validator.

Output retained at `data/processed/diachronic_shortlist_web_validated.csv` for direct row-level diff against a future `--provider google` run on the same input.

## 2026-05-12 — search_wild.py: pluggable provider interface (DDG + Google)

Refactored `search_wild.py` to support multiple search backends via a `SearchProvider` abstract base class. Two providers ship: `GoogleCSEProvider` (existing logic, preserves env-var requirement) and `DuckDuckGoProvider` (new, via the `ddgs` library — no API key). Provider selected via `--provider {ddg,google}`; default `ddg` for prototyping.

Output schema changed: column `google_total_results` → `total_results`, plus new `provider` column to disambiguate mixed-provider CSVs. `web_score` buckets are provider-specific (Google: 0/<10/<100/100+; DDG: 0/<3/<10/10+ capped at 30).

Notes on DDG: very noisy on rare archaic Romanian words — its auto backend rotates engines, `-site:` operators aren't always honored, and "exact-match" quotes fall back to fuzzy/related forms. Resolved partially with (a) post-filtering hits on the ignored-domain hostname list (since `-site:` is unreliable), (b) dropping `-site:` from the DDG query entirely (too long, kept hitting truncation), and (c) treating `DDGSException("No results found.")` as a valid 0-result outcome rather than an error. Expanded `DEFAULT_IGNORE_SITES` (added dex.ro, reverso, en-academic, glosbe, educalingo, archeus, etc.) for both providers.

Live smoke-test on 8 diachronic-shortlist words: `lăut` 4 results / `pribegit` 6 / `jălit` 9 — bottom of the range matches our extinct/declining verdicts. But top results are often false positives (Sheffield uni Romanian course, German Wikipedia for "Víti", Indonesian blog for "lăut"). Treat DDG as triage; plan to re-run with Google for ground truth.

`requirements.txt`: added `ddgs`; kept `google-api-python-client`.

## 2026-05-12 — Re-run validate_diachronic.py against clean CulturaX

Now that CulturaX has completed cleanly (40.3M docs / 17.0B tokens / 14,703 unique words, no cycling), regenerated the diachronic comparison. The previous `forgotten_words_diachronic.csv` (2026-04-29) was meaningless — produced when CulturaX data was either zero or ~6,600× inflated by the `ds.skip()` cycling bug, so every word fell into `historical_only` or `absent`. Preserved as `forgotten_words_diachronic.stale-2026-04-29.csv` for comparison.

Steps: regenerated `forgotten_words_curated.csv` from `lexemes.db` (1,884 rows → 1,077 unique after normalize() dedup), then ran `validate_diachronic.py` default mode.

Corpus sizes used: wikisource_ro 14,297,033 tokens, culturax_ro 16,969,999,321 tokens (1,187× larger).

Verdict breakdown (1,077 candidates):
- `extinct` 6, `declining` 2, `historical_only` 40, `stable` 7, `modern_only` 98, `emerging` 7, `absent` 917.

Top historically-skewed words (`hist_ppm > 0`, ordered by log_ratio): `ajutoriu`, `viți`, `pribegit`, `jălit`, `jăluit`, `puțân`, `lăut`, `substanțialist`, `jăcuit`, `bonsoar`, `estras`, `acufundat`, `alâm`, `jecuit`, `pohtit`, `adăogit`, `schopenhauerian`, `bergsonian`, `daleu`, `histeric` — all plausible 19th-century / pre-reform Romanian forms (`ajutoriu`/`pribegit`/`pohtit`/`puțân` are pre-modern spellings; `bergsonian`/`schopenhauerian` are dated philosophical adjectives).

Phase 2b diachronic output now reflects real signal; ready to feed into Phase 3 (`search_wild.py`) when desired.

## 2026-05-12 — Add status.py: at-a-glance pipeline summary

Added `status.py`, a read-only summary command. Prints five sections: header, corpus runs (from `processing_stats`, with checkpoint freshness for in-progress runs), pipeline artifacts (Phase 1/2/3 outputs with size, mtime, CSV row counts), process liveness (reuses `health_check.PROCESSES` and `_pid_alive()`), and recent audit (tail of `run_history.jsonl`, latest `quality_*.json` tally, last 7d of `alerts.log`). No flags, no writes, no alerts — just `python status.py`.

First run confirmed both corpora completed: culturax_ro 40.3M docs / 17.0B tokens / 14,703 unique words (duration 44m 27s, 421 tokens/doc); wikisource_ro 12,921 docs / 14.3M tokens / 6,876 words. All four quality checks pass for both. Stale `culturax.pid` correctly flagged as `DEAD` (loop exited cleanly when the run completed).

## 2026-05-12 — Add monitoring layer: health_check.py, audit.py, data/logs/

Added lightweight infrastructure for watching long-running corpus scripts:

- **`health_check.py`** — cron script (every 30 min) that checks loop PID liveness, checkpoint staleness (> 2 h without update = stalled), recent log errors, and corpus completion. Fires one alert per new problem via configurable backend (`OTZIOS_ALERT_URL` for webhooks, `OTZIOS_ALERT_EMAIL` for system mail). Alert state persisted in `data/logs/health_status.json` to prevent cron spam.
- **`audit.py`** — daily cron script that snapshots run history to `data/logs/run_history.jsonl` and runs quality checks: cycling detection (`MAX(document_count) ≤ docs_processed`), token-ratio sanity, word coverage floor, both-corpora-complete status. Writes dated `data/logs/quality_YYYY-MM-DD.json`; alerts on any `fail`.
- **`data/logs/`** — new canonical log/PID directory inside the repo (gitignored except `.gitkeep`). Updated CLAUDE.md, readme.md, and documentation to point here instead of `~/g2-dev/logs/`. Current culturax run PID copied to new location and log symlinked for immediate monitoring.
- **Cron installed** — both entries added to crontab.

Venv migration (to in-project `.venv`) deferred until the current culturax run completes. Steps documented in CLAUDE.md `## Monitoring` section.

## 2026-05-12 — process_culturax.py: fix cycling bug, rewrite to per-parquet checkpointing

Discovered that the existing `ds.skip(N)` approach had been cycling through the dataset repeatedly. Root cause: `SkipExamplesIterable._iter_arrow()` in `datasets` v4.8.5 contains a bug — when `skip(N)` is called with N greater than the dataset size, it sets `skipped = N` on the first batch (yielding an empty slice), then falls through a missing `continue`/`elif` to yield all remaining batches in full. Since the Romanian CulturaX shard is ~40M docs (64 parquet files × 630K rows) but the checkpoint had grown past 40M through successive restarts, every subsequent restart re-processed files 2–64 from near the beginning while advancing the checkpoint by ~67K each time. After ~6,600 bad restarts the checkpoint read 484M (12× the true dataset size) and occurrence counts were inflated ~6,600× non-uniformly.

Remediation:
- Wiped all `corpus_name = 'culturax_ro'` rows from `corpus_frequencies.db` and deleted the corrupted checkpoint.
- Rewrote `process_culturax.py` to bypass HuggingFace streaming entirely: lists the 64 parquet shards via `HfFileSystem`, reads each with `pyarrow.ParquetFile`, and checkpoints at the parquet-file + row-group level. On each restart the script opens the in-progress file, reads only the footer metadata to locate the right row group, and resumes with zero skip overhead. SIGTERM/SIGHUP flush the current batch cleanly before exit.
- Fixed the restart loop to `break` when the Python script exits 0 (all files done) rather than always restarting.

Fresh run started 2026-05-12; expected ~40M docs, ~8–16 hours total depending on SIGKILL frequency.

## 2026-05-05 — process_culturax.py: robustness fixes + auto-restart loop

Debugged repeated silent kills of `process_culturax.py` during resume runs. Root cause: SIGKILL (likely memory pressure from co-running `fetch_prices.py`) killing the process every ~50-75k docs. Fixes applied:
- Replaced manual skip loop with `ds.skip()` (IterableDataset native method) to avoid loading 190k+ docs into Python during resume
- Added `gc.collect()` after skip to free memory before processing begins
- Added SIGTERM/SIGHUP signal handler that logs exit point
- Added try/except with traceback around the main loop
- Switched to `python -u` (unbuffered) so log output isn't lost on hard kill
- Fixed progress print to flush immediately

Since SIGKILL can't be caught, launched a bash auto-restart loop (`nohup bash -c 'while true; do python -u process_culturax.py --resume; sleep 15; done'`) so the script resumes automatically from checkpoint after each kill. Checkpoint at 345k docs / ~100M tokens as of session end.

Also updated CLAUDE.md: added `## Logs` section documenting `~/g2-dev/logs/` and correct shared venv path (`~/g2-dev/monitorulpreturilor/venv`).

## 2026-04-29 — validate_diachronic.py: diachronic comparison script

Built `validate_diachronic.py`, the final piece of Enhancement #0. Joins `wikisource_ro` (historical literary) and `culturax_ro` (modern web) frequencies from `corpus_frequencies.db`. Normalizes both by corpus size (occurrences per million tokens), computes `log2((hist_ppm + 0.1) / (modern_ppm + 0.1))`, and assigns verdicts: `extinct`, `declining`, `stable`, `emerging`, `historical_only`, `modern_only`, `absent`. Output: `forgotten_words_diachronic.csv`, ranked by log ratio descending.

Tested against the existing 14.3M-token Wikisource run (CulturaX not yet run, so all modern_ppm = 0 — results are placeholder until CulturaX full run completes). Next step: run `process_culturax.py` on VPS.

---

## 2026-04-28 — Wikisource corpus pipeline; wordfreq limitations discovered

- Fixed `validate_with_wordfreq.py`: now uses `word_no_accent` for wordfreq lookups (DEX `form` field encodes stress with apostrophes, e.g. `bucl'e`); moved raw `word` column to end of output CSV. Added Data notes to README explaining the apostrophe convention.
- Investigated DEX `frequency` field: it measures lexicographic importance (how central a word is in dictionary definitions), not corpus frequency. `oțios` scores 0.85 in DEX but 0.000 in wordfreq — meaning DEX filters it out in Phase 1 despite being absent from all corpora.
- Found wordfreq's Romanian coverage to be binary: every tested word returns either 0.000 or ≥ 3.0, with nothing in between. Wordfreq is not a useful frequency signal for Romanian beyond identifying the top ~1,500 most common words.
- Pivoted Phase 2 strategy to diachronic corpus approach per `docs/corpus-options.md`: Wikisource RO as historical literary baseline ("then"), CulturaX RO as modern web baseline ("now"). Goal: compute log(freq_historical / freq_modern) to identify genuinely forgotten words.
- Wrote `process_wikisource.py`: fixes P0 bug from `process_corpus.py` (loads ~15k DEX forms from `lexemes.db` rather than 1.9k curated words); streams Wikisource RO from HuggingFace; checkpointing/resume; outputs to `corpus_frequencies.db` with `corpus_name = 'wikisource_ro'`. Test run: 500 docs, 1.4M tokens in 7 seconds.

---

## 2026-04-28 — Merge review-and-document branch into main

Merged the `review-and-document` feature branch back to `main`. Branch contained the methodological documentation, wordfreq tooling, and CLAUDE.md work from 2026-04-27/28.

---

## 2026-04-28 — Added initial project specs doc and updated readme

Added `docs/oțios-init-specs.docx.md` (converted from the original Google Docs spec). Updated `readme.md` with current status and links.

---

## 2026-04-28 — wordfreq/simplemma path: validate_with_wordfreq.py + requirements.txt

Added `validate_with_wordfreq.py` as a proof-of-concept for the pragmatic alternative to Phase 2's custom corpus pipeline. The script uses `wordfreq` frequency lookups + `simplemma` lemmatization to score candidates directly, bypassing the Wikipedia/OSCAR streaming setup entirely. Also added `requirements.txt` covering both the legacy pipeline (`datasets`) and the new path (`wordfreq`, `simplemma`).

Decision: flag `wordfreq` path as the recommended primary approach in documentation; demote full corpus streaming to a reranker role for rare candidates that fall below Zipf-3.

---

## 2026-04-27 — Methodological critique: conceptual roadmap, corpus catalog, methodology-v2

Added three new docs reflecting a deeper review of what the project is actually measuring:
- `docs/conceptual-roadmap.md` — reframes what "forgotten" should mean; critiques frequency-only approach; outlines Phase 3+ thinking
- `docs/corpus-options.md` — catalog of open Romanian corpora beyond Wikipedia (OSCAR, CoRoLa, CC-100, etc.) with access notes
- `docs/methodology-v2.md` — proposed revised methodology using wordfreq as primary signal
- `docs/wordfreq-recipe.md` — concrete implementation recipe for the wordfreq path

Also updated `docs/corpus-options.md` with additional corpus details, and moved `PHASE2_COMPLETE.md` from root to `docs/`.

---

## 2026-04-27 — CLAUDE.md: initial project review and enhancement backlog

Added `CLAUDE.md` with a full codebase review: pipeline documentation, data contracts, 10 known issues, and a ranked enhancement backlog. Updated `.gitignore`. This was the first formal AI-oriented documentation pass after the October 2025 implementation work.

---

## 2025-10-27 — Phase 2 complete: corpus validation pipeline

Built and tested the full Phase 2 pipeline in a single session:
- `download_wikipedia_ro.py` — pre-fetches Romanian Wikipedia via HuggingFace `datasets`
- `process_corpus.py` — streams Wikipedia (and optionally OSCAR-2301), counts candidate word occurrences, writes `corpus_frequencies.db`
- `validate_forgotten_words.py` — cross-references corpus frequencies with DEX candidates, produces `forgotten_words_validated.csv`, `false_positives.csv`, and `validation_report.txt`

Test run: 1,001 Wikipedia articles, 2,351 articles/sec, 1,007,108 tokens in 0.4s.

Note: the "159,543 confirmed forgotten" result from this test is misleading — the candidate-set mismatch bug (see `docs/BACKLOG.md`) means most words were never looked up in the corpus. Results need to be re-run after fixing that bug.

Also added `docs/phase2-corpus-validation-plan.md`, `docs/phase2-test-results.md`, and updated `docs/results-summary.md` and `readme.md`.

---

## 2025-10-27 — Phase 1 complete: DEX pipeline, analysis, curation

Built all Phase 1 scripts:
- `create_sample_db.py` — subsamples the 1.2 GB MySQL dump to ~285 MB
- `extract_lexemes.py` — regex-extracts the `Lexeme` table directly from the dump → `lexemes.csv` + `lexemes.db`
- `analyze_forgotten_words.py` — frequency analysis → `forgotten_words_v1.csv` + `statistics.txt`
- `create_curated_list.py` — heuristic filter → `forgotten_words_curated.csv` (~1,884 candidates)
- `mysql_to_sqlite.py`, `convert_to_sqlite.sh` — alternate conversion paths (not used in canonical pipeline)
- `explore_dex.py` — narrative exploration script (not a working pipeline step)

Also added initial `docs/` (database analysis, results summary, scripts guide, spec) and `readme.md`.

---

## 2025-10-26 — Project initialized

Repository created. Empty initial commit.
