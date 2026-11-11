"""VES-1 effect gate: run before render to block effects that would fight each other (stdlib only).

A span is one effect on the reel's timeline: {layer, start_f, end_f} plus an optional id (used in
messages). Transition spans also carry their beat and declaration from transitions.spans;
other layers ignore extra keys. Frames are output frames at the reel fps, end_f exclusive.
A cut frame is the first output frame of the next segment.

What the gate blocks:
  - two full-screen takeovers on screen at once (touching end-to-start is fine)
  - any a-roll transform (punch-in, follow-cam, Ken Burns, layout move) that runs across a cut
    (starting or ending exactly on the cut is fine)
Overlays and takeovers may cover cuts. A declared cut transition covers exactly one cut;
an overlay transition stays inside its own beat. Overlays may overlap anything.

underlay() adds the coverage underlay: one span under each run of back-to-back takeovers so the
a-roll never flashes between them. Its merge gap (merge_gap_s) is a taste option, not a rule.

  effect_gate.py check <gate.json>   gate.json: {"fps": "n/d" or number, "total_f": int,
                                                 "cut_frames": [int], "spans": [span]}
  effect_gate.py --selftest
"""
import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE))
from win_encoding import ensure_utf8_output  # noqa: E402
import fps as fpsmod  # noqa: E402
import transitions  # noqa: E402

LAYERS = ("aroll_transform", "takeover", "overlay", "transition", "broll")
GATE_KEYS = ("fps", "total_f", "cut_frames", "spans")


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _sec(f, rate):
    return f"{float(f / rate):.2f} s"


def _frames(s, rate):
    return f"frames {s['start_f']}-{s['end_f']}, {float(s['start_f'] / rate):.2f}-{_sec(s['end_f'], rate)}"


def _name(s, i):
    sid = s.get("id")
    return f"{s.get('layer', 'span')} {sid!r}" if isinstance(sid, str) and sid else f"{s.get('layer', 'span')} spans[{i}]"


