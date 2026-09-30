---
name: image-prompting
description: Use when a client wants a general image made on Higgsfield through this plugin (the Higgsfield REST API with their own key), or wants an image prompt written, fixed or improved, and the job is not a static ad, product shot or thumbnail. Trigger phrases include "make me an image of", "generate a picture of", "create an illustration", "edit this image so", "change the background", "write me an image prompt", "improve this prompt", "why does my image look off". Teaches the image prompt craft (brief structure, text in images, references, edits, iteration) and hands the finished prompt to hf-generate to price and run. Not for video, static ads, product shots or thumbnails (each has its own skill), diagrams or charts, local photo editing, or requests to run Nano Banana, which this plugin cannot reach.
---

# Image prompting: the craft

## Output contract

- **Produces:** one finished prompt per image, **shown to the client in full** before anything runs, plus the model pick and every setting written out. [SINGLE-SOURCE: project approval gates (§4#35)]
- **Then hands off** to `higgsfield-superengine:hf-generate`, the only skill that spends. It prices the job first and asks when the price needs a yes. This skill never spends and never calls the API itself.
- If the client only wants the prompt (to use later or elsewhere), stop after showing it.
- Static ads, product shots and thumbnails have their own skills (`higgsfield-superengine:static-ads`, `higgsfield-superengine:product-shots`, `higgsfield-superengine:thumbnails`). They use this method; switch to them when the request is one of those. Video goes to `higgsfield-superengine:video-prompting`.

**Re-invoke guard:** if the session has compacted since this skill loaded, or a step below seems to be missing, invoke `higgsfield-superengine:image-prompting` again before writing the next prompt.

## Evidence tags

Every rule carries its tag from the plugin's master playbook (§ = playbook section, kept so tags can be upgraded as tests land). The four tags match the model files: **TESTED** = at least 2 REST samples with a verdict · **DOCS** = a setting fact from the Higgsfield REST docs, 09.25.26 snapshot · **AGREED** = 3 or more independent authors, shown in the playbook's repetition map (§3) · **SINGLE-SOURCE** = one REST sample, or fewer than 3 independent authors shown to agree. "Field notes" = the plugin author's proven notes (reference, never TESTED).

Hold TESTED and DOCS as hard facts, AGREED as firm defaults, SINGLE-SOURCE as starting bets to drop when the client's own results say otherwise.

## 1. Ask, then pick

- Ask **at most 4 short questions with labeled options**. Skip anything the conversation already answers. Don't describe the plan and submit in the same breath. [AGREED §3#5] Usual gaps: where the image will be used (sets the aspect ratio), exact words that must appear, references the client owns (face, product, style), the look.
- Pick the model with `${CLAUDE_PLUGIN_ROOT}/references/model-picker.md`. **Flare is the default image route.** Then open that model's file in `${CLAUDE_PLUGIN_ROOT}/references/models/` (the picker names it) and follow its caps, fields and rules; where it differs from this file, the model file wins.
- Take values from `${CLAUDE_PLUGIN_ROOT}/references/settings-defaults.md` and **set quality, resolution and aspect ratio explicitly on every call**. Defaults differ by model, and leaving the aspect ratio out does not mean "follow the input". [SINGLE-SOURCE §5.0#8, plus the catalogs]
- Faces and dense text: `2k` + `high`, not `4k` (4k invents skin texture and blotches small type). [AGREED §3#22, field notes] Flare already defaults to high / 2k [DOCS 09.25.26]; set them anyway.

## 2. Write the brief

- A **directed brief in full sentences**, not a keyword list. [AGREED §3#9]
- **Front-load what matters.** Photos: the subject first. Designed graphics (ads, posters, slides): the image type first, then subject, layout, supporting elements, tone, material, typography; the aspect ratio stays a setting. [SINGLE-SOURCE: B11, D1 (§4#38)]
- Name subjects directly ("the woman with short black hair"), not with pronouns across sentences. [SINGLE-SOURCE §5.0#5]
- **One** style or mood anchor, after the structural decisions. Don't stack styles. [AGREED §3#16]
- Turn taste words into visible instructions: "premium" becomes "restrained layout, limited palette, generous negative space". [AGREED §3#26]
- **Name real light**: golden hour, hard directional key, soft diffused, rim, practical, Rembrandt; never just "dramatic lighting". For brand work, give background, then key-light color, then accent. [AGREED §3#17]
- Name materials: "brushed steel", "kraft paper", "frosted glass", "natural skin micro-texture, no retouching". [SINGLE-SOURCE §5.1]
- Lens strings are optional (100mm macro f/2.8 for detail, 85mm f/8 packshot, 35mm f/4 daylight). [AGREED §3#34] On Soul, leave them out: "+85mm" made no visible difference. [SINGLE-SOURCE: REST, 1 sample, T12]
- **Keep settings and hype out of the prompt**: no model name, resolution, aspect ratio, or "4K, 8K, masterpiece, ultra-detailed, award-winning". [tag soup is OUTDATED-EVERYWHERE §3#7]
- Don't contradict yourself: "no text" plus "the word AQUA+ on the label" makes the model pick one. [SINGLE-SOURCE §5.0#6]
- **Length follows the model.** Long structured prompts suit GPT-Image-class models such as Flare; every model's hard character cap is in its model file. [SINGLE-SOURCE: A21, D12, A15 (§4#1)]
- When layout matters (copy space, text zones), write **labeled blocks**: `HEADLINE:`, `LAYOUT:`, `PROOF OBJECTS:`, `LIGHTING:`, `AVOID:`. Short prompts hand the model creative control, including made-up text. [SINGLE-SOURCE, field notes §5.2; an app-route test agreed, reference only]
- Place things spatially, with percent of frame ("headline across the top ~40%") or zone fractions of the height ("text zone 0.10 to 0.35"). [SINGLE-SOURCE §5.1]

## 3. Text in the image

- **Bake text in by default** on text-capable models (Flare; probably Ideogram 4.0 and Recraft [SINGLE-SOURCE: reasoning, §4#3]). Composite only exact brand fonts and exact logos. [AGREED §3#23]
- Put exact copy in **double quotes**, with its position, font style, color and contrast. [AGREED §3#12]
- Text edits: `Change 'old' to 'new'`, at a similar length. Name the script for non-Latin text ("Japanese kana", "Arabic, right to left"). [SINGLE-SOURCE §5.1]
- Exact logos and brand fonts: leave their space clear and composite them afterwards; exact logo reproduction isn't promised. [AGREED §3#33]
- **Phrase constraints positively** ("a clean unmarked wall", not "no text"). Use a `negative_prompt` field only where the model has one (its model file says). [AGREED §3#24] Otherwise write at most one short, task-specific `AVOID:` line that ends with a positive restatement: "…no watermark. Just the headline, the product and the small wordmark." Never paste generic anatomy or quality banks. [SINGLE-SOURCE: A21 (§4#2)]

## 4. References

- Give each reference **one narrow job**: what it controls and what it must not. Put the main subject first. List unused references as controlling nothing. [AGREED §3#2]
- **Reference attached:** describe the action and the deliberate changes, not the identity. [AGREED §3#31] Things a reference can't lock (material, outfit rules) still get words. **No reference:** describe it fully, and repeat that description word for word every time. [SINGLE-SOURCE: D12, C3 (§4#7)]
- Real faces: a face reference holds identity. For skin, add the real photo as a **second** reference and write "render skin to match the real photo" on every pass that touches the person. [SINGLE-SOURCE: A18, A20 (§4#5); SINGLE-SOURCE, field notes §5.2]
- Style references: attach the client's own with a style-donor line ("Take only the visual render style and color grading. Never use the characters, inscriptions…"). Someone else's image (a competitor's ad or thumbnail): describe its style in words; don't attach it. [SINGLE-SOURCE: A6, A7, D4 (§4#36)]
- Don't turn reference details into invented facts (age, job, relationships). [SINGLE-SOURCE §5.0#13]

## 5. Edits

- **Every edit is a full regeneration.** Placement drifts and skin degrades each pass. Make one change per pass, say "Change ONLY <the one thing>. Keep <identity, pose, framing, text, background> exactly unchanged.", re-anchor skin every pass, and measure placement rather than eyeball it. Calls are stateless, so pass the previous result as a reference. [SINGLE-SOURCE: A18, A9 (§4#6)]
- Say only what changes, plus the keep list. Use directional words for moves ("move the headline from top-right to bottom-center"). "Transform" means a full rework. For a removal, say what fills the gap. [AGREED §3#6]

## 6. Consistency, iteration and cost

- The model remembers nothing between calls. Paste the same style, brand or character string **word for word** into every prompt; never write "(as above)". [AGREED §3#1]
- Series: "same structure, different product / city / emotion". Variants differ in angle, light and palette, not in paraphrased wording. A carousel locks one visual system. [SINGLE-SOURCE §5.1]
- Change **one variable per pass**; don't rewrite a brief that mostly works. [AGREED §3#13]
- After **2 misses** on the same problem, change the anchor, the structure or the model. Never send a third identical retry. Fix the prompt before switching models. [AGREED §3#8]
- **Draft cheap, then the hero:** explore at 1k / low or on a fast model, and render the final on the confirmed direction. hf-generate prices every run first. [AGREED §3#14]
- One job at a time while iterating. Batches only after the direction is confirmed and priced. [AGREED §3#41]
- Transparent assets: Flare has no background option [DOCS 09.25.26]. Generate on a solid key color (magenta; green or blue if the subject is pink) and remove it afterwards. [SINGLE-SOURCE §5.1]

## 7. Check every result

- **Redo (one change) when you see:** stray or misspelled text, a hero subject under ~50% of the frame, a washed-out palette, no negative space where copy must go, waxy skin, melted hands. [SINGLE-SOURCE §5.1]
- **Anti-slop:** no automatic leaves = organic, sparkles = premium, gold + serif = luxury; no floating products, plastic sheen or marble-pedestal "luxury" unless asked for; avoid the stock AI palettes (near-black + orange, near-black + neon cyan, beige + brass, purple glow). [SINGLE-SOURCE §5.1]

## 8. Safety and truth

- No real public figures, sexual content, trademarks or branded characters. A real person's likeness needs their rights. [AGREED §3#35]
- On an `nsfw` or `ip_detected` block: rephrase away from brands and real people, and remove one reference at a time. Never resubmit unchanged. [AGREED §3#11] Mood words such as "intimate" or "ambient" can cause false nsfw flags on product prompts. [SINGLE-SOURCE §5.0#22]
- "Make it look like <artist>" becomes an original homage. Don't claim an exact living artist's style. [SINGLE-SOURCE §5.0#23]
- Never invent claims, prices, stats, quotes or model names. [AGREED §3#21]
