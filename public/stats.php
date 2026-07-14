<?php
declare(strict_types=1);
require_once __DIR__ . '/api/_lib.php';

$registers = vocab('register');
$domains   = vocab('domain');
$etyms     = vocab('etymology');

global $POS_OPTIONS;

$tiers = [
    ['corpus_extinct',         'corp. extinct'],
    ['corpus_declining',       'corp. declining'],
    ['corpus_historical_only', 'corp. historical'],
    ['dex_invechit_absent',    'dex. învechit'],
    ['dex_absent_highfreq',    'dex. absent'],
];
?>
<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
  <script>(function(){try{var t=localStorage.getItem('otios.theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.setAttribute('data-theme',t);var s=localStorage.getItem('otios.textscale')||'100';document.documentElement.style.fontSize=s+'%';}catch(e){}})();</script>
  <title>Oțios — Statistici</title>
  <meta property="og:title" content="Oțios — statistici">
  <meta property="og:description" content="Statistical breakdown of forgotten Romanian words: etymology, parts of speech, registers, domains, and more.">
  <meta property="og:type" content="website">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&family=Public+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/htmx.org@2.0.4" integrity="sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+" crossorigin="anonymous"></script>
  <link rel="stylesheet" href="<?= BASE ?>/assets/app.css">
</head>
<body style="display:flex;flex-direction:column;height:100vh;overflow:hidden;">

  <form id="filter-form"
        hx-get="<?= BASE ?>/api/stats.php"
        hx-trigger="change"
        hx-target="#stats-container"
        hx-include="#filter-form">

    <!-- Row 1: word_tier + has_def + loading indicator -->
    <div class="filter-row">
      <div class="seg">
        <label class="seg-opt"><input type="radio" name="word_tier" value="forgotten" checked> uitate</label>
        <label class="seg-opt"><input type="radio" name="word_tier" value="rare_in_use"> rare</label>
      </div>
      <div class="fsep"></div>
      <div class="seg">
        <label class="seg-opt"><input type="radio" name="has_def" value="" checked> any</label>
        <label class="seg-opt"><input type="radio" name="has_def" value="1"> def ✓</label>
        <label class="seg-opt"><input type="radio" name="has_def" value="0"> def ✗</label>
      </div>
      <span class="htmx-indicator" style="margin-left:8px;">loading…</span>
    </div>

    <!-- Row 2: tier + POS checkboxes -->
    <div class="filter-row">
      <span class="flabel">tier</span>
      <?php foreach ($tiers as [$v, $lbl]): ?>
      <label class="pill">
        <input type="checkbox" name="tier[]" value="<?= e($v) ?>" checked> <?= e($lbl) ?>
      </label>
      <?php endforeach; ?>
      <div class="fsep"></div>
      <span class="flabel">POS</span>
      <?php foreach ($POS_OPTIONS as [$val, $lbl]): ?>
      <label class="pill">
        <input type="checkbox" name="pos[]" value="<?= e($val) ?>" checked> <?= e($lbl) ?>
      </label>
      <?php endforeach; ?>
    </div>

    <!-- Row 3: taxonomy selects + reset -->
    <div class="filter-row">
      <span class="flabel">filter</span>
      <select name="register" class="tax-select" aria-label="Filter by register">
        <option value="">register: any</option>
        <?php foreach ($registers as $r): ?>
        <option value="<?= e($r) ?>"><?= e($r) ?></option>
        <?php endforeach; ?>
      </select>
      <select name="domain" class="tax-select" aria-label="Filter by domain">
        <option value="">domain: any</option>
        <?php foreach ($domains as $d): ?>
        <option value="<?= e($d) ?>"><?= e($d) ?></option>
        <?php endforeach; ?>
      </select>
      <select name="etymology" class="tax-select" aria-label="Filter by etymology">
        <option value="">etymology: any</option>
        <?php foreach ($etyms as $et): ?>
        <option value="<?= e($et) ?>"><?= e(str_replace('limba ', '', $et)) ?></option>
        <?php endforeach; ?>
      </select>
      <select name="dict_min" class="tax-select" data-default="" aria-label="Minimum dictionaries">
        <option value="">dicts: any</option>
        <option value="3">dicts ≥3</option>
        <option value="6">dicts ≥6</option>
        <option value="10">dicts ≥10</option>
        <option value="15">dicts ≥15</option>
      </select>
      <span id="dex-rare-control" style="display:none">
        <select name="dex_max" class="tax-select" data-default="0.60" aria-label="DEX frequency ceiling">
          <option value="all">DEX: all</option>
          <option value="0.60" selected>DEX-rare ≤0.60</option>
          <option value="0.50">DEX-rare ≤0.50</option>
          <option value="0.30">DEX-rare ≤0.30</option>
        </select>
      </span>
      <button type="reset" id="reset-filters" class="reset-btn" title="Reset all filters">reset</button>
    </div>

  </form>

  <div id="stats-page-content">
    <div id="stats-container"
         hx-get="<?= BASE ?>/api/stats.php"
         hx-trigger="load"
         hx-include="#filter-form"
         hx-swap="innerHTML">
      <span class="htmx-indicator" style="opacity:1;display:block;padding:32px;text-align:center;font-family:var(--serif);font-style:italic;color:var(--text-3);font-size:0.8125rem;">loading…</span>
    </div>
  </div>

  <div id="status-bar">
    <span class="status-left">
      <a href="<?= BASE ?>/"
         style="color:var(--text-2);text-decoration:none;font-family:var(--serif);font-style:italic;font-size:0.8125rem;"
         onmouseover="this.style.color='var(--text)'"
         onmouseout="this.style.color='var(--text-2)'">← cuvinte</a>
    </span>
    <span class="status-right">
      <div class="scale-stepper scale-stepper--sm" role="group" aria-label="Mărime text">
        <button type="button" class="scale-btn" data-scale-btn="down" onclick="stepTextScale(-1)" title="Text mai mic">A−</button>
        <button type="button" class="scale-btn" data-scale-btn="up" onclick="stepTextScale(1)" title="Text mai mare">A+</button>
      </div>
      <div class="theme-toggle theme-toggle--sm" role="group" aria-label="Temă">
        <button type="button" class="tg-btn" data-theme-btn="light" onclick="setTheme('light')" title="Temă deschisă">☀</button>
        <button type="button" class="tg-btn" data-theme-btn="dark" onclick="setTheme('dark')" title="Temă întunecată">☾</button>
      </div>
      <a href="<?= BASE ?>/metodologie.html"
         style="color:var(--text-3);text-decoration:none;font-size:0.75rem;"
         onmouseover="this.style.color='var(--text)'"
         onmouseout="this.style.color='var(--text-3)'">🧐 metodologie</a>
      &nbsp; &middot; &nbsp;
      <a href="https://github.com/gov2-ro/otzios" target="_blank" rel="noopener"
         style="color:var(--text-3);text-decoration:none;font-size:0.75rem;"
         onmouseover="this.style.color='var(--text)'"
         onmouseout="this.style.color='var(--text-3)'">GitHub</a>
    </span>
  </div>

  <script>
  // Theme + text-scale controls (same logic as app.js, no full app.js load needed)
  var TEXT_SCALE_STEPS = [87.5, 100, 112.5, 125, 137.5];
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
  function currentTextScale() { return parseFloat(document.documentElement.style.fontSize) || 100; }
  function nearestScaleIdx(val) {
    var idx = TEXT_SCALE_STEPS.indexOf(val);
    if (idx !== -1) return idx;
    var best = 0;
    TEXT_SCALE_STEPS.forEach(function(v, i) { if (Math.abs(v - val) < Math.abs(TEXT_SCALE_STEPS[best] - val)) best = i; });
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
  syncThemeButtons();
  syncScaleButtons();

  // DEX-rare control visibility (same logic as app.js, no full app.js load needed)
  (function() {
    var ctrl = document.getElementById('dex-rare-control');
    if (!ctrl) return;
    function sync() {
      var sel = document.querySelector('#filter-form input[name=word_tier]:checked');
      ctrl.style.display = (sel && sel.value === 'rare_in_use') ? '' : 'none';
    }
    document.querySelectorAll('#filter-form input[name=word_tier]')
      .forEach(function(r) { r.addEventListener('change', sync); });
    sync();
  })();

  // Tax-select active highlight
  document.querySelectorAll('.tax-select').forEach(function(sel) {
    var dflt = sel.dataset.default !== undefined ? sel.dataset.default : '';
    function update() { sel.classList.toggle('active', sel.value !== dflt); }
    sel.addEventListener('change', update);
    if (sel.form) sel.form.addEventListener('reset', update);
    update();
  });

  // Form reset: re-dispatch change so HTMX re-fires the stats request
  var form = document.getElementById('filter-form');
  if (form) form.addEventListener('reset', function() {
    setTimeout(function() {
      form.dispatchEvent(new Event('change', { bubbles: true }));
    }, 0);
  });
  </script>

</body>
</html>
