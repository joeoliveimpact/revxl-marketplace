---
name: product-shots
description: Use when a client wants product photos generated on Higgsfield through this plugin (the Higgsfield REST API with their own key). Trigger phrases include "product photos of my", "studio shot of this product", "packshot on white", "lifestyle shot of my product", "flat lay", "close-up of the texture", "someone holding my product", "main image for Amazon or Shopify", "plan a product shoot", "redo this product photo for Christmas". Classifies the shot, plans a shoot, writes prompts that keep labels legible, and hands each one to hf-generate to price and run. Still images only; product video reveals go to video-prompting and person-led product videos to ugc-video-ads. Not for ad layouts with headlines (static-ads), marketplace listing card sets, or the official Higgsfield CLI product-photoshoot skill.
---

# Product shots: finished product stills

## Output contract

- **Produces:** finished product stills made through `higgsfield-superengine:hf-generate`; for more than one image, a short **shot plan** first (shot type, lighting, aspect ratio per shot). Each final prompt is **shown in full** before it runs [SINGLE-SOURCE: project approval gates (§4#35)], with its model and settings.
- **Stills only.** A product reveal, turntable or animated packshot goes to `higgsfield-superengine:video-prompting`, starting from the approved still. A person using or talking about the product on camera goes to `higgsfield-superengine:ugc-video-ads`.
- The prompt craft lives in `higgsfield-superengine:image-prompting`; invoke it if it isn't loaded.

**Re-invoke guard:** if the session has compacted since this skill loaded, or a step below seems to be missing, invoke `higgsfield-superengine:product-shots` again before the next shot.

Tags follow image-prompting's legend (TESTED / DOCS hard; AGREED firm defaults; SINGLE-SOURCE starting bets). Rules from the two product-shoot source skills with no playbook row are marked SINGLE-SOURCE (A3 = Higgsfield's product-photoshoot, D7 = a product-photography brief).

## 0. Connection check (free)

Before the questions, look for the file `higgsfield\.python` in the workspace folder (setup writes it). Missing: run `higgsfield-superengine:higgsfield-setup` first, then come back here with the request intact. Present: go ahead; hf-generate re-checks the key before anything spends. Nothing is spent here.

## 1. Read the intent

Pick by intent, not by a surface keyword. [SINGLE-SOURCE A3]
- Clean, white, studio, catalog, store listing → **studio packshot**
- In use, in a kitchen, outdoors, at the gym → **lifestyle scene**
- Hands holding, applying, pouring, demonstrating → **close-up with a person**
- Pinterest → **vertical pin** (2:3)
- Website header, email banner → **wide hero banner** (16:9 or 21:9)
- Carousel, multi-slide set → **a set locked to one visual system**
- Worn by a model, try-on → **model shot**
- Floating, splash, surreal, sculptural → **conceptual shot**
- New mood or season for an existing photo → **restyle** (an edit)

**Tie-breakers:** the platform or format beats the scene ("a Pinterest pin of my candle on a counter" is a pin; "a hero banner of my product in use" is a banner); multi-slide wins; the more specific genre wins. [SINGLE-SOURCE A3]

## 2. Ask (4 questions at most, labeled options, skip what's known) [AGREED §3#5]

- **No product photo yet:** ask for one first; it gives much higher fidelity. Otherwise get the category, packaging, colors and distinctive features. [SINGLE-SOURCE A3]
- **Photo in hand, open request:** how many [1 / 3 / 5]; style [clean studio / lifestyle / conceptual / with a model]; where it's used [store listing / Instagram / Pinterest / paid ads / website]; brand colors (skip if obvious).
- **Restyle:** which aesthetic, which season, what must not change.
- **Model shot:** the model archetype, the environment, the framing [full body / three-quarter / waist up / close on the product].

## 3. Plan the shoot

- **Eight shot types:** hero packshot on a seamless background · macro detail (texture, material, craft) · lifestyle in context · flat lay (top-down, curated props) · unboxing or packaging · hand or human context · range (variants or sizes together) · creative editorial. A full shoot uses the 4–6 that fit the brand; a single request uses the one that fits. [SINGLE-SOURCE D7]
- **Light by category:** soft diffused studio for beauty and skincare; hard, high-contrast chiaroscuro for luxury and men's grooming; golden hour or natural light for wellness and food. [SINGLE-SOURCE D7] Always name the setup. [AGREED §3#17]
- **Lens strings, optional:** 100mm macro f/2.8 for detail; 85mm f/8 for a packshot; 35mm f/4 in daylight for lifestyle. [AGREED §3#34]
- **Aspect by destination:** store main image 1:1 on a pure white seamless background [SINGLE-SOURCE D7]; Pinterest 2:3; Reels and Stories 9:16; banners 16:9 or 21:9. An Instagram 4:5 slot: Flare has no 4:5 [DOCS 09.25.26], so render 3:4 and crop to 4:5. [SINGLE-SOURCE §5.4]

## 4. Write each prompt

- A photo, so **the product comes first**, then scene, light, camera, style. [SINGLE-SOURCE: D1 (§4#38)]
- **Product photo attached: "match the product only."** Shape, label and colors come from the photo; the words go to scene, surface, props, light and angle. [SINGLE-SOURCE §5.4; AGREED §3#31]
- **Visible label or packaging text** needs a GPT-Image-class model: Flare, the default image route. [SINGLE-SOURCE: A3, JOE (§4#19)] Text that must read correctly goes in double quotes with its position. [AGREED §3#12]
- Name the materials and surfaces (frosted glass, matte anodized aluminum, brushed steel, kraft paper). [SINGLE-SOURCE §5.1]
- **Anti-slop:** no automatic floating product, plastic sheen, marble-pedestal "luxury", leaves = organic or sparkles = premium. Floating or splash only when the client asked for a conceptual shot. [SINGLE-SOURCE §5.1]
- **People in the shot:** a real person's likeness needs their rights. [AGREED §3#35] Identity comes from a reference photo, not a description. [AGREED §3#31]
- **Restyle is an edit:** "Change ONLY the season and mood to … Keep the product, its label, shape, size and position exactly unchanged." One change per pass. [AGREED §3#6; SINGLE-SOURCE: A18, A9 (§4#6)]
- **Resolution:** draft at 1k / low while exploring; finals at 2k / high. [AGREED §3#14; AGREED §3#22]

## 5. Sets, hand-off and checks

- A set or carousel **locks one visual system**: paste the same background, light and palette string word for word into every shot. [AGREED §3#1] Variants differ in angle, light and palette, not in paraphrased wording. [SINGLE-SOURCE §5.1]
- Hand `higgsfield-superengine:hf-generate` the final prompt, the model (from `${CLAUDE_PLUGIN_ROOT}/references/model-picker.md`; Flare unless it says otherwise; check it for a pixel-faithful, no-text edit such as a background swap), every setting stated explicitly (from `${CLAUDE_PLUGIN_ROOT}/references/settings-defaults.md`), and the product photo with its job.
- Run the first shot, get a yes, then batch the rest. [AGREED §3#41]
- **Check:** the label reads exactly; the product's shape and color match the photo; the hero fills enough of the frame; no stray text; plus image-prompting's redo list. Fix one thing per pass.
