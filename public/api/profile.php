<?php
declare(strict_types=1);
require_once __DIR__ . '/_auth.php';

// Set the display name. Asked for just-in-time, only when a user opts into something
// public (publishing a list, appearing on the leaderboard) — never as a signup wall.
//
//   POST { nickname } → { nickname }

require_method('POST');
require_post_same_origin();

$user    = current_user();
$user_id = (int) $user['id'];

if (!rate_limit($user_id, 'profile', 20, 3600)) {
    json_out(['error' => 'rate_limited'], 429);
}

$in   = json_input();
$name = trim(is_string($in['nickname'] ?? null) ? $in['nickname'] : '');

// Control characters would let a name break the layout of the leaderboard it appears on.
$name = preg_replace('/[\p{C}]+/u', '', $name) ?? '';
$name = trim(mb_substr($name, 0, 30));

if (mb_strlen($name) < 2) {
    json_out(['error' => 'nickname_too_short'], 400);
}

app_db()->prepare('UPDATE users SET nickname = ? WHERE id = ?')->execute([$name, $user_id]);

json_out(['nickname' => $name]);
