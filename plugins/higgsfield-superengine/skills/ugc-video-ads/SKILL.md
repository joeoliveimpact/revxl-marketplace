---
name: ugc-video-ads
description: Use when a client wants a UGC-style (creator-style) video ad generated on Higgsfield through this plugin (the Higgsfield REST API with their own key). Trigger phrases include "make a UGC ad for my product", "creator-style video of someone using my product", "talking-head ad", "testimonial-style video ad", "unboxing video ad", "selfie-style product video", "person holding my product talking to camera". Plans the shots, fits the client's own lines to the clip, writes the video prompts, and hands each one to hf-generate to price and run. The client brings the script and offer. Not for writing ad scripts, hooks or strategy from scratch, still ads (static-ads), product-only reveal clips (video-prompting), or lip-syncing a real recorded voice-over.
---

# UGC video ads: creator-style ad clips

## Output contract

- **Produces:** a finished creator-style ad, as one continuous clip or a short cut sequence, made through `higgsfield-superengine:hf-generate`. First a one-screen **shot plan** (shots, lines per shot, length, sound); then each final prompt, **shown in full** before it runs [SINGLE-SOURCE: project approval gates (§4#35)], with model, mode and settings.
- **The client brings the words**: their script, hook and offer (or the one to three lines to say). This skill fits those words to the clip; it doesn't write strategy or hooks from scratch, and never invents claims, results, prices or testimonials. [AGREED §3#21]
- The video craft lives in `higgsfield-superengine:video-prompting`, the creator still in `higgsfield-superengine:image-prompting`; invoke them if they aren't loaded.

**Re-invoke guard:** if the session has compacted since this skill loaded, or a step below seems to be missing, invoke `higgsfield-superengine:ugc-video-ads` again before the next clip.

Tags follow video-prompting's legend (TESTED / DOCS hard; AGREED firm defaults; SINGLE-SOURCE starting bets).

## 0. Connection check (free)

Before the questions, look for the file `higgsfield\.python` in the workspace folder (setup writes it). Missing: run `higgsfield-superengine:higgsfield-setup` first, then come back here with the request intact. Present: go ahead; hf-generate re-checks the key before anything spends. Nothing is spent here.

## 1. Ask (4 questions at most, labeled options, skip what's known) [AGREED §3#5]

1. **On camera:** [The client, from their photo / An AI creator (we make a creator still first) / Hands only, no face]. A real person's likeness needs their rights. [AGREED §3#35]
2. **The words:** their script or lines, or [No speech: music or ambient only].
3. **Format:** [One continuous clip / A cut sequence: creator → product close-up → reaction → call to action], the length, and where it runs (vertical 9:16 for Reels, TikTok and Shorts).
4. **The product:** a clear product photo.

## 2. Shape the ad

- **Hook in the first second:** the product, the problem or a pattern interrupt on screen immediately. [AGREED §3#25] Vertical: "subject centered, vertical composition". [SINGLE-SOURCE §5.20]
- **A ~30s skeleton:** hook 0–3s → problem 3–10s → product and proof 10–25s → call to action 25–30s; compress it for shorter ads. [SINGLE-SOURCE §5.40]
- **Fit the lines:** 15 words or fewer per sentence, numbers written out, about 150 words a minute, no em dashes, ellipses or `[PAUSE]` markers. [AGREED §3#29] About 2–3s per line; lip-sync degrades past about 6–7s, so split a long script across several clips or shots. [SINGLE-SOURCE §5.20]
- **Keyframe first:** make or pick the creator still, get a yes, then animate it. [AGREED §3#18] Reuse the same creator still for every clip of the campaign; one creator persona per brand. [SINGLE-SOURCE §5.40]
- **Model:** from `${CLAUDE_PLUGIN_ROOT}/references/model-picker.md`. Seedance 2.5 is the default video model; Kling 3.0 for a directed cut sequence. [SINGLE-SOURCE: A1, A13 (§4#11)] Settings from `${CLAUDE_PLUGIN_ROOT}/references/settings-defaults.md`, sound set explicitly. [SINGLE-SOURCE: catalogs (§4#14)]

## 3. Write the prompts

- **One continuous clip:** one flowing paragraph, no "Scene 1 / Scene 2". Location first ("INTERIOR kitchen, morning light"). Body mechanics over vague verbs. Pin prop counts ("only ONE bottle"). Sound as `Audio: "line 1" / [sound] / "line 2". Natural room acoustics.` [SINGLE-SOURCE §5.22]
- **Cut sequence:** creator → product close-up → reaction → call to action, one shot each in the model's multi-shot field, not typed into one prompt. [SINGLE-SOURCE §5.24] The multi-shot field is documented (DOCS 09.25.26; untested on REST).
- **Identity from the reference, not words:** spend the words on action. [AGREED §3#31] Point identity at the reference once in the action and once as a closing rule ("the creator's face stays exactly as in @Image1"), without describing the features. [SINGLE-SOURCE §5.22]
- **Product handling:** "product held in right hand at chest height, label facing camera". [SINGLE-SOURCE §5.40]
- **Trust signals:** small creator mannerisms (a nervous laugh, a hair tuck, direct eye contact). [SINGLE-SOURCE §5.40] Emotion as visible cues. [AGREED §3#27]
- Camera: lock it if wanted, but the creator always keeps micro-motion (breathing, blinks). [SINGLE-SOURCE: C3, C5, C13 (§4#10)]
- **Sound:** say "no music" when it's voice only. [AGREED §3#10] Generated voice is a draft or guide track for client work; a real voice-over gets mixed in afterwards. [AGREED §3#40]
- Mood words like "intimate" can trip false nsfw flags on product prompts. [SINGLE-SOURCE §5.0#22] Real-face references can be rejected; don't retry the same media. [SINGLE-SOURCE §5.21]

## 4. Variants, draft ladder, hand-off

- **Variants change one thing:** only the creator, or only the hook, with everything else pasted word for word. [SINGLE-SOURCE §5.22; AGREED §3#13] Hooks matter more than format: test several hooks on one format before one hook across formats. [SINGLE-SOURCE §5.40]
- **Ladder:** creator still → cheapest preview (lowest resolution, shortest length) → confirm → hero. [SINGLE-SOURCE §5.20] Each step goes to `higgsfield-superengine:hf-generate`, which prices it first. [AGREED §3#14]
- Hand hf-generate the final prompt(s), model, mode, every setting stated explicitly, and the creator still and product photo with their jobs.
- **Check:** the duration, and frames at the start, middle and end for face melt; the label reads; lips roughly match the lines; the hook lands in the first second. Fix one thing per pass. [SINGLE-SOURCE §5.20; AGREED §3#13]
- Recording a real voice-over and lip-syncing it isn't reachable through this plugin; the nearest option here is native dialogue with short lines. [SINGLE-SOURCE §7]
