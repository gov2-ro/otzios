<?php
declare(strict_types=1);
require_once __DIR__ . '/_lib.php';

// Random word that respects the current server-side filters (verdict, tier, POS,
// taxonomy, explore ranges, word_tier) plus the text query — powers "🎲 surprise".
['conditions' => $conditions, 'params' => $params] = build_word_filter($_GET);

$q = trim($_GET['q'] ?? '');
if ($q !== '') {
    $q_norm       = normalize_diacritics($q);
    $conditions[] = '(word LIKE ? OR word_normalized LIKE ?)';
    $params[]     = '%' . $q . '%';
    $params[]     = '%' . $q_norm . '%';
}

$where = $conditions ? 'WHERE ' . implode(' AND ', $conditions) : '';
$stmt  = db()->prepare("SELECT word FROM words $where ORDER BY RANDOM() LIMIT 1");
$stmt->execute($params);
$word = $stmt->fetchColumn();

header('Content-Type: application/json; charset=utf-8');
echo json_encode(['word' => $word !== false ? $word : null], JSON_UNESCAPED_UNICODE);
