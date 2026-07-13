---
name: lm-inspired-by
description: >
  Intake adapter for generating an ORIGINAL lead magnet inspired by someone else's
  material — a competitor guide, YouTube video, blog post, or any external source.
  Extracts the magnet's structural DNA, abstracts the pattern (never the prose),
  maps it to the user's niche, and generates a fully original magnet in their voice.
  Enforces the ORIGINALITY GUARDRAIL: no copy is ever reproduced verbatim.
triggers:
  - "make one like this"
  - "inspired by this competitor"
  - "/lm-inspired-by"
---

# /lm-inspired-by — Inspired-By Intake Skill

## Purpose

You have a competitor's lead magnet, video, guide, or post. You want to make something
just as good (or better) for your own audience — without copying it.

This skill ingests the source, extracts *what makes it work*, abstracts that into a
reusable pattern, and builds an **original** magnet in your voice.

**Origin: someone else's material. Output: entirely yours.**

---

## ORIGINALITY GUARDRAIL — Non-Negotiable

> **Never reproduce copy verbatim. Inspired-by, never copied.**

This constraint applies at every stage. Violations block output.

- During DNA extraction: note patterns and structure — never quote full sentences
  except as one-line labeled specimens (marked `[SPECIMEN — do not reuse]`).
- During generation: write in the user's voice from the abstracted pattern.
- Before output: run the **Verbatim-Overlap Self-Check** (Step 6 below).
  If overlap is too high, the output is blocked and revised until it passes.

---

## Workflow

### Step 0 — Intake Triage

Collect from the user:

1. **What you're sharing** — one or more of:
   - YouTube / video URL(s)
   - A PDF, guide, or file (attach or paste path)
   - A competitor landing page / blog URL
   - A description ("I saw a checklist that did X")
2. **Your niche and offer** — who you serve and what you sell (can be answered via Q&A below)
3. **Heavy harvest flag** — if the user provides more than 2 sources OR a multi-video playlist,
   dispatch to `lm-research` subagent rather than handling inline.

**Data-optional path:** if the user has no source to share (only a description or memory),
skip Step 1 and go to Step 2 with whatever they can describe. The magnet can still be built.

---

### Step 1 — Ingest External Sources

Walk the appropriate chain for each source type. Dispatch heavy/multi-source work to the
`lm-research` subagent (`${CLAUDE_PLUGIN_ROOT}/agents/lm-research.md`) using job type `magnet_dna`.

#### Source routing table

| Source type | Chain (left = primary) | lm-research job type |
|---|---|---|
| YouTube / video URL | yt-dlp → ffmpeg → Whisper server (profile `transcribe` endpoint) → Groq (if `GROQ_API_KEY`) → `video-use` skill | `video_teardown` |
| PDF / competitor guide (file) | `lib.extract_assets.extract(pdf_path)` → paste fallback | `magnet_dna` (page_extract chain) |
| Landing page / blog / URL | Firecrawl (if `scrape` cap) → Playwright → WebFetch floor | `magnet_dna` (page_extract chain) |
| Plain description / memory | Skip ingest — go to Step 2 with user-supplied details | N/A |
| Multiple sources (>2) or playlist | **Always dispatch to `lm-research` subagent** | `magnet_dna` |

#### Capability detection (before chaining)

Load the client profile and detect live capabilities before walking any chain:

```python
# Conceptual — pseudocode; actual signature shown below
import os
profile = lib.profile.load_profile(
    os.path.join(os.environ["CLAUDE_PLUGIN_DATA"], "profiles", "client.json")
)
caps = lib.capability_detect.detect(
    profile,
    probes={                          # probes is a dict, not a list
        "scrape":     lambda: firecrawl_health_check(),
        "transcribe": lambda: whisper_health_check(),
        "search":     lambda: searxng_health_check(),
    }
)
# caps -> {"scrape": True/False, "transcribe": True/False, ...}
```

Skip any chain slot whose corresponding capability is `False`.

#### Dispatch to lm-research

When dispatching, pass the `magnet_dna` job type:

```json
{
  "jobs": [
    {
      "type": "magnet_dna",
      "targets": ["<url-or-video-link>", "..."],
      "caps": { "search": true, "scrape": true, "transcribe": true, "social": false, "ranked": false }
    }
  ],
  "niche": "<client niche>",
  "profile_path": "${CLAUDE_PLUGIN_DATA}/profiles/client.json"
}
```

The subagent returns a digest containing a `magnet_dna` array. Use that array as input to Step 2.

#### QA fallback

If all chain members fail, `lib.sources.search()` returns `{"source": "qa", "results": []}`.
Surface this question to the user:

> "I wasn't able to pull the source automatically. Can you paste the key copy,
> describe the structure, or tell me the main points it covered?"

Continue with whatever they provide.

---

### Step 2 — Extract Magnet DNA

From the ingested material (or user description), extract and record the **structural DNA**.
This is analysis, not transcription. Never quote full paragraphs.

Fill all five fields per source. If a field can't be determined, mark it `null` and note why.

| Field | What to capture |
|---|---|
| `structure` | How it's organized — numbered steps, quiz flow, 3-video series, swipe file, chapter breakdown, etc. |
| `hooks` | The opening line(s) and secondary attention-grabbers. **Capture the pattern ("opens with a fear statement"), not the exact words.** You may include one quoted specimen per hook, labeled `[SPECIMEN — do not reuse]`. |
| `problem_solved` | The specific pain, fear, or desire addressed — one sentence. |
| `the_win` | The concrete promised outcome or transformation ("reader will be able to X by Y"). |
| `format` | Delivery mechanism: PDF, video series, email course, checklist, quiz, webinar, etc. |

---

### Step 3 — Score What's Working

