"""Auto edit and per-style learning: <scratch> [--case NAME]; synthetic reels only."""
import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from editor_test_state import copy_tool_state
from saved_style_test import SKILLS, module
from save_style_test import write
import saved_style as ss
import style_learn as learn

STYLE = {"look": {"id": "warm", "strength": .6}, "caption_style": {"style": "clean"},
         "edit_style": {"style": "punch-in", "punch_scale": 1.12}, "music": {"bed_gain_db": -18},
         "cut": {"default_attempt": "last"}, "transitions": {"allowed": []}, "font": "Inter", "accent": "#FFD84D"}


def setup(root, **config):
    workspace = root / "workspace"
    write(workspace / "editor/editor.config.json", config)
    ss.save(json.loads(json.dumps(STYLE)), "style-1")
    return workspace


def reel(workspace, number, *, small=True, boards=None):
    target = workspace / "videos" / f"reel-{number}"
    target.mkdir(parents=True)
    write(target / "work/render-ok.json", {"preview": "Preview 720p.mp4"})
    if small:
        write(target / "cut-board.config.json", {"gap_default_ms": 150, "lines": [{"id": "l_001", "default": 1}]})
        write(target / "cut-selection.json", {"lines": [{"id": "l_001", "pick": 1, "drop": False,
                                                       "gap_after": {"mode": "override", "ms": 70}}]})
    for filename, data in (boards or {}).items():
        write(target / filename, data)
    return target


def approve(workspace, number, *, auto=False, **kwargs):
    target = reel(workspace, number, **kwargs)
    if auto:
        assert ss.picker_lines(target) == ["Auto edit with Style 1. Say stop anytime."]
    else:
        ss.pick(target, "Style 1")
    return target, learn.record_approval(target)


def history(name="style-1"):
    return json.loads(ss.path(name).with_suffix(".learn.json").read_text(encoding="utf-8"))


def offer(lines):
    return any("is ready for Auto edit:" in line for line in lines)


def ready(workspace):
    for i in range(3):
        _, lines = approve(workspace, i)
        assert offer(lines) == (i == 2), lines


def case_unlock(root):
    workspace = setup(root)
    assert not learn.status("Style 1")["ready"]
    for i in range(3):
        target, lines = approve(workspace, i)
        assert offer(lines) == (i == 2), lines
    assert lines == ["Style 1 is ready for Auto edit: the last 3 reels needed only small tweaks. Turn it on?"]
    before = ss.path("style-1").with_suffix(".learn.json").read_bytes()
    assert learn.record_approval(target) == []
    assert ss.path("style-1").with_suffix(".learn.json").read_bytes() == before
    write(target / "work/render-ok.json", {"preview": "Another preview.mp4"})
    assert not offer(learn.record_approval(target)) and len(history()["reels"]) == 4
    assert history()["auto"]["offered_reel"] == 2
    for i in range(4, 6):
        _, lines = approve(workspace, i)
        assert offer(lines) == (i == 5), lines
    # Only a saved or auto pick for this exact reel counts.
    other = reel(workspace, "unpicked")
    assert learn.record_approval(other) == []
    for how in ("fresh", "copy"):
        ss.pick(other, how)
        assert learn.record_approval(other) == []
    assert len(history()["reels"]) == 6
    write(target / "work/render-ok.json", {"preview": "Returned to this reel.mp4"})
    learn.record_approval(target)
    assert len(history()["reels"]) == 7, "Learning lost an earlier reel's pick after switching reels"
    # Per-workspace threshold, excluding booleans and invalid numbers.
    for value, expected in ((1, 1), (4, 4), (True, 3), (0, 3), (1.5, 3), ("2", 3)):
        write(workspace / "editor/editor.config.json", {"auto_edit": {"unlock_after": value}})
        assert learn.status("Style 1", workspace=workspace)["threshold"] == expected
    assert learn.status("Style 1")["threshold"] == 3


def case_reset(root):
    workspace = setup(root)
    for i in range(6):
        boards = {"cut-selection.json": {"lines": [{"id": "l_001", "pick": 0, "drop": False}]}} if i == 2 else None
        _, lines = approve(workspace, i, boards=boards)
        assert offer(lines) == (i == 5), lines
    assert history()["reels"][2]["why"] == "a take was swapped"
    assert learn.status("style-1")["good_in_a_row"] == 3


def case_six_small(root):
    workspace = setup(root)
    boards = {"tweak-selection.json": {"version": "v1", "marks": [
        {"type": "tight", "a": i, "ms": 150} for i in range(6)]}}
    _, lines = approve(workspace, 1, small=False, boards=boards)
    row = history()["reels"][-1]
    assert len(row["changes"]) == 6 and all(c["small"] for c in row["changes"])
    assert row["big"] and row["why"] == "more than 5 small changes" and not offer(lines)
    boards["tweak-selection.json"]["marks"].pop()
    approve(workspace, 2, small=False, boards=boards)
    assert not history()["reels"][-1]["big"]


def music(delta):
    return {"config.json": {"bed_default": {"gain_db": -18}},
            "sound-selection.json": {"bed": {"gain_db": -18 + delta}}}


