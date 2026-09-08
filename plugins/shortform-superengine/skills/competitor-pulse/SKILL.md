---
name: competitor-pulse
description: The weekly heartbeat on the competitive field. Refreshes the competitor analysis with the last 7 days (14 on request), manages the roster, reads roster health, keyword-searches the field and mines comment patterns. Use for "run the weekly pulse", "run the pulse", "competitor pulse", "what changed this week", "refresh my competitor analysis", "make the pulse weekly", "run the pulse on 14 days", "roster health", "manage my roster", "add <handle> to my roster", "swap a competitor", "backfill and re-analyze", "search the field for <keyword>", "comment pulse", "comment pulse on <url>", "comment pulse on <scope>", "mine the comments on <url>", "what are people saying in <handle>'s comments", "run audience questions", "add/remove/swap a competitor". Requires a completed competitor-cross-reference run (analysis-data.json).
---

# competitor-pulse

Keeps a finished `competitor-cross-reference` project **alive**: a cheap weekly
delta pull, winners-only deep dives, roster upkeep, field keyword search, and
comment mining — all against the same project, same metrics engine, same
regression-locked contract. One pulse ≈ the cost of a coffee refill in credits;
the analysis never goes stale.

## Teach mode

One dial, three levels, family shared. Read `~/.claude/revxl/teach-level`
(`new` / `learning` / `pro`), else the legacy `~/.claude/revxl/teach-mode`,
else `new`. Snippet and adjust rules, verbatim:
`../_shared/references/teach-mode.md`. Re-read at every start, mirror to
`state.teach_level`.

## Terminal paths

Every ending routes, refusals and failures included. Phrases are verbatim from
the roster in `../_shared/references/journey-map.md`, grammar from `routing.md`
beside it, registry id in parentheses.

**Next moves** (E14)
1. Script this week's winner, the top new outlier as the angle. Say: "script that reel"
2. Open the refreshed pack, the This-week panel is live. Say: "open my visuals"
3. Roster upkeep: someone quiet, or someone missing? Say: "swap a competitor"
4. *If `pulse.scheduled` is false:* have this land on your desk weekly, on your day. Say: "make the pulse weekly"

**Next moves ... roster op done** (E15)
1. Backfill the new competitor's reels now (~3cr) and re-run the analysis. Say: "backfill and re-analyze"
2. Leave it. Next week's pulse folds them in automatically.
3. Run a pulse now to see the field with the new roster. Say: "run the pulse"

**Next moves ... empty week** (E16)
1. Widen the window to 14 days, same listing cost. Say: "run the pulse on 14 days"
2. Nothing changed and nothing extra was spent. Script from the ideas you have. Say: "script idea N from my content plan"
3. Who has gone quiet? The health pass costs nothing. Say: "roster health"

**Next moves ... schedule set** (E0b)
1. Run the first pulse now, so the schedule starts from fresh data. Say: "run the pulse"
2. Add a monthly roster pass on top of the weekly winners read: a deeper roster and outlier re-read once a month, no change to the weekly cost. Say: "roster health"
3. Check the roster is still the right field before the first scheduled run. Say: "manage my roster"

**Next moves ... some accounts failed** (F5)
1. Retry just the failed handles, listing legs only. Say: "run the pulse"
2. If the same handles keep failing, read the roster. Say: "roster health"
3. Proceed on the partial set, with the coverage caveat stated in the brief.

**Next moves ... no analysis yet** (E0)
1. Build the baseline first. The pulse refreshes an analysis, it cannot invent one. Say: "analyze my Instagram against my competitors"
2. *If you parked one mid-run:* pick it back up. Say: "resume my cross-reference"
3. Not sure where you are? Say: "what's next in shortform"

**Next moves ... no setup yet** (E0)
1. Run setup first. It is what lets the pulse pull real data at all. Say: "set up shortform superengine"
2. See what is installed and what is missing. Say: "show my setup"
3. Not sure where you are in the flow? Say: "what's next in shortform"

