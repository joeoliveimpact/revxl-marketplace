# Changelog — shortform-superengine

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
