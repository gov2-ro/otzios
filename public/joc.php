<?php
declare(strict_types=1);
require_once __DIR__ . '/api/_lib.php';
?>
<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
  <title>Oțios — Joc</title>
  <meta property="og:title" content="Oțios — joc">
  <meta property="og:description" content="Învață cuvinte românești uitate prin carduri și un test grilă.">
  <meta property="og:type" content="website">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Mona+Sans:wght@400..700&family=Lora:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="<?= BASE ?>/assets/app.css">
  <style>
    body { display:flex; flex-direction:column; min-height:100vh; }
    .joc-head {
      display:flex; align-items:center; gap:14px; flex-wrap:wrap;
      padding:10px 16px; border-bottom:1px solid var(--border); background:var(--surface);
    }
    .joc-title { font-family:var(--serif); font-weight:600; font-size:17px; color:var(--text); }
    .joc-modes { display:flex; gap:6px; }
    .joc-mode {
      font-family:var(--mono); font-size:12px; padding:4px 12px; border-radius:14px;
      border:1px solid var(--border-2); background:var(--surface); color:var(--text-2); cursor:pointer;
    }
    .joc-mode.active { background:var(--accent); border-color:var(--accent); color:#fff; }
    .joc-score { margin-left:auto; font-family:var(--mono); font-size:12px; color:var(--text-3); }
    .joc-nav a { font-family:var(--mono); font-size:12px; color:var(--text-3); text-decoration:none; margin-left:12px; }
    .joc-nav a:hover { color:var(--text); }
    .joc-main { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:24px 16px; }
    .joc-card {
      width:100%; max-width:580px; background:var(--surface); border:1px solid var(--border-2);
      border-radius:16px; box-shadow:0 8px 30px rgba(0,0,0,.08); padding:30px 28px;
    }
    .joc-prompt-label { font-family:var(--mono); font-size:10px; letter-spacing:.12em; text-transform:uppercase; color:var(--text-3); margin-bottom:10px; }
    .joc-word { font-family:var(--serif); font-weight:600; font-size:2.6em; letter-spacing:-.02em; line-height:1.05; color:var(--text); overflow-wrap:break-word; }
    .joc-def { font-family:var(--serif); font-style:italic; font-size:18px; line-height:1.6; color:var(--text); margin-top:6px; }
    .joc-pos { font-family:var(--mono); font-size:12px; color:var(--text-3); margin-top:8px; }
    .joc-choices { display:flex; flex-direction:column; gap:10px; margin-top:22px; }
    .joc-choice {
      text-align:left; font-family:var(--serif); font-size:18px; padding:12px 16px;
      border:1.5px solid var(--border-2); border-radius:10px; background:var(--surface); color:var(--text); cursor:pointer;
    }
    .joc-choice:hover:not(:disabled) { border-color:var(--accent); }
    .joc-choice.correct { border-color:#2e7d32; background:#e8f5e9; color:#1b5e20; }
    .joc-choice.wrong { border-color:#c0392b; background:#fdecea; color:#a93226; }
    .joc-choice:disabled { cursor:default; }
    .joc-actions { display:flex; gap:12px; margin-top:22px; flex-wrap:wrap; }
    .joc-btn {
      height:42px; padding:0 18px; border-radius:21px; font-family:var(--mono); font-size:13px; font-weight:700; cursor:pointer;
      border:1.5px solid var(--accent); background:var(--accent); color:#fff;
    }
    .joc-btn.secondary { background:var(--surface); color:var(--accent); }
    .joc-btn:active { transform:scale(.98); }
    .joc-feedback { font-family:var(--mono); font-size:13px; margin-top:16px; min-height:18px; }
    .joc-feedback.ok { color:#2e7d32; }
    .joc-feedback.no { color:#c0392b; }
    .joc-reveal { font-family:var(--mono); font-size:12px; color:var(--text-3); margin-top:8px; }
    .joc-dexlink { color:var(--accent); font-size:12px; text-decoration:none; }
    @media (max-width:768px) { .joc-word { font-size:2.1em; } .joc-def { font-size:17px; } }
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
    <span class="joc-nav"><a href="<?= BASE ?>/">← acasă</a><a href="<?= BASE ?>/stats.php">statistici</a></span>
  </div>

  <div class="joc-main">
    <div class="joc-card" id="joc-card">se încarcă…</div>
  </div>

  <script>var OTIOS_BASE = '<?= BASE ?>';</script>
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
