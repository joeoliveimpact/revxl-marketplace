#!/usr/bin/env python3
"""N1.1a check for word_map.py + skills/_shared/checks/map_check.py: the word map holds every kept word at
out_in_f/fps + (src_t - src_in_f/fps)/speed, and the map check blocks a missing or stale map, a word more than
6 ms off, a missing word and a word listed twice, and passes a clean reel.

usage: python tests/editor/n1_map_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 = every check passed. --case runs one case; without it every case runs.
Cases: map, check, nospeed. Every input is a synthetic cuts.json (built by gaps.py's own snap_cuts) and edit map
built here (no media); the scripts run as `python -X utf8 -I` in the editor's Python (EDITOR_SE_HOME), else this one.
"""
import argparse, importlib.util, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut_safety_test as cs  # noqa: E402  (PY, sh(), run(), fresh(), module(), load())

CHECK = HERE.parents[1] / "plugins" / "editor-superengine" / "skills" / "_shared" / "checks" / "map_check.py"
FPS, SPEED = 30, 1.25
PIECES = [(1.0, 2.9), (5.0, 8.0), (10.0, 11.0)]          # source seconds -> frames 30-87, 150-240, 300-330
# (id, word, start, end, parakeet_start, status)
WORDS = [("w_0000", " So", 0.40, 0.60, 0.40, "aligned"),     # before piece 1: cut
         ("w_0001", " Data", 1.10, 1.40, 1.10, "aligned"),
         ("w_0002", " Dog", 1.45, 1.80, 1.45, "aligned"),
         ("w_0003", " watches", 2.00, 2.50, 2.00, "overlap"),
         ("w_0004", " um", 3.20, 3.50, 3.20, "aligned"),      # between pieces: cut
         ("w_0005", " every", 5.05, 5.40, 4.95, "aligned"),   # parakeet_start before piece 2, start inside: kept
         ("w_0006", " uh", 6.20, 6.40, 6.20, "unresolved"),   # not in the audio (gaps.py:433): never mapped
         ("w_0007", " server", 6.50, 6.90, 6.50, "aligned"),
         ("w_0008", " in", 7.00, 7.15, 7.00, "aligned"),
         ("w_0009", " real", 7.20, 7.50, 7.20, "aligned"),
         ("w_0010", " time.", 7.55, 7.95, 7.55, "aligned"),
         ("w_0011", " Right", 9.00, 9.30, 9.00, "aligned"),   # between pieces: cut
         ("w_0012", " now.", 10.00, 10.60, 10.00, "aligned")]  # starts exactly on piece 3's first frame: kept
KEPT = ["w_0001", "w_0002", "w_0003", "w_0005", "w_0007", "w_0008", "w_0009", "w_0010", "w_0012"]

fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def reel(S, name, pieces=PIECES, speed=SPEED):
    """A reel folder with work/cuts.json (gaps.py snap_cuts + write_cuts) and work/edit_map.json."""
    d = cs.fresh(S, name)
    g = cs.module("gaps.py")
    g.write_cuts(d / "work", g.snap_cuts(pieces, FPS, speed))
    (d / "work" / "edit_map.json").write_text(json.dumps({"words": [
        dict(id=i, word=t, start=s, end=e, parakeet_start=p, status=st, score_min=-1.0)
        for i, t, s, e, p, st in WORDS]}), encoding="utf-8")
    return d


def expected(cuts):
    """The formula, written out independently: every non-unresolved word whose start is in [src_in, src_out)."""
    fps, speed, out = cuts["fps"], cuts.get("speed", 1.0), []
    for i, t, s, e, p, st in WORDS:
        for k, g in enumerate(cuts["segments"]):
            a, b, c = g["src_in_f"] / fps, g["src_out_f"] / fps, g["out_in_f"] / fps
            if st != "unresolved" and a <= s < b:
                out.append((i, k, c + (s - a) / speed, c + (e - a) / speed))
    return out


def word_map(d):
    p = cs.run("word_map.py", d)
    return p, cs.load(d / "work" / "word_map.json")


