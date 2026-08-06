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
<html lang="ro" data-skin="<?= DEFAULT_SKIN ?>">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
  <?= otios_skin_boot() ?>
  <title>Oțios — Statistici</title>
  <meta property="og:title" content="Oțios — statistici">
  <meta property="og:description" content="Statistical breakdown of forgotten Romanian words: etymology, parts of speech, registers, domains, and more.">
  <meta property="og:type" content="website">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&family=Public+Sans:ital,wght@0,400..800;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/htmx.org@2.0.4" integrity="sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+" crossorigin="anonymous"></script>
  <link rel="stylesheet" href="<?= BASE ?>/assets/app.css">
  <?= otios_skin_links() ?>
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
      <a href="<?= BASE ?>/" class="status-home">← cuvinte</a>
    </span>
    <span class="status-right">
      <div class="scale-stepper scale-stepper--sm" role="group" aria-label="Mărime text">
        <button type="button" class="scale-btn" data-scale-btn="down" onclick="stepTextScale(-1)" title="Text mai mic">A−</button>
        <button type="button" class="scale-btn" data-scale-btn="up" onclick="stepTextScale(1)" title="Text mai mare">A+</button>
      </div>
      <?= otios_skin_select("skin-select--sm") ?>
      <div class="theme-toggle theme-toggle--sm" role="group" aria-label="Temă">
        <button type="button" class="tg-btn" data-theme-btn="light" onclick="setTheme('light')" title="Temă deschisă">☀</button>
        <button type="button" class="tg-btn" data-theme-btn="dark" onclick="setTheme('dark')" title="Temă întunecată">☾</button>
      </div>
      <a href="<?= BASE ?>/metodologie.html">🧐 metodologie</a>
      <a href="https://github.com/gov2-ro/otzios" target="_blank" rel="noopener">GitHub</a>
    </span>
  </div>

  <script src="<?= BASE ?>/assets/prefs.js"></script>
  <script>
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
