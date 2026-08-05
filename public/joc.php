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
  <meta property="og:description" content="Învață cuvinte românești uitate: ghicește sensul sau cuvântul, în teste grilă.">
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
    /* Game card + word-detail pane: stacked on mobile, side-by-side on desktop. */
    .joc-layout { flex:1; display:flex; flex-direction:column; min-height:0; }
    .joc-main { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:flex-start; padding:24px 16px; }
    .joc-card {
      width:100%; max-width:640px; margin:auto; background:var(--surface); border:1px solid var(--border-2);
      border-radius:16px; box-shadow:0 8px 30px rgba(0,0,0,.08); padding:30px 28px;
    }
    .joc-prompt-label { font-family:var(--mono); font-size:0.625rem; letter-spacing:.12em; text-transform:uppercase; color:var(--text-3); margin-bottom:10px; }
    .joc-word { font-family:var(--serif); font-weight:600; font-size:2.6em; letter-spacing:-.02em; line-height:1.05; color:var(--text); overflow-wrap:break-word; }
    .joc-def { font-family:var(--serif); font-style:italic; font-size:1.125rem; line-height:1.6; color:var(--text); margin-top:6px; }
    .joc-pos { font-family:var(--mono); font-size:0.75rem; color:var(--text-3); margin-top:8px; }
    .joc-choices { display:flex; flex-direction:column; gap:10px; margin-top:22px; }
    .joc-choice {
      display:flex; align-items:flex-start; gap:10px;
      text-align:left; font-family:var(--serif); font-size:1.125rem; padding:12px 16px;
      border:1.5px solid var(--border-2); border-radius:10px; background:var(--surface); color:var(--text); cursor:pointer;
      transition:opacity .15s ease;
    }
    .joc-choice:hover:not(:disabled) { border-color:var(--accent); }
    .joc-choice--def { font-size:1rem; line-height:1.5; padding:12px 14px; }
    /* Verdict styling leans on shape + emoji, not colour alone */
    .joc-choice.correct, .joc-choice.wrong { font-weight:600; }
    .joc-choice.correct::before, .joc-choice.wrong::before {
      flex:none; font-family:var(--mono); font-size:1.125em; line-height:1.35;
    }
    /* inset ring thickens the border without nudging the text */
    .joc-choice.correct {
      border-color:var(--success-border); background:var(--success-bg); color:var(--success);
      box-shadow:inset 0 0 0 2px var(--success-border);
    }
    .joc-choice.correct::before { content:'✅'; }
    .joc-choice.wrong {
      border-color:var(--error-border); background:var(--error-bg); color:var(--error);
      box-shadow:inset 0 0 0 2px var(--error-border);
      text-decoration:line-through; text-decoration-thickness:1px;
      text-decoration-color:color-mix(in srgb, var(--error) 55%, transparent);
    }
    .joc-choice.wrong::before { content:'❌'; text-decoration:none; }
    /* Once answered, fade the choices nobody marked so the two verdicts pop */
    .joc-choice:disabled { cursor:default; }
    .joc-choice:disabled:not(.correct):not(.wrong) { opacity:.4; }
    .joc-actions { display:flex; gap:12px; margin-top:22px; flex-wrap:wrap; }
    .joc-btn {
      height:42px; padding:0 18px; border-radius:21px; font-family:var(--mono); font-size:0.8125rem; font-weight:700; cursor:pointer;
      border:1.5px solid var(--accent); background:var(--accent); color:var(--on-accent);
    }
    .joc-btn.secondary { background:var(--surface); color:var(--accent); }
    .joc-btn:active { transform:scale(.98); }
    .joc-feedback { font-family:var(--mono); font-size:0.875rem; font-weight:600; margin-top:16px; min-height:18px; }
    .joc-feedback.ok { color:var(--success); }
    .joc-feedback.no { color:var(--error); }
    .joc-reveal { font-family:var(--mono); font-size:0.75rem; color:var(--text-3); margin-top:8px; }
    .joc-dexlink { color:var(--accent); font-size:0.75rem; text-decoration:none; }

    /* Always-visible word-detail pane (reuses .fp-* content styling from app.css). */
    #panel-pane {
      border-top:1px solid var(--border);
      background:var(--surface);
    }
    .panel-placeholder { padding:20px 16px; color:var(--text-3); font-family:var(--mono); font-size:0.8125rem; text-align:center; }
    #panel-pane .fp-close { display:none; }   /* nothing to close — the pane is always shown */

    /* Read-only comparison card for a wrong 'grilă' guess — the word itself gets no
       bookmark/tags/notes (that would mean a second widget sharing element ids). */
    .panel-compare { padding:14px 16px; border-top:1px dashed var(--border); }
    .panel-compare-label { font-family:var(--mono); font-size:0.6875rem; color:var(--text-3); margin-bottom:4px; }
    .panel-compare-def { font-family:var(--serif); font-size:0.9375rem; line-height:1.5; color:var(--text-2); }

    @media (max-width:768px) { .joc-word { font-size:2.1em; } .joc-def { font-size:1.0625rem; } .joc-choice--def { font-size:0.9375rem; } }

    @media (min-width:900px) {
      .joc-layout { flex-direction:row; align-items:stretch; }
      .joc-main { flex:1; min-width:0; }
      #panel-pane {
        width:380px; flex-shrink:0; border-top:none; border-left:1px solid var(--border);
        overflow-y:auto;
      }
    }
  </style>
