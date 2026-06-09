<?php
declare(strict_types=1);
require_once __DIR__ . '/_lib.php';

['conditions' => $conditions, 'params' => $params] = build_word_filter($_GET);
$where = $conditions ? 'WHERE ' . implode(' AND ', $conditions) : '';

// ── Query 1: summary numbers ──────────────────────────────────────────────────
$sum_stmt = db()->prepare(
    "SELECT COUNT(*) AS total,
            SUM(CASE WHEN definition IS NOT NULL THEN 1 ELSE 0 END) AS with_def
     FROM words $where"
);
$sum_stmt->execute($params);
$summary = $sum_stmt->fetch();
$total   = (int)$summary['total'];

// ── Query 2: confidence_tier breakdown (single-value column, GROUP BY is exact) ─
$tier_stmt = db()->prepare(
    "SELECT confidence_tier, COUNT(*) AS cnt
     FROM words $where
     GROUP BY confidence_tier
     ORDER BY cnt DESC"
);
$tier_stmt->execute($params);
$tier_rows = $tier_stmt->fetchAll();

// ── Query 3: pipe-delimited fields — single scan, PHP aggregation ─────────────
$agg_stmt = db()->prepare(
    "SELECT dex_etymology, dex_register, dex_domain, dex_pos
     FROM words $where"
);
$agg_stmt->execute($params);

$etym_counts = [];
$reg_counts  = [];
$dom_counts  = [];
$pos_counts  = [];

while ($row = $agg_stmt->fetch(PDO::FETCH_NUM)) {
    [$etym, $reg, $dom, $pos] = $row;
    foreach (split_pipe($etym) as $v) { $etym_counts[$v] = ($etym_counts[$v] ?? 0) + 1; }
    foreach (split_pipe($reg)  as $v) { $reg_counts[$v]  = ($reg_counts[$v]  ?? 0) + 1; }
    foreach (split_pipe($dom)  as $v) { $dom_counts[$v]  = ($dom_counts[$v]  ?? 0) + 1; }
    foreach (split_pipe($pos)  as $v) { $pos_counts[$v]  = ($pos_counts[$v]  ?? 0) + 1; }
}

// Sort and slice top-N
arsort($etym_counts); $etym_top = array_slice($etym_counts, 0, 15, true);
arsort($reg_counts);
arsort($dom_counts);  $dom_top  = array_slice($dom_counts,  0, 10, true);
arsort($pos_counts);  $pos_top  = array_slice($pos_counts,  0,  8, true);

header('Content-Type: text/html; charset=utf-8');
render('stats_panels.php', [
    'summary'    => $summary,
    'total'      => $total,
    'tier_rows'  => $tier_rows,
    'etym_top'   => $etym_top,
    'reg_counts' => $reg_counts,
    'dom_top'    => $dom_top,
    'pos_top'    => $pos_top,
]);
