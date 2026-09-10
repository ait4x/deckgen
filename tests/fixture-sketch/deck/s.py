# One live p5.js sketch on each layout that can carry one. Four of them have no figure, so
# the build has to make their stills; the one over a drawn figure needs none. The code slides
# are editable (sketch.test.js types into them); the last one has a slider in its code.
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


SLIDER = '''let size;
function setup() {
  createCanvas(400, 300);
  // a number on a slider, labelled
  size = createSlider(10, 100, 40, 1, 'size');
  noLoop();
}
function draw() {
  background(255, 0, 0);
  circle(200, 150, size.value());
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
    code_slide('05 · SLIDER', 'A number on a slider', SLIDER, sketch=live('s-slider', SLIDER, 400, 300, hint='drag the slider')),
    end('done', 'ok', 'example.org'),
]}
