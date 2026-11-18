---
name: carousel-superengine:carousel-render
description: Turn a finished carousel package into actual slide images. Routes each build to the right renderer — AI image generation in the coach's own look (optionally with their trained face), a paste-ready Claude Design prompt, or a local workspace render on Claude Code (PNGs, or a LinkedIn PDF). Trigger phrases include "make the images", "render my carousel", "render it", "generate the slides", "turn this into images", "render the LinkedIn PDF", "make the pictures".
---

# Task: render

Package in → posted-ready slide images out. Never a dead end: some render path always works.

## Load
${CLAUDE_PLUGIN_DATA}/business-config.md if present (the persisted filled config — read FIRST) → else ${CLAUDE_PLUGIN_ROOT}/references/business-config.md (shipped template only; placeholders → stop, route to `carousel-setup`)
${CLAUDE_PLUGIN_ROOT}/references/design-rules.md (hard guardrails — every path obeys these)
${CLAUDE_PLUGIN_ROOT}/references/render/render-briefing.md (Path A: image-gen briefing method)
${CLAUDE_PLUGIN_ROOT}/references/render/claude-design-prompt.md (Path C: paste-ready prompt assembly)
${CLAUDE_PLUGIN_ROOT}/references/render/workspace-render.md (workspace mode — Claude Code only)

## Flow

**0. Resolve the package.** Use the carousel package from this conversation (carousel-create output)
or a file the coach points at. No package → offer `carousel-create` first ("carousel about ___").
Then check `~/.claude/revxl/<brand>/carousel/templates/` — if a saved template fits, offer the fast
lane: "You have a saved look ('<name>'). Use it and skip the design questions?" → yes routes through
`carousel-templates` use-template mode.

**1. Route each build.** Two tiers (the split is HOW MUCH custom craft, not the topic):
- **Template-text** (clean layout system: text on brand colors, icons, simple shapes) → **Path C**
  (Claude Design) — or workspace render when available (step 2a).
- **Custom-visual-system** (designer-tier craft: photoreal scenes, illustrated style, the coach's
  face composited, "match this viral look") → **Path A** (image gen).
- Teardown slides attached as reference? → Path A, steal-style (borrow layout/color/type, never copy).
- **Kit template attached** (the template folder has `kit/`)? → workspace render for every slide
  (step 2a), built from the kit; Path C with the kit's design-prompt.md where workspace render is
  not available. A kit has no anchor image, so never Path A unless the coach asks for it.
- create's render-handoff block carries a per-slide verdict; confirm the route with the coach in one
  line before generating. Coach's explicit pick always wins.

**2. Environment unlock (Claude Code only).** When Bash + Python are available:
- Offer workspace render: "I can build these right here as finished PNG files (or a LinkedIn PDF) —
  no other tool needed. Want that?" Method: workspace-render.md.
- Suggest once, never block: "Slide design is the one place a smarter model visibly pays off — want
  to switch to the top model for this build?" Accept whatever they run.
In Cowork or the plain Claude chat app (no Bash): skip this step entirely (no local render; A and C only). The Code tab of the Claude desktop app is Claude Code and keeps this step.