Rate each DNA element on a simple 1–3 scale before abstracting:

| Score | Meaning |
|---|---|
| 3 — Steal the pattern | This is doing heavy lifting. Replicate the underlying mechanic. |
| 2 — Adapt | The idea is sound but the execution is average. Improve it. |
| 1 — Skip | Weak or irrelevant to the user's niche. Discard. |

Document your scores and reasoning in 1–2 lines per element. This becomes the "what/why" doc in output.

---

### Step 4 — Abstract the Pattern

**This is the core step. Abstract the pattern, not the prose.**

Translate each DNA element into a format-agnostic, niche-agnostic mechanic. The abstraction
should be true for any audience — the competitor's specific words and niche must not appear.

Example:
- Source hook: *"Most real estate agents lose 40% of their leads in the first 24 hours."*
- Pattern: *Opens with a specific percentage loss tied to a time window — makes the cost of inaction concrete and immediate.*
- Use: *Apply this mechanic with a percentage and time window relevant to the user's niche.*

Write one abstraction per scored element (skip any scored 1). Record as:
`[mechanic name]: [one-sentence description of the pattern] → [how to apply in a new niche]`

---

### Step 5 — Map to User's Niche

If the user's niche and offer are not yet clear, ask:

1. **Who do you serve?** (Target audience — be specific: "female founders building their first team" beats "entrepreneurs")
2. **What do you sell?** (The next step after the magnet — program, service, product)
3. **What's the #1 result your clients get from working with you?**
4. **What keeps your audience up at night?** (The pain the magnet should address)

Map each abstracted mechanic to the user's niche:
- Restate `problem_solved` in the user's audience's language
- Restate `the_win` as a concrete outcome the user can actually deliver
- Choose the format that fits the audience's time-to-value expectation

Load `${CLAUDE_PLUGIN_ROOT}/references/lead-magnet-frameworks.md` (type/step framework) and
`${CLAUDE_PLUGIN_ROOT}/references/hooks-and-titles.md` (naming method) — bundled, always available.

Then lock in the blueprint inputs for `${CLAUDE_PLUGIN_ROOT}/core/build-core.md` Stage 1:
- **Type** (Hormozi: consumable / tool / lead-qualifying bridge)
- **Format** (PDF guide, checklist, quiz, video, etc.)
- **Hook / name** — run Hormozi step 4: draft 3 name options, pick the sharpest
- **The win** — one concrete thing the reader will have, know, or be able to do

---

### Step 6 — Generate Original Magnet → Verbatim-Overlap Self-Check → Output

Hand the blueprint inputs to `${CLAUDE_PLUGIN_ROOT}/core/build-core.md` (Stages 2–5) to draft, design, score, and output.

Before output is delivered, run the **Verbatim-Overlap Self-Check**:

#### Verbatim-Overlap Self-Check (MANDATORY — blocks output on failure)

1. **Collect source strings.** Pull all text extracted from the original source in Steps 1–2
   (hook specimens, structural quotes, any directly captured phrases).

2. **Scan generated copy.** For every sentence in the generated magnet, check whether it:
   - Matches any source string exactly (character-for-character), OR
   - Shares ≥ 7 consecutive words with any source string.

3. **Threshold:**
   - **0 exact matches and < 3 near-matches (≥7 consecutive words)** → PASS. Output proceeds.
   - **Any exact match OR ≥ 3 near-matches** → FAIL. Return to Stage 2 of `${CLAUDE_PLUGIN_ROOT}/core/build-core.md`.
     Revise the flagged sentences. Re-run the check. Do not deliver output until it passes.

4. **Log the result** in `magnet-meta.json` under key `originality_check`:
   ```json
   "originality_check": {
     "status": "PASS" | "FAIL",
     "exact_matches": 0,
     "near_matches": 0,
     "notes": "<any flagged phrases and how they were resolved>"
   }
   ```

---

## Output

Deliver the standard Stage 5 artifacts from `${CLAUDE_PLUGIN_ROOT}/core/build-core.md`:

| Artifact | Contents |
|---|---|
| **PDF** | The rendered original magnet |
| **"What/Why" doc** | Strategy decisions + scores from Step 3 explaining why each pattern was chosen or skipped |
| **JSON sidecar** (`magnet-meta.json`) | `type`, `hook`, `win`, `sources_used`, `rubric_score`, `rubric_flags`, `originality_check` (including self-check result), `source_dna` (the abstracted patterns used) |

---

## Cross-Reference Index

| Path | Role |
|---|---|
| `${CLAUDE_PLUGIN_ROOT}/core/build-core.md` | Stages 2–5: draft → design → score → output (this skill seeds Stage 1) |
| `${CLAUDE_PLUGIN_ROOT}/core/rubric.md` | 15-criterion self-check; run before output |
| `${CLAUDE_PLUGIN_ROOT}/core/source-chains.md` | Chain definitions and fallback questions per source type |
| `${CLAUDE_PLUGIN_ROOT}/agents/lm-research.md` | Subagent for heavy/multi-source harvesting; use `magnet_dna` job type |
| `${CLAUDE_PLUGIN_ROOT}/lib/extract_assets.py` | `extract(pdf_path)` — PDF brand colors and image extraction |
| `${CLAUDE_PLUGIN_ROOT}/lib/profile.py` | `load_profile(path)` / `resolve(profile, capability)` |
| `${CLAUDE_PLUGIN_ROOT}/lib/capability_detect.py` | `detect(profile, probes)` — probes is a **dict** `{capability: callable}` |
| `${CLAUDE_PLUGIN_ROOT}/lib/sources.py` | `search(query, chain)` — chain-walking with fallback |
| `${CLAUDE_PLUGIN_ROOT}/templates/field-guide.html.j2` | Jinja2 template used in Stage 3 |
