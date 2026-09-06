"""
Slide layouts — the eight ait4x layouts (Title, Section band, Content white,
Content ink, Two column, Question, Quote, Statement) plus the ones a course
usually wants (agenda, cards, timeline, journey map, activity step, video,
assessment, team, image_full, statement, figure_slide).

Every function returns a deckgen.Slide made of absolute elements on the
1920 x 1080 canvas. Geometry mirrors deckgen.classpoint so the PowerPoint export
sits on the same grid as the master layouts installed there.
"""
from __future__ import annotations

import re
from pathlib import Path

from .core import (Slide, Text, Para, Rect, Image, Figure, Embed, Exercise, T, P, runs, eyebrow, CODE, CODE_SMALL,
                     INK, WHITE, PAPER, GRAY, TEAL, TXT, MUTED, LINE, LINE_STRONG, ORANGE, VIOLET, PINK, YELLOW, GREEN, BLUE,
                     MUTED_ON_INK, LIGHT_ON_INK, YELLOWS, VIOLETS, TEALS, ORANGES, PINKS)

LOGO = str(Path(__file__).resolve().parent / 'assets' / 'polyu-design-logo.png')
LIGHT_BGS = {WHITE, PAPER}

M = 120            # margin
CW = 1680          # content width
TITLE_Y = 184


def _dark(bg):
    return bg not in LIGHT_BGS and bg not in YELLOWS and bg not in TEALS[1:] and bg not in VIOLETS[2:] and bg not in ORANGES[1:] and bg not in PINKS[1:]


def palette(bg):
    """(title, body, muted) colours for a background."""
    if _dark(bg):
        return WHITE, LIGHT_ON_INK, MUTED_ON_INK
    return INK, TXT, MUTED


def wordmark(x=1600, y=968, size=32, color=WHITE):
    paras = [Para([*runs('a·t4', 'black', size, color, spc=-0.04), *runs('x', 'black', size, ORANGE, spc=-0.04)], 'r', 1.0)]
    return Text(x, y, 200, size + 8, paras, 'b', name='chrome-wordmark')


def body_paras(lines, size=36, color=TXT, lh=1.4, gap=18, font='body'):
    """Strings -> paragraphs. '- ' prefix = orange dot bullet. '' = spacer."""
    out = []
    for i, line in enumerate(lines):
        if line == '':
            continue
        bullet = line.startswith('- ')
        txt = line[2:] if bullet else line
        out.append(P(txt, font, size, color, lh, before=gap if i else 0, bullet=bullet))
    return out


# ───────────────────────── chrome (footer, number, logo) ─────────────────────────
def add_chrome(slide, n, footer):
    t, b, m = palette(slide.bg)
    slide.els.append(T(M, 1000, 1000, 32, footer, 'monomed', 22, m, lh=1.2, valign='b', spc=0.14, caps=True, name='chrome-footer'))
    slide.els.append(T(1400, 1000, 400, 32, f'{n:02d}', 'monomed', 22, m, lh=1.2, align='r', valign='b', spc=0.14, name='chrome-num'))
    if slide.bg == WHITE:
        slide.els.append(Image(1668, 74, 132, 88, LOGO, 'contain', name='chrome-logo'))


def finalize(slides, footer):
    for i, s in enumerate(slides, start=1):
        if getattr(s, 'chrome', True):
            add_chrome(s, i, footer)
    return slides


def _slide(bg=WHITE, notes='', cp=None, title='', chrome=True):
    s = Slide(bg=bg, notes=notes, cp=cp, title=title)
    s.chrome = chrome
    return s


