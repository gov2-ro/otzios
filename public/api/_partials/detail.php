<?php
// $w = array with word row data
$verdict      = $w['verdict'] ?? 'unknown';
$verdict_cls  = str_replace(' ', '_', $verdict);
$pos_parts    = array_filter(array_map('trim', explode('|', $w['dex_pos'] ?? '')));
$reg_parts    = array_filter(array_map('trim', explode('|', $w['dex_register'] ?? '')));
$dom_parts    = array_filter(array_map('trim', explode('|', $w['dex_domain'] ?? '')));
$etym_parts   = array_filter(array_map('trim', explode('|', $w['dex_etymology'] ?? '')));
$etym_parts   = array_map(fn($e) => str_replace('limba ', '', $e), $etym_parts);

$sources = split_pipe($w['sources'] ?? '');
$dict_count = count($sources);

$meta_parts = array_filter([
    $pos_parts   ? e($pos_parts[0])   : null,
    $reg_parts   ? e($reg_parts[0])   : null,
    $etym_parts  ? e($etym_parts[0])  : null,
]);
?>
<button class="fp-close" onclick="closePanel()">✕</button>

<!-- Head: word + verdict + meta -->
<div class="fp-head">
  <div class="fp-title"><?= e($w['word']) ?></div>
  <div class="fp-subtitle">
    <span class="verdict-badge vb-<?= e($verdict_cls) ?>"><?= e($verdict) ?></span>
    <?php if ($meta_parts): ?>
    <span class="fp-pos-line"><?= implode(' · ', $meta_parts) ?></span>
    <?php endif; ?>
  </div>
</div>

<!-- Scrollable body -->
<div class="fp-body">

  <?php if ($w['definition']): ?>
  <div class="definition-text"><?= e($w['definition']) ?></div>
  <?php else: ?>
  <span class="fp-nodef">fără definiție locală</span>
  <?php endif; ?>

  <!-- Tag chips -->
  <?php $all_tags = array_merge(
      array_slice($pos_parts, 1),
      $reg_parts,
      $dom_parts,
      $etym_parts
  ); ?>
  <?php if ($all_tags || $w['confidence_tier']): ?>
  <div class="fp-chips">
    <?php if (count($pos_parts) > 1): ?>
      <?php foreach (array_slice($pos_parts, 1) as $p): ?><span class="detail-tag"><?= e($p) ?></span><?php endforeach; ?>
    <?php endif; ?>
    <?php foreach ($reg_parts as $r): ?><span class="detail-tag"><?= e($r) ?></span><?php endforeach; ?>
    <?php foreach ($dom_parts as $d): ?><span class="detail-tag" style="opacity:.85"><?= e($d) ?></span><?php endforeach; ?>
    <?php foreach ($etym_parts as $et): ?><span class="detail-tag" style="opacity:.7"><?= e($et) ?></span><?php endforeach; ?>
    <?php if ($w['confidence_tier']): ?><span class="detail-tag" style="opacity:.5;font-size:0.5625rem;"><?= e($w['confidence_tier']) ?></span><?php endif; ?>
  </div>
  <?php endif; ?>

  <!-- Dictionaries -->
  <?php if ($sources): ?>
  <div class="fp-dicts">
    <span class="fp-extra-label">📚 în <?= $dict_count ?> <?= $dict_count === 1 ? 'dicționar' : 'dicționare' ?></span>
    <?php foreach ($sources as $src): ?><span class="dict-chip"><?= e($src) ?></span><?php endforeach; ?>
  </div>
  <?php endif; ?>

  <!-- Sinonime placeholder -->
  <div style="margin-top:2px;">
    <span class="fp-extra-label">sinonime</span>
    <span class="fp-syns-placeholder">în curând</span>
  </div>

</div>

<!-- Footer: stats + actions + dexonline -->
<div class="fp-foot">

  <div class="fp-stats">
    <?php if ($w['zipf_frequency'] !== null): ?><span title="Zipf română — sub 3.0 = uitat"><em>zipf</em><?= number_format((float)$w['zipf_frequency'], 1) ?></span><?php endif; ?>
    <?php if ($w['en_zipf'] !== null): ?><span title="Zipf engleză — mare = posibil împrumut"><em>en</em><?= number_format((float)$w['en_zipf'], 1) ?></span><?php endif; ?>
    <span><em>hist</em><?= $w['hist_ppm'] !== null ? number_format((float)$w['hist_ppm'], 2) : '—' ?></span>
    <span><em>mod</em><?= $w['modern_ppm'] !== null ? number_format((float)$w['modern_ppm'], 2) : '—' ?></span>
    <span><em>ratio</em><?= $w['log_ratio'] !== null ? number_format((float)$w['log_ratio'], 2) : '—' ?></span>
  </div>

  <div class="fp-btns">
    <button id="bookmark-btn" data-word="<?= e($w['word']) ?>">☆</button>
    <div id="tags-row" data-word="<?= e($w['word']) ?>">
      <div class="quick-tags">
        <button type="button" class="qt-btn" data-qtkey="i" title="ignore (i)"><span class="qt-key">i</span>ignore</button>
        <button type="button" class="qt-btn" data-qtkey="B" title="boring (B)"><span class="qt-key">B</span>boring</button>
        <button type="button" class="qt-btn" data-qtkey="f" title="funny (f)"><span class="qt-key">f</span>funny</button>
        <button type="button" class="qt-btn" data-qtkey="x" title="remove (x)"><span class="qt-key">x</span>remove</button>
        <button type="button" class="qt-btn" data-qtkey="s" title="simple (s) — too simple, not worth quizzing"><span class="qt-key">s</span>simple</button>
      </div>
      <input id="tag-input" type="text" name="tag" placeholder="add tag…"
             list="tag-suggestions" autocomplete="off">
    </div>
  </div>

  <div class="fp-note">
    <textarea id="note-input" data-word="<?= e($w['word']) ?>" placeholder="note…"></textarea>
    <div id="note-status" style="display:none;"></div>
  </div>

  <a class="dex-link"
     href="https://dexonline.ro/definitie/<?= urlenc($w['word']) ?>"
     target="_blank" rel="noopener">↗ deschide pe dexonline.ro</a>

</div>
