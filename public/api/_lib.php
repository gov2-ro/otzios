<?php
declare(strict_types=1);

define('DB_PATH', __DIR__ . '/../data/ui.db');

// URL prefix for the public/ directory, e.g. '' (root) or '/otios' (subdirectory).
// Computed from DOCUMENT_ROOT vs the actual filesystem path of public/.
(function () {
    $doc_root = rtrim($_SERVER['DOCUMENT_ROOT'] ?? '', '/');
    $pub_dir  = rtrim(dirname(__DIR__), '/');   // parent of api/ = public/
    $base     = $doc_root !== '' ? substr($pub_dir, strlen($doc_root)) : '';
    define('BASE', $base === false ? '' : rtrim($base, '/'));
})();
define('PAGE_SIZE', 250);

$SORT_OPTIONS = [
    'rare'     => 'COALESCE(modern_ppm, -1) ASC',
    'declined' => 'log_ratio DESC NULLS LAST',
    'dex_freq' => 'dex_frequency ASC NULLS LAST',
    'alpha'    => 'word ASC',
];

$QUICK_TAGS = [
    ['ignore', 'i'],
    ['boring', 'B'],
    ['funny',  'f'],
    ['remove', 'x'],
];

$QUICK_TAG_EMOJIS = [
    'ignore' => '🙈',
    'boring' => '💤',
    'funny'  => '😄',
    'remove' => '❌',
];

$POS_OPTIONS = [
    ['substantiv feminin',  's.f.'],
    ['substantiv neutru',   's.n.'],
    ['substantiv masculin', 's.m.'],
    ['adjectiv',            'adj.'],
    ['verb',                'vb.'],
    ['adverb',              'adv.'],
    ['participiu',          'part.'],
    ['interjecție',         'interj.'],
];

function db(): PDO {
    static $pdo = null;
    if ($pdo === null) {
        $pdo = new PDO('sqlite:' . DB_PATH, null, null, [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
        $pdo->exec('PRAGMA query_only = ON');
    }
    return $pdo;
}

function e(?string $s): string {
    return htmlspecialchars($s ?? '', ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function urlenc(string $s): string {
    return rawurlencode($s);
}

function vocab(string $kind): array {
    $stmt = db()->prepare('SELECT value FROM vocab WHERE kind = ? ORDER BY count DESC');
    $stmt->execute([$kind]);
    return $stmt->fetchAll(PDO::FETCH_COLUMN);
}

function render(string $partial, array $vars = []): void {
    extract($vars, EXTR_SKIP);
    include __DIR__ . '/_partials/' . $partial;
}
