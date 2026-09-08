---
name: competitor-cross-reference
description: >
  Runs a competitor cross-reference analysis for an Instagram account and
  turns it into a client-facing strategy roadmap. Trigger phrases: "analyze
  my Instagram against my competitors", "competitor cross-reference
  analysis", "cross-reference my client against competitors", "content gap
  analysis for an Instagram account", "IG baseline plus competitor audit",
  "build a content/growth strategy roadmap from competitor data", "analyze
  why a client's reels underperform vs competitors", "create a client-facing
  strategy roadmap from Instagram data". Visuals-only mode, rendered straight
  from an existing analysis-data.json with no re-pull: "build my visual
  dashboards", "regenerate my visuals", "open my visuals", "make the charts".
  Mid-run controls: "run more seeds", "shrink the set to N", "resume my
  cross-reference".
  IG-only. Produces analysis-data.json (the artefact every other skill reads),
  a 10-section client-facing strategy roadmap grounded in real SocialCrawl
  reel data and firecrawl website intelligence, and the offline HTML pack.
---

## Overview

Given a client IG handle (and an optional website): a guided, checkpointed
pipeline. Client baseline, competitor discovery, reel gather, metrics analysis,
then a 10-section client-facing roadmap. It calls SocialCrawl through
`../_shared/references/socialcrawl-endpoints.md`, reuses the `firecrawl` skill
and the deterministic `./analyze.py` engine, and transcribes automatically: the
spoken track is the analysis text, the caption is metadata. Every recommendation
is evidence-cited (handle + metric + reel URL).

## Teach mode

One dial, three levels, family shared. Read `~/.claude/revxl/teach-level`
(`new` / `learning` / `pro`), else the legacy `~/.claude/revxl/teach-mode`,
else `new`. Snippet and adjust rules, verbatim:
`../_shared/references/teach-mode.md`. Re-read at every start, mirror to
`state.teach_level`.

## Terminal paths

Every ending routes, refusals included. Phrases are verbatim from the roster in
`../_shared/references/journey-map.md`, grammar from `routing.md` beside it,
registry id in parentheses.

**Next moves** (E3)
1. Script the top gap, in your voice, as the chosen angle. Say: "script the top gap"
2. See it: `visuals/overview.html`, the reach ladder and the gaps. Say: "build my visual dashboards"
3. Feed the winning themes into your brand brain, so later scripts lean on them. Say: "add these themes to my brand brain"
4. *If `pulse.scheduled` is false:* keep this alive week to week, on your day. Say: "make the pulse weekly"

**Next moves ... thin set** (E4)
1. Run more seed queries and rebuild the candidate list. Say: "run more seeds"
2. Park it. Baseline, candidates and the checkpoint are saved. Say: "resume my cross-reference"
3. Proceed thin anyway. Your explicit call: gaps read shallower with few competitors.

**Next moves ... credits short** (E5)
1. Shrink the set to fit the balance, I recompute the cost. Say: "shrink the set to N"
2. Top up, then pick this run back up where it stopped. Say: "resume my cross-reference"
3. Park it. Everything pulled so far stays, and is never re-charged.

**Next moves ... no setup yet** (E0)
1. Run setup first. It is what lets this pull real data at all. Say: "set up shortform superengine"
2. Already set up, and want to see what is missing? Say: "show my setup"
3. Not sure where you are in the flow? Say: "what's next in shortform"

**Next moves ... a parked run is waiting** (F1)
1. Resume at the stored checkpoint, nothing re-pulled or re-charged. Say: "resume my cross-reference"
2. Start fresh instead. The parked run stays on disk. Say: "competitor cross-reference analysis"
3. See the whole board first. Say: "what's next in shortform"

**Next moves ... Vault degraded** (F3)
1. Keep the roadmap: real field data, only the doctrine check skipped. Say: "build my visual dashboards"
2. Script the top gap on the bundled frameworks, labelled. Say: "script the top gap"
3. Install or update workspace-superengine, then re-run the roadmap step.

**Next moves ... visuals only** (E0b)
1. Script the top gap the charts just made obvious. Say: "script the top gap"
2. Re-render once the next pulse lands new data. Say: "regenerate my visuals"
3. Keep the field current so the charts stay true. Say: "run the weekly pulse"

## Prereq (E0)

The door is `onboarding`. This skill needs the marker
`~/.claude/shortform-superengine/.superengine` (for `active_brand`) and a
SocialCrawl key resolving through the ladder in
`../_shared/references/socialcrawl-endpoints.md`. No marker: the run refuses
and routes, rendering the `no setup yet` block with "set up shortform
superengine" as move one. Never start a paid pull to find out. Everything
downstream is gated on the `analysis` this run writes.

## State

