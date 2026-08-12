<?php
declare(strict_types=1);
require_once __DIR__ . '/api/_auth.php';

// The collections hub: /liste.php
//
// "Your collections" are the three buckets you already fill while browsing — fav, lol,
// meh. They are not stored as lists; they are derived from your annotations on every
// request, so they can never drift out of date. A row in the `lists` table is a
// *published snapshot* of one of them, which is why publishing is one button rather
// than a list-building flow.
//
// **One card per bucket, published or not.** There used to be a second section listing
// the published rows, which meant the same collection appeared twice under two different
// names — „favorite" above and „favorite — pax1" below — with the actions split between
// them: publish up here, refresh/unpublish/delete down there. The published row is a
// *state* of the bucket, not a sibling of it, so the card carries both and the actions
// change with the state.
//
// Server-rendered like lista.php: the bucket links carry packed ?w= URLs that PHP can
// build directly from ui.db, so opening a bucket in the explorer needs no JavaScript.

$user    = current_user();
$user_id = (int) $user['id'];
$pdo     = app_db();

// ── My published lists, keyed by the bucket they came from ────────────────────

$stmt = $pdo->prepare('SELECT * FROM lists WHERE user_id = ? ORDER BY updated_at DESC');
$stmt->execute([$user_id]);
$my_lists = $stmt->fetchAll();

$published = [];   // bucket key → list row, folded into that bucket's card
$orphans   = [];   // everything else: hand-assembled lists, and retired buckets
foreach ($my_lists as $l) {
    $tag = (string) ($l['source_tag'] ?? '');
    if ($tag !== '' && isset(LIST_BUCKETS[$tag]) && !isset($published[$tag])) {
        $published[$tag] = $l;
    } else {
        // Not silently dropped with the section that used to show them. A list created
        // through `create` + `add` has no bucket to fold into, and one published from
        // `ascunde` before that bucket was retired has no card left — hiding either
        // would make someone's list unreachable rather than tidy.
        $orphans[] = $l;
    }
}

// ── The buckets ───────────────────────────────────────────────────────────────

$buckets = [];
foreach (LIST_BUCKETS as $key => $meta) {
    $words = bucket_words($user_id, $key);
    // A word can outlive a data rebuild in app.db but vanish from ui.db; counting the
    // survivors keeps the number here equal to what the explorer will actually show.
    $valid = filter_existing_words($words);
    $words = array_values(array_filter($words, fn($w) => isset($valid[$w])));

    $buckets[$key] = $meta + [
        'words'  => $words,
        'count'  => count($words),
        'packed' => pack_words($words),
        'list'   => $published[$key] ?? null,
    ];
}

// ── Everyone's public lists ───────────────────────────────────────────────────

$stmt = $pdo->prepare(
    'SELECT l.*, u.nickname FROM lists l JOIN users u ON u.id = l.user_id
      WHERE l.is_public = 1 AND l.item_count > 0
      ORDER BY l.updated_at DESC LIMIT 30'
);
$stmt->execute();
$public_lists = $stmt->fetchAll();