**Next moves ... credits short** (F4)
1. Run the listing pass only, skip the deep legs. The brief still lands. Say: "run the pulse"
2. Top up, then run the full pulse. Say: "run the weekly pulse"
3. Trim the roster to the accounts that earn their credits. Say: "manage my roster"

**Next moves ... field search done** (E0b)
1. Script the top hit's angle in your voice. Say: "script that reel"
2. Found a creator worth tracking? Say: "add <handle> to my roster"
3. Mine what audiences say about it. Say: "comment pulse on <url>"

**Next moves ... comment intel** (E0b)
1. Script a reel answering the top question, a pre-validated hook. Say: "script the top question"
2. The intent-clustered version, `prism/audience-questions` at 30cr. Say: "run audience questions"
3. Mine another scope, another creator or the whole field. Say: "comment pulse on <scope>"
4. File the patterns as audience VoC, marked third-party, never the client's own voice. Say: "add this to my brand brain"

**Next moves ... 14-day window** (E23)
1. Script the widened window's top outlier. Say: "script that reel"
2. Open the refreshed pack. Say: "open my visuals"
3. Back to the weekly rhythm from here. Say: "make the pulse weekly"

**Next moves ... roster health** (E24)
1. Swap the quiet accounts out for live ones. Say: "swap a competitor"
2. Run the pulse now on the tightened roster. Say: "run the pulse"
3. Add someone specific you already have in mind. Say: "add <handle> to my roster"

## Prereq (E0)

Two doors. `onboarding` (the marker `~/.claude/shortform-superengine/.superengine`
plus a SocialCrawl key) and `competitor-cross-reference` (a finished project:
`analysis-data.json` on disk and `analysis` set in state). The pulse refreshes an
analysis, it cannot invent one. Either missing: refuse and route, rendering the
matching block above with the door as move one. Never a stall, and never a paid
call to find out.

## State

`~/.claude/shortform-superengine/state/<brand>.json`
(`../_shared/references/state-schema.md`). Resolve `<brand>` on the same ladder
competitor-cross-reference Step 0a uses: the marker's `active_brand`, then the
legacy `brand` alias, then ask once and carry on. Never infer it from a folder
name, and never run on a brand the client did not name.

**Read at start:** the whole file plus `~/.claude/revxl/teach-level`. Schedule
state comes from `state.pulse` FIRST. Only when the file has no `pulse` block (an
un-migrated 0.3.x home) fall back to the marker's `competitor_pulse` block, copy
it into `state.pulse`, and say so in one line. A home that already accepted a
schedule is never re-offered one.

When that fallback CREATES the state file, seed `analysis` in the same write from
the `analysis-data.json` Step 0 just located: `date` = its modified time as
YYYY-MM-DD, `n_competitors` = the competitor count inside it, `themes_set` false,
`resume` null. Say that in the same one line. Without the seed the compass reads
`analysis` as null on a machine that plainly has one and ranks "analyze my
Instagram against my competitors" first all over again. Seeded at file creation
only; `analysis.*` stays competitor-cross-reference's (`state-schema.md`).

**Write at end,** owned keys only (rule zero: no invented keys). `pulse.scheduled`,
`pulse.day`, `pulse.last_run` (local date), `pulse.last_snapshot` (the path under
`<project>/history/`). Plus the every-skill keys: `updated_at`, a
`completed_skills` append, `open_loops` opened or closed, `declined_offers` (a
declined schedule goes here and is not re-offered), the `teach_level` mirror.
**From 0.4.0 this skill never writes the `.superengine` marker**, and it never
writes `analysis.*`: those belong to onboarding and competitor-cross-reference.

## Credit discipline (non-negotiable)

Balance check (`GET /v1/credits/balance`, **0cr**) comes FIRST; every paid step
is priced out loud and confirmed at a ✋ before it runs. Per-call prices are the
endpoints table's, `../_shared/references/socialcrawl-endpoints.md`, and the
documented ones are verified against `credits_used`. **No paid call ever
precedes ✋P1.** Scheduled runs stop at ✋P1 too — a schedule wakes the pulse up,
it never spends by itself.

