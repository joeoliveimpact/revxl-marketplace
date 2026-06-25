# shortform-superengine plugin

RevXL **Short-form superengine** — format engine #1 in the content family. Turns competitor + creator intelligence into platform-ready short-form video scripts in the client's brand voice. (The shared analysis core is bundled here for now; it splits into its own plugin at format #2.)

Four skills ship today:

- **`onboarding`** — one-time first-run setup: detects what's on the machine, installs/offers the transcription tools (captions-first → Groq → local Whisper), wires the required SocialCrawl key, sets the default end-user voice (teach mode), writes a setup marker, and verifies end-to-end. Run this first.
- **`competitor-cross-reference`** — cross-references a client's Instagram reels against tiered competitors into a 10-section strategy roadmap (regression-locked metrics engine).
- **`creator-strategy-harvest`** — harvests a trusted creator's full library (YouTube + newsletter) into a dated, recency-ruled, framework-extracted corpus for vault ingestion (captions-first).
- **`reel-scripter`** — analysis-driven Instagram reel scripting: ranks proven niche moves from a cross-reference run and guides an in-voice Hook→CTA script with craft scoring.

Commands:

- **`/teach-mode beginner|off`** — switches the assistant's end-user voice: `beginner` (plain-English-first, explains terms) or `off` (standard voice). Defaults to `beginner` on first install; persists across sessions.
