---
name: carousel-superengine:carousel-templates
description: Save a finished carousel's look as a reusable design system, and build future carousels from saved looks in one step. Two modes — templatize (capture the look after a build) and use-template (drop new copy into a saved look and go straight to render). Trigger phrases include "save this look", "save my design system", "templatize this", "use my template", "same look as last time", "build it in my template".
---

# Task: templates

The compounding loop: create → render → **save the look** → next time, **drop copy in and go**.
A coach's third carousel takes minutes because their first became a template.

## Load
${CLAUDE_PLUGIN_DATA}/business-config.md if present (the persisted filled config — read FIRST) → else ${CLAUDE_PLUGIN_ROOT}/references/business-config.md (shipped template only) — brand name for the template path
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
4. Hand straight to `carousel-render` with the template attached: Path A → anchor.png + style.md
   drive the briefs; Path C/workspace → design-prompt.md with the copy placeholders filled.
5. Render's exits take over from there.

## Ends with (offer, never block)
- After **templatize**: "Use it right now on a fresh topic?" → `carousel-create` with the preset —
  "use my template" · **"Want weekly builds in this look?"** — the recipe is complete now (voice +
  look + topics), so autopilot drafts are one yes away → scheduled-builds flow (only when
  `{{SCHEDULE_STATUS}}` is unset; respect the once-per-session rule)
- After **use-template**: flows into `carousel-render`; render's exits apply.

## Rules
- Templates are per-brand shared assets — write only under `~/.claude/revxl/<brand>/carousel/templates/`.
- Never overwrite an existing template silently; same name → confirm or version the name (-v2).
- Capture real values only (from the actual render/kit) — no invented brand colors.
- One template = one look. A coach wanting a second style saves a second template, not edits.
