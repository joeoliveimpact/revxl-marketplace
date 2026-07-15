---
name: profile-optimization-superengine:brand-brain
description: Derive a living BRAND BRAIN... voice, ICP/pains, content seeds, signature humor, weekly topics... from a client's real sources (call recordings, own content, DMs) and keep it fresh on a 7-day heartbeat. Use when a user wants to capture their brand voice, build a voice guide, mine calls or content for voice-of-customer language, set up their brand for any REVXL superengine, or refresh a stale brain. Trigger phrases include "capture my voice", "build my brand brain", "mine my calls", "set up my voice", "refresh my voice guide", "update my topics".
---

# Brand Brain... producer

One skill, one job: **sources in... brain out** at the shared location. Every REVXL engine (email, shortform, profile, future) reads what this writes. This skill is bundled inside each engine and MUST run safely from any of them: no plugin-specific paths, no engine assumptions.

## Shared location (THE contract... never deviate)

    ~/.claude/revxl/<brand>/voc/
      voice-guide.md          # coach voice, register-tagged, voice_confidence stamped
      voc-profile.md          # freq-ranked verbatim prospect bank + evergreen content seeds
      business-config.md      # brand-level avatar + offer (shared)
      signature-bits.md       # the client's REAL humor, evidence-scored (canonization parked until a consumer reads bits)
      weekly-content-bank.md  # fast shelf: this week's themes/objections/jokes/seeds, 7-day TTL

`<brand>` resolves from config and is a NORMALIZED slug... lowercase, alphanumeric only, no separators ("Maria G Fit"... `mariagfit`)... so every engine resolves the same brand to the same folder. Before minting a new brand folder, check `~/.claude/revxl/` for a similar existing one and confirm with the user (two half-brains for one coach is the failure to avoid). One user can hold multiple brands. Raw transcripts + the mining index stay WORKSPACE-level (`voc/transcripts/<bucket>/`, `voc/index.md`)... bulky, private source data.

## Environment check FIRST (chat has no persistent filesystem)

Before any detect/build, establish where this skill is running... reuse the tier the audit skill or `profile-start` already confirmed this session if you have it, otherwise probe your own tools (shell/Bash or a browser tool present... Cowork/Code; neither... Claude.ai Chat).

- **Cowork / Code tier (a filesystem persists):** run the normal house behavior below... detect the shared brain, reuse if present, offer to build if absent.
- **Claude.ai Chat tier (NO persistent user filesystem):** do NOT attempt to read or build the brain. It cannot persist here... `~/.claude/revxl/...` will not survive. Degrade honestly: capture voice inline for THIS session only (ask the coach for 2-3 writing samples or voice-note transcripts and mirror them for the current work), and tell the coach plainly that the full persistent voice brain needs the Claude desktop app (Cowork) or Claude Code. Never pretend a brain was saved.

## Router... run this decision every invocation (Cowork/Code tier)

1. **Detect first (idempotent).** Check `~/.claude/revxl/<brand>/voc/` for existing artifacts.
2. **Present + fresh (<=7 days old)** ... REUSE. Say so in one line. Done.
3. **Present + stale (>7 days)** ... offer a quick update: *"Your voice + topics are N days old... want a quick update? (~1-3 min, only pulls what's new)"* ... yes: run ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/refresh.md · no: reuse as-is, log the decline in `voc/index.md`.
4. **Absent** ... full pass: run ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/mine.md.
5. **No usable sources at all** (ladder empty through tier C) ... ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/interview.md, and offer to turn on recording from call #1 so the brain compounds.

Offer refreshes at most ONCE per session... never nag on back-to-back builds.

## Rules that never bend

- **Elicit, never invent.** Voice, stories, jokes come from the client's real material. If a signal isn't there, it isn't in the brain.
- **Attribution guard.** Every extracted line belongs to the speaker who said it. A coach's bit never lands in a client's brain; a setter's phrasing never sets the coach's voice.
- **Approval-gated data.** Recordings, DMs, socials = personal data. Never pull without an explicit OK. Never send or export any of it externally.
- **Privacy.** One brain per brand; a filled brain is private and never ships inside any plugin.

## Profile tie-in

`profile-fb-audit` and `profile-ig-audit` consume the brain read-only: voice-guide sets the register and edge for any copy they write (bio options, CTA lines, About mini-sales letter), voc-profile supplies the avatar's pains in the avatar's own words, business-config supplies positioning + proof. The audit engines have no heavy config of their own... they gather intake conversationally... so the brain is the durable voice layer. If an audit starts with no brain, the voice step offers THIS skill (Cowork/Code) or captures voice inline for the session (Chat).

## Frameworks

- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/source-ladder.md... where voice + offer/avatar evidence comes from, confidence stamping
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/speaker-separation.md... who said it... where it goes
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/extraction.md... the mining method (voice / VoC / seeds, two shelves)
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/signature-bits.md... objective humor scoring + human canonization
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/freshness.md... stamps, age-on-access, 7-day heartbeat, delta refresh
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/artifacts.md... exact output schemas (what consumers parse)
