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
deck/assets/           images (deck/assets/generated/ is built, git-ignored)
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
`team_band` `two_col` `figure_slide` `end`. Inline markup in any string: `**bold**`,
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
deckgen build [--site] [--pptx] [--no-pdf] [DECK ...]
deckgen init [DIR]              scaffold a course repo
deckgen template [OUT]          write the ait4x .potx: master + the 8 layouts
deckgen --root PATH ...         act on a repo elsewhere
```

Neither `--site` nor `--pptx` means both. `build` exits non-zero if any text overflows its
box, so a broken slide fails the workflow rather than reaching the projector.
