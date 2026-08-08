<?php
// $w = array with word row data
$verdict      = $w['verdict'] ?? 'unknown';
$verdict_cls  = str_replace(' ', '_', $verdict);
$pos_parts    = array_filter(array_map('trim', explode('|', $w['dex_pos'] ?? '')));
$reg_parts    = array_filter(array_map('trim', explode('|', $w['dex_register'] ?? '')));
$dom_parts    = array_filter(array_map('trim', explode('|', $w['dex_domain'] ?? '')));
$etym_parts   = array_filter(array_map('trim', explode('|', $w['dex_etymology'] ?? '')));
$etym_parts   = array_map(fn($e) => str_replace('limba ', '', $e), $etym_parts);

$sources = split_pipe($w['sources'] ?? '');
$dict_count = count($sources);

// Comma-separated, unlike the pipe-delimited taxonomy columns — they come from prose in
// the Sinonime dictionaries, where a comma is the separator the source itself uses.
$synonyms = array_values(array_filter(array_map('trim',
    explode(',', $w['synonyms'] ?? '')), fn($s) => $s !== ''));
$antonyms = array_values(array_filter(array_map('trim',
    explode(',', $w['antonyms'] ?? '')), fn($s) => $s !== ''));

$meta_parts = array_filter([
    $pos_parts   ? e($pos_parts[0])   : null,
    $reg_parts   ? e($reg_parts[0])   : null,
    $etym_parts  ? e($etym_parts[0])  : null,
]);
?>
<button class="fp-close" onclick="closePanel()">✕</button>

<!-- Head: word + verdict + meta -->
<div class="fp-head">
  <div class="fp-title"><?= e($w['word']) ?></div>
  <div class="fp-subtitle">
    <span class="verdict-badge vb-<?= e($verdict_cls) ?>" title="<?= e(VERDICTS[$verdict]['tip'] ?? '') ?>"><?= e(verdict_label($verdict)) ?></span>
    <?php if ($meta_parts): ?>
    <span class="fp-pos-line"><?= implode(' · ', $meta_parts) ?></span>
    <?php endif; ?>
  </div>
</div>

<!-- Scrollable body -->
<div class="fp-body">

  <?php if ($w['definition']): ?>
  <div class="definition-text"><?= e($w['definition']) ?></div>
  <?php else: ?>
  <span class="fp-nodef">fără definiție locală</span>
  <?php endif; ?>

  <!-- Tag chips -->
  <?php $all_tags = array_merge(
      array_slice($pos_parts, 1),
      $reg_parts,
      $dom_parts,
      $etym_parts
  ); ?>
  <?php $tier_lbl = tier_label($w['confidence_tier'] ?? null); ?>
  <?php if ($all_tags || $tier_lbl): ?>
  <div class="fp-chips">
    <?php if (count($pos_parts) > 1): ?>
      <?php foreach (array_slice($pos_parts, 1) as $p): ?><span class="detail-tag"><?= e($p) ?></span><?php endforeach; ?>
    <?php endif; ?>
    <?php foreach ($reg_parts as $r): ?><span class="detail-tag"><?= e($r) ?></span><?php endforeach; ?>
    <?php foreach ($dom_parts as $d): ?><span class="detail-tag" style="opacity:.85"><?= e($d) ?></span><?php endforeach; ?>
    <?php foreach ($etym_parts as $et): ?><span class="detail-tag" style="opacity:.7"><?= e($et) ?></span><?php endforeach; ?>
    <?php if ($tier_lbl): ?><span class="detail-tag" style="opacity:.5;font-size:0.5625rem;" title="<?= e(TIERS[$w['confidence_tier']]['tip'] ?? '') ?>"><?= e($tier_lbl) ?></span><?php endif; ?>
  </div>
  <?php endif; ?>

  <!-- Synonyms / antonyms (scrape_synonyms.py; absent until a word has been scraped) -->
  <?php
    $syns = array_slice($synonyms, 0, 12);
    $ants = array_slice($antonyms, 0, 8);
  ?>
  <?php if ($syns): ?>
  <div class="fp-syn">
    <span class="fp-extra-label">≡ sinonime</span>
    <?php foreach ($syns as $s): ?><a class="syn-chip" href="<?= BASE ?>/?q=<?= urlenc($s) ?>"><?= e($s) ?></a><?php endforeach; ?>
    <?php if (count($synonyms) > count($syns)): ?><span class="syn-more">+<?= count($synonyms) - count($syns) ?></span><?php endif; ?>
  </div>
  <?php endif; ?>
  <?php if ($ants): ?>
  <div class="fp-syn">
    <span class="fp-extra-label">≠ antonime</span>
    <?php foreach ($ants as $a): ?><a class="syn-chip syn-chip--ant" href="<?= BASE ?>/?q=<?= urlenc($a) ?>"><?= e($a) ?></a><?php endforeach; ?>
  </div>
  <?php endif; ?>

  <!-- Dictionaries -->
  <?php if ($sources): ?>
  <div class="fp-dicts">
    <span class="fp-extra-label">📚 în <?= $dict_count ?> <?= $dict_count === 1 ? 'dicționar' : 'dicționare' ?></span>
    <?php
    // Last attestation: the newest dictionary that still prints this word. A
    // lexicographic claim, independent of the corpus figures in the footer below —
    // and a far more legible one than `raport 3.12`. `newest_dict_year` has been in
    // ui.db since the dict-sources extractor learned to read `Source.year`; this is
    // the first thing to read it. Absent for ~3% of words, where the dictionary is
    // unnamed or unmatched, and then simply not shown.
    $attested = isset($w['newest_dict_year']) ? (int) $w['newest_dict_year'] : 0;
    if ($attested > 0): ?>
      <span class="dict-chip dict-chip--year"
            title="Cel mai recent dicționar din DEX care încă include acest cuvânt">ultima atestare <?= $attested ?></span>
    <?php endif; ?>
    <?php foreach ($sources as $src): ?><span class="dict-chip"><?= e($src) ?></span><?php endforeach; ?>
  </div>
  <?php endif; ?>

