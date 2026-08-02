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
