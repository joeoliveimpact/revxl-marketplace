# Z-Image Turbo (REST)

Fast, cheap image iteration before a hero render. [SINGLE-SOURCE: A1, A10] Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `z-image/turbo`: text-to-image only.

## Settings [DOCS 09.25.26]
- `prompt`: non-blank, at most **800 chars**.
- `prompt_extend` default false; turning it on uses the enhanced price tier.
- `resolution` 1k/2k (default 1k). `aspect_ratio` 1:1, 2:3, 3:2, 3:4, 4:3, 7:9, 9:7, 9:16, 16:9, 21:9 (default 1:1).
- `seed` 0–2,147,483,647. No image input.

## Prompting rules
- Tight prompts only: the labeled-block and 250-word templates won't fit in 800 chars. [DOCS 09.25.26 cap]

## Cost and asks
- Priced from the live `/estimate` (the enhanced tier included when `prompt_extend` is on).

## Known failure modes
- A prompt over 800 chars is rejected. [DOCS 09.25.26]