| Leg | Endpoint | Cost | When |
|---|---|---|---|
| Balance | `credits/balance` | 0 | always first |
| Listing, client + roster | `instagram/profile/reels` p1 (~12 reels) | (N+1) × 1cr | every pulse, after ✋P1 |
| Client followers | `instagram/profile` | 1cr | every pulse |
| Competitor followers | `instagram/profile` × N | N × 1cr | MONTHLY or roster ops only — reach-eff tolerates week-stale denominators (noted in the brief) |
| Winner shares | `instagram/post/stats` | 5cr/reel | winners only, ✋P2, cap ~6 |
| Winner comments | `prism/comments` | **~5cr/reel on IG** (delegates to a native leg — live-verified; the 1cr doc price applies to non-IG platforms only) | optional, ✋P2 |
| New-handle verify / backfill | `instagram/profile` / `instagram/profile/reels` | 1cr / ~3cr | roster ops, gated |
| Transcription | local chain (Groq + Whisper parallel) | 0cr | automatic — runtime cost, not credits |

Typical 25-roster week ≈ **27cr**. Heavy week (6 deep-legged winners with
shares + comments) ≈ **87cr** (6 × 5cr shares + 6 × ~5cr comments + listing).
Quiet week = 27cr and stops there.

---

## Step 0 — Locate + mode

Find the project: the newest directory containing `analysis-data.json` (ask if
several match). None anywhere: render the `no analysis yet` block from Terminal
paths and stop, before any call. No marker: render `no setup yet` and stop.
Load the roster from `analysis-config.json` / `tiers.json` via the shared
loader (`_shared/lib/reel_io.load_config`). Read the journey file for `pulse`
(marker fallback per **State** above). Then route on what the user asked:

| Mode | The client says | Runs |
|---|---|---|
| pulse (default) | "run the weekly pulse", "run the pulse", "what changed this week", "refresh my competitor analysis" | Step 1, 7-day window |
| 14-day window | "run the pulse on 14 days" | Step 1 with the window set to 14 (`./references/modes.md`) |
| roster ops | "manage my roster", "add <handle> to my roster", "swap a competitor", "backfill and re-analyze" | `./references/modes.md` |
| roster health | "roster health" | `./references/modes.md`, free, no paid call |
| field search | "search the field for <keyword>" | `./references/modes.md` |
| comment pulse | "comment pulse", "comment pulse on <url>", "mine the comments on <url>", "run audience questions" | `./references/modes.md` |
| schedule | "make the pulse weekly" | Schedule, below |

## Step 1 — Snapshot

Copy the current `analysis-data.json` →
`history/analysis-data-<YYYY-MM-DD>.json` (create `history/` if absent). Dates
live in **filenames only** — the live JSON stays date-free so the deterministic
render contract holds. This snapshot is what "what changed" diffs against.

## ✋ Checkpoint P1 — price the listing pass

Balance first (0cr). Then state plainly:

> "Listing pass = (N roster + client) × 1cr + 1cr client profile ≈ **(N+2)cr**.
> Balance M → ≈ M−(N+2) after. Go?"

**Pause.** Nothing paid runs before this yes.

## Step 2 — Cheap listing pass (1cr legs only)

The window comes from the mode, never from a guess: **7 days by default, 14
when the client asked for "run the pulse on 14 days"**. Say which window this
run used in the brief.

- Client + each roster handle: `GET /v1/instagram/profile/reels?handle=…`
  **first page only** (~12 reels, 1cr). If EVERY reel on page 1 is younger than
  the window (high-cadence account), paginate once more via `max_id` (+1cr, say
  so).
- Client `GET /v1/instagram/profile` (1cr) → refresh `client_followers` in the
  config if changed.
- **New reels** = items whose `post.url` is not already in `source/**/reels`
  JSONs, filtered by `published_at` to that window.
- Zero new reels anywhere → report the quiet week honestly and end on the
  `empty week` block (E16). Total spend stays the listing cost.

## Step 3 — ✋ Checkpoint P2 — winners-only deep legs

**Winner** = a new reel with `views ≥ 2.5×` that creator's stored
`stats.med_views` (from the snapshot). For winners ONLY, offer per-reel deep
legs, each named with its price, hard-gated here (suggested cap: ~6/week):

