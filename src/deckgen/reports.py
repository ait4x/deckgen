"""
Link every question slide to the answers the room actually gave.

ClassPoint publishes each activity at `app.classpoint.io/activity/<activityId>`
— a public, login-free page with every response on it. After a class those ids
are the only thing standing between a student and their own work, so the deck
should carry them: `attach_reports` turns the eyebrow of each question slide
into

    QUESTION · MULTIPLE CHOICE · YOUR ANSWERS
                                 ^^^^^^^^^^^^ links to the report

which costs no layout space, survives every question variant including
multiple choice (where `hint` is not rendered), and becomes a real hyperlink in
the PowerPoint export as well as the published html.

The ids arrive in a small JSON file per deck, written after class by
`classpoint.py`'s weekly runner (https://github.com/venetanji/classpoint.py):

    [{"activity": "sa20260904033646383JAAW", "question": "Why is AI relevant for design?"},
     ...]

An entry may record an activity **without** linking it, by setting `activity`
to null:

    [{"activity": null, "question": "One hope and one worry.",
      "withheld": "names hidden"}]

That is not a formality. ClassPoint's public page honours an activity's
`isNamesHidden`, but the payload behind it still carries `participantName` for
every response — so a link to an activity the room was told was anonymous
hands out a way to undo that. The slide keeps its place in the count and
simply gets no link.

Order is the contract — ClassPoint mints an id the first time an activity runs,
so the activities of one class sort chronologically into exactly the order
their slides appear in. `question` is optional and checked when present, which
is what catches the case that actually happens: a question added to the deck
after the class it was matched against. Both mismatches raise. A missing file
is not an error — every deck can call this from the day it is written, and the
links appear the week it is taught.
"""

from __future__ import annotations

import json
from pathlib import Path

from .core import eyebrow

ACTIVITY_URL = 'https://app.classpoint.io/activity/{}'
LABEL = 'Your answers'
EYEBROW_NAME = 'question-eyebrow'


def activity_url(activity: str) -> str:
    return activity if activity.startswith('http') else ACTIVITY_URL.format(activity)


def load(source) -> list[dict]:
    """A report list from a path, a list of ids, or a list of entries."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.exists():
            return []
        source = json.loads(path.read_text(encoding='utf-8'))
    return [{'activity': e} if isinstance(e, str) else dict(e) for e in source]


def links(source) -> list[tuple[str, str]]:
    """(question, url) pairs, withheld entries omitted — for a course that
    wants to list them somewhere other than the slides."""
    return [(e.get('question') or e['activity'], activity_url(e['activity']))
            for e in load(source) if e.get('activity')]


def attach_reports(slides, source, label: str = LABEL, quiet: bool = False) -> int:
    """Add the report link to each ClassPoint slide of `slides`, in order.

    Returns the number of slides linked, which is not the number of entries if
    any were withheld. Call it before `finalize`; a missing or empty source is
    a no-op, anything inconsistent raises.
    """
    entries = load(source)
    if not entries:
        return 0
    targets = [s for s in slides if getattr(s, 'cp', None)]
    if len(targets) != len(entries):
        raise ValueError(
            f'{len(entries)} activities but {len(targets)} ClassPoint slides — the deck and the '
            f'class have drifted apart. Fix the report file rather than the deck: it is the record '
            f'of what was run.')

    linked = 0
    for s, entry in zip(targets, entries):
        want = entry.get('question')
        if want and want != s.title:
            raise ValueError(f'activity {entry["activity"]} is recorded against {want!r} '
                             f'but that slide now asks {s.title!r}')
        if not entry.get('activity'):   # recorded, deliberately not linked
            if not quiet:
                print(f'  report: {s.title[:48]:<48} withheld'
                      + (f" ({entry['withheld']})" if entry.get('withheld') else ''))
            continue
        url = activity_url(entry['activity'])
        for i, el in enumerate(s.els):
            if getattr(el, 'name', '') == EYEBROW_NAME:
                text = ''.join(r.text for p in el.paras for r in p.runs)
                s.els[i] = eyebrow(el.x, el.y, f'{text} · [{label}]({url})', el.paras[0].runs[0].color,
                                   w=el.w, size=el.paras[0].runs[0].size, name=EYEBROW_NAME)
                break
        else:
            raise ValueError(f'{s.title!r} has no {EYEBROW_NAME} to hang the link on')
        linked += 1
        if not quiet:
            print(f'  report: {s.title[:48]:<48} {url}')
    return linked
