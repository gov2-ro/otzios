// ── localStorage research store ───────────────────────────────────────────────

const STORE_KEY = 'otios.research';

const QUICK_TAG_EMOJIS = { ignore: '🙈', boring: '💤', funny: '😄', remove: '❌' };
const QUICK_TAG_KEYS   = Object.keys(QUICK_TAG_EMOJIS);

let openWord = null;
let arrivedViaShare = false;   // true while opening the panel from a shared ?word= link

function getResearch() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    const obj = raw ? JSON.parse(raw) : null;
    if (obj && obj.version === 1) return obj;
  } catch (_) {}
  return { version: 1, words: {} };
}

function saveResearch(obj) {
  localStorage.setItem(STORE_KEY, JSON.stringify(obj));
}

function getWord(word) {
  return getResearch().words[word] || { bookmarked: false, note: '', tags: [] };
}

function updateWord(word, patch) {
  const r = getResearch();
  const prev = r.words[word] || { bookmarked: false, note: '', tags: [] };
  const next = Object.assign({}, prev, patch, { updated_at: new Date().toISOString() });
  // prune empty entries
  if (!next.bookmarked && !next.note && (!next.tags || next.tags.length === 0)) {
    delete r.words[word];
  } else {
    r.words[word] = next;
  }
  saveResearch(r);
}

// ── Annotation hydration ───────────────────────────────────────────────────────

function currentSuppressEmoji() {
  const marks = document.querySelector('[name=marks]');
  if (!marks) return '';
  const v = marks.value;
  if (v === 'bookmarked') return '⭐';
  if (v === 'noted')      return '📝';
  if (v.startsWith('tag:')) {
    const tag = v.slice(4).trim();
    return QUICK_TAG_EMOJIS[tag] || '🏷️';
  }
  return '';
}

function buildOverlay(state, suppress) {
  let s = '';
  (state.tags || []).forEach(function(t) {
    const e = QUICK_TAG_EMOJIS[t] || '🏷️';
    if (e !== suppress) s += e;
  });
  if (state.note && '📝' !== suppress) s += '📝';
  if (state.bookmarked && '⭐' !== suppress) s += '⭐';
  return s;
}

function hydrateRows(root) {
  const suppress = currentSuppressEmoji();
  (root || document).querySelectorAll('.word-row[data-word]').forEach(function(row) {
    const word  = row.dataset.word;
    const state = getWord(word);

    // bookmarked class
    row.classList.toggle('bookmarked', !!state.bookmarked);

    // annotation overlay
    let overlay = row.querySelector('.ann-overlay');
    const text  = buildOverlay(state, suppress);
    if (text) {
      if (!overlay) {
        overlay = document.createElement('span');
        overlay.className = 'ann-overlay';
        row.appendChild(overlay);
      }
      overlay.textContent = text;
    } else if (overlay) {
      overlay.remove();
    }
  });
}

function hydrateDetail(root) {
  const panel = root || document.getElementById('detail-panel');
  if (!panel) return;

  const noteEl = panel.querySelector('#note-input');
  const bookEl = panel.querySelector('#bookmark-btn');
  const tagsEl = panel.querySelector('#tags-row');
  if (!noteEl && !bookEl) return;

  const word  = (noteEl || bookEl).dataset.word;
  if (!word) return;
  const state = getWord(word);

  // bookmark button
  if (bookEl) {
    bookEl.textContent = state.bookmarked ? '★' : '☆';
    bookEl.classList.toggle('active', !!state.bookmarked);
  }

  // note textarea
  if (noteEl) noteEl.value = state.note || '';

  // quick-tag buttons
  if (tagsEl) {
    tagsEl.querySelectorAll('.qt-btn[data-qtkey]').forEach(function(btn) {
      const tag = qtKeyToTag(btn.dataset.qtkey);
      if (tag) btn.classList.toggle('active', (state.tags || []).includes(tag));
    });

    // custom tag chips (re-render)
    tagsEl.querySelectorAll('.custom-tag').forEach(function(el) { el.remove(); });
    const input = tagsEl.querySelector('#tag-input');
    (state.tags || []).filter(function(t) { return !QUICK_TAG_KEYS.includes(t); }).forEach(function(t) {
      const span = document.createElement('span');
      span.className = 'tag custom-tag';
      span.innerHTML = escHtml(t) + ' <button class="tag-delete" data-tag="' + escHtml(t) + '" data-word="' + escHtml(word) + '">×</button>';
      tagsEl.insertBefore(span, input);
    });
  }
}

