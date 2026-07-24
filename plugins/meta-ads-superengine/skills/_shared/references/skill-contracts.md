# Skill contracts — all 27, 8 core fields (+ optional Brain row)

The design contract every SKILL.md implements. Fields: **Trigger** (canonical
phrases — quoted from `journey-map.md`, never redefined here) · **Prereqs**
(state keys; enforcement = edge E0) · **Inputs** · **Outputs** · **State**
(reads → writes, per the `state-schema.md` ownership table) · **Edges**
(in/out registry IDs) · **Teach hooks** (what `new` must gloss/explain beyond
the defaults) · **DoD** (the skill run is done when…). A **Brain** row appears
only on skills with a named trigger point (`vault-api.md` recipes).

Universal (not repeated below): read state + teach-level at start; write
`updated_at` + `completed_skills` + open/closed `open_loops` at end; every
terminal path ends with a Next-Moves block (`routing.md`); refusals route via
E0; canon is the veto layer; no unattributed stats in any output.

---

## Core (5)

### 1. meta-ads-start
- **Trigger:** journey-map roster.
- **Prereqs:** none.
- **Inputs:** `.superengine` marker (present?), state file (present?).
- **Outputs:** greeting + routing table (grouped skills, one line each) +
  compass pointer ("Lost? Say **what's next**") + canon-staleness banner when
  >90d (`canon.md`).
- **State:** reads marker + state → writes nothing (stateless-write, like
  next and guide).
- **Edges:** in: (entry) · out: E1 (first run → guide; setup when the opener
  signals existing ads), E2 (returning → next).
- **Teach hooks:** at `new`, the routing table carries one-line "what this
  gets you" per group, not per skill (don't wall-of-text the first screen).
- **DoD:** coach knows the three things they can say next; first-run coaches
  are pointed at guide, never at a bare list.

### 2. meta-ads-setup
- **Trigger:** roster. Chunked + resumable — re-entry says "we're N% through."
- **Prereqs:** none.
- **Inputs:** interview answers; existing marker/state if resuming.
- **Outputs:** (a) connections audit — Meta MCP, Brain key, socialcrawl
  key, GHL MCP, brand-brain, carousel-superengine: each ✅/⚠️ + what it
  unlocks + the fix (absent ≠ blocker, family law); (b) ads-history
  interview (Meta MCP connected → `currently_spending` cross-checked against a
  live ACTIVE read; all-paused corrects it to false and routes a relaunch,
  family law preserved); (c) business config; (d) teach calibration (2 questions
  when uncalibrated → `teach-level` + `tooling_level` on divergence, skipped
  with a one-line confirm when `teach-level` already exists; dual-write legacy).
- **State:** reads all → writes `.superengine` (marker, connections,
  active_brand, `tooling_level` when the axes diverge), `setup.*`,
  `offer_version` (stamped 0 explicitly at first capture; ++ on offer/price
  change), seeds `stage` from interview when confident.
- **Edges:** in: E1, E22, E0 (from any skill missing setup) · out: E3
  (minimal-viable → breakeven-math), E4 (paused), F5 (currently_spending →
  onramp: import history → stage-check, WITHOUT pausing anything live).
- **Teach hooks:** gloss "state file", "marker", "CRM"; explain WHY offer +
  price + spend are the only three hard requirements.
- **DoD:** minimal-viable-setup (offer + price + spend level) recorded, or an
  honest resumable stop with % + what's missing.

### 3. meta-ads-guide
- **Trigger:** roster.
- **Prereqs:** none.
- **Inputs:** state (to tailor the tour to what exists).
- **Outputs:** guided tour — the journey graph in plain English (the WHY of
  the order: math → funnel → creative → launch → wait → scale), then walks
  into setup or the first unmet step.
- **State:** reads → writes nothing.
- **Edges:** in: E1 · out: E22 (→ setup or first deliverable per state).
- **Teach hooks:** the tour IS the teach surface — at `pro` it compresses to
  a 10-line map.
- **DoD:** coach has seen the whole road once and is standing at their actual
  next step.

### 4. meta-ads-teach
- **Trigger:** roster (+ mid-session "plain" / "less hand-holding" handled
  in-place by any skill per `teach-mode.md`).