def check(spans, cut_frames, fps, total_f=None):
    """Plain-English problems with the effect timeline; an empty list means it may render."""
    try:
        rate = fpsmod.as_fraction(fps)
    except ValueError as e:
        return [f"fps {e}"]
    out = []
    if total_f is not None and not (_is_int(total_f) and total_f >= 1):
        out.append(f"total_f {total_f!r} is not a frame count; use the reel's length in frames (a whole number >= 1)")
        total_f = None
    if not isinstance(spans, list):
        out.append(f"spans {str(spans)[:60]!r} is not a list; use [] or a list of {{layer, start_f, end_f}}")
        spans = []
    if not isinstance(cut_frames, list):
        out.append(f"cut_frames {str(cut_frames)[:60]!r} is not a list; use [] or a list of frame numbers")
        cut_frames = []

    good = []  # (index, span) of well-shaped spans; the overlap rules only look at these
    for i, s in enumerate(spans):
        if not isinstance(s, dict):
            out.append(f"spans[{i}] {str(s)[:60]!r} is not an object; use {{layer, start_f, end_f}}")
            continue
        name, bad = _name(s, i), False
        if "id" in s and not isinstance(s["id"], str):
            out.append(f"spans[{i}].id {s['id']!r} is not text; use a string id")
        if s.get("layer") not in LAYERS:
            out.append(f"spans[{i}] layer {s.get('layer')!r} is not a layer; use one of {', '.join(LAYERS)}")
            bad = True
        for k in ("start_f", "end_f"):
            if not _is_int(s.get(k)):
                out.append(f"{name} {k} {s.get(k)!r} is not a frame; use a whole number")
                bad = True
        if bad:
            continue
        if not 0 <= s["start_f"] < s["end_f"]:
            out.append(f"{name} runs {_frames(s, rate)}; it must start at frame 0 or later and end after it starts")
            continue
        if total_f is not None and s["end_f"] > total_f:
            out.append(f"{name} ends at frame {s['end_f']} ({_sec(s['end_f'], rate)}), past the reel's end at frame "
                       f"{total_f} ({_sec(total_f, rate)}); trim it")
            continue
        good.append((i, s))

    cuts, prev = [], None
    for j, c in enumerate(cut_frames):
        if not _is_int(c):
            out.append(f"cut_frames[{j}] {c!r} is not a frame; use a whole number")
            continue
        if c <= 0 or (total_f is not None and c >= total_f):
            end = f" and before the reel's end at frame {total_f} ({_sec(total_f, rate)})" if total_f is not None else ""
            out.append(f"cut at frame {c} ({_sec(c, rate)}) is outside the reel; a cut must be after frame 0{end}")
            continue
        if prev is not None and c <= prev:
            out.append(f"cut at frame {c} ({_sec(c, rate)}) is not after the cut at frame {prev} ({_sec(prev, rate)}); "
                       f"list cuts once each, in increasing order")
            continue
        cuts.append(c)
        prev = c

    takeovers = sorted((t for t in good if t[1]["layer"] == "takeover"), key=lambda t: t[1]["start_f"])
    for n, (i, a) in enumerate(takeovers):  # ponytail: pairwise scan, fine for a reel's handful of takeovers
        for j, b in takeovers[n + 1:]:
            if b["start_f"] >= a["end_f"]:
                break
            n_f = min(a["end_f"], b["end_f"]) - b["start_f"]
            out.append(f"{_name(a, i)} ({_frames(a, rate)}) overlaps {_name(b, j)} ({_frames(b, rate)}) by "
                       f"{n_f} frame{'s' if n_f != 1 else ''} ({_sec(n_f, rate)}); two full-screen takeovers can't be on "
                       f"screen at once, so move one to start where the other ends")
    broll = sorted((t for t in good if t[1]["layer"] == "broll"), key=lambda t: t[1]["start_f"])
    for n, (i, a) in enumerate(broll):
        for j, b in broll[n + 1:]:
            if b["start_f"] >= a["end_f"]:
                break
            out.append(f"{_name(a, i)} overlaps {_name(b, j)}; move one to start where the other ends")
    for i, s in good:
        if s["layer"] != "aroll_transform":
            continue
        for c in cuts:
            if s["start_f"] < c < s["end_f"]:
                out.append(f"{_name(s, i)} ({_frames(s, rate)}) runs across the cut at frame {c} ({_sec(c, rate)}); "
                           f"an a-roll move can't span a cut, so start it on the cut or end it there")
    seen = set()
    for i, s in good:
        if s["layer"] != "transition":
            continue
        t, beat = s.get("transition"), s.get("beat")
        if not isinstance(t, dict) or not isinstance(beat, dict) or beat.get("transition") != t:
            out.append(f"{_name(s, i)} needs its beat's transition declaration")
            continue
        bad = transitions.problems([beat], cuts, fps, [])
        out.extend(bad)
        if bad:
            continue
        spec = transitions.MENU[t["type"]]
        if spec["kind"] == "cut":
            c, d = t["at_cut_frame"], t["dur_frames"]
            inside = [c0 for c0 in cuts if s["start_f"] < c0 < s["end_f"]]
            if inside != [c] or (s["start_f"], s["end_f"]) != (c - d, c + d):
                out.append(f"{_name(s, i)} must cover exactly one cut and name that cut")
            if c in seen:
                out.append(f"Two transitions name the same cut at frame {c}; keep one")
            seen.add(c)
        else:
            declared = transitions.spans([beat])
            if not any((s["start_f"], s["end_f"]) == (v["start_f"], v["end_f"]) for v in declared):
                out.append(f"{_name(s, i)} must stay inside its beat's declared edge window")
    return out


