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

// Skin discovery (assets/skins/*.css). Required here so every page that pulls
// in _lib.php — index, joc, stats, lista — gets the dropdown for free.
require_once __DIR__ . '/_skins.php';

$SORT_OPTIONS = [
    'rare'     => 'COALESCE(modern_ppm, -1) ASC',
    'declined' => 'log_ratio DESC NULLS LAST',
    'dex_freq' => 'dex_frequency ASC NULLS LAST',
    'alpha'    => 'word ASC',
];

$QUICK_TAGS = [
    ['ascunde', 'a'],
    ['lol',     'l'],
    ['meh',     'm'],
];

$QUICK_TAG_EMOJIS = [
    'ascunde' => '🙈',
    'lol'     => '😂',
    'meh'     => '😐',
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

function normalize_diacritics(string $s): string {
    $s = mb_strtolower($s, 'UTF-8');
    return str_replace(
        ['ț', 'ș', 'ţ', 'ş', 'ă', 'â', 'î'],
        ['t', 's', 't', 's', 'a', 'a', 'i'],
        $s
    );
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

function parse_multi(mixed $raw): array {
    if ($raw === null) return [];
    if (is_array($raw)) return array_values(array_filter(array_map('trim', $raw)));
    return array_values(array_filter(array_map('trim', explode(',', (string)$raw))));
}

function split_pipe(?string $s): array {
    if ($s === null || $s === '') return [];
    return array_values(
        array_filter(array_map('trim', explode('|', $s)), fn(string $v) => $v !== '')
    );
}

function db_has_column(string $col): bool {
    static $cols = null;
    if ($cols === null) {
        $cols = array_column(db()->query('PRAGMA table_info(words)')->fetchAll(), 'name');
    }
    return in_array($col, $cols, true);
}

// ── Packed word lists ─────────────────────────────────────────────────────────
//
// A share URL carries base36 word ids rather than the words: Romanian diacritics
// percent-encode to six characters each (ă → %C4%83), so twenty words run past 300
// characters as `?words=`, versus about 70 as `?w=`.
//
// The ids come from data/word_ids.tsv via the word_id column (tools/word_ids.py) and
// are append-only, so a link shared today still resolves after any number of data
// rebuilds. The leading version segment is the escape hatch if that ever has to
// change — an old client meeting a version it does not know decodes nothing rather
// than decoding the wrong words.

const WORD_PACK_VERSION = 1;
const WORD_PACK_MAX     = 500;   // ceiling on one URL, so `?w=` can't force a huge query

/** ['abacă','oțios'] → "1.1.396f". Unknown words are dropped; '' if none survive. */
function pack_words(array $words): string {
    $words = array_slice(array_values(array_unique(array_filter(
        $words, fn($w) => is_string($w) && $w !== ''
    ))), 0, WORD_PACK_MAX);
    if ($words === [] || !db_has_column('word_id')) return '';

    $ids = [];
    foreach (array_chunk($words, 400) as $chunk) {
        $ph   = implode(',', array_fill(0, count($chunk), '?'));
        $stmt = db()->prepare("SELECT word, word_id FROM words WHERE word IN ($ph) AND word_id IS NOT NULL");
        $stmt->execute($chunk);
        foreach ($stmt->fetchAll() as $r) { $ids[$r['word']] = (int) $r['word_id']; }
    }

    $out = [];
    foreach ($words as $w) {                       // caller's order is the payload
        if (isset($ids[$w])) $out[] = base_convert((string) $ids[$w], 10, 36);
    }
    return $out === [] ? '' : WORD_PACK_VERSION . '.' . implode('.', $out);
}

/** "1.1.396f" → ['abacă','oțios'], in URL order. [] on any version or format problem. */
function unpack_words(string $packed): array {
    $parts = explode('.', trim($packed));
    if (count($parts) < 2) return [];
    if (array_shift($parts) !== (string) WORD_PACK_VERSION) return [];
    if (!db_has_column('word_id')) return [];

    $ids = [];
    foreach (array_slice($parts, 0, WORD_PACK_MAX) as $seg) {
        // base_convert() silently treats out-of-alphabet characters as zero, so a
        // malformed segment would decode to id 0 rather than being rejected.
        if (!preg_match('/^[0-9a-z]{1,6}$/', $seg)) continue;
        $id = (int) base_convert($seg, 36, 10);
        if ($id > 0) $ids[] = $id;
    }
    if ($ids === []) return [];

    $by_id = [];
    foreach (array_chunk(array_unique($ids), 400) as $chunk) {
        $ph   = implode(',', array_fill(0, count($chunk), '?'));
        $stmt = db()->prepare("SELECT word_id, word FROM words WHERE word_id IN ($ph)");
        $stmt->execute($chunk);
        foreach ($stmt->fetchAll() as $r) { $by_id[(int) $r['word_id']] = $r['word']; }
    }

    $out = [];
    foreach ($ids as $id) {
        if (isset($by_id[$id])) $out[] = $by_id[$id];
    }
    return $out;
}

function build_word_filter(array $p): array {
    global $POS_OPTIONS;
    static $TIER_TOTAL    = 5;
    static $VERDICT_TOTAL = 4;
    $POS_TOTAL = count($POS_OPTIONS);

    $word_tier = trim($p['word_tier'] ?? 'forgotten');
    if (!in_array($word_tier, ['forgotten', 'rare_in_use'], true)) {
        $word_tier = 'forgotten';
    }

    $conditions = ['word_tier = ?'];
    $params     = [$word_tier];

    // Verdict multi-select checkboxes
    $verdict_values = parse_multi($p['verdict'] ?? null);
    if ($verdict_values !== [] && count($verdict_values) < $VERDICT_TOTAL) {
        $ph           = implode(',', array_fill(0, count($verdict_values), '?'));
        $conditions[] = "verdict IN ($ph)";
        $params       = array_merge($params, $verdict_values);
    }

    // Confidence tier checkboxes
    $tier_values = parse_multi($p['tier'] ?? null);
    if ($tier_values !== [] && count($tier_values) < $TIER_TOTAL) {
        $ph           = implode(',', array_fill(0, count($tier_values), '?'));
        $conditions[] = "confidence_tier IN ($ph)";
        $params       = array_merge($params, $tier_values);
    }

    // Taxonomy pipe-delimited single-value filters
    foreach ([
        ['dex_register',  trim($p['register']  ?? '')],
        ['dex_domain',    trim($p['domain']    ?? '')],
        ['dex_etymology', trim($p['etymology'] ?? '')],
    ] as [$col, $val]) {
        if ($val !== '') {
            $conditions[] = "('|'||{$col}||'|' LIKE ?)";
            $params[]     = '%|' . $val . '|%';
        }
    }

    // POS multi-select (OR across selected values)
    $pos_values = parse_multi($p['pos'] ?? null);
    if ($pos_values !== [] && count($pos_values) < $POS_TOTAL) {
        $or_parts     = array_fill(0, count($pos_values), "('|'||dex_pos||'|' LIKE ?)");
        $conditions[] = '(' . implode(' OR ', $or_parts) . ')';
        foreach ($pos_values as $pv) { $params[] = '%|' . $pv . '|%'; }
    }

    // Definition filter
    $has_def = trim($p['has_def'] ?? '');
    if ($has_def === '1') {
        $conditions[] = 'definition IS NOT NULL';
    } elseif ($has_def === '0') {
        $conditions[] = 'definition IS NULL';
    }

    // Minimum dictionaries
    $dict_min_int = (int)trim($p['dict_min'] ?? '');
    if ($dict_min_int > 0) {
        $conditions[] = 'dict_count >= ?';
        $params[]     = $dict_min_int;
    }

    // DEX frequency ceiling (only meaningful for rare_in_use tab)
    if ($word_tier === 'rare_in_use') {
        $dex_max = trim($p['dex_max'] ?? '');
        $ceiling = $dex_max === '' ? 0.60 : ($dex_max === 'all' ? null : (float)$dex_max);
        if ($ceiling !== null && $ceiling > 0) {
            $conditions[] = 'dex_frequency BETWEEN ? AND ?';
            $params[]     = 0.01;
            $params[]     = $ceiling;
        }
    }

    // ── Explore filters ────────────────────────────────────────────────────────

    // Zipf range (wordfreq Zipf scale 0–8)
    if (db_has_column('zipf_frequency')) {
        $zipf_min = isset($p['zipf_min']) && $p['zipf_min'] !== '' ? (float)$p['zipf_min'] : null;
        $zipf_max = isset($p['zipf_max']) && $p['zipf_max'] !== '' ? (float)$p['zipf_max'] : null;
        if ($zipf_min !== null) { $conditions[] = 'zipf_frequency >= ?'; $params[] = $zipf_min; }
        if ($zipf_max !== null) { $conditions[] = 'zipf_frequency <= ?'; $params[] = $zipf_max; }
    }

    // DEX frequency range (0–100 UI scale → 0–1 storage)
    $dexfreq_min = isset($p['dexfreq_min']) && $p['dexfreq_min'] !== '' ? (float)$p['dexfreq_min'] : null;
    $dexfreq_max = isset($p['dexfreq_max']) && $p['dexfreq_max'] !== '' ? (float)$p['dexfreq_max'] : null;
    if ($dexfreq_min !== null) { $conditions[] = 'dex_frequency >= ?'; $params[] = $dexfreq_min / 100.0; }
    if ($dexfreq_max !== null) { $conditions[] = 'dex_frequency <= ?'; $params[] = $dexfreq_max / 100.0; }

    // Hide loanwords (words common in English — en_zipf ≥ 4.0)
    if (db_has_column('en_zipf') && ($p['hide_loanwords'] ?? '') === '1') {
        $conditions[] = '(en_zipf IS NULL OR en_zipf < 4.0)';
    }

    // Hide proper nouns (proper_noun_like flag)
    if (db_has_column('proper_noun_like') && ($p['hide_proper'] ?? '') === '1') {
        $conditions[] = '(proper_noun_like IS NULL OR proper_noun_like = 0)';
    }

    return ['conditions' => $conditions, 'params' => $params, 'word_tier' => $word_tier];
}
