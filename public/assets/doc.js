// Sticky table of contents for the document pages (despre.php, metodologie.html).
//
// Two modes, because the two pages arrive differently:
//
//   * metodologie.html already ships a hand-written <ol> of links to section ids. That
//     ordering is editorial — it abbreviates „Faza 2 — Validare diacronică" to
//     „Faza 2" — so it is left exactly as written and only gets scroll-spy.
//   * despre.php has no list, so one is built from its headings.
//
// Either way the markup contract is the same: a container with `data-toc` pointing at the
// selector for the content it indexes.

(function () {
  'use strict';

  function slugify(text) {
    return text.toLowerCase()
      .replace(/[ăâ]/g, 'a').replace(/[îi]/g, 'i').replace(/ș/g, 's').replace(/ț/g, 't')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'sec';
  }

  function init(toc) {
    var body = document.querySelector(toc.getAttribute('data-toc'));
    if (!body) return;

    var links = Array.prototype.slice.call(toc.querySelectorAll('a[href^="#"]'));

    // No hand-written list → build one from the headings.
    if (!links.length) {
      var heads = Array.prototype.slice.call(body.querySelectorAll('h2, h3'));
      if (!heads.length) return;
      var ol = document.createElement('ol');
      heads.forEach(function (h) {
        if (!h.id) {
          var base = slugify(h.textContent), id = base, n = 2;
          while (document.getElementById(id)) { id = base + '-' + n++; }
          h.id = id;
        }
        var li = document.createElement('li');
        var a  = document.createElement('a');
        a.href = '#' + h.id;
        a.textContent = h.textContent.trim();
        if (h.tagName === 'H3') a.className = 'is-sub';
        li.appendChild(a); ol.appendChild(li);
      });
      toc.appendChild(ol);
      links = Array.prototype.slice.call(toc.querySelectorAll('a[href^="#"]'));
    }

    // ── Scroll-spy ──────────────────────────────────────────────────────────────
    //
    // Tracks the *last* target whose top has passed the reading line, rather than
    // whichever one is intersecting. With sections of wildly different lengths — this
    // page has one of two paragraphs and one of forty — "is visible" marks several at
    // once and flickers between them on every scroll tick.
    var targets = links.map(function (a) {
      var el = document.getElementById(decodeURIComponent(a.getAttribute('href').slice(1)));
      return el ? { link: a, el: el } : null;
    }).filter(Boolean);
    if (!targets.length) return;

    var current = null;
    function spy() {
      var line = 120;  // just under the fixed brand bar
      var found = targets[0];
      for (var i = 0; i < targets.length; i++) {
        if (targets[i].el.getBoundingClientRect().top <= line) found = targets[i];
      }
      // At the very bottom the last section may never cross the line — if the page is
      // scrolled to the end, the last entry is the honest answer.
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) {
        found = targets[targets.length - 1];
      }
      if (found === current) return;
      if (current) current.link.classList.remove('is-current');
      found.link.classList.add('is-current');
      current = found;
    }

    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () { spy(); ticking = false; });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    spy();

    // Clicking an entry inside the mobile disclosure closes it — leaving it open would
    // push the section the reader just asked for back off the screen.
    var details = toc.closest('details');
    if (details) {
      toc.addEventListener('click', function (e) {
        if (e.target.closest('a')) details.open = false;
      });
    }
  }

  function boot() {
    document.querySelectorAll('[data-toc]').forEach(init);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else { boot(); }
})();
