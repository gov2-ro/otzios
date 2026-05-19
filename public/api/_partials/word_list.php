<?php
// $words        = array of word rows
// $total        = int
// $page         = int
// $next_url     = string|null  full /api/search.php?... URL
?>
<?php if ($page === 1): ?>
<span id="status-word-count" hx-swap-oob="true"><?= (int)$total ?> words</span>
<?php endif; ?>
<?php foreach ($words as $w): include __DIR__ . '/word_row.php'; endforeach; ?>
<?php if (empty($words)): ?>
<p style="color:#555;padding:12px;">No words match.</p>
<?php endif; ?>
<?php if ($next_url): ?>
<div id="load-more"
     hx-get="<?= e($next_url) ?>"
     hx-trigger="intersect once"
     hx-target="#load-more"
     hx-swap="outerHTML"
     style="grid-column:1/-1;height:1px;"></div>
<?php endif; ?>
