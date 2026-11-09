#!/usr/bin/env python3
# Copied from shorts-studio scripts/clip_cut.py.
# Copyright (c) 2026 Claude Video Studio contributors. MIT License; full text in the plugin NOTICE.
# Changed: runtime tools; UTF-8/LF; full-batch range/name/output preflight;
# Changed: transcript adapters; no overwrites; encode-generation disclosure.
"""Cut Shorts from one recording; each output folder starts an independent reel.

clip_cut.py recording.mp4 --words work/tx.json --clips clips.json --out clips
Ranges use inclusive word indices (from/to), or start/end seconds.
"""
import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
from win_encoding import ensure_utf8_output
import runtime as rt


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def duration(video):
    p = subprocess.run([rt.tool("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                        "-of", "json", str(video)], check=True, capture_output=True)
    value = float(json.loads(p.stdout)["format"]["duration"])
    if not math.isfinite(value) or value <= 0:
        raise ValueError("the recording has no readable duration")
    return value


def adapt(doc):
    rows = doc["words"] if isinstance(doc, dict) else doc
    out = []
    for k, w in enumerate(rows):
        # Object transcripts use ordinal indices, including maps with w_NNNN ids.
        i = k if isinstance(doc, dict) else w.get("i", k)
        s, e = float(w["start"]), float(w["end"])
        if type(i) is not int or i < 0 or not (math.isfinite(s) and math.isfinite(e) and 0 <= s <= e):
            raise ValueError("the word list has an invalid index or time")
        out.append(dict(i=i, text=w.get("text", w.get("word", "")), start=s, end=e))
    if any(a["i"] >= b["i"] or a["start"] > b["start"] for a, b in zip(out, out[1:])):
        raise ValueError("the word list must be in index and time order")
    return out


def safe_name(name):
    # Portable single folder names, including Windows reserved device names.
    return (isinstance(name, str) and bool(name.strip()) and ".." not in name
            and not re.search(r'[<>:"/\\|?*\x00-\x1f\x7f]', name)
            and not name.endswith((" ", "."))
            and name.split(".")[0].upper() not in {"CON", "PRN", "AUX", "NUL", *("COM%d" % n for n in range(1, 10)),
                                                      *("LPT%d" % n for n in range(1, 10))})


def preflight(a, words, clips):
    if not isinstance(clips, list) or not clips:
        raise ValueError("clips.json needs a non-empty list")
    limit = min(duration(a.video), duration(a.also)) if a.also else duration(a.video)
    if not math.isfinite(a.pad) or a.pad < 0:
        raise ValueError("padding must be a non-negative number")
    plans, names = [], set()
    for n, c in enumerate(clips, 1):
        if "from" in c:
            first, last = c["from"], c["to"]
            if (type(first) is not int or type(last) is not int or first < 0 or first > last
                    or not words or last > words[-1]["i"]):
                raise ValueError("a word range runs past the word list or is invalid")
            ws = [w for w in words if first <= w["i"] <= last]
            if not ws or ws[0]["i"] != first or ws[-1]["i"] != last:
                raise ValueError("a word range has no matching endpoints")
            t0, t1 = max(0, ws[0]["start"] - a.pad), min(limit, ws[-1]["end"] + a.pad)
        else:
            t0, t1 = float(c["start"]), float(c["end"])
            ws = [w for w in words if w["start"] >= t0 and w["end"] <= t1]
        if not (math.isfinite(t0) and math.isfinite(t1) and 0 <= t0 < t1 <= limit):
            raise ValueError("a clip range runs past the recording's end or is invalid")
        name = c.get("name", "clip-%d" % n)
        if not safe_name(name):
            raise ValueError("a clip name is unsafe; use a single plain folder name")
        folder = Path(a.out) / name
        if name.casefold() in names or folder.exists() or folder.is_symlink():
            raise ValueError("a clip output folder already exists or is named twice; choose a new name")
        names.add(name.casefold())
        plans.append((name, folder, t0, t1, ws))
    return plans


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("video")
    ap.add_argument("--words", required=True)
    ap.add_argument("--clips", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pad", type=float, default=.15)
    ap.add_argument("--also", help="a second video on the same source timeline")
    a = ap.parse_args(argv)
    try:
        plans = preflight(a, adapt(load(a.words)), load(a.clips))
        print("info: encode generations +1 (re-encode crf 16)")
        for name, folder, t0, t1, ws in plans:
            folder.mkdir(parents=True, exist_ok=False)
            subprocess.run([rt.tool("ffmpeg"), "-nostdin", "-v", "error", "-n", "-ss", f"{t0:.3f}", "-i", a.video,
                            "-t", f"{t1 - t0:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "16",
                            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(folder / "source.mp4")], check=True)
            if a.also:
                subprocess.run([rt.tool("ffmpeg"), "-nostdin", "-v", "error", "-n", "-ss", f"{t0:.3f}", "-i", a.also,
                                "-t", f"{t1 - t0:.3f}", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                                "-pix_fmt", "yuv420p", str(folder / "screen.mp4")], check=True)
            re_t = [dict(i=k, text=w["text"], start=round(w["start"] - t0, 3), end=round(w["end"] - t0, 3))
                    for k, w in enumerate(ws)]
            (folder / "words_raw.json").write_bytes((json.dumps(re_t, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
            length, first = t1 - t0, " ".join(w["text"] for w in ws[:16])
            flag = "" if 15 <= length <= 75 else " (outside 15 to 75 s; check it)"
            print(f'{name}: {length:.2f} s raw{flag}\n   opens: "{first}"')
        print(f"{len(plans)} clip(s) -> {a.out}. Next: treat each source.mp4 as its own reel.")
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as e:
        print("The clips were stopped: " + str(e).strip().splitlines()[0], file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
