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
    var on = btn.dataset.themeBtn === theme;
    btn.classList.toggle('tg-active', on);
    // The class is the only thing that used to say which is active, so a screen
    // reader heard two identical unlabelled buttons. aria-pressed makes the state
    // part of the button rather than part of the stylesheet.
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
  });
}

/* ── Visual skin ──
   Orthogonal to light/dark — a skin defines both, so the two axes combine.
   `paper` is plain app.css; every other option is a file in assets/skins/,
   scoped entirely under its own [data-skin="<filename>"]. The dropdown's
   options are discovered server-side by _skins.php, so nothing here needs to
   know which skins exist. */

function setSkin(skin) {
  document.documentElement.setAttribute('data-skin', skin);
  try { localStorage.setItem('otios.skin', skin); } catch (_) {}
  syncSkinControls();
}

function syncSkinControls() {
  var skin = document.documentElement.getAttribute('data-skin');
  if (!skin) return;
  document.querySelectorAll('[data-skin-select]').forEach(function(sel) {
    // The boot script falls back to the default when a stored skin no longer
    // has a file, so trust the attribute over localStorage — but don't force a
    // value the <select> has no option for.
    if (sel.querySelector('option[value="' + CSS.escape(skin) + '"]')) sel.value = skin;
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
  syncSkinControls();
  syncScaleButtons();
}
syncPrefButtons();
document.addEventListener('DOMContentLoaded', syncPrefButtons);

/* ── `--statusbar-h` is measured, not declared ────────────────────────────────
 *
 * On mobile the footer is `position: fixed`, so that token is a *reservation*: the
 * body's bottom padding, the detail sheet's `bottom` and the toast's all read it, and
 * whatever it gets wrong is either dead space above the bar or a row of the list
 * underneath it.
 *
 * It cannot be got right as a constant, and the reason is worth stating: the bar's
 * height is a function of viewport width AND text scale AND skin, and it changes by
 * *reflow* rather than by scale — at 540px the bar is one line at 100% and two at 125%.
 * Measured over 6 skins × 5 widths × 3 text scales, no single set of CSS values covers
 * all 90; the best static attempt still under-reserved 16 of them. Declaring it was
 * always going to be a list of breakpoints chasing a layout, which is exactly the
 * history the app.css comments record: 44px, then 76px at ≤710, then 96px at ≤480, each
 * honest when written and each outliving the wrap it was written for.
 *
 * So: read the height off the element and write it back. Every skin, every width, every
 * text scale, and anything added to the bar later, for free.
 *
 * Three things to keep:
 *
 * 1. **Nothing that sizes the bar may read this token**, or measuring it feeds back into
 *    it and the observer oscillates. The bar sizes to its own content; `#status-bar` has
 *    no `height`/`min-height` in `--statusbar-h` terms anywhere.
 * 2. **The CSS values stay as a pre-JS fallback.** They are what the first frame uses,
 *    and what a page without this script gets (`despre.html`), so they should stay
 *    roughly right rather than being left to rot at 0.
 * 3. **`ghici.php` still wins.** It hides the footer on a phone, so the measurement is
 *    genuinely 0 there — the same answer its own `body.page-ghici { --statusbar-h: 0 }`
 *    gives, arrived at by measuring rather than by asserting.
 */
(function () {
  var bar = document.getElementById('status-bar');
  if (!bar) return;
  var root = document.documentElement;
  var last = -1;
  function sync() {
    // Ceil: a fractional reservation rounds down to a hairline of the list showing
    // under the bar, which reads as a rendering bug rather than as a gap.
    var h = Math.ceil(bar.getBoundingClientRect().height);
    if (h === last) return;
    last = h;
    root.style.setProperty('--statusbar-h', h + 'px');
  }
  sync();
  if (window.ResizeObserver) {
    new ResizeObserver(sync).observe(bar);
  } else {
    addEventListener('resize', sync);
  }
})();
