// ── Shared research store + server sync ───────────────────────────────────────
//
// Loaded by both index.php and joc.php. Previously each page carried its own copy
// of this logic (app.js and an inline block in joc.php), writing to the same
// localStorage key from two implementations.
//
// Writes stay local-first: every change lands in localStorage immediately so the UI
// is instant and keeps working offline, then the touched words are queued and pushed
// to the server. A failed push stays queued and retries on the next change or page
// load, so a server outage costs nothing but freshness.

var STORE_KEY = 'otios.research';   // { version, words: { word: {bookmarked, note, tags, updated_at} } }
var QUEUE_KEY = 'otios.pending';    // { word: "<iso8601 marked-dirty time>" }
var SYNC_KEY  = 'otios.sync';       // { since: <server seq>, migrated }

var syncInFlight = false;
var syncTimer    = null;

function nowIso() { return new Date().toISOString(); }

function readJson(key, fallback) {
  try {
    var raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) || fallback) : fallback;
  } catch (_) { return fallback; }
}

function writeJson(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) {}
}

// ── Local store ───────────────────────────────────────────────────────────────

function getResearch() {
  var obj = readJson(STORE_KEY, null);
  if (obj && obj.version === 1) return obj;
  return { version: 1, words: {} };
}

function saveResearch(obj) { writeJson(STORE_KEY, obj); }

function getWord(word) {
  return getResearch().words[word] || { bookmarked: false, note: '', tags: [] };
}

function updateWord(word, patch) {
  var r = getResearch();
  var prev = r.words[word] || { bookmarked: false, note: '', tags: [] };
  var next = Object.assign({}, prev, patch, { updated_at: nowIso() });
  // prune empty entries
  if (!next.bookmarked && !next.note && (!next.tags || next.tags.length === 0)) {
    delete r.words[word];
  } else {
    r.words[word] = next;
  }
  saveResearch(r);
  markDirty(word);
}

// ── Word-detail panel ────────────────────────────────────────────────────────────
//
// The panel markup (public/api/_partials/detail.php) and the annotation-editing
// behaviour are identical on index.php (sliding #detail-panel) and joc.php (a modal)
// — only the container differs, so nothing here hardcodes an id. Both containers
// carry the '.word-detail-panel' class instead, and handlers look up the nearest one
// from the click/keydown target.

var QUICK_TAG_EMOJIS = { ascunde: '🙈', lol: '😂', meh: '⚠️' };
var QUICK_TAG_KEYS   = Object.keys(QUICK_TAG_EMOJIS);
var QT_EXPLAINER_KEY = 'otios.qtExplainerDismissed';

function qtKeyToTag(key) {
  var map = { a: 'ascunde', l: 'lol', m: 'meh' };
  return map[key] || null;
}

function qtExplainerDismissed() {
  try { return localStorage.getItem(QT_EXPLAINER_KEY) === '1'; } catch (_) { return false; }
}

// Dismissal is held by a class on <html>, with CSS doing the hiding — not by an inline
// style written after each render.
//
// The inline version looked correct and failed in one specific way: the detail panel is
// re-rendered when you open the next word, and the fresh #qt-explainer arrives with no
// inline style, so the banner came back on every word even though localStorage said
// dismissed. (Verified: hydrateDetail did set display:none, and the computed style was
// `flex` a moment later with the inline value gone — a different element.) A root class
// cannot be lost that way, because it is not on the element being replaced.
function applyQtExplainerState() {
  if (typeof document === 'undefined' || !document.documentElement) return;
  document.documentElement.classList.toggle('qt-dismissed', qtExplainerDismissed());
}

function dismissQtExplainer() {
  try { localStorage.setItem(QT_EXPLAINER_KEY, '1'); } catch (_) {}
  applyQtExplainerState();
}

