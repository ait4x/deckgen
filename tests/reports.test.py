"""
Report links: the mapping contract, and that a link really reaches the html.

    python tests/reports.test.py

The order of a class's activities is the whole contract — ClassPoint mints an id
when an activity first runs, so they sort into slide order — and everything here
is about failing loudly when a deck and a delivered class have drifted apart.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'src'))

from deckgen import attach_reports, report_links
from deckgen.core import html_text, text_height, wrap_para
from deckgen.layouts import question, content, section

fails = []


def check(name, ok):
    print(('  ok  ' if ok else '  FAIL ') + name)
    if not ok:
        fails.append(name)


def raises(name, fn, fragment):
    try:
        fn()
    except ValueError as e:
        check(name, fragment in str(e))
    else:
        check(name, False)


def eb(slide):
    el = [e for e in slide.els if getattr(e, 'name', '') == 'question-eyebrow'][0]
    return el, ''.join(r.text for p in el.paras for r in p.runs)


def deck():
    return [section('01', 'A section', 'no activity here'),
            question('word_cloud', 'Why is AI relevant for design?', hint='One word.'),
            question('multiple_choice', 'Which of these is a chair?', ['A bean bag', 'A tree stump', 'Both']),
            content('AFTER', 'Not a question', ['no cp here'])]


IDS = ['wc20260903021235360VBUG', 'mc20260904043922212ZXSV']

# ── the happy path ───────────────────────────────────────────────────────────
S = deck()
n = attach_reports(S, IDS, quiet=True)
check('links only the ClassPoint slides', n == 2)
el, text = eb(S[1])
check('the eyebrow keeps what it said', text.startswith('QUESTION · Word cloud · '))
check('and gains the label', text.endswith('Your answers'))
runs = [r for p in el.paras for r in p.runs]
check('only the label is a link', [r.url for r in runs].count(None) == len(runs) - 1)
check('pointing at the activity', runs[-1].url.endswith(IDS[0]))
check('order is the contract', eb(S[2])[1].endswith('Your answers') and
      [r for p in eb(S[2])[0].paras for r in p.runs][-1].url.endswith(IDS[1]))
check('a full url passes through', report_links(['https://app.classpoint.io/activity/x'])[0][1]
      == 'https://app.classpoint.io/activity/x')

# ── it has to survive the real renderers ─────────────────────────────────────
html = ''.join(html_text(el))
check('the html carries an anchor', f'href="https://app.classpoint.io/activity/{IDS[0]}"' in html)
check('and opens it away from the deck', 'target="_blank"' in html)
check('the slide remembers its report', S[1].report.endswith(IDS[0]) and S[3].report == '')
import pathlib, tempfile
from deckgen.core import html_slide
_tmp = pathlib.Path(tempfile.mkdtemp())
page = html_slide(S[1], 1, _tmp, _tmp, 'assets')
check('the chip is a link to the answers', f'<a class="cp" data-classpoint href="https://app.classpoint.io/activity/{IDS[0]}"' in page and 'see the answers' in page)
check('a slide without a report keeps the badge', '<div class="cp" data-classpoint>' in html_slide(deck()[1], 1, _tmp, _tmp, 'assets'))
check('the longer eyebrow still fits on one line',
      text_height(el) <= el.h and sum(len(wrap_para(p, el.w)) for p in el.paras) == 1)

# ── missing is fine, wrong is not ────────────────────────────────────────────
with tempfile.TemporaryDirectory() as d:
    absent = pathlib.Path(d) / 'week99-reports.json'
    check('a deck taught next month is a no-op', attach_reports(deck(), absent, quiet=True) == 0)
    check('and so is an empty file', attach_reports(deck(), []) == 0)
    present = pathlib.Path(d) / 'week01-reports.json'
    present.write_text(json.dumps([{'activity': IDS[0], 'question': 'Why is AI relevant for design?'},
                                   {'activity': IDS[1], 'question': 'Which of these is a chair?'}]))
    check('a recorded question that still matches passes', attach_reports(deck(), present, quiet=True) == 2)
    check('and reads back as (question, url)',
          report_links(present)[0] == ('Why is AI relevant for design?',
                                       f'https://app.classpoint.io/activity/{IDS[0]}'))

# ── recorded, deliberately not linked ────────────────────────────────────────
S = deck()
n = attach_reports(S, [{'activity': None, 'question': 'Why is AI relevant for design?',
                        'withheld': 'names hidden'}, {'activity': IDS[1]}], quiet=True)
check('a withheld activity is not linked', n == 1)
check('but its slide keeps the eyebrow it had', eb(S[1])[1] == 'QUESTION · Word cloud')
check('and it does not throw the order off', [r for p in eb(S[2])[0].paras for r in p.runs][-1].url.endswith(IDS[1]))
check('withheld entries stay out of the link list',
      report_links([{'activity': None, 'question': 'One hope and one worry.'},
                    {'activity': IDS[1], 'question': 'Which of these is a chair?'}]) ==
      [('Which of these is a chair?', f'https://app.classpoint.io/activity/{IDS[1]}')])

raises('one activity short of the deck', lambda: attach_reports(deck(), IDS[:1]), 'drifted apart')
raises('one activity too many', lambda: attach_reports(deck(), IDS + ['sa20260904033646383JAAW']), 'drifted apart')
raises('a question that has since been rewritten',
       lambda: attach_reports(deck(), [{'activity': IDS[0], 'question': 'Something else entirely'},
                                       {'activity': IDS[1]}]), 'is recorded against')
raises('a slide with no eyebrow to hang it on',
       lambda: attach_reports([type('S', (), {'cp': {'type': 'word_cloud'}, 'els': [], 'title': 'bare'})()],
                              IDS[:1]), 'no question-eyebrow')

print(f'\n{len(fails)} FAILED: {fails}' if fails else '\nall report checks passed')
sys.exit(1 if fails else 0)
