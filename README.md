# deckgen

One slide spec, four outputs. A deck is a plain Python module; `deckgen build` turns it into

| Output | What |
|---|---|
| `_site/<deck>/index.html` | a reveal.js deck for GitHub Pages — arrows, `S` speaker notes, `O` overview, `F` full screen |
| `_site/<deck>/<name>.pdf` | the same deck printed by Chromium, ClassPoint chips hidden, video slides showing their thumbnail |
| `export/<deck>.pptx` + `<deck>-classpoint.pptx` | an editable PowerPoint, then the classroom copy: ait4x theme, slide master and 8 layouts, row-by-row entrance animations, and **live ClassPoint activity buttons** |
| `export/preview/` | a png of every slide, contact sheets, and a text-overflow check |

Built for the ait4x design system (PolyU School of Design) and extracted from
[`venetanji/sd2112-teaching`](https://github.com/venetanji/sd2112-teaching), where it
still runs the Week 1 deck.

## Install

```bash
pip install git+https://github.com/ait4x/deckgen@v0.1.0
```

Pure Python for everything except the PDF, which needs node 18+ and Playwright's Chromium:

```bash
npm install --no-save playwright@1.56.1 && npx playwright install chromium
```

`deckgen build --no-pdf` skips that step, and `deckgen build --pptx` never reaches it.

## A course repo

```bash
mkdir sd0000-teaching && cd sd0000-teaching
deckgen init            # deckgen.toml, deck/week01.py, .github/workflows/, .gitignore
$EDITOR deckgen.toml
deckgen build --pptx
```

```
deckgen.toml           the course: code, name, year, footer, which decks, what to publish
deck/week01.py         the slides as one Python spec — edit here, every output updates
deck/assets/           images (deck/assets/generated/ is built, git-ignored; deck/assets/sketches/
                       holds the stills of the live sketches, made by `deckgen snap`, committed)
deck/figures.py        course-specific drawn figures, on deckgen.figures.Canvas (optional)
syllabus/*.md          published if listed under [[publish]]
lessons/*.md           .docx + html into export/docs/, not published
site/index.html        the landing page; the reveal.js vendor bundle is added at build time
_site/  export/        outputs, git-ignored, rebuilt by the workflows
```

Both `.github/workflows/` files come from `deckgen init`: **Publish site** pushes `_site/`
to GitHub Pages, **Build PowerPoints** keeps `export/` as a 90-day artifact (named by
`[course].artifact`). PowerPoints are deliberately not published.

## Writing a deck

Every layout takes its **eyebrow** — the small tracked caps line — first, then its title.

```python
from deckgen.layouts import title, agenda, section, content, question, statement, end

DECK = {'title': 'Week 2', 'pdf': 'SD0000-week02.pdf', 'slides': [
    title('SD0000 · WEEK 02', 'Version control', 'Or: how to undo anything.'),
    agenda('SD0000 · WEEK 02', ['Commits', 'Branches', 'Pull requests']),
    section('01', 'Commits', 'Part one'),
    content('01 · COMMITS', 'What a commit is', [
        'A commit is a snapshot, not a diff.',
        '',
        '- it has a parent',
        '- it has **an author** and {orange:a message}',
        '- {mono:git log} walks the chain backwards',
    ], notes='Say this bit out loud.'),
    question('multiple_choice', 'Which of these is a commit?',
             choices=['A saved file', 'A snapshot with a parent', 'A branch name']),
    question('word_cloud', 'One word for version control?'),
    statement('Nothing you commit is ever really lost.'),
    end('See you next week', 'Bring a laptop.', 'venetanji.github.io/sd0000-teaching'),
]}
```

Layouts: `title` `agenda` `section` `statement` `quote` `content` `cards` `question`
`image_full` `image_grid` `timeline` `journey` `activity` `video` `assessment` `team`
`team_band` `two_col` `code_panel` `code_slide` `figure_slide` `sketch_slide` `exercise`
`end`. Inline markup in any string: `**bold**`,
`[text](url)`, `{orange:…}` `{teal:…}` `{muted:…}` `{mono:…}` and the other palette names.

ClassPoint activities come from `question(kind, …)` — `word_cloud`, `short_answer`,
`image_upload`, or `multiple_choice` when you pass `choices=[…]` — or from an explicit
`cp={'type': …}` on `content`, `cards`, `figure_slide` and `activity`.

## Scale

The canvas is 1920 × 1080 px on a 13.333 × 7.5 in slide, so **one design pixel is 0.5 pt**
in PowerPoint (72 px title = 36 pt, 36 px body = 18 pt, 24 px eyebrow = 12 pt).
`deckgen.PT` holds that factor; the master and layouts use the same scale.

## Fonts

Inter and JetBrains Mono variable fonts ship inside the package — the html deck and the
png previews use them directly. PowerPoint has no weight axis, so **the family name carries
the weight** (`Inter Black`, `Inter ExtraBold`, `Inter` + bold). See
[PPTX-EXPORT.md](PPTX-EXPORT.md). Install both fonts on the classroom PC or the projector
substitutes Arial.

## Command line

```
deckgen build [--site] [--pptx] [--no-pdf] [--snap] [DECK ...]
deckgen snap [--force] [DECK ...]   stills of the live sketches (deck/assets/sketches/)
deckgen init [DIR]              scaffold a course repo
deckgen template [OUT]          write the ait4x .potx: master + the 8 layouts
deckgen --root PATH ...         act on a repo elsewhere
```

Neither `--site` nor `--pptx` means both. `build` exits non-zero if any text overflows its
box, so a broken slide fails the workflow rather than reaching the projector.

## Runnable exercises

`exercise()` puts an editable code box, a Run button and a pass/fail check on a slide.
Students open the deck on their laptops and type into it; **Pyodide runs the Python in
the browser**, so there is nothing to install and nothing to submit.

```python
from deckgen.layouts import exercise

exercise('04 · TYPES', 'Make it say 12',
         'Two strings glued together give "66". Make Python add them as numbers.',
         code='a = "6"\nb = "6"\nprint(a + b)',
         expect='12')

exercise('04 · ALIASING', 'Stop the aliasing',
         'b should not change when a does.',
         code='a = [1, 2, 3]\nb = a\nb.append(4)\nprint(a)',
         check='ok = _out.strip() == "[1, 2, 3]"\n'
               'msg = "" if ok else "a still has the 4 in it"')
```

Pass **`expect`** (stdout must equal it, both sides stripped) or **`check`** (Python run
afterwards in the student's namespace, with the captured stdout bound to `_out`; set
`ok = True` to pass, and anything in `msg` is shown to them).

- **Nothing loads until it is used.** Pyodide is ~12 MB; the runtime is fetched on the
  first Run or the first time the console is opened, never on page load. A deck with no
  exercises never references it at all.
- **A console on every slide.** Backtick, or the button bottom-left. It keeps its state
  between lines, so you can demonstrate something and then poke at it.
- **Answers survive a reload** — code and pass/fail go into `localStorage`, keyed per deck.
- **Reveal's keyboard is released while typing**, so space and the arrows reach the editor
  instead of moving the deck.
- **pptx and PDF degrade to a static code panel**, because PowerPoint cannot run Python
  and a printed slide should still show the exercise.

Code everywhere — `exercise`, `code_panel`, `two_col`'s right panel, `question(example=…)`
— is set at `deckgen.CODE` (30 px = 15 pt), one size across every layout.

## Syntax colours

Code on a slide is coloured — keywords, builtins, strings, numbers, comments — by a small
lexer in `deckgen/syntax.py`, on every path at once: the html deck, the PowerPoint, the
png previews and the reading view, because a Run carries its own colour. The live editor
of an `exercise()` and the console's echo are painted by the same rules in JavaScript.

- `code_slide`, `two_col` (mono panel), `code_panel`, `exercise` and `activity(panel=…)`
  take `lang='py' | 'js' | None`. Python is the default; a `code_slide` with a live sketch
  defaults to JavaScript; `None` keeps the panel plain, for a diagram drawn in text
  (`two_col(…, lang=None)`). An activity panel is plain unless asked — a spec is not code.
- Inline markup on a `code_panel` line still wins: a `{orange:…}` span stays orange and
  the rest of the line gets its colours.
- The lexer is forgiving on purpose: an unclosed string, a line ending in a colon, a
  `___` placeholder — slide code is fragments, and it never raises.

## After the class: report links

ClassPoint publishes every activity at `app.classpoint.io/activity/<activityId>` — a
public page, no login, with all the responses on it. Those ids are the only thing between
a student and their own work, so a deck can carry them:

```python
from deckgen import attach_reports

attach_reports(S, Path(__file__).parent / 'week01-reports.json')
DECK = dict(title=..., slides=finalize(S, FOOTER), ...)
```

The eyebrow of each question slide gains a link, which costs no layout space, works on
every question variant including multiple choice (where `hint` is not rendered), and
becomes a real hyperlink in the PowerPoint as well as the html:

```
QUESTION · MULTIPLE CHOICE · YOUR ANSWERS
                             ^ https://app.classpoint.io/activity/mc20260904043922212ZXSV
```

The file is a list, one entry per activity, **in the order the class ran them**:

```json
[{"activity": "sa20260904033646383JAAW", "question": "Why is AI relevant for design?"},
 {"activity": "mc20260904034846877ZUKC", "question": "Which are you closest to?"}]
```

Order is the whole contract. ClassPoint mints an id the first time an activity runs, so
the activities of one class sort chronologically into exactly the order their slides
appear in — which is why the file needs no slide numbers and survives the deck being
re-cut around them. `question` is optional and checked when present; it catches the case
that actually happens, a question added or rewritten after the class it was matched
against. A count mismatch or a changed question raises. **A missing file is a no-op**, so
every deck can call this from the day it is written and the links appear the week it is
taught.

An entry can record an activity **without** linking it:

```json
[{"activity": null, "question": "One hope and one worry.", "withheld": "names hidden"}]
```

That is not a formality. ClassPoint's public page honours an activity's `isNamesHidden`,
but **the payload behind it still carries `participantName` for every response** — so a
link to an activity the room was told was anonymous hands out a way to undo that. The
slide keeps its place in the count and simply gets no link.

Writing the file is [`classpoint.py`](https://github.com/venetanji/classpoint.py)'s job —
it reads the activity ids back out of ClassPoint after class.

## Live p5.js sketches

Any slide can run a p5.js sketch, live, in the html deck: `live(name, code, w, h, hint=…,
extra=…, sound=False)` placed with `sketch_slide(…)` (full width), or as the media of
`content(…, sketch=)`, `figure_slide(…, sketch=)`, `code_slide(…, sketch=)` and
`activity(…, sketch=)`.

```python
from deckgen.layouts import code_slide, live

TEN = '''function setup() {
  createCanvas(600, 600);
  for (let i = 0; i < 10; i++) circle(random(600), random(600), 8);
}'''

code_slide('03 · TEN POINTS', 'Ten points at random', TEN,
           sketch=live('ten', TEN, 600, 600, hint='click to redraw',
                       extra='function mousePressed() { redraw(); }'))
```

- **The page under the iframe** (`_site/<deck>/sketches/<name>.html`) scales the canvas to
  its frame while keeping `mouseX`/`mouseY` right, so mouse, touch and keyboard interaction
  just work under reveal's own scaling. The deck's navigation keys (arrows, space, Esc, S, O,
  F) still reach reveal.js when the sketch has the focus; `R` restarts the sketch. A sketch
  that uses a key itself returns `false` from `keyPressed()`.
- **A LIVE chip** with the `hint` tells the room what to do, then fades. Its ↗ opens the
  sketch on its own page, which gets a title bar. The reading view links the same page.
- **`code`** is what the students see on the slide (keep it short and readable); **`extra`**
  is JavaScript appended only in the page, for the interaction the code panel does not show.
  `sound=True` also loads p5.sound. p5.js and p5.sound are in the vendor bundle, so the deck
  runs offline in the classroom.
- **The PowerPoint and the PDF cannot run code**, so every sketch has a still twin: the
  `figure=` you pass (the Python drawing of the same rule), or the snapshot in
  `deck/assets/sketches/<name>.png` made by `deckgen snap` — 1.5 s after load, mouse resting
  at 60 % / 40 % of the canvas, no click: design the sketch so that state looks right.
  Snapshots are committed, because the PowerPoint workflow has no browser; a missing one shows
  as a labelled box and fails the build. `deckgen build --snap` remakes them first. A page that
  makes no canvas (an error before `createCanvas`) writes no still, so a committed one is never
  replaced by a blank image.
- **`code_slide`** sets the code at `deckgen.CODE` when it fits the half-width panel, and steps
  down to `CODE_SMALL` or 22 px when it does not; a line too wide even then is an error, not a
  wrap.

## On a phone

reveal.js fits the 1920×1080 canvas to the viewport, so on a 390px screen the body text
lands at about **7px** and the exercise box is too small to type in. Scaling cannot fix
that, so every deck also carries a **reading view**: the same slides, reflowed into a
single readable column.

- **Automatic** on a narrow viewport, or portrait on a touch device. A **Reading view**
  button appears below 900px, and the deck has a **Deck view** button back.
- **The choice is remembered.** Until one is made, rotating to landscape returns the deck.
- **Exercises are moved, not copied.** There is one widget per exercise in the document
  and it is relocated between the two views, so its id, its saved answer and its pass/fail
  state cannot diverge. The editor is set at 16px there, which is the threshold below
  which iOS zooms on focus.
- **Printing always gets the deck**, whatever the device or the saved choice — the PDF is
  produced from this same page.

The reading view is built from the same slide data, with roles inferred from what the
layouts already encode: size, font, caps, bullets. Code is the exception — it is declared
by the layout (`name='code'`), because inferring it from "monospaced and biggish" turned
agenda numbers, timeline years and quote attributions into code blocks. Short mono labels
— a choice letter, an agenda number, a start time — are folded into the line they label,
except where that would cost a slide its heading.

It is a reading and exercise surface, not a reproduction of the deck: decorative rules and
panels are dropped, and images keep their place but not their composition.

## Tests

```bash
python tests/runtime.test.py     # the Python half, against the real interpreter
python tests/reports.test.py     # report links: the mapping contract, and the anchor
npm install --no-save jsdom
node tests/wiring.test.js        # the DOM half, Pyodide stubbed
node tests/handout.test.js       # the reading view: switching, and moving the widgets
node tests/browser.test.js       # the whole thing: real Chromium, real Pyodide, real phone
python tests/sketch.test.py      # live sketches: the twin, the geometry, a build with no still
python tests/syntax.test.py      # the code colours: the lexer, and every path that carries them
node tests/sketch.test.js        # live sketches in Chromium: mouse mapping, key relay, chip, print, snap
```

The JS suites build `tests/fixture/` (and `sketch.test.js` its own `tests/fixture-sketch/`)
themselves, so they need `deckgen` on `PATH`. `browser.test.js` and `sketch.test.js`
additionally need Playwright's Chromium; on Arch that means
`nss nspr at-spi2-core libxcomposite libxdamage libxrandr libxkbcommon libcups`.

**Run `browser.test.js` before shipping a change to the runtime or the reading view.** It
is the only suite with layout and a real reveal.js in it, and every bug it has found was
invisible to the other three: reveal cloning every slide below 435px, CSS overrides that
never matched because a node was inserted beside its slot instead of inside it, and
Pyodide handing JS `null` across as a sentinel that is not `None`.

`runtime.test.py` needs nothing but CPython — Pyodide runs the same interpreter, so what
passes there passes in the browser. `wiring.test.js` drives a built deck with a stubbed
Pyodide and checks status classes, output, `localStorage`, reset, the console and the
keyboard hand-off.

Once a report is attached, the ClassPoint chip in the bottom corner of the html slide
becomes a link to the activity page ("Short answer · see the answers"), and the reading
view's ClassPoint line links too. Before that it is a badge saying what kind of activity
the slide runs.