The journey file is `~/.claude/shortform-superengine/state/<brand>.json`
(`../_shared/references/state-schema.md`). `<brand>` is the marker's
`active_brand` (legacy alias `brand`).

**Read at start:** the whole file plus `~/.claude/revxl/teach-level`. Act on
`analysis.resume` (a parked run) and `pulse.scheduled` (never re-offer a
schedule already accepted).

**Write at end,** owned keys only (rule zero: no invented keys).
`analysis.date` (today, on a completed run), `analysis.n_competitors`,
`analysis.themes_set` (true ONLY when the theme-derivation step ran and wrote
`analysis-config.json`, false when `analyze.py` fell back to built-in themes),
`analysis.resume`
(`{"checkpoint": 2 or 3, "note": "<one line>", "opened": "<YYYY-MM-DD>"}` at a
park exit, null again once the run completes), `project_path`. Plus the
every-skill keys: `updated_at`, a `completed_skills` append, `open_loops`
opened or closed (a park opens one, a resume closes it), `declined_offers`, the
`teach_level` mirror. Nothing else. `voc.*` is derived on read, never written.

---

## Guided Pipeline

### Step 0 — Intake

**0a. Entry guard, before anything else.** Read the marker
`~/.claude/shortform-superengine/.superengine` and the journey file.

1. No marker: stop, render the `no setup yet` block. Do not pull, do not ask
   for a handle.
2. No `active_brand` and no legacy `brand`: ask once, normalize to the slug
   convention in `../_shared/references/state-schema.md`, carry on.
3. `analysis.resume` set: name the checkpoint it stopped at, render the
   `a parked run is waiting` block, offer the resume BEFORE a fresh run. On
   resume, re-enter there with the seeds and approved set already on disk
   (edge E22); clear `analysis.resume` when the run completes.

**0b. Intake.** Client IG handle (required), website URL, niche hint, any
creators they already have in mind, target competitor count (~25 as a floor,
8 large / 9 med / 8 small), transcription (on by default, opt-out only).

> **A handful of names is a seed, not the set.** Two or three named creators
> are seeds: expand to the ~25 floor in Step 2. Full intake table and the
> reasoning: `./references/pipeline-detail.md`.

Create `projects/<YYYY-MM-DD>-<client-slug>-baseline/` with the `source/` tree
the pipeline writes into. Layout and per-file owners:
`./references/project-shape.md`.

---

### Step 1 — Client Baseline

**1a. SocialCrawl profile + reels**

Call SocialCrawl directly. Paths, params, prices and the key ladder live in
`../_shared/references/socialcrawl-endpoints.md`:

1. `instagram/profile` with `handle` (1cr): follower count, bio, link-in-bio URL.
2. Paginate `instagram/profile/reels` with `handle` (1cr per page) via `&max_id=<next_cursor>` to ~36 reels (or until the cursor is exhausted). Apply the ingest repairs, mojibake and epoch coercion (`./references/guardrails.md`). Save raw JSON to `source/reels-full.json`.

**1b. Positioning.** With a website: `firecrawl map`, scrape home, about,
offers and lead magnets into `source/website-*.json`, and synthesize
`foundation.md` (niche, ICP, core offer, differentiators). Without one: derive
positioning from the IG bio, any link-in-bio page and the top captions, and
write `foundation.md` carrying the reduced-confidence notice. Both paths in
full, plus the views, likes and comments only constraint:
`./references/pipeline-detail.md`.

---

### ✋ Checkpoint 1 — Confirm Niche + Positioning

Present the inferred niche, the positioning summary from `foundation.md` and
the ICP hypothesis (`./references/pipeline-detail.md`).

**Pause. Do not proceed to competitor sourcing until the user confirms or corrects.**

---

### Step 2 — Competitor Sourcing

**2a. Derive niche seeds**

Follow `./references/niche-seeds.md` to construct broad + niche-specific seed phrases for the confirmed niche. Seeds cover: broad category terms, audience-descriptor terms, methodology/modality terms, and outcome/transformation terms.

Competitors the user named in Step 0 stay in the pool and get expanded around,
never treated as the finished set (`./references/pipeline-detail.md`).

**2b. SocialCrawl reel search**

For each seed, call `instagram/search/reels` with `query=<seed>` (1cr documented, 5cr as the pulse prices the same leg: verify against `credits_used` before looping, `../_shared/references/socialcrawl-endpoints.md`). Collect the unique creator handles into the candidate pool. Search returns a first-page sample of about 10 and does not paginate, so breadth comes from many diverse seeds.

**2c. Profile-tier candidates**

