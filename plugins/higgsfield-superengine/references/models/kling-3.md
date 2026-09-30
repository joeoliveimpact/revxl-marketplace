# Kling 3.0 and Kling 3.0 Turbo (REST)

Kling 3.0 is the newest Kling and the pick for directed multi-shot or `cfg_scale` control. Turbo is fast, cheap, silent single-frame animation. [SINGLE-SOURCE: C13] Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `kling-video/v3.0/std/text-to-video`, `kling-video/v3.0/std/image-to-video`
- `kling-video/v3.0/pro/text-to-video`, `kling-video/v3.0/pro/image-to-video`
- `kling-video/v3.0/4k/text-to-video`, `kling-video/v3.0/4k/image-to-video`
- `kling-video/v3.0-turbo/text-to-video`, `kling-video/v3.0-turbo/image-to-video`

## Settings [DOCS 09.25.26]
- Kling 3.0: `duration` 3–15 s (default 5); `aspect_ratio` 16:9/9:16/1:1 on text-to-video (image-to-video follows the image); `sound` on/off (default **on**); `cfg_scale` 0–1 (default 0.5). No `negative_prompt`, no seed.
- Image-to-video: `image_url` (first frame, required) plus optional `last_image_url`.
- `elements`: Kling element IDs as decimal strings, owned by the calling account. No REST endpoint creates one; make it in the Higgsfield app.
- Multi-shot: `multi_shots: true` plus 1–6 `multi_prompt` objects `{prompt ≤512 chars, duration 1–15}`, and always a non-empty top-level prompt (≤2,500 chars; longer is truncated). Shot durations add up and set the bill.
- Turbo: no `sound`, `multi_shots`, `elements` or last frame; `duration` 3–15; `resolution` 720p/1080p (default 720p); text-to-video `aspect_ratio` 16:9/9:16/1:1; prompt ≤2,500 (image-to-video) or 3,072 (text-to-video).

## Prompting rules
- "Direct a scene, don't describe an image": `[Scene] + [Subject & appearance] + [Action timeline] + [Camera] + [Audio & atmosphere]`, specs in parameters, 1–3 rich sentences per shot. [SINGLE-SOURCE: B8]
- Open with the shot size plus its abbreviation (ECU/CU/MCU/MS/WS); declare the camera move with a speed word (`static` is valid), at most 2 per shot; lighting triplet "key from camera-left window, 5500K, teal-and-amber"; `First, … Then, … Finally, …`; time slices for shots of 5 s or more; at least 3 physical emotion signals; at most 7 elements per shot. [SINGLE-SOURCE: A16]
- End each shot with `Motion settles as <ending state>`: with it the clip stopped exactly as written; without it, no ending. [SINGLE-SOURCE: REST, 1 sample per arm, T17]
- A locked camera is fine, but always give the subject micro-motion (breathing, blink, wind). [SINGLE-SOURCE: C13 (§4 #10)]
- Camera by intent: emotional → static or very slow dolly in; action → lateral tracking; reveal → slow pan or pull back; product → slow 180° orbit. Put camera language up front. [SINGLE-SOURCE: A16, B3]
- Repeat the full character and environment description word for word in every prompt and shot; never "(as above)". [AGREED, §3 #1]
- Image-to-video: motion and camera only, don't re-describe the frame. [AGREED, §3 #15] One short sentence, one direction; restate what must stay ("preserve the subject's face, pose, clothing; only the camera moves"). [SINGLE-SOURCE: C13, B3]
- Start and end frames should match in palette, style and light. [SINGLE-SOURCE: B8] Identical start and end frames make a seamless loop. [AGREED, §3 #19] The start frame's aspect ratio drives the clip. [SINGLE-SOURCE: B8]
- Dialogue: name the characters `[Character A: Silver-haired CEO]`, tie lines to action, give a voice tone, control timing ("After a beat"). [SINGLE-SOURCE: B8]
- `cfg_scale` 0.7–0.9 for strict adherence on stylized work; 0.3–0.4 for natural motion. [SINGLE-SOURCE: B3]
- Validate on std, finish on pro or 4k. [SINGLE-SOURCE: B3, C3]
- Multi-shot UGC: creator → product close-up → reaction → CTA, one `multi_prompt` each. [SINGLE-SOURCE: C14]
- Suppress text with positive wording ("blank unmarked awning"), not "no text anywhere in frame" (that came back with garbled signage); neither fully cleared storefront lettering. [SINGLE-SOURCE: REST, 1 sample per arm, T4]

## Cost and asks
- All 8 are priced from the live `/estimate`. With multi-shot, the shot durations add up and set the bill.

## Known failure modes
- Silent intent still produces sound unless `sound: "off"`. [SINGLE-SOURCE: C3]
- Top-level prompts over 2,500 chars are silently truncated; an empty top-level prompt with `multi_prompt` fails. [DOCS 09.25.26]
- Output is 24 fps on REST, not 30. [TESTED, 4 REST samples, T10]
- `elements` together with `last_image_url` is untested (T6); foreign element IDs are rejected. [DOCS 09.25.26]
