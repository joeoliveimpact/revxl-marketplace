"""Fast hook/caption regressions. Run with python -X utf8 -I this_file.py."""
import contextlib
import copy
import io
import json
import math
import sys
import tempfile
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[1]
SKILLS = PLUGIN / "skills"
for directory in (SKILLS / "_shared", SKILLS / "_shared/checks",
                  SKILLS / "reel-canvas-build/scripts", SKILLS / "reel-captions/scripts"):
    sys.path.insert(0, str(directory))
import placer
import compose
import captions
import layout_check

RATE, TOTAL, BAND = Fraction(30), 180, 149
OPENING = "Claude just killed Instagram."
ADVICE = "shorten the hook to one line, or use your opening words as the hook"
WORDS = [dict(word=text, start=start, end=end) for text, start, end in (
    ("Claude", .10, .40), ("just", .40, .55), ("killed", .55, .83),
    ("Instagram.", .87, 2.10), ("You", 2.14, 2.28), ("can", 2.28, 2.43),
    ("now", 2.43, 2.55), ("connect", 2.60, 2.90), ("to", 2.90, 3.02),
    ("Instagram", 3.04, 3.50))]
SPANS = ((3, 26, 0, 1), (26, 64, 2, 3), (64, 77, 4, 6), (78, 106, 7, 9))


def write_json(reel, name, doc):
    path = reel / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(doc) + "\n").encode("utf-8"))


def fixture(reel, small=False, scene=False):
    """Anchors are normalized face_crop boxes, before placer's 24 px padding."""
    reel.mkdir(parents=True)
    beat = dict(id="b1", start_f=0, end_f=TOTAL, layout="full", scene=None,
                speech_anchor=dict(w0=0, w1=9, text=OPENING))
    if scene:
        beat["scene"] = dict(id="hf-hook-title", slots=dict(title=OPENING), params={})
    beats = [beat]
    cuts = dict(fps=30, segments=[dict(out_in_f=0, out_out_f=26),
                                  dict(out_in_f=26, out_out_f=TOTAL)])
    write_json(reel, "work/cuts.json", cuts)
    write_json(reel, "work/edit_map.cut.json", dict(words=WORDS))
    write_json(reel, "beat-map-selection.json", dict(fps=30, beats=beats))
    write_json(reel, "work/scale_track.json", dict(
        fps=30, total_f=TOTAL, style={"style": "punch-in"}, tweens=[],
        keys=[dict(f=0, scale=1, ox=.5, oy=.38, layout="full")]))
    heads = [(200, 700, 880, 1450)] * 2 if small else [
        (0, 404, 1080, 1580), (0, 395, 1080, 1692)]
    anchors = []
    for i, (x0, y0, x1, y1) in enumerate(heads):
        box = [max(0, x0 + 24) / 1080, (y0 + 24) / 1920,
               min(1080, x1 - 24) / 1080, (y1 - 24) / 1920]
        # Full-width input is what face_crop emits; clipping removes x padding.
        if not small:
            box[0], box[2] = 0, 1
        anchors.append(dict(seg=i, samples=[dict(
            f=cuts["segments"][i]["out_in_f"], x=.5, y=(y0 + y1) / 3840, box=box)]))
    write_json(reel, "work/anchors.json", dict(segments=anchors))
    ctx = placer.load_ctx(reel)
    assert compose.TIERS["master"] == (1080, 1920)
    assert placer.SAFE == (60, 220, 960, 1470), placer.SAFE
    for i, expected in enumerate(heads):
        start, end = (0, 25) if i == 0 else (26, TOTAL - 1)
        actual = placer.head_box_at(ctx, start, end)
        assert all(math.isclose(a, b) for a, b in zip(actual, expected)), actual
    inp = dict(beats=beats, rate=RATE, fps=30, total=TOTAL, cuts=cuts,
               cut_frames=[26], words=[w["word"] for w in WORDS],
               timed_words=copy.deepcopy(WORDS), reel_dir=reel, bm={})
    return inp, ctx


def chunks():
    return dict(style={"style": "bold-pop"}, chunks=[dict(
        i=i, start_f=start, end_f=end, w0=w0, w1=w1,
        text=" ".join(w["word"] for w in WORDS[w0:w1 + 1]).upper(),
        words=[dict(text=w["word"].upper(), w=j) for j, w in enumerate(WORDS)
               if w0 <= j <= w1]) for i, (start, end, w0, w1) in enumerate(SPANS)])


def plan(inp, ctx, text=None):
    with contextlib.redirect_stdout(io.StringIO()):
        return compose.plan(inp, text, ctx=ctx)


def skip(doc, hooks):
    with contextlib.redirect_stdout(io.StringIO()):
        return compose.hook_captions(doc, hooks)


def place(ctx, doc):
    # The caption planner stores exclusive ends; placer expects inclusive ends.
    for chunk in doc["chunks"]:
        chunk["box"] = placer.place(ctx, chunk["start_f"], chunk["end_f"] - 1, BAND)


def qa(inp, doc):
    write_json(inp["reel_dir"], "work/captions.json", doc)
    write_json(inp["reel_dir"], "work/hook.json", compose.hook_record(inp))
    rows = layout_check.run(dict(reel_dir=inp["reel_dir"]))
    assert not any(r["check"] == "layout-face-unchecked" for r in rows), rows
    return rows


