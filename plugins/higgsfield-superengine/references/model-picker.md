# Model picker (REST only)

Pick by what the client wants, then load `references/models/<file>.md` for that model's settings and rules, and `references/settings-defaults.md` for what to set on every call. Every pick here is reachable on the Higgsfield REST API with the client's own key. App-only models (Nano Banana, Gemini Omni, Veo, GPT Image 2) are never picked; their files exist for reference only.

**Tag legend** (used in every reference file):
- **DOCS 09.25.26**: a setting fact from the Higgsfield REST docs snapshot of that date.
- **TESTED**: at least 2 REST samples with a verdict.
- **AGREED**: 3 or more independent authors state it, and the playbook keeps it (the `§3 #n` row is the evidence).
- **SINGLE-SOURCE**: one REST sample (written "REST, 1 sample"), or fewer than 3 independent authors (the source IDs follow).
- These four are the only tags. The playbook's own RESOLVED (a §4 ruling) and LIKELY labels become **AGREED** only when the §3 row that points to that ruling shows 3 or more independent authors and the ruling keeps that row's practice (the row is cited); otherwise they become **SINGLE-SOURCE** with the ruling's source IDs ("reasoning" when it names none). Never upgrade: a part of a line that goes beyond the row stays SINGLE-SOURCE.
- App-route results are reference only, never TESTED.

## Defaults
- **Lean popular:** Flare (GPT Image 2.5, what clients call ChatGPT images) for images, Soul for faces and consistent characters, Seedance 2.5 or Kling 3.0 for video. Use another model only for a specialty need: the client explicitly asks for the cheapest option or quick rough drafts, the client names it, motion transfer, 1080p/4k, logo/vector, a negative prompt, pixel-exact edits, or a feature only that model has. [Joe 09.29.26]
- **Image default: Flare** (`marketing-studio/image/flare`, GPT Image 2.5 per the app catalog). Sunburst is the alternative, but it asks before every run until one real Sunburst charge is measured.
- **Video default: Seedance 2.5** (up to 1080p on REST). [SINGLE-SOURCE: A1, A13 (§4 #11)]
- **Newest version first:** Kling 3.0 (not O3), Wan 3.0 (not Prime), HappyHorse 1.1. Older versions are fallbacks for a failed job or a parameter only the older one has.

## Image intents
- Text-heavy graphic, thumbnail, poster, slide, carousel → Flare (`marketing-studio-image.md`); alternatives Ideogram 4.0 (`ideogram.md`), Recraft (`recraft.md`).
- Product packshot with a legible label → Flare, product image first (`preset_id` + `enhance_prompt` path asks first).
- Photoreal person from a photo → Soul V2 with a trained `custom_reference_id` (`soul.md`), or Flare with the person as the 2nd image.
- Same character across many images → Soul V2 + Soul ID (`soul.md`).
- Cinematic still, concept art → Soul Cinema (`soul.md`).
- Reference-faithful edit, no text (swap background, keep pixels) → Qwen Image 3 edit (`qwen-image.md`), Grok Image 2.0 (`grok-image.md`).
- Branded mockup → Flare (`marketing-studio-image.md`).
- Logo, icon, vector-style art → Recraft V4.1 (`recraft.md`). REST output is raster only, and Recraft REST takes no reference image; trace to vector afterwards.
- Fast, cheap image iteration → Z-Image Turbo (`z-image.md`, 800-char prompts).
- Transparent asset → any model on a solid key color, then remove it (no REST model outputs transparency).

## Video intents
- Default video, animate an image → Seedance 2.5 (`seedance-2-5.md`).
- Text-to-video with native audio, up to 30 s → Seedance 2.5; Wan 3.0 (`wan.md`); Cinema Studio 4.0 (`cinema-studio-4.md`).
- 1080p → Seedance 2.5 (`seedance-2-5.md`). 4k → Seedance 2.0 (`seedance-2-0.md`, up to 4k); Kling 3.0 4K (`kling-3.md`); LTX-2.5 Fast (`ltx.md`, up to 4k).
- Directed multi-shot (UGC cuts, dialogue scenes) → Kling 3.0 or O3 with `multi_prompt` (`kling-3.md`, `kling-o3-omni.md`).
- Identity from references in video → Seedance 2.5 reference-to-video (30 image refs); Seedance 2.0 ref2v; Kling O3 image-reference; Wan 3.0 ref2v.
- Genre-directed cinematic film → Cinema Studio 4.0 (enums for genre, lens, movement, palette).
- Product reveal ad → Seedance 2.5 with `Stage 1/2/3` labels, never timecodes; or Seedance 2.0.
- Ad video with avatars, hooks and presets → build it on Seedance 2.5 or Kling 3.0 (Marketing Studio video is app only).
- Animate a still, silent, cheap → Kling 3.0 Turbo (`kling-3.md`).
- Start-to-end-frame bridge or loop → Seedance 2.0/2.5 `end_image_url`; Kling 3.0 `last_image_url`; Wan 2.7/3.0 `end_image_url`.
- Edit an existing clip → Seedance 2.5 video-edit; Kling O3/Omni video-edit (always asks first).
- Extend a clip → Seedance 2.5 video-extend.
- Motion transfer, object swap → Kling Motion Control 2.6/3.0 (`kling-2-and-motion-control.md`, always asks first); Genjutsu (`genjutsu.md`).
- Talking head, lip-sync → Seedance or Kling native dialogue, lines of 6–7 s or less; mix real voice-over in post.
- Stylized explainer (non-photoreal) → Seedance 2.5 reference-to-video with the style-donor prefix.
- Cheap preview before a hero render → Seedance 2.5 at 480p, Kling 3.0 std, LTX-2.5 Fast.
- Cheap with strong physics → Hailuo 2.3 (`hailuo.md`).
- Narration or voice only → none on REST.

## Other REST families
MiniMax H3 (`minimax-h3.md`, fixed 2K, native audio, long structured prompts), PixVerse V6 (`pixverse.md`), HappyHorse 1.0/1.1 (`happyhorse.md`), Grok Imagine Video 1.5 (`grok-video.md`), Kling 2.6 / 2.5 Turbo (`kling-2-and-motion-control.md`).
