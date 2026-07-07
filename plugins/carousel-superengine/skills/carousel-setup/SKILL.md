---
name: carousel-superengine:carousel-setup
description: First-run wizard for the carousel engine. Captures brand voice, avatar pains, platform defaults, content pillars, CTA destination, and the optional SocialCrawl key into the business config every build reads. Trigger phrases include "set up the carousel engine", "carousel setup", "configure carousels", "reconfigure my carousel config".
---

# Task: setup

First-run wizard. Capture config, write to business-config (persisted via `${CLAUDE_PLUGIN_DATA}`).

## Load
${CLAUDE_PLUGIN_ROOT}/references/business-config.md

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
13. **CTA destination** — where carousels drive: DM keyword (default for coaches), lead magnet link, profile follow, community. One primary; the CTA slide always points somewhere real.

**D. Teardown (optional, can skip and add later)**
14. **SocialCrawl key** — needed only for `carousel-teardown` link pulls. Resolution order: env `SOCIALCRAWL_API_KEY` → `~/.config/socialcrawl/api_key` → offer the 2-minute click-path in ${CLAUDE_PLUGIN_ROOT}/references/socialcrawl-key-setup.md. Skipping is fine; create works without it.
15. **Full-slide fetch setup** (Claude Code only) — full-slide teardown needs Python 3.10+ and the client's own Instagram cookies. No install, no browser script — the fetch is stdlib-only. Check `python --version` ≥ 3.10. If present, OFFER to capture cookies now: walk the client through the 2-minute Cookie-Editor export in ${CLAUDE_PLUGIN_ROOT}/references/ig-cookie-setup.md, save the pasted JSON to `${CLAUDE_PLUGIN_DATA}/ig_session.json`, and mark `{{FULL_SLIDE_FETCH}}: available`. Skipping is fine — teardown falls back to the SocialCrawl cover path, and cookies can be pasted later at first teardown. Refresh only when a fetch reports `login_required` (no scheduled expiry). On Cowork/Desktop (no local Python) mark `unavailable`.

**E. Output**
16. **Output destination** — chat draft (default) / workspace file / both.

> For beginners, OFFER 2 passes: essentials now (1-6, 11, 13, 16), the deeper avatar fields (7-10) next session. Flag that the deep fields are what make carousels convert, not just look right.

## Finish
- Write all values into business-config. Brand-level tokens (avatar, positioning, proof) also read/write the shared `~/.claude/revxl/<brand>/voc/business-config.md` when present — engine-specific keys (platform, pillars, CTA destination, teardown) stay in `${CLAUDE_PLUGIN_DATA}`.
- Confirm back in plain English (per explanation level).
- Offer to build the first carousel (route to `carousel-create`) or the guided tour (`carousel-guide`).
