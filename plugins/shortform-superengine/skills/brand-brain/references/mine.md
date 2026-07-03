# Task — mine (full derivation pass)

Runs when no brain exists at the shared location. Sources in → all five artifacts out.

## 1. Resolve the brand
Ask (or read from an engine's config if invoked from one): brand name → `<brand>` slug for `~/.claude/revxl/<brand>/voc/`. Create the folder if absent.

## 2. Walk the source ladder (${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/source-ladder.md)
Detect what exists, top tier down. Confirm each source with the user before pulling (approval gate).

- **Tier A (spoken):** auto-detect the recordings connector — Fathom MCP or Fireflies. Confirm which. Propose a how-far-back window (default: last 90 days or last ~20 calls). Ask which buckets they run: sales / client / group / other; create `voc/transcripts/<bucket>/` per bucket present.
- **Tier B (written-by-them):** own social captions (SocialCrawl if wired), sent newsletters, Meta DM export if the user has one (JSON DYI export; DMs feed the `sales` bucket).
- **Tier C (written-FOR-them):** website / landing pages via firecrawl — mine for OFFER + AVATAR only. Never for voice.
- **Nothing through C** → route to ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/interview.md.

**High-ticket + no sales recordings = red flag.** Don't just move on: ask where sales-call data lives (who runs calls, what tool, notes/CRM), and offer to help start capturing — those calls are the richest ideal-client data there is. Frame as helping.

## 3. Extract (one pass, two shelves)
Per ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/speaker-separation.md then ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/extraction.md:
- Prospect/client turns → VoC (pains, desires, objections, verbatim bank) — always useful.
- Coach turns → voice guide (only if the coach ran the call) + story/humor seeds.
- Staff/setter turns → VoC side only; DISCARD for voice; flag it to the user.
- Score humor candidates per ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/signature-bits.md.
- Split everything by shelf life: evergreen → brain files; this-week topical → weekly-content-bank.

## 4. Write artifacts
Per ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/artifacts.md — all five files, each stamped `updated_at` (ISO date + time) and voice-guide stamped `voice_confidence` (highest tier actually used for voice). Dedup + frequency-rank the VoC bank; tag by bucket and register.

## 5. Canonize bits (human-in-loop)
Present signature-bit candidates with their evidence (reaction quotes, frequency). User thumbs-up → mark canon. No approval, no canon.

## 6. Index + heartbeat
Write `voc/index.md` (per bucket: last-pull timestamp, source, #items mined, decline count 0). Then offer the auto-refresh schedule per ${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/freshness.md (Cowork scheduled task / Code routine; their pick of day). Never more than ~7 days stale.

## 7. Report
One short summary: sources used per tier, confidence stamp, counts (pains/objections/phrases/bits/seeds), where everything landed, and the one-line teach: *why* fresh VoC in their own words converts better.
