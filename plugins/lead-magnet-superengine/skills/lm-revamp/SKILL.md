---
name: lm-revamp
description: |
  Revamp an existing lead magnet. Trigger phrases: "revamp my lead magnet",
  "improve my opt-in", "/lm-revamp". Takes an existing PDF/docx/URL and
  runs it through diagnose → reshape → rebuild → deliver.
---

# /lm-revamp — Lead Magnet Revamp Skill

**Plain-English summary:** You hand Claude an existing lead magnet (the PDF or URL you already use to attract leads). Claude pulls it apart, grades it against a proven checklist, shows you what's broken and why, then (with your approval) rebuilds it into a sharper version with a "what changed & why" explanation.

---

## Trigger Phrases

- "revamp my lead magnet"
- "improve my opt-in"
- "/lm-revamp"
- "can you improve my freebie?"
- "diagnose my lead magnet"

---

## Prerequisites — What You Need Before Starting

1. The existing magnet: a PDF file path, a docx file, or a URL pointing to it.
2. (Optional) Your client profile at `${CLAUDE_PLUGIN_DATA}/profiles/<name>.json` (created by `/lm-setup`). If you don't have one, the skill will ask a few questions instead — upgrades are never required.

---

## Workflow — Five Steps

### Step 1: Ingest the Existing Magnet

**What happens:** Claude reads the file and extracts the raw material it needs for the rebuild — brand colors and embedded photos — so the new version looks like *yours*, not a generic template.

**How:**
```python
from lib import extract_assets, profile as profile_lib

# Pull brand colors + embedded images from the existing PDF
result = extract_assets.extract(pdf_path)
# result = {"colors": [...hex strings...], "images": [...file paths...]}

brand_color = result["colors"][0] if result["colors"] else "#3D2623"
hero_image  = result["images"][0] if result["images"] else ""
```