def case_self_correct(root):
    workspace = setup(root)
    before = ss.path("style-1").read_bytes()
    for i in range(3):
        _, lines = approve(workspace, i, small=False, boards=music(-2))
        if i < 2:
            assert ss.path("style-1").read_bytes() == before
    assert ss.load(name="style-1")["music"]["bed_gain_db"] == -20
    assert ss.path("style-1@v1").read_bytes() == before
    assert any("turn the music down about 2 dB" in line for line in lines), lines
    assert history()["learned"][0]["reels"] == [0, 1, 2]
    # No reuse of those three records after correction; missing changes break a streak.
    for i in range(3, 5):
        approve(workspace, i, small=False, boards=music(-2))
    assert len(history()["learned"]) == 1
    for name, deltas in (("mixed", [-2, 2, -2]), ("missing", [-2, None, -2])):
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / name)}):
            ws = setup(root / name)
            original = ss.path("style-1").read_bytes()
            for i, delta in enumerate(deltas):
                approve(ws, i, small=False, boards=music(delta) if delta is not None else {})
            assert ss.path("style-1").read_bytes() == original and not history()["learned"]
    # The grade uses the saved style proposal, and strength rounds to .05.
    for name, deltas in (("strength", [-.1, -.1, -.1]), ("strength-mixed", [-.1, .1, -.1])):
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / name)}):
            ws = setup(root / name)
            original = ss.path("style-1").read_bytes()
            for i, delta in enumerate(deltas):
                _, lines = approve(ws, i, small=False, boards={
                    "grade-selection.json": {"look": {"id": "warm", "strength": .6 + delta}}})
            assert ss.load(name="style-1")["look"]["strength"] == (.5 if name == "strength" else .6)
            if name == "strength":
                assert ss.path("style-1@v1").read_bytes() == original
                assert any("grade strength down about 10%" in line for line in lines)
            else:
                assert not history()["learned"]
    for name, key, boards, expected in (
            ("captions", "caption_style.style", {"look-picker-selection.json": {"caption_style": {"style": "boxed"}}}, "boxed"),
            ("look", "look.id", {"grade-selection.json": {"look": {"id": "natural"}}}, "natural"),
            ("scale", "edit_style.punch_scale", {"beat-map-selection.json": {"edit_style": {"punch_scale": 1.14}}}, 1.14)):
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / name)}):
            ws = setup(root / name)
            for i in range(3):
                approve(ws, i, small=False, boards=boards)
            assert ss._get(ss.load(name="style-1"), key) == expected
            assert len(history()["learned"]) == 1


def case_timing_recorded(root):
    workspace = setup(root)
    before = ss.path("style-1").read_bytes()
    for i in range(3):
        _, lines = approve(workspace, i, boards={"cut-selection.json": {"gap_default_ms": 70, "lines": [
            {"id": "l_001", "gap_after": {"mode": "override", "ms": 70}}]}})
    for row in history()["reels"]:
        default, pause = row["changes"]
        assert default["key"] == "cut.pause_ms" and default["delta"] == -80
        assert pause == dict(source="cut-board.pause", key=None, small=True, detail="a pause was changed",
                             line="l_001", mode="override", proposed_ms=150, sent_ms=70, delta_ms=-80)
    assert ss.load(name="style-1")["cut"]["pause_ms"] == 70
    assert ss.path("style-1@v1").read_bytes() == before
    assert "I noticed you tighten pauses about 80 ms, so Style 1 now does that." in lines
    after = ss.path("style-1").read_bytes()
    # The rest of the timing data, including the cut's version, survives too.
    target = reel(workspace, "other-timing", boards={
        "tweak-selection.json": {"version": "v7", "marks": [{"type": "cut", "a": 2, "b": 3}, {"type": "loose", "a": 4, "ms": 500}]},
        "config.json": {"cues": [{"id": "hit", "time": 1}]},
        "sound-selection.json": {"cues": [{"id": "hit", "time": 1.08}]}})
    edits = learn.changes(target, STYLE)
    assert next(c for c in edits if c["source"] == "tweak.cut") == dict(
        source="tweak.cut", key=None, small=False, detail="a cut was added", a_s=2, b_s=3, version="v7")
    cue = next(c for c in edits if c["source"] == "sound.cue")
    assert cue["proposed_s"] == 1 and cue["sent_s"] == 1.08 and cue["delta_ms"] == 80 and cue["cue"] == "hit"
    assert ss.path("style-1").read_bytes() == after


def edge_boards(marks, version="v1"):
    return {"tweak-board.config.json": {"version": "v1", "map": [[0, 2, 0, 2], [2, 4, 5, 7]]},
            "tweak-selection.json": {"version": version, "marks": marks}}


