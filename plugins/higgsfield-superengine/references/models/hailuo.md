# Hailuo 2.3 (REST)

**Settings only.** No source has Hailuo prompt guidance (playbook §8 gap); the one routing note is "cheap with strong physics". Use the universal video rules in the video-prompting skill. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `minimax/hailuo-2.3/standard/text-to-video`
- `minimax/hailuo-2.3/standard/image-to-video`

## Settings [DOCS 09.25.26]
- Fixed 768P output; there is no `resolution` field.
- `duration` 6 or 10 (default 6).
- `prompt_optimizer` default **on**: it rewrites your prompt. Set it false to send your prompt as written.
- Image-to-video: `image_url` required.
- No audio, aspect or seed field. Whether it outputs audio is untested.

## Cost and asks
- Both are priced from the live `/estimate`.
