#!/usr/bin/env python3
"""FX1 C+G: one half-open membership rule and one source of Tweak Board word times.

usage: python tests/editor/fx1_boundary_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 only when no checks fail.
"""
import argparse, contextlib, hashlib, io, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
P = REPO / "plugins/editor-superengine"
S = P / "skills/reel-first-cuts/scripts"
CHECKS = P / "skills/_shared/checks"
WALK = os.environ.get("EDITOR_SE_TEST_REEL_W2", "")
WALK = Path(WALK) if WALK else None
sys.path.insert(0, str(P / "skills/_shared"))
sys.path.insert(0, str(S))
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(json.dumps(obj, indent=1).encode("utf-8"))


def run(script, args, d):
    return subprocess.run([sys.executable, "-X", "utf8", "-I", str(script), *map(str, args)], cwd=d,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)


def board_words(cuts, em):
    import word_map
    return [dict(id=w["id"], w=w["word"], t=round(w["out_start"], 3))
            for w in word_map.build(cuts, em)["words"]]


def helper(scratch):
    import word_map
    for t, expected in ((2.033, (False, True)), (2.032, (True, False)),
                        (2.0333333, (False, True)), (1.0, (True, False))):
        got = (word_map.in_span(t, 0, 2.0333333), word_map.in_span(t, 2.0333333, 3.0))
        ck("helper: membership at %.7f" % t, got == expected, got)
    # Exercise build's use of the helper, not just the helper in isolation.
    cuts = dict(fps=30, speed=1.0, segments=[
        dict(src_in_f=0, src_out_f=61, out_in_f=0, out_out_f=61),
        dict(src_in_f=61, src_out_f=90, out_in_f=61, out_out_f=90)])
    em = dict(words=[dict(id="step", word="Step", start=2.033, end=2.3, parakeet_start=2.033)])
    mapped = word_map.build(cuts, em)["words"]
    ck("helper: word_map assigns a rounded boundary to the starting segment", len(mapped) == 1
       and mapped[0]["seg"] == 1, mapped)


def synthetic(scratch):
    import make_tweaks, tweaks_to_edl
    d = Path(tempfile.mkdtemp(prefix="fx1-boundary-", dir=scratch))
    cuts = dict(fps=30, speed=1.0, segments=[
        dict(src_in_f=0, src_out_f=60, out_in_f=0, out_out_f=60),
        dict(src_in_f=120, src_out_f=180, out_in_f=60, out_out_f=120)])
    # I's aligned start differs by >1 s within segment 1; you's alignment is in
    # segment 2 but its board anchor is in segment 1 (the walk's placement hole).
    em = dict(words=[dict(id="i", word="I", start=1.6, end=1.8, parakeet_start=0.4, status="aligned"),
                     dict(id="ghost", word="profit", start=0.8, end=1.0, parakeet_start=0.8, status="unresolved"),
                     dict(id="you", word="you", start=4.5, end=4.7, parakeet_start=1.2, status="aligned"),
                     dict(id="step", word="Step", start=4.0, end=4.3, parakeet_start=4.0, status="aligned")],
              events=[], silences=[])
    write(d / "work/cuts.json", cuts)
    write(d / "work/edit_map.json", em)
    seq = [dict(id=w["id"], word=w["word"], start=w["parakeet_start"], end=w["end"]) for w in em["words"]]
    write(d / "cut-board.config.json", dict(reel="syn", takes={"1": dict(edit_map="work/edit_map.json", words=seq)}))
    cmap = make_tweaks.cut_map(cuts)
    cfg = dict(reel="syn", cuts_sha256=hashlib.sha256((d / "work/cuts.json").read_bytes()).hexdigest(),
               version="v1", edit_map="work/edit_map.json", take=1, map=cmap, words=board_words(cuts, em))
    write(d / "tweak-board.config.json", cfg)
    write(d / "tweak-selection.json", dict(reel="syn", version="v1", speed=1.0,
                                           marks=[dict(id=1, type="cut", a=2.1, b=2.2)]))
    value = tweaks_to_edl.to_src(2.0, cmap, 1.0)
    ck("synthetic: Step at the shared cut boundary maps to source 4.0", abs(value - 4.0) < 0.001, value)
    for t, expected in ((1.9996, 4.0), (4.0, 6.0), (4.0004, 6.0), (-1.0, 0.0), (8.0, 6.0)):
        got = tweaks_to_edl.to_src(t, cmap, 1.0)
        ck("synthetic: endpoint clamp/fallback %.4f" % t, abs(got - expected) < 0.001, got)
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
    ck("synthetic: v1 marks accepted with canonical word times", p.returncode == 0
       and (d / "work/edl.json").is_file(), p.stdout + p.stderr)
    edl = read(d / "work/edl.json") if (d / "work/edl.json").exists() else []
    ck("synthetic: cut mark removes source 4.1-4.2", edl == [dict(src_in=0.0, src_out=2.0),
       dict(src_in=4.0, src_out=4.1), dict(src_in=4.2, src_out=6.0)], edl)
    p = run(S / "word_map.py", [d], d)
    ck("synthetic: word map written", p.returncode == 0, p.stdout + p.stderr)
    p = run(CHECKS / "map_check.py", [d], d)
    ck("synthetic: canonical tweak times pass map_check", p.returncode == 0
       and "tweak-time" not in p.stdout and "tweak-word" not in p.stdout, p.stdout + p.stderr)
    # The old placement rule includes unresolved words and assigns membership by anchor.
    cfg["words"] = [dict(id=w["id"], w=w["word"].strip(), t=round(c0 + (w["start"] - s0), 3))
                    for c0, c1, s0, s1 in cmap for w in seq if s0 <= w["start"] < s1]
    write(d / "tweak-board.config.json", cfg)
    p = run(CHECKS / "map_check.py", [d], d)
    ck("synthetic: old placement mutant is detected", "tweak-time" in p.stdout or "tweak-word" in p.stdout,
       p.stdout + p.stderr)
    # Independently exercise drift guard's refusal wording and its absent-ID branch.
    cfg["words"] = board_words(cuts, em)
    cfg["words"][0]["t"] += 0.2
    write(d / "tweak-board.config.json", cfg)
    (d / "work/edl.json").unlink(missing_ok=True)
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
    ck("synthetic: drift over 80 ms is refused in cut time", p.returncode == 3
       and "puts it at" in p.stderr and "in this cut (200 ms apart, over 80 ms)" in p.stderr
       and not (d / "work/edl.json").exists(), p.stdout + p.stderr)
    cfg["words"] = [dict(id="ghost", w="profit", t=0.8)]
    write(d / "tweak-board.config.json", cfg)
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
    ck("synthetic: an unresolved board word is refused", p.returncode == 3 and "has no such word" in p.stderr
       and not (d / "work/edl.json").exists(), p.stdout + p.stderr)


