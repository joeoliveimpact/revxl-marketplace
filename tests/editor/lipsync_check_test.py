#!/usr/bin/env python3
"""Light media proof for the pre-render stale-camera check.

usage: python tests/editor/lipsync_check_test.py <scratch-dir> [--case NAME]

The raw is 320x568, 8 s, 30 fps with a moving test pattern, a binary frame
counter and sine audio. The fixture uses render.conform()'s ACTUAL default
1080x1920 cover/crop geometry, then downsizes to 320x568 before encoding;
geometry is not identity (320/568 differs slightly from 9/16). Only tiny
media are encoded. No render.py globals or production files are changed.

Cases catch: accepting a stale equal-length second segment, rejecting a clean
or graded cut, rejecting the allowed one-frame offset, missing a short master,
and blocking on an absent raw. Both run(ctx) and the standalone exit are checked.
Tools and child Python come from the editor install, like n1_map_test.py.
"""
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut_safety_test as cs  # noqa: E402

CHECK = cs.REPO / "plugins/editor-superengine/skills/_shared/checks/lipsync_check.py"
FPS = 30
CASES = ("clean", "stale", "onefr", "length", "noraw", "noaroll", "graded", "speed")
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def write(path, obj):
    path.write_bytes((json.dumps(obj, indent=1) + "\n").encode("utf-8"))


def ff(*args):
    p = cs.sh([cs.rt.tool("ffmpeg"), "-y", "-v", "error", *args])
    if p.returncode:
        raise RuntimeError("fixture ffmpeg failed: " + p.stderr[-1500:])


def raw_fixture(scratch):
    raw = scratch / "raw.mp4"
    # A binary counter needs no drawtext/font dependency. Each bit is a large
    # neutral patch so nearby frames stay distinguishable after tiny decoding.
    counter = ",".join(
        "drawbox=x=%d:y=12:w=28:h=80:color=white:t=fill:enable='bitand(n,%d)'"
        % (12 + bit * 37, 1 << bit) for bit in range(8))
    ff("-f", "lavfi", "-i", "testsrc2=size=320x568:rate=30:duration=8," + counter,
       "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=8",
       "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-shortest", raw)
    return raw


def fixture(scratch, name, raw):
    d = cs.fresh(scratch, name)
    cuts = dict(fps=FPS, speed=1.0, segments=[
        dict(src_in_f=15, src_out_f=60, out_in_f=0, out_out_f=45),
        dict(src_in_f=105, src_out_f=150, out_in_f=45, out_out_f=90)])
    if name == "speed":
        cuts["speed"] = 1.5
        cuts["segments"][0].update(out_out_f=30)
        cuts["segments"][1].update(out_in_f=30, out_out_f=60)
    write(d / "work/cuts.json", cuts)
    write(d / "work/probe.json", dict(input=str(raw), video=dict(width=320, height=568)))
    r = cs.module("render.py")
    conform = r.conform(dict(width=320, height=568))
    shift = {"stale": 41, "onefr": 1, "speed": 42}.get(name, 0)
    end = 140 if name == "length" else 150
    grade = ",eq=contrast=1.4:saturation=0.5" if name == "graded" else ""
    retime = ",setpts=(PTS-STARTPTS)/1.5,fps=30" if name == "speed" else ""
    graph = (
        "[0:v]split=2[a][b];"
        "[a]trim=start_frame=15:end_frame=60,setpts=PTS-STARTPTS[v0];"
        "[b]trim=start_frame=%d:end_frame=%d,setpts=PTS-STARTPTS[v1];"
        "[v0][v1]concat=n=2:v=1:a=0,%s,scale=320:568%s%s[v]"
        % (105 + shift, end + shift, conform, grade, retime))
    renders = d / "work/renders"
    renders.mkdir()
    ff("-i", raw, "-filter_complex", graph, "-map", "[v]", "-an", "-c:v", "libx264",
       "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p", renders / "master-100x.mp4")
    if name == "noraw":
        write(d / "work/probe.json", dict(input=str(d / "missing.mp4")))
    if name == "noaroll":
        (renders / "master-100x.mp4").unlink()
    elif name == "speed":
        (renders / "master-100x.mp4").rename(renders / "master-150x.mp4")
    return d, cuts


def check_case(scratch, name, raw, mod):
    d, cuts = fixture(scratch, name, raw)
    rows = mod.run(dict(reel_dir=d, fps=FPS, cuts=cuts, beats=None, render=None))
    p = cs.sh([cs.PY, "-X", "utf8", "-I", CHECK, d])
    print(p.stdout.rstrip())
    ck(name + ": contract rows", isinstance(rows, list) and all(
        {"check", "level", "msg", "where"} <= h.keys() and h["level"] in ("block", "warn")
        and "\n" not in h["msg"] for h in rows), rows)
    if name in ("stale", "length", "speed"):
        blocks = [h for h in rows if h["level"] == "block"]
        ck(name + ": camera-stale, standalone exit 1", p.returncode == 1 and blocks
           and all(h["check"] == "camera-stale" for h in blocks)
           and "camera-stale" in p.stdout, (p.returncode, rows, p.stderr))
        if name == "stale":
            offsets = [float(m.group(1)) for h in blocks
                       if (m := re.search(r"out of step by about ([\d.]+) s", h["msg"]))]
            ck("stale: second segment is 41 frames (1.37 s) late",
               bool(offsets) and all(abs(v - 41 / FPS) <= 1 / FPS for v in offsets)
               and all(1.5 <= h.get("at", -1) < 3.0 for h in blocks), rows)
        elif name == "speed":
            offsets = [float(m.group(1)) for h in blocks
                       if (m := re.search(r"out of step by about ([\d.]+) s", h["msg"]))]
            ck("speed: 42 source frames reported in output seconds",
               bool(offsets) and all(abs(v - 42 / FPS / 1.5) <= 1 / FPS for v in offsets)
               and all(1.0 <= h.get("at", -1) < 2.0 for h in blocks), rows)
    elif name == "noraw":
        ck("noraw: one lipsync-unchecked warn, standalone exit 0", p.returncode == 0
           and len(rows) == 1 and rows[0]["check"] == "lipsync-unchecked"
           and rows[0]["level"] == "warn" and "lipsync-unchecked" in p.stdout,
           (p.returncode, rows, p.stderr))
    else:
        ck(name + ": no rows, standalone exit 0", rows == [] and p.returncode == 0,
           (p.returncode, rows, p.stderr))


def main():
    cs.ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch", type=Path)
    ap.add_argument("--case", choices=CASES)
    a = ap.parse_args()
    scratch = a.scratch.resolve() / "lipsync-check"
    scratch.mkdir(parents=True, exist_ok=True)
    if not CHECK.is_file():
        ck("pre-render lipsync module exists", False, str(CHECK))
        return 1
    spec = importlib.util.spec_from_file_location("lipsync_check", CHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ck("PHASE is pre", mod.PHASE == "pre")
    raw = raw_fixture(scratch)
    for name in ([a.case] if a.case else CASES):
        try:
            check_case(scratch, name, raw, mod)
        except Exception as e:
            ck(name + ": finishes", False, str(e))
    print("lipsync check: %d failure(s)" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