For each candidate handle, call `instagram/profile` with `handle` (1cr) for the follower count. Save the raw profile JSON to `source/competitors/profiles/<handle>.json`. Tier relative to the client: GURU at or above 500k (aspirational reference, not size-comparable, out of the LARGE benchmark), LARGE above 3x, MED 0.5x to 3x, SMALL below 0.5x. Why the GURU split exists: `./references/pipeline-detail.md`.

**2d. Deeper recon (optional).** Probe for socialcrawl-superengine as
`../_shared/references/socialcrawl-endpoints.md` describes (marker first, then
the plugin cache directory). Installed: offer its `research-plays` skill for
ad-library recon and a cost-gated share-of-voice one-shot. Absent: mention it
once and continue. Never block the pipeline, never fake a deep play (edge F9).

---

### ✋ Checkpoint 2 — Approve Competitor Set

Present the tiered candidate list with tier labels, filtered (drop hospitals,
celebrities, institutions, off-niche and private accounts, anything under 10
reels; flag borderline ones for human judgment). Target ~25 (8 large / 9 med /
8 small); the user may swap, add or remove. Still under ~25: back to Step 2 for
more seeds rather than present a thin set as final. Filters and reasoning:
`./references/pipeline-detail.md`.

**Pause. Do not gather reels until the user approves the final set.**

If the user stops here (set too thin, needs better seeds, out of time), never
leave them hanging: render the `thin set` block from Terminal paths (E4). On
the park exit, write `analysis.resume` FIRST: checkpoint 2, a one-line note
naming the seeds already run and the size of the candidate set so far, and
today's date. The pointer is persisted, never session memory.

---

### Step 3 — Gather Competitor Reels

For each approved competitor handle, paginate `instagram/profile/reels` with `handle` and `&max_id=<next_cursor>` to collect ~36 reels (1cr per page). Apply the same ingest repairs (mojibake, epoch coercion). Save each to `source/competitors/reels/<handle>.json`.

**Note:** ~36 reels per competitor × N competitors ≈ N×3 SocialCrawl credits.

---

### ✋ Checkpoint 3 — Confirm Reel Depth + Credit Cost

Fetch the **live balance** first: `GET /v1/credits/balance` reads
`data.balance` and costs 0 credits; every other price comes from
`../_shared/references/socialcrawl-endpoints.md`. Report the approved count,
reels per competitor (36), the estimated cost (`N x 3`) and the after-balance,
plainly and out loud (`./references/pipeline-detail.md`). Over balance: say so
and offer to shrink the set or top up. Never start a pull that runs dry
mid-way.

**Pause. Only begin the big pull after explicit confirmation.**

If the user declines the spend, never dead-end: render the `credits short`
block from Terminal paths (E5). On the park or the top-up exit, write
`analysis.resume` FIRST: checkpoint 3, a one-line note naming the approved set
and the priced cost, and today's date.

---

### Step 4 — Analyze

**4a. Write `tiers.json`**

In the project directory, write `tiers.json` mapping each handle to its tier:
`client`, `client_followers` (required integer), and the UPPERCASE tier keys
`GURU` (optional), `LARGE`, `MED`, `SMALL` holding bare handles with no `@`, so
they match the filenames under `source/competitors/profiles/`. Worked example:
`./references/pipeline-detail.md`.

**Roster rule, every run.** Exclude any account over **1M followers** from the
tier set: at that size it is a different universe and it drags the LARGE
benchmark off true. Between the GURU floor and 1M, keep it in `GURU` as
reference only. The band the roadmap models on is roughly 10k to 250k. And
**rank on outlier score**, a reel against its own channel's median, never raw
views: raw views rank the biggest account, outlier score ranks the best idea.
Doctrine: the FIELD row of `../_shared/references/vault-api.md`.

**4b. Run `analyze.py`**

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/competitor-cross-reference/analyze.py <project_dir>
```

**Transcribe first**, before `analyze.py`: the spoken track carries the
diagnosis, the caption read is a separate section. A caption-only run can be
re-run after transcription and upgrades in place. Why, and how:
`./references/transcription.md`.

It reads the client reels, the competitor reels, the profiles and `tiers.json`,
then writes `analysis-data.md` and `analysis-data.json`: reach efficiency,
engagement rate, per-creator outliers at 2.5x their own median, hook taxonomy,
theme clusters by tier, posting cadence. Engagement is views, likes and comments
**only**; saves and shares are never computed, displayed or estimated. Formulas
and field list: `./references/pipeline-detail.md`.

**4c. Pattern Matrix (recommended when transcripts exist)**

Once timestamped transcripts exist, run the two-layer pattern matrix (method
and dimension list: `./references/pattern-matrix.md`):

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/competitor-cross-reference/transcribe_reels.py <project_dir>
python ${CLAUDE_PLUGIN_ROOT}/skills/competitor-cross-reference/extract_patterns.py <project_dir>
python ${CLAUDE_PLUGIN_ROOT}/skills/competitor-cross-reference/select_beatmap_set.py <project_dir>
```

