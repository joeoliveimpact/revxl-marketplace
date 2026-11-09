#!/usr/bin/env python3
"""FX1: warn when one default read repeats another line's default read.

usage: python tests/editor/fx1_board_warn_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 only when no checks fail.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
P = REPO / "plugins/editor-superengine"
S = P / "skills/reel-first-cuts/scripts"
WALK1 = os.environ.get("EDITOR_SE_TEST_REEL_W1", "")
WALK1 = Path(WALK1) if WALK1 else None
sys.path.insert(0, str(P / "skills/_shared"))
sys.path.insert(0, str(S))
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def synthetic(scratch):
    from make_board import repeat_warns
    ck("synthetic: L02 inside L01", repeat_warns([
        ("L01", ["so", "you", "can", "now", "connect", "with", "me"]),
        ("L02", ["you", "can", "now", "connect"])]) == {"L02": "L01"})
    ck("synthetic: two-word containment alone does not warn", repeat_warns([
        ("L01", ["so", "you", "can", "connect"]), ("L02", []), ("L03", ["you", "can"])]) == {})
    ck("synthetic: L17 in the tail of L16", repeat_warns([
        ("L16", ["get", "the", "freebie", "drop", "killed", "in", "the", "comments"]),
        ("L17", ["drop", "killed", "in", "the", "comments"])]) == {"L17": "L16"})
    ck("synthetic: separated words are not a contiguous repeat", repeat_warns([
        ("L01", ["you", "can", "also", "now", "connect"]),
        ("L02", ["you", "can", "now", "connect"])]) == {})
    ck("synthetic: a line does not warn about itself", repeat_warns([
        ("L01", ["you", "can", "connect"])]) == {})
    earlier = "so it's time for me to go write some scripts drop killed in the comments".split()
    later = "drop kill in the comments get those prompts baby".split()
    ck("synthetic: neighboring near-repeat warns on L17", repeat_warns([
        ("L16", earlier), ("L17", later)]) == {"L17": "L16"})
    ck("synthetic: a line without a default breaks neighboring repeat checks", repeat_warns([
        ("L16", earlier), ("Lgap", []), ("L17", later)]) == {})
    ck("synthetic: containment keeps its first warning", repeat_warns([
        ("L01", later + ["now"]), ("L16", earlier), ("L17", later)]) == {"L17": "L01"})


def walk1(scratch):
    if WALK1 is None or not WALK1.is_dir():
        print("SKIP real-walk1: set EDITOR_SE_TEST_REEL_W1 to the S17 walk-1 reel folder to run this case")
        return
    d = Path(tempfile.mkdtemp(prefix="fx1-board-warn-walk1-", dir=scratch))
    for name in ("script.md", "shots.json", "work/edit_map.json", "work/tx.16k.wav",
                 "work/probe.json", "work/envelope.json"):
        dest = d / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(WALK1 / name, dest)
    p = subprocess.run([sys.executable, "-X", "utf8", "-I", str(S / "make_board.py"),
                        "--script", "script.md", "--take", "1:work/edit_map.json:work/tx.16k.wav",
                        "--shots", "shots.json", "--reel", WALK1.name, "-o", str(d)], cwd=d,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    ck("real-walk1: board rebuild", p.returncode == 0, p.stdout + p.stderr)
    if p.returncode:
        return
    cfg = json.loads((d / "cut-board.config.json").read_text(encoding="utf-8"))
    lines = {ln["id"]: ln for ln in cfg["lines"]}
    ck("real-walk1: L02 warns that L01 already says this", "Line L01 already says this;" in
       lines["L02"].get("warn", ""), lines["L02"].get("warn"))
    ck("real-walk1: L17 warns that L16 already says this", "Line L16 already says this;" in
       lines["L17"].get("warn", ""), lines["L17"].get("warn"))
    from build_edit_map import board_hash
    original_hash = cfg["board_hash"]
    for ln in cfg["lines"]:
        ln.pop("warn", None)
    ck("real-walk1: warnings do not affect the ruling hash", board_hash(cfg) == original_hash)


CASES = {"synthetic": synthetic, "real-walk1": walk1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=sorted(CASES))
    a = ap.parse_args()
    scratch = Path(a.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    for name, fn in CASES.items():
        if a.case in (None, name):
            try:
                fn(scratch)
            except Exception as e:
                ck(name, False, repr(e))
    print("\n%d failed" % len(fails) if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
