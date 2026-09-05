# Changelog — shortform-superengine

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.4.0] ... 2026-09-05

### Changed
- **Brain calls go through `revxl-brain-search`.** The wiring reference keeps its name
  and the shortform specifics (the per-reel budget, the project cache, the evidence line)
  and drops its own key ladder, the three curl blocks and the error table. Those live in
  one place for every RevXL plugin now: the `revxl-brain-search` skill in
  workspace-superengine 0.14.0, which also logs every call and tells the three 429
  reasons apart. reel-scripter's two trigger points invoke it by name; onboarding runs
  the skill's connection test instead of its own health check. The `content-strategy`
  spoke is now named explicitly on every call, so a wrong-vault answer is caught
  (before, the server default was relied on with no guard).
- Requires workspace-superengine 0.14.0 or later for live Brain pulls; without it the
  engine degrades to its bundled references and says so once.

## [0.3.3] — 2026-09-04

### Fixed
- **The 08.28 breakout-engine fix is now actually in the repo.** It was applied to
  the marketplace working tree and hand-patched into client caches on 08.28.26 and
  never committed, so every fresh install and every update kept the old ranker.
  Four files land byte-for-byte:
  - `analyze.py` — the client's own reels are excluded from the field outliers
    (Joe's ruling 08.28.26), so the brief can no longer recommend a pairing whose
    only evidence is a reel the client already posted; `outliers_full` is emitted
    alongside the capped list.
  - `scripting_brief.py` — reads `outliers_full`. The 30-row cap hid 483 of 513
    qualifying field reels from the theme × hook table.
  - `analysis-data.schema.json` — schema 1.3 (`outliers_full`, `period_breakouts`,
    `meta.generated_at`).
  - `render_visuals.py` — accepts schema 1.3, and **GURU joins `TIER_ORDER`**
    (SKLLPLG-262). `analyze.py` computed the tier; the renderer silently dropped it.
- **VAD enabled on the local faster-whisper path** (`transcribe_reels.py`,
  SKLLPLG-259). `vad_filter` defaults to False and was never set, so trailing
  silence decoded into invented sentences, sometimes in another language. Measured
  at roughly 8% of reels before the fix. `vad_filter=True` only: no batching, no
  VAD tuning, no `condition_on_previous_text` change (unmeasured; tracked
  separately). `onnxruntime` already ships with faster-whisper, so nothing new to
  install.

## [0.3.2] — 2026-08-17

### Added
- **brand-brain reference `transcription-vocabulary.md`.** How to turn the names
  already mined into `voc/business-config.md` and the `## Vocabulary` block of
  `voc/voice-guide.md` into a Whisper/Groq vocabulary prompt — and the two ways
  that prompt backfires (a bare comma list strips punctuation from the entire
  transcript; a prompt can drop a speaker's retakes, so compare output length).
- Guidance at both points that reach for Groq (`onboarding`,
  `competitor-cross-reference`), including preferring `whisper-large-v3-turbo`
  over full `large-v3` — no worse on proper nouns, ~3x cheaper, and it did not
  lose speech with a prompt where full v3 dropped 219 characters.

### Why
Measured across 48 minutes of real audio transcribed without a vocabulary: the
correct brand name appeared 3 times against 18 mangled ones. In one case a
reviewer read a mangled product name as the speaker stumbling and marked 9.4s
for deletion.


## [0.3.1] — 2026-07-21

### Added
- **C19 — secondary-hook dosage is a mandatory computation (Step 3).** The
  secondary-hook section now computes the placement COUNT from the length
  target via retention-psychology §4's dosage table (30s→1 · 45s→1–2 ·
  60s→2–3 · 90s→3–4) BEFORE generating, with 3 scored options per slot —
  never a single placement on a 60s+ reel. Dogfood catch (07.16.26, JOI-001):
  a 63s listicle shipped one secondary; the user hand-added the missing two
  exactly where the table places them. Sixth instance of the
  documented-but-optional-craft pattern (C15–C18).

## [0.3.0] — 2026-07-16

### Added — 2026-07-15 pm dogfood batch (C15–C18: implied craft → enforced screens)
- **C15 — mandatory skeleton-optimization pass (Step 2).** The beat skeleton is
  screened BEFORE Checkpoint 2 against four checks (one idea not a list · length
  budget · one loop paid late · single lever), presented pre-tightened with a
  one-line why per trim. Users approve an optimized skeleton, never a raw dump.
- **C16 — custom-idea field vet (`field_vet.py`, Step 1).** A user-supplied topic
  is vetted against the field before beats are committed: per-keyword spoken-track
  median vs field median (captions reported separately, never merged — the C7
  weighting), WINNER/NEUTRAL/LOSER/UNTESTED verdicts. Topic-level twin of the §8
  hook-type firewall. The idea is never vetoed — only the framing adapts.
- **C16b — LOSER vs UNTESTED branching.** LOSER (has data, underperforms) →
  pivot with 2–3 data-backed adjustments, user picks. UNTESTED / THIN (n<5) →
  NOT a loser: possible first-mover edge; de-risk by riding the novel topic on a
  proven hook type + nearest proven frame word. No data ≠ bad idea.
- **C17 — mandatory loop-integrity check (Step 4b).** Walks every beat seam and
  fails on dead-seam / early-close / flat-run before Checkpoint 4. Rule: from
  hook to CTA there is never a moment with zero open loops; the spanning loop
  resolves in the final beat.
- **C18 — Swap #8: second-person default (story-locks).** Every teaching /
  benefit / stakes line asks "can this be `you`, not `I`?" — first person kept
  ONLY for the creator's own proof/testimony. Vault-backed (viewer-as-protagonist).

### Added — 2026-07-15 batch (C-gate fixes + cheap enhancements)
- **C7 — dual-track analysis (schema 1.2, additive).** analyze.py now keys hook/
  theme/hook-line diagnosis on the SPOKEN transcript when one exists (per-reel
  caption fallback, marked `src`); the caption-keyed read ships as a separate
  "Caption patterns" md section + JSON `captions` bucket (packaging/SEO surface —
  never merged into the spoken diagnosis). `meta.transcript_coverage` reports
  degraded runs. Caption-only datasets stay byte-identical (regression gate).
- **C10 — scripting_brief.py reads live pipeline shapes.** `{reels}` top key
  native (legacy `{items}` fallback), JSON transcript ingest
  (client-transcripts.json + competitors/transcripts/*.json) when no txt
  transcripts exist — kills the caption-only "0 reels" failure.
- **C13 — text-overlay storyboard.** Step 3 gains a scored storyboard section
  (2 options, beat→overlay table 1:1 on the frozen skeleton, frame-1 = hook
  verbatim, ≤6 words/line, silent-scroll test); Step 5 template gains
  `## Text overlays`.
- **C12 substance layer explicit.** Client-topic reels REQUIRE a per-beat
  interview before generation; unanswered beats flagged, never invented.
- **C2** three-tier outlier cross-tab in `_pattern_stats.md`; **C4** 4-Killers
  validation note (120-reel corpus: 9/12 losers, 0/12 winners); **C5** blueprint
  synthesis-format template in pattern-matrix.md.
- **Wording:** Brain rebranded "Joe's Content Strategy Cloud Brain API"
  (constantly updated — the plugin double-checks current strategies);
  coach→client/brand-owner genericization (users may not be coaches).

### Added
- **Pattern Matrix — two-layer beat/pattern measurement (Step 4c).** Three new
  scripts in competitor-cross-reference, all config-driven (niche knowledge stays
  in the run's `analysis-config.json`, never in the plugin): `transcribe_reels.py`
  (batch transcription **straight off the pulled CDN URLs — no downloading, no
  yt-dlp**; parallel ffmpeg prefetch → faster-whisper; resume-safe; saves
  per-segment timestamps), `extract_patterns.py` (Layer 1: ~30 deterministic
  dims/reel — timing, rhetoric, CTA mechanics, caption↔spoken relationship,
  engagement joins — with auto winner-vs-loser lift tables, tool league, CTA
  payoff cross-tabs), `select_beatmap_set.py` (Layer 2: stratified N winners +
  N losers per cluster for Claude's semantic hand-map → Reel Beat Blueprint).
  New references: `pattern-matrix.md` (method + dims), `theme-derivation.md`
  (how to build a lane's `themes` override — method, not preset). Field-proven
  on a 1,000-reel corpus 07.12.26.
- **GURU competitor tier (4th, optional).** ≥500k-follower / household-authority
  accounts split out of LARGE so mega-accounts stop skewing the size-comparable
  benchmark (essential for small clients). analyze.py reads an optional `GURU`
  key in tiers.json/analysis-config.json — absent key = byte-identical legacy
  3-tier path. Documented in Step 2c + 4a.
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
  content-strategy intelligence from Joe's Content Strategy Cloud Brain API
  (constantly updated, so scripts are always
  double-checked against current strategies)
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
- **analyze.py read 0 reels from real pulled data (silent all-zero analysis).**
  `reels_of()` only accepted the mock `{items:[…]}` wrapper; the live puller writes
  `{handle,count,reels:[…]}`. Now accepts `reels` → `items` → `data.items`.
  Found on the first real-corpus run 07.12.26 — the engine had only ever been
  validated against synthetic harness data.
- **Cadence was always 0.0/wk on real data.** `cadence()` required epoch timestamps;
  the live API returns ISO-8601 `published_at`. New `_epoch()` helper accepts both.
- **Transcription step no longer instructs downloading.** The old text said to
  resolve videos via `yt-dlp`/instaloader — wrong and risky. The pulled reel JSON
  already carries the direct IG CDN `.mp4` (`post.content.media_urls`); ffmpeg
  streams it directly. Rewrote the step with the CDN-expiry rule (transcribe
  same-day or re-pull, ~3cr) and the segment-timestamps requirement.
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
