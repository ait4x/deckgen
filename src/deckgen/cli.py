"""
`deckgen` on the command line.

    deckgen build [--site] [--pptx] [--no-pdf] [DECK ...]
    deckgen init [DIR]          scaffold a course repo (deckgen.toml, deck/, workflows)
    deckgen template [OUT]      write the ait4x .potx: master + the 8 layouts

With neither --site nor --pptx, `build` does both. --no-pdf skips the Chromium step,
which is the only part that needs node.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .project import CONFIG_NAME, configure

SCAFFOLD = Path(__file__).resolve().parent / 'scaffold'


def cmd_build(args):
    from .build import build_repo
    proj = configure(args.root)
    explicit = args.site or args.pptx
    print(f'{proj.code} — {proj.root}')
    problems = build_repo(site=args.site or not explicit,
                          pptx=args.pptx or not explicit,
                          pdf=not args.no_pdf,
                          decks=args.decks or None)
    return 1 if problems else 0


def cmd_template(args):
    from . import classpoint
    proj = configure(args.root)
    out = Path(args.out) if args.out else proj.export / 'ait4x-template.potx'
    out.parent.mkdir(parents=True, exist_ok=True)
    classpoint.template(out, footer=proj.footer)
    return 0


def cmd_init(args):
    dest = Path(args.dir).resolve()
    if (dest / CONFIG_NAME).exists():
        print(f'{dest / CONFIG_NAME} already exists — nothing to do', file=sys.stderr)
        return 1
    # site/ is the vendor bundle, staged into _site/ at build time — not copied here.
    # Dotted names ship undotted (wheels are unreliable about dotfiles) and are restored now.
    shutil.copytree(SCAFFOLD, dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('site', 'dot-gitignore', 'github'))
    shutil.copy(SCAFFOLD / 'dot-gitignore', dest / '.gitignore')
    shutil.copytree(SCAFFOLD / 'github', dest / '.github', dirs_exist_ok=True)
    for sub in ('deck/assets', 'syllabus', 'lessons', 'site'):
        (dest / sub).mkdir(parents=True, exist_ok=True)
        (dest / sub / '.gitkeep').touch()
    print(f'scaffolded {dest}: edit {CONFIG_NAME}, then `deckgen build --pptx`')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog='deckgen', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', help=f'repo root, or any dir under it (default: cwd, searched upward for {CONFIG_NAME})')
    sp = ap.add_subparsers(dest='cmd', required=True)

    b = sp.add_parser('build', help='build the decks and documents')
    b.add_argument('--site', action='store_true', help='_site/ only: html decks, PDFs, published markdown')
    b.add_argument('--pptx', action='store_true', help='export/ only: PowerPoints, manifests, docx, previews')
    b.add_argument('--no-pdf', action='store_true', help='skip the Chromium PDF step (no node needed)')
    b.add_argument('decks', nargs='*', help='deck names; default: [course].decks in deckgen.toml')
    b.set_defaults(fn=cmd_build)

    t = sp.add_parser('template', help='write the ait4x PowerPoint template (.potx)')
    t.add_argument('out', nargs='?')
    t.set_defaults(fn=cmd_template)

    i = sp.add_parser('init', help='scaffold a course repo')
    i.add_argument('dir', nargs='?', default='.')
    i.set_defaults(fn=cmd_init)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == '__main__':
    sys.exit(main())
