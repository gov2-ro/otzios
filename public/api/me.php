<?php
declare(strict_types=1);
require_once __DIR__ . '/_auth.php';

// Identity probe. Called once on page load: mints the device identity if needed and
// tells the client what the server already holds, so store.js knows whether it still
// has a one-time localStorage migration to push.

require_method('GET');
$user = current_user();
$pdo  = app_db();

$stmt = $pdo->prepare('SELECT COUNT(*) FROM annotations WHERE user_id = ? AND deleted = 0');
$stmt->execute([$user['id']]);
$annotations = (int) $stmt->fetchColumn();

$stmt = $pdo->prepare('SELECT COUNT(*) FROM lists WHERE user_id = ?');
$stmt->execute([$user['id']]);
$lists = (int) $stmt->fetchColumn();

$stmt = $pdo->prepare("SELECT streak, best_streak, total, correct FROM game_stats WHERE user_id = ? AND mode = 'all'");
$stmt->execute([$user['id']]);
$stats = $stmt->fetch() ?: ['streak' => 0, 'best_streak' => 0, 'total' => 0, 'correct' => 0];

json_out([
    'public_id' => $user['public_id'],
    'nickname'  => $user['nickname'],
    'counts'    => ['annotations' => $annotations, 'lists' => $lists],
    'stats'     => [
        'streak'  => (int) $stats['streak'],
        'best'    => (int) $stats['best_streak'],
        'total'   => (int) $stats['total'],
        'correct' => (int) $stats['correct'],
    ],
]);
