---
name: competitor-pulse
description: The weekly heartbeat on the competitive field. Refreshes the competitor analysis with the last 7 days (14 on request), manages the roster, reads roster health, keyword-searches the field and mines comment patterns. Use for "run the weekly pulse", "run the pulse", "competitor pulse", "what changed this week", "refresh my competitor analysis", "make the pulse weekly", "run the pulse on 14 days", "retry the failed handles", "roster health", "manage my roster", "add <handle> to my roster", "swap a competitor", "backfill and re-analyze", "search the field for <keyword>", "comment pulse", "comment pulse on <url>", "comment pulse on <scope>", "mine the comments on <url>", "what are people saying in <handle>'s comments", "run audience questions", "add/remove/swap a competitor". Requires a completed competitor-cross-reference run (analysis-data.json).
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

**Next moves**
(E14)
1. Script this week's winner, the top reel in `analysis-data.json` `period_breakouts` as the angle. Say: "script that reel"
2. Open the refreshed pack, the This-week panel is live. Say: "open my visuals"
3. Roster upkeep: someone quiet, or someone missing? Say: "swap a competitor"
4. *If `pulse.scheduled` is false:* have this land on your desk weekly, on your day. Say: "make the pulse weekly"

**Next moves ... roster op done**
(E15)
1. Backfill the new competitor's reels now (~3cr) and re-run the analysis. Say: "backfill and re-analyze"
2. Leave it. Next week's pulse folds them in automatically.
3. Run a pulse now to see the field with the new roster. Say: "run the pulse"

**Next moves ... empty week**
(E16) nothing changed and nothing extra was spent.
1. Widen the window to 14 days, same per-account listing cost. Say: "run the pulse on 14 days"
2. Plan the week off the field you have ... 7 to 15 source-tagged ideas. Say: "plan my week"
3. *If `plan.path` is set:* Script from the ideas you have. Say: "script idea N from my content plan"
4. *If `pulse.scheduled` is false:* have the weekly delta land on your day. Say: "make the pulse weekly"

**Next moves ... schedule set**
(E0b)
1. Run the first pulse now, so the schedule starts from fresh data. Say: "run the pulse"
2. Add a monthly roster pass on top of the weekly winners read: a deeper roster and outlier re-read once a month, no change to the weekly cost. Say: "roster health"
3. Check the roster is still the right field before the first scheduled run. Say: "manage my roster"

**Next moves ... some accounts failed**
(F5)
1. Retry just the failed handles, listing legs only. Say: "retry the failed handles"
2. If the same handles keep failing, read the roster. Say: "roster health"
3. Proceed on the partial set, with the coverage caveat stated in the brief.

**Next moves ... no analysis yet**
(E0)
1. Build the baseline first. The pulse refreshes an analysis, it cannot invent one. Say: "analyze my Instagram against my competitors"
2. *If you parked one mid-run:* pick it back up. Say: "resume my cross-reference"
3. Not sure where you are? Say: "what's next in shortform"

**Next moves ... no setup yet**
(E0)
1. Run setup first. It is what lets the pulse pull real data at all. Say: "set up shortform superengine"
2. See what is installed and what is missing. Say: "show my setup"
3. Not sure where you are in the flow? Say: "what's next in shortform"

**Next moves ... credits short**
(F4)
1. Run the listing pass only, skip the deep legs. The brief still lands. Say: "run the pulse"
2. Top up, then run the full pulse. Say: "run the weekly pulse"
3. Trim the roster to the accounts that earn their credits. Say: "manage my roster"

**Next moves ... field search done**
(E0b)
1. Script the top hit's angle in your voice. Say: "script that reel"
2. Found a creator worth tracking? Say: "add <handle> to my roster"
3. Mine what audiences say about it. Say: "comment pulse on <url>"

**Next moves ... comment intel**
(E0b)
1. Script a reel answering the top question, a pre-validated hook. Say: "script the top question"
2. The intent-clustered version, `prism/audience-questions` at 30cr. Say: "run audience questions"
3. Mine another scope, another creator or the whole field. Say: "comment pulse on <scope>"
4. File the patterns as audience VoC, marked third-party, never the client's own voice. Say: "add this to my brand brain"

