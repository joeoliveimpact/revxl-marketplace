# Reel motion render fixtures

These are original text-only scenes, with no artwork or external assets.

- `reel-good-world`: slot and UI text clear every rest-point check; the camera pans text through both
  frame edges between rest points. Expected: all checks pass (exit 0).
- `reel-band-world`: the same scene with a non-slot UI row inside the caption band `[1320,1470)`.
  Expected: caption-band checks fail (exit 1); this is an intentional negative fixture.
- `reel-seek-world`: a deterministic three-second drift to `x: -90`. Expected: all checks pass (exit 0).
  `tests/editor/reel_seek_test.py` injects the accumulating/jump-dependent and random variants into
  temporary copies; its tests pass when those variants fail the seek comparison.

Duration is 3 seconds at 30 fps. Text is checked at frame 8 (0 + 0.25 s), frame 52
(`t1=1.5` + 0.25 s), and frame 89 (last frame). Frame indices round to the nearest integer using
Python's `round`, then clamp to the last frame.

`preview.png` files are transparent 270x480 **test placeholders**, not rendered thumbnails.
Adding `--write-previews` to a render command overwrites those tracked placeholders with real previews;
use it only when deliberately refreshing fixture thumbnails.

Run from this checkout with the editor Python and `EDITOR_SE_HOME` pointing to an installed state folder
containing node, chrome, ffmpeg and hyperframes. These are heavy jobs: run one at a time; the standalone
render runner does not acquire `plugins/editor-superengine/skills/_shared/heavy_job.py`'s lock itself.

```bash
<editor python> -X utf8 -I tests/editor/scene_render_test.py --scenes-dir tests/editor/fixtures/reel-motion/motion --scene reel-good-world
<editor python> -X utf8 -I tests/editor/scene_render_test.py --scenes-dir tests/editor/fixtures/reel-motion/motion --scene reel-band-world
<editor python> -X utf8 -I tests/editor/scene_render_test.py --scenes-dir tests/editor/fixtures/reel-motion/motion --scene reel-seek-world
<editor python> -X utf8 -I tests/editor/scene_render_test.py --scene callout
```

The last command checks the plugin's shipped `callout` scene rather than a reel fixture; it should exit 0.
The band fixture above is the only listed command expected to exit 1.
