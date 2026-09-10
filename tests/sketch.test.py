"""
The Python half of the live sketches: the twin, the geometry, the code panel's size, and a
build with no still yet (a labelled box and a warning, not a crash).

    python tests/sketch.test.py
"""
import pathlib
import sys
import tempfile

from deckgen import Project, configure, Sketch, Image, Figure, Editor, CODE, CODE_SMALL, build_html, build_png, build_pptx
from deckgen.core import js_str
from deckgen.layouts import live, place_sketch, sketch_slide, code_slide, content, activity, figure_slide, finalize, _slide
from deckgen.figures import Canvas, ORANGE

fails = []


def check(name, cond, extra=''):
    print(('  ok   ' if cond else '  FAIL ') + name + (f'  ({extra})' if extra else ''))
    if not cond:
        fails.append(name)


tmp = pathlib.Path(tempfile.mkdtemp(prefix='deckgen-sketch-'))
proj = configure(Project(root=tmp, code='T', name='t', decks=['d']))
DOT = 'function setup(){createCanvas(400,300)}\nfunction draw(){background(240);circle(mouseX,mouseY,60)}'

# live() and the twin
sk = live('dot', DOT, 400, 300, hint='move the mouse')
check('live() is a Sketch with a still by default', isinstance(sk, Sketch) and sk.twin and sk.kind == 'sketch')

