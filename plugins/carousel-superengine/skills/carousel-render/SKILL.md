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
- create's render-handoff block carries a per-slide verdict; confirm the route with the coach in one
  line before generating. Coach's explicit pick always wins.

**2. Environment unlock (Claude Code only).** When Bash + Python are available:
- Offer workspace render: "I can build these right here as finished PNG files (or a LinkedIn PDF) —
  no other tool needed. Want that?" Method: workspace-render.md.
- Suggest once, never block: "Slide design is the one place a smarter model visibly pays off — want
  to switch to the top model for this build?" Accept whatever they run.
On Cowork/Desktop: skip this step entirely (no local render; A and C only).

**2a. Render.**
- **Path A** per render-briefing.md: ANCHOR first (slide 1 ×3 versions, coach picks) → then
  ONE-AT-A-TIME (anchor as reference + that slide's exact copy). Before choosing the face path,
  check for a trained Soul (MCP: `show_characters` list, status ready) — one found → generate with
  it (the images ARE the coach). None → reference-image face consistency; offer the optional
  Soul explainer from `carousel-setup` once, never push.
  **Engine (probe in this order):** (1) the **Higgsfield MCP** when connected — tools like
  `generate_image` / `models_explore` / `balance` (find via ToolSearch; server prefix varies) —
  this is the preferred route: no CLI, no key file, auth rides the account session; (2) the
  `higgsfield-generate` skill/CLI as fallback. **Model:** Nano Banana Pro class for carousel slides
  — it holds legible text AND supports 4:5 natively (dogfood-verified 07.18.26: slide-level text
  came back character-perfect at 4k). Do NOT default to GPT Image 2 class: no 4:5 support, ~3.5×
  the credits. **Always pass `aspect_ratio` (4:5) and `resolution` as real API params, never prose
  only** — the server silently coerces unsupported ratios instead of erroring; after each
  generation verify the returned dimensions match, and surface any coercion to the coach.
  **State credit cost BEFORE the first paid generation** — on the MCP use the `get_cost: true`
  preflight (returns exact credits, spends nothing); coach confirms.
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
