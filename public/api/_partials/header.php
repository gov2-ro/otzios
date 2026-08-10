<?php
/**
 * Shared page header — brand, primary nav, and a slot for page-specific controls.
 *
 * Before this existed each of the five pages drew its own bar: `index.php` had
 * `.brand-bar`, `joc.php` had `.joc-head`, `lista`/`liste` had `.lista-nav`, and
 * `stats.php` had **nothing at all** — you landed on a bare filter strip with no
 * indication you were still in Oțios.
 *
 * **`joc` and `liste` live here; `statistici`, `metodologie` and the toggles are
 * in `footer.php`.** The two destinations people jump to mid-browse (play the
 * game, check a list) are one click from the brand, always visible; the rest of
 * travel plus text-scale/skin/theme are the bottom bar's job — see `footer.php`
 * for why that split exists at all.
 *
 * Set before requiring (all optional):
 *
 *   $page              string  Key of the current page, from NAV_ITEMS in
 *                              `_lib.php`. Marks the matching top-nav entry
 *                              `aria-current="page"` and unlinks it.
 *   $brand_tag         string  Tagline beside the wordmark. Defaults to the
 *                              site's.
 *   $header_nav_extra  string  HTML appended inside the top-nav, after joc/liste
 *                              — the explorer's `?` shortcuts/legend link, which
 *                              only exists on `index.php`.
 *   $header_center     string  HTML between the nav and the right cluster — the
 *                              explorer's search box. Rendered raw; escape at
 *                              source.
 *   $header_tools      string  HTML at the head of the right cluster, before
 *                              $header_after: the explorer's count, joc's mode
 *                              buttons and score.
 *   $header_after      string  HTML after $header_tools, i.e. last in the bar —
 *                              the explorer's filter button, which has to stay
 *                              put.
 *
 * Slots are strings rather than callbacks so a caller can build one with
 * `ob_start()` and keep writing ordinary markup.
 */

$page              = $page              ?? '';
$brand_tag         = $brand_tag         ?? 'voroave neglijate';
$header_nav_extra  = $header_nav_extra  ?? '';
$header_center     = $header_center     ?? '';
$header_tools      = $header_tools      ?? '';
$header_after      = $header_after      ?? '';
?>
<header class="brand-bar">
  <a class="brand-id" href="<?= BASE ?>/" title="Oțios — cuvinte negljate">
    <span class="brand-name">oțios</span>
    <span class="brand-sep"></span>
    <span class="brand-tag"><?= e($brand_tag) ?></span>
  </a>

  <nav class="top-nav" aria-label="Navigare principală">
    <?php
    /*
     * `joc` and `liste` are here at every width. `stats` and `metod` are here
     * only from 901px up, and in `footer.php` only below it — the same two
     * destinations, one bar at a time, with the crossover at the width the
     * footer nav already uses to drop its labels. Marked with
     * `top-nav-item--wide` / `nav-item--wide`; app.css owns the swap, so there
     * is no width where they render twice or not at all.
     *
     * The bar cannot take four labelled entries on a phone — that is the
     * measurement the header/footer split was built on and it has not changed.
     * What changed is the ask: on a desktop the bar has the room, and burying
     * statistici and metodologie in the footer was hiding the two pages that
     * explain what the site is.
     */
    foreach (['joc' => '', 'liste' => '', 'stats' => ' top-nav-item--wide', 'metod' => ' top-nav-item--wide'] as $key => $width_cls):
      $item = NAV_ITEMS[$key]; ?>
      <a style="text-transform: uppercase;" class="top-nav-item<?= $width_cls ?><?= $key === $page ? ' is-current' : '' ?>"
         href="<?= BASE . $item['path'] ?>" title="<?= e($item['label']) ?>"
         <?= $key === $page ? 'aria-current="page"' : '' ?>>
        <span class="nav-icon" aria-hidden="true"><?= $item['icon'] ?></span><span class="nav-label"><?= e($item['label']) ?></span>
      </a>
    <?php endforeach; ?>
  </nav>

  <?= $header_center ?>
  <div class="brand-right">
  <?= $header_nav_extra ?>  
  <?= $header_tools ?>
    <?= $header_after ?>
  </div>
</header>
