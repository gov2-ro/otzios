<?php
// $w = array with word row data
$verdict = str_replace(' ', '_', $w['verdict'] ?? 'unknown');
$classes = 'word-row verdict-' . $verdict;
if (mb_strlen($w['word']) >= 11) $classes .= ' word-wide';
if (str_contains($w['dex_register'] ?? '', 'învechit')) $classes .= ' inv';

$pos = explode('|', $w['dex_pos'] ?? '')[0];
$reg = explode('|', $w['dex_register'] ?? '')[0];
// hist_occ, not dex_frequency: the DEX score barely discriminates where people look
// (91% of the default view sits at 0.8-1.0) and reads backwards without a caveat.
// hist_occ is the signal make_shortlist.score leans on hardest and has real spread.
$hist_occ = ((int)($w['hist_occ'] ?? 0)) ?: null;
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
// `editor_pick` may be absent on a ui.db built before the column existed; empty() covers
// both that and the 0 case. It goes in the accessible name because the ★ chip below is
// aria-hidden like every other chip, and unlike them it is not restating a visible number.
$is_pick   = !empty($w['editor_pick']);
$row_label = $w['word'] . ($verdict_lbl ? ', ' . $verdict_lbl : '') . ($is_pick ? ', ales' : '');
?>
<a class="<?= e($classes) ?>"
   href="<?= BASE ?>/?word=<?= urlenc($w['word']) ?>"
   role="option"
   aria-selected="false"
   aria-label="<?= e($row_label) ?>"
   tabindex="-1"
   data-word="<?= e($w['word']) ?>"
   data-verdict="<?= e($w['verdict'] ?? 'unknown') ?>"
   data-vlabel="<?= e($verdict_lbl) ?>"
   data-pos="<?= e($pos) ?>"
   data-hist="<?= $hist_occ !== null ? $hist_occ : '' ?>"
   data-def="<?= e($def_preview) ?>"
   <?= $inv_title ?>
   hx-get="<?= BASE ?>/api/word.php?word=<?= urlenc($w['word']) ?>"
   hx-target="#detail-panel"
   hx-swap="innerHTML">
  <span class="verdict-dot" aria-hidden="true"></span>
  <span class="word-text"><?= e($w['word']) ?></span>
  <?php if ($is_pick): ?><span class="chip-pick" aria-hidden="true" title="Ales — pus deoparte pentru că merită">★</span><?php endif; ?>
  <?php if ($hist_occ !== null): ?><span class="chip-hist" aria-hidden="true" title="Atestări istorice: <?= $hist_occ ?> — de câte ori apare cuvântul, pe toată paradigma lui, în corpusul istoric"><?= $hist_occ ?></span><?php endif; ?>
  <?php if ($meta_str): ?><span class="chip-meta" aria-hidden="true"><?= e($meta_str) ?></span><?php endif; ?>
  <span class="chip-vbadge" aria-hidden="true" title="<?= e($verdict_lbl) ?>"><?= e($verdict_abbr) ?></span>
  <?php if ($dict_count > 0): ?><span class="chip-dict" aria-hidden="true">📚<?= $dict_count ?></span><?php endif; ?>
</a>
