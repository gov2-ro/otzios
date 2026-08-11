<?php
// $words        = array of word rows
// $total        = int
// $page         = int
// $next_url     = string|null  full /api/search.php?... URL
?>
<?php if ($page === 1): ?>
<?php /* hx-swap-oob replaces the whole element, so these have to carry the
         classes and surrounding wording the page markup already has — the
         count span was losing `.result-count` (and its styling) on the first
         search, and both were appending an English "words" next to the
         Romanian noun already in the status bar. */ ?>
<span id="status-word-count" hx-swap-oob="true"><?= (int)$total ?></span>
<span id="result-count" class="result-count" hx-swap-oob="true"><?= number_format((int)$total) ?></span>
<?php endif; ?>
<?php if ($page === 1 && !empty($facets)): ?>
<?php /* Per-option counts for the filter sheet, which lives outside #word-list and so
         cannot be swapped by the same response. Travels as one out-of-band data
         attribute rather than as markup: the sheet already knows where its numbers go
         (every option carries data-facet), and shipping HTML for it would mean the
         server rendering the sheet twice. app.js reads this on htmx:afterSwap. */ ?>
<span id="facet-data" hidden hx-swap-oob="true"
      data-facets="<?= e(json_encode($facets, JSON_UNESCAPED_UNICODE)) ?>"></span>
<?php endif; ?>
<?php foreach ($words as $w): include __DIR__ . '/word_row.php'; endforeach; ?>
<?php if (empty($words)): ?>
<p class="word-list-empty">Niciun cuvânt nu se potrivește filtrelor.</p>
<?php endif; ?>
<?php if ($next_url): ?>
<div id="load-more"
     hx-get="<?= e($next_url) ?>"
     hx-trigger="intersect once"
     hx-target="#load-more"
     hx-swap="outerHTML"
     style="grid-column:1/-1;height:1px;"></div>
<?php endif; ?>
