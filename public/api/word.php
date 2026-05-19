<?php
declare(strict_types=1);
require_once __DIR__ . '/_lib.php';

$word = trim($_GET['word'] ?? '');
if ($word === '') {
    http_response_code(400);
    exit('Bad request');
}

$stmt = db()->prepare('SELECT * FROM words WHERE word = ?');
$stmt->execute([$word]);
$w = $stmt->fetch();

if ($w === false) {
    http_response_code(404);
    exit('Not found');
}

header('Content-Type: text/html; charset=utf-8');
render('detail.php', ['w' => $w]);
