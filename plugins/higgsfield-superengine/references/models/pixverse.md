# PixVerse V6 (REST)

**Settings only.** No source has PixVerse-specific prompting guidance, including how to use its negative field (playbook §8 gap). Use the universal video rules in the video-prompting skill. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `pixverse/v6/text-to-video`
- `pixverse/v6/image-to-video`

## Settings [DOCS 09.25.26]
- `prompt` ≤5,000 chars. `negative_prompt`: a real field, 1–2,048 chars when sent.
- `resolution` 360p/540p/720p/1080p (default 720p). `duration` 1–15 s, fractional allowed (default 5). `generate_audio` default true. `seed` 0–2,147,483,647.
- Text-to-video `aspect_ratio` 16:9, 4:3, 1:1, 3:4, 9:16 (default 16:9).
- Image-to-video: `image_url` plus optional `end_image_url`; no aspect field (framing follows the image).

## Cost and asks
- Both are priced from the live `/estimate`.

## Known failure modes
- An empty `negative_prompt` string is outside the 1–2,048 range; leave the field out instead. [DOCS 09.25.26]
