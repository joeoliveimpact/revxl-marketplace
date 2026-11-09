#!/usr/bin/env python3
"""style-decoder — frame extraction passes.

    python styleframes.py <style-slug> <src-id> [--pass base|cuts|bursts|captions|measure|all]
                          [--band-top 33] [--band-bottom 72]

Passes (all write under sources/<src-id>/):
  base     auto-fps thumbnails (<=2fps, <=100 frames, 512px wide) -> frames/base_*.jpg
           Budget by duration:
           <=30s ~1-2fps · 30-60s ~40f · 1-3min ~60f · 3-10min ~80f · >10min 100f sparse.
  cuts     ffmpeg scene-detect (threshold cfg.style.scene_threshold) -> cuts.json
           + pacing.json (shot stats). CANDIDATES ONLY: misses panel swaps over
           static backgrounds, false-fires on caption pops — Claude cross-checks
           against the layout timeline in the decode phase.
  bursts   hook window 0-3s @ 4fps (0.25s density)
           + ±0.5s @ 4fps around each candidate cut -> frames/hook_*.jpg, cut_NN_*.jpg
  captions thin caption-band strips at ~2/s (band = --band-top..--band-bottom % of
           height, default 33-72) -> captions/cap_NNN.jpg + captions/timebase.json
  measure  full-res keyframes + hi-res zone crops + micro-bursts, driven by a
           request file (written by Claude in the decode phase):
             measure-request.json = {
               "keyframes":   [{"t": 3.2, "label": "mode-A"}],
               "crops":       [{"t": 4.1, "rect_pct": [10,40,80,20], "label": "caption-zone"}],
               "microbursts": [{"t": 4.2, "window_s": 0.75, "fps": 12, "label": "pill-pop"}]
             }
           -> frames/kf_*.png (full-res), frames/crop_*.png, frames/mb_<label>_*.png
           Micro-bursts measure animation duration + overshoot (easing class).

Frame names carry millisecond timestamps (base_0004_t2500.jpg) so the decode
phase can order animation states without ffprobe. Contract: styleframes-contract.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enginecfg import cfg  # noqa: E402
import stylespec  # noqa: E402  (also puts skills/_shared on sys.path)
from win_encoding import ensure_utf8_output  # noqa: E402

MAX_BASE_FRAMES = 100
MAX_BASE_FPS = 2.0
BASE_WIDTH = 512


def src_dir(slug: str, src: str) -> str:
    d = os.path.join(stylespec.style_dir(slug), "sources", src)
    if not os.path.isdir(d):
        sys.exit(f"no source dir: {d} — register the video first: stylespec.py add-source {slug} <file>")
    return d


def video_of(slug: str, src: str) -> tuple[str, float]:
    d = src_dir(slug, src)
    v = os.path.join(d, "source.mp4")
    fp = stylespec.fingerprint(v)
    if not fp.get("exists") or not fp.get("duration"):
        sys.exit(f"source.mp4 missing/unprobeable in {d}")
    # drift check against the registered fingerprint (staleness doctrine)
    sj = os.path.join(d, "source.json")
    if os.path.exists(sj):
        with open(sj, encoding="utf-8") as f:
            reg = json.load(f).get("fingerprint", {})
        if reg and (reg.get("size") != fp["size"] or abs((reg.get("duration") or 0) - fp["duration"]) > 0.1):
            sys.exit(f"DRIFT: source.mp4 does not match registered fingerprint in {sj}")
    return v, fp["duration"]


def run_ffmpeg(cmd: list[str]) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        tail = r.stderr.strip().splitlines()[-4:]
        sys.exit("ffmpeg failed:\n  " + "\n  ".join(tail))
    return r


def extract_at(video: str, t: float, out: str, width: int | None = None) -> None:
    vf = [f"scale={width}:-2"] if width else []
    run_ffmpeg([stylespec.tool("ffmpeg"), "-hide_banner", "-loglevel", "error",
                "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                *(["-vf", ",".join(vf)] if vf else []), "-q:v", "3", "-y", out])


# ---------------------------------------------------------------- base

def base_budget(duration: float) -> int:
    if duration <= 30:
        return min(MAX_BASE_FRAMES, max(10, int(duration * 1.5)))
    if duration <= 60:
        return 40
    if duration <= 180:
        return 60
    if duration <= 600:
        return 80
    return MAX_BASE_FRAMES


def pass_base(slug: str, src: str) -> None:
    video, dur = video_of(slug, src)
    frames = os.path.join(src_dir(slug, src), "frames")
    os.makedirs(frames, exist_ok=True)
    n = base_budget(dur)
    fps = min(MAX_BASE_FPS, n / dur)
    step = dur / n
    if dur > 600:
        print(f"[base] WARNING: {dur:.0f}s video — 100 frames is a sparse scan")
    for i in range(n):
        t = min(i * step, dur - 0.05)
        out = os.path.join(frames, f"base_{i:04d}_t{int(t * 1000)}.jpg")
        extract_at(video, t, out, BASE_WIDTH)
    print(f"[base] {n} frames @ ~{fps:.2f}fps -> {frames}")


# ---------------------------------------------------------------- cuts + pacing

def pass_cuts(slug: str, src: str) -> None:
    video, dur = video_of(slug, src)
    d = src_dir(slug, src)
    thr = cfg()["style"]["scene_threshold"]
    r = subprocess.run(
        [stylespec.tool("ffmpeg"), "-hide_banner", "-i", video,
         "-vf", f"select='gt(scene,{thr})',showinfo", "-f", "null", "-"],
        capture_output=True, text=True, timeout=600)
    times = [round(float(m), 3) for m in
             re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    times = sorted(set(times))

    shots = []
    prev = 0.0
    for t in times + [dur]:
        if t - prev > 0.05:
            shots.append(round(t - prev, 3))
        prev = t
    shots_sorted = sorted(shots)
    median = shots_sorted[len(shots_sorted) // 2] if shots_sorted else dur
    hist_edges = [0.5, 1, 2, 3, 5, 8]
    hist = {f"<{e}s": sum(1 for s in shots if s < e and (i == 0 or s >= hist_edges[i - 1]))
            for i, e in enumerate(hist_edges)}
    hist[f">={hist_edges[-1]}s"] = sum(1 for s in shots if s >= hist_edges[-1])

    with open(os.path.join(d, "cuts.json"), "w", encoding="utf-8") as f:
        json.dump({"threshold": thr, "note": "CANDIDATES ONLY — cross-check vs layout timeline",
                   "cut_times": times}, f, indent=2)
    pacing = {
        "duration_s": dur,
        "candidate_cuts": len(times),
        "cuts_per_10s": round(len(times) / dur * 10, 2) if dur else 0,
        "median_shot_s": median,
        "mean_shot_s": round(sum(shots) / len(shots), 3) if shots else dur,
        "longest_hold_s": max(shots) if shots else dur,
        "shot_histogram": hist,
        "hook_window": {"cuts_0_3s": sum(1 for t in times if t <= 3.0)},
    }
    with open(os.path.join(d, "pacing.json"), "w", encoding="utf-8") as f:
        json.dump(pacing, f, indent=2)
    print(f"[cuts] {len(times)} candidates · median shot {median}s · "
          f"{pacing['cuts_per_10s']}/10s -> cuts.json, pacing.json")


# ---------------------------------------------------------------- bursts

def pass_bursts(slug: str, src: str) -> None:
    video, dur = video_of(slug, src)
    d = src_dir(slug, src)
    frames = os.path.join(d, "frames")
    os.makedirs(frames, exist_ok=True)

    # hook window: 0-3s at 0.25s density
    n_hook = 0
    t = 0.0
    while t <= min(3.0, dur - 0.05):
        extract_at(video, t, os.path.join(frames, f"hook_t{int(t * 1000)}.jpg"), BASE_WIDTH)
        n_hook += 1
        t += 0.25

    cuts_file = os.path.join(d, "cuts.json")
    n_cut_frames = 0
    if os.path.exists(cuts_file):
        with open(cuts_file, encoding="utf-8") as f:
            cut_times = json.load(f)["cut_times"]
        for i, ct in enumerate(cut_times):
            t = max(0.0, ct - 0.5)
            end = min(dur - 0.05, ct + 0.5)
            while t <= end:
                extract_at(video, t,
                           os.path.join(frames, f"cut_{i:02d}_t{int(t * 1000)}.jpg"),
                           BASE_WIDTH)
                n_cut_frames += 1
                t += 0.25
    else:
        print("[bursts] no cuts.json — run --pass cuts first for cut bursts")
    print(f"[bursts] hook {n_hook} frames · cut-bursts {n_cut_frames} frames")


# ---------------------------------------------------------------- measure

def pass_captions(slug: str, src: str, y0: float = 33, y1: float = 72) -> None:
    """Thin caption-band strips at ~2/s across the whole runtime.

    Why a dedicated pass: caption groups turn over ~every 0.5s, so a ~1fps base
    pass structurally cannot recover the grouping rule — it samples slower than
    the thing it's measuring. Cropping to a band keeps ~90 reads cheap. Feeds
    typography.caption_mechanics thresholds (grouping algorithm), which is what a
    CLONE needs; a per-reel group list only describes one video. Band defaults to
    y 33-72% of height (--band-top / --band-bottom); move it when captions sit elsewhere.

    TIMEBASE — selects by FRAME INDEX, not the fps filter, so the printed formula
    is literally true. `fps=2` does NOT sample at N*0.5s: it takes the input frame
    nearest each slot's MIDPOINT, landing at (N-1)*0.5 + 0.25s quantized to the
    source frame grid (= +0.2333s on 30fps). That 233ms error mis-attributes
    captions across any layout swap inside the window. Measured (07.24.26) on a
    30fps reel, frame-exact md5 against a single-decode `select` reference:
        fps=2                -> (N-1)*0.5 + 0.2333s   (90 strips)
        fps=2:round=down     -> neither timebase, and DROPS a strip (89)
        fps=2:start_time=0   -> identical to plain fps=2 (no-op here)
        select mod(n,step)   -> exactly (N-1)*step/fps  <-- chosen
    A true formula beats a formula plus a correction constant, and the constant
    isn't even portable (it scales with source fps). Writes captions/timebase.json
    so strips stay self-describing regardless of what a doc says later.
    """
    video, dur = video_of(slug, src)
    out = os.path.join(src_dir(slug, src), "captions")
    os.makedirs(out, exist_ok=True)
    if not 0 <= y0 < y1 <= 100:
        sys.exit(f"caption band must satisfy 0 <= top < bottom <= 100, got {y0}-{y1}")

    probe = subprocess.run(
        [stylespec.tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=avg_frame_rate", "-of", "default=noprint_wrappers=1:nokey=1", video],
        capture_output=True, text=True, timeout=30)
    num, _, den = (probe.stdout.strip() or "0/1").partition("/")
    fps = (int(num) / int(den)) if den and int(den) else 0.0
    if fps <= 0:
        sys.exit("could not read source fps — cannot establish a caption timebase")
    step = max(1, round(fps / 2))          # ~2 strips/sec, on exact frame indices
    interval = step / fps                  # the REAL spacing (0.5005s on 29.97fps)

    run_ffmpeg([stylespec.tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-i", video,
                "-vf", f"select='not(mod(n\\,{step}))',"
                       f"crop=iw:ih*{y1 - y0}/100:0:ih*{y0}/100,scale=420:-2",
                "-vsync", "0", "-q:v", "4", "-y", os.path.join(out, "cap_%03d.jpg")])
    n = len([f for f in os.listdir(out) if f.startswith("cap_")])

    with open(os.path.join(out, "timebase.json"), "w", encoding="utf-8") as f:
        json.dump({
            "method": "frame-index select",
            "filter": f"select='not(mod(n,{step}))'",
            "source_fps": round(fps, 4),
            "frame_step": step,
            "interval_s": round(interval, 6),
            "formula": f"t_of(NNN) = (NNN-1) * {round(interval, 6)}",
            "exact": abs(interval - 0.5) < 1e-9,
            "strips": n,
            "band_pct_of_height": [y0, y1],
            "extracted": stylespec.now_iso(),
            "note": ("Frame-exact: strip NNN IS source frame (NNN-1)*step. Do not "
                     "assume the ffmpeg fps filter — it offsets to slot midpoints."),
        }, f, indent=2)
        f.write("\n")

    exact = "exact" if abs(interval - 0.5) < 1e-9 else f"{interval:.4f}s spacing (source {fps:.3f}fps)"
    print(f"[captions] {n} band strips (y {y0}-{y1}%) -> captions/  "
          f"strip NNN = source frame (NNN-1)*{step}, t=(NNN-1)*{interval:.4f}s [{exact}]")


def pass_measure(slug: str, src: str) -> None:
    video, dur = video_of(slug, src)
    d = src_dir(slug, src)
    frames = os.path.join(d, "frames")
    os.makedirs(frames, exist_ok=True)
    req_file = os.path.join(d, "measure-request.json")
    if not os.path.exists(req_file):
        sys.exit(f"no {req_file} — the decode phase writes it (keyframes/crops/microbursts)")
    with open(req_file, encoding="utf-8") as f:
        req = json.load(f)

    def slug_label(s: str) -> str:
        return re.sub(r"[^a-z0-9-]", "-", s.lower())

    n = 0
    for kf in req.get("keyframes", []):
        t = min(float(kf["t"]), dur - 0.05)
        out = os.path.join(frames, f"kf_{slug_label(kf.get('label', 'x'))}_t{int(t * 1000)}.png")
        extract_at(video, t, out)  # full-res
        n += 1
    for cr in req.get("crops", []):
        t = min(float(cr["t"]), dur - 0.05)
        x, y, w, h = cr["rect_pct"]
        out = os.path.join(frames, f"crop_{slug_label(cr.get('label', 'x'))}_t{int(t * 1000)}.png")
        run_ffmpeg([stylespec.tool("ffmpeg"), "-hide_banner", "-loglevel", "error",
                    "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                    "-vf", f"crop=iw*{w}/100:ih*{h}/100:iw*{x}/100:ih*{y}/100",
                    "-y", out])
        n += 1
    for mb in req.get("microbursts", []):
        t0 = max(0.0, float(mb["t"]) - 0.1)
        win = float(mb.get("window_s", 0.75))
        fps = int(mb.get("fps", 12))
        label = slug_label(mb.get("label", "x"))
        out = os.path.join(frames, f"mb_{label}_t{int(t0 * 1000)}_%02d.png")
        run_ffmpeg([stylespec.tool("ffmpeg"), "-hide_banner", "-loglevel", "error",
                    "-ss", f"{t0:.3f}", "-t", f"{win:.3f}", "-i", video,
                    "-vf", f"fps={fps},scale=720:-2", "-y", out])
        n += 1
    print(f"[measure] fulfilled {n} request(s) from measure-request.json")


# ---------------------------------------------------------------- main

PASSES = {"base": pass_base, "cuts": pass_cuts, "bursts": pass_bursts,
          "captions": pass_captions, "measure": pass_measure}
DEFAULT_ORDER = ["base", "cuts", "bursts", "captions"]  # measure runs later, on request


def main() -> None:
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug")
    ap.add_argument("src")
    ap.add_argument("--pass", dest="which", default="all",
                    choices=[*PASSES, "all"],
                    help="all = base+cuts+bursts+captions (measure only ever runs explicitly)")
    ap.add_argument("--band-top", type=float, default=33,
                    help="captions pass: band top, %% of frame height (default 33)")
    ap.add_argument("--band-bottom", type=float, default=72,
                    help="captions pass: band bottom, %% of frame height (default 72)")
    args = ap.parse_args()
    for name in (DEFAULT_ORDER if args.which == "all" else [args.which]):
        if name == "captions":
            pass_captions(args.slug, args.src, args.band_top, args.band_bottom)
        else:
            PASSES[name](args.slug, args.src)


if __name__ == "__main__":
    main()
