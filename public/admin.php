<?php
declare(strict_types=1);
require_once __DIR__ . '/api/_auth.php';

// Moderation queue for the public list directory (liste.php). The counterpart to
// `POST api/lists.php {action:'report'}`.
//
// Access is a single shared token, defined in the gitignored api/config.local.php:
//
//     define('OTIOS_ADMIN_TOKEN', '<48+ random hex chars>');
//
// With no token defined the page does not exist — 404, not 403, so an install that
// never configured moderation gives away nothing by being probed.
//
// The token is passed once as ?token=…; the page then seals it into a short-lived
// cookie and redirects to the bare URL, so it stops appearing in the address bar,
// the browser history, the access log and any outbound Referer.

const ADMIN_COOKIE  = 'otios_adm';
const ADMIN_SESSION = 8 * 3600;

if (!defined('OTIOS_ADMIN_TOKEN') || !is_string(OTIOS_ADMIN_TOKEN) || strlen(OTIOS_ADMIN_TOKEN) < 16) {
    http_response_code(404);
    exit('Not Found');
}

function admin_cookie_ok(): bool {
    $sealed = (string) ($_COOKIE[ADMIN_COOKIE] ?? '');
    if ($sealed === '') return false;
    $data = open_token($sealed, ADMIN_SESSION);
    return is_array($data) && ($data['adm'] ?? '') === '1';
}

$authed = admin_cookie_ok();

if (!$authed && isset($_GET['token'])) {
    // hash_equals, not ===: string comparison short-circuits on the first differing
    // byte, which leaks the token prefix to anyone willing to time the responses.
    if (hash_equals(OTIOS_ADMIN_TOKEN, (string) $_GET['token'])) {
        setcookie(ADMIN_COOKIE, seal_token(['adm' => '1', 't' => time()]), [
            'expires'  => time() + ADMIN_SESSION,
            'path'     => cookie_base_path(),
            'httponly' => true,
            'secure'   => is_https(),
            'samesite' => 'Lax',
        ]);
        header('Location: ' . BASE . '/admin.php');
        exit;
    }
    // Wrong token is indistinguishable from no token at all.
}

if (!$authed) {
    http_response_code(404);
    exit('Not Found');
}

$pdo = app_db();

// Keyed rather than reflected: the banner text is chosen here, and the URL only
// carries which one, so nothing a request supplies is ever echoed back.
const ADMIN_NOTICES = [
    'unpublished' => 'Lista a fost depublicată.',
    'dismissed'   => 'Raportările au fost respinse.',
    'deleted'     => 'Lista a fost ștearsă definitiv.',
];

// ── Actions ───────────────────────────────────────────────────────────────────

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST') {
    require_post_same_origin();

    $list_id = (int) ($_POST['list_id'] ?? 0);
    $now     = now_iso();
    $done    = '';

    switch ((string) ($_POST['do'] ?? '')) {
        // Unpublish rather than delete: the list stops being visible to anyone but its
        // owner, and nothing of theirs is destroyed on the strength of a stranger's report.
        case 'unpublish':
            $pdo->prepare('UPDATE lists SET is_public = 0, updated_at = ? WHERE id = ?')
                ->execute([$now, $list_id]);
            $pdo->prepare("UPDATE reports SET status = 'removed', resolved_at = ? WHERE list_id = ? AND status = 'open'")
                ->execute([$now, $list_id]);
            $done = 'unpublished';
            break;

        case 'dismiss':
            $pdo->prepare("UPDATE reports SET status = 'dismissed', resolved_at = ? WHERE list_id = ? AND status = 'open'")
                ->execute([$now, $list_id]);
            $done = 'dismissed';
            break;

        // The escape hatch for content that should not merely be hidden. Separate from
        // unpublish and never the default, because it is the only irreversible one.
        case 'delete':
            $pdo->prepare('DELETE FROM list_items WHERE list_id = ?')->execute([$list_id]);
            $pdo->prepare('DELETE FROM lists WHERE id = ?')->execute([$list_id]);
            $done = 'deleted';
            break;
    }

    // POST/redirect/GET, so a reload doesn't repeat the action.
    header('Location: ' . BASE . '/admin.php' . ($done !== '' ? '?done=' . $done : ''));
    exit;
}

$notice = ADMIN_NOTICES[(string) ($_GET['done'] ?? '')] ?? '';

$open = $pdo->query(
    "SELECT r.list_id,
            COUNT(*)                AS n_reports,
            MIN(r.created_at)       AS first_at,
            GROUP_CONCAT(NULLIF(r.reason, ''), ' ⁂ ') AS reasons,
            l.slug, l.title, l.description, l.is_public, l.item_count, l.source_tag,
            u.nickname
       FROM reports r
       JOIN lists l ON l.id = r.list_id
       JOIN users u ON u.id = l.user_id
      WHERE r.status = 'open'
      GROUP BY r.list_id
      ORDER BY n_reports DESC, first_at ASC"
)->fetchAll();

