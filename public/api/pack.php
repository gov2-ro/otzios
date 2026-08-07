<?php
declare(strict_types=1);
require_once __DIR__ . '/_auth.php';

// Word-list ⇄ compact-id codec, exposed so the browser never has to carry the
// 25k-word dictionary that pack_words()/unpack_words() read from ui.db.
//
//   POST { words: [...] }  → { w: "1.bcf.1", count: 2 }
//   GET  ?w=1.bcf.1        → { words: [...], count: 2 }
//
// Read-only against ui.db, so there is no rate limit — the caps in _lib.php
// (WORD_PACK_MAX) already bound the work per request.

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'GET') {
    $words = unpack_words((string) ($_GET['w'] ?? ''));
    json_out(['words' => $words, 'count' => count($words)]);
}

require_method('POST');
require_post_same_origin();

$in    = json_input();
$words = is_array($in['words'] ?? null) ? $in['words'] : [];
$w     = pack_words($words);

json_out(['w' => $w, 'count' => $w === '' ? 0 : substr_count($w, '.')]);
