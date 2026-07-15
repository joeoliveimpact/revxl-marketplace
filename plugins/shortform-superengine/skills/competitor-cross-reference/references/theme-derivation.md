# Theme Derivation — building the per-lane `themes` override

analyze.py ships with a **default theme set for one historical niche** (functional-medicine:
thyroid / gut / cortisol …). For any other lane those defaults are wrong and will
produce an empty or misleading theme table. **Every run outside that niche must set a
`themes` override in `analysis-config.json`.**

This file is the **method** for deriving a lane's themes. Do not ship any client's
finished theme set as a plugin preset — themes are niche knowledge and belong to the
run. (The worked example below is illustrative, not canonical.)

---

## Method (15–20 min per lane)

1. **Start from the client's own pillars, not from imagination.** Best source order:
   the client's brand brain / VoC profile (business-config pillars, weekly content
   themes) → their site/offer pages → their top-20 captions by views.
2. **Mine competitor captions for recurring nouns.** After the reel pull, grep the
   gathered captions for high-frequency topic words — these become theme candidates
   the *field* actually posts about (which is what the gap analysis needs).
3. **Shape 7–10 themes.** Fewer than ~6 → gaps are too coarse to act on; more than ~12
   → every theme is thin and medians get noisy. Each theme = one **content lane a reel
   could live in**, not a keyword.
4. **Write each regex to catch variants, not sentences.** Word stems + alternates
   (`automat|workflow|pipeline`), `\b` guards on short tokens (`\bgut\b`, `\bmcp\b`),
   never match on punctuation-sensitive phrases. Test against 5 real captions before
   locking.
5. **Cover both sides of the client's positioning:** what they *sell* (offer lanes)
   AND what the *field* over-posts (demand lanes). The interesting gaps live where
   those diverge.
6. Drop the set into `analysis-config.json` under `themes` — analyze.py and
   `extract_patterns.py` both read the same key (matrix runs it on *spoken* text too).

```json
{
  "client": "handle",
  "client_followers": 12345,
  "GURU": [], "LARGE": [], "MED": [], "SMALL": [],
  "themes": { "theme-name": "regex", "...": "..." }
}
```

## Worked example (one AI-business lane, 07.12.26 — illustrative only)

Derived from that client's brand-brain pillars + field captions; 9 themes:
`claude-ecosystem` (claude|cowork|plugin|workspace|\bmcp\b…) · `ai-tools-prompting` ·
`automation-systems` · `content-growth` · `leads-sales-offers` · `coaching-scale` ·
`seo-aeo-discovery` · `money-results` · `mindset-positioning`.

What made it work: `claude-ecosystem` was split out from generic `ai-tools-prompting`
because the client's differentiation lives there — and that split is exactly where the
analysis found the severe gap (client 2 reels vs field 654). **A theme set that merely
describes the niche finds nothing; one shaped around the client's edge finds the money.**

## Checklist before running analyze.py

- [ ] `themes` override present (unless the run really is the default niche)
- [ ] 7–10 themes, each regex tested on real captions
- [ ] At least one theme isolates the client's differentiator
- [ ] Theme names are kebab-case (they become table rows + JSON keys)
