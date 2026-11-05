# Grade details: what the page shows, what the bake writes, and the ffmpeg pass

Background for reel-grade. SKILL.md has the steps; this file explains the three places a grade can go wrong
between the Grade Board and the graded video.

## One set of numbers

Every constant and slider range lives in `boards/grade-board/grade_math.json`. `scripts/grade_math.py` (the bake)
and `boards/grade-board/grade_math.js` (the page) both read it, and the page's shader code is generated from the
same file. `scripts/selftest_math.py` pushes 200 random colours through both and fails above 1e-5. Run it after
any change to a `grade_math.*` file; when it fails, fix the maths, never the threshold.

A look is a short stack of tune numbers in `looks/looks.json` (temp, tint, con, sat, mat), not a LUT file.
Strength 0 to 1 scales those numbers linearly. `make_grade.py` copies each look's numbers into
`grade/grade-config.json`, so the board runs exactly the numbers the bake runs.

Order, on the page and in the bake: correction (exposure, black, white, skin rotation), then the fine tune when it
moves anything, then the look's slots. Each step clamps to 0..1.

## The page is 8-bit, the bake is float

The board draws in 8 bits per channel, and ffmpeg writes 8 bits too. The bake samples the grade on a 33x33x33
lattice and ffmpeg's `lut3d` interpolates between lattice points. Where the page clips a colour exactly (a
highlight pushed past white), the lattice rounds the corner, so a clipped colour can land up to about 3/255 away
from the page. That is invisible on screen. It is why the page is where the client judges and ffmpeg is what
writes the pixels: never ship a browser screenshot or canvas readback as the grade, because the browser's colour
management can shift what a readback contains. If a deep grade shows banding, bake at `--size 65`.

## Half a texel

A 3D LUT's 0..1 range maps to the centres of its texels, so a GPU that samples a LUT texture has to read at
`(c * (n - 1) + 0.5) / n`, not at `c`. Sampling at `c` sits half a texel off the lattice the bake wrote, and the
page and the bake then disagree in a way that looks like a maths bug and isn't one. The Grade Board has no LUT
texture (looks are tune numbers, computed straight in the shader), so this only matters if a LUT texture ever
comes back to the page.

## ffmpeg's lut3d path on Windows

A cube path inside an ffmpeg filter needs all three of these, or the filter fails to parse:

- forward slashes,
- the drive colon escaped (`C\:`),
- the whole path in single quotes: `lut3d=file='C\:/work/videos/<reel>/grade/<cube file>'`.

Escaping the colon without the quotes is not enough: ffmpeg has already split the option on the colon.
`apply_grade.py` builds this form (`filter_arg`), and refuses a path that has an apostrophe in it, which no quoting
can carry. Use `apply_grade.py`'s form anywhere else a cube goes into a filter.

## The sha check and the extra generation

`grade.json` names the cube for the cut and its sha256 (`cube`, `cube_sha`), plus one cube per take. Anything
that burns the grade in checks the sha first, so it applies exactly the cube that was approved.

Burning the grade into a finished video with `grade_from_selection.py --apply ... --yes` is one more encode on top
of the cut's own, so `grade.json` records `"extra_generations": 1`. A graded still is only a preview and records
nothing. Grading inside the cut's own render avoids the extra generation.
