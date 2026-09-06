from deckgen.layouts import title, exercise, end

DECK = {'title': 'wiring fixture', 'pdf': 't.pdf', 'slides': [
    title('FIXTURE', 'Exercises', 'Driven by tests/wiring.test.js.'),
    exercise('01 · TYPES', 'Make it say 12',
             'Two strings glued together give "66". Make Python add them as numbers.',
             code='a = "6"\nb = "6"\nprint(a + b)', expect='12'),
    exercise('02 · ALIASING', 'Stop the aliasing',
             'b should not change when a does.',
             code='a = [1, 2, 3]\nb = a\nb.append(4)\nprint(a)',
             check='ok = _out.strip() == "[1, 2, 3]"\nmsg = "" if ok else "a still has the 4 in it"'),
    end('done', 'ok', 'example.org'),
]}
