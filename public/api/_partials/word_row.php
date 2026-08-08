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

$verdict_raw  = $w['verdict'] ?? '';
$verdict_abbr = verdict_abbr($verdict_raw);
$verdict_lbl  = verdict_label($verdict_raw);

// Table mode meta: "pos · reg" or just pos or just reg
$meta_parts = array_filter([$pos, $reg]);
$meta_str = implode(' · ', $meta_parts);
?>
<?php
// Accessible name: the row's visible text is the headword plus a pile of unlabelled
// numbers and abbreviations (`89`, `s.f.`, `EXT`, `📚12`), which a screen reader would
// read out as exactly that. Naming the row explicitly keeps the announcement to the
// word and its verdict; the chips are hidden from the tree individually below.
$row_label = $w['word'] . ($verdict_lbl ? ', ' . $verdict_lbl : '');
?>
<div class="<?= e($classes) ?>"
     role="option"
     aria-selected="false"
     aria-label="<?= e($row_label) ?>"
     tabindex="-1"
     data-word="<?= e($w['word']) ?>"
     data-verdict="<?= e($w['verdict'] ?? 'unknown') ?>"
     data-vlabel="<?= e($verdict_lbl) ?>"
     data-pos="<?= e($pos) ?>"
     data-freq="<?= $freq !== null ? $freq : '' ?>"
     data-def="<?= e($def_preview) ?>"
     <?= $inv_title ?>
     hx-get="<?= BASE ?>/api/word.php?word=<?= urlenc($w['word']) ?>"
     hx-target="#detail-panel"
     hx-swap="innerHTML">
  <span class="verdict-dot" aria-hidden="true"></span>
  <span class="word-text"><?= e($w['word']) ?></span>
  <?php if ($freq !== null): ?><span class="chip-freq" aria-hidden="true" title="Frecvență DEX: <?= $freq ?>/100 — cu cât e mai mic, cu atât cuvântul e mai rar"><?= $freq ?></span><?php endif; ?>
  <?php if ($meta_str): ?><span class="chip-meta" aria-hidden="true"><?= e($meta_str) ?></span><?php endif; ?>
  <span class="chip-vbadge" aria-hidden="true" title="<?= e($verdict_lbl) ?>"><?= e($verdict_abbr) ?></span>
  <?php if ($dict_count > 0): ?><span class="chip-dict" aria-hidden="true">📚<?= $dict_count ?></span><?php endif; ?>
</div>