- If the input is a URL pointing directly to a PDF (URL ends in `.pdf` or server returns `Content-Type: application/pdf`): download the file to `output/_tmp/<filename>.pdf` — use the profile's `scrape` upgrade if connected, else Playwright render, else WebFetch as the floor — then run `extract_assets.extract` on that downloaded file exactly as you would for a local PDF.
- If the input is a URL pointing to a web page (not a PDF): fetch the rendered page for copy analysis — profile `scrape` upgrade if live → else Playwright render → else WebFetch floor. Brand colors and photos come from the page render (not `extract_assets`, which is PDF-only); set `brand_color` from the most prominent hex found in computed styles and `hero_image` from the largest above-the-fold `<img>` src, or fall back to defaults if neither is found.
- If the input is a docx, convert to PDF first (ask the user if tooling isn't available).
- Load the client profile: `p = profile_lib.load_profile(os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], "profiles", "<name>.json"))`. If no profile exists, skip — the skill degrades gracefully to questions.

**Output of this step:** brand colors, hero image path, raw copy (text extracted from the existing magnet).

---

### Step 2: Diagnose Against the Rubric

**What happens:** Claude scores the existing magnet on all criteria from `${CLAUDE_PLUGIN_ROOT}/core/rubric.md` (see that file for current counts — 4 Hormozi criteria (A), 6 coach-corpus criteria (B), and 5 anti-pattern checks (C) as of authoring, but rubric.md is the source of truth). Every criterion gets a PASS, FLAG, or FAIL with a one-line fix note.

**How (for Claude):**
- Read the extracted copy from Step 1.
- Score each criterion using the tables in `${CLAUDE_PLUGIN_ROOT}/core/rubric.md`.
- Fill in the scoring summary template (copy block at the bottom of the rubric).

**Anti-pattern scan (Section C — diagnose mode):**
Actively check for these five failure modes:
- **C1 Clinical/Dry** — cold, academic, or corporate tone?
- **C2 Catalog/Feature-Led** — a table of topics instead of a path to a result?
- **C3 Too Broad** — trying to help everyone with everything?
- **C4 Withholds the Win** — promises a result but delivers only awareness?
- **C5 Weak CTA** — no next step, or a vague "reach out!"?

**Output of this step:** A filled rubric scorecard, formatted exactly as the template in `${CLAUDE_PLUGIN_ROOT}/core/rubric.md`, showing PASS/FLAG/FAIL per criterion and a one-line fix for every FLAG and FAIL.

---

### Step 3: Present the Reshape Plan → PAUSE FOR APPROVAL

**What happens:** Claude presents a concise reshape plan — what's being kept, what's being cut, what's being rewritten, and the strategic rationale for each change. Then it **stops and waits**.

**Format for the reshape plan:**

```
## Reshape Plan — [Magnet Title]

**Verdict:** [READY / REVAMP NEEDED / REBUILD]
**Rubric score:** X PASS · Y FLAG · Z FAIL

### What stays
- [list items worth keeping]

### What changes
| Section / Element | Current state | Proposed change | Why |
|---|---|---|---|
| Headline | ... | ... | A1: audience not named |
| CTA | ... | ... | A4 + C5: buried + generic |
| ... | | | |

### Strategic bets
- Magnet type: [consumable / tool / lead-qualifying bridge]
- New hook: [proposed name — format: Result + For Whom + Speed/Ease]
- The win (one thing): [what the reader will have/know/do]

**Ready to rebuild? (yes / adjust the plan / cancel)**
```

> **APPROVAL GATE — do not proceed past this point without explicit user confirmation.**
> Ask: "Does this reshape plan look right? Say yes to rebuild, or tell me what to adjust."

---

### Step 4: Rebuild via Build Core

**Triggered only after user approves the reshape plan.**

Hand off to `${CLAUDE_PLUGIN_ROOT}/core/build-core.md` for the full five-stage pipeline. Supply these seed values:

| Seed value | Source |
|---|---|
| `brand_color` | Extracted in Step 1 |
| `hero_image` | Extracted in Step 1 |
| `sections` | Rebuilt copy from the reshape plan |
| `title` | New hook from the reshape plan |
| Rubric score | From Step 2 (pre-seeded into Stage 4) |

Build core handles: Blueprint → Draft → Design (render PDF via `lib.render_pdf.html_to_pdf`) → Score (rubric self-check) → Output (PDF + JSON sidecar).

QC check: `lib.qc_pdf.check(pdf_path)` — if `ok` is False, fix and re-render before delivering.

---

### Step 5: Deliver — New PDF + Changelog

Two artifacts delivered to the user:

**1. The rebuilt PDF**
Path: `output/<Client> - <New Title> - <MM.DD.YY>.pdf`

**2. "What Changed & Why" doc**
Plain-English explanation of every strategic decision made. Format:

```
## What Changed & Why — [Magnet Title]

**Magnet type:** [type]
**New hook:** [name]
**The win:** [one concrete thing]

### Changes made
| What | Before | After | Why it matters |
|---|---|---|---|
| Headline | ... | ... | A1 fix: names audience + problem |
| Opening | ... | ... | C1 fix: warm + specific |
| CTA | ... | ... | A4 + C5 fix: single, action-led |
| ... | | | |

### Rubric score: before → after
- Before: X PASS · Y FLAG · Z FAIL — [READY / REVAMP NEEDED / REBUILD]
- After: X PASS · Y FLAG · Z FAIL — [READY]

### Flags to watch
[Any remaining FLAG criteria and what to improve next iteration]
```

---

## Source Chains (Upgrades — Never Required)

If the user's profile has upgrades enabled, this skill can pull richer data:

| Need | Chain (walks left to right, stops at first hit) |
|---|---|
| Competitor context for rewrite framing | SearXNG (endpoint from profile `search` block) → Tavily → WebSearch floor |
| Competitor page copy | Firecrawl → Playwright scrape → WebFetch floor |
| Framework recall | Bundled references (always available, no upgrade): `${CLAUDE_PLUGIN_ROOT}/references/lead-magnet-frameworks.md` + `${CLAUDE_PLUGIN_ROOT}/references/lead-magnet-mistakes.md` |

If no profile or all sources fail: ask the user a plain question instead. See `${CLAUDE_PLUGIN_ROOT}/core/source-chains.md` for chain implementation.

Load upgrades: `profile_lib.resolve(profile, capability)` returns the upgrade block or `None` if disabled. Check before calling any upgrade tool.

---

## Degraded Mode (No Profile / No Upgrades)

The skill works without any profile or live sources. In degraded mode:
- Brand colors: extracted from the PDF (Step 1) or user picks one
- Images: extracted from the PDF (Step 1) or user provides a path
- Competitor context: skipped; Claude uses only the content of the existing magnet
- Framework recall: still available — bundled references ship with the plugin

Degraded mode still produces a full rubric scorecard and a rebuilt PDF.

---

## Error Handling

| Error | What to do |
|---|---|
| `extract_assets.extract` returns empty colors | Fall back to `#3D2623` for brand color; note it in the changelog |
| `extract_assets.extract` returns empty images | Set `hero_image = ""`; template renders without a cover photo |
| `qc_pdf.check` returns `ok: False` | Fix the flagged warnings and re-render; never deliver a failed QC |
| Profile not found | Log a note; proceed in degraded mode |
| User says "cancel" at approval gate | Stop cleanly; save the rubric scorecard to `output/reports/` for reference |

---

## Cross-Reference Index

| Path | Role |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/lib/extract_assets.py` | `extract(pdf_path)` — brand color + image extraction from existing PDF |
| `${CLAUDE_PLUGIN_ROOT}/lib/render_pdf.py` | `html_to_pdf(html, out_path)` — renders the rebuilt PDF |
| `${CLAUDE_PLUGIN_ROOT}/lib/qc_pdf.py` | `check(pdf_path)` — validates page count and catches render warnings |
| `${CLAUDE_PLUGIN_ROOT}/lib/profile.py` | `load_profile(path)` / `resolve(profile, capability)` — client capability config |
| `${CLAUDE_PLUGIN_ROOT}/core/rubric.md` | 15-criterion scoring rubric — all sections run in diagnose mode |
| `${CLAUDE_PLUGIN_ROOT}/core/build-core.md` | Five-stage Blueprint→Draft→Design→Score→Output pipeline |
| `${CLAUDE_PLUGIN_ROOT}/core/source-chains.md` | Ordered fallback chains for competitor data + framework recall |
| `${CLAUDE_PLUGIN_ROOT}/templates/field-guide.html.j2` | Jinja2 template; vars: `title`, `brand_color`, `hero_image`, `sections` |
