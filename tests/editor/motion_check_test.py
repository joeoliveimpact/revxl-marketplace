#!/usr/bin/env python3
"""LIGHT, synthetic proof for the post-render motion check (S9.4a).

    python tests/editor/motion_check_test.py <scratch-dir> [--case NAME]

Prints PASS/FAIL per check; exit 0 only when every check passes. Media are
360x640 at 30 fps, at most 8 s, with a tone. Uses runtime tools when installed,
else PATH's ffmpeg and this Python. All generated files stay under scratch.
"""
import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SHARED = HERE.parents[1] / "plugins" / "editor-superengine" / "skills" / "_shared"
CHECK = SHARED / "checks" / "motion_check.py"
sys.path.insert(0, str(SHARED))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

FPS = 30
MASTER = "Test Master - 11.06.26.mp4"
FAILS = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  [{detail}]"), flush=True)
    if not ok:
        FAILS.append(name)


def tool(name):
    try:
        installed = rt.tool(name)
        if Path(installed).is_file():
            return installed
    except (KeyError, OSError, ValueError):
        pass
    return sys.executable if name == "python" else shutil.which(name)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=1) + "\n").encode("utf-8"))


def moving(seconds=4):
    return f"testsrc2=size=360x640:rate={FPS}:duration={seconds}"


def media(root, name, vf=None, source=None, seconds=4):
    """Overwrite only this named synthetic fixture; never recursively remove scratch."""
    if not 0 < seconds <= 8:
        raise ValueError("LIGHT fixtures must be at most 8 seconds")
    reel = root / name
    render = reel / "renders" / MASTER
    render.parent.mkdir(parents=True, exist_ok=True)
    frames = round(seconds * FPS)
    write(reel / "work" / "cuts.json", {"fps": FPS, "segments": [
        {"src_in_f": 0, "src_out_f": frames, "out_in_f": 0, "out_out_f": frames}]})
    write(reel / "beat-map-selection.json", {"fps": FPS, "beats": []})
    (reel / "work" / "qa-ok.json").unlink(missing_ok=True)
    cmd = [FFMPEG, "-hide_banner", "-v", "error", "-nostdin", "-y", "-filter_threads", "1",
           "-f", "lavfi", "-i", source or moving(seconds),
           "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={seconds}"]
    if vf:
        cmd += ["-vf", vf]
    cmd += ["-t", str(seconds), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-threads", "2", "-c:a", "aac", "-b:a", "64k", str(render)]
    p = subprocess.run(cmd, capture_output=True, env=ENV, timeout=60)
    if p.returncode:
        raise RuntimeError("fixture ffmpeg failed: " + p.stderr.decode("utf-8", "replace")[-800:])
    return reel


def check(reel, expected, render=None, beats=None):
    """Exercise run(ctx) and the actual standalone entry point for every fixture."""
    cuts = json.loads((reel / "work" / "cuts.json").read_text(encoding="utf-8"))
    if beats is None:
        beats = json.loads((reel / "beat-map-selection.json").read_text(encoding="utf-8"))["beats"]
    chosen = render or reel / "renders" / MASTER
    rows = MC.run({"reel_dir": reel, "fps": FPS, "cuts": cuts, "beats": beats, "render": chosen})
    args = [PY, "-B", "-X", "utf8", "-I", str(CHECK), str(reel)]
    if render is not None:
        args += ["--render", str(render)]
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, timeout=60)
    detail = (p.stdout + p.stderr)[-1800:]
    ck(f"{reel.name}: standalone exit {expected}", p.returncode == expected, detail)
    ck(f"{reel.name}: module contract and seek times", all(
        set(("check", "level", "msg", "where")).issubset(row)
        and row["level"] in ("block", "warn") and row["msg"] and "\n" not in row["msg"]
        and isinstance(row.get("at"), (int, float)) for row in rows), rows)
    ck(f"{reel.name}: standalone reports the same findings", all(
        row["check"] in p.stdout for row in rows) and "Traceback" not in detail, detail)
    return rows


def kinds(rows, level=None):
    return [r["check"] for r in rows if level is None or r["level"] == level]