def check(d):
    """(standalone run: exit code + stdout, run(ctx) in-process)."""
    p = cs.sh([cs.PY, "-X", "utf8", "-I", CHECK, d])
    return p, MC.run(dict(reel_dir=str(d), fps=FPS, cuts=None, beats=None, render=None))


def edit(d, fn):
    f = d / "work" / "word_map.json"
    m = cs.load(f)
    fn(m)
    f.write_text(json.dumps(m, indent=1), encoding="utf-8")


def nudge(d, wid, key, by):
    def fn(m):
        w = next(w for w in m["words"] if w["id"] == wid)
        w[key] = round(w[key] + by, 6)
    edit(d, fn)


def load_check():
    spec = importlib.util.spec_from_file_location("map_check", CHECK)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


MC = load_check()


def kinds(H):
    return [h["check"] for h in H]


# ------------------------------------------------------------------------------------------- map
def case_map(S, a):
    d = reel(S, "map")
    cuts = cs.load(d / "work" / "cuts.json")
    ck("map: fixture cuts.json is at speed %s with an out_in_f that rounds (%s)" % (SPEED, cuts["segments"][1]),
       cuts["speed"] == SPEED and cuts["segments"][1]["out_in_f"] == 46, cuts)
    p, m = word_map(d)
    print(p.stdout.rstrip())
    ck("map: word_map.py exits 0 and writes work/word_map.json", p.returncode == 0 and bool(m.get("words")),
       (p.returncode, p.stderr[-400:]))
    got = [w["id"] for w in m.get("words", [])]
    ck("map: every kept word, in order, nothing cut, no unresolved word: %s" % got, got == KEPT, got)
    exp = {i: (k, o0, o1) for i, k, o0, o1 in expected(cuts)}
    bad = [w for w in m.get("words", []) if w["id"] not in exp or exp[w["id"]][0] != w["seg"]
           or abs(w["out_start"] - exp[w["id"]][1]) > 1e-6 or abs(w["out_end"] - exp[w["id"]][2]) > 1e-6]
    ck("map: segment + output start/end = out_in_f/fps + (src_t - src_in_f/fps)/1.25 for every word",
       not bad and len(exp) == len(KEPT), bad)
    w5 = next((w for w in m.get("words", []) if w["id"] == "w_0005"), {})
    ck("map: 'every' at 46/30 + 0.05/1.25 = %.6f s" % (46 / 30 + 0.04),
       abs(w5.get("out_start", 0) - (46 / 30 + 0.04)) < 1e-6, w5)
    ck("map: carries id, word, seg, src_start/src_end, out_start/out_end per word",
       all(set(w) == {"id", "word", "seg", "src_start", "src_end", "out_start", "out_end"} for w in m.get("words", [])),
       (m.get("words") or [{}])[0])
    ck("map: records fps, speed and both input hashes",
       m.get("fps") == FPS and m.get("speed") == SPEED and len(m.get("cuts_sha256") or "") == 64
       and len(m.get("edit_map_sha256") or "") == 64, {k: m.get(k) for k in ("fps", "speed", "cuts_sha256")})
    ck("map: word_map.json is LF only", b"\r" not in (d / "work" / "word_map.json").read_bytes())


