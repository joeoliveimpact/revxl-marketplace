---
name: meta-ads-superengine:meta-ads-competitor-pulse
description: Weekly competitor delta — snapshots the roster's Ad Library pull, diffs against stored observations, and reports what changed (new ads, disappearances, longevity promotions) with every line cited. Also handles roster ops (add or remove a competitor). Requires a roster built by competitor-intel first. Trigger phrases include "competitor pulse", "what changed in my niche", "add a competitor", "remove a competitor".
---

# meta-ads-competitor-pulse — the weekly delta

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #27.
One-shot searches structurally can't see longevity (the Ad Library returns
newest-first, no history). A persistent roster with weekly pulses measures it
as a by-product: an ad seen in week 1 and still delivering in week 9 has a
proven 60-day run. This skill is that pulse.

## Load
- shared refs
- Active brand state → `competitors` (the roster), the `ad-observations.json`
  sidecar + the latest `competitor-history/` snapshot
- Meta MCP connected? (`ads_library_search` — the scan tool; manual Ad Library
  browsing is the honest fallback)
- `.superengine` marker → `competitor_pulse` block (scheduled?)

## Prereq (E0)
`competitors[]` non-empty. Missing → refuse + route: *"There's no roster to
pulse yet — competitor-intel builds it (and it needs your own creative matrix
first). Build your roster first."* → Say: "competitor ads". (This transitively
enforces the PDA gate — no roster exists without intel, and intel refuses
without the coach's own matrix.)

## Empirical reality (locked — same probes as intel)
`ads_library_search` returns per ad only `id`, `page_id`/`page_name`,
`ad_creative_link_title`, `ad_creation_time`, `ad_delivery_start_time`
(longevity anchor), `ad_snapshot_url`, `currency`. The ACTIVE bucket per page
is small (usually <50 → one `limit: 50` pull retrieves it). Run-length =
today − `ad_delivery_start_time` on a still-ACTIVE ad. Competitor snapshot
URLs are 403 anonymously — teardowns are browser-gated.

## Flow

**1. Snapshot before refresh.** Copy the current `ad-observations.json` →
`competitor-history/ad-observations-<YYYY-MM-DD>.json` (create the dir if
absent). Dates live in **filenames only** — the live sidecar stays date-free.
This snapshot is what the diff runs against.

**2. Pull, per roster page.** `ads_library_search` page_ids-scoped (ACTIVE
pull, `limit: 50`) + status counts. Unconnected → the coach reads each page in
the Ad Library by hand; same diff, done from what they report.

**3. Inline diff vs stored observations** (Claude computes it — no script):
- **NEW ad** — `ad_id` not in observations → `first_seen` = today.
- **DISAPPEARED** — a previously-ACTIVE observation `ad_id` now absent from the
  pull or returning INACTIVE → "they killed it or it finished — note what it
  was" (keep the row, move `status_at_last_seen`).
- **TIER PROMOTION** — a still-ACTIVE ad whose run-length just crossed 30 / 60
  / 180 days → bump `tier` (`new`→`30d`→`60d`→`6mo+`).

**4. Update observations** — update-on-match by `ad_id` (`last_seen`,
`status_at_last_seen`, `tier` move), append-on-new, **never delete**.

**5. Render the "what changed" brief.** Every line cited (`page_name` · ad id
· run-length):
- **New angles** — new `ad_creative_link_title`s vs the PDA matrix (which cell
  they validate / add).
- **Promotions** — *"this ad just hit 60 days — they keep paying for it."*
- **Disappearances** — what died, and how long it had run.
- **Intensity shifts** — active-count deltas per page vs the snapshot.

### The tier ladder (label corpus vs house every time)
- **30d = good** — a month of consistent spend (Cockpit signal). *Corpus.*
- **60d = great** — house heuristic, interpolated. *House.*
- **6mo+ = MUST-STUDY, proven spend** — staged-framework canon. *Corpus.*

