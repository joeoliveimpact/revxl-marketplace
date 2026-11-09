# styleframes contract — style-decoder measurement passes

> Companion to `scripts/styleframes.py`. Passes over `sources/<src-id>/source.mp4`,
> which `stylespec.py add-source` puts there. `--pass all` = base + cuts + bursts +
> captions. The measure pass only ever runs explicitly, against a request file the
> decode phase writes. ffmpeg comes from the editor's own setup.

## Passes

| Pass | Output | What it's for |
|---|---|---|
| `base` | `frames/base_NNNN_t<ms>.jpg` (512px, ≤2fps, ≤100 frames, budget by duration) | The frames Claude reads fully in the decode phase. Filenames carry ms timestamps, so they order without ffprobe. Held-out frames come from here. |
| `cuts` | `cuts.json` + `pacing.json` | Scene-detect (`select='gt(scene,<style.scene_threshold>)'`, default 0.30) + shot stats: median/mean shot, cuts/10s, histogram, longest hold, hook-window cut count. |
| `bursts` | `frames/hook_t<ms>.jpg` (0–3 s @ 0.25 s) + `frames/cut_NN_t<ms>.jpg` (±0.5 s @ 0.25 s around each candidate cut) | Hook analysis + in/out states around cuts. |
| `captions` | `captions/cap_NNN.jpg` (thin band, 420px wide, ~2 strips/s) + `captions/timebase.json` | Recovering the **caption grouping rule**. The band is `--band-top`..`--band-bottom` % of frame height (defaults 33 and 72); move it when the captions sit elsewhere. `timebase.json` records the band. |
| `measure` | `frames/kf_*.png` (full-res) · `frames/crop_*.png` · `frames/mb_<label>_NN.png` (micro-bursts, 720px) | Precision layer: fonts/stroke/shadow/radii off full-res; animation duration + overshoot off micro-bursts. |

Groups turn over about every 0.5 s, so a ~1fps base pass samples slower than the
thing it measures: the grouping algorithm is unrecoverable without the captions
pass. **Timebase: strip NNN IS source frame `(NNN-1)*step`, `step =
round(source_fps/2)`, so `t = (NNN-1)*step/source_fps`.** Always read
`timebase.json` rather than assuming.

## Never assume an extractor's timebase — measure it

`fps=N` does **not** sample at `k/N` seconds. It emits the input frame nearest each
output slot's **midpoint**, so strips land about half a slot late (+0.233 s for
`fps=2` on 30fps source). That silently mis-attributes captions across any layout
swap inside the window. Measured against a frame-exact single-decode reference:

| filter | lands on |
|---|---|
| `fps=2` | `(N-1)*0.5 + 0.2333s` |
| `fps=2:round=down` | neither timebase, and **drops a strip** |
| `fps=2:start_time=0` | identical to plain `fps=2` |
| `select='not(mod(n,step))'` + `-vsync 0` | **exactly `(N-1)*step/fps`** |

1. **Select by frame index when the timestamp matters.** A true formula beats a
   formula plus a correction constant, and the constant scales with source fps.
2. **Ship the timebase as data.** Strips from different code versions look the
   same; only the sidecar tells them apart.
3. **Verify empirically, don't trust the flag.** Two plausible one-flag fixes
   failed, and one lost data.

## cuts.json is a CANDIDATE list

Scene-detect measures global frame change. On panel-style reels it **misses** panel
swaps over a static background and **false-fires** on caption pops. The decode
phase classifies base frames into layout modes (`layout_timeline.json`) and
cross-checks; `pacing.json` stats are candidate-derived and may be corrected.

## measure-request.json (written by the decode phase)

```json
{
  "keyframes":   [{"t": 3.2, "label": "mode-A"}],
  "crops":       [{"t": 4.1, "rect_pct": [10, 40, 80, 20], "label": "caption-zone"}],
  "microbursts": [{"t": 4.2, "window_s": 0.75, "fps": 12, "label": "pill-pop"}]
}
```

Micro-burst readout: first frame where the element appears → frame where it reaches
rest = `duration_s` (±1 frame). Overshoot then settle = `back/elastic`; monotonic
approach = `power-out`; constant step = `linear`; otherwise `UNKNOWN`. Classes, not
curves.

## Frame budget

`style.frame_budget` (default 120) caps what Claude *reads*, not what is on disk.
Read the base pass fully; bursts selectively (each layout transition + a few caption
events); measure outputs as they are produced.

## Guarantees

- No source dir → a plain message pointing to `stylespec.py add-source`.
- DRIFT gate: refuses to run if `source.mp4` no longer matches the fingerprint in
  `source.json`.
- Re-running a pass overwrites only its own files (distinct prefixes); frames are
  keyed to timestamps, so cited evidence never silently changes content.
- Over 10 minutes: the base pass warns that 100 frames is a sparse scan.