applyQtExplainerState();

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function hydrateDetail(root) {
  var panel = root || document.querySelector('.word-detail-panel');
  if (!panel) return;

  var noteEl = panel.querySelector('#note-input');
  var bookEl = panel.querySelector('#bookmark-btn');
  var tagsEl = panel.querySelector('#tags-row');
  if (!noteEl && !bookEl) return;

  var word = (noteEl || bookEl).dataset.word;
  if (!word) return;
  var state = getWord(word);

  if (bookEl) {
    bookEl.classList.toggle('active', !!state.bookmarked);
  }

  if (noteEl) noteEl.value = state.note || '';

  if (tagsEl) {
    tagsEl.querySelectorAll('.qt-btn[data-qtkey]').forEach(function(btn) {
      var tag = qtKeyToTag(btn.dataset.qtkey);
      if (tag) btn.classList.toggle('active', (state.tags || []).includes(tag));
    });

    tagsEl.querySelectorAll('.custom-tag').forEach(function(el) { el.remove(); });
    (state.tags || []).filter(function(t) { return !QUICK_TAG_KEYS.includes(t); }).forEach(function(t) {
      var span = document.createElement('span');
      span.className = 'tag custom-tag';
      span.innerHTML = escHtml(t) + ' <button class="tag-delete" data-tag="' + escHtml(t) + '" data-word="' + escHtml(word) + '">×</button>';
      tagsEl.appendChild(span);
    });
  }

  // The explainer's visibility is CSS, keyed on `.qt-dismissed` on <html> — see
  // applyQtExplainerState(). Nothing to do per render.
}

function closeDictTooltips() {
  document.querySelectorAll('.dict-tooltip:not([hidden])').forEach(function(t) { t.setAttribute('hidden', ''); });
  document.querySelectorAll('.fp-dicts-toggle[aria-expanded="true"]').forEach(function(b) { b.setAttribute('aria-expanded', 'false'); });
}

