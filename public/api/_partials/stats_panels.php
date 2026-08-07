<?php
declare(strict_types=1);

// Reusable bar chart rendering
$render_bars = function(array $counts, string $fill_class, ?int $limit = null): void {
    if (empty($counts)) {
        echo '<p class="bar-empty">no data</p>';
        return;
    }
    $max = max($counts);
    $i = 0;
    foreach ($counts as $label => $cnt):
        if ($limit !== null && $i++ >= $limit) break;
        $pct = $max > 0 ? round($cnt / $max * 100, 1) : 0;
        $display = e(str_replace('limba ', '', (string)$label));
?>
  <div class="bar-row">
    <div class="bar-row-head">
      <span class="bar-label"><?= $display ?></span>
      <span class="bar-count"><?= number_format($cnt) ?></span>
    </div>
    <div class="bar-track">
      <div class="bar-fill <?= $fill_class ?>" style="width:<?= $pct ?>%"></div>
    </div>
  </div>
<?php
    endforeach;
};


// Empty state guard
if ($total === 0):
?>
<div class="stats-empty">No words match the selected filters.</div>
<?php return; endif; ?>

<!-- Summary strip -->
<?php $pct_def = (int)round($summary['with_def'] / $total * 100); ?>
<div class="stats-summary">
  <div class="stat-num">
    <span class="stat-n"><?= number_format($total) ?></span>
    <span class="stat-l">cuvinte</span>
  </div>
  <div class="stat-num">
    <span class="stat-n"><?= number_format((int)$summary['with_def']) ?></span>
    <span class="stat-l">cu definiție</span>
  </div>
  <div class="stat-num">
    <span class="stat-n"><?= $pct_def ?>%</span>
    <span class="stat-l">acoperire DEX</span>
  </div>
</div>

<!-- Panels grid -->
<div class="stats-panels">
  <!-- CARD 1: Etymology (full width, top 15) -->
  <div class="stat-card stat-card--wide">
    <div class="stat-card-head">
      <span class="stat-card-title">etimologie</span>
      <span class="stat-card-sub">top 15 limbi sursă</span>
    </div>
    <div class="bar-chart bar-chart--wide">
      <?php $render_bars($etym_top, 'bar-fill--etym'); ?>
    </div>
  </div>

  <!-- CARD 2: Tier -->
  <div class="stat-card">
    <div class="stat-card-head">
      <span class="stat-card-title">tier</span>
    </div>
    <div class="bar-chart">
<?php
$max_t = $tier_rows ? max(array_column($tier_rows, 'cnt')) : 1;
foreach ($tier_rows as $tr):
    $key  = $tr['confidence_tier'] ?? '';
    // Labels and bar colours both come from TIERS (api/_lib.php). An unmapped tier
    // keeps its bar — the count is real — but is labelled "neclasificat" rather than
    // leaking the raw enum onto the page.
    $meta = TIERS[$key] ?? ['label' => 'neclasificat', 'fill' => ''];
    $pct  = $max_t > 0 ? round($tr['cnt'] / $max_t * 100, 1) : 0;
?>
      <div class="bar-row">
        <div class="bar-row-head">
          <span class="bar-label"><?= e($meta['label']) ?></span>
          <span class="bar-count"><?= number_format((int)$tr['cnt']) ?></span>
        </div>
        <div class="bar-track">
          <div class="bar-fill <?= $meta['fill'] ?>" style="width:<?= $pct ?>%"></div>
        </div>
      </div>
<?php endforeach; ?>
    </div>
  </div>

  <!-- CARD 3: POS (part of speech) -->
  <div class="stat-card">
    <div class="stat-card-head">
      <span class="stat-card-title">parte de vorbire</span>
    </div>
    <div class="bar-chart">
      <?php $render_bars($pos_top, 'bar-fill--pos'); ?>
    </div>
  </div>

  <!-- CARD 4: Register (all values) -->
  <div class="stat-card">
    <div class="stat-card-head">
      <span class="stat-card-title">registru</span>
    </div>
    <div class="bar-chart">
      <?php $render_bars($reg_counts, 'bar-fill--reg'); ?>
    </div>
  </div>

  <!-- CARD 5: Domain (top 10) -->
  <div class="stat-card">
    <div class="stat-card-head">
      <span class="stat-card-title">domeniu</span>
      <span class="stat-card-sub">top 10</span>
    </div>
    <div class="bar-chart">
      <?php $render_bars($dom_top, 'bar-fill--dom'); ?>
    </div>
  </div>
</div>