def case_clean(root):
    reel = media(root, "clean")
    for name in ("Preview.mp4", "Other Master - 01.01.00.mp4"):
        (reel / "renders" / name).unlink(missing_ok=True)
    rows = check(reel, 0)
    ck("clean: moving footage has no findings", rows == [], rows)
    ck("clean: post-render module", MC.PHASE == "post")
    # A newer unrelated preview must not be mistaken for the Master.
    decoy = reel / "renders" / "Preview.mp4"
    decoy.write_bytes(b"not a master")
    os.utime(decoy, (2000000000, 2000000000))
    rows = MC.run({"reel_dir": reel, "fps": FPS, "beats": [], "render": None})
    ck("clean: automatic lookup ignores newer previews", rows == [], rows)
    # The newest Master is chosen by modification time, not its date or filename.
    other = reel / "renders" / "Other Master - 01.01.00.mp4"
    other.write_bytes(b"unreadable newer master")
    os.utime(other, (2000000001, 2000000001))
    rows = MC.run({"reel_dir": reel, "fps": FPS, "beats": [], "render": None})
    ck("clean: newest Master is selected and unreadable media blocks", bool(kinds(rows, "block")), rows)
    ck("clean: explicit render overrides newest Master", check(reel, 0, render=reel / "renders" / MASTER) == [])


def case_black(root):
    for count, expected in ((18, 1), (9, 0), (15, 1)):
        reel = media(root, f"black-{count}", f"drawbox=color=black:t=fill:enable='between(n,30,{29 + count})'")
        rows = check(reel, expected)
        ck(f"black-{count}: mid-reel threshold", kinds(rows, "block") == (["black-gap"] if expected else []), rows)
        if expected:
            ck(f"black-{count}: gap seeks to 1 s", any(
                r["check"] == "black-gap" and abs(r["at"] - 1) <= 1 / FPS for r in rows), rows)
    for name, enable in (("opening", "lt(n,18)"), ("ending", "gte(n,102)")):
        reel = media(root, "black-" + name, f"drawbox=color=black:t=fill:enable='{enable}'")
        rows = check(reel, 0)
        ck(f"black-{name}: not a mid-reel black gap", "black-gap" not in kinds(rows), rows)
    reel = media(root, "black-penultimate", "drawbox=color=black:t=fill:enable='between(n,101,118)'")
    rows = check(reel, 1)
    ck("black: visible final frame closes an internal gap", kinds(rows, "block") == ["black-gap"], rows)


def freeze_media(root, name, hold, start=30):
    repeats = round(hold * FPS) - 1
    return media(root, name, f"loop=loop={repeats}:size=1:start={start},setpts=N/({FPS}*TB)",
                 source=moving(2), seconds=2 + repeats / FPS)


def case_freeze(root):
    for hold, expected in ((3.5, 1), (2, 0), (3, 0)):
        reel = freeze_media(root, f"freeze-{hold}", hold)
        rows = check(reel, expected)
        ck(f"freeze-{hold}: strictly over 3 s blocks", kinds(rows, "block") == (["frozen"] if expected else []), rows)
        if expected:
            ck("freeze: coach can OK it and seek to its start", any(
                r["check"] == "frozen" and abs(r["at"] - 1) <= 1 / FPS
                and "hub review notes" in r["msg"] and "Claude" in r["msg"] for r in rows), rows)
    # A freeze still continuing at EOF has no freeze_end in ffmpeg's log.
    reel = media(root, "freeze-tail", "tpad=stop_mode=clone:stop_duration=3.5", source=moving(1), seconds=4.5)
    rows = check(reel, 1)
    ck("freeze: detects an unfinished freeze at EOF", kinds(rows, "block") == ["frozen"], rows)


def case_freeze_ok(root):
    reel = freeze_media(root, "freeze-ok", 3.5)
    for allowed_at, expected in ((2, 0), (2.2, 1)):
        write(reel / "work" / "qa-ok.json", {"allow": [{"check": "frozen", "at": allowed_at}]})
        rows = check(reel, expected)
        want = "frozen" if expected else "frozen-ok"
        ck(f"freeze-ok at {allowed_at}: approval must be within 1 s", kinds(rows) == [want]
           and rows[0]["level"] == ("block" if expected else "warn"), rows)


