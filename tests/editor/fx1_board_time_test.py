#!/usr/bin/env python3
"""FX1 round 10: Tweak Board marks and the cut tool share aligned word starts.

usage: python tests/editor/fx1_board_time_test.py <scratch-dir> [--case NAME]
Real media are never changed; real-walk1b uses EDITOR_SE_TEST_REEL_W1B only.
"""
import argparse, hashlib, json, os, shlex, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
P = REPO / "plugins/editor-superengine"
S = P / "skills/reel-first-cuts/scripts"
CHECKS = P / "skills/_shared/checks"
sys.path.insert(0, str(P / "skills/_shared"))
sys.path.insert(0, str(S))
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)
    return ok


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(json.dumps(obj, indent=1).encode("utf-8"))


def run(script, args, d):
    return subprocess.run([sys.executable, "-X", "utf8", "-I", str(script), *map(str, args)], cwd=d,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)


def tweak_board(d, clock="out_start", version="v1"):
    # Same word mapping as make_tweaks, without a video or waveform.
    import word_map
    cuts = read(d / "work/cuts.json")
    em = read(d / "work/edit_map.json")
    mapped = word_map.build(cuts, em, word_map.read_edl(d / "work/edl.json"))["words"]
    cfg = dict(reel=read(d / "cut-board.config.json")["reel"], version=version, edit_map="work/edit_map.json", take=1,
               cuts_sha256=hashlib.sha256((d / "work/cuts.json").read_bytes()).hexdigest(),
               words=[dict(id=w["id"], w=w["word"], t=round(w[clock], 3)) for w in mapped])
    write(d / "tweak-board.config.json", cfg)
    return cfg, mapped


def check_map(d, label):
    p = run(S / "word_map.py", [d], d)
    if not ck(label + ": word map written", p.returncode == 0, p.stdout + p.stderr):
        return None, []
    p = run(CHECKS / "map_check.py", [d], d)
    return p, read(d / "work/map_check.json")["blocks"]


def chain(d, label):
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
    if not ck(label + ": real Tweak Send accepted", p.returncode == 0, p.stdout + p.stderr):
        return None, []
    command = next(l for l in p.stdout.splitlines() if l.startswith("<editor python>"))
    args = shlex.split(command[len("<editor python>"):].replace("${CLAUDE_PLUGIN_ROOT}", P.as_posix()))
    p = subprocess.run([sys.executable, *args], cwd=d, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180)
    if not ck(label + ": printed gaps command", p.returncode == 0, p.stdout + p.stderr):
        return None, []
    return check_map(d, label)


def mark(d, cfg, you, prompts):
    by_id = {w["id"]: w for w in cfg["words"]}
    write(d / "tweak-selection.json", dict(reel=cfg["reel"], version=cfg["version"], marks=[
        dict(id=1, type="cut", a=round(by_id[you]["t"] - 0.010, 3),
             b=round(by_id[prompts]["t"] - 0.010, 3))]))


def whole(d, wid):
    cuts = read(d / "work/cuts.json")
    words = [w for w in read(d / "work/word_map.json")["words"] if w["id"] == wid]
    if len(words) != 1:
        return False
    w = words[0]
    seg, fps = cuts["segments"][w["seg"]], cuts["fps"]
    return seg["src_in_f"] / fps <= w["src_start"] + 1e-9 and seg["src_out_f"] / fps >= w["src_end"] - 1e-9


