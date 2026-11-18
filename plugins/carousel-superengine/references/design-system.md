# Layout Kit Method (carousel-templates, Mode 3)

Builds a kit the coach can make any future carousel from: layouts with open slots, the fixed look,
and a pick-by-content guide. A kit is a saved template with more in it, so it lives in the same
template home and `use my template` works on it the day it is saved.

**Compacted mid-build?** Re-read this file, then `kit/inventory.md` and its Progress checklist in
the template folder, before doing anything else.

## Rules for every run

1. **Build a kit, never a snapshot.** One deck's slides and copy frozen as "the system" make every
   later carousel look like that deck. Layouts get open slots and neutral placeholder copy; real
   slides appear only as examples beside them.
2. **Name layouts by the job they do** (Statement, Numbered, Comparison), not by the role they
   played in one deck (Rehook, Catch), so they read as reusable for any topic.
3. **Say what is fixed and what flexes.** Fixed: the look and any bookends every deck shares.
   Flexible: which layouts, how many, in what order, and what fills each slot. Without this split
   the coach cannot tell a rule from an accident of one deck.
4. **Label where every value came from:** *exact* (read from build code), *estimated* (measured
   from an image), or *new* (chosen for this kit, not yet shipped). A guess written as fact gets
   copied into every later deck.
5. **From someone else's carousel, take structure only.** Slide roles, slot positions and rhythm
   carry over. Their words, art, colors, fonts and signature devices (a recurring graphic, a
   catchphrase, a copy formula) do not, and their images never go into the kit, as examples or as
   assets: cite the source link instead. The look, footer and bookends always come from the coach's
   own brand. Only the slide size may follow the reference, and only when the coach asks.
6. **Never rewrite the coach's copy** when quoting their slides as examples.
7. **No one to ask?** Take the default named in the step, write the question down, and list every
   open question in the hand-over.

## Where the kit lives

    ~/.claude/revxl/<brand>/carousel/templates/<kit-name>/
      style.md            # the look as named tokens (the same file Mode 1 writes)
      design-prompt.md    # reusable prompt block: tokens + the layout list, copy left as placeholders
      meta.md             # Mode 1's fields (created date, platform, one-line description) plus
                          # kind: kit, render path: workspace (else C), source mode,
                          # source decks or link, artifact link
      kit/
        inventory.md      # Step 2, plus the Progress checklist
        DESIGN-SYSTEM.md  # the brand book: pick table, layouts, slots and limits, fixed and flex
        slides.css        # every slide rule, written against the tokens
        layouts/          # one blueprint HTML per layout
        examples/         # the coach's OWN slides only, named by deck and slide
        fonts/            # the font files the decks used (none to copy: see Step 4)
        tryon/            # the three try-on slides from Step 5, as HTML and PNG
        build_kit.py      # the script that generates the files above
        index.html        # one page: pick table, every blueprint, the try-on slides

`<brand>` is `{{BRAND_SLUG}}` from the business config. Same name already saved: confirm, or
version the name (`-v2`). Never overwrite a saved template silently.

## Workflow

Copy this checklist into `kit/inventory.md` and tick it off:

```text
Progress:
- [ ] Step 1: Kit named, source chosen
- [ ] Step 2: Inventory written
- [ ] Step 3: Layouts and fixed/flex split decided
- [ ] Step 4: Kit built and saved
- [ ] Step 5: Checked
- [ ] Step 6: Handed over
```

**Step 1. Name the kit and choose the source.** Ask for a short name (default `<brand>-kit`),
kebab-case it, and create the template folder and its `kit/` folder now. Then pick the mode:

- **From my decks:** ask where the finished slides are (a folder, or the images themselves) and
  look in the current workspace for earlier render folders first. Use every deck that has final
  rendered slides (posted or not) and shares one look, not only the latest. Decks share a look when
  their build code uses the same fonts, palette and slide frame (image-only decks: the palette
  check returns the same colours and the frame matches). More than one look: ask which;
  default to the most recent look and name the decks left out.
- **From a reference:** one carousel whose layout the coach wants in their own brand. Offer the
  sources in this order and take the first that exists:
  1. **Content Goldmine dashboard.** If the workspace holds
     `visuals/Content Goldmine Dashboard - <date>.html` (built by the shortform engine's
     `content-goldmine` skill) and it lists carousels, show those winners and let the coach pick
     one. No carousels in it: say so in one line and move on.
  2. **A teardown already done** in this conversation or workspace (`carousel-teardown`).
  3. **A pasted link or images.** A link goes through `carousel-teardown`'s fetch only (its pull
     step). Teardown's rule that a rebuild may borrow the look does not apply to a kit: rule 5
     above wins.

  Download the slides in this same run: Instagram slide links stop working within days. The
  pull returned the cover only, or nothing (no key, no cookies): ask the coach for screenshots of
  every slide and carry on. Save reference slides in the workspace at
  `carousel-superengine/reference/<post id>/`, never in the template folder.

  The look comes from the coach's brand, in this order: a saved template's `style.md`, their most
  recent shipped deck, the palette direction and hex values noted at setup. No brand at all: ask for colors and fonts before building.

Done when you can name the source decks (or the one reference) and where the look comes from.

**Step 2. Inventory.** Write `kit/inventory.md`: one row per source slide with deck, slide number,
job, slots (headline, body, image, number, logo, footer), ground (light, dark, photo) and sizes.
Read build code and stylesheets first; open the rendered images to confirm; read copy files for
word counts. Where decks disagree on a value, the latest deck's value is the token and the range
goes in its usage note.

