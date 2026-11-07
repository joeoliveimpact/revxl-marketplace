#!/usr/bin/env python3
"""LIGHT S9.5 proof: python review_aids_test.py <scratch> [--case NAME].

Only generated 360x640, 30 fps media, at most three seconds. Editor tools and
Python come from EDITOR_SE_HOME; all writes stay in an owned scratch subtree.
"""
import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut_safety_test as cs  # noqa: E402

CHECKS = HERE.parents[1] / "plugins/editor-superengine/skills/_shared/checks"
fails = []


def ck(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(label)


def module(name):
    spec = importlib.util.spec_from_file_location(name, CHECKS / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value) + "\n").encode("utf-8"))


def fixture(scratch, name, still=False):
    reel = scratch / name
    master = reel / "renders" / (name + " Master - 11.06.26.mp4")
    master.parent.mkdir(parents=True)
    args = [cs.rt.tool("ffmpeg"), "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i",
            "testsrc2=s=360x640:r=30:d=" + ("1" if still else "3"),
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=3"]
    if still:
        args += ["-vf", "tpad=stop_mode=clone:stop_duration=2"]
    result = cs.sh(args + ["-c:v", "libx264", "-preset", "ultrafast", "-threads", "2",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-t", "3", master])
    if result.returncode:
        raise RuntimeError(result.stderr)
    cuts = dict(fps=30, speed=1, segments=[dict(src_in_f=a, src_out_f=a+30,
                out_in_f=a, out_out_f=a+30) for a in (0, 30, 60)])
    words = [dict(word=w, start=t, end=t+.04, id=str(i))
             for i, (w, t) in enumerate((("before", .95), ("after", 1.02), ("next", 2.01)))]
    put(reel / "work/cuts.json", cuts)
    put(reel / "work/edit_map.cut.json", dict(words=words))
    put(reel / "beat-map-selection.json", dict(beats=[]))
    return dict(reel_dir=reel, fps=30, cuts=cuts, beats=[], render=master)


def case_aids(scratch):
    mod = module("review_aids")
    ctx = fixture(scratch, "aids")
    calls = []
    labels = []
    real = mod.subprocess.run

    def inspect(args, **kwargs):
        calls.append([str(a) for a in args])
        labels.extend(p.read_text(encoding="utf-8").strip()
                      for p in (ctx["reel_dir"] / "work/qa").glob(".aids-*/*-words.txt"))
        return real(args, **kwargs)

    with patch.object(mod.subprocess, "run", side_effect=inspect):
        rows = mod.run(ctx)
    ck("aids: no failures", rows == [], rows)
    index = cs.load(ctx["reel_dir"] / "work/qa/index.json")
    ck("aids: index has two strips, contact, phone", set(index) == {"strips", "contact", "phone"}
       and len(index.get("strips", [])) == 2 and index.get("contact") == "work/qa/contact.jpg"
       and index.get("phone") == "work/qa/phone-720p.mp4", index)
    files = index.get("strips", []) + [index.get("contact"), index.get("phone")]
    ck("aids: every indexed file exists and is nonempty", len(files) == 4 and all(
        f and (ctx["reel_dir"] / f).is_file() and (ctx["reel_dir"] / f).stat().st_size for f in files), index)
    filters = [c[i+1] for c in calls for i, arg in enumerate(c[:-1]) if arg in ("-vf", "-filter_complex")]
    ck("aids: contiguous five-frame number pulls", any("between(n,28,32)" in f for f in filters)
       and any("between(n,58,62)" in f for f in filters), filters)
    ck("aids: waveform uses same span", any("showwavespic" in f and "atrim=start=" in f for f in filters), filters)
    p = cs.sh([cs.rt.tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height", "-of", "json", ctx["reel_dir"] / index["phone"]])
    ck("aids: phone is 720x1280", json.loads(p.stdout)["streams"][0] == dict(width=720, height=1280), p.stderr)
    ck("aids: label times use cut words", "before after" in labels and "next" in labels, labels)
    p = cs.sh([cs.PY, "-X", "utf8", "-I", CHECKS / "review_aids.py", ctx["reel_dir"]])
    ck("aids: standalone writes aids", p.returncode == 0 and "Review aids ready" in p.stdout, p.stdout + p.stderr)
    # A broken optional piece must leave the rest available and return only one warning.
    def fail_contact(args, **kwargs):
        if str(args[-1]).endswith("contact.jpg"):
            raise OSError("planted contact failure")
        return real(args, **kwargs)
    with patch.object(mod.subprocess, "run", side_effect=fail_contact):
        rows = mod.run(ctx)
    index = cs.load(ctx["reel_dir"] / "work/qa/index.json")
    ck("aids: partial failure warns once and keeps successful pieces", len(rows) == 1
       and rows[0]["check"] == "review-aids" and rows[0]["level"] == "warn"
       and len(index.get("strips", [])) == 2 and index.get("phone") and not index.get("contact"), (rows, index))
    # A bad label must leave the successful waveform in the shipped strip.
    put(ctx["reel_dir"] / "work/edit_map.cut.json", dict(words=[dict(word="broken")]))
    rows = mod.run(ctx)
    p = cs.sh([cs.rt.tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=height", "-of", "json", ctx["reel_dir"] / "work/qa/cut-01.png"])
    ck("aids: bad labels keep waveform and warn once", len(rows) == 1 and rows[0]["level"] == "warn"
       and json.loads(p.stdout)["streams"][0]["height"] == 448, (rows, p.stdout, p.stderr))


def case_pacing(scratch):
    mod = module("pacing_check")
    ctx = fixture(scratch, "still", still=True)
    rows = mod.run(ctx)
    ck("pacing: two-second still stretch warns, never blocks", any(
        r["check"] == "dead-zone" and isinstance(r.get("at"), (int, float)) for r in rows)
       and all(r["level"] == "warn" for r in rows), rows)
    p = cs.sh([cs.PY, "-X", "utf8", "-I", CHECKS / "pacing_check.py", ctx["reel_dir"]])
    ck("pacing: standalone warnings exit zero", p.returncode == 0 and "dead-zone" in p.stdout, p.stdout + p.stderr)
    ctx = fixture(scratch, "motion")
    ck("pacing: normal motion has no warnings", (rows := mod.run(ctx)) == [], rows)
    # Exercise pixel measurement, not cuts.json: a six-frame white shot between black shots.
    flash = ctx["reel_dir"] / "renders/flash.mp4"
    p = cs.sh([cs.rt.tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
               "color=black:s=360x640:r=30:d=2,drawbox=color=white:t=fill:enable='between(n,24,29)'",
               "-c:v", "libx264", "-threads", "2", flash])
    if p.returncode:
        raise RuntimeError(p.stderr)
    ctx["render"] = flash
    rows = mod.run(ctx)
    ck("pacing: short shot between hard cuts warns", any(r["check"] == "quick-flash" for r in rows)
       and all(r["level"] == "warn" for r in rows), rows)
    ctx["beats"] = [dict(transition=dict(type="flash", at_cut_frame=27, dur_frames=4))]
    ck("pacing: declared transition exempts short shot", not any(
        r["check"] == "quick-flash" for r in mod.run(ctx)))


def case_qajson(scratch):
    ctx = fixture(scratch, "qajson")
    original = ctx["reel_dir"] / "work/renders/master-100x.mp4"
    original.parent.mkdir()
    shutil.copyfile(ctx["render"], original)
    p = cs.sh([cs.PY, "-X", "utf8", "-I", CHECKS / "check.py", ctx["reel_dir"], "--phase", "post"])
    report = cs.load(ctx["reel_dir"] / "work/qa.json")
    index = cs.load(ctx["reel_dir"] / "work/qa/index.json")
    ck("qajson: post writes review aids into qa.json", bool(index) and report.get("aids") == index, (p.stdout, p.stderr, report))
    ck("qajson: review aids module did not crash or block", not any(
        r.get("module") == "review_aids" and r["level"] == "block" for r in report.get("checks", [])), report)


CASES = dict(aids=case_aids, pacing=case_pacing, qajson=case_qajson)


def main():
    cs.ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    args = ap.parse_args()
    scratch = Path(args.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="review-aids-", dir=scratch))
    print("python %s" % cs.PY)
    for name in [args.case] if args.case else CASES:
        print("-- " + name)
        try:
            CASES[name](root)
        except Exception as exc:
            ck(name + ": completed", False, repr(exc))
    print("\n%d failed" % len(fails) if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
