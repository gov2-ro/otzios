<?php
declare(strict_types=1);
require_once __DIR__ . '/api/_lib.php';

$total      = (int)db()->query("SELECT COUNT(*) FROM words WHERE word_tier='forgotten'")->fetchColumn();
$registers  = vocab('register');
$domains    = vocab('domain');
$etyms      = vocab('etymology');

// Cuvântul zilei — disabled. Flip to true to bring the banner back; the markup
// and the JS (openWotd/dismissWotd/initWotd) are still in place.
const SHOW_WOTD = false;

$WOTD_FILTER = "word_tier='forgotten' AND has_definition=1 "
             . "AND (proper_noun_like IS NULL OR proper_noun_like=0) AND dict_count >= 3";
$wotd = null;
if (SHOW_WOTD) {
    $wotd_total = (int)db()->query("SELECT COUNT(*) FROM words WHERE $WOTD_FILTER")->fetchColumn();
    if ($wotd_total > 0) {
        $seed = (int)floor(time() / 86400) % $wotd_total;
        $ws   = db()->prepare("SELECT word, definition FROM words WHERE $WOTD_FILTER ORDER BY word LIMIT 1 OFFSET ?");
        $ws->execute([$seed]);
        $wotd = $ws->fetch() ?: null;
    }
}

global $QUICK_TAGS, $POS_OPTIONS;

?>
<!DOCTYPE html>
<html lang="ro" data-skin="<?= DEFAULT_SKIN ?>">
<head>
  <meta charset="utf-8">
  <!-- No maximum-scale: blocking pinch-zoom fails WCAG 1.4.4, and this site is
       nothing but unfamiliar words. The in-app A−/A+ stepper is an addition to
       browser zoom, not a replacement for it. -->
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <?= otios_skin_boot() ?>
  <title>Oțios — Cuvinte Uitate</title>
  <meta property="og:title" content="Oțios — cuvinte uitate">
  <meta property="og:description" content="Exploratory tool to identify forgotten Romanian words from official dictionaries that have fallen out of modern usage.">
  <meta property="og:image" content="<?= BASE ?>/screenshot-otzios.png">
  <meta property="og:type" content="website">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&family=Public+Sans:ital,wght@0,400..800;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/htmx.org@2.0.4" integrity="sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+" crossorigin="anonymous"></script>
  <link rel="stylesheet" href="<?= BASE ?>/assets/app.css">
  <?= otios_skin_links() ?>
