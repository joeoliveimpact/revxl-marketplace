# Changelog... profile-optimization-superengine

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0]... 2026-07-13

### Added
- Initial release.
- **6 skills:** `profile-setup` (one-time onboarding wizard), `profile-start` (router... greets, offers setup, asks Facebook or Instagram or both, runs the environment detect once, hands off), `profile-fb-audit` (Facebook personal-profile audit), `profile-ig-audit` (Instagram personal-profile audit), `profile-competitor-scan` (optional SocialCrawl competitor benchmarks), and the bundled `brand-brain` voice producer.
- **Competitor benchmarks (`profile-competitor-scan`, optional):** pulls competitor FB + IG profiles via the SocialCrawl API (IG discovery via `search/profiles` + `similar`; pulls via `instagram/profile/full` / `facebook/profile/full`), extracts the same elements the audits score, and persists a benchmark layer to `${CLAUDE_PLUGIN_DATA}/competitors/benchmarks.md`. Both audits detect that file and weave the niche patterns into scoring notes and fixes... with NO hard dependency (absent = audits run exactly as before). Credit-gated with the full balance → estimate → confirm → report ritual authored in-skill; degrades gracefully with no key/marker and honestly states Facebook has no profile-discovery endpoint (FB competitors come from page URLs or reused IG handles). Needs a shell (Claude Code).
- **Persistent setup (`profile-setup`):** captures niche, ideal client, offer + lead magnet, DM keyword, platforms, account type (IG Creator/Business/Personal, FB Professional Mode), brand voice, and the teach-mode + voice-edge toggles ONCE into `${CLAUDE_PLUGIN_DATA}/business-config.md`. The router checks the `{{SETUP_COMPLETE}}` marker and offers setup first (skippable); both audits load the persisted basics and open by confirming instead of re-interviewing. The environment tier is deliberately NOT persisted... it is re-detected every session (a coach can set up in Cowork and later audit in Chat).
- **Facebook audit** scores 8 elements out of 80 (bio 101, profile pic + cover 320x320 / 820x360, Featured section, About, pinned post, CTAs, content pillars) plus a Professional Mode check, and delivers a prioritized action plan.
- **Instagram audit** scores 11 elements out of 110 (Name field 64, bio 150, profile photo, single link, Story Highlights, pinned trio, grid, account type, CTA/DM, SEO, content pillars).
- **Shared environment detect:** a silent capability probe classifies the session (Claude Code / Cowork Desktop / Claude.ai Chat), confirms the tier with the user, and branches the intake (live browser URL audit where a browser tool exists, screenshots otherwise, with login-wall degradation). `profile-start` runs it once; each audit skill reuses it or runs its own when invoked directly.
- **Single-direct-link standard (2026):** both platforms enforce ONE direct link to the lead magnet. Linktree, Beacons, and Stan appear only as a named anti-pattern to remove... Facebook and Instagram give identical link-strategy advice.
- **Bundled `brand-brain`:** derives a living, cross-engine voice brain at the shared `~/.claude/revxl/<brand>/voc/` location (Cowork/Code). On Claude.ai Chat, where no user filesystem persists, voice is captured inline for the session only and the coach is told the persistent brain needs the desktop app or Claude Code.
- **Teach mode (`{{TEACH_MODE}}`, on by default):** explains the WHY behind each fix in plain 8th-grade language so the coach learns to spot the leaks. Toggle anytime.
- **Config-driven:** `references/business-config.md` holds the toggles and persists via `${CLAUDE_PLUGIN_DATA}`; bundled docs resolve via `${CLAUDE_PLUGIN_ROOT}/...`.
- **Recommendations only:** never posts, never sends. B2C fitness/health/wellness vertical, REVXL voice, zero em dashes.

### Command naming
- Every command is prefixed `profile-` so the set groups under `/profile-` and never collides with another plugin's commands. Type `/profile-` to see the whole set.
