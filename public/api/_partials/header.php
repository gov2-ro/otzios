<?php
/**
 * Shared page header — brand, primary nav, and a slot for page-specific controls.
 *
 * Before this existed each of the five pages drew its own bar: `index.php` had
 * `.brand-bar`, `joc.php` had `.joc-head`, `lista`/`liste` had `.lista-nav`, and
 * `stats.php` had **nothing at all** — you landed on a bare filter strip with no
 * indication you were still in Oțios.
 *
 * **`joc` and `colectii` live here; `statistici`, `metodologie`, `liste` and the
 * toggles are in `footer.php` or nowhere.** The two destinations people jump to
 * mid-browse (play the game, see what everyone marked) are one click from the
 * brand, always visible; the rest of
 * travel plus text-scale/skin/theme are the bottom bar's job — see `footer.php`
 * for why that split exists at all.
 *
 * **`despre` is in this bar at every width — as a labelled nav entry from 901px
 * up, and as the `?` chip below it.** It used to be a footer entry on a phone
 * and that is where it died: measured against real traffic, mobile readers do
 * not press the ℹ️ down there, so they never learn what the marks mean. The
 * chip is drawn here rather than in `index.php` because it must exist on every
 * page — the explorer's own `?` (the shortcuts modal) is index-only, and it is
 * the wide half of the same slot. See `.shortcuts-link--wide/--narrow`.
 *
 * Set before requiring (all optional):
 *
 *   $page              string  Key of the current page, from NAV_ITEMS in
 *                              `_lib.php`. Marks the matching top-nav entry
 *                              `aria-current="page"` and unlinks it.
 *   $brand_tag         string  Tagline beside the wordmark. Defaults to the
 *                              site's.
 *   $header_nav_extra  string  HTML in the right cluster, before $header_tools —
 *                              the explorer's `?` shortcuts/legend link, which
 *                              only exists on `index.php` and only shows from
 *                              901px up.
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
$brand_tag         = $brand_tag         ?? 'neglijate';
$header_nav_extra  = $header_nav_extra  ?? '';
$header_center     = $header_center     ?? '';
$header_tools      = $header_tools      ?? '';
$header_after      = $header_after      ?? '';
?>
<header class="brand-bar">
  <a class="brand-id" href="<?= BASE ?>/" title="Voroave — cuvinte neglijate">
    <span class="brand-name">voroave</span>
    <span class="brand-sep"></span>
    <span class="brand-tag"><?= e($brand_tag) ?></span>
  </a>

  <nav class="top-nav" aria-label="Navigare principală">
    <?php
    /*
     * `ghici` and `colectii` are here at every width; `despre` only from 901px up,
     * marked `top-nav-item--wide`. Below that it is the `?` chip in
     * `.brand-right` — one destination, one bar, never both at once.
     *
     * **The bar cannot take three labelled entries on a phone**, which is the
     * measurement the header/footer split was built on and it has not changed:
     * DESPRE plus its icon and gap is ~69px of a 390px bar that also carries the
     * wordmark, a search toggle and the filter button. The chip is how `despre`
     * gets there anyway — it is a glyph, and it lands in a slot that is empty on
     * four of the five pages and vacated by the shortcuts modal on the fifth.
     *
     * `stats`, `metod` and `liste` are in `NAV_ITEMS` but in neither bar — the
     * first two are linked from `despre`, `liste` from the top of `/colectii`.
     * Do not add them back without re-reading the paragraph above.
     */
    foreach (['ghici' => '', 'colectii' => '', 'despre' => ' top-nav-item--wide'] as $key => $width_cls):
      $item = NAV_ITEMS[$key]; ?>
      <a style="text-transform: uppercase;" class="top-nav-item<?= $width_cls ?><?= $key === $page ? ' is-current' : '' ?>"
         href="<?= BASE . $item['path'] ?>" title="<?= e($item['label']) ?>"
         <?= $key === $page ? 'aria-current="page"' : '' ?>>
        <span class="nav-icon" aria-hidden="true"><?= $item['icon'] ?></span><span class="nav-label"><?= e($item['label']) ?></span>
      </a>
    <?php endforeach; ?>
  </nav>

  <?= $header_center ?>  <span class="landing-tagline">Cuvinte aproximativ căzute în uitare. <strong>Suveranism lexical</strong>.</span>
  <div class="brand-right">
    <?php /*
     * The phone's `despre` link. Below 901px the top-nav entry above is hidden
     * and the footer no longer carries one, so this is it — and it sits in the
     * slot `index.php`'s shortcuts `?` vacates at the same breakpoint, so the
     * bar's width does not move on the one page that has both.
     *
     * It keeps the `?` cap and the `.shortcuts-link` class deliberately: the
     * cap is the only thing `kbd { display: none }` is exempted for below
     * 768px (see app.css), and govuk/registru re-ground `.brand-bar
     * .shortcuts-link` for their ink masthead — a class of its own would come
     * out near-black on black in both.
     *
     * `.shortcuts-alt` is the visually-hidden accessible name, so this reads
     * „? despre" to a screen reader rather than „?".
     */ ?>
    <a class="shortcuts-link shortcuts-link--narrow" href="<?= BASE . NAV_ITEMS['despre']['path'] ?>"
       title="Despre — legendă, marcaje și metodă"><kbd>?</kbd><span class="shortcuts-alt">despre</span></a>
  <?= $header_nav_extra ?>
  <?= $header_tools ?>
    <?= $header_after ?>
  </div>
</header>
