<?php
declare(strict_types=1);
require_once __DIR__ . '/_lib.php';

// Random word from whatever the reader is looking at — powers "🎲 surprise".
//
// The form serializes everything, including the query box and the hidden `w` input, so
// this draws from the same scope api/search.php just listed: matches of a typed query,
// else an open playlist, else the filter sheet. Drawing from the filters while the list
// on screen came from a search would hand back a word that is not in it.
$conditions = [];
$params     = [];
word_scope($_GET, $conditions, $params);

$where = $conditions ? 'WHERE ' . implode(' AND ', $conditions) : '';
$stmt  = db()->prepare("SELECT word FROM words $where ORDER BY RANDOM() LIMIT 1");
$stmt->execute($params);
$word = $stmt->fetchColumn();

header('Content-Type: application/json; charset=utf-8');
echo json_encode(['word' => $word !== false ? $word : null], JSON_UNESCAPED_UNICODE);
