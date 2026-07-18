---
name: carousel-superengine:carousel-setup
description: First-run wizard for the carousel engine. Captures brand voice, avatar pains, platform defaults, content pillars, CTA destination, and the optional SocialCrawl key into the business config every build reads. Trigger phrases include "set up the carousel engine", "carousel setup", "configure carousels", "reconfigure my carousel config".
---

# Task: setup

First-run wizard. Capture config, write it to `${CLAUDE_PLUGIN_DATA}/business-config.md` (persists
across plugin updates — this is the copy every other skill reads first).

## Load
${CLAUDE_PLUGIN_DATA}/business-config.md when present (existing persisted config — reconfigure runs start from it)
${CLAUDE_PLUGIN_ROOT}/references/business-config.md (the shipped template/schema this wizard fills)

## Ask + write each key
Ask conversationally, per `{{EXPLANATION_LEVEL}}`. Push for CONCRETE phrasing in the coach's words, not categories ("my clients say they've tried everything and their body just doesn't respond anymore," not "weight loss struggles"). Specific avatar language is what makes a broadcast carousel feel personal.

**A. Tone + brand**
1. **Explanation level** — beginner / intermediate / advanced (default beginner). How much jargon I translate.
2. **Teach mode** — on (default) / off. Plain: "As I build, I explain WHY each move works... why this hook, why this slide order... so you learn the craft, not just get the slides. Want it on?"
3. **Program + positioning + audience** — who they serve, one-line positioning.
4. **Brand voice** — detect-if-exists first, in order: (a) the shared brand brain `~/.claude/revxl/<brand>/voc/voice-guide.md` — if present, use it and skip interim capture; (b) any other voice-guide path the user has. Neither → note interim anchor sources AND offer to run the bundled `brand-brain` skill (mines their real calls/content into a durable, cross-engine brain).
5. **Voice edge** — `{{VOICE_EDGE}}` dial: vanilla → conversational → locker-room. Match the coach's actual register; edge is a setting to match, not a risk to sand down.

**B. Avatar (the specificity engine)**
6. **Top shared pains** — 3-5, in the avatar's words (these become hooks + slide content).
7. **Dream outcome in STATUS terms** — how they want to be SEEN, not just what they want.
8. **The enemy** — named villain the avatar already resents (a method, a guru type, an industry norm). Powers myth-bust and us-vs-them carousels.
9. **Awareness level** — problem-aware / solution-aware / product-aware (shapes hook archetype choice).
10. **Proof assets** — specific client results WITH numbers (feeds case-study carousels; never invented).

