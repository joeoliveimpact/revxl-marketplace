# Build Core — Shared Five-Stage Flow

Every intake skill (`/lm-create`, `/lm-revamp`, `/lm-inspired-by`) seeds a run and then hands off here. This document is the shared contract for the blueprint → draft → design → score → output pipeline. No intake skill re-implements these stages; they only supply the seed data.

---

## Stage 1 — Blueprint

Decide the shape of the magnet before writing a word.

**Load first (bundled references):**
- `${CLAUDE_PLUGIN_ROOT}/references/lead-magnet-frameworks.md` — the Hormozi type/step framework this stage applies
- `${CLAUDE_PLUGIN_ROOT}/references/format-by-niche-matrix.md` — format selection by niche + audience sophistication
- `${CLAUDE_PLUGIN_ROOT}/references/hooks-and-titles.md` — naming method for the Hook / name decision

| Decision | What to lock in |
|---|---|
| **Type** | One of Hormozi's three magnet types: (1) consumable (guide, checklist, swipe file), (2) tool (template, calculator, framework), or (3) lead-qualifying bridge (mini-course, quiz, video series). |
| **Format** | PDF field guide, interactive HTML, audio teardown, etc. Pick the format that matches the audience's time-to-value expectation. |
| **Hook / name** | Run Hormozi step 4: the name itself must carry the promise. Format: `[Result] [For Whom] [Speed/Ease modifier]`. Draft 3 options; pick the sharpest. |
| **The win** | One concrete thing the reader will have, know, or be able to do after consuming the magnet — and nothing else. |

Inputs for this stage come from whichever intake skill seeded the run (e.g., raw copy + url for `/lm-revamp`; niche + audience + rough idea for `/lm-create`).

---

## Stage 2 — Draft

**Voice (in order):** check the shared brain at `~/.claude/revxl/<brand>/voc/` — if
`voice-guide.md` is present, voice-match the draft to it (plus `voc-profile.md` and
`signature-bits.md` where present; honor `provisional` stamps and freshness per the brain's own
rules). If absent, offer the bundled `brand-brain` skill (`${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/SKILL.md`)
before drafting — or, if the user declines, proceed voice-neutral and say so in the "what/why" doc.

Write outcome-first, problem-led, narrow copy that delivers the win decided in Stage 1.

- Open with the problem, not the solution. The reader must feel seen before they feel helped.
- Deliver the "what" and "why" fully. Do not withhold. The implementation gap is what sells the next step.
- Keep language at an 8th-grade reading level. Run every sentence through: "could a busy person skim this and get it?"
- One CTA at the end. State: what the reader does, what happens next, what they get.

All copy is evaluated against `${CLAUDE_PLUGIN_ROOT}/core/rubric.md` in Stage 4 before output.

---

## Stage 3 — Design

Render the draft into the deliverable PDF.

### Template data schema

The template uses four top-level variables:

| Variable | Type | Notes |
|---|---|---|
| `{{ title }}` | string | Document/cover title; also used in the running header on every page. |
| `{{ brand_color }}` | string | CSS hex color (e.g. `#3D2623`). Falls back to `#3D2623` if omitted. |
| `{{ hero_image }}` | string | Path or URL to the cover photo. Optional — omit or pass `""` to skip. |
| `{{ sections }}` | list of section objects | See below. Rendered via `{% for section in sections %}`. |

**`sections` list — each object may contain:**

| Key | Type | Required | Purpose |
|---|---|---|---|
| `eyebrow` | string | no | Small all-caps label above the heading (e.g. "Chapter 1"). |
| `heading` | string | no | Main section heading rendered as `<h2>`. |
| `lead` | string | no | Intro paragraph in larger type below the heading. |
| `blocks` | list of block objects | no | Ordered content blocks for the body of the page (see block types below). |
| `dark` | boolean | no | `true` → dark background page variant. |
| `paper` | boolean | no | `true` → off-white paper background variant (mutually exclusive with `dark`). |
| `disclaimer` | string | no | Small-print text rendered at the bottom of the page. |

**`blocks` list — each block object must have a `type` key:**

| `type` value | Additional keys | Purpose |
|---|---|---|
| `paragraph` | `content` (string) | Body text paragraph. |
| `card` | `heading` (string), `rows` (list of `{label, value}`) | Boxed content card with optional label/value rows. |
| `pull` | `content` (string), `attribution` (string, optional) | Pull-quote block with optional speaker attribution. |
| `faq` | `items` (list of `{q, a}`) | Two-column FAQ grid. |
| `cta` | `label` (string), `url` (string, optional), `sublabel` (string, optional) | Call-to-action button. |

