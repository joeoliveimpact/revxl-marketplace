---
name: shortform-superengine:brand-brain
description: Derive a living BRAND BRAIN — voice, ICP/pains, content seeds, signature humor, weekly topics — from a client's real sources (call recordings, own content, DMs) and keep it fresh on a 7-day heartbeat. Use when a user wants to capture their brand voice, build a voice guide, mine calls or content for voice-of-customer language, set up their brand for any REVXL superengine, or refresh a stale brain. Trigger phrases include "capture my voice", "build my brand brain", "mine my calls", "set up my voice", "refresh my voice guide", "update my topics".
---

# Brand Brain — producer

One skill, one job: **sources in → brain out** at the shared location. Every REVXL engine (email, shortform, future) reads what this writes. This skill is bundled inside each engine and MUST run safely from any of them: no plugin-specific paths, no engine assumptions. If a brain already exists (built from any engine), NEVER rebuild from scratch — detect and reuse.

## Shared location (THE contract — never deviate)

    ~/.claude/revxl/<brand>/voc/
      voice-guide.md          # coach voice, register-tagged, voice_confidence stamped
      voc-profile.md          # freq-ranked verbatim prospect bank + evergreen content seeds
      business-config.md      # brand-level avatar + offer (shared)
      signature-bits.md       # the client's REAL humor, evidence-scored (canonization parked until a consumer reads bits)
      weekly-content-bank.md  # fast shelf: this week's themes/objections/jokes/seeds, 7-day TTL

`<brand>` resolves from config and is a NORMALIZED slug — lowercase, alphanumeric only, no separators ("Maria G Fit" → `mariagfit`) — so every engine resolves the same brand to the same folder. Before minting a new brand folder, check `~/.claude/revxl/` for a similar existing one and confirm with the user (two half-brains for one coach is the failure to avoid). One user can hold multiple brands. Raw transcripts + the mining index stay WORKSPACE-level (`voc/transcripts/<bucket>/`, `voc/index.md`) — bulky, private source data.

## Router — run this decision every invocation

1. **Detect first (idempotent).** Check `~/.claude/revxl/<brand>/voc/` for existing artifacts.
2. **Present + fresh (≤7 days old)** → REUSE. Say so in one line. Done.
3. **Present + stale (>7 days)** → offer a quick update: *"Your voice + topics are N days old — want a quick update? (~1-3 min, only pulls what's new)"* → yes: run ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/refresh.md · no: reuse as-is, log the decline in `voc/index.md`, then never dead-end — **Next moves**: 1) proceed with what you were doing on the current brain · 2) *"want a reminder at the next 7-day mark instead? I'll set a remind-only nudge — it never mines by itself"* (suggested schedule, Step-4c pattern, `refresh.mode: "remind-only"`) · 3) the lighter option: a top-patterns quick pass (~1 min) instead of the full refresh.
4. **Absent** → full pass: run ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/mine.md.
5. **No usable sources at all** (ladder empty through tier C) → ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/interview.md, and offer to turn on recording from call #1 so the brain compounds. End the interview floor with **Next moves**: 1) wire the recording source now (Fathom/Fireflies) so the brain builds itself from your next call · 2) *"first real refresh in ~a week? I'll suggest it, you confirm"* (suggested schedule) · 3) script now on the interim voice — honest floor, upgrades automatically once real sources land.

Offer refreshes at most ONCE per session — never nag on back-to-back builds.

**After any completed mine or refresh — Next moves**
1. Script a reel off the freshest topical seed — I hand the seed straight to reel-scripter as the angle. Say: "script the top seed"
2. *If no auto-refresh is set:* keep the brain fresh on a schedule (Friday night / Monday morning / your pick — always asked, never silent). Say: "schedule my brain refresh"
3. Back to what you were doing — the consuming engine picks the fresh brain up automatically.

## Rules that never bend

- **Elicit, never invent.** Voice, stories, jokes come from the client's real material. If a signal isn't there, it isn't in the brain.
- **Attribution guard.** Every extracted line belongs to the speaker who said it. A coach's bit never lands in a client's brain; a setter's phrasing never sets the coach's voice.
- **Approval-gated data.** Recordings, DMs, socials = personal data. Never pull without an explicit OK. Never send or export any of it externally.
- **Privacy.** One brain per brand; a filled brain is private and never ships inside any plugin.

## Frameworks

- ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/source-ladder.md — where voice + offer/avatar evidence comes from, confidence stamping
- ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/speaker-separation.md — who said it → where it goes
- ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/extraction.md — the mining method (voice / VoC / seeds, two shelves)
- ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/signature-bits.md — objective humor scoring + human canonization
- ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/freshness.md — stamps, age-on-access, 7-day heartbeat, delta refresh
- ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/artifacts.md — exact output schemas (what consumers parse)

## Shortform tie-in

reel-scripter reads `voice-guide.md` (registers `written-content` / `spoken-video`) plus `voc-profile.md` and `business-config.md`. `weekly-content-bank.md` has no wired consumer yet — after a mine or refresh, offer to script a reel off the freshest topical seed by handing the seed text to reel-scripter inline (as the angle input), not by pointing at the file.