**C. Platform + content**
11. **Primary platform** — instagram (default) / linkedin / both. Sets format defaults per ${CLAUDE_PLUGIN_ROOT}/references/platform-nuance.md.
12. **Content pillars** — 3-5 recurring themes the coach wants to own.
13. **CTA destination** — where carousels drive: DM keyword (default for coaches), lead magnet link, profile follow, community, or per-build (decide per carousel from competitor data — needs an inspire run; until one exists, create resolves the destination at each build's frame lock). One primary; the CTA slide always points somewhere real.

**D. Data sources (optional, can skip and add later)**
14. **SocialCrawl key** — needed only for `carousel-teardown` / `carousel-inspire` pulls. Resolution order: env `SOCIALCRAWL_API_KEY` → `~/.config/socialcrawl/api_key` → offer the 2-minute click-path in ${CLAUDE_PLUGIN_ROOT}/references/socialcrawl-key-setup.md. Skipping is fine; create works without it.
15. **Full-slide fetch setup** (Claude Code only) — full-slide teardown needs Python 3.10+ and the client's own Instagram cookies. No install, no browser script — the fetch is stdlib-only. Check `python --version` ≥ 3.10. If present, OFFER to capture cookies now: walk the client through the 2-minute Cookie-Editor export in ${CLAUDE_PLUGIN_ROOT}/references/ig-cookie-setup.md, save the pasted JSON to `${CLAUDE_PLUGIN_DATA}/ig_session.json`, and mark `{{FULL_SLIDE_FETCH}}: available`. Skipping is fine — teardown falls back to the SocialCrawl cover path, and cookies can be pasted later at first teardown. Refresh only when a fetch reports `login_required` (no scheduled expiry). On Cowork/Desktop (no local Python) mark `unavailable`.
16. **Call transcripts** — `{{TRANSCRIPT_SOURCE}}`: does the coach record calls (Fathom, Fireflies, Granola…)? Connected service → name it; otherwise `manual` (paste when needed — default). Plain: "If your calls get recorded, I can turn this week's client questions straight into carousels."

**E. Output + rendering**
17. **Output destination** — chat draft (default) / workspace file / both.
18. **Render preference** — `{{RENDER_PREF}}`: when a build finishes, images via image-gen (A) / Claude Design prompt (C) / ask each time (default). Plain-English the two: "A = I generate the finished slides, optionally with YOUR face on them. C = I hand you one prompt; Claude's Design tool builds the cards on your existing plan."
19. **Environment detect (silent):** Bash + Python available → `{{WORKSPACE_RENDER}}: available` (unlocks local PNG/PDF rendering — see the `carousel-render` skill); Cowork/Desktop → `unavailable`. Higgsfield: probe the **MCP first** (ToolSearch for `generate_image` / `models_explore` / `balance` — server prefix varies; a ToolSearch hit alone isn't proof — confirm with one free read like `balance`, and an auth error means NOT connected), then the `higgsfield-generate` skill/CLI. Either confirmed reachable → `{{HIGGSFIELD_STATUS}}: detected` (note which route: `mcp` / `cli`), else `absent`. **When the MCP is up, also check for an existing trained Soul** (`show_characters`, status ready) — one found → record its name + soul_id in the config so renders use it automatically instead of re-asking. Never make the coach answer what the machine can tell us.
20. **Existing design system?** — brand templates / Canva kit / a past carousel look they love → offer to capture it now via `carousel-templates` (import variant): "Save your look once and every build after this skips the design questions." Nothing to import → pick a **starter palette direction** (wellness-warm / dark-tech spec-sheet / editorial / bold-color — see design-rules.md) so builds never default to someone else's niche aesthetic; record hex values when the coach has them.
21. **Soul (optional, only when `{{HIGGSFIELD_STATUS}}: detected` AND no ready Soul was found in Q19)** — plain-English offer, never a gate:
    "One optional extra: I can train the AI on your face — a few photos, one time, about 5 minutes. After that, every image we generate is actually YOU... your real face, in any style we build. Without it we can still match your look from reference photos; it's just less consistent slide to slide. You can skip now and add it any time. Heads up: needs a paid Higgsfield plan." Yes → route to the `higgsfield-soul-id` skill. No/skip → note it, move on, re-offer exactly once at the first Path A render.

**F. Scheduled builds (seed only — never ask at setup)**
Write section F into the config as `{{SCHEDULE_STATUS}}: unset` (plus empty cadence/source/template/render/handle fields per business-config.md). The autopilot OFFER happens later at natural exits (after a render, after a template save) — setup just plants the fields.

> For beginners, OFFER 2 passes: essentials now (1-6, 11, 13, 17), the deeper avatar fields (7-10) next session. Flag that the deep fields are what make carousels convert, not just look right.

## Finish
- Write all values into `${CLAUDE_PLUGIN_DATA}/business-config.md` (the exact write target — never into the plugin's references copy, which is the template). Brand-level tokens (avatar, positioning, proof) also read/write the shared `~/.claude/revxl/<brand>/voc/business-config.md` when present — engine-specific keys (platform, pillars, CTA destination, data sources, rendering, schedule) stay in `${CLAUDE_PLUGIN_DATA}/business-config.md`.
- Confirm back in plain English (per explanation level).

## Ends with (offer, never block)
- **Seed the niche data first** (when `{{SOCIALCRAWL_KEY_STATUS}}: saved`) → `carousel-inspire` —
  "Want me to study your niche before build #1? One pull (~cost named) seeds every build for
  ~30 days; without it the first build runs data-blind."
- **First build** → `carousel-create` — "carousel about ___"
- Hand-held tour instead → `carousel-guide` — "walk me through it"
- (When they named an existing design system in Q20 and skipped capture) "Import your look now?" → `carousel-templates` — "save my design system"
- (When voice came out thin/interim) "Capture your real voice from your calls + content?" → `brand-brain` — "build my brand brain"