</head>
<body>

  <!-- ═══════════════════════════════════════
       BRAND BAR — shared shell, three slots of explorer-specific controls.
       Nav lives in the footer; see api/_partials/header.php for why.
  ══════════════════════════════════════════ -->
  <?php
  $page = 'index';

  ob_start(); ?>
    <!-- Opens the shortcuts/legend modal — explorer-only, so it rides along in
         $header_nav_extra rather than living in header.php itself. `kbd` is
         display:none below 768px (shortcuts mean nothing on a phone), which
         left this a zero-width tap target — and the modal is where the colour
         legend lives on narrow screens, since the footer legend hides below
         1280px. So the label falls back to a word there rather than
         disappearing. -->
    <a href="#" class="shortcuts-link" onclick="showShortcuts();return false;"
       title="Legendă și scurtături"><kbd>?</kbd><span class="shortcuts-alt">legendă</span></a>
  <?php $header_nav_extra = ob_get_clean();

  ob_start(); ?>
    <!-- Collapsed behind a magnifier by default — see openSearch()/closeSearchIfEmpty()
         in app.js. Opens on click, on the `/` shortcut, or already-open if the page
         loaded with a `q` in the URL (applyUrlToForm sets the value; the open check
         runs right after it). -->
    <div class="search-wrap" id="search-wrap">
      <button type="button" class="search-toggle-btn" id="search-toggle-btn"
              onclick="openSearch(true)" aria-label="Caută" aria-expanded="false"
              aria-controls="search" title="Caută (/)">
        <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="7" cy="7" r="5" stroke="currentColor" stroke-width="1.6"/>
          <line x1="11" y1="11" x2="15" y2="15" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
        </svg>
      </button>
      <input id="search" form="filter-form"
             type="text" name="q" placeholder="caută un cuvânt…"
             hx-get="<?= BASE ?>/api/search.php" hx-trigger="input changed delay:200ms"
             hx-target="#word-list" hx-include="#filter-form, #search" autocomplete="off"
             onblur="closeSearchIfEmpty()"
             title="Caută (diacriticele opționale: 'otios' găsește 'oțios')">
    </div>
  <?php $header_center = ob_get_clean();

  ob_start(); ?>
    <span class="htmx-indicator brand-spinner" aria-hidden="true">…</span>
    <span id="result-count" class="result-count"><?= number_format((int)$total) ?></span>
  <?php $header_tools = ob_get_clean();

  ob_start(); ?>
    <!-- Filter button — stays last in the bar, so it is the `$header_after` slot -->
    <button type="button" class="filter-toggle-btn" id="filter-toggle-btn"
            onclick="toggleFilterDrawer()" aria-label="Filtre" aria-expanded="false">
      <svg width="16" height="11" viewBox="0 0 16 11" fill="none" aria-hidden="true">
        <rect width="16" height="2" rx="1" fill="currentColor"/>
        <rect y="4.5" width="11" height="2" rx="1" fill="currentColor"/>
        <rect y="9" width="7" height="2" rx="1" fill="currentColor"/>
      </svg>
      filtre <span class="filter-count-badge" id="filter-count-badge" style="display:none"></span>
    </button>
  <?php $header_after = ob_get_clean();

  require __DIR__ . '/api/_partials/header.php';
  ?>

  <!-- ═══════════════════════════════════════
       LAYOUT ROW — filter rail (desktop) + word area.
       Below 1024px the rail leaves the flow and becomes a bottom drawer.
  ══════════════════════════════════════════ -->
  <div class="layout-row">

  <!-- ═══════════════════════════════════════
       FILTER SHEET / RAIL
  ══════════════════════════════════════════ -->
  <form id="filter-form"
        class="filter-sheet"
        hx-get="<?= BASE ?>/api/search.php"
        hx-trigger="change"
        hx-target="#word-list"
        hx-include="#filter-form, #search">

    <!-- Drag handle (drawer only) -->
    <div class="fs-handle-wrap"><div class="fs-handle"></div></div>

    <!-- Header -->
    <div class="fs-header">
      <span class="fs-title">Filtre</span>
      <button type="reset" id="reset-filters" class="fs-reset">resetează</button>
      <button type="button" class="fs-close" onclick="toggleFilterDrawer()">✕</button>
    </div>

    <!-- Shown only while a playlist is open (form gets data-playlist) — the server
         ignores the filters for a curated list, so the sheet has to say so rather
         than sit there looking live. -->
    <p class="fs-playlist-note">
      Listă deschisă — filtrele nu se aplică, ca să vezi toate cuvintele primite.
      Ieși din listă ca să filtrezi.
    </p>

    <!-- Scrollable body -->
    <div class="fs-body">

      <!-- Sort + tier -->
      <div class="fs-section fs-section-top">
        <div class="seg seg-sm fs-tier">
          <label class="seg-opt"><input type="radio" name="word_tier" value="forgotten" checked> uitate</label>
          <label class="seg-opt"><input type="radio" name="word_tier" value="rare_in_use"> rare</label>
        </div>
        <select name="sort" class="fs-sort">
          <?php if (db_has_column('quality_score')): ?>
          <option value="quality">↓ cele mai potrivite</option>
          <?php endif; ?>
          <option value="rare">↓ rarest modern</option>
          <option value="declined">↓ most declined</option>
          <option value="dex_freq">↓ DEX frequency</option>
          <?php if (db_has_column('newest_dict_year')): ?>
          <option value="attested">↑ ultima atestare</option>
          <?php endif; ?>
          <option value="alpha">↕ alphabetical</option>
        </select>
      </div>

      <?php if (db_has_column('seam')): ?>
      <!-- Seam: which of the two lists you are browsing. Hidden on the rare tab (JS) —
           those words are not split into seams. -->
      <div class="fs-section" id="seam-control">
        <div class="fs-label">listă</div>
        <div class="seg seg-sm">
          <label class="seg-opt"><input type="radio" name="seam" value="relevant" checked> relevante</label>
          <label class="seg-opt"><input type="radio" name="seam" value="curiosity"> curiozități</label>
          <label class="seg-opt"><input type="radio" name="seam" value="all"> toate</label>
        </div>
      </div>
      <?php endif; ?>

      <!-- Verdict -->
      <div class="fs-section">
        <div class="fs-label">verdict</div>
        <div class="fs-pills">
          <?php foreach (VERDICTS as $v => $meta): ?>
          <label class="fs-pill fs-pill-verdict fs-pill-<?= $meta['dot'] ?>" title="<?= e($meta['tip']) ?>">
            <span class="fs-dot" style="background:var(--<?= $meta['dot'] ?>)"></span>
            <input type="checkbox" name="verdict[]" value="<?= e($v) ?>" checked>
            <?= e($meta['label']) ?>
          </label>
          <?php endforeach; ?>
        </div>
      </div>

      <!-- Nivel / Tier -->
      <div class="fs-section">
        <div class="fs-label">nivel</div>
        <?php foreach (TIERS as $v => $meta): ?>
        <label class="fs-pill" title="<?= e($meta['tip']) ?>">
          <span class="fs-check"></span>
          <input type="checkbox" name="tier[]" value="<?= e($v) ?>" checked>
          <?= e($meta['label']) ?>
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
        <?php if (db_has_column('newest_dict_year')): ?>
        <!-- Cel mai recent dicționar care încă tipărește cuvântul, ca interval — după
             Y1, înainte de Y2. Aproape tot ce răspunde la asta stă în seamul
             „curiozități”: „relevante” cere deja prezența într-un dicționar de după
             2005, deci „după” e aproape mereu adevărat acolo și „înainte” aproape
             mereu fals. -->
        <select name="attested_after" class="fs-select tax-select" data-default=""
                title="Cel mai recent dicționar în care apare cuvântul e din anul ales sau mai nou">
          <option value="">ultima atestare (după): oricând</option>
          <option value="1970">după 1970</option>
          <option value="1990">după 1990</option>
          <option value="2005">după 2005</option>
          <option value="2010">după 2010</option>
        </select>
        <select name="attested_before" class="fs-select tax-select" data-default=""
                title="Cel mai recent dicționar în care apare cuvântul e mai vechi de anul ales">
          <option value="">ultima atestare (înainte): oricând</option>
          <option value="1970">înainte de 1970</option>
          <option value="1990">înainte de 1990</option>
          <option value="2005">înainte de 2005</option>
          <option value="2010">înainte de 2010</option>
        </select>
        <?php endif; ?>
        <!-- Both of these mean something only on the „rare" tab, so JS shows them only
             there. `hide_loanwords` matches 6 of the 110 rare words and none at all of
             the 17.5k forgotten ones — in the main sheet it was a switch with nothing
             behind it. -->
        <span id="dex-rare-control" class="dex-rare-control" style="display:none">
          <select name="dex_max" class="fs-select tax-select" data-default="all">
            <option value="all" selected>DEX: toate</option>
            <option value="0.60">DEX-rar ≤0.60</option>
            <option value="0.50">DEX-rar ≤0.50</option>
            <option value="0.30">DEX-rar ≤0.30</option>
          </select>
          <?php if (db_has_column('en_zipf')): ?>
          <label class="fs-pill fs-pill-sm" title="Ascunde cuvintele comune în engleză (semnal de împrumut: en Zipf ≥ 4.0)">
            <span class="fs-check"></span>
            <input type="checkbox" name="hide_loanwords" value="1">
            ascunde împrumuturi
          </label>
          <?php endif; ?>
        </span>
        <!-- „marcate" rather than „adnotate": the values cover every kind of meta
             a reader can leave on a word — fav, a quick tag, a custom tag, a note —
             and only the last of those is an annotation in the ordinary sense. The
             option *values* stay `marked`/`unmarked` because they are URL state and
             `markedWordsForFilter()` in app.js reads them. -->
        <select name="marks" class="fs-select tax-select" data-default="all">
          <option value="all">toate cuvintele</option>
          <option value="unmarked">nemarcate</option>
          <option value="marked">marcate</option>
          <option value="bookmarked">☆ favorite</option>
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

      <!-- Clase speciale — one three-state control each, „fără / cu / doar".
           These were six checkboxes, and the polarity had to differ per class because an
           unchecked box submits nothing: three read „arată X" and two „ascunde X", which
           looked like one set of controls and behaved like two. A radio always submits,
           so all four read the same way now and only the default differs — diminutivele
           are the one class shown by default. „doar" on several means their union; see
           build_word_filter() in api/_lib.php. -->
      <div class="fs-section" id="class-control">
        <div class="fs-label">clase</div>
        <?php
        $CLASS_ROWS = array_values(array_filter([
          ['regional', 'regional_only', 'regionalisme', 'hide',
           'Cuvinte marcate doar regional/dialectal, fără să fie și învechite.'],
          ['variants', 'variant_like', 'variante vechi', 'hide',
           'Grafii vechi ale unor cuvinte încă folosite (politeță/politețe, uleu/ulei), detectate prin paradigma comună.'],
          ['spellings', 'archaic_spelling', 'grafii vechi', 'hide',
           'Grafii ieșite din uz ale unor cuvinte foarte vii: situațiune → situație, sgomot → zgomot, advocat → avocat.'],
          ['diminutives', 'diminutive_like', 'diminutive', 'show',
           'Diminutive (noruleț, cuconiță, fecioraș) — cuvinte pe care DEX le definește ca „diminutiv al lui…”.'],
        ], function ($row) { return db_has_column($row[1]); }));
        ?>
        <?php foreach ($CLASS_ROWS as [$name, $col, $label, $default, $tip]): ?>
        <div class="fs-row" title="<?= e($tip) ?>">
          <span class="fs-row-label"><?= e($label) ?></span>
          <div class="seg seg-sm">
            <label class="seg-opt"><input type="radio" name="<?= e($name) ?>" value="hide"<?= $default === 'hide' ? ' checked' : '' ?>> fără</label>
            <label class="seg-opt"><input type="radio" name="<?= e($name) ?>" value="show"<?= $default === 'show' ? ' checked' : '' ?>> cu</label>
            <label class="seg-opt"><input type="radio" name="<?= e($name) ?>" value="only"> doar</label>
          </div>
        </div>
        <?php endforeach; ?>
      </div>

      <!-- Explore: numeric ranges (zipf, DEX frequency) -->
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
      </div>

    </div><!-- .fs-body -->

    <!-- Apply button (drawer only) -->
    <div class="fs-footer">
      <button type="button" class="fs-apply" onclick="toggleFilterDrawer()">
        Arată <span id="result-count-sheet"><?= number_format((int)$total) ?></span> cuvinte
      </button>
    </div>

    <!-- Playlist transport. `w` is the compact form (base36 word ids, pack_words() in
         api/_lib.php) and is what new links use; `words` is the plaintext form, kept
         so links shared before the codec still load. -->
    <input type="hidden" id="playlist-w" name="w" value="">
    <input type="hidden" id="playlist-words" name="words" value="">
  </form>

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
        <!-- A listbox with a roving tabindex, not 25k tab stops. Tab reaches the list
             once and lands on the selected word (or the first one); j/k/arrows move
             within it and carry the tabindex along. See selectRow() in app.js. -->
        <div id="word-list"
             role="listbox"
             aria-label="Cuvinte"
             tabindex="0"
             hx-get="<?= BASE ?>/api/search.php"
             hx-trigger="load"
             hx-include="#filter-form, #search"
             hx-swap="innerHTML">
          <span class="htmx-indicator">loading…</span>
        </div>
      </div>
      <div id="detail-panel" class="word-detail-panel"></div>
    </div>

  </div><!-- .word-area -->
  </div><!-- .layout-row -->

  <!-- Status bar — shared nav, plus the one thing only the explorer has -->
  <?php
  ob_start(); ?>
    <span id="status-word-count"><?= (int)$total ?></span> cuvinte · <span id="bookmark-count">0</span> favorite
    <button id="share-bookmarks-btn" onclick="shareBookmarks()" title="Copiază URL playlist" style="display:none">share ↗</button>
  <?php $footer_left = ob_get_clean();

  ob_start(); ?>
    <!-- Legend. The cloud encodes four things with no label anywhere on the
         page: the word's colour (beton) or its dot (paper), two different
         underlines, and the superscript. Hidden below 1280px, where the bar has
         no room — the same legend is in the ? modal for narrow screens. -->
    <span class="status-legend" aria-label="Legendă">
      <span class="lg"><i class="lg-sw lg-sw-ext"></i>dispărut</span>
      <span class="lg"><i class="lg-sw lg-sw-dec"></i>declin</span>
      <span class="lg"><i class="lg-sw lg-sw-hist"></i>istoric</span>
      <span class="lg"><i class="lg-sw lg-sw-abs"></i>absent</span>
      <span class="lg-sep"></span>
      <span class="lg"><i class="lg-mark lg-inv">învechit</i></span>
      <span class="lg"><i class="lg-mark lg-fav">favorit</i></span>
      <span class="lg"><i class="lg-freq">42</i>frecvență DEX</span>
    </span>
  <?php $footer_extra = ob_get_clean();

  ob_start(); ?>
    <!-- Play modes (moved out of the filter panel — always reachable). Both
         hidden pending a home for them outside the footer: 🎲/surpriseWord()
         stays bound to the `r` shortcut, 📇/enterFeed() has no shortcut of its
         own yet. Either can come back by unhiding it. -->
    <div class="play-group" role="group" aria-label="Moduri de joc">
      <button type="button" class="play-btn" onclick="surpriseWord()" hidden
              title="Cuvânt aleator din selecția curentă (r)">🎲 <span class="play-label">la întâmplare</span></button>
      <button type="button" class="play-btn" onclick="enterFeed()" hidden
              title="Mod card: cuvânt cu cuvânt (f)">📇 <span class="play-label">feed</span></button>
    </div>

    <!-- View toggle: cloud ⊞ / table ≡ -->
    <div class="view-toggle" id="view-toggle" role="group" aria-label="Mod de afișare">
      <button type="button" class="vt-btn vt-active" id="btn-cloud" aria-pressed="true"
              onclick="setView('cloud')" title="Nor de cuvinte" aria-label="Nor de cuvinte">⊞</button>
      <button type="button" class="vt-btn" id="btn-table" aria-pressed="false"
              onclick="setView('table')" title="Tabel" aria-label="Tabel">≡</button>
    </div>
  <?php $footer_tools = ob_get_clean();

  require __DIR__ . '/api/_partials/footer.php';
  ?>

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

  <div id="shortcuts-overlay" style="display:none">
    <div id="shortcuts-modal">
      <div class="shortcuts-header">
        <span>Legendă și scurtături</span>
        <span class="shortcuts-esc">Esc pentru închidere</span>
      </div>
      <table class="shortcuts-table">
        <!-- Legend first: the cloud encodes two things with no label on them —
             the superscript number and (in the beton skin, which drops the
             verdict dot) the colour of the word itself. -->
        <tr><td colspan="2" class="shortcuts-group">Legendă</td></tr>
        <!-- Not "cu cât e mai mic, cu atât e mai rar", which is what this said and is
             the exact confusion the methodology page exists to clear up: the number is
             lexicographic prominence, so zapciu (dispărut) sits at 96 and internet at 88. -->
        <tr><td><span class="legend-freq">42</span></td>
            <td>Frecvență DEX, <strong>0–100</strong> — cât de central e cuvântul în dicționar,
                nu cât de des e folosit
                (<a href="<?= BASE ?>/metodologie.html#frecvente">explicație</a>)</td></tr>
        <tr><td><span class="legend-sw" style="background:var(--v-ext-word,var(--v-ext))"></span></td>
            <td><em>dispărut din uz</em> — niciun semnal modern</td></tr>
        <tr><td><span class="legend-sw" style="background:var(--v-dec-word,var(--v-dec))"></span></td>
            <td><em>în declin</em> — încă folosit, dar tot mai rar</td></tr>
        <tr><td><span class="legend-sw" style="background:var(--v-hist-word,var(--v-hist))"></span></td>
            <td><em>doar istoric</em> — apare doar în surse istorice</td></tr>
        <tr><td><span class="legend-sw" style="background:var(--v-abs-word,var(--v-abs))"></span></td>
            <td><em>absent</em> — niciun semnal în corpus, posibil cel mai uitat</td></tr>
        <tr><td colspan="2" class="shortcuts-group">Navigare</td></tr>
        <tr><td><kbd>j</kbd><kbd>k</kbd><kbd>h</kbd><kbd>→</kbd></td><td>Navigare grilă (↓ ↑ ← →) — <kbd>l</kbd> e liber pentru <em>lol</em></td></tr>
        <tr><td><kbd>g</kbd><kbd>g</kbd></td><td>Salt la început</td></tr>
        <tr><td><kbd>G</kbd></td><td>Salt la final</td></tr>
        <tr><td colspan="2" class="shortcuts-group">Căutare</td></tr>
        <tr><td><kbd>/</kbd></td><td>Focus căutare</td></tr>
        <tr><td><kbd>r</kbd></td><td>Cuvânt aleator</td></tr>
        <tr><td><kbd>Esc</kbd></td><td>Închide</td></tr>
        <tr><td colspan="2" class="shortcuts-group">Acțiuni</td></tr>
        <tr><td><kbd>f</kbd></td><td><em>fav</em> — păstrează</td></tr>
        <tr><td><kbd>a</kbd></td><td><em>ascunde</em> — neinteresant, prea cunoscut</td></tr>
        <tr><td><kbd>l</kbd></td><td><em>lol</em> — amuzant</td></tr>
        <tr><td><kbd>m</kbd></td><td><em>meh</em> — ca <em>ascunde</em>, zis altfel</td></tr>
        <tr><td><kbd>o</kbd></td><td>Deschide dexonline.ro</td></tr>
        <tr><td><kbd>?</kbd></td><td>Arată / ascunde shortcut-uri</td></tr>
      </table>
    </div>
  </div>

  <script>var OTIOS_BASE = '<?= BASE ?>';</script>
  <script src="<?= BASE ?>/assets/prefs.js"></script>
  <script src="<?= BASE ?>/assets/store.js"></script>
  <script src="<?= BASE ?>/assets/app.js"></script>
  <script async src="https://scripts.simpleanalyticscdn.com/latest.js"></script>
  <noscript><img src="https://queue.simpleanalyticscdn.com/noscript.gif" alt="" referrerpolicy="no-referrer-when-downgrade"/></noscript>
</body>
</html>
