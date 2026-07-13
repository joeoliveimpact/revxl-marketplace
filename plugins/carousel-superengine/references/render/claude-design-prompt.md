# Claude Design Prompt — Path C (paste-ready assembly)

Path C hands the coach ONE complete prompt to paste into Claude Design (claude.ai/design — the
"Design" option inside their existing Claude plan; no extra tool, no connector). Claude Design
returns a multi-card carousel they export as PNGs (optional Canva pass for final tweaks).

## What the assembled prompt must contain — all of it, in this order

1. **The job, one line.** "Design a <N>-slide Instagram carousel, 1080×1350 portrait cards, for
   <coach's positioning from config>."
2. **The design system.** From the saved template when one exists (colors, fonts, margins,
   watermark corner, per-slide layout pattern) — otherwise from the brand kit in config + the
   proven default: cream/off-white base, one deep anchor color, ONE accent reserved for data points
   and CTA, two locked fonts (one bold display, one quiet body).
3. **Per-slide content, verbatim.** For each slide: role (hook / value / summary / CTA), the EXACT
   copy in quotes (headline + body, bold-marked skim path), and the one-line visual direction from
   the package.
4. **The guardrails, stated as instructions** (Claude Design follows them when told):
   - Text ≤20% of each card's area; body 25-50 words max; one idea per card.
   - Headlines ≥36px-equivalent bold; body ≥22px-equivalent; 35-45 characters per line.
   - Max 2-3 colors per card; high contrast text-on-background, always.
   - Same two fonts on every card. Watermark (@handle) same corner, every card.
   - One dominant visual per card; generous negative space; no clip art, no stock-photo look.
   - CTA card wired to `{{CTA_DESTINATION}}` exactly as the package words it.
5. **Slide count + order lock.** "Exactly <N> cards, in this order. Do not merge, split, or reorder."

## Delivery script (what render tells the coach)

First time (teach mode on): explain the 3 steps in plain words — (1) copy this whole block, (2)
paste it at claude.ai/design and let it build, (3) export the cards as PNGs; upload straight to
Instagram, or pull into Canva first if you want to nudge anything. Add: "Your slide text is locked
in the prompt — if a card comes back with different words, tell it 'use my exact copy on card N'."

Repeat use: hand the block, one line: "Same drill — paste at claude.ai/design, export PNGs."

## Honesty rules

- Claude Design output can drift from copy — tell the coach to CHECK text against the package
  before posting (they approve every card; drafts only).
- LinkedIn: PNGs from Claude Design must be assembled into a single PDF document post (5-10 pages).
  On Claude Code, offer the workspace assembler; otherwise name the manual path (Canva → share →
  download as PDF) in one line.
- If the coach's plan doesn't show the Design option, say so and fall back: workspace render (Code)
  or the per-slide briefs for their own tool. Never leave them stuck.
