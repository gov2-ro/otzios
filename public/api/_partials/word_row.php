<?php
// $w = array with word row data
$verdict = str_replace(' ', '_', $w['verdict'] ?? 'unknown');
$classes = 'word-row verdict-' . $verdict;
if (mb_strlen($w['word']) >= 11) $classes .= ' word-wide';
if (str_contains($w['dex_register'] ?? '', 'învechit')) $classes .= ' inv';

$pos = explode('|', $w['dex_pos'] ?? '')[0];
$reg = explode('|', $w['dex_register'] ?? '')[0];
$freq = $w['dex_frequency'] !== null ? (int)round((float)$w['dex_frequency'] * 100) : null;
$def_preview = mb_substr($w['definition'] ?? '', 0, 120);
$inv_title = str_contains($w['dex_register'] ?? '', 'învechit') ? ' title="învechit"' : '';

$dict_count = count(split_pipe($w['sources'] ?? ''));

$verdict_abbr = match($w['verdict'] ?? '') {
    'extinct'         => 'EXT',
    'declining'       => 'DEC',
    'historical_only' => 'IST',
    'absent'          => 'ABS',
    default           => '?',
};

// Table mode meta: "pos · reg" or just pos or just reg
$meta_parts = array_filter([$pos, $reg]);
$meta_str = implode(' · ', $meta_parts);
?>
<div class="<?= e($classes) ?>"
     data-word="<?= e($w['word']) ?>"
     data-verdict="<?= e($w['verdict'] ?? 'unknown') ?>"
     data-pos="<?= e($pos) ?>"
     data-freq="<?= $freq !== null ? $freq : '' ?>"
     data-def="<?= e($def_preview) ?>"
     <?= $inv_title ?>
     hx-get="<?= BASE ?>/api/word.php?word=<?= urlenc($w['word']) ?>"
     hx-target="#detail-panel"
     hx-swap="innerHTML">
  <span class="verdict-dot"></span>
  <span class="word-text"><?= e($w['word']) ?></span>
  <?php if ($freq !== null): ?><span class="chip-freq" title="Frecvență DEX: <?= $freq ?>/100 — cu cât e mai mic, cu atât cuvântul e mai rar"><?= $freq ?></span><?php endif; ?>
  <?php if ($meta_str): ?><span class="chip-meta"><?= e($meta_str) ?></span><?php endif; ?>
  <span class="chip-vbadge"><?= $verdict_abbr ?></span>
  <?php if ($dict_count > 0): ?><span class="chip-dict">📚<?= $dict_count ?></span><?php endif; ?>
</div>