def synthetic(scratch):
    import build_edit_map
    d = Path(tempfile.mkdtemp(prefix="fx1-board-time-", dir=scratch))
    base = d / "base"
    em = dict(words=[dict(id=wid, word=word, start=start, end=end, parakeet_start=anchor, status="aligned")
                     for wid, word, start, end, anchor in (
                         ("before", "before", 16.800, 17.053, 16.800),
                         ("you", "you", 17.053, 17.173, 17.093),
                         ("the", "the", 17.173, 17.293, 17.173),
                         ("prompts", "prompts.", 17.293, 17.700, 17.333))], events=[], silences=[])
    write(base / "work/edit_map.json", em)
    write(base / "work/cuts.json", dict(fps=30, speed=1.0, segments=[
        dict(src_in_f=0, src_out_f=540, out_in_f=0, out_out_f=540)]))
    write(base / "work/edl.json", [dict(src_in=0.0, src_out=18.0)])
    write(base / "work/probe.json", dict(out_rate=30, calibration=dict(
        gap_db=-50.0, speech_db=-40.0, speech_run_windows=3)))
    # Continuous speech prevents unrelated silence tightening in this timing fixture.
    write(base / "work/envelope.json", dict(db=[-12.0] * 1800, win_s=0.01))
    seq = build_edit_map.board_sequence(em)
    whash = build_edit_map.word_list_hash(seq)
    cfg = dict(reel="syn", gap_default_ms=300,
               takes={"1": dict(edit_map="work/edit_map.json", wav="unused.wav", words=seq, word_list_hash=whash)},
               lines=[dict(id="L08", attempts=[dict(take=1, src_in=0.0, src_out=18.0, word_from=0, word_to=3,
                    words=[dict(i=i, w=w["word"], s=w["start"], cin=w["start"]) for i, w in enumerate(seq)])])])
    cfg["board_hash"] = build_edit_map.board_hash(cfg)
    write(base / "cut-board.config.json", cfg)
    write(base / "cut-selection.json", dict(reel="syn", board_hash=cfg["board_hash"], word_list_hash={"1": whash},
                                           lines=[dict(id="L08", pick=0, rm={"0": []})]))
    tw, _ = tweak_board(base)
    write(base / "tweak-selection.json", dict(reel="syn", version="v1", marks=[]))
    p, blocks = check_map(base, "synthetic aligned board")
    ck("synthetic: aligned board passes before cutting", p is not None and p.returncode == 0 and not blocks,
       "word map failed" if p is None else p.stdout + p.stderr)

    old, _ = tweak_board(base, "out_anchor")
    p, blocks = check_map(base, "synthetic old board")
    rebuild = "Rebuild the Tweak Board (make_tweaks.py) from this cut."
    ck("synthetic: old board blocks tweak-time with rebuild advice", p is not None and p.returncode == 1
       and {h["where"].rsplit(" ", 1)[-1] for h in blocks if h["check"] == "tweak-time"} == {"you", "prompts"}
       and all(h["level"] == "block" and rebuild in h["msg"] for h in blocks),
       "word map failed" if p is None else p.stdout + p.stderr)
    write(base / "tweak-board.config.json", tw)
    # 100 ms after aligned start is only 60 ms after the old anchor: distinguish the drift guards.
    drift = read(base / "tweak-board.config.json")
    next(w for w in drift["words"] if w["id"] == "you")["t"] += 0.100
    write(base / "tweak-board.config.json", drift)
    p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], base)
    ck("synthetic: drift guard compares against aligned start", p.returncode == 3
       and "rebuild the board with make_tweaks.py" in p.stderr, p.stdout + p.stderr)
    write(base / "tweak-board.config.json", tw)

    for label, board in (("aligned", tw), ("anchor mutant", old)):
        target = d / label.replace(" ", "-")
        shutil.copytree(base, target)
        # The old board also records cut-word intent from its displayed anchor times.
        write(target / "tweak-board.config.json", board)
        mark(target, board, "you", "prompts")
        p, blocks = chain(target, "synthetic " + label)
        if p is None:
            continue
        if label == "aligned":
            ids = {w["id"] for w in read(target / "work/word_map.json")["words"]}
            ck("synthetic: you and the are out, prompts. is whole and in",
               "you" not in ids and "the" not in ids and whole(target, "prompts"), ids)
            ck("synthetic: aligned mark passes map_check", p.returncode == 0 and not blocks, p.stdout + p.stderr)
        else:
            ck("synthetic: old mark times reproduce quote failure", p.returncode == 1 and any(
                (h["check"] == "quote-missing" and "'prompts.'" in h["msg"])
                or (h["check"] == "quote-extra" and "'you'" in h["msg"]) for h in blocks), p.stdout + p.stderr)


def real_walk1b(scratch):
    value = os.environ.get("EDITOR_SE_TEST_REEL_W1B", "")
    if not value:
        print("SKIP real-walk1b: set EDITOR_SE_TEST_REEL_W1B to run this case")
        return
    source = Path(value)
    if not ck("real-walk1b: configured reel exists", source.is_dir()):
        return
    d = Path(tempfile.mkdtemp(prefix="fx1-board-time-walk-", dir=scratch))
    for name in ("cut-board.config.json", "cut-selection.json", "work/cuts.json", "work/edit_map.json",
                 "work/probe.json", "work/envelope.json", "work/edl.json", "work/tweak-cuts.json"):
        if name in ("work/edl.json", "work/tweak-cuts.json") and not (source / name).exists():
            continue
        dest = d / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, dest)
    # Preserve earlier accepted cut rounds when this Send records its own word intent.
    cfg, mapped = tweak_board(d, version="fx1-board-time")
    cb, sel = read(d / "cut-board.config.json"), read(d / "cut-selection.json")
    line = next(l for l in sel["lines"] if l["id"] == "L08")
    attempt = next(l for l in cb["lines"] if l["id"] == "L08")["attempts"][line["pick"]]
    seq = cb["takes"][str(attempt["take"])]["words"]
    line_ids = {seq[w["i"]]["id"] for w in attempt["words"]}

    def find(word):
        matches = [w for w in mapped if w["id"] in line_ids and w["word"] == word
                   and 17.05 <= w["out_start"] <= 17.35]
        if len(matches) != 1:
            raise ValueError("expected one L08 %r near cut time 17.05-17.35, got %d" % (word, len(matches)))
        return matches[0]

    you, prompts = find("you"), find("prompts.")
    if not ck("real-walk1b: you precedes prompts.", you["out_start"] < prompts["out_start"]):
        return
    mark(d, cfg, you["id"], prompts["id"])
    p, blocks = chain(d, "real-walk1b")
    if p is not None:
        ck("real-walk1b: prompts. is whole and in", whole(d, prompts["id"]))
        ck("real-walk1b: aligned mark passes map_check", p.returncode == 0 and not blocks, p.stdout + p.stderr)


CASES = {"synthetic": synthetic, "real-walk1b": real_walk1b}


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