s = _slide()
frame = place_sketch(s, sk, (120, 320, 1680, 640))
check('fitted to the aspect, centred', frame == (120 + (1680 - 853) // 2, 320, 853, 640), frame)
img = s.els[-1]
check('the still stands in: an Image at the frame with a placeholder', isinstance(img, Image) and (img.x, img.y, img.w, img.h) == frame and img.placeholder and img.src == str(proj.sketches / 'dot.png'))
check('the sketch itself is html-only, at the frame', s.html_only == [sk] and (sk.x, sk.y, sk.w, sk.h) == frame)

c = Canvas(400, 300); c.rect(0, 0, 400, 300, fill=ORANGE); fig = c.finish('box')
s2 = _slide()
sk2 = live('dot2', DOT, 400, 300)
place_sketch(s2, sk2, (120, 320, 1680, 640), figure=fig)
check('with a figure the figure is the twin and no still is needed', isinstance(s2.els[-1], Figure) and sk2.twin is False)
check('the short form (name, js, w, h, hint) works', place_sketch(_slide(), ('dot3', DOT, 400, 300, 'hi'), (0, 0, 800, 600)) == (0, 0, 800, 600))

# code panel sizes
short = 'function setup() {\n  createCanvas(400, 300);\n}'
wide = ('  let x = random(600), y = random(600); // ok').ljust(55)    # 55 chars: 715 px at 22, 880 px at 26
long = short + '\n' + wide
tall = '\n'.join(f'line{i}' for i in range(17))                    # 17 lines: 673 px tall at 30, 583 at 26
check('short code at CODE', code_slide('E', 't', short, sketch=live('a', short)).els[3].paras[0].runs[0].size == CODE)
check('a 55-char line steps down to 22', code_slide('E', 't', long, sketch=live('b', long)).els[3].paras[0].runs[0].size == 22)
check('seventeen lines step down to CODE_SMALL on a static panel', code_slide('E', 't', tall, sketch=live('c', tall), edit=False).els[3].paras[0].runs[0].size == CODE_SMALL)
check('and to 22 when the editor bar takes its 60 px', code_slide('E', 't', tall, sketch=live('c2', tall)).els[3].paras[0].runs[0].size == 22)
try:
    code_slide('E', 't', 'x' * 80, sketch=live('d', 'x'))
    check('a line too wide even at 22 raises', False)
except ValueError as e:
    check('a line too wide even at 22 raises', 'too' in str(e) or 'fit' in str(e))
check('code_size can be forced', code_slide('E', 't', long, code_size=CODE, sketch=live('e', long)).els[3].paras[0].runs[0].size == CODE)

# the editable panel
ed = code_slide('E', 't', short, sketch=live('ed', short, 400, 300), caption='c')
editor = [e for e in ed.html_only if e.kind == 'editor']
check('code_slide with a sketch adds an Editor to the html-only elements', len(editor) == 1 and isinstance(editor[0], Editor))
check('the editor covers the paper panel and carries the code, the sketch and the size',
      editor and (editor[0].x, editor[0].y, editor[0].w, editor[0].h) == (120, 296, 800, 684) and editor[0].code == short
      and editor[0].sketch == 'ed' and editor[0].size == ed.els[3].paras[0].runs[0].size and editor[0].lang == 'js' and editor[0].eid == 'ed')
check('edit=False keeps the panel static', not any(e.kind == 'editor' for e in code_slide('E', 't', short, sketch=live('ed2', short), edit=False).html_only))
check('a code_slide with a figure and no sketch has nothing to run', not any(e.kind == 'editor' for e in code_slide('E', 't', short, figure=fig).html_only))
check('the static panel is still there for the pptx and the reading view', any(getattr(e, 'name', '') == 'code' for e in ed.els))
hint = code_slide('E', 't', short, sketch=live('ed3', short), hint='try a number')
check('the hint is the bar text; an empty one drops it', [e for e in hint.html_only if e.kind == 'editor'][0].hint == 'try a number'
      and [e for e in code_slide('E', 't', short, sketch=live('ed4', short), hint='').html_only if e.kind == 'editor'][0].hint == '')

# the layouts that take a sketch
for name, sl in [('sketch_slide', sketch_slide('E', 't', live('f', DOT, 400, 300), body=['one line'])),
                 ('content', content('E', 't', ['body'], sketch=live('g', DOT, 400, 300))),
                 ('activity', activity('1', 3, 't', ['body'], sketch=live('h', DOT, 400, 300))),
                 ('figure_slide', figure_slide('E', 't', fig, sketch=live('i', DOT, 400, 300)))]:
    check(f'{name} carries one live sketch', len(sl.html_only) == 1 and sl.html_only[0].kind == 'sketch')
check('activity with a panel names it code (reading view)', any(getattr(e, 'name', '') == 'code' for e in activity('1', 3, 't', ['b'], panel=['rule:', 'chance:']).els))

# a build with no still yet
deck = {'title': 'd', 'pdf': 'd.pdf', 'slides': finalize([sketch_slide('E', 'no still yet', live('nostill', DOT, 400, 300, hint='hover'))], 'T')}
files, warnings = build_png(deck, tmp / 'export' / 'preview' / 'd')
check('png preview warns about the missing still', len(warnings) == 1 and 'deckgen snap' in warnings[0], warnings)
pptx, manifest = build_pptx(deck, tmp / 'export' / 'd.pptx', 'T')
check('pptx builds with a labelled box instead', pptx.exists() and pptx.stat().st_size > 10000)
index = build_html(deck, tmp / '_site' / 'd')
html = index.read_text()
page = tmp / '_site' / 'd' / 'sketches' / 'nostill.html'
check('the sketch page is written with the code as a literal and the course', page.exists() and 'code: ' + js_str(DOT) in page.read_text() and '<b>T</b>' in page.read_text())
check('the page runs the code through runSketch and answers the deck', 'runSketch(DECKGEN.code)' in page.read_text() and "deckgen: 'ready'" in page.read_text())
check('a </script> in the code cannot end the tag', '<\\/script>' in js_str('a</script>b') and '</' not in js_str('a</script>b'))
check('the deck embeds the page and shows the hint', 'data-src="sketches/nostill.html"' in html and 'Live · hover' in html)
check('the missing still is a labelled box on screen, not an image', 'nostill · live in the html deck' in html and 'assets/nostill' not in html)
check('the reading view links the sketch', 'sketches/nostill.html">Open the live sketch' in html)
check('a deck without an editable sketch does not ship the editor runtime', '<script src="../vendor/sketch-editor.js">' not in html and not (tmp / '_site' / 'vendor' / 'sketch-editor.js').exists())

# a build with an editable sketch
deck2 = {'title': 'e', 'pdf': 'e.pdf', 'slides': finalize([code_slide('E', 'editable', short, sketch=live('edit-me', short, 400, 300))], 'T')}
html2 = build_html(deck2, tmp / '_site' / 'e').read_text()
check('the deck carries the editor over the panel, wired to its sketch',
      '<div class="ex ex-js" id="ex-edit-me" data-eid="edit-me" data-sketch="edit-me" style="left:120px;top:296px;width:800px;height:684px">' in html2
      and '<textarea class="ex-code"' in html2 and 'createCanvas(400, 300)' in html2 and 'class="ex-run"' in html2 and 'ctrl+enter runs it' in html2)
check('and ships the runtime', '<script src="../vendor/sketch-editor.js">' in html2 and (tmp / '_site' / 'vendor' / 'sketch-editor.js').exists())
check('the static code stays for print and the reading view', html2.count('createCanvas') >= 3)   # the panel, the editor, its mirror


print(f'\n{len(fails)} FAILED' if fails else f'\nall {len(fails) or 0} failures — sketch checks passed'.replace('all 0 failures — ', 'all '))
sys.exit(1 if fails else 0)
