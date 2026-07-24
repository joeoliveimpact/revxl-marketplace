# State schema — `state/<brand>.json`

The single per-brand journey record. **Every skill reads it at start and writes
its declared keys at end** — nothing else in the plugin persists journey
position. Routing (`journey-map.md` + `routing.md`) is computed FROM this file;
if a fact isn't in state, the router doesn't know it.

**Rule zero: no invented keys.** A skill may only write keys this schema
declares for it (see the ownership table). Need a new key? Add it HERE first
(additive minor bump), then write it. Unknown keys found in a file are
preserved untouched — never deleted, never "cleaned up."

## Locations

| Path | What |
|---|---|
| `~/.claude/meta-ads-superengine/.superengine` | Install marker (JSON): `installed_at`, `connections` audit results, `active_brand` slug, optional `marker_version` (mirrors current `schema_version`; absent = legacy) |
| `~/.claude/meta-ads-superengine/state/<brand>.json` | THIS schema — per-brand journey state |
| `~/.claude/meta-ads-superengine/state/<brand>/history/` | Imported Ads-Manager exports, past winners (raw files) |
| `~/.claude/meta-ads-superengine/state/<brand>/kpi-log.json` | Append-only KPI log (owned by kpi-tracker; see `metrics.md`) |
| `~/.claude/meta-ads-superengine/state/<brand>/ad-observations.json` | Append-only competitor-ad observation log (owned by competitor-pulse; intel seeds first rows; see Competitor sidecars below) |
| `~/.claude/meta-ads-superengine/state/<brand>/competitor-history/` | Date-suffixed snapshots of `ad-observations.json` — pulse writes one per run (shortform snapshot-before-refresh pattern) |

`<brand>` = normalized brand slug, **same convention as brand-brain**
(`~/.claude/revxl/<brand>/voc/`): lowercase, spaces→hyphens, strip punctuation.
One coach = usually one brand; agencies/multi-offer = N files, fully isolated.

## Schema (version 1.2)