**6. Teardown nominations.** Any promotion INTO 6mo+ earns a teardown offer —
the **same ✋ EFFORT gate as intel** (consent, not credits): *"Each teardown =
opening the ad in your logged-in browser + a structured read of length,
caption, layout, script framework — worth it for the N nominated ads?"* On
yes → open `ad_snapshot_url` → structured teardown → record the
`teardown_artifact` path on the row.

## Roster ops (add / remove / swap)
- **Add** — resolve the named handle/page to a `page_id` (a library term-search
  on the name when connected; unconnected, the coach pastes the page's Ad
  Library URL and the `view_all_page_id` value is the id ... same capture as
  competitor-intel's paste lane), append to `competitors[]` (`source: "manual"`), note the target
  is 3–8 pages and warn on imbalance; the next pulse picks it up (or offer a
  scan now).
- **Remove** — drop the page from `competitors[]` AND **retire, don't delete**:
  set that page's observation rows to `status_at_last_seen: "retired"`. Retired
  data is recoverable; nothing is erased.
- **Swap** = remove + add in one confirmation.
- Log every op as one line inside the brief (op · page · why).

## Cadence — the weekly schedule offer (offer once)
Only if the `.superengine` `competitor_pulse` block shows no schedule, offer
ONCE per session: *"Want this weekly? A Monday-morning read before you plan
creative, or a slot you pick."* On yes, record the block additively in
`.superengine`: `{scheduled, cadence, runtime, last_run}`
(**Cowork** → a scheduled task; **Claude Code** → `/schedule`, cron, or Task
Scheduler). **A scheduled run still stops at the ✋ effort gate** — the schedule
wakes the pulse; it never opens teardowns by itself. Declines are respected —
log it, don't re-offer this session.

## Terminal paths — inline blocks (routing.md grammar)

**Delta delivered (E24):** preamble = the "what changed" brief (or the roster
op that just ran), then:

**Next moves**
1. Fold the movement into your creative plan — a promoted or new angle maps to the matrix. Say: "creative strategy"  ← start here
2. *If any ad was promoted into 6mo+:* tear down the proven ones — opening each in your logged-in browser. Say: "competitor pulse"
3. *If the roster needs a change:* add or drop a competitor. Say: "add a competitor"
4. See where this sits on the whole journey. Say: "what's next"

**Next moves — empty week (nothing moved)**
Nothing changed — no new ads, no promotions, no disappearances. Honest quiet week:
1. Fold what's already tracked into the plan — the standing roster still feeds angles. Say: "creative strategy"
2. Adjust the roster if it feels thin or stale. Say: "add a competitor"
3. *If not already scheduled:* want this weekly so movement lands on your desk automatically? Say: "competitor pulse"

**Next moves — after a roster op**
1. Run a pulse now to see the field with the new roster. Say: "competitor pulse"
2. Leave it — the next scheduled pulse folds the change in.
3. Fold the current angles into your plan. Say: "creative strategy"

## Teach mode
In `new`: deep-gloss the ladder ("an ad running six months is spending money
on purpose — that's proof it works"), each tier labeled corpus vs house; gloss
"Ad Library" and "run-length" on first use; "what this means for you" on a
disappearance ("they stopped paying for it — that angle may be cooling").
`learning`: one-liner tiers. `pro`: cited delta table, terse.

## Guardrails
- E0 is hard — no roster, no pulse (routes to intel, which enforces the PDA
  gate).
- Every brief line is cited (`page_name` · ad id · run-length) — no vibes.
- Observations are **append-only** — update-on-match, retire-on-remove, never
  delete.
- The teardown ✋ is EFFORT (consent), not credits; SocialCrawl (if ever used)
  is a separate ✋ credit gate with the cost named.
- Competitor snapshot URLs are browser-gated (403 anonymously) — never claim a
  teardown from a raw fetch.
- No Brain step (market mining, not the vault).