def case_nudge_learn(root):
    workspace = setup(root)
    ss.save({**STYLE, "cut": {"default_attempt": "last", "pause_ms": 300}}, "style-1")
    tail = {"type": "cut", "a": 1.96, "b": 2}
    head = {"type": "cut", "a": 2, "b": 2.04}
    for i in range(3):
        marks = [{"type": "cut", "a": 2, "b": 2.02}, {"type": "cut", "a": 2, "b": 2.06}] if i == 1 else [head]
        _, lines = approve(workspace, i, small=False, boards=edge_boards(marks))
    assert ss.load(name="style-1")["cut"]["nudge_ms"] == 40
    assert "I noticed you trim cuts about 40 ms later, so Style 1 now does that." in lines
    row = history()["reels"][0]["changes"][0]
    assert row["source"] == "tweak.edge" and row["small"] and row["edge"] == "head"
    assert row["join_s"] == 2 and row["nudge_ms"] == 40 and row["delta"] == 40
    assert offer(lines)
    for name, marks, version in (("far", [{"type": "cut", "a": .2, "b": .4}], "v1"),
                                 ("stale", [head], "v0"),
                                 ("long", [{"type": "cut", "a": 1, "b": 2}], "v1"),
                                 ("cross", [{"type": "cut", "a": 1.96, "b": 2.04}], "v1")):
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / name)}):
            ws = setup(root / name)
            before = ss.path("style-1").read_bytes()
            for i in range(3):
                approve(ws, i, small=False, boards=edge_boards(marks, version))
            assert ss.path("style-1").read_bytes() == before and not history()["learned"]
            edits = history()["reels"][0]["changes"]
            assert all(not c["small"] for c in edits)
    # Tail rows never affect the mean, even alongside head trims on the same reel.
    with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / "mixed")}):
        ws = setup(root / "mixed")
        ss.save({**STYLE, "cut": {"default_attempt": "last", "pause_ms": 300}}, "style-1")
        for i in range(3):
            approve(ws, i, small=False, boards=edge_boards([tail, head]))
        assert ss.load(name="style-1")["cut"]["nudge_ms"] == 40
        assert all(c["small"] for c in history()["reels"][0]["changes"])
    # Edge rows remain individual small changes for the >5 rule.
    approve(workspace, "six-edges", small=False, boards=edge_boards([tail] * 6))
    assert history()["reels"][-1]["why"] == "more than 5 small changes"


def case_nudge_swallowed(root):
    for name, pause, old in (("no-room", 120, None), ("at-room", 160, 20), ("past-room", 120, 40)):
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / name)}):
            workspace = setup(root / name, auto_edit={"unlock_after": 4})
            cut = {"default_attempt": "last", "pause_ms": pause}
            if old is not None:
                cut["nudge_ms"] = old
            ss.save({**STYLE, "cut": cut}, "style-1")
            before = ss.path("style-1").read_bytes()
            for i in range(3):
                _, lines = approve(workspace, i, small=False, boards=edge_boards([
                    {"type": "cut", "a": 2, "b": 2.04}]))
                assert lines == [], lines
            assert ss.path("style-1").read_bytes() == before and not history()["learned"]
            assert not list(ss.path("style-1").parent.glob("style-1@v*.json"))
            assert learn.status("style-1")["good_in_a_row"] == 3
            assert len(history()["reels"]) == 3
            for row in history()["reels"]:
                change, = row["changes"]
                assert not row["big"] and change["small"] and change["source"] == "tweak.edge"
                assert change["edge"] == "head" and change["nudge_ms"] == change["delta"] == 40


def case_nudge_partial(root):
    for name, pause, expected in (("saved", 160, 20), ("learned", 120, 20),
                                  ("selection", None, 10), ("board", None, 10), ("default", None, 10)):
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / name)}):
            workspace = setup(root / name)
            if pause is not None:
                ss.save({**STYLE, "cut": {"default_attempt": "last", "pause_ms": pause}}, "style-1")
            boards = edge_boards([{"type": "cut", "a": 2, "b": 2.04}])
            if name in ("learned", "selection", "board"):
                boards["cut-board.config.json"] = {"gap_default_ms": 120 if name == "learned" else 160}
            if name in ("learned", "selection"):
                boards["cut-selection.json"] = {"gap_default_ms": 160}
            for i in range(3):
                _, lines = approve(workspace, i, small=False, boards=boards)
            assert ss.load(name="style-1")["cut"]["nudge_ms"] == expected
            assert f"I noticed you trim cuts about {expected} ms later, so Style 1 now does that." in lines
            learned, = [row for row in history()["learned"] if row["key"] == "cut.nudge_ms"]
            assert learned["from"] == 0 and learned["to"] == expected and learned["reels"] == [0, 1, 2]
            if name == "learned":
                assert ss.load(name="style-1")["cut"]["pause_ms"] == 160


def case_nudge_room_next_reel(root):
    for name, pause in (("missing", None), ("out-of-range", 700)):
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / name)}):
            workspace = setup(root / name, auto_edit={"unlock_after": 4})
            if pause is not None:
                ss.save({**STYLE, "cut": {"default_attempt": "last", "pause_ms": pause}}, "style-1")
            boards = edge_boards([{"type": "cut", "a": 2, "b": 2.04}])
            boards["cut-board.config.json"] = {"gap_default_ms": 300}
            boards["cut-selection.json"] = {"gap_default_ms": 300}
            for i in range(3):
                _, lines = approve(workspace, i, small=False, boards=boards)
                if i < 2:
                    assert lines == [], lines
            style = ss.load(name="style-1")
            assert style["cut"].get("pause_ms") == pause
            assert style["cut"]["nudge_ms"] == 10, style["cut"]
            assert lines == ["I noticed you trim cuts about 10 ms later, so Style 1 now does that."], lines
            learned, = history()["learned"]
            assert learned["key"] == "cut.nudge_ms" and learned["from"] == 0 and learned["to"] == 10
            assert learn.status("style-1")["good_in_a_row"] == 3
            assert module("reel-first-cuts", "make_board").pause_default(workspace / "videos/reel-2") == 150


