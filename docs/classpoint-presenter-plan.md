# HTML ClassPoint Presenter: Deckgen PR Direction

## Status and Source Handoff

The instructor confirmed a successful PowerPoint-free HTML presenter POC on
2026-10-04. Students continued using ClassPoint's existing student app. This draft
PR records the integration direction; it does not add a CLI command or runtime
feature yet.

The working POC and the full two-PR plan are uploaded in `venetanji/classpoint.py`
on branch `poc/html-presenter-cloud-handoff`:

- `experiments/html-presenter/`: runnable source, pinned dependencies, UI/design
  context, and a cloud-safe mock/browser validation script.
- `docs/live-presenter-plan.md`: protocol/client extraction plan, shared boundary,
  acceptance criteria, and follow-ups.

No private captures, TLS secrets, instructor settings, or student data are in the
handoff. Do not duplicate the live protocol code into this repository.

## The Two PRs

1. **classpoint.py:** extract an optional renderer-independent live client for
   SignalR, slide uploads, class/activity lifecycle, and response events. Preserve
   its existing PPTX/report APIs and keep networking dependencies optional.
2. **deckgen (this PR):** consume that client from a local HTML presenter, using
   the current deck loader, HTML builder, Reveal.js, and `Slide.cp` metadata.

Dependency direction is deckgen -> classpoint.py -> ClassPoint/Azure. The client
must not import deckgen or Playwright. Existing deckgen PPTX integration remains
unchanged; replacing its export helpers is not part of this work.

## Rough Implementation Direction

1. Introduce a local presentation command, for example
   `deckgen present week01 --classpoint`. This is proposed syntax, not a command
   implemented by the handoff. Offer browser/live dependencies through an
   optional extra, with actionable setup errors when they are absent.
2. Adapt the POC's `deck.py` to deckgen's normal project loading/build path and
   trusted course assets. Generated presenter files remain temporary. Reuse
   `Slide.cp` rather than inventing another activity manifest or question spec.
3. Adapt `presenter.py` into a loopback-only server and Reveal snapshot adapter.
   The client receives image bytes and slide/step metadata; screenshotting,
   browser state, local routes, and CSRF/Host/Origin checks remain in deckgen.
4. Adapt `web/` into the operator shell. Retain ait4x typography/palette and make
   the slide the primary surface. Polish start/close/end controls, join code,
   response tallies, sync status, busy/failed/disconnected states, and retries.
5. Make the existing multiple-choice badge actionable only in local presenter
   mode. Published decks stay static/passive; report links and reading view
   remain intact outside that mode. Never embed credentials in generated HTML.
6. Add fake-client adapter tests and real-renderer/browser smoke tests for deck
   selection, question switching, fragments, tallies, keyboard controls,
   fullscreen join-code display, and desktop/mobile layouts. Keep cloud tests
   independent of ClassPoint accounts and private captures.

## First Acceptance Case

- Start a class and a multiple-choice activity directly from a deckgen HTML slide,
  without launching PowerPoint.
- Students join/answer in ClassPoint's existing app and can see the raster slide.
- Navigation synchronizes slide/fragment snapshots; opening another question
  closes/ends the previous activity but retains the class.
- The operator can close submissions and explicitly end the class, with truthful
  errors and cleanup status. No ClassPoint connection starts just from page load.
- Ordinary site/PDF/PPTX builds remain usable without live dependencies, and
  existing tests continue to pass.

## Cloud Session Workflow

Read the companion plan and run the preserved POC's `validate.py` first. That
script starts mock ClassPoint/Azure services on loopback and renders real deckgen
HTML using Chromium. It uses synthetic configuration and answers, not captures.
Install Chromium and its OS dependencies as needed; instructions are in the POC
README. The POC pins this repository's baseline commit to
`9990546c01865807e6aaac5aaa50977b4b6b916a`.

Implement against a fake client while PR 1's interface settles, then switch the
adapter to the extracted client. Keep the baseline runnable until the new command
passes the same workflow. Actual classroom acceptance remains a separate,
explicit instructor action and must never run automatically in CI.

## Scope Limits

Only multiple choice is proven for this first integration. Do not expand to
stars, quiz grading, countdowns, report persistence, or other activity types in
the initial PR. Capture-based configuration is experimental, not a finished
authentication/onboarding flow.

The POC captures a specified slide/fragment in a fresh browser; it does not mirror
the presenting browser's live sketch, editor, or video state. Document that limit.
A later in-browser snapshot/state-transfer approach should address it explicitly.