```jsonc
{
  "schema_version": "1.2",          // additive-minor: new optional keys bump 1.x; never remove/rename in 1.x
  "brand": "<slug>",
  "created_at": "YYYY-MM-DD",
  "updated_at": "YYYY-MM-DD",       // every writer refreshes this

  // ---- setup (owner: setup) ----
  "setup": {
    "complete_pct": 0,              // resumable interview progress
    "offer": null,                  // string — what's sold (minimal-viable field 1)
    "price": null,                  // number USD (minimal-viable field 2)
    "backend_price": null,          // OPTIONAL number USD — backend/client value for free or low-ticket front ends; breakeven anchors on this when price is 0
    "spend_level": null,            // number USD/day, current or planned (minimal-viable field 3)
    "close_rate": null,             // booked call → client, 0–1 (sanity-checked by breakeven-math)
    "show_rate": null,              // booked → showed, 0–1
    "lead_to_call_rate": null,      // qualified lead → booked call, 0–1
    "lead_to_qualified_rate": null, // raw lead → passes qualifying questions, 0–1 (fills targets.cpl; breakeven-math sanity-checks)
    "funnel_type": null,            // "call" | "checkout" — does a sales call sit between lead and purchase?
    "avg_retention_months": null,   // OPTIONAL — subscription offers only; client_value = monthly price × this (LTV)
    "lead_to_purchase_rate": null,  // OPTIONAL, checkout funnels — lead → buyer, 0–1; skip freely, targets.cpl stays null until real data
    "gross_margin": null,           // OPTIONAL 0–1 — solicited only when real per-client delivery costs exist; null = service assumption (~1.0)
    "crm": null,                    // "ghl" | "kajabi" | "clickfunnels" | "other:<name>" | "none"
    "ran_ads_before": null,         // true/false + free-text "what happened" in history_note
    "history_note": null,
    "currently_spending": null      // true = already-running onramp (import, don't pause)
  },

  // ---- journey position ----
  "stage": null,                    // 1|2|3|4 — spend stage (owner: stage-check; setup may seed; scale-decision on advance)
  "teach_level": null,              // mirror of ~/.claude/revxl/teach-level at last read (convenience, not authority)
  "completed_skills": [],           // append skill name on every completed run (owner: every skill)
  "open_loops": [],                 // [{skill, note, opened}] — unfinished business the compass surfaces
  "declined_offers": [],            // [{offer, date}] — offer-once discipline; never re-offer this session/journey
  "voice_sketch": null,             // {answers, captured_at} — 3-question inline register capture; written by any F10 consumer on capture; voc/ presence supersedes it

  // ---- targets (owner: breakeven-math) ----
  "targets": {
    "cpl": null,                    // affordable cost per lead
    "cpql": null,                   // affordable cost per QUALIFIED lead
    "cost_per_call": null,
    "breakeven_roas": null,
    "hard_deck": null,              // budget floor — bad-day protocol never cuts below this
    "client_value": null,           // the anchor breakeven-math computed (incl. LTV when subscription) — persisted so re-runs are reproducible
    "targets_version": 0,           // ++ on every re-run; consumers stamp the version they used
    "offer_version_used": null,     // which offer_version these targets were computed against (breakeven-math stamps it; meta-ads-next flags a mismatch as stale math)
    "computed_at": null
  },
  "offer_version": 0,               // 0 = initial capture (setup stamps it explicitly at first write); ++ on every offer/price EDIT → invalidates targets + compliance. Consumers null-check, never falsy-check (0 is a valid value)

  // ---- funnel + signal (owners: funnel-qualify, signal-setup) ----
  "funnel": {
    "qualified_event": null,        // event name (e.g. "QualifiedLead") — null = LAUNCH-blocking
    "qualification_gate": null,     // what qualifies a lead (plain english)
    "wiring": null,                 // "ghl" | "crm-neutral-spec" | "pending"
    "spec_artifact": null           // path to the CRM-neutral event spec, if produced
  },
  "signal": {
    "pixel": null,                  // "live" | "pending" | null
    "capi": null,                   // "live" | "one-click" | "pending" | null
    "dedup_checked": null,          // event_id dedup verified true/false
    "checked_at": null
  },

  // ---- compliance (owner: compliance-check) — per-offer, live-checked ----
  "compliance": [
    // {"offer_version": 1, "result": "pass"|"flagged"|"unverified", "categories": [], "constraints": [], "checked_at": "YYYY-MM-DD"}
    // constraints = plain-language creative restrictions surfaced by the live check (e.g. "no before/after"); consumers read the entry matching CURRENT offer_version only
    // LAUNCH gate reads the entry matching CURRENT offer_version — stale pass ≠ pass
  ],

  // ---- launch + creative registry (owner: launch-runbook; creative skills append drafts) ----
  "launched_at": null,              // launch date — native writer launch-runbook, OR performance-review import mode (F5 backfill); unlocks daily-brief 72h lockout math
  "launched_at_source": null,       // OPTIONAL "runbook" | "import" | "reactivation" — absent = legacy = runbook
  "creatives": [
    // {"id": "c1", "concept": "<distinct concept>", "format": "static|video|ugc|vsl|carousel",
    //  "status": "draft"|"launched"|"killed"|"winner",
    //  "artifacts": {"hooks": null, "copy": null, "static": null, "script": null},  // per-kind path map — one key per producing skill (hook-writer→hooks, ad-copy→copy, static-ads→static, video-script→script); each key present only once its skill produces it, so two writers never collide. LEGACY: an older row's single "artifact": "<path>" string is preserved untouched (rule 0) and read as an artifact of unspecified kind
    //  "source": "produced"|"upload"|"post-id",  // OPTIONAL — asset origin (absent = produced)
    //  "post_id": null,                          // OPTIONAL string|null — set when source == "post-id"
    //  "live_at": null, "killed_at": null, "won_at": null}   — live_at written by launch-runbook (dual-clock source); killed_at/won_at written by creative-test on the kill/winner verdict
  ],
  "campaign_plan": null,            // path to campaign-plan's artifact (launch-runbook's input)

  // ---- competitor roster (owner: competitor-intel adds/removes; competitor-pulse reads) ----
  "competitors": [
    // {"page_id": "<meta page id>", "page_name": "<name>", "added_at": "YYYY-MM-DD",
    //  "source": "manual"|"shortform-seed"|"library-search"}
    // The tracked roster (3–8 pages). Ad-level observations live in the ad-observations.json
    // sidecar, NOT here. competitor-pulse's E0 prereq is this array non-empty.
  ],

  // ---- ops (owners: kpi-tracker, performance-review, scale-decision) ----
  "kpi_log": null,                  // pointer: "state/<brand>/kpi-log.json" once first entry exists
  "last_review": null,              // {"date", "verdict", "targets_version_used"}; verdict "imported-no-live" = import parsed but nothing currently delivering (read by daily-brief's no-launch block); targets_version_used present only when targets exist
  "bad_day_counter": 0              // daily-brief increments/resets; 3 → route performance-review
}
```