def underlay(spans, fps, merge_gap_s=0.6):
    """Coverage underlay spans: one under each run of 2+ takeovers whose gaps are <= merge_gap_s.

    merge_gap_s is taste, not a rule: how short a gap between takeovers still reads as one run.
    Expects spans that already passed check(). Overlays never get an underlay."""
    rate = fps if isinstance(fps, Fraction) else fpsmod.as_fraction(fps)
    gap = round(Fraction(str(merge_gap_s)) * rate)
    takes = sorted((s for s in spans if s.get("layer") == "takeover"), key=lambda s: s["start_f"])
    out, run = [], None  # run = [start_f, end_f, count]
    for s in takes:
        if run and s["start_f"] - run[1] <= gap:
            run[1], run[2] = max(run[1], s["end_f"]), run[2] + 1
            continue
        if run and run[2] >= 2:
            out.append({"layer": "underlay", "start_f": run[0], "end_f": run[1]})
        run = [s["start_f"], s["end_f"], 1]
    if run and run[2] >= 2:
        out.append({"layer": "underlay", "start_f": run[0], "end_f": run[1]})
    return out


def spans_from_beats(beats, move_f, scene_kind=None):
    """Gate spans from S6a beats: overlay beats as overlays, and an a-roll move of move_f frames at each
    boundary where the layout changes (starting on the boundary; move_f 0 = no moves).

    scene_kind (a dict or a callable: scene id -> "overlay" | "takeover") turns on G2-a scenes: a beat with a
    scene gives ONE span of that layer over [start_f, end_f), instead of the overlay span its layout would give.
    A scene id with no kind raises ValueError with a plain line. None = scenes are ignored."""
    if not (_is_int(move_f) and move_f >= 0):
        raise ValueError(f"move_f {move_f!r} is not a move length; use a whole number of frames >= 0")
    kind_of = scene_kind.get if isinstance(scene_kind, dict) else scene_kind
    out = []
    for b in beats:
        transition_bad = transitions.beat_problems(b)
        if transition_bad:
            raise ValueError(" ".join(transition_bad))
        if b.get("broll") is not None:
            out.append({"layer": "broll", "start_f": b["start_f"], "end_f": b["end_f"], "id": b["id"]})
        sid = (b.get("scene") or {}).get("id") if kind_of else None
        if sid is not None:
            layer = kind_of(sid)
            if layer not in ("overlay", "takeover"):
                raise ValueError(f"beat {b['id']} uses scene {sid!r}, which has no kind (overlay or takeover); "
                                 f"pick a scene from the scenes folder")
            out.append({"layer": layer, "start_f": b["start_f"], "end_f": b["end_f"], "id": b["id"]})
        elif b.get("layout") == "overlay":
            out.append({"layer": "overlay", "start_f": b["start_f"], "end_f": b["end_f"], "id": b["id"]})
    solid = sorted((b for b in beats if b.get("layout") != "overlay"), key=lambda b: b["start_f"])
    out.extend(transitions.spans(beats))
    for a, b in zip(solid, solid[1:]):
        if move_f and a["layout"] != b["layout"]:
            out.append({"layer": "aroll_transform", "start_f": b["start_f"], "end_f": b["start_f"] + move_f,
                        "id": f"{a['id']}->{b['id']}"})
    return out


def cmd_check(path):
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"BLOCK the gate file {path} can't be read as JSON ({e})")
        return 1
    if not isinstance(doc, dict):
        print(f"BLOCK the gate file {path} is not a JSON object; it needs {', '.join(GATE_KEYS)}")
        return 1
    missing = [k for k in GATE_KEYS if k not in doc]
    if missing:
        print(f"BLOCK the gate file {path} is missing {', '.join(missing)}; it needs {', '.join(GATE_KEYS)}")
        return 1
    try:
        fps = fpsmod.parse_fps(doc["fps"])
    except ValueError as e:
        print(f"BLOCK fps {e}")
        return 1
    problems = check(doc["spans"], doc["cut_frames"], fps, doc["total_f"])
    for p in problems:
        print(f"BLOCK {p}")
    if problems:
        return 1
    print(f"OK effect gate: {len(doc['spans'])} spans, {len(doc['cut_frames'])} cuts, "
          f"{len(underlay(doc['spans'], fps))} underlay spans")
    return 0


