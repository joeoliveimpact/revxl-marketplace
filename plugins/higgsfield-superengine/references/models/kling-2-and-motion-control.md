# Kling 2.6, Kling 2.5 Turbo, Kling Motion Control 2.6/3.0 (REST)

Older Kling versions (fallbacks) and motion transfer from a driving video. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `kling-video/v2.6/pro/text-to-video`, `kling-video/v2.6/pro/image-to-video`
- `kling-video/v2.5-turbo/pro/text-to-video`, `kling-video/v2.5-turbo/pro/image-to-video`, `kling-video/v2.5-turbo/standard/image-to-video`
- `kling-video/motion-control/std`, `kling-video/motion-control/pro` (Motion Control 2.6)
- `kling-video/v3/motion-control/std`, `kling-video/v3/motion-control/pro` (Motion Control 3.0)

## Settings [DOCS 09.25.26]
- Kling 2.6: `duration` 5 or 10 (default 5); `sound` on/off (default on); `cfg_scale` 0–1 (default 0.5); `aspect_ratio` 16:9/9:16/1:1. Image-to-video has **no last-frame field**.
- Kling 2.5 Turbo: `duration` 5 or 10; `cfg_scale`; a real `negative_prompt`; no `sound` or `aspect_ratio` field.
- Motion Control: `image_url` (the character; ≤10 MB, 300–65,536 px per side; outside a 0.4–2.5 width/height ratio it is adjusted) plus `video_url` (the motion, 3–30 s; over 100 MB is compressed). No `duration`: output follows the video. `character_orientation` image/video (default video); `keep_original_sound` "yes"/"no" strings (default yes); prompt optional.

## Prompting rules
- 2.5 Turbo: keep `negative_prompt` to focused failures you've actually seen, never a generic bank. [SINGLE-SOURCE: B9, B7]
- Motion Control: the prompt describes appearance and scene only; don't re-script the driving performance; match framing between the image and the video (full-body to full-body). [SINGLE-SOURCE: B9]

## Cost and asks
- The 4 Motion Control endpoints **always ask**: `/estimate` fails for them, so the price is unknown.
- Kling 2.6 and 2.5 Turbo are priced from the live `/estimate`.

## Known failure modes
- `keep_original_sound` as a boolean instead of "yes"/"no", or a `duration` on Motion Control, doesn't match the schema. [DOCS 09.25.26]
