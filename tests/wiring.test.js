// Test the DOM half of the runtime with a stubbed Pyodide. The Python half is already
// verified against the real interpreter; this covers the wiring: status classes, output
// rendering, localStorage, reset, ctrl+enter, console echo, and reveal keyboard release.
const { JSDOM } = require('jsdom');
const fs = require('fs');

const path = require('path');
const { execFileSync } = require('child_process');

// The fixture in tests/fixture/ is built here rather than pointed at, so the suite is
// self-contained and the exercise ids below are guaranteed to be the ones it asserts on.
const FIX = path.join(__dirname, 'fixture');
try {
  execFileSync('deckgen', ['build', '--site', '--no-pdf'], { cwd: FIX, stdio: 'pipe' });
} catch (e) {
  console.error('could not build the fixture — is deckgen on PATH?\n' + (e.stderr || e.message));
  process.exit(1);
}
const html = fs.readFileSync(path.join(FIX, '_site/t/index.html'), 'utf8');
const js = fs.readFileSync(path.join(FIX, '_site/vendor/pyodide-console.js'), 'utf8');

const dom = new JSDOM(html, { url: 'http://x/t/', runScripts: 'outside-only', pretendToBeVisual: true });
const w = dom.window;

// canned Python: mirrors what _dg_run/_dg_eval actually returned in the interpreter test
const fakePy = {
  runPython() {},
  globals: { get(n) {
    if (n === '_dg_run') return (code, check, expect) => {
      if (code.includes('int(a) + int(b)')) return JSON.stringify({out:'12\n',err:'',ok:true,msg:''});
      if (code.includes('a + b'))           return JSON.stringify({out:'66\n',err:'',ok:false,msg:'Expected:\n12'});
      if (code.includes('a.copy()'))        return JSON.stringify({out:'[1, 2, 3]\n',err:'',ok:true,msg:''});
      if (code.includes('b = a'))           return JSON.stringify({out:'[1, 2, 3, 4]\n',err:'',ok:false,msg:'a still has the 4'});
      if (code.includes('1/0'))             return JSON.stringify({out:'',err:'ZeroDivisionError: division by zero',ok:null,msg:''});
      return JSON.stringify({out:'',err:'',ok:null,msg:''});
    };
    if (n === '_dg_eval') return (src) => {
      if (src === 'x * 2') return JSON.stringify({out:'42\n',err:''});
      if (src.includes('total += r')) return JSON.stringify({out:'6\n',err:''});
      return JSON.stringify({out:'',err:''});
    };
  }},
};
w.PYODIDE_URL = 'http://x/pyodide/';  // the inline script that sets this does not run under runScripts:'outside-only'
w.loadPyodide = () => Promise.resolve(fakePy);
w.fetch = () => Promise.resolve({ ok: true, text: () => Promise.resolve('# stub') });
// the loader injects a <script>; short-circuit it since loadPyodide is already defined
const realAppend = w.document.head.appendChild.bind(w.document.head);
w.document.head.appendChild = (el) => (el.tagName === 'SCRIPT' && el.src && el.src.includes('pyodide.js'))
  ? (setTimeout(() => el.onload && el.onload(), 0), el) : realAppend(el);
let kb = [];
w.Reveal = { isReady: () => true, configure: (o) => kb.push(o.keyboard), getIndices: () => ({h:0}) };

w.eval(js);
// jsdom is still 'loading' when we eval, so the runtime's DOMContentLoaded hook is armed
// but never fires; a real browser has already parsed the page by the time the tag runs.
w.document.dispatchEvent(new w.Event('DOMContentLoaded'));

const $ = (s) => w.document.querySelector(s);
const wait = (fn, ms=3000) => new Promise((res, rej) => {
  const t0 = Date.now();
  (function tick(){ if (fn()) return res(); if (Date.now()-t0>ms) return rej(new Error('timeout: '+fn)); setTimeout(tick, 10); })();
});

