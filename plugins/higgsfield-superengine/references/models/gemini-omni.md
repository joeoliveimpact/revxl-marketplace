# Gemini Omni / Omni Flash 1.1: not available through this plugin (app only)

**Not available through this plugin (app only).** Google's Gemini Omni video model has no Higgsfield REST endpoint, so this plugin can never call it and the model picker never suggests it. Not to be confused with Kling Omni, which is REST (`kling-o3-omni.md`). This file is prompting reference only. Tags: see the legend in `references/model-picker.md`.

## REST alternative
- General video, or identity from references → Seedance 2.5 (`seedance-2-5.md`), reference-to-video for references.
- Stylized explainer (non-photoreal) → Seedance 2.5 reference-to-video with the style-donor prefix.

## App IDs (app catalog 09.24.26, reference only)
- `gemini_omni`: reference-driven, native audio.
- `gemini_omni_flash_1_1`: `mode` required (text-to-video / image-to-video / reference-to-video / edit); 3–10 s (edit uses the source, capped at 30 s); 360p–4k; 16:9/9:16.

## Prompting guidance (app route)
- No negative prompts and no `Avoid:` blocks; phrase everything positively. [SINGLE-SOURCE: A17]
- Edits: describe only the change; add "keep everything else exactly the same" on later rounds; regenerate fresh at about round 4. [SINGLE-SOURCE: A17]
- Track 3 subjects or fewer; write prompts in English. [SINGLE-SOURCE: A17]
- Stylized explainer: `STYLE REFERENCE: Match the attached reference image EXACTLY… / SCENE / MOTION / AUDIO: ambient SFX or music only—NO voice`, one action per block; end the style descriptor with "non-photorealistic, illustrated, not a photo"; mascots greet "by gesture with mouth closed"; drop the NEGATIVE block. [SINGLE-SOURCE: A6]
- Veo's audio-line and 8 s rules apply to Omni only after testing.
- On the app route a submit can return a `preset_recommendation` notice instead of a job; ask the user or decline it. (Omni run, app route only: reference, not TESTED)
