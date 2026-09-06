// Screenshot every slide of a built html deck with the pre-installed Chromium.
// usage: NODE_PATH=<repo>/node_modules node screenshot.js _site/week02/index.html out/
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright');

(async () => {
  const [, , file, outDir] = process.argv;
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto(file.startsWith('http') ? file : 'file://' + path.resolve(file), { waitUntil: 'load' });
  await page.waitForFunction(() => window.Reveal && Reveal.isReady());
  await page.evaluate(() => document.fonts.ready);
  const n = await page.evaluate(() => Reveal.getTotalSlides());
  for (let i = 0; i < n; i++) {
    await page.evaluate((i) => Reveal.slide(i), i);
    await page.waitForTimeout(120);
    await page.screenshot({ path: path.join(outDir, `slide-${String(i + 1).padStart(2, '0')}.png`) });
  }
  console.log(`captured ${n} slides -> ${outDir}`);
  await browser.close();
})();
