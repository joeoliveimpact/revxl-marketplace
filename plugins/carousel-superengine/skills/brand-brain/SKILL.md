---
name: carousel-superengine:brand-brain
description: Derive a living BRAND BRAIN — voice, ICP/pains, content seeds, signature humor, weekly topics — from a client's real sources (call recordings, own content, DMs) and keep it fresh on a 7-day heartbeat. Use when a user wants to capture their brand voice, build a voice guide, mine calls or content for voice-of-customer language, set up their brand for any REVXL superengine, or refresh a stale brain. Trigger phrases include "capture my voice", "build my brand brain", "mine my calls", "set up my voice", "refresh my voice guide", "update my topics".
---

# Brand Brain — producer

One skill, one job: **sources in → brain out** at the shared location. Every REVXL engine (email,
shortform, carousel, future) reads what this writes. This skill is bundled inside each engine and
MUST run safely from any of them: no plugin-specific paths, no engine assumptions.

## Shared location (THE contract — never deviate)

    ~/.claude/revxl/<brand>/voc/
      voice-guide.md          # coach voice, register-tagged, voice_confidence stamped
      voc-profile.md          # freq-ranked verbatim prospect bank + evergreen content seeds
      business-config.md      # brand-level avatar + offer (shared)
      signature-bits.md       # the client's REAL humor, evidence-scored (canonization parked until a consumer reads bits)
      weekly-content-bank.md  # fast shelf: this week's themes/objections/jokes/seeds, 7-day TTL

`<brand>` resolves from the engine's config (here: `{{BRAND_SLUG}}` in
`${CLAUDE_PLUGIN_DATA}/business-config.md`) and is a NORMALIZED slug — lowercase, alphanumeric only, no
separators ("Maria G Fit" → `mariagfit`) — so every engine resolves the same brand to the same
folder. Before minting a new brand folder, check `~/.claude/revxl/` for a similar existing one and
confirm with the user (two half-brains for one coach is the failure to avoid). One user can hold
multiple brands. Raw transcripts + the mining index stay WORKSPACE-level
(`voc/transcripts/<bucket>/`, `voc/index.md`) — bulky, private source data.

## Router — run this decision every invocation

1. **Detect first (idempotent).** Check `~/.claude/revxl/<brand>/voc/` for existing artifacts.
2. **Present + fresh (≤7 days old)** → REUSE. Say so in one line. Done.
3. **Present + stale (>7 days)** → offer a quick update: *"Your voice + topics are N days old —
   want a quick update? (~1-3 min, only pulls what's new)"* → yes: run
   ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/refresh.md · no: reuse as-is, log the decline in
   `voc/index.md`.
4. **Absent** → full pass: run ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/mine.md.
5. **No usable sources at all** (ladder empty through tier C) →
   ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/interview.md, and offer to turn on recording from
   call #1 so the brain compounds.

Offer refreshes at most ONCE per session — never nag on back-to-back builds.

## Rules that never bend

- **Elicit, never invent.** Voice, stories, jokes come from the client's real material. If a signal
  isn't there, it isn't in the brain.
- **Attribution guard.** Every extracted line belongs to the speaker who said it. A coach's bit
  never lands in a client's brain; a setter's phrasing never sets the coach's voice.
- **Approval-gated data.** Recordings, DMs, socials = personal data. Never pull without an explicit
  OK. Never send or export any of it externally.
- **Privacy.** One brain per brand; a filled brain is private and never ships inside any plugin.

## Carousel tie-in

**This skill sets the brand name for the whole carousel engine.** The moment a brand folder is confirmed or
created (any router branch), write its slug to `{{BRAND_SLUG}}` in
`${CLAUDE_PLUGIN_DATA}/business-config.md` (create that file from the plugin's references copy if it is not
there yet). `{{BRAND_SLUG}}` already set → use it as `<brand>` and never ask again. Every other carousel skill
reads `<brand>` from that one token.

`carousel-create` and `carousel-setup` consume the brain read-only: voice-guide sets register +
edge, voc-profile supplies avatar pains in the avatar's words (hooks + captions), business-config
supplies positioning + proof. The carousel engine's own filled config persists at
`${CLAUDE_PLUGIN_DATA}/business-config.md` (read first by every carousel skill; the plugin's
references copy is just the template) — brand-level tokens sync with the shared
`~/.claude/revxl/<brand>/voc/business-config.md`. If a build starts with no brain, setup offers
THIS skill before any interim voice capture.

## Frameworks

- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/source-ladder.md — where voice + offer/avatar evidence comes from, confidence stamping
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/speaker-separation.md — who said it → where it goes
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/extraction.md — the mining method (voice / VoC / seeds, two shelves)
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/signature-bits.md — objective humor scoring + human canonization
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/freshness.md — stamps, age-on-access, 7-day heartbeat, delta refresh
- ${CLAUDE_PLUGIN_ROOT}/references/brand-brain/artifacts.md — exact output schemas (what consumers parse)

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `carousel-superengine/reports/report-body.md` under the workspace folder: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text, slide copy).
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin carousel-superengine --plugin-version 0.6.0 --skill brand-brain --step '<mining, refresh or interview>' --error-line '<the error line>' --summary '<headline>' --body-file carousel-superengine/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`

The client never types any of these; you run them.
