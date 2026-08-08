<?php
declare(strict_types=1);
require_once __DIR__ . '/api/_auth.php';

// Public page for a shared word list: /lista.php?l=<slug>
//
// Server-rendered rather than fetched, so a shared link previews properly and works
// without JavaScript. Reads the list from app.db and the word data from ui.db — two
// connections, since db() is opened read-only for ui.db.

$slug = trim($_GET['l'] ?? '');
$pdo  = app_db();

$row = null;
if ($slug !== '') {
    $stmt = $pdo->prepare(
        'SELECT l.*, u.nickname FROM lists l JOIN users u ON u.id = l.user_id WHERE l.slug = ?'
    );
    $stmt->execute([$slug]);
    $row = $stmt->fetch() ?: null;
}

// A private list is invisible to everyone but its owner — an unguessable slug is not
// access control. current_user() is only consulted once a list actually exists, so a
// bad link doesn't mint an identity for a passing crawler.
if ($row && !$row['is_public']) {
    $viewer = current_user();
    if ((int) $row['user_id'] !== (int) $viewer['id']) $row = null;
}

$words = [];
if ($row) {
    $stmt = $pdo->prepare('SELECT word FROM list_items WHERE list_id = ? ORDER BY position, added_at');
    $stmt->execute([$row['id']]);
    $names = $stmt->fetchAll(PDO::FETCH_COLUMN);

    if ($names !== []) {
        $ph   = implode(',', array_fill(0, count($names), '?'));
        $stmt = db()->prepare(
            "SELECT word, definition, dex_pos, dex_register, verdict, dex_frequency
               FROM words WHERE word IN ($ph)"
        );
        $stmt->execute($names);
        $by_word = [];
        foreach ($stmt->fetchAll() as $w) { $by_word[$w['word']] = $w; }
        // Preserve the curator's ordering, and keep words that have since left ui.db.
        foreach ($names as $n) {
            $words[] = $by_word[$n] ?? ['word' => $n, 'definition' => null, 'dex_pos' => '',
                                        'dex_register' => '', 'verdict' => null, 'dex_frequency' => null];
        }
    }
}

if (!$row) http_response_code(404);

$title = $row ? $row['title'] : 'Listă negăsită';
$owner = $row && $row['nickname'] ? $row['nickname'] : 'anonim';
$desc  = $row && $row['description'] !== ''
    ? $row['description']
    : ($row ? count($words) . ' cuvinte uitate, alese de ' . $owner : 'Această listă nu există sau nu este publică.');
?>
<!DOCTYPE html>
<html lang="ro" data-skin="<?= DEFAULT_SKIN ?>">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <?= otios_skin_boot() ?>
  <title><?= e($title) ?> — Oțios</title>
  <meta name="description" content="<?= e($desc) ?>">
  <meta property="og:title" content="<?= e($title) ?> — Oțios">
  <meta property="og:description" content="<?= e($desc) ?>">
  <meta property="og:type" content="article">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&family=Public+Sans:ital,wght@0,400..800;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="<?= BASE ?>/assets/app.css">
  <?= otios_skin_links() ?>
  <style>
    .lista-wrap { max-width: 760px; margin: 0 auto; padding: 28px 20px 64px; }
    .lista-head { border-bottom: 1px solid var(--border); padding-bottom: 18px; margin-bottom: 22px; }
    .lista-title { font-family: var(--serif); font-size: 1.75rem; font-weight: 600; color: var(--text); margin: 0 0 6px; }
    .lista-meta { font-family: var(--mono); font-size: 0.75rem; color: var(--text-3); }
    .lista-desc { margin: 10px 0 0; color: var(--text-2); font-size: 0.9375rem; }
    .lista-item { padding: 12px 0; border-bottom: 1px solid var(--border); }
    .lista-word { font-family: var(--serif); font-size: 1.125rem; font-weight: 600; color: var(--text); text-decoration: none; }
    .lista-word:hover { text-decoration: underline; }
    .lista-tags { font-family: var(--mono); font-size: 0.6875rem; color: var(--text-3); margin-left: 8px; }
    .lista-def { margin: 4px 0 0; color: var(--text-2); font-size: 0.9375rem; line-height: 1.5; }
    .lista-nodef { color: var(--text-4); font-style: italic; }
    .lista-empty { color: var(--text-3); padding: 30px 0; }
    .lista-share { display: flex; gap: 6px; margin-top: 14px; flex-wrap: wrap; }
    .lista-share a.playlist-btn { text-decoration: none; display: inline-block; }
    /* Deliberately the quietest control on the page — a plain link in muted text,
       well below the share buttons. Reporting should be findable, not inviting. */
    .lista-report { margin-top: 26px; font-size: 0.75rem; color: var(--text-3); }
    .lista-report button { font: inherit; color: var(--text-3); background: none; border: none;
                           padding: 0; cursor: pointer; text-decoration: underline; }
    .lista-report button:hover { color: var(--text-2); }
  </style>
