"""
The Python half of the in-slide runtime, against the real interpreter.

    python tests/runtime.test.py

Pyodide runs the same CPython, so what passes here passes in the browser. The DOM half
is covered by tests/wiring.test.js.
"""
import json
import pathlib
import sys

SRC = pathlib.Path(__file__).resolve().parent.parent / 'src' / 'deckgen' / 'js' / 'pyodide-runtime.py'
g = {}
exec(SRC.read_text(), g)
run, ev, reset = g['_dg_run'], g['_dg_eval'], g['_dg_reset_console']

fails = []


def check(name, cond):
    print(('  ok   ' if cond else '  FAIL ') + name)
    if not cond:
        fails.append(name)


r = json.loads(run('a = "6"\nb = "6"\nprint(int(a) + int(b))', '', '12'))
check('expect matches', r['ok'] is True and r['out'] == '12\n')

r = json.loads(run('a = "6"\nb = "6"\nprint(a + b)', '', '12'))
check('expect fails and says so', r['ok'] is False and 'Expected' in r['msg'] and r['out'] == '66\n')

CHK = 'ok = _out.strip() == "[1, 2, 3]"\nmsg = "" if ok else "a still has the 4"'
r = json.loads(run('a=[1,2,3]\nb=a.copy()\nb.append(4)\nprint(a)', CHK, None))
check('check passes', r['ok'] is True)
r = json.loads(run('a=[1,2,3]\nb=a\nb.append(4)\nprint(a)', CHK, None))
check('check fails with its message', r['ok'] is False and r['msg'] == 'a still has the 4')

r = json.loads(run('print(', '', '1'))
check('syntax error is reported, not raised', 'SyntaxError' in r['err'] and r['ok'] is None)
r = json.loads(run('1/0', '', '1'))
check('runtime error is reported', 'ZeroDivisionError' in r['err'])

# reading the traceback is the week-2 lesson, so it has to name the line and show the
# source — and it must not leak the runtime's own frames
r = json.loads(run('def f(xs):\n    return sum(xs) / len(xs)\n\nprint(f([]))', '', None))
check('traceback names the student\'s lines',
      'line 4, in <module>' in r['err'] and 'line 2, in f' in r['err'])
check('traceback hides the scaffolding',
      '_dg_capture' not in r['err'] and '<lambda>' not in r['err'])
r = json.loads(run('print(', '', None))
check('a syntax error shows the source line', 'print(' in r['err'] and '^' in r['err'])
r = json.loads(run('print(1)', 'ok = undefined_name', None))
check('a broken check blames itself', r['ok'] is False and 'the check itself failed' in r['msg'])

r = json.loads(run('import sys\nprint("out")\nsys.stderr.write("err\\n")', '', None))
check('stderr is captured too', 'out' in r['out'] and 'err' in r['out'])
r = json.loads(run('x = 1', '', None))
check('no check means no verdict', r['ok'] is None)


class _JsNull:
    """Pyodide 314 hands JS null over as a sentinel object, not None. That made
    `expect is not None` true for every check-based exercise and blew up on .strip()."""
    def __repr__(self):
        return 'JsNull'


CHK2 = 'ok = _out.strip() == "1"'
r = json.loads(run('print(1)', CHK2, _JsNull()))
check('a JsNull expect is treated as absent', r['ok'] is True and not r['err'])
r = json.loads(run('print(1)', _JsNull(), _JsNull()))
check('a JsNull check is treated as absent', r['ok'] is None and not r['err'])

# each exercise gets a clean namespace
run('leaked = 99', '', None)
r = json.loads(run('print("leaked" in dir())', '', None))
check('namespaces do not leak between exercises', r['out'].strip() == 'False')

# the console keeps state, and echoes like a REPL
reset()
check('console assignment is quiet', json.loads(ev('x = 21'))['out'] == '')
check('console remembers', json.loads(ev('x * 2'))['out'].strip() == '42')
check('console reprs strings', json.loads(ev('"hi"'))['out'].strip() == "'hi'")
check('console runs statements', json.loads(ev('for i in range(2): print(i)'))['out'] == '0\n1\n')
check('console reports NameError', 'NameError' in json.loads(ev('nope'))['err'])

# a whole block pasted in at once: everything runs, and a trailing expression still echoes
BLOCK = 'rows = [1, 2, 3]\ntotal = 0\nfor r in rows:\n    total += r\ntotal'
check('console runs a pasted block', json.loads(ev(BLOCK))['out'].strip() == '6')
check('console keeps the block\'s names', json.loads(ev('rows'))['out'].strip() == '[1, 2, 3]')
DEF = 'def double(x):\n    return x * 2\n\nprint(double(21))'
check('console defines and calls', json.loads(ev(DEF))['out'].strip() == '42')
check('a block ending in a statement is quiet',
      json.loads(ev('a = 1\nb = 2'))['out'] == '')
r = json.loads(ev('x = 1\ny = 0\nprint(x / y)'))
check('a block reports the line that failed', 'ZeroDivisionError' in r['err'])
r = json.loads(ev('for i in range(3):'))
check('an unfinished block is reported, not a crash',
      'IndentationError' in r['err'] and 'for i in range(3):' in r['err'])
reset()
check('console reset clears state', 'NameError' in json.loads(ev('x'))['err'])

print(f'\n{len(fails)} FAILED: {fails}' if fails else '\nall runtime checks passed')
sys.exit(1 if fails else 0)
