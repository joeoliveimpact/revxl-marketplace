---
name: shortform-superengine:brand-brain
description: Derive a living BRAND BRAIN ... voice, ICP/pains, content seeds, signature humor, weekly topics ... from a client's real sources (call recordings, own content, DMs) and keep it fresh on a 7-day heartbeat. Use when a user wants to capture their brand voice, build a voice guide, mine calls or content for voice-of-customer language, set up their brand for any REVXL superengine, refresh a stale brain, or hand it themes and audience language gathered elsewhere. Trigger phrases include "capture my voice", "build my brand brain", "mine my calls", "set up my voice", "refresh my voice guide", "update my topics", "add these themes to my brand brain", "add this to my brand brain", "schedule my brain refresh".
---

# Brand Brain — producer

One skill, one job: **sources in → brain out** at the shared location. Every REVXL engine (email, shortform, future) reads what this writes. This skill is bundled inside each engine and MUST run safely from any of them: no plugin-specific paths, no engine assumptions. If a brain already exists (built from any engine), NEVER rebuild from scratch — detect and reuse.

## Teach mode

Read `~/.claude/revxl/teach-level` (one word: `new`, `learning`, `pro`). If it is
absent but the legacy `~/.claude/revxl/teach-mode` exists, map `beginner` to `new`
and `off` to `pro`; if neither exists, `new`. At `new` explain in plain words
first, then name the term with a one-line gloss on first use and add a "what this
means for you" line where the consequence is not obvious; at `learning` the term
goes inline; at `pro` no scaffolding. Gates, refusals and privacy warnings render
in full at every level. Convention and the switch:
`../_shared/references/teach-mode.md`.

## Prereq (E0)

None beyond a brand slug. `<brand>` is the normalized slug defined below; it comes
from the engine that invoked this skill, or from the `.superengine` marker's
`active_brand` when there is one, or from asking the client once. This skill
refuses nobody, and it **writes no journey state**: `voc.present` and
`voc.refreshed_at` are derived on read from `~/.claude/revxl/<brand>/voc/` by
whoever needs them (`../_shared/references/state-schema.md`), so the disk is the
only answer to "does this client have a voice guide". Nothing here is
shortform-specific; this skill ships inside several engines and must run the same
way in all of them.

## Terminal paths

Every ending of this skill is written out here, so a client is never left holding
a finished brain with nowhere to go. Ids are rows in
`../_shared/references/journey-map.md`; the block shape is
`../_shared/references/routing.md`.

**Next moves** (E10, a mine or a refresh completed)
1. Script a reel off the freshest topical seed ... I hand the seed text straight to reel-scripter as the angle, not a file path. Say: "script the top seed"
2. *If no refresh cadence is set:* keep the brain fresh on a schedule (Friday night, Monday morning, a time you pick ... always asked, never silent). Say: "schedule my brain refresh"
3. Back to what you were doing. The consuming engine picks the fresh brain up on its own.

**Next moves ... themes ingested** (E10)
1. Script a reel off the theme that just landed. Say: "script the top seed"
2. Hand over more ... another theme list, or another batch of audience lines, appends the same way. Say: "add these themes to my brand brain"
3. Back to what you were doing.

**Next moves ... refresh declined** (E11)
1. Carry on with the brain as it stands ... I label its real age, nothing is faked. Say: "what's next in shortform"
2. A remind-only nudge at the next 7-day mark instead ... it never mines by itself. Say: "schedule my brain refresh"
3. The lighter option: a top-patterns quick pass, about a minute, instead of the full refresh. Say: "update my topics"

**Next moves ... interview floor** (E12)
1. Wire the recording source now (Fathom, Fireflies) so the next call builds the brain for you, then mine it. Say: "mine my calls"
2. First real refresh in about a week ... I suggest it, you confirm. Say: "schedule my brain refresh"
3. Script now on the interim voice ... an honest floor that upgrades itself the moment real sources land. Say: "write a reel script"

**Next moves ... the brain is already fresh** (E0b)
1. Back to what you were doing ... nothing to rebuild, the brain is under 7 days old. Say: "what's next in shortform"
2. Script off the freshest seed already on the shelf. Say: "script the top seed"
3. Top the topics up anyway if this week moved fast. Say: "update my topics"

## Shared location (THE contract — never deviate)

    ~/.claude/revxl/<brand>/voc/
      voice-guide.md          # brand-owner voice, register-tagged, voice_confidence stamped
      voc-profile.md          # freq-ranked verbatim prospect bank + evergreen content seeds
      business-config.md      # brand-level avatar + offer (shared)
      signature-bits.md       # the client's REAL humor, evidence-scored (canonization parked until a consumer reads bits)
      weekly-content-bank.md  # fast shelf: this week's themes/objections/jokes/seeds, 7-day TTL

`<brand>` resolves from config and is a NORMALIZED slug — lowercase, alphanumeric only, no separators ("Maria G Fit" → `mariagfit`) — so every engine resolves the same brand to the same folder. Before minting a new brand folder, check `~/.claude/revxl/` for a similar existing one and confirm with the user (two half-brains for one brand owner is the failure to avoid). One user can hold multiple brands. Raw transcripts + the mining index stay WORKSPACE-level (`voc/transcripts/<bucket>/`, `voc/index.md`) — bulky, private source data.

## Router — run this decision every invocation

**Handed material first.** If the invocation arrives carrying content ("add these
themes to my brand brain", "add this to my brand brain" ... a theme list from a
competitor cross-reference, audience voice-of-customer lines from a comment
pulse), do NOT re-mine and do not rebuild anything. Append it: themes and topical
seeds go on the end of `weekly-content-bank.md` under a dated heading naming where
they came from; audience VoC lines go into `voc-profile.md`'s audience section,
verbatim, attributed to the audience and never to the brand owner (the attribution
guard below still holds). Stamp `updated_at` on both files, say in one line what
landed where, then end with the themes-ingested block (E10) from
`## Terminal paths`. Nothing is invented and nothing already in the brain is
rewritten: handed material is evidence, exactly like a transcript.

1. **Detect first (idempotent).** Check `~/.claude/revxl/<brand>/voc/` for existing artifacts.
2. **Present + fresh (≤7 days old)** → REUSE. Say so in one line, then end with the already-fresh block (E0b) from `## Terminal paths`.
3. **Present + stale (>7 days)** → offer a quick update: *"Your voice + topics are N days old ... want a quick update? (~1-3 min, only pulls what's new)"* → yes: run ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/refresh.md · no: reuse as-is, log the decline in `voc/index.md`, then end with the refresh-declined block (E11) from `## Terminal paths`.
4. **Absent** → full pass: run ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/mine.md.
5. **No usable sources at all** (ladder empty through tier C) → ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/interview.md, and offer to turn on recording from call #1 so the brain compounds. End with the interview-floor block (E12) from `## Terminal paths`.

Offer refreshes at most ONCE per session — never nag on back-to-back builds.

## Rules that never bend

- **Elicit, never invent.** Voice, stories, jokes come from the client's real material. If a signal isn't there, it isn't in the brain.
- **Attribution guard.** Every extracted line belongs to the speaker who said it. A brand owner's bit never lands in a client's brain; a setter's phrasing never sets the brand owner's voice.
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