# ───────────────────────── layouts ─────────────────────────
def title(eyebrow_text, title_text, sub, notes='', size=150, mark=False):
    s = _slide(INK, notes, title=title_text, chrome=False)
    s.els += [
        eyebrow(M, 560, eyebrow_text, MUTED_ON_INK),
        T(M, 620, CW, 300, title_text, 'black', size, WHITE, lh=0.88, valign='b', spc=-0.045),
        T(M, 940, 1400, 60, sub, 'body', 36, LIGHT_ON_INK, lh=1.2),
    ]
    if mark:  # the a·t4x wordmark; off by default on the title (it stays on the end slide)
        s.els.append(wordmark())
    return s


def end(title_text, sub, site, notes=''):
    s = _slide(INK, notes, title=title_text, chrome=False)
    s.els += [
        T(M, 560, CW, 360, title_text, 'black', 130, WHITE, lh=0.88, valign='b', spc=-0.045),
        T(M, 940, 1400, 60, sub, 'body', 36, LIGHT_ON_INK, lh=1.2),
        eyebrow(M, 1000, site, MUTED_ON_INK, size=22),
        wordmark(),
    ]
    return s


def agenda(eyebrow_text, items, notes='', title_text='Today'):
    s = _slide(WHITE, notes, title=title_text)
    s.els += [eyebrow(M, 96, eyebrow_text), T(M, TITLE_Y, CW, 140, title_text, 'xbold', 72, INK, lh=0.95, spc=-0.03)]
    per_col = (len(items) + 1) // 2
    for i, label in enumerate(items):
        col, row = divmod(i, per_col)
        x = M + col * 880
        y = 372 + row * 140
        s.els += [
            T(x, y + 10, 62, 56, f'{i + 1:02d}', 'monomed', 28, ORANGE, lh=1.2),
            # 88px, not 76: two lines at 36/1.2 are 86.4px, and an agenda item that wraps
            # is normal. Raised by 6 so the centre stays put and one-line items do not move.
            T(x + 92, y - 6, 700, 88, label, 'body', 36, INK, lh=1.2, valign='m'),
            Rect(x, y + 92, 800, 2, LINE),
        ]
    return s


def section(num, title_text, kicker, notes='', bg=VIOLET):
    dark = _dark(bg)
    tint = '#F2ECF5' if dark else INK
    s = _slide(bg, notes, title=title_text)
    s.els += [
        eyebrow(M, 560, num, tint),
        T(M, 620, CW, 300, title_text, 'black', 130, WHITE if dark else INK, lh=0.88, valign='b', spc=-0.045),
        T(M, 940, 1400, 60, kicker, 'monomed', 28, tint, lh=1.2, spc=0.14, caps=True),
    ]
    return s


def statement(text, eyebrow_text=None, notes='', size=120, bg=INK):
    t, b, m = palette(bg)
    s = _slide(bg, notes, title=text[:60])
    if eyebrow_text:
        s.els.append(eyebrow(M, 96, eyebrow_text, m))
    s.els.append(T(M, TITLE_Y, CW, 760, text, 'black', size, t, lh=0.92, valign='m', spc=-0.04))
    return s


def quote(text, who, image=None, notes='', size=80, bg=PAPER, fit='cover'):
    t, b, m = palette(bg)
    s = _slide(bg, notes, title=text[:60])
    if image:
        s.els.append(Image(M, TITLE_Y, 560, 766, image, fit))
        s.els += [T(780, 300, 1020, 500, text, 'xbold', size, t, lh=1.0, valign='m', spc=-0.03),
                  T(780, 840, 1020, 80, who, 'mono', 26, m, lh=1.3)]
    else:
        s.els += [T(M, 300, 1600, 500, text, 'xbold', size, t, lh=1.0, valign='m', spc=-0.03),
                  T(M, 840, 1600, 80, who, 'mono', 26, m, lh=1.3)]
    return s


