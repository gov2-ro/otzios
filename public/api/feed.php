<?php
declare(strict_types=1);
require_once __DIR__ . '/_lib.php';

// A batch of random words (with definitions) for the card / swipe feed, drawn from the
// same scope as the list itself: matches of a typed query, else an open playlist, else
// the filter sheet. See word_scope() in _lib.php.
$conditions = [];
$params     = [];
word_scope($_GET, $conditions, $params);

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
