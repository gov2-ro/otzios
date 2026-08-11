<?php
declare(strict_types=1);
require_once __DIR__ . '/api/_lib.php';

// The "what is this" page: /despre.php
//
// It replaced `statistici` and `metodologie` in the nav rather than joining them. Three
// entries competing for a phone bar was already the constraint that split the nav between
// header and footer; a fourth would have broken it again. Both pages are linked from here
// instead, which is also the more honest shape — a reader who wants the method has almost
// always read the overview first.
//
// Counts come from ui.db so the page cannot drift from the data the way a hardcoded
// number would. `db_has_column()` guards each one for an older database.

$n_total     = (int) db()->query("SELECT COUNT(*) FROM words")->fetchColumn();
$n_relevant  = db_has_column('seam')
    ? (int) db()->query("SELECT COUNT(*) FROM words WHERE seam='relevant'")->fetchColumn() : 0;
$n_curiosity = db_has_column('seam')
    ? (int) db()->query("SELECT COUNT(*) FROM words WHERE seam='curiosity'")->fetchColumn() : 0;
$n_defs      = (int) db()->query("SELECT COUNT(*) FROM words WHERE definition IS NOT NULL")->fetchColumn();

$nf = fn(int $n): string => number_format($n, 0, ',', '.');

$og_title = 'Despre — Oțios';
$og_desc  = 'Cum sunt găsite cuvintele uitate ale limbii române: două corpusuri, '
          . 'dicționarul DEX, și marcajele cititorilor. ' . $nf($n_total) . ' de cuvinte.';
?>
<!DOCTYPE html>
<html lang="ro" data-skin="<?= DEFAULT_SKIN ?>">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <?= otios_skin_boot() ?>
  <title><?= e($og_title) ?></title>
  <meta name="description" content="<?= e($og_desc) ?>">
  <link rel="canonical" href="<?= e(otios_abs_url('/despre.php')) ?>">

  <meta property="og:type" content="article">
  <meta property="og:site_name" content="Oțios">
  <meta property="og:locale" content="ro_RO">
  <meta property="og:title" content="<?= e($og_title) ?>">
  <meta property="og:description" content="<?= e($og_desc) ?>">
  <meta property="og:url" content="<?= e(otios_abs_url('/despre.php')) ?>">
  <meta property="og:image" content="<?= e(otios_abs_url('/screenshot-otzios.png')) ?>">
  <meta property="og:image:alt" content="Lista de cuvinte uitate din Oțios">

  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="<?= e($og_title) ?>">
  <meta name="twitter:description" content="<?= e($og_desc) ?>">
  <meta name="twitter:image" content="<?= e(otios_abs_url('/screenshot-otzios.png')) ?>">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&family=Public+Sans:ital,wght@0,400..800;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="<?= BASE ?>/assets/app.css">
  <link rel="stylesheet" href="<?= BASE ?>/assets/doc.css">
  <?= otios_skin_links() ?>
  <style>
    .despre-wrap { max-width: 1240px; margin: 0 auto; padding: 28px 20px 64px; }
    .despre-wrap h1 {
      font-family: var(--serif); font-size: 2rem; font-weight: 600;
      color: var(--text); margin: 0 0 6px;
    }
    .despre-lede { color: var(--text-2); font-size: 1.0625rem; line-height: 1.6; margin: 0 0 30px; }
    .despre-wrap h2 {
      font-family: var(--mono); font-size: 0.6875rem; text-transform: uppercase;
      letter-spacing: .08em; color: var(--text-3); font-weight: 500;
      margin: 34px 0 10px; padding-bottom: 6px; border-bottom: 1px solid var(--border);
    }
    .despre-wrap p  { color: var(--text-2); font-size: 0.9375rem; line-height: 1.65; margin: 0 0 12px; }
    .despre-wrap li { color: var(--text-2); font-size: 0.9375rem; line-height: 1.6; margin-bottom: 6px; }
    .despre-wrap ul { margin: 0 0 14px; padding-left: 20px; }
    .despre-wrap strong { color: var(--text); font-weight: 600; }
    .despre-wrap a { color: var(--accent); }
    .despre-wrap code, .despre-key {
      font-family: var(--mono); font-size: 0.8125em;
      background: var(--surface-2); border: 1px solid var(--border);
      border-radius: 3px; padding: 1px 5px; color: var(--text);
    }
    /* Size and placement come from doc.css — on desktop these float out into the gutter
       beside the prose. Here only the frame. */
    .despre-shot { margin: 14px 0 20px; }
    .despre-shot img {
      display: block; width: 100%; height: auto;
      border: 1px solid var(--border); border-radius: var(--radius);
      background: var(--surface);
    }
    .despre-shot figcaption {
      font-family: var(--mono); font-size: 0.6875rem; color: var(--text-4);
      margin-top: 6px; line-height: 1.5;
    }
    .despre-stats {
      display: flex; flex-wrap: wrap; gap: 18px;
      margin: 0 0 24px; padding: 14px 0; border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
    }
    .despre-stat b {
      display: block; font-family: var(--serif); font-size: 1.375rem;
      color: var(--text); font-weight: 600; line-height: 1.1;
    }
    .despre-stat span { font-family: var(--mono); font-size: 0.6875rem; color: var(--text-3); }
    .despre-more { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; }
    .despre-more a {
      display: inline-block; text-decoration: none;
      font-family: var(--mono); font-size: 0.75rem;
      border: 1px solid var(--border-2); border-radius: var(--radius);
      padding: 8px 12px; color: var(--text-2);
    }
    .despre-more a:hover { border-color: var(--accent); color: var(--accent); }
  </style>
