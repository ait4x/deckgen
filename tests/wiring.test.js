// Test the DOM half of the runtime with a stubbed Pyodide. The Python half is already
// verified against the real interpreter; this covers the wiring: status classes, output
// rendering, localStorage, reset, ctrl+enter, console echo, and reveal keyboard release.
const { JSDOM } = require('jsdom');
const fs = require('fs');

const DECK = process.env.DECK_HTML || '/tmp/extest/_site/t/index.html';
const RT = process.env.DECK_JS || '/tmp/extest/_site/vendor/pyodide-console.js';
const html = fs.readFileSync(DECK, 'utf8');
const js = fs.readFileSync(RT, 'utf8');

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
    if (n === '_dg_eval') return (src) =>
      JSON.stringify(src === 'x * 2' ? {out:'42\n',err:''} : {out:'',err:''});
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
