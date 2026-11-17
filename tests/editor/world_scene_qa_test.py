"""Reel scene resolution and strict drawn-face pre-checks; no media."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[2] / "plugins/editor-superengine"
sys.path.insert(0, str(P / "skills/_shared/checks"))
sys.path.insert(0, str(P / "skills/reel-canvas-build/scripts"))
import check
import placer


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data) + "\n").encode("utf-8"))


class WorldSceneQA(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.reel = Path(self.tmp.name)
        fixture = Path(__file__).parent / "fixtures/reel-motion/motion/reel-good-world"
        self.scene = self.reel / "motion/reel-good-world"
        shutil.copytree(fixture, self.scene)
        self.spec = json.loads((self.scene / "scene.json").read_text(encoding="utf-8"))
        self.spec.update(area="stack", caption_band=[12, 166])
        write(self.scene / "scene.json", self.spec)
        self.beats = [dict(id="b_001", start_f=0, end_f=60, layout="stack",
                           scene=dict(id="reel-good-world", slots={"text": "Clear world"}, params={})),
                      dict(id="b_002", start_f=60, end_f=180, layout="full", scene=None)]
        self.save_beats()
        write(self.reel / "work/cuts.json", dict(fps=30, segments=[
            dict(src_in_f=0, src_out_f=180, out_in_f=0, out_out_f=180)]))
        self.track = dict(fps=30, total_f=180, style=dict(style="punch-in"), keys=[
            dict(f=0, scale=1, ox=.5, oy=.5, layout="full")], tweens=[])
        write(self.reel / "work/scale_track.json", self.track)
        # Including placer's 24px pad: full-frame protected head = (200, 700, 880, 1100).
        write(self.reel / "work/anchors.json", dict(segments=[dict(seg=0, samples=[
            dict(f=0, x=.5, y=.45, box=[224/1080, 724/1920, 856/1080, 1076/1920])])]))

    def save_beats(self):
        write(self.reel / "beat-map-selection.json", dict(fps=30, beats=self.beats))

    def caption(self, box, start=4, end=22):
        write(self.reel / "work/captions.json", dict(style=dict(style="clean"), hooks=[], chunks=[
            dict(start_f=start, end_f=end, text="Claude", words=[dict(text="Claude")], box=box)]))

    def rows(self, only=("layout_check",)):
        rows = check.run_checks(check.build_context(self.reel), "pre", only=set(only))
        self.assertFalse([r for r in rows if r["check"].endswith("-crashed")], rows)
        self.assertFalse([r for r in rows if r["level"] == "warn"], rows)
        return rows

    def test_scene_fill_resolves_reel_and_still_checks_overflow(self):
        self.assertEqual(self.rows(("scene_fill_check",)), [])
        self.beats[0]["scene"]["slots"]["text"] = "x" * 13
        self.save_beats()
        self.assertEqual([r["check"] for r in self.rows(("scene_fill_check",))], ["slot-overflow"])

    def test_stack_band_clear_but_drawn_face_still_blocks(self):
        self.caption([160, 874, 920, 1014])
        self.assertEqual(self.rows(), [])
        ctx = placer.load_ctx(self.reel)
        self.assertEqual(placer.head_box_at(ctx, 4, 21), (200, 162, 880, 562))
        self.caption([160, 300, 920, 440])
        self.assertEqual([r["check"] for r in self.rows()], ["word-covered"])

    def test_world_slot_drops_zoom_and_protects_whole_head(self):
        self.track["keys"][0].update(layout="stack", scale=1.2)
        write(self.reel / "work/scale_track.json", self.track)
        # Cover-fit subtracts 538; punch scale is dropped during this world.
        self.caption([160, 874, 920, 1014])
        self.assertEqual(self.rows(), [])
        self.assertEqual(placer.head_box_at(placer.load_ctx(self.reel), 4, 21),
                         (200, 162, 880, 562))
        self.caption([160, 300, 920, 440])
        self.assertEqual([r["check"] for r in self.rows()], ["word-covered"])

    def test_full_world_does_not_exempt_drawn_head_and_pip_still_blocks(self):
        self.spec.update(area="full", caption_band=[1320, 1470])
        write(self.scene / "scene.json", self.spec)
        self.beats[0].update(layout="full", cover_face=True)
        self.save_beats()
        self.caption([160, 720, 920, 820])
        self.assertEqual([r["check"] for r in self.rows()], ["word-covered"])
        self.track["keys"][0]["layout"] = "pip"
        self.beats[0].update(layout="pip", cover_face=False)
        self.save_beats()
        write(self.reel / "work/scale_track.json", self.track)
        self.caption([738, 28, 1050, 583])
        self.assertTrue(any(r["check"] in ("word-covered", "caption-on-face") for r in self.rows()))

    def test_crossing_world_end_keeps_uncovered_face(self):
        self.caption([160, 874, 920, 1014], start=55, end=65)
        self.assertEqual([r["check"] for r in self.rows()], ["word-covered"])
        self.caption([160, 874, 920, 1014], start=60, end=65)
        self.assertEqual([r["check"] for r in self.rows()], ["word-covered"])

    def test_split_world_moves_whole_head_into_lower_slot(self):
        self.spec.update(area="split", caption_band=[220, 360])
        write(self.scene / "scene.json", self.spec)
        self.beats[0]["layout"] = "split"
        self.save_beats()
        self.caption([160, 720, 920, 820])
        self.assertEqual(self.rows(), [])
        self.assertEqual(placer.head_box_at(placer.load_ctx(self.reel), 4, 21),
                         (200, 1180, 880, 1580))
        self.caption([160, 1250, 920, 1390])
        self.assertEqual([r["check"] for r in self.rows()], ["word-covered"])

    def test_unfixed_full_track_never_exempts_hidden_lower_head(self):
        # Model the old compositor: strict QA must still reject y874-992.
        from unittest.mock import patch
        self.caption([160, 874, 920, 992])
        ctx = placer.load_ctx(self.reel)
        ctx["world_slots"] = []
        with patch.object(placer, "load_ctx", return_value=ctx):
            self.assertEqual([r["check"] for r in self.rows()], ["word-covered"])
        self.assertEqual(placer.visible_head_box_at(ctx, 4, 21), (200, 700, 880, 1100))

    def test_full_world_end_keeps_short_visible_tail_protected(self):
        self.spec.update(area="full", caption_band=[1320, 1470])
        write(self.scene / "scene.json", self.spec)
        self.beats[0].update(layout="full", cover_face=True)
        self.save_beats()
        self.caption([160, 720, 920, 820], start=4, end=61)
        self.assertEqual([r["check"] for r in self.rows()], ["word-covered"])

    def test_missing_world_inputs_do_not_exempt_face(self):
        (self.scene / "scene.json").unlink()
        self.caption([160, 874, 920, 1014])
        self.assertEqual([r["check"] for r in self.rows()], ["word-covered"])


if __name__ == "__main__":
    unittest.main()
