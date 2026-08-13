<?php
declare(strict_types=1);
require_once __DIR__ . '/api/_appdb.php';

// What everyone marked: /colectii.php
//
// Marking words is the site's main triage loop, and until 2026-08-13 the marks went
// exactly two places — your own three buckets on /liste, and a damped nudge in the
// `populare` sort. Nobody could see what anyone else had marked, so „colecții" in the nav
// meant three empty cards to every visitor who had not marked anything yet.
//
// Two tabs, both ranked across all visitors: ★+🤣 („îndrăgite") and ⛔️ („respinse").
//
// **No current_user() call anywhere in this file, and _appdb.php rather than _auth.php.**
// This is a public read; touching the identity would mint a device token for every
// passing crawler, which is the trap lista.php already documents at its own guard.
//
// **Marks still only ever add.** This page is a surface, not a filter: nothing here
// removes a word from the explorer, reorders a search, or subtracts from anyone's view.
// That is the same invariant vote_counts_subquery() is built on, and the reason a page
// driven by anonymous device tokens is safe to publish at all.

const AGG_LIMIT = 200;

$tabs = [
    'indragite' => ['col' => 'n_up',   'label' => 'îndrăgite', 'emoji' => '★'],
    'respinse'  => ['col' => 'n_down', 'label' => 'respinse',  'emoji' => '⛔️'],
];

$tab = isset($_GET['t']) && isset($tabs[$_GET['t']]) ? (string) $_GET['t'] : 'indragite';
$col = $tabs[$tab]['col'];          // whitelisted above — never interpolated from input

$rows       = [];
$tab_counts = ['indragite' => 0, 'respinse' => 0];
$n_marks    = 0;
$n_people   = 0;
$have_db    = attach_app_db();

if ($have_db) {
    $agg = mark_counts_subquery();

    // quality_score breaks ties among the many words sitting at one or two marks. Guarded
    // the way search.php guards its fallback sort: the column is a build-time product of
    // make_shortlist.py, and an older ui.db may predate it.
    $tiebreak = db_has_column('quality_score')
        ? 'COALESCE(w.quality_score, 0) DESC'
        : 'w.dex_frequency DESC';

    // INNER JOIN on purpose: a word can outlive a data rebuild in app.db and vanish from
    // ui.db, and there is nothing to show for one — the same survivors-only rule
    // liste.php gets from filter_existing_words().
    $stmt = db()->query(
        "SELECT w.word, w.definition, w.dex_pos, w.dex_register,
                m.n_fav, m.n_lol, m.n_up, m.n_down
           FROM words w
           JOIN ($agg) m ON m.mark_word = w.word
          WHERE m.$col > 0
          ORDER BY m.$col DESC, $tiebreak, w.word ASC
          LIMIT " . AGG_LIMIT
    );
    $rows = $stmt->fetchAll();

    // Counted through the same JOIN the rows use, or the tab would advertise a number the
    // page cannot show: words that left ui.db in a rebuild still carry marks in app.db,
    // and on the fixture data that is a tab reading 70 above a list of 67.
    $c = db()->query(
        "SELECT SUM(CASE WHEN m.n_up   > 0 THEN 1 ELSE 0 END) AS n_indragite,
                SUM(CASE WHEN m.n_down > 0 THEN 1 ELSE 0 END) AS n_respinse
           FROM ($agg) m JOIN words w ON w.word = m.mark_word"
    )->fetch();
    $tab_counts = [
        'indragite' => (int) ($c['n_indragite'] ?? 0),
        'respinse'  => (int) ($c['n_respinse']  ?? 0),
    ];

    $t = db()->query(
        'SELECT COUNT(*) AS n, COUNT(DISTINCT user_id) AS people
           FROM app.annotations WHERE deleted = 0'
    )->fetch();
    $n_marks  = (int) ($t['n'] ?? 0);
    $n_people = (int) ($t['people'] ?? 0);
}

$tab_url = fn(string $k): string => BASE . '/colectii' . ($k === 'indragite' ? '' : '?t=' . $k);

