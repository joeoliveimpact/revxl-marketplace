# MiniMax H3 (REST)

Fixed-2K video with native audio and long structured prompts. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `minimax/h3/text-to-video`
- `minimax/h3/image-to-video`
- `minimax/h3/reference-to-video`

## Settings [DOCS 09.25.26]
- `resolution` fixed to "2K" (case-sensitive). `duration` 5–15 s (default 5).
- Prompt: non-blank; **only the first 7,000 chars are read**, so cap prompts at about 6,500.
- `aspect_ratio` auto, adaptive, 21:9, 16:9, 4:3, 1:1, 3:4, 9:16 (default auto). Text-only auto/adaptive resolves to 16:9; image-to-video follows the input frame even when an aspect is sent.
- Image-to-video: `image_url` (first frame) plus optional `end_image_url`. No last-frame-only mode.
- Reference-to-video: up to 9 images, 3 videos, 3 audio; audio needs an image or video reference; video and audio each fit a 15 s budget.
- `aigc_watermark` default false. No audio flag: native audio is on by default. [TESTED, 2 REST samples, T11]

## Prompting rules
- Official T2VA fields `integrated_multimodal_description` / `overall_soundscape` / `non_diegetic_music` pass through. [SINGLE-SOURCE: REST, 1 sample, T11] Whether the audio follows `overall_soundscape` is still unchecked.
- Shot cues: `[Shot N] At 00:03.500, the camera cuts to…`. Speaker IDs `(S1)`; dialogue `<d>[English] Exact words.</d>`. [SINGLE-SOURCE: B9]
- Treat visible typography as a whitelist: quote the allowed text and forbid all other readable text. [SINGLE-SOURCE: B9]
- Cut only when a shot adds a new subject, space, state, viewpoint or time; otherwise use a camera move. [SINGLE-SOURCE: B9]
- Performance transfer: the reference video supplies "performance, not identity". [SINGLE-SOURCE: B9]
- B9's official examples are 7,487 and 12,461 chars; trim them before use. [SINGLE-SOURCE: B9]

## Cost and asks
- Text-to-video and image-to-video are priced from the live `/estimate`.
- `minimax/h3/reference-to-video` **always asks** (reference cost unknown).

## Known failure modes
- Text past 7,000 chars is silently ignored. [DOCS 09.25.26]
- Lowercase "2k" doesn't match the case-sensitive "2K"; audio-only references are rejected. [DOCS 09.25.26]
