# Teardown Method — data paths + analysis shape

How `carousel-teardown` turns a pasted link into a structural teardown. Two data paths, one analysis
shape, hard honesty rules.

## Path A — SocialCrawl post pull (default; works on Cowork, Desktop, and Code)

**Key resolution** (never proceed without one):
1. Env `SOCIALCRAWL_API_KEY` (must start `sc_`)
2. `~/.config/socialcrawl/api_key`
3. Neither → offer the 2-minute click-path in @socialcrawl-key-setup.md, then save to the file above.

**The pull** (state cost first; a post pull is a low-single-digit credit call):

    curl -s -H "x-api-key: <key>" "https://www.socialcrawl.dev/v1/instagram/post?url=<URL-ENCODED-LINK>"

Envelope: `{ success, data, … }` — the post lands under `data` (`content` holds caption + media
fields; creator + engagement fields alongside). Extract:
- **caption** (full text — hook line, structure, CTA, hashtags)
- **cover image URL** (`content.media_urls` / `thumbnail_url` — this is the HOOK SLIDE)
- **engagement** — likes, comments (+ views where present)
- **creator context** — handle, follower count (baselines the engagement read)

Download the cover (`curl -s -o cover.jpg "<url>"` — CDN links expire in ~24h, pull it now) and Read
it for vision analysis of the hook slide.

**⚠️ Cover-only honesty rule:** SocialCrawl returns ONE image for a carousel — the cover. Slides 2+
are not visible on this path. Verified against the payload spec + live integration (2026-06). The
teardown therefore reads: hook slide (vision) + caption (full) + metrics. Say this plainly in the
output; never present slide-flow guesses as observed slides. When the caption narrates the slide
sequence ("swipe for the 5 steps…"), inferences from it get tagged `(inferred from caption)`.

## Path B — full-slide fetch (Claude Code + Python; the client's own Instagram cookies)

When `{{FULL_SLIDE_FETCH}}: available`, the bundled script pulls EVERY slide via Instagram's
authenticated mobile API — the only path that still returns all slides (2026-07). No browser
automation, no install: it runs on cookies the client exported once with the **Cookie-Editor** browser
extension (captured during setup — see @ig-cookie-setup.md). Stdlib-only Python.

**The pull** (uses the saved cookie export, default `${CLAUDE_PLUGIN_DATA}/ig_session.json`):

    python ${CLAUDE_PLUGIN_ROOT}/scripts/carousel_fetch.py "<post-url>" "<work-dir>" --session "<cookie-file>"

stdout = one JSON object: `{ok, shortcode, username, caption, taken_at, likes, comments, is_carousel,
slides:[{index, kind, file}], message}`. Slide files land in `<work-dir>` as `slide_00`, `slide_01`… —
Read each image in sequence for the true slide-by-slide teardown.

**Cookies expired?** A `login_required` result means the session is stale. There is NO fixed timer —
Instagram sessions last months for an active account, but a log-out / password change kills them. Have
the client re-export via Cookie-Editor and paste again (@ig-cookie-setup.md). The skill detects
`login_required` and asks; never set an arbitrary refresh clock, and never retry-loop.

**Why authenticated:** anonymous fetch is `403 login_required`-dead (Instagram clamped down mid-2026)
and instaloader's web path is dead even logged-in. Cookies + the mobile API is the working, client-side
replica of what iqsaved does server-side. See memory `ig-carousel-fetch-reality`.

**Conduct rules (non-negotiable):**
- The client's OWN cookies only. NEVER a shared account — concentrated volume on one account is the
  fingerprint that gets banned; per-account volume stays tiny by design.
- Public + accessible posts only. Private = hard stop, no workarounds.
- One post per run. Batch = explicit user yes + spacing.
- Downloaded media is analysis input for the user's own research. It is never reposted, repackaged, or
  shipped anywhere. (Scraping may violate Instagram's ToS — the user owns that call; keep usage
  personal-research-scoped.)
- The cookie file is a secret (full account access). It stays in `${CLAUDE_PLUGIN_DATA}` on the client's
  machine; never commit or share it. Logging the account out revokes it.

## Analysis shape (both paths — degrade gracefully on partial data)

Output as markdown, these sections in order:

1. **Format archetype** — Listicle / Story-arc / Before-after / Hook-payoff / Educational-steps /
   Myth-bust / Case-study (+ one-line slide-flow summary).
2. **Slide map** — per slide: n, role (Hook / Tip / Proof / Transition / CTA), what it does in ≤12
   words. Path A: only rows actually observed or `(inferred from caption)`.
3. **Hook mechanics** — what the cover does in the first 0.5s: pattern, promise, curiosity gap,
   visual device. Reference @hook-patterns.md archetypes by name.
4. **Caption mechanics** — first-line hook, structure, CTA, hashtag strategy, how caption and slides
   split the job.
5. **CTA read** — what action the post optimizes (save / share / DM / follow / click) and the device
   used.
6. **What works** (2-4 bullets, specific) / **What doesn't** (1-3, specific).
7. **Why** — 2-4 sentences on the underlying retention/conversion mechanics, in teach-mode plainness
   when `{{TEACH_MODE}}` is on.
8. **Craft score** — 0-100 + label (Weak / Fair / Solid / Strong / Exceptional). Craft quality, NOT a
   performance prediction; engagement numbers contextualize but don't set it.
9. **Steal-this** — the 2-3 structural moves worth carrying into the coach's version (structure, not
   wording).

Then offer the rebuild → `carousel-create` with this teardown as input.
