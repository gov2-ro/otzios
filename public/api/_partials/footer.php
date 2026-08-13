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
 * **This bar draws no nav entries any more — only GitHub and the display
 * toggles.** `joc` and `liste` moved to `header.php`'s top nav, `cuvinte`
 * (index) was dropped as redundant with the brand mark, and `despre` — the last
 * one left, and only below 901px — followed them up in 2026-08-13 as a `?` chip
 * in the brand bar. The reason was traffic rather than layout: nobody on a phone
 * pressed an ℹ️ parked at the end of a row of display toggles, so the one page
 * that explains the marks was unread by the readers with no other route to it.
 *
 * `$page` is consequently unused here now — still accepted so no caller breaks,
 * and still meaningful to `header.php`, which every one of them also draws.
 *
 * **Text scale / skin / theme moved here from `header.php`.** They are the same
 * three controls on every page, which is exactly what this partial is already
 * for — one nav bar instead of five. The brand bar keeps only what is genuinely
 * page-specific (search, count, play, filters).
 *
 * Set before requiring (all optional):
 *
 *   $page         string  Key of the current page, from NAV_ITEMS. Accepted but
 *                         no longer used — see above.
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
      <?php /*
       * No nav entries left here — this bar is GitHub and the display toggles.
       *
       * `despre` was the last one, drawn below 901px only (the header showed it
       * above). It is gone because it did not work: on a phone the ℹ️ sat at the
       * far end of a bar of display toggles and readers did not press it, so the
       * page that explains what the marks mean went unread by exactly the people
       * who had no other way to find out. `header.php` now puts a `?` chip in the
       * brand bar at that width instead — top of the screen, next to the words,
       * and free (it reuses the slot `index.php`'s shortcuts modal vacates).
       *
       * If a nav entry ever comes back here it needs `.nav-item` and the ≤900px
       * label/icon rules with it; both were removed from app.css as dead rather
       * than left to rot. Git history has them.
       */ ?>
      <!-- <a class="nav-item" href="https://github.com/gov2-ro/voroave" target="_blank" rel="noopener"
         title="Cod sursă pe GitHub"><span class="nav-label">GitHub</span><span class="nav-icon" aria-hidden="true">↗</span></a> -->
        <a href="https://github.com/gov2-ro/voroave" target="_blank" rel="noopener" aria-label="GitHub" style="color: var(--text3); line-height: 1; display: inline-flex; align-items: center; flex-shrink: 0; float: right; margin-top: 1px;"><svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.342-3.369-1.342-.454-1.155-1.11-1.462-1.11-1.462-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0112 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.163 22 16.418 22 12c0-5.523-4.477-10-10-10z"></path></svg></a>
    </nav>
  </div>
</div>
