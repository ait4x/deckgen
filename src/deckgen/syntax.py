"""
Syntax colouring for the code on slides.

One small regex lexer, two languages (Python and the JavaScript of the p5.js sketches),
two themes (a light panel, a dark one). It emits deckgen Runs, so the same colours reach
the html deck, the PowerPoint, the png previews and the reading view without any of
them knowing about it — a Run already carries its own colour.

    from deckgen.syntax import code_runs
    paras = [Para(rs, 'l', 1.45) for rs in code_runs(code, size=CODE)]

The lexer is deliberately forgiving: slide code is often a fragment — a line ending in
a colon, a `___` where the student types, an unclosed string in a "find the fault"
drill — and a tokenizer that raised on any of that would be worse than no colours.
The JavaScript twin in js/pyodide-console.js follows the same rules, token for token,
so the live editor and the printed panel agree.
"""
from __future__ import annotations

import keyword
import re

from .core import Run, INK, MUTED, MUTED_ON_INK, LIGHT_ON_INK, ORANGE, VIOLET, BLUE, DEEP_TEAL

# token kinds: kw keyword · bi builtin / p5 function · fn a name being defined · str · num · com comment · txt
LIGHT = {'base': INK, 'kw': VIOLET, 'bi': BLUE, 'fn': BLUE, 'str': DEEP_TEAL, 'num': ORANGE, 'com': MUTED}
DARK = {'base': LIGHT_ON_INK, 'kw': '#C9A3CC', 'bi': '#8CC1F0', 'fn': '#8CC1F0', 'str': '#64C2C3',
        'num': '#E38E5D', 'com': MUTED_ON_INK}

PY_KW = set(keyword.kwlist) | {'match', 'case'}
PY_BI = {'print', 'len', 'range', 'int', 'float', 'str', 'bool', 'list', 'dict', 'set', 'tuple', 'type',
         'input', 'sum', 'min', 'max', 'abs', 'round', 'sorted', 'reversed', 'enumerate', 'zip', 'map',
         'filter', 'any', 'all', 'open', 'isinstance', 'repr', 'chr', 'ord', 'id', 'hasattr', 'getattr',
         'super', 'object', 'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
         'ZeroDivisionError', 'self'}
JS_KW = {'function', 'let', 'const', 'var', 'for', 'while', 'do', 'if', 'else', 'return', 'new', 'class',
         'this', 'true', 'false', 'null', 'undefined', 'of', 'in', 'break', 'continue', 'switch', 'case',
         'default', 'typeof', 'instanceof', 'async', 'await', 'import', 'export', 'from', 'try', 'catch',
         'finally', 'throw', 'delete', 'void', 'yield', 'extends', 'static', 'get', 'set'}
JS_BI = {'createCanvas', 'background', 'fill', 'noFill', 'stroke', 'noStroke', 'strokeWeight', 'rect',
         'square', 'circle', 'ellipse', 'line', 'point', 'triangle', 'arc', 'beginShape', 'endShape',
         'vertex', 'random', 'randomSeed', 'noise', 'noiseSeed', 'push', 'pop', 'translate', 'rotate',
         'scale', 'noLoop', 'loop', 'redraw', 'frameRate', 'map', 'constrain', 'lerp', 'dist', 'floor',
         'ceil', 'round', 'abs', 'sin', 'cos', 'atan2', 'sqrt', 'min', 'max', 'width', 'height', 'mouseX',
         'mouseY', 'pmouseX', 'pmouseY', 'mouseIsPressed', 'frameCount', 'PI', 'TWO_PI', 'HALF_PI',
         'text', 'textSize', 'textAlign', 'color', 'colorMode', 'rectMode', 'ellipseMode', 'console',
         'Math', 'document', 'window', 'setup', 'draw', 'keyPressed', 'mousePressed', 'mouseMoved',
         'mouseDragged', 'key', 'keyCode', 'loadImage', 'image', 'createVector', 'millis', 'deltaTime'}

LANGS = {
    'py': dict(kw=PY_KW, bi=PY_BI, defs={'def', 'class'}, line_comment='#', block=None,
               triple=('"""', "'''"), quotes='"\'', prefix=r'[rbfuRBFU]{0,2}'),
    'js': dict(kw=JS_KW, bi=JS_BI, defs={'function', 'class'}, line_comment='//', block=('/*', '*/'),
               triple=(), quotes='"\'`', prefix=''),
}

_NAME = re.compile(r'[A-Za-z_$][\w$]*')
_NUM = re.compile(r'0[xXoObB][0-9a-fA-F_]+|\d[\d_]*(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+')
_WS = re.compile(r'[ \t]+')


