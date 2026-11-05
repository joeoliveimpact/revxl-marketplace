#!/usr/bin/env python3
"""N1.4 check for reel-first-cuts' no-board Stage 2 (line_score.py, H-N1-8, H-N1-2): only backward-facing lines are
free cuts, a forward line never is, the table ranks free cuts / your call / keeps with ties in input order, and a
bad labels file (a line with no direction or no why, an unknown direction, a repeated id) refuses with exit 2 and
writes nothing. No run ever writes an EDL, a cut selection or any file but work/line-table.md.

usage: python tests/editor/n1_score_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 = every check passed. Cases: rank, refuse (both by default, a second or two).
line_score.py is stdlib only; it runs as `python -X utf8 -I` under the Python running this test. Fixtures are
synthetic JSON built here; no media.
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPT = REPO / "plugins" / "editor-superengine" / "skills" / "reel-first-cuts" / "scripts" / "line_score.py"
sys.path.insert(0, str(REPO / "plugins" / "editor-superengine" / "skills" / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402

fails = []
FREE, CALL, KEEP = "free cut", "your call", "keep: it opens a loop the viewer stays for"


def L(i, direction, why="a reason", text=None):
    d = {"id": i, "text": text or "line %s of REEL_018" % i, "src_in": 1.0, "src_out": 2.0, "why": why}
    if direction is not None:
        d["direction"] = direction
    return d


# Input order mixes the three directions; L2 is a forward line with zero information (it must still be kept).
GOOD = [L("L1", "forward", "sets up the reveal"), L("L2", "forward", "no facts, but it asks what happens next"),
        L("L3", "backward", "restates the opening claim"), L("L4", "neutral", "adds a detail | not needed"),
        L("L5", "backward", "repeats the price"), L("L6", "neutral", "a side note"), L("L7", "forward", "a rehook")]
WANT = [("L3", "backward", FREE), ("L5", "backward", FREE), ("L4", "neutral", CALL), ("L6", "neutral", CALL),
        ("L1", "forward", KEEP), ("L2", "forward", KEEP), ("L7", "forward", KEEP)]


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def fresh(S, name, lines):
    d = S / name
    shutil.rmtree(d, ignore_errors=True)
    (d / "work").mkdir(parents=True)
    # a file a no-board run already has: it may not change, and nothing but the table may appear
    (d / "work" / "edit_map.json").write_bytes(b'{"words": []}\n')
    (d / "work" / "line-labels.json").write_bytes(json.dumps({"lines": lines}, indent=1).encode("utf-8"))
    return d


def snap(d):
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in d.rglob("*") if p.is_file()}


def run(d, *args):
    return subprocess.run([sys.executable, "-X", "utf8", "-I", str(SCRIPT), str(d)] + [str(x) for x in args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)


def rows(md):
    """Table body rows as cell lists (an escaped \\| stays inside its cell)."""
    out = []
    for ln in md.splitlines():
        if ln.startswith("| ") and not ln.startswith("| rank "):
            out.append([c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", ln)[1:-1]])
    return out


def case_rank(S, a):
    d = fresh(S, "rank", GOOD)
    before = snap(d)
    p = run(d)
    ck("rank: good labels exit 0", p.returncode == 0, p.stdout + p.stderr)
    ck("rank: nothing on stderr (no warning, no traceback)", not p.stderr.strip(), p.stderr)
    after = snap(d)
    new = sorted(set(after) - set(before))
    ck("rank: the only new file is work/line-table.md", new == ["work/line-table.md"], new)
    ck("rank: existing files unchanged", all(after.get(k) == v for k, v in before.items()))
    ck("rank: no edl.json or cut-selection.json anywhere",
       not any(Path(k).name in ("edl.json", "cut-selection.json") for k in after), sorted(after))
    md = after.get("work/line-table.md", b"").decode("utf-8")
    ck("rank: table written with LF only", md and "\r" not in md)
    ck("rank: the printed table is the written one", md and md in p.stdout, p.stdout)
    r = rows(md)
    ck("rank: one row per line", len(r) == len(GOOD), r)
    got = [(c[1], c[3], c[5]) for c in r]
    ck("rank: free cuts, then your call, then keeps; ties in input order", got == WANT, got)
    ck("rank: ranks run 1..n", [c[0] for c in r] == [str(k) for k in range(1, len(GOOD) + 1)], r)
    ck("rank: why and text carried (a | in a cell stays in its cell)",
       any(c[1] == "L4" and c[4] == "adds a detail | not needed" and c[2] == "line L4 of REEL_018" for c in r), r)
    verdict = {c[1]: c[5] for c in r}
    ck("rank: a forward line is never a free cut", all(verdict.get(i) == KEEP for i in ("L1", "L2", "L7")), verdict)
    ck("rank: a backward line is a free cut", all(verdict.get(i) == FREE for i in ("L3", "L5")), verdict)
    ck("rank: only backward lines are free cuts",
       {i for i, v in verdict.items() if v == FREE} == {"L3", "L5"}, verdict)
    # an all-forward reel offers no free cut at all
    d2 = fresh(S, "rank-forward", [L("F1", "forward"), L("F2", "forward")])
    p2 = run(d2)
    md2 = (d2 / "work" / "line-table.md").read_text(encoding="utf-8") if p2.returncode == 0 else ""
    ck("rank: all-forward labels give no free cut",
       p2.returncode == 0 and FREE not in md2 and [c[5] for c in rows(md2)] == [KEEP, KEEP], p2.stdout + p2.stderr)
    # --labels: a relative path is read from the reel folder
    d3 = fresh(S, "rank-labels", [L("X1", "forward")])
    (d3 / "work" / "other.json").write_bytes(json.dumps({"lines": [L("Y1", "backward")]}).encode("utf-8"))
    p3 = run(d3, "--labels", "work/other.json")
    md3 = (d3 / "work" / "line-table.md").read_text(encoding="utf-8") if p3.returncode == 0 else ""
    ck("rank: --labels reads the named file", [c[1] for c in rows(md3)] == ["Y1"], p3.stdout + p3.stderr)


def refuses(S, name, lines, ids):
    d = fresh(S, name, lines)
    before = snap(d)
    p = run(d)
    ck("refuse/%s: exit 2" % name, p.returncode == 2, (p.returncode, p.stdout + p.stderr))
    ck("refuse/%s: nothing written" % name, snap(d) == before, sorted(set(snap(d)) - set(before)))
    ck("refuse/%s: the message names %s" % (name, ", ".join(ids) or "the problem"),
       all(i in p.stderr for i in ids) and "refused" in p.stderr, p.stderr)
    return p


def case_refuse(S, a):
    refuses(S, "no-direction", [L("A1", "backward"), L("A2", None), L("A3", "forward")], ["A2"])
    p = refuses(S, "no-why", [L("B1", "backward", why=""), L("B2", "neutral", why="  "), L("B3", "forward")],
                ["B1", "B2"])
    ck("refuse/no-why: a labelled line is not named", "B3" not in p.stderr, p.stderr)
    refuses(S, "unknown-direction", [L("C1", "sideways"), L("C2", "Backward"), L("C3", "neutral")], ["C1", "C2"])
    refuses(S, "duplicate-id", [L("D1", "backward"), L("D2", "neutral"), L("D1", "forward")], ["D1"])
    refuses(S, "no-lines", [], [])
    # a stale table from an earlier run is left alone on a refusal, never rewritten
    d = fresh(S, "stale", [L("E1", None)])
    (d / "work" / "line-table.md").write_bytes(b"old table\n")
    p = run(d)
    ck("refuse/stale: an earlier table is not touched",
       p.returncode == 2 and (d / "work" / "line-table.md").read_bytes() == b"old table\n", p.stderr)
    d = S / "no-file"
    shutil.rmtree(d, ignore_errors=True)
    (d / "work").mkdir(parents=True)
    p = run(d)
    ck("refuse/no-file: a missing labels file exits 2 and writes nothing",
       p.returncode == 2 and not any(d.rglob("*.*")), p.stdout + p.stderr)


CASES = {"rank": case_rank, "refuse": case_refuse}


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=CASES)
    a = ap.parse_args()
    S = Path(a.scratch).resolve()
    S.mkdir(parents=True, exist_ok=True)
    for name, fn in CASES.items():
        if not a.case or a.case == name:
            fn(S, a)
    print("%d check(s) failed: %s" % (len(fails), ", ".join(fails)) if fails else "all checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