With only images to go on (a reference, or own decks with no build code), look at every slide in
posted order (use the fetch's metadata when file order and post order differ; if the order cannot
be recovered, mark the deck shape estimated) and write one line each on: ground, colour, type,
hierarchy, layout, recurring parts (handle, counter, swipe cue, logo spot), content blocks (how
lists, numbers, quotes and screenshots are drawn) and copy feel (words per slide, caps, tone). Get
colours with the palette check below instead of judging them by eye. If the slides carry no text
at all, tell the coach before going further: the kit will be photo roles plus a caption rule, with
no copy slots. Reference mode: leave the reference's colours and type out of the inventory;
record structure only.

Done when every slide in every source deck is in the file.

**Step 3. Decide the layouts.** Group slides that share a structure into one layout and name it by
job. A structure that shipped only once still becomes a layout when it does a job a later deck
could need (a comparison, a quote, a big question); mark it "shipped once". Only a slide that
cannot be separated from one deck's content stays an example. A small difference inside a
structure (headline at the top instead of the bottom) is a variant of that layout, not a new one.

For each layout write: its slots; a hard limit per slot, in words for copy at the slot's stated
font size and as a count for rows or items, taken from the longest copy that shipped and still fit
(reference mode: start from the reference's word counts, then re-fit at the brand's type size in
the blueprint and keep what fits); what it is for; and whether it is required (the format breaks
without it, such as the opener and closer), usual (in most decks, can be skipped) or optional.
Limits never exceed the text budget in design-rules.md.

Then write the fixed/flex split (rule 3) and a table mapping content needs to layouts ("a list" →
the numbered layout). A kit with a single layout is valid: the table then maps content to what
fills its slots.

Done when a topic none of the source decks covered could be planned from the table alone.

**Step 4. Build and save.** Generate the files from `kit/build_kit.py`, saved to disk, never from
a long inline shell command: quotes and apostrophes in slide copy break those and the whole
command fails silently. Write, in this order:

1. `style.md`: colors per ground, type styles, spacing, radii, slide size and safe lines, each with
   a usage note and its exact / estimated / new label. Type samples are neutral, never a source
   deck's headline. Keep Mode 1's field names (`colors:`, `fonts:`, `frame:`, `layout pattern:`,
   `source:`) so `use my template` reads a kit like any other template.
2. `kit/fonts/` and `kit/slides.css` (every slide rule, written against the tokens). No font
   files to copy (image-only decks, or a reference): ask the coach for the font names or files;
   without an answer use the nearest system font, label it estimated, and list it as an open
   question.
3. `kit/layouts/<Layout>.html`: a **blueprint** (the layout with labeled slots and placeholder
   copy filled to each slot's limit, so a slot that overflows at its own maximum shows up now).
   The coach's own slides that filled it go in `kit/examples/`, from as many decks as have one.
4. `kit/DESIGN-SYSTEM.md`: open with the pick-by-content table, then deck shapes that have shipped
   (as examples, not presets), the layouts with slots and limits, fixed, flex, and how to build a
   deck.
5. `design-prompt.md` (tokens, the layout list and the pick table, per-slide copy left as
   `<SLIDE-N COPY>`) and `meta.md` with every field named in the folder map above. A kit has no
   `anchor.png`: it renders through workspace render, or the design prompt where that is not
   available.
6. `kit/index.html`: the pick table, every blueprint and the try-on slides, inline in the page
   (slides loaded through iframes from local files render blank).

**Publish it when the account can.** List the Artifact types. If a Design System type is offered,
publish with its `type_url`, a title and no files, then follow the instructions that call returns,
and save the link in `meta.md`. If it is not offered, the saved kit and `kit/index.html` are the
deliverable: open `index.html` for the coach and say in one line that the shareable page is not
available on this account. Never stop the build over it.

Read ${CLAUDE_PLUGIN_ROOT}/references/design-system-build-notes.md before writing the first
blueprint: it holds the mechanics and the traps that cost a rebuild.

**Step 5. Check.** Go back to Step 4 when check 1, 2 or 3 fails.

1. **Look.** Open `kit/index.html` in the browser pane (or the published page) and look at every
   layout in each ground.
2. **Snapshot test.** Search the tokens, stylesheet, blueprints and layout notes for nouns from
   the source decks (product names, the keyword, the hook). Any hit fails. The coach's handle and
   face are brand, not content. The brand book may name source decks only in its shipped-shapes
   table. In reference mode, also confirm no color, font, wording or image from the reference is
   in the kit.
3. **Try-on.** Build three slides on a topic none of the source decks covered (the opener, one
   content slide, the closer; include a dark slide if the kit has one) from the blueprints and
   tokens alone, with placeholder frames where art would go. Save them as
   `kit/tryon/slide_01.html` to `slide_03.html`, each with its slide element carrying `id="slide"`.
   Export them with
   `python "${CLAUDE_PLUGIN_ROOT}/scripts/render_slides.py" kit/tryon --out kit/tryon` (add
   `--width` and `--height` when the kit is not 1080x1350), show the three images in your reply
   and put them in `kit/index.html`. If they cannot be built without opening a source deck, the
   kit is missing something.
4. **Contrast.** Run the contrast check on the try-on HTML slides, and on source slides that
   exist as HTML with real art (image-only sources: try-ons only); results over a placeholder
   frame mean nothing. A low ratio is a finding, not a
   failure: record the measured ratio in that token's usage note, keep the brand's colour, and
   tell the coach.

**Step 6. Hand over.** Give the template name (and the link, when published), the layout list, the
fixed/flex split in two lines, every open question (rule 7), and what is estimated, new or
unverified. Then: "Say 'use my template' and your next carousel is built from this kit."

## The checks script

`${CLAUDE_PLUGIN_ROOT}/scripts/slide_check.py` reads an image's colours (`palette`) and measures
text contrast on an HTML slide (`contrast`). The exact commands, what it needs and what to do
when a package is missing are in the build notes, under "The checks script".
