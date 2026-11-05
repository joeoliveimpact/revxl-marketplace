#!/usr/bin/env python3
"""N1.4b check for gaps.py keep_edge_words (H-N1-11): an EDL edge inside a word keeps that word whole only when the
Cut Board picked it for that cut (its board cut time, make_board.in_point, lies inside the cut's own
[src_in, src_out)); a straddled word that was not picked is left out (the edge moves inward past it). Same rule at
in-points and out-points. A word that was not picked but overlaps a picked word never clips the picked word: the
conflict is logged. An edge inside no word does not move. An edit map with no parakeet_start keeps the old rule.

usage: python tests/editor/n1_edge_test.py <scratch-dir> [--case NAME]
Cases: unit (keep_edge_words in-process, no media), cli (gaps.py on a synthetic envelope, with and without
parakeet_start). Prints PASS/FAIL per check; exit 0 = every check passed.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut_safety_test as cs  # noqa: E402  (PY, run(), fresh(), module(), text())

FPS, GUARD = 30, 0.070
# (id, word, start, end, parakeet_start) - edit-map aligned times, sorted by start
WORDS = [("w_0000", "And", 1.00, 1.20, 1.00), ("w_0001", "now", 1.26, 1.50, 1.26), ("w_0002", "go.", 1.60, 2.00, 1.60),
         ("w_0003", "it's", 3.00, 3.30, 3.00), ("w_0004", "time", 3.20, 3.50, 3.20),    # overlap: conflict at an in-point
         ("w_0005", "real", 5.00, 5.30, 5.00), ("w_0006", "um", 5.20, 5.50, 5.25),      # overlap: conflict at an out-point
         ("w_0007", "so", 6.00, 6.30, 6.12), ("w_0008", "uh", 6.05, 6.15, 6.00),        # both under one in-point
         ("w_0009", "right", 7.00, 7.30, 7.05), ("w_0010", "mm", 7.15, 7.25, 7.22)]     # both under one out-point
W = [dict(id=i, word=w, start=s, end=e, parakeet_start=p, status="aligned") for i, w, s, e, p in WORDS]
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def whole(w, c):
    return c["src_in"] <= w["start"] and w["end"] <= c["src_out"]


def case_unit(S, a):
    g = cs.module("gaps.py")
    env = g.Env([-60.0] * 800, 0.01, {})
    by = {w["word"]: w for w in W}

    def edge(cut, cin):
        log = []
        return g.keep_edge_words([dict(src_in=cut[0], src_out=cut[1])], env, W, GUARD, FPS, log, cin)[0], log

    def cins(**at):   # board cut times by word (punctuation dropped from the name); every other word sits far away
        return {w["id"]: at.get(w["word"].replace("'", "").replace(".", ""), 99.0) for w in W}

    c, log = edge((1.10, 2.10), cins(And=0.95, now=1.21, go=1.55))
    ck("in-point inside 'And', not picked (cin 0.95 < src_in 1.10): the edge moves INWARD past it (%.3f)" % c["src_in"],
       by["And"]["end"] <= c["src_in"] <= by["now"]["start"] and whole(by["now"], c)
       and any("leave out 'And' (not picked)" in x for x in log), (c, log))
    c, log = edge((1.10, 2.10), cins(And=1.10, now=1.21, go=1.55))
    ck("in-point inside 'And', picked (cin 1.10 inside, aligned start 1.00 before the edge): the edge moves OUTWARD "
       "(%.3f)" % c["src_in"], by["And"]["start"] - GUARD <= c["src_in"] <= by["And"]["start"] and whole(by["And"], c)
       and any("keep 'And'" in x for x in log), (c, log))
    c, log = edge((0.50, 1.35), cins(And=0.95, now=1.40))
    ck("out-point inside 'now', not picked (cin 1.40 >= src_out 1.35): the edge moves INWARD before it (%.3f)"
       % c["src_out"], by["And"]["end"] <= c["src_out"] <= by["now"]["start"] and whole(by["And"], c)
       and any("leave out 'now' (not picked)" in x for x in log), (c, log))
    c, log = edge((0.50, 1.35), cins(And=0.95, now=1.21))
    ck("out-point inside 'now', picked (cin 1.21 inside): the edge moves OUTWARD past it (%.3f)" % c["src_out"],
       by["now"]["end"] <= c["src_out"] <= by["go."]["start"] and whole(by["now"], c)
       and any("keep 'now'" in x for x in log), (c, log))
    c, log = edge((3.10, 4.00), cins(its=2.95, time=3.15))
    ck("conflict at an in-point: 'it's' (not picked) overlaps picked 'time': 'time' stays whole, the edge stops at its "
       "start (%.3f), the conflict is logged" % c["src_in"],
       3.10 < c["src_in"] <= by["time"]["start"] and whole(by["time"], c)
       and any("EDGE conflict: 'it's' was not picked" in x for x in log), (c, log))
    c, log = edge((4.50, 5.40), cins(real=4.95, um=5.45))
    ck("conflict at an out-point: 'um' (not picked) overlaps picked 'real': 'real' stays whole (%.3f), the conflict "
       "is logged" % c["src_out"], by["real"]["end"] <= c["src_out"] < 5.40 and whole(by["real"], c)
       and any("EDGE conflict: 'um' was not picked" in x for x in log), (c, log))
    c, log = edge((6.10, 6.80), cins(so=6.12, uh=6.00))
    ck("picked 'so' and unpicked 'uh' both under the in-point: 'so' stays whole (%.3f), the edge moves OUTWARD, and "
       "the conflict for 'uh' is logged" % c["src_in"], c["src_in"] <= by["so"]["start"] and whole(by["so"], c)
       and any("keep 'so'" in x for x in log) and any("EDGE conflict: 'uh' was not picked" in x for x in log), (c, log))
    c, log = edge((6.50, 7.20), cins(right=7.05, mm=7.22))
    ck("picked 'right' and unpicked 'mm' both under the out-point: 'right' stays whole (%.3f), the edge moves OUTWARD, "
       "and the conflict for 'mm' is logged" % c["src_out"], c["src_out"] >= by["right"]["end"] and whole(by["right"], c)
       and any("keep 'right'" in x for x in log) and any("EDGE conflict: 'mm' was not picked" in x for x in log), (c, log))
    c, log = edge((0.80, 2.50), cins(And=0.95, now=1.21, go=1.55))
    ck("edges inside no word do not move and log nothing", c == dict(src_in=0.80, src_out=2.50) and not log, (c, log))
    c, log = edge((1.10, 2.10), None)
    ck("no board cut times (no parakeet_start): the old rule keeps 'And' whole (edge %.3f)" % c["src_in"],
       c["src_in"] <= by["And"]["start"] and any("keep 'And'" in x for x in log), (c, log))


def case_cli(S, a):
    """gaps.py's own main(): board cut times come from the edit map (in_point: parakeet_start - 0.05 with no
    silences), so src_in 1.10 leaves 'And' (cut time 0.95) out; the same map without parakeet_start keeps it."""
    for label, ps, want in (("parakeet_start", True, "EDGE moved to leave out 'And' (not picked)"),
                            ("no parakeet_start", False, "EDGE moved to keep 'And'")):
        d = cs.fresh(S, "cli-" + label.replace(" ", "-"))
        w = d / "work"
        db = [-60.0] * 800
        for x in W:
            for k in range(int(x["start"] / 0.01), int(x["end"] / 0.01)):
                db[k] = -20.0
        (w / "probe.json").write_text(json.dumps(dict(out_rate=FPS, calibration=dict(
            gap_db=-50.0, speech_db=-40.0, speech_run_windows=3))), encoding="utf-8")
        (w / "envelope.json").write_text(json.dumps(dict(db=db, win_s=0.01)), encoding="utf-8")
        (w / "edit_map.json").write_text(json.dumps(dict(words=[{k: v for k, v in x.items()
                                                                if ps or k != "parakeet_start"} for x in W],
                                                         events=[], silences=[])), encoding="utf-8")
        (w / "edl.json").write_text(json.dumps([dict(src_in=1.10, src_out=2.10)]), encoding="utf-8")
        p = cs.run("gaps.py", w, "--edl", w / "edl.json", "--words", w / "edit_map.json", cwd=d)
        plan = cs.text(w / "gap-plan.txt")
        ck("cli %s: gaps.py exits 0 and logs \"%s\"" % (label, want), p.returncode == 0 and want in plan,
           (p.returncode, p.stderr[-300:], [x for x in plan.splitlines() if "EDGE" in x]))


CASES = {"unit": case_unit, "cli": case_cli}


def main():
    cs.ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    a = ap.parse_args()
    S = Path(a.scratch).resolve()
    S.mkdir(parents=True, exist_ok=True)
    print("python %s" % cs.PY)
    for name in [a.case] if a.case else list(CASES):
        print("-- %s" % name)
        CASES[name](S, a)
    print("\n%d failed" % len(fails) if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
