# HappyHorse 1.0 and 1.1 (REST)

**Settings only.** No source has HappyHorse guidance (playbook §8 gap). Use the universal video rules in the video-prompting skill. HappyHorse 1.1 is the newest and the default version. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `alibaba/happy-horse/v1.1/text-to-video`, `alibaba/happy-horse/v1.1/image-to-video`, `alibaba/happy-horse/v1.1/reference-to-video`
- `alibaba/happy-horse/text-to-video`, `alibaba/happy-horse/image-to-video`, `alibaba/happy-horse/reference-to-video` (1.0)

## Settings [DOCS 09.25.26]
- `resolution` 720p/1080p: 1.1 defaults to 1080p, 1.0 to 720p.
- `duration` 3–15 s on text-to-video, 2–15 s on image and reference (default 5). `seed` 1–2,147,483,646.
- Text-to-video: non-empty prompt; `aspect_ratio` 16:9, 9:16, 1:1, 4:3, 3:4 (default 16:9).
- Image-to-video: one first-frame `image_url`; prompt optional; no last frame.
- Reference-to-video: 1–9 `image_urls` (enforced at submit); no video references.
- No audio field. Whether it outputs audio is untested.

## Cost and asks
- All six are priced from the live `/estimate`.

## Known failure modes
- An empty text-to-video prompt, or more than 9 reference images, is rejected at submit. [DOCS 09.25.26]
