#!/usr/bin/env python3
"""FX1 A: calibrated boundary gate and concrete recovery instructions.

usage: python tests/editor/fx1_audit_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 only when no checks fail.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
S = REPO / "plugins/editor-superengine/skills/reel-first-cuts/scripts"
WALK = os.environ.get("EDITOR_SE_TEST_REEL_W2", "")
WALK = Path(WALK) if WALK else None
WALK1 = os.environ.get("EDITOR_SE_TEST_REEL_W1", "")
WALK1 = Path(WALK1) if WALK1 else None
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(json.dumps(obj, indent=1).encode("utf-8"))


def run(d, *args):
    return subprocess.run([sys.executable, "-X", "utf8", "-I", str(S / "boundary_audit.py"),
                           str(d), str(d / "edit_map.json"), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=60)


def fixture(scratch):
    d = Path(tempfile.mkdtemp(prefix="fx1-audit-", dir=scratch))
    db = [-60.0] * 1000
    for a, b in ((120, 160), (520, 560)):
        db[a:b] = [-8.0] * (b - a)
    db[203] = -27.7  # 30 ms outside seg00 OUT, below this take's speech floor
    write(d / "envelope.json", dict(db=db, win_s=0.01))
    write(d / "segments.json", [[1.0, 2.0], [5.0, 6.0]])
    write(d / "edit_map.json", dict(words=[dict(word="one", start=1.2, end=1.6),
                                                      dict(word="two", start=5.2, end=5.6)]))
    write(d / "probe.json", dict(calibration=dict(speech_db=-27.0, speech_run_windows=6, gap_db=-32.0)))
    return d


def calibrated(scratch):
    d = fixture(scratch)
    p = run(d)
    ck("calibrated: breath tail is clean at the take's floor", p.returncode == 0
       and "flagged 0 | level -27.0 dB (this take's calibration)" in p.stdout, (p.returncode, p.stdout, p.stderr))
    p = run(d, "--hot", "-38")
    ck("calibrated: fixed-floor mutant flags the breath tail", p.returncode == 1
       and "seg00 OUT" in p.stdout and "level -38.0 dB (--hot)" in p.stdout, (p.returncode, p.stdout, p.stderr))
    ck("calibrated: missing EDL gives the flagged segment's hold", "No EDL found at " in p.stdout
       and "--hold 1.000:2.000" in p.stdout and "then run this audit again" in p.stdout, p.stdout)


def clipped(scratch):
    d = fixture(scratch)
    env = json.loads((d / "envelope.json").read_text(encoding="utf-8"))
    env["db"][202:240] = [-8.0] * 38  # a kept word's tail continues beyond OUT
    write(d / "envelope.json", env)
    em = json.loads((d / "edit_map.json").read_text(encoding="utf-8"))
    em["words"].append(dict(word="clipped", start=1.98, end=2.4))
    write(d / "edit_map.json", em)
    edl = [dict(src_in=0.5, src_out=3.0, line="L07"), dict(src_in=4.5, src_out=6.5, line="L08")]
    write(d / "edl.json", edl)
    p = run(d)
    ck("clipped: internal gap edge flags and holds its EDL cut", p.returncode == 1
       and "seg00 OUT" in p.stdout and "--hold 0.500:3.000" in p.stdout
       and "append to any --hold already on it" in p.stdout, (p.returncode, p.stdout, p.stderr))
    # Two flagged edges of one EDL cut must produce one hold, in first-seen order.
    write(d / "segments.json", [[1.3, 2.0], [5.0, 6.0]])
    p = run(d)
    ck("clipped: holds deduplicate without changing the flag format", p.returncode == 1
       and "INSIDE 'one'" in p.stdout and p.stdout.count("0.500:3.000") == 1, p.stdout)
    write(d / "segments.json", [[1.0, 2.0], [5.0, 6.0]])
    edl[0]["src_out"] = 2.0
    # Exercise the optional --edl path rather than the default file.
    write(d / "board-edl.json", edl)
    p = run(d, "--edl", str(d / "board-edl.json"))
    ck("clipped: board edge asks for a new Send on L07", p.returncode == 1
       and "A board cut sits on speech (line L07)" in p.stdout and "rebuild that board" in p.stdout
       and "new Send" in p.stdout and "--hold" not in p.stdout, (p.returncode, p.stdout, p.stderr))


def no_probe(scratch):
    d = fixture(scratch)
    (d / "probe.json").unlink()
    p = run(d)
    ck("no-probe: default floor is named", p.returncode == 1
       and "level -38.0 dB (default, no calibration found)" in p.stdout, (p.returncode, p.stdout, p.stderr))
    for probe in ({}, {"calibration": {}}, {"calibration": {"gap_db": -32}}):
        write(d / "probe.json", probe)
        p = run(d)
        ck("no-probe: missing speech_db falls back (%s)" % probe, p.returncode == 1
           and "level -38.0 dB (default, no calibration found)" in p.stdout, p.stdout + p.stderr)


def dropped(scratch):
    d = fixture(scratch)
    db = [-60.0] * 1000
    db[202:230] = [-6.0] * 28
    write(d / "envelope.json", dict(db=db, win_s=0.01))
    write(d / "segments.json", [[1.0, 2.0]])
    kept = dict(word="give", start=1.8, end=2.0)
    omitted = dict(word="you", start=2.02, end=2.3)
    write(d / "edit_map.json", dict(words=[kept, omitted]))
    p = run(d)
    ck("synthetic-dropped: dropped word 20 ms after OUT is clean", p.returncode == 0
       and "flagged 0" in p.stdout, p.stdout + p.stderr)
    write(d / "segments.json", [[1.0, 2.0], [2.01, 3.0]])
    p = run(d)
    ck("synthetic-dropped: the same word kept in the next segment flags outside energy", p.returncode == 1
       and "seg00 OUT" in p.stdout and "dB just outside" in p.stdout, p.stdout + p.stderr)
    write(d / "segments.json", [[1.0, 2.0]])
    # Same energy, but it belongs to a kept word continuing across the edge.
    write(d / "edit_map.json", dict(words=[dict(word="give", start=1.8, end=2.3)]))
    p = run(d)
    ck("synthetic-dropped: a kept word's continuing tail still flags", p.returncode == 1
       and "seg00 OUT" in p.stdout and "INSIDE 'give'" in p.stdout, p.stdout + p.stderr)
    # Even a nearby dropped word must not hide a kept word's continuation.
    write(d / "edit_map.json", dict(words=[dict(word="give", start=1.8, end=2.3), omitted]))
    p = run(d)
    ck("synthetic-dropped: nearby dropped word cannot hide a kept tail", p.returncode == 1
       and "seg00 OUT" in p.stdout, p.stdout + p.stderr)
    for side, boundary, start, end, status in (
            ("OUT", 2.0, 1.995, 2.3, "unresolved"),
            ("IN", 2.3, 2.0, 2.28, "aligned"),
            ("IN", 2.3, 2.0, 2.305, "unresolved")):
        write(d / "segments.json", [[1.0, boundary]] if side == "OUT" else [[boundary, 3.0]])
        word = kept if side == "OUT" else dict(word="next", start=2.5, end=2.8)
        write(d / "edit_map.json", dict(words=[word, dict(word="dropped", start=start, end=end, status=status)]))
        db = [-60.0] * 1000
        db[int(start * 100):int(end * 100)] = [-6.0] * (int(end * 100) - int(start * 100))
        write(d / "envelope.json", dict(db=db, win_s=0.01))
        p = run(d)
        ck("synthetic-dropped: %s dropped word (%s, %.3f-%.3f) is clean" % (side, status, start, end),
           p.returncode == 0 and "flagged 0" in p.stdout, p.stdout + p.stderr)
    # Sustained speech in the remaining gap still counts.
    write(d / "segments.json", [[1.0, 2.0]])
    write(d / "edit_map.json", dict(words=[kept, dict(word="you", start=2.08, end=2.3)]))
    db = [-60.0] * 1000
    db[201:207] = [-6.0] * 6
    write(d / "envelope.json", dict(db=db, win_s=0.01))
    p = run(d)
    ck("synthetic-dropped: sustained energy before the dropped word still flags", p.returncode == 1
       and "seg00 OUT" in p.stdout and "dB just outside" in p.stdout, p.stdout + p.stderr)
    db[204] = -60.0  # six hot windows in total, interrupted before the run reaches six
    db[207] = -6.0
    write(d / "envelope.json", dict(db=db, win_s=0.01))
    p = run(d)
    ck("synthetic-dropped: interrupted hot windows are not sustained speech", p.returncode == 0
       and "flagged 0" in p.stdout, p.stdout + p.stderr)


def adjacent_boundary(scratch):
    d = fixture(scratch)
    write(d / "segments.json", [[1.0, 2.0]])
    kept = dict(word="give", start=1.8, end=2.0)
    omitted = dict(word="you", start=2.04, end=2.3)
    write(d / "edit_map.json", dict(words=[kept, omitted]))
    db = [-60.0] * 1000
    db[200:203] = [-3.0] * 3  # 30 ms of coarticulation before the dropped word
    write(d / "envelope.json", dict(db=db, win_s=0.01))
    p = run(d)
    ck("synthetic-adjacent: a 30 ms boundary before a dropped word is clean", p.returncode == 0
       and "flagged 0" in p.stdout, p.stdout + p.stderr)
    write(d / "probe.json", dict(calibration=dict(speech_db=-27.0, speech_run_windows=3)))
    p = run(d, "--hot", "-38")
    ck("synthetic-adjacent: calibrated run length also applies with --hot", p.returncode == 1
       and "seg00 OUT" in p.stdout and "dB just outside" in p.stdout, p.stdout + p.stderr)
    write(d / "probe.json", dict(calibration=dict(speech_db=-27.0)))
    p = run(d)
    ck("synthetic-adjacent: missing run length defaults to six windows", p.returncode == 0
       and "flagged 0" in p.stdout, p.stdout + p.stderr)
    # Mirrored IN: the dropped word ends before the 30 ms boundary.
    write(d / "segments.json", [[2.04, 3.0]])
    write(d / "edit_map.json", dict(words=[dict(word="give", start=1.8, end=2.0),
                                            dict(word="you", start=2.04, end=2.3)]))
    p = run(d)
    ck("synthetic-adjacent: a 30 ms boundary after a dropped word is clean", p.returncode == 0
       and "flagged 0" in p.stdout, p.stdout + p.stderr)
    # No adjacent dropped word: the same edge still uses the original peak gate.
    write(d / "segments.json", [[1.0, 2.0]])
    write(d / "edit_map.json", dict(words=[kept]))
    p = run(d)
    ck("synthetic-adjacent: a short tail without a dropped word still flags", p.returncode == 1
       and "seg00 OUT" in p.stdout and "dB just outside" in p.stdout, p.stdout + p.stderr)
    db[200:208] = [-3.0] * 8  # the kept word's energy continues 80 ms beyond OUT
    write(d / "envelope.json", dict(db=db, win_s=0.01))
    p = run(d)
    ck("synthetic-adjacent: an 80 ms kept tail without a dropped word still flags", p.returncode == 1
       and "seg00 OUT" in p.stdout and "dB just outside" in p.stdout, p.stdout + p.stderr)


def walk(scratch):
    if WALK is None or not WALK.is_dir():
        print("SKIP real-walk: set EDITOR_SE_TEST_REEL_W2 to the S17 walk-2 reel folder to run this case")
        return
    d = Path(tempfile.mkdtemp(prefix="fx1-audit-walk-", dir=scratch))
    for name in ("envelope.json", "segments.json", "edit_map.json", "probe.json", "edl.json"):
        shutil.copyfile(WALK / "work" / name, d / name)
    p = run(d)
    print(p.stdout, end="")
    ck("real-walk: the calibrated audit is clean", p.returncode == 0 and "flagged 0" in p.stdout,
       (p.returncode, p.stdout, p.stderr))


def walk1(scratch):
    if WALK1 is None or not WALK1.is_dir():
        print("SKIP real-walk1: set EDITOR_SE_TEST_REEL_W1 to the S17 walk-1 reel folder to run this case")
        return
    d = Path(tempfile.mkdtemp(prefix="fx1-audit-walk1-", dir=scratch))
    for name in ("envelope.json", "segments.json", "edit_map.json", "probe.json", "edl.json"):
        shutil.copyfile(WALK1 / "work" / name, d / name)
    p = run(d)
    print(p.stdout, end="")
    ck("real-walk1: the audit is clean", p.returncode == 0 and "flagged 0" in p.stdout,
       (p.returncode, p.stdout, p.stderr))


CASES = {"synthetic-calibrated": calibrated, "synthetic-clipped": clipped, "synthetic-dropped": dropped,
         "synthetic-adjacent": adjacent_boundary, "no-probe": no_probe, "real-walk": walk, "real-walk1": walk1}


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
