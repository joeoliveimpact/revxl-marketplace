# Changelog — shortform-superengine

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] — 2026-07-10 (proposed ship: 0.3.0)

### Added
- **Visual deliverables layer.** New deterministic renderer
  `competitor-cross-reference/render_visuals.py`: `analysis-data.json` →
  self-contained offline HTML at `<project>/visuals/` — **overview.html**
  (stat cards, reach-efficiency ladder, tier scoreboard, hooks + themes
  field-vs-client, followers×views map, cadence, opportunity map, gap cards,
  outlier wall, this-week panel), **competitors.html** (profile picker;
  `--split` writes standalone per-competitor pages for client delivery),
  **client.html** (profile + hook mix + the written roadmap inlined).
  Chart.js 4.4.7 vendored + inlined (zero network in output); dataviz-validated
  CVD-safe palette; table-view twin per chart; every JSON string HTML-escaped;
  brand tokens via optional `<project>/visual-theme.json`; `--prev` computes
  `whats-new.json` deltas; client trend charts once `history/` has ≥2 snapshots.
- **`competitor-pulse` skill (new, 5th user-facing).** The weekly heartbeat:
  snapshot → priced listing pass (✋ before any spend) → winners-only deep legs
  (✋, capped) → additive merge → re-analyze → refreshed visuals → cited
  "what changed this week" brief. Plus: **roster ops** (add/remove/swap with
  tier-balance check; removal moves data to `retired/` so no analysis ghosts),
  **field search** (free local-corpus keyword search first; live legs offered
  cost-labeled), **comment-pulse** (single post / creator last-N / field
  winners → deterministic word-frequency tables + quote-receipted opinion,
  objection, and question mining at ~5cr/post on IG — live-verified native
  delegation, not the 1cr doc price), and an optional-research-legs price
  table. Weekly schedule is SUGGESTED only (Step 4c pattern) — a
  scheduled run still stops at the credit checkpoint.
- **"Next moves" mesh — no dead ends.** Every pipeline skill now ends every
  terminal path (including declines and empty weeks) with 2–4 exact-trigger
  next-step offers; schedulable items are asked, never auto-set. Convention +
  E1–E16 edge registry: `skills/_shared/references/next-moves.md`. Closed dead
  ends: reel-scripter post-script + topic-pool no-pick, brand-brain
  refresh-decline + interview floor, harvest post-manifest, cross-reference
  checkpoint stops.
- **Schema 1.1 (additive).** `analysis-data.json` gains per-creator + client
  `hook_mix` ({hook_type: count}); versioning rules documented in the contract
  (minor = additive-only, consumers ignore unknown keys; major = hard stop).
  md + stdout verified byte-identical (regression gate).
- **RevXL Brain wiring (living knowledge API).** reel-scripter now pulls current
  content-strategy intelligence from Joe's Brain API (`brain.engineforimpact.com`)
  at exactly two named triggers — brief build (0d) and hook step — with a hard
  per-reel budget (≤2 searches + ≤3 note reads), a project-local cache
  (`<project>/brain-pulls/`), and full degrade to the bundled reference files when
  the key is missing/inactive or the API is unreachable. Key resolution mirrors
  SocialCrawl: env `VAULT_API_KEY` → `~/.config/revxl/vault_api_key` → ask-once+save.
  New shared reference: `skills/_shared/references/vault-api.md`. Onboarding Step 3
  gains an optional "RevXL Brain" wiring block (key issued by Joe; never blocks).
- **Brain API v1.1 — full hub-search surface** (live-verified over HTTPS 07.10.26):
  search gains `mode` (hybrid/semantic/fulltext/title), `path` similarity ("more like
  this note"), `tags`/`scope`/`frontmatter` filters with `-` exclusions, `threshold`,
  `rerank`, `snippet_length`; new `/v1/related` (graph traversal, depth ≤2); `/v1/note`
  reads up to 3 notes per call (+`raw`, `related:false`), returns links + backlinks.
  Budgets unchanged (each read path = 1 unit).

### Changed
- **Transcription is now ON by default and automatic** (was: off, opt-in). Spoken
  transcripts are the primary analysis text; an IG post caption is metadata, NOT what
  the creator says on camera — caption-only analysis is a flagged degrade, never a
  silent substitute. (Root cause of the 07.09 client run that analyzed captions.)
- **Parallel transcription:** Groq + local Whisper launch together, first healthy
  transcript wins (was: sequential fallback with captions preferred). `yt-dlp` is the
  fetch floor; platform subtitle track → post caption only when both engines fail,
  with a `caption-only` flag on every output that cites that reel.
- Automatic scope: all client reels + every outlier + each competitor's top performers;
  full-fleet expansion offered (free chain — runtime warning, not credits).
- competitor-cross-reference intake: `Transcript opt-in (off)` → `Transcription (on —
  automatic, explicit opt-out only)`.
- onboarding Step 2 reframed: transcription is the heart of the system, not garnish;
  gate rule now names yt-dlp the *fetch* floor (not "captions floor").
- creator-strategy-harvest + YouTube ref wording: YouTube subtitle tracks are real
  spoken-word transcripts (distinct from the IG post-caption shortcut); behavior unchanged.

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