// Romanian counts take „de" before the noun unless the last two digits are 01–19:
// 5 cuvinte, 18 cuvinte, but 20 de cuvinte and 473 de marcaje. Worth the three lines —
// „473 marcaje" is the kind of wrong that reads as machine-written.
$ro_count = function (int $n, string $one, string $many): string {
    if ($n === 1) return '1 ' . $one;
    $r = $n % 100;
    return $n . ' ' . ($r >= 1 && $r <= 19 ? '' : 'de ') . $many;
};
$n_words = fn(int $n): string => $ro_count($n, 'cuvânt', 'cuvinte');

// 200 words is well inside WORD_PACK_MAX (500), so the whole tab opens in the explorer.
$packed = $rows ? pack_words(array_column($rows, 'word')) : '';

$title = $tab === 'respinse'
    ? 'Cuvinte respinse de vizitatori'
    : 'Cuvintele îndrăgite de vizitatori';
$desc = $tab === 'respinse'
    ? 'Cuvintele uitate pe care vizitatorii le-au trecut cu ⛔️ — clasament după câți oameni le-au marcat.'
    : 'Cuvintele uitate pe care vizitatorii le-au marcat cu ★ sau 🤣 — clasament după câți oameni le-au marcat.';
?>
<!DOCTYPE html>
<html lang="ro" data-skin="<?= DEFAULT_SKIN ?>">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <?= otios_skin_boot() ?>
  <title><?= e($title) ?> — Voroave</title>
  <meta name="description" content="<?= e($desc) ?>">
  <!-- Indexable, unlike /liste. Every string on this page comes out of ui.db or is an
       integer — no nicknames, no list titles, no user-supplied text at all — so the
       noindex that keeps the public list directory out of search results has nothing to
       protect here. -->
  <!-- site_origin() rather than otios_abs_url(): HTTP_HOST is attacker-supplied and this
       lands in a URL crawlers follow, and only site_origin() whitelists it. -->
  <link rel="canonical" href="<?= e(site_origin() . '/colectii' . ($tab === 'respinse' ? '?t=respinse' : '')) ?>">
  <meta property="og:title" content="<?= e($title) ?> — Voroave">
  <meta property="og:description" content="<?= e($desc) ?>">
  <meta property="og:type" content="website">
  <link rel="stylesheet" href="<?= BASE ?>/assets/fonts/app-fonts.css">
  <link rel="stylesheet" href="<?= BASE ?>/assets/app.css">
  <?= otios_skin_links() ?>
  <style>
    .lista-wrap { max-width: 760px; margin: 0 auto; padding: 28px 20px 64px; }
    .liste-h1 { font-family: var(--serif); font-size: 1.75rem; font-weight: 600; color: var(--text); margin: 0 0 4px; }
    .liste-lede { color: var(--text-2); font-size: 0.9375rem; margin: 0 0 6px; }
    .agg-crosslink { font-size: 0.875rem; margin: 0 0 22px; }
    .agg-crosslink a { color: var(--accent); }
    /* The tab strip and the open-in-explorer button on one line, wrapping on a phone. */
    .agg-bar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }
    .agg-bar a.playlist-btn { text-decoration: none; display: inline-block; }
    .agg-note { font-family: var(--mono); font-size: 0.6875rem; color: var(--text-4); margin: 0 0 14px; }
  </style>
    <!-- favicon -->
  <link rel="icon" type="image/png" href="/assets/favicon/favicon-96x96.png" sizes="96x96" />
  <link rel="icon" type="image/svg+xml" href="/assets/favicon/favicon.svg" />
  <link rel="shortcut icon" href="/assets/favicon/favicon.ico" />
  <link rel="apple-touch-icon" sizes="180x180" href="/assets/favicon/apple-touch-icon.png" />
  <meta name="apple-mobile-web-app-title" content="Voroave neglijate" />
  <link rel="manifest" href="/assets/favicon/site.webmanifest" />