def case_nudge_room_shrinks(root):
    workspace = setup(root, auto_edit={"unlock_after": 4})
    ss.save({**STYLE, "cut": {"default_attempt": "last", "pause_ms": 160, "nudge_ms": 40}}, "style-1")
    before = ss.path("style-1").read_bytes()
    for i in range(3):
        _, lines = approve(workspace, i, small=False, boards=edge_boards([
            {"type": "cut", "a": 2, "b": 2.04}]))
        assert lines == [], lines
    assert ss.load(name="style-1")["cut"]["nudge_ms"] == 40
    assert ss.path("style-1").read_bytes() == before and not history()["learned"]
    assert len(history()["reels"]) == learn.status("style-1")["good_in_a_row"] == 3


def case_earlier_ignored(root):
    workspace = setup(root)
    before = ss.path("style-1").read_bytes()
    for i in range(3):
        _, lines = approve(workspace, i, small=False, boards=edge_boards([
            {"type": "cut", "a": 1.96, "b": 2}]))
        assert lines == ([] if i < 2 else [
            "Style 1 is ready for Auto edit: the last 3 reels needed only small tweaks. Turn it on?"])
    assert ss.path("style-1").read_bytes() == before and not history()["learned"]
    assert not list(ss.path("style-1").parent.glob("style-1@v*.json"))
    assert learn.status("style-1")["good_in_a_row"] == 3
    for row in history()["reels"]:
        change, = row["changes"]
        assert not row["big"] and change["small"] and change["source"] == "tweak.edge"
        assert change["edge"] == "tail" and change["nudge_ms"] == change["delta"] == -40


def case_frame_edges(root):
    workspace = setup(root)
    for fps in (30, 29.97, 23.976):
        join = 37 / fps
        anchor = round(join, 3)
        for source in ("board", "cuts", "probe", "unknown"):
            boards = edge_boards([])
            cfg = boards["tweak-board.config.json"]
            cfg["map"] = [[0, join, 0, join], [join, join + 2, 5, 7]]
            if source == "board":
                cfg["fps"] = fps
            elif source == "cuts":
                boards["work/cuts.json"] = {"fps": fps}
            elif source == "probe":
                boards["work/probe.json"] = {"fps": {"measured_fps": fps}}
            for edge in ("tail", "head"):
                mark = {"type": "cut", "a": round(anchor - .04, 3) if edge == "tail" else anchor,
                        "b": anchor if edge == "tail" else round(anchor + .04, 3)}
                boards["tweak-selection.json"]["marks"] = [mark]
                target = reel(workspace, f"{fps}-{source}-{edge}", small=False, boards=boards)
                change, = learn.changes(target, STYLE)
                assert change["source"] == "tweak.edge" and change["small"] and change["edge"] == edge
                assert change["join_s"] == join and change["nudge_ms"] == (-40 if edge == "tail" else 40)
            for name, a, b in (("far", join - .04 - 2 / fps, join - 2 / fps),
                               ("long", join - .151, join),
                               ("other-end", join - .151, join - .01)):
                boards["tweak-selection.json"]["marks"] = [{"type": "cut", "a": a, "b": b}]
                target = reel(workspace, f"{fps}-{source}-{name}", small=False, boards=boards)
                change, = learn.changes(target, STYLE)
                assert change["source"] == "tweak.cut" and not change["small"]


def case_pause_tweak(root):
    workspace = setup(root)
    for i in range(3):
        _, lines = approve(workspace, i, small=False, boards={
            "cut-board.config.json": {"gap_default_ms": 300},
            "tweak-selection.json": {"marks": [{"type": "tight", "a": 1, "ms": 220},
                                                {"type": "tight", "a": 3, "ms": 200}]}})
    assert ss.load(name="style-1")["cut"]["pause_ms"] == 60  # starting 150 minus mean 90
    assert "I noticed you tighten pauses about 90 ms, so Style 1 now does that." in lines
    assert sum(c["key"] == "cut.pause_ms" for c in history()["reels"][0]["changes"]) == 1
    for name, boards in (("mixed", {"cut-board.config.json": {"gap_default_ms": 300},
            "tweak-selection.json": {"marks": [{"type": "tight", "a": 1, "ms": 220},
                                                {"type": "loose", "a": 3, "ms": 500}]}}),
            ("no-cuts", {"cut-board.config.json": {"gap_default_ms": 150},
                "cut-selection.json": {"gap_default_ms": 70},
                "tweak-selection.json": {"marks": [{"type": "loose", "a": 1, "ms": 500}]},
                "config.json": {"cues": [{"id": "hit", "time": 1}]},
                "sound-selection.json": {"cues": [{"id": "hit", "time": 1.04}]}})):
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / name)}):
            ws = setup(root / name)
            for i in range(3):
                approve(ws, i, small=False, boards=boards)
            assert "nudge_ms" not in ss.load(name="style-1")["cut"]
            assert not any(c["source"] == "tweak.edge" for r in history()["reels"] for c in r["changes"])
            if name == "mixed":
                assert not history()["learned"]
            else:
                assert ss.load(name="style-1")["cut"]["pause_ms"] == 70, "Default-pause Send must win over Tweak pauses"


