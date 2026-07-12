---
name: reel-scripter
description: >
  Analysis-driven Instagram reel scripting. Trigger phrases: "write a reel
  script", "script a reel from my analysis", "turn my competitor analysis into
  a reel", "draft an IG reel in my voice", "reel-scripter", "script the next
  reel for <client>", "give me a reel hook + body + CTA", "weekly topic pool",
  "idea bank", "20 ideas from the best performers". Consumes a completed
  competitor-cross-reference run (analysis-data.json) plus the client's voice
  profile, and produces an in-voice reel script grounded in the niche's *proven*
  moves — Hook → Secondary hook → Body beats → Proof → CTA, plus caption and a
  flow-check. Shortform format engine #1 of the Content Superengine.
---

## Teach mode

Read `~/.claude/revxl/teach-mode` if it exists, else default `beginner`. In
**beginner**: plain-English-first — explain in plain words, then name the
technical term with a one-line gloss on first use, and add a "what this means for
you" line where the consequence isn't obvious. In **off**: standard professional
voice, no glosses. Convention + adjust rules: `../_shared/references/teach-mode.md`
(`/teach-mode off`, or a plain request like "stop explaining the basics", →
rewrite that file and confirm).

## Overview

`reel-scripter` is the **Shortform** format engine. It does not guess what to post —
it reads what already wins in the client's niche (from a `competitor-cross-reference`
run) and writes a single reel in the client's own voice off that evidence.

Inputs it stands on:
- **The analysis** — `<project>/analysis-data.json` (the core→format interface produced by
  `competitor-cross-reference/analyze.py`). Ranked gaps, winning hook types, theme×hook,
  outliers, opener patterns. This is the *what to say* layer.
- **The brief** — `reel-scripter/scripting_brief.py` distils that JSON (+ transcripts when
  present) into `<project>/scripting-brief.md`: attack themes, winning hooks, opener
  patterns, winning structures, length targets. This is the *how it's working* layer.
- **The voice** — shared `voc/` artifacts (`voice-guide.md`, `voc-profile.md`,
  `business-config`) when available; **degrades** to a fast interim voice-anchor capture
  when they aren't. This is the *sound like the client* layer.

It is a **guided, checkpointed** pipeline — you pause for a human decision at each ✋ before
spending the next move. One run = one finished reel script written to `<project>/scripts/<slug>.md`.

> **Definition of done:** a reel script the client could film today — hook that earns the
> first 3 seconds, a body built on a structure the niche has proven, a CTA matched to the
> goal, a caption, and an honest craft-score + flow-check — all in the client's voice.

---

## Guided Pipeline

### Step 0 — Resolve inputs + voice

**0a. Locate the analysis.** Confirm `<project>/analysis-data.json` exists (a completed
`competitor-cross-reference` run). If only the older `analysis-data.md` exists, re-run
`analyze.py` to emit the JSON. If there is no analysis at all, stop and route the user to
`competitor-cross-reference` first — this skill is analysis-driven by design.

