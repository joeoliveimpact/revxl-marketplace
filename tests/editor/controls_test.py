"""Lane browser proof: every hub board in Simple/Advanced and live iframe flips with real Sends.
Run: python -X utf8 -I tests/editor/controls_test.py
Reuses hub_test's owned fixture/server/tool state and mandatory heavy_lock; no real recordings.
"""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from hub_test import Proof, Blocked, HEAVY, need, read, write
import canvas_boards_test as canvas


def prepare(p):
    d = p.videos / "reel-01"
    canvas.reel_fixture(d)
    # Caption and cover preparation sample only this two-second synthetic clip.
    words = read(d / "work/edit_map.cut.json")["words"][:6]
    for i, word in enumerate(words):
        word.update(start=i * 0.25, end=i * 0.25 + 0.22, parakeet_start=i * 0.25)
    write(d / "work/edit_map.cut.json", {"words": words})
    write(d / "work/cuts.json", {"fps": 12, "speed": 1, "segments": [
        {"src_in_f": 0, "src_out_f": 24, "out_in_f": 0, "out_out_f": 24}]})
    write(d / "work/plan.json", {"beats": [{"w0": 0, "w1": 2, "layout": "full", "value": 3},
        {"w0": 3, "w1": 5, "layout": "split"}], "word_marks": [], "needs": ""})
    p.py(p.plugin / "skills/reel-canvas-build/scripts/make_beat_map.py", "--reel-dir", d, "--plan", d / "work/plan.json")
    beat = read(d / "beat-map.state.json")
    beat["edit_style"] = {"style": "punch-in", "punch_scale": 1.12, "moves": {}}
    write(d / "beat-map.state.json", beat)
    write(d / "beat-map-selection.json", dict(beat, sent_at="2026-11-05T12:00:00-05:00"))
    sketches = read(d / "sketches.state.json")
    sketches["scenes"] = {"b_001": {"id": "counter", "slots": {"label": "Three"}, "params": {"value": 3}}}
    write(d / "sketches.state.json", sketches)
    master = d / "work/renders/master-100x.mp4"
    master.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p.clip, master)
    p.py(p.plugin / "skills/reel-captions/scripts/captions.py", "picker", "--reel-dir", d)
    p.py(p.plugin / "skills/reel-cover/scripts/cover_pick.py", "candidates", "--reel-dir", d)
    p.py(p.plugin / "skills/reel-grade/scripts/make_grade.py", "--reel", d.name, "--video", d / "raw/take.mp4", "--reel-dir", d)
    attempt = {"take": 1, "attempt": 1, "src_in": 0, "src_out": 1, "snapped": [True],
        "sub_retakes": [], "silences": [{"after": 0, "a": 0.2, "b": 0.5}],
        "words": [{"i": 0, "w": "Three", "s": 0, "e": 0.2, "cin": 0, "snapped": True}]}
    write(d / "cut-board.config.json", {"reel": d.name, "rule": "fixture", "board_hash": "fixture",
        "gap_default_ms": 300, "beat_ms": 300, "gap_presets": [["short", 150], ["normal", 300]],
        "speed_default": 1, "speed_options": [1], "shots": {"vocab": ["talking head"]},
        "takes": {str(n): {"n": n, "wav": "raw/take.mp4", "word_list_hash": str(n)} for n in (1, 2)},
        "lines": [{"id": "L01", "label": "Opening", "text": "Three", "default": 0,
                   "attempts": [attempt, dict(attempt, take=2)]}]})
    write(d / "tweak-board.config.json", {"reel": d.name, "version": "fixture", "duration": 2, "fps": 12,
        "video": "raw/take.mp4", "words": [{"t": 0, "w": "Three"}], "bins_per_s": 10,
        "peaks": [0.1] * 20, "presets": [["short", 150]], "speed_options": [1],
        "ship_speed": 1, "map": [[0, 2, 0, 2]]})  # make_tweaks.py shape: one segment, duration = map[-1][1]
    write(d / "tweak-board.state.json", {"reel": d.name, "version": "fixture",
        "marks": [{"id": 1, "type": "note", "a": 0.5, "text": "Keep it"},
                  {"id": 2, "type": "tight", "a": 0.7, "ms": 150},
                  {"id": 3, "type": "cut", "a": 1, "b": 1.5}]})
    write(d / "config.json", {"dur": 2, "fps": 12, "picture_url": "raw/take.mp4", "library": [], "beds": [],
        "cues": [{"id": "c1", "beat": "Opening", "time": 0.5, "candidates": []}]})
    write(d / "waveforms.json", {"bins_per_s": 10, "voice": {"peaks": [0.1] * 20}, "beds": {}})
    for name in ("base", "t1"):
        dest = d / "trials" / name / "trial.mp4"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p.clip, dest)
    write(d / "trials/trials-report.json", {"base": {"id": "base", "file": "trials/base/trial.mp4"},
        "versions": [{"id": "t1", "change": "hook", "file": "trials/t1/trial.mp4"}]})
    p.refresh()


def main():
    p = None
    with tempfile.TemporaryDirectory(prefix="editor-controls-") as tmp:
        try:
            p = Proof(Path(tmp))
            with patch.dict(os.environ, p.env):
                prepare(p)
                for mode in ("simple", "advanced"):
                    p.py(p.doctor / "check_deps.py", "--set-controls", mode)
                    p.refresh()
                    p.start()
                    job = p.scratch / f"controls-{mode}.json"
                    write(job, {"base": p.base, "mode": mode, "userDataDir": str(p.scratch / f"profile-{mode}")})
                    result = p.run([sys.executable, "-X", "utf8", "-I", HEAVY, "--wait", "20", "--min-gb", "3", "--",
                        p.tools["node"], HERE / "controls_click.js", p.pup, p.tools["chrome"], job], timeout=150, check=False)
                    if result.returncode in (75, 76) or ("PermissionError" in result.stderr and "heavy.lock" in result.stderr):
                        raise Blocked(f"heavy_lock denied: {result.returncode}: {result.stderr[-500:]}")
                    need(result.returncode == 0, result.stdout + result.stderr)
                    need(len(json.loads(result.stdout.strip().splitlines()[-1])["checked"]) == 9, "missing board")
                    print(f"PASS {mode}: all nine hub tabs, everyday controls, disclosure defaults" +
                          (", live iframe flips and one persisted request per flip" if mode == "simple" else ""))
            return 0
        except Blocked as error:
            print(f"BLOCKED controls: {error}")
            return 77
        finally:
            if p:
                p.close()


if __name__ == "__main__":
    sys.exit(main())
