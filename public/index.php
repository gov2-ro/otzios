<?php
declare(strict_types=1);
require_once __DIR__ . '/api/_lib.php';

$total      = (int)db()->query("SELECT COUNT(*) FROM words WHERE word_tier='forgotten'")->fetchColumn();
$registers  = vocab('register');
$domains    = vocab('domain');
$etyms      = vocab('etymology');

// Word of the day — deterministic daily pick over a "good" subset (has a definition,
// established headword, not a proper noun). Same word for everyone on a given day.
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
      <div class="seg" title="Switch between forgotten words (absent from modern corpora) and rare words (low but non-zero modern frequency)">
        <label class="seg-opt"><input type="radio" name="word_tier" value="forgotten" checked> uitate</label>
        <label class="seg-opt"><input type="radio" name="word_tier" value="rare_in_use"> rare</label>
      </div>
      <div class="fsep"></div>
      <input id="search" type="text" name="q" placeholder="Search words…"
             hx-get="<?= BASE ?>/api/search.php" hx-trigger="input changed delay:200ms"
             hx-target="#word-list" hx-include="#filter-form" autocomplete="off"
             title="Search by word (diacritic-insensitive: 'otios' matches 'oțios')">
      <select name="sort" class="sort-select" title="Sort order">
        <option value="rare">↓ rarest modern</option>
        <option value="declined">↓ most declined</option>
        <option value="dex_freq">↓ DEX frequency</option>
        <option value="alpha">↕ alphabetical</option>
      </select>
      <div class="fsep"></div>
      <select name="marks" class="tax-select" data-default="all" aria-label="Marks filter" title="Filter by your annotations (bookmarks, notes, tags)">
        <option value="all">all words</option>
        <option value="unmarked">unmarked only</option>
        <option value="marked">marked only</option>
        <option value="bookmarked">☆ bookmarked</option>
        <option value="noted">has note</option>
        <?php foreach ($QUICK_TAGS as [$tag, $key]): ?>
        <option value="tag:<?= e($tag) ?>">tag: <?= e($tag) ?></option>
        <?php endforeach; ?>
      </select>
      <div class="seg" title="Show all words, or restrict to words with / without a local definition">
        <label class="seg-opt"><input type="radio" name="has_def" value="" checked> any</label>
        <label class="seg-opt"><input type="radio" name="has_def" value="1"> def ✓</label>
        <label class="seg-opt"><input type="radio" name="has_def" value="0"> def ✗</label>
      </div>
      <button type="button" id="surprise-btn" class="play-btn" onclick="surpriseWord()" title="Cuvânt la întâmplare din selecția curentă (r)">🎲 surprise</button>
      <button type="button" id="feed-btn" class="play-btn" onclick="enterFeed()" title="Mod card: explorează cuvânt cu cuvânt, păstrează sau sari">📇 feed</button>
      <span class="htmx-indicator">loading…</span>
      <span id="result-count" class="result-count"><?= number_format((int)$total) ?> words</span>
    </div>

    <!-- Row 2: verdict + tier + POS + taxonomy selects -->
    <div class="filter-row filter-row-filters">
      <span class="flabel" title="Diachronic verdict: how word usage has changed between historical (Wikisource) and modern (CulturaX) corpora">verdict</span>
      <?php foreach ([
          ['extinct',        'pv-ext',  'extinct',    'Present in historical corpus, absent from modern — usage has disappeared'],
          ['declining',      'pv-dec',  'declining',  'Significantly more common historically than in modern Romanian text'],
          ['historical_only','pv-hist', 'historical', 'Found only in Wikisource (historical), not in CulturaX (modern web)'],
          ['absent',         'pv-abs',  'absent',     'No corpus signal at all — potentially the most forgotten; includes words never digitised'],
      ] as [$v, $cls, $lbl, $tip]): ?>
      <label class="pill <?= e($cls) ?>" title="<?= e($tip) ?>">
        <input type="checkbox" name="verdict[]" value="<?= e($v) ?>" checked> <?= e($lbl) ?>
      </label>
      <?php endforeach; ?>
      <div class="fsep fsep-tall"></div>
      <span class="flabel" title="Confidence tier: why this word was classified as forgotten">tier</span>
      <?php
      $tier_tips = [
          'corpus_extinct'         => 'Corpus evidence: modern_ppm = 0, hist_ppm > 0',
          'corpus_declining'       => 'Corpus evidence: log-ratio decline above threshold',
          'corpus_historical_only' => 'Found in Wikisource but absent from CulturaX',
          'dex_invechit_absent'    => 'Marked "învechit" (archaic) in DEX and absent from modern corpus',
          'dex_absent_highfreq'    => 'High DEX editorial frequency but zero corpus presence — possibly overlooked',
      ];
      foreach ($tiers as [$v, $lbl]): ?>
      <label class="pill" title="<?= e($tier_tips[$v] ?? $lbl) ?>">
        <input type="checkbox" name="tier[]" value="<?= e($v) ?>" checked> <?= e($lbl) ?>
      </label>
      <?php endforeach; ?>
      <div class="fsep"></div>
      <span class="flabel" title="Part of speech">POS</span>
      <?php foreach ($POS_OPTIONS as [$val, $lbl]): ?>
      <label class="pill" title="<?= e($val) ?>">
        <input type="checkbox" name="pos[]" value="<?= e($val) ?>" checked> <?= e($lbl) ?>
      </label>
      <?php endforeach; ?>
      <div class="fsep fsep-tall"></div>
      <span class="flabel" title="Narrow by DEX taxonomy metadata">filter</span>
      <select name="register" class="tax-select" aria-label="Filter by register" title="Filter by DEX register tag (archaic, dialectal, rare, etc.)">
        <option value="">register: any</option>
        <?php foreach ($registers as $r): ?>
        <option value="<?= e($r) ?>"><?= e($r) ?></option>
        <?php endforeach; ?>
      </select>
      <select name="domain" class="tax-select" aria-label="Filter by domain" title="Filter by technical domain — note: a word appears here if any of its senses carry this domain tag, not necessarily the primary meaning">
        <option value="">domain: any</option>
        <?php foreach ($domains as $d): ?>
        <option value="<?= e($d) ?>"><?= e($d) ?></option>
        <?php endforeach; ?>
      </select>
      <select name="etymology" class="tax-select" aria-label="Filter by etymology" title="Filter by language of origin as tagged in DEX">
        <option value="">etymology: any</option>
        <?php foreach ($etyms as $et): ?>
        <option value="<?= e($et) ?>"><?= e(str_replace('limba ', '', $et)) ?></option>
        <?php endforeach; ?>
      </select>
      <select name="dict_min" class="tax-select" data-default="" aria-label="Minimum dictionaries" title="Show only words listed in at least N distinct DEX dictionaries — higher = more established headword">
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
      <button type="reset" id="reset-filters" class="reset-btn" title="Reset all filters to defaults">reset</button>
    </div>

    <!-- Row 3: explore filters -->
    <div class="filter-row filter-row-explore">
      <span class="flabel">explore</span>
      <?php if (db_has_column('zipf_frequency')): ?>
      <span class="explore-range" title="wordfreq Romanian Zipf score (0–8)">zipf
        <input type="number" name="zipf_min" step="0.1" min="0" max="8" placeholder="min" class="explore-input">–<input type="number" name="zipf_max" step="0.1" min="0" max="8" placeholder="max" class="explore-input">
      </span>
      <div class="fsep"></div>
      <?php endif; ?>
      <span class="explore-range" title="DEX editorial frequency 0–100">dex
        <input type="number" name="dexfreq_min" step="1" min="0" max="100" placeholder="min" class="explore-input">–<input type="number" name="dexfreq_max" step="1" min="0" max="100" placeholder="max" class="explore-input">
      </span>
      <?php if (db_has_column('en_zipf')): ?>
      <div class="fsep"></div>
      <label class="pill" title="Hide words common in English (loanword signal: en Zipf ≥ 4.0)">
        <input type="checkbox" name="hide_loanwords" value="1"> hide loanwords
      </label>
      <?php endif; ?>
      <?php if (db_has_column('proper_noun_like')): ?>
      <label class="pill" title="Hide headwords capitalized in DEX (names / places / brands)">
        <input type="checkbox" name="hide_proper" value="1"> hide proper nouns
      </label>
      <?php endif; ?>
    </div>

    <input type="hidden" id="playlist-words" name="words" value="">
  </form>

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
           hx-include="#filter-form"
           hx-swap="innerHTML">
        <span class="htmx-indicator">loading…</span>
      </div>
    </div>
  </div>

  <div id="detail-panel"></div>

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

  <div id="status-bar">
    <span class="status-left"><span id="status-word-count"><?= (int)$total ?> words</span> · <span id="bookmark-count">0</span> bookmarked <button id="share-bookmarks-btn" onclick="shareBookmarks()" title="Copy bookmark playlist URL" style="display:none">share ↗</button></span>
    <span class="status-right"><a href="<?= BASE ?>/joc.php" style="color:var(--text-3);text-decoration:none;font-size:12px;" onmouseover="this.style.color='var(--text)'" onmouseout="this.style.color='var(--text-3)'">🎮 joc</a> &nbsp; &middot; &nbsp; <a href="<?= BASE ?>/stats.php" style="color:var(--text-3);text-decoration:none;font-size:12px;" onmouseover="this.style.color='var(--text)'" onmouseout="this.style.color='var(--text-3)'">📊 statistici</a> &nbsp; &middot; &nbsp; <a href="<?= BASE ?>/metodologie.html" style="color:var(--text-3);text-decoration:none;font-size:12px;" onmouseover="this.style.color='var(--text)'" onmouseout="this.style.color='var(--text-3)'"><span style="transform: scale(1.3);">🧐</span> metodologie</a> &nbsp; &middot; &nbsp; <a href="https://github.com/gov2-ro/otzios" target="_blank" rel="noopener" style="color:var(--text-3);text-decoration:none;font-size:12px;" onmouseover="this.style.color='var(--text)'" onmouseout="this.style.color='var(--text-3)'">GitHub</a> &nbsp; &middot; &nbsp; <a href="#" onclick="showShortcuts();return false;" style="color:var(--text-3);text-decoration:none;font-size:12px;" onmouseover="this.style.color='var(--text)'" onmouseout="this.style.color='var(--text-3)'"><kbd>?</kbd> shortcuts</a></span>
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
        <tr><td colspan="2" class="shortcuts-group">Search &amp; explore</td></tr>
        <tr><td><kbd>/</kbd></td><td>Focus search</td></tr>
        <tr><td><kbd>r</kbd></td><td>Cuvânt la întâmplare (surprise)</td></tr>
        <tr><td><kbd>Esc</kbd></td><td>Blur / close popup</td></tr>
        <tr><td colspan="2" class="shortcuts-group">Actions</td></tr>
        <tr><td><kbd>b</kbd></td><td>Toggle bookmark</td></tr>
        <tr><td><kbd>i</kbd></td><td><em>ignore</em> — neinteresant pentru tine (skip)</td></tr>
        <tr><td><kbd>B</kbd></td><td><em>boring</em> — plictisitor</td></tr>
        <tr><td><kbd>f</kbd></td><td><em>funny</em> — amuzant</td></tr>
        <tr><td><kbd>x</kbd></td><td><em>remove</em> — nu e cu adevărat uitat (exclude)</td></tr>
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