</head>
<body class="page-doc">
  <?php $page = 'colectii'; $brand_tag = 'colecții'; require __DIR__ . '/api/_partials/header.php'; ?>

  <div class="lista-wrap">
    <h1 class="liste-h1">Colecții</h1>
    <p class="liste-lede">
      <?php if ($n_marks > 0): ?>
        
        <?= $ro_count($n_marks, 'marcaj', 'cuvinte selectate') ?>
        de la <?= $ro_count($n_people, 'persoană', 'utilizatori') ?>.
      <?php else: ?>
        Ce au salvat vizitatorii în timp ce răsfoiau.
      <?php endif; ?>
      <!-- Apasă <strong>f</strong>, <strong>l</strong> sau <strong>m</strong> pe un cuvânt în
      explorator și intră și marcajul tău în socoteală. -->
    </p>
    <p class="agg-crosslink">
    &rarr; vezi și <a href="<?= BASE ?>/liste">listele tale și cele publice</a>
    </p>

    <div class="agg-bar">
      <nav class="seg" aria-label="Fel de marcaj">
        <?php foreach ($tabs as $k => $t): $on = $k === $tab; ?>
          <a class="seg-link<?= $on ? ' is-on' : '' ?>" href="<?= $tab_url($k) ?>"
             <?= $on ? 'aria-current="page"' : '' ?>>
            <?= $t['emoji'] ?> <?= e($t['label']) ?>
            <span class="seg-n"><?= $tab_counts[$k] ?></span>
          </a>
        <?php endforeach; ?>
      </nav>
      <?php if ($packed !== ''): ?>
        <a class="playlist-btn" href="<?= BASE ?>/?w=<?= e($packed) ?>">deschide toate în explorator</a>
      <?php endif; ?>
    </div>

    <?php if (!$have_db || !$rows): ?>
      <p class="lista-empty">
        <?php if ($tab === 'respinse'): ?>
          Niciun cuvânt respins deocamdată. Marchează unul cu <strong>m</strong> în explorator.
        <?php else: ?>
          Niciun cuvânt marcat deocamdată. Apasă <strong>f</strong> pe unul care îți place
          și va fi primul de aici.
        <?php endif; ?>
      </p>
    <?php else: ?>
      <p class="agg-note">
        <?= $n_words(count($rows)) ?><?= count($rows) >= AGG_LIMIT ? ' (primele ' . AGG_LIMIT . ')' : '' ?>
        · numărul este câți oameni au marcat cuvântul, nu de câte ori
      </p>

      <?php foreach ($rows as $w):
        $pos  = explode('|', $w['dex_pos'] ?? '')[0];
        $reg  = explode('|', $w['dex_register'] ?? '')[0];
        $meta = implode(' · ', array_filter([$pos, $reg]));
        $def  = $w['definition'] !== null
            ? mb_strimwidth(explode('|', $w['definition'])[0], 0, 260, '…')
            : null;
      ?>
        <div class="lista-item">
          <?php
          // The lead number is the ranking: how many *people*. n_fav/n_lol follow it as a
          // breakdown and may sum higher — someone who both ★'d and 🤣'd a word counts
          // once in the ranking and appears in both. Hence the two levels of separator:
          // one „·" after the lead, plain spaces inside the breakdown.
          //
          // **The breakdown is drawn on the „respinse" tab too, and that is the point.**
          // The fav-beats-meh precedence is per *person*, not per word — a word one
          // visitor ★'d and another ⛔️'d is on both tabs, honestly. Leading with „⛔️4"
          // and saying nothing else would report a word 19 people liked as rejected.
          $break = [];
          if ((int) $w['n_fav'] > 0) $break[] = '★' . (int) $w['n_fav'];
          if ((int) $w['n_lol'] > 0) $break[] = '🤣' . (int) $w['n_lol'];
          if ($tab === 'respinse' && (int) $w['n_up'] === 0) $break = [];
          ?>
          <span class="agg-marks" title="Câți oameni au marcat cuvântul">
            <?php if ($tab === 'respinse'): ?>⛔️ <?php endif
            ?><span class="agg-n"><?= (int) $w[$col] ?></span><?php
            if ($break): ?> · <?= implode(' ', $break) ?><?php endif; ?>
          </span>
          <a class="lista-word" href="<?= BASE ?>/?word=<?= urlenc($w['word']) ?>"><?= e($w['word']) ?></a>
          <?php if ($meta): ?><span class="lista-tags"><?= e($meta) ?></span><?php endif; ?>
          <p class="lista-def<?= $def === null ? ' lista-nodef' : '' ?>">
            <?= $def === null ? 'fără definiție' : e($def) ?>
          </p>
        </div>
      <?php endforeach; ?>
    <?php endif; ?>
  </div>

  <?php require __DIR__ . '/api/_partials/footer.php'; ?>

  <script src="<?= BASE ?>/assets/prefs.js"></script>
</body>
</html>