def content(eyebrow_text, title_text, body, image=None, figure=None, fit='cover', notes='', bg=WHITE, body_size=36, title_size=72, caption=None, cp=None, images=None):
    """Title + body; optional media on the right: image path, figure (svg, png), or a list of images (grid)."""
    t, b, m = palette(bg)
    s = _slide(bg, notes, cp=cp, title=title_text)
    s.els.append(eyebrow(M, 96, eyebrow_text, m))
    media = image or figure or images
    if media:
        s.els.append(T(M, TITLE_Y, 800, 260, title_text, 'xbold', title_size, t, lh=0.95, spc=-0.03))
        s.els.append(Text(M, 480, 800, 470, body_paras(body, body_size, b), 't'))
        box = (1000, TITLE_Y, 800, 766 if not caption else 680)
        if image:
            s.els.append(Image(*box, image, fit))
        elif figure:
            svg, png = figure
            s.els.append(_fit_figure(box, svg, png))
        else:
            s.els += image_grid(images, *box)
        if caption:
            s.els.append(T(1000, TITLE_Y + 692, 800, 80, caption, 'mono', 20, m, lh=1.3))
    else:
        s.els.append(T(M, TITLE_Y, CW, 140, title_text, 'xbold', title_size, t, lh=0.95, spc=-0.03))
        s.els.append(Text(M, 372, CW, 580, body_paras(body, body_size, b), 't'))
    return s


