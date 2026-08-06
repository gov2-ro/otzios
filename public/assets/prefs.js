/* ══════════════════════════════════════════════════════════════════════════════
   Display preferences — colour theme, visual skin, text scale.

   Every page links this. app.js is index-only, so the toggle logic the other
   pages also need used to be copy-pasted into joc.php and stats.php; three
   copies that had already started to drift. This is the single one.

   The stored values are applied before first paint by the inline boot script in
   each <head>, so there's no flash — this file only wires up the controls and
   keeps their pressed state in sync with what's applied.
══════════════════════════════════════════════════════════════════════════════ */

var TEXT_SCALE_STEPS = [87.5, 100, 112.5, 125, 137.5];

/* ── Colour theme: light | dark ── */

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  try { localStorage.setItem('otios.theme', theme); } catch (_) {}
  syncThemeButtons();
}

function syncThemeButtons() {
  var theme = document.documentElement.getAttribute('data-theme') || 'light';
  document.querySelectorAll('[data-theme-btn]').forEach(function(btn) {
    btn.classList.toggle('tg-active', btn.dataset.themeBtn === theme);
  });
}

/* ── Visual skin: brutal (beton) | paper (the original editorial look) ──
   Orthogonal to light/dark — each skin defines both, so the two axes combine
   into four looks. `paper` is plain app.css; `brutal` layers skin-brutal.css
   on top, which is scoped entirely under [data-skin="brutal"]. */

function setSkin(skin) {
  document.documentElement.setAttribute('data-skin', skin);
  try { localStorage.setItem('otios.skin', skin); } catch (_) {}
  syncSkinButtons();
}

function syncSkinButtons() {
  var skin = document.documentElement.getAttribute('data-skin') || 'brutal';
  document.querySelectorAll('[data-skin-btn]').forEach(function(btn) {
    btn.classList.toggle('tg-active', btn.dataset.skinBtn === skin);
  });
}

/* ── Text scale ── */

function currentTextScale() {
  return parseFloat(document.documentElement.style.fontSize) || 100;
}

function nearestScaleIdx(val) {
  var idx = TEXT_SCALE_STEPS.indexOf(val);
  if (idx !== -1) return idx;
  var best = 0;
  TEXT_SCALE_STEPS.forEach(function(v, i) {
    if (Math.abs(v - val) < Math.abs(TEXT_SCALE_STEPS[best] - val)) best = i;
  });
  return best;
}

function stepTextScale(direction) {
  var idx = nearestScaleIdx(currentTextScale());
  var next = Math.max(0, Math.min(TEXT_SCALE_STEPS.length - 1, idx + direction));
  var pct = TEXT_SCALE_STEPS[next];
  document.documentElement.style.fontSize = pct + '%';
  try { localStorage.setItem('otios.textscale', String(pct)); } catch (_) {}
  syncScaleButtons();
}

function syncScaleButtons() {
  var idx = nearestScaleIdx(currentTextScale());
  document.querySelectorAll('[data-scale-btn]').forEach(function(btn) {
    var dir = btn.dataset.scaleBtn === 'down' ? -1 : 1;
    btn.disabled = (dir === -1 && idx <= 0) || (dir === 1 && idx >= TEXT_SCALE_STEPS.length - 1);
  });
}

/* Scripts are at the end of <body>, so the controls already exist — but sync
   again on DOMContentLoaded in case a page ever moves this to the head. */
function syncPrefButtons() {
  syncThemeButtons();
  syncSkinButtons();
  syncScaleButtons();
}
syncPrefButtons();
document.addEventListener('DOMContentLoaded', syncPrefButtons);
