# Recraft V4.1 (REST)

Logos, icons, vector-style graphics, controlled-palette art, print/cut graphics. Utility = clean front-facing product shots and mockups. [SINGLE-SOURCE: A1, A5] Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `recraft/v4.1/text-to-image`: 1k only.
- `recraft/v4.1/pro/text-to-image`: 2k only.
- `recraft/v4.1/utility/text-to-image`: 1k only.
- `recraft/v4.1/utility/pro/text-to-image`: 2k only.

## Settings [DOCS 09.25.26]
- `prompt` 1–10,000 chars.
- `resolution` is fixed per endpoint (above); pick the endpoint for the tier.
- `colors`: an array of `{"rgb":[R,G,B]}` objects; `background_color` is one such object. Each value an integer 0–255, exactly three.
- `output_format` jpg/png/webp (default jpg): raster only, no SVG on REST.
- `aspect_ratio`: 14 values incl. 4:5, 6:10, 14:10, 10:14 (default 1:1).
- **No reference-image input.**

## Prompting rules
- Logo prompt order: mark type → central subject → shape logic → style register → palette behavior → composition → constraint tail. Every clause must change the drawing. [SINGLE-SOURCE: A5]
- One visual idea; one distinctive device (silhouette, negative space, motif); never a generic swoosh, blob, orbit, shield, spark, leaf or letter-in-circle. [SINGLE-SOURCE: A5]
- Colors go in the `colors` parameter, never the prompt; describe roles in words; 1–3 colors ("three is a maximum, not a target"). [SINGLE-SOURCE: A5]
- No camera or lighting words, and never name a live brand or designer. [SINGLE-SOURCE: A5]
- Constraint tail: "Flat vector design, clean lines, no shadows, no texture, no text. Clean editable vector paths, SVG-friendly, minimal anchor points." [SINGLE-SOURCE: A5]
- Print/cut: "solid pure black artwork… no grays, no gradients, no halftones"; "thick clean lines… paths continuous, no floating specks". [SINGLE-SOURCE: D9]
- Output is raster, so a real vector needs a trace step afterwards. [SINGLE-SOURCE: A5, D9]

## Cost and asks
- All four are priced from the live `/estimate`.

## Known failure modes
- Hex color strings (`#RRGGBB`) are the app format; REST wants RGB objects. [DOCS 09.25.26]
- A resolution other than the endpoint's tier is rejected. [DOCS 09.25.26]
