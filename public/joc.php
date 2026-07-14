<?php
declare(strict_types=1);
require_once __DIR__ . '/api/_lib.php';
?>
<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
  <script>(function(){try{var t=localStorage.getItem('otios.theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.setAttribute('data-theme',t);var s=localStorage.getItem('otios.textscale')||'100';document.documentElement.style.fontSize=s+'%';}catch(e){}})();</script>
  <title>Oțios — Joc</title>
  <meta property="og:title" content="Oțios — joc">
  <meta property="og:description" content="Învață cuvinte românești uitate prin carduri și un test grilă.">
  <meta property="og:type" content="website">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&family=Public+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="<?= BASE ?>/assets/app.css">
  <style>
    body { display:flex; flex-direction:column; min-height:100vh; }
    .joc-head {
      display:flex; align-items:center; gap:14px; flex-wrap:wrap;
      padding:10px 16px; border-bottom:1px solid var(--border); background:var(--surface);
    }
    .joc-title { font-family:var(--serif); font-weight:600; font-size:1.0625rem; color:var(--text); }
    .joc-modes { display:flex; gap:6px; }
    .joc-mode {
      font-family:var(--mono); font-size:0.75rem; padding:4px 12px; border-radius:14px;
      border:1px solid var(--border-2); background:var(--surface); color:var(--text-2); cursor:pointer;
    }
    .joc-mode.active { background:var(--accent); border-color:var(--accent); color:var(--on-accent); }
    .joc-score { margin-left:auto; font-family:var(--mono); font-size:0.75rem; color:var(--text-3); }
    .joc-nav a { font-family:var(--mono); font-size:0.75rem; color:var(--text-3); text-decoration:none; margin-left:12px; }
    .joc-nav a:hover { color:var(--text); }
    .joc-main { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:24px 16px; }
    .joc-card {
      width:100%; max-width:580px; background:var(--surface); border:1px solid var(--border-2);
      border-radius:16px; box-shadow:0 8px 30px rgba(0,0,0,.08); padding:30px 28px;
    }
    .joc-prompt-label { font-family:var(--mono); font-size:0.625rem; letter-spacing:.12em; text-transform:uppercase; color:var(--text-3); margin-bottom:10px; }
    .joc-word { font-family:var(--serif); font-weight:600; font-size:2.6em; letter-spacing:-.02em; line-height:1.05; color:var(--text); overflow-wrap:break-word; }
    .joc-def { font-family:var(--serif); font-style:italic; font-size:1.125rem; line-height:1.6; color:var(--text); margin-top:6px; }
    .joc-pos { font-family:var(--mono); font-size:0.75rem; color:var(--text-3); margin-top:8px; }
    .joc-choices { display:flex; flex-direction:column; gap:10px; margin-top:22px; }
    .joc-choice {
      text-align:left; font-family:var(--serif); font-size:1.125rem; padding:12px 16px;
      border:1.5px solid var(--border-2); border-radius:10px; background:var(--surface); color:var(--text); cursor:pointer;
    }
    .joc-choice:hover:not(:disabled) { border-color:var(--accent); }
    .joc-choice.correct { border-color:var(--success-border); background:var(--success-bg); color:var(--success); }
    .joc-choice.wrong { border-color:var(--error-border); background:var(--error-bg); color:var(--error); }
    .joc-choice:disabled { cursor:default; }
    .joc-actions { display:flex; gap:12px; margin-top:22px; flex-wrap:wrap; }
    .joc-btn {
      height:42px; padding:0 18px; border-radius:21px; font-family:var(--mono); font-size:0.8125rem; font-weight:700; cursor:pointer;
      border:1.5px solid var(--accent); background:var(--accent); color:var(--on-accent);
    }
    .joc-btn.secondary { background:var(--surface); color:var(--accent); }
    .joc-btn:active { transform:scale(.98); }
    .joc-feedback { font-family:var(--mono); font-size:0.8125rem; margin-top:16px; min-height:18px; }
    .joc-feedback.ok { color:var(--success); }
    .joc-feedback.no { color:var(--error); }
    .joc-reveal { font-family:var(--mono); font-size:0.75rem; color:var(--text-3); margin-top:8px; }
    .joc-dexlink { color:var(--accent); font-size:0.75rem; text-decoration:none; }
    @media (max-width:768px) { .joc-word { font-size:2.1em; } .joc-def { font-size:1.0625rem; } }
  </style>
</head>
<body>
  <div class="joc-head">
    <span class="joc-title">Oțios · joc</span>
    <div class="joc-modes">
      <button type="button" class="joc-mode active" data-mode="flash" onclick="setMode('flash')">📇 carduri</button>
      <button type="button" class="joc-mode" data-mode="quiz" onclick="setMode('quiz')">❓ grilă</button>
    </div>
    <span class="joc-score" id="joc-score"></span>
    <div class="scale-stepper scale-stepper--sm" role="group" aria-label="Mărime text">
      <button type="button" class="scale-btn" data-scale-btn="down" onclick="stepTextScale(-1)" title="Text mai mic">A−</button>
      <button type="button" class="scale-btn" data-scale-btn="up" onclick="stepTextScale(1)" title="Text mai mare">A+</button>
    </div>
    <div class="theme-toggle theme-toggle--sm" role="group" aria-label="Temă">
      <button type="button" class="tg-btn" data-theme-btn="light" onclick="setTheme('light')" title="Temă deschisă">☀</button>
      <button type="button" class="tg-btn" data-theme-btn="dark" onclick="setTheme('dark')" title="Temă întunecată">☾</button>
    </div>
    <span class="joc-nav"><a href="<?= BASE ?>/">← acasă</a><a href="<?= BASE ?>/stats.php">statistici</a></span>
  </div>

  <div class="joc-main">
    <div class="joc-card" id="joc-card">se încarcă…</div>
  </div>

  <script>var OTIOS_BASE = '<?= BASE ?>';</script>
  <script>
  // Theme + text-scale controls (duplicated small logic, no full app.js load needed)
  var TEXT_SCALE_STEPS = [87.5, 100, 112.5, 125, 137.5];
  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem('otios.theme', theme); } catch (_) {}
    syncThemeButtons();
  }
  function syncThemeButtons() {
    var theme = document.documentElement.getAttribute('data-theme') || 'light';
    document.querySelectorAll('[data-theme-btn]').forEach(function(btn) {
      btn.classList.toggle('tg-active', btn.dataset.themeBtn === theme);
    });
  }
  function currentTextScale() { return parseFloat(document.documentElement.style.fontSize) || 100; }
  function nearestScaleIdx(val) {
    var idx = TEXT_SCALE_STEPS.indexOf(val);
    if (idx !== -1) return idx;
    var best = 0;
    TEXT_SCALE_STEPS.forEach(function(v, i) { if (Math.abs(v - val) < Math.abs(TEXT_SCALE_STEPS[best] - val)) best = i; });
    return best;
  }
  function stepTextScale(direction) {
    var idx = nearestScaleIdx(currentTextScale());
    var next = Math.max(0, Math.min(TEXT_SCALE_STEPS.length - 1, idx + direction));
    var pct = TEXT_SCALE_STEPS[next];
    document.documentElement.style.fontSize = pct + '%';
    try { localStorage.setItem('otios.textscale', String(pct)); } catch (_) {}
    syncScaleButtons();
  }
  function syncScaleButtons() {
    var idx = nearestScaleIdx(currentTextScale());
    document.querySelectorAll('[data-scale-btn]').forEach(function(btn) {
      var dir = btn.dataset.scaleBtn === 'down' ? -1 : 1;
      btn.disabled = (dir === -1 && idx <= 0) || (dir === 1 && idx >= TEXT_SCALE_STEPS.length - 1);
    });
  }
  syncThemeButtons();
  syncScaleButtons();
  </script>
  <script>
  (function() {
    var base = (typeof OTIOS_BASE !== 'undefined' ? OTIOS_BASE : '');
    var mode = 'flash';
    var cur = null;        // current question {word, definition, pos, choices, answer}
    var answered = false;

    // ── localStorage: shared bookmarks + quiz streak ──
    function getResearch() {
      try { var o = JSON.parse(localStorage.getItem('otios.research') || 'null'); if (o && o.version === 1) return o; } catch (_) {}
      return { version: 1, words: {} };
    }
    function isBookmarked(w) { var e = getResearch().words[w]; return !!(e && e.bookmarked); }
    function toggleBookmark(w) {
      var r = getResearch();
      var prev = r.words[w] || { bookmarked: false, note: '', tags: [] };
      prev.bookmarked = !prev.bookmarked;
      prev.updated_at = new Date().toISOString();
      if (!prev.bookmarked && !prev.note && (!prev.tags || !prev.tags.length)) delete r.words[w];
      else r.words[w] = prev;
      localStorage.setItem('otios.research', JSON.stringify(r));
    }
    function getQuizStats() {
      try { return JSON.parse(localStorage.getItem('otios.quiz') || '{}') || {}; } catch (_) { return {}; }
    }
    function setQuizStats(s) { try { localStorage.setItem('otios.quiz', JSON.stringify(s)); } catch (_) {} }

    function esc(s) { return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
    function maskWord(def, word) {
      if (!def || !word) return def;
      var re = new RegExp(word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
      return def.replace(re, '———');
    }

    function renderScore() {
      var s = getQuizStats();
      var el = document.getElementById('joc-score');
      if (mode === 'quiz') el.textContent = 'serie: ' + (s.streak || 0) + ' · record: ' + (s.best || 0);
      else el.textContent = '';
    }

    function setMode(m) {
      mode = m;
      document.querySelectorAll('.joc-mode').forEach(function(b) { b.classList.toggle('active', b.dataset.mode === m); });
      load();
    }
    window.setMode = setMode;

    function dexLink(w) {
      return '<a class="joc-dexlink" href="https://dexonline.ro/definitie/' + encodeURIComponent(w) + '" target="_blank" rel="noopener">↗ dexonline.ro</a>';
    }

    function load() {
      answered = false;
      var card = document.getElementById('joc-card');
      card.textContent = 'se încarcă…';
      fetch(base + '/api/quiz.php')
        .then(function(r) { return r.json(); })
        .then(function(d) {
          if (d.error) { card.textContent = 'Niciun cuvânt disponibil.'; return; }
          cur = d;
          if (mode === 'flash') renderFlash(); else renderQuiz();
          renderScore();
        })
        .catch(function() { card.textContent = 'Eroare la încărcare.'; });
    }

    function renderFlash() {
      var card = document.getElementById('joc-card');
      var star = isBookmarked(cur.word) ? '★' : '☆';
      card.innerHTML =
        '<div class="joc-prompt-label">card · ghicește sensul</div>' +
        '<div class="joc-word">' + esc(cur.word) + '</div>' +
        (cur.pos ? '<div class="joc-pos">' + esc(cur.pos) + '</div>' : '') +
        '<div id="flash-def" style="display:none">' +
          '<div class="joc-def">' + esc(cur.definition) + '</div>' +
          '<div class="joc-reveal">' + dexLink(cur.word) + '</div>' +
        '</div>' +
        '<div class="joc-actions" id="flash-actions">' +
          '<button class="joc-btn" id="flash-reveal">arată definiția</button>' +
        '</div>';
      document.getElementById('flash-reveal').onclick = function() {
        document.getElementById('flash-def').style.display = '';
        document.getElementById('flash-actions').innerHTML =
          '<button class="joc-btn secondary" id="flash-keep">' + star + ' păstrează</button>' +
          '<button class="joc-btn" id="flash-next">următorul →</button>';
        document.getElementById('flash-keep').onclick = function() {
          toggleBookmark(cur.word);
          this.textContent = (isBookmarked(cur.word) ? '★' : '☆') + ' păstrează';
        };
        document.getElementById('flash-next').onclick = load;
      };
    }

    function renderQuiz() {
      var card = document.getElementById('joc-card');
      var html =
        '<div class="joc-prompt-label">grilă · ce cuvânt are acest sens?</div>' +
        '<div class="joc-def">' + esc(maskWord(cur.definition, cur.word)) + '</div>' +
        '<div class="joc-choices" id="quiz-choices">';
      cur.choices.forEach(function(c) {
        html += '<button class="joc-choice" data-word="' + esc(c) + '">' + esc(c) + '</button>';
      });
      html += '</div><div class="joc-feedback" id="quiz-feedback"></div>' +
              '<div class="joc-actions" id="quiz-actions"></div>';
      card.innerHTML = html;
      card.querySelectorAll('.joc-choice').forEach(function(btn) {
        btn.onclick = function() { answer(btn.dataset.word); };
      });
    }

    function answer(choice) {
      if (answered) return;
      answered = true;
      var correct = choice === cur.answer;
      var s = getQuizStats();
      s.streak = correct ? (s.streak || 0) + 1 : 0;
      s.best = Math.max(s.best || 0, s.streak);
      setQuizStats(s);
      document.querySelectorAll('.joc-choice').forEach(function(btn) {
        btn.disabled = true;
        if (btn.dataset.word === cur.answer) btn.classList.add('correct');
        else if (btn.dataset.word === choice) btn.classList.add('wrong');
      });
      var fb = document.getElementById('quiz-feedback');
      fb.className = 'joc-feedback ' + (correct ? 'ok' : 'no');
      fb.innerHTML = (correct ? '✓ corect! ' : '✗ era „' + esc(cur.answer) + '”. ') + dexLink(cur.answer);
      document.getElementById('quiz-actions').innerHTML = '<button class="joc-btn" id="quiz-next">următoarea →</button>';
      document.getElementById('quiz-next').onclick = load;
      renderScore();
    }

    // Keyboard: space/enter reveals or advances; 1-4 pick a quiz choice
    document.addEventListener('keydown', function(e) {
      if (mode === 'quiz') {
        if (!answered && e.key >= '1' && e.key <= '4') {
          var btns = document.querySelectorAll('.joc-choice');
          var i = parseInt(e.key, 10) - 1;
          if (btns[i]) { e.preventDefault(); btns[i].click(); }
        } else if (answered && (e.key === 'Enter' || e.key === ' ')) {
          var n = document.getElementById('quiz-next'); if (n) { e.preventDefault(); n.click(); }
        }
      } else {
        if (e.key === 'Enter' || e.key === ' ') {
          var rv = document.getElementById('flash-reveal'); var nx = document.getElementById('flash-next');
          if (rv) { e.preventDefault(); rv.click(); } else if (nx) { e.preventDefault(); nx.click(); }
        }
      }
    });

    load();
  })();
  </script>
</body>
</html>