def case_timing_limits(root):
    for name, key, old, delta, expected in (("pause-high", "pause_ms", 580, 80, 600),
            ("pause-low", "pause_ms", 50, -80, 40), ("later", "nudge_ms", 120, 40, 150),
            ("pause-ceiling", "pause_ms", 600, 80, 600),
            ("pause-floor", "pause_ms", 40, -80, 40), ("nudge-ceiling", "nudge_ms", 150, 40, 150)):
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / name)}):
            ws = setup(root / name)
            ss.save({**STYLE, "cut": {"default_attempt": "last", "pause_ms": 300, key: old}}, "style-1")
            before = ss.path("style-1").read_bytes()
            if key == "pause_ms":
                boards = {"cut-board.config.json": {"gap_default_ms": 150},
                          "cut-selection.json": {"gap_default_ms": 150 + delta}}
            else:
                marks = [{"type": "cut", "a": 2 if delta > 0 else 1.96,
                          "b": 2.04 if delta > 0 else 2}] * 2
                boards = edge_boards(marks)
            for i in range(3):
                _, lines = approve(ws, i, small=False, boards=boards)
            assert ss.load(name="style-1")["cut"][key] == expected
            assert len(history()["learned"]) == int(expected != old)
            learned_lines = [line for line in lines if line.startswith("I noticed")]
            if expected == old:
                assert not learned_lines and ss.path("style-1").read_bytes() == before
                assert not list(ss.path("style-1").parent.glob("style-1@v*.json"))
            else:
                words = (f"{'loosen' if delta > 0 else 'tighten'} pauses about {abs(expected - old)} ms"
                         if key == "pause_ms" else f"trim cuts about {expected} ms later")
                assert learned_lines == [f"I noticed you {words}, so Style 1 now does that."]


def case_decline(root):
    workspace = setup(root)
    ready(workspace)
    learn.decline("Style 1")
    assert history()["auto"]["declined_reel"] == 2
    assert history()["auto"]["offered_reel"] is None
    for i in range(3, 8):
        boards = {"cut-selection.json": {"lines": [{"id": "l_001", "pick": 0}]}} if i == 4 else None
        _, lines = approve(workspace, i, boards=boards)
        assert offer(lines) == (i == 7), lines