// Delegated on document.body so it works no matter how the panel HTML was inserted
// (htmx swap on index.php, plain fetch+innerHTML on joc.php). Guarded on
// `document.body` because this file also runs inside a Node `vm` stub in
// tests/test_store_sync.js, whose fake `document` has no `body`.
if (typeof document !== 'undefined' && document.body) {
  document.body.addEventListener('click', function(e) {
    var explainerClose = e.target.closest('#qt-explainer-close');
    if (explainerClose) {
      e.preventDefault();
      dismissQtExplainer();
      return;
    }

    var bookBtn = e.target.closest('#bookmark-btn');
    if (bookBtn) {
      e.preventDefault();
      var bWord = bookBtn.dataset.word;
      if (!bWord) return;
      var bState = getWord(bWord);
      var nowFav = !bState.bookmarked;
      updateWord(bWord, { bookmarked: nowFav });
      hydrateDetail(e.target.closest('.word-detail-panel'));
      if (typeof hydrateRows === 'function') hydrateRows(document.getElementById('word-list'));
      if (typeof updateBookmarkCount === 'function') updateBookmarkCount();
      // Marking moves you on (see advanceAfterMark in app.js). Un-favouriting does
      // not: that is a correction, and advancing would take you off the word you
      // just came back to fix. The row survives a fav, hence removesRow = false.
      if (nowFav && typeof advanceAfterMark === 'function') advanceAfterMark(bWord, false);
      return;
    }

    var qtBtn = e.target.closest('.qt-btn[data-qtkey]');
    if (qtBtn) {
      e.preventDefault();
      var tagsRow = qtBtn.closest('#tags-row');
      var qWord = tagsRow ? tagsRow.dataset.word : null;
      if (!qWord) return;
      var tag = qtKeyToTag(qtBtn.dataset.qtkey);
      if (!tag) return;
      var qState    = getWord(qWord);
      var qTags     = qState.tags || [];
      var wasTagged = qTags.includes(tag);
      var next      = wasTagged ? qTags.filter(function(t) { return t !== tag; }) : qTags.concat([tag]);
      updateWord(qWord, { tags: next });
      hydrateDetail(e.target.closest('.word-detail-panel'));
      if (typeof hydrateRows === 'function') hydrateRows(document.getElementById('word-list'));
      // Applying any quick tag moves you on to the next word; removing one does not
      // (see advanceAfterMark in app.js). `ascunde`/`meh` additionally pop the row
      // out of the grid instead of waiting for a re-search — that is what the second
      // argument says. `advanceAfterMark` is index-only; joc.php loads this file
      // without it and only ever needs the fade, hence the fallback.
      var hides = (tag === 'ascunde' || tag === 'meh');
      if (!wasTagged) {
        if (typeof advanceAfterMark === 'function')         advanceAfterMark(qWord, hides);
        else if (hides && typeof fadeOutRow === 'function') fadeOutRow(qWord);
      }
      return;
    }

    var delBtn = e.target.closest('.tag-delete');
    if (delBtn) {
      e.preventDefault();
      var dWord = delBtn.dataset.word;
      var dTag  = delBtn.dataset.tag;
      if (!dWord || !dTag) return;
      var dState = getWord(dWord);
      updateWord(dWord, { tags: (dState.tags || []).filter(function(t) { return t !== dTag; }) });
      hydrateDetail(e.target.closest('.word-detail-panel'));
      if (typeof hydrateRows === 'function') hydrateRows(document.getElementById('word-list'));
      if (typeof populateTagDatalist === 'function') populateTagDatalist();
      if (typeof populateTagFilterOptions === 'function') populateTagFilterOptions();
      return;
    }

    // Dictionary-name tooltip — the label doubles as its own toggle button so
    // the names stop printing straight into the panel body (see .fp-dicts in
    // detail.php). Closes any other open one first: only one at a time.
    var dictToggle = e.target.closest('.fp-dicts-toggle');
    if (dictToggle) {
      e.preventDefault();
      var dictTip = dictToggle.parentElement.querySelector('.dict-tooltip');
      if (!dictTip) return;
      var willOpen = dictTip.hasAttribute('hidden');
      closeDictTooltips();
      if (willOpen) {
        dictTip.removeAttribute('hidden');
        dictToggle.setAttribute('aria-expanded', 'true');
        // Fixed positioning has nothing to anchor to on its own — place it
        // under the toggle, clamped so it can't run past the viewport edge.
        var rect = dictToggle.getBoundingClientRect();
        var maxLeft = window.innerWidth - dictTip.offsetWidth - 8;
        dictTip.style.top = Math.round(rect.bottom + 4) + 'px';
        dictTip.style.left = Math.round(Math.max(8, Math.min(rect.left, maxLeft))) + 'px';
      }
      return;
    }
    if (!e.target.closest('.dict-tooltip')) closeDictTooltips();
  });

  // A stale-positioned tooltip left open through a scroll is worse than none —
  // 'scroll' doesn't bubble, so this has to be a capturing listener on document
  // to catch it from `.fp-body` (the panel's own scrolling region).
  document.addEventListener('scroll', closeDictTooltips, true);

  // Tag input — add custom tag on Enter
  document.body.addEventListener('keydown', function(e) {
    var input = e.target.closest('#tag-input');
    if (!input || e.key !== 'Enter') return;
    e.preventDefault();
    var val = input.value.trim();
    if (!val) return;
    var tagsRow = input.closest('#tags-row');
    var word = tagsRow ? tagsRow.dataset.word : null;
    if (!word) return;
    var state = getWord(word);
    var tags  = state.tags || [];
    if (!tags.includes(val)) {
      updateWord(word, { tags: tags.concat([val]) });
      hydrateDetail(e.target.closest('.word-detail-panel'));
      if (typeof hydrateRows === 'function') hydrateRows(document.getElementById('word-list'));
      if (typeof populateTagDatalist === 'function') populateTagDatalist();
      if (typeof populateTagFilterOptions === 'function') populateTagFilterOptions();
    }
    input.value = '';
  }, true);

  // Note — save on Enter
  document.body.addEventListener('keydown', function(e) {
    var textarea = e.target.closest('#note-input');
    if (!textarea || e.key !== 'Enter') return;
    e.preventDefault();
    var word = textarea.dataset.word;
    if (!word) return;
    updateWord(word, { note: textarea.value });
    var status = document.getElementById('note-status');
    if (status) {
      status.innerHTML = '<span class="saved-notice">saved</span>';
      status.style.display = '';
    }
    if (typeof hydrateRows === 'function') hydrateRows(document.getElementById('word-list'));
  }, true);
}

// ── Outbound queue ────────────────────────────────────────────────────────────
//
// The queue holds only the set of touched words, not an event log: the payload is
// rebuilt from current local state at push time. Repeated edits to one word collapse
// into a single change, and a replayed push is idempotent.

function getQueue() { return readJson(QUEUE_KEY, {}) || {}; }
function saveQueue(q) { writeJson(QUEUE_KEY, q); }

