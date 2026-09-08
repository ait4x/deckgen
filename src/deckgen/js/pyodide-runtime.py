"""
The Python half of the in-slide runtime, exec'd once into Pyodide.

Everything the browser needs happens here and comes back as one JSON string, so the
JavaScript side only ever calls a function with strings. Keeping PyProxy objects out
of the JS is deliberate: their lifetimes have to be managed by hand, and a leak in a
lecture is a laptop that stops responding halfway through class.
"""
import ast
import io
import json
import sys
import traceback

_dg_console_ns = {}          # the console keeps its state between lines

# Filenames the student's own code is compiled under. Everything else in a
# traceback is our scaffolding and gets cut.
_DG_SOURCES = ('<your code>', '<console>', '<check>')


def _dg_capture(fn):
    """Run fn() with stdout and stderr redirected; return (value, output, error)."""
    buf = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = buf
    err = ''
    value = None
    try:
        value = fn()
    except BaseException:
        # Drop our exec scaffolding and keep everything from the student's own frame
        # down. Slicing a fixed count off the end was not enough: a SyntaxError puts its
        # source line and its caret in separate entries, so the tail alone was a caret
        # pointing at nothing. Reading the traceback is the week-2 lesson — show it whole.
        parts = traceback.format_exception(*sys.exc_info())
        mine = next((i for i, f in enumerate(parts)
                     if any(('"%s"' % n) in f for n in _DG_SOURCES)), None)
        err = ''.join(parts[mine:] if mine is not None else parts[-2:]).rstrip()
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return value, buf.getvalue(), err


def _dg_run(src, check, expect):
    """One exercise: the student's code, then the check. Fresh namespace every time.

    `check` and `expect` arrive from JavaScript. Pyodide 314 hands JS `null` across as a
    JsNull sentinel rather than None, so `expect is not None` was true for an exercise
    that has no expected output and `.strip()` raised AttributeError — every check-based
    exercise failed in the browser while passing under CPython. Anything that is not a
    str is absent, whatever the FFI decided to call it.
    """
    check = check if isinstance(check, str) else ''
    expect = expect if isinstance(expect, str) else None
    ns = {}
    _, out, err = _dg_capture(lambda: exec(compile(src, '<your code>', 'exec'), ns))
    ok, msg = None, ''
    if not err and expect is not None:
        ok = out.strip() == expect.strip()
        if not ok:
            msg = 'Expected:\n' + expect
    elif not err and check:
        ns['_out'] = out
        ns['ok'] = False
        ns['msg'] = ''
        _, _, cerr = _dg_capture(lambda: exec(compile(check, '<check>', 'exec'), ns))
        if cerr:
            ok, msg = False, 'the check itself failed:\n' + cerr
        else:
            ok = bool(ns.get('ok'))
            msg = str(ns.get('msg') or '')
    return json.dumps({'out': out, 'err': err, 'ok': ok, 'msg': msg})


def _dg_eval(src):
    """One console entry — a single line, or a whole block pasted in at once.

    A REPL echoes the value of a trailing expression, so the entry is split rather than
    compiled whole: everything but the last statement is exec'd, and the last one is
    eval'd when it is an expression. Compiling the sliced tree instead of re-parsing a
    slice of the text keeps the original line numbers in any traceback.
    """
    def go():
        tree = ast.parse(src, '<console>', 'exec')
        if not tree.body:
            return
        head, last = tree.body[:-1], tree.body[-1]
        if head:
            exec(compile(ast.Module(body=head, type_ignores=[]), '<console>', 'exec'),
                 _dg_console_ns)
        if isinstance(last, ast.Expr):
            value = eval(compile(ast.Expression(last.value), '<console>', 'eval'),
                         _dg_console_ns)
            if value is not None:
                print(repr(value))
        else:
            exec(compile(ast.Module(body=[last], type_ignores=[]), '<console>', 'exec'),
                 _dg_console_ns)
    _, out, err = _dg_capture(go)
    return json.dumps({'out': out, 'err': err})


def _dg_reset_console():
    _dg_console_ns.clear()
    return '{}'
