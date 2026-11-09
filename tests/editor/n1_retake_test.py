#!/usr/bin/env python3
"""N1.2a check for repeat_check.py: reworded retakes are flagged for review (tier "review", never cut, never in the
exit code) and "never, never" is said twice on purpose.

usage: python tests/editor/n1_retake_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 = every check passed. --case runs one case; without it every case runs.
Cases: reworded, never, strict, deep-gate. Every input is a synthetic tx-cut.json built here (no media, no
transcriber); repeat_check.py runs as `python -X utf8 -I` in the editor's Python (EDITOR_SE_HOME), else this one.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut_safety_test as cs  # noqa: E402  (PY, ENV, SCRIPTS, run(), fresh(), module(), load())
import ports_test as pt  # noqa: E402  (PLANT: S4b.2's strict repeat + retake text, timed())

fails = []

A = "We built this tool to fix your audio fast."
M = "Then it saves the file."
B = "This tool fixes your audio really fast, we built it."
OTHER = "Now the export runs in the background quietly."
C = "Coffee wakes developers."        # content words: coffee, wakes, developers
J4 = "Strong tea wakes developers."   # 2 shared of 5 in all: Jaccard 0.4
J5 = "Tea wakes developers."          # 2 shared of 4 in all: Jaccard 0.5


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def tx(d, name, words):
    f = d / "work" / name
    f.write_text(json.dumps({"words": [{"i": k, "word": t, "start": s, "end": e}
                                       for k, (t, s, e) in enumerate(words)]}), encoding="utf-8")
    return f


def check(d, f, *args):
    """repeat_check.py on f: (process, drop list from --json, review list from --review)."""
    out, rev = f.with_suffix(".hits.json"), f.with_suffix(".review.json")
    for x in (out, rev):
        x.unlink(missing_ok=True)
    p = cs.run("repeat_check.py", f, "--json", out, "--review", rev, *args, cwd=d)
    return p, cs.load(out) if out.exists() else None, cs.load(rev) if rev.exists() else None


def starts(words, w):
    return [s for t, s, _ in words if t == w]


# ------------------------------------------------------------------------------------------- reworded
def case_reworded(S, a):
    d = cs.fresh(S, "reworded")
    words = pt.timed(" ".join((A, M, B)), gaps={9: 1.0, 14: 1.0})
    second = len((A + " " + M).split())
    p, H, R = check(d, tx(d, "tx-cut.json", words))
    print(p.stdout.rstrip())
    ck("reworded: no strict hit, so exit 0 and 'no repeats found'",
       p.returncode == 0 and "no repeats found" in p.stdout, (p.returncode, p.stdout[-300:], p.stderr[-300:]))
    ck("reworded: the drop list (--json) is empty, so nothing is auto-cut", H == [], H)
    r = (R or [{}])[0]
    ck("reworded: exactly one review hit, kind loose-retake, tier review", R is not None and len(R) == 1
       and r.get("kind") == "loose-retake" and r.get("tier") == "review", R)
    ck("reworded: the review hit carries no drop span", R is not None and all("drop" not in h for h in R), R)
    ck("reworded: it joins the two takes: at = [%s, %s], first = 0, second = %d"
       % (words[0][1], words[second][1], second),
       r.get("at") == [words[0][1], words[second][1]] and r.get("first") == 0 and r.get("second") == second, r)
    ck("reworded: Jaccard %s >= 0.5" % r.get("jaccard"), (r.get("jaccard") or 0) >= 0.5, r)
    ck("reworded: stdout shows it as a review line and counts it apart",
       "said twice in different words: pick one (not cut)" in p.stdout
       and "1 reworded retake(s) for review (not cut)" in p.stdout, p.stdout[-400:])
    p, H, R = check(d, tx(d, "tx-cut.json", words), "--jaccard", "0.8")
    ck("reworded: --jaccard 0.8 (above this pair's %s) flags nothing, exit 0" % r.get("jaccard"),
       p.returncode == 0 and H == [] and R == [], (p.returncode, H, R))
    # The 15 s limit: A then B with nothing between; B's first word starts 3.15 s + gap after A's first word.
    for gap, flag in ((10.85, True), (12.85, False)):
        w2 = pt.timed(A + " " + B, gaps={9: gap})
        apart = round(w2[9][1] - w2[0][1], 3)
        p, H, R = check(d, tx(d, "tx-span.json", w2))
        ck("reworded: sentence starts %s s apart are %s (limit 15 s), exit 0, nothing cut"
           % (apart, "flagged" if flag else "not flagged"),
           p.returncode == 0 and H == [] and R is not None and len(R) == (1 if flag else 0), (apart, p.returncode, H, R))
    # The Jaccard 0.5 limit: C shares {wakes, developers} with each; M (2 content words) sits between so find()
    # never sees "wakes developers" twice in a row.
    for b2, jac, flag in ((J4, 0.4, False), (J5, 0.5, True)):
        p, H, R = check(d, tx(d, "tx-jac.json", pt.timed(" ".join((C, M, b2)), gaps={3: 1.0, 8: 1.0})))
        ck("reworded: content-word Jaccard %s is %s at the default --jaccard 0.5, exit 0, nothing cut"
           % (jac, "flagged" if flag else "not flagged"),
           p.returncode == 0 and H == [] and R is not None and len(R) == (1 if flag else 0)
           and (not flag or R[0].get("jaccard") == jac), (p.returncode, H, R))
    p, H, R = check(d, tx(d, "tx-jac.json", pt.timed(" ".join((C, M, J4)), gaps={3: 1.0, 8: 1.0})), "--jaccard", "0.4")
    ck("reworded: ... and the 0.4 pair IS flagged at --jaccard 0.4 (so only the threshold held it back)",
       p.returncode == 0 and H == [] and R is not None and len(R) == 1 and R[0].get("jaccard") == 0.4, (H, R))
    p, H, R = check(d, tx(d, "tx-other.json", pt.timed(" ".join((A, M, OTHER)), gaps={9: 1.0, 14: 1.0})))
    ck("reworded: two different sentences are not flagged", p.returncode == 0 and H == [] and R == [],
       (p.returncode, H, R))


# ------------------------------------------------------------------------------------------- never
def case_never(S, a):
    d = cs.fresh(S, "never")
    p, H, R = check(d, tx(d, "tx-never.json", pt.timed("I will never, never give up on this.")))
    ck("never: 'never, never' is not flagged, exit 0", p.returncode == 0 and H == [] and R == []
       and "no repeats found" in p.stdout, (p.returncode, H, R, p.stdout[-200:]))
    p, H, R = check(d, tx(d, "tx-always.json", pt.timed("I will always, always give up on this.")))
    ck("never: the same line with 'always, always' IS flagged as a repeat, exit 1 (the whitelist is word-specific)",
       p.returncode == 1 and [h.get("kind") for h in H or []] == ["repeat"], (p.returncode, H))


# ------------------------------------------------------------------------------------------- strict
def case_strict(S, a):
    d = cs.fresh(S, "strict")
    words = pt.timed(pt.PLANT, gaps={9: 1.0, 15: 1.0, 18: 2.0})
    p, H, R = check(d, tx(d, "tx-plant.json", words))
    H = H or []
    rep = [h for h in H if h.get("kind") == "repeat"]
    ret = [h for h in H if h.get("kind") == "retake"]
    ck("strict: 'and fixes and fixes' still found, drop = the first copy %s" % starts(words, "and"),
       len(rep) == 1 and rep[0]["drop"] == starts(words, "and") and rep[0]["n"] == 2, rep)
    ck("strict: the 6-word retake still found, drop = the first take %s" % starts(words, "It"),
       len(ret) == 1 and ret[0]["drop"] == starts(words, "It") and ret[0]["n"] == 6, ret)
    ck("strict: exit 1, exactly those 2 hits, no review hit (the strict retake isn't flagged twice)",
       p.returncode == 1 and len(H) == 2 and R == [], (p.returncode, H, R))
    n = len(words)
    tail = pt.timed(" ".join((A, M, B)), t0=words[-1][2] + 20.0, gaps={9: 1.0, 14: 1.0})
    p, H2, R = check(d, tx(d, "tx-mixed.json", words + tail))
    H2 = H2 or []
    ck("strict: with a reworded retake added, the drop list is still exactly the 2 strict hits, same drops",
       [(h.get("kind"), h.get("drop")) for h in H2] == [(h.get("kind"), h.get("drop")) for h in H], (H, H2))
    ck("strict: ... the reworded pair is the one review hit (first = %d), and the exit code is still 1" % n,
       p.returncode == 1 and R is not None and len(R) == 1 and R[0].get("first") == n
       and "2 repeat(s) found" in p.stdout, (p.returncode, R, p.stdout[-300:]))
    ck("strict: no hit in the drop list has tier review or kind loose-retake",
       not any(h.get("tier") == "review" or h.get("kind") == "loose-retake" for h in H + H2), H + H2)


# ------------------------------------------------------------------------------------------- deep gate
def case_deep_gate(S, a):
    """Deep mode runs find() per 3 s window, so find() itself must stay strict: no loose hits from it."""
    d = cs.fresh(S, "deep-gate")
    rc = cs.module("repeat_check.py")
    W = rc.load(tx(d, "tx-cut.json", pt.timed(" ".join((A, M, B)), gaps={9: 1.0, 14: 1.0})))
    F = rc.find(W)
    ck("deep-gate: find() (deep mode's per-window finder) returns nothing on the reworded pair", F == [], F)
    ck("deep-gate: loose() on the same words returns the one review hit", len(rc.loose(W, F)) == 1)
    F = rc.find(rc.load(tx(d, "tx-never.json", pt.timed("never never stop."))))
    ck("deep-gate: 'never never' gives find() nothing (in-process, the said-twice list)", F == [], F)


CASES = {"reworded": case_reworded, "never": case_never, "strict": case_strict, "deep-gate": case_deep_gate}


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
