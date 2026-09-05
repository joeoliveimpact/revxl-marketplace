---
name: editor-superengine:reel-motion-comps
description: The design-iteration loop for reel visuals — direction comps over real plates, parametric ladders for craft tweaks, measured verification, and rulings taken from frames. Use when someone says "design the hook", "motion comps", "direction comps for the reel", "hook treatment options", "ladder the blur", "iterate this visual", "reel design pass", or "comp the intro". For anyone designing or iterating the on-screen visuals of a short-form reel after picture lock. Not for the spoken cut itself, and not for captions.
---

# Reel Motion Comps — the design-iteration loop

The loop that landed a reel hook in 12 rungs without a wasted round, after the same
session burned roughly 590k tokens learning it the wrong way first. Two laws above
everything: **the reviewer rules from frames, never prose** · **iteration is parametric,
not conversational.**

Before the first comp, read
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/house-rules.md` (rule 4: load the
governing docs first, and show divergent directions before one finished thing).

## The loop

1. **Directions first, divergent in APPROACH.** 2–4 options per open decision, low-fi,
   over the REAL plates (never a proxy — check plate resolution before comping; a 2x
   upscale is a picture judgment on a proxy). Nothing that is the dictionary
   illustration of its word. Each option's label strip names its approach and tradeoff.
   The hook direction is also bound by
   `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/frame-zero-hook.md`: the complete
   visual text hook is readable at 0.000s, and only the secondary pieces may animate in.
2. **Build one CSS/param factory per element under iteration.** A hook treatment exposed
   as `hook_white_css(halo, lift, blur, alpha)` is the pattern: every craft variable is a
   parameter. First build may be an agent; **every subsequent tweak is a main-thread
   parameter change + re-render** — seconds, near-free. Five agent dispatches for one
   chip treatment is the measured failure mode this rule exists to prevent.
3. **Tweaks ship as LADDERS, not single attempts.** Spread / blur / opacity / stroke:
   render 3–4 rungs plus ONE stacked comparison image (crop to the element region) so the
   reviewer judges the whole axis in a single look. Measure don't opine: the counter-flood
   % (accent colour remaining in letter bowls) is the lift-vs-glow discriminator; opacity
   in chained drop-shadows is NON-linear (−40% alpha bought −15pp, −20% bought −5.5pp).
4. **The reviewer's picks are rulings.** Number them, write them into the plan's rulings
   table the same turn, and cite them on every artboard label strip that implements them.
   Rulings come off rendered frames, never off a description:
   `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/preview-before-render.md`.

## Measurement kit (all caught real defects)

- **Ink measured on rendered Ranges**, never block boxes (caught a 104px overrun).
- **SVG ink bbox measured, never the declared viewBox** (one brand wordmark SVG's box is
  47% air; applying its correction to a different wordmark would CLIP — verify which file
  a viewBox belongs to before using it).
- **SVG clips its own filter output** — `overflow:visible` on any svg carrying a
  drop-shadow, or the shadow slices at the letter edge.
- **Unmasked font control**: a loaded face must NOT measure the same width as its
  fallback; the renderer exits nonzero on a miss.
- **Prove the guard fails**: push a comp out of bounds on a throwaway copy and confirm
  the check reports it. Blur radii bigger than half a letter bowl (~10–15px wide at
  headline sizes) go INTO the letters, not around them.
- **Instagram UI reserves** are a pre-check, never proof — the script cannot see pixels:
  ```bash
  python ${CLAUDE_PLUGIN_ROOT}/skills/reel-motion-comps/scripts/ig-safe-zones.py --svg comps.html

  It finds text-bearing elements by the hex constants at the top of the script (`TEXTISH`,
  `ANNOTATION_FILLS`), which come from one sketch convention. On comps that use other colours it
  detects nothing and reports clean, so before the first run set those constants to the comp's
  own text and annotation colours. Pre-check only, never proof.
  ```

## Conventions

- Artboards 1080×1920 + a dark mono label strip BELOW the frame (direction letter,
  approach, timings, ruling numbers, what's INVENTED vs ruled vs [PROPOSED]).
- The approved script copy verbatim, always. UI mock content (thread questions,
  filenames) is allowed but labeled "UI CONTENT, not script" on the artboard.
- Comp animations = one infinite CSS keyframe timeline per element (cues as % of loop);
  JS class-toggle restarts silently fail in embedded previews.
- Design comps preview CHOREOGRAPHY, never the clock — stamp LANDS ON onset, pop FIRES
  ON onset re-verify against the word map at the port into the animation tool.
- Word maps: consume by WORD index only, never segment index; skip empty-text tokens.

## Token discipline (the melt rules)

- Checker/audit passes only on spec-bearing steps (timing derivations, word maps,
  governing docs). A recolor gets a look, not a 120k audit.
- Kill a runaway agent as soon as its useful work has landed; salvage and finish
  main-thread (a 356k-token agent was killed mid-font-work; everything after cost
  ~nothing).
- **One review surface** — a single canvas the reviewer comments on. Never mirror every
  iteration into a second copy.
