# One live p5.js sketch on each layout that can carry one. Three of them have no figure, so
# the build has to make their stills; the fourth sits over a drawn figure and needs none.
from deckgen.layouts import title, sketch_slide, code_slide, content, activity, live, end
from deckgen.figures import Canvas, ORANGE

DOT = '''function setup() {
  createCanvas(400, 300);
}
function draw() {
  background(240);
  fill(0);
  circle(mouseX, mouseY, 60);   // follows the mouse
}'''


def box(name='box', w=400, h=300):
    c = Canvas(w, h)
    c.rect(20, 20, w - 40, h - 40, fill=ORANGE)
    return c.finish(name)


DECK = {'title': 'sketch fixture', 'pdf': 's.pdf', 'slides': [
    title('FIXTURE', 'Sketches', 'Driven by tests/sketch.test.js.'),
    sketch_slide('01 · LIVE', 'A dot follows the mouse', live('s-dot', DOT, 400, 300, hint='move the mouse')),
    code_slide('02 · CODE', 'The code beside it', DOT, sketch=live('s-dot-code', DOT, 400, 300)),
    content('03 · CONTENT', 'Over a figure', ['The figure is the twin.'], figure=box(), sketch=live('s-dot-fig', DOT, 400, 300)),
    activity('1 / 1', 3, 'Play with it', ['Move the mouse.'], sketch=live('s-dot-act', DOT, 400, 300)),
    end('done', 'ok', 'example.org'),
]}