**Next moves ... 14-day window**
(E23)
1. Script the widened window's top outlier. Say: "script that reel"
2. Open the refreshed pack. Say: "open my visuals"
3. Back to the weekly rhythm from here. Say: "make the pulse weekly"

**Next moves ... roster health**
(E24)
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

That fallback's creation write also seeds `analysis`, `setup.*`, `project_path`
and `state.pulse`, once, never overwritten: read `./references/modes.md`
"Marker-fallback seed" before that write.

**Write at end,** owned keys only (rule zero: no invented keys). `pulse.scheduled`,
`pulse.day`, `pulse.last_run` (local date), `pulse.last_snapshot` (the path under
`<project>/history/`), the last two written on every completed run, the quiet
week included. Plus the every-skill keys: `updated_at`, a
`completed_skills` append, `open_loops` opened or closed, `declined_offers` (a
declined schedule goes here and is not re-offered), the `teach_level` mirror.
**From 0.4.0 this skill never writes the `.superengine` marker except one
write-if-absent**: when the ask-once rung above resolved the brand and the
marker's `active_brand` is absent or null, write it there with that value, never
over an existing one. It never writes `analysis.*` after the creation seed
above; the owner is competitor-cross-reference.

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

Week totals (typical, heavy, quiet): `./references/modes.md` "Week prices".

---

## Step 0 — Locate + mode

Find the project: the marker's `competitor_pulse.project` FIRST, then the newest
directory containing `analysis-data.json` (ask if several match), the same order
`shortform-start` uses at its migration. None anywhere: render the `no analysis yet` block from Terminal
paths and stop, before any call. No marker: render `no setup yet` and stop.
Load the roster from `analysis-config.json` / `tiers.json` via the shared
loader (`_shared/lib/reel_io.load_config`). Read the journey file for `pulse`
(marker fallback per **State** above). Then route on what the user asked:

| Mode | The client says | Runs |
|---|---|---|
| pulse (default) | "run the weekly pulse", "run the pulse", "what changed this week", "refresh my competitor analysis" | Step 1, 7-day window |
| 14-day window | "run the pulse on 14 days" | Step 1 with the window set to 14 (`./references/modes.md`) |
| failed-only retry | "retry the failed handles" | `./references/modes.md`, the failed handles only, never the full pulse |
| roster ops | "manage my roster", "add <handle> to my roster", "swap a competitor", "backfill and re-analyze" | `./references/modes.md` |
| roster health | "roster health" | `./references/modes.md`, free, no paid call |
| field search | "search the field for <keyword>" | `./references/modes.md` |
| comment pulse | "comment pulse", "comment pulse on <url>", "mine the comments on <url>", "run audience questions" | `./references/modes.md` |
| schedule | "make the pulse weekly" | Schedule, below |

## Step 1 — Snapshot

No hand copy: the script owns the snapshot. Step 4's `analyze.py` copies the
`analysis-data.json` it is about to overwrite to
`history/analysis-data-<local date>.json` (a same-day rerun takes `-2`, `-3`; an
identical snapshot already in `history/` is reused, never duplicated). Until
Step 4 the live file IS that baseline, so Step 3 reads it. Dates
live in **filenames only** — the live JSON stays date-free so the deterministic
render contract holds. This snapshot is what "what changed" diffs against.

## ✋ Checkpoint P1 — price the listing pass

Balance first (0cr). Then state plainly:

> "Listing pass = (N roster + client) × 1cr + 1cr client profile ≈ **(N+2)cr**,
> plus 1cr per further page a handle needs to cover the window.
> Balance M → ≈ M−(N+2) after. Go?"

**Pause.** Nothing paid runs before this yes.

## Step 2 — Cheap listing pass (1cr legs only)

