<?php
declare(strict_types=1);
require_once __DIR__ . '/_lib.php';

$sort      = trim($_GET['sort']      ?? '');
$page      = max(1, (int)($_GET['page'] ?? 1));
$offset    = ($page - 1) * PAGE_SIZE;
$marks     = trim($_GET['marks']     ?? 'all');
$q         = trim($_GET['q']         ?? '');
$verdict   = trim($_GET['verdict']   ?? '');

$marked_words_raw = trim($_GET['marked_words'] ?? '');
$marked_words = $marked_words_raw !== ''
    ? array_filter(array_map('trim', explode(',', $marked_words_raw)))
    : [];

// Build shared server-side filters
['conditions' => $conditions, 'params' => $params, 'word_tier' => $word_tier] = build_word_filter($_GET);

// search-only: text search
if ($q !== '') {
    $q_norm       = normalize_diacritics($q);
    $conditions[] = '(word LIKE ? OR word_normalized LIKE ?)';
    $params[]     = '%' . $q . '%';
    $params[]     = '%' . $q_norm . '%';
}
// search-only: verdict
if ($verdict !== '') {
    $conditions[] = 'verdict = ?';
    $params[]     = $verdict;
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
