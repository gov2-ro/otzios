<?php
declare(strict_types=1);
require_once __DIR__ . '/api/_lib.php';

$total      = (int)db()->query("SELECT COUNT(*) FROM words WHERE word_tier='forgotten'")->fetchColumn();
$registers  = vocab('register');
$domains    = vocab('domain');
$etyms      = vocab('etymology');

$WOTD_FILTER = "word_tier='forgotten' AND has_definition=1 "
             . "AND (proper_noun_like IS NULL OR proper_noun_like=0) AND dict_count >= 3";
$wotd       = null;
$wotd_total = (int)db()->query("SELECT COUNT(*) FROM words WHERE $WOTD_FILTER")->fetchColumn();
if ($wotd_total > 0) {
    $seed = (int)floor(time() / 86400) % $wotd_total;
    $ws   = db()->prepare("SELECT word, definition FROM words WHERE $WOTD_FILTER ORDER BY word LIMIT 1 OFFSET ?");
    $ws->execute([$seed]);
    $wotd = $ws->fetch() ?: null;
}

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
  <link href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500&family=Public+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/htmx.org@2.0.4" integrity="sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+" crossorigin="anonymous"></script>
  <link rel="stylesheet" href="<?= BASE ?>/assets/app.css">
</head>
<body>

  <!-- ═══════════════════════════════════════
       BRAND BAR
  ══════════════════════════════════════════ -->
  <header class="brand-bar">
    <div class="brand-id">
      <span class="brand-name">otios</span>
      <span class="brand-sep"></span>
      <span class="brand-tag">cuvinte uitate</span>
    </div>

    <input id="search" form="filter-form"
           type="text" name="q" placeholder="caută un cuvânt…"
           hx-get="<?= BASE ?>/api/search.php" hx-trigger="input changed delay:200ms"
           hx-target="#word-list" hx-include="#filter-form, #search" autocomplete="off"
           title="Caută (diacriticele opționale: 'otios' găsește 'oțios')">

    <div class="brand-right">
      <span class="htmx-indicator brand-spinner" aria-hidden="true">…</span>
      <span id="result-count" class="result-count"><?= number_format((int)$total) ?></span>

      <!-- View toggle: cloud ⊞ / table ≡ -->
      <div class="view-toggle" id="view-toggle" role="group" aria-label="Mod de afișare">
        <button type="button" class="vt-btn vt-active" id="btn-cloud"
                onclick="setView('cloud')" title="Nor de cuvinte">⊞</button>
        <button type="button" class="vt-btn" id="btn-table"
                onclick="setView('table')" title="Tabel">≡</button>
      </div>

      <!-- Filter button (always visible) -->
      <button type="button" class="filter-toggle-btn" id="filter-toggle-btn"
              onclick="toggleFilterDrawer()" aria-label="Filtre">
        <svg width="16" height="11" viewBox="0 0 16 11" fill="none" aria-hidden="true">
          <rect width="16" height="2" rx="1" fill="currentColor"/>
          <rect y="4.5" width="11" height="2" rx="1" fill="currentColor"/>
          <rect y="9" width="7" height="2" rx="1" fill="currentColor"/>
        </svg>
        filtre <span class="filter-count-badge" id="filter-count-badge" style="display:none"></span>
      </button>
    </div>
  </header>

  <!-- ═══════════════════════════════════════
       WORD AREA (full width)
  ══════════════════════════════════════════ -->
  <div class="word-area">

    <div id="playlist-banner" style="display:none">
      <span id="playlist-count"></span>
      <button class="playlist-btn" onclick="copyPlaylistUrl()">copy URL</button>
      <button class="playlist-btn playlist-btn-exit" onclick="exitPlaylist()">✕ exit playlist</button>
    </div>

    <div id="active-filters" aria-label="Active filters"></div>

    <?php if ($wotd): ?>
    <div id="wotd-banner" data-word="<?= e($wotd['word']) ?>" style="display:none">
      <span class="wotd-label">cuvântul zilei</span>
      <button type="button" class="wotd-word" onclick="openWotd()"><?= e($wotd['word']) ?></button>
      <?php if (!empty($wotd['definition'])): ?>
      <span class="wotd-def"><?= e(mb_strimwidth($wotd['definition'], 0, 110, '…')) ?></span>
      <?php endif; ?>
      <button type="button" class="wotd-dismiss" onclick="dismissWotd()" aria-label="închide">✕</button>
    </div>
    <?php endif; ?>

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
             hx-include="#filter-form, #search"
             hx-swap="innerHTML">
          <span class="htmx-indicator">loading…</span>
        </div>
      </div>
      <div id="detail-panel"></div>
    </div>

  </div><!-- .word-area -->

  <!-- Status bar -->
  <div id="status-bar">
    <span class="status-left"><span id="status-word-count"><?= (int)$total ?></span> cuvinte · <span id="bookmark-count">0</span> favorite <button id="share-bookmarks-btn" onclick="shareBookmarks()" title="Copiază URL playlist" style="display:none">share ↗</button></span>
    <span class="status-right">
      <a href="<?= BASE ?>/joc.php">🎮 joc</a>
      <a href="<?= BASE ?>/stats.php">📊 statistici</a>
      <a href="<?= BASE ?>/metodologie.html">metodologie</a>
      <a href="https://github.com/gov2-ro/otzios" target="_blank" rel="noopener">GitHub</a>
      <a href="#" onclick="showShortcuts();return false;"><kbd>?</kbd></a>
    </span>
  </div>

  <!-- ═══════════════════════════════════════
       FILTER SHEET (always a bottom drawer)
  ══════════════════════════════════════════ -->
  <form id="filter-form"
        class="filter-sheet"
        hx-get="<?= BASE ?>/api/search.php"
        hx-trigger="change"
        hx-target="#word-list"
        hx-include="#filter-form, #search">

    <!-- Drag handle -->
    <div class="fs-handle-wrap"><div class="fs-handle"></div></div>

    <!-- Header -->
    <div class="fs-header">
      <span class="fs-title">Filtre</span>
      <button type="reset" id="reset-filters" class="fs-reset">resetează</button>
      <button type="button" class="fs-close" onclick="toggleFilterDrawer()">✕</button>
    </div>

    <!-- Scrollable body -->
    <div class="fs-body">

      <!-- Sort + tier -->
      <div class="fs-section fs-section-top">
        <div class="seg seg-sm fs-tier">
          <label class="seg-opt"><input type="radio" name="word_tier" value="forgotten" checked> uitate</label>
          <label class="seg-opt"><input type="radio" name="word_tier" value="rare_in_use"> rare</label>
        </div>
        <select name="sort" class="fs-sort">
          <option value="rare">↓ rarest modern</option>
          <option value="declined">↓ most declined</option>
          <option value="dex_freq">↓ DEX frequency</option>
          <option value="alpha">↕ alphabetical</option>
        </select>
      </div>

      <!-- Verdict -->
      <div class="fs-section">
        <div class="fs-label">verdict</div>
        <div class="fs-pills">
          <?php foreach ([
              ['extinct',         'v-ext',  'dispărut din uz', '#B14A2D', 'Prezent în corpus istoric, absent din cel modern'],
              ['declining',       'v-dec',  'în declin',       '#B8893A', 'Semnificativ mai comun istoric față de româneasca modernă'],
              ['historical_only', 'v-hist', 'doar istoric',    '#5E7184', 'Găsit doar în Wikisource (istoric), nu în CulturaX (modern)'],
              ['absent',          'v-abs',  'absent',          '#7C6A86', 'Niciun semnal în corpus — posibil cel mai uitat'],
          ] as [$v, $cls, $lbl, $color, $tip]): ?>
          <label class="fs-pill fs-pill-verdict fs-pill-<?= $cls ?>" title="<?= e($tip) ?>">
            <span class="fs-dot" style="background:<?= $color ?>"></span>
            <input type="checkbox" name="verdict[]" value="<?= e($v) ?>" checked>
            <?= e($lbl) ?>
          </label>
          <?php endforeach; ?>
        </div>
      </div>

      <!-- Nivel / Tier -->
      <div class="fs-section">
        <div class="fs-label">nivel</div>
        <?php
        $tier_tips = [
            'corpus_extinct'         => 'modern_ppm = 0, hist_ppm > 0',
            'corpus_declining'       => 'scădere log-ratio deasupra pragului',
            'corpus_historical_only' => 'Wikisource da, CulturaX nu',
            'dex_invechit_absent'    => '"învechit" în DEX + absent din corpus modern',
            'dex_absent_highfreq'    => 'Frecvență editorială DEX ridicată, dar zero prezenți în corpus',
        ];
        foreach ($tiers as [$v, $lbl]): ?>
        <label class="fs-pill" title="<?= e($tier_tips[$v] ?? $lbl) ?>">
          <span class="fs-check"></span>
          <input type="checkbox" name="tier[]" value="<?= e($v) ?>" checked>
          <?= e($lbl) ?>
        </label>
        <?php endforeach; ?>
      </div>

      <!-- Categorie / POS -->
      <div class="fs-section">
        <div class="fs-label">categorie</div>
        <div class="fs-pills fs-pills-pos">
          <?php foreach ($POS_OPTIONS as [$val, $lbl]): ?>
          <label class="fs-pill fs-pill-pos" title="<?= e($val) ?>">
            <span class="fs-check"></span>
            <input type="checkbox" name="pos[]" value="<?= e($val) ?>" checked>
            <?= e($lbl) ?>
          </label>
          <?php endforeach; ?>
        </div>
      </div>

      <!-- Taxonomy selects -->
      <div class="fs-section">
        <div class="fs-label">filtru</div>
        <select name="register" class="fs-select tax-select" data-default="" title="Filtru după registru DEX">
          <option value="">registru: orice</option>
          <?php foreach ($registers as $r): ?>
          <option value="<?= e($r) ?>"><?= e($r) ?></option>
          <?php endforeach; ?>
        </select>
        <select name="domain" class="fs-select tax-select" data-default="" title="Filtru după domeniu tehnic">
          <option value="">domeniu: orice</option>
          <?php foreach ($domains as $d): ?>
          <option value="<?= e($d) ?>"><?= e($d) ?></option>
          <?php endforeach; ?>
        </select>
        <select name="etymology" class="fs-select tax-select" data-default="" title="Filtru după limbă de origine">
          <option value="">etimologie: orice</option>
          <?php foreach ($etyms as $et): ?>
          <option value="<?= e($et) ?>"><?= e(str_replace('limba ', '', $et)) ?></option>
          <?php endforeach; ?>
        </select>
        <select name="dict_min" class="fs-select tax-select" data-default="" title="Arată doar cuvintele prezente în cel puțin N dicționare DEX">
          <option value="">dicționare: orice</option>
          <option value="3">≥ 3 dicționare</option>
          <option value="6">≥ 6 dicționare</option>
          <option value="10">≥ 10 dicționare</option>
          <option value="15">≥ 15 dicționare</option>
        </select>
        <span id="dex-rare-control" class="dex-rare-control" style="display:none">
          <select name="dex_max" class="fs-select tax-select" data-default="0.60">
            <option value="all">DEX: toate</option>
            <option value="0.60" selected>DEX-rar ≤0.60</option>
            <option value="0.50">DEX-rar ≤0.50</option>
            <option value="0.30">DEX-rar ≤0.30</option>
          </select>
        </span>
        <select name="marks" class="fs-select tax-select" data-default="all">
          <option value="all">toate cuvintele</option>
          <option value="unmarked">neanotate</option>
          <option value="marked">annotate</option>
          <option value="bookmarked">☆ favorite</option>
          <option value="noted">cu notă</option>
          <?php foreach ($QUICK_TAGS as [$tag, $key]): ?>
          <option value="tag:<?= e($tag) ?>">tag: <?= e($tag) ?></option>
          <?php endforeach; ?>
        </select>
        <div class="fs-row">
          <span class="fs-row-label">definiție</span>
          <div class="seg seg-sm">
            <label class="seg-opt"><input type="radio" name="has_def" value="" checked> orice</label>
            <label class="seg-opt"><input type="radio" name="has_def" value="1"> da ✓</label>
            <label class="seg-opt"><input type="radio" name="has_def" value="0"> nu ✗</label>
          </div>
        </div>
      </div>

      <!-- Explore: zipf, dexfreq, toggles -->
      <div class="fs-section">
        <div class="fs-label">explore</div>
        <?php if (db_has_column('zipf_frequency')): ?>
        <div class="fs-range-row" title="Scor Zipf română wordfreq (0–8)">
          <span class="fs-range-label">zipf</span>
          <input type="number" name="zipf_min" step="0.1" min="0" max="8" placeholder="min" class="fs-input">
          <span class="fs-range-sep">–</span>
          <input type="number" name="zipf_max" step="0.1" min="0" max="8" placeholder="max" class="fs-input">
        </div>
        <?php endif; ?>
        <div class="fs-range-row" title="Frecvență editorială DEX 0–100">
          <span class="fs-range-label">dex</span>
          <input type="number" name="dexfreq_min" step="1" min="0" max="100" placeholder="min" class="fs-input">
          <span class="fs-range-sep">–</span>
          <input type="number" name="dexfreq_max" step="1" min="0" max="100" placeholder="max" class="fs-input">
        </div>
        <?php if (db_has_column('en_zipf')): ?>
        <label class="fs-pill fs-pill-sm" title="Ascunde cuvintele comune în engleză (semnal de împrumut: en Zipf ≥ 4.0)">
          <span class="fs-check"></span>
          <input type="checkbox" name="hide_loanwords" value="1">
          ascunde împrumuturi
        </label>
        <?php endif; ?>
        <?php if (db_has_column('proper_noun_like')): ?>
        <label class="fs-pill fs-pill-sm" title="Ascunde headword-urile cu majusculă în DEX (nume, locuri, branduri)">
          <span class="fs-check"></span>
          <input type="checkbox" name="hide_proper" value="1">
          ascunde nume proprii
        </label>
        <?php endif; ?>
      </div>

      <!-- Play modes -->
      <div class="fs-section fs-section-play">
        <div class="fs-label">mod</div>
        <button type="button" class="fs-play-btn" onclick="surpriseWord(); toggleFilterDrawer();" title="Cuvânt aleator din selecția curentă (r)">🎲 la întâmplare</button>
        <button type="button" class="fs-play-btn" onclick="enterFeed(); toggleFilterDrawer();" title="Mod card: cuvânt cu cuvânt (f)">📇 feed</button>
      </div>

    </div><!-- .fs-body -->

    <!-- Apply button -->
    <div class="fs-footer">
      <button type="button" class="fs-apply" onclick="toggleFilterDrawer()">
        Arată <span id="result-count-sheet"><?= number_format((int)$total) ?></span> cuvinte
      </button>
    </div>

    <input type="hidden" id="playlist-words" name="words" value="">
  </form>

  <!-- Filter backdrop -->
  <div class="filter-backdrop" id="filter-backdrop" onclick="toggleFilterDrawer()"></div>

  <!-- Feed overlay -->
  <div id="feed-overlay" style="display:none">
    <div class="feed-top">
      <span class="feed-progress" id="feed-progress"></span>
      <button type="button" class="feed-exit" onclick="exitFeed()">✕ ieși</button>
    </div>
    <div class="feed-card" id="feed-card"></div>
    <div class="feed-actions">
      <button type="button" class="feed-skip" onclick="feedSkip()" title="sari (← / h)">✗ sari</button>
      <button type="button" class="feed-keep" onclick="feedKeep()" title="păstrează la favorite (→ / l)">★ păstrează</button>
    </div>
    <div class="feed-hint">← sari · păstrează → &nbsp;·&nbsp; sau glisează stânga/dreapta</div>
  </div>

  <datalist id="tag-suggestions"></datalist>

  <div id="shortcuts-overlay" style="display:none">
    <div id="shortcuts-modal">
      <div class="shortcuts-header">
        <span>Keyboard shortcuts</span>
        <span class="shortcuts-esc">Esc to close</span>
      </div>
      <table class="shortcuts-table">
        <tr><td colspan="2" class="shortcuts-group">Navigare</td></tr>
        <tr><td><kbd>j</kbd><kbd>k</kbd><kbd>h</kbd><kbd>l</kbd></td><td>Navigare grilă (↓ ↑ ← →)</td></tr>
        <tr><td><kbd>g</kbd><kbd>g</kbd></td><td>Salt la început</td></tr>
        <tr><td><kbd>G</kbd></td><td>Salt la final</td></tr>
        <tr><td colspan="2" class="shortcuts-group">Căutare</td></tr>
        <tr><td><kbd>/</kbd></td><td>Focus căutare</td></tr>
        <tr><td><kbd>r</kbd></td><td>Cuvânt aleator</td></tr>
        <tr><td><kbd>Esc</kbd></td><td>Închide</td></tr>
        <tr><td colspan="2" class="shortcuts-group">Acțiuni</td></tr>
        <tr><td><kbd>b</kbd></td><td>Toggle favorite</td></tr>
        <tr><td><kbd>i</kbd></td><td><em>ignore</em></td></tr>
        <tr><td><kbd>B</kbd></td><td><em>boring</em></td></tr>
        <tr><td><kbd>f</kbd></td><td><em>funny</em></td></tr>
        <tr><td><kbd>x</kbd></td><td><em>remove</em></td></tr>
        <tr><td><kbd>t</kbd></td><td>Focus tag input</td></tr>
        <tr><td><kbd>n</kbd></td><td>Focus notă</td></tr>
        <tr><td><kbd>o</kbd></td><td>Deschide dexonline.ro</td></tr>
        <tr><td><kbd>?</kbd></td><td>Arată / ascunde shortcut-uri</td></tr>
      </table>
    </div>
  </div>

  <script>var OTIOS_BASE = '<?= BASE ?>';</script>
  <script src="<?= BASE ?>/assets/app.js"></script>
  <script async src="https://scripts.simpleanalyticscdn.com/latest.js"></script>
  <noscript><img src="https://queue.simpleanalyticscdn.com/noscript.gif" alt="" referrerpolicy="no-referrer-when-downgrade"/></noscript>
</body>
</html>
