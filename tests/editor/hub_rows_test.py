"""M9 stdlib proof: real temporary workspaces, configured paths and Cockpit snapshots."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[2] / "plugins/editor-superengine"
SCRIPTS = PLUGIN / "skills/editor-doctor/scripts"
sys.path.insert(0, str(SCRIPTS))
import hub_rows as hub


class HubRowsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "editor").mkdir()
        (self.root / "editor/editor.config.json").write_text(
            json.dumps({"paths": {"videos": "media/reels", "editor": "boards"}}), encoding="utf-8")
        self.reel = self.root / "media/reels/New reel"
        self.reel.mkdir(parents=True)

    def row(self):
        # These unrelated user libraries are deliberately not consulted by this temp-only proof.
        with patch.object(hub, "goldmine", return_value=None), patch.object(hub, "style_rows", return_value=[]):
            return hub.build(self.root)["reels"][0]

    def test_record_layouts(self):
        for names, expected in [([], "Record"), (["RAW.mp4"], "Cut"),
                                (["raw/x.mp4"], "Cut"), (["raw/x.mp4", "raw/y.MOV"], "Cut"),
                                (["raw/x.mp4.tmp", "raw/y.txt"], "Record")]:
            with self.subTest(names=names):
                made = []
                for name in names:
                    p = self.reel / name
                    p.parent.mkdir(exist_ok=True)
                    p.write_bytes(b"")
                    made.append(p)
                self.assertEqual(self.row()["stage"], expected)
                for p in made:
                    p.unlink()

    def test_snapshot_open_send_then_ack(self):
        send = self.reel / "beat-map-selection.json"
        send.write_text('{"beats": []}', encoding="utf-8")
        os.utime(send, (100, 100))
        snapshot = self.root / "boards/hub/cockpit-state.json"
        snapshot.parent.mkdir(parents=True)
        def save(acked):
            snapshot.write_text(json.dumps({"baseline": 1, "acked": acked}), encoding="utf-8")
        save({})
        row = self.row()
        self.assertEqual(row["waiting_on"], "claude")
        self.assertEqual([(s["board"], s["mtimeMs"]) for s in row["open_sends"]], [("beatmap", 100000)])
        self.assertEqual(self.row()["open_sends"], row["open_sends"], "refresh never acknowledges a Send")
        save({"New reel/beat-map-selection.json": 100000})
        self.assertEqual(self.row()["open_sends"], [])
        self.assertEqual(self.row()["waiting_on"], "you")

    def test_brand_new_reel_intake_both_layouts(self):
        spec = importlib.util.spec_from_file_location(
            "prepare_reel", PLUGIN / "skills/reel-first-cuts/scripts/prepare_reel.py")
        intake = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(intake)
        for take in ("RAW.mp4", "raw/x.mp4"):
            with self.subTest(take=take):
                result = intake.prepare(self.root, "Fresh reel")
                folder = self.root / "media/reels/Fresh reel"
                self.assertEqual(result["mode"], "record")
                self.assertTrue((folder / "raw").is_dir())
                p = folder / take
                p.write_bytes(b"")
                with patch.object(hub, "goldmine", return_value=None), patch.object(hub, "style_rows", return_value=[]):
                    rows = hub.build(self.root)["reels"]
                self.assertEqual(next(r for r in rows if r["id"] == "Fresh reel")["stage"], "Cut")
                result = intake.prepare(self.root, "Fresh reel")
                self.assertEqual(result["mode"], "single")
                self.assertTrue((folder / "RAW.mp4").is_file())
                with patch.object(hub, "goldmine", return_value=None), patch.object(hub, "style_rows", return_value=[]):
                    rows = hub.build(self.root)["reels"]
                self.assertEqual(next(r for r in rows if r["id"] == "Fresh reel")["stage"], "Cut")
                self.assertTrue(p.is_file(), "intake preserves the original")
                for f in folder.rglob("*"):
                    if f.is_file():
                        f.unlink()
                (folder / "raw").rmdir()
                folder.rmdir()

    def test_several_recordings_stay_separate(self):
        spec = importlib.util.spec_from_file_location(
            "prepare_reel", PLUGIN / "skills/reel-first-cuts/scripts/prepare_reel.py")
        intake = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(intake)
        (self.reel / "raw").mkdir()
        for name in ("x.mp4", "y.mov"):
            (self.reel / "raw" / name).write_bytes(b"original")
        result = intake.prepare(self.root, self.reel.name)
        self.assertEqual(result["mode"], "several")
        self.assertEqual(len(result["sources"]), 2)
        self.assertFalse((self.reel / "RAW.mp4").exists())
        (self.reel / "RAW.mp4").write_bytes(b"older take")
        self.assertEqual(intake.prepare(self.root, self.reel.name)["mode"], "several")
        self.assertEqual((self.reel / "RAW.mp4").read_bytes(), b"older take")

    def test_single_take_copy_preserves_source_bytes_and_existing_raw(self):
        spec = importlib.util.spec_from_file_location(
            "prepare_reel", PLUGIN / "skills/reel-first-cuts/scripts/prepare_reel.py")
        intake = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(intake)
        (self.reel / "raw").mkdir()
        source = self.reel / "raw/x.mov"
        source.write_bytes(b"original recording")
        intake.prepare(self.root, self.reel.name)
        self.assertEqual(source.read_bytes(), b"original recording")
        self.assertEqual((self.reel / "RAW.mp4").read_bytes(), b"original recording")
        (self.reel / "RAW.mp4").write_bytes(b"existing raw")
        intake.prepare(self.root, self.reel.name)
        self.assertEqual((self.reel / "RAW.mp4").read_bytes(), b"existing raw")


if __name__ == "__main__":
    unittest.main()
