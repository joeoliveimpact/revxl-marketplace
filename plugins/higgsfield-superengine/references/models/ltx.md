# LTX-2.5 (REST)

Fast/Pro video with a camera enum; Fast goes up to 4k. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `lightricks/ltx-2.5/text-to-video/fast`, `lightricks/ltx-2.5/text-to-video/pro`
- `lightricks/ltx-2.5/image-to-video/fast`, `lightricks/ltx-2.5/image-to-video/pro`

## Settings [DOCS 09.25.26]
- `prompt` ≤5,000 chars. `duration` 6, 8 or 10 only (default 6).
- Pro: `resolution` 720p/1080p, `fps` 24/25/50. Fast: 720p/1080p/2k/4k, 24/25/48/50 fps. Defaults 720p, 25 fps.
- `aspect_ratio` 16:9 or 9:16 only (default 16:9). `generate_audio` default true.
- `camera_movement`: dolly_in, dolly_out, dolly_left, dolly_right, jib_up, jib_down, static, focus_shift.
- Image-to-video: `image_url` (first frame) plus optional `end_image_url`.

## Prompting rules [SINGLE-SOURCE: B9, every rule here]
- 4–8 present-tense sentences linked with "as / while / then".
- Order: shot and style → setting and light → subject → chronological action → camera and resulting frame → synchronized audio.
- Multi-shot: "A hard cut transitions to…", and re-identify characters at each cut. "The camera pans" keeps one take.
- Keep the text's camera direction consistent with `camera_movement`.
- Don't promise exact on-screen spelling; add titles in post.
- Use observable emotion cues; avoid still-photo phrasing; no legacy `Style:` prefix.

## Cost and asks
- All four are priced from the live `/estimate`.

## Known failure modes
- 2k, 4k or 48 fps on a Pro endpoint are outside its schema (use Fast); a duration other than 6/8/10 is too. [DOCS 09.25.26]
