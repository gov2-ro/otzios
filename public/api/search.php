<?php
declare(strict_types=1);
require_once __DIR__ . '/_lib.php';

$q         = trim($_GET['q']         ?? '');
$word_tier = trim($_GET['word_tier'] ?? 'forgotten');
$verdict   = trim($_GET['verdict']   ?? '');
$tier      = trim($_GET['tier']      ?? '');
$register  = trim($_GET['register']  ?? '');
$domain    = trim($_GET['domain']    ?? '');
$etym      = trim($_GET['etymology'] ?? '');
$pos       = trim($_GET['pos']       ?? '');
$has_def   = trim($_GET['has_def']   ?? '');
$marks     = trim($_GET['marks']     ?? 'all');
$sort      = trim($_GET['sort']      ?? '');
$page      = max(1, (int)($_GET['page'] ?? 1));
$offset    = ($page - 1) * PAGE_SIZE;

// marked_words is a comma-separated list sent by client JS for marks filtering
$marked_words_raw = trim($_GET['marked_words'] ?? '');
$marked_words = $marked_words_raw !== ''
    ? array_filter(array_map('trim', explode(',', $marked_words_raw)))
    : [];

$valid_tiers = ['forgotten', 'rare_in_use'];
$word_tier   = in_array($word_tier, $valid_tiers, true) ? $word_tier : 'forgotten';

$conditions = ['word_tier = ?'];
$params     = [$word_tier];

if ($q !== '') {
    $conditions[] = 'word LIKE ?';
    $params[]     = '%' . $q . '%';
}
if ($verdict !== '') {
    $conditions[] = 'verdict = ?';
    $params[]     = $verdict;
}
if ($tier !== '') {
    $conditions[] = 'confidence_tier = ?';
    $params[]     = $tier;
}
foreach ([
    ['dex_register', $register],
    ['dex_domain',   $domain],
    ['dex_etymology', $etym],
    ['dex_pos',      $pos],
] as [$col, $val]) {
    if ($val !== '') {
        $conditions[] = "('|'||{$col}||'|' LIKE ?)";
        $params[]     = '%|' . $val . '|%';
    }
}
if ($has_def === '1') {
    $conditions[] = 'definition IS NOT NULL';
} elseif ($has_def === '0') {
    $conditions[] = 'definition IS NULL';
}

// Client-driven marks filter
if (in_array($marks, ['bookmarked', 'noted', 'marked'], true) || str_starts_with($marks, 'tag:')) {
    if ($marked_words !== []) {
        $placeholders = implode(',', array_fill(0, count($marked_words), '?'));
        $conditions[] = "word IN ($placeholders)";
        $params       = array_merge($params, array_values($marked_words));
    } else {
        // Filter matches nothing — return empty
        $conditions[] = '1=0';
    }
} elseif ($marks === 'unmarked') {
    if ($marked_words !== []) {
        $placeholders = implode(',', array_fill(0, count($marked_words), '?'));
        $conditions[] = "word NOT IN ($placeholders)";
        $params       = array_merge($params, array_values($marked_words));
    }
    // If no marked words, unmarked = all words — no extra condition needed
}

$where    = $conditions ? 'WHERE ' . implode(' AND ', $conditions) : '';
global $SORT_OPTIONS;
$order_by = $SORT_OPTIONS[$sort] ?? $SORT_OPTIONS['rare'];

// Count total matching rows
$count_sql = "SELECT COUNT(*) FROM words $where";
$total     = (int)db()->prepare($count_sql)->execute($params) ? db()->prepare($count_sql)->execute($params) : 0;
$count_stmt = db()->prepare($count_sql);
$count_stmt->execute($params);
$total = (int)$count_stmt->fetchColumn();

// Fetch page
$page_stmt = db()->prepare("SELECT * FROM words $where ORDER BY $order_by LIMIT ? OFFSET ?");
$page_stmt->execute(array_merge($params, [PAGE_SIZE, $offset]));
$words = $page_stmt->fetchAll();

$next_url = null;
if ($page * PAGE_SIZE < $total) {
    $args         = $_GET;
    $args['page'] = $page + 1;
    $next_url     = BASE . '/api/search.php?' . http_build_query($args);
}

header('Content-Type: text/html; charset=utf-8');
render('word_list.php', [
    'words'    => $words,
    'total'    => $total,
    'page'     => $page,
    'next_url' => $next_url,
]);
