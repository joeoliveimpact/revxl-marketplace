# Kling O3 and Kling Omni (REST)

Frame bridges, image references, video references and video edits on Kling. Not the Google "Gemini Omni" (that one is app only, see `gemini-omni.md`). Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `kling-video/o3/first-last-frame`, `kling-video/o3/image-reference`, `kling-video/o3/video-reference`, `kling-video/o3/video-edit`
- `kling-video/omni/first-last-frame`, `kling-video/omni/image-reference`, `kling-video/omni/video-reference`, `kling-video/omni/video-edit`

## Settings [DOCS 09.25.26]
- Frames use `first_frame_url` / `last_frame_url` (not Kling 3.0's `image_url` / `last_image_url`).
- `mode`: O3 std/pro/4k (video-reference std/pro); Omni std/pro. Default pro, except O3 image-reference (std).
- `sound` on/off, default **off**: O3 first-last-frame and image-reference only. The other six have no `sound` field.
- `aspect_ratio` 16:9/9:16/1:1. Top-level prompt ≤2,500 chars (longer is truncated).
- Duration: O3 first-last-frame and image-reference 3–15 s; Omni first-last-frame 5 or 10; Omni image-reference and both video-reference endpoints 3–10.
- Multi-shot (O3 first-last-frame, image-reference): `multi_shots: true` plus 1–6 `multi_prompt` `{prompt ≤512 chars, duration ≥1 s}` and a non-empty top-level prompt; shot durations add up and set the bill. Image-reference has `shot_type` customize/intelligent (default customize); `multi_prompt` is required even with intelligent.
- `image_urls` for references; video-reference and video-edit take up to 4 `image_urls` and 4 `elements` (account-owned IDs).
- Video-edit: exactly one source in `video_urls` (O3 3–15.5 s, Omni 3–10 s, ≤200 MB); no `duration` (it follows the source). Video-reference: exactly one video.

## Prompting rules
- Generation (frames, image or video reference): write prompts as for Kling 3.0 (`kling-3.md`). [SINGLE-SOURCE: playbook §5.26, reasoning only]
- References: no token syntax is documented for O3/Omni. With 2 or more images, open with a manifest (`IMAGE REFERENCES: image 1 = …; image 2 = …`) and name each by number plus a noun every time. Plain "image 1 / image 2" with no manifest fused two images into one object. [SINGLE-SOURCE: 1 client sample, video-edit 4k, 10.01.26]
- Video-edit is untested for restyles: restyling a motion sketch with 2 image references froze the sketch's motion completely (1 sample, 10.01.26). Describe appearance only; don't re-script motion the source video already carries; no negatives; validate on std or pro before 4k. See `references/video-edit-recipes.md`.
- Edits: describe only the change; on later rounds add "keep everything else exactly the same". [SINGLE-SOURCE: A17, A14]
- Edit chains lose quality: at about round 4, regenerate fresh from a description of the current version. [SINGLE-SOURCE: A17]
- No source covers O3/Omni video-reference or video-edit specifically (playbook §8 gap).

## Cost and asks
- `kling-video/o3/video-edit` and `kling-video/omni/video-edit` **always ask**: `/estimate` fails for them, so the price is unknown.
- The other six are priced from the live `/estimate`; with multi-shot, shot durations set the bill.

## Known failure modes
- Last-frame-only "cover reveal" doesn't work: `first_frame_url` is required. [DOCS 09.25.26; T8 `/estimate` rejection, 1 sample]
- `sound` defaults to off on O3; set it on if you want audio. [DOCS 09.25.26]
- Zero-second shots are rejected. [DOCS 09.25.26]
