"""
Week 1 — the deck as one Python spec: text, speaker notes, ClassPoint activities,
in the order the class runs. Edit here; the html deck, the PDF, the PowerPoint and
the previews all follow.

    deckgen build --pptx        # export/ only, no node needed
    deckgen build               # everything, as the workflows run it

Every layout takes its eyebrow (the small tracked caps line) first, then its title.
Inline markup works in any string: **bold**, [text](url), {orange:…} {teal:…}
{muted:…} {mono:…}.
"""
from deckgen.layouts import title, agenda, section, content, question, statement, end

COURSE = 'SD0000'
SITE = 'venetanji.github.io/sd0000-teaching'

DECK = {
    'title': f'{COURSE} · Week 1',
    'pdf': f'{COURSE}-week01.pdf',
    'slides': [
        title(f'{COURSE} · WEEK 01', 'The title of the week', 'A subtitle underneath it.'),

        agenda(f'{COURSE} · WEEK 01', [
            'The first thing',
            'The second thing',
            'The third thing',
        ]),

        section('01', 'A section', 'Part one'),

        content('01 · A SECTION', 'A content slide', [
            'A line of body text, which wraps on its own.',
            '',
            '- a bullet',
            '- another, with **bold**, {orange:colour} and {mono:code}',
        ], notes='What to say out loud while this is up.'),

        # ClassPoint: the kind picks the activity and the button.
        # word_cloud · short_answer · image_upload · multiple_choice (pass choices=)
        question('word_cloud', 'One word for how that went?',
                 hint='Three words each, no wrong answers.'),

        question('multiple_choice', 'Which of these is true?',
                 choices=['The first one', 'The second one', 'Neither']),

        statement('One idea, big enough to fill the slide.'),

        end('See you next week', 'Bring a laptop.', SITE),
    ],
}
