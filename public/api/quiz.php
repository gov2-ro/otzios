<?php
declare(strict_types=1);
require_once __DIR__ . '/_auth.php';

// One quiz question: a target word (+ definition) and 4 shuffled options, with
// distractors drawn from the same part of speech where possible. Serves three modes
// on joc.php, selected with ?mode=:
//   sense — show `word`, pick among four candidate definitions
//   quiz  — show `definition`, pick among four candidate words
//   flash — word + definition, no grading (hidden mode)
//
// Options are opaque {id, text} pairs and the response never names the target, so the
// answer cannot be read out of devtools. Grading happens in game.php against the
// `qid`, an encrypted token carrying the correct id. Earlier this endpoint returned `answer`
// outright and the browser graded itself — fine for a private toy, useless once
// scores are recorded and ranked.
//
// The mode matters to the payload: in `quiz` the target word IS the answer, so it
// must not appear at top level, and the definition is masked server-side.

// DEX definitions pack citations (quoted usage + "AUTHOR, WORK page.") and often
// several distinct senses into the same pipe-delimited `definition` column — see
// "bolovan", which has ~5 real senses interleaved with citations. `word` is masked
// only in the eventual full definition text, so what needs catching here is a
// definition that reuses the word's own stem (e.g. "mătura" -> "...cu mătura",
// "bolovan" -> "Bolovan de sare") — that makes a question trivial no matter which
// option it lands on, target or distractor.
function normalize_lite(string $s): string {
    return normalize_diacritics($s);
}

function common_prefix_len(string $a, string $b): int {
    $n = min(mb_strlen($a), mb_strlen($b));
    for ($i = 0; $i < $n; $i++) {
        if (mb_substr($a, $i, 1) !== mb_substr($b, $i, 1)) break;
    }
    return $i;
}

function reveals_word(string $word, string $segment): bool {
    $w = normalize_lite($word);
    // Too short for a stem match to mean anything — would false-positive constantly.
    if (mb_strlen($w) < 5) return false;
    $norm = normalize_lite($segment);
    foreach (preg_split('/[^\p{L}]+/u', $norm, -1, PREG_SPLIT_NO_EMPTY) as $tok) {
        if (mb_strlen($tok) < 4) continue;
        // A literal-prefix cut misses regular Romanian inflection, where the
        // stem's last vowel alternates (purcică -> purceaua, "purc" shared,
        // "ică"/"ea" diverge). Requiring the shared prefix to cover all but the
        // last ~3 characters of the shorter string catches that without needing
        // real stemming.
        $shared = common_prefix_len($w, $tok);
        if ($shared >= 4 && $shared >= min(mb_strlen($w), mb_strlen($tok)) - 3) return true;
    }
    return false;
}

function truncate_def(string $d): string {
    if (mb_strlen($d) <= 200) return $d;
    $cut = mb_substr($d, 0, 200);
    $sp  = mb_strrpos($cut, ' ');
    return rtrim($sp !== false ? mb_substr($cut, 0, $sp) : $cut, " ,;:") . '…';
}

// Picks one usable sense at random out of every pipe segment (not just the first) so
// the same word can surface a different, still-valid definition on a later question.
// A segment qualifies as a standalone sense when it's long enough, isn't a bare
// cross-reference or truncated header, isn't a citation (any run of 3+ uppercase
// letters is an author marker like EMINESCU or CREANGĂ), and doesn't give the word
// away. Returns null when the word has no usable sense at all.
function pick_sense(string $word, ?string $raw): ?string {
    $candidates = [];
    foreach (explode('|', (string) $raw) as $seg) {
        $seg = trim($seg);
        if (mb_strlen($seg) < 12) continue;
        if (str_starts_with(mb_strtolower($seg), 'vezi ')) continue;
        if (str_ends_with($seg, ':')) continue;
        if (preg_match('/^[A-Z][A-Z]/', $seg)) continue;    // unparsed dump header, e.g. "FLAIM U C sm."
        if (preg_match('/\p{Lu}{3,}/u', $seg)) continue;     // citation / author marker
        if (reveals_word($word, $seg)) continue;
        $candidates[] = truncate_def($seg);
    }
    if (!$candidates) return null;
    return $candidates[array_rand($candidates)];
}

require_method('GET');
$user = current_user();          // establish the device identity before the first answer

$mode = (string) ($_GET['mode'] ?? 'sense');
if (!in_array($mode, ['sense', 'quiz', 'flash'], true)) $mode = 'sense';

$pdo = db();
$BASE = "word_tier='forgotten' AND definition IS NOT NULL";
$base_params = [];

// A word tagged 'ascunde' or 'meh' (both mean "not interesting, too well known")
// by this player is excluded from their own pool — the same per-device annotation
// store that backs bookmarks/other quick-tags (see _appdb.php), just enforced here
// instead of staying purely informational.
if (attach_app_db()) {
    foreach (['tag:ascunde', 'tag:meh'] as $marks) {
        $sub = annotated_words_subquery($marks, (int) $user['id']);
        if ($sub !== null) {
            [$sub_sql, $sub_params] = $sub;
            $BASE          .= " AND word NOT IN ($sub_sql)";
            $base_params    = array_merge($base_params, $sub_params);
        }
    }
}

