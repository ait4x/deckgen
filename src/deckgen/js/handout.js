// Reading view — the deck, reflowed, for a phone.
//
// reveal.js fits the 1920x1080 canvas to the viewport, so on a 390px screen the body
// text renders at about 7px and the exercise box is too small to type in. Scaling cannot
// fix that; the content has to reflow. build_html emits a second, semantic copy of every
// slide into <main class="handout">, and this switches between the two.
//
// The exercise widgets are NOT duplicated. There is one of each in the deck DOM, and it
// is moved into the reading view and back, so its id, its saved answer and its pass/fail
// state cannot diverge between the views.
(function () {
  'use strict';

  var KEY = 'deckgen.view';
  var body = document.body;
  var openBtn = document.getElementById('ho-open');
  var deckBtn = document.getElementById('ho-deck');
  var main = document.querySelector('.handout');
  if (!main) return;

  // Narrow, or portrait on a touch device: the deck is unreadable there.
  function shouldDefault() {
    var narrow = window.matchMedia('(max-width: 900px)').matches;
    var portrait = window.matchMedia('(orientation: portrait)').matches;
    var touch = window.matchMedia('(hover: none)').matches;
    return narrow || (portrait && touch);
  }

  function homeFor(ex) {
    return document.querySelector('.ex-home[data-for="' + cssEscape(ex.dataset.eid) + '"]');
  }
  function cssEscape(s) {
    return String(s).replace(/["\\]/g, '\\$&');
  }

  // Leave a marker where each exercise lives in the deck, so it can go back.
  function markHomes() {
    Array.prototype.forEach.call(document.querySelectorAll('.reveal .ex'), function (ex) {
      if (ex.previousElementSibling && ex.previousElementSibling.classList.contains('ex-home')) return;
      var home = document.createElement('div');
      home.className = 'ex-home';
      home.hidden = true;
      home.dataset.for = ex.dataset.eid;
      ex.parentNode.insertBefore(home, ex);
    });
  }

  function moveExercises(toHandout) {
    var sel = toHandout ? '.reveal .ex' : '.handout .ex';
    Array.prototype.forEach.call(document.querySelectorAll(sel), function (ex) {
      var slot = toHandout
        ? main.querySelector('.ho-ex[data-for="' + cssEscape(ex.dataset.eid) + '"]')
        : homeFor(ex);
      if (slot && slot.parentNode) slot.parentNode.insertBefore(ex, slot.nextSibling);
    });
  }

  function apply(on, remember) {
    body.classList.toggle('ho', on);
    main.hidden = !on;
    moveExercises(on);
    if (window.Reveal && Reveal.configure) {
      // hidden or not, reveal should not be answering the keyboard in reading view
      Reveal.configure({ keyboard: !on, touch: !on });
      if (!on) setTimeout(function () { Reveal.layout(); }, 0);
    }
    if (remember) {
      try { localStorage.setItem(KEY, on ? 'handout' : 'deck'); } catch (e) { /* private mode */ }
    }
    if (on) window.scrollTo(0, 0);
  }

  function init() {
    markHomes();
    // The PDF is printed from this same page by js/pdf.js. body.ho hides .reveal, so a
    // saved reading-view choice would otherwise produce a PDF of nothing at all.
    if (location.search.indexOf('print-pdf') !== -1) { apply(false, false); return; }
    var saved = null;
    try { saved = localStorage.getItem(KEY); } catch (e) { /* private mode */ }
    apply(saved ? saved === 'handout' : shouldDefault(), false);

    openBtn && openBtn.addEventListener('click', function () { apply(true, true); });
    deckBtn && deckBtn.addEventListener('click', function () { apply(false, true); });

    // Rotating to landscape is a request to see the deck, unless the choice was explicit.
    window.matchMedia('(orientation: portrait)').addEventListener('change', function (e) {
      var explicit = null;
      try { explicit = localStorage.getItem(KEY); } catch (err) { /* private mode */ }
      if (!explicit) apply(e.matches && window.matchMedia('(hover: none)').matches, false);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
