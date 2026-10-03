---
name: thumbnails
description: Use when a client wants a YouTube thumbnail or video cover image generated on Higgsfield through this plugin (the Higgsfield REST API with their own key). Trigger phrases include "make a thumbnail for this video", "thumbnail ideas for", "redo my thumbnail", "thumbnail with my face", "faceless thumbnail", "cover image for my video", "make the thumbnail pop". Brainstorms concepts, writes a headline-plus-proof-object prompt that stays readable at small size, locks the face from a photo, and hands it to hf-generate to price and run. Not for video titles or channel strategy, static ads (static-ads), product photos (product-shots), or the official Higgsfield CLI youtube-thumbnail skill.
---

# Thumbnails: the finished thumbnail image

## Output contract

- **Produces:** a short concept list first, then 1 to 3 finished thumbnails (16:9; 9:16 for a vertical cover) made through `higgsfield-superengine:hf-generate`. Each final prompt is **shown in full** before it runs [SINGLE-SOURCE: project approval gates (§4#35)], with its model and settings.
- The thumbnail must **honestly represent the video**; it may exaggerate, never mislead. [SINGLE-SOURCE §5.2]
- The prompt craft lives in `higgsfield-superengine:image-prompting`; invoke it if it isn't loaded.

**Re-invoke guard:** if the session has compacted since this skill loaded, or a step below seems to be missing, invoke `higgsfield-superengine:thumbnails` again before the next thumbnail.

Tags follow image-prompting's legend (TESTED / DOCS hard; AGREED firm defaults; SINGLE-SOURCE starting bets).

## 0. Connection check (free)

Before the questions, look for the file `higgsfield/.python` in the workspace folder (setup writes it). Missing: run `higgsfield-superengine:higgsfield-setup` first, then come back here with the request intact. Present: go ahead; hf-generate re-checks the key before anything spends. Nothing is spent here.

## 1. Ask (4 questions at most, labeled options, skip what's known) [AGREED §3#5]

1. **The video:** what it's about and its title. The thumbnail teases or answers the title; it doesn't repeat it.
2. **Face or faceless?** Always ask; it depends on the channel's niche and there is no universal winner. [SINGLE-SOURCE: A7, A21 (§4#34)] With a face: a clear, well-lit photo of the person, who must be the client or someone whose likeness they have rights to. [AGREED §3#35]
3. **Headline:** the client's 2–4 words, or [Propose 2–3 options].
4. **Look:** brand colors, or their own past thumbnails to stay consistent with (theirs may be attached as a style donor).

## 2. Concepts first

- Brainstorm **at least 5 concepts across different frameworks** (posed portrait, one action mid-moment, before/after, the product as the answer, extreme size contrast, a simple graphic or chart, a big number or day badge), then recommend the strongest. [SINGLE-SOURCE §5.2]
- Each concept opens an **information gap**: the image raises the question the video answers. [SINGLE-SOURCE, Higgsfield's youtube-thumbnail skill]
- **One unified frame, no split screen**, unless the video is a comparison. [SINGLE-SOURCE §5.2]
- **Someone else's thumbnail** as inspiration: describe its idea in words; never attach it. [SINGLE-SOURCE: A6, A7, D4 (§4#36)]

## 3. Write the prompt

- **Headline pack:** a 2–4 word headline in heavy, condensed, all-caps type, with **one word emphasized** (color flip, reversed box or underline); one headline plus **one proof object**; maximum contrast; no clutter. **Keep the bottom-right ~30% clear** for the duration stamp. [SINGLE-SOURCE §5.2]
- Headline in double quotes with position, style and color [AGREED §3#12], baked in [AGREED §3#23], placed so it never covers a face.
- **References manifest first:** with any attached image, the prompt's first line is `IMAGE REFERENCES: image 1 = <person / object>; image 2 = …` in upload order. The `#K` below is that number. [SINGLE-SOURCE §5.2, official youtube-thumbnail skill]
- **Faces:** 40–60% of the frame. For each photo-referenced person, the identity-lock block, verbatim: "CHARACTER N: the person from attached face reference #K — IDENTITY LOCK: reproduce this exact person with a photographic identity match — same bone structure, eye shape, nose, lips, jawline, skin tone, hairline and hair texture. Do not beautify, average, or restyle the face. Expression: <emotion phrase>." Light people with the lighting-rig phrase: "signature YouTube thumbnail lighting rig — strong key light sculpting the face, soft dreamy fill lifting shadows, and defined back light plus hair light tracing a clean bright rim around hair, shoulders and silhouette." [SINGLE-SOURCE §5.2] (Both quoted from Higgsfield's MIT-licensed youtube-thumbnail skill.)
- **Skin:** pass the real photo as a **second** reference and write "render skin to match the real photo" on every pass that touches the face. [SINGLE-SOURCE, field notes §5.2]
- **Render at 2k / high, not 4k**: 4k invents skin texture and blotches the headline. [AGREED §3#22] Set 16:9 explicitly (Flare, the default image route, supports it) [DOCS 09.25.26].

## 4. Variants and the pick

- Make **2–3 headline variants**; keep the one that still reads at about 120px wide (shrink it to check). [SINGLE-SOURCE §5.2] Change one thing per variant. [AGREED §3#13]
- Draft concepts at 1k / low; render the chosen one at 2k / high. [AGREED §3#14]
- **Edits repaint the whole frame:** one change per pass, "Change ONLY the expression to …; keep identity, pose, text, background, lighting and composition exactly unchanged", and measure placement rather than eyeball it. [SINGLE-SOURCE: A18, A9 (§4#6)]

## 5. Hand off and check

- Hand `higgsfield-superengine:hf-generate` the final prompt, the model (from `${CLAUDE_PLUGIN_ROOT}/references/model-picker.md`; Flare unless it says otherwise), every setting stated explicitly (from `${CLAUDE_PLUGIN_ROOT}/references/settings-defaults.md`), and the face photo (first) and other references with their jobs.
- **Check:** the headline is spelled exactly and reads at ~120px; the face matches the photo; skin isn't waxy; the bottom-right is clear; one focal point; plus image-prompting's redo list.
