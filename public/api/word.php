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

// Full sense tree (docs/senses-plan.md), additive to $w['definition'] — never a
// replacement for it (see the invariants in CLAUDE.md §"Key data contracts"). A
// deployed ui.db built before this feature landed has neither table, and the panel
// must still open, so both queries are guarded rather than assumed to succeed.
$senses = [];
$cites_by_sense = [];
try {
    $sstmt = db()->prepare('SELECT * FROM senses WHERE word = ? ORDER BY ord');
    $sstmt->execute([$word]);
    $senses = $sstmt->fetchAll();

    $cstmt = db()->prepare(
        'SELECT * FROM sense_citations WHERE word = ? ORDER BY sense_ord, ord');
    $cstmt->execute([$word]);
    foreach ($cstmt->fetchAll() as $c) {
        $cites_by_sense[(int) $c['sense_ord']][] = $c;
    }
} catch (PDOException $e) {
    $senses = [];
    $cites_by_sense = [];
}

header('Content-Type: text/html; charset=utf-8');
render('detail.php', ['w' => $w, 'senses' => $senses, 'cites_by_sense' => $cites_by_sense]);
