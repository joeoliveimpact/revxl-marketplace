---
name: meta-ads-superengine:meta-ads-signal-setup
description: Sets up the tracking plumbing — browser Pixel plus server-side CAPI with event_id dedup, one-click CAPI, the AI-assisted-Pixel opt-out review, EMQ direction, and (from Stage 2) value rules that inject CRM knowledge Meta can't see. Trigger phrases include "set up tracking", "pixel and capi", "conversions api", "signal setup".
---

# meta-ads-signal-setup — the tracking plumbing

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #10.
Signal quality is the moat (framework 2.2). **Volatile domain** — product
surfaces (button names, menu paths) are live-checked regardless of canon age.

## Load
- shared refs + `vault-api.md`
- Active brand state → `funnel.qualified_event`, `setup.crm`, `stage`

## Prereq (E0)
`funnel.qualified_event` set. Missing → funnel-qualify.

## Steps

**0. Destination fork (ask FIRST, before any Pixel/CAPI prescription).**
"Where does the ad send people, and do you control that page?"
- **(a) You control it** (own site / funnel / landing page) → the Pixel + CAPI
  path (steps 1–5) applies as written.
- **(b) You don't** (Skool / Facebook group / Discord / a marketplace) → there
  is no page to install a Pixel on. Use **Meta Instant Forms** (native,
  pixel-free — the qualified-lead questions ride ON the form; see "write my
  lead questions"). Honest
  tradeoff: Instant Forms need no page and convert higher, but leads run
  lower-intent than a landing-page opt-in — the qualifying questions carry the
  filtering. **Skip steps 1–3** (no Pixel to place); pick up at EMQ (4).
  **Feeding the CRM's qualified-event back to Meta on this lane (conditional):**
  before offering a CAPI bridge, check live WITH the coach that the destination
  platform actually has a Zapier / Make trigger for the qualified event (open
  the app directory together ... Skool, for example, has none today). Trigger
  exists AND the coach is up for a one-time builder-tool setup → offer the
  bridge, labeled honestly as **low-code (one-time setup), not no-code**. No
  trigger, or the coach won't touch a builder tool → say plainly the automated
  feedback loop isn't available on this lane, and the qualified-event read runs
  through the weekly review's CRM cross-check instead (zero tooling, works
  today). Point at "review my ads".

**1. Dual tracking.** Walk Pixel (browser) + CAPI (server) with **`event_id`
dedup** — mismatched IDs double-count. CAPI at ALL spend levels (the $5k/mo
threshold is obsolete — canon: Signals).

**2. One-click CAPI** (Meta-hosted, real ~2026) — offer it as the no-dev
path; **caveat:** may not dedup against pre-existing custom server events →
check Events Manager for double-counting after enabling.

**3. AI-assisted Pixel review.** Auto-scrapes page/product metadata,
**auto-enables (opt-out)** — surface the setting on any account touched; the
coach decides.

**4. EMQ.** Maximize on the money event (hashed email = biggest lift, phone
w/ country code next). **Direction only — never chase specific decimals**
(canon: Signals). Complete signal volume beats a perfect score on fewer events.
**Volume-floor check (S1 budgets):** before locking the optimization event, do
the math on it against metrics.md's learning-phase floor ... if the chosen
qualified event's expected weekly count lands far under it, optimize on the
higher-volume upstream event (raw lead) first, qualify downstream, and revisit
as spend grows. (Reference metrics.md; don't restate the number.)

**4b. Live signal-health check (when connected — replaces guesswork).** If the
marker shows `connections.meta_mcp` connected, verify the plumbing with real
data instead of asking the coach to eyeball Events Manager:
- `ads_get_datasets` — which pixels / datasets exist + `last_fired` freshness
  (is the event actually firing?),
- `ads_get_dataset_quality` — EMQ / match coverage (direction only — never
  chase decimals, canon: Signals),
- `ads_get_dataset_stats` — event volume over the last **28 days** (note the
  window when you report it),
- `ads_get_customconversions` — custom-conversion rules + URL match (does the
  qualified event map to the right rule?).
Branch-aware: on branch (a) it checks the Pixel + CAPI events; on branch (b) it
checks the Instant-Form dataset, plus the CAPI-bridge dataset ONLY where a
bridge was actually built (per Step 0b's conditional) ... no bridge means no
bridge dataset to check, so the Instant-Form data is what gets verified.
**Unconnected → the paste /
screenshot-of-Events-Manager path stays first-class** — the coach shows me what
they see and we verify together.

**5. Value rules module (Stage 2+ only).** After real CRM analysis, bid ±% on
segments the coach KNOWS differ in value (age band, source, device) — inject
LTV knowledge Meta can't see; accept possibly higher CPL for better quality.
Skip at Stage 1 (no data yet).

**6. Brain (1 search).** Recipe = funnel-event / signal row: query "CAPI pixel
dedup EMQ coaching", variants keyed to the CRM. Self-evidencing line;
degrade F9.

**7. Live-check the product surface** (menu paths, one-click CAPI availability)
before instructing clicks — volatile. Live check unavailable → give the canon
path labeled "unverified — menu may have moved", never block.

**8. Write** `signal.{pixel, capi, dedup_checked, checked_at}`.

## Terminal paths — inline blocks (routing.md grammar)

**Dual-tracking live (E8):** preamble states what's verified (pixel, CAPI,
dedup) or the exact click-TODO list left — **branch-aware:** branch (b) (no
controlled page) lists Instant-Form steps, plus CAPI-bridge steps only when a
bridge was actually chosen and built (no bridge ... the weekly CRM cross-check
is the feedback loop, say so), never un-clickable Pixel TODOs. Then:

**Next moves**
1. Run the live policy gate — launch stays locked until it passes. Say: "compliance check"  ← start here
2. Start building the ads themselves — the creative plan. Say: "creative strategy"

**Next moves — weak-signal re-entry (E16/F2)**
1. Re-verify the qualified event fires + dedup holds — I'll walk Events Manager with you. Say: "set up tracking" (verify step)
2. Back to the review once green. Say: "review my ads"

## Teach mode
In `new`: plain-English-first — the doorbell-camera (Pixel) and
phone-call-vs-postcard (CAPI) analogies from glossary Section 3 lead;
"deduplicated" explained before `event_id`; every Events Manager click gets
a "what this toggle is" line. In `learning`: gloss Pixel/CAPI/EMQ first use.
In `pro`: checklist voice, terse.

## Guardrails
- No AEM setup (obsolete — canon). No fake EMQ decimals.
- Health-coaching pixel events: the "prohibited information" data rule is
  FLAGGED (canon: Compliance) — tell the coach to verify before firing health events;
  route the live policy lookup via compliance-check (Say: "compliance check").
