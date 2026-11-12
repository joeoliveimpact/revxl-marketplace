#!/usr/bin/env python3
"""JSON-only proof for the pre-render layout map; no media or renderer needed.

Usage: python tests/editor/layout_check_test.py <scratch-dir> [--case NAME]
Print PASS/FAIL and exit 0 only when every assertion passes. Child scripts use
the editor venv (EDITOR_SE_HOME), else this interpreter, with -X utf8 -I.
Fixtures use real captions.plan(), fixed measured head corners, and saved hook
inputs. Threshold placements use measured advances and line height independently
of the layout check's geometry helpers.
"""
import argparse
from contextlib import nullcontext
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cut_safety_test as cs  # noqa: E402
from editor_test_state import isolated_home

SKILLS = HERE.parents[1] / "plugins/editor-superengine/skills"
CHECKS = SKILLS / "_shared/checks"
sys.path.insert(0, str(SKILLS / "reel-captions/scripts"))
sys.path.insert(0, str(SKILLS / "reel-canvas-build/scripts"))
import captions  # noqa: E402
import compose  # noqa: E402
import placer  # noqa: E402

LC = None
fails = []
HEAD = (200, 700, 880, 1100)


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  [{detail}]"))
    if not ok:
        fails.append(name)


def save(path, doc):
    path.write_bytes((json.dumps(doc, indent=2) + "\n").encode("utf-8"))


def fixture(scratch, name):
    # Do not remove or reuse a caller's folder: each invocation owns a new reel.
    import tempfile
    d = Path(tempfile.mkdtemp(prefix="layout-" + name + "-", dir=scratch))
    (d / "work").mkdir()
    save(d / "work/cuts.json", {"fps": 30, "segments": [
        {"src_in_f": 0, "src_out_f": 150, "out_in_f": 0, "out_out_f": 150}]})
    save(d / "work/edit_map.cut.json", {"words": [
        {"id": "w_0", "word": "Extraordinary.", "start": 0.5, "end": 0.9},
        {"id": "w_1", "word": "Coaching.", "start": 3.0, "end": 3.4}]})
    save(d / "beat-map-selection.json", {"fps": 30, "caption_style": {
        "style": "clean", "accent": "#FFD84D"}, "beats": [
            {"id": "b_001", "start_f": 0, "end_f": 60, "layout": "full",
             "speech_anchor": {"text": "A useful title", "w0": 0, "w1": 0}, "scene": None},
            {"id": "b_002", "start_f": 60, "end_f": 150, "layout": "full",
             "speech_anchor": {"text": "Coaching.", "w0": 1, "w1": 1}, "scene": None}]})
    save(d / "work/scale_track.json", {"fps": 30, "total_f": 150,
        "style": {"style": "punch-in"}, "keys": [
            {"f": 0, "scale": 1, "ox": 0.5, "oy": 0.5, "layout": "full"}], "tweens": []})
    # placer adds 24 master pixels around each measured head sample.
    save(d / "work/anchors.json", {"segments": [{"seg": 0, "samples": [
        {"f": 0, "x": 0.5, "y": 0.45, "box": [
            (HEAD[0] + 24) / 1080, (HEAD[1] + 24) / 1920,
            (HEAD[2] - 24) / 1080, (HEAD[3] - 24) / 1920]}]}]})
    doc = captions.plan(d)
    assert len(doc["chunks"]) == 2, doc
    for c in doc["chunks"]:
        c["box"] = [160, 1400, 920, 1540]
    save(d / "work/captions.json", doc)
    return d, doc


