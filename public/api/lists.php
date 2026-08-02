<?php
declare(strict_types=1);
require_once __DIR__ . '/_auth.php';

// Named word lists — the persistent successor to the stateless ?words=a,b,c playlist
// URLs, and what docs/BACKLOG.md asks for under "publish favorites, custom lists".
//
//   GET  ?                       → { lists: [...] }              own lists
//   GET  ?slug=<slug>            → { list, items }               own list, or any public one
//   POST { action: create, title, description }
//   POST { action: update, id, title?, description?, is_public? }
//   POST { action: delete, id }
//   POST { action: add,    id, words: [...] }
//   POST { action: remove, id, words: [...] }
//
// One endpoint with an `action` rather than REST verbs, matching the flat, router-free
// style of the rest of api/.

$user    = current_user();
$user_id = (int) $user['id'];

/** URL-safe slug from a Romanian title, plus a short suffix to guarantee uniqueness. */
function slugify(string $title): string {
    $s = normalize_diacritics($title);              // reused from _lib.php
    $s = preg_replace('/[^a-z0-9]+/u', '-', $s) ?? '';
    $s = trim($s, '-');
    if ($s === '') $s = 'lista';
    return mb_substr($s, 0, 40) . '-' . bin2hex(random_bytes(3));
}

function list_row(PDO $pdo, int $id): ?array {
    $stmt = $pdo->prepare('SELECT * FROM lists WHERE id = ?');
    $stmt->execute([$id]);
    return $stmt->fetch() ?: null;
}

/** Load a list the caller is allowed to act on, or bail out. */
function owned_list(PDO $pdo, int $id, int $user_id): array {
    $row = list_row($pdo, $id);
    if (!$row) json_out(['error' => 'not_found'], 404);
    if ((int) $row['user_id'] !== $user_id) json_out(['error' => 'forbidden'], 403);
    return $row;
}

function touch_list(PDO $pdo, int $id): void {
    $pdo->prepare(
        'UPDATE lists
            SET item_count = (SELECT COUNT(*) FROM list_items WHERE list_id = ?),
                updated_at = ?
          WHERE id = ?'
    )->execute([$id, now_iso(), $id]);
}

function public_list_json(array $row): array {
    return [
        'id'          => (int) $row['id'],
        'slug'        => $row['slug'],
        'title'       => $row['title'],
        'description' => $row['description'],
        'is_public'   => (bool) $row['is_public'],
        'item_count'  => (int) $row['item_count'],
        'created_at'  => $row['created_at'],
        'updated_at'  => $row['updated_at'],
    ];
}

$pdo = app_db();

// ── Reads ─────────────────────────────────────────────────────────────────────

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'GET') {
    $slug = trim($_GET['slug'] ?? '');

    if ($slug === '') {
        $stmt = $pdo->prepare('SELECT * FROM lists WHERE user_id = ? ORDER BY updated_at DESC');
        $stmt->execute([$user_id]);
        json_out(['lists' => array_map('public_list_json', $stmt->fetchAll())]);
    }

    $stmt = $pdo->prepare('SELECT * FROM lists WHERE slug = ?');
    $stmt->execute([$slug]);
    $row = $stmt->fetch();
    if (!$row) json_out(['error' => 'not_found'], 404);
    // A private list is visible only to its owner; an unguessable slug is not access control.
    if (!$row['is_public'] && (int) $row['user_id'] !== $user_id) json_out(['error' => 'not_found'], 404);

    $stmt = $pdo->prepare('SELECT word, note, added_at FROM list_items WHERE list_id = ? ORDER BY position, added_at');
    $stmt->execute([$row['id']]);

    json_out([
        'list'  => public_list_json($row) + ['owner' => (int) $row['user_id'] === $user_id],
        'items' => $stmt->fetchAll(),
    ]);
}

// ── Writes ────────────────────────────────────────────────────────────────────

require_method('POST');
require_post_same_origin();

if (!rate_limit($user_id, 'lists', 60, 3600)) {
    json_out(['error' => 'rate_limited'], 429);
}

$in     = json_input();
$action = (string) ($in['action'] ?? '');
$now    = now_iso();

