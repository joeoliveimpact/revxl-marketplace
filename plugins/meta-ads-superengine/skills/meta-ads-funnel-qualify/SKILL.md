---
name: meta-ads-superengine:meta-ads-funnel-qualify
description: The qualification strategy — what to gate on so Meta learns to find buyers, not tire-kickers. Defines the qualified-conversion event and its trigger, wires it to GHL when present or produces a CRM-neutral spec for any other stack. Trigger phrases include "qualify my leads", "funnel strategy", "qualified event", "what should I optimize for".
---

# meta-ads-funnel-qualify — the signal-strategy layer

Contract: `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/skill-contracts.md` #8.
THE coach edge (framework 2.2): feed Meta raw leads, it finds cheap
tire-kickers; feed it *qualified* leads, it finds buyers. Owns the strategy +
event spec; hands wiring to GHL or a CRM-neutral spec.

## Load
- shared refs + `vault-api.md` + `metrics.md` (the learning-phase volume floor
  ... the gate has to leave enough event volume to exit learning)
- Active brand state → `targets`, `setup.crm`, `setup.offer`

## Prereq (E0)
`targets` set (needs the real CPQL). Missing → breakeven-math.

## Steps

**1. Set the qualification gate** — what makes a lead "qualified" for THIS
offer, in the coach's words (e.g. revenue ≥ $X/mo AND budget ≥ $Y, or a
readiness/timeline answer). Informed by the CPQL: the gate has to leave enough
volume to optimize.

**2. Choose the objective + event pattern:**
- Conversion-Leads objective; fire a **distinct server-side event ONLY on
  qualified-yes** ("no" is captured for nurture but the pixel stays blindfold).
- Set expectation plainly: **CPL rises, cost-per-QUALIFIED-lead falls** — that
  trade is the entire point.

**3. Wiring path:**
- `setup.crm == "ghl"` → **GHL fast-path:** pipeline-stage CAPI (pixel ID +
  CAPI token as custom values → "Meta Conversion API" action fires on
  stage change → pass stage name → real revenue on won). Distinguish funnel
  events (pages/forms) from lead events (Instant Forms — GHL dedups).
- otherwise → **CRM-neutral spec artifact:** event name, trigger condition,
  webhook shape (for Kajabi/ClickFunnels/whatever). Save it; note the path in
  state. No-code implement paths: Zapier/Make → Conversions API, or a
  CRM-native Meta integration — the actual wiring is signal-setup's job
  (Say: "set up tracking").

**4. Brain (1 search).** Recipe = funnel-event row: query "qualified lead
event conversion leads", variants keyed to the CRM + gate. Self-evidencing
line; degrade F9.

**5. Write** `funnel.{qualified_event, qualification_gate, wiring,
spec_artifact}`.

## Terminal paths — inline blocks (routing.md grammar)

**Event spec written (E6):**

**Next moves**
1. Write the questions that do the qualifying — money-gate + intel, in your voice. Say: "write my lead questions"  ← start here
2. Wire the tracking that carries this signal to Meta. Say: "set up tracking"

**Next moves — junk-leads re-entry (F2)**
The gate just got tightened; the spec is re-issued.
1. Verify the qualified event actually fires with the new gate. Say: "set up tracking"
2. Back to the weekly review once verified. Say: "review my ads"

## Teach mode
In `new`: plain-English-first — the "feed Meta raw leads, it finds
tire-kickers; feed it qualified leads, it finds buyers" explanation comes
BEFORE the term "qualified event" (deep-tier gloss with the puppy-training
analogy), and the CPL-up/CPQL-down trade gets a worked example with the
coach's own targets. In `learning`: gloss qualified event / Conversion-Leads
first use. In `pro`: gate → event spec → wiring path, terse.

## Guardrails
- CRM-neutral spec is a first-class output, never a fallback — GHL is a
  fast-path, not a dependency (premortem #5).
- The GHL One-Click-CAPI tie-in is practitioner-reported — say "verify in GHL
  directly", don't state it as confirmed (canon: Signals).
- No unattributed stats (the 17.8% figure is a Meta marketing claim — attribute
  it as such or omit).
