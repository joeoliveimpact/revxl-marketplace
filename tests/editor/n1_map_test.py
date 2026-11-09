#!/usr/bin/env python3
"""N1.1a + N1.1b check for word_map.py + skills/_shared/checks/map_check.py: the word map holds every kept word at
out_in_f/fps + (src_t - src_in_f/fps)/speed (aligned start) and its board anchor time (parakeet_start), read from
the edit map the cut was made from; the map check blocks a missing or stale map, a word more than 6 ms off, a
missing word and a word listed twice, and passes a clean reel (N1.1a). With a Cut Board ruling it also checks the
cut against the picks (quote checks), checks the Tweak Board's word times against the anchor time (H-N1-9), and the
standalone run writes work/map_check.json (H-N1-10) (N1.1b). N1.1c (H-N1-13): the Tweak Board is checked only while
it was built from the current cuts.json, else one warn (F1); with no edit map, tx.json's word times are checked, and
with no word times at all one warn and exit 0 (F2); a ruling on take 2 is checked against work/take2/cuts.json (F3).

usage: python tests/editor/n1_map_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 = every check passed. --case runs one case; without it every case runs.
Cases: map, check, nospeed (N1.1a); board, shift, twice, struck, swap, take2, anchor, noboard, real (N1.1b);
tweakstale, txmap, notimes, take2dir (N1.1c; tweakstale runs the real make_tweaks.py on a 3 s tone); take2merged (H-EGM6-1).
Every input except `real` is a synthetic cuts.json (built by gaps.py's own snap_cuts), edit map, cut-board config
and selection built here (no media). `real` runs S3's work files (copied, read only) through the real make_board.py,
selection_to_edl.py and gaps.py (no Chrome, no render), prints what the map check says as INFO, and (N1.4b) asserts
zero blocks and every picked word whole inside one piece. The scripts run as `python -X utf8 -I` in the editor's Python
(EDITOR_SE_HOME), else this one.
"""
import argparse, collections, importlib.util, json, shlex, shutil, sys
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
    return ok


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
    ck("map: carries id, word, seg, src_start/src_end, out_start/out_end, parakeet_start/out_anchor per word",
       all(set(w) == {"id", "word", "seg", "src_start", "src_end", "out_start", "out_end", "parakeet_start",
                      "out_anchor"} for w in m.get("words", [])),
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


# ------------------------------------------------------------------------------------------- N1.1b board fixtures
# (id, word, start, end, parakeet_start, status): three script lines, a filler between L01 and L02, a breath event
BW = [("w_0000", " Big", 1.00, 1.25, 1.00, "aligned"),
      ("w_0001", " sale", 1.30, 1.55, 1.30, "aligned"),
      ("w_0002", " today.", 1.60, 1.95, 1.60, "aligned"),
      ("w_0003", " um", 2.40, 2.60, 2.40, "aligned"),          # between L01 and L02: in no line
      ("w_0004", " Everything", 3.00, 3.35, 3.00, "aligned"),
      ("w_0005", " is", 3.44, 3.55, 3.40, "aligned"),         # aligned start 40 ms after parakeet_start
      ("w_0006", " half", 3.60, 3.85, 3.60, "aligned"),
      ("w_0007", " off.", 3.90, 4.20, 3.90, "aligned"),
      ("w_0008", " Come", 5.00, 5.25, 5.00, "aligned"),
      ("w_0009", " in", 5.30, 5.45, 5.30, "unresolved"),      # picked, inside the piece, not in the audio
      ("w_0010", " now.", 5.60, 5.95, 5.60, "aligned")]
EVENTS = [("v_0000", "[breath]", 4.50, 4.70)]
LINES = [("L01", ["w_0000", "w_0001", "w_0002"]), ("L02", ["w_0004", "w_0005", "w_0006", "w_0007"]),
         ("L03", ["w_0008", "w_0009", "w_0010"])]
CLEAN = [(0.9, 2.0), (2.9, 4.3), (4.9, 6.0)]     # each line's read, in script order
T2 = 20.0                                       # take 2 is the same read 20 s later in its own edit map
KEPT_B = [w[0] for w in BW if w[0] not in ("w_0003", "w_0009")]


def write(path, obj):
    b = json.dumps(obj, indent=1).encode("utf-8")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(b)


def board_map(shift=0.0):
    return {"words": [dict(id=i, word=t, start=round(s + shift, 3), end=round(e + shift, 3),
                           parakeet_start=round(p + shift, 3), status=st, score_min=-1.0) for i, t, s, e, p, st in BW],
            "events": [dict(id=i, word=t, start=round(s + shift, 3), end=round(e + shift, 3)) for i, t, s, e in EVENTS]}


def board_cfg(ems):
    """A cut-board.config.json in make_board.py's shape (the fields the checks read): takes[n].words is
    build_edit_map.board_sequence() of the take's map, attempts[].words[].i indexes it, one attempt per take."""
    bem = cs.module("build_edit_map.py")
    takes = {str(n): dict(n=n, edit_map=rel, words=bem.board_sequence(m)) for n, (rel, m) in ems.items()}
    lines = []
    for lid, ids in LINES:
        atts = []
        for n in ems:
            seq = takes[str(n)]["words"]
            ix = {w["id"]: k for k, w in enumerate(seq)}
            atts.append(dict(take=n, words=[dict(i=ix[w], w=seq[ix[w]]["word"].strip(), s=seq[ix[w]]["start"],
                                                 cin=round(seq[ix[w]]["start"] - 0.05, 3)) for w in ids]))
        lines.append(dict(id=lid, attempts=atts, default=0))
    return dict(reel="REEL_018", lines=lines, takes=takes)


def sel_of(picks, rm=None):
    """cut-selection.json: picks = {line id: attempt index}; rm = {line id: [board word ids struck]}."""
    return dict(v=2, reel="REEL_018", lines=[dict(id=lid, pick=picks.get(lid, 0), drop=False, rm=(rm or {}).get(lid, {}))
                                             for lid, _ in LINES])


def board_idx(d, take, wid):
    seq = cs.load(d / "cut-board.config.json")["takes"][str(take)]["words"]
    return next(k for k, w in enumerate(seq) if w["id"] == wid)


def cut_to(d, pieces, shift=0.0):
    g = cs.module("gaps.py")
    g.write_cuts(d / "work", g.snap_cuts([(a + shift, b + shift) for a, b in pieces], FPS, SPEED))


def board_reel(S, name, pieces=CLEAN, take2=False, picks=None):
    d = cs.fresh(S, name)
    ems = {1: ("work/edit_map.json", board_map())}
    if take2:
        ems[2] = ("work/edit_map.take2.json", board_map(T2))
    for rel, m in ems.values():
        write(d / rel, m)
    write(d / "cut-board.config.json", board_cfg(ems))
    write(d / "cut-selection.json", sel_of(picks or {}))
    cut_to(d, pieces)
    return d


def report(d):
    return cs.load(d / "work" / "map_check.json")


def msgs(H):
    return [h["msg"] for h in H]


def blocks(H):
    return [h for h in H if h["level"] == "block"]


# ------------------------------------------------------------------------------------------- board
def case_board(S, a):
    d = board_reel(S, "board")
    p, m = word_map(d)
    print(p.stdout.rstrip())
    ck("board: word_map reads work/edit_map.json for take 1 and records it with its sha256",
       m.get("edit_map") == "work/edit_map.json" and m.get("edit_map_sha256") == MC.word_map.sha(d / "work/edit_map.json"),
       {k: m.get(k) for k in ("edit_map", "edit_map_sha256")})
    ck("board: the map keeps every line word, no filler, no unresolved word: %s" % [w["id"] for w in m.get("words", [])],
       [w["id"] for w in m.get("words", [])] == KEPT_B)
    p, H = check(d)
    print(p.stdout.rstrip())
    ck("board: a clean board reel passes (run(ctx) == [], exit 0), the unresolved picked word 'in' (L03) included",
       p.returncode == 0 and H == [], (p.returncode, H))
    f = d / "work" / "map_check.json"
    ck("board: work/map_check.json is {'blocks': [], 'warns': []} when clean, LF only",
       report(d) == {"blocks": [], "warns": []} and b"\r" not in f.read_bytes(), report(d))
    f.unlink()
    MC.run(dict(reel_dir=str(d), fps=FPS, cuts=None, beats=None, render=None))
    ck("board: run(ctx) writes nothing (map_check.json not recreated)", not f.exists())
    q, struck = MC.quote(cs.load(d / "cut-board.config.json"), cs.load(d / "cut-selection.json"), board_map())
    ck("board: the quote is the picked words in script order, unresolved left out",
       [w for _, w, _ in q] == KEPT_B and q[0][0] == "L01" and q[-1][0] == "L03" and struck == {}, q)


# ------------------------------------------------------------------------------------------- shift
def case_shift(S, a):
    d = board_reel(S, "shift", pieces=[(1.25, 2.6), (2.9, 4.3), (4.9, 6.0)])   # L01's range a phrase late
    word_map(d)
    p, H = check(d)
    print(p.stdout.rstrip())
    want = ["line L01: the word 'Big' was picked but is not in the cut.",
            "line L01: the cut also keeps the word 'um', which is not in the picked words (a cut edge has moved)."]
    ck("shift: a range shifted by a phrase blocks: 'Big' missing and 'um' extra, both on L01, exit 1",
       p.returncode == 1 and sorted(kinds(H)) == ["quote-extra", "quote-missing"] and sorted(msgs(H)) == sorted(want),
       (p.returncode, H))
    r = report(d)
    ck("shift: work/map_check.json holds the block reasons, no warns",
       sorted(h["msg"] for h in r.get("blocks", [])) == sorted(want) and r.get("warns") == [], r)


# ------------------------------------------------------------------------------------------- twice
def case_twice(S, a):
    d = board_reel(S, "twice", pieces=[(0.9, 2.0), (2.9, 4.3), (1.55, 1.9), (4.9, 6.0)])   # 'today.' cut in again
    word_map(d)
    p, H = check(d)
    print(p.stdout.rstrip())
    qt = [h for h in H if h["check"] == "quote-twice"]
    ck("twice: a picked word in two pieces blocks (quote-twice on L01 'today.', besides word-twice), exit 1",
       p.returncode == 1 and set(kinds(H)) == {"word-twice", "quote-twice"} and len(qt) == 1
       and qt[0]["msg"].startswith("line L01: the word 'today.' was picked once but plays twice"), (p.returncode, H))


# ------------------------------------------------------------------------------------------- struck
def case_struck(S, a):
    d = board_reel(S, "struck")
    s = cs.load(d / "cut-selection.json")
    s["lines"][1]["rm"] = {"0": [board_idx(d, 1, "w_0006")]}          # 'half' struck on L02, cut left whole
    write(d / "cut-selection.json", s)
    word_map(d)
    p, H = check(d)
    print(p.stdout.rstrip())
    ck("struck: a struck word inside a kept piece blocks: 'line L02: the word 'half' was struck but is still in the cut.'",
       p.returncode == 1 and kinds(H) == ["quote-extra"]
       and "line L02: the word 'half' was struck but is still in the cut." in H[0]["msg"], (p.returncode, H))
    cut_to(d, [(0.9, 2.0), (2.9, 3.58), (3.88, 4.3), (4.9, 6.0)])     # the cut that honours the strike
    word_map(d)
    p, H = check(d)
    ck("struck: the cut without 'half' passes", p.returncode == 0 and H == [], (p.returncode, H))


# ------------------------------------------------------------------------------------------- swap
def case_swap(S, a):
    d = board_reel(S, "swap", pieces=[(2.9, 4.3), (0.9, 2.0), (4.9, 6.0)])   # L02 plays before L01
    word_map(d)
    p, H = check(d)
    print(p.stdout.rstrip())
    ck("swap: two pieces swapped in output order block once (quote-order: L02 'Everything' before L01 'today.')",
       p.returncode == 1 and kinds(H) == ["quote-order"]
       and H[0]["msg"] == "line L02: the word 'Everything' plays before 'today.' (line L01) in the cut, but the picks "
                          "put it after.", (p.returncode, H))


# ------------------------------------------------------------------------------------------- take2
def case_take2(S, a):
    d = board_reel(S, "take2", take2=True, picks={lid: 1 for lid, _ in LINES})
    cut_to(d, CLEAN, shift=T2)
    p, m = word_map(d)
    print(p.stdout.rstrip())
    w0 = next((w for w in m.get("words", []) if w["id"] == "w_0000"), {})
    ck("take2: a take-2 ruling makes word_map read work/edit_map.take2.json (path + sha256 recorded, 'Big' at %s s)"
       % w0.get("src_start"), p.returncode == 0 and m.get("edit_map") == "work/edit_map.take2.json"
       and m.get("edit_map_sha256") == MC.word_map.sha(d / "work/edit_map.take2.json")
       and w0.get("src_start") == 1.0 + T2 and [w["id"] for w in m["words"]] == KEPT_B, (p.returncode, p.stderr, m))
    p, H = check(d)
    ck("take2: the map check passes the take-2 cut", p.returncode == 0 and H == [], (p.returncode, H))
    s = cs.load(d / "cut-selection.json")
    write(d / "cut-selection.json", sel_of({}))                          # re-ruled on take 1, map not rebuilt
    p, H = check(d)
    ck("take2: switching the ruling to take 1 makes the take-2 map stale (word-map-stale)",
       p.returncode == 1 and kinds(H) == ["word-map-stale"], (p.returncode, H))
    write(d / "cut-selection.json", sel_of({"L01": 0, "L02": 1, "L03": 1}))   # mixed takes
    p, _ = word_map(d)
    pc, H = check(d)
    # N4: a mixed ruling is allowed now (each cut piece names its take); against this single-take cut.json the
    # picked take-1 words aren't in the cut, so the map check still blocks it, as missing quotes
    ck("take2: a ruling mixing takes runs word_map.py (N4) and the map check blocks the single-take cut (quote-missing)",
       p.returncode == 0 and pc.returncode == 1 and H and set(kinds(H)) == {"quote-missing"},
       (p.returncode, p.stderr[-300:], H))
    write(d / "cut-selection.json", s)


# ------------------------------------------------------------------------------------------- anchor (H-N1-9)
def tweak(d, m, shift=None):
    """tweak-board.config.json words as make_tweaks.py writes them: t = c0 + (parakeet_start - s0)/speed, rounded
    to 1 ms, every board word whose parakeet_start is in a piece (unresolved ones too). shift = {id: t override}."""
    cuts = cs.load(d / "work" / "cuts.json")
    out = []
    for g in cuts["segments"]:
        c0, s0, s1 = g["out_in_f"] / FPS, g["src_in_f"] / FPS, g["src_out_f"] / FPS
        for i, t, s, e, pk, st in BW:
            if s0 <= pk < s1:
                out.append(dict(id=i, w=t.strip(), t=round(c0 + (pk - s0) / SPEED, 3)))
    for x in out:
        if shift and x["id"] in shift:
            x["t"] = shift[x["id"]](m)
    write(d / "tweak-board.config.json", dict(reel="REEL_018", words=out,
                                              cuts_sha256=MC.word_map.sha(d / "work" / "cuts.json")))


def case_anchor(S, a):
    d = board_reel(S, "anchor")
    p, m = word_map(d)
    w5 = next((w for w in m.get("words", []) if w["id"] == "w_0005"), {})
    ck("anchor: 'is' (aligned start 40 ms after parakeet_start) carries both: out_anchor = out_start - 0.040/%s" % SPEED,
       w5.get("parakeet_start") == 3.40 and abs(w5.get("out_anchor", 0) - (w5.get("out_start", 0) - 0.040 / SPEED)) < 1e-6,
       w5)
    tweak(d, m)
    p, H = check(d)
    print(p.stdout.rstrip())
    ck("anchor: tweak t from parakeet_start passes; the unresolved 'in' the Tweak Board lists is a warn only, exit 0",
       p.returncode == 0 and kinds(H) == ["tweak-word"] and H[0]["level"] == "warn" and "w_0009" in H[0]["where"],
       (p.returncode, H))
    r = report(d)
    ck("anchor: work/map_check.json lists the warn under warns, no blocks",
       r.get("blocks") == [] and [h["check"] for h in r.get("warns", [])] == ["tweak-word"], r)
    at = lambda by: (lambda m: round(next(w for w in m["words"] if w["id"] == "w_0005")[by[0]] + by[1], 6))
    tweak(d, m, {"w_0005": at(("out_start", 0))})
    p, H = check(d)
    ck("anchor: tweak t from the aligned start (32 ms off the anchor) blocks (tweak-time on w_0005)",
       p.returncode == 1 and [h["check"] for h in blocks(H)] == ["tweak-time"] and "w_0005" in blocks(H)[0]["where"],
       (p.returncode, H))
    for by, ok in ((0.006, True), (0.007, False)):
        tweak(d, m, {"w_0005": at(("out_anchor", by))})
        p, H = check(d)
        ck("anchor: tweak t = anchor + %d ms %s" % (by * 1000, "passes" if ok else "blocks"),
           (p.returncode == 0 and not blocks(H)) if ok else (p.returncode == 1 and [h["check"] for h in blocks(H)] == ["tweak-time"]),
           (p.returncode, H))
    tweak(d, m)
    for by, ok in ((0.007, False), (0.005, True), (0.006, True)):
        word_map(d)
        nudge(d, "w_0005", "out_start", by)
        p, H = check(d)
        ck("anchor: the render map still checks the aligned out_start: +%d ms %s" % (by * 1000, "passes" if ok else "blocks"),
           (p.returncode == 0 and not blocks(H)) if ok else (p.returncode == 1 and [h["check"] for h in blocks(H)] == ["word-time"]),
           (p.returncode, H))


# ------------------------------------------------------------------------------------------- noboard
def case_noboard(S, a):
    d = reel(S, "noboard")
    word_map(d)
    p, H = check(d)
    ck("noboard: a no-board reel that cuts words passes, no quote check runs", p.returncode == 0 and H == [], (p.returncode, H))
    d = board_reel(S, "noboard-shift", pieces=[(1.25, 2.6), (2.9, 4.3), (4.9, 6.0)], take2=True)
    (d / "cut-selection.json").unlink()
    p, m = word_map(d)
    pc, H = check(d)
    ck("noboard: board config without a selection: word_map reads work/edit_map.json, quote checks skipped (no block)",
       m.get("edit_map") == "work/edit_map.json" and pc.returncode == 0 and H == [], (m.get("edit_map"), pc.returncode, H))
    write(d / "cut-selection.json", sel_of({}))
    pc, H = check(d)
    ck("noboard: the same cut with the selection back blocks (quote checks run)",
       pc.returncode == 1 and set(kinds(H)) == {"quote-missing", "quote-extra"}, (pc.returncode, H))


# ------------------------------------------------------------------------------------------- real
def case_real(S, a):
    """S3's take through the real make_board.py, selection_to_edl.py and gaps.py: the script is the take's own
    sentences, every line keeps its first attempt, nothing struck. The map check's findings are printed as INFO.
    N1.4b (H-N1-11): gaps.py leaves out the word before L21 ('And') and L31 ("it's") instead of pulling it in, keeps
    L07's own 'It's' whole, the map check has zero blocks and every picked word is whole inside one piece."""
    d = cs.fresh(S, "REEL_018")
    fx = Path(cs.S3_WORK)
    for n in ("edit_map.json", "tx.16k.wav", "probe.json", "envelope.json"):
        shutil.copyfile(fx / n, d / "work" / n)
    em = cs.load(d / "work" / "edit_map.json")
    lines, cur = [], []
    for w in em["words"]:
        cur.append(w["word"].strip())
        if cur[-1].endswith((".", "?", "!")):
            lines.append(" ".join(cur))
            cur = []
    lines += [" ".join(cur)] if cur else []
    (d / "script.md").write_bytes(("# Test script\n---\n" + "\n".join(lines) + "\n").encode("utf-8"))
    write(d / "shots.json", {"vocab": ["talking head", "screen"], "default": "talking head"})
    p = cs.run("make_board.py", "--script", d / "script.md",
               "--take", "1:%s:%s" % (d / "work/edit_map.json", d / "work/tx.16k.wav"),
               "--shots", d / "shots.json", "--reel", "REEL_018", "-o", d, cwd=S)
    print(p.stdout.splitlines()[0] if p.stdout else p.stderr[-400:])
    if not ck("real: make_board.py builds the board", p.returncode == 0, (p.returncode, p.stderr[-500:])):
        return
    cfg = cs.load(d / "cut-board.config.json")
    sel = dict(v=2, reel="REEL_018", gap_default_ms=cfg["gap_default_ms"], speed=1.0, beat_ms=cfg["beat_ms"],
               word_list_hash={n: t["word_list_hash"] for n, t in cfg["takes"].items()}, board_hash=cfg["board_hash"],
               lines=[dict(id=l["id"], pick=0 if l["attempts"] else None, drop=not l["attempts"], flag=None, note="",
                           gap_after={"mode": "default"}, shot=None, rm={}, sil={}) for l in cfg["lines"]])
    write(d / "cut-selection.json", sel)
    p = cs.run("selection_to_edl.py", d / "cut-selection.json", d / "cut-board.config.json", cwd=S)
    line = next((ln for ln in p.stdout.splitlines() if "gaps.py" in ln), "")
    if not ck("real: selection_to_edl.py writes the EDL and the gaps.py command", p.returncode == 0 and line,
              (p.returncode, p.stderr[-400:])):
        return
    plugin = HERE.parents[1] / "plugins" / "editor-superengine"
    g = cs.sh(shlex.split(line.replace("<editor python>", Path(cs.PY).as_posix())
                          .replace("${CLAUDE_PLUGIN_ROOT}", plugin.as_posix())), cwd=S)
    if not ck("real: gaps.py writes cuts.json", g.returncode == 0 and (d / "work/cuts.json").is_file(),
              (g.returncode, g.stderr[-400:])):
        return
    p, m = word_map(d)
    print(p.stdout.rstrip())
    if not ck("real: word_map.py maps the cut", p.returncode == 0 and m.get("words"), (p.returncode, p.stderr[-400:])):
        return
    p, H = check(d)
    r = report(d)
    ck("real: the standalone run and run(ctx) agree, and work/map_check.json lists the same blocks (exit %d)" % p.returncode,
       p.returncode == (1 if blocks(H) else 0) and r.get("blocks") == blocks(H), (p.returncode, len(H), len(r.get("blocks", []))))
    kept = [l for l in sel["lines"] if not l["drop"]]
    print("INFO real: %d script lines, %d kept (first attempt), %d pieces, %d mapped words, speed %s"
          % (len(sel["lines"]), len(kept), len(cs.load(d / "work/cuts.json")["segments"]), len(m["words"]), m["speed"]))
    print("INFO real: map check: %d block(s), %d warn(s): %s" % (len(blocks(H)), len(H) - len(blocks(H)),
                                                               dict(collections.Counter(kinds(H)))))
    for h in H:
        print("INFO real: %s %s %s  (%s)" % (h["level"].upper(), h["check"], h["msg"], h["where"]))
    ck("real: the map check has zero blocks (L21 and L31 gone)", not blocks(H)
       and not any(x in h["msg"] for h in H for x in ("line L21", "line L31")), [h["msg"] for h in blocks(H)])
    plan = (d / "work/gap-plan.txt").read_text(encoding="utf-8")
    cuts, byid, tw = cs.load(d / "work/cuts.json"), {w["id"]: w for w in em["words"]}, cfg["takes"]["1"]["words"]
    segs = [(g["src_in_f"] / cuts["fps"], g["src_out_f"] / cuts["fps"]) for g in cuts["segments"]]
    ck("real: 'And' and \"it's\" (not picked) are out of the cut and L07's 'It's' stays whole",
       all(all(byid[wid]["end"] <= a0 or byid[wid]["start"] >= b0 for a0, b0 in segs) for wid in ("w_0130", "w_0216"))
       and "EDGE moved to keep 'It's'" in plan, [ln for ln in plan.splitlines() if "EDGE" in ln])
    lines, picked = {ln["id"]: ln for ln in cfg["lines"]}, []
    for ln in kept:
        for x in lines[ln["id"]]["attempts"][ln["pick"]]["words"]:
            w = byid.get(tw[x["i"]].get("id"))
            if w and w.get("status") != "unresolved":   # gaps.py skips unresolved words (not in the audio)
                picked.append((ln["id"], w))
    clipped = [(lid, w["word"], w["start"], w["end"]) for lid, w in picked
               if not any(a0 <= w["start"] and w["end"] <= b0 for a0, b0 in segs)]
    ck("real: every picked word (%d) is whole inside one piece of cuts.json" % len(picked), picked and not clipped,
       clipped[:6])


# ------------------------------------------------------------------------------------------- N1.1c (H-N1-13)
OLD_TWEAK = "Tweak Board is from an older cut, rebuild it to re-check timing"
NO_TIMES = "No word timings on this computer, so the word check was skipped; the cut can still render"


def case_tweakstale(S, a):
    """F1: the real make_tweaks.py stamps the cuts.json it read; the tweak check runs only while that still matches."""
    d = board_reel(S, "tweakstale")
    p, m = word_map(d)
    cut = d / "work" / "renders" / "cut.mp4"
    cut.parent.mkdir(parents=True, exist_ok=True)
    cs.ff("-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-c:a", "aac", cut)
    p = cs.run("make_tweaks.py", "--cut", cut, "--work", d / "work", "--config", d / "cut-board.config.json",
               "--take", "1", "-o", d)
    tb = cs.load(d / "tweak-board.config.json")
    if not ck("tweakstale: make_tweaks.py stamps cuts_sha256 = sha256 of the cuts.json it read",
              p.returncode == 0 and tb.get("cuts_sha256") == MC.word_map.sha(d / "work" / "cuts.json"),
              (p.returncode, p.stderr[-400:], tb.get("cuts_sha256"))):
        return
    p, H = check(d)
    ck("tweakstale: the board as built passes (no block, exit 0)", p.returncode == 0 and not blocks(H), (p.returncode, H))
    anchor = next(w for w in m["words"] if w["id"] == "w_0005")["out_anchor"]
    next(x for x in tb["words"] if x["id"] == "w_0005")["t"] = round(anchor + 0.007, 6)
    write(d / "tweak-board.config.json", tb)
    p, H = check(d)
    ck("tweakstale: board from the current cuts.json with 'is' 7 ms off blocks (tweak-time), exit 1",
       p.returncode == 1 and [h["check"] for h in blocks(H)] == ["tweak-time"] and "w_0005" in blocks(H)[0]["where"],
       (p.returncode, H))
    cut_to(d, [(0.9, 2.0), (2.8, 4.3), (4.9, 6.0)])     # a Stage 9 round moves piece 2's in-point: L02 plays 80 ms later
    word_map(d)
    p, H = check(d)
    print(p.stdout.rstrip())
    r = report(d)
    ck("tweakstale: the same board after cuts.json changed: one warn '%s', no block, exit 0" % OLD_TWEAK,
       p.returncode == 0 and kinds(H) == ["tweak-stale"] and H[0]["level"] == "warn" and H[0]["msg"] == OLD_TWEAK
       and r.get("blocks") == [] and [h["check"] for h in r.get("warns", [])] == ["tweak-stale"], (p.returncode, H))
    cut_to(d, CLEAN)
    word_map(d)
    tb.pop("cuts_sha256")
    write(d / "tweak-board.config.json", tb)
    p, H = check(d)
    ck("tweakstale: a board with no cuts_sha256 gives the same warn, no block, exit 0",
       p.returncode == 0 and kinds(H) == ["tweak-stale"] and H[0]["msg"] == OLD_TWEAK, (p.returncode, H))


def tx_reel(S, name, tx):
    """reel() without an edit map: work/cuts.json, and work/tx.json = tx when given."""
    d = reel(S, name)
    (d / "work" / "edit_map.json").unlink()
    if tx is not None:
        write(d / "work" / "tx.json", tx)
    return d


def case_txmap(S, a):
    """F2: no edit map (no word alignment) but tx.json word times: the map is built from them and checked."""
    tx = {"text": "", "words": [dict(i=k, word=t, start=s, end=e) for k, (i, t, s, e, p, st) in enumerate(WORDS)]
          + [dict(i=len(WORDS), word="[breath]", start=10.70, end=10.80)]}     # an event inside piece 3: never mapped
    d = tx_reel(S, "txmap", tx)
    p, m = word_map(d)
    print(p.stdout.rstrip())
    ids = [w["id"] for w in m.get("words", [])]
    want = sorted(KEPT + ["w_0006"])     # tx.json has no 'unresolved' mark, so 'uh' (inside piece 2) is kept
    ck("txmap: word_map.py builds the map from work/tx.json (edit_map recorded as work/tx.json, cut work/cuts.json): %s"
       % ids, p.returncode == 0 and m.get("edit_map") == "work/tx.json" and m.get("cuts") == "work/cuts.json"
       and m.get("edit_map_sha256") == MC.word_map.sha(d / "work/tx.json") and ids == want, (p.returncode, p.stderr[-300:], m))
    ck("txmap: aligned start = tx start, anchor = the same time (out_anchor == out_start)",
       all(w["parakeet_start"] == w["src_start"] and w["out_anchor"] == w["out_start"] for w in m.get("words", [])))
    p, H = check(d)
    ck("txmap: the clean map passes, exit 0", p.returncode == 0 and H == [], (p.returncode, H))
    nudge(d, "w_0005", "out_start", 0.007)
    p, H = check(d)
    print(p.stdout.rstrip())
    ck("txmap: 'every' +7 ms off blocks (word-time on w_0005), exit 1",
       p.returncode == 1 and kinds(H) == ["word-time"] and "w_0005" in H[0]["where"], (p.returncode, H))


def case_notimes(S, a):
    """F2: no edit map and no word times anywhere: one plain warn, nothing blocks, both scripts exit 0."""
    for name, tx in (("notimes", None), ("notimes-tx", {"text": "Hi there", "words": [{"word": " Hi"}]})):
        d = tx_reel(S, name, tx)
        p = cs.run("word_map.py", d)
        ck("%s: word_map.py says '%s', writes no map, exit 0" % (name, NO_TIMES),
           p.returncode == 0 and NO_TIMES in p.stdout and not (d / "work" / "word_map.json").exists(),
           (p.returncode, p.stdout[-300:], p.stderr[-300:]))
        p, H = check(d)
        print(p.stdout.rstrip())
        r = report(d)
        ck("%s: map check gives exactly one warn with that sentence, no block, exit 0" % name,
           p.returncode == 0 and kinds(H) == ["no-word-times"] and H[0]["level"] == "warn" and H[0]["msg"] == NO_TIMES
           and r.get("blocks") == [] and [h["msg"] for h in r.get("warns", [])] == [NO_TIMES], (p.returncode, H, r))


def case_take2dir(S, a):
    """F3: a take-2 ruling (take 2's own folder, work/take2/, as SKILL.md Stage 0 lays it out) is checked against
    work/take2/cuts.json; work/cuts.json is ignored."""
    d = cs.fresh(S, "take2dir")
    ems = {1: ("work/edit_map.json", board_map()), 2: ("work/take2/edit_map.json", board_map(T2))}
    for rel, em in ems.values():
        write(d / rel, em)
    write(d / "cut-board.config.json", board_cfg(ems))
    write(d / "cut-selection.json", sel_of({lid: 1 for lid, _ in LINES}))
    g = cs.module("gaps.py")
    put = lambda w, pieces, sh: g.write_cuts(d / w, g.snap_cuts([(x + sh, y + sh) for x, y in pieces], FPS, SPEED))
    late = [(1.25, 2.6), (2.9, 4.3), (4.9, 6.0)]          # L01's range a phrase late (as in case shift)
    put("work", late, 0.0)                                 # take 1's folder: would block if it were read
    put("work/take2", CLEAN, T2)
    p, m = word_map(d)
    print(p.stdout.rstrip())
    ck("take2dir: word_map reads work/take2/cuts.json (cuts + sha256 recorded) and take 2's edit map",
       p.returncode == 0 and m.get("cuts") == "work/take2/cuts.json"
       and m.get("cuts_sha256") == MC.word_map.sha(d / "work/take2/cuts.json")
       and m.get("edit_map") == "work/take2/edit_map.json" and [w["id"] for w in m["words"]] == KEPT_B,
       (p.returncode, p.stderr[-300:], {k: m.get(k) for k in ("cuts", "edit_map")}))
    p, H = check(d)
    ck("take2dir: the clean take-2 cut passes although work/cuts.json would block, exit 0",
       p.returncode == 0 and H == [], (p.returncode, H))
    put("work", CLEAN, 0.0)
    p, H = check(d)
    ck("take2dir: changing work/cuts.json changes nothing (not stale, still clean)", p.returncode == 0 and H == [],
       (p.returncode, H))
    put("work/take2", late, T2)                            # the planted error, in take 2's cuts.json
    p, H = check(d)
    ck("take2dir: changing work/take2/cuts.json makes the map stale (word-map-stale)",
       p.returncode == 1 and kinds(H) == ["word-map-stale"], (p.returncode, H))
    word_map(d)
    p, H = check(d)
    print(p.stdout.rstrip())
    ck("take2dir: the planted error in work/take2/cuts.json blocks: 'Big' missing and 'um' extra on L01, exit 1",
       p.returncode == 1 and sorted(kinds(H)) == ["quote-extra", "quote-missing"]
       and all("line L01" in h["msg"] for h in H), (p.returncode, H))


def case_take2merged(S, a):
    """H-EGM6-1: a takes.py cut containing only take 2 uses its words, with or without a board ruling."""
    d = cs.fresh(S, "take2merged")
    first, second = board_map(), board_map()
    first["words"][0]["word"], second["words"][0]["word"] = " FirstOnly", " SecondOnly"
    ems = {1: ("work/edit_map.json", first), 2: ("work/take2/edit_map.json", second)}
    for rel, em in ems.values():
        write(d / rel, em)
    write(d / "cut-board.config.json", board_cfg(ems))
    write(d / "cut-selection.json", sel_of({lid: 1 for lid, _ in LINES}))
    g = cs.module("gaps.py")
    cuts = g.snap_cuts(CLEAN, FPS, SPEED)
    # takes.py writes raw/work per take and a take number on each merged segment.
    cuts["takes"] = {"2": dict(raw="take2.mp4", work="work/take2")}
    cuts["segments"] = [dict(s, take=2) for s in cuts["segments"]]
    write(d / "work/cuts.json", cuts)
    ck("take2merged: take 2 has no local cuts.json", not (d / "work/take2/cuts.json").exists())
    for ruling in ("board", "no board"):
        if ruling == "no board":
            (d / "cut-board.config.json").unlink()
            (d / "cut-selection.json").unlink()
        p, m = word_map(d)
        words = [w["word"] for w in m.get("words", [])]
        ck("take2merged (%s): word map exits 0, keeps SecondOnly and excludes FirstOnly" % ruling,
           p.returncode == 0 and "SecondOnly" in words and "FirstOnly" not in words,
           (p.returncode, p.stderr[-300:], words))
        ck("take2merged (%s): merged cut and take 2 map are the recorded sources" % ruling,
           m.get("cuts") == "work/cuts.json" and m.get("edit_map") == {"2": "work/take2/edit_map.json"},
           {k: m.get(k) for k in ("cuts", "edit_map")})
        p, H = check(d)
        ck("take2merged (%s): map check passes, exit 0" % ruling, p.returncode == 0 and H == [],
           (p.returncode, H))
    d = reel(S, "take2merged-plain")
    p, m = word_map(d)
    ck("take2merged: plain single-take sources and word IDs keep their existing shape",
       p.returncode == 0 and m.get("cuts") == "work/cuts.json" and m.get("edit_map") == "work/edit_map.json"
       and [w["id"] for w in m.get("words", [])] == KEPT, (p.returncode, m))
    p, H = check(d)
    ck("take2merged: plain single-take map check passes, exit 0", p.returncode == 0 and H == [], (p.returncode, H))


CASES = {"map": case_map, "check": case_check, "nospeed": case_nospeed, "board": case_board, "shift": case_shift,
         "twice": case_twice, "struck": case_struck, "swap": case_swap, "take2": case_take2, "anchor": case_anchor,
         "noboard": case_noboard, "real": case_real, "tweakstale": case_tweakstale, "txmap": case_txmap,
         "notimes": case_notimes, "take2dir": case_take2dir, "take2merged": case_take2merged}


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
