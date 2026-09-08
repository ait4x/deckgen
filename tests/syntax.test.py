"""
The lexer behind the code colours: tokens partition the text exactly, fragments do not
raise, inline markup on a code_panel survives, and every rendering path carries the
colour — the static exercise panel, a two_col, a code_slide, the reading view.

    python tests/syntax.test.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'src'))

from deckgen.project import Project, configure                           # noqa: E402
from deckgen.syntax import tokens, code_runs, highlight_runs, html, LIGHT, DARK   # noqa: E402
from deckgen.core import runs, exercise_static, Exercise, handout_text, INK, ORANGE, VIOLET, BLUE, DEEP_TEAL, MUTED  # noqa: E402
from deckgen.layouts import two_col, code_panel, code_slide, live, activity   # noqa: E402

tmp = pathlib.Path(tempfile.mkdtemp())
(tmp / 'deck').mkdir()
configure(Project(root=tmp, code='T', name='t', decks=['d']))

bad = 0


def check(name, ok):
    global bad
    print(('  ok   ' if ok else '  FAIL ') + name)
    bad += not ok


def kinds(line, lang='py'):
    return [(k, t) for k, t in tokens(line, lang)[0] if t.strip()]


# partition
for src in ['x = "a # not a comment"  # comment', 'def f(xs):\n    return sum(xs) / len(xs)', 'print(', 'for i in range(3):', 's = """open', '', '   ']:
    check(f'partition: {src[:28]!r}', all(''.join(t for _, t in ln) == raw for ln, raw in zip(tokens(src), src.split('\n'))))

# kinds
check('string is a string, even with # inside', ('str', '"a # b"') in kinds('x = "a # b"  # c'))
check('comment after code', ('com', '# c') in kinds('x = "a # b"  # c'))
check('keyword', ('kw', 'for') in kinds('for i in range(3):') and ('kw', 'in') in kinds('for i in range(3):'))
check('builtin', ('bi', 'range') in kinds('for i in range(3):'))
check('number', ('num', '3') in kinds('for i in range(3):'))
check('def name', ('fn', 'mean_height') in kinds('def mean_height(rows, year):'))
check('a name is plain', ('txt', '(rows, year):') in kinds('def mean_height(rows, year):'))
check('f-string prefix stays with the string', ('str', 'f"{name} is {years}"') in kinds('print(f"{name} is {years}")'))
check('underscore placeholder is plain', kinds('x = ___') == [('txt', 'x = ___')])
check('number inside a name is not a number', kinds('x2 = 1') == [('txt', 'x2 = '), ('num', '1')])
tri = tokens('s = """one\ntwo""" + x')
check('triple quote carries across lines', tri[0][-1][0] == 'str' and tri[1][0] == ('str', 'two"""'))
check('unclosed string does not raise', kinds('print("hello') == [('bi', 'print'), ('txt', '('), ('str', '"hello')])
check('js comment and keyword', ('com', '// redraw') in kinds('for (let i = 0; i < 10; i++) circle(1, 2, 8); // redraw', 'js')
      and ('kw', 'let') in kinds('let x = 1', 'js'))
check('js p5 builtin', ('bi', 'createCanvas') in kinds('createCanvas(600, 600);', 'js'))
check('js block comment', [k for k, _ in kinds('/* a */ x', 'js')][0] == 'com')
check('js function name', ('fn', 'setup') in kinds('function setup() {', 'js'))
check('python keywords are not js keywords', kinds('def x', 'js') == [('txt', 'def x')])

# runs
rs = code_runs('print("hi")  # say', 30)
check('code_runs colours', [r.color for r in rs[0]] == [BLUE, INK, DEEP_TEAL, INK, MUTED])
check('blank line keeps its height', code_runs('a\n\nb', 30)[1][0].text == ' ')
check('dark theme', code_runs('for', 30, DARK)[0][0].color == DARK['kw'])
hr = highlight_runs(runs('{orange:draw_vertical} = random(grid) > abs(w-h)', 'mono', 30, INK))
check('inline markup keeps its colour', hr[0].color == ORANGE and hr[0].text == 'draw_vertical')
check('the rest of the line is coloured', any(r.color == BLUE and r.text == 'abs' for r in hr))

# the rendering paths
st = exercise_static(Exercise(0, 0, 800, 600, 'x = 1  # one'))
code_el = [e for e in st if getattr(e, 'name', '') == 'code'][0]
check('static exercise panel is coloured', {r.color for r in code_el.paras[0].runs} >= {ORANGE, MUTED})
tc = two_col('E', 't', ['a'], ['def f():', '    return 1'])
tc_code = [e for e in tc.els if getattr(e, 'name', '') == 'code'][0]
check('two_col colours its panel', tc_code.paras[0].runs[0].color == VIOLET)
tc0 = two_col('E', 't', ['a'], ['TAPE 1 0 1'], lang=None)
check('two_col lang=None stays plain', all(r.color == INK for p in [e for e in tc0.els if getattr(e, 'name', '') == 'code'][0].paras for r in p.runs))
cp = code_panel('E', 't', ['{orange:x} = 1', 'print(x)'])
cp_code = [e for e in cp.els if getattr(e, 'name', '') == 'code'][0]
check('code_panel: tagged span orange, print blue', cp_code.paras[0].runs[0].color == ORANGE and cp_code.paras[1].runs[0].color == BLUE)
cs = code_slide('E', 't', 'function setup() {\n  createCanvas(1, 1);\n}', sketch=live('a', 'x'))
cs_code = [e for e in cs.els if getattr(e, 'name', '') == 'code'][0]
check('code_slide with a sketch colours as js', cs_code.paras[0].runs[0].color == VIOLET and cs_code.paras[1].runs[1].color == BLUE)
ac = activity('1', 3, 't', ['b'], panel=['rule:', 'chance:'])
check('activity panel is plain unless asked', all(r.color == INK for p in [e for e in ac.els if getattr(e, 'name', '') == 'code'][0].paras for r in p.runs))
check('reading view carries the colour', f'color:{VIOLET}' in handout_text(tc_code, 'code') and '<pre class="ho-code">' in handout_text(tc_code, 'code'))
check('html escapes and colours', html('if a < "b":') == f'<span style="color:{VIOLET}">if</span> a &lt; <span style="color:{DEEP_TEAL}">&quot;b&quot;</span>:'
      or 'a &lt;' in html('if a < "b":') and f'color:{VIOLET}' in html('if a < "b":'))

print(f'\n{bad} FAILED' if bad else f'\nall syntax checks passed')
sys.exit(1 if bad else 0)
