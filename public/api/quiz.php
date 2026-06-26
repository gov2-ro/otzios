<?php
declare(strict_types=1);
require_once __DIR__ . '/_lib.php';

// One quiz question: a target word (+ definition) and 4 shuffled word choices,
// with distractors drawn from the same part of speech where possible.
// Also serves the flashcard mode (which just uses word + definition).
$pdo = db();
$BASE = "word_tier='forgotten' AND definition IS NOT NULL";

$target = $pdo->query(
    "SELECT word, definition, dex_pos FROM words
     WHERE $BASE AND (proper_noun_like IS NULL OR proper_noun_like = 0) AND dict_count >= 3
     ORDER BY RANDOM() LIMIT 1"
)->fetch();

if (!$target) {
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['error' => 'no words']);
    exit;
}

$pos_first = trim(explode('|', $target['dex_pos'] ?? '')[0]);
$choices   = [$target['word']];

if ($pos_first !== '') {
    $st = $pdo->prepare(
        "SELECT word FROM words
         WHERE $BASE AND word != ? AND ('|'||dex_pos||'|' LIKE ?)
         ORDER BY RANDOM() LIMIT 3"
    );
    $st->execute([$target['word'], '%|' . $pos_first . '|%']);
    foreach ($st->fetchAll(PDO::FETCH_COLUMN) as $w) { $choices[] = $w; }
}

// Fill from the general pool if same-POS distractors were scarce
if (count($choices) < 4) {
    $ph = implode(',', array_fill(0, count($choices), '?'));
    $st = $pdo->prepare(
        "SELECT word FROM words WHERE $BASE AND word NOT IN ($ph) ORDER BY RANDOM() LIMIT ?"
    );
    $st->execute(array_merge($choices, [4 - count($choices)]));
    foreach ($st->fetchAll(PDO::FETCH_COLUMN) as $w) { $choices[] = $w; }
}

shuffle($choices);

header('Content-Type: application/json; charset=utf-8');
echo json_encode([
    'word'       => $target['word'],
    'definition' => $target['definition'],
    'pos'        => $pos_first,
    'choices'    => $choices,
    'answer'     => $target['word'],
], JSON_UNESCAPED_UNICODE);
