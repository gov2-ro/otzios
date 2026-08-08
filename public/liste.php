<?php
declare(strict_types=1);
require_once __DIR__ . '/api/_auth.php';

// The lists hub: /liste.php
//
// "Your lists" are the four buckets you already fill while browsing — fav, lol,
// ascunde, meh. They are not stored as lists; they are derived from your annotations
// on every request, so they can never drift out of date. A row in the `lists` table is
// a *published snapshot* of one of them, which is why publishing is one button rather
// than a list-building flow.
//
// Server-rendered like lista.php: the bucket links carry packed ?w= URLs that PHP can
// build directly from ui.db, so opening a bucket in the explorer needs no JavaScript.

$user    = current_user();
$user_id = (int) $user['id'];
$pdo     = app_db();

// ── The four buckets ──────────────────────────────────────────────────────────

$buckets = [];
foreach (LIST_BUCKETS as $key => $meta) {
    $words = bucket_words($user_id, $key);
    // A word can outlive a data rebuild in app.db but vanish from ui.db; counting the
    // survivors keeps the number here equal to what the explorer will actually show.
    $valid = filter_existing_words($words);
    $words = array_values(array_filter($words, fn($w) => isset($valid[$w])));

    $buckets[$key] = $meta + ['words' => $words, 'count' => count($words), 'packed' => pack_words($words)];
}

// ── My published lists ────────────────────────────────────────────────────────

$stmt = $pdo->prepare('SELECT * FROM lists WHERE user_id = ? ORDER BY updated_at DESC');
$stmt->execute([$user_id]);
$my_lists = $stmt->fetchAll();

// ── Everyone's public lists ───────────────────────────────────────────────────

$stmt = $pdo->prepare(
    'SELECT l.*, u.nickname FROM lists l JOIN users u ON u.id = l.user_id
      WHERE l.is_public = 1 AND l.item_count > 0
      ORDER BY l.updated_at DESC LIMIT 30'
);
$stmt->execute();
$public_lists = $stmt->fetchAll();

$list_url = fn(array $r): string => BASE . '/lista.php?l=' . urlenc($r['slug']);
$n_words  = fn(int $n): string => $n . ' ' . ($n === 1 ? 'cuvânt' : 'cuvinte');
?>
<!DOCTYPE html>
<html lang="ro" data-skin="<?= DEFAULT_SKIN ?>">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <?= otios_skin_boot() ?>
  <title>Liste — Oțios</title>
  <meta name="description" content="Listele tale de cuvinte uitate și listele publicate de alții.">
  <!-- The public directory has no report/takedown path yet (see docs/BACKLOG.md,
       "Moderation for public lists"), so it stays out of search results until it does.
       In-app discovery is unaffected. -->
  <meta name="robots" content="noindex">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&family=Public+Sans:ital,wght@0,400..800;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="<?= BASE ?>/assets/app.css">
  <?= otios_skin_links() ?>
  <style>
    .lista-wrap { max-width: 760px; margin: 0 auto; padding: 28px 20px 64px; }
    .liste-h1 { font-family: var(--serif); font-size: 1.75rem; font-weight: 600; color: var(--text); margin: 0 0 4px; }
    .liste-lede { color: var(--text-2); font-size: 0.9375rem; margin: 0 0 26px; }
    .liste-section { margin-bottom: 34px; }
    .liste-section > h2 {
      font-family: var(--mono); font-size: 0.6875rem; text-transform: uppercase;
      letter-spacing: .08em; color: var(--text-3); font-weight: 500;
      margin: 0 0 2px; padding-bottom: 6px; border-bottom: 1px solid var(--border);
    }
    .liste-note { font-family: var(--mono); font-size: 0.6875rem; color: var(--text-4); margin: 8px 0 0; }

    .bucket-emoji { font-size: 1rem; }
    .list-card.is-empty .list-name,
    .list-card.is-empty .bucket-emoji { opacity: .45; }
    .list-hint { color: var(--text-3); font-size: 0.8125rem; margin: 6px 0 0; }
    .list-owner { font-family: var(--mono); font-size: 0.6875rem; color: var(--text-3); }
    .list-desc { color: var(--text-2); font-size: 0.875rem; margin: 6px 0 0; }
    /* Reuse the explorer's small-button look rather than inventing a second one. */
    .list-actions a.playlist-btn { text-decoration: none; display: inline-block; }
  </style>
