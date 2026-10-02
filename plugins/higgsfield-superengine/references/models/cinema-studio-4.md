# Cinema Studio 4.0 (REST)

**Settings only.** No source writes prompts for Cinema Studio 4.0's enum system (playbook §8, high-priority gap). Use the universal video rules in the video-prompting skill. Tags: see the legend in `references/model-picker.md`.

## Endpoints
- `higgsfield/cinema-studio/4.0`: text-to-video with no media; reference-to-video when any media array is non-empty. It makes new videos only; edits and extensions use the Seedance 2.5 endpoints.

## Settings [DOCS 09.25.26]
- `duration` 4–30 s (default 5); `resolution` 480p/720p (default 720p); `aspect_ratio` 16:9, 4:3, 1:1, 3:4, 9:16, 21:9 (default 16:9); `generate_audio` default true.
- References: up to 30 `image_urls`, 10 `video_urls`, 10 `audio_urls`, 50 total; video and audio each normalized to 30 s total.
- Prompt tokens `<<<image_1>>>`, `<<<video_1>>>`, `<<<audio_1>>>` (one-based); each must point at an attached item of the same type.
- **Omit a creative field to let the director choose; the literal "auto" is rejected.**
- `genre`: epic, drama, noir, comedy, horror, action. `era`: 1960s, 1980s, 1990s, 2000s, 2020s. `light`: silhouette, practicals, window, overhead-fall, contre-jour, soft-cross. `pacing`: chaotic, dynamic, calm, single-shot.
- `camera_model`: modern, 35mm-film, 8mm-film, dv-camcorder. `camera_lens`: clean-sharp, anamorphic, vintage-anamorphic, warm-vintage, halation-vintage. `camera_aperture`: f14-wide-open, f4-moderate, f11-deep-focus.
- `camera_movement` (33): snorricam, robot-arm, tilt-up, rack-focus, tilt-down, pov, pan-left, crane-up, pan-right, crane-down, side-tracking, pedestal-up, pedestal-down, handheld, tracking, drone-orbit, dolly-zoom, aerial-pullback, static-shot, bullet-time, whip-pan, slow-zoom-in, arc-left, slow-zoom-out, arc-right, truck-right, dolly-in, truck-left, dolly-out, slider-right, crush-zoom, slider-left, helicopter-shot.
- `color_palette` (50): static-noon, twilight-fable, back-row-kissing-seats, on-the-other-side-of-the-porthole, the-emerald-ambush, highway-standoff, the-faded-fresco, oil-ochre, the-mountain-convent, ghost-in-the-code, pink-velvet, two-days-to-the-horizon, industrial-fog, stairs-go-up, field-post, home-is-the-next-gas-station, glossy-flesh, the-crimson-ballet, neon-rain-at-midnight, the-morning-after-rain, the-iron-borough, the-ground, the-investigation, turquoise-mirage, a-dream-in-color, breakfast-on-schedule, favela-gold, a-hotel-for-one, after-dark, crimson-vigi, the-neighbors-saw-everything, the-grey-channel, mirage-at-noon, bubblegum-boulevard, yellow-room, the-earth-keeps-things-reluctantly, tropic-fever-dream, bioluminescent-night, dont-turn-it-off-im-watching, the-silk-curtain-falls, the-butterfly, playtime, wallpaper-romance, overtime, the-way-home-is-longer, everyone-speaks-in-whispers, runaway-summer, amber-wasteland, the-circus, gasoline-sunset.

## Cost and asks
- Priced by the Seedance token formula. `generate_audio` true (the default) asks until the audio cost is measured; set it `false` to be priced silently.
- Video references are priced on their real length when the plugin uploaded them (`hf_rest.py upload` records it); otherwise as 30 s of input, so those jobs often go over the silent cap and ask.

## Known failure modes
- Sending "auto" for any enum is rejected; leave the field out instead. [DOCS 09.25.26]
- A token like `<<<image_2>>>` with only one image attached breaks the one-to-one rule. [DOCS 09.25.26]
