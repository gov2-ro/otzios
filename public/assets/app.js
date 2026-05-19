// ── localStorage research store ───────────────────────────────────────────────

const STORE_KEY = 'otios.research';

const QUICK_TAG_EMOJIS = { ignore: '🙈', boring: '💤', funny: '😄', remove: '❌' };
const QUICK_TAG_KEYS   = Object.keys(QUICK_TAG_EMOJIS);

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
}

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
  if (!url.startsWith('/api/search.php')) return;
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
  }
  if (target.id === 'detail-panel') {
    target.classList.add('panel-open');
    const hb = document.getElementById('hover-box');
    if (hb) hb.classList.remove('visible');
    hydrateDetail(target);
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
function closePanel()    { document.getElementById('detail-panel').classList.remove('panel-open'); }

document.addEventListener('keydown', function(e) {
  const tag     = document.activeElement.tagName;
  const inInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
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

// Sync selectedIdx on mouse click
document.addEventListener('click', function(e) {
  const container = document.getElementById('word-list-container');
  if (!container || !container.contains(e.target)) return;
  const row = e.target.closest('.word-row');
  if (!row) return;
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

// ── Init ────────────────────────────────────────────────────────────────────────

updateBookmarkCount();
populateTagDatalist();