def examine(d, doc, label, expected, exit_code, hook_box=None):
    save(d / "work/captions.json", doc)
    with patch.object(compose, "hook_box", return_value=hook_box) if hook_box else nullcontext():
        rows = LC.run({"reel_dir": d, "fps": 30, "cuts": None, "beats": None, "render": None})
    ck(label + ": rows", sorted(r["check"] for r in rows) == sorted(expected), rows)
    ck(label + ": seekable rows", all(
        r["where"] in ("caption 0", "caption 1", "hook")
        and isinstance(r.get("at"), (int, float)) and r["at"] == round(r["at"], 2)
        and r["level"] == ("warn" if r["check"] == "layout-face-unchecked" else "block")
        for r in rows), rows)
    command = [cs.PY, "-X", "utf8", "-I", CHECKS / "layout_check.py", d]
    if hook_box:
        # compose has fixed hook geometry, with no saved position override.
        # Inject the same geometry in the child, then run the real CLI main.
        code = ("import runpy,sys; sys.path.insert(0, %r); import compose; "
                "compose.hook_box=lambda *args: %r; sys.argv=%r; "
                "runpy.run_path(sys.argv[0], run_name='__main__')"
                % (str(SKILLS / "reel-canvas-build/scripts"), hook_box,
                   [str(CHECKS / "layout_check.py"), str(d)]))
        command = [cs.PY, "-X", "utf8", "-I", "-c", code]
    p = cs.sh(command)
    ck(label + f": standalone exit {exit_code}", p.returncode == exit_code,
       (p.returncode, p.stdout, p.stderr))
    ck(label + ": standalone findings", all(check in p.stdout for check in expected), p.stdout)
    return rows


def case_clean(scratch):
    d, doc = fixture(scratch, "clean")
    ck("clean: real protected head", placer.head_box_at(placer.load_ctx(d), 0, 149) == HEAD)
    examine(d, doc, "clean", [], 0)
    (d / "work/captions.json").unlink()
    ck("clean: missing captions skip", LC.run({"reel_dir": d}) == [])


def case_unplaced(scratch):
    d, doc = fixture(scratch, "unplaced")
    for c in doc["chunks"]:
        del c["box"]
    for label, mixed in (("all unplaced", False), ("mixed placements", True)):
        if mixed:
            doc["chunks"][1]["box"] = [160, 1400, 920, 1540]
        rows = examine(d, doc, label, ["placement-not-judged"], 1)
        ck(label + ": one honest placement block", len(rows) == 1 and rows[0]["msg"] ==
           compose.qa_check.PLACEMENT_NOT_JUDGED, rows)
    doc["style"]["style"] = "none"
    examine(d, doc, "captions off need no placements", [], 0)
    doc["style"]["style"] = "clean"
    for c in doc["chunks"]:
        c["box"] = [160, 1400, 920, 1540]
    examine(d, doc, "placed captions are judged", [], 0)
    doc["chunks"][1]["box"] = [160, 1098, 920, 1238]
    examine(d, doc, "placed captions give real findings", ["caption-on-face"], 1)


def offscreen_hook(outside):
    x, y, width, size = compose.hook_box(1080, 1920)
    return (1080 + outside - width / 2, y, width, size)


def case_offscreen(scratch):
    d, doc = fixture(scratch, "offscreen")
    for outside in (8, 5):
        examine(d, doc, f"offscreen {outside}px", ["text-off-screen"] if outside == 8 else [],
                1 if outside == 8 else 0, hook_box=offscreen_hook(outside))
    # A contained word must not repeat its chunk's off-frame finding.
    doc["chunks"][0]["box"] = [330, 1400, 1090, 1540]
    examine(d, doc, "offscreen chunk belongs to caption check", [], 0)
    p = cs.sh([cs.PY, "-X", "utf8", "-I", CHECKS / "check.py", d, "--phase", "pre"])
    qa = cs.load(d / "work/qa.json")
    offscreen = [r for r in qa.get("checks", [])
                 if r["check"] in ("caption-off-frame", "text-off-screen")]
    ck("offscreen chunk: exactly one off-frame row in qa.json", p.returncode == 1
       and len(offscreen) == 1 and offscreen[0]["check"] == "caption-off-frame"
       and offscreen[0]["module"] == "caption_check", (p.stdout, p.stderr, qa))
    width = captions.text_width_em(doc["chunks"][0]["text"],
                                   doc.get("font", captions.STYLES[doc["style"]["style"]]["font"])) * 64
    centre = 1088 - width / 2
    doc["chunks"][0]["box"] = [centre - 380, 1400, centre + 380, 1540]
    examine(d, doc, "offscreen word contained in off-frame chunk", [], 0)
    # Stored preview coordinates must not reintroduce duplicate word findings.
    doc["width"] = 720
    for c in doc["chunks"]:
        c["box"] = [v * 2 / 3 for v in c["box"]]
    examine(d, doc, "offscreen chunk stored at 720", [], 0)

    # A malformed, short chunk can let the line-height word box protrude.
    # That independent off-screen word is still layout_check's responsibility.
    doc.pop("width")
    doc["chunks"][0]["box"] = [160, 1870, 920, 1910]
    doc["chunks"][1]["box"] = [160, 1400, 920, 1540]
    examine(d, doc, "offscreen protruding word", ["text-off-screen"], 1)


