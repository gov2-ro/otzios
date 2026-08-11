<?php
/**
 * Shared footer — the site's one navigation bar, plus the display preferences
 * that used to live in the brand bar.
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
 * **Only `statistici` and `metodologie` loop from `NAV_ITEMS` here, and only
 * below 901px.** `joc` and `liste` moved to `header.php`'s top nav — reachable
 * from every page now, not just thumb-reach on a phone — and `cuvinte` (index)
 * is dropped rather than moved: the brand mark in every header already links
 * home, so a second link to the same place was pure redundancy.
 *
 * The two that remain are marked `nav-item--wide` and are **hidden from 901px
 * up**, where `header.php` shows them instead (`top-nav-item--wide`). They are
 * in both partials on purpose, with app.css picking exactly one: the header bar
 * has the room on a desktop and burying the two explanatory pages in the footer
 * was hiding them, but four labelled nav entries do not fit a phone bar — which
 * is the measurement this split was built on in the first place. Above the
 * crossover this bar keeps only the GitHub link.
 *
 * **Text scale / skin / theme moved here from `header.php`.** They are the same
 * three controls on every page, which is exactly what this partial is already
 * for — one nav bar instead of five. The brand bar keeps only what is genuinely
 * page-specific (search, count, play, filters).
 *
 * Set before requiring (all optional):
 *
 *   $page         string  Key of the current page, from NAV_ITEMS below. Marks
 *                         that entry `aria-current="page"` and unlinks it.
 *   $footer_left  string  HTML for the left slot — the explorer's word and
 *                         bookmark counts. Rendered raw; escape at source.
 *   $footer_extra string  HTML between the left slot and the preferences — the
 *                         explorer's colour legend, which is too wide for any
 *                         other page and hides itself below 1280px anyway.
 *   $footer_tools string  HTML between the legend and the preferences — the
 *                         explorer's feed button and cloud/table view toggle,
 *                         the only controls here that are index-only.
 */

$page         = $page         ?? '';
$footer_left  = $footer_left  ?? '';
$footer_extra = $footer_extra ?? '';
$footer_tools = $footer_tools ?? '';
?>
<div id="status-bar">
  <span class="status-left"><?= $footer_left ?></span>

  <div class="status-right">
    <?= $footer_extra ?>

    <?= $footer_tools ?>

    <div class="status-prefs" role="group" aria-label="Afișare">
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
    </div>

    <nav class="site-nav" aria-label="Navigare">
      <?php // Explicit rather than a diff over NAV_ITEMS: that const is the registry of
            // pages, and `stats`/`metod` are still in it (so they can be marked current)
            // while no longer being nav entries. A diff would silently put them back.
            foreach (['despre'] as $key): $item = NAV_ITEMS[$key];
        // The current page stays an <a>, marked `aria-current="page"`. Rendering it
        // as a <span> meant it no longer matched any skin's `#status-bar a` rule and
        // needed a colour of its own — which on beton's ink footer came out near-black
        // on black. Anything a skin has already said about a link in this bar applies
        // to it for free this way, and `is-current` only adds an underline. ?>
        <a class="nav-item nav-item--wide<?= $key === $page ? ' is-current' : '' ?>"
           href="<?= BASE . $item['path'] ?>" title="<?= e($item['label']) ?>"
           <?= $key === $page ? 'aria-current="page"' : '' ?>>
          <span class="nav-icon" aria-hidden="true"><?= $item['icon'] ?></span><span class="nav-label"><?= e($item['label']) ?></span>
        </a>
      <?php endforeach; ?>
      <a class="nav-item" href="https://github.com/gov2-ro/otzios" target="_blank" rel="noopener"
         title="Cod sursă pe GitHub"><span class="nav-label">GitHub</span><span class="nav-icon" aria-hidden="true">↗</span></a>
    </nav>
  </div>
</div>