(async () => {
  const pass = [];
  const ex1 = $('#ex-make-it-say-12'), ex2 = $('#ex-stop-the-aliasing');

  ex1.querySelector('.ex-run').click();
  await wait(() => ex1.classList.contains('fail'));
  pass.push(['E1 as-given fails', ex1.classList.contains('fail')]);
  pass.push(['E1 shows expected', ex1.querySelector('.ex-out').textContent.includes('Expected')]);
  pass.push(['E1 shows its output', ex1.querySelector('.ex-out').textContent.includes('66')]);

  ex1.querySelector('.ex-code').value = 'a = "6"\nb = "6"\nprint(int(a) + int(b))';
  ex1.querySelector('.ex-run').click();
  await wait(() => ex1.classList.contains('pass'));
  pass.push(['E1 fixed passes', ex1.classList.contains('pass')]);
  pass.push(['E1 status text', ex1.querySelector('.ex-status').textContent === 'passed']);

  ex2.querySelector('.ex-run').click();
  await wait(() => ex2.classList.contains('fail'));
  pass.push(['E2 check msg shown', ex2.querySelector('.ex-out').textContent.includes('a still has the 4')]);

  const saved = JSON.parse(w.localStorage.getItem('deckgen.ex./t/'));
  pass.push(['saved code', saved['make-it-say-12'].code.includes('int(a)')]);
  pass.push(['saved result', saved['make-it-say-12'].ok === true]);

  // reset restores the starter
  ex1.querySelector('.ex-reset').click();
  pass.push(['reset restores', ex1.querySelector('.ex-code').value === 'a = "6"\nb = "6"\nprint(a + b)']);
  pass.push(['reset clears status', !ex1.classList.contains('pass')]);

  // console
  const input = $('.pyc-in');
  input.value = 'x * 2';
  input.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
  await wait(() => $('.pyc-log').textContent.includes('42'));
  pass.push(['console echoes result', $('.pyc-log').textContent.includes('>>> x * 2') && $('.pyc-log').textContent.includes('42')]);

  // a pasted block keeps its newlines and its indentation, and runs as one entry
  input.value = 'rows = [1, 2, 3]\ntotal = 0\nfor r in rows:\n    total += r\ntotal';
  input.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
  await wait(() => $('.pyc-log').textContent.includes('6'));
  pass.push(['block echoed with continuation prompts',
    $('.pyc-log').textContent.includes('>>> rows = [1, 2, 3]') &&
    $('.pyc-log').textContent.includes('...     total += r')]);
  pass.push(['block is consumed', input.value === '']);

  // enter on an unfinished block adds an indented line instead of running
  const logLen = $('.pyc-log').textContent.length;
  input.value = 'for i in range(3):';
  input.selectionStart = input.selectionEnd = input.value.length;
  input.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
  pass.push(['open block continues, indented', input.value === 'for i in range(3):\n    ']);
  pass.push(['open block did not run', $('.pyc-log').textContent.length === logLen]);

  // a blank line closes it, the way a REPL does
  input.value = 'for i in range(3):\n    pass\n\n';
  input.selectionStart = input.selectionEnd = input.value.length;
  input.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
  pass.push(['blank line ends the block', input.value === '']);

  // shift+enter always adds a line, even on a finished one
  input.value = 'x = 1';
  input.selectionStart = input.selectionEnd = input.value.length;
  input.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, bubbles: true }));
  pass.push(['shift+enter adds a line', input.value === 'x = 1\n']);
  input.value = '';

  // the exercise's console button loads the drill, indentation intact
  $('#pyc').classList.remove('on');
  ex2.querySelector('.ex-send').click();
  pass.push(['console button opens the console', $('#pyc').classList.contains('on')]);
  pass.push(['console button loads the drill', input.value === ex2.querySelector('.ex-code').value.replace(/\s+$/, '')]);
  input.value = '';

  // syntax colours: the <pre> behind the editor is painted at load and repainted on input
  const hl1 = ex1.querySelector('.ex-hl');
  pass.push(['editor overlay exists', !!hl1 && hl1.querySelector('span[style*="color"]') !== null]);
  pass.push(['overlay text matches the editor', hl1.textContent.replace(/\n$/, '') === ex1.querySelector('.ex-code').value]);
  ex1.querySelector('.ex-code').value = 'for i in range(3):  # loop';
  ex1.querySelector('.ex-code').dispatchEvent(new w.Event('input', { bubbles: true }));
  pass.push(['overlay repaints on input', hl1.textContent.startsWith('for i in range(3):  # loop')
    && Array.from(hl1.querySelectorAll('span')).some(sp => sp.textContent === 'for')
    && Array.from(hl1.querySelectorAll('span')).some(sp => sp.textContent === '# loop')]);
  ex1.querySelector('.ex-reset').click();
  pass.push(['reset repaints', hl1.textContent.replace(/\n$/, '') === 'a = "6"\nb = "6"\nprint(a + b)']);
  pass.push(['console echo is coloured', $('.pyc-log').querySelector('.in span[style*="color"]') !== null
    && $('.pyc-log').textContent.includes('>>> x * 2')]);

  // reveal keyboard released while typing
  kb = [];
  ex1.querySelector('.ex-code').dispatchEvent(new w.FocusEvent('focusin', { bubbles: true }));
  ex1.querySelector('.ex-code').dispatchEvent(new w.FocusEvent('focusout', { bubbles: true }));
  pass.push(['reveal keyboard off then on', JSON.stringify(kb) === '[false,true]']);

  // backtick inside a textarea must not open the console
  const wasOpen = $('#pyc').classList.contains('on');
  const ta = ex1.querySelector('.ex-code');
  Object.defineProperty(w.document, 'activeElement', { value: ta, configurable: true });
  const ev = new w.KeyboardEvent('keydown', { key: '`', bubbles: true });
  Object.defineProperty(ev, 'target', { value: ta });
  w.document.dispatchEvent(ev);
  pass.push(['backtick ignored in editor', $('#pyc').classList.contains('on') === wasOpen]);

  let bad = 0;
  for (const [n, ok] of pass) { if (!ok) bad++; console.log((ok ? '  ok   ' : '  FAIL ') + n); }
  console.log(bad ? `\n${bad} FAILED` : `\nall ${pass.length} wiring checks passed`);
  process.exit(bad ? 1 : 0);
})().catch(e => { console.error('ERROR', e.message); console.error('ex1 class:', $('#ex-make-it-say-12') && $('#ex-make-it-say-12').className); console.error('out:', $('#ex-make-it-say-12') && $('#ex-make-it-say-12').querySelector('.ex-out').textContent); process.exit(1); });
