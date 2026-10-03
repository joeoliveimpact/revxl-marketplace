# Ideogram 4.0 (REST)

**Settings only.** No source has model-specific prompting guidance for Ideogram 4.0 (playbook §8 gap). Use the universal image and text rules in the image-prompting skill. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `ideogram/v4.0`: text-to-image, or remix/edit with `image_url`.

## Settings [DOCS 09.25.26]
- `prompt` 2–2,048 chars.
- `image_url` for remix/edit; `image_weight` 1–100 sets how much of the input survives (edit requests only).
- `rendering_speed` TURBO / DEFAULT / QUALITY, case-sensitive (default DEFAULT).
- `aspect_ratio`: 23 values incl. 4:5 (default 1:1, even with an input image, so always set it).

## Cost and asks
- Priced from the live `/estimate`.

## Known failure modes
- Lowercase `rendering_speed` values are rejected. [DOCS 09.25.26]
- Leaving out `aspect_ratio` gives a square, even when editing a non-square image. [DOCS 09.25.26]
