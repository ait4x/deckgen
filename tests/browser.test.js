// The whole thing, in a real browser: real Pyodide, a real phone viewport.
//
//     node tests/browser.test.js
//
// Needs playwright with its Chromium, and `deckgen` on PATH. Everything else is stubbed
// somewhere, and stubs are why the three bugs this suite found survived the other tests:
//
//   - reveal.js activates its own scroll view below 435px and CLONES every slide, so a
//     phone got two of every exercise: duplicate ids, and Run doing nothing on whichever
//     copy the browser resolved first.
//   - the widget was inserted beside its slot rather than inside it, so the `.ho-ex .ex`
//     rules never matched and the editor kept its 860px slide width on a 390px screen.
//   - the "Reading view" button stayed up while already reading, on top of the console button.
//
// jsdom has no layout and no reveal.js, so it could not have caught any of them.
const { chromium, devices } = require('playwright');
const { execFileSync, spawn } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');

const FIX = path.join(__dirname, 'fixture');
const PORT = 8907;
const pass = [];
const check = (n, c, extra) => pass.push([n + (extra !== undefined ? '  (' + extra + ')' : ''), c]);

(async () => {
  execFileSync('deckgen', ['build', '--site', '--no-pdf'], { cwd: FIX, stdio: 'pipe' });
  const root = path.join(FIX, '_site');
  const types = { '.html': 'text/html', '.js': 'text/javascript', '.py': 'text/plain',
                  '.css': 'text/css', '.ttf': 'font/ttf' };
  const server = http.createServer((req, res) => {
    let f = path.join(root, decodeURI(req.url.split('?')[0]));
    if (f.endsWith('/')) f += 'index.html';
    fs.readFile(f, (e, d) => e ? (res.writeHead(404), res.end())
      : (res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }), res.end(d)));
  }).listen(PORT);

  const URL = `http://127.0.0.1:${PORT}/t/`;
  const browser = await chromium.launch();
  const errs = [];

  // ── desktop: the deck, and Python that actually runs ──
  const p = await (await browser.newContext({ viewport: { width: 1600, height: 900 } })).newPage();
  p.on('pageerror', e => errs.push('desktop: ' + e.message));
  await p.goto(URL, { waitUntil: 'load' });
  await p.waitForFunction(() => window.Reveal && Reveal.isReady());
  check('desktop opens the deck', !await p.evaluate(() => document.body.classList.contains('ho')));
  check('one widget per exercise', await p.locator('.ex').count() === 2, await p.locator('.ex').count());

  const ex = p.locator('#ex-make-it-say-12');
  await p.evaluate(() => Reveal.slide(1));
  await ex.locator('.ex-run').click();

  await p.waitForFunction(() => {
    const e = document.querySelector('#ex-make-it-say-12');
    return e.classList.contains('pass') || e.classList.contains('fail');
  }, null, { timeout: 240000 });
  check('real Pyodide runs the starter and marks it wrong', await ex.evaluate(e => e.classList.contains('fail')));
  await ex.locator('.ex-code').fill('a = "6"\nb = "6"\nprint(int(a) + int(b))');
  await ex.locator('.ex-run').click();
  await p.waitForFunction(() => document.querySelector('#ex-make-it-say-12').classList.contains('pass'), null, { timeout: 60000 });
  check('and marks the fix right', true);

  await p.keyboard.press('`');
  await p.locator('.pyc-in').fill('sum(range(10))');
  await p.locator('.pyc-in').press('Enter');
  await p.waitForFunction(() => document.querySelector('.pyc-log').textContent.includes('45'), null, { timeout: 60000 });
  check('the console evaluates and keeps state', true);
  await p.keyboard.press('`');

  const before = await p.evaluate(() => Reveal.getIndices().h);
  await ex.locator('.ex-code').click();
  await p.keyboard.press('Space');
  await p.keyboard.press('ArrowRight');
  check('typing in the editor does not move the deck', before === await p.evaluate(() => Reveal.getIndices().h));

  // ── phone: the reading view ──
  const m = await (await browser.newContext({ ...devices['iPhone 13'] })).newPage();
  m.on('pageerror', e => errs.push('phone: ' + e.message));
  await m.goto(URL, { waitUntil: 'load' });
  await m.waitForFunction(() => window.Reveal && Reveal.isReady());
  const total = await m.locator('.ex').count();
  check('phone opens the reading view', await m.evaluate(() => document.body.classList.contains('ho')));
  check('reveal did not clone the slides', total === 2, 'total .ex = ' + total);
  check('every widget is in the reading view', await m.locator('.handout .ex').count() === 2);
  check('none left in the deck', await m.locator('.reveal .ex').count() === 0);

  const box = await m.evaluate(() => {
    const ta = document.querySelector('.handout .ex-code');
    const bodyP = [...document.querySelectorAll('.ho-slide p')].find(e => !e.className);
    return { editor: parseFloat(getComputedStyle(ta).fontSize),
             width: Math.round(ta.getBoundingClientRect().width),
             view: document.documentElement.clientWidth,
             body: bodyP ? parseFloat(getComputedStyle(bodyP).fontSize) : 0,
             overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
             openVisible: getComputedStyle(document.getElementById('ho-open')).display !== 'none' };
  });
  check('editor is >= 16px, below which iOS zooms on focus', box.editor >= 16, box.editor + 'px');
  check('editor fits the viewport', box.width <= box.view, box.width + '/' + box.view);
  check('body text is readable', box.body >= 16, box.body + 'px');
  check('no horizontal overflow', !box.overflow);
  check('the Reading view button hides itself once reading', !box.openVisible);

  const mex = m.locator('.handout #ex-stop-the-aliasing');
  await mex.scrollIntoViewIfNeeded();
  await mex.locator('.ex-code').fill('a = [1, 2, 3]\nb = a.copy()\nb.append(4)\nprint(a)');
  await mex.locator('.ex-run').click();
  await m.waitForFunction(() => document.querySelector('#ex-stop-the-aliasing').classList.contains('pass'), null, { timeout: 240000 });
  check('an exercise can be solved on a phone', true);

  await m.locator('#ho-deck').click();
  check('switching to the deck moves them back', await m.locator('.reveal .ex').count() === 2 && await m.locator('.ex').count() === 2);
  await m.locator('#ho-open').click();
  check('and back again, still without duplicating', await m.locator('.handout .ex').count() === 2 && await m.locator('.ex').count() === 2);

  check('no page errors anywhere', errs.length === 0, errs.join(' / ') || 'none');

  await browser.close();
  server.close();
  let bad = 0;
  for (const [n, ok] of pass) { if (!ok) bad++; console.log((ok ? '  ok   ' : '  FAIL ') + n); }
  console.log(bad ? `\n${bad} FAILED` : `\nall ${pass.length} browser checks passed`);
  process.exit(bad ? 1 : 0);
})().catch(e => { console.error('ERROR', e.message); process.exit(1); });