**0b. Run the brief.**

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/reel-scripter/scripting_brief.py <project_dir>
```

This writes `<project_dir>/scripting-brief.md`. Read it — it is your menu of proven moves.
It auto-detects **FULL** mode (spoken transcripts present) vs **CAPTION-ONLY** degrade
(no transcripts — structures inferred from captions, flagged in a banner).

**0c. Resolve the voice.** In priority order:
1. Shared `voc/` artifacts — `voice-guide.md` (rules/tone), `voc-profile.md` (verbatim
   audience pains, vocabulary, phrases to use/avoid), `business-config` (offer, ICP, CTAs).
   Check the shared brand brain FIRST — `~/.claude/revxl/<brand>/voc/` (brand slug from the
   onboarding marker/config; a brain built from ANY engine lives here) — then the project,
   then the workspace-level `voc/` if one is wired. On read: compute `days_since_update`
   from the stamp; >7 days → surface the age + offer a brand-brain refresh ONCE, never gate
   scripting on it. If the stamp says `provisional: true` (fewer than 3 sources mined),
   treat rankings and voice reads as hypotheses — confirm with the user instead of leaning
   bold. Never quote `voc-profile.md` "Mirror Language (hypothesis)" entries as audience
   VoC — that's the coach's own phrasing about herself, not her market's.
2. **Interim capture (degrade)** — if no `voc/`, capture a lightweight voice anchor now:
   either 3–5 of the client's own top captions/transcripts (already in the project) **or** a
   4-question voice Q&A (Who are you talking to? What do you say that they don't expect? What
   words do you never use? What's your one CTA?). Note in the final script that voice was
   interim, not the full profile.

**0d. Brain pull #1 — current frameworks for this topic (Trigger 1 of 2).**
Resolve the Brain key per [`../_shared/references/vault-api.md`](../_shared/references/vault-api.md)
(ladder: env → `~/.config/revxl/vault_api_key` → ask once). **Check
`<project>/brain-pulls/` first** — a cached pull for this topic means no call.
If a key resolves and no cache: ONE `/v1/search` — `query` = the reel's topic/theme,
`variants` = niche + format terms (e.g. `["<niche> reels", "<format> hook"]`). The format
isn't locked yet at this step, so read it off the INPUT when it shows one: list-shaped
source → `"listicle reel"`; client story/transformation → `"story reel"`; belief-flip →
`"myth bust reel"`; no clear shape → default `["<niche> reels", "<topic>"]` and let hybrid
search do the aiming — **never skip the pull because the content doesn't fit a mold.** Save
the cited hits to `<project>/brain-pulls/<topic-slug>.md` and weave them into the
brief's menu as extra evidence, cited `[brain] <path>`. No key / 4xx / 5xx / timeout →
follow the reference's degrade table and move on — the Brain never blocks a script.

### ✋ Checkpoint 0 — Confirm the voice anchor + brief read
Show: the mode (FULL/caption-only), the top 2–3 attack themes from the brief, and the voice
source (full `voc/` vs interim). **Pause** until the user confirms the voice sounds right and
picks a direction — do not script in a voice you haven't confirmed.

---

### Step 1 — Pick the move

From `scripting-brief.md`, propose **2–3 concrete reel angles**, each = {attack theme ×
winning hook type × the gap it closes}, with the evidence cited (`@handle · metric · reel URL`
from the analysis). Example shape: *"Myth-bust on [under-served high-value theme] — the field's
myth-bust hooks median Nx the client's; closes the [gap] gap."*

### ✋ Checkpoint 1 — Pick one angle
**Pause.** The user picks one angle (or redirects). Everything downstream serves that one move.

---

### Step 2 — Structure → beats

For the chosen hook type, pull the matching body skeleton from
`./references/body-structures.md` (organized by hook bucket: question / myth-bust / listicle /
story / pain-callout / contrarian / statement). Lay out the beat list for THIS reel:
`Hook → Secondary hook → Body beat 1..n → Proof → CTA`. Keep it to the length target the brief
gives (most winning reels are short — respect it).

### ✋ Checkpoint 2 — Approve the skeleton
Show the empty beat list (labels only, no copy yet). **Pause** for the user to add/cut/reorder
beats before any line is written.

---

### Step 3 — Fill in voice

Write each beat, in order, **in the client's voice**:
- **Hook** — front-load value using the **HOOK → PROMISE → MICRO-INTRO** opener structure +
  bucket templates in `./references/opener-patterns.md`; for a fast first draft, pull a proven
  shape from `./references/hook-formulas.md` (each maps to the hook bucket the analysis ranked).
  **Brain pull #2 (Trigger 2 of 2, optional):** if the Brain key resolves and the hook bucket
  feels stale or thin, ONE `/v1/search` — `query` = `hook <bucket> <topic>` with the bucket
  Step 2 locked (question / myth-bust / listicle / story / pain-callout / contrarian /
  statement — one always exists by now; hybrid angle → one variant per bucket in play) + up
  to 3 `/v1/note` reads on the top hits — current hook patterns beat frozen ones. Cache to `<project>/brain-pulls/`,
  cite `[brain] <path>`. Same degrade rules; **total Brain budget for the whole reel: ≤2
  searches + ≤3 note reads, never inside loops.**
  Use the client's vocabulary; pull verbatim audience pains from `voc-profile.md` where they fit
  (the client's words beat yours). On IG the hook is the **frame-1 on-screen text** — write it to
  double as burned-in caption.
- **Secondary hook** — the 1–2 second re-hook that keeps the viewer past the open.
- **Body beats** — fill the skeleton; one idea per beat; cut anything that delays the payoff.
- **Proof** — the specific/credible line (number, mechanism, story) the structure calls for.
- **CTA** — pull the matching scaffold from `./references/cta-scaffolds.md`, mapped to the
  client's actual goal/offer (from `business-config`).

Dial the **edge** to the voice guide (how blunt/contrarian the client is). Then run the whole draft
through the **7 Swaps** line-edit pass in `./references/story-locks.md` (name it · kill hedges · go
negative · add contrast · loop-openers every ~20–30s · narrate the doubt), and fix weak lines with
`./references/say-this-not-that.md` (creator-POV → viewer-benefit, vague → specific, buried →
front-loaded, jargon → plain).

Then write the **caption** (hook line + context + the same CTA) and suggest on-screen text for
the hook.

---

### Step 4 — Flow-check + craft score

**4a. Hook lens — the 4 Hook Killers.** Run the hook through
`../_shared/references/hook-diagnostics.md`: does it lose on **DELAY** (payoff too late),
**CONFUSION** (ambiguous/jargon), **IRRELEVANCE** ("I"-framing, no viewer benefit), or
**DISINTEREST** (topic the audience doesn't care about)? Fix any that fire before scoring.

**4b. Flow-check.** Read the script top to bottom as a viewer: does each beat earn the next?
Any dead beat, any place the attention drops — flag and tighten.

**4c. Craft score.** Score **Hook / Body / CTA / overall (0–100)** against the **Story Locks rubric**
(`./references/story-locks.md`) — how many of the 6 Story Locks + 7 Swaps the script lands (contrast,
zero hedges, named framework, negative-frame, loop-openers at cadence, viewer-framing). This is an
honest **craft** read, **not** a performance prediction: it never claims views. State the one
highest-leverage fix. *(This is the **single** craft score for the script — the dashboard's Scripting
Studio displays it, it does not recompute its own.)*

### ✋ Checkpoint 4 — Review the scored draft
Show the full draft + the four scores + the top fix + which Hook Killers were caught. **Pause**
for the user's edits or approval.

---

### Step 5 — Write the script file (one reel per run)

Write the approved reel to `<project>/scripts/<slug>.md` (slug = short kebab of the angle).
Structure:

```
# <Reel title / angle>
> Voice: <full voc | interim>  ·  Mode: <full | caption-only>  ·  Angle: <theme × hook>