def case_auto_pick(root):
    workspace = setup(root)
    assert not learn.status("Style 1")["on"]
    try:
        learn.set_auto("Style 1", True)
    except ValueError:
        pass
    assert not learn.status("Style 1")["on"]
    ready(workspace)
    learn.set_auto("Style 1", True)
    target = reel(workspace, "auto", small=False)
    assert ss.load(target) == {}, "Auto edit applied before the picker recorded this reel's pick"
    result = subprocess.run([sys.executable, "-X", "utf8", "-I", str(SKILLS / "_shared/saved_style.py"),
                             "picker", str(target)], capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0 and not result.stderr
    assert result.stdout.splitlines() == ["Auto edit with Style 1. Say stop anytime."]
    assert ss.pick_for(target)["how"] == "auto" and ss.load(target)["look"] == STYLE["look"]
    assert ss.pick(target, "normal") == "This reel uses Style 1."
    assert ss.pick_for(target)["how"] == "saved" and ss.pick_for(target)["style"] == "style-1"
    assert ss.load(target)["edit_style"] == STYLE["edit_style"]
    assert ss.picker_lines(target) == ["This reel uses Style 1."]
    ss.save({"font": "Other"}, "style-2")
    ss.set_default("style-2")
    assert ss.picker_lines(workspace / "videos/new")[0] == "Which style for this reel?"
    learn.set_auto("Style 1", False)
    assert not learn.status("Style 1")["on"]


def case_auto_no_stop(root):
    workspace = setup(root)
    ready(workspace)
    learn.set_auto("Style 1", True)
    target = reel(workspace, "auto", small=False)
    ss.picker_lines(target)
    assert not list(target.glob("*-selection.json"))
    editing = module("reel-canvas-build", "styles")
    captions = module("reel-captions", "captions")
    grade = module("reel-grade", "bake_grade")
    assert editing.pick_style({}, reel=target, remember=False) == (STYLE["edit_style"], "saved")
    assert captions.pick_style(target, {}, remember=False) == (STYLE["caption_style"], "saved")
    assert grade.resolve_look(target) == STYLE["look"]
    ss.pick(target, "fresh")
    try:
        editing.pick_style({}, reel=target, remember=False)
    except editing.Stop:
        pass
    else:
        raise AssertionError("Start fresh did not ask for an editing style")


def case_paid_still_asks(root):
    workspace = setup(root)
    ready(workspace)
    learn.set_auto("Style 1", True)
    ss.picker_lines(reel(workspace, "paid", small=False))
    import cost_ask
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert cost_ask.refuse_without_yes(False) == 3
    assert output.getvalue().strip() == cost_ask.REFUSAL
    assert cost_ask.refuse_without_yes(True) is None


def case_qa_still_stops(root):
    workspace = setup(root)
    ready(workspace)
    learn.set_auto("Style 1", True)
    import qa_test as qa
    # The existing tiny anchor fixture exercises the real discovery and QA runner.
    target = qa.reel(workspace / "videos", "qa")
    ss.picker_lines(target)
    result, report = qa.qa(target)
    assert result.returncode == 0 and not report["blocks"], (result.stdout, result.stderr)
    qa.edit_beats(target, lambda beats: beats[0]["speech_anchor"].update(text="We stopped"))
    result, report = qa.qa(target)
    assert result.returncode == 1 and qa.has(report, "anchor-lost"), (result.stdout, result.stderr)
    assert learn.status("Style 1")["on"], "QA must stop the edit without changing the learning history"


def case_relock(root):
    workspace = setup(root)
    ready(workspace)
    learn.decline("Style 1")
    for i in range(3, 6):
        approve(workspace, i)
    learn.set_auto("Style 1", True)
    _, lines = approve(workspace, "big", auto=True, boards={
        "cut-selection.json": {"lines": [{"id": "l_001", "pick": 0}]}})
    assert lines == ["Auto edit is off for Style 1: this reel needed a bigger change (a take was swapped). 3 more smooth reels turn it back on."]
    assert not learn.status("Style 1")["on"] and history()["reels"][-1]["mode"] == "auto"
    for i in range(6, 9):
        _, lines = approve(workspace, i)
        assert offer(lines) == (i == 8), lines
    learn.set_auto("Style 1", True)
    approve(workspace, "smooth", auto=True)
    assert learn.status("Style 1")["on"]


def case_hub(root):
    workspace = setup(root)
    ready(workspace)
    hub = module("editor-doctor", "hub_rows")
    row = hub.build(workspace)["styles"][0]
    assert row["auto"] == dict(label="Style 1", ready=True, on=False, good_in_a_row=3, threshold=3)
    target = ss.path("style-1").with_suffix(".learn.json")
    before = target.read_bytes()
    for i, raw in enumerate((b"{", b"[]", b"null", b'{"schema":1,"reels":[],"auto":{},"learned":[]}')):
        target.write_bytes(raw)
        auto = hub.build(workspace)["styles"][0]["auto"]
        assert not auto["ready"] and not auto["on"]
        picked = reel(workspace, f"bad-{i}", small=False)
        ss.pick(picked, "Style 1")
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            assert learn.record_approval(picked) == []
        assert output.getvalue().splitlines() == [learn.NOTE] and target.read_bytes() == raw
    target.write_bytes(before)


def case_sources(root):
    workspace = setup(root)
    target = reel(workspace, 1, small=False)
    before = ss.path("style-1").read_bytes()
    # Every big source has a matching unchanged negative.
    write(target / "cut-board.config.json", {"gap_default_ms": 150, "lines": [
        {"id": "keep", "default": 1}, {"id": "gone", "default": None}]})
    write(target / "cut-selection.json", {"lines": [{"id": "keep", "pick": 1, "drop": False},
                                                        {"id": "gone", "drop": True}]})
    assert learn.changes(target, STYLE) == []
    write(target / "cut-selection.json", {"lines": [{"id": "keep", "drop": True},
                                                        {"id": "gone", "drop": False, "pick": 0}]})
    assert [c["source"] for c in learn.changes(target, STYLE)] == ["cut-board.drop", "cut-board.restore"]
    write(target / "beat-map.state.json", {"proposed": {"b1": {"layout": "full"}}})
    write(target / "beat-map-selection.json", {"beats": [{"id": "b1", "layout": "full"}]})
    assert not any(c["source"] == "beat-map.layout" for c in learn.changes(target, STYLE))
    write(target / "beat-map-selection.json", {"beats": [{"id": "b1", "layout": "split"}]})
    assert next(c for c in learn.changes(target, STYLE) if c["source"] == "beat-map.layout")["small"] is False
    for delta, small in ((-3, True), (-3.1, False), (3, True), (3.1, False)):
        for filename, data in music(delta).items():
            write(target / filename, data)
        assert next(c for c in learn.changes(target, STYLE) if c["source"] == "sound.bed")["small"] == small
    for delta, small in ((150, True), (-150, True), (151, False), (-151, False)):
        write(target / "cut-selection.json", {"lines": [{"id": "keep", "pick": 1, "gap_after": {"mode": "override", "ms": 150 + delta}}]})
        assert next(c for c in learn.changes(target, STYLE) if c["source"] == "cut-board.pause")["small"] == small
        write(target / "config.json", {"cues": [{"id": "hit", "time": 2}]})
        write(target / "sound-selection.json", {"cues": [{"id": "hit", "time": 2 + delta / 1000}]})
        assert next(c for c in learn.changes(target, STYLE) if c["source"] == "sound.cue")["small"] == small
    write(target / "cut-selection.json", {"lines": [{"id": "keep", "pick": 1,
        "gap_after": {"mode": "override", "ms": None}, "sil": {"1": {"0": None}}}]})
    pauses = [c for c in learn.changes(target, STYLE) if c["source"] == "cut-board.pause"]
    assert len(pauses) == 2
    assert all(c["proposed_ms"] == 150 and c["sent_ms"] == 9000 and c["delta_ms"] == 8850
               and c["sent_as_spoken"] and not c["small"] for c in pauses)
    write(target / "cut-selection.json", {"lines": [{"id": "keep", "pick": 1, "gap_after": {"mode": "override"}}]})
    assert not any(c["source"] == "cut-board.pause" for c in learn.changes(target, STYLE))
    # Corrupt, absent and non-object boards are ignored rather than guessed.
    for file in target.glob("*.json"):
        file.write_bytes(b"{")
    assert learn.changes(target, STYLE) == []
    assert ss.path("style-1").read_bytes() == before


def case_stale_learn(root):
    workspace = setup(root)
    ready(workspace)
    planted = history()
    planted.pop("style_created", None)
    planted["auto"]["on"] = True
    planted["reels"] *= 2
    target = reel(workspace, "reused", small=False, boards={"grade-selection.json": {"look": STYLE["look"]}})
    for suffix, created in (("missing", None), ("different", "a previous style")):
        if created is not None:
            planted["style_created"] = created
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / suffix)}):
            ss.save(STYLE, "style-1")
            learning = ss.path("style-2").with_suffix(".learn.json")
            write(learning, planted)
            raw = learning.read_bytes()
            # A leftover sibling does not reserve the next automatic style id.
            assert ss._next_style(ss._index()) == ("style-2", "Style 2")
            with contextlib.redirect_stdout(io.StringIO()):
                assert ss.main(["save-from-reel", str(target)]) == 0
            ss.path("style-2@v1").with_suffix(".intake.json").write_bytes(b"{}\n")
            state = learn.status("style-2")
            assert not state["on"] and not state["ready"] and state["good_in_a_row"] == 0
            ss.set_default("style-2")
            assert ss.picker_lines(target)[0] == "Which style for this reel?"
            assert not any("Auto edit with" in line for line in ss.picker_lines(target))
            archive = ss.path("style-2@v2").with_suffix(".learn.json")
            assert archive.read_bytes() == raw
            assert not ss.path("style-2@v1").exists() and not ss.path("style-2@v2").exists()
            try:
                learn.set_auto("style-2", True)
            except ValueError:
                pass
            else:
                raise AssertionError("Stale learning unlocked Auto edit")
            ss.pick(target, "style-2")
            assert not offer(learn.record_approval(target))
            fresh = history("style-2")
            assert fresh["style_created"] == ss._index()["styles"]["style-2"]["created"]
            assert len(fresh["reels"]) == 1 and not fresh["auto"]["on"]
            assert archive.read_bytes() == raw
            archived = {p: p.read_bytes() for p in archive.parent.glob("style-2@v*.json")}
            learn.decline("style-2")
            current = ss.path("style-2").read_bytes()
            fresh_raw = learning.read_bytes()
            with contextlib.redirect_stdout(io.StringIO()):
                assert ss.main(["delete", "style-2"]) == 0
            assert ss.path("style-2@v3").read_bytes() == current
            assert ss.path("style-2@v3").with_suffix(".learn.json").read_bytes() == fresh_raw
            assert all(p.read_bytes() == content for p, content in archived.items())


