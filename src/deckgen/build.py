"""
Build a course repo: every deck in `[course].decks`, then the documents.

    from deckgen.build import build_repo
    build_repo(site=True, pptx=True)

`_site/` gets the landing page and the repo's `site/` overlay, the reveal.js vendor
bundle that ships with the package, one folder per deck (html + assets + PDF), and
the published markdown. `export/` gets the PowerPoints, the ClassPoint manifests,
the .docx documents and the preview contact sheets. Both are git-ignored.
"""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

from . import core, docs
from .project import Project, current

SCAFFOLD = Path(__file__).resolve().parent / 'scaffold'


def load_deck(proj: Project, name: str):
    """Import deck/<name>.py as a module without requiring the repo to be a package."""
    path = proj.decks_dir / f'{name}.py'
    if not path.is_file():
        raise FileNotFoundError(f'{path} — listed in deckgen.toml but not present')
    spec = importlib.util.spec_from_file_location(f'deck_{name}', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def stage_site(proj: Project):
    """Fresh _site/: the package's vendor bundle, then the repo's site/ on top of it."""
    if proj.site.exists():
        shutil.rmtree(proj.site)
    shutil.copytree(SCAFFOLD / 'site', proj.site)
    if proj.site_src.is_dir():
        shutil.copytree(proj.site_src, proj.site, dirs_exist_ok=True)
    (proj.site / '.nojekyll').touch()


def build_repo(site=True, pptx=True, pdf=True, decks=None) -> list[str]:
    """Build the repo. Returns the layout warnings (text that overflows its box)."""
    proj = current()
    if site:
        stage_site(proj)
    problems = []
    for name in (decks or proj.decks):
        mod = load_deck(proj, name)
        footer = getattr(mod, 'FOOTER', None) or proj.footer
        out = core.build_all(mod.DECK, name, footer,
                             do_pptx=pptx, do_html=site, do_png=True, do_pdf=site and pdf)
        n = len(mod.DECK['slides'])
        cp = sum(1 for s in mod.DECK['slides'] if s.cp)
        made = [str(out[k].relative_to(proj.root)) for k in ('html', 'pdf', 'classpoint') if k in out]
        print(f'{name}: {n} slides, {cp} ClassPoint activities -> ' + ', '.join(made))
        problems += [f'{name}: {w}' for w in out.get('warnings') or []]
    docs.main(site=site, export=pptx)
    for p in problems:
        print('WARNING', p)
    if site:
        files = [f for f in proj.site.rglob('*') if f.is_file()]
        print(f'_site: {len(files)} files, {sum(f.stat().st_size for f in files) / 1e6:.1f} MB')
    return problems