### New build
1. Populate `${CLAUDE_PLUGIN_ROOT}/templates/field-guide.html.j2` with the draft content.
   - Scalar placeholders: `{{ title }}`, `{{ brand_color }}`, `{{ hero_image }}`.
   - `{{ sections }}` is a **list of section objects** (see schema above) iterated via `{% for section in sections %}`.
2. Call `lib.render_pdf.html_to_pdf(html, out_path) -> str` to render the PDF via Playwright/Chromium.
3. Call `lib.qc_pdf.check(pdf_path) -> {"pages": int, "ok": bool, "warnings": [str]}` to validate.
   - If `ok` is `False` or `warnings` is non-empty, fix and re-render before proceeding.

### Revamp / ingest (existing PDF supplied)
1. Call `lib.extract_assets.extract(pdf_path) -> {"colors": [...], "images": [...]}` first to pull brand colors and embedded images from the existing PDF.
2. Seed `{{brand_color}}` and `{{hero_image}}` in the template from the extracted palette and image paths.
3. Render and QC as above.

---

## Stage 4 — Score

**Load first (bundled references):**
- `${CLAUDE_PLUGIN_ROOT}/references/conversion-benchmarks.md` — honest expectation-setting; sanity-check any implied numbers
- `${CLAUDE_PLUGIN_ROOT}/references/lead-magnet-mistakes.md` — screen the draft against the five failure modes before scoring

Run the `${CLAUDE_PLUGIN_ROOT}/core/rubric.md` self-check against the drafted content.

- Score all 15 criteria (Sections A, B, C).
- Any FAIL → revise before output. Return to Stage 2 for copy fixes or Stage 3 for design fixes.
- Any FLAG → note in the JSON sidecar; surface to the user in the "what/why" doc.
- A score of 0 FAIL and 0–2 FLAG = READY to output.

This check is non-negotiable. No output ships without a passing rubric.

---

## Stage 5 — Output

**Load first (bundled reference):**
- `${CLAUDE_PLUGIN_ROOT}/references/nurture-handoff.md` — what happens after opt-in; informs the CTA hand-off and the "what/why" doc's next-step guidance

Deliver three artifacts:

| Artifact | Description |
|---|---|
| **PDF** | The rendered magnet from Stage 3. |
| **"What/Why" doc** | A short plain-English document explaining what strategy decisions were made (magnet type, hook, win) and why — so the client understands their magnet, not just has it. |
| **JSON sidecar** | `magnet-meta.json` with keys: `type`, `hook`, `win`, `sources_used` (list of source kinds that contributed data), `rubric_score` (pass/flag/fail counts), `rubric_flags` (list of flagged criteria and their fix notes). |

---

## Cross-reference index

| Path | Role |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/lib/render_pdf.py` | `html_to_pdf(html, out_path)` — Playwright renderer |
| `${CLAUDE_PLUGIN_ROOT}/lib/extract_assets.py` | `extract(pdf_path)` — brand color + image extraction |
| `${CLAUDE_PLUGIN_ROOT}/lib/qc_pdf.py` | `check(pdf_path)` — page count + warning validation |
| `${CLAUDE_PLUGIN_ROOT}/templates/field-guide.html.j2` | Jinja2 HTML template; scalars: `{{ title }}`, `{{ brand_color }}`, `{{ hero_image }}`; list: `{{ sections }}` (iterated via `{% for section in sections %}`) |
| `${CLAUDE_PLUGIN_ROOT}/core/rubric.md` | 15-criterion scoring rubric; all sections run in self-check mode |
| `${CLAUDE_PLUGIN_ROOT}/lib/profile.py` | `load_profile(path)` / `resolve(profile, capability)` — reads client capability config |
| `${CLAUDE_PLUGIN_ROOT}/lib/capability_detect.py` | `detect(profile, probes)` — live-probes which upgrades are actually available |
| `${CLAUDE_PLUGIN_ROOT}/lib/sources.py` | `search(query, chain)` — data sourcing with ordered fallback chain |
| `${CLAUDE_PLUGIN_ROOT}/agents/lm-research.md` | Subagent that handles heavy multi-source harvesting |
