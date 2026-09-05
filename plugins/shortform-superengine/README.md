# shortform-superengine plugin

RevXL **Short-form superengine** — format engine #1 in the content family. Turns competitor + creator intelligence into platform-ready short-form video scripts in the client's brand voice. (The shared analysis core is bundled here for now; it splits into its own plugin at format #2.)

Five user-facing skills ship today:

- **`onboarding`** — one-time first-run setup: detects what's on the machine, installs/offers the transcription tools (Groq + local Whisper in parallel, `yt-dlp` fetch floor), wires the required SocialCrawl key (+ optional RevXL Brain key, connected through workspace-superengine's `revxl-brain-search`), sets the default end-user voice (teach mode), writes a setup marker, and verifies end-to-end. Run this first.
- **`competitor-cross-reference`** — cross-references a client's Instagram reels against tiered competitors into a 10-section strategy roadmap (regression-locked metrics engine) **plus an offline HTML visual pack** (overview dashboard, per-competitor profiles, client profile — self-contained, client-brandable).
- **`competitor-pulse`** — the weekly heartbeat on a finished analysis: last-7-days delta pull (credit-gated), winners flagged, charts refreshed, "what changed this week" brief; roster add/remove/swap; field keyword search; comment mining. Scheduling is suggested, never silent.
- **`creator-strategy-harvest`** — harvests a trusted creator's full library (YouTube + newsletter) into a dated, recency-ruled, framework-extracted corpus for vault ingestion (YouTube subtitle tracks — real spoken-word transcripts, fetched in seconds).
- **`reel-scripter`** — analysis-driven Instagram reel scripting: ranks proven niche moves from a cross-reference run and guides an in-voice Hook→CTA script with craft scoring.

Every skill ends with **Next moves** — exact-phrase offers for the natural next step (registry: `skills/_shared/references/next-moves.md`). No dead ends.

**Bundled dependencies** (used by the skills above, not invoked directly): **`brand-brain`** — mines the client's real sources into the shared brand voice at `~/.claude/revxl/<brand>/voc/`; **`socialcrawl`** — the bundled SocialCrawl API reference the data layer runs on.

Commands:

- **`/teach-mode beginner|off`** — switches the assistant's end-user voice: `beginner` (plain-English-first, explains terms) or `off` (standard voice). Defaults to `beginner` on first install; persists across sessions.
