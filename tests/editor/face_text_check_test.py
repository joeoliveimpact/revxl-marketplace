#!/usr/bin/env python3
"""Tiny, real-media proofs for the post-render face and caption contrast check.

Usage: python tests/editor/face_text_check_test.py <scratch-dir> [--case NAME]
All jobs are 360x640, 30 fps, two seconds. Tools and child Python come from
EDITOR_SE_HOME. Fixtures live only under the supplied scratch folder.
Removing either detector, comparing the wrong frame, ignoring layout/zoom,
or treating missing face data as a block must fail these proofs.
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parents[1] / "plugins/editor-superengine/skills"
sys.path.insert(0, str(SKILLS / "_shared"))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

CHECK = SKILLS / "_shared/checks/face_text_check.py"
FPS, TOTAL = 30, 60
CASES = ("synthetic", "clean", "face", "contrast", "noface", "nocaps", "many", "w2e")
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  [{detail}]"))
    if not ok:
        fails.append(name)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value) + "\n").encode("utf-8"))


def ff(*args):
    p = subprocess.run([rt.tool("ffmpeg"), "-nostdin", "-y", "-v", "error", *map(str, args)],
                       capture_output=True, env=rt.python_env(), timeout=60)
    if p.returncode:
        raise ValueError(p.stderr.decode("utf-8", errors="replace")[-1200:])


def fixture(scratch, name, zoom=False, split=False):
    reel = scratch / ("face-text-" + name + ("-zoom" if zoom else "") + ("-split" if split else ""))
    (reel / "work/renders").mkdir(parents=True, exist_ok=True)
    (reel / "renders").mkdir(exist_ok=True)
    layout = "split" if split else "full"
    beat = dict(id="b1", start_f=0, end_f=TOTAL, layout=layout, value=None,
                speech_anchor=dict(text="", w0=0, w1=0), scene=None, broll=None, transition=None)
    write(reel / "beat-map-selection.json", dict(fps=FPS, beats=[beat]))
    write(reel / "work/cuts.json", dict(fps=FPS, speed=1.0, segments=[
        dict(src_in_f=0, src_out_f=TOTAL, out_in_f=0, out_out_f=TOTAL)]))
    write(reel / "work/scale_track.json", dict(fps=FPS, total_f=TOTAL,
          style=dict(style="punch-in"), keys=[dict(f=0, scale=1.2 if zoom else 1,
          ox=0.5, oy=0.5, layout=layout)], tweens=[]))
    anchors = reel / "work/anchors.json"
    write(anchors, dict(segments=[dict(seg=0, samples=[
        dict(f=0, x=0.5, y=0.3, box=[0.35, 0.18, 0.65, 0.42])])]))
    if name == "noface":
        anchors.unlink()
    # Caption boxes use master-pixel corners, independently of the media size.
    x, y, w, h = (90, 145, 180, 80) if name == "face" else (60, 460, 240, 100)
    if split:
        y = 340 if name == "face" else 60
    caps = reel / "work/captions.json"
    write(caps, dict(schema=1, style=dict(style="clean"), declared_drops=[], notes=[], chunks=[
        dict(i=0, w0=0, w1=0, start_f=30, end_f=60, text="TEST", words=[],
             box=[x * 3, y * 3, (x + w) * 3, (y + h) * 3])]))
    if name == "many":
        # Twelve distinct midpoints: the tenth is frame 47 (zero-based chunk 9).
        write(caps, dict(schema=1, style=dict(style="clean"), declared_drops=[], notes=[], chunks=[
            dict(i=i, w0=0, w1=0, start_f=i * 5, end_f=(i + 1) * 5, text="TEST", words=[],
                 box=[x * 3, y * 3, (x + w) * 3, (y + h) * 3]) for i in range(12)]))
    if name == "nocaps":
        caps.unlink()
    aroll = reel / "work/renders/master-test.mp4"
    # Moving pixels inside the measured head expose accidental time/frame mismatches.
    ff("-f", "lavfi", "-i", "testsrc2=size=360x640:rate=30", "-frames:v", TOTAL,
       "-c:v", "libx264", "-preset", "ultrafast", "-crf", "16", "-pix_fmt", "yuv420p", aroll)
    master = reel / "renders/Test Master - 11.06.26.mp4"
    filters = ["scale=432:768,crop=360:640:36:64"] if zoom else []
    if split:
        # The split layout cover-fits the source in the bottom 360x320 box.
        filters.append("crop=360:320:0:160,pad=360:640:0:320:color=0x0a0c12")
    if name != "nocaps":
        # A dark plate and bright rectangular glyph strokes; no machine font dependency.
        # Only frame 45 is planted in the face case: the checker must pull by number.
        enabled = (":enable='eq(n,45)'" if name == "face" else
                   "" if name == "many" else ":enable='between(n,30,59)'")
        color = "white"
        background = "white" if name == "contrast" else "0x282828"
        filters.append(f"drawbox=x={x}:y={y}:w={w}:h={h}:color={background}:t=fill{enabled}")
        for left in (x + 20, x + 70, x + 120):
            if name == "contrast":
                filters.append(f"drawbox=x={left - 5}:y={y + 20}:w=40:h=40:color=black:t=fill{enabled}")
            filters.append(f"drawbox=x={left}:y={y + 25}:w=30:h=30:color={color}:t=fill{enabled}")
    if name == "many":
        filters.append("drawbox=x=90:y=145:w=180:h=80:color=black:t=fill:enable='eq(n,47)'")
    ff("-i", aroll, "-vf", ",".join(filters) if filters else "null", "-frames:v", TOTAL,
       "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", master)
    return reel, master


def check(reel, master, explicit=False, count_pulls=False):
    spec = importlib.util.spec_from_file_location("face_text_check", CHECK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ck("module: post-render contract", module.PHASE == "post")
    pulls, real_run = [], subprocess.run

    def spy(cmd, *args, **kwargs):
        if Path(cmd[0]).stem.lower() == "ffmpeg" and "rawvideo" in cmd:
            pulls.append(cmd)
        return real_run(cmd, *args, **kwargs)

    if count_pulls:
        module.subprocess.run = spy
    try:
        rows = module.run(dict(reel_dir=reel, fps=FPS, cuts=None, beats=None,
                               render=master if explicit else None))
    finally:
        module.subprocess.run = real_run
    if count_pulls:
        ck("many: at most two ffmpeg frame pulls", 0 < len(pulls) <= 2, len(pulls))
    py = rt.tool("python")
    p = subprocess.run([py, "-X", "utf8", "-I", str(CHECK), str(reel)] +
                       (["--render", str(master)] if explicit else []),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=rt.python_env(), timeout=120)
    print(p.stdout.rstrip())
    ck("rows: user messages and locations", all(
        {"check", "level", "msg", "where"} <= set(r) and r["level"] in ("warn", "block")
        and r["where"] and r["msg"] and "\n" not in r["msg"] for r in rows), rows)
    return rows, p


def synthetic(scratch):
    spec = importlib.util.spec_from_file_location("face_text_synthetic", CHECK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reel = scratch / "synthetic"
    master = reel / "renders/Synthetic Master - test.mp4"
    master.parent.mkdir(parents=True, exist_ok=True)
    master.touch()
    caps = dict(style=dict(style="bold-pop", accent="#FFD84D"), chunks=[dict(
        start_f=30, end_f=60, box=[0, 0, 1080, 1920], words=[],
        text="STEP TWO, THEN JUST TELL HIM TO CONNECT")])  # long enough to span the whole band

    def picture(background, plate=False):
        data = bytearray([background] * (100 * 100 * 3))
        def rect(x0, y0, x1, y1, value):
            for y in range(y0, y1):
                for x in range(x0, x1):
                    data[(y * 100 + x) * 3:(y * 100 + x) * 3 + 3] = bytes([value] * 3)
        if plate:
            rect(0, 0, 100, 100, 40)
        for x in (10, 40, 70):
            rect(x, 20, x + 20, 80, 0)  # black stroke covers more than 10% of the box
            rect(x + 4, 25, x + 16, 75, 255)
        return data

    def findings(data):
        write(reel / "work/captions.json", caps)
        with patch.object(module, "dimensions", return_value=(100, 100, "30", 2)), \
                patch.object(module, "frames", return_value={45: data}):
            return [r for r in module.run(dict(reel_dir=reel, render=master, cuts={}))
                    if r["check"] == "low-contrast"]

    rows = findings(picture(255))
    ck("white text with black stroke on white blocks with time and fix",
       len(rows) == 1 and rows[0]["level"] == "block" and rows[0]["at"] == 1.5
       and "1.50 seconds" in rows[0]["msg"] and "Boxed" in rows[0]["msg"], rows)
    ck("white text on dark stays readable", findings(picture(20)) == [])
    ck("white text over a dark plate stays readable", findings(picture(255, plate=True)) == [])
    caps["style"]["accent"] = "#101010"
    caps["chunks"][0]["words"] = [dict(mark="emph")]
    ck("dark marked accent is checked too", len(findings(picture(20))) == 1)
    caps["style"]["mark_look"] = "marker"
    ck("marker keeps the white fill", findings(picture(20)) == [])
    # A short caption's plate covers only the middle of its band; the empty band around it is not behind the words.
    caps["style"].update(mark_look="accent", accent="#FFD84D")
    caps["chunks"][0].update(text="HIM,", words=[])
    narrow = bytearray([255] * (100 * 100 * 3))
    for y in range(100):
        for x in range(35, 65):
            value = 255 if 45 <= x < 55 and 40 <= y < 60 else 40
            narrow[(y * 100 + x) * 3:(y * 100 + x) * 3 + 3] = bytes([value] * 3)
    ck("a short caption on its own dark plate over a white page stays readable", findings(narrow) == [])
    caps["font"] = dict(family="Inter", weight=100, style="italic")
    with patch.object(module, "drawn", wraps=module.drawn) as measured:
        findings(narrow)
    ck("contrast measures with the document's saved brand font",
       measured.call_args.args[3:] == (caps["font"],), measured.call_args)
    caps["style"]["style"] = "none"
    ck("captions off skips contrast", findings(picture(255)) == [])


def real_w2e():
    value = os.environ.get("EDITOR_SE_TEST_REEL_W2E")
    if not value:
        print("SKIP W2e real-frame regression: EDITOR_SE_TEST_REEL_W2E is unset")
        return
    reel = Path(value)
    spec = importlib.util.spec_from_file_location("face_text_w2e", CHECK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    masters = sorted(reel.glob("renders/* Master - *.mp4"), key=lambda m: m.stat().st_mtime_ns)
    if not masters:
        ck("W2e: the reel has a rendered Master", False, reel)
        return
    rows = module.run(dict(reel_dir=reel, render=masters[-1]))
    blocks = [r for r in rows if r["level"] == "block"]
    ck("W2e: exactly the three unreadable captions block",
       [(r["check"], round(r.get("at", -1), 2)) for r in blocks] ==
       [("low-contrast", 30.83), ("low-contrast", 31.57), ("low-contrast", 32.03)], blocks)


def case(scratch, name):
    if name == "synthetic":
        return synthetic(scratch)
    if name == "w2e":
        return real_w2e()
    reel, master = fixture(scratch, name)
    rows, p = check(reel, master, explicit=name == "contrast", count_pulls=name == "many")
    blocks = [r for r in rows if r["level"] == "block"]
    expected = {"face": "face-covered", "contrast": "low-contrast", "many": "face-covered"}.get(name)
    if expected:
        ck(f"{name}: planted defect blocks with its seek time",
           [r["check"] for r in blocks] == [expected]
           and blocks[0].get("at") == (47 / FPS if name == "many" else 1.5), rows)
        ck(f"{name}: standalone exits 1", p.returncode == 1, (p.returncode, p.stderr))
    else:
        ck(f"{name}: no blocks and standalone exits 0", not blocks and p.returncode == 0,
           (rows, p.returncode, p.stderr))
        ck(f"{name}: only the expected warnings", [r["check"] for r in rows] ==
           (["face-unchecked"] if name == "noface" else []), rows)
    if name == "clean":
        reel, master = fixture(scratch, name, zoom=True)
        rows, p = check(reel, master, explicit=True)
        ck("clean: zoomed moving a-roll stays clean", rows == [] and p.returncode == 0, rows)
        reel, master = fixture(scratch, name, split=True)
        rows, p = check(reel, master, explicit=True)
        ck("clean: split cover-fit stays clean", rows == [] and p.returncode == 0, rows)
    if name == "face":
        reel, master = fixture(scratch, name, split=True)
        rows, p = check(reel, master, explicit=True)
        ck("face: split layout overlay blocks", [r["check"] for r in rows] ==
           ["face-covered"] and p.returncode == 1, rows)
        track_path = reel / "work/scale_track.json"
        track = json.loads(track_path.read_text(encoding="utf-8"))
        track["tweens"] = [dict(start_f=30, end_f=60, prop="scale", **{"from": 1, "to": 1.2})]
        write(track_path, track)
        rows, p = check(reel, master, explicit=True)
        ck("face: ambiguous moving envelope is skipped", rows == [] and p.returncode == 0, rows)
    if name == "contrast":
        (reel / "work/anchors.json").unlink()
        rows, p = check(reel, master)
        ck("contrast: missing face data still checks text", sorted(r["check"] for r in rows) ==
           ["face-unchecked", "low-contrast"] and p.returncode == 1, rows)
    if name == "noface":
        # Missing a-roll must also produce one warning, while contrast still runs.
        (reel / "work/renders/master-test.mp4").unlink()
        rows, p = check(reel, master)
        ck("noface: missing both inputs warns once", [r["check"] for r in rows] ==
           ["face-unchecked"] and p.returncode == 0, rows)
    if name == "nocaps":
        ck("nocaps: no low-contrast rows", not any(r["check"] == "low-contrast" for r in rows), rows)
        # With no captions the beat midpoint is frame 30. Plant only there.
        ff("-i", master, "-vf", "drawbox=x=90:y=145:w=180:h=80:color=black:t=fill:enable='eq(n,30)'",
           "-c:v", "libx264", "-preset", "ultrafast", reel / "renders/Beat overlay.mp4")
        rows, p = check(reel, reel / "renders/Beat overlay.mp4", explicit=True)
        ck("nocaps: beat midpoint still catches a face overlay", [r["check"] for r in rows] ==
           ["face-covered"] and rows[0].get("at") == 1.0 and p.returncode == 1, rows)


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch", type=Path)
    ap.add_argument("--case", choices=CASES)
    args = ap.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    for name in (args.case,) if args.case else CASES:
        try:
            case(args.scratch.resolve(), name)
        except Exception as exc:
            ck(name, False, f"{type(exc).__name__}: {exc}")
    print(f"\n{len(fails)} failed" if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
