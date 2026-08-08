<?php
/**
 * Shared footer — the site's one navigation bar.
 *
 * Every page used to answer "how do I get to the other four?" differently:
 * `index.php` in the bottom status bar, `joc.php` in a top `.joc-nav`,
 * `stats.php` with a lone "← cuvinte", `lista`/`liste` with "← Oțios". Same five
 * destinations, four placements, and no page listed all of them.
 *
 * The bottom bar won because `index.php` — the page people actually spend time on
 * — already used it, it is thumb-reachable on a phone, and the top bar on the
 * explorer has no room left. See `header.php` for the other half of the split.
 *
 * Set before requiring (all optional):
 *
 *   $page         string  Key of the current page, from NAV_ITEMS below. Marks
 *                         that entry `aria-current="page"` and unlinks it.
 *   $footer_left  string  HTML for the left slot — the explorer's word and
 *                         bookmark counts. Rendered raw; escape at source.
 *   $footer_extra string  HTML between the left slot and the nav — the
 *                         explorer's colour legend, which is too wide for any
 *                         other page and hides itself below 1280px anyway.
 */

$page         = $page         ?? '';
$footer_left  = $footer_left  ?? '';
$footer_extra = $footer_extra ?? '';
?>
<div id="status-bar">
  <span class="status-left"><?= $footer_left ?></span>

  <?= $footer_extra ?>

  <nav class="status-right site-nav" aria-label="Navigare">
    <?php foreach (NAV_ITEMS as $key => $item):
      // The current page stays an <a>, marked `aria-current="page"`. Rendering it
      // as a <span> meant it no longer matched any skin's `#status-bar a` rule and
      // needed a colour of its own — which on beton's ink footer came out near-black
      // on black. Anything a skin has already said about a link in this bar applies
      // to it for free this way, and `is-current` only adds an underline. ?>
      <a class="nav-item<?= $key === $page ? ' is-current' : '' ?>"
         href="<?= BASE . $item['path'] ?>" title="<?= e($item['label']) ?>"
         <?= $key === $page ? 'aria-current="page"' : '' ?>>
        <span class="nav-icon" aria-hidden="true"><?= $item['icon'] ?></span><span class="nav-label"><?= e($item['label']) ?></span>
      </a>
    <?php endforeach; ?>
    <a class="nav-item" href="https://github.com/gov2-ro/otzios" target="_blank" rel="noopener"
       title="Cod sursă pe GitHub"><span class="nav-label">GitHub</span><span class="nav-icon" aria-hidden="true">↗</span></a>
  </nav>
</div>