Transcribe the same day as the pull (CDN expiry). Layer 1 writes corpus-scale
statistics; Layer 2 picks the stratified subset Claude hand-maps into the Reel
Beat Blueprint feeding Step 5 and reel-scripter. Clusters and themes come from
`analysis-config.json`, never from the scripts
(`./references/theme-derivation.md`, `./references/pipeline-detail.md`).

---

### Step 5 — Synthesize Strategy Roadmap

Write `strategy-roadmap.md` on the 10-section structure in
`./references/roadmap-template.md`, which is the authority on each section's
shape: executive summary, current state, strengths, weaknesses, competitor
gaps, opportunity matrix, content strategy, 30-day plan, 90-day roadmap,
hypotheses.

**Citing evidence:** every recommendation cites at least one data point, `@handle · metric · reel URL`. No claim that is not traceable to `analysis-data.md` or `source/`.

**Hook-gap diagnosis:** ground every hook observation in the 4 Hook Killers
(DELAY, CONFUSION, IRRELEVANCE, DISINTEREST) from
`../_shared/references/hook-diagnostics.md`, and diagnose *why* a hook type
under-reaches, not just which one does. That is what makes a recommendation
concrete instead of generic.

**Vault trigger point (the roadmap).** Before the roadmap is finalized, run the
one pull this skill is allowed, per `../_shared/references/vault-api.md`: one
Skill call to `workspace-superengine:revxl-vault-search`, `depth=med`,
`plugin=shortform-superengine`, `spoke=content-strategy`, the question and the
three FIELD angles from that file's recipe table. Read the echoed spoke back.
Print the evidence line either way:
`Vault: <n> searches, <m> reads | <ok|degraded|skipped: reason>`. Callee
missing or erroring: continue on the bundled references, say so in one line,
render the `Vault degraded` block (edge F3). The Vault never blocks the
roadmap.

---

### ✋ Checkpoint 4 — Deliverable Scope + Tone

Before finalizing `strategy-roadmap.md`, surface the roadmap audience, the tone
and any sections to expand, trim or rename
(`./references/pipeline-detail.md`).

**Pause. Finalize only after confirmation.**

---

## Guardrails

Non-negotiable on every run, in full in `./references/guardrails.md`:
`&max_id` pagination only, Windows and Python path safety, balance plus cost
plus confirm before any paid batch, saves and shares never fabricated,
latin1-mojibake caption repair on ingest, an honest caveat on every estimated
number.

---

## Transcription (ON by default, automatic)

**ON by default, automatic.** The spoken transcript is the **primary text** the
analysis reads; the caption is metadata. A caption-only analysis is a broken
analysis and is never presented as the real thing. Skip only on an explicit
opt-out.

**Never** call any `*/transcript` endpoint and never add `include=transcript`
to a paid call: 10 credits per reel for no advantage over the free local chain.
The `hooks/credit-guard.mjs` PreToolUse hook hard-denies them.

The chain, the vocabulary prompt, timestamps, the caption-only floor and the
signed-CDN expiry trap: `./references/transcription.md`.

---

## Output shape

Two primary artefacts: **`analysis-data.json`**, the machine artefact
`analyze.py` writes beside `analysis-data.md` and the one `competitor-pulse`,
`reel-scripter`, `content-plan` and `render_visuals.py` all read (the ANALYSIS
gate checks for it), and **`strategy-roadmap.md`**, the 10-section client-facing
deliverable. Everything else: `./references/project-shape.md`.

---

## References

Scripts sit beside this file (`analyze.py`, `transcribe_reels.py`,
`extract_patterns.py`, `select_beatmap_set.py`, `render_visuals.py`); bundled
and shared reference files are named at the step that needs them. Full index:
`./references/pipeline-detail.md`.

---

## Render the visual pack

When the roadmap is delivered, offer the visuals. People share what they see.

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/competitor-cross-reference/render_visuals.py <project_dir> [--split]
```

Writes `<project>/visuals/`: `overview.html`, `competitors.html`,
`client.html`, self-contained offline HTML that opens and sends anywhere. Page
contents, `--split` delivery files and `visual-theme.json` branding:
`./references/project-shape.md`.

**Visuals-only mode:** charts wanted and `analysis-data.json` already on disk,
run the command directly. No re-pull, no re-analysis. It ends on the
`visuals only` block in Terminal paths (E0b).

## When the roadmap + visuals are delivered

State the one-line preamble (what was produced, where it was saved), then
render the E3 block from Terminal paths, bare. Deeper research legs (audience
questions, trend scans, comment mining) live in `competitor-pulse`.
