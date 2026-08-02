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

// DEX definitions append citations after pipes; keep the first segment only and
// cap the length so all four options read at a comparable size.
function clean_def(?string $def): string {
    $d = trim(explode('|', (string) $def)[0]);
    if (mb_strlen($d) <= 200) return $d;
    $cut = mb_substr($d, 0, 200);
    $sp  = mb_strrpos($cut, ' ');
    return rtrim($sp !== false ? mb_substr($cut, 0, $sp) : $cut, " ,;:") . '…';
}

require_method('GET');
current_user();          // establish the device identity before the first answer

$mode = (string) ($_GET['mode'] ?? 'sense');
if (!in_array($mode, ['sense', 'quiz', 'flash'], true)) $mode = 'sense';

$pdo = db();
$BASE = "word_tier='forgotten' AND definition IS NOT NULL";
// Distractor definitions are displayed too, so hold them to the target's bar.
// The last four drop definitions that can't stand alone as a quiz option: bare
// cross-references ("vezi jeț"), truncated headers ("Compus:") and unparsed DEX
// entries, which start with the headword in caps ("FLAIM U C sm. Tont…").
// All four test the same first segment clean_def() keeps, not the raw column.
$SEG = "trim(substr(definition, 1, coalesce(nullif(instr(definition,'|'), 0) - 1, length(definition))))";
$QUALITY = "(proper_noun_like IS NULL OR proper_noun_like = 0) AND dict_count >= 3
            AND length($SEG) >= 12
            AND lower($SEG) NOT LIKE 'vezi %'
            AND $SEG NOT LIKE '%:'
            AND $SEG NOT GLOB '[A-Z][A-Z]*'";

$target = $pdo->query(
    "SELECT word, definition, dex_pos FROM words
     WHERE $BASE AND $QUALITY
     ORDER BY RANDOM() LIMIT 1"
)->fetch();

if (!$target) {
    json_out(['error' => 'no words']);
}

$pos_first = trim(explode('|', $target['dex_pos'] ?? '')[0]);
$options   = [['word' => $target['word'], 'definition' => clean_def($target['definition'])]];

if ($pos_first !== '') {
    $st = $pdo->prepare(
        "SELECT word, definition FROM words
         WHERE $BASE AND $QUALITY AND word != ? AND ('|'||dex_pos||'|' LIKE ?)
         ORDER BY RANDOM() LIMIT 3"
    );
    $st->execute([$target['word'], '%|' . $pos_first . '|%']);
    foreach ($st->fetchAll() as $row) {
        $def = clean_def($row['definition']);
        if ($def !== '') { $options[] = ['word' => $row['word'], 'definition' => $def]; }
    }
}

// Fill from the general pool if same-POS distractors were scarce or cleaned away
if (count($options) < 4) {
    $words = array_column($options, 'word');
    $ph    = implode(',', array_fill(0, count($words), '?'));
    $need  = 4 - count($options);
    $st = $pdo->prepare(
        "SELECT word, definition FROM words
         WHERE $BASE AND $QUALITY AND word NOT IN ($ph)
         ORDER BY RANDOM() LIMIT ?"
    );
    // Over-fetch: some rows clean down to an empty definition
    $st->execute(array_merge($words, [$need * 3]));
    foreach ($st->fetchAll() as $row) {
        if (count($options) >= 4) break;
        $def = clean_def($row['definition']);
        if ($def !== '') { $options[] = ['word' => $row['word'], 'definition' => $def]; }
    }
}

shuffle($options);

$word     = $target['word'];
$full_def = clean_def($target['definition']);

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
