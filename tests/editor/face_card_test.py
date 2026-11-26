"""Face card + head pop (0.2.4): the pre-render check and the caption placer's geometry; no renderer.

    python -X utf8 -I tests/editor/face_card_test.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[2] / "plugins/editor-superengine"
sys.path.insert(0, str(P / "skills/_shared/checks"))
sys.path.insert(0, str(P / "skills/reel-canvas-build/scripts"))
import face_card_check  # noqa: E402
import compose  # noqa: E402
import gate_check  # noqa: E402


def beat(i, s, e, layout):
    return {"id": i, "start_f": s, "end_f": e, "layout": layout}


class FaceCardCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.reel = Path(self.tmp.name)
        (self.reel / "work/renders").mkdir(parents=True)
        (self.reel / "work/renders/master-100x.mp4").write_bytes(b"cut")
        self.cuts = {"fps": 30, "speed": 1.0, "segments": [{"out_in_f": 0, "out_out_f": 90}]}
        self.beats = [beat("b1", 0, 30, "full"), beat("b2", 30, 90, "facecard")]

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self, beats=None):
        return face_card_check.run({"reel_dir": self.reel, "beats": self.beats if beats is None else beats,
                                    "cuts": self.cuts, "fps": None, "render": None})

    def track(self, layout):
        (self.reel / "work/scale_track.json").write_text(json.dumps(
            {"keys": [{"f": 0, "layout": "full"}, {"f": 30, "layout": layout}], "tweens": []}), encoding="utf-8")

    def test_no_face_card_no_rows(self):
        self.assertEqual(self.run_check([beat("b1", 0, 90, "split")]), [])

    def test_missing_cutout_blocks(self):
        rows = self.run_check()
        self.assertEqual([(r["check"], r["level"], r["where"]) for r in rows],
                         [("face-card-cutout", "block", "beat 2")])
        self.assertIn("cutout step", rows[0]["msg"])

    def test_cutout_older_than_cut_blocks(self):
        (self.reel / "work/matte").mkdir()
        (self.reel / compose.HEAD_MATTE).write_bytes(b"old")
        os.utime(self.reel / compose.HEAD_MATTE, (1, 1))
        self.assertIn("older cut", self.run_check()[0]["msg"])

    def test_punch_in_track_warns_hidden_and_skips_the_cutout(self):
        self.track("full")  # punch-in plans every key full
        rows = self.run_check()
        self.assertEqual([(r["check"], r["level"]) for r in rows], [("face-card-hidden", "warn")])
        self.assertIn("Layout switches", rows[0]["msg"])


class FaceCardGeometry(unittest.TestCase):
    def test_placer_maps_the_head_through_the_full_size_picture(self):
        lay = compose.layout("facecard", 1)
        self.assertEqual(lay["video"], [70, 557, 1080, 1920])
        import placer
        # A head at master (380, 300)-(700, 700) sits on screen offset by (70, 557), unshrunk, above the card top.
        box = placer._map((380, 300, 700, 700), tuple(lay["video"]), 1.0, (0.5, 0.38))
        self.assertEqual(tuple(round(v, 6) for v in box), (450, 857, 770, 1257))
        self.assertLess(box[1], lay["box"][1])

    def test_foreground_sets_agree(self):
        self.assertEqual(gate_check.FOREGROUND, compose.FOREGROUND)
        self.assertIn("facecard", compose.BAKED)


if __name__ == "__main__":
    unittest.main()
