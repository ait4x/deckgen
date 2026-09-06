"""
A drawing surface for slide figures.

The same geometry is drawn twice — as SVG (for the html deck) and with PIL (for the
pptx and the png preview) — so both outputs carry the identical illustration.
A figure function builds a Canvas and returns `c.finish(name)`, i.e. (svg_markup, png_path);
`deckgen.layouts.figure_slide` takes that pair. Course-specific figures live in the
course repo, not here.

    from deckgen.figures import Canvas, INK, ORANGE

    def my_figure(name='thing', w=800, h=400):
        c = Canvas(w, h)
        c.rect(0, 0, 200, 100, fill=ORANGE)
        c.text(100, 60, 'hello', anchor='middle')
        return c.finish(name)
"""
from __future__ import annotations

import math
import random
from PIL import Image, ImageDraw

from .project import current

INK, ORANGE, MUTED, LINE, TEAL, VIOLET = '#000B1C', '#ED6D24', '#5C6470', '#E1E1DE', '#64C2C3', '#943890'


class Canvas:
    """Tiny dual backend: collects SVG and draws PIL at the same time."""

    def __init__(self, w, h, bg=None, scale=2):
        self.w, self.h, self.scale = w, h, scale
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">']
        self.im = Image.new('RGBA', (w * scale, h * scale), (0, 0, 0, 0) if bg is None else bg)
        self.d = ImageDraw.Draw(self.im)
        if bg:
            self.svg.append(f'<rect width="{w}" height="{h}" fill="{bg}"/>')

    def s(self, v):
        return v * self.scale

    def line(self, x1, y1, x2, y2, color=INK, width=3, cap='round'):
        self.svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{width}" stroke-linecap="{cap}"/>')
        self.d.line([self.s(x1), self.s(y1), self.s(x2), self.s(y2)], fill=color, width=max(1, round(self.s(width))))
        if cap == 'round':
            r = self.s(width) / 2
            for (x, y) in ((x1, y1), (x2, y2)):
                self.d.ellipse([self.s(x) - r, self.s(y) - r, self.s(x) + r, self.s(y) + r], fill=color)

    def poly(self, pts, fill=None, stroke=None, width=3):
        p = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
        self.svg.append(f'<polygon points="{p}" fill="{fill or "none"}" stroke="{stroke or "none"}" stroke-width="{width}" stroke-linejoin="round"/>')
        spts = [(self.s(x), self.s(y)) for x, y in pts]
        self.d.polygon(spts, fill=fill, outline=stroke, width=max(1, round(self.s(width))) if stroke else 0)

    def rect(self, x, y, w, h, fill=None, stroke=None, width=3):
        self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill, stroke, width)

    def circle(self, cx, cy, r, fill=None, stroke=None, width=3):
        self.svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill or "none"}" stroke="{stroke or "none"}" stroke-width="{width}"/>')
        self.d.ellipse([self.s(cx - r), self.s(cy - r), self.s(cx + r), self.s(cy + r)], fill=fill, outline=stroke, width=max(1, round(self.s(width))) if stroke else 0)

    def text(self, x, y, t, size=20, color=MUTED, mono=True, anchor='start', weight=500):
        fam = "'JetBrains Mono',Menlo,Consolas,monospace" if mono else "'Inter',Helvetica,Arial,sans-serif"
        ta = {'start': 'start', 'middle': 'middle', 'end': 'end'}[anchor]
        self.svg.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{ta}">{t}</text>')
        from .core import pil_font
        f = pil_font('monomed' if mono else 'semibold', round(self.s(size)))
        tw = f.getlength(t)
        ax = {'start': 0, 'middle': tw / 2, 'end': tw}[anchor]
        asc, desc = f.getmetrics()
        self.d.text((self.s(x) - ax, self.s(y) - asc), t, font=f, fill=color)

    def finish(self, name):
        """Write the png into deck/assets/generated/ and return (svg, png_path)."""
        self.svg.append('</svg>')
        out = current().generated
        out.mkdir(parents=True, exist_ok=True)
        p = out / f'{name}.png'
        self.im.save(p)
        return '\n'.join(self.svg), str(p)
