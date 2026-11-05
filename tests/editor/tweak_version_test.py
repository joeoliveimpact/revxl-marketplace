#!/usr/bin/env python3
"""EGM B1 check: tweaks_to_edl.py never applies one Tweak Board round's marks to another round's cut.

usage: python tests/editor/tweak_version_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 = every check passed. Cases: refuse, noversion, accept.

Synthetic reel, no media: a six-word edit map, a round-1 cut (v1) and a round-2 cut (v2) that dropped a word, so
their cut times differ. refuse: the v1 Send against the v2 board exits 3 with one plain line and writes no
work/edl.json. noversion: a Send with no version key is refused the same way, with the
older-round line. accept: a v2 Send against the v2 board exits 0 and writes work/edl.json. tweaks_to_edl.py runs on
the editor's venv Python (EDITOR_SE_HOME, else the default; else this interpreter).
"""
import argparse, json, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPTS = REPO / "plugins" / "editor-superengine" / "skills" / "reel-first-cuts" / "scripts"
sys.path.insert(0, str(REPO / "plugins" / "editor-superengine" / "skills" / "_shared"))
import runtime as rt  # noqa: E402

PY = rt.tool("python") if Path(rt.tool("python")).exists() else sys.executable
FPS = 30
WORDS = [("one", 0.5, 0.8), ("two", 1.0, 1.3), ("three", 1.6, 1.9), ("four", 4.2, 4.5), ("five", 4.8, 5.1),
         ("six", 5.4, 5.7)]
# [src_in_f, src_out_f] per segment; out frames follow on
ROUND = {"v1": [(0, 60), (120, 180)],                # round 1 keeps "two"
         "v2": [(0, 27), (45, 60), (120, 180)]}      # round 2 dropped it: every later cut time moved
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def write(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=1), encoding="utf-8")


def cuts(version):
    segs, o = [], 0
    for a, b in ROUND[version]:
        segs.append(dict(src_in_f=a, src_out_f=b, out_in_f=o, out_out_f=o + b - a))
        o += b - a
    return dict(fps=FPS, speed=1.0, segments=segs)


def board(version):
    """tweak-board.config.json the way make_tweaks.py stamps it: version, edit_map, words[] in cut time."""
    c = cuts(version)
    words = []
    for i, (w, s, _) in enumerate(WORDS):
        for g in c["segments"]:
            if g["src_in_f"] / FPS <= s < g["src_out_f"] / FPS:
                words.append(dict(id="w%d" % i, w=w, t=round(g["out_in_f"] / FPS + s - g["src_in_f"] / FPS, 3)))
    return dict(reel="syn", version=version, edit_map="work/edit_map.json", take=1, words=words)


def reel(S, name, version):
    """A reel folder holding the round's cut and board."""
    d = S / name
    shutil.rmtree(d, ignore_errors=True)
    write(d / "work/edit_map.json", dict(events=[], words=[dict(id="w%d" % i, word=w, parakeet_start=s, start=s, end=e)
                                                         for i, (w, s, e) in enumerate(WORDS)]))
    write(d / "work/cuts.json", cuts(version))
    write(d / "tweak-board.config.json", board(version))
    return d


def send(d, version, a, b):
    sel = dict(reel="syn", version=version, speed=1.0, marks=[dict(id=1, type="cut", a=a, b=b)])
    if version is None:   # a Send from a board with no version stamp
        del sel["version"]
    write(d / "tweak-selection.json", sel)
    return subprocess.run([str(PY), "-X", "utf8", "-I", str(SCRIPTS / "tweaks_to_edl.py"), str(d / "tweak-selection.json"),
                           str(d / "work")], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)


def case_refuse(S):
    d = reel(S, "refuse", "v2")
    # round 1's mark on "two" (cut time 0.95-1.35 in v1); through v2's map it would land on "three"
    p = send(d, "v1", 0.95, 1.35)
    err = p.stderr.strip().splitlines()
    ck("refuse: a v1 Send against the v2 board exits 3 with one plain line (%s)" % p.stderr.strip()[-200:],
       p.returncode == 3 and len(err) == 1 and "another cut" in err[0] and "--version" in err[0], (p.returncode, p.stderr[-300:]))
    ck("refuse: nothing written (no work/edl.json)", not (d / "work/edl.json").exists())


def case_noversion(S):
    d = reel(S, "noversion", "v2")
    p = send(d, None, 2.15, 2.55)
    err = p.stderr.strip().splitlines()
    ck("noversion: a Send with no version key exits 3 with the older-round line (%s)" % p.stderr.strip()[-200:],
       p.returncode == 3 and len(err) == 1 and "older round" in err[0] and "make_tweaks.py" in err[0], (p.returncode, p.stderr[-300:]))
    ck("noversion: nothing written (no work/edl.json)", not (d / "work/edl.json").exists())


def case_accept(S):
    d = reel(S, "accept", "v2")
    # round 2's mark on "five": source 4.8-5.1 is cut time 2.2-2.5 in v2
    p = send(d, "v2", 2.15, 2.55)
    edl = json.loads((d / "work/edl.json").read_text(encoding="utf-8")) if (d / "work/edl.json").exists() else []
    ck("accept: a v2 Send against the v2 board exits 0 and writes work/edl.json", p.returncode == 0 and bool(edl),
       (p.returncode, p.stderr[-300:]))
    inside = lambda s, e: any(x["src_in"] <= s and e <= x["src_out"] for x in edl)
    ck("accept: the edl drops 'five' and keeps 'three' and 'six' (%s)" % edl,
       not inside(4.8, 5.1) and inside(1.6, 1.9) and inside(5.4, 5.7))


CASES = {"refuse": case_refuse, "noversion": case_noversion, "accept": case_accept}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=sorted(CASES))
    a = ap.parse_args()
    S = Path(a.scratch).resolve()
    S.mkdir(parents=True, exist_ok=True)
    print("python %s" % PY)
    for name, fn in CASES.items():
        if a.case in (None, name):
            fn(S)
    print("\n%d failed" % len(fails) if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
