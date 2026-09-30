# Seedance 2.5 (REST)

The default video model. REST tops out at 720p; use Seedance 2.0 for 1080p/4k. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `bytedance/seedance-2.5/text-to-video`
- `bytedance/seedance-2.5/image-to-video`
- `bytedance/seedance-2.5/reference-to-video`
- `bytedance/seedance-2.5/video-edit`
- `bytedance/seedance-2.5/video-extend`

## Settings [DOCS 09.25.26]
- `duration` 4–30 s (default 5). Video-edit takes no `duration`: it follows the source (normalized to at least 4 s).
- `resolution` 480p/720p (default 720p). `bitrate_mode` standard/high (default high). `generate_audio` default true. Text-to-video also has `output_format` mp4/mov.
- `aspect_ratio` (text-to-video, reference-to-video): 16:9, 4:3, 1:1, 3:4, 9:16, 21:9 (default 16:9). Image-to-video has none: framing follows `image_url`, so crop the start frame to the target ratio first. Edit/extend follow the source video.
- Image-to-video: `image_url` required, `end_image_url` optional, prompt optional.
- Reference-to-video: at least one non-empty array; up to 30 images, 10 videos, 10 audio, 50 items total; video and audio are each normalized to 30 s total. Audio-only references are allowed.
- Edit/extend: `video_url` required, and it counts toward the 10-video limit.
- Public media URLs only; `asset://` is rejected.

## Prompting rules
- Simple shot: `[Subject] in [setting and light] [one action arc]. [Shot size + one motivated camera move]. [Visual treatment]. [Audio]. End on [final image].` [SINGLE-SOURCE: A14, B9]
- Longer clips: `Stage 1: Start with <state>. <one action>. End with <state>.` Stages worked. [SINGLE-SOURCE: REST, 1 sample, T18]
- Complex pieces: `FORMAT / STARTING STATE / TIMELINE / CAMERA / CONTINUITY / AUDIO / ENDING STATE / CONSTRAINTS`. [SINGLE-SOURCE: A14, B9]
- One camera move per shot. [SINGLE-SOURCE: A15, B9 (§4 #9)]
- Reference tokens: `@ImageN` or `<<<image_N>>>`. [SINGLE-SOURCE: REST, 1 sample per direction, T1 + T1b] Never plain "Image N": it morphed between references. [SINGLE-SOURCE: REST, 1 informative sample, T1b]
- Give each reference one narrow, labeled job: "@Image1 controls only [X]. Do not copy [Y]." [AGREED, §3 #2]
- A video that supplies only motion: exclude its identity, clothing and setting. List unused references in an `Unused references:` block, check upload order before writing index labels, and don't let an image and a video compete for one job. [SINGLE-SOURCE: A14, B9]
- Don't re-describe a referenced face; spend the words on action. [SINGLE-SOURCE: REST, 1 sample per arm, T5]
- Style-donor prefix copies style without the character: "Take only the visual render style and color grading… Never use the characters, inscriptions…". [SINGLE-SOURCE: REST, 1 sample, T16]
- Edit: "Edit @Video1. It is the sole edit master… Change only… All other visible content remains unchanged." Preserved context first, then the region, then the change; one edit per pass; split edit-then-extend into two prompts. [SINGLE-SOURCE: A14, B9]
- Extend: "The new first image continues @Video1's final frame." State what already finished; don't replay it. [SINGLE-SOURCE: A14, B9]
- Sound notation: `{dialogue}`, `()` music, `<>` SFX. Don't invent dialogue; with supplied dialogue audio, refer to the asset and never type the words. [SINGLE-SOURCE: A14, B9]
- Prefer editing an unhappy result over regenerating it. [SINGLE-SOURCE: A15]
- Drop the anatomy "do-not" tail: no visible gain. [SINGLE-SOURCE: REST, 1 sample per arm, T3]
- Don't auto-fill 30 s: pick the shortest duration that fits the beats (it bills by length). [AGREED, §3 #20]

## Cost and asks
- Priced by the token formula (resolution × seconds; input-video seconds added; image and audio references free).
- `generate_audio` true (the default) asks until the audio cost is measured; set it `false` to be priced silently.
- Jobs with an input video (edit, extend, video references) are priced as 30 s of input, so they often go over the silent cap and ask.

## Known failure modes
- Bracketed timecodes (`[0-2s] …`) are blocked as `nsfw` on innocent prompts; use Stage labels. [TESTED, 2 REST samples, T18]
- Real-face references may be rejected; don't retry the same media. [SINGLE-SOURCE: A14]
- `asset://` URLs and a `duration` on video-edit are rejected. [DOCS 09.25.26]
