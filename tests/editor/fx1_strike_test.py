#!/usr/bin/env python3
"""FX1 B: earlier real words establish the floor for a board in-point.

usage: python tests/editor/fx1_strike_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 only when no checks fail.
"""
import argparse, json, os, shlex, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
P = REPO / "plugins/editor-superengine"
S = P / "skills/reel-first-cuts/scripts"
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


def run(script, args, cwd):
    return subprocess.run([sys.executable, "-X", "utf8", "-I", str(script), *map(str, args)], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)


def synthetic(scratch):
    import make_board
    words = [dict(word=w, start=s, end=e) for w, s, e in [
        ("you", 110.22, 110.30), ("the", 110.34, 110.42), ("prompt,", 110.46, 111.10),
        ("I", 110.80, 114.40), ("profit", 110.96, 114.64), ("[vocal]", 114.5, 114.6),
        ("the", 114.64, 114.74)]]
    islands = [[111.07, 111.75], [111.76, 112.28], [112.87, 113.35], [115.53, 116.35]]
    value, island = make_board.in_point(words, 6, islands)
    ck("synthetic: struck words cannot return after the cut", value >= 114.64, value)
    ck("synthetic: keep the snapped island", island == [112.87, 113.35], island)
    value, island = make_board.in_point(words, 1, islands)
    ck("synthetic: kept 'you' retains its tail", value >= 110.30 and island is None, (value, island))
    plain = [dict(word="a", start=1.0, end=1.2), dict(word="b", start=2.0, end=2.3)]
    ck("synthetic: ordinary snap stays 1.75", make_board.in_point(plain, 1, [[1.3, 1.9]]) == (1.75, [1.3, 1.9]))
    ck("synthetic: no earlier real word leaves the fallback", make_board.in_point(plain, 0, []) == (0.95, None))
    # Events do not impose a floor, even when they extend past a real word.
    events = [dict(word="[vocal]", start=0.0, end=2.2), *plain]
    ck("synthetic: event tails are excluded", make_board.in_point(events, 2, [[1.3, 1.9]])[0] == 1.75)
    overlap = [dict(word="a", start=1.0, end=3.0), dict(word="b", start=2.0, end=2.3)]
    ck("synthetic: pathological overlap leaves the snap unchanged", make_board.in_point(overlap, 1, [[1.3, 1.9]])[0] == 1.75)


def walk(scratch):
    if WALK is None or not WALK.is_dir():
        print("SKIP real-walk: set EDITOR_SE_TEST_REEL_W2 to the S17 walk-2 reel folder to run this case")
        return
    import make_board
    from build_edit_map import board_sequence
    em = read(WALK / "work/edit_map.json")
    words = board_sequence(em)
    islands = [[s["start"], s["end"]] for s in em["silences"]]
    i = next(i for i, w in enumerate(words) if w["id"] == "w_0163")
    value = make_board.in_point(words, i, islands)[0]
    ck("real-walk: w_0163 starts after struck profit ends", value >= 114.64, value)
    d = Path(tempfile.mkdtemp(prefix="fx1-strike-walk-", dir=scratch))
    for name in ("script.md", "shots.json", "cut-selection.json", "work/edit_map.json", "work/tx.16k.wav",
                 "work/probe.json", "work/envelope.json"):
        dest = d / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(WALK / name, dest)
    p = run(S / "make_board.py", ["--script", "script.md", "--take", "1:work/edit_map.json:work/tx.16k.wav",
                                 "--shots", "shots.json", "--reel", WALK.name, "-o", d], d)
    ck("real-walk: Stage 2 board rebuild", p.returncode == 0, p.stdout + p.stderr)
    if p.returncode:
        return
    cfg, sel = read(d / "cut-board.config.json"), read(d / "cut-selection.json")
    sel["board_hash"] = cfg["board_hash"]
    line = next(l for l in sel["lines"] if l["id"] == "L13")
    att = next(l for l in cfg["lines"] if l["id"] == "L13")["attempts"][line["pick"]]
    struck = [w["i"] for w in att["words"] if w["w"] in ("the", "prompt,", "I", "profit")
              and 110.32 - 0.001 <= w["s"] <= 110.96 + 0.001]
    ck("real-walk: identify exactly four struck board words", len(struck) == 4, struck)
    if len(struck) != 4:
        return
    line["rm"] = {str(line["pick"]): struck}
    (d / "cut-selection.json").write_bytes(json.dumps(sel, indent=1).encode("utf-8"))
    p = run(S / "selection_to_edl.py", ["cut-selection.json", "cut-board.config.json"], d)
    ck("real-walk: Stage 3 selection to EDL", p.returncode == 0, p.stdout + p.stderr)
    if p.returncode:
        return
    command = next(l for l in p.stdout.splitlines() if l.startswith("<editor python>"))
    # Split the printed command without a shell; forward slashes survive shlex on Windows too.
    command = command.replace("${CLAUDE_PLUGIN_ROOT}", P.as_posix())
    args = shlex.split(command[len("<editor python>"):])
    p = subprocess.run([sys.executable, *args], cwd=d, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180)
    ck("real-walk: printed gaps command", p.returncode == 0, p.stdout + p.stderr)
    if p.returncode:
        return
    p = run(S / "word_map.py", [d], d)
    ck("real-walk: word map rebuild", p.returncode == 0, p.stdout + p.stderr)
    p = run(P / "skills/_shared/checks/map_check.py", [d], d)
    extra = any("quote-extra" in row and "L13" in row for row in p.stdout.splitlines())
    ck("real-walk: struck L13 words stay out and map check passes", p.returncode == 0 and not extra,
       p.stdout + p.stderr)
    p = run(S / "boundary_audit.py", [d / "work", d / "work/edit_map.json"], d)
    ck("real-walk-strike: audit is clean after the L13 strike chain", p.returncode == 0
       and "flagged 0" in p.stdout, p.stdout + p.stderr)


CASES = {"synthetic": synthetic, "real-walk": walk}


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