def walk(scratch):
    if WALK is None or not WALK.is_dir():
        print("SKIP real-walk: set EDITOR_SE_TEST_REEL_W2 to the S17 walk-2 reel folder to run this case")
        return
    d = Path(tempfile.mkdtemp(prefix="fx1-boundary-walk-", dir=scratch))
    for name in ("cut-board.config.json", "tweak-board.config.json", "tweak-selection.json",
                 "work/cuts.json", "work/edit_map.json"):
        dest = d / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(WALK / name, dest)
    cfg = read(d / "tweak-board.config.json")
    cfg["words"] = board_words(read(d / "work/cuts.json"), read(d / "work/edit_map.json"))
    cfg["cuts_sha256"] = hashlib.sha256((d / "work/cuts.json").read_bytes()).hexdigest()
    write(d / "tweak-board.config.json", cfg)
    sel = read(d / "tweak-selection.json")
    sel["version"] = cfg["version"]
    write(d / "tweak-selection.json", sel)
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
    ck("real-walk: rebuilt tweak words accept the Send", p.returncode == 0
       and (d / "work/edl.json").is_file(), p.stdout + p.stderr)
    p = run(S / "word_map.py", [d], d)
    ck("real-walk: word map written", p.returncode == 0, p.stdout + p.stderr)
    p = run(CHECKS / "map_check.py", [d], d)
    ck("real-walk: no tweak-time blocks", p.returncode == 0 and "tweak-time" not in p.stdout,
       p.stdout + p.stderr)
    p = run(CHECKS / "check.py", [d, "--phase", "pre"], d)
    print("INFO real-walk: pre-check exit %d\n%s%s" % (p.returncode, p.stdout, p.stderr))
    ck("real-walk: pre-check has no tweak-time row", "tweak-time" not in p.stdout
       and "tweak-time" not in p.stderr and "Traceback" not in p.stderr
       and "QA:" in p.stdout and "map_check-crashed" not in p.stdout, p.stdout + p.stderr)


def tweak_rebuild(scratch):
    try:
        import make_tweaks
    except ImportError as e:
        print("SKIP tweak-rebuild: make_tweaks cannot import: %s" % e)
        return
    try:
        make_tweaks.find_tools()
    except SystemExit as e:
        if e.code != 2:
            raise
        print("SKIP tweak-rebuild: editor video tools unavailable")
        return
    d = Path(tempfile.mkdtemp(prefix="fx1-tweak-rebuild-", dir=scratch))
    text = json.dumps(dict(reel="syn", version="v1", words=[]))
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = make_tweaks.write_config(d, text)
    ck("tweak-rebuild: first config is written", result == "written"
       and (d / "tweak-board.config.json").read_bytes() == text.encode("utf-8"), result)
    ck("tweak-rebuild: no trial warning without a plan", "plan the trials again" not in output.getvalue(),
       output.getvalue())
    # An old timestamp makes an accidental rewrite visible even on coarse clocks.
    config = d / "tweak-board.config.json"
    os.utime(config, ns=(1000000000, 1000000000))
    before = config.stat().st_mtime_ns
    write(d / "trials/trials.json", {})
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = make_tweaks.write_config(d, text)
    ck("tweak-rebuild: identical bytes preserve mtime", result == "same"
       and config.stat().st_mtime_ns == before and config.read_bytes() == text.encode("utf-8"), result)
    ck("tweak-rebuild: unchanged board says nothing changed", output.getvalue().strip()
       == "syn v1: the Tweak Board is already up to date (nothing changed).", output.getvalue())
    changed = json.dumps(dict(reel="syn", version="v2", words=[]))
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = make_tweaks.write_config(d, changed)
    ck("tweak-rebuild: changed board writes and warns about the trial plan", result == "written"
       and config.read_bytes() == changed.encode("utf-8") and
       "This changes the Tweak Board, so the trial plan made before it is out of date: "
       "plan the trials again before making trial versions." in output.getvalue(), output.getvalue())


CASES = {"helper": helper, "synthetic": synthetic, "real-walk": walk, "tweak-rebuild": tweak_rebuild}


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
