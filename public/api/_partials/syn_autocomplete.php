<?php
// $rows = [['form','band'], ...] from syn_autocomplete(), capped at 8.
?>
<?php if ($rows): ?>
<ul class="syn-ac-list" role="listbox" id="syn-ac-list">
  <?php foreach ($rows as $r): ?>
  <li role="option"><a href="<?= BASE ?>/sinonime?q=<?= urlenc($r['form']) ?>"><?= e($r['form']) ?></a></li>
  <?php endforeach; ?>
</ul>
<?php endif; ?>