## Read/write contract

1. **Read at start** — every skill loads the active brand's file (create from
   the template above if absent) and re-reads `~/.claude/revxl/teach-level`.
2. **Write at end** — only your owned keys + always: `updated_at`,
   `completed_skills` append, any `open_loops` you opened/closed.
3. **Append, don't overwrite** arrays (`compliance`, `creatives`, `open_loops`).
4. **Version cascade:** changing `setup.offer` or `setup.price` bumps
   `offer_version` → routing treats `targets` and `compliance` for older
   versions as STALE (re-run required before LAUNCH).
5. **Never hand-write `launched_at`.** It is the keystone
   timestamp: daily-brief's 72h lockout, creative-test's dual clock, and
   performance-review's week-1 mode are all computed from it (and from
   per-creative `live_at`). Native writer = launch-runbook. **Sanctioned
   exception (F5 backfill):** performance-review import mode MAY backfill it
   from EVIDENCE — an imported export's campaign start date, or a live MCP
   read of real campaign start dates. **Backfill draws ONLY from campaigns that
   are CURRENTLY DELIVERING:** a live read must confirm `effective_status ==
   "ACTIVE"` before its `start_time` counts; a CSV or paste source must
   establish delivering status from its status column, and if delivering status
   cannot be established the backfill does not happen. Epoch or pre-2004 dates
   are API nulls, never launches. Never from coach say-so alone; it
   stamps `launched_at_source: "import"`. `0` is NOT a valid `launched_at`
   analog: the value must be a real date drawn from evidence.
