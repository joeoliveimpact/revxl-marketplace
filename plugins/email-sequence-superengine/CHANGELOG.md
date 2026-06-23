# Changelog — email-sequence-superengine

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-06-22

### Added
- Initial release.
- **12 skills:** `email-start-here` (orchestrator/router), `email-setup` (first-run config wizard), `email-guide` (plain-English first-time tour), `email-add-stories` (Q&A that banks the coach's real stories), and 8 campaign generators: `email-show-up-sequence`, `email-presell-video`, `email-launch-promo-sequence`, `email-warm-nurture-sequence`, `email-no-show-sequence`, `email-follow-up-sequence`, `email-winback-sequence`, `email-onboarding-sequence`.
- **Command naming:** every command is prefixed `email-` so the plugin's commands group under `/email-` and never collide with other plugins' `start`/`setup`/`guide`.
- **Broadcast model:** every sequence is built once and fires to everyone on the trigger. Specificity comes from the coach's voice + the avatar's shared pains + merge tokens, never per-prospect or invented facts.
- **Shared systems:** dosed storytelling engine (`story-engines` + `story-bank`, elicit-not-invent), CTA pattern library with a soft-pitch gradient (none to hard), goal-indexed length system measured from a large real-email corpus, no-false-scarcity guardrail, `{{VOICE_EDGE}}` dial (vanilla to locker-room), `{{TEACH_MODE}}` plain-English why-explanations, P.S. strategy, and deliverability + reply-routing rules.
- **ESP-agnostic output** with optional GoHighLevel template push (`ghl-push`); `email-setup` detects your ESP.
- **Config-driven:** one `references/business-config.md` holds all `{{VARIABLE}}` values and ships with placeholders, so each installer runs `email-setup` fresh. Config + story-bank persist via `${CLAUDE_PLUGIN_DATA}` and survive plugin updates.
- **Drafts only:** never sends; building GHL workflow timing stays a manual step.
- **Bundled docs** resolve via `${CLAUDE_PLUGIN_ROOT}/...` for reliable loading on Claude Desktop and Claude Code.
