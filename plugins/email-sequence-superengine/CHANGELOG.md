# Changelog — email-sequence-superengine

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] — 2026-06-30

### Added
- **`brand-brain` skill (bundled shared producer).** Mines a client's real sources — Fathom/Fireflies call recordings, own social/newsletters, Meta DM export, or a guided-interview floor — into a living brand brain at the cross-engine shared location `~/.claude/revxl/<brand>/voc/`: `voice-guide.md` (register-tagged, confidence-stamped), `voc-profile.md` (frequency-ranked verbatim prospect language + evergreen content seeds), `business-config.md` (shared brand-level avatar/offer), `signature-bits.md` (evidence-scored, human-canonized humor), `weekly-content-bank.md` (7-day topical shelf). Idempotent detect-and-reuse with a 7-day freshness heartbeat and delta-only refreshes. Validated against a real-call acceptance fixture (6/6).

### Changed
- **`voice-anchor` detect-path now checks the shared brand brain first** (`~/.claude/revxl/<brand>/voc/voice-guide.md`) before any workspace guide or interim extraction — completes the VoC-contract follow-up so one captured voice serves every REVXL engine.
- **`business-config` brand-level tokens (avatar/offer/positioning) read/write the shared location when present**; engine-specific keys stay in `${CLAUDE_PLUGIN_DATA}`. `email-setup` detects the shared brain + config before asking, and offers `brand-brain` when no voice guide exists.

## [0.1.2] — 2026-06-24

### Changed
- Maintenance re-publish (version bump only) to refresh the hosted marketplace listing so the in-app installer resolves the plugin; some clients saw a 404 installing v0.1.1 from the in-app directory. No functional, command, or content changes.

## [0.1.1] — 2026-06-23

### Changed
- **Renamed all 12 commands to an `email-` prefix** so the plugin's commands group under `/email-` and never collide with another plugin's bare `start`/`setup`/`guide`. Behavior, frameworks, and bundled files are unchanged. Mapping:
  - `start` → `email-start-here`
  - `setup` → `email-setup`
  - `guide` → `email-guide`
  - `story-intake` → `email-add-stories`
  - `precall-nurture` → `email-show-up-sequence`
  - `precall-video-script` → `email-presell-video`
  - `launch` → `email-launch-promo-sequence`
  - `warm-nurture` → `email-warm-nurture-sequence`
  - `no-show-recovery` → `email-no-show-sequence`
  - `post-call-followup` → `email-follow-up-sequence`
  - `winback` → `email-winback-sequence`
  - `onboarding` → `email-onboarding-sequence`

## [0.1.0] — 2026-06-22

### Added
- Initial release.
- **12 skills:** `start` (orchestrator/router), `setup` (first-run config wizard), `guide` (plain-English first-time tour), `story-intake` (Q&A that banks the coach's real stories), and 8 campaign generators: `precall-nurture`, `precall-video-script`, `launch`, `warm-nurture`, `no-show-recovery`, `post-call-followup`, `winback`, `onboarding`.
- **Broadcast model:** every sequence is built once and fires to everyone on the trigger. Specificity comes from the coach's voice + the avatar's shared pains + merge tokens, never per-prospect or invented facts.
- **Shared systems:** dosed storytelling engine (`story-engines` + `story-bank`, elicit-not-invent), CTA pattern library with a soft-pitch gradient (none to hard), goal-indexed length system measured from a large real-email corpus, no-false-scarcity guardrail, `{{VOICE_EDGE}}` dial (vanilla to locker-room), `{{TEACH_MODE}}` plain-English why-explanations, P.S. strategy, and deliverability + reply-routing rules.
- **ESP-agnostic output** with optional GoHighLevel template push (`ghl-push`); `setup` detects your ESP.
- **Config-driven:** one `references/business-config.md` holds all `{{VARIABLE}}` values and ships with placeholders, so each installer runs `setup` fresh. Config + story-bank persist via `${CLAUDE_PLUGIN_DATA}` and survive plugin updates.
- **Drafts only:** never sends; building GHL workflow timing stays a manual step.
- **Bundled docs** resolve via `${CLAUDE_PLUGIN_ROOT}/...` for reliable loading on Claude Desktop and Claude Code.
