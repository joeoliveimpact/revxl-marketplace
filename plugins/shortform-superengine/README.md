# shortform-superengine plugin

RevXL **Short-form superengine** ... format engine #1 in the content family. Turns
competitor intelligence, the client's own material and this week's signals into
Instagram reel scripts in their brand voice. One front door, four exits, no dead
ends. (The shared analysis core is bundled here for now; it splits into its own
plugin at format #2.)

**10 skills**, grouped by the stage of the journey they serve:

**Start here**

- **`shortform-start`** ... the front door. Say "start shortform" and it asks what
  you are here for, then puts you on the road that goal needs. On a machine set up
  under 0.3.x it carries your setup over, pulse schedule included, without asking
  you anything twice.
- **`shortform-next`** ... the compass. Say "what's next in shortform" at any point
  and it reads where you actually are and ranks the two to four moves that make
  sense from there. It writes nothing, so ask it as often as you like.
- **`onboarding`** ... one-time first-run setup: detects what is on the machine,
  installs the transcription chain (Groq plus local Whisper, `yt-dlp` for the
  harvest fetch), wires the SocialCrawl key, sets the teach level, writes the setup marker
  and verifies end to end. Run this first.

**Voice**

- **`brand-brain`** ... mines the client's real sources (calls, posts, captions)
  into the shared brand voice at `~/.claude/revxl/<brand>/voc/`: voice guide,
  pillars, and a weekly bank of topics they already talk about.

**Field**

- **`competitor-cross-reference`** ... cross-references a client's Instagram reels
  against tiered competitors into a 10-section strategy roadmap (regression-locked
  metrics engine) **plus an offline HTML visual pack** (overview dashboard,
  per-competitor profiles, client profile ... self-contained, client-brandable).
- **`creator-strategy-harvest`** ... harvests a trusted creator's full library
  (YouTube plus newsletter) into a dated, recency-ruled, framework-extracted
  corpus, from real subtitle tracks rather than paid transcription.

**Make**

- **`content-plan`** ... the weekly plan: 7 to 15 source-tagged ideas drawn from
  four sources (the field's outliers, the client's own material and VoC, fresh
  signals, audience questions), balanced across their pillars and deduped against
  everything already scripted.
- **`reel-scripter`** ... analysis-driven reel scripting: ranks proven niche moves,
  then guides an in-voice Hook to CTA script with craft scoring.

**Pulse**

- **`competitor-pulse`** ... the weekly heartbeat on a finished analysis:
  last-7-days delta pull (credit-gated), winners flagged, charts refreshed, a "what
  changed this week" brief; roster add, remove and swap; field keyword search;
  comment mining. Scheduling is suggested, never silent.

**API**

- **`socialcrawl`** ... the bundled SocialCrawl API core the other skills call:
  key resolution, the per-platform endpoint references, the cheat codes that
  change the cost math, and the credit gates. It makes the call and reports what
  it cost.

## No dead ends

Every terminal path ... success, decline, empty result, degraded run, refused
prereq ... ends in a **Next moves** block: two to four numbered options, most
likely first, each carrying the exact phrase to say next. The edges live in
`skills/_shared/references/journey-map.md` and the block grammar in
`routing.md`, so a phrase is never invented at the point of use. Say
**"what's next in shortform"** at any time for the same block on demand. The four
exits the journey aims at are a scripted reel, a competitor analysis and roadmap,
a weekly content plan, and a read on your own results (through the pulse until
the dedicated read ships in 0.5.0). `scripts/check_routing.py` runs in CI and
fails the build when a block goes missing, sits past the point a long file gets
truncated, or leaves a registry edge that no block cites. A phrase that leads
nowhere is a warning, not a failure.

## Requirements

Bring-your-own SocialCrawl key (your data, your credits). The API skill is
bundled (`skills/socialcrawl/`, with the per-platform endpoint references);
socialcrawl-superengine, when installed, executes the searches. The calls the
pipeline itself makes, and what each one costs, are listed in
`skills/_shared/references/socialcrawl-endpoints.md`. Anything deeper than that
table ... field search beyond your own roster, creator vetting, share of voice,
lead finding ... lives in **socialcrawl-superengine**, and this plugin tells you
so in writing rather than faking it. Live RevXL Vault pulls need
**workspace-superengine 0.15.1 or later** (the 0.15.0 caller contract plus the
0.15.1 skill map); without it every skill says so in one line and runs on its
bundled references.

Commands:

- **`/teach-mode new|learning|pro`** ... switches the assistant's end-user voice:
  `new` (plain-English first, explains terms), `learning` (some fluency assumed)
  or `pro` (standard voice). Shared across every installed RevXL superengine and
  persists across sessions.

## Hooks

Two hooks ship in `hooks/hooks.json`:

- **Skill nudge** (`UserPromptSubmit`, `hooks/skill-trigger.sh`) ... when a prompt
  contains one of the skills' unmistakable trigger phrases ("what's next in
  shortform", "start shortform", "script a reel", "script idea 3 from my content
  plan", "plan my week", "competitor cross-reference", "build my brand brain",
  "run the weekly pulse", "harvest <creator>'s library", "onboard shortform"), it
  adds one line naming the skill to invoke instead of doing the work by hand.
  Silent on everything else; exit 0 always; fail-open on empty or malformed
  input. Ceiling: it fires in Claude Code (terminal and Desktop, verified on
  Windows Desktop 09.04.26) and never in Cowork, which does not load plugin hooks.
- **Credit guard** (`PreToolUse` on `Bash`, `hooks/credit-guard.mjs` plus
  `hooks/costs.json`) ... the same file socialcrawl-superengine ships:
  hard-denies the banned `*/transcript` endpoints and asks before metered or
  >=5-credit SocialCrawl calls. The two copies must be updated together. Same
  Cowork ceiling as above.
