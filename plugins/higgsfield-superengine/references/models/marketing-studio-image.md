# Marketing Studio Image: Flare, Sunburst, 2.0 Alpha (REST)

The plugin's default image route. Flare and Sunburst are GPT Image 2.5 per the app catalog (reference, not TESTED). REST Flare rendered GPT-Image-style, letter-perfect text. [SINGLE-SOURCE: REST, 1 sample, T2] Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `marketing-studio/image/flare`: 2.5 Flare, the default.
- `marketing-studio/image/sunburst`: 2.5 Sunburst.
- `marketing-studio/image`: 2.0 Alpha.

## Settings [DOCS 09.25.26]
- `prompt` up to 5,000 chars.
- `quality`: Flare/Sunburst low/medium/high/xhigh/max; 2.0 Alpha low/medium/high only, and must be `high` when `enhance_prompt=true`. Default `high`.
- `resolution`: 1k/2k/4k tiers, default 2k; exact pixels depend on the aspect ratio.
- `aspect_ratio`: auto, 1:1, 3:2, 2:3, 4:3, 3:4, 16:9, 9:16, 21:9. Without enhancement, `auto` gives square output. No 4:5.
- `image_urls`: up to 16 (JPEG/PNG/WebP) when `enhance_prompt=false`; omit them for text-to-image.
- `enhance_prompt=true` needs a `preset_id` (list them with the free `GET /marketing-studio/image/presets`) plus 1–2 images: product first, optional person second.
- `moderation` auto/low (default auto). No `background` field, so no transparent output.

## Prompting rules
- The GPT Image 2 rules below are an untested transfer to 2.5. [SINGLE-SOURCE: §5.3 route mapping; REST, 1 sample, T2]
- For 4:5, generate 3:4 and crop the vertical excess. [AGREED, §3 #39]
- Put exact on-image text in double quotes, with its position, font style and color. [AGREED, §3 #12]
- Bake text into the image by default; composite only exact brand fonts and logos. [AGREED, §3 #23]
- Long, structured prompts are fine. Labeled blocks work: `HEADLINE / LAYOUT / PROOF OBJECTS / LIGHTING / AVOID: … Just <the elements>.`, about 230–250 words. [SINGLE-SOURCE: A21, D3]
- Faces and dense text: 2k + `high`; 4k invents skin texture and blotches dense type. [AGREED, §3 #22]
- Edits: `Change ONLY <X>. Keep <identity, pose, framing, text, background> exactly unchanged.` [AGREED, §3 #6]
- Every edit repaints the whole frame and placement drifts: one change per pass, measure placement, and pass the prior result as an image (calls are stateless). [SINGLE-SOURCE: A18, A9 (§4 #6)]
- Up to 16 `image_urls`: with 2 or more, open the prompt with an `IMAGE REFERENCES: image 1 = …; image 2 = …` manifest in upload order and name each by number plus a noun (see image-prompting §4). [SINGLE-SOURCE: B3, official youtube-thumbnail skill]
- Face lock from a reference works. For skin, pass the real photo as a second reference and say "render skin to match the real photo" on every pass. [SINGLE-SOURCE: A18, A20]
- Product first, person second. Order barely mattered in the test; follow the docs order anyway. [SINGLE-SOURCE: REST, 1 sample per order, T15]
- Static ads: structure (layout, zones) from a neutral wireframe as Image 1, never a competitor ad; background, type and accent from the brand guide; "match the product only". A/B it against the `preset_id` path. [SINGLE-SOURCE: D4]
- Composite exact logos and fonts in post. [AGREED, §3 #33] Brand logo reproduction isn't promised. [SINGLE-SOURCE: A18, D3]

## Cost and asks
- Flare: priced silently from a conservative per-tier ceiling (xhigh/max cost about double), plus a small allowance per reference image; the balance is re-read after the job. Setting `enhance_prompt` or `preset_id` asks first (that cost isn't in the price).
- Sunburst: asks before every run until one real Sunburst charge has been measured.
- 2.0 Alpha: priced from the live `/estimate`.

## Known failure modes
- Forgetting `aspect_ratio` gives a square image. [DOCS 09.25.26]
- `enhance_prompt=true` without a `preset_id`, or with more than 2 images, is rejected; so is 2.0 Alpha with enhancement and `quality` other than `high`. [DOCS 09.25.26]
