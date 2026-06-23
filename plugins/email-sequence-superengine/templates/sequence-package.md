# Sequence Package Template (all campaigns — framework, not swipe copy)

Fill the slots in the coach's voice. Slots in `[brackets]`. Structure + levers only, no canned sentences.

## Per-email framework (repeat per email in the campaign)

```
--- EMAIL [#] ---
Send: [timing — from the campaign framework]
Format mode: [text-only | light-HTML]
Lever: [from the campaign framework's lever column]
Trigger spec: [GHL trigger — e.g. tag / X hours after event]
Benchmark to watch: [the metric this email moves]

Subject: [hook-type: curiosity | value | urgency | personalization] — [the line]
Preview: [the line]

Body:
[Body architecture: PAS | HSO | two-line plain-text]
[Open in the coach's voice — name a specific AVATAR pain/objection from config; merge tokens only, no individual facts]
[One point. One CTA destination.]
[CTA — single next action, repeated up to 3x, same destination]

P.S. [strategic, high-attention — pick one: subplot / social proof / curiosity-loop / personality / soft nudge. NOT the primary CTA.]
```

## Sequence-package wrapper

```
# [Campaign Name] Sequence — [Program]

## Overview
[1-2 lines: what this sequence does, who/when it fires to, expected outcome]

## Avatar anchor (used for specificity)
Pains: [from config] · #1 objection: [from config]

## Format-mode banner
[the campaign's text/HTML mix and why]

## Decision-table placement
[the campaign framework's email-by-email fire-trigger + goal-metric table]

## GHL setup note
Stage as templates (opt-in), named per email. Wire timing/triggers in a GHL workflow MANUALLY (no MCP
endpoint for workflow timing). Keep replies in GHL Conversations. Merge tokens resolve per-contact at send.

## Companion touchpoints (optional, wire in GHL — not generated here)
[campaign-relevant: SMS / DM / retarget — flag only]
```
