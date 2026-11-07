#!/usr/bin/env python3
"""Post-render motion check (S9.4a, TRI-2, H-M19).

    python motion_check.py <reel_dir> [--render <mp4>]
    Exit 1 on any block, 0 when clean or suggestions only.

Module contract (H-B6): PHASE = "post"; run(ctx) returns a list of
{check, level: "block"|"warn", msg, where, at?}. ctx = {reel_dir, fps,
cuts, beats, render}; run() writes nothing. Without render, use the newest
renders/* Master - *.mp4. Standalone reads work/cuts.json for fps and
beat-map-selection.json for beats. Thresholds come from tuning.json,
defaulting to 0.5 s black and 3 s frozen when absent.

Blocks: black-gap (mid-reel, >= threshold), frozen (> threshold), pop
(one odd frame between similar neighbours), motion-unreadable (cannot check).
Warns: frozen-ok (work/qa-ok.json approves that freeze within 1 s and one frame),
first-frame-plain (nearly uniform opening picture; suggestion only).
Only the first declared transition window at each cut exempts pops.
Two ffmpeg passes: black/freezedetect, then small grey frames for both the
opening suggestion and pops. Frame numbers are preserved, never resampled.
"""
import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

PHASE = "post"
TUNING = HERE.parents[2] / "reel-canvas-build" / "references" / "tuning.json"
WIDTH, HEIGHT = 72, 128
FRAME_BYTES = WIDTH * HEIGHT
# Full-range grey levels: a pop must be a large jump on BOTH sides, while
# its surrounding pictures remain close. Ordinary motion/cuts lack that return.
POP_JUMP, POP_RETURN, POP_RATIO = 32, 12, 4
NUMBER = r"([+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)"
BLACK = re.compile(r"\bblack_start:\s*" + NUMBER + r"\s+black_end:\s*" + NUMBER
                   + r"\s+black_duration:\s*" + NUMBER)
FREEZE = re.compile(r"\bfreeze_(start|end):\s*" + NUMBER)


def _row(check, msg, where, at=None, level="block"):
    row = dict(check=check, level=level, msg=msg, where=str(where))
    if at is not None:
        row["at"] = at
    return row


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _fps(value):
    if isinstance(value, bool):
        raise ValueError("The cut has no usable frame rate; rebuild the cut list.")
    rate = float(Fraction(str(value)))
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("The cut has no usable frame rate; rebuild the cut list.")
    return rate


def _thresholds():
    tri = _read(TUNING).get("tri2", {}) if TUNING.exists() else {}
    values = tri.get("black_gap_s", 0.5), tri.get("frozen_s", 3)
    if not all(_number(v) and v > 0 for v in values):
        raise ValueError("The motion check limits must be positive seconds; restore tuning.json.")
    return values


def _render(reel, chosen):
    if chosen is not None:
        path = Path(chosen)
        if not path.is_absolute() and not path.is_file():
            path = reel / path
    else:
        candidates = [p for p in (reel / "renders").glob("* Master - *.mp4") if p.is_file()]
        if not candidates:
            raise ValueError("No Master video was found; render the Master before running this check.")
        path = max(candidates, key=lambda p: (p.stat().st_mtime_ns, p.name))
    if not path.is_file():
        raise ValueError("The Master video is missing; render it again or choose the right video.")
    return path


def _windows(beats):
    """First valid declaration wins per cut; a duplicate never widens its window."""
    if isinstance(beats, dict):
        beats = beats["beats"]
    if not isinstance(beats, list):
        raise ValueError("The beat map can't be read; save it again before checking transitions.")
    windows = {}
    for beat in beats:
        transition = beat.get("transition")
        if not isinstance(transition, dict):
            continue
        cut, duration = transition.get("at_cut_frame"), transition.get("dur_frames")
        # Incomplete/invalid declarations cannot hide a pop. beat_schema permits
        # a bare {type: cut}; it supplies no declared window to exempt.
        if (not isinstance(transition.get("type"), str) or not transition["type"]
                or not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0
                           for v in (cut, duration))):
            continue
        if cut not in windows:
            windows[cut] = (cut - duration, cut + duration)
    return list(windows.values())


