# Beat Schema — the per-slide record contract <!-- T1: the shape ships; the DATA it captures is always the coach's own (T3) -->

A slide IS a beat — same frame the shortform + youtube engines use on video. `carousel-inspire`
extracts one record PER SLIDE (not per post); `carousel-create` grades copy against the resulting
dataset. Shape proven live on a 430-slide run (07.17.26) before it was written here.

## The record

```json
{
  "post_id": "top03_handle_SHORTCODE",
  "handle": "creator handle",
  "tier": "top | bottom",
  "eng_likes": 0, "eng_comments": 0, "per1k": 0.0,
  "total_slides": 8, "slide_pos": 1,
  "order_verified": true,
  "role": "hook | value | proof | context | reassurance | summary | payoff | cta",
  "copy_verbatim": "exact on-slide text",
  "copy_formula": "the abstracted fill-in shape",
  "framework_role": "what this beat does for the deck in ≤8 words",
  "visual": "layout/palette/type in one line",
  "engagement_device": "curiosity-gap | open-loop | numbered-tease | proof-receipt | pattern-break | save-bait | keyword-gate | none",
  "loop_tier": "primary | secondary | micro | none",
  "seam_question": "the open question this slide leaves for the next swipe (null = dead seam)",
  "notes": "anything the fields can't hold"
}
```

Persist as `beats-<niche>-<date>.json` in `${CLAUDE_PLUGIN_DATA}/analysis/`, alongside the prose
report — the report interprets, the dataset is queryable.

## Field rules

- **role** shares the cross-engine vocabulary where it overlaps (hook / proof / payoff / cta match
  shortform); carousel-only roles: value, context, reassurance, summary.
- **copy_verbatim** is captured for analysis and NEVER ships into a generated deck or a shipped
  reference — verbatims are the coach's pulled evidence (T3). Formulas (abstracted shapes) may
  graduate into shipped refs per the tiering rule.
- **order_verified**: false when slide order came from filename/position heuristics rather than
  confirmed display order — synthesis must down-weight positional claims from unverified decks.
- **seam_question + loop_tier** feed the seam audit and loop-chain checks in
  @retention-loops.md / @carousel-quality.md.
- **per1k** = likes per 1k followers at pull time — the tier split (top/bottom) is per-niche
  relative, never an absolute threshold.

## What synthesis must emit from this dataset (inspire step 4)

1. **Hook library** — every slide-1 (verbatim + formula + device), win/loss-tagged.
2. **Framework skeletons** — winning role-sequences as reusable blueprints ("S2 spec-sheet:
   hook → context → value×4 → proof → payoff → cta").
3. **Positional beat-map** — what each slide position does in winners vs losers.
4. **Kill-list** — losing beat-patterns to gate against (buried reader stake, unresolved close,
   context overload, tease-stacking).
