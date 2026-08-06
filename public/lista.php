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
<html lang="ro" data-skin="brutal">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script>(function(){try{var d=document.documentElement;var t=localStorage.getItem('otios.theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');d.setAttribute('data-theme',t);d.setAttribute('data-skin',localStorage.getItem('otios.skin')||'brutal');var s=localStorage.getItem('otios.textscale')||'100';d.style.fontSize=s+'%';}catch(e){}})();</script>
  <title><?= e($title) ?> — Oțios</title>
  <meta name="description" content="<?= e($desc) ?>">
  <meta property="og:title" content="<?= e($title) ?> — Oțios">
  <meta property="og:description" content="<?= e($desc) ?>">
  <meta property="og:type" content="article">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&family=Public+Sans:ital,wght@0,400..800;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="<?= BASE ?>/assets/app.css">
  <link rel="stylesheet" href="<?= BASE ?>/assets/skin-brutal.css">
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
    .lista-nav {
      font-family: var(--mono); font-size: 0.75rem; margin-bottom: 20px;
      display: flex; align-items: center; gap: 8px;
    }
    .lista-nav a { color: var(--text-3); text-decoration: none; }
    .lista-nav a:hover { color: var(--accent); }
    /* .skin-toggle only — the theme toggle also carries .theme-toggle, and
       giving both `margin-left:auto` splits the free space between them. */
    .lista-nav .skin-toggle { margin-left: auto; }
    .lista-empty { color: var(--text-3); padding: 30px 0; }
  </style>
</head>
<body>
  <div class="lista-wrap">
    <!-- A shared list is often someone's first page on the site, so the display
         controls belong here too — otherwise an arriving visitor is stuck with
         whatever skin and theme happen to be the defaults. -->
    <div class="lista-nav">
      <a href="<?= BASE ?>/">← Oțios</a>
      <div class="theme-toggle theme-toggle--sm skin-toggle" role="group" aria-label="Stil vizual">
        <button type="button" class="tg-btn" data-skin-btn="paper" onclick="setSkin('paper')" title="Stil hârtie — editorial, cald">▤</button>
        <button type="button" class="tg-btn" data-skin-btn="brutal" onclick="setSkin('brutal')" title="Stil beton — brutalist, contrast dur">▩</button>
      </div>
      <div class="theme-toggle theme-toggle--sm" role="group" aria-label="Temă">
        <button type="button" class="tg-btn" data-theme-btn="light" onclick="setTheme('light')" title="Temă deschisă">☀</button>
        <button type="button" class="tg-btn" data-theme-btn="dark" onclick="setTheme('dark')" title="Temă întunecată">☾</button>
      </div>
    </div>

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
    <?php endif; ?>
  </div>
  <script src="<?= BASE ?>/assets/prefs.js"></script>
</body>
</html>