$resolved = (int) $pdo->query("SELECT COUNT(*) FROM reports WHERE status != 'open'")->fetchColumn();
?>
<!DOCTYPE html>
<html lang="ro" data-skin="<?= DEFAULT_SKIN ?>">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <!-- same-origin, not no-referrer: this page's own forms POST back here, and
       no-referrer would both strip the Referer and serialize Origin as "null",
       which is exactly what require_post_same_origin() rejects. same-origin still
       keeps /admin.php out of any third party's logs. -->
  <meta name="referrer" content="same-origin">
  <?= otios_skin_boot() ?>
  <title>Moderare — Oțios</title>
  <link rel="stylesheet" href="<?= BASE ?>/assets/app.css">
  <?= otios_skin_links() ?>
  <style>
    .adm-wrap { max-width: 860px; margin: 0 auto; padding: 24px 20px 60px; }
    .adm-head { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }
    .adm-head h1 { font-size: 1.25rem; margin: 0; }
    .adm-sub { color: var(--text-3); font-size: 0.8125rem; font-family: var(--mono); }
    .adm-notice { background: var(--accent-bg); color: var(--text); border: 1px solid var(--border);
                  padding: 8px 12px; border-radius: var(--radius); margin-bottom: 16px; font-size: 0.875rem; }
    .adm-card { border: 1px solid var(--border); border-radius: var(--radius);
                background: var(--surface); padding: 14px 16px; margin-bottom: 12px; }
    .adm-card-head { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
    .adm-card-head a { color: var(--text); font-weight: 700; font-size: 1rem; }
    .adm-badge { font-family: var(--mono); font-size: 0.6875rem; background: var(--v-ext-bg);
                 color: var(--v-ext-tx); padding: 1px 6px; border-radius: 999px; }
    .adm-meta { color: var(--text-3); font-size: 0.75rem; font-family: var(--mono); margin-top: 4px; }
    .adm-reasons { margin: 8px 0 0; font-size: 0.8125rem; color: var(--text-2);
                   white-space: pre-wrap; word-break: break-word; }
    .adm-btns { display: flex; gap: 6px; margin-top: 12px; flex-wrap: wrap; }
    .adm-btns button { font: inherit; font-size: 0.8125rem; padding: 5px 12px; cursor: pointer;
                       border: 1px solid var(--border); border-radius: var(--radius);
                       background: var(--surface-2); color: var(--text); }
    .adm-btns button:hover { border-color: var(--accent); }
    .adm-btns .adm-danger { color: var(--v-ext-tx); }
    .adm-empty { color: var(--text-3); padding: 30px 0; }
  </style>
</head>
<body>
  <div class="adm-wrap">
    <div class="adm-head">
      <h1>Moderare</h1>
      <span class="adm-sub"><?= count($open) ?> în așteptare · <?= $resolved ?> rezolvate</span>
      <a class="adm-sub" href="<?= BASE ?>/liste" style="margin-left:auto">← colecții</a>
    </div>

    <?php if ($notice !== ''): ?>
      <div class="adm-notice"><?= e($notice) ?></div>
    <?php endif; ?>

    <?php if ($open === []): ?>
      <p class="adm-empty">Nicio raportare în așteptare.</p>
    <?php endif; ?>

    <?php foreach ($open as $r): ?>
      <div class="adm-card">
        <div class="adm-card-head">
          <a href="<?= BASE ?>/lista?l=<?= urlenc($r['slug']) ?>" target="_blank" rel="noopener">
            <?= e($r['title']) ?>
          </a>
          <span class="adm-badge"><?= (int) $r['n_reports'] ?> raportări</span>
          <?php if (!$r['is_public']): ?><span class="adm-badge">deja privată</span><?php endif; ?>
        </div>
        <div class="adm-meta">
          de <?= e($r['nickname'] ?: 'anonim') ?> ·
          <?= (int) $r['item_count'] ?> cuvinte ·
          <?= e($r['source_tag'] !== '' ? $r['source_tag'] : 'manuală') ?> ·
          prima raportare <?= e(substr((string) $r['first_at'], 0, 16)) ?>
        </div>
        <?php if ($r['description'] !== ''): ?>
          <p class="adm-reasons"><em><?= e($r['description']) ?></em></p>
        <?php endif; ?>
        <?php if ($r['reasons']): ?>
          <p class="adm-reasons"><?= e((string) $r['reasons']) ?></p>
        <?php endif; ?>
        <form method="post" class="adm-btns">
          <input type="hidden" name="list_id" value="<?= (int) $r['list_id'] ?>">
          <button type="submit" name="do" value="unpublish">depublică</button>
          <button type="submit" name="do" value="dismiss">respinge raportările</button>
          <!-- The title is deliberately not interpolated into this string: it is
               user-supplied, and building JS source out of it is a quoting bug
               waiting to happen. The card above already says which list this is. -->
          <button type="submit" name="do" value="delete" class="adm-danger"
                  onclick="return confirm('Ștergi definitiv această listă? Acțiunea nu poate fi anulată.')">
            șterge definitiv
          </button>
        </form>
      </div>
    <?php endforeach; ?>
  </div>
</body>
</html>