function markDirty(word) {
  var q = getQueue();
  q[word] = nowIso();
  saveQueue(q);
  scheduleSync();
}

function getSyncState() { return readJson(SYNC_KEY, {}) || {}; }
function saveSyncState(s) { writeJson(SYNC_KEY, s); }

// One-time push of whatever a returning user already had in localStorage before
// server storage existed. Marks every stored word dirty; the normal sync path does
// the rest, and last-write-wins keeps it safe to run against existing server data.
function migrateLocalStore() {
  var state = getSyncState();
  if (state.migrated) return;

  var words = getResearch().words;
  var q = getQueue();
  Object.keys(words).forEach(function (w) {
    if (!q[w]) q[w] = words[w].updated_at || nowIso();
  });
  saveQueue(q);

  state.migrated = true;
  saveSyncState(state);
}

// ── Sync ──────────────────────────────────────────────────────────────────────

function buildChanges(queue) {
  var words = getResearch().words;
  return Object.keys(queue).map(function (w) {
    var e = words[w];
    if (!e) {
      // Pruned locally (unbookmarked, note cleared, tags removed) — send a tombstone
      // so the deletion reaches the user's other devices instead of being resurrected.
      return { word: w, bookmarked: false, note: '', tags: [], updated_at: queue[w], deleted: true };
    }
    return {
      word:       w,
      bookmarked: !!e.bookmarked,
      note:       e.note || '',
      tags:       e.tags || [],
      updated_at: e.updated_at || queue[w],
      deleted:    false
    };
  });
}

function applyRemote(changes) {
  if (!changes || !changes.length) return false;
  var r = getResearch();
  var touched = false;

  changes.forEach(function (c) {
    var local = r.words[c.word];
    // Local edit is newer — keep it; our own copy will win on the next push.
    if (local && local.updated_at && local.updated_at >= c.updated_at) return;

    if (c.deleted) {
      if (local) { delete r.words[c.word]; touched = true; }
      return;
    }
    r.words[c.word] = {
      bookmarked: !!c.bookmarked,
      note:       c.note || '',
      tags:       c.tags || [],
      updated_at: c.updated_at
    };
    touched = true;
  });

  if (touched) saveResearch(r);   // deliberately not markDirty — this came from the server
  return touched;
}

function scheduleSync(delay) {
  if (syncTimer) clearTimeout(syncTimer);
  syncTimer = setTimeout(function () { syncNow(); }, delay == null ? 1500 : delay);
}

function syncNow() {
  if (syncInFlight) return Promise.resolve(false);
  var base = (typeof OTIOS_BASE !== 'undefined' ? OTIOS_BASE : '');

  var queue    = getQueue();
  var snapshot = Object.keys(queue);
  var state    = getSyncState();

  syncInFlight = true;
  return fetch(base + '/api/sync.php', {
    method:      'POST',
    credentials: 'same-origin',
    headers:     { 'Content-Type': 'application/json' },
    body:        JSON.stringify({ since: state.since || 0, changes: buildChanges(queue) })
  })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(new Error('sync ' + r.status)); })
    .then(function (data) {
      // Drop only what we actually sent: edits made while the request was in flight
      // must survive for the next push.
      var q = getQueue();
      snapshot.forEach(function (w) { delete q[w]; });
      saveQueue(q);

      var changed = applyRemote(data.changes);
      var s = getSyncState();
      s.since = data.server_seq;
      saveSyncState(s);

      if (changed) {
        document.dispatchEvent(new CustomEvent('otios:synced', { detail: { changed: true } }));
      }
      if (data.has_more) scheduleSync(200);
      return changed;
    })
    .catch(function () { return false; })   // stay queued, retry on next change or load
    .then(function (result) { syncInFlight = false; return result; });
}

function otiosMe() {
  var base = (typeof OTIOS_BASE !== 'undefined' ? OTIOS_BASE : '');
  return fetch(base + '/api/me.php', { credentials: 'same-origin' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .catch(function () { return null; });
}

// Push anything still queued when the page goes away (tab close, navigation).
document.addEventListener('visibilitychange', function () {
  if (document.visibilityState === 'hidden' && Object.keys(getQueue()).length) syncNow();
});

migrateLocalStore();
scheduleSync(300);
