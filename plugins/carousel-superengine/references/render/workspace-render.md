# Workspace Render — Claude Code power mode (HTML → PNG / LinkedIn PDF)

Claude Code + Python only. Builds finished slide files locally: one HTML file per slide, exported
to 1080×1350 PNGs (Instagram) or assembled into a single PDF (LinkedIn document post). The coach
never touches code — this all happens in their workspace; they get files.

Not available on Cowork/Desktop — never offer it there.

## Method

1. **Design the system first, then fill slides.** Decide once: palette (from template/brand kit —
   2-3 colors), the two fonts, margin frame (~60px), watermark corner, headline/body scale. Every
   slide reuses the system; only the focal content changes. Slides designed one-off read as a mess.
2. **Write one self-contained HTML file per slide** (`slide_01.html` …) in a scratch dir:
   - Fixed canvas: `<div id="slide" style="width:1080px;height:1350px">` (LinkedIn: 1080×1080 or
     keep 1080×1350 — pick per platform-nuance.md and stay consistent).
   - **Embed fonts as base64** `@font-face` data-URIs (or system-font fallbacks: Arial Black /
     Georgia class). Never link external font CDNs — headless export races the network and ships
     fallback fonts silently.
   - All CSS inline or in a `<style>` block; zero external requests.
   - Obey design-rules.md: text budget per the deck's format (default 20%; spec-sheet/educational
     up to 25-40% — design-rules.md is authoritative), headline ≥36px bold, body ≥22px, 35-45
     chars/line, line-height 1.4-1.6, 2-3 colors, watermark same corner every slide, bold skim path.
   - Craft, not template-default: opinionated type scale, real negative space, one deliberate
     accent. If it would pass for a slide deck default theme, push further.
3. **Export** with the bundled script:
   - PNGs: `python ${CLAUDE_PLUGIN_ROOT}/scripts/render_slides.py <dir> --out <dir>/png`
   - LinkedIn PDF: add `--pdf <dir>/carousel.pdf` (assembles pages in filename order).
   - The script screenshots the `#slide` ELEMENT (`element.screenshot()`, never viewport clip) —
     exact pixels, no scrollbar/DPR surprises.
4. **Verify before delivering:** open/Read 2-3 exported PNGs — text renders, fonts applied, nothing
   clipped. PDF: page count 5-10, file ≤10MB, watermark on every page. Fix in HTML, re-export.
5. **Deliver** file paths per `{{OUTPUT_DESTINATION}}`. Drafts; the coach posts.

## Dependencies (handle conversationally, once)

Playwright missing → ask, then: `pip install playwright && playwright install chromium`
(~1-2 min, one time). Coach declines or install fails → degrade to Path C without ceremony.

## Model note

Slide design quality tracks model quality more than any other step in this engine. On entry (once
per session): "Slide design is the one place a smarter model visibly pays off — want to switch to
the top model for this build?" Suggest only; run with whatever they choose.