switch ($action) {
    case 'create': {
        $stmt = $pdo->prepare('SELECT COUNT(*) FROM lists WHERE user_id = ?');
        $stmt->execute([$user_id]);
        if ((int) $stmt->fetchColumn() >= MAX_LISTS_PER_USER) {
            json_out(['error' => 'too_many_lists'], 409);
        }

        $title = trim(is_string($in['title'] ?? null) ? $in['title'] : '');
        if ($title === '') $title = 'Listă fără nume';
        $title = mb_substr($title, 0, 120);

        $pdo->prepare(
            'INSERT INTO lists (user_id, slug, title, description, is_public, item_count, created_at, updated_at)
             VALUES (?, ?, ?, ?, 0, 0, ?, ?)'
        )->execute([
            $user_id,
            slugify($title),
            $title,
            mb_substr(is_string($in['description'] ?? null) ? $in['description'] : '', 0, 500),
            $now,
            $now,
        ]);

        json_out(['list' => public_list_json(list_row($pdo, (int) $pdo->lastInsertId()))]);
    }

    case 'update': {
        $row = owned_list($pdo, (int) ($in['id'] ?? 0), $user_id);

        $title = array_key_exists('title', $in) && is_string($in['title']) && trim($in['title']) !== ''
            ? mb_substr(trim($in['title']), 0, 120) : $row['title'];
        $desc = array_key_exists('description', $in) && is_string($in['description'])
            ? mb_substr($in['description'], 0, 500) : $row['description'];
        $pub = array_key_exists('is_public', $in) ? (!empty($in['is_public']) ? 1 : 0) : (int) $row['is_public'];

        // Publishing attaches a name to the list, so require one first. This is the
        // only place an anonymous device is asked for anything.
        if ($pub === 1 && !$row['is_public'] && ($user['nickname'] ?? '') === '') {
            json_out(['error' => 'nickname_required'], 409);
        }

        $pdo->prepare('UPDATE lists SET title = ?, description = ?, is_public = ?, updated_at = ? WHERE id = ?')
            ->execute([$title, $desc, $pub, $now, $row['id']]);

        json_out(['list' => public_list_json(list_row($pdo, (int) $row['id']))]);
    }

    case 'delete': {
        $row = owned_list($pdo, (int) ($in['id'] ?? 0), $user_id);
        $pdo->prepare('DELETE FROM list_items WHERE list_id = ?')->execute([$row['id']]);
        $pdo->prepare('DELETE FROM lists WHERE id = ?')->execute([$row['id']]);
        json_out(['deleted' => true]);
    }

    case 'add': {
        $row   = owned_list($pdo, (int) ($in['id'] ?? 0), $user_id);
        $words = is_array($in['words'] ?? null) ? array_slice($in['words'], 0, MAX_WORDS_PER_LIST) : [];
        $valid = filter_existing_words($words);

        $stmt = $pdo->prepare('SELECT COALESCE(MAX(position), 0), COUNT(*) FROM list_items WHERE list_id = ?');
        $stmt->execute([$row['id']]);
        [$pos, $count] = array_values($stmt->fetch(PDO::FETCH_NUM));

        $ins     = $pdo->prepare('INSERT OR IGNORE INTO list_items (list_id, word, position, note, added_at) VALUES (?, ?, ?, ?, ?)');
        $added   = 0;
        $pdo->beginTransaction();
        try {
            foreach ($words as $w) {
                if (!is_string($w) || !isset($valid[$w])) continue;
                if ($count + $added >= MAX_WORDS_PER_LIST) break;
                $ins->execute([$row['id'], $w, ++$pos, '', $now]);
                $added += $ins->rowCount();
            }
            touch_list($pdo, (int) $row['id']);
            $pdo->commit();
        } catch (Throwable $e) {
            $pdo->rollBack();
            throw $e;
        }

        json_out(['added' => $added, 'list' => public_list_json(list_row($pdo, (int) $row['id']))]);
    }

    case 'remove': {
        $row   = owned_list($pdo, (int) ($in['id'] ?? 0), $user_id);
        $words = is_array($in['words'] ?? null) ? $in['words'] : [];

        $del     = $pdo->prepare('DELETE FROM list_items WHERE list_id = ? AND word = ?');
        $removed = 0;
        $pdo->beginTransaction();
        try {
            foreach ($words as $w) {
                if (!is_string($w)) continue;
                $del->execute([$row['id'], $w]);
                $removed += $del->rowCount();
            }
            touch_list($pdo, (int) $row['id']);
            $pdo->commit();
        } catch (Throwable $e) {
            $pdo->rollBack();
            throw $e;
        }

        json_out(['removed' => $removed, 'list' => public_list_json(list_row($pdo, (int) $row['id']))]);
    }
}

json_out(['error' => 'unknown_action'], 400);
