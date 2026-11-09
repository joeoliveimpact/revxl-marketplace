# Changed from shorts-studio scripts/pacing_check.py (MIT): stdlib pixel measurements via runtime.tool, warning-only rows, declared transition windows; contact sheet moved to review_aids.
"""Post-render pacing suggestions from small grey frames (port 6).

    python -X utf8 -I pacing_check.py <reel_dir> [--render <mp4>]

H-B6: PHASE = "post"; run(ctx) returns [{check, level: "warn", msg, where,
at?}]. ctx = {reel_dir, fps, cuts, beats, render}. Nothing is written. At 0.1 s
steps, a change means over 0.4% of pixels differ by more than 14 levels. A gap
over 1 s suggests a change; a shot under 0.3 s between hard cuts suggests a
longer hold, unless inside one declared transition window. Never blocks.
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

PHASE = "post"
WIDTH, HEIGHT, RATE = 96, 160, 30


def _moved(left, right, threshold):
    return sum(abs(a - b) > threshold for a, b in zip(left, right)) / len(left)


def _windows(beats, fps):
    # Match the picture check: one declaration per cut, never widened by duplicates.
    windows = {}
    for beat in beats or []:
        transition = beat.get("transition")
        if not isinstance(transition, dict):
            continue
        cut, duration = transition.get("at_cut_frame"), transition.get("dur_frames")
        if (not isinstance(transition.get("type"), str) or not transition["type"]
                or not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0
                           for v in (cut, duration))):
            continue
        windows.setdefault(cut, ((cut - duration) / fps, (cut + duration) / fps))
    return list(windows.values())


def _warn(check, msg, render, at=None):
    row = dict(check=check, level="warn", msg=msg, where=str(render))
    if at is not None:
        row["at"] = round(at, 2)
    return row


def run(ctx):
    render = ctx.get("render")
    try:
        if render is None:
            raise ValueError("no video")
        probe = subprocess.run([rt.tool("ffprobe"), "-v", "error", "-select_streams", "v:0",
                                "-show_entries", "stream=duration:format=duration", "-of", "json", str(render)],
                               capture_output=True, check=True, timeout=30, env=rt.python_env())
        info = json.loads(probe.stdout)
        duration = float(info["streams"][0].get("duration") or info["format"]["duration"])
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("no duration")
        decoded = subprocess.run([rt.tool("ffmpeg"), "-nostdin", "-v", "error", "-i", str(render),
                                  "-vf", f"fps={RATE},scale={WIDTH}:{HEIGHT},format=gray", "-an",
                                  "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                                 capture_output=True, check=True, timeout=60 + 2 * duration, env=rt.python_env())
        size = WIDTH * HEIGHT
        data = memoryview(decoded.stdout)
        frames = [data[i:i+size] for i in range(0, len(data), size) if i + size <= len(data)]
        if len(frames) < 2:
            raise ValueError("no frames")
        events, cuts = [], []
        for i in range(1, len(frames)):
            if _moved(frames[i-1], frames[i], 30) > .35:
                cuts.append(i / RATE)
            if i % 3 == 0 and _moved(frames[i-3], frames[i], 14) > .004:
                events.append(i / RATE)
        points = [0.0, *events, duration]
        rows = [_warn("dead-zone", f"Nothing visibly changes for {end-start:.1f} seconds here. "
                      "Consider a zoom, B-roll or a cut at this point.", render, start)
                for start, end in zip(points, points[1:]) if end - start > 1.0 + 1e-9]
        fps = float(ctx.get("fps") or RATE)
        windows = _windows(ctx.get("beats"), fps)
        for start, end in zip(cuts, cuts[1:]):
            if end - start < .3 - 1e-9 and not any(a <= start and end <= b for a, b in windows):
                rows.append(_warn("quick-flash", "This shot lasts less than 0.3 seconds between cuts. "
                                  "Consider holding it longer so it is easier to follow.", render, start))
        return rows
    except (OSError, ValueError, KeyError, IndexError, TypeError, subprocess.SubprocessError):
        return [_warn("pacing-unchecked", "The pacing check could not read the finished video. "
                      "Make the final video, check the editor's video tools and try again.", render or "renders")]


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reel_dir", type=Path)
    ap.add_argument("--render", type=Path)
    args = ap.parse_args()
    sys.path.insert(0, str(HERE))  # -I omits the script directory.
    from check import build_context
    render = args.render or max((args.reel_dir / "renders").glob("* Master - *.mp4"),
                                key=lambda p: (p.stat().st_mtime_ns, p.name), default=None)
    try:
        rows = run(build_context(args.reel_dir, render))
    except (OSError, ValueError, KeyError, TypeError):
        rows = [_warn("pacing-unchecked", "The pacing inputs could not be read. Restore the cut list and Beat Map, "
                      "then run the check again.", args.reel_dir)]
    for row in rows:
        print("WARN  %s  %s" % (row["check"], row["msg"]))
    if not rows:
        print("Pacing check: no suggestions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
