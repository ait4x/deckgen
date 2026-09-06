"""
Where a course repo keeps its things.

The generator used to derive every path from `Path(__file__).parent.parent`, which
only worked when it lived inside the one repo it built. A Project carries those
paths instead, so the same package builds any number of courses.

A repo declares itself in `deckgen.toml` at its root:

    [course]
    code     = "SD5913"
    name     = "Programming for Artists and Designers"
    year     = "2026/27"
    school   = "PolyU School of Design"
    footer   = "SD5913 · PFAD"        # optional; defaults to "<code> · <name>", upper-cased
    decks    = ["week02"]
    artifact = "sd5913-powerpoints"   # optional; the Actions artifact name

    [[nav]]                            # the doc-page nav bar, in order
    label = "SD5913"
    href  = "index.html"

    [[publish]]                        # markdown published on the site; everything
    src   = "SD5913-syllabus-2026.md"  # else is built to export/docs only
    out   = "syllabus.html"
    title = "SD5913 · Syllabus 2026/27"

Paths are conventional and relative to the repo root: deck/, deck/assets/,
syllabus/, lessons/, site/, and the two git-ignored outputs _site/ and export/.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_NAME = 'deckgen.toml'


@dataclass
class Project:
    root: Path
    code: str = 'COURSE'
    name: str = ''
    year: str = ''
    school: str = 'PolyU School of Design'
    footer: str = ''
    decks: list = field(default_factory=list)
    artifact: str = ''
    nav: list = field(default_factory=list)       # [{label, href}]
    publish: list = field(default_factory=list)   # [{src, out, title}]

    def __post_init__(self):
        self.root = Path(self.root).resolve()
        if not self.footer:
            self.footer = f'{self.code} · {self.name}'.strip(' ·').upper()
        if not self.artifact:
            self.artifact = f'{self.code.lower()}-powerpoints'

    # ── source dirs ──
    @property
    def decks_dir(self): return self.root / 'deck'
    @property
    def assets(self): return self.root / 'deck' / 'assets'
    @property
    def generated(self): return self.assets / 'generated'
    @property
    def site_src(self): return self.root / 'site'
    @property
    def doc_sources(self):
        """Markdown built to .docx (and .html): the syllabus and the lesson plans."""
        return sorted((self.root / 'syllabus').glob('*.md')) + sorted((self.root / 'lessons').glob('*.md'))

    # ── build outputs (git-ignored) ──
    @property
    def site(self): return self.root / '_site'
    @property
    def export(self): return self.root / 'export'

    @property
    def eyebrow(self):
        return ' · '.join(p for p in (self.school, self.code, self.year) if p).upper()

    def resolve_asset(self, src) -> Path:
        """Deck images are named relative to deck/assets; absolute paths pass through."""
        p = Path(src)
        return p if p.is_absolute() else self.assets / p

    @classmethod
    def load(cls, start: Path | str | None = None) -> 'Project':
        """Find deckgen.toml in `start` or a parent, and read it."""
        cfg = find_config(start)
        data = tomllib.loads(cfg.read_text(encoding='utf-8'))
        course = dict(data.get('course') or {})
        return cls(root=cfg.parent, **course,
                   nav=list(data.get('nav') or []), publish=list(data.get('publish') or []))


def find_config(start: Path | str | None = None) -> Path:
    here = Path(start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        if (d / CONFIG_NAME).is_file():
            return d / CONFIG_NAME
    raise FileNotFoundError(f'no {CONFIG_NAME} in {here} or any parent — is this a course repo?')


# The project the current build is for. `deckgen.configure()` sets it; the backends
# read it. One project per process, which is what a build is.
_current: Project | None = None


def configure(project: Project | Path | str | None = None) -> Project:
    global _current
    _current = project if isinstance(project, Project) else Project.load(project)
    return _current


def current() -> Project:
    return _current if _current is not None else configure()
