<?php
/**
 * Shared page header — brand, a slot for page-specific controls, and the three
 * display preferences (text scale, skin, theme).
 *
 * Before this existed each of the five pages drew its own bar: `index.php` had
 * `.brand-bar`, `joc.php` had `.joc-head`, `lista`/`liste` had `.lista-nav`, and
 * `stats.php` had **nothing at all** — you landed on a bare filter strip with no
 * indication you were still in Oțios. The three preference toggles were pasted
 * into all five, so adding a fourth meant editing five files.
 *
 * **Navigation is deliberately not here — it is in `footer.php`.** `index.php`
 * already put it in the bottom status bar, that bar is the right size for it, and
 * the top bar on the explorer is already carrying brand + search + count + play +
 * view + scale + skin + theme + filters. Five more links is the one thing it
 * cannot take. Identity goes at the top, travel goes at the bottom, on every page.
 *
 * Set before requiring (all optional):
 *
 *   $brand_tag     string  Tagline beside the wordmark. Defaults to the site's.
 *   $header_center string  HTML between brand and the right cluster — the
 *                          explorer's search box. Rendered raw; escape at source.
 *   $header_tools  string  HTML at the head of the right cluster, before the
 *                          preferences: the explorer's count/play/view, joc's
 *                          mode buttons and score.
 *   $header_after  string  HTML after the preferences, i.e. last in the bar —
 *                          the explorer's filter button, which has to stay put.
 *
 * Slots are strings rather than callbacks so a caller can build one with
 * `ob_start()` and keep writing ordinary markup.
 */

$brand_tag     = $brand_tag     ?? 'cuvinte uitate';
$header_center = $header_center ?? '';
$header_tools  = $header_tools  ?? '';
$header_after  = $header_after  ?? '';
?>
<header class="brand-bar">
  <a class="brand-id" href="<?= BASE ?>/" title="Oțios — cuvinte uitate">
    <span class="brand-name">otios</span>
    <span class="brand-sep"></span>
    <span class="brand-tag"><?= e($brand_tag) ?></span>
  </a>

  <?= $header_center ?>

  <div class="brand-right">
    <?= $header_tools ?>

    <!-- Font-size stepper. An addition to browser zoom, not a replacement:
         pinch-zoom is deliberately left unblocked (WCAG 1.4.4). -->
    <div class="scale-stepper scale-stepper--sm" role="group" aria-label="Mărime text">
      <button type="button" class="scale-btn" data-scale-btn="down" onclick="stepTextScale(-1)"
              title="Text mai mic" aria-label="Text mai mic">A−</button>
      <button type="button" class="scale-btn" data-scale-btn="up" onclick="stepTextScale(1)"
              title="Text mai mare" aria-label="Text mai mare">A+</button>
    </div>

    <!-- Options discovered from assets/skins/*.css — no registry to update. -->
    <?= otios_skin_select('skin-select--sm') ?>

    <div class="theme-toggle theme-toggle--sm" role="group" aria-label="Temă">
      <button type="button" class="tg-btn" data-theme-btn="light" onclick="setTheme('light')"
              title="Temă deschisă" aria-label="Temă deschisă">☀</button>
      <button type="button" class="tg-btn" data-theme-btn="dark" onclick="setTheme('dark')"
              title="Temă întunecată" aria-label="Temă întunecată">☾</button>
    </div>

    <?= $header_after ?>
  </div>
</header>
