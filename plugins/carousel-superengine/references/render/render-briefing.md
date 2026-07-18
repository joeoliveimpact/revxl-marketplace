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
skim path. [Text budget: default ≤20% of canvas; spec-sheet/educational decks legitimately run
25-40% — match the deck's actual format, don't fight it.]
STYLE: [from the COACH'S template/teardown/brand — never a stock look. e.g. dark spec-sheet:
"warm near-black ground, cream serif display, gold accents, mono labels" / or wellness-warm:
"clean editorial, cream base, forest-green headline type, coral accent on the one data point"]
COMPOSITION: [layout + focal element + negative space, e.g. "headline upper-left, coach cutout
right third, generous whitespace"]
COLORS: [from the brand system — hex codes preferred when the brand defines them (#171613 ground,
#F2ECDF ink...); plain names only when no kit exists. A hex-defined brand ships in hex.]
TEXTURE: [surface feel: matte, paper grain, soft shadow — never glossy AI sheen]
GUARDRAILS: watermark/handle [corner] on the slide; keep headlines and focal elements inside the
center-upper 75% (IG UI covers the bottom band); high contrast text-on-ground.
AVOID: lightbulbs, handshakes, puzzle pieces, gears, stock-photo poses, glossy AI aesthetic,
watermark artifacts, extra fingers, gibberish text
FORMAT: 4:5 portrait (1080×1350)
```

**Params are not prose (hard rule).** The FORMAT line describes intent, but the generation call
must ALSO pass `aspect_ratio: "4:5"` (and `resolution`) as real API parameters — the server
silently coerces unsupported/unspecified ratios to the closest match instead of erroring. After
every generation, check the returned dimensions against 4:5; if the API reports an adjustment,
tell the coach before shipping the slide.

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

## Engine selection

**Route: Higgsfield MCP first** (tools like `generate_image` / `models_explore` / `balance`,
found via ToolSearch — no CLI, no key file, auth rides the account session), `higgsfield-generate`
skill/CLI as fallback. Verify the chosen model's supported ratios via the catalog
(`models_explore`) before the first call — **any carousel model MUST support 4:5.**

- **Carousel slides (text-heavy AND reference/reskin): Nano Banana Pro class** — holds legible
  text (dogfood-verified 07.18.26: full slide copy character-perfect at 4k), strongest reference
  adherence, native 4:5, cheapest text-capable option (~2cr @2k / ~4cr @4k).
- **GPT Image 2 class:** sharp text but **no 4:5 support** and ~3.5× the credits — never the
  carousel default; only for non-4:5 side assets.
- Soul-bound slides: whichever model the trained Soul runs on (Soul V2 → `soul_2` + soul_id).
  Check for a ready Soul via `show_characters` (MCP) before asking the coach — one may exist that
  setup never recorded.
- State the credit/cost implication before the FIRST paid call of the session — on the MCP use
  the zero-spend `get_cost: true` preflight for exact numbers; batch estimates for the whole
  carousel up front ("~N generations ≈ X credits — go?"). This pre-spend disclosure is the
  CALLER's rule and wins over any downstream skill guidance that says don't pre-estimate.
