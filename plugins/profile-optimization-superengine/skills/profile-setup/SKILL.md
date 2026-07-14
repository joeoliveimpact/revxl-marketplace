---
name: profile-optimization-superengine:profile-setup
description: First-run wizard for the profile optimization engine. Captures the coach's niche, ideal client, offer + lead magnet, account type (IG Creator/Business/Personal, FB Professional Mode), which platforms they run, brand voice, and the teach-mode + voice-edge toggles into the business config both audits read... so the audits never re-ask the basics. Trigger phrases include "set up the profile engine", "profile setup", "configure profile optimization", "reconfigure my profile config".
---

# Task: setup

First-run wizard. Capture config ONCE, write it to `${CLAUDE_PLUGIN_DATA}/business-config.md` (persists across plugin updates... this is the copy every other skill reads first). The point: the audits skip Round 1 basics and open by confirming, not re-interviewing.

## Load
${CLAUDE_PLUGIN_DATA}/business-config.md when present (existing persisted config... reconfigure runs start from it)
${CLAUDE_PLUGIN_ROOT}/references/business-config.md (the shipped template/schema this wizard fills)

## 1. Branded intro (short)
Open with a tight, branded line and set expectations: this is a one-time setup so the audits don't make them repeat their niche, avatar, and offer every session. Keep it to a couple of sentences, then get moving. Honor `{{EXPLANATION_LEVEL}}` (default beginner) throughout.

## 2. Environment detect (silent, session-live... NOT persisted)
Run the SAME probe the audits use... do not narrate it, do not ask the coach what platform they're on:
- Shell/Bash present... **Claude Code** tier. No shell but a real browser tool present... **Cowork (Desktop)** tier. Neither... **Claude.ai Chat** tier.
- Separately confirm whether a real browser tool is present in-session (`mcp__Claude_Browser__*`, superpowers-chrome `use_browser`, browser-use, or playwright).

This tier decides ONLY the brand-brain behavior below and is thrown away at end of session. Do NOT write the tier into config. (See the "Session-live, NEVER persisted" note in business-config.md.)

## 3. Brand brain: detect-or-build (respects chat-tier degradation)
Reuse the tier from step 2:
- **Cowork / Code tier (a filesystem persists):** run the bundled `brand-brain` skill's detect-or-build... check `~/.claude/revxl/<brand>/voc/voice-guide.md` first, reuse if present, offer to build from the coach's real calls/content if absent. On build or reuse, set `{{BRAND_BRAIN_BUILT}}: persistent` and point `{{BRAND_VOICE}}` at the shared guide.
- **Claude.ai Chat tier (NO persistent user filesystem):** do NOT try to read or build the brain... it can't persist here. Capture voice inline for THIS session only (ask for 2-3 writing samples... a caption, a DM, a voice-note transcript) and tell the coach plainly the full persistent voice brain needs the Claude desktop app or Claude Code. Set `{{BRAND_BRAIN_BUILT}}: inline-session` and `{{BRAND_VOICE}}: inline`.
- If the coach declines entirely, set `{{BRAND_BRAIN_BUILT}}: none` and proceed... never gate setup on it.

## 4. Deep intake (captured ONCE)
Ask conversationally, grouped, per `{{EXPLANATION_LEVEL}}`. Push for CONCRETE phrasing in the coach's words, not categories ("my clients say the same 20lbs comes back every time they diet," not "weight loss struggles"). Specific avatar language is what makes the copy the audits write feel personal.

1. **Coaching niche** ... in their words (`{{NICHE}}`).
2. **Ideal client / avatar** ... age range, lifestyle, biggest struggle (`{{IDEAL_CLIENT}}`).
3. **Current offer + lead magnet** ... the program, and the free asset the single bio link will point to (`{{OFFER}}`, `{{LEAD_MAGNET}}`). No price stored... the coach supplies that live. If the coach has no named paid program yet and the free lead magnet is their only offer, that is fine... set `{{OFFER}}` to the lead magnet itself (not "none") so the audits treat the guide as the entry offer and never scold them for a missing program.
4. **DM keyword** ... propose one short shouty-caps word from the lead magnet (e.g. a "Metabolism Reset Starter Guide" ... RESET), confirm it, and store it (`{{DM_KEYWORD}}`) so every element uses the same one.
5. **Which platform(s) do you run?** ... Facebook, Instagram, or both (`{{PLATFORMS}}`).
6. **Current account type:**
   - If Instagram: Creator / Business / Personal (`{{IG_ACCOUNT_TYPE}}`). Note if not Creator... it's a critical quick win the audit will flag.
   - If Facebook: is Professional Mode on or off (`{{FB_PROFESSIONAL_MODE}}`)? Note if off... it's Priority Zero for the FB audit.

## 5. Toggles
- **Teach mode** ... on (default) / off (`{{TEACH_MODE}}`). Plain: "As I audit, I explain WHY each fix works in simple terms, so you learn to spot the leaks yourself, not just get the fixes. Want it on?" (See ${CLAUDE_PLUGIN_ROOT}/references/teach-mode.md.)
- **Voice edge** ... `{{VOICE_EDGE}}` dial: vanilla / conversational (default) / spicy / locker-room. Match the coach's actual register; edge is a setting to match, not a risk to sand down. Controls how bold the bio / CTA / About copy reads.

## 5b. Optional: competitor benchmark scan (offer, never force, credit-gated)
Offer, don't push: "Optional... I can scan a few top accounts in your niche and benchmark your profile against them ('4 of 5 use a keyword Name field... you don't'). It uses the SocialCrawl API, which costs a small amount of the coach's own credits, so it's opt-in and I'll show you the cost before spending anything. Want to set that up now, or skip and add it later?"
- Yes → route to `profile-competitor-scan` (it runs its own key-resolution + credit ritual). On success it writes `${CLAUDE_PLUGIN_DATA}/competitors/benchmarks.md` and stamps `{{COMPETITORS_SCANNED}}`.
- No/skip → fine. Leave `{{COMPETITORS_SCANNED}}: none`. The audits run without benchmarks and can add the scan any time. Never gate setup on it.

## 6. Finish (persist + confirm)
- Write all values into `${CLAUDE_PLUGIN_DATA}/business-config.md` (the exact write target... never into the plugin's `${CLAUDE_PLUGIN_ROOT}` references copy, which is the template). Set `{{SETUP_COMPLETE}}: true`.
- Brand-level tokens (`{{NICHE}}`, `{{IDEAL_CLIENT}}`, `{{OFFER}}`, `{{BRAND_NAME}}`, `{{BRAND_VOICE}}`) also read/write the shared `~/.claude/revxl/<brand>/voc/business-config.md` when present (Cowork/Code)... engine-specific keys (platforms, account type, DM keyword, toggles, markers) stay in `${CLAUDE_PLUGIN_DATA}`.
- Do NOT write the environment tier anywhere... it is re-detected every session.
- Confirm back in plain English (per explanation level): what you captured, and that the audits will now skip the basics.

## Ends with (offer, never block)
- **Run an audit now** ... route to `profile-fb-audit` or `profile-ig-audit` per `{{PLATFORMS}}` (both... FB first, then IG). "Want me to audit your Facebook / Instagram now?"
- (When voice came out thin or inline) "Capture your real voice from your calls + content for a durable, cross-engine brain?" ... `brand-brain` (Cowork/Code only).
- (When they skipped 5b) "Benchmark against your niche's top accounts first?" ... `profile-competitor-scan` (Claude Code, credit-gated).
