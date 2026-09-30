# Seedance 2.0 (REST)

The REST pick for 1080p and 4k Seedance. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `bytedance/seedance-2.0/text-to-video`
- `bytedance/seedance-2.0/image-to-video`
- `bytedance/seedance-2.0/reference-to-video`

## Settings [DOCS 09.25.26]
- `duration` 4–15 s (default 5). `resolution` 480p/720p/1080p/4k (default 720p). `generate_audio` default true. No seed, no genre, no `bitrate_mode`.
- `aspect_ratio` (text-to-video, reference-to-video): 16:9, 4:3, 1:1, 3:4, 9:16, 21:9 (default 16:9). Image-to-video framing follows `image_url`.
- Image-to-video: `image_url` required, `end_image_url` optional, prompt optional.
- Reference-to-video: up to 9 images, 3 videos, 3 audio. Needs a non-empty `image_urls` or `video_urls`; audio alone doesn't count. Never mix reference arrays with `image_url`, `end_image_url` or `video_url`. Reference videos are trimmed to 15 s each; audio to 2–15 s per file, 15 s total.
- Public media URLs only; `asset://` is rejected.

## Prompting rules
- Use the 8 elements as a checklist, not a keyword template: subject, action, scene, lighting/color, camera, style, (quality goes in the parameter), positive constraints. Or director sections: `Setting: Action: Camera: Style: Audio: Shot 1: … Final shot:`. [SINGLE-SOURCE: A15, B9]
- After `@ImageN`, always add a noun clarifier: "@Image1 (the dark-haired woman) walks into @Image2 (the living room)". Never put a verb or number straight after the tag. [SINGLE-SOURCE: A15]
- To anchor identity and motion, pass a character image plus the previously approved shot. [SINGLE-SOURCE: A15]
- Formulas: "Refer to the [subject] from Image N to generate [scene], keeping [subject] consistent"; "Replace [element] in Video N with [new element], preserving all original motions and camera work"; "Generate content after Video N: …". [SINGLE-SOURCE: B5]
- Multi-shot in one clip stays consistent because it's one pass. [SINGLE-SOURCE: A15] Label beats `Stage 1/2/3`: bracketed timecodes were blocked as `nsfw` on Seedance 2.5 REST [TESTED, 2 REST samples, T18]; untested on 2.0.
- Dual-frame archetype: hold on the start frame … match the end frame exactly. Products: a timed SFX list plus a silent tail hold. [SINGLE-SOURCE: C2, C20]
- UGC recreation: one continuous flow, no Scene 1/2; location first ("INTERIOR kitchen"); face lock stated inline and as a closing rule; body mechanics over vague verbs; `Audio: "line 1" / [sound] / "line 2". Natural room acoustics.`; variants change only the character. [SINGLE-SOURCE: C15]
- Pin prop counts and who holds what ("only ONE ice cube"). [AGREED, §3 #37]
- Stay under about 1,000 English words; longer dilutes focus. [SINGLE-SOURCE: A15]
- The anatomy "do-not" tail is opt-in only (no visible gain on Seedance 2.5). [SINGLE-SOURCE: REST, 1 sample per arm, T3]

## Cost and asks
- Priced by the same token formula as Seedance 2.5. `generate_audio` true (the default) asks until the audio cost is measured; set it `false` to be priced silently.
- Reference videos are priced as 45 s of input, so those jobs often go over the silent cap and ask.

## Known failure modes
- Audio-only references, and mixing reference arrays with frame fields, are rejected. [DOCS 09.25.26]
