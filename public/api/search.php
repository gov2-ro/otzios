<?php
declare(strict_types=1);
require_once __DIR__ . '/_lib.php';

$q         = trim($_GET['q']         ?? '');
$word_tier = trim($_GET['word_tier'] ?? 'forgotten');
$verdict   = trim($_GET['verdict']   ?? '');
$register  = trim($_GET['register']  ?? '');
$domain    = trim($_GET['domain']    ?? '');
$etym      = trim($_GET['etymology'] ?? '');

// tier[] and pos[] are multi-value checkboxes; also accept comma-separated from URL deep links
function parse_multi(mixed $raw): array {
    if ($raw === null) return [];
    if (is_array($raw)) return array_values(array_filter(array_map('trim', $raw)));
    return array_values(array_filter(array_map('trim', explode(',', (string)$raw))));
}
global $POS_OPTIONS;
$TIER_TOTAL = 5; // corpus_extinct, corpus_declining, corpus_historical_only, dex_invechit_absent, dex_absent_highfreq
$POS_TOTAL  = count($POS_OPTIONS);
$tier_values = parse_multi($_GET['tier'] ?? null);
$pos_values  = parse_multi($_GET['pos']  ?? null);
$has_def   = trim($_GET['has_def']   ?? '');
$dex_max   = trim($_GET['dex_max']   ?? '');
$dict_min  = trim($_GET['dict_min']  ?? '');
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
    $q_norm       = normalize_diacritics($q);
    $conditions[] = '(word LIKE ? OR word_normalized LIKE ?)';
    $params[]     = '%' . $q . '%';
    $params[]     = '%' . $q_norm . '%';
}
if ($verdict !== '') {
    $conditions[] = 'verdict = ?';
    $params[]     = $verdict;
}
// Only filter if some-but-not-all tiers selected; "all" or "none" = no filter (preserves NULLs)
if ($tier_values !== [] && count($tier_values) < $TIER_TOTAL) {
    $ph = implode(',', array_fill(0, count($tier_values), '?'));
    $conditions[] = "confidence_tier IN ($ph)";
    $params       = array_merge($params, $tier_values);
}
foreach ([
    ['dex_register', $register],
    ['dex_domain',   $domain],
    ['dex_etymology', $etym],
] as [$col, $val]) {
    if ($val !== '') {
        $conditions[] = "('|'||{$col}||'|' LIKE ?)";
        $params[]     = '%|' . $val . '|%';
    }
}
// POS multi-select: OR across selected values; "all" or "none" = no filter
if ($pos_values !== [] && count($pos_values) < $POS_TOTAL) {
    $or_parts = array_fill(0, count($pos_values), "('|'||dex_pos||'|' LIKE ?)");
    $conditions[] = '(' . implode(' OR ', $or_parts) . ')';
    foreach ($pos_values as $pv) {
        $params[] = '%|' . $pv . '|%';
    }
}
if ($has_def === '1') {
    $conditions[] = 'definition IS NOT NULL';
} elseif ($has_def === '0') {
    $conditions[] = 'definition IS NULL';
}
$dict_min_int = (int)$dict_min;
if ($dict_min_int > 0) {
    $conditions[] = 'dict_count >= ?';
    $params[]     = $dict_min_int;
}

// DEX-rarity ceiling — only meaningful on the rare tab. The rare_in_use tier has
// no intrinsic rarity gate, so this restricts it to words DEX itself rates as
// non-standard (frequency <= ceiling). Defaults to 0.60 when unset; 'all'
// disables it. The 0.01 floor drops frequency=0 (missing data, per CLAUDE.md).
// Ignored on the forgotten tab.
if ($word_tier === 'rare_in_use') {
    $ceiling = $dex_max === '' ? 0.60 : ($dex_max === 'all' ? null : (float)$dex_max);
    if ($ceiling !== null && $ceiling > 0) {
        $conditions[] = 'dex_frequency BETWEEN ? AND ?';
        $params[]     = 0.01;
        $params[]     = $ceiling;
    }
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