def case_restore_auto(root):
    workspace = setup(root)
    legacy = ss._index()
    legacy.pop("archived_created", None)
    write(ss.path("default").with_name("_index.json"), legacy)
    ready(workspace)
    with contextlib.redirect_stdout(io.StringIO()):
        assert learn.main(["auto", "style-1", "on"]) == 0
    created = ss._index()["styles"]["style-1"]["created"]
    learning = ss.path("style-1").with_suffix(".learn.json")
    before = learning.read_bytes()
    with contextlib.redirect_stdout(io.StringIO()):
        assert ss.main(["delete", "style-1"]) == 0
        assert ss.main(["restore", "style-1@v1"]) == 0
    assert ss._index()["archived_created"]["style-1"] == created
    assert ss._index()["styles"]["style-1"]["created"] == created
    assert learn.status("style-1")["on"] is True
    assert learn.status("style-1")["good_in_a_row"] == 3
    assert learning.read_bytes() == before
    assert list(learning.parent.glob("style-1@v*.learn.json")) == [
        ss.path("style-1@v1").with_suffix(".learn.json")]


def case_pause_default(root):
    workspace = setup(root)
    lines = [{"id": str(i), "default": 1} for i in range(6)]
    target = reel(workspace, "default", small=False, boards={
        "cut-board.config.json": {"gap_default_ms": 150, "lines": lines},
        "cut-selection.json": {"gap_default_ms": 70, "lines": [
            {"id": row["id"], "gap_after": {"mode": "default"}} for row in lines]}})
    ss.pick(target, "style-1")
    learn.record_approval(target)
    record = history()["reels"][-1]
    assert not record["big"]
    assert record["changes"] == [dict(source="cut-board.pause_default", key="cut.pause_ms", small=True,
        detail="a pause was changed", proposed_ms=150, sent_ms=70, delta_ms=-80, delta=-80)]
    write(target / "cut-selection.json", {"gap_default_ms": 70, "lines": [
        {"id": "0", "gap_after": {"mode": "override", "ms": 90}}, {"id": "1"}]})
    edits = learn.changes(target, STYLE)
    assert len(edits) == 2 and edits[1]["source"] == "cut-board.pause"
    assert edits[1]["mode"] == "override" and edits[1]["sent_ms"] == 90
    write(target / "cut-selection.json", {"gap_default_ms": 150, "lines": [
        {"id": "0", "gap_after": {"mode": "default"}}]})
    assert learn.changes(target, STYLE) == []


def case_used_attempt(root):
    workspace = setup(root)
    target = reel(workspace, "attempts", small=False, boards={
        "cut-board.config.json": {"gap_default_ms": 150, "lines": [{"id": "line", "default": 1}]}})
    for pick, used in (({}, 1), ({"pick": 0}, 0)):
        write(target / "cut-selection.json", {"lines": [{"id": "line", **pick,
            "sil": {"0": {"0": 70}, "1": {"0": 90}}}]})
        edits = learn.changes(target, STYLE)
        pauses = [c for c in edits if c["source"] == "cut-board.pause"]
        assert len(pauses) == 1 and pauses[0]["attempt"] == used
        assert pauses[0]["sent_ms"] == (70 if used == 0 else 90)
        assert pauses[0]["mode"] == "override" and pauses[0]["silence"] == "0"
    for skip in ({"drop": True}, {"pick": None}):
        write(target / "cut-selection.json", {"lines": [{"id": "line", **skip, "sil": {"1": {"0": 70}}}]})
        assert not any(c["source"] == "cut-board.pause" for c in learn.changes(target, STYLE))