def _approvals(reel):
    path = reel / "work" / "qa-ok.json"
    if not path.exists():
        return []
    allow = _read(path).get("allow", [])
    if not isinstance(allow, list):
        raise ValueError("The review approvals can't be read; save the hub review notes again or tell Claude.")
    return [entry["at"] for entry in allow if isinstance(entry, dict) and entry.get("check") == "frozen"
            and _number(entry.get("at")) and entry["at"] >= 0]


def _tool(name):
    try:
        installed = rt.tool(name)
        if Path(installed).is_file():
            return installed
    except (KeyError, OSError, ValueError):
        pass
    # Allows the same LIGHT proof on a machine without an editor installation.
    found = shutil.which(name)
    if not found:
        raise ValueError("The video tool is missing; run the editor setup and try again.")
    return found


def _decode(render, black_s, frozen_s):
    ffmpeg, env = _tool("ffmpeg"), rt.python_env()
    probe = subprocess.run([_tool("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                            "-of", "json", str(render)], capture_output=True, env=env, timeout=60)
    if probe.returncode:
        raise ValueError("The Master video couldn't be read; render it again and rerun the motion check.")
    duration = float(json.loads(probe.stdout)["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("The Master video couldn't be read; render it again and rerun the motion check.")
    timeout = 60 + 2 * duration
    base = [ffmpeg, "-hide_banner", "-nostats", "-nostdin", "-threads", "2", "-i", str(render),
            "-map", "0:v:0", "-an", "-sn", "-dn", "-filter_threads", "1"]
    filters = f"blackdetect=d={black_s:.9f}:pix_th=0.10,freezedetect=n=-60dB:d={frozen_s:.9f}"
    detected = subprocess.run(base + ["-vf", filters, "-f", "null", "-"],
                              capture_output=True, env=env, timeout=timeout)
    if detected.returncode:
        raise ValueError("The Master video couldn't be read; render it again and rerun the motion check.")
    decoded = subprocess.run(base + ["-v", "error", "-vf", f"scale={WIDTH}:{HEIGHT}:flags=area,format=gray",
                                     "-fps_mode", "passthrough", "-pix_fmt", "gray", "-threads", "1",
                                     "-f", "rawvideo", "pipe:1"],
                             capture_output=True, env=env, timeout=timeout)
    if decoded.returncode or not decoded.stdout or len(decoded.stdout) % FRAME_BYTES:
        raise ValueError("The Master pictures couldn't be read; render it again and rerun the motion check.")
    return detected.stderr.decode("utf-8", "replace"), decoded.stdout


def _freezes(log, duration):
    start = None
    spans = []
    for match in FREEZE.finditer(log):
        kind, value = match[1], float(match[2])
        if kind == "start":
            start = value
        elif start is not None:
            spans.append((start, max(0, value - start)))
            start = None
    if start is not None:  # freezedetect does not emit freeze_end at EOF.
        spans.append((start, max(0, duration - start)))
    return spans


def _mad(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / FRAME_BYTES


def _picture_rows(raw, render, fps, windows):
    frames = memoryview(raw)
    first = frames[:FRAME_BYTES]
    rows = []
    mean = sum(first) / FRAME_BYTES
    variance = sum(v * v for v in first) / FRAME_BYTES - mean * mean
    if variance <= 4:  # <= 2 luma levels standard deviation over the whole picture.
        rows.append(_row("first-frame-plain", "The first picture looks like a plain background. Consider opening "
                         "with the speaker or the hook title already visible.", render, 0, "warn"))
    count = len(raw) // FRAME_BYTES
    if count < 3:
        return rows
    left, middle = first, frames[FRAME_BYTES:2 * FRAME_BYTES]
    before = _mad(left, middle)
    for n in range(1, count - 1):
        right = frames[(n + 1) * FRAME_BYTES:(n + 2) * FRAME_BYTES]
        after = _mad(middle, right)
        if before >= POP_JUMP and after >= POP_JUMP and not any(a <= n <= b for a, b in windows):
            surrounding = _mad(left, right)
            if surrounding <= POP_RETURN and min(before, after) >= POP_RATIO * surrounding:
                rows.append(_row("pop", f"A single picture flashes at {n / fps:.3f} s. Remove that frame, or declare "
                                 "the intended transition in the beat map.", render, n / fps))
        left, middle, before = middle, right, after
    return rows


def run(ctx):
    reel = Path(ctx["reel_dir"])
    where = reel
    try:
        render = _render(reel, ctx.get("render"))
        where = render
        fps = ctx.get("fps")
        if fps is None:
            cuts = ctx.get("cuts")
            fps = (cuts if cuts is not None else _read(reel / "work" / "cuts.json"))["fps"]
        fps = _fps(fps)
        beats = ctx.get("beats")
        if beats is None:
            path = reel / "beat-map-selection.json"
            beats = _read(path)["beats"] if path.exists() else []
        windows, approvals = _windows(beats), _approvals(reel)
        black_s, frozen_s = _thresholds()
        log, raw = _decode(render, black_s, frozen_s)
        count = len(raw) // FRAME_BYTES
        duration, last_frame = count / fps, (count - 1) / fps
        # black_end is the first non-black frame, except at EOF where ffmpeg
        # reports the last black frame instead. A gap ending on the penultimate
        # frame is internal if the final picture is visible. Match blackdetect's
        # default 98% black-pixel rule at its 0.10 threshold in full-range grey.
        last_black = sum(v <= 25.5 for v in raw[-FRAME_BYTES:]) / FRAME_BYTES >= 0.98
        edge_epsilon = max(1e-6, duration * 1e-6)  # ffmpeg prints rounded timestamps.
        rows = []
        for match in BLACK.finditer(log):
            start, end, length = map(float, match.groups())
            internal_end = (end < last_frame - edge_epsilon
                            or (abs(end - last_frame) <= edge_epsilon and not last_black))
            if start > 1e-6 and internal_end and length >= black_s - 1e-6:
                rows.append(_row("black-gap", f"The picture goes black for {length:.2f} s at {start:.3f} s. "
                                 "Close the gap or replace the missing picture.", render, start))
        for start, length in _freezes(log, duration):
            if length <= frozen_s + 1e-6:
                continue
            approved = any(abs(at - start) <= 1 + 1 / fps + 1e-6 for at in approvals)
            msg = (f"The picture stays still for {length:.2f} s at {start:.3f} s; check for a freeze. "
                   + ("This pause has the client's OK; keep it if it still fits the edit." if approved else
                      "Fix it, or OK it from the hub review notes or tell Claude."))
            rows.append(_row("frozen-ok" if approved else "frozen", msg, render, start,
                             "warn" if approved else "block"))
        rows.extend(_picture_rows(raw, render, fps, windows))
        return rows
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ZeroDivisionError,
            OverflowError, subprocess.SubprocessError) as exc:
        detail = str(exc).splitlines()[0] if str(exc) else "an input is missing"
        return [_row("motion-unreadable", "The motion check could not finish: " + detail
                     + " Check the Master video and the reel's work files, then try again.", where)]


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reel_dir")
    ap.add_argument("--render")
    args = ap.parse_args(argv)
    rows = run({"reel_dir": args.reel_dir, "render": args.render, "fps": None, "cuts": None, "beats": None})
    for row in rows:
        print(f"{row['level']} {row['check']}: {row['msg']} ({row['where']})")
    if not rows:
        print("Motion check: nothing to fix.")
    return 1 if any(row["level"] == "block" for row in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
