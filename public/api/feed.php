<?php
declare(strict_types=1);
require_once __DIR__ . '/_lib.php';

// A batch of random words (with definitions) for the card / swipe feed, respecting
// the current filters — or, when a playlist is open, drawn from the playlist alone
// (see api/search.php for why a curated list is not filtered again).
$playlist   = playlist_words($_GET);
$conditions = [];
$params     = [];
if ($playlist === null) {
    ['conditions' => $conditions, 'params' => $params] = build_word_filter($_GET);
} else {
    playlist_condition($playlist, $conditions, $params);
}

$q = trim($_GET['q'] ?? '');
if ($q !== '') {
    $q_norm       = normalize_diacritics($q);
    $conditions[] = '(word LIKE ? OR word_normalized LIKE ?)';
    $params[]     = '%' . $q . '%';
    $params[]     = '%' . $q_norm . '%';
}
// Cards need content — only feed words that have a definition.
$conditions[] = 'definition IS NOT NULL';

$limit = (int)($_GET['n'] ?? 24);
if ($limit < 1 || $limit > 100) $limit = 24;

$where = $conditions ? 'WHERE ' . implode(' AND ', $conditions) : '';
$stmt  = db()->prepare(
    "SELECT word, definition, verdict, dex_pos, dex_frequency, sources
     FROM words $where ORDER BY RANDOM() LIMIT $limit"
);
$stmt->execute($params);

header('Content-Type: application/json; charset=utf-8');
echo json_encode(['words' => $stmt->fetchAll()], JSON_UNESCAPED_UNICODE);
