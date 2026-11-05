#!/usr/bin/env python3
"""S6b check for reel-canvas-build's VES-1 effect gate (effect_gate.py) and its coverage underlay.

usage: python -X utf8 -I tests/editor/effect_gate_test.py
Runs `effect_gate.py check` on planted gate files in a temp dir, then the underlay and
spans_from_beats helpers, then both scripts' selftests. Prints PASS/FAIL per check; exit 0 = all passed.
"""
import importlib.util, json, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPTS = REPO / "plugins" / "editor-superengine" / "skills" / "reel-canvas-build" / "scripts"
GATE = SCRIPTS / "effect_gate.py"
fails = []


def load(name):
    spec = importlib.util.spec_from_file_location("editor_" + name, SCRIPTS / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


eg, bs = load("effect_gate"), load("beat_schema")


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=60)


def sp(layer, s, e, i=None):
    return {"layer": layer, "start_f": s, "end_f": e, **({"id": i} if i else {})}


def gate(tmp, name, spans=None, cuts=(), total=300, fps="30", raw=None):
    p = Path(tmp) / (name + ".json")
    p.write_text(raw if raw is not None else json.dumps(
        {"fps": fps, "total_f": total, "cut_frames": list(cuts), "spans": spans or []}), encoding="utf-8")
    return run(GATE, "check", p)


def expect(name, p, code, *needles):
    out = p.stdout + p.stderr
    ok = p.returncode == code and "Traceback" not in out and all(n in p.stdout for n in needles)
    if code == 1:
        ok = ok and any(l.startswith("BLOCK ") for l in p.stdout.splitlines())
    else:
        ok = ok and p.stdout.startswith("OK effect gate:")
    ck(name, ok, "exit %s: %s" % (p.returncode, out.strip()[-400:]))


with tempfile.TemporaryDirectory() as tmp:
    expect("takeovers overlapping by 1 frame block, both named",
           gate(tmp, "t1", [sp("takeover", 0, 31, "tk_a"), sp("takeover", 30, 60, "tk_b")]), 1, "tk_a", "tk_b")
    expect("touching takeovers pass",
           gate(tmp, "t2", [sp("takeover", 0, 30, "tk_a"), sp("takeover", 30, 60, "tk_b")]), 0)
    expect("a-roll move across a cut blocks, span + cut named",
           gate(tmp, "a1", [sp("aroll_transform", 50, 70, "punch_1")], [60]), 1, "punch_1", "frame 60", "2.00 s")
    expect("a-roll move ending on the cut passes", gate(tmp, "a2", [sp("aroll_transform", 50, 60, "p")], [60]), 0)
    expect("a-roll move starting on the cut passes", gate(tmp, "a3", [sp("aroll_transform", 60, 70, "p")], [60]), 0)
    expect("overlay over a cut passes", gate(tmp, "o1", [sp("overlay", 40, 80, "ov")], [60]), 0)
    expect("takeover over a cut passes", gate(tmp, "o2", [sp("takeover", 40, 80, "tk")], [60]), 0)
    expect("overlay overlapping a takeover passes",
           gate(tmp, "o3", [sp("takeover", 40, 80, "tk"), sp("overlay", 30, 90, "ov")], [60]), 0)
    expect("bad: layer 'zoom'", gate(tmp, "b1", [sp("zoom", 0, 10, "z")]), 1, "'zoom'")
    expect("bad: start_f == end_f", gate(tmp, "b2", [sp("overlay", 10, 10, "e")]), 1, "'e'")
    expect("bad: float frame", gate(tmp, "b3", [sp("overlay", 1.5, 10, "f")]), 1, "1.5")
    expect("bad: cut frame >= total_f", gate(tmp, "b4", [], [300], total=300), 1, "frame 300")
    expect("bad: unsorted cuts", gate(tmp, "b5", [], [90, 60]), 1, "increasing order")
    expect("bad: missing spans", gate(tmp, "b6", raw=json.dumps({"fps": "30", "total_f": 300, "cut_frames": []})),
           1, "missing spans")
    expect("bad: invalid JSON", gate(tmp, "b7", raw="{not json"), 1, "can't be read as JSON")

U = [{"layer": "underlay", "start_f": 0, "end_f": 60}]
cases = [
    ("two back-to-back takeovers -> one underlay", [sp("takeover", 0, 30), sp("takeover", 30, 60)], U),
    ("gap 18 f at 30 fps, merge 0.6 s -> one", [sp("takeover", 0, 30), sp("takeover", 48, 60)], U),
    ("gap 19 f -> none", [sp("takeover", 0, 30), sp("takeover", 49, 60)], []),
    ("three in a row -> one", [sp("takeover", 0, 20), sp("takeover", 20, 40), sp("takeover", 50, 60)], U),
    ("single takeover -> none", [sp("takeover", 0, 30)], []),
    ("overlays only -> none", [sp("overlay", 0, 30), sp("overlay", 30, 60)], []),
]
for name, spans, want in cases:
    got = eg.underlay(spans, "30", merge_gap_s=0.6)
    ck("underlay: " + name, got == want, got)


def beat(i, s, e, layout):
    return {"id": i, "start_f": s, "end_f": e, "speech_anchor": {"text": "", "w0": 0, "w1": 0},
            "layout": layout, "value": None, "scene": None, "broll": None, "transition": None}


beats = [beat("b1", 0, 60, "full"), beat("ov", 30, 90, "overlay"), beat("b2", 60, 120, "split"),
         beat("b3", 120, 150, "split"), beat("b4", 150, 200, "full")]
doc = {"schema": bs.SCHEMA, "reel": "demo", "fps": 30, "words": bs.DEFAULT_WORDS, "beats": beats,
       "word_marks": [], "proposed": {}, "notes": {}, "needs": "", "sent_at": None}
ck("test beats are a valid S6a beat map", bs.beat_map_problems(doc) == [], bs.beat_map_problems(doc))
got = eg.spans_from_beats(beats, 8)
moves = sorted((s["start_f"], s["end_f"], s["id"]) for s in got if s["layer"] == "aroll_transform")
ck("spans_from_beats: a-roll moves at 60 and 150 only, each move_f long",
   moves == [(60, 68, "b1->b2"), (150, 158, "b3->b4")], moves)
ov = [s for s in got if s["layer"] == "overlay"]
ck("spans_from_beats: overlay span 30-90", ov == [{"layer": "overlay", "start_f": 30, "end_f": 90, "id": "ov"}], ov)
try:
    eg.spans_from_beats(beats, 0)
    ck("spans_from_beats: move_f 0 raises ValueError", False, "no error")
except ValueError:
    ck("spans_from_beats: move_f 0 raises ValueError", True)

for script in ("effect_gate.py", "fps.py"):
    p = run(SCRIPTS / script, "--selftest")
    ck(script + " --selftest", p.returncode == 0 and p.stdout.strip() == "selftest ok", (p.stdout + p.stderr)[-400:])

print("%d failed" % len(fails) if fails else "all passed")
sys.exit(1 if fails else 0)