</head>
<body>
  <?php $page = 'liste'; $brand_tag = 'liste'; require __DIR__ . '/api/_partials/header.php'; ?>

  <div class="lista-wrap">
    <h1 class="liste-h1">Liste</h1>
    <p class="liste-lede">
      Cuvintele pe care le marchezi în timp ce explorezi se adună singure în patru liste.
      Publică una și primești un link de trimis mai departe.
    </p>

    <!-- ── Buckets ────────────────────────────────────────────────────────── -->
    <section class="liste-section">
      <h2>Listele mele</h2>
      <?php foreach ($buckets as $key => $b): $empty = $b['count'] === 0; ?>
      <div class="list-card<?= $empty ? ' is-empty' : '' ?>">
        <div class="list-card-top">
          <span class="bucket-emoji"><?= $b['emoji'] ?></span>
          <span class="list-name"><?= e($b['label']) ?></span>
          <span class="list-count"><?= $n_words($b['count']) ?></span>
        </div>
        <?php if ($empty): ?>
          <p class="list-hint">
            <?= $key === 'fav'
                ? 'Apasă f pe un cuvânt care îți place și apare aici.'
                : 'Apasă ' . e(mb_substr($key, 0, 1)) . ' pe un cuvânt și apare aici.' ?>
          </p>
        <?php else: ?>
          <div class="list-actions">
            <a class="playlist-btn" href="<?= BASE ?>/?w=<?= e($b['packed']) ?>">deschide în explorator</a>
            <button class="playlist-btn" data-act="copy-w" data-packed="<?= e($b['packed']) ?>">copiază link</button>
            <button class="playlist-btn" data-act="publish" data-bucket="<?= e($key) ?>">publică</button>
          </div>
        <?php endif; ?>
      </div>
      <?php endforeach; ?>
    </section>

    <!-- ── Published ──────────────────────────────────────────────────────── -->
    <section class="liste-section">
      <h2>Publicate de mine</h2>
      <?php if (!$my_lists): ?>
        <p class="lists-empty">Nimic publicat încă. Apasă <em>publică</em> pe una din listele de mai sus.</p>
      <?php endif; ?>
      <?php foreach ($my_lists as $l): ?>
      <div class="list-card" data-id="<?= (int) $l['id'] ?>">
        <div class="list-card-top">
          <span class="list-name"><?= e($l['title']) ?></span>
          <span class="list-count"><?= $n_words((int) $l['item_count']) ?></span>
          <?php if ($l['is_public']): ?><span class="list-pub">publică</span><?php endif; ?>
        </div>
        <?php if ($l['description'] !== ''): ?><p class="list-desc"><?= e($l['description']) ?></p><?php endif; ?>
        <div class="list-actions">
          <a class="playlist-btn" href="<?= $list_url($l) ?>">deschide</a>
          <?php if ($l['is_public']): ?>
            <button class="playlist-btn" data-act="copy-url" data-url="<?= e($list_url($l)) ?>">copiază link</button>
          <?php endif; ?>
          <?php if (isset(LIST_BUCKETS[$l['source_tag'] ?? ''])): ?>
            <button class="playlist-btn" data-act="refresh" data-id="<?= (int) $l['id'] ?>"
                    title="Reia cuvintele din lista „<?= e(LIST_BUCKETS[$l['source_tag']]['label']) ?>”">actualizează</button>
          <?php endif; ?>
          <button class="playlist-btn" data-act="toggle-public" data-id="<?= (int) $l['id'] ?>"
                  data-public="<?= $l['is_public'] ? '1' : '0' ?>"><?= $l['is_public'] ? 'fă privată' : 'publică' ?></button>
          <button class="playlist-btn" data-act="delete" data-id="<?= (int) $l['id'] ?>">șterge</button>
        </div>
      </div>
      <?php endforeach; ?>
    </section>

    <!-- ── Directory ──────────────────────────────────────────────────────── -->
    <section class="liste-section">
      <h2>Liste publice</h2>
      <?php if (!$public_lists): ?>
        <p class="lists-empty">Nicio listă publică deocamdată. A ta poate fi prima.</p>
      <?php endif; ?>
      <?php foreach ($public_lists as $l): ?>
      <div class="list-card">
        <div class="list-card-top">
          <a class="list-name" href="<?= $list_url($l) ?>"><?= e($l['title']) ?></a>
          <span class="list-count"><?= $n_words((int) $l['item_count']) ?></span>
          <span class="list-owner">de <?= e($l['nickname'] ?: 'anonim') ?></span>
        </div>
        <?php if ($l['description'] !== ''): ?><p class="list-desc"><?= e($l['description']) ?></p><?php endif; ?>
      </div>
      <?php endforeach; ?>
      <p class="liste-note">Listele publice sunt scrise de vizitatori. Nu sunt verificate.</p>
    </section>
  </div>

  <?php require __DIR__ . '/api/_partials/footer.php'; ?>

  <script>var OTIOS_BASE = '<?= BASE ?>';</script>
  <script src="<?= BASE ?>/assets/prefs.js"></script>
  <script src="<?= BASE ?>/assets/store.js"></script>
  <script>
  (function() {
    function toast(msg) {
      var t = document.createElement('div');
      t.className = 'toast';
      t.textContent = msg;
      document.body.appendChild(t);
      setTimeout(function() { t.remove(); }, 2200);
    }

    function listsApi(body) {
      return fetch(OTIOS_BASE + '/api/lists.php', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
      }).then(function(r) { return r.json().then(function(d) { return { status: r.status, data: d }; }); });
    }

    // Publishing is the one moment an anonymous visitor is asked for anything: a name to
    // put on the list.
    function ensureNickname() {
      return otiosMe().then(function(me) {
        if (me && me.nickname) return me.nickname;
        var name = prompt('Sub ce nume publici lista?');
        if (!name || name.trim().length < 2) return null;
        return fetch(OTIOS_BASE + '/api/profile.php', {
          method: 'POST', credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nickname: name.trim() })
        }).then(function(r) { return r.json(); }).then(function(d) { return d.nickname || null; });
      });
    }

    function copy(text, msg) {
      navigator.clipboard.writeText(text).then(function() { toast(msg); },
                                              function() { toast('Nu am putut copia linkul'); });
    }

    document.addEventListener('click', function(e) {
      var btn = e.target.closest('[data-act]');
      if (!btn) return;
      var act = btn.dataset.act;
      var id  = parseInt(btn.dataset.id, 10);

      if (act === 'copy-w') {
        copy(location.origin + OTIOS_BASE + '/?w=' + btn.dataset.packed, 'Link copiat!');
        return;
      }
      if (act === 'copy-url') {
        copy(location.origin + btn.dataset.url, 'Link copiat!');
        return;
      }
      if (act === 'publish') {
        ensureNickname().then(function(name) {
          if (!name) { toast('Ai nevoie de un nume ca să publici'); return; }
          listsApi({ action: 'publish_bucket', bucket: btn.dataset.bucket }).then(function(res) {
            if (res.status !== 200) { toast('Nu am putut publica lista'); return; }
            location.reload();
          });
        });
        return;
      }
      if (act === 'refresh') {
        listsApi({ action: 'refresh', id: id }).then(function(res) {
          if (res.status !== 200) { toast('Nu am putut actualiza lista'); return; }
          location.reload();
        });
        return;
      }
      if (act === 'toggle-public') {
        var makePublic = btn.dataset.public !== '1';
        var go = function() {
          listsApi({ action: 'update', id: id, is_public: makePublic }).then(function(res) {
            if (res.status !== 200) { toast('Nu am putut schimba vizibilitatea'); return; }
            location.reload();
          });
        };
        if (!makePublic) { go(); return; }
        ensureNickname().then(function(name) {
          if (!name) { toast('Ai nevoie de un nume ca să publici'); return; }
          go();
        });
        return;
      }
      if (act === 'delete') {
        if (!confirm('Ștergi lista?')) return;
        listsApi({ action: 'delete', id: id }).then(function() { location.reload(); });
      }
    });

    // The counts above are rendered from the server's copy of your annotations. If this
    // tab still has unsynced edits — marked offline, or in a tab that never lost focus —
    // push them and re-render, rather than showing a stale zero.
    if (Object.keys(getQueue()).length) {
      syncNow().then(function() { location.reload(); });
    }
  })();
  </script>
</body>
</html>
