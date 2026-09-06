"""
The Python half of the in-slide runtime, exec'd once into Pyodide.

Everything the browser needs happens here and comes back as one JSON string, so the
JavaScript side only ever calls a function with strings. Keeping PyProxy objects out
of the JS is deliberate: their lifetimes have to be managed by hand, and a leak in a
lecture is a laptop that stops responding halfway through class.
"""
import io
import json
import sys
import traceback

_dg_console_ns = {}          # the console keeps its state between lines


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
        # limit=-2 keeps the student's own frame and drops our exec scaffolding
        err = ''.join(traceback.format_exception(*sys.exc_info())[-2:]).rstrip()
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return value, buf.getvalue(), err


def _dg_run(src, check, expect):
    """One exercise: the student's code, then the check. Fresh namespace every time."""
    ns = {}
    _, out, err = _dg_capture(lambda: exec(src, ns))
    ok, msg = None, ''
    if not err and expect is not None:
        ok = out.strip() == expect.strip()
        if not ok:
            msg = 'Expected:\n' + expect
    elif not err and check:
        ns['_out'] = out
        ns['ok'] = False
        ns['msg'] = ''
        _, _, cerr = _dg_capture(lambda: exec(check, ns))
        if cerr:
            ok, msg = False, 'the check itself failed:\n' + cerr
        else:
            ok = bool(ns.get('ok'))
            msg = str(ns.get('msg') or '')
    return json.dumps({'out': out, 'err': err, 'ok': ok, 'msg': msg})


def _dg_eval(src):
    """One console line. Echoes the repr of an expression, the way a REPL does."""
    def go():
        try:
            code = compile(src, '<console>', 'eval')
        except SyntaxError:
            exec(compile(src, '<console>', 'exec'), _dg_console_ns)
        else:
            value = eval(code, _dg_console_ns)
            if value is not None:
                print(repr(value))
    _, out, err = _dg_capture(go)
    return json.dumps({'out': out, 'err': err})


def _dg_reset_console():
    _dg_console_ns.clear()
    return '{}'
