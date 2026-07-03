---
name: email-sequence-superengine:brand-brain
description: Derive a living BRAND BRAIN — voice, ICP/pains, content seeds, signature humor, weekly topics — from a client's real sources (call recordings, own content, DMs) and keep it fresh on a 7-day heartbeat. Use when a user wants to capture their brand voice, build a voice guide, mine calls or content for voice-of-customer language, set up their brand for any REVXL superengine, or refresh a stale brain. Triggers: "capture my voice", "build my brand brain", "mine my calls", "set up my voice", "refresh my voice guide", "update my topics".
---

# Brand Brain — producer

One skill, one job: **sources in → brain out** at the shared location. Every REVXL engine (email, shortform, future) reads what this writes. This skill is bundled inside each engine and MUST run safely from any of them: no plugin-specific paths, no engine assumptions.

## Shared location (THE contract — never deviate)

    ~/.claude/revxl/<brand>/voc/
      voice-guide.md          # coach voice, register-tagged, voice_confidence stamped
      voc-profile.md          # freq-ranked verbatim prospect bank + evergreen content seeds
      business-config.md      # brand-level avatar + offer (shared)
      signature-bits.md       # the client's REAL humor, evidence-scored, human-canonized
      weekly-content-bank.md  # fast shelf: this week's themes/objections/jokes/seeds, 7-day TTL

`<brand>` resolves from config; one user can hold multiple brands. Raw transcripts + the mining index stay WORKSPACE-level (`voc/transcripts/<bucket>/`, `voc/index.md`) — bulky, private source data.

## Router — run this decision every invocation

1. **Detect first (idempotent).** Check `~/.claude/revxl/<brand>/voc/` for existing artifacts.
2. **Present + fresh (≤7 days old)** → REUSE. Say so in one line. Done.
3. **Present + stale (>7 days)** → offer a quick update: *"Your voice + topics are N days old — want a quick update? (~1-3 min, only pulls what's new)"* → yes: run ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/refresh.md · no: reuse as-is, log the decline in `voc/index.md`.
4. **Absent** → full pass: run ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/mine.md.
5. **No usable sources at all** (ladder empty through tier C) → ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/interview.md, and offer to turn on recording from call #1 so the brain compounds.

Offer refreshes at most ONCE per session — never nag on back-to-back builds.

## Rules that never bend

- **Elicit, never invent.** Voice, stories, jokes come from the client's real material. If a signal isn't there, it isn't in the brain.
- **Attribution guard.** Every extracted line belongs to the speaker who said it. A coach's bit never lands in a client's brain; a setter's phrasing never sets the coach's voice.
- **Approval-gated data.** Recordings, DMs, socials = personal data. Never pull without an explicit OK. Never send or export any of it externally.
- **Privacy.** One brain per brand; a filled brain is private and never ships inside any plugin.

## Frameworks

- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/source-ladder.md — where voice + offer/avatar evidence comes from, confidence stamping
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/speaker-separation.md — who said it → where it goes
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/extraction.md — the mining method (voice / VoC / seeds, two shelves)
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/signature-bits.md — objective humor scoring + human canonization
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/freshness.md — stamps, age-on-access, 7-day heartbeat, delta refresh
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/artifacts.md — exact output schemas (what consumers parse)
