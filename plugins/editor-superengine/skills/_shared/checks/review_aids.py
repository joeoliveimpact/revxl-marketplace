#!/usr/bin/env python3
"""Post-render review aids: cut strips, contact sheet and a phone-size copy.

    python -X utf8 -I review_aids.py <reel_dir> [--render <mp4>]

H-B6: PHASE = "post"; run(ctx) returns [] or one review-aids warning, never a
block. ctx = {reel_dir, fps, cuts, beats, render}. Writes work/qa/index.json
with reel-relative paths to successful pieces. Cut pictures use contiguous
frame-number ranges, never timestamp seeks (F-12). The grey-frame pacing port
lives in pacing_check; the port-6 contact sheet lives here. Stdlib only.
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
import textwrap
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

PHASE = "post"
FONT = HERE.parents[2] / "runtime/fonts/Inter-Regular.woff2"


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _ffmpeg(args, duration):
    subprocess.run([rt.tool("ffmpeg"), "-nostdin", "-v", "error", "-y", *map(str, args)],
                   capture_output=True, check=True, timeout=60 + 2 * duration, env=rt.python_env())


def strip_filter(first, last):
    """Inspectable F-12 contract; scale/split preserve the input frame numbers."""
    return f"select='between(n,{first},{last})',tile={last-first+1}x1"


def _filter_path(path):
    return "'" + path.as_posix().replace(":", "\\:").replace("'", "'\\''") + "'"


def _strip(render, frames, target, first, last, fps, words, temp, duration):
    """Drop failed decorations independently; the numbered frame strip still ships."""
    width = 180 * (last - first + 1)
    start, end = first / fps, (last + 1) / fps
    wave = temp / (target.stem + "-wave.png")
    failed = False
    try:
        _ffmpeg(["-i", render, "-filter_complex",
                 f"[0:a:0]atrim=start={start:.9f}:end={end:.9f},asetpts=PTS-STARTPTS,"
                 f"showwavespic=s={width}x64:colors=white[wave]",
                 "-map", "[wave]", "-frames:v", "1", wave], duration)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        failed = True
    text = temp / (target.stem + "-words.txt")
    try:
        labels = " ".join(w["word"].strip() for w in words
                          if w["start"] < end and w["end"] > start)
        text.write_bytes(("\n".join(textwrap.wrap(labels, max(20, width // 9))) + "\n").encode("utf-8"))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        labels, failed = "", True
    args = ["-i", frames]
    if wave.is_file() and wave.stat().st_size:
        args += ["-i", wave]
        base = "[0:v][1:v]vstack=inputs=2,pad=iw:ih+64:0:0:color=black"
    else:
        base = "[0:v]pad=iw:ih+64:0:0:color=black"
    # Unsupported WOFF2 is an expected fallback: retry without labels.
    if labels and FONT.is_file():
        label = (f",drawtext=fontfile={_filter_path(FONT)}:textfile={_filter_path(text)}:"
                 "expansion=none:fontcolor=white:fontsize=14:x=8:y=h-56")
        try:
            _ffmpeg([*args, "-filter_complex", base + label, "-frames:v", "1", target], duration)
            return failed
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            pass
    try:
        _ffmpeg([*args, "-filter_complex", base, "-frames:v", "1", target], duration)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        failed = True
        shutil.copyfile(frames, target)
    return failed


def _build(ctx, index):
    reel, render = Path(ctx["reel_dir"]), Path(ctx["render"])
    qa = reel / "work/qa"
    qa.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run([rt.tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=nb_frames,r_frame_rate,duration:format=duration", "-of", "json", str(render)],
                           capture_output=True, check=True, timeout=30, env=rt.python_env())
    info = json.loads(probe.stdout)
    stream = info["streams"][0]
    fps = float(Fraction(stream["r_frame_rate"]))
    duration = float(stream.get("duration") or info["format"]["duration"])
    total = int(stream["nb_frames"]) if str(stream.get("nb_frames", "")).isdigit() else math.ceil(duration * fps)
    if total <= 0 or fps <= 0 or not math.isfinite(duration):
        raise ValueError("no picture")
    cuts = ctx.get("cuts") or _read(reel / "work/cuts.json")
    failed = False
    try:
        words = _read(reel / "work/edit_map.cut.json")["words"]
    except (OSError, ValueError, KeyError, TypeError):
        words, failed = [], True
    with tempfile.TemporaryDirectory(prefix=".aids-", dir=qa) as folder:
        temp = Path(folder)
        strips = [(max(0, min(total-1, int(s["out_in_f"]) - 2)),
                   max(0, min(total-1, int(s["out_in_f"]) + 2))) for s in cuts["segments"][1:]]
        frames = [temp / ("cut-%02d-frames.png" % i) for i in range(1, len(strips) + 1)]
        if strips:
            # One decode and one scale for every boundary, rather than decoding the
            # Master again for each cut. n stays the original input frame number.
            split = (f"[0:v]scale=180:320,split={len(strips)}" +
                     "".join(f"[v{i}]" for i in range(len(strips))))
            filters = [split] + [f"[v{i}]" + strip_filter(a, b) + f"[s{i}]"
                                 for i, (a, b) in enumerate(strips)]
            outputs = [arg for i, frame in enumerate(frames)
                       for arg in ("-map", f"[s{i}]", "-frames:v", "1", frame)]
            try:
                _ffmpeg(["-i", render, "-filter_complex", ";".join(filters), *outputs], duration)
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                # A failed output must not discard all the other cut strips.
                pass
        for i, ((first, last), frame) in enumerate(zip(strips, frames), 1):
            target = qa / ("cut-%02d.png" % i)
            try:
                if not frame.is_file() or not frame.stat().st_size:
                    _ffmpeg(["-i", render, "-vf", "scale=180:320," + strip_filter(first, last),
                             "-frames:v", "1", frame], duration)
                failed = _strip(render, frame, target, first, last, fps, words, temp, duration) or failed
                index["strips"].append(target.relative_to(reel).as_posix())
            except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
                # In particular, malformed words must not lose the picture strip.
                failed = True
                if frame.is_file() and frame.stat().st_size:
                    shutil.copyfile(frame, target)
                    index["strips"].append(target.relative_to(reel).as_posix())
        for key, name, args in (
                ("contact", "contact.jpg", ["-i", render, "-vf",
                 f"fps=1,scale=180:-2,tile=8x{max(1, math.ceil(duration / 8))}:padding=8:margin=8:color=white",
                 "-frames:v", "1", "-q:v", "4"]),
                ("phone", "phone-720p.mp4", ["-i", render, "-map", "0:v:0", "-map", "0:a?",
                 "-vf", "scale=720:1280", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                 "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart"])):
            target = qa / name
            try:
                _ffmpeg([*args, target], duration)
                if not target.is_file() or not target.stat().st_size:
                    raise ValueError("empty aid")
                index[key] = target.relative_to(reel).as_posix()
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                failed = True
    return failed


def run(ctx):
    index = dict(strips=[], contact=None, phone=None)
    try:
        failed = _build(ctx, index)
    except Exception:
        # QA tooling is optional: even a malformed input cannot block the final.
        failed = True
    try:
        qa = Path(ctx["reel_dir"]) / "work/qa"
        qa.mkdir(parents=True, exist_ok=True)
        (qa / "index.json").write_bytes((json.dumps(index, indent=2) + "\n").encode("utf-8"))
    except (OSError, ValueError, KeyError):
        failed = True
    return [dict(check="review-aids", level="warn", where="work/qa",
                 msg="Some review pictures or the phone copy could not be made. Use the available files, "
                     "check the editor's video tools and run QA again.")] if failed else []


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
        ctx = build_context(args.reel_dir, render)
    except (OSError, ValueError, KeyError, TypeError):
        ctx = dict(reel_dir=args.reel_dir, render=render)
    rows = run(ctx)
    for row in rows:
        print("WARN  %s  %s" % (row["check"], row["msg"]))
    if not rows:
        print("Review aids ready in work/qa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
