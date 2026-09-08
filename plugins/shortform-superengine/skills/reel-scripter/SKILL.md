---
name: reel-scripter
description: >
  Analysis-driven Instagram reel scripting. Trigger phrases:
  "write a reel script", "write a reel script from my analysis",
  "script a reel from my analysis", "turn my competitor analysis into a reel",
  "draft an IG reel in my voice", "script the next reel for <client>",
  "give me a reel hook + body + CTA", "script the next angle",
  "script that reel", "script the top gap", "script the top seed",
  "script the top idea", "script the top question",
  "script idea N from my content plan".
  Consumes a completed competitor-cross-reference run (analysis-data.json)
  plus the client's voice profile, and produces an in-voice reel script
  grounded in the niche's *proven* moves: hook, secondary hook, body beats,
  proof, CTA, plus a caption and a flow-check.
  Shortform format engine #1 of the Content Superengine.
---

## Teach mode

One family-shared dial: `~/.claude/revxl/teach-level` (`new` / `learning` / `pro`, default
`new`), legacy `teach-mode` mapped on read. Copy the read snippet verbatim from
`../_shared/references/teach-mode.md`, re-read it at every start, mirror it to
`state.teach_level`.

## Terminal paths

Every ending routes. Edge ids: `../_shared/references/journey-map.md`. Block grammar:
`../_shared/references/routing.md`.

**Next moves ... script written (E6)**
1. *If `angles_unpicked[]` is not empty:* the next Step 1 angle, already vetted. Say: "script the next angle"
2. *If it is empty:* build the week's plan so the next reel has a source. Say: "content plan"
3. Refresh the pack so the client sees the field this attacks. Say: "regenerate my visuals"
4. *If `pulse.scheduled` is false:* next week's winners land here. Say: "run the weekly pulse"

**Next moves ... no analysis at Step 0a (E9, general form F2)**
1. Field analysis first: no `analysis-data.json`, nothing to script off. Say: "analyze my Instagram against my competitors"
2. *If the marker is missing:* set up first, the analysis needs the key. Say: "set up shortform superengine"
3. Lost in the order? Say: "what's next in shortform"

**Next moves ... no voice guide on disk (gate VOICE, F7)**
1. Continue on the Step 0c interim anchor; the script is labelled "voice: interim".
2. Build the voice guide once; every later script inherits it. Say: "build my brand brain"
3. *If one exists and is over 7 days old (F7):* refresh it, offered once. Say: "refresh my voice guide"

**Next moves ... Vault degraded: no key, or workspace-superengine missing, or the callee errored (F3)**
1. Finish the reel on the bundled `./references/`, printing `Vault: 0 searches, 0 reads | skipped: <reason>`. The Vault never blocks a script.
2. Retry at the next reel, never twice inside one named step; or install workspace-superengine for the live pulls, then script again. Say: "write a reel script"
3. Check what else is stale before spending. Say: "what's next in shortform"

**Next moves ... voice not confirmed at Checkpoint 0 (E0b)**
1. Capture the voice properly first, once. Say: "build my brand brain"
2. Redo the interim anchor the other way (top captions, or the Q&A), then re-show Checkpoint 0.
3. Park the reel and pick it up later. Say: "what's next in shortform"

**Next moves ... an idea picked from the content plan (E7)**
1. Script it: idea N is the angle, the run starts at Checkpoint 0. Say: "script idea N from my content plan"
2. *If no `content-plan-<week>.md` is on disk (E0):* build the plan first. Say: "content plan"
3. Prefer a field angle? Step 1 proposes 2 to 3 off the analysis. Say: "write a reel script"

**Next moves ... subject-first requested (F8)**
1. subject-matter ships in 0.5.0; until then field-first. Every claim here traces to `analysis-data.json`, and the brief that satisfies that guardrail is what 0.5.0 adds. Say: "use my own material" (if installed)
2. Bring the topic inside field-first: Step 1's vet adapts the framing, never vetoes it. Say: "write a reel script"
3. No analysis yet? That is the real blocker. Say: "analyze my Instagram against my competitors"

## Prereq (E0)

- **Analysis, required.** `<project>/analysis-data.json` from a finished
  `competitor-cross-reference` run, plus `analysis.date` in state. Without it this skill
  refuses and routes (E9 above); it never improvises a field read.
- **Brand slug, required.** `active_brand` from
  `~/.claude/shortform-superengine/.superengine` (legacy `brand`, same value): it picks the
  state file and the voice directory.
- **Voice, optional.** `~/.claude/revxl/<brand>/voc/`. Absent, Step 0c captures an interim
  anchor and says so on the script. A reel is never gated on it.

## State

