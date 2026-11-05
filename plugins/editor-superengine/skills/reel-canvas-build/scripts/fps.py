"""The reel's real frame rate, read from the video, never guessed (stdlib only).

Rates are exact rationals "num/den" (30000/1001 stays 30000/1001, never 29.97 rounded). The rate
comes from the video's average frame rate only; there is no nominal-rate fallback and no default
(H-R34: a reel ran at 25 fps while work/probe.json's out_rate said 30.0, so callers pass the real
rate). Anything that can't be read raises FpsError with a plain message.
parse_fps follows video-use helpers/render.py (https://github.com/browser-use/video-use,
MIT License, Copyright (c) 2026 Browser Use), reimplemented here to raise ValueError.

  fps.py probe <video> [--ffprobe PATH]   one JSON line {"fps": "n/d", "vfr": bool, "frames": int}
  fps.py --selftest
"""
import argparse
import json
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime  # noqa: E402

MAX_COMPONENT = 2_147_483_647  # ffmpeg keeps rates as signed 32-bit num/den; bounding keeps parse_fps idempotent
RATE_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?|[0-9]+/[0-9]+")
BAD_RATE = "is not a frame rate; use a positive number or fraction, e.g. 30, 29.97 or 30000/1001"


class FpsError(ValueError):
    """The frame rate (or frame count) of a video couldn't be read."""


def parse_fps(value):
    """Canonical exact rate "num/den" from "60", "29.97", "30000/1001" (or a JSON number). Idempotent."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f"{value!r} {BAD_RATE}")
    text = str(value).strip()
    if len(text) > 32 or not RATE_RE.fullmatch(text):
        raise ValueError(f"{text[:40]!r} {BAD_RATE}")
    try:
        rate = Fraction(text)
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"{text!r} {BAD_RATE}") from None
    if rate <= 0:
        raise ValueError(f"{text!r} is not a frame rate; it must be greater than zero")
    if rate.numerator > MAX_COMPONENT or rate.denominator > MAX_COMPONENT:
        raise ValueError(f"{text!r} is too precise or too large to be a frame rate; use e.g. 30000/1001")
    return f"{rate.numerator}/{rate.denominator}"


def as_fraction(rate):
    return Fraction(parse_fps(rate))


def _ffprobe(video, ffprobe, args, what):
    """stdout of ffprobe <args> <video>; any failure is an FpsError naming the video."""
    name = Path(video).name
    try:
        exe = ffprobe or runtime.tool("ffprobe")
    except KeyError:
        raise FpsError(f"couldn't read the {what} of {name}; ffprobe isn't installed, run the editor setup first") from None
    try:
        p = subprocess.run([str(exe), "-v", "error", *args, str(video)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", check=True)
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or "").strip().splitlines()[-1:] or ["ffprobe failed"]
        raise FpsError(f"couldn't read the {what} of {name}; {detail[0]}") from None
    except OSError as e:
        raise FpsError(f"couldn't read the {what} of {name}; ffprobe didn't run ({e})") from None
    return p.stdout


def _stream(video, ffprobe, args, what):
    out = _ffprobe(video, ffprobe, ["-select_streams", "v:0", *args, "-of", "json"], what)
    try:
        streams = json.loads(out).get("streams") or []
    except (ValueError, AttributeError):
        streams = []
    if not streams or not isinstance(streams[0], dict):
        raise FpsError(f"couldn't read the {what} of {Path(video).name}; it has no video stream")
    return streams[0]


def probe_fps(video, ffprobe=None):
    """The video's average frame rate as "num/den". No r_frame_rate fallback, no default."""
    what = "frame rate"
    value = _stream(video, ffprobe, ["-show_entries", "stream=avg_frame_rate"], what).get("avg_frame_rate")
    if not value or value == "0/0":
        raise FpsError(f"couldn't read the {what} of {Path(video).name}; the video reports no average "
                       f"frame rate, so pass the rate explicitly")
    try:
        return parse_fps(value)
    except ValueError:
        raise FpsError(f"couldn't read the {what} of {Path(video).name}; it reports {str(value)[:40]!r}, "
                       f"which is not a frame rate") from None


def resolve_fps(video=None, explicit=None, ffprobe=None):
    """An explicit rate wins (no probe); otherwise the video's own rate."""
    if explicit is not None:
        return parse_fps(explicit)
    if video is None:
        raise FpsError("couldn't work out the frame rate; give a video or an explicit rate")
    return probe_fps(video, ffprobe)


def is_vfr(video, ffprobe=None, tolerance=0.002):
    """True when the gaps between frames vary by more than `tolerance` seconds (variable frame rate)."""
    out = _ffprobe(video, ffprobe, ["-select_streams", "v:0", "-show_entries", "packet=pts_time",
                                    "-of", "csv=p=0"], "frame timing")
    pts = []
    for line in out.splitlines():
        s = line.strip().strip(",")
        if not s or s == "N/A":
            continue
        try:
            pts.append(float(s))
        except ValueError:
            raise FpsError(f"couldn't read the frame timing of {Path(video).name}; ffprobe printed "
                           f"{s[:40]!r}") from None
    if len(pts) < 3:
        return False
    pts.sort()
    deltas = [b - a for a, b in zip(pts, pts[1:])]
    return max(deltas) - min(deltas) > tolerance


def frame_count(video, ffprobe=None):
    """Exact number of decoded video frames (decodes the whole stream)."""
    what = "frame count"
    value = _stream(video, ffprobe, ["-count_frames", "-show_entries", "stream=nb_read_frames"],
                    what).get("nb_read_frames")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise FpsError(f"couldn't read the {what} of {Path(video).name}; ffprobe reported "
                       f"{str(value)[:40]!r}") from None


def selftest():
    fails = []
    for value, want in (("60", "60/1"), ("29.97", "2997/100"), ("30000/1001", "30000/1001"), (25, "25/1"),
                        (" 24 ", "24/1"), ("50/2", "25/1")):
        try:
            got = parse_fps(value)
            if got != want or parse_fps(got) != got:
                fails.append(f"parse_fps({value!r}) = {got!r}, want {want!r} (idempotent)")
        except ValueError as e:
            fails.append(f"parse_fps({value!r}) raised {e}")
    for value in ("", "nope", "0", "-24", "1/0", "1e3", "1_000", "0.12345678901234567890", "1" * 33,
                  "2147483648", "1/2147483648", True, None):
        try:
            parse_fps(value)
            fails.append(f"parse_fps({value!r}) did not raise")
        except ValueError:
            pass
    if as_fraction("30000/1001") != Fraction(30000, 1001):
        fails.append("as_fraction('30000/1001') is wrong")
    if fails:
        for f in fails:
            print(f"selftest FAILED: {f}")
        return 1
    print("selftest ok")
    return 0


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Read a video's real frame rate.")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks (no ffprobe) and exit")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("probe", help="print the video's fps, whether it is variable, and its frame count")
    p.add_argument("video")
    p.add_argument("--ffprobe", help="ffprobe to use (default: the editor's own)")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd == "probe":
        try:
            info = {"fps": probe_fps(a.video, a.ffprobe), "vfr": is_vfr(a.video, a.ffprobe),
                    "frames": frame_count(a.video, a.ffprobe)}
        except FpsError as e:
            print(e)
            return 1
        print(json.dumps(info))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
