<?php
/**
 * Landing state, q === ''. ui.md § Landing state: a centred search box (drawn by the
 * caller) plus one-click examples chosen to teach the tool without a paragraph of copy.
 */
?>
<div class="syn-landing">
  <p class="syn-landing-lead">
    O unealtă de scris: caută un cuvânt, primești alternative — ordonate după cât de vii
    sunt azi în limba română, nu alfabetic.
  </p>
  <div class="syn-examples">
    <a class="syn-example" href="<?= BASE ?>/sinonime?q=frumos">
      <strong>frumos</strong><span>sinonime vii și moarte, unul lângă altul</span>
    </a>
    <a class="syn-example" href="<?= BASE ?>/sinonime?q=v%C4%83z">
      <strong>văz</strong><span>trei sensuri diferite, trei ciorchini diferiți</span>
    </a>
    <a class="syn-example" href="<?= BASE ?>/sinonime?q=repede">
      <strong>repede</strong><span>o căutare obișnuită, complet vie</span>
    </a>
  </div>
</div>