def tokens(code, lang='py'):
    """Per line, a list of (kind, text). The kinds partition the line exactly, so
    ''.join(t for _, t in line) == line."""
    L = LANGS[lang]
    out = []
    open_str = None      # a triple quote or block comment carried across lines: (closer, kind)
    prev_word = None
    for line in code.split('\n'):
        toks = []
        i = 0
        n = len(line)
        if open_str:
            closer, kind = open_str
            j = line.find(closer)
            if j < 0:
                toks.append((kind, line))
                out.append(toks)
                continue
            toks.append((kind, line[:j + len(closer)]))
            i = j + len(closer)
            open_str = None
        while i < n:
            c = line[i]
            # comments
            if L['line_comment'] and line.startswith(L['line_comment'], i):
                toks.append(('com', line[i:]))
                break
            if L['block'] and line.startswith(L['block'][0], i):
                j = line.find(L['block'][1], i + 2)
                if j < 0:
                    toks.append(('com', line[i:]))
                    open_str = (L['block'][1], 'com')
                    break
                toks.append(('com', line[i:j + 2]))
                i = j + 2
                continue
            # strings, with an optional prefix (f"", r'', b"")
            m = re.match(L['prefix'], line[i:]) if L['prefix'] else None
            p = m.group(0) if m else ''
            k = i + len(p)
            if k < n and line[k] in L['quotes']:
                q3 = next((t for t in L['triple'] if line.startswith(t, k)), None)
                if q3:
                    j = line.find(q3, k + 3)
                    if j < 0:
                        toks.append(('str', line[i:]))
                        open_str = (q3, 'str')
                        break
                    toks.append(('str', line[i:j + 3]))
                    i = j + 3
                    continue
                q = line[k]
                j = k + 1
                while j < n and line[j] != q:
                    j += 2 if line[j] == '\\' else 1
                toks.append(('str', line[i:min(j + 1, n)]))
                i = min(j + 1, n)
                continue
            m = _NUM.match(line, i)
            if m and (i == 0 or not (line[i - 1].isalnum() or line[i - 1] == '_')):
                toks.append(('num', m.group(0)))
                i = m.end()
                prev_word = None
                continue
            m = _NAME.match(line, i)
            if m:
                w = m.group(0)
                if w in L['kw']:
                    kind = 'kw'
                elif prev_word in L['defs']:
                    kind = 'fn'
                elif w in L['bi']:
                    kind = 'bi'
                else:
                    kind = 'txt'
                toks.append((kind, w))
                prev_word = w
                i = m.end()
                continue
            m = _WS.match(line, i)
            if m:
                toks.append(('txt', m.group(0)))
                i = m.end()
                continue
            toks.append(('txt', c))
            prev_word = None
            i += 1
        out.append(_merge(toks))
        prev_word = None
    return out


def _merge(toks):
    """Adjacent tokens of one kind become one — fewer runs in the pptx and the html."""
    out = []
    for kind, text in toks:
        if out and out[-1][0] == kind:
            out[-1] = (kind, out[-1][1] + text)
        else:
            out.append((kind, text))
    return out


def code_runs(code, size, theme=LIGHT, lang='py', font='mono'):
    """One list of Runs per line, coloured by the theme. A blank line is a single space,
    so the paragraph keeps its height."""
    lines = code.split('\n') if isinstance(code, str) else list(code)
    out = []
    for toks in tokens('\n'.join(lines), lang):
        rs = [Run(text, font, size, theme.get(kind, theme['base'])) for kind, text in toks]
        out.append(rs or [Run(' ', font, size, theme['base'])])
    return out


def highlight_runs(rs, theme=LIGHT, lang='py'):
    """Colour the plain mono runs of an inline-markup line, leaving anything the author
    tagged — {orange:…}, **bold**, a link — exactly as it was."""
    from .core import FONTS
    out = []
    for r in rs:
        if r.font == 'mono' and r.color == theme['base'] and not r.url and FONTS[r.font][5]:
            for kind, text in tokens(r.text, lang)[0]:
                out.append(Run(text, r.font, r.size, theme.get(kind, r.color), r.spc, r.caps, r.italic))
        else:
            out.append(r)
    return out


def theme_for(bg):
    from .layouts import _dark
    return DARK if _dark(bg) else LIGHT


def html(code, lang='py', theme=LIGHT):
    """The code as html spans, for the editor overlay and the reading view."""
    from .core import esc
    lines = []
    for toks in tokens(code, lang):
        lines.append(''.join(esc(t) if k == 'txt' else f'<span style="color:{theme[k]}">{esc(t)}</span>'
                             for k, t in toks))
    return '\n'.join(lines)