</head>
<body>
  <div class="joc-head">
    <span class="joc-title">Oțios · joc</span>
    <div class="joc-modes">
      <button type="button" class="joc-mode active" data-mode="sense" onclick="setMode('sense')">🔤 sensuri</button>
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
    <span class="joc-nav"><a href="#" onclick="openBoard();return false;">🏆 clasament</a><a href="<?= BASE ?>/">← acasă</a><a href="<?= BASE ?>/stats.php">statistici</a></span>
  </div>

  <div class="joc-layout">
    <div class="joc-main">
      <div class="joc-card" id="joc-card">se încarcă…</div>
    </div>
    <div id="panel-pane" class="word-detail-panel">
      <p class="panel-placeholder">se încarcă…</p>
    </div>
  </div>

  <div id="board-overlay" style="display:none" onclick="if(event.target===this)closeBoard()">
    <div id="board-modal">
      <div class="board-head">
        <span id="board-title">Clasament · cele mai lungi serii</span>
        <button class="board-x" onclick="closeBoard()">✕</button>
      </div>
      <div id="board-body"><p class="board-empty">se încarcă…</p></div>
    </div>
  </div>

  <script>var OTIOS_BASE = '<?= BASE ?>';</script>
  <script src="<?= BASE ?>/assets/store.js"></script>
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
    // 'sense' (word → pick the meaning) is the default; 'flash' is retained but has
    // no button — reach it with ?mode=flash.
    var MODES = { sense: 1, quiz: 1, flash: 1 };
    var mode = (new URLSearchParams(location.search).get('mode') || '');
    if (!MODES[mode]) mode = 'sense';
    // Current question. Options are opaque {id, text}: the server does not say which
    // one is correct, so grading goes through /api/game.php.
    var cur = null;
    var answered = false;
    var askedAt = 0;       // for the per-answer response time recorded server-side

    // ── Bookmarks (shared store in store.js, synced to the server) + per-mode score ──
    function isBookmarked(w) { return !!getWord(w).bookmarked; }
    function toggleBookmark(w) { updateWord(w, { bookmarked: !isBookmarked(w) }); }
    // Local mirror of the server's per-mode correct/total, keyed by mode, so the score
    // is on screen immediately on load instead of waiting for a round trip. Sense and
    // quiz are tracked separately — they test different skills, so a streak or tally
    // built up in one shouldn't bleed into the other's readout. The server remains
    // authoritative.
    function getQuizStats(m) {
      try {
        var all = JSON.parse(localStorage.getItem('otios.quiz') || '{}') || {};
        return all[m] || { correct: 0, total: 0 };
      } catch (_) { return { correct: 0, total: 0 }; }
    }
    function setQuizStats(m, s) {
      try {
        var all = JSON.parse(localStorage.getItem('otios.quiz') || '{}') || {};
        all[m] = s;
        localStorage.setItem('otios.quiz', JSON.stringify(all));
      } catch (_) {}
    }

    function esc(s) { return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

    function renderScore() {
      var el = document.getElementById('joc-score');
      if (mode === 'quiz' || mode === 'sense') {
        var s = getQuizStats(mode);
        var total = s.total || 0, correct = s.correct || 0;
        el.textContent = 'corecte: ' + correct + ' · ratate: ' + (total - correct);
      } else {
        el.textContent = '';
      }
    }

    function syncModeButtons() {
      document.querySelectorAll('.joc-mode').forEach(function(b) { b.classList.toggle('active', b.dataset.mode === mode); });
    }
    function setMode(m) {
      mode = m;
      syncModeButtons();
      load();
    }
    window.setMode = setMode;

    function dexLink(w) {
      return '<a class="joc-dexlink" href="https://dexonline.ro/definitie/' + encodeURIComponent(w) + '" target="_blank" rel="noopener">↗ dexonline.ro</a>';
    }

    // ── Word-detail pane (full widget from the main page — tags, dictionaries,
    // fav/ascunde/lol/meh quick-tags — reused as-is via store.js's hydrateDetail/handlers) ──
    // Always visible rather than opened on demand. In `quiz` mode the word is
    // deliberately withheld from the client until grading, so the pane shows a
    // placeholder until showVerdict() reveals it; every other mode knows the word
    // immediately and can populate the pane right away.
    function showDetailPlaceholder(text) {
      document.getElementById('panel-pane').innerHTML = '<p class="panel-placeholder">' + esc(text) + '</p>';
    }
    // hideDefinition: in 'sense' mode the raw definition is the very thing being
    // guessed among the four choices, so showing it in the pane would just hand the
    // answer over — the rest of the widget (dictionaries, tags, notes) is still useful.
    function showWordDetail(word, hideDefinition) {
      if (!word) return;
      var pane = document.getElementById('panel-pane');
      pane.innerHTML = '<p class="panel-placeholder">se încarcă…</p>';
      fetch(base + '/api/word.php?word=' + encodeURIComponent(word), { credentials: 'same-origin' })
        .then(function(r) { return r.text(); })
        .then(function(html) {
          pane.innerHTML = html;
          if (hideDefinition) {
            var def = pane.querySelector('.definition-text, .fp-nodef');
            if (def) def.style.display = 'none';
          }
          hydrateDetail(pane);
        })
        .catch(function() { pane.innerHTML = '<p class="panel-placeholder">Nu am putut încărca detaliile.</p>'; });
    }
    // Pull just the title + definition out of a word.php fragment, for the read-only
    // "you picked X" comparison card — the wrong choice gets no bookmark/tags/notes of
    // its own (that would mean two widgets sharing the same element ids), just enough
    // to see why it wasn't the answer.
    function extractWordSummary(html) {
      var tmp = document.createElement('div');
      tmp.innerHTML = html;
      var title = tmp.querySelector('.fp-title');
      var def   = tmp.querySelector('.definition-text');
      return { word: title ? title.textContent : '', definition: def ? def.textContent : '(fără definiție locală)' };
    }
    // Wrong 'quiz' answer: show the correct word's full widget plus a lightweight
    // comparison card for the word the player actually picked, so both definitions are
    // visible side by side.
    function showWordDetailCompare(correctWord, wrongWord) {
      var pane = document.getElementById('panel-pane');
      pane.innerHTML = '<p class="panel-placeholder">se încarcă…</p>';
      Promise.all([
        fetch(base + '/api/word.php?word=' + encodeURIComponent(correctWord), { credentials: 'same-origin' }).then(function(r) { return r.text(); }),
        fetch(base + '/api/word.php?word=' + encodeURIComponent(wrongWord), { credentials: 'same-origin' }).then(function(r) { return r.text(); })
      ]).then(function(results) {
        var wrongSummary = extractWordSummary(results[1]);
        pane.innerHTML = results[0] +
          '<div class="panel-compare">' +
            '<div class="panel-compare-label">ai ales „' + esc(wrongSummary.word) + '”</div>' +
            '<div class="panel-compare-def">' + esc(wrongSummary.definition) + '</div>' +
          '</div>';
        hydrateDetail(pane);
      }).catch(function() { pane.innerHTML = '<p class="panel-placeholder">Nu am putut încărca detaliile.</p>'; });
    }
    // detail.php's markup still carries a "✕" close button (hidden here via CSS,
    // since there's nothing to close) that calls this by name — keep it a harmless
    // no-op rather than leaving the name undefined.
    window.closePanel = function() {};

    function load() {
      answered = false;
      askedAt = 0;
      var card = document.getElementById('joc-card');
      card.textContent = 'se încarcă…';
      fetch(base + '/api/quiz.php?mode=' + encodeURIComponent(mode), { credentials: 'same-origin' })
        .then(function(r) { return r.json(); })
        .then(function(d) {
          if (d.error) { card.textContent = 'Niciun cuvânt disponibil.'; return; }
          cur = d;
          askedAt = Date.now();
          if (mode === 'sense') renderSense();
          else if (mode === 'quiz') renderQuiz();
          else renderFlash();
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
      showWordDetail(cur.word);
    }

    // Both graded modes render the same shape: a prompt plus four opaque choices,
    // keyed by the server's option id.
    function renderChoices(label, promptHtml, defClass) {
      var card = document.getElementById('joc-card');
      var html =
        '<div class="joc-prompt-label">' + label + '</div>' + promptHtml +
        '<div class="joc-choices" id="quiz-choices">';
      (cur.options || []).forEach(function(o) {
        html += '<button class="joc-choice' + (defClass ? ' joc-choice--def' : '') +
                '" data-id="' + o.id + '">' + esc(o.text) + '</button>';
      });
      html += '</div><div class="joc-feedback" id="quiz-feedback"></div>' +
              '<div class="joc-actions" id="quiz-actions"></div>';
      card.innerHTML = html;
      card.querySelectorAll('.joc-choice').forEach(function(btn) {
        btn.onclick = function() { answer(parseInt(btn.dataset.id, 10)); };
      });
    }

    // One word, four candidate definitions. The word is known up front, so the
    // detail pane can populate immediately — but the definition itself is the puzzle,
    // so it stays hidden in the pane until the round is decided some other way.
    function renderSense() {
      renderChoices('sensuri · ce înseamnă acest cuvânt?',
        '<div class="joc-word">' + esc(cur.word) + '</div>' +
        (cur.pos ? '<div class="joc-pos">' + esc(cur.pos) + '</div>' : ''),
        true);
      showWordDetail(cur.word, true);
    }

    // One definition, four candidate words. The definition arrives already masked, so
    // the target word — and its detail pane — stay unknown until showVerdict() grades
    // the answer.
    function renderQuiz() {
      renderChoices('grilă · ce cuvânt are acest sens?',
        '<div class="joc-def">' + esc(cur.definition) + '</div>', false);
      showDetailPlaceholder('răspunde ca să vezi detaliile cuvântului');
    }

    function answer(choiceId) {
      if (answered || !cur || !cur.qid) return;
      answered = true;

      var buttons = document.querySelectorAll('.joc-choice');
      buttons.forEach(function(b) { b.disabled = true; });
      var fb = document.getElementById('quiz-feedback');
      fb.className = 'joc-feedback';
      fb.textContent = 'se verifică…';

      fetch(base + '/api/game.php', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ qid: cur.qid, choice_id: choiceId, ms: askedAt ? Date.now() - askedAt : null })
      })
        .then(function(r) { return r.json(); })
        .then(function(d) {
          if (d.error) throw new Error(d.error);
          showVerdict(d, choiceId);
        })
        .catch(function() {
          // Every question already needs the network, so a failure here is the same
          // outage that would have blocked the next question anyway. Let them retry.
          answered = false;
          buttons.forEach(function(b) { b.disabled = false; });
          fb.className = 'joc-feedback no';
          fb.textContent = '⚠ nu am putut verifica răspunsul — încearcă din nou.';
        });
    }

    function showVerdict(d, choiceId) {
      document.querySelectorAll('.joc-choice').forEach(function(btn) {
        var id = parseInt(btn.dataset.id, 10);
        if (id === d.correct_id) btn.classList.add('correct');
        else if (id === choiceId) btn.classList.add('wrong');
      });

      var fb = document.getElementById('quiz-feedback');
      fb.className = 'joc-feedback ' + (d.correct ? 'ok' : 'no');
      // In 'sense' mode the word is already on screen — point at the highlighted
      // definition instead of naming the word again.
      var miss = mode === 'sense' ? '❌ greșit — sensul corect e cel bifat. '
                                  : '❌ greșit — era „' + esc(d.answer) + '”. ';
      fb.innerHTML = (d.correct ? '✅ corect! ' : miss) + dexLink(d.answer);

      document.getElementById('quiz-actions').innerHTML = '<button class="joc-btn" id="quiz-next">următoarea →</button>';
      document.getElementById('quiz-next').onclick = load;

      // 'sense' already populated the detail pane before answering (the word was
      // never secret there); 'quiz' only learns the word now, from the grading
      // response, so the pane can only be filled in at this point. On a wrong guess,
      // compare both: the correct word's full widget plus what the player picked.
      if (mode === 'quiz') {
        if (d.correct) {
          showWordDetail(d.answer);
        } else {
          var chosen = (cur.options || []).find(function(o) { return o.id === choiceId; });
          if (chosen) showWordDetailCompare(d.answer, chosen.text);
          else showWordDetail(d.answer);
        }
      }

      setQuizStats(mode, { correct: d.total_correct, total: d.total });
      renderScore();
    }

    // Keyboard: space/enter reveals or advances; 1-4 pick a quiz choice
    document.addEventListener('keydown', function(e) {
      if (e.metaKey || e.ctrlKey || e.altKey) return;   // leave browser shortcuts alone
      if (mode === 'quiz' || mode === 'sense') {
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

    // ── Leaderboard ──
    // Nothing here is client-asserted: game.php recomputes streaks server-side, so a
    // rank reflects answers the server actually graded.
    var BOARD_MODE_LABEL = { sense: 'sensuri', quiz: 'grilă' };
    function openBoard() {
      // flash isn't graded and has no leaderboard of its own — fall back to sense,
      // matching the clamp leaderboard.php already applies server-side.
      var boardMode = BOARD_MODE_LABEL[mode] ? mode : 'sense';
      document.getElementById('board-overlay').style.display = 'flex';
      document.getElementById('board-title').textContent = 'Clasament · ' + BOARD_MODE_LABEL[boardMode] + ' · cele mai lungi serii';
      var body = document.getElementById('board-body');
      body.innerHTML = '<p class="board-empty">se încarcă…</p>';

      fetch(base + '/api/leaderboard.php?mode=' + encodeURIComponent(boardMode), { credentials: 'same-origin' })
        .then(function(r) { return r.json(); })
        .then(function(d) {
          var rows = d.entries || [];
          var html = '';

          if (!rows.length) {
            html += '<p class="board-empty">Niciun scor încă. Fii primul!</p>';
          } else {
            html += '<table class="board-table"><tbody>';
            rows.forEach(function(e) {
              html += '<tr' + (e.you ? ' class="board-you"' : '') + '>' +
                      '<td class="board-rank">' + e.rank + '</td>' +
                      '<td class="board-name"></td>' +
                      '<td class="board-best">' + e.best + '</td>' +
                      '<td class="board-tot">' + e.correct + '/' + e.total + '</td></tr>';
            });
            html += '</tbody></table>';
          }

          // Not on the board yet: show where they stand and offer the one opt-in.
          if (d.you && d.you.listed === false) {
            html += '<div class="board-self">Seria ta cea mai lungă: <strong>' + d.you.best + '</strong>' +
                    ' · locul ' + d.you.rank + ' dacă te înscrii.' +
                    '<button class="joc-btn secondary" id="board-join">apari în clasament</button></div>';
          }
          body.innerHTML = html;

          // Nicknames are user input — assigned as text, never built into the HTML.
          var names = body.querySelectorAll('.board-name');
          rows.forEach(function(e, i) { if (names[i]) names[i].textContent = e.nickname; });

          var join = document.getElementById('board-join');
          if (join) join.onclick = joinBoard;
        })
        .catch(function() {
          document.getElementById('board-body').innerHTML =
            '<p class="board-empty">Nu am putut încărca clasamentul.</p>';
        });
    }

    function closeBoard() { document.getElementById('board-overlay').style.display = 'none'; }

    function joinBoard() {
      var name = prompt('Sub ce nume vrei să apari?');
      if (!name || name.trim().length < 2) return;
      fetch(base + '/api/profile.php', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nickname: name.trim() })
      })
        .then(function(r) { return r.json(); })
        .then(function(d) { if (d.nickname) openBoard(); });
    }

    window.openBoard = openBoard;
    window.closeBoard = closeBoard;

    syncModeButtons();
    load();

    // Reconcile the local score mirror with the server's, so the tally survives a
    // cleared browser the same way bookmarks now do.
    if (typeof otiosMe === 'function') {
      otiosMe().then(function(me) {
        if (!me || !me.stats) return;
        ['sense', 'quiz'].forEach(function(m) {
          if (me.stats[m]) setQuizStats(m, me.stats[m]);
        });
        renderScore();
      });
    }
  })();
  </script>
</body>
</html>
