---
name: carousel-superengine:carousel-teardown
description: Paste a public Instagram carousel or post link and get a structural teardown of why it works, then optionally rebuild it as your own. Pulls caption, cover, and engagement through the client's own SocialCrawl key; on Claude Code with Python it can fetch every slide for a full slide-by-slide teardown. Trigger phrases include "tear down this carousel", "analyze this carousel", "why does this carousel work", "steal this structure", an Instagram post/reel URL pasted with analysis intent.
---

# Task: teardown

Link in → teardown out → offer "build my version."

## Load
${CLAUDE_PLUGIN_ROOT}/references/business-config.md
${CLAUDE_PLUGIN_ROOT}/references/teardown-method.md (the full method — data paths, analysis shape, honesty rules)

## Flow

**1. Validate the link.** Accept `instagram.com/p/…`, `/reel/…`, `/tv/…` (public posts only). LinkedIn
has no pull path — offer the manual route (user pastes slide text / screenshots; analysis quality is
the same once content is in hand).

**2. Pick the data path** (details + exact calls in teardown-method.md):
- **Path A — SocialCrawl (default, works everywhere):** client's own key → one post pull → caption +
  cover image + engagement + creator context. State the credit cost before spending. Cover-only:
  say plainly that slides 2+ aren't visible on this path and the teardown reads hook + caption +
  metrics (that's still where most of the signal lives).
- **Path B — full slides (Claude Code + Python, `{{FULL_SLIDE_FETCH}}: available`):** uses the client's
  own Instagram cookies (exported once with the Cookie-Editor extension during setup, saved to
  `${CLAUDE_PLUGIN_DATA}/ig_session.json`). If that file is missing, or a fetch returns `login_required`,
  walk the client through a fresh Cookie-Editor export (@ig-cookie-setup.md) and save it — then
  `carousel_fetch.py … --session <file>` pulls every slide via the authenticated mobile API → true
  slide-by-slide teardown. Their own cookies only, never shared. Exact calls + conduct in teardown-method.md.
- Neither available → manual route (paste the slide text in order).

**3. Analyze** per the shape in teardown-method.md: format archetype, slide-flow map, hook mechanics,
caption mechanics, CTA read, what works / what doesn't / why, craft score. Flag every inference made
from partial data as an inference.

**4. Offer the rebuild.** "Want your version?" → route to the `carousel-create` skill with the
teardown as input. The rebuild borrows STRUCTURE (archetype, slide roles, retention devices) and
replaces every atom of content with the coach's: their avatar pains, their proof, their voice, their
CTA destination. Never reuse the source's wording, examples, or images.

## Rules
- Public posts only. Never suggest ways around a private account.
- Research + inspiration use. The pulled media/copy is analysis input, not content to repost.
- One post per teardown by default; batch pulls need an explicit yes (credits + throttle).