Contract: `../_shared/references/state-schema.md`. **Read at start** from
`~/.claude/shortform-superengine/state/<brand>.json`: `active_brand` (marker), `analysis`,
`voc.present` (derived from the `voc/` directory, never a stored field), `scripts[]`,
`angles_unpicked[]`, `plan`. **Written here and nowhere else:** `scripts[]`,
`angles_unpicked[]`, `completed_skills`, `open_loops`, `declined_offers`, `updated_at`.
`plan` belongs to `content-plan`, read-only here. No invented keys.

## Overview

`reel-scripter` is the **Shortform** format engine. It does not guess what to post —
it reads what already wins in the client's niche (from a `competitor-cross-reference`
run) and writes a single reel in the client's own voice off that evidence.

Its three input layers (the analysis, the brief, the voice):
`./references/pipeline-detail.md` "Inputs".

A **guided, checkpointed** pipeline: pause at each ✋ before spending the next move. One run
= one reel at `<project>/scripts/<slug>.md`.

> **Definition of done:** a reel the client could film today, in their voice, on a structure
> the niche has proven. In full: `./references/pipeline-detail.md`.

---

## Guided Pipeline

### Step 0 — Resolve inputs + voice

**0a. Locate the analysis.** Confirm `<project>/analysis-data.json` exists (a completed
`competitor-cross-reference` run). If only the older `analysis-data.md` exists, re-run
`analyze.py` to emit the JSON. If there is no analysis at all, stop and route the user to
`competitor-cross-reference` first — this skill is analysis-driven by design.

No analysis on disk is a terminal path, not an error: render E9 above and stop.

**0b. Run the brief.**

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/reel-scripter/scripting_brief.py <project_dir>
```

This writes `<project_dir>/scripting-brief.md`. Read it: your menu of proven moves, and its
**§8 Avoid list is this niche's own losers**, which screens every option later. Its two
modes: `./references/pipeline-detail.md` "Step 0b".

**0c. Resolve the voice.** Priority: shared `voc/` at `~/.claude/revxl/<brand>/voc/` FIRST
(a brain built by any engine lives there), then the project, then the workspace. With no
`voc/`, **interim capture (degrade)**: 3 to 5 of the client's own top captions, or the
4-question voice Q&A, noted on the script as interim. Full read rules (`days_since_update`
and the single refresh offer, `provisional: true`, the Mirror-Language ban):
`./references/pipeline-detail.md` "Step 0c". No `voc/` renders **no voice guide on disk**.
A `voc/` over 7 days old gets ONE refresh offer (F7); proceeding without it records
`voc_refresh:<voc.refreshed_at>` in `declined_offers` (entry shape:
`../_shared/references/state-schema.md`), which stops the compass re-offering it.

**0d. Vault pull #1, the angle and its doctrine (named trigger point 1 of 2).**
Check `<project>/brain-pulls/<slug>.md` first: a cached pull younger than **14 days** is
reused, no call. Otherwise invoke the callee ONCE, MAKE-topic recipe from
`../_shared/references/vault-api.md`:

```
Skill: workspace-superengine:revxl-vault-search
args:  depth=med plugin=shortform-superengine spoke=content-strategy
       question: <the reel's topic>
       angles: content_ideation; transpositioning; evergreen_content
