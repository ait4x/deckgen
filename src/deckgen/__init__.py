"""
deckgen — one slide spec, three outputs.

A course repo declares itself in `deckgen.toml`, writes each deck as a Python module
in `deck/`, and gets an html deck (reveal.js, for GitHub Pages), a PDF of it, an
editable PowerPoint with the ait4x master and live ClassPoint buttons, and png
previews with a text-overflow check — all from the one spec.

    deckgen build            # everything
    deckgen build --pptx     # export/ only, no node needed
    deckgen build --site     # _site/ only
    deckgen init             # scaffold a new course repo here

In a deck module:

    from deckgen.layouts import title, section, content, question

    FOOTER = 'SD5913 · PFAD'        # optional; deckgen.toml supplies it otherwise
    DECK = {'title': 'Week 2', 'pdf': 'SD5913-week02.pdf', 'slides': [
        title('Week 2', 'Version control'),
        question('Which of these is a commit?', choices=[...], cp='multiple_choice'),
    ]}

The design system is ait4x (PolyU School of Design). See PPTX-EXPORT.md for why
PowerPoint font names carry the weight, and README.md for the repo layout.
"""
from .project import Project, configure, current, find_config
from .reports import attach_reports, activity_url, links as report_links
from .core import (
    # element model
    Slide, Run, Para, Text, Rect, Image, Figure, Embed, Sketch, Exercise,
    # authoring helpers
    T, P, runs, eyebrow, pil_font, text_height,
    # geometry, and the one size for code
    W, H, PX, PT, FONTS, CODE, CODE_SMALL,
    # tokens
    INK, WHITE, PAPER, GRAY, TEAL, TXT, MUTED, LINE, LINE_STRONG,
    ORANGE, VIOLET, PINK, YELLOW, GREEN, BLUE, DEEP_TEAL, RED,
    MUTED_ON_INK, LIGHT_ON_INK, YELLOWS, VIOLETS, TEALS, ORANGES, PINKS,
    # backends
    build_html, build_pptx, build_png, build_pdf, build_all, contact_sheet,
)

__version__ = '0.1.0'

__all__ = [
    'Project', 'configure', 'current', 'find_config',
    'attach_reports', 'activity_url', 'report_links',
    'Slide', 'Run', 'Para', 'Text', 'Rect', 'Image', 'Figure', 'Embed', 'Sketch', 'Exercise',
    'T', 'P', 'runs', 'eyebrow', 'pil_font', 'text_height',
    'W', 'H', 'PX', 'PT', 'FONTS', 'CODE', 'CODE_SMALL',
    'INK', 'WHITE', 'PAPER', 'GRAY', 'TEAL', 'TXT', 'MUTED', 'LINE', 'LINE_STRONG',
    'ORANGE', 'VIOLET', 'PINK', 'YELLOW', 'GREEN', 'BLUE', 'DEEP_TEAL', 'RED',
    'MUTED_ON_INK', 'LIGHT_ON_INK', 'YELLOWS', 'VIOLETS', 'TEALS', 'ORANGES', 'PINKS',
    'build_html', 'build_pptx', 'build_png', 'build_pdf', 'build_all', 'contact_sheet',
    '__version__',
]
