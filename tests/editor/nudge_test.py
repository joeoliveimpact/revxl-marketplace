"""Light splice checks: <scratch> [--case unit|cli]; no media or third-party test dependencies."""
import argparse
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills/reel-first-cuts/scripts"
EDL = [dict(src_in=.3, src_out=1.5), dict(src_in=2., src_out=3.2)]
CAPS = dict(internal=.3, join=.3, beat_join=.32, lead=.08, tail=.1, min_gap=.1)
CAL = dict(gap_db=-50, speech_db=-40, speech_run_windows=3)


def envelope():
    db = [-60.] * 400
    for a, b in ((50, 100), (250, 300)):
        db[a:b] = [-20.] * (b - a)
    return db


def case_unit(root):
    spec = importlib.util.spec_from_file_location("gaps", SCRIPTS / "gaps.py")
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    env = g.Env(envelope(), .01, CAL)

    def pieces(nudge=None, words=()):
        kw = {} if nudge is None else dict(nudge=nudge)
        dels, log = g.plan(EDL, env, CAPS, .07, .1, [], words=words, **kw)
        return g.segments(EDL, dels, env, .1, words, log)[0]

    plain = pieces()
    assert pieces(0) == plain

    def pause(p, end=1.):
        return p[0][1] - end + 2.5 - p[1][0]

    later = pieces(.04)
    assert abs(later[0][1] - plain[0][1] - .04) < 1e-8
    assert abs(later[1][0] - plain[1][0] - .04) < 1e-8
    assert abs(pause(later) - pause(plain)) < 1e-8
    limited = pieces(1.)
    assert abs(2.5 - limited[1][0] - .07) < 1e-8
    assert abs(pause(limited) - pause(plain)) < 1e-8
    # Earlier requests are ignored, including their log, with the 70 ms guard unchanged.
    for value in (-.04, -1.):
        assert pieces(value) == plain and abs(plain[0][1] - 1. - .07) < 1e-8
        assert g.plan(EDL, env, CAPS, .07, .1, [], nudge=value) == g.plan(EDL, env, CAPS, .07, .1, [])
    # A quiet word beyond envelope speech is still protected on both sides of the splice.
    words = [dict(id="quiet", word="quiet", start=1.08, end=1.12),
             dict(id="soft", word="soft", start=2.3, end=2.4)]
    for value in (-1., -.04, .04, 1.):
        moved = pieces(value, words)
        assert all(not w["start"] < edge < w["end"] for p in moved for edge in p for w in words)
        assert abs(pause(moved) - pause(pieces(0, words))) < 1e-8


def case_cli(root):
    work = root / "work"
    work.mkdir(parents=True)
    for file, data in (("probe.json", dict(out_rate=1000, calibration=CAL)),
                       ("envelope.json", dict(db=envelope(), win_s=.01)), ("edl.json", EDL)):
        (work / file).write_bytes(json.dumps(data).encode("utf-8"))

    def run(*flags):
        p = subprocess.run([sys.executable, "-X", "utf8", "-I", str(SCRIPTS / "gaps.py"), str(work),
                            "--edl", str(work / "edl.json"), "--join", ".3", "--min-island", ".1", *flags],
                           capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert p.returncode == 0, p.stdout + p.stderr
        return {name: (work / name).read_bytes() for name in
                ("cuts.json", "segments.json", "gap-plan.txt", "listen.txt", "timemap.json")}

    baseline = run()
    assert run("--nudge", "0") == baseline, "Zero must leave every generated file byte-identical"
    assert run("--nudge", "-0.04") == baseline, "Earlier must be clamped to zero, including logs"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=("unit", "cli"))
    args = ap.parse_args()
    scratch = Path(args.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nudge-", dir=scratch) as tmp:
        root = Path(tmp)
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / "state")}):
            for name in [args.case] if args.case else ("unit", "cli"):
                globals()["case_" + name](root)
                print("PASS " + name)
    print("all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
