# Changelog — email-sequence-superengine

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] ... 2026-09-05

### Added
- **Every content skill checks the Brain before it drafts.** Nine skills (the eight
  campaign generators plus `email-add-stories`) each gained ONE named trigger point, fired
  after the brief is locked and before the first line is written: one invocation of
  `workspace-superengine:revxl-vault-search` against the `email-reference-library` spoke,
  a corpus of successful marketing emails from master copywriters. What comes back is
  STRUCTURE ... sequence shape, subject-line pattern, open and close moves ... never a
  line of source copy, which is that vault's own client-facing rule. The coach's voice
  still comes from brand-brain. Each pull is cached to `<project>/brain-pulls/`, cited
  `[brain] <path>`, and evidenced at the next checkpoint with `Brain: [brain] <path>
  woven` or `Brain: skipped (...)`. An optional second pull (`depth=low`, spoke
  `content-strategy`) covers subject-line hooks and CTA moves when the first found none.
- **`references/vault-api.md`** ... the wiring reference: both spokes, the invocation, the
  copyright rule verbatim from the vault, one query recipe per generator, the cache rule,
  the per-step budget (at most 2 searches + 3 note reads), the evidence line and the
  degrade rule. No curl, no key ladder and no endpoint appear anywhere in this plugin.
- **`email-setup` runs the Brain connection test** ... it invokes the skill with `test` and
  shows the coach the connection card, or says workspace-superengine is missing. Setup
  never blocks on the Brain.

### Changed
- Requires workspace-superengine 0.15.0 or later for live Brain pulls; without it (or
  without a key) the engine degrades to its bundled campaign frameworks and says so once.

## [0.2.1] — 2026-07-04

Premortem-driven hardening of the bundled `brand-brain` producer + its consumers. A premortem found the signature-bits pipeline weak at both ends: bit candidates from a single private call carried no quality bar, and no consumer reads `signature-bits.md` yet — so v0.2.0's "human-canonized humor" described a ceremony whose output nothing consumed. This release makes the honest state explicit and hardens the brain's labeling.

### Changed
- **Signature-bit canonization is PARKED.** Candidates are still mined, scored, and filed (schema unchanged, all `status: candidate`), but no canonization review runs until a consumer engine actually reads canon bits. Retires the 0.2.0 "human-canonized" claim.
- **Bit candidacy gained mechanical deployability gates:** portability (a line/setup that names call participants, the operator, or session context is not a candidate) + self-contained setup. **Canon floor:** canon requires recurrence across ≥2 independent sources — single-source brains hold zero canon, honestly.
- **Machine-readable overfit flag:** every brain artifact's stamp block gains additive `source_count` + `provisional` keys (`provisional: true` under 3 independent sources). `voice_confidence` enum unchanged. Consumers (voice-anchor, generator flow) treat provisional brains as hypotheses — surface age on read, offer a refresh once, never gate.
- **Mirror-language tier blessed into the schema with a consumer guard:** a coach's own client-experience phrasing lives in a labeled "Mirror Language (hypothesis)" subsection of `voc-profile.md` and is never quoted as avatar VoC.
- Signature-bit reaction evidence now carries strength (`explicit` vs `riff-along`); provisional-set ranking tiebreak formalized (multi-client attestation > in-call repetition > single mention); brand slug normalized (lowercase, no separators) with a similar-folder check so two engines can't mint two half-brains for one coach.

### Fixed
- Older brains written before these stamps upgrade lazily on next refresh touch (no silent stale labeling).

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
