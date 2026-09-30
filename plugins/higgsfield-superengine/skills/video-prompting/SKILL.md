---
name: video-prompting
description: Use when a client wants a general video clip made on Higgsfield through this plugin (the Higgsfield REST API with their own key), or wants a video prompt written, fixed or improved. Trigger phrases include "make a video of", "animate this image", "turn this photo into a video", "product reveal video", "make this loop", "extend this clip", "edit this video so", "write me a video prompt", "why does my clip look off". Teaches the video prompt craft (shot structure, camera and motion words, sound and dialogue lines, frames and references, multi-shot, continuity) and hands the finished prompt to hf-generate to price and run. Not for UGC or creator-style video ads (ugc-video-ads has that), still images, writing scripts or ad copy, or requests to run Veo or Gemini Omni, which this plugin cannot reach.
---

# Video prompting: the craft

## Output contract

- **Produces:** one finished prompt per clip (or one per shot in a multi-shot clip), **shown to the client in full** before anything runs, plus the model pick, the mode, and every setting written out, sound included. [SINGLE-SOURCE: project approval gates (§4#35)]
- **Then hands off** to `higgsfield-superengine:hf-generate`, the only skill that spends. It prices the job first and asks when the price needs a yes. This skill never spends and never calls the API itself.
- If the client only wants the prompt, stop after showing it.
- Creator-style video ads go to `higgsfield-superengine:ugc-video-ads` (it uses this method). Stills go to `higgsfield-superengine:image-prompting`.

**Re-invoke guard:** if the session has compacted since this skill loaded, or a step below seems to be missing, invoke `higgsfield-superengine:video-prompting` again before writing the next prompt.

## Evidence tags

Every rule carries its tag from the plugin's master playbook (§ = playbook section, kept so tags can be upgraded as tests land). The four tags match the model files: **TESTED** = at least 2 REST samples with a verdict · **DOCS** = a setting fact from the Higgsfield REST docs, 09.25.26 snapshot · **AGREED** = 3 or more independent authors, shown in the playbook's repetition map (§3) · **SINGLE-SOURCE** = one REST sample, or fewer than 3 independent authors shown to agree. "Field notes" = the plugin author's proven notes (reference, never TESTED).

Hold TESTED and DOCS as hard facts, AGREED as firm defaults, SINGLE-SOURCE as starting bets to drop when the client's own results say otherwise.

## 1. Ask, then pick

- Ask **at most 4 short questions with labeled options**; skip what the conversation already answers; don't describe the plan and submit in the same breath. [AGREED §3#5] Usual gaps: where it plays (aspect ratio, vertical or not), length, sound (none / ambient / music / dialogue), a starting image or references the client owns, and the one thing that must happen.
- Pick the model with `${CLAUDE_PLUGIN_ROOT}/references/model-picker.md`; **Seedance 2.5 is the default video model**, Kling 3.0 when you want directed multi-shot. [SINGLE-SOURCE: A1, A13 (§4#11)] Then open that model's file in `${CLAUDE_PLUGIN_ROOT}/references/models/` (the picker names it). It holds the field names, caps, modes and reference-token syntax, and wins where it differs from this file.
- **Set every setting explicitly, sound above all.** Audio defaults differ by model, some on and some off. [SINGLE-SOURCE: catalogs (§4#14)] MiniMax H3 has no audio switch and returns sound anyway (TESTED, 2 REST samples, T11). Values come from `${CLAUDE_PLUGIN_ROOT}/references/settings-defaults.md`.
- **Pick the shortest duration that fits the beats.** Don't fill the maximum; video bills by length. [AGREED §3#20]

## 2. Choose the mode (modes don't mix)

- Modes: text only · start image (i2v) · start + end frames · references (ref2v) · edit a clip · extend a clip · motion transfer. **Frames and references are separate modes; never mix them in one call.** [AGREED §3#38]
- **Start image (i2v):** the image already fixes the look, so the prompt is **motion and camera only**; don't re-describe the frame. Restate what must hold ("preserve the face, pose and clothing; only the camera moves"). [AGREED §3#15] The start frame's aspect ratio drives the whole clip. [SINGLE-SOURCE §5.24]
- **Start + end frames** give boundary control; an identical start and end frame makes a seamless loop. The two frames must match in palette, style and light. [AGREED §3#19]
- **Keyframe first:** character sheet or anchor still, then animate. [AGREED §3#18] A storyboard sheet goes in as a **reference, never as the start frame** (it would become the literal first frame). [SINGLE-SOURCE: A8 (§4#37)]
- **Edit** a clip that is mostly right rather than regenerating it. [SINGLE-SOURCE §5.21] Name the source clip as the sole edit master, state the preserved context first, then the region, then the change; one edit per pass; edit and extend are two separate prompts. To replace a moving subject, keep the original's timing, path, speed and occlusions. [SINGLE-SOURCE §5.21] Around the 4th edit round quality drops: regenerate fresh from a description of the current version. [SINGLE-SOURCE §5.26]
- **Extend:** "the new first image continues the clip's final frame"; state what already finished and don't replay it. [SINGLE-SOURCE §5.21]
- **Motion transfer:** the driving video supplies the motion. The prompt describes only appearance and scene, and the framing matches (full body to full body). [SINGLE-SOURCE §5.20]

## 3. Write the shot

- A **directed brief in sentences**: direct a scene, don't describe an image. [AGREED §3#9]
- Order: style line, shot, actor behavior, environment, camera, sound. [SINGLE-SOURCE §5.20] The style line is one line with one look ("35mm anamorphic, naturalistic color, soft contrast"). [SINGLE-SOURCE §5.20]
- **One take, one location:** one flowing paragraph. **Several beats:** untimed stages ("Stage 1: Start with <state>. <one action>. End with <state>."). [SINGLE-SOURCE: C15, A14 (§4#8)] **Seedance 2.5: never bracketed timecodes** — they were blocked as `nsfw` 2/2 (TESTED, 2 REST samples); stages worked (SINGLE-SOURCE: REST, 1 sample). **Kling:** multi-shot goes in the model's multi-shot field, one short prompt per shot, not typed into the text (DOCS 09.25.26; untested on REST).
- **Camera:** real vocabulary (dolly push, whip-pan, rack focus, tracking). [AGREED §3#3] One motivated move per shot on Seedance and by default; up to 2 on Kling. [SINGLE-SOURCE: A15, B9, A16 (§4#9)] Lock the camera when wanted ("static locked-off camera, zero movement"), but always give the subject micro-motion: breathing, a blink, wind. [SINGLE-SOURCE: C3, C5, C13 (§4#10)] Partial orbits with a number ("orbit 45° at constant velocity") are fine; full 360s and a vague "epic drone shot" are the risk. [SINGLE-SOURCE: C1, C2, C20 (§4#16)]
- **Motion:** cinematic verbs, not "moves" or "goes"; a speed anchor instead of a bare "slow" ("like dust suspended in honey"); numbers where they matter ("push-in over 2.5s"). [AGREED §3#26]
- **Actors:** emotion as visible physical cues ("her eyes glass over; she does not blink"), a weight cue, a micro-action and a held beat. Actions get a start point, a path and a force. [AGREED §3#27]
- **Environment:** wind or water acting on several elements (one moving element reads as a fan on set). Stop the model filling empty space with spatial zoning ("left third: pure black, no movement; right two-thirds: all action"). [SINGLE-SOURCE §5.20]
- **Continuity inside a clip:** each beat starts from the result of the last; the cause comes before the reaction; anchor space to fixed objects (the counter, the doorway). [SINGLE-SOURCE §5.20] Pin prop counts and who holds what ("only ONE ice cube", "the cup stays in her left hand"). [AGREED §3#37]
- **Beats:** 15s holds 2–4 clear beats. A random extra shot at the end means the duration was too long for the beats. [AGREED §3#20]
- **End deliberately:** state the final state and any residual motion ("End on …"). [AGREED §3#28] On Kling, "Motion settles as <state>" controlled how the clip ended (SINGLE-SOURCE (REST, 1 sample per arm), T17).
- **Transitions** (dissolve, morph, wipe): fine as a deliberate design inside one generated multi-shot piece; banned as invisible bridges between separate clips. [SINGLE-SOURCE: C2, C20, C8, C9, C11 (§4#15)]
- **Several characters:** position and outfit anchors, a fixed camera, 3 or fewer tracked subjects. [SINGLE-SOURCE §3#36]
- **Settings stay out of the text:** no model, resolution, duration, fps or hype words; use the duration only to plan the beats. [tag soup is OUTDATED-EVERYWHERE §3#7]
- **Phrase constraints positively;** use a negative field only where the model has one. Skip anatomy "do-not" tails: no visible gain (SINGLE-SOURCE (REST, 1 sample per arm, T3)). [AGREED §3#24]

## 4. Sound and dialogue

- **Sound gets its own line:** primary source, secondary, music (instruments + emotion, "low in the mix"), atmosphere. Place sounds in space ("rain close in the foreground, thunder distant"). Write "no music" or "room tone only, no dialogue" when that's wanted. [AGREED §3#10]
- Sound not essential and the model has a switch: turn it off (cheaper, fewer artifacts). [SINGLE-SOURCE §5.20]
- **Dialogue:** quote each line with a voice tag before it ("(she speaks with a warm Irish accent): '…'"). Sentences of 15 words or fewer, numbers written out, about 150 words a minute, no em dashes, ellipses or `[PAUSE]` markers. [AGREED §3#29] Allow about 2–3s per line; lip-sync degrades past about 6–7s. [SINGLE-SOURCE §5.20] Don't invent dialogue the client didn't give. [SINGLE-SOURCE §5.21]
- Generated sound is a draft or guide track for client work; real voice-over gets mixed in afterwards. [AGREED §3#40]

## 5. References

- **One narrow job per reference:** "@Image1 controls only the jacket. Do not copy her face." Main subject first; list unused references as controlling nothing; check the upload order before writing index labels; don't let an image and a video compete for the same job; a video used for motion contributes no identity, clothing or setting. [AGREED §3#2]
- Use the reference token the model file documents, **followed by a noun clarifier**: "@Image1 (the dark-haired woman) walks into @Image2 (the living room)". Never put a verb or number straight after the tag. [SINGLE-SOURCE: A15 (§4#30)] On Seedance 2.5, `@ImageN` or `<<<image_N>>>` (SINGLE-SOURCE: REST, 1 sample per direction, T1 + T1b); never plain "Image N", which morphed between references (SINGLE-SOURCE: REST, 1 informative sample, T1b).
- **Reference attached:** spend the words on the action, not the face. Re-describing a referenced face weakened the action. [AGREED §3#31; SINGLE-SOURCE (REST, 1 sample per arm, T5, Seedance 2.5 ref2v)]
- **Style from the client's own image:** attach it with the style-donor line ("Take only the visual render style and color grading. Never use the characters, inscriptions…"); it carried the style without the character (SINGLE-SOURCE (REST, 1 sample), T16). Someone else's image: describe its style in words. [SINGLE-SOURCE: A6, A7, D4 (§4#36)]
- Real-face references can be rejected; don't retry the same media. [SINGLE-SOURCE §5.21]

## 6. Across clips

- The model remembers nothing between calls. Paste the same continuity anchors **word for word** into every shot: lighting, wardrobe, time of day, where the actor ended the last shot, and the sound bed. Never "(as above)". [AGREED §3#1]
- Chain clips on the **actual last rendered frame**, and never switch models mid-chain. Longer pieces are micro-takes, each with a set first and last frame and fewer characters. [SINGLE-SOURCE §5.20]
- Music across stitched clips: tempo and key in every prompt, and "ends clean on the downbeat". [SINGLE-SOURCE §5.20]
- Vertical: "subject centered, vertical composition". [SINGLE-SOURCE §5.20] For ads, the hook lands in the first second. [AGREED §3#25]

## 7. Draft, iterate, check

- **Ladder:** storyboard sheet (as a reference) → end-frame still → cheapest preview (lowest resolution, shortest length, cheapest tier) → confirm → hero. [SINGLE-SOURCE §5.20] hf-generate prices each step before it runs. [AGREED §3#14]
- Change **one variable per pass**. [AGREED §3#13] After **2 misses** on the same problem, change the anchor, structure or model; never a third identical retry. [AGREED §3#8] One job at a time while iterating. [AGREED §3#41]
- **Check every result:** the duration, and 3 frames (start, middle, end) for face melt. Redo once with a simpler prompt; the client is the final judge. Make 2 variants of important shots. [SINGLE-SOURCE §5.20]
- On an `nsfw` or `ip_detected` block: rephrase away from brands and real people, remove one reference at a time, never resubmit unchanged. [AGREED §3#11]
- No real people or brands without rights. [AGREED §3#35] "Make it look like <director>" becomes an original homage. [SINGLE-SOURCE §5.0#23] Never invent claims, prices, stats or quotes. [AGREED §3#21]