## On-screen hook
## Script
  Hook:
  Secondary:
  Body:
  Proof:
  CTA:
## Caption
## Craft score
  Hook __/100 · Body __/100 · CTA __/100 · Overall __/100 — top fix: ...
## Evidence
  <@handle · metric · reel URL> citations from the analysis the angle stands on
```

Report the path. One run = one script.

**Next moves**
1. Script the next angle — the unpicked angles from Step 1 are still on the table; I'll re-show them. Say: "script the next angle"
2. Build the weekly idea bank instead of going reel-by-reel. Say: "weekly topic pool"
3. Refresh the visual pack so the client sees the field this script attacks. Say: "regenerate my visuals"
4. *If no pulse is scheduled yet:* want next week's winners to land here automatically? The weekly competitor pulse feeds this skill fresh outliers. Say: "run the weekly pulse"

---

## Topic Pool mode — "20 ideas from the best performers"

An alternate, ideation-only mode. Trigger phrases: "weekly topic pool", "topic pool",
"idea bank", "20 ideas", "what should I post this week". Runs INSTEAD of the
script pipeline — it produces ideas, not a script.

**Inputs (same Step 0 resolution):** `scripting-brief.md` + `analysis-data.json`, plus
the project's `transcripts/` when present. In FULL mode, mine the **top ~3
highest-performing transcripts per competitor** (rank by the analysis's outlier/views
data); in caption-only degrade, mine outlier captions + hook lines and say so.

**Output:** `<project>/topic-pool.md` — **~20 concrete reel ideas** from the niche's
proven winners, grouped by attack theme. Each idea is one tight block:

```
N. <Idea title — the angle in one line>
   Hook bucket: <from the analysis>  ·  Theme: <attack theme>  ·  Gap it closes: <gap>
   Why it wins: <the proven move it's stolen from, one line>
   Evidence: @handle · <metric> · <reel URL>