function qtKeyToTag(key) {
  const map = { i: 'ignore', B: 'boring', f: 'funny', x: 'remove' };
  return map[key] || null;
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Bookmark count ──────────────────────────────────────────────────────────────

function updateBookmarkCount() {
  const el = document.getElementById('bookmark-count');
  if (!el) return;
  const count = Object.values(getResearch().words).filter(function(w) { return w.bookmarked; }).length;
  el.textContent = String(count);
  const shareBtn = document.getElementById('share-bookmarks-btn');
  if (shareBtn) shareBtn.style.display = count > 0 ? '' : 'none';
}

function showToast(msg) {
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(function() { t.remove(); }, 2200);
}

function shareBookmarks() {
  const r = getResearch();
  const bookmarked = Object.entries(r.words)
    .filter(function(entry) { return entry[1].bookmarked; })
    .map(function(entry) { return entry[0]; });
  if (!bookmarked.length) { showToast('No bookmarks yet'); return; }
  const url = location.origin + location.pathname + '?words=' + bookmarked.map(encodeURIComponent).join(',');
  navigator.clipboard.writeText(url).then(function() { showToast('Playlist URL copied!'); });
}

function copyPlaylistUrl() {
  const pwInput = document.getElementById('playlist-words');
  if (!pwInput || !pwInput.value) return;
  const url = location.origin + location.pathname + '?words=' + pwInput.value;
  navigator.clipboard.writeText(url).then(function() { showToast('Playlist URL copied!'); });
}

function exitPlaylist() {
  const pwInput = document.getElementById('playlist-words');
  if (pwInput) pwInput.value = '';
  const banner = document.getElementById('playlist-banner');
  if (banner) banner.style.display = 'none';
  var params = new URLSearchParams(location.search);
  params.delete('words');
  var qs = params.toString();
  history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
  var form = document.getElementById('filter-form');
  if (form) htmx.trigger(form, 'change');
}

// ── Play / exploration ───────────────────────────────────────────────────────────

function openWordPanel(word, share) {
  if (!word) return;
  openWord = word;
  if (share) arrivedViaShare = true;
  var base = (typeof OTIOS_BASE !== 'undefined' ? OTIOS_BASE : '');
  htmx.ajax('GET', base + '/api/word.php?word=' + encodeURIComponent(word),
            { target: '#detail-panel', swap: 'innerHTML' });
}

function formQuery() {
  var form = document.getElementById('filter-form');
  if (!form) return '';
  return new URLSearchParams(new FormData(form)).toString();
}

function surpriseWord() {
  var base = (typeof OTIOS_BASE !== 'undefined' ? OTIOS_BASE : '');
  var qs = formQuery();
  fetch(base + '/api/random.php' + (qs ? '?' + qs : ''))
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.word) { showToast('Niciun cuvânt pentru aceste filtre'); return; }
      openWordPanel(d.word, false);
    })
    .catch(function() { showToast('Eroare la „surprise”'); });
}

// Word of the day
function wotdToday() { return new Date().toISOString().slice(0, 10); }

function openWotd() {
  var b = document.getElementById('wotd-banner');
  if (b) openWordPanel(b.dataset.word, false);
  dismissWotd();
}

function dismissWotd() {
  var b = document.getElementById('wotd-banner');
  if (b) b.style.display = 'none';
  try { localStorage.setItem('otios.wotd.seen', wotdToday()); } catch (_) {}
}

(function initWotd() {
  var b = document.getElementById('wotd-banner');
  if (!b) return;
  var seen = '';
  try { seen = localStorage.getItem('otios.wotd.seen') || ''; } catch (_) {}
  if (seen !== wotdToday()) b.style.display = '';
})();

// ── Feed / swipe mode ──────────────────────────────────────────────────────────

var FEED_DAILY_LIMIT = 50;          // soft, friendly nudge — not a hard block
var feedQueue = [];
var feedIdx   = 0;
var feedKept  = 0;
var feedLoading = false;

function feedOpen() {
  var o = document.getElementById('feed-overlay');
  return o && o.style.display !== 'none';
}

function feedDailyCount() {
  try {
    var raw = JSON.parse(localStorage.getItem('otios.feed') || '{}');
    return raw.date === wotdToday() ? (raw.count || 0) : 0;
  } catch (_) { return 0; }
}
function feedBumpDaily() {
  var c = feedDailyCount() + 1;
  try { localStorage.setItem('otios.feed', JSON.stringify({ date: wotdToday(), count: c })); } catch (_) {}
  return c;
}

function enterFeed() {
  var o = document.getElementById('feed-overlay');
  if (!o) return;
  feedQueue = []; feedIdx = 0; feedKept = 0;
  o.style.display = 'flex';
  closePanel();
  loadFeedBatch(function() { renderFeedCard(); });
}

function exitFeed() {
  var o = document.getElementById('feed-overlay');
  if (o) o.style.display = 'none';
}

function loadFeedBatch(cb) {
  if (feedLoading) return;
  feedLoading = true;
  var base = (typeof OTIOS_BASE !== 'undefined' ? OTIOS_BASE : '');
  var qs = formQuery();
  fetch(base + '/api/feed.php?n=24' + (qs ? '&' + qs : ''))
    .then(function(r) { return r.json(); })
    .then(function(d) {
      feedLoading = false;
      if (d.words && d.words.length) { feedQueue = feedQueue.concat(d.words); }
      if (cb) cb();
    })
    .catch(function() { feedLoading = false; });
}

function renderFeedCard() {
  var card = document.getElementById('feed-card');
  var prog = document.getElementById('feed-progress');
  if (!card) return;
  if (feedIdx >= feedQueue.length) {
    if (!feedLoading) {
      loadFeedBatch(function() {
        if (feedIdx >= feedQueue.length) {
          card.innerHTML = '<div class="feed-empty">Niciun cuvânt pentru aceste filtre.</div>';
        } else { renderFeedCard(); }
      });
    }
    card.innerHTML = '<div class="feed-empty">se încarcă…</div>';
    return;
  }
  var w = feedQueue[feedIdx];
  var verdict = w.verdict || 'unknown';
  var pos = (w.dex_pos || '').split('|')[0];
  var freq = (w.dex_frequency !== null && w.dex_frequency !== undefined) ? Math.round(w.dex_frequency * 100) : null;
  var dictN = w.sources ? w.sources.split('|').filter(Boolean).length : 0;
  var meta = [];
  if (pos)  meta.push(escHtml(pos));
  if (freq !== null) meta.push('dex ' + freq);
  if (dictN) meta.push('📚 ' + dictN);
  card.innerHTML =
    '<div class="feed-verdict verdict-badge vb-' + escHtml(verdict.replace(/ /g, '_')) + '">' + escHtml(verdict) + '</div>' +
    '<div class="feed-word">' + escHtml(w.word) + '</div>' +
    (meta.length ? '<div class="feed-cardmeta">' + meta.join(' · ') + '</div>' : '') +
    '<div class="feed-def">' + escHtml(w.definition || '') + '</div>';
  card.classList.remove('feed-anim-keep', 'feed-anim-skip');
  if (prog) {
    var today = feedDailyCount();
    prog.textContent = 'azi: ' + today + ' · păstrate: ' + feedKept;
  }
}