def case_collision(scratch):
    d, doc = fixture(scratch, "collision")
    x, y, width, size = compose.hook_box(1080, 1920)
    height = size * 1.15 * compose.title_lines("A useful title", width, size)
    bottom = y + height
    # Equal widths make the overlap fraction relative to the smaller still.
    for fraction in (0.4, 0.35, 0.3, 0.25, 0.2):
        top = bottom - fraction * min(height, 140)
        doc["chunks"][0]["box"] = [x - width / 2, top, x + width / 2, top + 140]
        examine(d, doc, f"collision {fraction:.0%}", ["text-collision"] if fraction > 0.3 else [],
                1 if fraction > 0.3 else 0)
    # Same geometry after the hook disappears must be clear (exclusive ends).
    doc["chunks"][0].update(start_f=60, end_f=75)
    top = bottom - 0.4 * min(height, 140)
    doc["chunks"][0]["box"] = [x - width / 2, top, x + width / 2, top + 140]
    examine(d, doc, "collision after hook", [], 0)
    bm = cs.load(d / "beat-map-selection.json")
    bm["beats"][0]["scene"] = {"id": "unused-fixture-scene"}
    save(d / "beat-map-selection.json", bm)
    doc["chunks"][0].update(start_f=15, end_f=30)
    examine(d, doc, "collision scene suppresses hook", [], 0)


def case_covered(scratch):
    d, doc = fixture(scratch, "covered")
    # The second caption starts after frame 60, so the whole head is protected.
    for fraction in (0.7, 0.65, 0.6):
        top = HEAD[3] - fraction * (64 * 1.2) - 16
        doc["chunks"][1]["box"] = [160, top, 920, top + 140]
        rows = examine(d, doc, f"covered {fraction:.0%}",
                       ["word-covered"] if fraction >= 0.65 else ["caption-on-face"], 1)
        if fraction == 0.7:
            ck("covered: plain message", len(rows) == 1 and rows[0]["msg"] ==
               'The word \'Coaching.\' at 3.00 s sits on your face. On the Look Picker, choose "No captions", then Send.', rows)
            p = cs.sh([cs.PY, "-X", "utf8", "-I", CHECKS / "check.py", d, "--phase", "pre"])
            qa = cs.load(d / "work/qa.json")
            ck("covered: entry point blocks and saves word-covered", p.returncode == 1 and any(
                r["check"] == "word-covered" and r["module"] == "layout_check"
                and r["level"] == "block" and r["where"] == "caption 1" and r["at"] == 3.0
                for r in qa.get("checks", [])), (p.stdout, p.stderr, qa))


def case_hook_face(scratch):
    d, doc = fixture(scratch, "hook-face")
    # FX2b protects 15%-75% of the head while the opening hook is active.
    face_top = HEAD[1] + 0.15 * (HEAD[3] - HEAD[1])
    face_bottom = HEAD[1] + 0.75 * (HEAD[3] - HEAD[1])
    top = face_top - 140
    doc["chunks"][0]["box"] = [160, top, 920, face_top]
    examine(d, doc, "hook allows caption over hair", [], 0)
    for fraction in (0.7, 0.65, 0.6):
        top = face_bottom - fraction * (64 * 1.2) - 16
        doc["chunks"][0]["box"] = [160, top, 920, top + 140]
        rows = examine(d, doc, f"hook face covered {fraction:.0%}",
                       ["word-covered"] if fraction >= 0.65 else ["caption-on-face"], 1)
        ck("one-line plain hook: advice names No captions",
           all(r["msg"].endswith(compose.QA_NO_CAPTIONS_ADVICE) and compose.QA_OVERLAY_ADVICE not in r["msg"]
               for r in rows), rows)


