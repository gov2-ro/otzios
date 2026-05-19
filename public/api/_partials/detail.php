<?php
// $w = array with word row data
$verdict      = $w['verdict'] ?? 'unknown';
$verdict_cls  = str_replace(' ', '_', $verdict);
$pos_parts    = array_filter(array_map('trim', explode('|', $w['dex_pos'] ?? '')));
$reg_parts    = array_filter(array_map('trim', explode('|', $w['dex_register'] ?? '')));
$dom_parts    = array_filter(array_map('trim', explode('|', $w['dex_domain'] ?? '')));
$etym_parts   = array_filter(array_map('trim', explode('|', $w['dex_etymology'] ?? '')));
$etym_parts   = array_map(fn($e) => str_replace('limba ', '', $e), $etym_parts);
?>
<button class="fp-close" onclick="closePanel()">✕</button>

<div class="fp-word">
  <div class="fp-title">
    <h2><?= e($w['word']) ?></h2>
    <span class="verdict-badge vb-<?= e($verdict_cls) ?>" style="font-size:9px;padding:1px 6px;flex-shrink:0;"><?= e($verdict) ?></span>
  </div>
  <div class="fp-chips">
    <?php if ($pos_parts): ?><span class="detail-tag"><?= e($pos_parts[0]) ?></span><?php endif; ?>
    <?php foreach ($reg_parts as $r): ?><span class="detail-tag"><?= e($r) ?></span><?php endforeach; ?>
    <?php foreach ($dom_parts as $d): ?><span class="detail-tag" style="opacity:.8;"><?= e($d) ?></span><?php endforeach; ?>
    <?php foreach ($etym_parts as $et): ?><span class="detail-tag" style="opacity:.7;"><?= e($et) ?></span><?php endforeach; ?>
    <?php if ($w['confidence_tier']): ?><span class="detail-tag" style="opacity:.55;font-size:9px;"><?= e($w['confidence_tier']) ?></span><?php endif; ?>
  </div>
</div>

<div class="fp-right">
  <div class="fp-def">
    <?php if ($w['definition']): ?>
    <div class="definition-text"><?= e($w['definition']) ?></div>
    <?php else: ?>
    <span style="color:var(--text-3);font-family:var(--serif);font-style:italic;font-size:11px;">no definition</span>
    <?php endif; ?>
    <a class="dex-link" style="font-size:10px;margin-top:3px;"
       href="https://dexonline.ro/definitie/<?= urlenc($w['word']) ?>"
       target="_blank" rel="noopener">↗ dexonline.ro</a>
  </div>

  <div class="fp-actions">
    <div class="fp-stats">
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
        </div>
        <input id="tag-input" type="text" name="tag" placeholder="add tag…"
               list="tag-suggestions" autocomplete="off">
      </div>
    </div>
    <div class="fp-note">
      <textarea id="note-input" data-word="<?= e($w['word']) ?>" placeholder="note…"></textarea>
      <div id="note-status" style="display:none;"></div>
    </div>
  </div>
</div>
