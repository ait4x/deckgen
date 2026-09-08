// Live p5.js sketches, in a real browser: the page under the iframe, the mouse mapping under
// reveal's scaling, the key relay back to the deck, the LIVE chip, print (the frame hides, the
// twin shows), the standalone page, and the stills: the build makes the missing ones, a page
// with no canvas makes none, `deckgen snap --force` remakes them.
//
//     node tests/sketch.test.js
//
// Needs playwright with its Chromium, and `deckgen` on PATH. Builds tests/fixture-sketch/ itself.
const { chromium } = require('playwright');
const { spawnSync } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');
const os = require('os');

const FIX = path.join(__dirname, 'fixture-sketch');
const STILLS = path.join(FIX, 'deck/assets/sketches');
const PORT = 8908;
const pass = [];
const check = (n, c, extra) => pass.push([n + (extra !== undefined ? '  (' + extra + ')' : ''), c]);
const last = (r) => (r.stdout + r.stderr).trim().split('\n').filter(Boolean).pop();

(async () => {
  // a clean fixture: no stills yet, so the build has to make them
  fs.rmSync(STILLS, { recursive: true, force: true });
  const build = spawnSync('deckgen', ['build', '--site', '--no-pdf'], { cwd: FIX, encoding: 'utf8' });
  check('the build exits 0 (stills made, no warning)', build.status === 0, last(build));
  const stills = fs.existsSync(STILLS) ? fs.readdirSync(STILLS).sort() : [];
  check('a still for each sketch without a figure', JSON.stringify(stills) === JSON.stringify(['s-dot-act.png', 's-dot-code.png', 's-dot.png']), stills.join(','));
  const size = stills.includes('s-dot.png') ? fs.statSync(path.join(STILLS, 's-dot.png')).size : 0;
  check('a still has pixels in it', size > 3000, size + ' bytes');
  check('the sketch pages are written', fs.existsSync(path.join(FIX, '_site/s/sketches/s-dot.html')));
  check('p5 is staged into the site', fs.existsSync(path.join(FIX, '_site/vendor/p5/p5.min.js')));
  const html = fs.readFileSync(path.join(FIX, '_site/s/index.html'), 'utf8');
  check('the deck embeds the page with a chip', html.includes('data-src="sketches/s-dot.html"') && html.includes('Live · move the mouse'));
  check('the reading view links the page', html.includes('sketches/s-dot.html">Open the live sketch'));

  const root = path.join(FIX, '_site');
  const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.ttf': 'font/ttf', '.png': 'image/png', '.jpg': 'image/jpeg' };
  const server = http.createServer((req, res) => {
    let f = path.join(root, decodeURI(req.url.split('?')[0].split('#')[0]));
    if (f.endsWith('/')) f += 'index.html';
    fs.readFile(f, (e, d) => e ? (res.writeHead(404), res.end())
      : (res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' }), res.end(d)));
  }).listen(PORT);

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(`http://127.0.0.1:${PORT}/s/#/1`, { waitUntil: 'load' });
  await page.waitForFunction(() => window.Reveal && Reveal.isReady());
  const iframe = await page.waitForSelector('section.present iframe');
  const frame = await iframe.contentFrame();
  const canvas = await frame.waitForSelector('canvas', { state: 'visible', timeout: 8000 });
  check('the sketch runs in the frame', !!canvas);

  // reveal scales the whole deck and the page scales the canvas by css: the mouse must still land right
  const box = await canvas.boundingBox();
  await page.mouse.move(box.x + box.width * 0.75, box.y + box.height * 0.5);
  await page.waitForTimeout(300);
  const mx = await frame.evaluate(() => Math.round(mouseX));
  check('mouseX maps through the scaling (3/4 across = 300)', Math.abs(mx - 300) <= 6, mx);

  await page.waitForTimeout(4500);
  check('the LIVE chip dims after four seconds', await page.$eval('section.present .live', el => el.classList.contains('dim')));

  await canvas.click();
  const before = await page.evaluate(() => Reveal.getIndices().h);
  await page.keyboard.press('ArrowRight');
  await page.waitForTimeout(400);
  const after = await page.evaluate(() => Reveal.getIndices().h);
  check('ArrowRight inside the frame moves the deck', after === before + 1, `${before} -> ${after}`);
  check('the deck takes the keyboard back', await page.evaluate(() => document.activeElement.tagName !== 'IFRAME'), await page.evaluate(() => document.activeElement.tagName));
  await page.keyboard.press('ArrowLeft');
  await page.waitForTimeout(400);
  check('and the arrows work on the deck again', await page.evaluate(() => Reveal.getIndices().h) === before);

  await page.emulateMedia({ media: 'print' });
  check('print hides the live frame', await page.$eval('section.present .embed.sketch', el => getComputedStyle(el).display === 'none'));
  check('print shows the still under it', await page.$eval('section.present .img img', el => getComputedStyle(el).display !== 'none' && el.getAttribute('src').includes('s-dot')));
  await page.emulateMedia({ media: 'screen' });

  await page.goto(`http://127.0.0.1:${PORT}/s/sketches/s-dot.html`, { waitUntil: 'load' });
  await page.waitForSelector('canvas', { state: 'visible' });
  check('the standalone page shows its title bar', await page.evaluate(() => document.body.classList.contains('top') && getComputedStyle(document.getElementById('bar')).display === 'flex'));
  check('the bar names the course', await page.$eval('#bar b', el => el.textContent) === 'SKETCH');
  check('no page errors', errors.length === 0, errors.join(' | '));
  await browser.close();
  server.close();

  // a page with no p5 beside it never shows a canvas: no still, exit 1
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'deckgen-snap-'));
  fs.mkdirSync(path.join(tmp, 'a/sketches'), { recursive: true });
  fs.copyFileSync(path.join(FIX, '_site/s/sketches/s-dot.html'), path.join(tmp, 'a/sketches/s-dot.html'));
  const snapjs = path.join(__dirname, '..', 'src', 'deckgen', 'js', 'snap.js');
  const r = spawnSync('node', [snapjs, path.join(tmp, 'a/sketches/s-dot.html'), path.join(tmp, 'out.png'), '400', '300'], { encoding: 'utf8' });
  check('snap.js: no canvas is exit 1', r.status === 1, last(r));
  check('snap.js: no canvas writes nothing', !fs.existsSync(path.join(tmp, 'out.png')));

  const t0 = fs.statSync(path.join(STILLS, 's-dot.png')).mtimeMs;
  const snap = spawnSync('deckgen', ['snap', '--force', 's'], { cwd: FIX, encoding: 'utf8' });
  check('deckgen snap --force exits 0', snap.status === 0, last(snap));
  check('and remakes the still', fs.statSync(path.join(STILLS, 's-dot.png')).mtimeMs > t0);

  let bad = 0;
  for (const [n, ok] of pass) { if (!ok) bad++; console.log((ok ? '  ok   ' : '  FAIL ') + n); }
  console.log(bad ? `\n${bad} FAILED` : `\nall ${pass.length} sketch checks passed`);
  process.exit(bad ? 1 : 0);
})().catch(e => { console.error('ERROR', e); process.exit(1); });
