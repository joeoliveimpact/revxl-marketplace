# Grok Imagine Video 1.5 (REST)

**Settings only.** No source has current Grok Video guidance (playbook §8 gap). Use the universal video rules in the video-prompting skill. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `xai/grok-imagine-video/v1.5/reference-to-video`: one endpoint, three modes.

## Settings [DOCS 09.25.26]
- Modes: text only; one first frame (`image_url`); or references (`image_urls` ≤7 plus `audio_url`). Never combine the first frame with references.
- `duration` 1–15 s (default 5).
- `resolution` 480p/720p/1080p (default 480p); in reference mode only 480p or 720p.
- `aspect_ratio` auto, 1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3 (default auto).
- Images must be JPEG, PNG, WebP or GIF; SVG and XML are unsupported.
- No audio flag. Whether it outputs audio without an `audio_url` is untested.

## Cost and asks
- Priced from the live `/estimate`.

## Known failure modes
- 1080p with references is rejected, although the shared schema lists it. [DOCS 09.25.26]