function feedAdvance(animClass) {
  var card = document.getElementById('feed-card');
  if (card && animClass) card.classList.add(animClass);
  var count = feedBumpDaily();
  feedIdx++;
  var go = function() { renderFeedCard(); };
  if (count === FEED_DAILY_LIMIT) {
    showToast('Ai explorat ' + FEED_DAILY_LIMIT + ' de cuvinte azi 🎉');
  }
  setTimeout(go, animClass ? 160 : 0);
}

function feedKeep() {
  if (feedIdx >= feedQueue.length) return;
  var w = feedQueue[feedIdx];
  if (w && !getWord(w.word).bookmarked) {
    updateWord(w.word, { bookmarked: true });
    feedKept++;
    updateBookmarkCount();
  }
  feedAdvance('feed-anim-keep');
}

function feedSkip() {
  if (feedIdx >= feedQueue.length) return;
  feedAdvance('feed-anim-skip');
}

// Touch swipe on the feed card
(function() {
  var startX = 0, startY = 0, tracking = false;
  var card = function() { return document.getElementById('feed-card'); };
  document.addEventListener('touchstart', function(e) {
    if (!feedOpen() || e.touches.length !== 1) return;
    var c = card();
    if (!c || !c.contains(e.target)) return;
    startX = e.touches[0].clientX; startY = e.touches[0].clientY; tracking = true;
  }, { passive: true });
  document.addEventListener('touchend', function(e) {
    if (!tracking) return;
    tracking = false;
    var t = e.changedTouches[0];
    var dx = t.clientX - startX, dy = t.clientY - startY;
    if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy)) {
      if (dx > 0) feedKeep(); else feedSkip();
    }
  }, { passive: true });
})();

// ── Datalist for tag autocomplete ───────────────────────────────────────────────

function populateTagDatalist() {
  const dl = document.getElementById('tag-suggestions');
  if (!dl) return;
  const seen = new Set();
  Object.values(getResearch().words).forEach(function(w) {
    (w.tags || []).forEach(function(t) {
      if (!QUICK_TAG_KEYS.includes(t)) seen.add(t);
    });
  });
  dl.innerHTML = '';
  seen.forEach(function(t) {
    const opt = document.createElement('option');
    opt.value = t;
    dl.appendChild(opt);
  });
}

// Populate marks <select> with custom tags from localStorage so they're filterable
function populateTagFilterOptions() {
  const sel = document.querySelector('select[name=marks]');
  if (!sel) return;
  sel.querySelectorAll('option.custom-tag-opt').forEach(function(o) { o.remove(); });
  const seen = new Set();
  Object.values(getResearch().words).forEach(function(w) {
    (w.tags || []).forEach(function(t) {
      if (!QUICK_TAG_KEYS.includes(t)) seen.add(t);
    });
  });
  seen.forEach(function(t) {
    const opt = document.createElement('option');
    opt.value = 'tag:' + t;
    opt.textContent = 'tag: ' + t;
    opt.className = 'custom-tag-opt';
    sel.appendChild(opt);
  });
}

// ── Marks filter: inject marked_words before HTMX search request ───────────────

function markedWordsForFilter(marks) {
  const research = getResearch();
  const words    = research.words;

  if (marks === 'bookmarked') {
    return Object.entries(words).filter(function([,w]) { return w.bookmarked; }).map(function([k]) { return k; });
  }
  if (marks === 'noted') {
    return Object.entries(words).filter(function([,w]) { return w.note && w.note.trim(); }).map(function([k]) { return k; });
  }
  if (marks === 'marked') {
    return Object.entries(words).filter(function([,w]) {
      return w.bookmarked || (w.note && w.note.trim()) || (w.tags && w.tags.length);
    }).map(function([k]) { return k; });
  }
  if (marks === 'unmarked') {
    // return all marked words so server can do NOT IN
    return Object.entries(words).filter(function([,w]) {
      return w.bookmarked || (w.note && w.note.trim()) || (w.tags && w.tags.length);
    }).map(function([k]) { return k; });
  }
  if (marks.startsWith('tag:')) {
    const tag = marks.slice(4).trim();
    return Object.entries(words).filter(function([,w]) {
      return (w.tags || []).includes(tag);
    }).map(function([k]) { return k; });
  }
  return null;
}

document.addEventListener('htmx:configRequest', function(e) {
  const url = e.detail.path || '';
  const base = (typeof OTIOS_BASE !== 'undefined' ? OTIOS_BASE : '');
  if (!url.startsWith(base + '/api/search.php')) return;
  const marks = e.detail.parameters['marks'] || 'all';
  const wordList = markedWordsForFilter(marks);
  if (wordList !== null) {
    e.detail.parameters['marked_words'] = wordList.join(',');
  }
});