</head>
<body class="page-doc">
  <?php $page = 'despre'; $brand_tag = 'despre'; require __DIR__ . '/api/_partials/header.php'; ?>

  <div class="despre-wrap doc-layout">

    <!-- Built from the h2s by assets/doc.js; sticky beside the text on desktop, a
         collapsed disclosure above it on a phone. -->
    <nav class="doc-toc" data-toc=".doc-body" aria-label="Cuprins">
      <div class="doc-toc-title">Pe această pagină</div>
    </nav>
    <details class="doc-toc-mobile">
      <summary>Pe această pagină</summary>
      <div class="doc-toc" data-toc=".doc-body"></div>
    </details>

    <div class="doc-body">
    <h1>Despre Oțios</h1>
    <p class="despre-lede">
      Oțios caută cuvintele pe care româna le-a avut și le-a lăsat să cadă. Nu cuvinte rare,
      nu cuvinte grele — cuvinte <em>folosite</em> odată și aproape absente azi.
    </p>

    <div class="despre-stats">
      <div class="despre-stat"><b><?= $nf($n_total) ?></b><span>cuvinte</span></div>
      <?php if ($n_relevant): ?>
      <div class="despre-stat"><b><?= $nf($n_relevant) ?></b><span>relevante</span></div>
      <div class="despre-stat"><b><?= $nf($n_curiosity) ?></b><span>curiozități</span></div>
      <?php endif; ?>
      <div class="despre-stat"><b><?= $nf($n_defs) ?></b><span>cu definiție</span></div>
    </div>

    <h2>Cum sunt găsite</h2>
    <p>
      Pornim de la <strong>DEX Online</strong> — dicționarul întreg, cu toate formele lui
      flexionare. Apoi numărăm fiecare cuvânt în două corpusuri de text:
    </p>
    <ul>
      <li><strong>istoric</strong> — Wikisource plus romane vechi, ~14 milioane de cuvinte;</li>
      <li><strong>modern</strong> — CulturaX, <strong>17 miliarde</strong> de cuvinte.</li>
    </ul>
    <p>
      Un cuvânt care apare des în primul și aproape deloc în al doilea e un cuvânt uitat.
      Numărătoarea se face pe <em>toată paradigma</em>, nu pe forma de dicționar: altfel
      orice verb pare dispărut, fiindcă infinitivul lui e rar chiar și când verbul e viu.
    </p>
    <p>
      Contraintuitiv, dar important: <strong>cu cât un cuvânt mai are urme azi, cu atât e
      material mai bun</strong>. <em>Zapciu</em>, <em>birjă</em>, <em>vechil</em> apar de
      câteva mii de ori în româna modernă — de-asta le și recunoști. Cuvintele cu zero
      apariții sunt de obicei fantome de dicționar, care n-au circulat niciodată.
    </p>

    <h2>Cele două liste</h2>
    <p>
      <strong>Relevante</strong> sunt cuvintele cu dovezi puternice: atestate istoric,
      aproape absente azi, prezente în multe dicționare, și încă într-unul tipărit din 2005
      încoace. <strong>Curiozități</strong> e restul — încă îndeplinesc condițiile, dar
      dovada e mai slabă. Implicit vezi doar prima listă; bifează-le pe amândouă în
      <em>Filtre</em> ca să le vezi pe toate.
    </p>

    <figure class="despre-shot is-wide">
      <a href="<?= BASE ?>/assets/despre/grid.png" target="_blank" rel="noopener" title="Vezi la mărime completă"><img src="<?= BASE ?>/assets/despre/grid.png" alt="Grila de cuvinte din Oțios, cu scorul de frecvență DEX lângă fiecare cuvânt" loading="lazy"></a>
      <figcaption>Lista. Cifra mică de lângă cuvânt e frecvența DEX — cât de bine e cuvântul
      așezat în canonul literar, nu cât de des e folosit.</figcaption>
    </figure>

    <h2>Filtrele îți spun ce ascund</h2>
    <p>
      Fiecare filtru arată <strong>câte cuvinte ar întoarce</strong>, recalculat după
      tot ce ai ales deja, și fiecare secțiune are un <span class="despre-key">?</span> cu
      explicația. Nimic nu e scos din listă în tăcere: dacă o clasă de cuvinte e ascunsă
      implicit, e un comutator vizibil, iar „doar” ți le arată exact pe ele — ca să vezi
      unde am tras linia greșit.
    </p>

    <figure class="despre-shot">
      <a href="<?= BASE ?>/assets/despre/filtre.png" target="_blank" rel="noopener" title="Vezi la mărime completă"><img src="<?= BASE ?>/assets/despre/filtre.png" alt="Panoul de filtre, cu numărul de cuvinte lângă fiecare opțiune" loading="lazy"></a>
      <figcaption>Panoul de filtre. Numerele se recalculează la fiecare schimbare.</figcaption>
    </figure>

    <h2>Cuvinte marcate</h2>
    <p>
      Poți marca orice cuvânt din panoul de detalii sau direct de la tastatură:
    </p>
    <ul>
      <li><span class="despre-key">f</span> <strong>★ fav</strong> — merită păstrat;</li>
      <li><span class="despre-key">l</span> <strong>😂 lol</strong> — amuzant;</li>
      <li><span class="despre-key">m</span> <strong>⚠️ meh</strong> — nu e ce căutăm;</li>
      <li><span class="despre-key">a</span> <strong>🙈 ascunde</strong> — scoate-l din calea mea.</li>
    </ul>
    <p>
      Marcajele rămân ale tale și te urmează între dispozitive. Fiecare marcaj te trece
      automat la cuvântul următor — marcarea e o buclă de triaj, nu un formular.
    </p>
    <p>
      Marcajele <em>tuturor</em> intră și în ordinea listei, prin sortarea
      <strong>„populare”</strong>: ★ și 😂 urcă un cuvânt, ⚠️ îl coboară. Efectul e
      amortizat deliberat — fiecare dublare a numărului de voturi valorează încă vreo două
      puncte — și <strong>voturile doar reordonează, niciodată nu scot un cuvânt din
      listă</strong>.
    </p>

    <figure class="despre-shot">
      <a href="<?= BASE ?>/assets/despre/detail.png" target="_blank" rel="noopener" title="Vezi la mărime completă"><img src="<?= BASE ?>/assets/despre/detail.png" alt="Panoul de detalii al unui cuvânt, cu definiția și butoanele de marcare" loading="lazy"></a>
      <figcaption>Panoul de detalii: definiția, dicționarele în care apare, și butoanele de marcare.</figcaption>
    </figure>

    <h2>Liste publice</h2>
    <p>
      Cuvintele pe care le marchezi se adună singure în patru liste — nu le construiești,
      apar din marcaje. Oricare dintre ele se poate <strong>publica</strong> cu un buton, și
      primești un link de trimis mai departe. Nu există „adaugă la listă” per cuvânt tocmai
      pentru asta: curatoriezi marcând, în timp ce citești.
    </p>
    <p>
      Un link partajat arată exact cuvintele trimise — filtrele implicite nu se aplică peste
      lista altcuiva. O listă de douăzeci de cuvinte ajunge cu douăzeci.
    </p>

    <figure class="despre-shot is-wide">
      <a href="<?= BASE ?>/assets/despre/liste.png" target="_blank" rel="noopener" title="Vezi la mărime completă"><img src="<?= BASE ?>/assets/despre/liste.png" alt="Pagina de liste, cu lista redacției și cele patru liste proprii" loading="lazy"></a>
      <figcaption>Pagina <a href="<?= BASE ?>/liste.php">Liste</a>: alegerile redacției sus,
      cele patru liste proprii dedesubt.</figcaption>
    </figure>

    <h2>Mai departe</h2>
    <p>
      Proiectul e deschis, iar metoda e scrisă în detaliu — inclusiv ce <em>nu</em> a
      funcționat, care e adesea partea mai utilă.
    </p>
    <div class="despre-more">
      <a href="<?= BASE ?>/metodologie.html">🧐 Metodologie — cum se măsoară</a>
      <a href="<?= BASE ?>/stats.php">📊 Statistici — ce e în bază</a>
      <a href="https://github.com/gov2-ro/otzios" target="_blank" rel="noopener">↗ Cod sursă pe GitHub</a>
    </div>
    </div><!-- /.doc-body -->
  </div>

  <?php require __DIR__ . '/api/_partials/footer.php'; ?>
  <script src="<?= BASE ?>/assets/doc.js"></script>
  <script src="<?= BASE ?>/assets/store.js"></script>
  <script src="<?= BASE ?>/assets/app.js"></script>
</body>
</html>
