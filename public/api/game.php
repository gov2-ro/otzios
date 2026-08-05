<?php
declare(strict_types=1);
require_once __DIR__ . '/_auth.php';

// Grade one quiz answer and record it.
//
//   POST { qid, choice_id, ms }
//    →   { correct, correct_id, answer, streak, best, total }
//
// The client cannot grade itself: quiz.php never tells it which option is right.
// `qid` is an encrypted token carrying the correct id, so no server-side session is
// needed — which matters on a shared host with no persistent process. It must be
// encrypted rather than signed: a signed payload is readable, and reading it would
// give away the answer.
//
// Every answer is appended to game_events. game_stats is a derived cache: streak and
// best are recomputed here rather than trusted from the client, and the whole table
// can be rebuilt from game_events if it is ever lost.

require_method('POST');
require_post_same_origin();

$user    = current_user();
$user_id = (int) $user['id'];

// Generous enough for fast keyboard play (1-4 keys), tight enough that a script
// can't grind the leaderboard.
if (!rate_limit($user_id, 'answer', 120, 60)) {
    json_out(['error' => 'rate_limited'], 429);
}

$in  = json_input();
$qid = is_string($in['qid'] ?? null) ? $in['qid'] : '';

$q = open_token($qid);
if ($q === null) {
    // Expired or tampered with. The client's recourse is to load a fresh question.
    json_out(['error' => 'bad_question'], 400);
}

// Single use: a winning token must not be replayable to farm a streak.
if (!consume_nonce((string) $q['n'])) {
    json_out(['error' => 'already_answered'], 409);
}

$mode       = in_array($q['m'] ?? '', ['sense', 'quiz'], true) ? $q['m'] : 'sense';
$correct_id = (int) $q['a'];
$word       = (string) $q['w'];
$choice_id  = isset($in['choice_id']) ? (int) $in['choice_id'] : -1;
$correct    = $choice_id === $correct_id;
$ms         = isset($in['ms']) ? max(0, min(600000, (int) $in['ms'])) : null;

$pdo = app_db();
$now = now_iso();

$pdo->beginTransaction();
try {
    $pdo->prepare(
        'INSERT INTO game_events (user_id, mode, word, chosen, correct, ms, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)'
    )->execute([$user_id, $mode, $word, (string) $choice_id, $correct ? 1 : 0, $ms, $now]);

    // 'all' is the streak the UI shows — deliberately shared across sense and quiz,
    // matching the existing behaviour. Per-mode rows are kept for later analysis.
    //
    // The new counters are computed in PHP rather than in the UPDATE expression.
    // PDO binds parameters as strings, and SQLite compares a bare '1' = 1 as FALSE
    // (no affinity is applied between two expressions), so a `CASE WHEN :ok = 1`
    // would silently never fire and pin every streak to zero.
    $read = $pdo->prepare('SELECT streak, best_streak, total, correct FROM game_stats WHERE user_id = ? AND mode = ?');
    $write = $pdo->prepare(
        'INSERT INTO game_stats (user_id, mode, streak, best_streak, total, correct, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)
         ON CONFLICT(user_id, mode) DO UPDATE SET
            streak      = excluded.streak,
            best_streak = excluded.best_streak,
            total       = excluded.total,
            correct     = excluded.correct,
            updated_at  = excluded.updated_at'
    );

    foreach ([$mode, 'all'] as $bucket) {
        $read->execute([$user_id, $bucket]);
        $prev = $read->fetch() ?: ['streak' => 0, 'best_streak' => 0, 'total' => 0, 'correct' => 0];

        $streak = $correct ? (int) $prev['streak'] + 1 : 0;
        $write->execute([
            $user_id,
            $bucket,
            $streak,
            max((int) $prev['best_streak'], $streak),
            (int) $prev['total'] + 1,
            (int) $prev['correct'] + ($correct ? 1 : 0),
            $now,
        ]);
    }

    $pdo->commit();
} catch (Throwable $e) {
    $pdo->rollBack();
    throw $e;
}

// Own-mode bucket, not 'all': the header shows correct/missed for whichever game is
// currently being played, so it needs that game's tally, not the merged total.
$stmt = $pdo->prepare('SELECT streak, best_streak, total, correct FROM game_stats WHERE user_id = ? AND mode = ?');
$stmt->execute([$user_id, $mode]);
$stats = $stmt->fetch() ?: ['streak' => 0, 'best_streak' => 0, 'total' => 0, 'correct' => 0];

json_out([
    'correct'       => $correct,
    'correct_id'    => $correct_id,
    'answer'        => $word,
    'streak'        => (int) $stats['streak'],
    'best'          => (int) $stats['best_streak'],
    'total'         => (int) $stats['total'],
    'total_correct' => (int) $stats['correct'],
]);