```

`depth=med` is **1 search and up to 2 reads for this step**, the whole budget. Never loop.
Read the echoed `spoke` back; if it is not `content-strategy`, say so and treat the hits as
unscoped. Save them to `<project>/brain-pulls/<slug>.md`, weave them into the brief's menu,
cite `[vault] <path>`. The callee owns the key: this skill never reads or prints one. Errors
degrade per `vault-api.md` and the run continues (**Vault degraded**); the skill not
resolving is **workspace-superengine missing**.

### ✋ Checkpoint 0 — Confirm the voice anchor + brief read
Show: the mode (FULL or caption-only), the top 2 to 3 attack themes, the voice source (full
`voc/` vs interim), and **one Vault status line, mandatory on every brief** even at zero
calls: `Vault: <n> searches, <m> reads | <ok|degraded|skipped: reason>`. A cache hit or a
missing callee is never a reason to drop it. Where Vault doctrine and the brief's local
stats disagree, the brief says so in one sentence and ranks the doctrine first.
(SKLLPLG-268) **Pause** until the user confirms the voice and picks a direction. Never
script in a voice you have not confirmed; a decline renders **voice not confirmed at
Checkpoint 0** above.

---

### Step 1 — Pick the move

**Dedupe before proposing.** Read `state.scripts[]` AND `<project>/scripts/*.md`; every
approved reel there carries an `Angle: <theme> × <hook type>` line (Step 5 writes it). State
is the fast path, the files are the truth when they disagree. Exclude used `(theme, hook)`
pairs unless nothing else remains; a deliberate repeat says so: "you scripted this pairing
on <date of that file>". (SKLLPLG-201)

From `scripting-brief.md`, propose **2 to 3 concrete reel angles**, each = {attack theme ×
winning hook type × the gap it closes}, evidence cited (`@handle · metric · reel URL`).
Example shape: `./references/pipeline-detail.md` "Step 1 propose".

**Custom-idea field vet (mandatory when the user brings their OWN topic).** A brief-derived
angle is field-backed; a user-supplied idea is not. Vet it before committing beats:

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/reel-scripter/field_vet.py <project_dir> <keyword> [keyword2 ...]
```

Pass the obvious frame word AND its adjacent candidates so a losing frame surfaces its
winning neighbor. **The idea is never vetoed, only the framing adapts.** The report and the
four verdict branches (WINNER / NEUTRAL, LOSER, UNTESTED / THIN / NONE, thin-n):
`./references/pipeline-detail.md` "Step 1 field vet".

**Deeper field layer (optional, detect-first).** With socialcrawl-superengine installed
(the two-step probe is in `../_shared/references/socialcrawl-endpoints.md`),
`research-plays` widens the angle set. Absent, do not fake it: render the F9 refusal block described in
`../_shared/references/journey-map.md` (edge F9) and continue on the analysis.

**Persist the angles not taken.** On the Checkpoint 1 pick, write every other proposed angle
to `state.angles_unpicked[]` as `{angle, from, opened}`, so "script the next angle" survives
a session boundary. Step 5 removes the one scripted.

### ✋ Checkpoint 1 — Pick one angle
**Pause.** The user picks one angle (or redirects). Everything downstream serves that one move.

---

### Step 2 — Structure → beats

For the chosen hook type, pull the body skeleton from `./references/body-structures.md` and
the post-hook structure and loop plan from `./references/retention-psychology.md`. Lay out
this reel's beat list, `Hook, Secondary hook, Body beat 1..n, Proof, CTA`, inside the
brief's length target. Most winning reels are short; respect it.

**Optimize the skeleton BEFORE showing it (mandatory).** A raw beat list is a draft: screen
it, then present the TIGHTENED version with a one-line why per change. Never hand over an
un-optimized skeleton. The four screens (one idea not a list, length budget, one loop paid
late, single lever): `./references/pipeline-detail.md` "Step 2". The user owns Checkpoint 2
and can override any trim.

### ✋ Checkpoint 2 — Approve the skeleton (then it FREEZES)
Show the empty beat list (labels only, no copy yet). **Pause** for the user to add/cut/reorder
beats before any line is written. On approval the skeleton **locks**: everything downstream
fills it — only the user can change it after this point, voice never can.

---

### Step 3 — Fill in voice: scored options, the user assembles

The skeleton is frozen. Voice works **inside** it: reword a beat, never add, cut, reorder,
re-purpose or soften one. Substance comes from the analysis and the client's own input;
`voc/` sets tone and vocabulary only. On a client-supplied angle the beat-by-beat interview
is **mandatory before any option is generated**, and an unanswered beat is flagged, never
filled with invented teaching.

Work **section by section, in order** (Hook, Secondary hook(s), Body beats, Proof, CTA,
Text-overlay storyboard, Caption hook), running **generate ... screen ... score ... gate ...
pick** per section. Option counts, hook laws, secondary-hook placement and dosage,
storyboard rules, screening tables, the 1 to 10 scoring dimensions and the score-7 gate:
`./references/step3-options.md`. Run them from there; they are not restated here.

**Vault pull #2, the hook (named trigger point 2 of 2).** Only when the hook layer is thin
or stale, and only after Step 2 locked the bucket. Check `<project>/brain-pulls/` first
(same 14-day TTL), then invoke the callee ONCE, MAKE-hook recipe from `vault-api.md`:

```
Skill: workspace-superengine:revxl-vault-search
args:  depth=med plugin=shortform-superengine spoke=content-strategy
       question: what makes the first three seconds work for <the locked angle>
       angles: hook_first_3_seconds; hook_alignment; hook_negative_framing
```

Same budget, cache, degrade and evidence line. **Two named steps per reel, 0d and this
one.** That is the entire Vault spend for a reel.

On the picked hook, run the **three-hook alignment check** (`hook-mastery.md`): visual, spoken,
and text hook must mean the same thing — fix before moving on.

Then dial the **edge** to the voice guide, run the draft through the **8 Swaps** pass in
`./references/story-locks.md`, and fix weak lines with `./references/say-this-not-that.md`.
That pass tightens lines, never restructures. Then write the **caption** (picked caption
hook, context, the same single CTA).

---

### Step 4 — Flow-check + craft score

**4a. Hook lens, the 4 Hook Killers.** Run the hook through
`../_shared/references/hook-diagnostics.md`, fix any that fire, then re-scan the whole
assembled wording against the brief's §8 Avoid list and the losing tables (detail:
`./references/pipeline-detail.md` "Step 4a").

**4b. Loop integrity (mandatory, before the flow read).** Walk the beat **seams** and label,
at each seam, which loop is still OPEN. The three fail conditions (dead seam, early close,
flat run) and their fixes: `./references/pipeline-detail.md` "Step 4b".

Rule: from the hook to the CTA there is never a moment with zero open loops. The spanning loop
(opened at hook or secondary) resolves in the final beat, not before. Flag every seam you fixed.

**4c. Flow-check + skeleton integrity.** Read it top to bottom as a viewer, tighten any dead
beat, then confirm the draft matches the Checkpoint-2 skeleton **beat-for-beat**. A change
the **user** asks for is always allowed: the lock binds voice, not the user.

**4d. Craft score.** **Hook / Body / CTA / overall (0 to 100)** on the Story Locks rubric
(`./references/story-locks.md`). Craft only, **never** a performance prediction, and it
never claims views. State the one highest-leverage fix. Both sub-steps in full:
`./references/pipeline-detail.md` "Step 4c and 4d".

### ✋ Checkpoint 4 — Review the scored draft
Show the full draft + the four scores + the top fix + which Hook Killers were caught. **Pause**
for the user's edits or approval.

---

### Step 5 — Write the script file (one reel per run)

Write the approved reel to `<project>/scripts/<slug>.md` (slug = short kebab of the angle).
The section template (the `Voice` / `Mode` / `Angle` header line, On-screen hook, Script,
Text overlays, Caption, Craft score, Evidence) is in `./references/pipeline-detail.md`
"Step 5 template". Write every section; the `Angle:` line is what Step 1's dedupe reads.
Report the path. One run = one script.

**Write state, then the evidence line.** Append `{slug, angle, source, date}` to
`state.scripts[]`, drop the scripted angle from `state.angles_unpicked[]`, append
`reel-scripter` to `completed_skills`, refresh `updated_at`. Print the Vault line again,
exactly as at Checkpoint 0, then render **script written (E6)** above.

---

## Content plan

The weekly idea pool is `content-plan`'s, not this skill's
(`./references/pipeline-detail.md` "Content plan"). Coming back with an idea, the entry is "script idea N from my content plan": read
`<project>/content-plan-<newest week>.md`, take idea N (with its source tag and angle) as
the chosen angle, then run from Checkpoint 0 for voice and on to Step 2. Step 1's proposal
is skipped; the guardrails are not. No plan on disk is a missing prereq (E0).

---

## Guardrails

- **Structure locks, voice is skin.** Proven data + the reference doctrine decide the beats,
  moves, and loops; voice only decides how a locked beat *sounds*. Voice never restructures.
- **Analysis-driven, not vibes.** Every angle cites the analysis (`@handle · metric · URL`). If a
  claim about "what wins" isn't traceable to `analysis-data.json` / `scripting-brief.md`, cut it.
- **Voice before copy.** Never write final lines until the voice anchor is confirmed (Checkpoint 0).
  When degraded to interim voice, say so on the script.
- **Their substance, never invented.** On a client-supplied topic, teaching-beat content comes
  from the beat-by-beat interview (Step 3) — a beat with no client answer gets flagged, not filled.
- **Craft, not promises.** The score is craft quality. Never predict views, reach, or virality —
  the engine measures what already happened, it does not forecast (consistent with the no-score
  discipline elsewhere in the product).
- **Respect the length target.** The brief's length target reflects what the niche's winners do.
  Don't pad.
- **Honest degrade.** Caption-only mode (no transcripts) can't see spoken structure — say so;
  don't invent structural claims the data can't support.
- **Never pay for transcripts.** Harvest spoken transcripts with the local chain
  (Groq + local Whisper in parallel, subtitle track as fallback — the chain `onboarding`
  installs), **never** SocialCrawl `media/transcript` — it's a 10-credit premium call
  with no advantage.
- **Windows / Python:** `open(encoding='utf-8')`; never print non-ASCII to the cp1252 console
  (write to file). The brief script already follows this.

---

## References

Every reference is linked from the step that uses it. Entry points:
`./references/step3-options.md` (Step 3) · `./references/pipeline-detail.md` (every
other step) · `./scripting_brief.py` · `./field_vet.py` ·
`../_shared/references/journey-map.md` · `../_shared/contracts/analysis-data.schema.json`

---

## Non-Goals

One script per run. Everything this skill deliberately does not do, in full:
`./references/pipeline-detail.md` "Non-Goals".