# ------------------------------------------------------------------------------------------- check
def case_check(S, a):
    ck("check: PHASE is 'pre'", getattr(MC, "PHASE", None) == "pre")
    d = reel(S, "check")
    p, H = check(d)
    ck("check: missing map blocks (word-map-missing), standalone exit 1",
       p.returncode == 1 and kinds(H) == ["word-map-missing"], (p.returncode, H, p.stdout[-300:]))
    ck("check: run(ctx) returns the contract shape [{check, level, msg, where}], level block|warn",
       isinstance(H, list) and H and all(isinstance(h, dict) and set(h) == {"check", "level", "msg", "where"}
                                          and h["level"] in ("block", "warn") for h in H), H)
    word_map(d)
    p, H = check(d)
    print(p.stdout.rstrip())
    ck("check: clean reel passes, run(ctx) == [] (a list), standalone exit 0",
       p.returncode == 0 and isinstance(H, list) and H == [], (p.returncode, H, p.stdout[-300:], p.stderr[-300:]))

    nudge(d, "w_0005", "out_start", 0.007)
    p, H = check(d)
    print(p.stdout.rstrip())
    ck("check: a word +7 ms off blocks (word-time on w_0005), standalone exit 1",
       p.returncode == 1 and kinds(H) == ["word-time"] and H[0]["level"] == "block" and "w_0005" in H[0]["where"],
       (p.returncode, H))
    word_map(d)
    nudge(d, "w_0005", "out_start", 0.005)
    p, H = check(d)
    ck("check: a word +5 ms off passes, exit 0", p.returncode == 0 and H == [], (p.returncode, H))
    word_map(d)
    nudge(d, "w_0010", "out_end", -0.007)
    p, H = check(d)
    ck("check: a word's end 7 ms early blocks too", p.returncode == 1 and kinds(H) == ["word-time"], (p.returncode, H))

    word_map(d)
    edit(d, lambda m: m.__setitem__("words", [w for w in m["words"] if w["id"] != "w_0008"]))
    p, H = check(d)
    ck("check: a kept word missing from the map blocks (word-missing on w_0008)",
       p.returncode == 1 and kinds(H) == ["word-missing"] and H[0]["where"].endswith("w_0008"), (p.returncode, H))

    word_map(d)
    edit(d, lambda m: m["words"].append(dict(m["words"][0], seg=1)))
    p, H = check(d)
    ck("check: a word listed in two segments blocks (word-twice)",
       p.returncode == 1 and kinds(H) == ["word-twice"], (p.returncode, H))

    word_map(d)
    g = cs.module("gaps.py")
    g.write_cuts(d / "work", g.snap_cuts([(1.0, 2.9), (5.0, 7.5), (10.0, 11.0)], FPS, SPEED))
    p, H = check(d)
    print(p.stdout.rstrip())
    ck("check: cuts.json changed after the map was written blocks (word-map-stale), exit 1",
       p.returncode == 1 and kinds(H) == ["word-map-stale"], (p.returncode, H))
    word_map(d)
    p, H = check(d)
    ck("check: rerunning word_map.py clears the stale block", p.returncode == 0 and H == [], (p.returncode, H))

    c = cs.load(d / "work" / "cuts.json")
    c["segments"] = [dict(src_in_f=30, src_out_f=87, out_in_f=0, out_out_f=46),
                     dict(src_in_f=45, src_out_f=105, out_in_f=46, out_out_f=94)]   # overlapping pieces
    (d / "work" / "cuts.json").write_text(json.dumps(c), encoding="utf-8")
    word_map(d)
    p, H = check(d)
    ck("check: words whose start sits in two overlapping pieces block (word-twice only)",
       p.returncode == 1 and H and set(kinds(H)) == {"word-twice"}, (p.returncode, H))

    (d / "work" / "word_map.json").unlink()
    p, H = check(d)
    ck("check: deleting the map blocks again (word-map-missing)", p.returncode == 1 and kinds(H) == ["word-map-missing"],
       (p.returncode, H))


# ------------------------------------------------------------------------------------------- nospeed
def case_nospeed(S, a):
    d = reel(S, "nospeed", speed=1.0)
    c = cs.load(d / "work" / "cuts.json")
    c.pop("speed")
    (d / "work" / "cuts.json").write_text(json.dumps(c), encoding="utf-8")
    p, m = word_map(d)
    exp = {i: (o0, o1) for i, k, o0, o1 in expected(c)}
    ck("nospeed: cuts.json without speed reads as 1.0 (H-S4b-4)", m.get("speed") == 1.0 and bool(m.get("words"))
       and all(abs(w["out_start"] - exp[w["id"]][0]) < 1e-6 for w in m["words"]), (m.get("words") or [])[:2])
    p, H = check(d)
    ck("nospeed: map check passes it", p.returncode == 0 and H == [], (p.returncode, H))


CASES = {"map": case_map, "check": case_check, "nospeed": case_nospeed}


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
