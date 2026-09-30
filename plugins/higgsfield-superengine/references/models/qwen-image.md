# Qwen Image 3 (REST)

Reference-faithful edits without text, and text-to-image with a real negative field. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `alibaba/qwen-image-3/text-to-image`
- `alibaba/qwen-image-3/edit`

## Settings [DOCS 09.25.26]
- `negative_prompt`: a real field on both.
- `prompt_extend` and `enable_thinking` default **on**; `enable_thinking` needs `prompt_extend=true`. Set both false to use your prompt as written.
- `prompt_extend_mode`: direct or agent on text-to-image; direct only on edit.
- `resolution` 1k/2k (default 1k; 2k square = 1536×1536). `aspect_ratio` 1:1, 2:3, 3:2, 3:4, 4:3, 7:9, 9:7, 9:16, 16:9, 21:9 (default 1:1); no 4:5.
- `seed` 0–2,147,483,647. About 4,500 tokens of prompt is advisory, not enforced.
- Edit: 1–3 ordered `image_urls`, required. Text-to-image takes no images.

## Prompting rules
- With auto-rewrite on, describe only the edited region; with it off, describe the whole scene. [SINGLE-SOURCE: B7]
- Phrase constraints positively; use `negative_prompt` only where the field exists (it does here). [AGREED, §3 #24]
- Keep negatives short and task-specific, never a generic anatomy bank. [SINGLE-SOURCE: A21, B7 (§5.0 #10)]
- Edits: say only what changes, plus an explicit "keep everything else" list. [AGREED, §3 #6]

## Cost and asks
- Both are priced from the live `/estimate`.

## Known failure modes
- `enable_thinking: true` with `prompt_extend: false` is invalid. [DOCS 09.25.26]
- An empty `image_urls` list on edit is rejected. [DOCS 09.25.26]
