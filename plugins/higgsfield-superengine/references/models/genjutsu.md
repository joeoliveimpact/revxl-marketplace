# Genjutsu motion transfer and object swap (REST)

Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `higgsfield/genjutsu/motion-transfer/v1.0`
- `higgsfield/genjutsu/object-swap/v1.0`
- The older misspelled slug is legacy and hidden from discovery; don't use it. [DOCS 09.25.26]

## Settings [DOCS 09.25.26]
- `video_url` required: at least 4 s; longer than 30 s is trimmed to 30 s; output length follows the source.
- `image_urls` required: 1–8 images.
- `prompt` optional (≤10,000 chars). `resolution` 720p/480p (default 720p).
- Object swap: the source video needs at least 409,600 pixels per frame (width × height).

## Prompting rules
- Motion transfer: describe appearance and scene, not the motion. [SINGLE-SOURCE: B9]
- Object swap: "Replace [X] with [the item in image 1], preserving all original motion and camera work". [SINGLE-SOURCE: C15, B5]

## Cost and asks
- Priced per second of source video. The length isn't known before submit, so it's priced as 30 s and often goes over the silent cap and asks.

## Known failure modes
- A source video under 4 s, or an object-swap source under 409,600 pixels per frame, is rejected. [DOCS 09.25.26]