def case_write_order(root):
    workspace = setup(root)
    boards = {**music(-2), "grade-selection.json": {"look": {"id": "warm", "strength": .5}}}
    for i in range(2):
        approve(workspace, i, small=False, boards=boards)
    before = ss.path("style-1").read_bytes()
    learning = ss.path("style-1").with_suffix(".learn.json")
    learning.write_bytes(b" \n" + learning.read_bytes())
    learning_before = learning.read_bytes()
    target = reel(workspace, 2, small=False, boards=boards)
    ss.pick(target, "style-1")
    with patch.object(learn, "_write", side_effect=OSError("learning write failed")):
        try:
            learn.record_approval(target)
        except OSError:
            pass
        else:
            raise AssertionError("The learning write failure was ignored")
    assert ss.path("style-1").read_bytes() == before and len(history()["reels"]) == 2
    assert not list(ss.path("style-1").parent.glob("style-1@v*.json"))

    def failed_save(*args, **kwargs):
        # The correction must already be durable when saving its style is attempted.
        assert {r["key"]: r["to"] for r in history()["learned"]} == {
            "music.bed_gain_db": -20, "look.strength": .5}
        assert len(history()["reels"]) == 3
        assert args[0]["music"]["bed_gain_db"] == -20 and args[0]["look"]["strength"] == .5
        raise OSError("style write failed")

    with patch.object(ss, "save", side_effect=failed_save) as saving:
        try:
            learn.record_approval(target)
        except OSError:
            pass
        else:
            raise AssertionError("The style write failure was ignored")
    assert saving.call_count == 1
    assert ss.path("style-1").read_bytes() == before
    assert not history()["learned"] and len(history()["reels"]) == 2
    assert learning.read_bytes() == learning_before
    lines = learn.record_approval(target)
    assert len(history()["reels"]) == 3 and len(history()["learned"]) == 2
    assert ss.load(name="style-1")["music"]["bed_gain_db"] == -20
    assert ss.load(name="style-1")["look"]["strength"] == .5
    assert list(ss.path("style-1").parent.glob("style-1@v*.json")) == [ss.path("style-1@v1")]
    assert any("turn the music down about 2 dB" in line for line in lines)
    assert offer(lines)
    assert learn.record_approval(target) == []


def case_current_threshold(root):
    workspace = setup(root, auto_edit={"unlock_after": 4})
    for i in range(3):
        assert not offer(approve(workspace, i)[1])
    output = io.StringIO()
    with contextlib.redirect_stderr(output):
        assert learn.main(["auto", "Style 1", "on"]) == 2
    assert "4 smooth reels" in output.getvalue() and not learn.status("Style 1")["on"]
    with contextlib.redirect_stdout(io.StringIO()):
        assert learn.main(["auto", "Style 1", "on", "--workspace", str(root / "absent")]) == 0
    assert history()["auto"]["offered_reel"] is None
    learn.set_auto("Style 1", False)
    approve(workspace, 3)
    with contextlib.redirect_stdout(io.StringIO()):
        assert learn.main(["auto", "Style 1", "on"]) == 0
    assert learn.status("Style 1")["on"]
    index = ss._index()
    index["active_reel"] = None
    ss._write_index(index)
    assert learn.set_auto("Style 1", True)


CASES = {"unlock": case_unlock, "reset": case_reset, "six-small": case_six_small,
         "nudge-learn": case_nudge_learn, "earlier-ignored": case_earlier_ignored,
         "nudge-swallowed": case_nudge_swallowed, "nudge-partial": case_nudge_partial,
         "nudge-room-next-reel": case_nudge_room_next_reel, "nudge-room-shrinks": case_nudge_room_shrinks,
         "frame-edges": case_frame_edges, "pause-tweak": case_pause_tweak,
         "timing-limits": case_timing_limits,
         "self-correct": case_self_correct, "timing-recorded": case_timing_recorded,
         "decline": case_decline, "auto-pick": case_auto_pick, "auto-no-stop": case_auto_no_stop,
         "paid-still-asks": case_paid_still_asks, "qa-still-stops": case_qa_still_stops,
         "relock": case_relock, "hub": case_hub, "sources": case_sources,
         "stale-learn": case_stale_learn, "restore-auto": case_restore_auto,
         "pause-default": case_pause_default,
         "used-attempt": case_used_attempt, "write-order": case_write_order,
         "current-threshold": case_current_threshold}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    args = ap.parse_args()
    scratch = Path(args.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    source = ss.runtime.state_dir()
    failures = 0
    with tempfile.TemporaryDirectory(prefix="auto-edit-", dir=scratch) as tmp:
        for name in [args.case] if args.case else CASES:
            root = Path(tmp) / name
            home = copy_tool_state(source, root / "state")
            with patch.dict(os.environ, {"EDITOR_SE_HOME": str(home)}):
                try:
                    CASES[name](root)
                    print(f"PASS {name}")
                except Exception as error:
                    failures += 1
                    print(f"FAIL {name}: {type(error).__name__}: {error}")
    print(f"{failures} failed" if failures else "all passed")
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
