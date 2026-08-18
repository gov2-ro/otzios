<?php
declare(strict_types=1);
require_once __DIR__ . '/_lib.php';
require_once __DIR__ . '/_syn.php';

// Public read-only fragment endpoint. Never requires _appdb.php or _auth.php -- a device
// token must not be minted for a crawler passing through /sinonime. See _syn.php's header.
header('Content-Type: text/html; charset=utf-8');

if (isset($_GET['ac'])) {
    $rows = syn_autocomplete((string) ($_GET['q'] ?? ''));
    render('syn_autocomplete.php', ['rows' => $rows]);
    exit;
}

$q = trim((string) ($_GET['q'] ?? ''));
$resolved     = $q !== '' ? syn_resolve($q) : ['word' => null, 'suggestions' => []];
$neighborhood = $resolved['word'] ? syn_neighborhood($resolved['word']) : null;

render('syn_result.php', ['q' => $q, 'resolved' => $resolved, 'neighborhood' => $neighborhood]);