- **Shares** — `instagram/post/stats`, **5cr/reel**. The only place real share
  counts exist. Presented in the weekly brief labeled "fetched via post/stats";
  **never merged into `analysis-data.json`** (the engine's engagement stays
  views/likes/comments).
- **Comments** — `prism/comments`, **~5cr/reel on IG** (prism delegates to the
  native leg and bills it — live-verified 07.09.26; 1cr only on non-IG
  platforms). Feeds Comment-pulse if the user wants patterns.
- **Transcription** — free local chain, automatic per house policy (runtime
  warning, not credits). Transcripts land in `transcripts/`.

Raw deep-leg responses → `source/winners/<shortcode>-stats.json`.

## Step 4 — Merge + re-analyze (additive, never destructive)

- Append new reel items into the matching `source/competitors/reels/<handle>.json`
  (or client reels file) **in the same raw shape** `analyze.py` reads.
  **Replace-on-match by `post.url`** (a re-listed reel carries CURRENT counts —
  view growth is real signal), **append-on-new**, never delete.
- Re-run the engine:

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/competitor-cross-reference/analyze.py <project_dir>
```

## Step 5 — Delta + visuals

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/competitor-cross-reference/render_visuals.py <project_dir> \
       --prev history/analysis-data-<last>.json --stamp "Week of <date>"
```

Regenerates `visuals/` + writes `visuals/whats-new.json`; archive a copy to
`history/whats-new-<date>.json`.

## Step 6 — "What changed this week" brief

Present from `whats-new.json` + the listings just pulled — **every line cited**
(`@handle · metric · reel URL`):

- **New outliers** (the week's breakouts — each with mult, hook line, link)
- **Hook movement** (`hook_taxonomy` field/client med-views old → new)
- **Cadence movement** (+ "posted K this week vs X/wk average" from the listing)
- **Client movement** (stats + reach-efficiency rank old → new)
- **Quiet accounts** (nothing new ≥14 days — roster-health candidates)
- **Credits**: used this run / balance remaining

Write `pulse.last_run` and `pulse.last_snapshot` to the journey file, then end
on the **E14** block in Terminal paths. An empty week ends on **E16**. Any
account that failed to pull (`failed > 0`) ends on **F5**: the retry pass
first, then roster health.

---

## Sub-modes

Bodies live in `./references/modes.md`, one section each. Each names the
Terminal-paths block it ends on.

- **Roster ops** (add / remove / swap / backfill): verify, tier, write the
  config, move retired data, log the op. Ends on E15.
- **Roster health**: a free read of the roster you already have, quiet accounts
  and tier balance, recommendations only. Ends on E24.
- **Field search**: free local corpus first, then the priced Tier 2 legs behind
  a ✋. Ends on the `field search done` block.
- **Comment pulse**: scope, price, pull, then the two-layer intel doc. Ends on
  the `comment intel` block.
- **14-day window**: the same pipeline with the window set to 14. Ends on E23.

---

## Schedule (suggested, never automatic)

Offer ONCE per session, and only when `pulse.scheduled` is false:

> "Want this to run weekly? Monday morning before content planning, Friday
> wrap-up, or a slot you pick. There is also a monthly roster pass you can add
> on top of the weekly winners read: a deeper roster and outlier re-read once a
> month. No change to what a week costs."

The schedule itself stays **weekly**. On yes, mirror the onboarding Step 4c
pattern: **Cowork** a scheduled task, **Claude Code** `/schedule`, cron or
Windows Task Scheduler. Record it in the journey file as `pulse.scheduled` and
`pulse.day`. Nothing is written to the marker.

A scheduled run still stops at ✋P1 before spending. A decline is respected:
log it in `declined_offers` and do not re-offer this session. Ends on the
`schedule set` block in Terminal paths.

## Notes

- Requires a completed cross-reference project. None on disk: the
  `no analysis yet` block (E0), never a stall.
- Never use SocialCrawl `media/transcript` (10cr) — transcription is the free
  local chain, always.
- Shares data never enters `analysis-data.json` — the metrics engine's
  engagement definition stays regression-locked.
