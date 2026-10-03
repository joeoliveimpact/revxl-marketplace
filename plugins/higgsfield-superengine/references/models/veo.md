# Veo 3 / 3.1 / 3.1 Lite: not available through this plugin (app only)

**Not available through this plugin (app only).** Veo has no Higgsfield REST endpoint, so this plugin can never call it and the model picker never suggests it. This file is prompting reference only. Tags: see the legend in `references/model-picker.md`.

## REST alternative
- Text-to-video with native audio → Seedance 2.5 (`seedance-2-5.md`) or Wan 3.0 (`wan.md`).
- Cheap preview → Seedance 2.5 at 480p, Kling 3.0 std (`kling-3.md`), LTX-2.5 Fast (`ltx.md`).
- Talking head → Seedance or Kling native dialogue, lines of 6–7 s or less.

## App IDs (app catalog 09.24.26, reference only)
- `veo3_1`: 4/6/8 s; `quality` basic/high/ultra; `variant` veo-3-1-preview / veo-3-1-fast; start image only; 16:9/9:16.
- `veo3_1_lite`: 4/6/8 s; start + end image; `generate_audio` default false. `veo3`: variant.

## Prompting guidance (app route) [SINGLE-SOURCE: B10, C4, every rule here]
- Anatomy: subject · action · scene · camera · lighting/mood · style · audio · timing; one clear motion per clip.
- Audio cues noticeably improve native audio: dialogue in quotes plus who and tone, `SFX:`, ambient, music mood. Short lines for lip-sync.
- Exclude things by describing the scene: "a desolate landscape with no buildings".
- Prompts up to about 1,024 tokens are fine (Veo only).
- 8 s max per clip. Route pure talking-head explainers to an avatar or lip-sync tool rather than forcing Veo.
