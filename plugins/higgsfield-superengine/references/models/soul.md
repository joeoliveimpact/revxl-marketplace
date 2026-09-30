# Soul V2, Soul Cinema, Soul (REST)

Consistent characters from a trained Soul ID, and fixed-style cinematic stills. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `higgsfield-ai/soul/v2/standard`: Soul V2.
- `higgsfield-ai/soul/cinema`: Soul Cinema (fixed style; may be missing from model discovery, call it by ID).
- `higgsfield-ai/soul/standard`: Soul.

## Settings [DOCS 09.25.26]
- `resolution` 720p/1080p (default 720p); `batch_size` 1 or 4; `aspect_ratio` 9:16, 16:9, 4:3, 3:4, 1:1, 2:3, 3:2 (default 1:1; Soul 4:3).
- `seed` 1–1,000,000; on V2 and Cinema an explicit null is invalid.
- Identity: `custom_reference_id` (a completed character owned by the calling account) plus `custom_reference_strength` above 0 and at most 1. On V2, 0 fails; on Soul, 0 means the style's default strength.
- `style_id` on V2 and Soul; `style_strength` is accepted but does nothing. Cinema ignores `style_id`, and a `custom_reference_id` turns on its prompt enhancement.
- `enhance_prompt` default false, but short prompts in the general style are enhanced anyway.
- Soul only: `image_reference_url` guides enhancement; it is not a trained identity. V2 and Cinema take no image input.
- Training (not a generation endpoint): `POST /v1/custom-references` with 1–100 images and `model_version` v1/v2/cinema (default v1; match the family you'll generate with). Poll `GET /v1/custom-references/{id}` until `completed`.

## Prompting rules
- Use a longer prompt plus a 2–5 word face anchor phrase: it came closest to the reference; the short prompt drifted. [SINGLE-SOURCE: REST, 1 sample, T12]
- Don't put the Soul ID or a name in the prompt text. [SINGLE-SOURCE: D8, A1]
- Lens terms are optional; "+85mm" made no visible difference. [SINGLE-SOURCE: REST, 1 sample, T12]
- Say what the character is doing. Keep backgrounds simple (complex ones speed up drift); studio scenes are the most stable reset; lighting consistency matters more than clothing. [SINGLE-SOURCE: D8]
- Once a result matches, lock `seed`, `style_id` and reference strength and change only the scene; test one image per scene type before scaling. [SINGLE-SOURCE: D8]
- Training photos: varied angles, light and expressions, at least 1024 px, one person, no filters. [AGREED, §3 #45]
- Aim for 8–15 photos (the service accepts 1–100): front, 3/4 left and right, slight up/down; neutral, smile, serious; three lighting types; face at least 40% of the frame; no sunglasses, hats, group shots or costumes. [SINGLE-SOURCE: A2, D8, D18 (§4 #21)]

## Cost and asks
- All three are priced from the live `/estimate`. Training is a separate paid job, priced from its own `/estimate`.

## Known failure modes
- `custom_reference_strength: 0` on V2 fails for a character reference. [DOCS 09.25.26]
- Identity was only moderate when trained on low-res frames; follow the photo guide. [SINGLE-SOURCE: REST, 1 sample, T12]
