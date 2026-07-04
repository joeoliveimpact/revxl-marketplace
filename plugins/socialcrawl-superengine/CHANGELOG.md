# Changelog — socialcrawl-superengine

## 0.1.0 — 2026-07-04

Initial release.

- **`socialcrawl` skill (canon):** full 43-platform / 333-endpoint reference set,
  generated from SocialCrawl's own docs + pricing registry — every endpoint row carries
  its **exact** credit cost (the public 1/5/10 tier model hides ~30 flat-override
  endpoints priced up to 50 credits; the refs don't). Cheat-codes section (free
  `prism/lookup` URL dispatcher, 1-credit `prism/post-stats` for 100 URLs, 1-credit
  `prism/comments`, 1-credit `reddit/omni-search` VoC sweep, 5-credit
  `prism/handle-audit` pre-pull gate). Hardened ⛔ transcription ban on all 9
  `*/transcript` endpoints.
- **`research-plays` skill:** 6 guided plays (VoC mining, ad-library recon,
  AI-visibility audit, link-in-bio offer recon, TikTok audience demographics, dev
  radar) + 10 big-gun one-shot runbooks (15–50cr) behind a strict gate ritual
  (balance + named cost + explicit confirm, never batched).
- **`onboarding` skill:** BYO-key setup with guided signup, 1-credit verify,
  plain-English credit briefing, and the `~/.claude/socialcrawl-superengine/.superengine`
  marker that RevXL format engines detect to offer deep plays.
