// The reading view: switching, and the single exercise widget moving between views.
//
// The thing most worth guarding is that the widget is MOVED, not copied. Two copies with
// the same id would both wire themselves, both write the same localStorage key, and drift
// apart the moment a student typed into one of them.
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const FIX = path.join(__dirname, 'fixture');
try {
  execFileSync('deckgen', ['build', '--site', '--no-pdf'], { cwd: FIX, stdio: 'pipe' });
} catch (e) {
  console.error('could not build the fixture — is deckgen on PATH?\n' + (e.stderr || e.message));
  process.exit(1);
}
const html = fs.readFileSync(path.join(FIX, '_site/t/index.html'), 'utf8');
const js = fs.readFileSync(path.join(FIX, '_site/vendor/handout.js'), 'utf8');

const pass = [];
function check(n, c) { pass.push([n, c]); }

function makeDom(opts) {
  const dom = new JSDOM(html, { url: 'http://x/t/', runScripts: 'outside-only', pretendToBeVisual: true });
  const w = dom.window;
  const listeners = [];
  w.matchMedia = (q) => ({
    matches: !!(opts.media || {})[q],
    media: q,
    addEventListener: (_, fn) => listeners.push([q, fn]),
    addListener: (fn) => listeners.push([q, fn]),
    removeEventListener: () => {},
  });
  const cfg = [];
  w.Reveal = { configure: (o) => cfg.push(o), layout: () => {} };
  if (opts.saved) w.localStorage.setItem('deckgen.view', opts.saved);
  w.eval(js);
  w.document.dispatchEvent(new w.Event('DOMContentLoaded'));
  return { w, cfg, listeners };
}

const PHONE = { '(max-width: 900px)': true, '(orientation: portrait)': true, '(hover: none)': true };

// printing must always get the deck, whatever the device or the saved choice
{
  const dom = new JSDOM(html, { url: 'http://x/t/?print-pdf', runScripts: 'outside-only', pretendToBeVisual: true });
  const w = dom.window;
  w.matchMedia = () => ({ matches: true, addEventListener(){}, addListener(){}, removeEventListener(){} });
  w.Reveal = { configure(){}, layout(){} };
  w.localStorage.setItem('deckgen.view', 'handout');
  w.eval(js);
  w.document.dispatchEvent(new w.Event('DOMContentLoaded'));
  check('print-pdf forces the deck even on a phone with reading view saved',
        !w.document.body.classList.contains('ho') && w.document.querySelectorAll('.reveal .ex').length === 2);
}
const DESKTOP = {};

// ── a phone gets the reading view by default ──
{
  const { w, cfg } = makeDom({ media: PHONE });
  const d = w.document;
  check('phone defaults to reading view', d.body.classList.contains('ho'));
  check('handout is shown', !d.querySelector('.handout').hidden);
  check('reveal keyboard and touch released', JSON.stringify(cfg[0]) === '{"keyboard":false,"touch":false}');
  check('exercises moved into the reading view', d.querySelectorAll('.handout .ex').length === 2);
  check('none left in the deck', d.querySelectorAll('.reveal .ex').length === 0);
  check('widgets are moved, not copied', d.querySelectorAll('.ex').length === 2);
  check('each landed in its own slot',
    Array.from(d.querySelectorAll('.handout .ex')).every(
      ex => ex.previousElementSibling.dataset.for === ex.dataset.eid));

  // switching back returns them to where they came from
  d.getElementById('ho-deck').click();
  check('deck view restores', !d.body.classList.contains('ho'));
  check('exercises returned to the deck', d.querySelectorAll('.reveal .ex').length === 2);
  check('still exactly two widgets', d.querySelectorAll('.ex').length === 2);
  check('back inside their slides',
    Array.from(d.querySelectorAll('.reveal .ex')).every(ex => !!ex.closest('section')));
  check('choice remembered', w.localStorage.getItem('deckgen.view') === 'deck');
}

// ── a desktop gets the deck ──
{
  const { w } = makeDom({ media: DESKTOP });
  const d = w.document;
  check('desktop defaults to the deck', !d.body.classList.contains('ho'));
  check('handout hidden', d.querySelector('.handout').hidden);
  check('exercises stay in the deck', d.querySelectorAll('.reveal .ex').length === 2);
  d.getElementById('ho-open').click();
  check('desktop can opt in', d.body.classList.contains('ho') && d.querySelectorAll('.handout .ex').length === 2);
}

// ── a remembered choice beats the device ──
{
  const { w } = makeDom({ media: PHONE, saved: 'deck' });
  check('saved deck choice wins on a phone', !w.document.body.classList.contains('ho'));
}
{
  const { w } = makeDom({ media: DESKTOP, saved: 'handout' });
  check('saved reading choice wins on desktop', w.document.body.classList.contains('ho'));
}

// ── rotating to landscape drops the reading view, unless the choice was explicit ──
{
  const { w, listeners } = makeDom({ media: PHONE });
  check('starts in reading view', w.document.body.classList.contains('ho'));
  listeners.forEach(([q, fn]) => q.includes('orientation') && fn({ matches: false }));
  check('rotating to landscape shows the deck', !w.document.body.classList.contains('ho'));
}
{
  const { w, listeners } = makeDom({ media: PHONE, saved: 'handout' });
  listeners.forEach(([q, fn]) => q.includes('orientation') && fn({ matches: false }));
  check('an explicit choice survives rotation', w.document.body.classList.contains('ho'));
}

let bad = 0;
for (const [n, ok] of pass) { if (!ok) bad++; console.log((ok ? '  ok   ' : '  FAIL ') + n); }
console.log(bad ? `\n${bad} FAILED` : `\nall ${pass.length} handout checks passed`);
process.exit(bad ? 1 : 0);
