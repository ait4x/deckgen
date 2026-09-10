// The code of a live sketch, editable in the deck.
//
// The editor half is pyodide-console.js's: a coloured <pre> under a transparent textarea,
// Run, Reset, the code kept in localStorage per deck. The running is done by the sketch's
// own page (SKETCH_TMPL in deckgen.core), which is handed the code by postMessage and
// answers ran or error — so the deck never evaluates a line of JavaScript itself, and a
// sketch that throws every frame cannot take the slides down with it.
//
// Injected by deckgen.core.build_html only when the deck has an editable sketch.
(function () {
  'use strict';

  var KEY = 'deckgen.play.' + location.pathname;   // one bucket per deck

  function store() {
    try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { return {}; }
  }
  function save(eid, patch) {
    try {
      var all = store();
      all[eid] = Object.assign(all[eid] || {}, patch);
      localStorage.setItem(KEY, JSON.stringify(all));
    } catch (e) { /* private mode, quota — not worth interrupting a class for */ }
  }

  // Pasted code arrives with whatever the source used; tabs become the two spaces the
  // sketches are written with, so the box never mixes the two.
  function clean(text) { return text.replace(/\r\n?/g, '\n').replace(/\t/g, '  '); }
  function pasteClean(el, e) {
    var cd = e.clipboardData || window.clipboardData;
    if (!cd) return false;
    var text = clean(cd.getData('text') || '');
    if (!text) return false;
    e.preventDefault();
    var st = el.selectionStart, en = el.selectionEnd;
    el.value = el.value.slice(0, st) + text + el.value.slice(en);
    el.selectionStart = el.selectionEnd = st + text.length;
    return true;
  }

  // ── syntax colours: the JavaScript rules of deckgen/syntax.py, token for token ───────
  var KW = {};
  ('function let const var for while do if else return new class this true false null undefined of in break continue switch case default typeof instanceof async await import export from try catch finally throw delete void yield extends static get set').split(' ').forEach(function (k) { KW[k] = 1; });
  var BI = {};
  ('createCanvas background fill noFill stroke noStroke strokeWeight rect square circle ellipse line point triangle arc beginShape endShape vertex random randomSeed noise noiseSeed push pop translate rotate scale noLoop loop redraw frameRate map constrain lerp dist floor ceil round abs sin cos atan2 sqrt min max width height mouseX mouseY pmouseX pmouseY mouseIsPressed frameCount PI TWO_PI HALF_PI text textSize textAlign color colorMode rectMode ellipseMode console Math document window setup draw keyPressed mousePressed mouseMoved mouseDragged key keyCode loadImage image createVector millis deltaTime createSlider createButton textFont strokeCap nf radians degrees pow exp log tan atan int str resizeCanvas windowWidth windowHeight keyIsDown lerpColor quad').split(' ').forEach(function (k) { BI[k] = 1; });
  var LIGHT = { kw: '#943890', bi: '#146AB5', fn: '#146AB5', str: '#00544C', num: '#ED6D24', com: '#5C6470' };
  var NUM = /^(?:0[xXoObB][0-9a-fA-F_]+|\d[\d_]*(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+)/;
  var NAME = /^[A-Za-z_$][\w$]*/;

  function escHtml(t) { return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  // html of `code`, coloured
  function hl(code) {
    var out = [], inBlock = false;   // a /* */ comment carried across lines
    var lines = code.split('\n');
    for (var li = 0; li < lines.length; li++) {
      var line = lines[li], i = 0, n = line.length, html = '', prev = null, m, j;
      var span = function (kind, t) { html += kind === 'txt' ? escHtml(t) : '<span style="color:' + LIGHT[kind] + '">' + escHtml(t) + '</span>'; };
      if (inBlock) {
        j = line.indexOf('*/');
        if (j < 0) { span('com', line); out.push(html); continue; }
        span('com', line.slice(0, j + 2)); i = j + 2; inBlock = false;
      }
      while (i < n) {
        var c = line.charAt(i), rest = line.slice(i);
        if (rest.indexOf('//') === 0) { span('com', rest); break; }
        if (rest.indexOf('/*') === 0) {
          j = line.indexOf('*/', i + 2);
          if (j < 0) { span('com', rest); inBlock = true; break; }
          span('com', line.slice(i, j + 2)); i = j + 2; prev = null; continue;
        }
        if (c === '"' || c === "'" || c === '`') {
          j = i + 1;
          while (j < n && line.charAt(j) !== c) j += line.charAt(j) === '\\' ? 2 : 1;
          span('str', line.slice(i, Math.min(j + 1, n))); i = Math.min(j + 1, n); prev = null; continue;
        }
        m = NUM.exec(rest);
        if (m && (i === 0 || !/\w/.test(line.charAt(i - 1)))) { span('num', m[0]); i += m[0].length; prev = null; continue; }
        m = NAME.exec(rest);
        if (m) {
          var w = m[0], kind = KW[w] ? 'kw' : (prev === 'function' || prev === 'class') ? 'fn' : BI[w] ? 'bi' : 'txt';
          span(kind, w); prev = w; i += w.length; continue;
        }
        m = /^[ \t]+/.exec(rest);
        if (m) { span('txt', m[0]); i += m[0].length; continue; }
        span('txt', c); prev = null; i += 1;
      }
      out.push(html);
    }
    return out.join('\n');
  }

  // keep a <pre> behind a textarea painted with the textarea's text
  function mirror(ta, pre) {
    function paint() { pre.innerHTML = hl(ta.value) + '\n'; }
    ta.addEventListener('input', paint);
    ta.addEventListener('scroll', function () { pre.scrollTop = ta.scrollTop; pre.scrollLeft = ta.scrollLeft; });
    paint();
    return paint;
  }

  // ── the editors ──────────────────────────────────────────────────────────────────
  var boxes = [];

  // the frame of this editor's sketch: on the same slide, by the page it loads
  function frameOf(ex) {
    var section = ex.closest('section');
    return section && section.querySelector('iframe[data-src="sketches/' + ex.dataset.sketch + '.html"]');
  }

  function wire(ex) {
    var eid = ex.dataset.eid;
    var ta = ex.querySelector('.ex-code');
    var out = ex.querySelector('.ex-out');
    var status = ex.querySelector('.ex-status');
    var runBtn = ex.querySelector('.ex-run');
    var resetBtn = ex.querySelector('.ex-reset');
    var original = ta.value;
    var saved = store()[eid];
    if (saved && typeof saved.code === 'string') ta.value = saved.code;
    var paint = mirror(ta, ex.querySelector('.ex-hl'));

    function setStatus(cls, text) {
      ex.classList.remove('fail', 'busy');
      if (cls) ex.classList.add(cls);
      if (status) status.textContent = text || '';
    }
    function send(code) {
      var f = frameOf(ex);
      if (!f || !f.contentWindow) { setStatus('fail', 'no sketch on this slide'); return; }
      out.textContent = '';
      setStatus('busy', 'running…');
      f.contentWindow.postMessage({ deckgen: 'run', code: code }, '*');
    }

    boxes.push({
      ex: ex,
      ready: function () { if (ta.value !== original) send(ta.value); },      // a reload, or a return to the slide: the edited sketch again
      ran: function () { setStatus('', ta.value === original ? '' : 'ran'); },
      error: function (msg) { out.textContent = msg; setStatus('fail', 'error'); },
    });

    runBtn.addEventListener('click', function () { save(eid, { code: ta.value }); send(ta.value); });
    resetBtn.addEventListener('click', function () {
      ta.value = original;
      paint();
      save(eid, { code: original });
      send(original);
    });

    // ctrl/cmd+enter runs; tab indents instead of leaving the box
    ta.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); runBtn.click(); return; }
      if (e.key === 'Tab') {
        e.preventDefault();
        var st = ta.selectionStart, en = ta.selectionEnd;
        ta.value = ta.value.slice(0, st) + '  ' + ta.value.slice(en);
        ta.selectionStart = ta.selectionEnd = st + 2;
        paint();
      }
    });
    ta.addEventListener('input', function () { save(eid, { code: ta.value }); });
    ta.addEventListener('paste', function (e) {
      if (pasteClean(ta, e)) { paint(); save(eid, { code: ta.value }); }
    });
  }

  // what the sketch pages say: ready (loaded), ran, error — matched to the editor whose frame spoke
  addEventListener('message', function (e) {
    var d = e.data;
    if (!d || !d.deckgen || (d.deckgen !== 'ready' && d.deckgen !== 'ran' && d.deckgen !== 'error')) return;
    for (var i = 0; i < boxes.length; i++) {
      var f = frameOf(boxes[i].ex);
      if (!f || f.contentWindow !== e.source) continue;
      if (d.deckgen === 'ready') boxes[i].ready();
      else if (d.deckgen === 'ran') boxes[i].ran();
      else boxes[i].error(String(d.message || 'error'));
    }
  });

  // reveal.js owns the arrow keys and space; while a student is typing, it must not.
  function releaseKeyboard() {
    function typing(el) { return el && el.tagName === 'TEXTAREA' && el.classList.contains('ex-code'); }
    document.addEventListener('focusin', function (e) {
      if (typing(e.target) && window.Reveal) Reveal.configure({ keyboard: false });
    });
    document.addEventListener('focusout', function (e) {
      if (typing(e.target) && window.Reveal) Reveal.configure({ keyboard: true });
    });
  }

  var inited = false;
  function init() {
    if (inited) return;
    inited = true;
    Array.prototype.forEach.call(document.querySelectorAll('.ex-js'), wire);
    releaseKeyboard();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
