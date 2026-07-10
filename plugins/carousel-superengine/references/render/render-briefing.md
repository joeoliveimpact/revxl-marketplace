# Render Briefing — Path A (image generation)

How to brief an image model so slides come out professional, on-brand, and consistent across the
carousel. Method adapted from the coach's own documented steal-style workflow + the
image-prompt-generator skill (cdeistopened/skill-stack, MIT) — brief structure and rework language
borrowed with attribution.

## The sequence (never generate the whole carousel at once)

1. **STEAL (when a reference exists).** Teardown slides or a saved template set the visual system:
   layout, color, typography, spacing. Borrow the SYSTEM, ignore the original's copy entirely.
2. **BRIEF.** One structured brief per slide (format below). The carousel package supplies the exact
   copy; the visual system supplies everything else.
3. **ANCHOR.** Generate slide 1 THREE times. Coach picks the winner. That image is now the visual
   anchor for every remaining slide.
4. **ONE-AT-A-TIME.** Each subsequent slide = anchor attached as reference + that slide's brief.
   Never batch; consistency dies in batches.
5. **RINSE.** Small misses get a rework instruction (below), not a regeneration from scratch.

## Brief format (per slide)

```
Create a [style type] slide graphic, 1080×1350 portrait.

CONCEPT: [what this slide shows — one clear visual idea, 2-3 elements max]
TEXT (render exactly, in quotes): "[headline]" large and bold; "[body lines]" smaller. Bold the
skim path. Text occupies no more than 20% of the canvas.
STYLE: [from template/teardown/brand: e.g. "clean editorial, cream base, forest-green headline
type, coral accent reserved for the one data point"]
COMPOSITION: [layout + focal element + negative space, e.g. "headline upper-left, coach cutout
right third, generous whitespace"]
COLORS: [name them — cream, charcoal, burnt orange. Names, not hex codes]
TEXTURE: [surface feel: matte, paper grain, soft shadow — never glossy AI sheen]
AVOID: lightbulbs, handshakes, puzzle pieces, gears, stock-photo poses, glossy AI aesthetic,
watermark artifacts, extra fingers, gibberish text
FORMAT: 4:5 portrait (1080×1350)
```

Write like a creative director briefing a human artist: full sentences, specific materials and
lighting, the "for whom" context ("for a fitness coach's Instagram educating busy dads"). Tag soup
("gym, coach, 8k, trending") produces generic slop.

**Route override:** if the coach asks for an image-gen brief on a slide the render handoff tagged
template-text, honor the request — brief it normally — but say in one line that Path C / workspace
was the recommended route for that slide.

**Text on slides:** current image models render text excellently — put the EXACT copy in quotes and
demand it verbatim. Verify every generated slide's text character-by-character anyway; one typo =
one rework instruction. Long body text (40+ words) is the one case that still favors Path C or
workspace render — flag it instead of forcing it.

## Face consistency (the coach on their own slides)

- **Soul model trained** (`higgsfield-soul-id`): generate with it — every image IS the coach. This
  is the strongest trust signal this demographic has; real face beats every other authority cue.
- **No Soul:** attach 1-2 real photos as reference + "Keep the person's facial features exactly the
  same as the reference image." Expression/pose may change; identity may not. Weaker than Soul —
  expect occasional drift, verify each slide.
- Photoreal body-transformation claims: NEVER generate. Real `{{PROOF_ASSETS}}` receipts only —
  composite the real screenshot/photo onto the designed slide instead of synthesizing one.

## Rework instructions (fixing, not regenerating)

When a slide is 80% right, instruct the edit — anchor stays attached:
- Preserve explicitly: "Keep the composition, colors, and the person's face exactly the same."
- Change explicitly: "Change ONLY the headline to '<new text>'." / "Remove the object bottom-left."
- Comparative nudges: "Make the lighting warmer." / "Slightly more whitespace around the headline."

## Engine selection (via the higgsfield-generate skill)

- **Text-heavy slide** (headline + body): GPT Image 2 class — sharpest text rendering.
- **Reference/reskin slide** (steal-style, anchor-following, face reference): Nano Banana class —
  strongest reference adherence.
- Soul-bound slides: whichever model the trained Soul runs on.
- State the credit/cost implication before the FIRST paid call of the session; batch estimates for
  the whole carousel up front ("~N generations ≈ X credits — go?").