</div>

<!-- Footer: stats + actions + dexonline -->
<div class="fp-foot">

  <div class="fp-stats">
    <?php if ($w['zipf_frequency'] !== null): ?><span title="Frecvență Zipf în română — sub 3,0 înseamnă ieșit din uz"><em>zipf ro</em><?= number_format((float)$w['zipf_frequency'], 1) ?></span><?php endif; ?>
    <?php if ($w['en_zipf'] !== null): ?><span title="Frecvență Zipf în engleză — o valoare mare sugerează un împrumut recent"><em>zipf en</em><?= number_format((float)$w['en_zipf'], 1) ?></span><?php endif; ?>
    <span title="Apariții la un milion de cuvinte în corpusul istoric (Wikisource)"><em>istoric</em><?= $w['hist_ppm'] !== null ? number_format((float)$w['hist_ppm'], 2) : '—' ?></span>
    <span title="Apariții la un milion de cuvinte în corpusul modern (CulturaX)"><em>modern</em><?= $w['modern_ppm'] !== null ? number_format((float)$w['modern_ppm'], 2) : '—' ?></span>
    <span title="log2(istoric / modern) — cât de mult a scăzut folosirea"><em>raport</em><?= $w['log_ratio'] !== null ? number_format((float)$w['log_ratio'], 2) : '—' ?></span>
  </div>

  <div class="fp-btns">
    <button id="bookmark-btn" data-word="<?= e($w['word']) ?>" title="fav (f) — păstrează, cuvânt de care ești mândru"><span class="qt-key">f</span><span class="fav-star">★</span> fav</button>
    <div id="tags-row" data-word="<?= e($w['word']) ?>">
      <div class="quick-tags">
        <button type="button" class="qt-btn" data-qtkey="a" title="ascunde (a) — neinteresant, prea cunoscut. Dispare din listă, îl regăsești în settings"><span class="qt-key">a</span>ascunde</button>
        <button type="button" class="qt-btn" data-qtkey="l" title="lol (l) — amuzant, de păstrat"><span class="qt-key">l</span>lol</button>
        <button type="button" class="qt-btn" data-qtkey="m" title="meh (m) — la fel ca ascunde, doar zis altfel. Dispare din listă, îl regăsești în settings"><span class="qt-key">m</span>meh</button>
      </div>
    </div>
  </div>

  <div id="qt-explainer" class="qt-explainer">
    <span>★ <strong>fav</strong> și <strong>lol</strong> = cuvinte de păstrat. <strong>ascunde</strong> și <strong>meh</strong> = prea cunoscut, dispare din listă (îl regăsești în <em>settings</em>).</span>
    <button type="button" id="qt-explainer-close" title="ascunde acest mesaj">✕</button>
  </div>

  <a class="dex-link"
     href="https://dexonline.ro/definitie/<?= urlenc($w['word']) ?>"
     target="_blank" rel="noopener">↗ deschide pe dexonline.ro</a>

</div>