```

Rules:
- Every idea cites evidence (`@handle · metric · URL`) — same discipline as angles in
  Step 1. No vibes-only ideas.
- Spread across the brief's attack themes; don't let one theme eat the pool.
- These are **ideas in the niche's language, not yet in the client's voice** — voice
  work happens when an idea is picked.
- Refresh cadence: the pool is a **weekly** artifact. If `topic-pool.md` is older than
  ~7 days (or the analysis has been re-run), offer to regenerate instead of appending.

**The handoff (always end with it):** present the pool and ask — *"Pick one and I'll
make it yours"* — then run the normal pipeline from Step 1 with the picked idea as the
chosen angle (Checkpoint 0 voice rules still apply).

**If they don't pick (never a dead end)** — **Next moves**
1. The pool is saved at `<project>/topic-pool.md` — later, say: "script idea N from my topic pool"
2. Keep it fresh without lifting a finger — the weekly competitor pulse regenerates the pool off new data. Want it weekly? Say: "run the weekly pulse"
3. Re-spread the pool toward a theme you care about. Say: "rebuild the pool, lean <theme>"
4. Or I just script the single best idea now. Say: "script the top idea"

**Deeper trend/seed layer (optional):** if `~/.claude/socialcrawl-superengine/.superengine`
exists, offer the superengine's plays to enrich the pool — trend deep-dives and the
cost-gated `audience-questions` seeding (real audience questions clustered by intent).
Absent → one-line mention, continue.

---

## Guardrails

- **Analysis-driven, not vibes.** Every angle cites the analysis (`@handle · metric · URL`). If a
  claim about "what wins" isn't traceable to `analysis-data.json` / `scripting-brief.md`, cut it.
- **Voice before copy.** Never write final lines until the voice anchor is confirmed (Checkpoint 0).
  When degraded to interim voice, say so on the script.
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

- `./scripting_brief.py` — deterministic brief generator; run first (Step 0b)
- `./references/story-locks.md` — the 6 Story Locks + 7 Swaps craft-scoring rubric + line-edit pass (Step 4c)
- `./references/opener-patterns.md` — HOOK→PROMISE→MICRO-INTRO + first-3-seconds opener templates by hook bucket
- `./references/hook-formulas.md` — view-validated hook formulas mapped to the analysis's hook buckets
- `./references/body-structures.md` — body skeletons by hook bucket (Step 2)
- `./references/cta-scaffolds.md` — CTA patterns by goal (Step 3)
- `./references/say-this-not-that.md` — weak→strong rewrites, tagged to the 4 Hook Killers
- `../_shared/references/hook-diagnostics.md` — the 4 Hook Killers hook lens (Step 4a)
- `../_shared/contracts/analysis-data.schema.json` — the analysis JSON this skill consumes

---

## Non-Goals

- Generating a content calendar or a batch of finished reels — script mode writes
  **one** script per run. (Topic Pool mode may list ~20 *ideas*, but never batch-writes
  scripts — each idea still goes through the full pipeline one at a time.)
- Multi-platform (TikTok/Shorts/YouTube) — IG reels only; sibling format engines own the rest.
- Running the competitor analysis — that's `competitor-cross-reference`; this consumes its output.
- Predicting performance — craft quality only, never a views/virality forecast.
- Building the voice profile — that's the shared voice-matching skill; this consumes `voc/` or
  degrades to interim capture.
