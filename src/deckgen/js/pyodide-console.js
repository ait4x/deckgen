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
      }
    });
    ta.addEventListener('input', function () { save(eid, { code: ta.value }); });
  }

  // ── the global console ─────────────────────────────────────────────────────
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
      span.textContent = text + '\n';
      log.appendChild(span);
      log.scrollTop = log.scrollHeight;
    }

    function toggle(on) {
      var want = on === undefined ? !box.classList.contains('on') : on;
      box.classList.toggle('on', want);
      if (want) { boot().then(function () { input.focus(); }); }
    }

    openBtn && openBtn.addEventListener('click', function () { toggle(); });
    clearBtn && clearBtn.addEventListener('click', function () { log.textContent = ''; });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        var src = input.value;
        if (!src.trim()) return;
        history.push(src); hpos = history.length;
        input.value = '';
        echo('>>> ' + src, 'in');
        boot().then(function () {
          var r = JSON.parse(evalFn(src));
          if (r.out) echo(r.out.replace(/\n$/, ''));
          if (r.err) echo(r.err, 'err');
        }).catch(function (err) { echo(String(err.message || err), 'err'); });
      } else if (e.key === 'ArrowUp' && hpos > 0) {
        e.preventDefault(); input.value = history[--hpos];
      } else if (e.key === 'ArrowDown') {
        e.preventDefault(); hpos = Math.min(hpos + 1, history.length);
        input.value = hpos === history.length ? '' : history[hpos];
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key !== '`' || e.ctrlKey || e.metaKey || e.altKey) return;
      var t = e.target;
      if (t && (t.tagName === 'TEXTAREA' || (t.tagName === 'INPUT' && t !== input))) return;
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
