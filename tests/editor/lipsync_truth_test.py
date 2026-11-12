#!/usr/bin/env python3
"""Picture-match truth matrix: real first-cut renders, then four-frame mutants.

usage: python -X utf8 -I tests/editor/lipsync_truth_test.py <scratch-dir>
       [--rates 25,24000/1001,30000/1001,50] [--speeds 1.0,1.10,1.15]
       [--plugin <checker plugin root>]

Fixtures reuse diagnose.py's moving picture plus binary frame identity, with
48 kHz sound. The checkout's build_graph + encode produce tiny 320px renders
with the null picture filter; --plugin selects only the checker under test so
the same known renders can disprove another tree's matcher. Nothing is played.
"""
import argparse
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PLUGIN = REPO / "plugins/editor-superengine"
RATES = "25,24000/1001,30000/1001,50"
SPEEDS = "1.0,1.10,1.15"
PIECES = [[0.30, 1.80], [2.35, 3.90], [4.40, 6.10], [6.35, 7.90]]
FPS = 30.0


def load(path, name):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write(path, obj):
    path.write_bytes((json.dumps(obj, indent=1) + "\n").encode("utf-8"))


def source(render, folder, rate, bf):
    path = folder / ("source-%s-b%d.mp4" % (rate.replace("/", "_"), bf))
    counter = ",".join(
        "drawbox=x=%d:y=12:w=28:h=80:color=white:t=fill:enable='bitand(n,%d)'"
        % (12 + bit * 37, 1 << bit) for bit in range(8))
    import subprocess
    p = subprocess.run([str(c) for c in [
        render.FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i",
        "testsrc2=size=320x568:rate=%s:duration=8," % rate + counter,
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=8",
        "-c:v", "libx264", "-preset", "medium" if bf else "veryfast", "-bf", bf,
        "-crf", 16, "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", path]],
        capture_output=True, timeout=60)
    if p.returncode:
        raise RuntimeError(p.stderr.decode("utf-8", "replace")[-1500:])
    return path


def assess(check, reel):
    """Observe real match results without changing the matching or its thresholds."""
    measured = []
    original = check.match

    def record(*args):
        result = original(*args)
        measured.append(result)
        return result

    check.match = record
    try:
        rows = check.run(dict(reel_dir=reel))
    finally:
        check.match = original
    return rows, measured


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch", type=Path)
    ap.add_argument("--plugin", type=Path, default=PLUGIN)
    ap.add_argument("--rates", default=RATES)
    ap.add_argument("--speeds", default=SPEEDS)
    a = ap.parse_args()
    scratch = a.scratch.resolve()
    folder = scratch / "lipsync-truth"
    folder.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(PLUGIN / "skills/_shared"))
    render = load(PLUGIN / "skills/reel-first-cuts/scripts/render.py", "truth_render")
    gaps = load(PLUGIN / "skills/reel-first-cuts/scripts/gaps.py", "truth_gaps")
    check = load(a.plugin.resolve() / "skills/_shared/checks/lipsync_check.py", "truth_check")
    render.find_tools()
    started, passed, failed, correct = time.monotonic(), 0, 0, []
    print("checker %s" % a.plugin.resolve(), flush=True)

    def verdict(name, bad):
        nonlocal passed, failed
        print(("FAIL " if bad else "PASS ") + name + ("  [%s]" % bad if bad else ""), flush=True)
        failed += bool(bad)
        passed += not bool(bad)

    for rate in a.rates.split(","):
        for bf in ([3, 0] if rate == "25" else [0]):
            raw = source(render, folder, rate, bf)
            for speed in map(float, a.speeds.split(",")):
                name = "%s fps b%d %.2fx" % (rate, bf, speed)
                reel = folder / ("%s-b%d-%.2f" % (rate.replace("/", "_"), bf, speed))
                work = reel / "work"
                (work / "renders").mkdir(parents=True, exist_ok=True)
                cuts = gaps.snap_cuts(PIECES, FPS, speed)
                write(work / "cuts.json", cuts)
                write(work / "probe.json", dict(input=str(raw), video=dict(width=320, height=568)))
                out = work / "renders" / ("master-%s.mp4" % ("%.2fx" % speed).replace(".", ""))
                graph = work / "graph.txt"
                graph.write_bytes(render.build_graph(cuts, 48000, "null").encode("utf-8"))
                render.encode(raw, graph, out, FPS, "-fps_mode", 18, "veryfast", 30, "64k")
                # Explicit times make freshness assertions independent of filesystem granularity.
                stamp = time.time() - 10
                os.utime(work / "cuts.json", (stamp, stamp))
                os.utime(out, (stamp + 2, stamp + 2))
                rows, measured = assess(check, reel)
                results = [m for m in measured if m is not None]
                correct.extend(results)
                bad = ""
                if rows or not measured or len(results) != len(measured):
                    bad = "rows=%s; compared %d/%d" % (rows, len(results), len(measured))
                noisy = [m for m in results if m[0] != 0 and m[1] >= check.MIN_GAIN]
                verdict(name + " correct", bad or ("non-zero lag above threshold: %s" % noisy if noisy else ""))
                if noisy:
                    print("STOP: correct render produced an above-threshold non-zero lag; no tuning permitted.")
                    return 1
                # Prepend four output pictures; the audio graph stays exactly the same.
                count = cuts["segments"][-1]["out_out_f"]
                vf = "tpad=start_mode=clone:start=4,trim=end_frame=%d" % count
                graph.write_bytes(render.build_graph(cuts, 48000, vf).encode("utf-8"))
                render.encode(raw, graph, out, FPS, "-fps_mode", 18, "veryfast", 30, "64k")
                os.utime(out, (stamp + 2, stamp + 2))
                for older in (False, True):
                    if older:
                        os.utime(work / "cuts.json", (stamp + 4, stamp + 4))
                    rows, measured = assess(check, reel)
                    blocks = [r for r in rows if r["level"] == "block"]
                    offsets = [m for m in measured if m is not None and abs(m[0]) > 1 and m[1] >= check.MIN_GAIN]
                    bad = ""
                    if not blocks or not offsets:
                        bad = "four-frame picture shift escaped: %s; %s" % (rows, measured)
                    elif not all(abs(abs(lag) / speed - 4) <= 1 for lag, gain in offsets):
                        bad = "wrong measured output offset: %s" % offsets
                    elif not all("%.2f s" % r["at"] in r["msg"] and "behind the voice" in r["msg"]
                                 and (m := re.search(r"picture is about ([\d.]+) s", r["msg"]))
                                 and abs(float(m[1]) - 4 / FPS) <= 1 / FPS for r in blocks):
                        bad = "missing measured offset/time: %s" % blocks
                    elif not older and any("older than your latest cut" in r["msg"].lower() for r in rows):
                        bad = "claimed older without mtime evidence"
                    verdict(name + (" really older" if older else " mutant"), bad)
    worst = max(correct, key=lambda m: (abs(m[0]), m[1]), default=(0, 0.0))
    print("truth: %d passed, %d failed; worst correct lag=%d gain=%.6f; %.1f s" %
          (passed, failed, worst[0], worst[1], time.monotonic() - started), flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
