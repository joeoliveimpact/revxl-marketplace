"""MB7-F7: drawn world slots, hard boundaries and pre-render crossing refusal."""
import contextlib
import copy
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import world_scene_qa_test as fixture
import compose
import placer


class WorldSceneLayout(unittest.TestCase):
    setUp = fixture.WorldSceneQA.setUp
    save_beats = fixture.WorldSceneQA.save_beats

    def prepare(self, area="stack"):
        self.spec.update(area=area, caption_band=[300, 500])
        fixture.write(self.scene / "scene.json", self.spec)
        page = (self.scene / "scene.html").read_text(encoding="utf-8")
        (self.scene / "scene.html").write_bytes(page.replace("1920", str(
            {"stack": 1076, "split": 960}[area])).encode("utf-8"))
        self.beats[0].update(start_f=17, end_f=61, layout=area)
        self.beats[1].update(start_f=61)
        self.beats.insert(0, dict(id="before", start_f=0, end_f=17, layout="full", scene=None,
                                 speech_anchor=dict(text="", w0=0, w1=0)))
        self.save_beats()
        self.track["keys"].append(dict(f=40, scale=1.2, ox=.3, oy=.4, layout="full"))
        self.track["tweens"] = [dict(prop="scale", start_f=8, end_f=90,
            **{"from": 1, "to": 1.3}, ease="power2.inOut", id="crossing punch")]
        fixture.write(self.reel / "work/scale_track.json", self.track)

    def inputs(self):
        return dict(beats=copy.deepcopy(self.beats), reel_dir=self.reel, track=self.track,
            rate=30, fps="30/1", total=180, words=["Clear", "world"], cut_frames=[],
            under=[], hook_f=0, hooks=[], captions=None)

    def assert_slot(self, area, want):
        self.prepare(area)
        before = (self.reel / "work/scale_track.json").read_bytes()
        ctx = placer.load_ctx(self.reel)
        baseline = dict(ctx, world_slots=[])
        for frame in range(17, 61):
            self.assertEqual(placer.head_box_at(ctx, frame, frame), want)
        for frame in (16, 61):
            self.assertEqual(placer.head_box_at(ctx, frame, frame),
                             placer.head_box_at(baseline, frame, frame))
        self.assertEqual(placer.head_box_at(ctx, 16, 61)[3], max(want[3],
            placer.head_box_at(ctx, 16, 16)[3], placer.head_box_at(ctx, 61, 61)[3]))
        for w, h, geometry in ((1080, 1920, {
                "stack": "translate(0px, 0px) !important; width: 1080px !important; height: 844px",
                "split": "translate(0px, 960px) !important; width: 1080px !important; height: 960px"}),
                (720, 1280, {
                "stack": "translate(0px, 0px) !important; width: 720px !important; height: 562.67px",
                "split": "translate(0px, 640px) !important; width: 720px !important; height: 640px"})):
            for layers in ("all", "aroll"):
                page = compose.main_html(self.inputs(), w, h, [(self.beats[1], "world")], layers=layers)
                self.assertIn('"data-world-face": "' + area + '"', page)
                self.assertIn('"data-world-face": ""', page)
                self.assertIn(geometry[area], page)
                self.assertIn('#aroll-move { transform: none !important; }', page)
        self.assertEqual((self.reel / "work/scale_track.json").read_bytes(), before)

    def test_every_stack_frame_and_exact_boundaries(self):
        self.assert_slot("stack", (200, 162, 880, 562))

    def test_every_split_frame_and_exact_boundaries(self):
        self.assert_slot("split", (200, 1180, 880, 1580))

    def test_layout_switch_tween_cannot_move_face_out_of_world_slot(self):
        self.prepare()
        self.track["style"]["style"] = "layout-switch"
        self.track["tweens"].append(dict(prop="layout", start_f=8, end_f=90,
            **{"from": "full", "to": "split"}, ease="power2.inOut", id="layout move"))
        fixture.write(self.reel / "work/scale_track.json", self.track)
        ctx = placer.load_ctx(self.reel)
        for frame in range(17, 61):
            self.assertEqual(placer.head_box_at(ctx, frame, frame), (200, 162, 880, 562))
        page = compose.main_html(self.inputs(), 1080, 1920, [(self.beats[1], "world")])
        self.assertIn('"data-world-face": "stack"', page)

    def test_crossing_drawn_head_refused_by_area_check_and_plan(self):
        self.prepare()
        ctx = placer.load_ctx(self.reel)
        ctx["world_slots"] = []  # Forced old full-layout draw, not a coverage exemption.
        problem = compose.world_area_problem(self.beats[1], self.spec, self.reel, ctx=ctx)
        self.assertIsNotNone(problem)
        self.assertIn("b_001", problem)
        self.assertIn("head", problem.lower())
        with self.assertRaises(compose.Stop), contextlib.redirect_stdout(io.StringIO()):
            compose.plan(self.inputs(), None, ctx=ctx)

    def test_overlapping_area_refused_even_with_slot_override(self):
        self.prepare()
        ctx = placer.load_ctx(self.reel)
        with patch.object(compose, "world_area", return_value=(0, 400, 1080, 1520)):
            self.assertIsNotNone(compose.world_area_problem(self.beats[1], self.spec, self.reel, ctx=ctx))
            with self.assertRaises(compose.Stop), contextlib.redirect_stdout(io.StringIO()):
                compose.plan(self.inputs(), None)

    def test_crossing_refusal_precedes_render_and_shared_lock(self):
        self.prepare()
        track = dict(self.track, warnings=[], spans=[])
        ctx = dict(placer.load_ctx(self.reel), world_slots=[])
        with (patch.object(compose, "load_inputs", return_value=self.inputs()),
              patch.object(compose, "probe_inputs"),
              patch.object(compose.styles, "plan", return_value=track),
              patch.object(placer, "load_ctx", return_value=ctx),
              patch.object(compose, "heavy_job", side_effect=AssertionError("Reached shared lock")),
              self.assertRaises(compose.Stop) as error):
            compose.render(self.reel, "preview", None)
        self.assertIn("b_001", str(error.exception))
        self.assertIn("head", str(error.exception))

    def test_no_world_beat_html_segments_are_byte_equal(self):
        self.prepare()
        inp = self.inputs()
        baseline = copy.deepcopy(inp)
        baseline["beats"][1]["scene"] = None
        old = compose.main_html(baseline, 1080, 1920, [])
        new = compose.main_html(inp, 1080, 1920, [(inp["beats"][1], "world")])
        # The original style timeline keeps running unchanged, including a move
        # crossing both world boundaries. Slot attributes alone mask it inside.
        def style_segments(page):
            return "\n".join(line for line in page.splitlines()
                if 'tl.' in line and ('"#aroll-move"' in line or '"#aroll-box"' in line)
                and "data-world-face" not in line).encode("utf-8")
        self.assertEqual(style_segments(new), style_segments(old))
        slot_lines = [line for line in new.splitlines() if "tl.set" in line and "data-world-face" in line]
        self.assertEqual(len(slot_lines), 2)
        self.assertTrue(slot_lines[0].endswith(", " + compose.at(17, 30) + ");"), slot_lines)
        self.assertTrue(slot_lines[1].endswith(", " + compose.at(61, 30) + ");"), slot_lines)


if __name__ == "__main__":
    unittest.main(verbosity=2)