6. Multi-brand: skills operate on `.superengine`→`active_brand`; switching
   brands = switching files, no shared state. **Brand-mention guard:** before
   any ops run (daily-brief, kpi-tracker, performance-review, scale-decision), a
   brand name in the coach's message that does not match `active_brand` STOPS
   the run ... offer the switch (setup's "switch brand" fast path), never
   silently report another brand's numbers.
7. **Schema-version bump on new keys:** any writer that adds a key introduced
   after the file's stamped `schema_version` also bumps `schema_version` to
   the current version — the file stays honest about the shape it holds.

## Ownership table (who writes what)

| Key | Writer(s) |
|---|---|
| `setup.*`, `offer_version` | setup (offer/price edits anywhere must route through setup) |
| `setup.close_rate`, `setup.show_rate`, `setup.lead_to_call_rate`, `setup.lead_to_qualified_rate`, `setup.lead_to_purchase_rate`, `setup.funnel_type`, `setup.avg_retention_months`, `setup.gross_margin` | setup (interview) · breakeven-math (sanctioned: persists the rates it gathers/sanity-checks when setup skipped them — so F3 has a baseline) |
| `stage` | stage-check (setup may seed from interview) · scale-decision (on a stage advance) |
| `targets.*` | breakeven-math only |
| `funnel.*` | funnel-qualify (lead-questions reads, writes `spec_artifact` addendum) |
| `signal.*` | signal-setup only |
| `compliance[]` | compliance-check only |
| `launched_at` (+`launched_at_source`), `creatives[].live_at` | launch-runbook (native; first publish writes `launched_at_source: "runbook"`, a re-activation re-stamps a fresh `launched_at` with `launched_at_source: "reactivation"`) · performance-review import mode (F5 backfill of `launched_at`, writes `launched_at_source: "import"`) |
| `creatives[]` (draft rows, incl. optional `source`/`post_id`); each producer writes ONLY its own `artifacts` key (hook-writer→`artifacts.hooks`, ad-copy→`artifacts.copy`, static-ads→`artifacts.static`, video-script→`artifacts.script`) — never another skill's key | creative production skills (hook-writer/ad-copy/static-ads/video-script via creative-strategy) |
| `voice_sketch` | voice-consuming skills (F10 capture): creative-strategy/hook-writer/ad-copy/static-ads/video-script + lead-questions |
| `creatives[].status`, `creatives[].killed_at`, `creatives[].won_at` | creative-test (kill/winner verdicts + their dates) |
| `teach_level` | every skill (mirror of `~/.claude/revxl/teach-level` at last read — convenience, not authority) |
| `campaign_plan` | campaign-plan only |
| `competitors[]` | competitor-intel (adds/removes) · competitor-pulse (roster ops: add/remove/swap; a remove retires the page's observation rows, never deletes) |
| `ad-observations.json` (sidecar), `competitor-history/` | competitor-pulse (native) · competitor-intel (seeds the first observation rows on the first scan) |
| `kpi_log`, kpi-log.json | kpi-tracker only |
| `last_review` | performance-review only |
| `bad_day_counter` | daily-brief only |
| `completed_skills`, `open_loops`, `declined_offers`, `updated_at` | every skill |

> **Marker (`.superengine`):** owned by setup — Section 0 writes `active_brand`
> (+ optional `marker_version`), Section D updates `installed_at`/`connections`.
> **`connections.brain_key` (optional):** the ask-once outcome so later trigger
> points stay silent ... `"ok <date>"` | `"declined <date>"` | `"server-401 <date>"`;
> absent = never asked (run the ladder). See `vault-api.md`.
> **`tooling_level` (optional):** the Claude/tooling-familiarity level
> (`new`/`learning`/`pro`) when it DIVERGES from the ads-familiarity `teach-level`;
> absent = the two axes match (today's behavior). See `teach-mode.md`.
> **Additive exception:** competitor-pulse may append one optional
> `competitor_pulse` scheduling block (`{scheduled, cadence, runtime, last_run}`)
> when the coach accepts the weekly-pulse offer — the marker is additive JSON;
> the block is absent until then.

## Competitor sidecars

Two competitor artifacts live outside `state/<brand>.json` (they grow per
observation, not per journey — same reason the KPI log is a sidecar):

**`ad-observations.json`** — append-only, owned by competitor-pulse (intel
seeds the first rows). One row per observed competitor ad:

```jsonc
{
  "schema_version": "1.0",
  "observations": [
    {
      "ad_id": "1392454146032870",     // Meta ad id — the update-on-match key
      "page_id": "<roster page id>",
      "delivery_start": "YYYY-MM-DD",   // from ad_delivery_start_time — the LONGEVITY anchor
      "link_title": "<ad_creative_link_title>",  // the ONLY creative text the search returns
      "first_seen": "YYYY-MM-DD",       // first pulse that saw this ad
      "last_seen": "YYYY-MM-DD",        // most recent pulse that saw it still delivering
      "status_at_last_seen": "active"|"inactive"|"retired",  // "retired" = its page was removed from the roster
      "tier": "new"|"30d"|"60d"|"6mo+",  // run-length ladder (see journey-map / the skills)
      "teardown_artifact": null          // path once a browser teardown is done, else null
    }
  ]
}
```

Rules: **update-on-match by `ad_id`** (`last_seen`, `status_at_last_seen`,
`tier` move as the ad ages / disappears), **append-on-new**, **never delete**.
Removing a page from the roster sets its rows' `status_at_last_seen` to
`"retired"` (retire, not delete — recoverable, mirrors the shortform pattern).
Competitor-intel's unconnected lane (manual paste capture) populates this SAME
shape from pasted Ad Library fields (`page_id` from the page URL's
`view_all_page_id`, `ad_id` = Library ID, `delivery_start` = started-running
date, `link_title` = headline); any field the UI doesn't expose stays `null`,
never guessed.

**`competitor-history/`** — a directory of date-suffixed snapshots of
`ad-observations.json` (`ad-observations-<YYYY-MM-DD>.json`), one written by
pulse at the top of each run before it mutates the live file. Dates live in
**filenames only**; the live sidecar stays date-free. This snapshot is what
"what changed" diffs against.

## Versioning

`schema_version` follows additive-minor: 1.x changes may ADD optional keys
only. Removing or renaming a key = 2.0 + a migration note in this file.
Skills tolerate missing optional keys (treat as null) — never crash on an
older file.
