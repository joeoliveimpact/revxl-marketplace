---
name: carousel-superengine:carousel-templates
description: Save a finished carousel's look as a reusable design system, and build future carousels from saved looks in one step. Three modes — templatize (capture the look after a build), use-template (drop new copy into a saved look and go straight to render), and build-a-kit (turn the coach's own finished carousels, or one reference carousel, into a kit of reusable slide layouts in their brand). Trigger phrases include "save this look", "save my design system", "templatize this", "use my template", "same look as last time", "build it in my template", "make a design system from my carousels", "build a layout kit", "copy this carousel's layout", "make a carousel template kit", "turn my carousels into templates", "make mine look like this one".
---

# Task: templates

The compounding loop: create → render → **save the look** → next time, **drop copy in and go**.
A coach's third carousel takes minutes because their first became a template.

**Pick the mode before anything else:** a look to save from ONE build or a brand kit → Mode 1. New copy into a saved look → Mode 2. Several finished decks, or someone else's carousel whose layout they want → Mode 3. **Context was compacted mid-kit?** Re-read ${CLAUDE_PLUGIN_ROOT}/references/design-system.md and the saved `kit/inventory.md` before continuing.

## Load
${CLAUDE_PLUGIN_DATA}/business-config.md if present (the persisted filled config — read FIRST) → else ${CLAUDE_PLUGIN_ROOT}/references/business-config.md (shipped template only) — `{{BRAND_SLUG}}` is `<brand>` in the template path. Still a placeholder → ask the brand name once, slug it (lowercase, letters and numbers only), check `~/.claude/revxl/` for an existing folder, and write it to `${CLAUDE_PLUGIN_DATA}/business-config.md` before saving anything (create that file from the references copy if it is not there; never write the plugin's own copy)
${CLAUDE_PLUGIN_ROOT}/references/design-rules.md (capture fields + the 90-day system rule)

**Template home:** `~/.claude/revxl/<brand>/carousel/templates/<template-name>/` — shared brand
asset, survives plugin updates, visible to every REVXL engine. Never inside the plugin dir.

## Mode 1 — templatize (after a render, or importing an existing brand look)

1. **Name it.** Ask for a short name ("clean-coral", "story-dark") — kebab-case the folder.
2. **Capture the design system as named tokens** — write `style.md`:
   - `colors:` base / anchor / accent (names + hex)
   - `fonts:` display + body (the locked pair)
   - `frame:` margins, watermark corner + handle, headline/body scale, alignment habits
   - `layout pattern:` per-slide-role skeleton (hook slide look, value slide look, CTA slide look)
   - `source:` what this came from (render session date, imported Canva kit, teardown handle)
3. **Write the path-specific recipe:**
   - Path A render → also capture the ANCHOR image (copy the coach's picked slide-1 PNG into the
     pack as `anchor.png`) + the winning brief's STYLE/COMPOSITION/TEXTURE lines.
   - Path C / workspace render → write `design-prompt.md`: the reusable prompt block with the
     design-system section filled and per-slide copy left as `<SLIDE-N COPY>` placeholders.
4. **Write `meta.md`:** created date · source path (A / C / workspace) · platform · one-line
   description. The date drives the staleness nudge.
5. Confirm saved + say what it unlocks: "Next time just say 'use my template' — new copy drops into
   this look and we skip every design question."

**Import variant** (coach has an existing design system / Canva brand kit, no render yet): same
capture conversation, fields from their answers/screenshots instead of a finished build.

## Mode 2 — use-template (the everyday fast lane)

1. List saved templates (name + one-liner + age). One template → confirm it; several → coach picks.
2. **Staleness nudge (90-day rule, once):** if `meta.md` date is >90 days old — "This look has run
   ~N months. Recognition compounds, so keeping it is smart — but if results have flattened, want a
   refresh pass on it after this build?" Never block the build on it.
3. Get the new content: a finished package from `carousel-create` in this conversation, or the
   topic → run create with the template preset (create skips design questions; the look is decided).
   **Template has a `kit/` folder** → read `kit/DESIGN-SYSTEM.md` BEFORE create writes copy and give
   create the pick table and each layout's slot limits, so the copy is written to fit.
4. Hand straight to `carousel-render` with the template attached: Path A → anchor.png + style.md
   drive the briefs; Path C/workspace → design-prompt.md with the copy placeholders filled.
   **Template has a `kit/` folder** → attach `kit/DESIGN-SYSTEM.md`, `kit/slides.css` and the
   blueprints, with the layout picked for each slide: workspace render builds from them instead of
   designing a new look. No workspace render on this setup → design-prompt.md carries the kit.
5. Render's exits take over from there.

## Mode 3 — build a kit (from finished decks, or from one reference carousel)

For the coach who has shipped a few carousels and wants every next one to look like theirs without looking the
same, or who saw a carousel and wants its layout in their own brand. The output is a saved template plus a
`kit/` of open-slot layouts, a pick-by-content table and the fixed look.

1. Read ${CLAUDE_PLUGIN_ROOT}/references/design-system.md and follow its six steps exactly. It holds the rules,
   where the kit is saved, the checks and the hand-over.
2. **From my decks** → their own finished slides, every deck that shares the look.
   **From a reference** → one carousel: a pick from their Content Goldmine dashboard when they have one that
   lists carousels, else a teardown already done, else a pasted link. Structure only; the look is the coach's.
3. Published as a Design System page when the account offers that artifact type; otherwise the saved kit and
   its `kit/index.html` are the deliverable. Never block on it.
4. Hand over per Step 6 of the method, then the offer below.

## Ends with (offer, never block)
- After **templatize**: "Use it right now on a fresh topic?" → `carousel-create` with the preset —
  "use my template" · **"Want weekly builds in this look?"** — the recipe is complete now (voice +
  look + topics), so autopilot drafts are one yes away → scheduled-builds flow (only when
  `{{SCHEDULE_STATUS}}` is unset; respect the once-per-session rule)
- After **use-template**: flows into `carousel-render`; render's exits apply.
- After **build a kit**: "Try it on a fresh topic?" → `carousel-create` with the template preset — "use my template"

## Rules
- Templates are per-brand shared assets — write only under `~/.claude/revxl/<brand>/carousel/templates/`.
- Never overwrite an existing template silently; same name → confirm or version the name (-v2).
- Capture real values only (from the actual render/kit) — no invented brand colors.
- One template = one look. A coach wanting a second style saves a second template, not edits.
- A kit is layouts with open slots, never one deck frozen. From someone else's carousel take structure only: never their words, colors, fonts or images.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `carousel-superengine/reports/report-body.md` under the workspace folder: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text, slide copy).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin carousel-superengine --plugin-version 0.6.0 --skill carousel-templates --step '<saving the template, building the kit, the slide checks or publishing>' --error-line '<the error line>' --summary '<headline>' --body-file carousel-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`

The client never types any of these; you run them.