The window is computed, never guessed: `window_from` = the older of
`pulse.last_run` and today minus 7 days (minus 14 on "run the pulse on 14
days"), local dates; no `last_run`, today minus 7. The window is never under 7
days, and a 23-day gap is covered in full. Say the window in the brief.

Execution rules: socialcrawl-superengine's `socialcrawl` skill when installed,
else `../socialcrawl/SKILL.md` and `../socialcrawl/references/instagram.md:126-131`.

- Client + each roster handle: `GET /v1/instagram/profile/reels?handle=…`
  (~12 reels, 1cr a page). Page on with `&max_id=<next_cursor>` until the oldest
  reel on the page is older than `window_from` or `next_cursor` is absent.
  Pinned reels (old ones shown first) never decide that stop. +1cr a page, say so.
- One `Idempotency-Key` per handle + window, suffixed per page
  (`pulse-<brand>-<handle>-<window_from>-p<n>`; one key reused with other params returns
  422), so a resumed run replays at 0cr within 24h and never re-bills. A 502/503
  retries once, key + `-r<local HHMMSS>` taken at the retry.
- **Failed handles.** A handle that still fails logs `<date> · probe-failed · @handle · <error> · window from <window_from>` in `refresh-log.md`, then gets one failed-handles-only pass before the Step 4 merge, keys suffixed `-r<local HHMMSS>` (`./references/modes.md`); a failure there logs again, a pull logs it as `probe-ok`, with no `<error>`. Still failing: the brief ends on F5. A handle whose newest probe line was `probe-failed` and pulls in the normal listing logs `probe-ok` the same way.
- Client `GET /v1/instagram/profile` (1cr) → refresh `client_followers` in the
  config if changed.
- **New reels** = items whose `post.url` is not already in `source/**/reels`
  JSONs, filtered by `published_at` to that window.
- Zero new reels anywhere → write `pulse.last_run` (today's local date), leave
  `pulse.last_snapshot` as it is (no re-analysis ran), THEN report the quiet
  week honestly and end on the `empty week` block (E16). A quiet week is a
  completed run: without that write the compass keeps ranking the pulse it just
  ran. Total spend stays the listing cost.

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
python ${CLAUDE_PLUGIN_ROOT}/skills/competitor-cross-reference/analyze.py <project_dir> --window-from <window_from>
```

Transcription model changed since the last run? Take the instrument delta first
(`./references/modes.md`).

## Step 5 — Delta + visuals

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/competitor-cross-reference/render_visuals.py <project_dir> \
       --prev <project_dir>/history/analysis-data-<last>.json --stamp "Week of <date>"
```

Regenerates `visuals/` + writes `visuals/whats-new.json`; archive a copy to
`history/whats-new-<date>.json`. `<project_dir>` is absolute (`state.project_path`); `<last>` is the snapshot Step 4 took. An
unreadable `--prev` stops the render (exit 1, nothing written): report it with
the path, fix the path, re-run this step.

## Step 6 — "What changed this week" brief

Present from `whats-new.json` + the listings just pulled — **every line cited**
(`@handle · metric · reel URL`):

- **Breakouts** from `analysis-data.json` `period_breakouts` (each with mult, hook line, link), never `whats-new.json` `new_outliers`, which is the all-time top-30 leaderboard
- **Hook movement** from `whats-new.json` `hook_moves[]`: field and client med-views old → new, each with its `field_n` / `client_n` (`[old, new]`); a client median whose new n is under 5 is marked thin
- **Coverage** (counts include the client): `meta.window_reels` reels in the window, `meta.window_reels_transcribed` transcribed; transcribed sample newest `meta.transcribed_newest_published_at`, median `meta.transcribed_median_published_at`; corpus `meta.transcript_coverage` beside it
- **Tier balance**: the loaded roster's count per tier vs the ~8/9/8 target roster mode declares (`./references/modes.md`), drift named
- **Cadence movement** (+ "posted K this week vs X/wk average" from the listing)
- **Client movement** (stats + reach-efficiency rank old → new)
- **Quiet accounts** (nothing new ≥14 days — roster-health candidates)
- **Failed**: handles still failing after the retry pass, named, with the partial-set caveat
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
- **Failed-only retry**: the F5 retry over the logged failed handles only. Ends on E14, or F5, or E24 when nothing is logged.

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

- Never use SocialCrawl `media/transcript` (10cr) — transcription is the free
  local chain, always.
- Shares data never enters `analysis-data.json` — the metrics engine's
  engagement definition stays regression-locked.
