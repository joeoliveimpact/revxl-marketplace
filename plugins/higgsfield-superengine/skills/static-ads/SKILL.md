---
name: static-ads
description: Use when a client wants a finished still ad image generated on Higgsfield through this plugin (the Higgsfield REST API with their own key). Trigger phrases include "generate a static ad for my offer", "make the ad image with this headline", "recreate this ad layout with my product", "put our brand on this ad style", "feed ad creative", "story ad image", "banner ad visual". Runs the visual method (structure from a reference, brand from the client, layout zones, baked headline text, safe zones, variants) and hands each prompt to hf-generate to price and run. The client brings the ad copy. Not for writing ad copy, hooks or campaign strategy, video ads (ugc-video-ads), plain product photos (product-shots), or YouTube thumbnails (thumbnails).
---

# Static ads: the finished still ad image

## Output contract

- **Produces:** 1 to 3 finished still ad images per concept, made through `higgsfield-superengine:hf-generate`. Each final prompt is **shown in full** before it runs [SINGLE-SOURCE: project approval gates (§4#35)], with its model and settings written out.
- **The visual only.** The headline, subline and button text come from the client, word for word. This skill never writes ad strategy or hooks, and never invents claims, prices, stats, reviews or quotes. [AGREED §3#21] No copy yet: ask for it, or leave marked copy space in the design.
- The prompt craft lives in `higgsfield-superengine:image-prompting`; invoke it if it isn't loaded. This file adds the ad-specific method on top.

**Re-invoke guard:** if the session has compacted since this skill loaded, or a step below seems to be missing, invoke `higgsfield-superengine:static-ads` again before the next ad.

Tags follow image-prompting's legend (TESTED / DOCS hard; AGREED firm defaults; SINGLE-SOURCE starting bets).

## 0. Connection check (free)

Before the questions, look for the file `higgsfield\.python` in the workspace folder (setup writes it). Missing: run `higgsfield-superengine:higgsfield-setup` first, then come back here with the request intact. Present: go ahead; hf-generate re-checks the key before anything spends. Nothing is spent here.

## 1. Ask (4 questions at most, labeled options, skip what's known) [AGREED §3#5]

1. **Starting point:** [Recreate a reference ad's layout / Build from the brief]
2. **Exact copy:** the headline (short), an optional subline, the button or CTA text. The client pastes it.
3. **Placement:** [Feed square 1:1 / Feed portrait (4:5 slot) / Story or Reel 9:16 / Landscape 16:9]
4. **Product and brand:** a product photo (much higher fidelity than a description), plus brand colors and font style, or "match the product's own look".

## 2. Structure from the reference, brand from the client

- From a reference ad take **structure only**: the layout, zone proportions and the kinds of UI elements. From the client's brand take the background, typeface and accent colors. Say so in the prompt: "Do not carry over any colour, typeface or visual treatment from the reference; those belong to another brand." [SINGLE-SOURCE §5.4]
- **Someone else's ad is described in words, never attached**; attaching it copies its identity. The client's own past ads may be attached as a style donor. [SINGLE-SOURCE: A6, A7, D4 (§4#36)]
- A product photo attached: "match the product only". Its shape, label and colors come from the photo; the words go to layout, scene, light and type. [SINGLE-SOURCE §5.4]

## 3. Write the prompt

- **Designed graphic, so the image type goes first** ("A 1:1 paid-social static ad for …"), then the product, layout, supporting elements, tone, materials, typography. [SINGLE-SOURCE: B11 (§4#38)]
- **Labeled blocks:** `HEADLINE:`, `LAYOUT:`, `PRODUCT:`, `SUPPORTING ELEMENTS:`, `LIGHTING:`, `AVOID:`. [SINGLE-SOURCE, field notes §5.2]
- **Layout as zone fractions of the frame height**, e.g. headline zone 0.08–0.30, product 0.35–0.85, button 0.88–0.95. Pick the fractions per concept; don't reuse one set everywhere. [SINGLE-SOURCE §5.1]
- **Copy:** in double quotes, with position, font style, color and contrast [AGREED §3#12], baked into the image [AGREED §3#23]. Exact logos or brand fonts: keep their area clear and composite them afterwards. [AGREED §3#33]
- **Legible label or packaging text** needs a GPT-Image-class model: Flare, the default image route. [SINGLE-SOURCE: A3, JOE (§4#19)]
- **Story / Reel 9:16:** keep the top and bottom ~10% free of text, logos, icons and buttons; hands or product entering those bands is fine. [SINGLE-SOURCE §3#52]
- One `AVOID:` line at most, ending with "Just <the elements that should be there>." [SINGLE-SOURCE: A21 (§4#2)]
- **4:5 feed slot:** Flare has no 4:5 [DOCS 09.25.26]. Generate 3:4 and crop to 4:5 (keep the top 93.75% of the height), so keep nothing important in the bottom ~6%. [SINGLE-SOURCE §5.4]
- Always set the aspect ratio: Marketing Studio Image's `auto` without enhancement returns a square. [SINGLE-SOURCE §5.4]

## 4. Variants

- 2–3 variants per concept, **each changing one variable** (headline, hero visual, or layout), so the client can compare them in a test. [AGREED §3#13] They must differ for real, not be paraphrases. [SINGLE-SOURCE §5.1]
- Paste the brand string (palette, type style, background) **word for word** into every variant. [AGREED §3#1]
- Draft at 1k / low while the direction is open; render finals at 2k / high. [AGREED §3#14; AGREED §3#22]

## 5. Hand off and check

- Hand `higgsfield-superengine:hf-generate` the final prompt, the model (from `${CLAUDE_PLUGIN_ROOT}/references/model-picker.md`; Flare unless it says otherwise), every setting stated explicitly (from `${CLAUDE_PLUGIN_ROOT}/references/settings-defaults.md`), and the reference images with their jobs. It prices and runs the job.
- Marketing Studio's built-in preset path (a preset plus prompt enhancement, product image first) is in the model file. It is an alternative to this method; its price can't be fixed in advance, so it always needs the client's yes.
- Run one ad first; batch the rest only after it's approved and priced. [AGREED §3#41]
- **Check:** the copy is spelled exactly; the headline reads at phone size; the product label is intact; nothing sits in a safe zone; plus image-prompting's redo list. Fix one thing per pass: "Change ONLY …, keep everything else exactly unchanged." [SINGLE-SOURCE: A18, A9 (§4#6)]