</head>
<body>
  <!-- A shared list is often someone's first page on the site, which is most of
       why the header is shared: an arriving visitor gets the brand, the way back
       into the explorer and the display controls without this page restating any
       of it. `$page` is left unset on purpose — this is not `liste.php`, so
       nothing in the nav should render as the current page and go unclickable. -->
  <?php $brand_tag = 'listă'; require __DIR__ . '/api/_partials/header.php'; ?>

  <div class="lista-wrap">
    <?php if (!$row): ?>
      <h1 class="lista-title">Listă negăsită</h1>
      <p class="lista-desc">Această listă nu există sau nu mai este publică.</p>
    <?php else: ?>
      <div class="lista-head">
        <h1 class="lista-title"><?= e($row['title']) ?></h1>
        <div class="lista-meta">
          <?= count($words) ?> <?= count($words) === 1 ? 'cuvânt' : 'cuvinte' ?> ·
          de <?= e($owner) ?>
          <?php if (!$row['is_public']): ?> · <strong>privată</strong> (doar tu o vezi)<?php endif; ?>
        </div>
        <?php if ($row['description'] !== ''): ?>
          <p class="lista-desc"><?= e($row['description']) ?></p>
        <?php endif; ?>

        <?php if ($words !== []):
          // Packed here rather than in the browser: PHP already holds the words and the
          // id map, so the explorer link works with JavaScript off.
          $packed = pack_words(array_column($words, 'word')); ?>
        <div class="lista-share">
          <?php if ($packed !== ''): ?>
            <a class="playlist-btn" href="<?= BASE ?>/?w=<?= e($packed) ?>">deschide toate în explorator</a>
          <?php endif; ?>
          <button type="button" class="playlist-btn" id="copy-link-btn">copiază link</button>
          <button type="button" class="playlist-btn" id="share-btn" hidden>trimite</button>
        </div>
        <?php endif; ?>
      </div>

      <?php if ($words === []): ?>
        <p class="lista-empty">Lista este goală deocamdată.</p>
      <?php endif; ?>

      <?php foreach ($words as $w):
        $pos = explode('|', $w['dex_pos'] ?? '')[0];
        $reg = explode('|', $w['dex_register'] ?? '')[0];
        $meta = implode(' · ', array_filter([$pos, $reg]));
        $def = $w['definition'] !== null ? mb_strimwidth(explode('|', $w['definition'])[0], 0, 260, '…') : null;
      ?>
        <div class="lista-item">
          <a class="lista-word" href="<?= BASE ?>/?word=<?= urlenc($w['word']) ?>"><?= e($w['word']) ?></a>
          <?php if ($meta): ?><span class="lista-tags"><?= e($meta) ?></span><?php endif; ?>
          <p class="lista-def<?= $def === null ? ' lista-nodef' : '' ?>">
            <?= $def === null ? 'fără definiție' : e($def) ?>
          </p>
        </div>
      <?php endforeach; ?>

      <?php // Public lists only — there is nothing to report about one that only you
            // can read. Ownership is NOT checked here on purpose: that would mean
            // calling current_user() on every public view, minting an identity for
            // every passing crawler (see the note above). The API rejects a report on
            // your own list, and the button reports that back.
            if ($row['is_public']): ?>
      <p class="lista-report">
        Conținut nepotrivit? <button type="button" id="report-btn">raportează lista</button>
      </p>
      <?php endif; ?>
    <?php endif; ?>
  </div>

  <?php require __DIR__ . '/api/_partials/footer.php'; ?>

  <script src="<?= BASE ?>/assets/prefs.js"></script>
  <script>
  (function() {
    var copyBtn  = document.getElementById('copy-link-btn');
    var shareBtn = document.getElementById('share-btn');
    var reportBtn = document.getElementById('report-btn');

    var title = <?= json_encode($title, JSON_UNESCAPED_UNICODE) ?> + ' — Oțios';
    var slug  = <?= json_encode($slug, JSON_UNESCAPED_UNICODE) ?>;

    function toast(msg) {
      var t = document.createElement('div');
      t.className = 'toast';
      t.textContent = msg;
      document.body.appendChild(t);
      setTimeout(function() { t.remove(); }, 2200);
    }

    if (copyBtn) copyBtn.addEventListener('click', function() {
      navigator.clipboard.writeText(location.href).then(
        function() { toast('Link copiat!'); },
        function() { toast('Nu am putut copia linkul'); }
      );
    });

    if (reportBtn) reportBtn.addEventListener('click', function() {
      var reason = prompt('Ce e în neregulă cu această listă? (opțional)');
      if (reason === null) return;             // cancelled — not a report

      reportBtn.disabled = true;
      fetch(<?= json_encode(BASE . '/api/lists.php', JSON_UNESCAPED_SLASHES) ?>, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'report', slug: slug, reason: reason })
      }).then(function(r) { return r.json().catch(function() { return {}; }); })
        .then(function(res) {
          if (res.reported) {
            reportBtn.textContent = 'raportat';
            toast('Mulțumim. Lista va fi verificată.');
          } else if (res.error === 'own_list') {
            reportBtn.disabled = false;
            toast('Este lista ta.');
          } else if (res.error === 'rate_limited') {
            reportBtn.disabled = false;
            toast('Prea multe raportări. Încearcă mai târziu.');
          } else {
            reportBtn.disabled = false;
            toast('Nu am putut trimite raportarea.');
          }
        })
        .catch(function() { reportBtn.disabled = false; toast('Nu am putut trimite raportarea.'); });
    });

    // Only offered where the OS actually has a share sheet; elsewhere the copy button
    // is the whole story and a dead "trimite" would just be noise.
    if (navigator.share && shareBtn) {
      shareBtn.hidden = false;
      shareBtn.addEventListener('click', function() {
        navigator.share({ title: title, url: location.href }).catch(function() {});
      });
    }
  })();
  </script>
</body>
</html>
