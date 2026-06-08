<?php
declare(strict_types=1);
require_once __DIR__ . '/api/_lib.php';

$total      = (int)db()->query("SELECT COUNT(*) FROM words WHERE word_tier='forgotten'")->fetchColumn();
$registers  = vocab('register');
$domains    = vocab('domain');
$etyms      = vocab('etymology');

global $QUICK_TAGS, $POS_OPTIONS;

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
  <title>Oțios — Cuvinte Uitate</title>
  <meta property="og:title" content="Oțios — cuvinte uitate">
  <meta property="og:description" content="Exploratory tool to identify forgotten Romanian words from official dictionaries that have fallen out of modern usage.">
  <meta property="og:image" content="<?= BASE ?>/screenshot-otzios.png">
  <meta property="og:type" content="website">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Mona+Sans:wght@400..700&family=Lora:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/htmx.org@2.0.4" integrity="sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+" crossorigin="anonymous"></script>
  <link rel="stylesheet" href="<?= BASE ?>/assets/app.css">
</head>
<body>
  <form id="filter-form"
        hx-get="<?= BASE ?>/api/search.php"
        hx-trigger="change"
        hx-target="#word-list"
        hx-include="#filter-form">

    <!-- Row 1: search + utility controls -->
    <div class="filter-row">
      <div class="seg">
        <label class="seg-opt"><input type="radio" name="word_tier" value="forgotten" checked> uitate</label>
        <label class="seg-opt"><input type="radio" name="word_tier" value="rare_in_use"> rare</label>
      </div>
      <div class="fsep"></div>
      <input id="search" type="text" name="q" placeholder="Search words…"
             hx-get="<?= BASE ?>/api/search.php" hx-trigger="input changed delay:200ms"
             hx-target="#word-list" hx-include="#filter-form" autocomplete="off">
      <select name="sort" class="sort-select">
        <option value="rare">↓ rarest modern</option>
        <option value="declined">↓ most declined</option>
        <option value="dex_freq">↓ DEX frequency</option>
        <option value="alpha">↕ alphabetical</option>
      </select>
      <div class="fsep"></div>
      <select name="marks" class="tax-select" data-default="all" aria-label="Marks filter">
        <option value="all">all words</option>
        <option value="unmarked">unmarked only</option>
        <option value="marked">marked only</option>
        <option value="bookmarked">☆ bookmarked</option>
        <option value="noted">has note</option>
        <?php foreach ($QUICK_TAGS as [$tag, $key]): ?>
        <option value="tag:<?= e($tag) ?>">tag: <?= e($tag) ?></option>
        <?php endforeach; ?>
      </select>
      <div class="seg">
        <label class="seg-opt"><input type="radio" name="has_def" value="" checked> any</label>
        <label class="seg-opt"><input type="radio" name="has_def" value="1"> def ✓</label>
        <label class="seg-opt"><input type="radio" name="has_def" value="0"> def ✗</label>
      </div>
      <span class="htmx-indicator">loading…</span>
      <span id="result-count" class="result-count"><?= number_format((int)$total) ?> words</span>
    </div>

    <!-- Row 2: tier + POS -->
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

    <!-- Row 3: taxonomy selects -->
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
      <span id="dex-rare-control" class="dex-rare-control" style="display:none">
        <select name="dex_max" class="tax-select" data-default="0.60" aria-label="Restrict rare tab to DEX-rare words">
          <option value="all">DEX: all</option>
          <option value="0.60" selected>DEX-rare ≤0.60</option>
          <option value="0.50">DEX-rare ≤0.50</option>
          <option value="0.30">DEX-rare ≤0.30</option>
        </select>
      </span>
      <button type="reset" id="reset-filters" class="reset-btn" title="Reset all filters">reset</button>
    </div>

  </form>

  <div id="app">
    <div id="hover-box">
      <div id="hb-word"></div>
      <div id="hb-verdict-row">
        <span id="hb-verdict" class="verdict-badge"></span>
        <span id="hb-meta"></span>
      </div>
      <div id="hb-def"></div>
    </div>
    <div id="word-list-container">
      <div id="word-list"
           hx-get="<?= BASE ?>/api/search.php"
           hx-trigger="load"
           hx-swap="innerHTML">
        <span class="htmx-indicator">loading…</span>
      </div>
    </div>
  </div>

  <div id="detail-panel"></div>

  <div id="status-bar">
    <span class="status-left"><span id="status-word-count"><?= (int)$total ?> words</span> · <span id="bookmark-count">0</span> bookmarked</span>
    <span class="status-right"><a href="<?= BASE ?>/metodologie.html" style="color:var(--text-3);text-decoration:none;font-size:12px;" onmouseover="this.style.color='var(--text)'" onmouseout="this.style.color='var(--text-3)'"><span style="transform: scale(1.3);">🧐</span> metodologie</a> &nbsp; &middot; &nbsp; <a href="https://github.com/gov2-ro/otzios" target="_blank" rel="noopener" style="color:var(--text-3);text-decoration:none;font-size:12px;" onmouseover="this.style.color='var(--text)'" onmouseout="this.style.color='var(--text-3)'">GitHub</a> &nbsp; &middot; &nbsp; <a href="#" onclick="showShortcuts();return false;" style="color:var(--text-3);text-decoration:none;font-size:12px;" onmouseover="this.style.color='var(--text)'" onmouseout="this.style.color='var(--text-3)'"><kbd>?</kbd> shortcuts</a></span>
  </div>

  <datalist id="tag-suggestions"></datalist>

  <div id="shortcuts-overlay" style="display:none">
    <div id="shortcuts-modal">
      <div class="shortcuts-header">
        <span>Keyboard shortcuts</span>
        <span class="shortcuts-esc">Esc to close</span>
      </div>
      <table class="shortcuts-table">
        <tr><td colspan="2" class="shortcuts-group">Navigation</td></tr>
        <tr><td><kbd>j</kbd><kbd>k</kbd><kbd>h</kbd><kbd>l</kbd></td><td>Navigate grid (↓ ↑ ← →)</td></tr>
        <tr><td><kbd>g</kbd><kbd>g</kbd></td><td>Jump to top</td></tr>
        <tr><td><kbd>G</kbd></td><td>Jump to bottom</td></tr>
        <tr><td colspan="2" class="shortcuts-group">Search</td></tr>
        <tr><td><kbd>/</kbd></td><td>Focus search</td></tr>
        <tr><td><kbd>Esc</kbd></td><td>Blur / close popup</td></tr>
        <tr><td colspan="2" class="shortcuts-group">Actions</td></tr>
        <tr><td><kbd>b</kbd></td><td>Toggle bookmark</td></tr>
        <tr><td><kbd>i</kbd></td><td>Toggle <em>ignore</em> tag</td></tr>
        <tr><td><kbd>B</kbd></td><td>Toggle <em>boring</em> tag</td></tr>
        <tr><td><kbd>f</kbd></td><td>Toggle <em>funny</em> tag</td></tr>
        <tr><td><kbd>x</kbd></td><td>Toggle <em>remove</em> tag</td></tr>
        <tr><td><kbd>t</kbd></td><td>Focus tag input (autocomplete)</td></tr>
        <tr><td><kbd>n</kbd></td><td>Focus note field</td></tr>
        <tr><td><kbd>o</kbd></td><td>Open in dexonline.ro</td></tr>
        <tr><td><kbd>?</kbd></td><td>Show / hide this popup</td></tr>
      </table>
    </div>
  </div>

  <script>var OTIOS_BASE = '<?= BASE ?>';</script>
  <script src="<?= BASE ?>/assets/app.js"></script>
  <script async src="https://scripts.simpleanalyticscdn.com/latest.js"></script>
  <noscript><img src="https://queue.simpleanalyticscdn.com/noscript.gif" alt="" referrerpolicy="no-referrer-when-downgrade"/></noscript>
</body>
</html>
