# Changelog — shortform-superengine

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.2] — 2026-07-04

### Changed
- **Bundled `socialcrawl` skill is now a generated lean core** derived from the
  `socialcrawl-superengine` plugin's canonical skill: 12 reference files covering exactly
  the platforms this engine uses (Instagram, TikTok, YouTube, Facebook, Reddit, Google
  search/ads/trends/news, LinkedIn, Prism, universal search) with **exact per-call
  credits on every endpoint row** — including the Prism cheat codes (free URL resolver,
  1-credit batch post stats for 100 URLs, 1-credit full comments). 19 unused platform
  refs removed. The ⛔ transcript ban carries over verbatim (now covering all 9 banned
  endpoints, price-accurate).
- **SocialCrawl Superengine detection:** competitor-cross-reference (sourcing step),
  reel-scripter (Topic Pool), and onboarding (activation) now detect
  `~/.claude/socialcrawl-superengine/.superengine` and offer the deep research plays
  (ad-library recon, share-of-voice, audience-questions seeding) when the plugin is
  installed — one-line mention when it isn't, never a blocker.
- Onboarding: both-transcribers recommendation hardened (Groq + local Whisper both, so
  no reel falls through); updating guide rewritten dual-OS (Mac + Windows sync fixes).
- reel-scripter: Topic Pool mode ("20 ideas from the best performers" → evidence-cited
  weekly `topic-pool.md`); never-pay-for-transcripts guardrail.

## [0.2.1] — 2026-07-04

Premortem-driven hardening of the bundled `brand-brain` producer + reel-scripter's voice wiring (same premortem as email-sequence-superengine 0.2.1).

### Fixed
- **reel-scripter now checks the shared brand brain FIRST** — `~/.claude/revxl/<brand>/voc/` was missing from its voice-resolution ladder, so a brain built from another engine (e.g. email) was invisible to reel scripting. The cross-engine promise now actually resolves.
- Brand-brain tie-in doc no longer claims reel-scripter reads `weekly-content-bank.md` (it doesn't; topical seeds are handed inline after a mine/refresh).

### Changed
- **Signature-bit canonization is PARKED** (bundled brand-brain): candidates still mined + filed (schema unchanged), no canonization review until a consumer engine reads canon bits. Candidacy gained mechanical deployability gates (portability, self-contained setup); canon requires recurrence across ≥2 independent sources.
- **Machine-readable overfit flag:** brain stamp blocks gain additive `source_count` + `provisional` keys; reel-scripter treats `provisional: true` brains as hypotheses, surfaces brain age on read, offers a refresh once, never gates scripting.
- **Mirror-language guard:** reel-scripter never quotes `voc-profile.md` "Mirror Language (hypothesis)" entries as audience VoC.
- Bit reaction evidence carries strength (`explicit`|`riff-along`); ranking tiebreak formalized; brand slug normalized with a similar-folder check.

## [0.2.0] — 2026-06-30

### Added
- **`brand-brain` skill (bundled shared producer)** — same producer bundled in email-sequence-superengine v0.2.0. Mines a client's real sources (Fathom/Fireflies recordings, own social, Meta DM export, guided-interview floor) into the shared brand brain at `~/.claude/revxl/<brand>/voc/` (voice-guide, voc-profile + evergreen seeds, shared business-config, signature-bits, weekly-content-bank). Idempotent detect-and-reuse: if the brain exists (built from ANY engine), it reuses/refreshes, never re-mines. reel-scripter's detect-and-prefer path now has its producer in-box.

### Changed
- **onboarding step 4b:** when no brand brain exists, offers to build it now with the bundled `brand-brain` skill (was: "fast-follow, not installed yet" message).

## [0.1.1] — 2026-06-26

### Added
- **`socialcrawl` skill bundled** — the full SocialCrawl API reference (27 platforms, 28 endpoint files) now ships inside the plugin, so onboarding no longer depends on a separately-installed global skill. Documents the Instagram `&max_id` pagination contract + a transient-failure retry note.
- **`onboarding`**: Node.js prerequisite check; new `references/troubleshooting.md` (antivirus install-block workaround, restart-via-Task-Manager, MCP-won't-attach recovery); SocialCrawl referral sign-up link.

### Changed
- **`competitor-cross-reference`**: pre-flight now shows live credit balance + estimated cost + confirm before any spend; expands a 2–3 handle seed to the ~25-competitor floor instead of accepting a thin set.

### Fixed
- Onboarding no longer dead-ends when a client lacks the global `socialcrawl` skill — the root cause of an Instagram scrape failure observed during a live client onboarding.

## [0.1.0] — 2026-06-24

### Added
- Initial release. Format engine #1 of the RevXL content family (shared analysis core bundled for now; splits out at format #2).
- **`onboarding`** — guided one-time setup: runtime + transcription-tier detection (yt-dlp captions floor + Groq / local faster-whisper), gate rule (captions + at least one real transcriber), bring-your-own-key SocialCrawl wiring with a client click-path, default beginner teach mode, state marker, and end-to-end verify.
- **`competitor-cross-reference`** — Instagram client-vs-competitor reel cross-reference → 10-section, client-facing strategy roadmap. Deterministic, regression-locked metrics engine; captions-first optional transcription (portable chain, no private infra).
- **`creator-strategy-harvest`** — harvest a trusted creator's full library (YouTube channel + playlists + newsletter) into a dated, recency-ruled, framework-extracted corpus for a knowledge vault (captions-first).
- **`reel-scripter`** — analysis-driven IG reel scripting: ranks proven niche moves from a cross-reference run and guides an in-voice Hook → Secondary → Body → Proof → CTA script with caption, flow-check, and craft scoring.
- **`/teach-mode`** command + shared teach-mode convention (`~/.claude/revxl/teach-mode`, `beginner` / `off`) — plain-English-first end-user voice by default, switchable.
- Skills chain forward: onboarding → competitor-cross-reference → reel-scripter.
