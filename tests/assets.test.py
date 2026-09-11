"""
copy_asset: images reach the html assets dir as jpeg (or png with alpha), downscaled; an animated gif
is copied as it is, every frame kept, because a re-encoding would keep one frame of it.

    python tests/assets.test.py
"""
import pathlib
import sys
import tempfile

from PIL import Image as PImage

from deckgen import Project, configure
from deckgen.core import copy_asset

fails = []


def check(name, cond, extra=''):
    print(('  ok   ' if cond else '  FAIL ') + name + (f'  ({extra})' if extra else ''))
    if not cond:
        fails.append(name)


tmp = pathlib.Path(tempfile.mkdtemp(prefix='deckgen-assets-'))
proj = configure(Project(root=tmp, code='T', name='t', decks=['d']))
proj.assets.mkdir(parents=True)
out = tmp / 'site' / 'assets'

# a two-frame animation
frames = [PImage.new('RGB', (32, 24), c) for c in ((255, 0, 0), (0, 0, 255))]
frames[0].save(proj.assets / 'zoom.gif', save_all=True, append_images=frames[1:], duration=100, loop=0)
name = copy_asset('zoom.gif', out)
check('an animated gif keeps its name and extension', name == 'zoom.gif', name)
check('and its bytes: every frame', (out / 'zoom.gif').read_bytes() == (proj.assets / 'zoom.gif').read_bytes())
check('and it still animates', getattr(PImage.open(out / 'zoom.gif'), 'n_frames', 1) == 2)

# a one-frame gif and a big png go the usual way: jpeg, at most 1920 px
PImage.new('RGB', (32, 24), (0, 200, 0)).save(proj.assets / 'still.gif')
check('a one-frame gif becomes a jpeg', copy_asset('still.gif', out) == 'still.jpg')
PImage.new('RGB', (4000, 1000), (200, 30, 30)).save(proj.assets / 'wide.png')
name = copy_asset('wide.png', out)
check('an opaque png becomes a jpeg, downscaled to 1920', name == 'wide.jpg' and PImage.open(out / name).size == (1920, 480))
check('a missing image is None', copy_asset('nope.png', out) is None)

print(f'{len(fails)} failed' if fails else 'all ok')
sys.exit(1 if fails else 0)
