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


class GoldmineShapesTest(unittest.TestCase):
    """H-S17-2: titles come from manifest hook lines; odd export shapes never crash the hub refresh."""
    def gold(self, manifest, ranking):
        with tempfile.TemporaryDirectory() as t:
            rb = Path(t) / "reel-build"; rb.mkdir()
            for name, value in (("goldmine-run.json", {"manifest": "manifest.json",
                                                       "compute": {"popularity": "popularity.json"}}),
                                ("manifest.json", manifest),
                                ("popularity.json", {"corpus": {"reels_total": 3}, "breakout_ranking": ranking})):
                (rb / name).write_text(json.dumps(value), encoding="utf-8")
            with patch.object(hub.Path, "home", return_value=Path(t)):
                return hub.goldmine(Path(t))

    def test_titles(self):
        g = self.gold({"count": 2, "breakouts": [{"id": "A1", "hook_line": "Stop posting daily", "hook": "statement"},
                                                 {"id": "B2", "hook_line": "", "hook": "none"}]},
                      [{"shortcode": "A1"}, {"shortcode": "B2"}, {"shortcode": "C3", "title": "kept"}, "odd"])
        self.assertEqual([r["title"] if isinstance(r, dict) else r for r in g["ranking"]],
                         ["Stop posting daily", None, "kept", "odd"])

    def test_odd_shapes_do_not_crash(self):
        for manifest, ranking in (({"count": 1, "breakouts": None}, [{"shortcode": "A1"}]),
                                  ({"count": 1, "breakouts": [{"id": ["x"], "hook_line": "h"}]}, [{"shortcode": ["x"]}]),
                                  ({"count": 1, "breakouts": {"A1": {}}}, None)):
            g = self.gold(manifest, ranking)
            self.assertIsInstance(g["ranking"], list)
            self.assertTrue(all(r.get("title") is None for r in g["ranking"]))


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

    def test_plain_health_only_flags_chosen_handoff(self):
        # Copied from the S17W2 walk's status list; this proof never reads that workspace.
        status = [
            {"component": "machine", "level": "ok",
             "detail": "Windows 11 (10.0.26300) AMD64, no NVIDIA GPU, 31.7 GB RAM (4.9 GB free) [test masks: gpu,resolve]",
             "fix": None},
            {"component": "python", "level": "ok", "detail": "the editor's own Python 3.12.16 in its venv", "fix": None},
            {"component": "ffmpeg", "level": "ok", "detail": "ffmpeg 8.1.2 with zscale", "fix": None},
            {"component": "node", "level": "ok", "detail": "Node.js v22.23.4", "fix": None},
            {"component": "hyperframes", "level": "ok", "detail": "HyperFrames 0.8.184", "fix": None},
            {"component": "chrome", "level": "ok", "detail": "Chrome for rendering 152.0.7977.30", "fix": None},
            {"component": "cutout-model", "level": "ok", "detail": "u2net_human_seg: 1 file(s) match their sha256", "fix": None},
            {"component": "rvm", "level": "ok", "detail": "RVM cutout ready (torch + torchvision)", "fix": None},
            {"component": "transcriber", "level": "ok", "detail": "parakeet-cpu packages are installed and load", "fix": None},
            {"component": "model-parakeet", "level": "ok", "detail": "4 file(s) match their sha256", "fix": None},
            {"component": "align", "level": "ok", "detail": "align_words with wav2vec2: 7 file(s) match their sha256", "fix": None},
            {"component": "engine", "level": "ok", "detail": "parakeet-cpu (Windows without an NVIDIA GPU)", "fix": None},
            {"component": "resolve-installed", "level": "warn",
             "detail": "DaVinci Resolve isn't installed, so the Resolve hand-off stays off (optional)",
             "fix": "Nothing is needed for editing. For the Resolve hand-off, install DaVinci Resolve Studio 21.1 or newer from blackmagicdesign.com, then Claude re-runs the doctor."},
            {"component": "nle", "level": "ok", "detail": "none (the Resolve hand-off stays off)", "fix": None},
            {"component": "config", "level": "ok", "detail": "editor/editor.config.json is up to date", "fix": None},
        ]
        health = hub.plain_health(status, "none")
        self.assertEqual(len(health), 15)
        self.assertFalse(any(h["matters"] and h["level"] != "ok" for h in health))
        self.assertEqual([h["label"] for h in health],
                         ["This computer", "The editor's Python", "Video tools", "Motion renderer runtime",
                          "Motion renderer", "Render browser", "Cutout model", "Cutout for moving shots",
                          "Transcriber", "Transcription model", "Word timing", "Transcription engine",
                          "DaVinci Resolve", "Editor hand-off", "Editor settings"])
        self.assertEqual([health[i]["detail"] for i in (6, 9, 10)], ["Downloaded and checked."] * 3)
        self.assertEqual(health[0]["detail"], "Windows 11, no NVIDIA GPU, 31.7 GB RAM (4.9 GB free)")
        self.assertEqual([health[i]["detail"] for i in (1, 2, 3, 4, 5, 7, 11)], ["Ready."] * 7)
        self.assertEqual(health[8]["detail"], "Installed and working.")
        self.assertEqual(health[13]["detail"], "No editor hand-off chosen (you can ask for one later).")
        self.assertEqual(health[14]["detail"], "Your editor settings are up to date.")
        for original, h in zip(status, health):
            for key in ("component", "level", "fix"):
                self.assertEqual(h[key], original[key])
            self.assertNotRegex(h["detail"] + h["label"], r"sha256|test mask")
            self.assertNotRegex(h["detail"], r"/|\.json|venv|torch|AMD64|\d+\.\d+\.\d+|parakeet-cpu")
        self.assertIs(next(h for h in health if h["component"] == "resolve-installed")["matters"], False)
        health = hub.plain_health(status, "resolve")
        self.assertIs(next(h for h in health if h["component"] == "resolve-installed")["matters"], True)
        extra = hub.plain_health([dict(component=c, level="missing", detail="missing or damaged: model.bin", fix="Repair it")
                                  for c in ("gpu", "model-other", "resolve-edition", "resolve-version",
                                            "resolve-scripting", "other-tool")], "mcp")
        self.assertEqual([h["label"] for h in extra], ["Graphics card", "Transcription model", "DaVinci Resolve edition",
                                                       "DaVinci Resolve version", "DaVinci Resolve scripting", "Other tool"])
        self.assertTrue(all(h["detail"] == "Some of its files are missing or damaged." for h in extra))
        legacy = "STATUS ffmpeg warn Needs repair"
        self.assertEqual(hub.plain_health([legacy, None, 7], "none"), [legacy, None, 7])
        (self.root / "editor/.platform.json").write_bytes((json.dumps({"status": status}) + "\n").encode("utf-8"))
        cfg_path = self.root / "editor/editor.config.json"
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["nle"] = "none"
        cfg_path.write_bytes((json.dumps(cfg) + "\n").encode("utf-8"))
        with patch.object(hub, "goldmine", return_value=None), patch.object(hub, "style_rows", return_value=[]):
            health = hub.build(self.root)["health"]
        self.assertEqual(len(health), 15)
        self.assertFalse(any(h["matters"] and h["level"] != "ok" for h in health))
        self.assertTrue(all(h.get("label") for h in health))
        self.assertTrue(all("sha256" not in h["detail"] and "test mask" not in h["detail"] for h in health))
        for h in health:
            self.assertNotRegex(h["detail"], r"/|\.json|venv|torch|AMD64|\d+\.\d+\.\d+|parakeet-cpu")

    def test_plain_health_handoff_choices(self):
        for choice, expected in (("none", "No editor hand-off chosen (you can ask for one later)."),
                                 ("mcp", "Files for another editor"), ("resolve", "DaVinci Resolve")):
            with self.subTest(choice=choice):
                row = dict(component="nle", level="ok", detail=choice + " (chosen by you; the doctor keeps it)")
                self.assertEqual(hub.plain_health([row], choice)[0]["detail"], expected)

    def test_plain_health_machine_keeps_os_gpu_and_ram(self):
        for architecture in ("AMD64", "arm64", "x86_64"):
            with self.subTest(architecture=architecture):
                row = dict(component="machine", level="ok",
                           detail=f"macOS 15.2.1 {architecture}, NVIDIA GPU, 32 GB RAM (8 GB free)")
                self.assertEqual(hub.plain_health([row], "none")[0]["detail"],
                                 "macOS 15, NVIDIA GPU, 32 GB RAM (8 GB free)")

    def test_plain_health_warning_paths_keep_the_problem(self):
        for level in ("warn", "missing"):
            for filename in ("editor/editor.config.json", r"C:\editor\editor.config.json",
                             "editor.config.json", "/tmp/editor/config.dat"):
                with self.subTest(level=level, filename=filename):
                    row = dict(component="config", level=level,
                               detail=f"{filename} isn't valid JSON, so the doctor left it as it is", fix="Repair it")
                    result = hub.plain_health([row], "none")[0]
                    self.assertEqual(result["detail"], "a settings file isn't valid JSON, so the doctor left it as it is")
                    self.assertEqual(result["level"], level)
                    self.assertEqual(result["fix"], "Repair it")
        row = dict(component="ffmpeg", level="warn", detail="Video tools need a check")
        self.assertEqual(hub.plain_health([row], "none")[0]["detail"], "Video tools need a check")

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

    def test_voice_only_mix_without_sketches_or_sound_board(self):
        (self.reel / "beat-map.state.json").write_bytes(b'{"sent_at": "now", "beats": []}')
        (self.reel / "sound").mkdir()
        (self.reel / "sound/final.mp4").write_bytes(b"mix")
        row = self.row()
        stages, _ = hub.cockpit_rules()
        for name in ("Motion", "Sound"):
            self.assertTrue(row["done"][next(i for i, s in enumerate(stages) if s["name"] == name)])
        self.assertIs(row["sound_board"], False)
        self.assertIs(row["sound_pass_ran"], True)
        self.assertIs(row["sound_voice_only"], True)
        sound = next(l for l in row["lanes"] if l["label"] == "Sound")
        self.assertEqual((sound["done"], sound["total"]), (1, 1))
        self.assertNotIn(".mp4", row["render_label"])
        (self.reel / "config.json").write_bytes(b"{}")
        self.assertIs(self.row()["sound_board"], True)

    def test_sound_pack_and_pass_are_independent(self):
        library = self.root / "boards/sound"
        library.mkdir(parents=True)
        index = library / "library-index.json"
        self.assertIs(self.row()["sound_pack_installed"], False)
        index.write_bytes(b'{"files": {"tick.wav": {"sha256": "fixture"}}}')
        self.assertIs(self.row()["sound_pack_installed"], False)
        (library / "tick.wav").write_bytes(b"sound")
        row = self.row()
        self.assertIs(row["sound_pack_installed"], True)
        self.assertIs(row["sound_pass_ran"], False)
        self.assertIs(row["sound_board"], False)
        (self.reel / "sound-selection.json").write_bytes(b"{}")
        self.assertIs(self.row()["sound_pass_ran"], True)
        self.assertIs(self.row()["sound_voice_only"], True)
        for choice in ({"cues": [{"file": "tick.wav"}]}, {"bed": {"file": "music.mp3"}}):
            (self.reel / "sound-selection.json").write_bytes(json.dumps(choice).encode("utf-8"))
            self.assertIs(self.row()["sound_voice_only"], False)
        (self.reel / "sound-selection.json").unlink()
        (self.reel / "sound").mkdir()
        (self.reel / "sound/final.mp4").write_bytes(b"mix")
        for bed, voice_only in (({"source": "music.mp3"}, False), ({"source": None}, True)):
            (self.reel / "sound/placement.json").write_bytes(json.dumps({"bed": bed, "cues": []}).encode("utf-8"))
            self.assertIs(self.row()["sound_voice_only"], voice_only)
        index.write_bytes(b"bad JSON")
        self.assertIs(self.row()["sound_pack_installed"], False)

    def test_only_post_remaining_is_ready_even_with_optional_lanes_untouched(self):
        self.assertIs(self.row()["ready_to_post"], False)
        (self.reel / "RAW.mp4").write_bytes(b"")
        (self.reel / "work").mkdir()
        (self.reel / "tweak-selection.json").write_bytes(b"{}")
        (self.reel / "work/cuts.json").write_bytes(b"{}")
        os.utime(self.reel / "tweak-selection.json", (100, 100))
        os.utime(self.reel / "work/cuts.json", (200, 200))
        (self.reel / "beat-map.state.json").write_bytes(b'{"sent_at": "now", "beats": []}')
        (self.reel / "sound-selection.json").write_bytes(b"{}")
        (self.reel / "renders").mkdir()
        (self.reel / "renders/New reel Master - 11.09.26.mp4").write_bytes(b"video")
        with patch.object(hub, "filmstrip", return_value=[]), patch.object(hub, "video_info", return_value={"streams": [{"codec_type": "video"}]}):
            row = self.row()
        self.assertEqual(row["stage_id"], "post")
        self.assertIs(row["ready_to_post"], True)
        self.assertEqual(next(l for l in row["lanes"] if l["label"] == "Grade")["done"], 0)

    def motion_row(self):
        (self.reel / "RAW.mp4").write_bytes(b"")
        (self.reel / "work").mkdir(exist_ok=True)
        (self.reel / "tweak-selection.json").write_bytes(b"{}")
        (self.reel / "work/cuts.json").write_bytes(b"{}")
        os.utime(self.reel / "tweak-selection.json", (100, 100))
        os.utime(self.reel / "work/cuts.json", (200, 200))

    def test_recording_alone_leaves_every_later_stage_unticked(self):
        (self.reel / "RAW.mp4").write_bytes(b"")
        row = self.row()
        self.assertEqual(row["stage"], "Cut")
        self.assertEqual(row["done"], [True, False, False, False, False, False, False, False, False])

    def test_cockpit_rules_read_all_stages_and_reject_unknown_json_predicate(self):
        stages, _ = hub.cockpit_rules()
        self.assertEqual([s["name"] for s in stages],
                         ["Record", "Cut", "Ear pass", "Beat map", "Motion", "Sound", "Grade", "Master", "Post"])
        source = (PLUGIN / "hooks/mod/logic.ts").read_text(encoding="utf-8")
        with patch.object(hub.Path, "read_text", return_value=source.replace("when: sentWithoutScenes", "when: unknownPredicate")):
            with self.assertRaisesRegex(ValueError, "Unrecognised Cockpit JSON rule for Motion"):
                hub.cockpit_rules()

    def test_motion_no_scenes_then_resend_with_scene(self):
        self.motion_row()
        p = self.reel / "beat-map.state.json"
        for beats in ([], [{"scene": None}, {}]):
            p.write_bytes(json.dumps({"sent_at": 0, "beats": beats}).encode("utf-8"))
            row = self.row()
            self.assertTrue(row["done"][4])
            self.assertEqual(row["stage"], "Sound")
        p.write_bytes(json.dumps({"sent_at": "later", "beats": [{"scene": None}, {"scene": "title"}]}).encode("utf-8"))
        row = self.row()
        self.assertFalse(row["done"][4])
        self.assertEqual(row["stage"], "Motion")

    def test_motion_missing_or_malformed_beat_plans_require_locked_sketches(self):
        stages, _ = hub.cockpit_rules()
        rule = next(s["rule"] for s in stages if s["name"] == "Motion")
        self.assertFalse(hub.stage_done(rule, {}, self.reel))
        states = [None, [], {}, {"sent_at": None, "beats": []}, {"beats": []}, {"sent_at": "now"},
                  {"sent_at": "now", "beats": {}}, {"sent_at": "now", "beats": [None]}]
        states += [{"sent_at": "now", "beats": [{"scene": scene}]} for scene in ("title", False, 0, "")]
        for state in states:
            (self.reel / "beat-map.state.json").write_bytes(json.dumps(state).encode("utf-8"))
            self.assertFalse(hub.stage_done(rule, {}, self.reel))
        (self.reel / "sketches.state.json").write_bytes(b'{"locked_at": "now"}')
        self.assertTrue(hub.stage_done(rule, {}, self.reel))

    def test_motion_unlocked_locked_and_unreadable(self):
        stages, _ = hub.cockpit_rules()
        rule = next(s["rule"] for s in stages if s["name"] == "Motion")
        (self.reel / "beat-map.state.json").write_bytes(b'{"sent_at": "now", "beats": []}')
        p = self.reel / "sketches.state.json"
        for content, expected in ((b"{}", True), (b'{"locked_at": "now"}', True), (b"bad JSON", False)):
            p.write_bytes(content)
            self.assertEqual(hub.stage_done(rule, {}, self.reel), expected)
        read_text = hub.Path.read_text
        def busy(path, *args, **kwargs):
            if path == p:
                raise PermissionError("busy")
            return read_text(path, *args, **kwargs)
        with patch.object(hub.Path, "read_text", busy):
            self.assertFalse(hub.stage_done(rule, {}, self.reel))

    def test_ear_pass_requires_an_applied_selection(self):
        (self.reel / "RAW.mp4").write_bytes(b"")
        (self.reel / "work").mkdir()
        selection = self.reel / "tweak-selection.json"
        selection.write_bytes(b"{}")
        os.utime(selection, (200, 200))
        for name in ("edl.json", "cuts.json"):
            p = self.reel / "work" / name
            p.write_bytes(b"{}")
            os.utime(p, (100, 100))
        self.assertEqual(self.row()["stage"], "Ear pass")
        self.assertFalse(self.row()["done"][2])
        for name in ("edl.json", "cuts.json"):
            p = self.reel / "work" / name
            for stamp in (200, 300):
                os.utime(p, (stamp, stamp))
                self.assertTrue(self.row()["done"][2])
            os.utime(p, (100, 100))

    def test_render_labels_are_plain_words(self):
        cases = [("renders/New reel Master - 11.08.26.mp4", "Final master"),
                 ("renders/New reel Preview 720p - 11.08.26.mp4", "Preview (720p)"),
                 ("work/renders/master-1.1x.mp4", "First cut"), ("RAW.mp4", "Your recording"),
                 ("raw/take.mp4", "Your recording"), ("work/other.mp4", "Latest render")]
        for name, expected in cases:
            with self.subTest(name=name):
                p = self.reel / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"video")
                with patch.object(hub, "filmstrip", return_value=[]), patch.object(hub, "video_info", return_value={}):
                    self.assertEqual(self.row()["render_label"], expected)
                p.unlink()
        self.assertEqual(self.row()["render_label"], "No render yet")

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
