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
  check('a still for each sketch without a figure', JSON.stringify(stills) === JSON.stringify(['s-dot-act.png', 's-dot-code.png', 's-dot.png', 's-slider.png']), stills.join(','));
  const size = stills.includes('s-dot.png') ? fs.statSync(path.join(STILLS, 's-dot.png')).size : 0;
  check('a still has pixels in it', size > 3000, size + ' bytes');
  check('the sketch pages are written', fs.existsSync(path.join(FIX, '_site/s/sketches/s-dot.html')));
  check('p5 is staged into the site', fs.existsSync(path.join(FIX, '_site/vendor/p5/p5.min.js')));
  const html = fs.readFileSync(path.join(FIX, '_site/s/index.html'), 'utf8');
  check('the deck embeds the page with a chip', html.includes('data-src="sketches/s-dot.html"') && html.includes('Live · move the mouse'));
  check('the reading view links the page', html.includes('sketches/s-dot.html">Open the live sketch'));
  check('the code slides carry an editor over the panel', html.includes('data-sketch="s-dot-code"') && html.includes('data-sketch="s-slider"') && html.includes('vendor/sketch-editor.js'));
  check('the editor runtime is staged', fs.existsSync(path.join(FIX, '_site/vendor/sketch-editor.js')));

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

  // ── the editable panel: slide 3 is code_slide with the dot sketch ──
  const pixel = (fr, x, y) => fr.evaluate(([x, y]) => { const c = document.querySelector('canvas'); return c ? Array.from(c.getContext('2d').getImageData(x, y, 1, 1).data).join(',') : 'no canvas'; }, [x, y]);
  const frameOn = async () => { const el = await page.waitForSelector('section.present iframe'); const fr = await el.contentFrame(); await fr.waitForSelector('canvas', { state: 'visible', timeout: 8000 }); return fr; };
  const goSlide = async (n) => { await page.evaluate(n => Reveal.slide(n), n); await page.waitForSelector(`section.present[data-slide="${n + 1}"]`); };
  await goSlide(2);
  let fr = await frameOn();
  const ex = await page.waitForSelector('section.present .ex-js');
  check('the editor is on the slide, with the code in the box', !!ex && (await page.$eval('section.present .ex-code', el => el.value)).includes('circle(mouseX, mouseY, 60)'));
  check('the box is coloured like the panel', await page.$eval('section.present .ex-hl span', el => el.textContent) === 'function');
  await fr.waitForFunction(() => document.querySelector('canvas').getContext('2d').getImageData(390, 290, 1, 1).data[0] === 240, null, { timeout: 4000 }).catch(() => null);
  check('the sketch drew its grey background (read away from the dot on the mouse)', await pixel(fr, 390, 290) === '240,240,240,255', await pixel(fr, 390, 290));
  // edit and run: the frame swaps the sketch for the new code
  await page.$eval('section.present .ex-code', el => { el.value = el.value.replace('background(240)', 'background(0, 0, 255)'); el.dispatchEvent(new Event('input')); });
  await page.click('section.present .ex-run');
  await page.waitForFunction(() => document.querySelector('section.present .ex-status').textContent === 'ran', null, { timeout: 8000 });
  await fr.waitForFunction(() => { const c = document.querySelector('canvas'); return c && c.getContext('2d').getImageData(390, 290, 1, 1).data[2] === 255; }, null, { timeout: 4000 }).catch(() => null);
  check('Run re-runs the sketch with the edited code (blue background)', await pixel(fr, 390, 290) === '0,0,255,255', await pixel(fr, 390, 290));
  check('one canvas, not two', await fr.evaluate(() => document.querySelectorAll('canvas').length) === 1);
  check('the mirror follows the edit', (await page.$eval('section.present .ex-hl', el => el.textContent)).includes('background(0, 0, 255)'));
  // a syntax error comes back into the box
  await page.$eval('section.present .ex-code', el => { el.value = 'function setup() {\n  createCanvas(400, 300;\n}'; el.dispatchEvent(new Event('input')); });
  await page.keyboard.press('Control+Enter');   // the textarea does not have focus: click Run instead
  await page.click('section.present .ex-run');
  await page.waitForFunction(() => document.querySelector('section.present .ex-js').classList.contains('fail'), null, { timeout: 8000 });
  const err = await page.$eval('section.present .ex-out', el => el.textContent);
  check('a syntax error is shown under the box', /SyntaxError|Unexpected|missing/.test(err), err.slice(0, 60));
  check('and the old canvas is gone, not left running', await fr.evaluate(() => document.querySelectorAll('canvas').length) === 0);
  // the edited code survives a reload and runs again on its own
  await page.$eval('section.present .ex-code', el => { el.value = el.value.replace('(400, 300;', '(400, 300);\n  background(0, 0, 255);'); el.dispatchEvent(new Event('input')); });
  await page.click('section.present .ex-run');
  await page.waitForFunction(() => document.querySelector('section.present .ex-status').textContent === 'ran', null, { timeout: 8000 });
  await page.reload({ waitUntil: 'load' });
  await page.waitForFunction(() => window.Reveal && Reveal.isReady());
  await page.waitForSelector('section.present[data-slide="3"]');
  fr = await frameOn();
  await fr.waitForFunction(() => { const c = document.querySelector('canvas'); return c && c.getContext('2d').getImageData(390, 290, 1, 1).data[2] === 255; }, null, { timeout: 8000 }).catch(() => null);
  check('after a reload the saved code is back in the box and running', (await page.$eval('section.present .ex-code', el => el.value)).includes('background(0, 0, 255)') && await pixel(fr, 390, 290) === '0,0,255,255', await pixel(fr, 390, 290));
  check('the status says it is the edited sketch', await page.$eval('section.present .ex-status', el => el.textContent) === 'ran');
  // Reset: the slide's code, run again
  await page.click('section.present .ex-reset');
  await page.waitForFunction(() => document.querySelector('section.present .ex-status').textContent === '', null, { timeout: 8000 });
  await fr.waitForFunction(() => { const c = document.querySelector('canvas'); return c && c.getContext('2d').getImageData(390, 290, 1, 1).data[0] === 240; }, null, { timeout: 4000 }).catch(() => null);
  check('Reset brings the slide\'s code back and runs it', (await page.$eval('section.present .ex-code', el => el.value)).includes('background(240)') && await pixel(fr, 390, 290) === '240,240,240,255', await pixel(fr, 390, 290));
  // typing in the box does not move the deck
  await page.click('section.present .ex-code');
  await page.keyboard.press('ArrowRight');
  await page.waitForTimeout(300);
  check('the arrows stay in the box while typing', await page.evaluate(() => Reveal.getIndices().h) === 2);
  await page.keyboard.press('Tab');
  check('tab indents two spaces instead of leaving the box', (await page.$eval('section.present .ex-code', el => el.value)).includes('  ') && await page.evaluate(() => document.activeElement.classList.contains('ex-code')));
  await page.click('section.present .ex-reset');
  await page.waitForTimeout(300);
  await page.emulateMedia({ media: 'print' });
  check('print hides the editor and shows the static panel', await page.$eval('section.present .ex-js', el => getComputedStyle(el).display === 'none') && await page.$$eval('section.present .el', els => els.some(el => el.textContent.includes('createCanvas(400, 300)'))));
  await page.emulateMedia({ media: 'screen' });

  // ── a slider in the code: slide 6 ──
  await goSlide(5);
  fr = await frameOn();
  await fr.waitForSelector('#ctl.on label', { timeout: 8000 });
  check('createSlider with a label puts a labelled slider in the bar', await fr.$eval('#ctl label', el => el.textContent.trim()) === 'size40' || await fr.$eval('#ctl label', el => el.textContent.replace(/\s+/g, '')) === 'size40', await fr.$eval('#ctl label', el => el.textContent));
  check('the canvas makes room for the bar', await fr.evaluate(() => document.querySelector('canvas').style.top.includes('calc')) && await fr.evaluate(() => { const c = document.querySelector('canvas').getBoundingClientRect(); return c.bottom <= innerHeight - 44 + 1; }));
  check('the circle is at its starting size (red outside a 20 px radius)', await pixel(fr, 200 - 45, 150) === '255,0,0,255', await pixel(fr, 155, 150));
  await fr.evaluate(() => { const s = document.querySelector('#ctl input'); s.value = 100; s.dispatchEvent(new Event('input', { bubbles: true })); });
  await page.waitForTimeout(200);
  check('moving the slider redraws the noLoop sketch (white inside a 50 px radius)', await pixel(fr, 155, 150) === '255,255,255,255', await pixel(fr, 155, 150));
  check('and the bar shows the value', await fr.$eval('#ctl output', el => el.textContent) === '100');
  check('no page errors so far', errors.length === 0, errors.join(' | '));

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
