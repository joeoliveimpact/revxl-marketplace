#!/usr/bin/env python3
"""FX1 round 5: accepted Tweak Board cuts persist across rounds for quote checks.

usage: python tests/editor/fx1_tweak_cut_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 only when no checks fail.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
P = REPO / "plugins/editor-superengine"
S = P / "skills/reel-first-cuts/scripts"
CHECKS = P / "skills/_shared/checks"
WALK = os.environ.get("EDITOR_SE_TEST_REEL_W2B", "")
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


def check_map(d):
    p = run(S / "word_map.py", [d], d)
    ck("word map written", p.returncode == 0, p.stdout + p.stderr)
    p = run(CHECKS / "map_check.py", [d], d)
    return p, read(d / "work/map_check.json")["blocks"]


def cut_to(d, spans):
    segs, out = [], 0
    for a, b in spans:
        a, b = round(a * 30), round(b * 30)
        segs.append(dict(src_in_f=a, src_out_f=b, out_in_f=out, out_out_f=out + b - a))
        out += b - a
    cuts = dict(fps=30, speed=1.0, segments=segs)
    write(d / "work/cuts.json", cuts)
    return cuts


def synthetic(scratch):
    import build_edit_map, word_map
    d = Path(tempfile.mkdtemp(prefix="fx1-tweak-cut-", dir=scratch))
    em = dict(words=[dict(id=wid, word=word, start=t, end=t + 0.4, parakeet_start=t, status="aligned")
                     for wid, word, t in (("a", "A", 0.0), ("b", "B", 1.0),
                                          ("c", "C", 2.0), ("d", "D", 3.0))], events=[], silences=[])
    write(d / "work/edit_map.json", em)
    cuts = cut_to(d, [(0, 4)])
    seq = build_edit_map.board_sequence(em)
    whash = build_edit_map.word_list_hash(seq)
    cfg = dict(reel="syn", gap_default_ms=300,
               takes={"1": dict(edit_map="work/edit_map.json", wav="unused.wav", words=seq, word_list_hash=whash)},
               lines=[dict(id="L01", attempts=[dict(take=1, src_in=0.0, src_out=4.0, word_from=0, word_to=3,
                    words=[dict(i=i, w=w["word"], s=w["start"], cin=w["start"]) for i, w in enumerate(seq)])])])
    cfg["board_hash"] = build_edit_map.board_hash(cfg)
    write(d / "cut-board.config.json", cfg)
    write(d / "cut-selection.json", dict(reel="syn", board_hash=cfg["board_hash"], word_list_hash={"1": whash},
                                        lines=[dict(id="L01", pick=0, rm={"0": []})]))
    tw = dict(reel="syn", version="v1", edit_map="work/edit_map.json", take=1,
              cuts_sha256=hashlib.sha256((d / "work/cuts.json").read_bytes()).hexdigest(),
              words=[dict(id=w["id"], w=w["word"], t=round(w["out_start"], 3))
                     for w in word_map.build(cuts, em)["words"]])
    write(d / "tweak-board.config.json", tw)
    # Reverse endpoints, B on the inclusive edge and C on the exclusive edge.
    sel = dict(reel="syn", version="v1", marks=[dict(id=1, type="cut", a=2.0, b=1.0)])
    write(d / "tweak-selection.json", sel)
    record = d / "work/tweak-cuts.json"
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
    ck("synthetic: real Tweak Board Send accepted", p.returncode == 0
       and (d / "work/edl.json").is_file(), p.stdout + p.stderr)
    saved = read(record) if record.is_file() else None
    ck("synthetic: half-open cut records only B", saved == dict(version=2, rounds={"v1": {"b": "B"}}), saved)
    if saved is None:
        return

    cut_to(d, [(0, 1), (2, 4)])
    p, blocks = check_map(d)
    ck("synthetic: intentionally cut B is not quote-missing", p.returncode == 0
       and not blocks and "quote-missing" not in p.stdout, p.stdout + p.stderr)
    record.unlink()
    p, blocks = check_map(d)
    missing_b = dict(check="quote-missing", level="block",
                     msg="line L01: the word 'B' was picked but is not in the cut.", where="cut-selection.json: L01 b")
    ck("synthetic: deleting the record reproduces the bug", p.returncode == 1 and blocks == [missing_b]
       and "quote-missing" in p.stdout, p.stdout + p.stderr)
    write(record, saved)

    cut_to(d, [(0, 1), (3, 4)])
    p, blocks = check_map(d)
    ck("synthetic: unmarked missing C still blocks with the existing message", p.returncode == 1 and blocks == [
        dict(check="quote-missing", level="block", msg="line L01: the word 'C' was picked but is not in the cut.",
             where="cut-selection.json: L01 c")], p.stdout + p.stderr)
    cut_to(d, [(0, 4)])
    p, blocks = check_map(d)
    ck("synthetic: B still in the cut gives Tweak Board quote-extra", p.returncode == 1 and blocks == [
        dict(check="quote-extra", level="block", where="cut-selection.json: L01 b",
             msg="line L01: the word 'B' was cut on the Tweak Board but is still in the cut. "
                 "Mark a slightly wider cut around it on the Tweak Board and press Send again.")], p.stdout + p.stderr)

    cut_sel = read(d / "cut-selection.json")
    cut_sel["lines"][0]["rm"]["0"] = [1]
    write(d / "cut-selection.json", cut_sel)
    p, blocks = check_map(d)
    ck("synthetic: Cut Board strike takes precedence over Tweak cut", p.returncode == 1 and blocks == [
        dict(check="quote-extra", level="block", where="cut-selection.json: L01 b",
             msg="line L01: the word 'B' was struck but is still in the cut. "
                 "Put that word back on the Cut Board (click it) and press Send again, or strike the words around it too.")]
       and "cut on the Tweak Board" not in p.stdout, p.stdout + p.stderr)
    cut_sel["lines"][0]["rm"]["0"] = []
    write(d / "cut-selection.json", cut_sel)

    sel["marks"] = []
    write(d / "tweak-selection.json", sel)
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
    ck("synthetic: same-version no-mark re-Send deletes the last cut record", p.returncode == 0
       and not record.exists(), p.stdout + p.stderr)
    p, blocks = check_map(d)
    ck("synthetic: re-Send keeping B has no false quote-extra", p.returncode == 0
       and not blocks, p.stdout + p.stderr)
    sel["marks"] = [dict(id=1, type="cut", a=2.0, b=1.0)]
    write(d / "tweak-selection.json", sel)
    write(record, dict(version=1, words={"b": "B"}))
    cut_to(d, [(0, 1), (2, 4)])
    p, blocks = check_map(d)
    ck("synthetic: legacy record still suppresses missing B", p.returncode == 0 and not blocks,
       p.stdout + p.stderr)
    cut_to(d, [(0, 4)])
    p, blocks = check_map(d)
    ck("synthetic: legacy record still reports B kept in the cut", p.returncode == 1 and len(blocks) == 1
       and blocks[0]["check"] == "quote-extra" and "cut on the Tweak Board" in blocks[0]["msg"],
       p.stdout + p.stderr)
    write(record, saved)

    cut_to(d, [(0, 1), (2, 4)])
    tw["version"] = "v2"
    tw["words"] = [dict(id=w["id"], w=w["word"], t=round(w["out_start"], 3))
                   for w in word_map.build(read(d / "work/cuts.json"), em)["words"]]
    tw["cuts_sha256"] = hashlib.sha256((d / "work/cuts.json").read_bytes()).hexdigest()
    write(d / "tweak-board.config.json", tw)
    p, blocks = check_map(d)
    ck("synthetic: rebuilt v2 board with v1 selection still passes", p.returncode == 0
       and not blocks and "quote-missing" not in p.stdout and read(record) == saved, p.stdout + p.stderr)
    before = record.read_bytes()
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
    ck("synthetic: refused old Send preserves the record", p.returncode == 3
       and record.read_bytes() == before, p.stdout + p.stderr)

    for bad in (b"not json", b"\xff", b'{"words": null}', b"[]", b"null",
                b'{"version": 1, "words": []}', b'{"version": 2, "rounds": []}',
                b'{"version": 2, "rounds": {"v1": []}}',
                b'{"version": 2, "rounds": {"v1": {"b": []}}}'):
        record.write_bytes(bad)
        p, blocks = check_map(d)
        ck("synthetic: unreadable record %r is ignored" % bad, p.returncode == 1 and blocks == [missing_b]
           and "Traceback" not in p.stderr, p.stdout + p.stderr)
    write(record, saved)

    # A takes cut uses qualified ids and has no Tweak Board rulings.
    mixed = read(d / "work/cuts.json")
    mixed["takes"] = {"1": dict(work="work")}
    mixed["segments"] = [dict(s, take=1) for s in mixed["segments"]]
    write(d / "work/cuts.json", mixed)
    write(record, dict(version=1, words={"b": "B", "t1:b": "B"}))
    p, blocks = check_map(d)
    ck("synthetic: take-qualified cuts ignore tweak records", p.returncode == 1
       and blocks == [dict(missing_b, where="cut-selection.json: L01 t1:b")], p.stdout + p.stderr)

    # A later accepted Send migrates legacy words and records its own round.
    cut_to(d, [(0, 4)])
    tw["version"] = "v1"
    tw["words"] = [dict(id=w["id"], w=w["word"], t=round(w["out_start"], 3))
                   for w in word_map.build(read(d / "work/cuts.json"), em)["words"]]
    tw["cuts_sha256"] = hashlib.sha256((d / "work/cuts.json").read_bytes()).hexdigest()
    write(d / "tweak-board.config.json", tw)
    write(record, dict(version=1, words={"old": "earlier round", "b": "old text"}))
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work", "--out", "alternate"], d)
    ck("synthetic: rounds merge in work even with --out", p.returncode == 0
       and (d / "alternate/edl.json").is_file() and not (d / "alternate/tweak-cuts.json").exists()
       and read(record) == dict(version=2, rounds={"?": {"old": "earlier round", "b": "old text"},
                                                  "v1": {"b": "B"}}), p.stdout + p.stderr)
    before = record.read_bytes()
    tw["words"][0]["t"] += 0.2
    write(d / "tweak-board.config.json", tw)
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
    ck("synthetic: drift refusal preserves the record", p.returncode == 3
       and record.read_bytes() == before, p.stdout + p.stderr)
    tw["words"][0]["t"] -= 0.2
    write(d / "tweak-board.config.json", tw)
    sel["marks"] = [dict(id=2, type="note", a=0.5, text="keep")]
    write(d / "tweak-selection.json", sel)
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
    ck("synthetic: no cut marks clear this round and preserve legacy words", p.returncode == 0
       and read(record) == dict(version=2, rounds={"?": {"old": "earlier round", "b": "old text"}, "v1": {}}),
       p.stdout + p.stderr)
    record.unlink()
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
    ck("synthetic: no cut marks do not create a record", p.returncode == 0
       and not record.exists(), p.stdout + p.stderr)

    for bad in (b"not json", b'{"words": []}', b"null", b"[]", b"\xff", b'{"version": 1, "words": []}',
                b'{"version": 2, "rounds": []}', b'{"version": 2, "rounds": {"v0": []}}',
                b'{"version": 2, "rounds": {"v0": {"b": []}}}'):
        record.write_bytes(bad)
        sel["marks"] = [dict(id=1, type="cut", a=2.0, b=1.0)]
        write(d / "tweak-selection.json", sel)
        p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
        ck("synthetic: corrupt record %r is replaced by a clean accepted Send" % bad, p.returncode == 0
           and "Traceback" not in p.stderr and read(record) == saved, p.stdout + p.stderr)

    tw["version"] = sel["version"] = "v2"
    write(d / "tweak-board.config.json", tw)
    sel["marks"] = [dict(id=2, type="cut", a=2.0, b=3.0)]
    write(d / "tweak-selection.json", sel)
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
    ck("synthetic: v2 cutting C preserves v1 cutting B", p.returncode == 0
       and read(record) == dict(version=2, rounds={"v1": {"b": "B"}, "v2": {"c": "C"}}), p.stdout + p.stderr)
    cut_to(d, [(0, 1), (3, 4)])
    p, blocks = check_map(d)
    ck("synthetic: map check uses the union of rounds", p.returncode == 0 and not blocks, p.stdout + p.stderr)
    cut_to(d, [(0, 4)])
    sel["marks"] = []
    write(d / "tweak-selection.json", sel)
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
    ck("synthetic: empty v2 re-Send preserves only v1 cut words", p.returncode == 0
       and read(record) == dict(version=2, rounds={"v1": {"b": "B"}, "v2": {}}), p.stdout + p.stderr)
    cut_to(d, [(0, 1), (2, 4)])
    p, blocks = check_map(d)
    ck("synthetic: restored C is clean while B stays intentionally cut", p.returncode == 0 and not blocks,
       p.stdout + p.stderr)

    write(record, saved)
    p = run(S / "selection_to_edl.py", ["cut-selection.json", "cut-board.config.json"], d)
    ck("synthetic: real Cut Board Send clears the record", p.returncode == 0
       and (d / "work/edl.json").is_file() and not record.exists(), p.stdout + p.stderr)


def walk(scratch):
    import word_map
    if WALK is None or not WALK.is_dir():
        print("SKIP real-walk2b: set EDITOR_SE_TEST_REEL_W2B to the S17 re-walk-2 reel folder to run this case")
        return
    d = Path(tempfile.mkdtemp(prefix="fx1-tweak-cut-walk-", dir=scratch))
    for source in list(WALK.glob("*.json")) + [WALK / "script.md"] + [
            WALK / "work" / (name + ".json") for name in ("cuts", "edit_map", "probe", "envelope", "segments", "edl")]:
        dest = d / source.relative_to(WALK)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    sel = read(d / "cut-selection.json")
    line = next(l for l in sel["lines"] if l["id"] == "L14")
    line["rm"]["1"] = [i for i in line["rm"]["1"] if i not in (165, 166)]
    write(d / "cut-selection.json", sel)
    tw = read(d / "tweak-board.config.json")
    tw["words"] = [dict(id=w["id"], w=w["word"], t=round(w["out_start"], 3))
                   for w in word_map.build(read(d / "work/cuts.json"), read(d / "work/edit_map.json"),
                                           word_map.read_edl(d / "work/edl.json"))["words"]]
    tw["cuts_sha256"] = hashlib.sha256((d / "work/cuts.json").read_bytes()).hexdigest()
    write(d / "tweak-board.config.json", tw)
    p, blocks = check_map(d)
    ck("real-walk2b: before, Okay and so are quote-missing", p.returncode == 1
       and all(any(h["check"] == "quote-missing" and h["where"] == "cut-selection.json: L14 " + wid
                   and "the word '%s' was picked but is not in the cut." % word in h["msg"] for h in blocks)
               for wid, word in (("w_0153", "Okay,"), ("w_0154", "so"))), p.stdout + p.stderr)
    write(d / "work/tweak-cuts.json", dict(version=2, rounds={"v2": {"w_0153": "Okay,", "w_0154": "so"}}))
    p, blocks = check_map(d)
    ck("real-walk2b: after, the saved Tweak Board cuts pass", p.returncode == 0
       and not blocks and "quote-missing" not in p.stdout, p.stdout + p.stderr)


CASES = {"synthetic": synthetic, "real-walk2b": walk}


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