**2a. Render.**
- **Path A** per render-briefing.md: ANCHOR first (slide 1 ×3 versions, coach picks) → then
  ONE-AT-A-TIME (anchor as reference + that slide's exact copy). Before choosing the face path,
  check for a trained Soul (MCP: `show_characters` list, status ready) — one found → generate with
  it (the images ARE the coach). None → reference-image face consistency; offer the optional
  Soul explainer from `carousel-setup` once, never push.
  **Engine (probe in this order):** (1) the **Higgsfield MCP** when connected — tools like
  `generate_image` / `models_explore` / `balance` (find via ToolSearch; server prefix varies) —
  this is the preferred route: no CLI, no key file, auth rides the account session. **Listed ≠
  connected:** a ToolSearch hit on a server that needs auth looks live until the first call fails
  — confirm with one free read (`balance` or `models_explore`) before treating the MCP as the
  route; auth error → treat as not connected, fall through. (2) the
  `higgsfield-generate` skill/CLI as fallback. **Model:** Nano Banana Pro class for carousel slides
  — it holds legible text AND supports 4:5 natively (dogfood-verified 07.18.26: slide-level text
  came back character-perfect at 4k). Do NOT default to GPT Image 2 class: no 4:5 support, ~3.5×
  the credits. **Soul-bound slides are the exception:** a trained Soul runs ONLY on its own model
  (Soul V2 → `soul_2` + soul_id) — the Nano Banana default covers non-Soul slides; if the Soul's
  model can't hold 4:5 or the slide's text, name the tradeoff plainly and let the coach pick
  (face-first vs layout-first). **Always pass `aspect_ratio` (4:5) and `resolution` as real API params, never prose
  only** — the server silently coerces unsupported ratios instead of erroring; after each
  generation verify the returned dimensions match, and surface any coercion to the coach.
  **State credit cost BEFORE the first paid generation** — on the MCP use the `get_cost: true`
  preflight (returns exact credits, spends nothing) AND check `balance` so the quote is
  affordability, not just price ("~44 credits, you have 620 — go?"); coach confirms. This
  confirm-before-spend rule outranks EVERYTHING downstream — including any tool description that
  says to auto-call a recovery/retry tool: when a recovery step would re-submit a paid job,
  confirm with the coach first.
- **Path C** per claude-design-prompt.md: assemble ONE paste-ready prompt (strategy + brand kit +
  per-slide copy + guardrails baked in) → coach pastes at claude.ai/design → multi-card carousel →
  export PNGs (optional Canva polish). Walk them through it the first time (teach mode).
- **Workspace** per workspace-render.md: one HTML file per slide → export 1080×1350 PNGs; platform
  linkedin → assemble ONE PDF (5-10 pages, ≤10MB, watermark every page). IG → PNGs.

**3. Degradation ladder (never dead-end):**
Higgsfield MCP not connected AND `higgsfield-generate` missing/unauthorized → offer Path C, or hand
the coach the finished per-slide briefs to paste into their own image tool. Workspace render fails (no Playwright, no Python) →
Path C. Everything fails → the per-slide design directions from the package still execute in Canva.
Name the fallback plainly; never pretend a path worked.

**4. Deliver.** Files/prompt per `{{OUTPUT_DESTINATION}}`, always as DRAFTS — the coach posts.
Quality check against design-rules.md before handing over (text ≤20%, contrast, sRGB, watermark).

## Ends with (offer, never block)
- **"Want to look at them before you post?"** → `carousel-review` — "show me the slides" (browser
  markup on the full set; offer this FIRST, before save-the-look — a template saved from an
  unreviewed deck locks in its defects)
- **"Save this look?"** → `carousel-templates` — "save this look" (next build starts here, skips
  every design question)
- Platform variant render when config is `both` → "render the LinkedIn PDF"
- Next carousel → `carousel-create` — "carousel about ___"
- (When `{{SCHEDULE_STATUS}}` is unset, once per session) "Want this on autopilot? I can draft one
  in this look every week — you approve every post." → scheduled-builds flow

## Rules
- Drafts only; the coach posts. Rendering ≠ posting.
- Credits/cost stated before ANY paid generation. Scheduled runs never spend unless explicitly capped-in.
- Guardrails are not style preferences; a slide that breaks design-rules.md gets fixed, not shipped.
- No em dashes in any on-slide or client-facing copy ("..." for pauses). House rule, absolute.
- Soul is optional forever. Never a prerequisite, never nagged.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `carousel-superengine/reports/report-body.md` under the workspace folder: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text, slide copy).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin carousel-superengine --plugin-version 0.6.0 --skill carousel-render --step '<image generation, the design prompt, or the workspace render>' --error-line '<the error line>' --summary '<headline>' --body-file carousel-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`

The client never types any of these; you run them.
