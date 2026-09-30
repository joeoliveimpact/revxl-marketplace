# Settings defaults (REST)

## Rules for every call
- **Set every setting explicitly on every call: quality and resolution first, then aspect ratio, duration and audio.** Defaults differ by model, and leaving out aspect ratio does not mean "follow the input". [DOCS 09.25.26; SINGLE-SOURCE: A9 (§5.0 #8)]
- Settings go in parameters, never in the prompt: no model name, resolution, duration, aspect ratio, fps or "4K, masterpiece" words. [AGREED, §3 #30]
- Audio is a setting, and its default differs per model (list below). Set it explicitly; turn it off when it isn't needed. [DOCS 09.25.26 (§4 #14)]
- Draft cheap (lowest resolution or tier, shortest duration), then render the hero on the confirmed direction. [AGREED, §3 #14]
- Pick the shortest duration that fits the beats. [AGREED, §3 #20]
- The price check prices an omitted field at its schema default, never the cheapest tier.
- Spending: every paid call is estimated first. A job under the silent cap (the lower of $5 and 25% of the known balance, over a rolling 24 hours) runs after the check; anything over it asks.
- `failed` and `nsfw` results are not charged; reserved credits are refunded. [DOCS 09.25.26] On a block, rephrase or remove one reference at a time; never resubmit unchanged. [AGREED, §3 #11]
- Never auto-resubmit: a retry can charge twice. [AGREED, §3 #41] A 400 can mean the concurrency limit, not a bad request. [DOCS 09.25.26]

## Prompt length caps [DOCS 09.25.26 (§4 #1)]
Z-Image 800 chars · Ideogram 2,048 · Kling 2,500 top-level + 512 per shot (Kling 3.0 Turbo t2v 3,072) · MiniMax H3 about 6,500 (only the first 7,000 are read) · Marketing Studio Image, LTX-2.5, PixVerse 5,000 · Recraft 10,000 · Qwen about 4,500 tokens (advisory).

## Audio defaults
- On by default: Seedance 2.0/2.5 `generate_audio`, Cinema Studio 4.0, Wan 3.0 / 3.0 Prime, LTX-2.5, PixVerse V6, Kling 3.0 and 2.6 `sound`. [DOCS 09.25.26]
- Off by default: Kling O3 `sound` (first-last-frame, image-reference). [DOCS 09.25.26]
- No audio field: MiniMax H3 has native audio anyway [TESTED, 2 REST samples, T11]. Hailuo, HappyHorse and Grok Video: whether they output audio is untested.
- No `sound` field: Kling 3.0 Turbo, Kling 2.5 Turbo, all Kling Omni endpoints, Kling O3 video-edit and video-reference. [DOCS 09.25.26] Kling Motion Control uses `keep_original_sound` yes/no [yes].

## Per family: what to set (schema default in brackets) [DOCS 09.25.26 unless tagged]
- **Flare / Sunburst:** `quality` [high] and `resolution` [2k] every call; draft 1k/low, final 2k/high [AGREED, §3 #22; SINGLE-SOURCE: untested transfer from GPT Image 2 (§5.3)]. `aspect_ratio` always (auto = square). 2.0 Alpha: `quality` low/medium/high only.
- **Soul V2 / Cinema / Soul:** `resolution` 720p/1080p [720p], `aspect_ratio` [1:1; Soul 4:3], `batch_size` 1 or 4 [1], `seed`.
- **Recraft V4.1:** resolution is fixed per endpoint (1k standard/utility, 2k pro); set `aspect_ratio` [1:1] and `output_format` [jpg].
- **Ideogram 4.0:** `aspect_ratio` always [1:1, even with an input image]; `rendering_speed` [DEFAULT].
- **Qwen Image 3:** `resolution` [1k]; `prompt_extend` + `enable_thinking` [both on; set both false to use your prompt as written].
- **Grok Image 2.0:** `quality` low/medium [medium], `resolution` [1k], `aspect_ratio` [auto].
- **Z-Image Turbo:** `resolution` [1k], `aspect_ratio` [1:1], `prompt_extend` [off].
- **Seedance 2.5:** `resolution` [720p] (480p preview, then the hero [SINGLE-SOURCE: C17, A8]), `duration` [5], `generate_audio` [true], `aspect_ratio` on t2v/ref2v [16:9].
- **Seedance 2.0:** `resolution` 480p–4k [720p], `duration` 4–15 [5], `generate_audio` [true].
- **Kling 3.0:** tier: validate on std, finish on pro or 4k [SINGLE-SOURCE: B3, C3]; `sound` [on], `duration` [5], `aspect_ratio` on t2v [16:9], `cfg_scale` [0.5]. Turbo: `resolution` [720p].
- **Kling O3 / Omni:** `mode` [pro on most; std on O3 image-reference], `sound` on O3 [off], `duration`.
- **Kling 2.6 / 2.5 Turbo:** `duration` 5/10 [5]; 2.6 `sound` [on].
- **Cinema Studio 4.0:** `resolution` [720p], `duration` [5], `generate_audio` [true]; omit enums you want it to choose.
- **Wan 3.0 / Prime:** `resolution` [1080p], `generate_audio` [true], `aspect_ratio` [adaptive], `enable_thinking` [false]. Wan 2.6/2.7: `resolution` [720p], `prompt_extend` [false].
- **MiniMax H3:** resolution fixed "2K"; `duration` 5–15 [5]; `aspect_ratio` [auto].
- **LTX-2.5:** `resolution` [720p], `fps` [25], `duration` 6/8/10 [6], `generate_audio` [true].
- **PixVerse V6:** `resolution` [720p], `duration` [5], `generate_audio` [true].
- **Hailuo 2.3:** fixed 768P; `duration` 6/10 [6]; `prompt_optimizer` [on].
- **HappyHorse:** `resolution` [1.1: 1080p; 1.0: 720p], `duration` [5].
- **Grok Video 1.5:** `resolution` [480p; references allow 480p/720p only], `duration` [5].
- **Genjutsu:** `resolution` 480p/720p [720p].