- **Prereqs:** none.
- **Inputs:** requested level or a calibration exchange.
- **Outputs:** confirmed level + what changes ("I'll stop glossing Meta terms
  you know").
- **State:** reads `teach-level` (+ marker `tooling_level`) → writes
  `~/.claude/revxl/teach-level` + legacy `teach-mode` dual-write +
  `state.teach_level` mirror + marker `tooling_level` when the axes split.
- **Edges:** in: any · out: E21 (back to what you were doing).
- **Teach hooks:** self-demonstrating — confirm in the NEW level's voice.
- **DoD:** both files written, change demonstrated, coach returned to work.

### 5. meta-ads-next
- **Trigger:** roster.
- **Prereqs:** none (empty state → "your journey starts at setup").
- **Inputs:** state + journey-map.
- **Outputs:** "you are here" (done / current / next rendered against the
  journey graph) + 2–4 ranked moves with why + trigger phrases; surfaces
  `open_loops` and stale gates (compliance older than offer_version; targets
  computed against an older offer_version).
- **State:** reads everything → writes nothing.
- **Edges:** in: E2, E15, E21, and every block's fallback · out: whatever the
  state says (it renders edges, it doesn't own one).
- **Teach hooks:** position phrased per level ("you've done the math and the
  funnel plan; creative is next" vs "post-foundations, pre-hub").
- **DoD:** ranked moves whose #1 is actionable RIGHT NOW with prereqs met.

---

## Strategy (7)

### 6. meta-ads-stage-check
- **Trigger:** roster.
- **Prereqs:** `setup.spend_level`.
- **Inputs:** spend level, kpi-log (if exists), exit-criteria evidence.
- **Outputs:** stage diagnosis (1–4) + posture card (structure, creative
  count, testing mode, automation posture, failure modes for THIS stage) +
  exit-criteria audit if the coach thinks they're ready to move.
- **State:** reads setup, kpi_log → writes `stage`.
- **Edges:** in: E5, F5 (onramp), E12-in · out: E12 (→ campaign-plan /
  scale-decision).
- **Teach hooks:** gloss "exit criteria"; the WHY of "stages advance on
  evidence, never impatience."
- **DoD:** `stage` written + the coach can say what has to be true before
  the next stage.
- **Brain:** stage recipe row (locked choice: diagnosed stage).

### 7. meta-ads-breakeven-math
- **Trigger:** roster.
- **Prereqs:** `setup.offer` + `setup.price` (0 is valid — free front end;
  requires `setup.backend_price`).
- **Inputs:** `funnel_type` (call vs checkout, decides which rates matter),
  `client_value` (`setup.price`, or `setup.backend_price` when price ≤ 0;
  monthly price × `avg_retention_months` for subscriptions), close rate, show
  rate, lead→call rate, qualification rate (raw lead → passes questions),
  `lead_to_purchase_rate` (checkout funnels), `avg_retention_months`
  (subscriptions), `gross_margin` (light-touch, asked only when real
  per-client delivery costs exist, else service default ~1.0) (pulls from
  setup; asks for missing; **sanity-checks** — a claimed 80% close rate gets
  challenged with the plain question "out of your last 10 calls, how many
  bought?").
- **Outputs:** affordable CPL / CPQL / cost-per-call, breakeven ROAS, budget
  floor (hard deck), the persisted `client_value` anchor, the
  `offer_version_used` stamp (which `offer_version` these targets ran against),
  margin-factor explanation — the numbers gate before $1 is spent. Artifact: the
  math shown, not just the answers.
- **State:** reads setup → writes `targets.*` (`targets_version`++),
  `targets.offer_version_used` (stamps the current `offer_version`),
  `targets.computed_at`.
- **Edges:** in: E3, F3 (re-run cascade), F4 (second total failure) · out:
  E5 · F6 (no-go: honest exit — the number that has to change, revisit
  offer/price in setup, or park ads).
- **Teach hooks:** gloss CPL/CPQL/breakeven ROAS/hard deck; the "expensive
  leads can be profitable" reframe; at `new`, walk the formula line by line.
- **DoD:** targets written with version bump, OR a no-go delivered with the
  specific blocking number — never a shrug.
- **Brain:** corroborating-pattern recipe (1 search, optional — a
  breakeven/CAC-tolerance pattern for the offer type).

### 8. meta-ads-funnel-qualify
- **Trigger:** roster.
- **Prereqs:** `targets` set.
- **Inputs:** offer, CRM (`setup.crm`), current funnel description.
- **Outputs:** qualification STRATEGY: what to gate on (informed by the real
  CPQL number), Conversion-Leads objective guidance, the qualified-event spec
  — fire server-side ONLY on qualified-yes. **GHL fast-path** when
  `setup.crm == "ghl"` (pipeline-stage CAPI pattern); otherwise a
  **CRM-neutral spec** artifact (event name, trigger condition, webhook
  shape) for Kajabi/ClickFunnels/anything.
- **State:** reads setup, targets → writes `funnel.*`.
- **Edges:** in: E5, F2 (junk-leads tighten) · out: E6 (→ lead-questions).
- **Teach hooks:** gloss "qualified event"; THE coach edge explained: "feed
  Meta raw leads, it finds tire-kickers; feed it qualified leads, it finds
  buyers" + the CPL-up/CPQL-down trade.
- **DoD:** `funnel.qualified_event` named + `funnel.qualification_gate` set
  (what a lead must clear — lead-questions' prereq) + wiring path chosen +
  spec artifact saved when CRM-neutral.
- **Brain:** funnel-event recipe row.

### 9. meta-ads-lead-questions
- **Trigger:** roster.
- **Prereqs:** `funnel.qualification_gate`.
- **Inputs:** the gate, targets (friction-vs-volume tuning),
  `setup.price`/`setup.backend_price` (what a client pays; `setup.price == 0`
  forks the gate ... soft readiness gate at the free opt-in, real money
  question deferred downstream), voc/ (voice), offer.
- **Outputs:** the actual form/quiz question set — money-gate forked on the
  front-end price: paid front end → filter-not-scare on the coach's real
  number; free / $0 front end → soft readiness gate at the opt-in (no dollar
  figure at the free door), the real money question placed downstream at the
  application before call booking; commitment/timeline question, pre-call
  intel that arms the close; count tuned friction-vs-quality; Instant Form vs
  external quiz mechanics.
- **State:** reads funnel, targets, voc, `voice_sketch` → writes
  `funnel.spec_artifact` addendum (question set path) + `voice_sketch` on F10
  capture.
- **Edges:** in: E6 · out: E7 (→ signal-setup). F10 if voc/ absent.
- **Teach hooks:** gloss Instant Form; why fewer/more questions trades
  volume for quality.
- **DoD:** a paste-ready question set artifact in the coach's voice.
- **Brain:** funnel-event / awareness recipe row (1 search, optional).

### 10. meta-ads-signal-setup
- **Trigger:** roster.
- **Prereqs:** `funnel.qualified_event`.
- **Inputs:** CRM, funnel spec, account access level.
- **Outputs:** destination fork first (no controlled page → Instant Forms
  instead of a Pixel, plus a **conditional** CAPI bridge ... offered only when
  the destination platform has a Zapier / Make trigger AND the coach will do
  the one-time builder-tool setup, labeled low-code not no-code; otherwise the
  qualified-event read runs through the weekly review's CRM cross-check); on a controlled page: Pixel + CAPI
  dual-tracking walkthrough with `event_id` dedup check, one-click CAPI (with
  the dedup-after caveat), AI-assisted-Pixel review (auto-ON, opt-out), EMQ
  direction (no fake decimals), **value-rules module** (Stage 2+: inject CRM
  knowledge as ±% bids — the S2 doctrine home). Live signal-health diagnostic
  when connected (`ads_get_datasets` freshness, `ads_get_dataset_quality`
  EMQ/coverage, `ads_get_dataset_stats` 28-day volume, `ads_get_customconversions`
  rules) — paste/screenshot verify stays first-class.
- **State:** reads funnel, setup → writes `signal.*`.
- **Edges:** in: E7, E16 (weak-signal diagnosis), F2 · out: E8
  (→ compliance-check).
- **Teach hooks:** gloss Pixel/CAPI/EMQ/dedup with the "browser half +
  server half" analogy; "what this means for you: Meta finds who you feed
  it."
- **DoD:** dual-tracking live (or an exact TODO list of the coach's clicks),
  dedup verified or flagged, `signal.checked_at` stamped.
- **Brain:** signal recipe row. Volatile domain — product-surface facts
  (button names, menu paths) live-checked regardless of canon.

### 11. meta-ads-compliance-check
- **Trigger:** roster. Sub-mode: **rejection-triage** (entered via F8).
- **Prereqs:** `setup.offer`.
- **Inputs:** the offer + its claims + landing page, per `offer_version`.
- **Outputs:** **live policy check** (never cache, never vault — canon rule
  2; via `ads_get_help_article` when the Meta MCP is connected, else
  WebFetch/WebSearch): Special Ad Categories incl. Financial Products &
  Services, AI-content labeling posture, claims review;
  pass/flagged/unverified verdict (unverified = live lookup unavailable,
  never a cached pass). Rejection-triage: diagnose rejection/restriction,
  appeal path, don't-make-it-worse warnings.
- **State:** reads setup → appends `compliance[]`
  `{offer_version, result, categories, constraints, checked_at}`.
- **Edges:** in: E8, E9-in, F8 (rejection) · out: E9 (pass) · F1 (fail →
  fix → re-run; LAUNCH stays blocked) · F11 (unverified → keep building,
  re-run when online).
- **Teach hooks:** gloss Special Ad Categories; "what this means for you: a
  financial-adjacent offer changes what targeting Meta allows you."
- **DoD:** a dated verdict row for the CURRENT offer_version, from live
  sources, incl. any creative constraints — with the LAUNCH gate consequence
  stated.
- **Brain:** NONE — hard-excluded (compliance never from the vault).

### 12. meta-ads-campaign-plan
- **Trigger:** roster.
- **Prereqs:** `targets` + `stage`.
- **Inputs:** stage, targets, creative registry (what exists), naming
  grammar.
- **Outputs:** stage-appropriate structure artifact: consolidated CBO, broad
  targeting (location/age-floor/language), automated bidding, names from
  `naming.md`, budget per targets, **per-concept asset-source lane**
  (`produced` / `upload` / `post-id` with Post ID) the launch-runbook reads;
  Stage 1 = one campaign, one ad set, 3–5 distinct concepts. **High-ticket
  branch ($10k+ offers):** the omnipresent warm-audience exception, alongside
  (never instead of) conversion campaigns.
- **State:** reads targets, stage, creatives → writes `campaign_plan` (path).
- **Edges:** in: E9, E12 · out: E13 (→ launch-runbook if gate met; else E0
  to the missing gate item).
- **Teach hooks:** gloss CBO/objective/broad; the WHY of "don't fight the
  defaults, inject knowledge."
- **DoD:** a plan artifact the launch-runbook can execute click-by-click —
  named objects, budgets, and the paused-first instruction.
- **Brain:** stage recipe rows (campaign structure rides on the stage posture).

---

## Creative (8)

### 13. meta-ads-creative-strategy — THE HUB
- **Trigger:** roster.
- **Prereqs:** `targets` (funnel recommended; reads voc/ — spec omission
  fixed).
- **Inputs:** offer, avatar (from voc-profile), stage (concept count), best-
  content + competitor-intel outputs when present, `compliance[]` constraints
  (current offer_version).
- **Outputs:** PDA matrix (Persona × Desire × Awareness) → 3–5 genuinely
  distinct concepts at S1 (8–20 at scale; stage unset → S1 count, labeled),
  format mix per stage, per-concept production routing (which production skill,
  which brief).
- **State:** reads targets, stage, voc, `voice_sketch`, creatives → appends
  `creatives[]` concept rows (id `cN` per naming grammar, status draft) +
  `voice_sketch` on F10 capture.
- **Edges:** in: E9, E16 (fatigue), E17, E18 (iterate), E19 (intel feeds),
  F4 (new batch) · out: E10 (→ production per format mix).
- **Teach hooks:** gloss PDA/awareness/distinct-concept with the "bundling"
  why: near-twins = one lottery ticket.
- **DoD:** concept rows in state, each with a one-line brief distinct on at
  least one PDA axis — no near-duplicates.
- **Brain:** awareness + format recipe rows (the hub is the heaviest Brain
  consumer).

### 14. meta-ads-hook-writer
- **Trigger:** roster.
- **Prereqs:** concept rows exist.
- **Inputs:** concept brief, voc/ (voice + customer language), hook-formula
  library (bundled ref, P3).
- **Outputs:** hooks per concept across formulas, on the avatar/offer, in
  the coach's voice; labeled h1/h2… (naming grammar — CT-Tool variant IDs).
- **State:** reads creatives, voc, `voice_sketch` → updates concept rows (hook
  inventory in the artifact, path on the row's `artifacts.hooks` key only) + `voice_sketch` on F10 capture.
- **Edges:** in: E10 · out: E11 (→ next asset / campaign-plan when count
  met). F10 voice cold-start.
- **Teach hooks:** gloss hook/hook-rate; why the hook is 80% of a video ad's
  job.
- **DoD:** hooks distinct per concept (not rephrasings), voice-matched or
  honestly labeled low-confidence.
- **Brain:** hook + awareness recipe rows.

### 15. meta-ads-ad-copy
- **Trigger:** roster.
- **Prereqs:** concept rows exist.
- **Inputs:** concept brief + hooks, voc/, copy-framework refs (P3),
  `compliance[]` constraints (current offer_version).
- **Outputs:** primary text + headlines per concept (PAS/BAB/SLAP/H-P-O-CTA),
  char limits enforced (125 visible / 40), AI-tells avoided, **5-slot
  variants inside one ad** (never 5 ads), zero unattributed stats, default
  CTA buttons + strong in-copy CTA.
- **State:** reads creatives, voc, `voice_sketch` → updates concept rows
  (artifact path on the row's `artifacts.copy` key only) + `voice_sketch` on F10 capture.
- **Edges:** in: E10, E11 · out: E11. F10.
- **Teach hooks:** gloss primary text/headline/5-slot; "the visible zone is
  the ad."
- **DoD:** paste-ready copy blocks per concept with slot variants, stripped
  of every number that lacks a source.
- **Brain:** format (copy) + awareness recipe rows.

### 16. meta-ads-static-ads
- **Trigger:** roster.
- **Prereqs:** concept rows exist.
- **Inputs:** concept brief + copy, brand look (voc/ or asked), stage,
  `compliance[]` constraints (current offer_version).
- **Outputs:** static layouts — patterns, safe zones **14/35/6**, 4:5 specs,
  long-copy statics as the cold-traffic engine, designed AND plain styles
  (Andromeda format-personalizes). Design directions executable in Canva;
  optional FAL renderer = P5 (named here, not wired). Before/after imagery is
  three-state gated on the current-offer_version constraint: banned → blocked;
  unknown (no current-version entry) → flag for the compliance gate; clear →
  proceed.
- **State:** reads creatives, voc, `voice_sketch` → updates concept rows
  (artifact path on the row's `artifacts.static` key only) + `voice_sketch` on F10 capture.
- **Edges:** in: E10, E11 · out: E11. F10 voice cold-start. Boundary:
  slide/carousel production → carousel-superengine when installed (one
  pointer line, no dupe).
- **Teach hooks:** gloss safe zones/4:5; why long-copy statics work on cold
  coaching traffic.
- **DoD:** per-concept design directions a non-designer can execute, safe
  zones respected, before/after offered only when the current-offer_version
  constraint permits it.
- **Brain:** format (static) recipe row.

### 17. meta-ads-video-script
- **Trigger:** roster.
- **Prereqs:** concept rows exist.
- **Inputs:** concept brief + hooks, voc/, format pick (talking-head / UGC /
  VSL), `compliance[]` constraints (current offer_version).
- **Outputs:** scripts at bipolar lengths (15–30s direct AND 90–120s+ VSL,
  CTA past ~1:15), teleprompter formatting, voice-matched; AI-avatar caveat
  (C2PA auto-labeling + trust cost). Higgsfield directors = optional-tools
  appendix (requires MCP; P3).
- **State:** reads creatives, voc, `voice_sketch` → updates concept rows
  (artifact path on the row's `artifacts.script` key only) + `voice_sketch` on F10 capture.
- **Edges:** in: E10, E11 · out: E11. F10. Boundary: paid-native only
  (VSL/offer-CTA) — organic reels belong to shortform-superengine; Post-ID
  bridges the two.
- **Teach hooks:** gloss VSL/UGC/talking-head; why one-size 30s scripts are
  legacy.
- **DoD:** shootable scripts (word-for-word + direction lines) per video
  concept.
- **Brain:** format (video/vsl) recipe row.

### 18. meta-ads-creative-test
- **Trigger:** roster.
- **Prereqs:** `creatives[].live_at` (something is actually running).
- **Inputs:** live creatives + their clocks, kpi data, stage.
- **Outputs:** stage-mapped test verdicts + next test design: **dimensional
  swings only** as separate ads; micro-variants exclusively via Meta's
  native CT Tool (≤5, Highest-Volume caveat); **dual-clock** (48–72h
  fast-kill / 7–10d judgment, computed from `live_at`);
  replicate→iterate→net-new priority; **S3 pack protocol** (dated ad-set
  min-spend pattern) when new ads starve; **20% testing-budget guardrail**.
  **Mandatory pre-kill check:** never kill a high-spend low-ROAS ad while
  overall KPI holds (last-click exception — check assist behavior first).
- **State:** reads creatives, kpi_log, stage → updates `creatives[].status`
  (killed/winner), kill/win dates.
- **Edges:** in: roster (post-launch, once `creatives[].live_at` exists;
  reached over time after E14) · out: E18 (→ creative-strategy iterate /
  production replace). F4 on total failure.
- **Teach hooks:** gloss dimensional swing/CT Tool/dual clock; the
  do-not-edit-winners why (learning resets).
- **DoD:** every live creative has a clock-aware verdict (keep / kill /
  too-early-say-when) + the pre-kill check evidenced.
- **Brain:** ops-verdict recipe row.

### 19. meta-ads-competitor-intel — roster builder + first scan
- **Trigger:** roster.
- **Prereqs:** own PDA exists (`creative-strategy` completed) — **never
  offered before** (gate row).
- **Inputs:** niche + competitor names/handles; `ads_library_search` when the
  Meta MCP is connected (page_ids-scoped per competitor; term-search for
  discovery **with the mandatory relevance post-filter** — drop non-niche
  pages, wrong-market currencies); manual Ad Library paste-capture when
  unconnected (first-class ... paste each page's Ad Library URL for its
  `page_id` via `view_all_page_id`, then Library ID + started-running date +
  headline per notable ad; longevity ladder labeled "partial (manual
  capture)", uncapturable fields stay null); shortform competitor roster
  (detect-first, seed offer);
  socialcrawl (✋ credit-gated enhancement, no longer the depth path).
- **Outputs:** (a) the tracked roster written to `competitors[]` (3–8 pages);
  (b) seeded `ad-observations.json` first rows; (c) the longevity ladder table
  (per page: active count, total ever, oldest-active run-length, tier flags);
  (d) top angle candidates from `ad_creative_link_title` mapped to PDA cells.
  Guardrails IN the output: mine ANGLES not structure; never clone 8-figure
  brands; model brands 1–2 steps bigger. Tier-2 teardown offer (✋ effort gate:
  opening each ad in a logged-in browser + a structured read) on ads ≥6mo and
  notable 30/60d newcomers → `teardown_artifact` path per observation row.
- **State:** reads setup, creatives → writes `competitors[]`, seeds
  `ad-observations.json`; open_loop "feed intel to creative-strategy".
- **Edges:** in: E10-adjacent (hub offers it) · out: E19 (→ hub, only
  consumer).
- **Teach hooks:** gloss Ad Library; why 6-months-running = proven spend; the
  ladder tiers always labeled corpus (30d Cockpit / 6mo+ staged-framework) vs
  house (60d interpolated).
- **DoD:** roster written + ladder delivered + angle inventory routed into the
  hub; competitor snapshot teardowns are browser-gated (403 anonymously);
  credits spent only after ✋ approval.
- **Brain:** none (this skill mines the MARKET, not the vault).

### 20. meta-ads-best-content
- **Trigger:** roster.
- **Prereqs:** `setup` done (+ history imports or profile handles).
- **Inputs:** `state/<brand>/history/`, inline-paste of past-ad numbers
  (name, spend, results, cost/result ... filed into `history/`), organic
  profiles. **Reuses shortform
  `analysis-data.json` first** when that plugin is installed — crawl (✋
  credit-gated) only for what's missing.
- **Outputs:** own-winner analysis: what worked organically/in past ads →
  what to replicate into paid (founder-face default). Post-ID synergy note
  (run winners as ads keeping social proof — executed in launch-runbook).
- **State:** reads setup, history → artifact + open_loop to the hub.
- **Edges:** in: E10-adjacent (hub offers it); roster · out: E19 (→ hub).
- **Teach hooks:** gloss Post-ID; "your best organic Reel + a 5–10s CTA is
  a free ad."
- **DoD:** a ranked replicate-list from the coach's OWN material, no crawl
  without approval.

---

## Launch (1)

### 21. meta-ads-launch-runbook
- **Trigger:** roster.
- **Prereqs:** **THE GATE** — `campaign_plan` + `compliance[]` pass @ current
  `offer_version` + `funnel.qualified_event`. Missing → E0 with the exact
  missing item.
- **Inputs:** the campaign-plan artifact, produced creatives, Ads Manager
  (coach's hands or MCP later).
- **Outputs:** guided click-path: build **paused** (campaign → ad set → ads,
  names verbatim from the plan) → verify (objective, budget, broad settings,
  enhancement rules per canon, 5-slot copy in place, Post-ID where applicable)
  → publish → the 72h speech. Writes the go-live facts.
- **State:** reads campaign_plan, creatives (visual `artifacts.static` / `artifacts.script` kinds for the visual-asset check; a legacy `artifact` string is kind-unverifiable, ask the coach), compliance, funnel → writes
  `launched_at` (native writer; performance-review import backfill is the
  sanctioned exception — state-schema rule 5; a re-activation re-stamps a fresh
  `launched_at` with `launched_at_source: "reactivation"`, same native writer),
  `creatives[].live_at`, status launched.
- **Edges:** in: E13 · out: E14 (→ daily-brief tomorrow + kpi baseline). F8
  (rejection at publish → compliance rejection-triage).
- **Teach hooks:** every Ads Manager screen glossed at `new` ("this toggle
  is X, leave it because Y"); the paused-first why.
- **DoD:** a PUBLISHED campaign + `launched_at` AND `creatives[].live_at`
  written — the journey's keystone timestamps — or a precise stop-point
  (which screen, which blocker).

---

## Ops (5)

### 22. meta-ads-ops-setup
- **Trigger:** roster.
- **Prereqs:** `setup` done.
- **Inputs:** platform (Desktop/Code), account access.
- **Outputs:** Cockpit hookup — **client path:** hosted official Meta MCP
  (`mcp.facebook.com/ads`, OAuth in Claude Desktop; connector grants the full
  tool surface — no read-only scope exists) — consumer-doable; **operator
  path:** official CLI (System User token), Joe-assisted. Write-safety =
  server-side per-account "Actions allowed" + behavioral read-only.
  Manual-paste stays first-class regardless. When write access lands
  (NTB-10): paused-first + confirm-every-write doctrine, inherited NOW.
- **State:** reads marker → updates `.superengine` connections.
- **Edges:** in: setup audit offer; roster ("connect ads manager", often
  after paste friction) · out: E20.
- **Teach hooks:** gloss MCP/OAuth/scope; "read-only means it can look, not
  touch."
- **DoD:** connection state honestly recorded; zero write tools invoked in
  v1; Actions-allowed verified per account.

### 23. meta-ads-daily-brief
- **Trigger:** roster.
- **Prereqs:** `launched_at` (native or F5 import backfill).
- **Inputs:** today's numbers (paste/CSV first-class; live `ads_get_ad_entities`
  today+yesterday when connected), targets, stage, clocks;
  `ads_insights_anomaly_signal` as trusted-detection bad-day evidence;
  `delivery_sub_status` + `ads_account_get_activity_logs` (GATED on rollout,
  verified 07.22.26) detect-first when available.
- **Outputs:** the 60-second glance: pacing, CPL vs target, fatigue flags
  (storytelling metrics as WHY only). **Stage 1 = READ-ONLY:** shows numbers
  then actively talks the coach OUT of touching anything inside 72h /
  early-stage windows (the lockout speech, computed from `launched_at`).
  Optimization actions unlock Stage 2+. **No-launch block is state-gated:** an
  empty-import `last_review` routes a relaunch (never re-offers the empty
  import); launch is offered only when the LAUNCH gate is met, else the missing
  gate piece is named (E0).
- **State:** reads targets, stage, launched_at, kpi_log → writes
  `bad_day_counter` (increment/reset); invokes kpi-tracker for the log row.
- **Edges:** in: E14 (+daily) · out: E15 · F7 (3 bad days →
  performance-review, mandatory before any cut, hard-deck floor) · F8
  (restriction noticed).
- **Teach hooks:** the 72h/learning-reset why is THE teach moment; gloss
  learning phase.
- **DoD:** glance delivered; zero optimization prescribed at S1; counter
  accurate.

### 24. meta-ads-kpi-tracker
- **Trigger:** roster ("show my trends") — otherwise invoked BY brief/review
  (the data layer, deliberately thin).
- **Prereqs:** `targets`.
- **Inputs:** pulls, review-window or daily-brief `window_days: 1` (paste/CSV
  first-class; live `ads_get_ad_entities`
  at the row's `window_days`, `source:"mcp"`, field-validated via
  `ads_get_field_context` when connected).
- **Outputs:** appended `kpi-log.json` row (schema in `metrics.md`) + trend
  render vs exit criteria, verdicts stamped `targets_version`.
- **State:** reads targets → writes kpi-log.json + `kpi_log` pointer.
- **Edges:** in: E14 (baseline), invoked-by · out: E23 (back to caller /
  scale-decision when exit criteria trend met).
- **Teach hooks:** gloss exit criteria; primary-vs-storytelling in one line.
- **DoD:** the log row exists and the trend answer is evidence, not vibes.

### 25. meta-ads-performance-review
- **Trigger:** roster. Modes: **week-1** (post-launch, gentler bars, computed
  from `launched_at`) · standard weekly · **monthly backend audit** (MER,
  nCAC, new-vs-returning — the cannibalization catch) · **import mode** (F5
  onramp: diagnose a running account from exports; backfills `launched_at`
  from evidence, currently-delivering campaigns only (state-schema rule 5),
  stamping `launched_at_source: "import"`; an import that parsed but found
  nothing delivering ends at a dedicated empty-import terminal, no re-offer).
- **Prereqs:** `launched_at` OR import mode.
- **Inputs:** pulled data (manual-paste/CSV first-class; live per-ad
  `ads_get_ad_entities` when connected), CRM reality (booked calls + closes
  where a call funnel + CRM exist; else the coach's own conversion tally,
  first-class → `conversions_manual` on the kpi row), kpi-log;
  `ads_insights_anomaly_signal` (trusted-detection evidence, never a
  direct kill) + `ads_insights_performance_trend` / industry+auction benchmarks
  / `ads_insights_advertiser_context` as storytelling context when connected.
- **Outputs:** diagnosis vs stage framework → **ROUTES to the fix**, never
  just reports: fatigue → creative-strategy · weak signal → signal-setup ·
  junk leads (CRM disagrees with Meta) → funnel-qualify · exit criteria met →
  scale-decision · actuals ≠ assumptions → breakeven-math re-run. Enforces
  stage wait-windows. **Pre-kill check** (last-click exception) before any
  kill recommendation. Parses names per `naming.md`.
- **State:** reads everything → writes `last_review` (the empty-import verdict
  when an import parsed but nothing is currently delivering; `targets_version_used`
  only when `targets` exist) (+ `launched_at`, `launched_at_source` in import
  mode when a currently-delivering start date is derivable); invokes
  kpi-tracker.
- **Edges:** in: E15 (review day), F7 · out: E16 (the diagnosed fix), F2,
  F3.
- **Teach hooks:** gloss MER/nCAC at monthly mode; "your CRM is the truth,
  Meta is the claim."
- **DoD:** one primary diagnosis + one routed fix with its trigger phrase —
  not a metrics dump. Import mode additionally backfills `launched_at` from
  evidence when a campaign start date is derivable (else says so, no backfill).
- **Brain:** ops-verdict recipe row.

### 26. meta-ads-scale-decision
- **Trigger:** roster.
- **Prereqs:** `kpi_log` evidence (refuses on vibes — gate row).
- **Inputs:** kpi-log trends, stage, targets (+ hard deck), 20% guardrail
  status; live `ads_get_ad_entities` (last_14d/30d) cross-check +
  `ads_insights_performance_trend` corroboration +
  `ads_insights_auction_ranking_benchmarks` in the ceiling diagnosis when
  connected — log stays authoritative.
- **Outputs:** stage-exit audit (criteria met? evidence shown) →
  raise-in-place instruction (≤20% / 48–72h, wobble warning, never
  duplicate-to-scale) OR hold verdict with the missing evidence named.
  Checks the **testing-budget guardrail** (~20% to new concepts). Stage 4:
  cost-cap circuit breaker + backend north-star handoff.
- **State:** reads kpi_log, stage, targets → writes stage (on advance),
  open_loop for the post-raise check date.
- **Edges:** in: E16, E23, E12 · out: E17 (raise + cadence) · F3 (actuals
  diverge → re-math first).
- **Teach hooks:** gloss raise-in-place/duplicate-to-scale/wobble; "a raise
  is a bet the 7-day average confirms."
- **DoD:** a go/hold verdict citing specific kpi-log rows, with the next
  check date on the calendar (open_loop).
- **Brain:** ops-verdict (scaling) recipe row.

---

## Creative — competitor subsystem (1)

### 27. meta-ads-competitor-pulse — the weekly delta
- **Trigger:** roster.
- **Prereqs:** `competitors[]` non-empty (empty → E0 to competitor-intel,
  "build your roster first" — which transitively enforces the PDA gate).
- **Inputs:** `competitors[]`, the `ad-observations.json` sidecar + its last
  `competitor-history/` snapshot, `ads_library_search` (page_ids-scoped per
  roster page; ACTIVE pull + status counts), the PDA matrix (angle mapping).
- **Outputs:** a snapshot-before-refresh of observations → per-page ACTIVE
  pull → inline diff vs stored observations: **NEW** ads (`first_seen`=today),
  **DISAPPEARED** (was active, now absent/inactive), **TIER PROMOTIONS**
  (run-length crossed 30/60/180d) → the "what changed" brief, every line
  cited (`page_name` · ad id · run-length). Teardown nominations on any 6mo+
  promotion (✋ effort gate, same as intel). Roster ops (add/remove/swap) on
  request. Empty-week honest variant when nothing moved.
- **State:** reads `competitors[]`, `ad-observations.json` → writes updated
  observations (update-on-match by `ad_id`, append-on-new, never delete; a
  remove retires rows), a `competitor-history/` snapshot, optional
  `.superengine` `competitor_pulse` scheduling block; `competitors[]` on a
  roster op.
- **Edges:** in: E19-adjacent (offered once a roster exists); roster · out:
  E24 (→ creative-strategy primary · teardown offer · roster ops · back to
  caller). E0 on empty roster.
- **Teach hooks:** at `new`, deep-gloss the ladder ("an ad running six months
  is spending money on purpose — that's proof it works"); `learning`
  one-liners; `pro` terse. Tiers always labeled corpus vs house.
- **DoD:** a cited delta brief (or an honest empty-week report) + observations
  updated + a history snapshot written; scheduled runs still stop at the ✋
  effort gate.
- **Brain:** none (market mining, not the vault — same exclusion as intel).
