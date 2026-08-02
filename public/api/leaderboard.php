<?php
declare(strict_types=1);
require_once __DIR__ . '/_auth.php';

// Top streaks. Only users who chose a display name appear — an anonymous device has
// nothing to show and no claim to a rank, so opting in is what publishes you.
//
//   GET → { entries: [{rank, nickname, best, total, correct}], you: {...}|null }
//
// Ranks come from game_stats, which game.php recomputes server-side on every answer;
// nothing here trusts a number the client sent.

require_method('GET');

$user    = current_user();
$user_id = (int) $user['id'];
$pdo     = app_db();

const BOARD_SIZE = 50;

$stmt = $pdo->prepare(
    "SELECT u.id, u.nickname, s.best_streak, s.total, s.correct
       FROM game_stats s
       JOIN users u ON u.id = s.user_id
      WHERE s.mode = 'all'
        AND u.nickname IS NOT NULL AND TRIM(u.nickname) != ''
        AND s.best_streak > 0
      ORDER BY s.best_streak DESC, s.correct DESC, s.updated_at ASC
      LIMIT " . BOARD_SIZE
);
$stmt->execute();

$entries = [];
$rank    = 0;
$you     = null;
foreach ($stmt->fetchAll() as $r) {
    $rank++;
    $row = [
        'rank'     => $rank,
        'nickname' => $r['nickname'],
        'best'     => (int) $r['best_streak'],
        'total'    => (int) $r['total'],
        'correct'  => (int) $r['correct'],
        'you'      => (int) $r['id'] === $user_id,
    ];
    if ($row['you']) $you = $row;
    $entries[] = $row;
}

// Off the board: report the caller's own standing so there is something to chase.
if ($you === null) {
    $stmt = $pdo->prepare("SELECT best_streak, total, correct FROM game_stats WHERE user_id = ? AND mode = 'all'");
    $stmt->execute([$user_id]);
    if ($mine = $stmt->fetch()) {
        $ahead = $pdo->prepare(
            "SELECT COUNT(*) FROM game_stats s JOIN users u ON u.id = s.user_id
              WHERE s.mode = 'all' AND u.nickname IS NOT NULL AND TRIM(u.nickname) != ''
                AND s.best_streak > ?"
        );
        $ahead->execute([(int) $mine['best_streak']]);
        $you = [
            'rank'     => ((int) $ahead->fetchColumn()) + 1,
            'nickname' => $user['nickname'],
            'best'     => (int) $mine['best_streak'],
            'total'    => (int) $mine['total'],
            'correct'  => (int) $mine['correct'],
            'you'      => true,
            'listed'   => false,          // no nickname yet, so not on the public board
        ];
    }
}

json_out(['entries' => $entries, 'you' => $you]);
