// Stills of the live p5.js sketches: what the PowerPoint and the PDF show where the html deck runs the sketch.
// usage: NODE_PATH=<repo>/node_modules node snap.js <page.html> <out.png> <canvas w> <canvas h> [more quadruples...]
// The still is taken 1.5 s after load with the mouse resting at 60 % / 40 % of the canvas, no click: design the
// sketch so that this resting state is a good picture. `deckgen snap` (deckgen.core.snapshot_sketches) drives
// this for whole decks. A page that never shows a canvas gets no still and the exit code is 1.
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const args = process.argv.slice(2);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
  let failed = 0;
  for (let i = 0; i + 3 < args.length; i += 4) {
    const [file, out] = [args[i], args[i + 1]];
    const cw = Number(args[i + 2]), ch = Number(args[i + 3]);
    const page = await browser.newPage({ viewport: { width: cw, height: ch }, deviceScaleFactor: 2 });
    page.on('pageerror', e => console.log(`error in ${path.basename(file)}: ${String(e).slice(0, 200)}`));
    page.on('console', m => { if (m.type() === 'error') console.log(`console in ${path.basename(file)}: ${m.text().slice(0, 200)}`); });
    try {
      await page.goto('file://' + path.resolve(file) + '?snap', { waitUntil: 'load' });
      await page.waitForSelector('canvas', { state: 'visible', timeout: 8000 }).catch(() => null);
      await page.mouse.move(Math.round(cw * 0.6), Math.round(ch * 0.4));
      await page.waitForTimeout(1500);
      const c = await page.$('canvas');
      if (c && await c.isVisible()) {
        await c.screenshot({ path: out, timeout: 10000 });
        console.log(`snap: ${path.basename(out)}`);
      } else {                   // p5 not loaded, or the sketch threw before createCanvas: no still, the old one stays
        console.log(`no canvas in ${path.basename(file)}: nothing written to ${path.basename(out)}`);
        failed += 1;
      }
    } catch (e) {                // one bad page must not stop the rest of the batch
      console.log(`failed ${path.basename(file)}: ${String(e).split('\n')[0].slice(0, 200)}; nothing written to ${path.basename(out)}`);
      failed += 1;
    }
    await page.close();
  }
  await browser.close();
  process.exitCode = failed ? 1 : 0;
})();
