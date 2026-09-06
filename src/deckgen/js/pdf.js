// Print a built html deck to PDF: reveal.js print mode in Chromium (Playwright).
// The print stylesheet hides the ClassPoint chips and shows video thumbnails.
// Invoked by deckgen.core.build_pdf, which sets NODE_PATH to the course repo's
// node_modules — this file lives in site-packages, so node cannot find playwright otherwise.
// usage: NODE_PATH=<repo>/node_modules node pdf.js _site/week02/index.html out.pdf
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const [, , file, out] = process.argv;
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const url = (file.startsWith('http') ? file : 'file://' + path.resolve(file)) + '?print-pdf';
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForFunction(() => window.Reveal && Reveal.isReady());
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(800);
  const n = await page.evaluate(() => document.querySelectorAll('.pdf-page').length);
  await page.pdf({ path: out, width: '1920px', height: '1080px', printBackground: true, preferCSSPageSize: true,
                   margin: { top: 0, right: 0, bottom: 0, left: 0 } });
  console.log(`pdf: ${n} pages -> ${out}`);
  await browser.close();
})();