def spoken_placement(root):
    inp, ctx = fixture(root / "spoken-placement")
    plan(inp, ctx)
    doc = chunks()
    # Exercise all early boxes even though the skip helper later removes two.
    place(ctx, doc)
    hook = ctx["stills"][0]
    early = [c for c in doc["chunks"] if c["start_f"] < hook[1]]
    assert len(early) == 2
    for chunk in early:
        assert not placer.hits(chunk["box"], hook[2]), chunk


def spoken_skipping(root):
    inp, ctx = fixture(root / "spoken-skipping")
    plan(inp, ctx)
    hook = inp["hooks"][0]
    assert hook["spoken"] and hook["word_count"] == 4, hook
    assert inp["hook_f"] == hook["end_f"] == 63, hook
    doc = chunks()
    assert skip(doc, inp["hooks"]) == 2
    assert [(c["w0"], c["w1"]) for c in doc["chunks"]] == [(4, 6), (7, 9)], doc
    assert hook["shown_words"] == [0, 1, 2, 3], hook
    assert [c["i"] for c in doc["chunks"]] == [0, 1]
    # Clamp both ends, using the same timed word rather than a fixed hold.
    for seconds, expected in ((1.0, 45), (2.10, 63), (5.8, 150)):
        timed = copy.deepcopy(WORDS)
        timed[3]["end"] = seconds
        actual = compose.plain_hook(OPENING, inp["beats"][0], RATE, timed, TOTAL)
        assert actual["end_f"] == expected, actual
    # An all-hook chunk at the exclusive end and a mixed chunk must survive.
    boundary = chunks()
    boundary["chunks"][0]["start_f"], boundary["chunks"][0]["end_f"] = 63, 64
    boundary["chunks"][1]["w1"] = 4
    assert skip(boundary, inp["hooks"]) == 0, boundary


def different_one_line(root):
    inp, ctx = fixture(root / "different-one-line")
    plan(inp, ctx, "Stop scrolling")
    assert not inp["hooks"][0]["spoken"]
    doc = chunks()
    before = copy.deepcopy(doc["chunks"])
    assert skip(doc, inp["hooks"]) == 0
    assert doc["chunks"] == before
    place(ctx, doc)
    hook = ctx["stills"][0]
    for chunk in doc["chunks"]:
        assert chunk["start_f"] < hook[1]
        assert chunk["box"][1] == math.ceil(hook[2][3] + placer.UNDER_HEAD_GAP), chunk
        assert not placer.hits(chunk["box"], hook[2]), chunk
        head = placer.head_box_at(ctx, chunk["start_f"], chunk["end_f"] - 1)
        assert not placer.hits(chunk["box"], placer.face_band(head), placer.CAPTION_PAD), chunk
    rows = qa(inp, doc)
    assert not any(r["level"] == "block" for r in rows), rows


def hook_scene(root):
    for small in (False, True):
        inp, ctx = fixture(root / ("scene-small" if small else "scene-tight"), small=small, scene=True)
        # Inspect the filled scene before the placement helper may replace it.
        plan(inp, None)
        scene = inp["beats"][0]["scene"]
        assert scene["params"]["entrance"] == "none", scene
        notes = compose.place_hook_titles(inp, ctx)
        record = compose.hook_record(inp)
        if not small:
            assert inp["beats"][0]["scene"] is None, inp["beats"]
            assert any("didn't fit above your face" in n for n in notes), notes
            assert record["kind"] == "plain" and record["text"] == OPENING, record
            assert inp["hooks"] and inp["hook_f"] == 63
        else:
            assert inp["beats"][0]["scene"] is not None and not notes, notes
            assert record["kind"] == "scene", record
            head = placer.head_box_at(ctx, 0, TOTAL - 1)
            assert record["box"][3] <= placer.face_band(head)[1] - placer.UNDER_HEAD_GAP, record
            doc = chunks()
            assert skip(doc, compose.placement_hooks(inp)) == 0
            place(ctx, doc)
            for chunk in doc["chunks"]:
                assert not placer.hits(chunk["box"], record["box"]), chunk
            rows = qa(inp, doc)
            assert not any(r["check"] == "text-collision" for r in rows), rows


def different_two_lines(root):
    inp, ctx = fixture(root / "different-two-lines")
    plan(inp, ctx, "Watch this before you post")
    doc = chunks()
    assert skip(doc, inp["hooks"]) == 0
    place(ctx, doc)
    assert any(ADVICE in n.lower() for n in ctx["notes"]), ctx["notes"]
    rows = qa(inp, doc)
    assert any(r["level"] == "block" and ADVICE in r["msg"].lower() for r in rows), rows


def main():
    failures = []
    with tempfile.TemporaryDirectory(prefix="hook-captions-") as home:
        root = Path(home)
        # Saved user choices must not affect this fixture or receive any writes.
        with patch.object(compose.rt, "state_dir", return_value=root / "state"):
            for case in (spoken_placement, spoken_skipping, different_one_line,
                         hook_scene, different_two_lines):
                try:
                    case(root)
                except Exception as exc:
                    failures.append(case.__name__)
                    print(f"FAIL {case.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        return 1
    print("hook captions test ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