// Distractor definitions are displayed too, so hold them to the target's bar. This is
// a cheap SQL-level pre-filter on segment 1 only — pick_sense() re-checks every
// segment in PHP, so this just keeps the RANDOM() pool from being mostly junk.
$SEG = "trim(substr(definition, 1, coalesce(nullif(instr(definition,'|'), 0) - 1, length(definition))))";
$QUALITY = "(proper_noun_like IS NULL OR proper_noun_like = 0) AND dict_count >= 3
            AND length($SEG) >= 12
            AND lower($SEG) NOT LIKE 'vezi %'
            AND $SEG NOT LIKE '%:'
            AND $SEG NOT GLOB '[A-Z][A-Z]*'";

// pick_sense() rejects a real chunk of rows (self-revealing, citation-only, etc.), so
// candidate selection over-fetches and filters in PHP rather than trusting a single
// RANDOM() LIMIT row/set to already be usable. One retry at a larger limit before
// giving up.
$target = null;
foreach ([20, 40] as $limit) {
    $st = $pdo->prepare(
        "SELECT word, definition, dex_pos FROM words
         WHERE $BASE AND $QUALITY
         ORDER BY RANDOM() LIMIT ?"
    );
    $st->execute([...$base_params, $limit]);
    foreach ($st->fetchAll() as $row) {
        $sense = pick_sense($row['word'], $row['definition']);
        if ($sense !== null) { $target = ['word' => $row['word'], 'sense' => $sense, 'dex_pos' => $row['dex_pos']]; break 2; }
    }
}

if (!$target) {
    json_out(['error' => 'no words']);
}

$pos_first = trim(explode('|', $target['dex_pos'] ?? '')[0]);
$options   = [['word' => $target['word'], 'definition' => $target['sense']]];
$used_words = [$target['word']];

// Same part of speech first — same-POS distractors read more plausibly.
if ($pos_first !== '') {
    foreach ([20, 40] as $limit) {
        if (count($options) >= 4) break;
        $ph = implode(',', array_fill(0, count($used_words), '?'));
        $st = $pdo->prepare(
            "SELECT word, definition FROM words
             WHERE $BASE AND $QUALITY AND word NOT IN ($ph) AND ('|'||dex_pos||'|' LIKE ?)
             ORDER BY RANDOM() LIMIT ?"
        );
        $st->execute([...$base_params, ...$used_words, '%|' . $pos_first . '|%', $limit]);
        foreach ($st->fetchAll() as $row) {
            if (count($options) >= 4) break;
            $sense = pick_sense($row['word'], $row['definition']);
            if ($sense === null) continue;
            $options[]    = ['word' => $row['word'], 'definition' => $sense];
            $used_words[] = $row['word'];
        }
    }
}

// Fill from the general pool if same-POS distractors were scarce.
if (count($options) < 4) {
    foreach ([20, 40] as $limit) {
        if (count($options) >= 4) break;
        $ph = implode(',', array_fill(0, count($used_words), '?'));
        $st = $pdo->prepare(
            "SELECT word, definition FROM words
             WHERE $BASE AND $QUALITY AND word NOT IN ($ph)
             ORDER BY RANDOM() LIMIT ?"
        );
        $st->execute([...$base_params, ...$used_words, $limit]);
        foreach ($st->fetchAll() as $row) {
            if (count($options) >= 4) break;
            $sense = pick_sense($row['word'], $row['definition']);
            if ($sense === null) continue;
            $options[]    = ['word' => $row['word'], 'definition' => $sense];
            $used_words[] = $row['word'];
        }
    }
}

shuffle($options);

$word     = $target['word'];
$full_def = $target['sense'];

// Flash cards aren't graded and show both sides, so there is nothing to protect.
if ($mode === 'flash') {
    json_out([
        'mode'       => 'flash',
        'word'       => $word,
        'definition' => $full_def,
        'pos'        => $pos_first,
    ]);
}

$correct_id = 0;
$out        = [];
foreach ($options as $i => $o) {
    if ($o['word'] === $word) $correct_id = $i;
    // sense: the four candidate meanings. quiz: the four candidate words.
    $out[] = [
        'id'   => $i,
        'text' => $mode === 'sense' ? mask_word($o['definition'], $word) : $o['word'],
    ];
}

$payload = [
    'n' => bin2hex(random_bytes(12)),   // single-use nonce, burned by game.php
    'a' => $correct_id,
    'w' => $word,
    'm' => $mode,
    't' => time(),
];

json_out([
    'mode'    => $mode,
    'qid'     => seal_token($payload),
    'pos'     => $pos_first,
    'options' => $out,
    // Only ever send the half of the pair that isn't the answer.
    'word'       => $mode === 'sense' ? $word : null,
    'definition' => $mode === 'quiz'  ? mask_word($full_def, $word) : null,
]);
