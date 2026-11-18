# Layout Kit Build Notes

Open at Step 4 of ${CLAUDE_PLUGIN_ROOT}/references/design-system.md. Blueprints, Tokens, Writing the files and The checks script apply to every kit. Previews, Themes and grounds, and Assets and the index apply only when the kit is published as a Design System artifact: there, follow the type's own instructions for file shapes; these notes cover the choices and traps specific to carousels.

## Contents

- Previews
- Blueprints
- Themes and grounds
- Assets and the index
- Tokens
- Writing the files
- No Design System type on the account
- The checks script
- Failures already hit

## Previews

- Layout previews stay blank with "bundle.js is missing" until `components/bundle.js` exists. Slides are static HTML, so a three-line bundle is enough. Line 1 is the header, for example `/* @ds-bundle: {"format":4,"namespace":"Kit","components":[{"name":"CoverSlide"},{"name":"Statement"}]} */`, then `window.Kit = {};`. Set the same namespace in the index.
- Put all slide CSS in `components/bundle.css`, written against token variables (`var(--ember)`), so each preview is only markup.
- Render slides at full size (for example 1080x1350) inside a fixed "stage" box and scale them with `transform: scale()`. Around 0.3 lets several sit in a row.
- Previews load lazily. A blank row right after opening is not a failure; wait a few seconds before judging.
- Every system needs its own cover at `components/Cover/preview.html`, written last, following the type's cover reference (color blocks, one pattern, the name). Keep that folder bare, and name the cover-slide layout something else (`CoverSlide`).

## Blueprints

A blueprint is the live layout with its slots labeled:

- Headline slot: placeholder copy that states the rule ("One claim per slide, ember phrase.").
- Image, video and art slots: a dashed frame naming what can go there ("PROOF SLOT: screenshot · video · replica board").
- Optional slots say OPTIONAL and list the choices, including "nothing".
- Never draw a label on top of a copy slot: it hides the copy. Labels go inside empty art slots, or as small numbered badges in the margin with a legend under the slide.
- After the blueprint, show real slides as images with a caption naming the deck. Only place a slide under a layout when you have confirmed it uses that layout; unconfirmed slides go in the assets group labeled by deck and slide number.

## Themes and grounds

- Model light and dark slides as two color themes so `ground` and `ink` flip together.
- The page's own light/dark switch drives the theme of every preview. Pin each slide to its ground (`data-theme="<id>"` on the slide element) or light slides turn dark when the viewer's page is dark.
- Pin the wrapper around captions and legends too, or they vanish in the other theme.
- Theme names show in the page's theme switcher, so name them plainly ("Light slide", "Dark slide").
- A photo cover is a third ground with no theme of its own: set its type colour directly from a token such as `on-photo`.
- A system cover block bound to a token that equals the ground in one theme disappears there. Check the cover in both.

## Assets and the index

- Upload rendered slides, logos and art as assets first, at most 25 files per call; previews reference them by the returned `/_blob/<id>` URL.
- Record each upload in the index with a name that carries its deck (`deck-011-slide-04.png`). Bare `slide-04.png` becomes ambiguous the moment a second deck is added.
- Write the index last, and re-read it right before any later change.

## Tokens

- Token families are lists of `{name, value, usage}`. A name-to-value map shows as empty.
- Flag an accent that is below 4.5:1 on its ground as large-type only in its usage note, with the ratio `slide_check.py contrast` measured. Never work a ratio out by hand: a hand figure of 4.4:1 was really 3.9:1. Keep the brand's color; do not "fix" it.
- Give each slot's limit in the layout's guidelines ("claim: 8 words, body: 18 words, rows: 5").
- Put slide geometry (width, height, safe line, footer position) in its own token family.

## Writing the files

- Generate previews and guidelines from one script saved as a file beside the system. Long inline shell heredocs break on quotes and apostrophes in slide copy.
- Use HTML entities for apostrophes and quotes inside placeholder copy.
- The saved kit in the template folder is the working copy, so the kit can be revised without re-reading it from the artifact.

## No Design System type on the account

The saved kit is the deliverable. `kit/DESIGN-SYSTEM.md` holds the brand book, tokens as tables and each layout's slots and limits. `kit/index.html` is one page with the pick table, every blueprint and the try-on slides, with the slides inline in the page (slides loaded through iframes from local files render blank) and the fonts in `kit/fonts/` linked with relative paths.

## The checks script

`${CLAUDE_PLUGIN_ROOT}/scripts/slide_check.py`: run it, do not read it.

- Colours of an image: `python "${CLAUDE_PLUGIN_ROOT}/scripts/slide_check.py" palette <image ...>`
- Contrast of an HTML slide, every text block against the pixels behind it: `python "${CLAUDE_PLUGIN_ROOT}/scripts/slide_check.py" contrast <slide.html ...> --scale <viewed size / authored size>` (about 0.36 for a 1080 px slide on a 390 px phone)
- Add `--size WxH` to `contrast` when the kit's slide is not 1080x1350.
- `--help` lists the options; `--selftest` proves it works on this machine.
- `python` not found (stock Mac): use `python3` in every command.

`palette` needs Pillow; `contrast` also needs Playwright with Chromium. A package is missing: ask the coach in one line ("I need to install two small tools to read colours and measure contrast, about a minute. OK?"), then install it yourself (`python -m pip install pillow playwright`, then `python -m playwright install chromium`). The coach never types a command. They decline, or the install fails: skip the contrast check, say it was skipped in the hand-over, and after a failed install offer the failure report in the skill.

## Failures already hit

| What happened | Cause | Rule |
|---|---|---|
| The user said it would look like "the same exact carousel every time" | Layouts were live copies of one deck's slides, named for that deck's roles | Method rules 1 and 2 |
| Every preview blank | No `components/bundle.js` | Previews |
| Cream slides rendered dark | Page theme switch reached the slides | Themes and grounds |
| A contrast ratio in the tokens was wrong | Worked out by hand instead of measured | Tokens |
| A 60% opacity footer passed contrast at 20:1 | The check ignored opacity set on a parent | Fixed in `slide_check.py`; the cream footer really measures 4.3:1 |
| Reference mode would have copied the other creator's slides in as examples | Step 4 said "real slides" without saying whose | Method rule 5 |
| A comparison layout was dropped as a one-off | "Appears once" was the only test | Method Step 3 |
| A script changed nothing | Heredoc quoting error stopped the whole command | Writing the files |
