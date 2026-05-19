<?php
// $w = array with word row data
$verdict = str_replace(' ', '_', $w['verdict'] ?? 'unknown');
$classes = 'word-row verdict-' . $verdict;
if (mb_strlen($w['word']) >= 11) $classes .= ' word-wide';
if (str_contains($w['dex_register'] ?? '', 'învechit')) $classes .= ' inv';
$pos = explode('|', $w['dex_pos'] ?? '')[0];
$freq = $w['dex_frequency'] !== null ? (int)round((float)$w['dex_frequency'] * 100) : null;
$def_preview = mb_substr($w['definition'] ?? '', 0, 120);
$inv_title = str_contains($w['dex_register'] ?? '', 'învechit') ? ' title="învechit"' : '';
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
  <span class="word-text"><?= e($w['word']) ?></span>
  <?php if ($freq !== null): ?><span class="chip-freq"><?= $freq ?></span><?php endif; ?>
</div>
