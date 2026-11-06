# Grade live test: pass rule (S13.2, written before the run)

This file is committed before the live run so the bar cannot move after the results are seen (PB-19, PB-31).

The run uses a real portrait talking-head recording (a scratch copy; the original is never touched), the real board server, and the Grade Board opened from the hub's Grade tab. It passes only when every line below holds.

1. **Loads.** The Grade Board opens on the recording's face frames from the hub tab, at identity (white 1.000, correction equal to the grade maths defaults), with the looks rail showing None and the five looks.
2. **Bakes.** Picking a look and a strength, then Send, writes `grade-selection.json` in the reel folder; `grade_from_selection.py` turns it into a `.cube` and a `grade.json` whose `cube_sha` is the sha256 of that cube.
3. **Applies.** The cube applies in the editor's ffmpeg two ways, both from the raw: `apply_grade.py` (one extra generation, recorded) and `render.py --grade` (no extra generation). Both outputs play.
4. **Known colour.** A known-colour test frame (lavfi colour patches) through the same cube matches the board's own maths within 3/255 per channel (8-bit), and the identity look stays within 2/255.
5. **Skin.** The skin guard passes for the chosen look on the recording's face (hue shift within its limit; Mono checks luminance only).
6. **The reviewer's eye OK.** The reviewer looks at the five looks on the face frame and the graded result (before/after frames) and says it is OK. A "no" is a fail: fix and retest, parked after three rounds; the release waits.

Evidence kept outside the repo: screenshots, the Send file, the cube, before/after frames, the logs and exit codes.
