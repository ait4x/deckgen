// Runnable Python in the slides.
//
// One Pyodide instance for the whole deck, loaded the first time a student presses Run
// or opens the console — never on page load, because that is ~12 MB and a lecture
// theatre full of laptops. Each exercise runs in its own namespace so one drill cannot
// break the next, stdout is captured, and an optional check decides pass or fail.
// Answers and results are kept in localStorage, so a reload mid-class loses nothing.
//
// Injected by deckgen.core.build_html only when the deck has exercises.
(function () {
  'use strict';

  var KEY = 'deckgen.ex.' + location.pathname;   // one bucket per deck
  var pyodide = null, loading = null;
  var consoleLoad = null;   // set by consoleSetup; used by each exercise's ›_ button

  // Pasted code arrives with whatever the source used. CRLF confuses nothing but is
  // noise, and a tab is a real hazard: Python accepts it, mixing it with the four
  // spaces already in the box is an IndentationError the student cannot see.
  function clean(text) { return text.replace(/\r\n?/g, '\n').replace(/\t/g, '    '); }

  // Paste into a textarea at the caret, normalised. Returns false when the browser
  // gave us no clipboard (jsdom, some mobile paths) so the default can stand.
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

  // ── storage ────────────────────────────────────────────────────────────────
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

  // ── the runtime ────────────────────────────────────────────────────────────
  var loadEl = function () { return document.getElementById('pyload'); };

  function banner(text) {
    var el = loadEl();
    if (!el) return;
    if (text) { el.textContent = text; el.classList.add('on'); }
    else { el.classList.remove('on'); }
  }

  var runFn = null, evalFn = null;

  function boot() {
    if (pyodide) return Promise.resolve(pyodide);
    if (loading) return loading;
    banner('Loading Python…');
    loading = new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = window.PYODIDE_URL + 'pyodide.js';
      s.onload = resolve;
      s.onerror = function () { reject(new Error('could not fetch pyodide.js — check the network')); };
      document.head.appendChild(s);
    }).then(function () {
      return loadPyodide({ indexURL: window.PYODIDE_URL });
    }).then(function (py) {
      // the Python half does the exec'ing, the capturing and the checking; see
      // vendor/pyodide-runtime.py. JS never holds a PyProxy except these two callables.
      return fetch('../vendor/pyodide-runtime.py').then(function (r) {
        if (!r.ok) throw new Error('could not fetch pyodide-runtime.py');
        return r.text();
      }).then(function (src) {
        py.runPython(src);
        pyodide = py;
        runFn = py.globals.get('_dg_run');
        evalFn = py.globals.get('_dg_eval');
        banner('');
        return py;
      });
    }).catch(function (err) {
      banner('');
      loading = null;
      throw err;
    });
    return loading;
  }

  // {out, err, ok, msg} — ok is null when the exercise has no check.
  function run(code, check, expect) {
    return boot().then(function () {
      return JSON.parse(runFn(code, check || '', expect === undefined ? null : expect));
    });
  }

  // ── syntax colours ─────────────────────────────────────────────────────────
  // The twin of deckgen/syntax.py: same tokens, same colours, so the editor agrees with
  // the printed panel. Python only here — the editor and the console never hold JS.
  var KW = {};
  ('False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield match case').split(' ').forEach(function (k) { KW[k] = 1; });
  var BI = {};
  ('print len range int float str bool list dict set tuple type input sum min max abs round sorted reversed enumerate zip map filter any all open isinstance repr chr ord id hasattr getattr super object Exception ValueError TypeError KeyError IndexError ZeroDivisionError self').split(' ').forEach(function (k) { BI[k] = 1; });
  var LIGHT = { kw: '#943890', bi: '#146AB5', fn: '#146AB5', str: '#00544C', num: '#ED6D24', com: '#5C6470' };
  var DARK = { kw: '#C9A3CC', bi: '#8CC1F0', fn: '#8CC1F0', str: '#64C2C3', num: '#E38E5D', com: '#B3B7BE' };
  var TOKEN = /(#.*)|([rbfuRBFU]{0,2}(?:"""[\s\S]*?(?:"""|$)|'''[\s\S]*?(?:'''|$)|"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?))|(\b(?:0[xXoObB][0-9a-fA-F_]+|\d[\d_]*(?:\.\d*)?(?:[eE][+-]?\d+)?)|\.\d+)|([A-Za-z_]\w*)|(\s+)|([\s\S])/g;

  function escHtml(t) { return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  // html of `code`, coloured; `theme` is LIGHT or DARK
  function hl(code, theme) {
    var out = '', prev = null, m;
    TOKEN.lastIndex = 0;
    while ((m = TOKEN.exec(code)) !== null) {
      var t = m[0], kind = null;
      if (m[1]) kind = 'com';
      else if (m[2]) kind = 'str';
      else if (m[3]) kind = 'num';
      else if (m[4]) kind = KW[t] ? 'kw' : (prev === 'def' || prev === 'class') ? 'fn' : BI[t] ? 'bi' : null;
      if (m[4]) prev = t; else if (!m[5]) prev = null;
      out += kind ? '<span style="color:' + theme[kind] + '">' + escHtml(t) + '</span>' : escHtml(t);
    }
    return out;
  }

  // keep a <pre> behind a textarea painted with the textarea's text
  function mirror(ta, pre) {
    function paint() { pre.innerHTML = hl(ta.value, LIGHT) + '\n'; }
    ta.addEventListener('input', paint);
    ta.addEventListener('scroll', function () { pre.scrollTop = ta.scrollTop; pre.scrollLeft = ta.scrollLeft; });
    paint();
    return paint;
  }

  // ── exercises ──────────────────────────────────────────────────────────────
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
    var pre = ex.querySelector('.ex-hl');
    var paint = pre ? mirror(ta, pre) : function () {};
    if (saved && saved.ok === true) { ex.classList.add('pass'); if (status) status.textContent = 'passed'; }

    function setStatus(cls, text) {
      ex.classList.remove('pass', 'fail', 'busy');
      if (cls) ex.classList.add(cls);
      if (status) status.textContent = text || '';
    }

    function show(res) {
      out.textContent = '';
      if (res.out) out.appendChild(document.createTextNode(res.out));
      if (res.err) {
        var e = document.createElement('span');
        e.className = 'err'; e.textContent = (res.out ? '\n' : '') + res.err;
        out.appendChild(e);
        setStatus('fail', 'error');
      } else if (res.ok === true) {
        setStatus('pass', 'passed');
        if (res.msg) { var m = document.createElement('span'); m.className = 'msg'; m.textContent = '\n' + res.msg; out.appendChild(m); }
      } else if (res.ok === false) {
        setStatus('fail', 'not yet');
        if (res.msg) { var f = document.createElement('span'); f.className = 'err'; f.textContent = (res.out ? '\n' : '') + res.msg; out.appendChild(f); }
      } else {
        setStatus('', 'ran');
      }
      save(eid, { code: ta.value, ok: res.ok });
    }

    runBtn.addEventListener('click', function () {
      setStatus('busy', 'running…');
      out.textContent = '';
      run(ta.value, ex.dataset.check, ex.dataset.expect)
        .then(show)
        .catch(function (err) {
          out.textContent = String(err.message || err);
          out.className = 'ex-out';
          setStatus('fail', 'error');
        });
    });

    resetBtn.addEventListener('click', function () {
      ta.value = original;
      paint();
      out.textContent = '';
      setStatus('', '');
      save(eid, { code: original, ok: null });
    });

    // ctrl/cmd+enter runs; tab indents instead of leaving the box
    ta.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); runBtn.click(); return; }
      if (e.key === 'Tab') {
        e.preventDefault();
        var st = ta.selectionStart, en = ta.selectionEnd;
        ta.value = ta.value.slice(0, st) + '    ' + ta.value.slice(en);
        ta.selectionStart = ta.selectionEnd = st + 4;
        paint();
      }
    });
    ta.addEventListener('input', function () { save(eid, { code: ta.value }); });
    ta.addEventListener('paste', function (e) {
      if (pasteClean(ta, e)) { paint(); save(eid, { code: ta.value }); }
    });

    // ›_ — put this drill in the console, where they can take it a line at a time
    var sendBtn = ex.querySelector('.ex-send');
    if (sendBtn) sendBtn.addEventListener('click', function () {
      if (consoleLoad) consoleLoad(ta.value);
    });
  }

  // ── the global console ─────────────────────────────────────────────────────
  //
  // The input is a <textarea>, not an <input>. An <input> silently drops newlines on
  // paste, so a student pasting a loop out of a slide got it all on one line and Python
  // answered with a SyntaxError about indentation they could not see.
  function consoleSetup() {
    var box = document.getElementById('pyc');
    if (!box) return;
    var log = box.querySelector('.pyc-log');
    var input = box.querySelector('.pyc-in');
    var openBtn = document.getElementById('pyc-open');
    var clearBtn = document.getElementById('pyc-clear');
    var history = [], hpos = 0;

    function echo(text, cls) {
      var span = document.createElement('span');
      if (cls) span.className = cls;
      if (cls === 'in') {
        // '>>> ' and '... ' stay the prompt colour; the code after them gets its colours
        span.innerHTML = text.split('\n').map(function (l) {
          return escHtml(l.slice(0, 4)) + hl(l.slice(4), DARK);
        }).join('\n') + '\n';
      } else {
        span.textContent = text + '\n';
      }
      log.appendChild(span);
      log.scrollTop = log.scrollHeight;
    }

    // The box grows with what is in it, up to the CSS max-height; counting lines rather
    // than measuring scrollHeight keeps this working in a headless DOM.
    function grow() { input.rows = Math.min(14, input.value.split('\n').length); }

    // Is this entry a finished thought, or is the student mid-block? A REPL's rule: an
    // open bracket, a trailing colon or backslash, or a still-indented last line means
    // more is coming — and a blank line ends it. Quotes and comments are stripped first
    // so a colon or bracket inside them does not count.
    function needsMore(src) {
      if (/\n[ \t]*\n$/.test(src)) return false;
      var s = src.replace(/'[^'\n]*'|"[^"\n]*"/g, "''").replace(/#.*$/gm, '');
      var depth = 0;
      for (var i = 0; i < s.length; i++) {
        var c = s.charAt(i);
        if (c === '(' || c === '[' || c === '{') depth++;
        else if (c === ')' || c === ']' || c === '}') depth--;
      }
      if (depth > 0) return true;
      var lines = s.replace(/[ \t]+$/, '').split('\n');
      var last = lines[lines.length - 1];
      if (/:[ \t]*$/.test(last) || /\\$/.test(last)) return true;
      return lines.length > 1 && /^[ \t]+\S/.test(last);
    }

    // Newline that keeps the current indent, and adds one level after a colon.
    function newline() {
      var st = input.selectionStart, v = input.value;
      var line = v.slice(0, st).split('\n').pop();
      var pad = (line.match(/^[ \t]*/) || [''])[0];
      if (/:[ \t]*$/.test(line)) pad += '    ';
      var ins = '\n' + pad;
      input.value = v.slice(0, st) + ins + v.slice(input.selectionEnd);
      input.selectionStart = input.selectionEnd = st + ins.length;
      grow();
    }

    function submit() {
      var src = input.value.replace(/[ \t\n]+$/, '');
      if (!src.trim()) { input.value = ''; grow(); return; }
      history.push(src); hpos = history.length;
      input.value = ''; grow();
      echo(src.split('\n').map(function (l, i) { return (i ? '... ' : '>>> ') + l; }).join('\n'), 'in');
      boot().then(function () {
        var r = JSON.parse(evalFn(src));
        if (r.out) echo(r.out.replace(/\n$/, ''));
        if (r.err) echo(r.err, 'err');
      }).catch(function (err) { echo(String(err.message || err), 'err'); });
    }

    function toggle(on) {
      var want = on === undefined ? !box.classList.contains('on') : on;
      box.classList.toggle('on', want);
      if (want) { boot().then(function () { input.focus(); }); }
    }

    // What an exercise's ›_ button calls: open, drop the drill in, caret at the end.
    consoleLoad = function (code) {
      toggle(true);
      input.value = clean(code).replace(/[ \t\n]+$/, '');
      grow();
      input.selectionStart = input.selectionEnd = input.value.length;
      input.focus();
      log.scrollTop = log.scrollHeight;
    };

    openBtn && openBtn.addEventListener('click', function () { toggle(); });
    clearBtn && clearBtn.addEventListener('click', function () { log.textContent = ''; });

    input.addEventListener('input', grow);
    input.addEventListener('paste', function (e) { if (pasteClean(input, e)) grow(); });

    input.addEventListener('keydown', function (e) {
      var multi = input.value.indexOf('\n') !== -1;
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (input.value.trim() && needsMore(input.value)) newline(); else submit();
      } else if (e.key === 'Enter') {
        e.preventDefault(); newline();
      } else if (e.key === 'Tab') {
        e.preventDefault();
        var st = input.selectionStart;
        input.value = input.value.slice(0, st) + '    ' + input.value.slice(input.selectionEnd);
        input.selectionStart = input.selectionEnd = st + 4;
      } else if (e.key === 'ArrowUp' && hpos > 0 && (!multi || input.selectionStart === 0)) {
        // while a block is in the box the arrows move the caret; history only takes over
        // at its edges, or when the entry is a single line
        e.preventDefault(); input.value = history[--hpos]; grow();
      } else if (e.key === 'ArrowDown' && (!multi || input.selectionStart === input.value.length)) {
        e.preventDefault(); hpos = Math.min(hpos + 1, history.length);
        input.value = hpos === history.length ? '' : history[hpos];
        grow();
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key !== '`' || e.ctrlKey || e.metaKey || e.altKey) return;
      var t = e.target;
      if (t && (t.tagName === 'INPUT' || (t.tagName === 'TEXTAREA' && t !== input))) return;
      e.preventDefault();
      toggle(t === input ? false : undefined);
    });
  }

  // reveal.js owns the arrow keys and space; while a student is typing, it must not.
  function releaseKeyboard() {
    function typing(el) {
      return el && (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT');
    }
    document.addEventListener('focusin', function (e) {
      if (typing(e.target) && window.Reveal) Reveal.configure({ keyboard: false });
    });
    document.addEventListener('focusout', function (e) {
      if (typing(e.target) && window.Reveal) Reveal.configure({ keyboard: true });
    });
  }

  // Guarded: if this ever ran twice, every handler would double and one click on Run
  // would execute the exercise twice.
  var inited = false;
  function init() {
    if (inited) return;
    inited = true;
    Array.prototype.forEach.call(document.querySelectorAll('.ex'), wire);
    consoleSetup();
    releaseKeyboard();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
