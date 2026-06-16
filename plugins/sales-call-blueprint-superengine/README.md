# sales-call-blueprint-superengine

> Paste the DM thread that led to a booked call — get back a customized, psychology-driven battle-plan for that call. For coaches and closers.

![demo placeholder](../../docs/demos/sales-call-blueprint-superengine.gif)

---

## What this plugin does

A booked call is only as good as the prep behind it. This plugin reads the pre-call conversation (the DM thread, plus any prior triage notes or call transcript), builds a psychological profile of the prospect from their own words, and hands you a blueprint for the call — who they are, what they actually want, the order to ask things, the objections coming, and how to close.

**Five skills + one batch agent** take you from zero to a finished blueprint:

- A **first-run setup** that fills in your brand/program details by reading where they already live (no blank form), and a **plain-English guided tour** for non-technical users.
- Two call types: **triage** (the 15-minute "are they a fit" qualifier) and **strategy** (the full RFPDP closing call).
- Two output shapes: a deep **Pre-Call Prep** doc you read beforehand, and a one-screen **Call-Time Blueprint** card you keep open during the call — one or both.

It uses *your* playbook (the RFPDP method, your objection handling), pulls prior-call transcripts from whatever recorder you use, and delivers finished blueprints wherever you want them. **It never stores your pricing** — you say the number live; the skill just structures how to drop it.

**Audience:** coaches and the people who take their sales calls. Explainer mode is on by default (plain-English narration with a "what this means for you" line); say "explainer off" for quick mode once you're comfortable.

---

## Skills

#### `start`
**Triggers:** "/sales-call-blueprint-superengine", "prep my sales call", "build a call blueprint", "blueprint this prospect", "I have a call booked"

The orchestrator. Greets, confirms the three gate questions (call type · who's taking it · which output), and routes to the right skill. Sends first-time users to the tour; returning users straight to triage/strategy.

#### `setup`
**Triggers:** "set up the blueprint skill", "configure blueprints", "reconfigure for a different business", "change my transcript source"

First-run wizard. Auto-discovers brand/program/closer details from your CLAUDE.md, website, or Drive; sets your transcript source and output destination; runs a dependency check scoped only to what your choices actually need. Re-runnable any time.

#### `guide`
**Triggers:** "first time", "how do I use this", "walk me through the blueprint skill", "I'm new", "help"

Plain-English first-time tour for non-technical users. Explains what the skill does, runs setup, and builds your first blueprint with extra hand-holding — jargon glossed inline.

#### `triage-blueprint`
**Triggers:** "triage", "qualification call prep", "prep my triage call", "screen this lead before the sales call"

Builds a 15-minute qualification blueprint for the gatekeeper/setter: a tight diagnostic structure, in/out decision criteria, a pricing-deflection script, and both a "book the strategy call" and a "redirect with respect" script. Plus a post-call notes sheet so confirmed intel feeds a later strategy blueprint. Never pitches; never quotes pricing.

#### `strategy-blueprint`
**Triggers:** "strategy", "closing call prep", "prep my sales call", "blueprint this discovery call"

The heavy workflow. Builds a full RFPDP closing-call blueprint: deep psychological profile (gaps flagged, never fabricated), the 10 discovery topics ranked for *this* prospect, an objection playbook built from their DMs, and a pitch structure ending in a price drop you control. Folds in prior triage-call intel when it exists.

---

## Agent

### `sales-blueprint-builder` (Claude Code only)
**Triggers:** "blueprint all these DMs", "I got 8 launch DMs, prep them all", "build a blueprint for [name]", "batch these triage/strategy calls"

Builds blueprints for one prospect or a whole batch in its own context window, so the main chat stays clean. Runs two ways: **autonomous** (pulls the transcript and delivers itself, if connectors are reachable) or **bookended** (you hand it the text and handle delivery). Draft-first, always — nothing is delivered before you approve, and nothing ever goes to a prospect.

---

## Quick install

### Claude Desktop (recommended for coaches)

1. Customize → Skills → **+** next to "Personal plugins"
2. Paste: `joeoliveimpact/revxl-marketplace`
3. Click Sync → click **Install** on `sales-call-blueprint-superengine`

Then in your first conversation:
1. Say _"first time"_ or _"walk me through it"_ → the `guide` tour orients you, runs setup, and builds your first blueprint
2. From then on: just paste a DM thread and say _"prep my sales call"_

### Claude Code

```
/plugin marketplace add joeoliveimpact/revxl-marketplace
/plugin install sales-call-blueprint-superengine@revxl-marketplace
```

Full step-by-step in the [marketplace INSTALL guide](../../README.md#install).

---

## Dependencies

**None are required** — paste a DM thread and you're working. The integrations below are optional and only checked if you choose to use them (the `setup` wizard scopes the dependency check to your actual choices):

| Capability | Optional integration | Always-available fallback |
|------------|----------------------|---------------------------|
| Pull a prior call's transcript | A recorder's MCP (Fathom / Fireflies / Granola / Otter) or the GoHighLevel MCP | Paste the transcript manually |
| Transcribe a local audio file (`local-audio` source) | `ffmpeg` + a local Whisper (faster-whisper / whisper.cpp / GPU) | Use a recorder service, or paste |
| Deliver to Google Drive (dated folders) | Google Workspace access (`gws` CLI / Drive) | Save locally, or paste on screen |
| Deliver as a GHL contact note | GoHighLevel MCP | Save locally |

Pricing is intentionally not stored anywhere — you supply it live.

---

## Compatibility

| Platform | Skills | Agent |
|----------|--------|-------|
| Claude Desktop | ✅ all 5 | only inline (not as a subagent) |
| Claude Code | ✅ all 5 | ✅ as a subagent (batch mode) |

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).

## Part of

[revxl-marketplace](../../README.md) — REVXL's curated Claude superengine catalog.