$list_url = fn(array $r): string => BASE . '/lista?l=' . urlenc($r['slug']);
$n_words  = fn(int $n): string => $n . ' ' . ($n === 1 ? 'cuvânt' : 'cuvinte');
?>
<!DOCTYPE html>
<html lang="ro" data-skin="<?= DEFAULT_SKIN ?>">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <?= otios_skin_boot() ?>
  <title>Colecții — Voroave</title>
  <meta name="description" content="Colecțiile tale de cuvinte uitate și cele publicate de alții.">
  <!-- The public directory has no report/takedown path yet (see docs/BACKLOG.md,
       "Moderation for public lists"), so it stays out of search results until it does.
       In-app discovery is unaffected. -->
  <meta name="robots" content="noindex">
  <link rel="stylesheet" href="<?= BASE ?>/assets/fonts/app-fonts.css">
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
    /* The published-as line. Deliberately quiet type rather than another card: it states
       a state of the bucket above it, and a second card is what this page had before. */
    .list-pub-note { font-size: 0.8125rem; color: var(--text-3); margin: 6px 0 0; }
    .list-pub-note a { color: var(--text-2); }
    .list-card.is-empty .list-name,
    .list-card.is-empty .bucket-emoji { opacity: .45; }
    .list-hint { color: var(--text-3); font-size: 0.8125rem; margin: 6px 0 0; }
    .list-owner { font-family: var(--mono); font-size: 0.6875rem; color: var(--text-3); }
    .list-desc { color: var(--text-2); font-size: 0.875rem; margin: 6px 0 0; }
    /* Reuse the explorer's small-button look rather than inventing a second one. */
    .list-actions a.playlist-btn { text-decoration: none; display: inline-block; }
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
  <?php $page = 'liste'; $brand_tag = 'colecții'; require __DIR__ . '/api/_partials/header.php'; ?>

  <div class="lista-wrap">
    <h1 class="liste-h1">Colecții</h1>
    <p class="liste-lede">
      Cuvintele pe care le marchezi în timp ce explorezi se adună singure în trei colecții.
      Publică una și primești un link de trimis mai departe.
    </p>

    <!-- ── Buckets ────────────────────────────────────────────────────────── -->
    <section class="liste-section">
      <h2>Colecțiile mele</h2>
      <?php foreach ($buckets as $key => $b):
        $empty = $b['count'] === 0;
        $l     = $b['list'];
      ?>
      <div class="list-card<?= $empty && !$l ? ' is-empty' : '' ?>"<?= $l ? ' data-id="' . (int) $l['id'] . '"' : '' ?>>
        <div class="list-card-top">
          <span class="bucket-emoji"><?= $b['emoji'] ?></span>
          <span class="list-name"><?= e($b['label']) ?></span>
          <span class="list-count"><?= $n_words($b['count']) ?></span>
          <?php if ($l && $l['is_public']): ?><span class="list-pub">publică</span><?php endif; ?>
        </div>

        <?php if ($empty && !$l): ?>
          <p class="list-hint">
            <?= $key === 'fav'
                ? 'Apasă f pe un cuvânt care îți place și apare aici.'
                : 'Apasă ' . e(mb_substr($key, 0, 1)) . ' pe un cuvânt și apare aici.' ?>
          </p>
        <?php else: ?>
          <div class="list-actions">
            <?php if (!$empty): ?>
              <a class="playlist-btn" href="<?= BASE ?>/?w=<?= e($b['packed']) ?>">deschide în explorator</a>
            <?php endif; ?>

            <?php if ($l && $l['is_public']): ?>
              <!-- The published page's link, not the packed one: once a collection has a
                   page of its own, that is the address worth sending. -->
              <button class="playlist-btn" data-act="copy-url" data-url="<?= e($list_url($l)) ?>">copiază link</button>
            <?php elseif (!$empty): ?>
              <button class="playlist-btn" data-act="copy-w" data-packed="<?= e($b['packed']) ?>">copiază link</button>
            <?php endif; ?>

            <?php if ($l): ?>
              <button class="playlist-btn" data-act="refresh" data-id="<?= (int) $l['id'] ?>"
                      title="Reia cuvintele marcate acum în „<?= e($b['label']) ?>”">actualizează</button>
            <?php endif; ?>

            <?php if ($l && $l['is_public']): ?>
              <button class="playlist-btn" data-act="toggle-public" data-id="<?= (int) $l['id'] ?>"
                      data-public="1">fă privată</button>
            <?php elseif (!$empty): ?>
              <!-- Always `publish_bucket`, never `update {is_public:1}` — it reuses the
                   existing row *and* refills it from the annotations, so re-publishing a
                   collection that was made private cannot hand out a stale snapshot. -->
              <button class="playlist-btn" data-act="publish" data-bucket="<?= e($key) ?>">publică</button>
            <?php endif; ?>

            <?php if ($l): ?>
              <button class="playlist-btn" data-act="delete" data-id="<?= (int) $l['id'] ?>">șterge</button>
            <?php endif; ?>
          </div>

          <?php if ($l): $stale = (int) $l['item_count'] !== $b['count']; ?>
          <p class="list-pub-note">
            <?= $l['is_public'] ? 'Publicată ca' : 'Salvată privat ca' ?>
            <a href="<?= $list_url($l) ?>">„<?= e($l['title']) ?>”</a><?php if ($stale): ?>
            · <?= $n_words((int) $l['item_count']) ?> în versiunea publicată — apasă
            <em>actualizează</em> ca s-o aduci la zi<?php endif; ?>.
          </p>
          <?php endif; ?>
        <?php endif; ?>
      </div>
      <?php endforeach; ?>
    </section>

    <!-- ── Anything that has no bucket to fold into ───────────────────────── -->
    <?php if ($orphans): ?>
    <section class="liste-section">
      <h2>Alte liste</h2>
      <?php foreach ($orphans as $l): ?>
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
          <button class="playlist-btn" data-act="toggle-public" data-id="<?= (int) $l['id'] ?>"
                  data-public="<?= $l['is_public'] ? '1' : '0' ?>"><?= $l['is_public'] ? 'fă privată' : 'publică' ?></button>
          <button class="playlist-btn" data-act="delete" data-id="<?= (int) $l['id'] ?>">șterge</button>
        </div>
      </div>
      <?php endforeach; ?>
      <p class="liste-note">Liste făcute de mână sau rămase dintr-un marcaj scos din uz. Nu se mai actualizează singure.</p>
    </section>
    <?php endif; ?>

    <!-- ── Directory ──────────────────────────────────────────────────────── -->
    <section class="liste-section">
      <h2>Colecții publice</h2>
      <?php if (!$public_lists): ?>
        <p class="lists-empty">Nicio colecție publică deocamdată. A ta poate fi prima.</p>
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
      <p class="liste-note">Colecțiile publice sunt făcute de vizitatori. Nu sunt verificate.</p>
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
        var name = prompt('Sub ce nume publici colecția?');
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
            if (res.status !== 200) { toast('Nu am putut publica colecția'); return; }
            location.reload();
          });
        });
        return;
      }
      if (act === 'refresh') {
        listsApi({ action: 'refresh', id: id }).then(function(res) {
          if (res.status !== 200) { toast('Nu am putut actualiza colecția'); return; }
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
        // The card is the bucket now, so this has to say which of the two it removes:
        // the published snapshot goes, the marked words stay where they were.
        if (!confirm('Ștergi versiunea publicată? Cuvintele marcate rămân în colecția ta.')) return;
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