// ── HTMX lifecycle ─────────────────────────────────────────────────────────────

document.body.addEventListener('htmx:afterSwap', function(e) {
  const target = e.detail.target;
  if (target.id === 'word-list') {
    selectedIdx = -1;
    hydrateRows(target);
    // Highlight the word from a shared URL after the list renders
    if (openWord) {
      var all = rows();
      var idx = all.findIndex(function(r) { return r.dataset.word === openWord; });
      if (idx >= 0) selectRow(idx, true);
    }
  }
  if (target.id === 'detail-panel') {
    target.classList.add('panel-open');
    // Definition-as-hero when arriving from a shared link; normal height otherwise.
    if (arrivedViaShare) {
      target.classList.add('share-focus');
      arrivedViaShare = false;
      setTimeout(function() { target.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, 60);
    } else {
      target.classList.remove('share-focus');
    }
    const hb = document.getElementById('hover-box');
    if (hb) hb.classList.remove('visible');
    hydrateDetail(target);
    var wordEl = target.querySelector('[data-word]');
    if (wordEl) { openWord = wordEl.dataset.word; syncUrlFromForm(); }
  }
});

// Also hydrate OOB-swapped load-more results
document.body.addEventListener('htmx:oobAfterSwap', function() {
  hydrateRows(document.getElementById('word-list'));
});

// ── Click handlers (delegated) ─────────────────────────────────────────────────

document.body.addEventListener('click', function(e) {
  // Bookmark button
  const bookBtn = e.target.closest('#bookmark-btn');
  if (bookBtn) {
    e.preventDefault();
    const word = bookBtn.dataset.word;
    if (!word) return;
    const state = getWord(word);
    updateWord(word, { bookmarked: !state.bookmarked });
    hydrateDetail(document.getElementById('detail-panel'));
    hydrateRows(document.getElementById('word-list'));
    updateBookmarkCount();
    return;
  }

  // Quick-tag button
  const qtBtn = e.target.closest('.qt-btn[data-qtkey]');
  if (qtBtn) {
    e.preventDefault();
    const tagsRow = qtBtn.closest('#tags-row');
    const word = tagsRow ? tagsRow.dataset.word : null;
    if (!word) return;
    const tag = qtKeyToTag(qtBtn.dataset.qtkey);
    if (!tag) return;
    const state = getWord(word);
    const tags  = state.tags || [];
    const next  = tags.includes(tag) ? tags.filter(function(t) { return t !== tag; }) : [...tags, tag];
    updateWord(word, { tags: next });
    hydrateDetail(document.getElementById('detail-panel'));
    hydrateRows(document.getElementById('word-list'));
    return;
  }

  // Custom tag delete
  const delBtn = e.target.closest('.tag-delete');
  if (delBtn) {
    e.preventDefault();
    const word = delBtn.dataset.word;
    const tag  = delBtn.dataset.tag;
    if (!word || !tag) return;
    const state = getWord(word);
    updateWord(word, { tags: (state.tags || []).filter(function(t) { return t !== tag; }) });
    hydrateDetail(document.getElementById('detail-panel'));
    hydrateRows(document.getElementById('word-list'));
    populateTagDatalist();
    populateTagFilterOptions();
    return;
  }
});

// Tag input — add custom tag on Enter
document.body.addEventListener('keydown', function(e) {
  const input = e.target.closest('#tag-input');
  if (!input || e.key !== 'Enter') return;
  e.preventDefault();
  const val = input.value.trim();
  if (!val) return;
  const tagsRow = input.closest('#tags-row');
  const word = tagsRow ? tagsRow.dataset.word : null;
  if (!word) return;
  const state = getWord(word);
  const tags  = state.tags || [];
  if (!tags.includes(val)) {
    updateWord(word, { tags: [...tags, val] });
    hydrateDetail(document.getElementById('detail-panel'));
    hydrateRows(document.getElementById('word-list'));
    populateTagDatalist();
    populateTagFilterOptions();
  }
  input.value = '';
}, true);

// Note — save on Enter
document.body.addEventListener('keydown', function(e) {
  const textarea = e.target.closest('#note-input');
  if (!textarea || e.key !== 'Enter') return;
  e.preventDefault();
  const word = textarea.dataset.word;
  if (!word) return;
  updateWord(word, { note: textarea.value });
  const status = document.getElementById('note-status');
  if (status) {
    status.innerHTML = '<span class="saved-notice">saved</span>';
    status.style.display = '';
  }
  hydrateRows(document.getElementById('word-list'));
}, true);

// ── Grid navigation (preserved from base.html) ─────────────────────────────────

let selectedIdx = -1;
let gPressed    = false;

function rows() { return Array.from(document.querySelectorAll('.word-row')); }

function selectRow(idx, noClick) {
  const all = rows();
  if (!all.length) return;
  selectedIdx = Math.max(0, Math.min(idx, all.length - 1));
  all.forEach(function(r) { r.removeAttribute('data-selected'); });
  const r = all[selectedIdx];
  if (r) {
    r.setAttribute('data-selected', '');
    r.scrollIntoView({ block: 'nearest' });
    if (!noClick) r.click();
  }
}

function navigateSpatial(direction) {
  const all = rows();
  if (!all.length) return;
  if (selectedIdx < 0) { selectRow(0); return; }
  const cur   = all[selectedIdx].getBoundingClientRect();
  const curMX = (cur.left + cur.right) / 2;
  let best    = { idx: -1, score: Infinity };
  all.forEach(function(el, idx) {
    if (idx === selectedIdx) return;
    const r  = el.getBoundingClientRect();
    const mx = (r.left + r.right) / 2;
    const sameRow = Math.abs(r.top - cur.top) < cur.height * 0.6;
    let score;
    if (direction === 'left') {
      if (!sameRow || r.right > cur.left + 1) return;
      score = cur.left - r.right;
    } else if (direction === 'right') {
      if (!sameRow || r.left < cur.right - 1) return;
      score = r.left - cur.right;
    } else if (direction === 'up') {
      if (r.bottom > cur.top + 1) return;
      score = (cur.top - r.bottom) * 10 + Math.abs(mx - curMX);
    } else {
      if (r.top < cur.bottom - 1) return;
      score = (r.top - cur.bottom) * 10 + Math.abs(mx - curMX);
    }
    if (score < best.score) best = { idx: idx, score: score };
  });
  if (best.idx >= 0) selectRow(best.idx);
}

function showShortcuts() { document.getElementById('shortcuts-overlay').style.display = 'flex'; }
function hideShortcuts() { document.getElementById('shortcuts-overlay').style.display = 'none'; }
function closePanel() {
  var panel = document.getElementById('detail-panel');
  panel.classList.remove('panel-open');
  panel.classList.remove('share-focus');
  openWord = null;
  syncUrlFromForm();
}

document.addEventListener('keydown', function(e) {
  const tag     = document.activeElement.tagName;
  const inInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
  // Feed mode captures navigation keys
  if (feedOpen()) {
    if (e.key === 'Escape') { e.preventDefault(); exitFeed(); return; }
    if (e.key === 'ArrowRight' || e.key === 'l') { e.preventDefault(); feedKeep(); return; }
    if (e.key === 'ArrowLeft'  || e.key === 'h') { e.preventDefault(); feedSkip(); return; }
    return;
  }
  if (e.key === '?') { e.preventDefault(); showShortcuts(); return; }
  if (inInput) {
    if (e.key === 'Escape') {
      hideShortcuts();
      const wasSearch = document.activeElement.id === 'search';
      document.activeElement.blur();
      if (wasSearch && rows().length) selectRow(selectedIdx >= 0 ? selectedIdx : 0, true);
    }
    return;
  }
  if (e.key === 'Escape') { hideShortcuts(); closePanel(); return; }
  if (e.key === '/') { e.preventDefault(); document.getElementById('search').focus(); return; }
  if (e.key === 'j' || e.key === 'ArrowDown')  { e.preventDefault(); navigateSpatial('down');  gPressed = false; return; }
  if (e.key === 'k' || e.key === 'ArrowUp')    { e.preventDefault(); navigateSpatial('up');    gPressed = false; return; }
  if (e.key === 'h' || e.key === 'ArrowLeft')  { e.preventDefault(); navigateSpatial('left');  gPressed = false; return; }
  if (e.key === 'l' || e.key === 'ArrowRight') { e.preventDefault(); navigateSpatial('right'); gPressed = false; return; }
  if (e.key === 'G') { e.preventDefault(); selectRow(rows().length - 1); gPressed = false; return; }
  if (e.key === 'g') {
    if (gPressed) { selectRow(0); gPressed = false; }
    else { gPressed = true; setTimeout(function() { gPressed = false; }, 400); }
    return;
  }
  if (e.key === 'r') { e.preventDefault(); surpriseWord(); return; }
  // Actions — call localStorage handlers instead of HTMX
  if (e.key === 'b') {
    const btn = document.getElementById('bookmark-btn');
    if (btn) { e.preventDefault(); btn.click(); }
    return;
  }
  if (e.key === 'n') {
    const note = document.getElementById('note-input');
    if (note) { e.preventDefault(); note.focus(); }
    return;
  }
  if (e.key === 'o') {
    const link = document.querySelector('#detail-panel .dex-link');
    if (link) { e.preventDefault(); window.open(link.href, '_blank', 'noopener'); }
    return;
  }
  if (e.key === 't') {
    const ti = document.getElementById('tag-input');
    if (ti) { e.preventDefault(); ti.focus(); }
    return;
  }
  if (e.key === 'i' || e.key === 'B' || e.key === 'f' || e.key === 'x') {
    const btn = document.querySelector('#detail-panel .qt-btn[data-qtkey="' + e.key + '"]');
    if (btn) { e.preventDefault(); btn.click(); }
    return;
  }
});

// Sync selectedIdx on mouse click (and handle dismissing on mobile)
document.addEventListener('click', function(e) {
  const container = document.getElementById('word-list-container');
  if (!container || !container.contains(e.target)) return;
  const row = e.target.closest('.word-row');
  
  if (!row) {
    // Tapped an empty spot in the list -> Hide panel and deselect
    closePanel();
    const selected = document.querySelector('.word-row[data-selected]');
    if (selected) selected.removeAttribute('data-selected');
    return;
  }

  const all = rows();
  const idx = all.indexOf(row);
  if (idx < 0) return;
  all.forEach(function(r) { r.removeAttribute('data-selected'); });
  row.setAttribute('data-selected', '');
  selectedIdx = idx;
});

// Shortcuts overlay dismiss
document.addEventListener('click', function(e) {
  const overlay = document.getElementById('shortcuts-overlay');
  if (overlay && e.target === overlay) hideShortcuts();
});

// Deselectable radio pills
document.querySelectorAll('#filter-form label.pill').forEach(function(label) {
  label.addEventListener('mousedown', function() {
    const input = this.querySelector('input[type=radio]');
    if (input) input.dataset.wasChecked = input.checked ? '1' : '';
  });
});
document.querySelectorAll('#filter-form label.pill input[type=radio]').forEach(function(r) {
  r.addEventListener('click', function() {
    if (this.dataset.wasChecked === '1') {
      this.checked = false;
      this.dataset.wasChecked = '';
      this.form.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
});

// DEX-rare filter is only meaningful on the rare tab — show it there only.
(function() {
  const ctrl = document.getElementById('dex-rare-control');
  if (!ctrl) return;
  function sync() {
    const sel = document.querySelector('#filter-form input[name=word_tier]:checked');
    ctrl.style.display = (sel && sel.value === 'rare_in_use') ? '' : 'none';
  }
  document.querySelectorAll('#filter-form input[name=word_tier]')
    .forEach(function(r) { r.addEventListener('change', sync); });
  sync();
})();

// Tax-select active highlight
document.querySelectorAll('.tax-select').forEach(function(sel) {
  const dflt = sel.dataset.default !== undefined ? sel.dataset.default : '';
  function update() { sel.classList.toggle('active', sel.value !== dflt); }
  sel.addEventListener('change', update);
  if (sel.form) sel.form.addEventListener('reset', update);
  update();
});

// ── Hover info box ─────────────────────────────────────────────────────────────

(function() {
  const box    = document.getElementById('hover-box');
  const hbWord = document.getElementById('hb-word');
  const hbVerd = document.getElementById('hb-verdict');
  const hbMeta = document.getElementById('hb-meta');
  const hbDef  = document.getElementById('hb-def');
  const panel  = document.getElementById('detail-panel');

  document.addEventListener('mouseover', function(e) {
    const row = e.target.closest('.word-row');
    if (!row || panel.classList.contains('panel-open')) return;
    const verdict = row.dataset.verdict || 'unknown';
    hbWord.textContent = row.querySelector('.word-text').textContent;
    hbVerd.textContent = verdict;
    hbVerd.className   = 'verdict-badge vb-' + verdict.replace(/ /g, '_');
    const parts = [];
    if (row.dataset.pos)  parts.push(row.dataset.pos);
    if (row.dataset.freq) parts.push('dex ' + row.dataset.freq);
    hbMeta.textContent = parts.join(' · ');
    if (row.dataset.def) {
      hbDef.textContent  = row.dataset.def;
      hbDef.style.display = '';
    } else {
      hbDef.style.display = 'none';
    }
    box.classList.add('visible');
  });

  document.addEventListener('mouseout', function(e) {
    const row = e.target.closest('.word-row');
    if (!row) return;
    const to = e.relatedTarget;
    if (to && row.contains(to)) return;
    box.classList.remove('visible');
  });
})();

// ── Active-filter chips (at-a-glance, individually removable) ────────────────────

var AF_SPECS = [
  { name: 'q',              type: 'text',     label: function(v){ return '„' + v + '”'; } },
  { name: 'has_def',        type: 'radio',  def: '', label: function(v){ return v === '1' ? 'cu definiție' : 'fără definiție'; } },
  { name: 'register',       type: 'select', def: '', label: function(v){ return 'registru: ' + v; } },
  { name: 'domain',         type: 'select', def: '', label: function(v){ return 'domeniu: ' + v; } },
  { name: 'etymology',      type: 'select', def: '', label: function(v){ return 'etim: ' + v.replace('limba ', ''); } },
  { name: 'dict_min',       type: 'select', def: '', label: function(v){ return 'dicts ≥' + v; } },
  { name: 'dex_max',        type: 'select', def: '0.60', label: function(v){ return 'DEX ' + (v === 'all' ? 'toate' : '≤' + v); } },
  { name: 'zipf_min',       type: 'number',   label: function(v){ return 'zipf ≥' + v; } },
  { name: 'zipf_max',       type: 'number',   label: function(v){ return 'zipf ≤' + v; } },
  { name: 'dexfreq_min',    type: 'number',   label: function(v){ return 'dex ≥' + v; } },
  { name: 'dexfreq_max',    type: 'number',   label: function(v){ return 'dex ≤' + v; } },
  { name: 'hide_loanwords', type: 'checkbox', label: function(){ return 'fără împrumuturi'; } },
  { name: 'hide_proper',    type: 'checkbox', label: function(){ return 'fără nume proprii'; } },
  { name: 'verdict',        type: 'group',    label: function(n, t){ return 'verdict ' + n + '/' + t; } },
  { name: 'tier',           type: 'group',    label: function(n, t){ return 'tier ' + n + '/' + t; } },
  { name: 'pos',            type: 'group',    label: function(n, t){ return 'POS ' + n + '/' + t; } },
];

function activeFilterChips() {
  var form = document.getElementById('filter-form');
  if (!form) return [];
  var wordTier = (form.querySelector('input[name=word_tier]:checked') || {}).value || 'forgotten';
  var chips = [];
  AF_SPECS.forEach(function(spec) {
    if (spec.name === 'dex_max' && wordTier !== 'rare_in_use') return;
    if (spec.type === 'text' || spec.type === 'number') {
      var el = form.querySelector('input[name=' + spec.name + ']');
      if (el && el.value.trim()) chips.push({ spec: spec, text: spec.label(el.value.trim()) });
    } else if (spec.type === 'radio') {
      var r = form.querySelector('input[name=' + spec.name + ']:checked');
      if (r && r.value !== spec.def) chips.push({ spec: spec, text: spec.label(r.value) });
    } else if (spec.type === 'select') {
      var s = form.querySelector('select[name=' + spec.name + ']');
      if (s && s.value !== spec.def && s.value !== '') chips.push({ spec: spec, text: spec.label(s.value) });
    } else if (spec.type === 'checkbox') {
      var c = form.querySelector('input[name=' + spec.name + ']');
      if (c && c.checked) chips.push({ spec: spec, text: spec.label() });
    } else if (spec.type === 'group') {
      var all = Array.from(form.querySelectorAll('input[name="' + spec.name + '[]"]'));
      var chk = all.filter(function(cb){ return cb.checked; });
      if (all.length && chk.length < all.length) chips.push({ spec: spec, text: spec.label(chk.length, all.length) });
    }
  });
  return chips;
}

function clearFilter(spec) {
  var form = document.getElementById('filter-form');
  if (!form) return;
  if (spec.type === 'text' || spec.type === 'number') {
    var el = form.querySelector('input[name=' + spec.name + ']');
    if (el) el.value = '';
  } else if (spec.type === 'radio') {
    form.querySelectorAll('input[name=' + spec.name + ']').forEach(function(r){ r.checked = (r.value === spec.def); });
  } else if (spec.type === 'select') {
    var s = form.querySelector('select[name=' + spec.name + ']');
    if (s) { s.value = spec.def; s.dispatchEvent(new Event('change', { bubbles: true })); return; }
  } else if (spec.type === 'checkbox') {
    var c = form.querySelector('input[name=' + spec.name + ']');
    if (c) c.checked = false;
  } else if (spec.type === 'group') {
    form.querySelectorAll('input[name="' + spec.name + '[]"]').forEach(function(cb){ cb.checked = true; });
  }
  form.dispatchEvent(new Event('change', { bubbles: true }));
}

function renderActiveFilters() {
  var bar = document.getElementById('active-filters');
  if (!bar) return;
  var chips = activeFilterChips();
  bar.innerHTML = '';
  chips.forEach(function(c) {
    var chip = document.createElement('span');
    chip.className = 'af-chip';
    chip.appendChild(document.createTextNode(c.text + ' '));
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.setAttribute('aria-label', 'elimină filtrul');
    btn.textContent = '×';
    btn.addEventListener('click', function() { clearFilter(c.spec); });
    chip.appendChild(btn);
    bar.appendChild(chip);
  });
  if (chips.length > 1) {
    var clearAll = document.createElement('button');
    clearAll.type = 'button';
    clearAll.className = 'af-clear-all';
    clearAll.textContent = 'resetează tot';
    clearAll.addEventListener('click', function() {
      var form = document.getElementById('filter-form');
      if (form) form.reset();
    });
    bar.appendChild(clearAll);
  }
}

document.getElementById('filter-form') &&
  document.getElementById('filter-form').addEventListener('change', renderActiveFilters);

// ── URL ↔ filter sync ──────────────────────────────────────────────────────────

// Param names whose default value means "no filter" (omit from URL when at default)
var URL_PARAM_DEFAULTS = {
  word_tier: 'forgotten',
  has_def:   '',
  sort:      'rare',
  marks:     'all',
};

function applyUrlToForm() {
  var params = new URLSearchParams(location.search);
  if (!params.toString()) return;
  var form = document.getElementById('filter-form');
  if (!form) return;

  // Text input
  var q = params.get('q');
  if (q) { var qi = form.querySelector('input[name=q]'); if (qi) qi.value = q; }

  // Radio groups
  ['word_tier', 'has_def'].forEach(function(name) {
    var val = params.get(name);
    if (val === null) return;
    form.querySelectorAll('input[name=' + name + ']').forEach(function(r) {
      r.checked = (r.value === val);
    });
  });

  // Checkbox groups (verdict, tier, pos): comma-separated in URL; absent = all checked
  ['verdict', 'tier', 'pos'].forEach(function(name) {
    var val = params.get(name);
    if (val === null) return; // not in URL → leave all checked
    var selected = val.split(',').filter(Boolean);
    form.querySelectorAll('input[name="' + name + '[]"]').forEach(function(cb) {
      cb.checked = selected.includes(cb.value);
    });
  });

  // Selects: sort, register, domain, etymology, dex_max, dict_min, marks
  ['sort', 'register', 'domain', 'etymology', 'dex_max', 'dict_min', 'marks'].forEach(function(name) {
    var val = params.get(name);
    if (val === null) return;
    var el = form.querySelector('select[name=' + name + ']');
    if (el) el.value = val;
  });

  // Explore: number inputs (zipf_min, zipf_max, dexfreq_min, dexfreq_max)
  ['zipf_min', 'zipf_max', 'dexfreq_min', 'dexfreq_max'].forEach(function(name) {
    var val = params.get(name);
    if (val === null) return;
    var el = form.querySelector('input[name=' + name + ']');
    if (el) el.value = val;
  });

  // Explore: checkboxes (hide_loanwords, hide_proper)
  ['hide_loanwords', 'hide_proper'].forEach(function(name) {
    var val = params.get(name);
    if (val === null) return;
    var el = form.querySelector('input[name=' + name + ']');
    if (el) el.checked = (val === '1');
  });

  // Word profile param
  var wordParam = params.get('word');
  if (wordParam) openWord = wordParam;

  // Playlist words param
  var wordsParam = params.get('words');
  if (wordsParam) {
    var pwInput = document.getElementById('playlist-words');
    if (pwInput) pwInput.value = wordsParam;
    var banner = document.getElementById('playlist-banner');
    var countEl = document.getElementById('playlist-count');
    if (banner) banner.style.display = '';
    if (countEl) {
      var wcount = wordsParam.split(',').filter(Boolean).length;
      countEl.textContent = wcount + (wcount === 1 ? ' word' : ' words') + ' in playlist';
    }
  }
}

function syncUrlFromForm() {
  var form = document.getElementById('filter-form');
  if (!form) return;
  var params = new URLSearchParams();

  // Text input
  var q = form.querySelector('input[name=q]');
  if (q && q.value.trim()) params.set('q', q.value.trim());

  // Radio groups
  ['word_tier', 'has_def'].forEach(function(name) {
    var el = form.querySelector('input[name=' + name + ']:checked');
    var val = el ? el.value : '';
    if (val && val !== (URL_PARAM_DEFAULTS[name] || '')) params.set(name, val);
  });

  // Checkbox groups: only write to URL when some-but-not-all are checked
  ['verdict', 'tier', 'pos'].forEach(function(name) {
    var all  = Array.from(form.querySelectorAll('input[name="' + name + '[]"]'));
    var chkd = all.filter(function(cb) { return cb.checked; });
    if (chkd.length > 0 && chkd.length < all.length) {
      params.set(name, chkd.map(function(cb) { return cb.value; }).join(','));
    }
  });

  // Selects
  ['sort', 'register', 'domain', 'etymology', 'dex_max', 'dict_min', 'marks'].forEach(function(name) {
    var el = form.querySelector('select[name=' + name + ']');
    if (!el) return;
    var val = el.value;
    if (val && val !== (URL_PARAM_DEFAULTS[name] || '')) params.set(name, val);
  });

  // Explore: number inputs
  ['zipf_min', 'zipf_max', 'dexfreq_min', 'dexfreq_max'].forEach(function(name) {
    var el = form.querySelector('input[name=' + name + ']');
    if (el && el.value.trim()) params.set(name, el.value.trim());
  });

  // Explore: binary checkboxes
  ['hide_loanwords', 'hide_proper'].forEach(function(name) {
    var el = form.querySelector('input[name=' + name + ']');
    if (el && el.checked) params.set(name, '1');
  });

  // Preserve open word and playlist
  if (openWord) params.set('word', openWord);
  var pwInput = document.getElementById('playlist-words');
  if (pwInput && pwInput.value.trim()) params.set('words', pwInput.value.trim());

  var qs = params.toString();
  history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
}

// Reset: re-fire HTMX search and clear URL after the browser resets form values
document.getElementById('filter-form') && document.getElementById('filter-form').addEventListener('reset', function() {
  setTimeout(function() {
    var form = document.getElementById('filter-form');
    if (form) form.dispatchEvent(new Event('change', { bubbles: true }));
    syncUrlFromForm();
    renderActiveFilters();
  }, 0);
});

// Apply URL params to form before HTMX fires its initial load request
applyUrlToForm();

// Rehydrate open word from URL on page load — definition takes the spotlight
(function() {
  var w = new URLSearchParams(location.search).get('word');
  if (!w) return;
  arrivedViaShare = true;
  var base = (typeof OTIOS_BASE !== 'undefined' ? OTIOS_BASE : '');
  htmx.ajax('GET', base + '/api/word.php?word=' + encodeURIComponent(w), { target: '#detail-panel', swap: 'innerHTML' });
})();

// Keep URL in sync with every HTMX search request
document.addEventListener('htmx:configRequest', function(e) {
  var url = e.detail.path || '';
  var base = (typeof OTIOS_BASE !== 'undefined' ? OTIOS_BASE : '');
  if (!url.startsWith(base + '/api/search.php')) return;
  syncUrlFromForm();
});

// ── Init ────────────────────────────────────────────────────────────────────────

updateBookmarkCount();
populateTagDatalist();
populateTagFilterOptions();
renderActiveFilters();

// ── Mobile Auto-Close on Scroll ─────────────────────────────────────────────────

(function() {
  let mobileTouchStartY = 0;
  
  // Track where a swipe begins
  document.addEventListener('touchstart', function(e) {
    if (e.touches.length > 0) {
      mobileTouchStartY = e.touches[0].clientY;
    }
  }, { passive: true });

  // Check if they swipe significantly
  document.addEventListener('touchmove', function(e) {
    if (window.innerWidth > 768 || e.touches.length === 0) return;
    
    const panel = document.getElementById('detail-panel');
    if (!panel || !panel.classList.contains('panel-open')) return;

    // Do NOT close if they are scrolling INSIDE the definition drawer itself
    if (panel.contains(e.target)) return;

    const touchY = e.touches[0].clientY;
    // If they drag up or down by 15px in the word list, close it
    if (Math.abs(touchY - mobileTouchStartY) > 15) {
      closePanel();
      
      // Visually remove the dark highlight from the word
      const selected = document.querySelector('.word-row[data-selected]');
      if (selected) selected.removeAttribute('data-selected');
    }
  }, { passive: true });
})();