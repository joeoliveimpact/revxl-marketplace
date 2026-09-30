# Wan 2.6, 2.7, 3.0, 3.0 Prime (REST)

Wan 3.0 is the newest (the default Wan); Prime and 2.6/2.7 are alternatives. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `alibaba/wan-3.0/text-to-video`, `alibaba/wan-3.0/image-to-video`, `alibaba/wan-3.0/reference-to-video`
- `alibaba/wan-3.0-prime/text-to-video`, `alibaba/wan-3.0-prime/image-to-video`, `alibaba/wan-3.0-prime/reference-to-video`
- `wan/v2.7/text-to-video`, `wan/v2.7/image-to-video`, `wan/v2.7/reference-to-video`
- `wan/v2.6/text-to-video`, `wan/v2.6/image-to-video`, `wan/v2.6/reference-to-video`

## Settings [DOCS 09.25.26]
- Wan 3.0 and Prime: `duration` 2–30 s (default 5; no "-1 = model picks" on REST); `resolution` 480p/720p/1080p (default 1080p); `aspect_ratio` 16:9, 4:3, 1:1, 3:4, 9:16, adaptive (default adaptive); `generate_audio` default true; `enable_thinking` default false; `seed` is forwarded only when nonzero.
- Wan 3.0 / Prime image-to-video: `image_url` plus optional `end_image_url`. Reference-to-video: optional `image_urls` (≤10), `video_urls` (≤5; clips 1–30 s, 30 s total), `audio_urls` (≤5; WAV/MP3, 30 s total), and `file_url` or `link_url` (a document or web page; it turns thinking on; `file_url` wins if both).
- Wan 2.7: `duration` 2–15 (reference 2–10); `resolution` 720p/1080p (default 720p); `negative_prompt` on all 3; `prompt_extend` default false; `audio_url` driving audio (text, image); image-to-video has `end_image_url`; reference-to-video takes ≤5 images and videos combined, 16:9 or 9:16 only.
- Wan 2.6: `duration` 5/10/15 (reference 5/10); image-to-video 480p–1080p, others 720p/1080p (default 720p); `negative_prompt` on image-to-video only; `audio_url` (text, image); `multi_shots` (it also turns `prompt_extend` on); image-to-video has no last frame; reference-to-video needs 1–3 `video_urls`. Images are resized to at most 1,440 px.

## Prompting rules
- No Wan 3.0-specific source exists; these are an untested transfer from B9's Wan 2.2 guide. [SINGLE-SOURCE: B9 (§5.32)]
- Image-to-video = motion plus camera, ordered opening → camera motion → payoff. [SINGLE-SOURCE: B9]
- Keep 2–6 anchors consistent across retries. [SINGLE-SOURCE: B9]
- Negatives (2.6/2.7 only): just the failures you've actually seen. [SINGLE-SOURCE: B9]
- C1's six-block video craft transfers unchanged. [SINGLE-SOURCE: C1]

## Cost and asks
- Wan 3.0: priced per second by resolution. It asks when `generate_audio` is true (the default) or `enable_thinking` is set. `alibaba/wan-3.0/reference-to-video` **always asks** (reference cost unknown).
- Wan 3.0 Prime: priced from the live `/estimate`; asks when `generate_audio` is true (the default).
- Wan 2.6 and 2.7: priced from the live `/estimate`.
- Set `generate_audio: false` for silent pricing on Wan 3.0 / Prime.

## Known failure modes
- `seed: 0` is silently dropped (not forwarded). [DOCS 09.25.26]
- Wan 2.6 `multi_shots: true` silently turns on `prompt_extend`. [DOCS 09.25.26]
- Wan 2.7 reference-to-video with more than 5 references is rejected at submit. [DOCS 09.25.26]
