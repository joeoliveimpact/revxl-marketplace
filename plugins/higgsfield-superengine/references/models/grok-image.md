# Grok Image 2.0 (REST)

**Settings only.** No source has current prompting guidance for Grok Image 2.0 (playbook §8 gap). Use the universal image rules in the image-prompting skill. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `xai/grok-imagine-image-2.0`: text-to-image (no `image_urls`) or editing (with them).

## Settings [DOCS 09.25.26]
- `quality` low or medium only (default medium).
- `resolution` 1k/2k (default 1k).
- `aspect_ratio` auto, 1:1, 1:2, 2:1, 3:2, 2:3, 4:3, 3:4, 16:9, 9:16 (default auto); no 4:5.
- `image_urls`: up to 10 references for editing; they may be resized before submission.
- One image per request; no batch count.

## Cost and asks
- Priced from the live `/estimate`.

## Known failure modes
- `quality: high` is rejected (low/medium only). [DOCS 09.25.26]