def case_overlay_advice(scratch):
    d, doc = fixture(scratch, "overlay-advice")
    doc["chunks"][1]["box"] = [160, 1098, 920, 1238]
    bm = json.loads((d / "beat-map-selection.json").read_text(encoding="utf-8"))
    bm["beats"][1]["scene"] = {"id": "counter", "slots": {}, "params": {}}
    save(d / "beat-map-selection.json", bm)
    rows = examine(d, doc, "caption under a small overlay", ["caption-on-face"], 1)
    ck("small overlay: advice names the checkbox", rows[0]["msg"].endswith(compose.QA_OVERLAY_ADVICE), rows)
    bm["beats"][1]["scene"] = None
    save(d / "beat-map-selection.json", bm)
    rows = examine(d, doc, "caption without an overlay", ["caption-on-face"], 1)
    ck("no overlay: advice names No captions", rows[0]["msg"].endswith(compose.QA_NO_CAPTIONS_ADVICE), rows)
    bm["beats"][1]["scene"] = {"id": "unused-fixture-scene"}
    save(d / "beat-map-selection.json", bm)
    rows = examine(d, doc, "missing optional scene setting is unknown", ["caption-on-face"], 1)
    ck("unknown overlay: advice names No captions", rows[0]["msg"].endswith(compose.QA_NO_CAPTIONS_ADVICE), rows)


def case_broll(scratch):
    d, doc = fixture(scratch, "broll")
    # This caption is inside the hook span: overlap its protected face band.
    face_bottom = HEAD[1] + 0.75 * (HEAD[3] - HEAD[1])
    top = face_bottom - 0.7 * (64 * 1.2) - 16
    doc["chunks"][0]["box"] = [160, top, 920, top + 140]
    bm = json.loads((d / "beat-map-selection.json").read_text(encoding="utf-8"))
    bm["beats"][0]["broll"] = {"src": "broll/clip.mp4", "in": 0, "out": 60, "fit": "cover"}
    save(d / "beat-map-selection.json", bm)
    examine(d, doc, "over full-frame B-roll the hidden face is not covered", [], 0)
    bm["beats"][1]["broll"] = bm["beats"][0].pop("broll")
    save(d / "beat-map-selection.json", bm)
    examine(d, doc, "B-roll on another beat leaves this face showing", ["word-covered"], 1)


def case_touch(scratch):
    d, doc = fixture(scratch, "touch")
    # Test whole-head contact after the hook ends, using the later caption.
    doc["chunks"][1]["box"] = [160, 1098, 920, 1238]
    examine(d, doc, "touch 2px", ["caption-on-face"], 1)
    doc["chunks"][1]["box"] = [160, 1100, 920, 1240]
    examine(d, doc, "touch edge only", [], 0)


def case_noface(scratch):
    d, doc = fixture(scratch, "noface")
    (d / "work/anchors.json").unlink()
    examine(d, doc, "noface missing anchors", ["layout-face-unchecked"], 0)
    hook = offscreen_hook(8)
    examine(d, doc, "noface still blocks offscreen", ["layout-face-unchecked", "text-off-screen"], 1,
            hook_box=hook)
    (d / "work/scale_track.json").unlink()
    examine(d, doc, "noface cannot load placer", ["layout-face-unchecked", "text-off-screen"], 1,
            hook_box=hook)


CASES = {"clean": case_clean, "unplaced": case_unplaced, "offscreen": case_offscreen, "collision": case_collision,
         "covered": case_covered, "hook-face": case_hook_face, "overlay-advice": case_overlay_advice, "broll": case_broll,
         "touch": case_touch, "noface": case_noface}


@isolated_home()
def main():
    global LC
    cs.ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch", type=Path)
    ap.add_argument("--case", choices=list(CASES))
    args = ap.parse_args()
    scratch = args.scratch.resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("layout_check", CHECKS / "layout_check.py")
    LC = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(LC)
    except (OSError, ImportError) as exc:
        ck("layout check loads", False, exc)
        return 1
    print(f"python {cs.PY}")
    for name in [args.case] if args.case else CASES:
        try:
            CASES[name](scratch)
        except Exception as exc:
            ck(name + ": completes", False, repr(exc))
    print(f"\n{len(fails)} failed" if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