def case_plain0(root):
    reel = media(root, "plain0", "drawbox=color=blue:t=fill:enable='eq(n,0)'")
    rows = check(reel, 0)
    ck("plain0: suggestion only, never a block", kinds(rows) == ["first-frame-plain"]
       and kinds(rows, "block") == [] and rows[0]["at"] == 0, rows)


def case_pop(root):
    for colour in ("white", "black", "magenta"):
        reel = media(root, "pop-" + colour, f"drawbox=color={colour}:t=fill:enable='eq(n,60)'")
        rows = check(reel, 1)
        ck(f"pop-{colour}: single odd frame blocks at 2 s", kinds(rows, "block") == ["pop"]
           and abs(rows[0]["at"] - 2) <= 1 / FPS, rows)


def case_pop_exempt(root):
    reel = media(root, "pop-exempt", "drawbox=color=white:t=fill:enable='eq(n,60)'")
    transition = {"type": "flash", "at_cut_frame": 60, "dur_frames": 2}
    beats = [{"id": "b1", "transition": transition}]
    write(reel / "beat-map-selection.json", {"fps": FPS, "beats": beats})
    rows = check(reel, 0)
    ck("pop-exempt: declared transition window skips pop", "pop" not in kinds(rows), rows)
    rows = MC.run({"reel_dir": reel, "fps": FPS, "render": reel / "renders" / MASTER, "beats": []})
    ck("pop-exempt: run(ctx) uses supplied beats rather than disk", kinds(rows, "block") == ["pop"], rows)
    # Two declarations for one cut do not widen the first window.
    beats = [{"id": "b1", "transition": dict(transition, dur_frames=0)},
             {"id": "b2", "transition": dict(transition, dur_frames=4)}]
    reel = media(root, "pop-duplicate", "drawbox=color=white:t=fill:enable='eq(n,62)'")
    write(reel / "beat-map-selection.json", {"fps": FPS, "beats": beats})
    rows = check(reel, 1)
    ck("pop-exempt: a second transition at the same cut adds no exemption", kinds(rows, "block") == ["pop"], rows)
    # Windows include both boundary frames.
    beats = [{"transition": transition}]
    write(reel / "beat-map-selection.json", {"fps": FPS, "beats": beats})
    rows = check(reel, 0)
    ck("pop-exempt: inclusive end of window", "pop" not in kinds(rows), rows)
    write(reel / "beat-map-selection.json", {"fps": FPS, "beats": [
        {"transition": dict(transition, at_cut_frame=64)}]})
    rows = check(reel, 0)
    ck("pop-exempt: inclusive start of window", "pop" not in kinds(rows), rows)


def case_cut(root):
    source = (moving(2) + "[a];testsrc=size=360x640:rate=30:duration=2,format=yuv420p[b];"
              "[a][b]concat=n=2:v=1:a=0")
    reel = media(root, "cut", source=source)
    rows = check(reel, 0)
    ck("cut: two moving patterns with a hard cut have no pop", "pop" not in kinds(rows), rows)


CASES = {"clean": case_clean, "black": case_black, "freeze": case_freeze, "freeze-ok": case_freeze_ok,
         "plain0": case_plain0, "pop": case_pop, "pop-exempt": case_pop_exempt, "cut": case_cut}


def main():
    global ENV, FFMPEG, PY, MC
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    args = ap.parse_args()
    root = Path(args.scratch).resolve() / "motion-check"
    root.mkdir(parents=True, exist_ok=True)
    ENV, FFMPEG, PY = rt.python_env(), tool("ffmpeg"), tool("python")
    if not FFMPEG:
        ck("ffmpeg is available", False, "Install the editor tools or put ffmpeg on PATH.")
        return 1
    try:
        spec = importlib.util.spec_from_file_location("motion_check", CHECK)
        MC = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(MC)
    except (OSError, ImportError) as exc:
        ck("motion check module loads", False, exc)
        return 1
    print(f"python {PY}\nffmpeg {FFMPEG}", flush=True)
    for name in [args.case] if args.case else CASES:
        print("-- " + name, flush=True)
        try:
            CASES[name](root)
        except Exception as exc:
            ck(name, False, f"{type(exc).__name__}: {exc}")
    print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
