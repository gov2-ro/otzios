<?php
/**
 * $q             string        the raw query
 * $resolved      ['word' => row|null, 'suggestions' => rows]   from syn_resolve()
 * $neighborhood  array|null    from syn_neighborhood(), only set when $resolved['word']
 *
 * Four states, ui.md: landing (q===''), not-found (word===null, q!==''), found-but-empty
 * ("the empty state is a first-class screen" -- 27.6%+ of 1k+ lookups per findings.md §4),
 * and the graph+list. The htmx endpoint (api/syn.php) and the page (sinonime.php) both
 * render through this one partial, which is what makes the initial page load and every
 * subsequent search/recenter produce byte-identical markup for the same $q.
 */
?>
<?php if ($q === ''): ?>
  <?php include __DIR__ . '/syn_landing.php'; ?>

<?php elseif ($resolved['word'] === null): ?>
  <div class="syn-empty">
    <p class="syn-empty-msg">Niciun rezultat pentru <strong><?= e($q) ?></strong>.</p>
    <?php if ($resolved['suggestions']): ?>
    <p class="syn-empty-sub">Poate ai vrut:</p>
    <ul class="syn-suggest-list">
      <?php foreach ($resolved['suggestions'] as $s): ?>
      <li><a href="<?= BASE ?>/sinonime?q=<?= urlenc($s['form']) ?>"><?= e($s['form']) ?></a></li>
      <?php endforeach; ?>
    </ul>
    <?php else: ?>
    <p class="syn-empty-sub">
      <a class="syn-dex-link" href="https://dexonline.ro/definitie/<?= urlenc($q) ?>"
         target="_blank" rel="noopener">caută pe dexonline.ro ↗</a>
    </p>
    <?php endif; ?>
  </div>

<?php elseif (empty($neighborhood['senses'])): ?>
  <?php
    $w  = $resolved['word'];
    $pl = syn_pos_label($w['pos']);
  ?>
  <div class="syn-empty syn-empty--found">
    <div class="syn-empty-head">
      <span class="syn-empty-word"><?= e($w['form']) ?></span>
      <?php if ($pl): ?><span class="syn-empty-pos"><?= e($pl) ?></span><?php endif; ?>
      <?= syn_band_meter((int) $w['band']) ?>
    </div>
    <p class="syn-empty-msg">Sursele noastre nu au niciun sinonim pentru acest cuvânt.</p>
    <a class="syn-dex-link" href="https://dexonline.ro/definitie/<?= urlenc($w['form']) ?>"
       target="_blank" rel="noopener">caută pe dexonline.ro ↗</a>
  </div>

<?php else: ?>
  <?php $multi = count($neighborhood['senses']) > 1; ?>
  <div class="syn-layout">
    <details class="syn-graph-details" open>
      <summary class="syn-graph-summary">graful cuvântului ▾</summary>
      <div class="syn-graph-wrap">
        <?= syn_svg($neighborhood, syn_layout($neighborhood)) ?>
      </div>
    </details>
    <div class="syn-list-wrap">
      <ol class="syn-list<?= $multi ? ' syn-list--grouped' : '' ?>">
        <?php foreach ($neighborhood['senses'] as $s): ?>
          <?php if ($multi): ?>
          <li class="syn-sense-heading" role="presentation"><?= e($s['label'] ?? 'alt sens') ?></li>
          <?php endif; ?>
          <?php foreach ($s['members'] as $m): $pl = syn_pos_label($m['pos']); ?>
          <li class="syn-row" data-word="<?= e($m['form']) ?>">
            <a class="syn-row-word" href="<?= BASE ?>/sinonime?q=<?= urlenc($m['form']) ?>"><?= e($m['form']) ?></a>
            <?= syn_band_meter($m['band']) ?>
            <?php if ($pl): ?><span class="syn-row-pos"><?= e($pl) ?></span><?php endif; ?>
            <?php foreach (syn_reg_labels($s['reg']) as $rl): ?><span class="syn-reg-tag"><?= e($rl) ?></span><?php endforeach; ?>
            <button type="button" class="syn-copy-btn" data-word="<?= e($m['form']) ?>"
                    title="copiază <?= e($m['form']) ?>" aria-label="copiază <?= e($m['form']) ?>">⧉</button>
          </li>
          <?php endforeach; ?>
        <?php endforeach; ?>
      </ol>
    </div>
  </div>
  <script type="application/json" id="syn-data"><?= json_encode([
      'center'  => $neighborhood['center']['form'],
      'senses'  => array_map(fn($s) => [
          'label'   => $s['label'],
          'members' => array_map(fn($m) => [
              'form' => $m['form'], 'band' => $m['band'],
              'ring2' => array_map(fn($c) => ['form' => $c['form'], 'band' => $c['band']], $m['ring2']),
          ], $s['members']),
      ], $neighborhood['senses']),
  ], JSON_UNESCAPED_UNICODE) ?></script>
<?php endif; ?>