def _fit_figure(box, svg, png):
    from PIL import Image as PImage
    x, y, w, h = box
    iw, ih = PImage.open(png).size
    r = min(w / iw, h / ih)
    fw, fh = round(iw * r), round(ih * r)
    return Figure(x + (w - fw) // 2, y, fw, fh, svg, png)


def image_grid(paths, x, y, w, h, gap=16):
    n = len(paths)
    cols = 2 if n <= 4 else 3 if n <= 9 else 4
    rows = (n + cols - 1) // cols
    cw = (w - gap * (cols - 1)) // cols
    ch = (h - gap * (rows - 1)) // rows
    side = min(cw, ch)
    out = []
    for i, p in enumerate(paths):
        r, c = divmod(i, cols)
        out.append(Image(x + c * (side + gap), y + r * (side + gap), side, side, p, 'cover'))
    return out


def figure_slide(eyebrow_text, title_text, figure, notes='', bg=WHITE, caption=None, body=None, cp=None):
    """Title on top, a wide figure below (max 1680 x 640)."""
    t, b, m = palette(bg)
    s = _slide(bg, notes, cp=cp, title=title_text)
    s.els += [eyebrow(M, 96, eyebrow_text, m), T(M, TITLE_Y, CW, 110, title_text, 'xbold', 64, t, lh=0.95, spc=-0.03)]
    svg, png = figure
    top = 320
    if body:
        s.els.append(Text(M, 300, CW, 90, body_paras(body, 30, b, lh=1.3), 't'))
        top = 400
    bottom = 896 if caption else 960
    s.els.append(_fit_figure((M, top, CW, bottom - top), svg, png))
    if caption:
        s.els.append(T(M, 912, CW, 80, caption, 'mono', 20, m, lh=1.3))
    return s


def cards(eyebrow_text, title_text, items, notes='', bg=WHITE, head_size=None, text_size=None, cp=None, sub=None):
    """items: (label, heading, text). Laid out as one row of hairline cards."""
    t, b, m = palette(bg)
    s = _slide(bg, notes, cp=cp, title=title_text)
    s.els += [eyebrow(M, 96, eyebrow_text, m), T(M, TITLE_Y, CW, 140, title_text, 'xbold', 72, t, lh=0.95, spc=-0.03)]
    n = len(items)
    gap = 40
    w = (CW - gap * (n - 1)) // n
    hs = head_size or (44 if n <= 2 else 40 if n == 3 else 34 if n == 4 else 30)
    ts = text_size or (30 if n <= 3 else 26 if n == 4 else 24)
    y0 = 372 if not sub else 400
    if sub:
        s.els.append(T(M, 330, CW, 50, sub, 'body', 30, m, lh=1.3))
    for i, (label, head, text) in enumerate(items):
        x = M + i * (w + gap)
        s.els += [
            Rect(x, y0, w, 2, LINE if not _dark(bg) else '#2A3644'),
            T(x, y0 + 24, w, 36, label, 'monomed', 22, ORANGE, lh=1.2, spc=0.14, caps=True),
            T(x, y0 + 76, w, 130, head, 'xbold', hs, t, lh=1.05, spc=-0.02),
            Text(x, y0 + 216, w, 980 - (y0 + 216), body_paras(text if isinstance(text, list) else [text], ts, b, lh=1.4, gap=12), 't'),  # ends above the footer
        ]
    return s


KIND_LABEL = {'word_cloud': 'Word cloud', 'multiple_choice': 'Multiple choice', 'short_answer': 'Short answer', 'image_upload': 'Image upload'}


def question(kind, question_text, choices=None, hint=None, notes='', eyebrow_text=None, size=None, cp=None, bg=WHITE, example=None):
    t, b, m = palette(bg)
    s = _slide(bg, notes, title=question_text)
    s.els.append(eyebrow(M, 96, eyebrow_text or f'QUESTION · {KIND_LABEL[kind]}', m))
    n = len(question_text)
    qs = size or (110 if n <= 34 else 92 if n <= 60 else 76 if n <= 90 else 64)
    if choices:
        s.els.append(T(M, 200, CW, 440, question_text, 'black', qs, t, lh=0.92, valign='m', spc=-0.04))
        y = 680
        rh = 76 if len(choices) <= 3 else 68
        for i, ch in enumerate(choices):
            letter = 'ABCDEF'[i]
            s.els += [
                Rect(M, y, 64, 56, INK if not _dark(bg) else WHITE),
                T(M, y, 64, 56, letter, 'monomed', 28, WHITE if not _dark(bg) else INK, lh=1.2, align='c', valign='m'),
                T(M + 92, y, 1200, 56, ch, 'body', 34, t, lh=1.2, valign='m'),
            ]
            y += rh
        cp = cp or {'type': 'multiple_choice', 'choices': ['ABCDEF'[i] for i in range(len(choices))]}
    else:
        s.els.append(T(M, 240, CW, 420, question_text, 'black', qs, t, lh=0.92, valign='m', spc=-0.04))
        if hint:
            s.els.append(T(M, 700, 1300, 120, hint, 'body', 32, m, lh=1.35))
        if example:
            s.els.append(T(M, 840, 1300, 100, example, 'mono', CODE_SMALL, m, lh=1.4))
        cp = cp or ({'type': 'word_cloud', 'submissions': 1} if kind == 'word_cloud'
                    else {'type': 'image_upload', 'hide_names': False} if kind == 'image_upload'
                    else {'type': 'short_answer', 'hide_names': False, 'multiple': False})
    s.cp = cp
    return s


def image_full(src, eyebrow_text, caption, notes='', fit='cover', bg=INK, n=None):
    s = _slide(bg, notes, title=caption[:60], chrome=False)
    if fit == 'cover':
        s.els.append(Image(0, 0, 1920, 960, src, 'cover'))
    else:
        s.els.append(Image(M, 40, CW, 880, src, 'contain'))
    s.els += [Rect(0, 960, 1920, 120, INK),
              eyebrow(M, 972, eyebrow_text, MUTED_ON_INK, size=22),
              T(M, 1006, 1560, 64, caption, 'body', 24, WHITE, lh=1.2),
              ]
    s.caption_band = True
    return s


def timeline(eyebrow_text, title_text, items, notes='', bg=WHITE):
    """items: (year, label, sub) — up to 8 across."""
    t, b, m = palette(bg)
    s = _slide(bg, notes, title=title_text)
    s.els += [eyebrow(M, 96, eyebrow_text, m), T(M, TITLE_Y, CW, 140, title_text, 'xbold', 72, t, lh=0.95, spc=-0.03)]
    n = len(items)
    w = CW // n
    s.els.append(Rect(M, 560, CW, 3, LINE))
    for i, (year, label, sub) in enumerate(items):
        x = M + i * w
        s.els += [
            T(x, 470, w - 24, 40, str(year), 'monomed', 26, ORANGE, lh=1.2, spc=0.06),
            Rect(x, 552, 18, 18, INK if not _dark(bg) else WHITE),
            T(x, 600, w - 28, 110, label, 'xbold', 27, t, lh=1.05, spc=-0.02),
            Text(x, 716, w - 28, 240, body_paras([sub], 22, b, lh=1.3), 't'),
        ]
    return s


def journey(eyebrow_text, title_text, rows, notes='', bg=WHITE, here=None):
    """rows: dict(label, color, dark(bool), cells=[(week, title)]). here=(row_index, cell_index)."""
    t, b, m = palette(bg)
    s = _slide(bg, notes, title=title_text)
    s.els += [eyebrow(M, 96, eyebrow_text, m), T(M, TITLE_Y, CW, 110, title_text, 'xbold', 64, t, lh=0.95, spc=-0.03)]
    y = 318
    rh, gap = 98, 10
    for ri, row in enumerate(rows):
        lc = WHITE if row.get('dark') else INK
        s.els += [Rect(M, y, 380, rh, row['color']),
                  T(M + 20, y, 340, rh, row['label'], 'xbold', 26, lc, lh=1.1, valign='m', spc=-0.02)]
        cells = row['cells']
        n = len(cells)
        cx0, cw_total = 520, 1280
        cw = (cw_total - gap * (n - 1)) / n
        for ci, (wk, ttl) in enumerate(cells):
            cx = round(cx0 + ci * (cw + gap))
            s.els += [Rect(cx, y, round(cw), rh, row.get('tint', PAPER)),
                      T(cx + 16, y + 10, round(cw) - 32, 24, wk, 'monomed', 18, m, lh=1.2, spc=0.14, caps=True),
                      T(cx + 16, y + 38, round(cw) - 32, rh - 44, ttl, 'semibold', 22, INK, lh=1.1, valign='t', spc=-0.01)]
            if here == (ri, ci):
                s.els.append(Rect(cx, y, round(cw), rh, None, ORANGE, 5))
        y += rh + gap
    return s


def activity(step, minutes, title_text, body, notes='', bg=YELLOWS[0], eyebrow_text='ACTIVITY', cp=None):
    t, b, m = palette(bg)
    s = _slide(bg, notes, cp=cp, title=title_text)
    s.els += [
        eyebrow(M, 96, f'{eyebrow_text} · {step}', INK),
        T(1300, 60, 500, 130, minutes if isinstance(minutes, str) else f'{minutes} min', 'black', 96, INK, lh=1.0, align='r', spc=-0.04),
        T(M, 300, 1400, 240, title_text, 'xbold', 84, INK, lh=0.95, valign='b', spc=-0.035),
        Text(M, 580, 1400, 380, body_paras(body, 34, INK, lh=1.35), 't'),
    ]
    return s


def video(eyebrow_text, title_text, yt, body, notes='', bg=WHITE, thumb=None, body_size=30):
    t, b, m = palette(bg)
    s = _slide(bg, notes, title=title_text)
    s.els += [
        eyebrow(M, 96, eyebrow_text, m),
        T(M, TITLE_Y, 800, 260, title_text, 'xbold', 72, t, lh=0.95, spc=-0.03),
        Text(M, 480, 800, 470, body_paras(body, body_size, b, lh=1.4), 't'),
        Embed(1000, TITLE_Y, 800, 450, yt, thumb),
    ]
    return s


def assessment(eyebrow_text, title_text, comps, notes='', bg=WHITE):
    """comps: (pct, label, desc, highlight)."""
    t, b, m = palette(bg)
    s = _slide(bg, notes, title=title_text)
    s.els += [eyebrow(M, 96, eyebrow_text, m), T(M, TITLE_Y, CW, 140, title_text, 'xbold', 72, t, lh=0.95, spc=-0.03)]
    n = len(comps)
    gap = 40
    w = (CW - gap * (n - 1)) // n
    for i, (pct, label, desc, hl) in enumerate(comps):
        x = M + i * (w + gap)
        s.els += [
            Rect(x, 372, w, 2, LINE),
            T(x, 396, w, 110, pct, 'black', 88, ORANGE if hl else t, lh=1.0, spc=-0.04),
            T(x, 520, w, 90, label, 'xbold', 30, t, lh=1.05, spc=-0.02),
            Text(x, 620, w, 340, body_paras([desc], 24, b, lh=1.35), 't'),
        ]
    return s


def team(eyebrow_text, title_text, people, notes='', bg=WHITE):
    """people: (name, role, text, color, initials, dark_text)."""
    t, b, m = palette(bg)
    s = _slide(bg, notes, title=title_text)
    s.els += [eyebrow(M, 96, eyebrow_text, m), T(M, TITLE_Y, CW, 140, title_text, 'xbold', 72, t, lh=0.95, spc=-0.03)]
    n = len(people)
    gap = 40
    w = (CW - gap * (n - 1)) // n
    for i, (name, role, text, color, initials, light) in enumerate(people):
        x = M + i * (w + gap)
        s.els += [
            Rect(x, 372, 120, 120, color),
            T(x, 372, 120, 120, initials, 'black', 44, WHITE if light else INK, lh=1.0, align='c', valign='m', spc=-0.04),
            T(x, 520, w, 50, name, 'xbold', 34, t, lh=1.1, spc=-0.02),
            T(x, 574, w, 34, role, 'monomed', 22, ORANGE, lh=1.2, spc=0.1, caps=True),
            Text(x, 630, w, 330, body_paras(text if isinstance(text, list) else [text], 26, b, lh=1.35, gap=10), 't'),
        ]
    return s


def team_band(eyebrow_text, title_text, leads, band_label, assistants, notes='', bg=WHITE):
    """Two wide cards (lecturer, coordinator) over a band of small cards (the teaching assistants).
    leads: (name, role, lines, color, initials, light) · assistants: (name, text, color, initials, light)."""
    t, b, m = palette(bg)
    s = _slide(bg, notes, title=title_text)
    s.els += [eyebrow(M, 96, eyebrow_text, m), T(M, TITLE_Y, CW, 140, title_text, 'xbold', 72, t, lh=0.95, spc=-0.03)]
    gap = 40
    w = (CW - gap * (len(leads) - 1)) // len(leads)
    for i, (name, role, lines, color, initials, light) in enumerate(leads):
        x = M + i * (w + gap)
        s.els += [
            Rect(x, 372, 120, 120, color),
            T(x, 372, 120, 120, initials, 'black', 44, WHITE if light else INK, lh=1.0, align='c', valign='m', spc=-0.04),
            T(x + 152, 372, w - 152, 50, name, 'xbold', 34, t, lh=1.1, spc=-0.02),
            T(x + 152, 424, w - 152, 34, role, 'monomed', 22, ORANGE, lh=1.2, spc=0.1, caps=True),
            Text(x + 152, 470, w - 152, 170, body_paras(lines if isinstance(lines, list) else [lines], 26, b, lh=1.35, gap=8), 't'),
        ]
    y = 660
    s.els += [Rect(M, y, CW, 2, LINE if not _dark(bg) else '#2A3644'),
              T(M, y + 20, CW, 34, band_label, 'monomed', 22, ORANGE, lh=1.2, spc=0.14, caps=True)]
    w = (CW - gap * (len(assistants) - 1)) // len(assistants)
    for i, (name, text, color, initials, light) in enumerate(assistants):
        x = M + i * (w + gap)
        s.els += [
            Rect(x, y + 74, 96, 96, color),
            T(x, y + 74, 96, 96, initials, 'black', 36, WHITE if light else INK, lh=1.0, align='c', valign='m', spc=-0.04),
            T(x, y + 186, w, 44, name, 'xbold', 30, t, lh=1.1, spc=-0.02),
            Text(x, y + 232, w, 100, body_paras([text], 24, b, lh=1.35), 't'),
        ]
    return s


def two_col(eyebrow_text, title_text, left, right, notes='', bg=WHITE, right_bg=PAPER, right_font='mono', right_size=CODE):
    """Body left, a code / text panel right."""
    t, b, m = palette(bg)
    s = _slide(bg, notes, title=title_text)
    s.els += [
        eyebrow(M, 96, eyebrow_text, m),
        T(M, TITLE_Y, 800, 260, title_text, 'xbold', 72, t, lh=0.95, spc=-0.03),
        Text(M, 480, 800, 470, body_paras(left, 34, b, lh=1.4), 't'),
        Rect(1000, TITLE_Y, 800, 766, right_bg),
        Text(1040, TITLE_Y + 40, 720, 690, body_paras(right, right_size, INK if right_bg != INK else LIGHT_ON_INK, lh=1.5, gap=0, font=right_font), 't'),
    ]
    return s


def code_panel(eyebrow_text, title_text, lines, notes='', bg=WHITE, caption=None, cp=None):
    """A slide that is mostly code. One column, full width, at the canonical CODE size."""
    t, b, m = palette(bg)
    s = _slide(bg, notes, cp=cp, title=title_text)
    s.els += [
        eyebrow(M, 96, eyebrow_text, m),
        T(M, TITLE_Y, CW, 140, title_text, 'xbold', 72, t, lh=0.95, spc=-0.03),
        Rect(M, 372, CW, 520 if caption else 580, PAPER if bg is not PAPER else WHITE),
        Text(M + 40, 412, CW - 80, 500, [Para([runs(ln or ' ', 'mono', CODE, INK)[0]], 'l', 1.45)
                                         for ln in lines], 't'),
    ]
    if caption:
        s.els.append(T(M, 916, CW, 60, caption, 'body', 30, m, lh=1.3))
    return s


def exercise(eyebrow_text, title_text, brief, code, check=None, expect=None, eid=None,
             label=None, hint=None, notes='', bg=WHITE, rows=8, cp=None):
    """A drill the room does on their laptops.

    `brief` is the one or two lines telling them what to do — keep it to one idea.
    `code` is what starts in the editor; leave a blank or a `___` where they type.
    Pass either `expect` (the exact stdout you want) or `check` (Python that runs
    afterwards in the same namespace and sets `ok = True`, with `_out` bound to the
    captured stdout). Everything degrades to a static code panel in the pptx and PDF,
    so the deck still reads on a projector with no network.

        exercise('04 · TYPES', 'Make it say 12',
                 'Fix the line so the total prints as a number, not "66".',
                 code='a = "6"\nb = "6"\nprint(a + b)',
                 expect='12')
    """
    t, b, m = palette(bg)
    s = _slide(bg, notes, cp=cp, title=title_text)
    s.els += [
        eyebrow(M, 96, eyebrow_text, m),
        T(M, TITLE_Y, 780, 200, title_text, 'xbold', 64, t, lh=0.98, spc=-0.03),
        Text(M, 400, 780, 300, body_paras(brief if isinstance(brief, list) else [brief],
                                          32, b, lh=1.4, gap=14), 't'),
    ]
    s.els.append(Exercise(940, 184, 860, 766, code,
                          check=check or '', expect=expect,
                          eid=eid or _eid(title_text), label=label or 'YOUR TURN',
                          hint=hint or 'ctrl+enter runs it', rows=rows))
    return s


def _eid(text):
    """A stable, readable id for localStorage — the saved answer must survive a rebuild."""
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:40] or 'ex'