def selftest():
    def sp(layer, s, e, i=None):
        return {"layer": layer, "start_f": s, "end_f": e, **({"id": i} if i else {})}

    cases = [  # (name, problems, substring a failure must contain; None = must pass)
        ("broll overlap", check([sp("broll", 0, 31), sp("broll", 30, 60)], [], "30", 90), "overlaps broll"),
        ("broll touch", check([sp("broll", 0, 30), sp("broll", 30, 60)], [], "30", 90), None),
        ("broll across cut", check([sp("broll", 0, 90)], [60], "30", 90), None),
        ("takeovers overlap", check([sp("takeover", 0, 31, "a"), sp("takeover", 30, 60, "b")], [], "30", 90),
         "takeover 'a'"),
        ("takeovers touch", check([sp("takeover", 0, 30, "a"), sp("takeover", 30, 60, "b")], [], "30", 90), None),
        ("move across cut", check([sp("aroll_transform", 50, 70, "m")], [60], "30", 90), "cut at frame 60 (2.00 s)"),
        ("move ends on cut", check([sp("aroll_transform", 50, 60, "m")], [60], "30", 90), None),
        ("move starts on cut", check([sp("aroll_transform", 60, 70, "m")], [60], "30", 90), None),
        ("overlay + takeover over a cut", check([sp("overlay", 0, 90), sp("takeover", 40, 80)], [60], "30", 90), None),
        ("bad layer", check([sp("zoom", 0, 10)], [], "30"), "is not a layer"),
        ("empty span", check([sp("overlay", 10, 10)], [], "30"), "end after it starts"),
        ("bool frame", check([sp("overlay", False, 10)], [], "30"), "is not a frame"),
        ("unsorted cuts", check([], [60, 30], "30", 90), "increasing order"),
        ("cut past end", check([], [90], "30", 90), "outside the reel"),
        ("bad fps", check([], [], "0"), "fps"),
    ]
    beat = {"id": "REEL_A", "layout": "full", "start_f": 0, "end_f": 90,
            "transition": {"type": "flash", "at_cut_frame": 60, "dur_frames": 3}}
    cases.extend([
        ("declared transition", check(transitions.spans([beat]), [60], "30", 90), None),
        ("transition over two cuts", check(transitions.spans([beat]), [59, 60], "30", 90), "exactly one cut"),
        ("transition names no cut", check(transitions.spans([beat]), [61], "30", 90), "exactly one cut"),
        ("two transitions at one cut", check(transitions.spans([beat, beat]), [60], "30", 90), "Two transitions"),
        ("undeclared transition", check([sp("transition", 57, 63)], [60], "30", 90), "declaration"),
        ("overlay fade", check(transitions.spans([dict(beat, layout="overlay", transition={
            "type": "fade", "at_cut_frame": None, "dur_frames": 3, "edge": "both"})]), [60], "30", 90), None),
    ])
    fails = []
    for name, problems, want in cases:
        if want is None and problems:
            fails.append(f"{name}: expected pass, got {problems}")
        elif want is not None and not any(want in p for p in problems):
            fails.append(f"{name}: expected a problem containing {want!r}, got {problems}")
    t = [sp("takeover", 0, 30), sp("takeover", 48, 60), sp("takeover", 79, 90)]
    if underlay(t, "30") != [{"layer": "underlay", "start_f": 0, "end_f": 60}]:
        fails.append(f"underlay: got {underlay(t, '30')}")
    for rate in (Fraction(25), Fraction(30), Fraction(30000, 1001)):
        if underlay(t, rate) != underlay(t, str(rate)):
            fails.append(f"underlay: exact rate {rate} differs from its text form")
    beats = [{"id": "b1", "start_f": 0, "end_f": 60, "layout": "full"},
             {"id": "b2", "start_f": 60, "end_f": 90, "layout": "split"}]
    if spans_from_beats(beats, 6) != [{"layer": "aroll_transform", "start_f": 60, "end_f": 66, "id": "b1->b2"}]:
        fails.append(f"spans_from_beats: got {spans_from_beats(beats, 6)}")
    if fails:
        for f in fails:
            print(f"selftest FAILED: {f}")
        return 1
    print("selftest ok")
    return 0


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Block effects that would fight each other, before render.")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="check a gate.json")
    c.add_argument("gate")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd == "check":
        return cmd_check(a.gate)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
