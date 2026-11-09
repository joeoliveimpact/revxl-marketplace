#!/usr/bin/env python3
"""S9.3: check a tiny finished Master against its cut and original audio.

Usage: python tests/editor/render_check_test.py <scratch-dir> [--case NAME]
Print PASS/FAIL lines; exit 0 only when every selected case passes.
All media are synthetic testsrc2 360x640 at 30 fps (25 for the fps case) with AAC sine audio,
at most three seconds long. No camera files, browser or heavy imports.
"""
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / "plugins/editor-superengine/skills/_shared"
CHECK = SHARED / "checks/render_check.py"
sys.path.insert(0, str(SHARED))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

CASES = ("clean", "frames", "sound", "nosrc", "soft", "norender",
         "streams", "av-length", "fps", "two-audio")


def tool(name):
    try:
        found = rt.tool(name)
        if Path(found).is_file():
            return found
    except (KeyError, OSError, ValueError):
        pass
    found = shutil.which(name)
    if not found:
        raise RuntimeError("%s is unavailable; run the editor setup first" % name)
    return found


def sh(args):
    return subprocess.run([str(a) for a in args], env=rt.python_env(),
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=120)


def ff(*args):
    p = sh([tool("ffmpeg"), "-nostdin", "-y", "-v", "error", *args])
    if p.returncode:
        raise RuntimeError("fixture creation failed: " + " ".join(p.stderr.splitlines())[-800:])


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, indent=1) + "\n").encode("utf-8"))


def fixture(root, name):
    # A unique subfolder makes reruns safe without deleting a caller's files.
    reel = Path(tempfile.mkdtemp(prefix=name + "-", dir=root))
    duration = 2
    total = 90 if name == "frames" else 60
    write(reel / "work/cuts.json", dict(fps=30, speed=1.0, segments=[dict(
        src_in_f=0, src_out_f=total, out_in_f=0, out_out_f=total)]))
    if name == "norender":
        return reel, None
    source = reel / "work/renders/master-100x.mp4"
    source.parent.mkdir(parents=True)
    rate = 25 if name == "fps" else 30
    if name == "fps":
        total = 50  # Isolate the rate block from the frame-count block.
        write(reel / "work/cuts.json", dict(fps=30, speed=1.0, segments=[dict(
            src_in_f=0, src_out_f=total, out_in_f=0, out_out_f=total)]))
    ff("-f", "lavfi", "-i", f"testsrc2=size=360x640:rate={rate}:duration={duration}",
       "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={duration + (name == 'av-length')}",
       *(["-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000:duration=2",
          "-map", "0:v:0", "-map", "1:a:0", "-map", "2:a:0"] if name == "two-audio" else []),
       "-c:v", "libx264", "-preset", "ultrafast",
       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", source)
    render = reel / "renders/Test Master - 11.06.26.mp4"
    render.parent.mkdir()
    ff("-i", source, "-map", "0:v:0",
       *([] if name == "streams" else ["-map", "0:a:0"]), "-c:v", "copy",
       "-c:a", "aac" if name == "sound" else "copy",
       *(["-b:a", "32k"] if name == "sound" else []), render)
    if name == "nosrc":
        source.unlink()
    if name == "soft":
        write(reel / "work/scale_track.json", dict(
            schema=1, fps="30/1", total_f=60,
            keys=[dict(f=0, scale=1.0), dict(f=30, scale=1.2)], tweens=[],
            warnings=["softness: beat B01 reaches 1.2"]))
        write(reel / "beat-map-selection.json", dict(beats=[dict(id="B01", start_f=30)]))
    return reel, render


def check_case(module, root, name, python):
    """Catch missing checks, wrong severity, duplicate warnings and wrong CLI exit codes."""
    reel, render = fixture(root, name)
    cuts = json.loads((reel / "work/cuts.json").read_text(encoding="utf-8"))
    hits = module.run(dict(reel_dir=reel, fps=30, cuts=cuts, beats=[], render=render))
    for h in hits:
        assert {"check", "level", "msg", "where"} <= h.keys(), h
        assert h["level"] in ("block", "warn"), h
        assert h["msg"] and len(h["msg"].splitlines()) == 1, h
    blocks = [h["check"] for h in hits if h["level"] == "block"]
    warns = [h["check"] for h in hits if h["level"] == "warn"]
    if name in ("clean", "nosrc", "soft", "two-audio"):
        assert not blocks, hits
    if name in ("clean", "sound", "frames", "norender", "streams", "av-length", "fps", "two-audio"):
        assert not warns, hits
    if name in ("clean", "two-audio"):
        assert hits == [], hits
    elif name == "frames":
        assert blocks == ["frame-count"], hits
        msg = next(h["msg"] for h in hits if h["check"] == "frame-count")
        assert "60" in msg and "90" in msg, msg
    elif name == "sound":
        assert blocks == ["sound-changed"], hits
    elif name == "nosrc":
        assert warns == ["sound-unchecked"], hits
    elif name == "soft":
        assert warns == ["soft"], hits
        assert hits[0].get("at") == 1.0, hits
    elif name == "norender":
        assert blocks == ["no-render"] and len(hits) == 1, hits
    elif name in ("streams", "av-length", "fps"):
        assert blocks == [name], hits
    expected = 1 if blocks else 0
    p = sh([python, "-X", "utf8", "-I", CHECK, reel])
    assert p.returncode == expected, (p.returncode, p.stdout, p.stderr)
    for h in hits:
        assert h["check"] in p.stdout, (h, p.stdout)
    if render is not None:
        p = sh([python, "-X", "utf8", "-I", CHECK, reel, "--render", render])
        assert p.returncode == expected, (p.returncode, p.stdout, p.stderr)


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=CASES)
    a = ap.parse_args()
    root = Path(a.scratch).resolve()
    root.mkdir(parents=True, exist_ok=True)
    try:
        python = rt.tool("python")
        if not Path(python).is_file():
            python = sys.executable
        spec = importlib.util.spec_from_file_location("render_check", CHECK)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.PHASE == "post", "render_check must run after rendering"
    except Exception as e:
        print("FAIL setup  [%s]" % " ".join(str(e).splitlines()))
        return 1
    failed = 0
    for name in [a.case] if a.case else CASES:
        try:
            check_case(module, root, name, python)
            print("PASS " + name)
        except Exception as e:
            failed += 1
            print("FAIL %s  [%s]" % (name, " ".join(str(e).splitlines())))
    print("\n%d failed" % failed if failed else "\nall passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
