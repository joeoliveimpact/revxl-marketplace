"""MB5 no-render proof of the shipped motion review builder and registrations."""
import contextlib
import io
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

P = Path(__file__).resolve().parents[2] / "plugins/editor-superengine"
S = P / "skills/reel-canvas-build/scripts"
sys.path.insert(0, str(S))
import motion_review as review
import scene_render
import heavy_job as jobs


class ReviewTests(unittest.TestCase):
    def test_shipped_rate_is_measured(self):
        # 11.16.26 lane run: 188 s for one 4.2 s scene over 11 passes (~4.1 s); shipped rounded up to 5.
        self.assertEqual(review.SECONDS_PER_SCENE_SECOND, 5)

    def setUp(self):
        if self._testMethodName != "test_shipped_rate_is_measured":
            rate = patch.object(review, "SECONDS_PER_SCENE_SECOND", 10)  # arithmetic tests use a fixed rate
            rate.start(); self.addCleanup(rate.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.reel = Path(self.tmp.name) / "reel"
        self.reel.mkdir()
        fixture = Path(__file__).parent / "fixtures/reel-motion/motion/reel-good-world"
        shutil.copytree(fixture, self.reel / "motion/reel-good-world")
        self.send = {"fps": "30/1", "beats": [{"id": "b_001", "start_f": 0, "end_f": 120,
                     "layout": "full", "cover_face": True, "scene": {"id": "reel-good-world"},
                     "speech_anchor": {"w0": 0, "w1": 1}}]}
        self.write("beat-map-selection.json", self.send)
        self.write("work/edit_map.cut.json", {"words": [{"word": "Clear"}, {"word": "world"}]})

    def write(self, name, obj):
        p = self.reel / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((json.dumps(obj) + "\n").encode())

    def test_none_records_explicit_choice_without_a_beat_map(self):
        (self.reel / "beat-map-selection.json").unlink()
        self.write("motion-review-selection.json", {"sections": [{"leave": False, "note": "Change it"}]})
        before = datetime.now(timezone.utc)
        with (patch.object(sys, "argv", ["motion_review.py", "none", "--reel-dir", str(self.reel)]),
              contextlib.redirect_stdout(io.StringIO()) as out):
            self.assertEqual(review.main(), 0)
        path = self.reel / "motion-review-selection.json"
        record = json.loads(path.read_bytes())
        self.assertEqual(set(record), {"none", "sections", "sent_at"})
        self.assertIs(record["none"], True)
        self.assertEqual(record["sections"], [])
        self.assertLessEqual(before, datetime.fromisoformat(record["sent_at"]))
        self.assertLessEqual(datetime.fromisoformat(record["sent_at"]), datetime.now(timezone.utc))
        self.assertNotIn(b"\r", path.read_bytes())
        self.assertEqual(out.getvalue().splitlines(), ["Recorded no motion graphics for this reel."])

    def test_estimate_and_spike_rate(self):
        self.write("beat-map-selection.json", dict(self.send, edit_style={"style": "punch-in"}))
        # Authored world: 3s * 5 passes; selected fill: 4s * 5; loop: 4s.
        self.assertEqual(review.estimate_text(review.entries(self.reel), self.reel),
                         "About 390 seconds for 1 scene (10 seconds per scene second per render pass; "
                         "11 render passes total), one scene at a time.")
        with patch.object(review, "SECONDS_PER_SCENE_SECOND", 2):
            with (patch.object(review, "heavy_job", side_effect=jobs.HeavyJobError("Need RAM.")),
                  contextlib.redirect_stdout(io.StringIO()) as out,
                  self.assertRaises(jobs.HeavyJobError)):
                review.build(self.reel)
            self.assertEqual(out.getvalue().splitlines()[0],
                             "About 78 seconds for 1 scene (2 seconds per scene second per render pass; "
                             "11 render passes total), one scene at a time.")

    def test_estimate_counts_each_kind_and_multiple_scenes(self):
        entry = review.entries(self.reel)[0]
        spec = json.loads((self.reel / "motion/reel-good-world/scene.json").read_text())
        for kind, params, seconds, passes in (("overlay", {}, 320, 9),
                                             ("overlay", {"dy": {}}, 460, 13),
                                             ("takeover", {}, 460, 13)):
            with self.subTest(kind=kind, params=params):
                self.write("motion/reel-good-world/scene.json", dict(spec, kind=kind, params=params))
                text = review.estimate_text([entry, entry], self.reel)
                self.assertIn(f"About {seconds * 2} seconds for 2 scenes", text)
                self.assertIn(f"{passes * 2} render passes total", text)

    def test_shipped_files_have_no_build_lane_paths(self):
        for path in P.rglob("*"):
            if path.is_file():
                content = path.read_bytes().replace(b"\\", b"/")
                self.assertFalse(b"C:/Work/_scratch" in content or b"_scratch/editor-superengine" in content,
                                 f"Build lane path in {path}")

    def test_lock_uses_editor_home_override(self):
        home = self.reel / "editor-home"
        with (patch.dict(os.environ, {"EDITOR_SE_HOME": str(home)}),
              patch.object(jobs, "_resources")):
            with review.heavy_job("Motion review"):
                lock = home / "locks/heavy.lock"
                self.assertEqual(json.loads(lock.read_text())["label"], "Motion review")
        self.assertFalse(lock.exists())

    def test_build_waits_for_held_lock_then_builds_without_rendering(self):
        self.write("beat-map-selection.json", dict(self.send, edit_style={"style": "punch-in"}))
        lock = self.reel / "locks/heavy.lock"
        lock.parent.mkdir()
        lock.write_text(json.dumps(dict(pid=os.getpid(), label="First preview", started=1)))
        reached = []
        def media(reel, entry, work):
            self.assertTrue(released.is_set())
            self.assertEqual(json.loads(lock.read_text())["label"], "Motion review")
            reached.append(entry["scene"])
        released = threading.Event()
        def release():
            lock.unlink()
            released.set()
        timer = threading.Timer(1.1, release)
        with (patch.dict(os.environ, EDITOR_SE_HOME=str(self.reel)),
              patch.object(jobs, "_resources"),
              patch.object(review, "build_media", side_effect=media),
              contextlib.redirect_stdout(io.StringIO()) as out):
            timer.start()
            try:
                result = review.build(self.reel)
            finally:
                timer.cancel()
                timer.join()
        self.assertEqual(result, 0, out.getvalue())
        self.assertEqual(reached, ["reel-good-world"])
        self.assertEqual(out.getvalue().count(
            "Another editor job is running (First preview); yours is queued and starts when it finishes."), 1)
        self.assertFalse(lock.exists())

    def test_lock_times_out_only_after_two_hours_with_one_plain_line(self):
        self.write("beat-map-selection.json", dict(self.send, edit_style={"style": "punch-in"}))
        lock = self.reel / "locks/heavy.lock"
        lock.parent.mkdir()
        data = json.dumps(dict(pid=os.getpid(), label="First preview", started=1))
        lock.write_text(data)
        with (patch.dict(os.environ, EDITOR_SE_HOME=str(self.reel)),
              patch.object(jobs, "_resources"),
              patch.object(jobs.time, "monotonic", side_effect=[0, 60, 7199, 7200]),
              patch.object(jobs.time, "sleep") as sleep,
              patch.object(sys, "argv", ["motion_review.py", "build", "--reel-dir", str(self.reel)]),
              contextlib.redirect_stdout(io.StringIO()) as out):
            self.assertEqual(review.main(), 1)
        self.assertEqual(sleep.call_count, 2)
        self.assertTrue(all(call.args[0] > 0 for call in sleep.call_args_list))
        self.assertEqual(out.getvalue().splitlines()[1:], [
            "Another editor job is running (First preview); yours is queued and starts when it finishes.",
            "Waited 2 hours for another editor job to finish; run this job again."])
        self.assertEqual(lock.read_text(), data)

    def test_resources_and_single_line_refusal(self):
        self.write("beat-map-selection.json", dict(self.send, edit_style={"style": "punch-in"}))
        with (patch.dict(os.environ, EDITOR_SE_HOME=str(self.reel)),
              patch.object(jobs, "free_ram_mb", return_value=3071),
              patch.object(review, "build_media") as media,
              patch.object(sys, "argv", ["motion_review.py", "build", "--reel-dir", str(self.reel)]),
              contextlib.redirect_stdout(io.StringIO()) as out):
            self.assertEqual(review.main(), 1)
        media.assert_not_called()
        self.assertEqual(out.getvalue().splitlines()[1:], [
            "This editor job needs 3 GB free RAM; close other apps and run again."])
        self.assertFalse((self.reel / "locks/heavy.lock").exists())

    def test_first_beat_and_only_referenced_scenes(self):
        other = dict(self.send["beats"][0], id="b_002", start_f=120, end_f=240, scene={"id": "callout"})
        self.send["beats"].append(other)
        self.send["hook"] = {"scene": {"id": "reel-hook-world"}}
        self.write("beat-map-selection.json", self.send)
        entries = review.entries(self.reel)
        self.assertEqual([(e["scene"], e["beat"]) for e in entries],
                         [("reel-good-world", "b_001")])

    def test_notes_apply_and_bad_review_shape(self):
        self.send["edit_style"] = {"style": "layout-switch"}
        self.write("beat-map-selection.json", self.send)
        self.write("motion-review-selection.json", {"sections": [
            {"scene": "reel-good-world", "beat": "b_001", "note": " Keep the windows larger ", "leave": False}]})
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(review.apply(self.reel), 0)
        self.assertEqual(out.getvalue(), "reel-good-world: Keep the windows larger\n")
        self.assertFalse((self.reel / "motion/reel-good-world/locked").exists())
        self.assertTrue(review.review_problems({"schema": 1, "cards": [{}]}))
        self.assertTrue(review.review_problems([]))

    def test_apply_copies_saved_style_and_preserves_existing_choice(self):
        self.write("motion-review-selection.json", {"sections": []})
        saved = {"style": "punch-in", "punch_scale": 1.2}
        with (patch.object(review.compose.styles.saved_style, "load", return_value={"edit_style": saved}),
              contextlib.redirect_stdout(io.StringIO()) as out):
            self.assertEqual(review.apply(self.reel), 0)
        self.assertEqual(json.loads((self.reel / "beat-map-selection.json").read_text())["edit_style"], saved)
        self.assertIn("saved", out.getvalue())
        stamp = (self.reel / "beat-map-selection.json").stat().st_mtime_ns
        with contextlib.redirect_stdout(io.StringIO()):
            review.apply(self.reel)
        self.assertEqual((self.reel / "beat-map-selection.json").stat().st_mtime_ns, stamp)

    def test_apply_without_style_prints_exact_ask_and_succeeds(self):
        self.write("motion-review-selection.json", {"sections": []})
        with (patch.object(review.compose.styles.saved_style, "load", return_value={}),
              contextlib.redirect_stdout(io.StringIO()) as out):
            self.assertEqual(review.apply(self.reel), 0)
        self.assertEqual(out.getvalue(), "Ask the user once: punch-ins on jump cuts, or layout switches? Then record it with motion_review.py style --reel-dir <reel> --style punch-in|layout-switch.\n")
        self.assertNotIn("edit_style", json.loads((self.reel / "beat-map-selection.json").read_text()))

    def test_invalid_saved_style_asks_without_changing_send(self):
        path = self.reel / "beat-map-selection.json"
        before = path.read_bytes()
        self.write("motion-review-selection.json", {"sections": []})
        for saved in ({"style": "invalid"}, {"style": "punch-in", "extra": True},
                      {"punch_scale": 1.2}, "punch-in", None):
            with (self.subTest(saved=saved),
                  patch.object(review.compose.styles.saved_style, "load", return_value={"edit_style": saved}),
                  contextlib.redirect_stdout(io.StringIO()) as out):
                self.assertEqual(review.apply(self.reel), 0)
            self.assertEqual(out.getvalue(), review.STYLE_ASK + "\n")
            self.assertEqual(path.read_bytes(), before)

    def test_saved_style_never_creates_missing_beat_map_send(self):
        path = self.reel / "beat-map-selection.json"
        path.unlink()
        for saved in ({"edit_style": {"style": "punch-in"}}, {}):
            with (self.subTest(saved=saved),
                  patch.object(review.compose.styles.saved_style, "load", return_value=saved),
                  contextlib.redirect_stdout(io.StringIO()) as out):
                review.record_saved_style(self.reel)
            self.assertEqual(out.getvalue(), "The Beat Map Send is missing; Send the Beat Map first.\n")
            self.assertFalse(path.exists())

    def test_style_command_validates_and_changes_only_edit_style(self):
        for style in review.compose.styles.STYLES:
            with patch.object(sys, "argv", ["motion_review.py", "style", "--reel-dir", str(self.reel), "--style", style]):
                self.assertEqual(review.main(), 0)
            self.assertEqual(json.loads((self.reel / "beat-map-selection.json").read_text()),
                             dict(self.send, edit_style={"style": style}))
        before = (self.reel / "beat-map-selection.json").read_bytes()
        with (patch.object(sys, "argv", ["motion_review.py", "style", "--reel-dir", str(self.reel), "--style", "invalid"]),
              contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit)):
            review.main()
        self.assertEqual((self.reel / "beat-map-selection.json").read_bytes(), before)

    def test_media_composites_native_area_over_newest_cut_without_audio(self):
        self.write("beat-map-selection.json", dict(self.send, edit_style={"style": "punch-in"}))
        folder = self.reel / "motion/reel-good-world"
        spec = json.loads((folder / "scene.json").read_text())
        spec["area"] = "stack"
        self.write("motion/reel-good-world/scene.json", spec)
        renders = self.reel / "work/renders"
        renders.mkdir(parents=True)
        for i in (1, 2):
            master = renders / f"master-{i}.mp4"
            master.write_bytes(b"fixture")
            import os
            os.utime(master, (i, i))
        entry = review.entries(self.reel)[0]
        entry["_beat"]["layout"] = "stack"
        entry["start_s"], entry["end_s"] = 1, 5
        work = self.reel / "temp"
        work.mkdir()
        def make_project(dst, *args):
            dst.mkdir()
            (dst / "index.html").write_bytes((folder / "scene.html").read_bytes())
        with (patch.object(scene_render, "make_env", return_value=({}, work / "net.jsonl")),
              patch.object(scene_render, "scene_test") as checks,
              patch.object(review.compose, "scene_project", side_effect=make_project) as project,
              patch.object(scene_render, "render", return_value=(True, "")),
              patch.object(scene_render, "probe", return_value={"nb_read_frames": 120}),
              patch.object(scene_render, "caption_band_ranges", return_value=[]),
              patch.object(scene_render, "kill_warm"), patch.object(review, "run_media") as media):
            review.build_media(self.reel, entry, work)
        self.assertEqual(checks.call_args.args[5], "review")
        self.assertEqual(project.call_args.args[1], entry["_beat"])
        preview, start, loop = [call.args[0] for call in media.call_args_list]
        self.assertIn("select=eq(n\\,119),scale=270:480:flags=lanczos,format=rgba", preview)
        self.assertIn("select=eq(n\\,0),scale=270:480:flags=lanczos,format=rgba", start)
        self.assertEqual(loop[loop.index("-ss") + 1], "1")
        self.assertEqual(loop[loop.index("-i") + 1], renders / "master-2.mp4")
        x, y, _, _ = review.compose.world_area("stack")
        self.assertIn(f"overlay={x}:{y}:shortest=1,scale=720:1280", loop[loop.index("-filter_complex") + 1])
        self.assertIn("-an", loop)
        self.assertIn("libx264", loop)

    def test_selected_fill_is_checked_and_pip_face_stays_above_world(self):
        self.write("beat-map-selection.json", dict(self.send, edit_style={"style": "punch-in"}))
        renders = self.reel / "work/renders"
        renders.mkdir(parents=True)
        (renders / "master-fixture.mp4").write_bytes(b"fixture")
        entry = review.entries(self.reel)[0]
        entry["_beat"]["layout"] = "pip"
        entry["_beat"]["scene"]["slots"] = {"text": "Selected"}
        entry["_beat"]["scene"]["params"] = {"t1": 1.4}
        work = self.reel / "temp"
        work.mkdir()
        with (patch.object(scene_render, "make_env", return_value=({}, work / "net.jsonl")),
              patch.object(scene_render, "scene_test") as checks,
              patch.object(scene_render, "render", return_value=(True, "")),
              patch.object(scene_render, "probe", return_value={"nb_read_frames": 120}),
              patch.object(scene_render, "caption_band_ranges", return_value=[]),
              patch.object(scene_render, "kill_warm"), patch.object(review, "run_media") as media):
            review.build_media(self.reel, entry, work)
        self.assertEqual(checks.call_count, 2, "Selected fill never received holds and seek checks")
        selected = checks.call_args.kwargs
        self.assertEqual(selected["fill_override"]["text"], "Selected")
        self.assertEqual(selected["fill_override"]["t1"], 1.4)
        self.assertIn('data-duration="4"', selected["html_override"])
        graph = media.call_args_list[-1].args[0]
        graph = graph[graph.index("-filter_complex") + 1]
        self.assertIn("[graphic][face]overlay=", graph)
        self.assertLess(graph.index("[base][scene]overlay="), graph.index("[graphic][face]overlay="))

    def test_between_hold_crossings_reach_user_as_separate_plain_lines(self):
        self.send["edit_style"] = {"style": "punch-in"}
        renders = self.reel / "work/renders"
        renders.mkdir(parents=True)
        (renders / "master-fixture.mp4").write_bytes(b"fixture")
        beat = self.send["beats"][0]
        beat.update(start_f=180, end_f=300)
        self.write("beat-map-selection.json", self.send)
        self.write("work/word_map.json", {"words": [
            {"id": "w_0000", "word": "other beat", "out_start": 5.9, "out_end": 6.6},
            {"id": "w_0001", "word": "Claude", "out_start": 6.49, "out_end": 6.6},
            {"id": "w_0002", "word": "can", "out_start": 6.5, "out_end": 6.6},
            {"id": "w_0003", "word": "later", "out_start": 7, "out_end": 7.1},
            {"id": "w_0004", "word": "boundary", "out_start": 7.1, "out_end": 7.2}]})
        width, height = map(int, review.compose.world_area("full")[2:])
        buf = bytearray(120 * width * height)
        for frame in (15, 30, 31, 32):
            buf[(frame * height + 1320) * width + 100] = 1
        work = self.reel / "temp"
        work.mkdir()
        with (patch.object(review, "heavy_job", lambda label: contextlib.nullcontext()),
              patch.object(scene_render, "make_env", return_value=({}, work / "net.jsonl")),
              patch.object(scene_render, "scene_test"),
              patch.object(scene_render, "probe", return_value={"nb_read_frames": 120}),
              patch.object(scene_render, "raw", return_value=bytes(buf)) as raw,
              patch.object(review, "run_media"),
              patch.object(scene_render, "kill_warm"), contextlib.redirect_stdout(io.StringIO()) as out):
            self.assertEqual(review.build(self.reel), 1)
        self.assertEqual(out.getvalue().splitlines()[1:], [
            "Beat b_001: from 6.50 to 6.53 s the graphic crosses the caption band, "
            "under the words 'Claude can'. Move it out of the band.",
            "Beat b_001: from 7.00 to 7.10 s the graphic crosses the caption band, "
            "under the words 'later'. Move it out of the band."])
        self.assertEqual(raw.call_args.args[0].name, "reel-good-world.mov")
        self.assertEqual(raw.call_args.args[0].parent.name, "selected-check")
        self.assertEqual(json.loads((self.reel / "motion/review/review.json").read_bytes())["cards"], [])

    def test_lock_sha_apply_and_idempotency(self):
        self.write("motion-review-selection.json", {"schema": 1, "sections": [
            {"scene": "reel-good-world", "beat": "b_001", "note": "", "leave": True}]})
        folder = self.reel / "motion/reel-good-world"
        self.assertFalse(review.is_locked(folder))
        with contextlib.redirect_stdout(io.StringIO()):
            review.apply(self.reel)
            stamp = (folder / "locked").stat().st_mtime_ns
            review.apply(self.reel)
        self.assertTrue(review.is_locked(folder))
        self.assertEqual(review.scene_check.scene_problems(folder), [])
        self.assertEqual((folder / "locked").stat().st_mtime_ns, stamp)
        with (folder / "scene.html").open("ab") as f:
            f.write(b"\n<!-- edit -->\n")
        self.assertFalse(review.is_locked(folder))

    def test_build_fixture_cards_failure_and_locked_skip(self):
        self.write("beat-map-selection.json", dict(self.send, edit_style={"style": "punch-in"}))
        # Inject only the expensive boundary; exercise discovery, output and state in the real builder.
        def media(reel, entry, work):
            for path in (reel / "motion" / entry["scene"] / "preview.png",
                         reel / "motion/review" / (entry["scene"] + "-start.png"),
                         reel / "motion/review" / (entry["scene"] + "-loop.mp4")):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fixture")
            (reel / "motion" / entry["scene"] / "preview.png").write_bytes(
                b"\x89PNG\r\n\x1a\n" + b"\0\0\0\rIHDR" + struct.pack(">II", 270, 480))
        with (patch.object(review, "heavy_job", lambda label: contextlib.nullcontext()),
              patch.object(review, "build_media", side_effect=media) as render,
              contextlib.redirect_stdout(io.StringIO()) as output):
            result = review.build(self.reel)
            self.assertEqual(result, 0, output.getvalue())
            doc = json.loads((self.reel / "motion/review/review.json").read_text())
            self.assertEqual(len(doc["cards"]), 1)
            self.assertEqual(review.review_problems(doc), [])
            self.assertEqual(doc["cards"][0]["state"], "new")
            catalog = json.loads((self.reel / "scenes/catalog.json").read_bytes())
            own = next(item for item in catalog if item["id"] == "reel-good-world")
            self.assertIs(own["reel"], True)
            self.assertEqual(own["beats"], ["b_001"])
            self.assertEqual(own["preview"], "motion/reel-good-world/preview.png")
            self.assertEqual(doc["cards"][0]["checks"], "passed")
            self.assertIn("About 390 seconds", output.getvalue())
            self.assertEqual(review.build(self.reel), 0)
            self.assertEqual(json.loads((self.reel / "motion/review/review.json").read_text())["cards"][0]["state"], "new")
            self.write("motion-review-selection.json", {"sections": [
                {"scene": "reel-good-world", "beat": "b_001", "note": "Larger windows", "leave": False}]})
            self.assertEqual(review.build(self.reel), 0)
            self.assertEqual(json.loads((self.reel / "motion/review/review.json").read_text())["cards"][0]["state"], "rebuilt")
            self.write("motion-review-selection.json", {"sections": [
                {"scene": "reel-good-world", "beat": "b_001", "note": "", "leave": True}]})
            review.apply(self.reel)
            render.reset_mock()
            self.assertEqual(review.build(self.reel), 0)
            render.assert_not_called()
            self.assertEqual(json.loads((self.reel / "motion/review/review.json").read_text())["cards"][0]["state"], "locked")
            (self.reel / "motion/reel-good-world/scene.html").write_bytes(b"broken")
            self.assertEqual(review.build(self.reel), 1)
            self.assertEqual(json.loads((self.reel / "motion/review/review.json").read_text())["cards"], [])
            self.assertNotIn("reel-good-world", [item["id"] for item in
                json.loads((self.reel / "scenes/catalog.json").read_bytes())])

    def test_registration_and_dangling_references(self):
        entry = json.loads((P / "skills/editor-doctor/scripts/boards.json").read_text())["boards"]["motion-review"]
        self.assertEqual(entry, {"skill": "reel-canvas-build", "template": "skills/reel-canvas-build/boards/motion-review",
            "writes": ["motion-review-selection.json"], "tab": {"label": "Motion review", "stages": ["motion"], "order": 35}})
        self.assertTrue((P / entry["template"] / "index.html").is_file())
        text = (P / "skills/reel-canvas-build/references/motion-build.md").read_text()
        command = '<editor python> -X utf8 -I "${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/scripts/motion_review.py"'
        self.assertIn(command + ' build --reel-dir "<reel folder>"', text)
        self.assertIn(command + ' apply --reel-dir "<reel folder>"', text)
        self.assertNotIn("MB5 adds it here", text)
        sys.path.insert(0, str(P / "skills/editor-doctor/scripts"))
        import hub_rows
        _, sends = hub_rows.cockpit_rules(P)
        self.assertIn({"file": "motion-review-selection.json", "board": "motionreview",
                       "downstream": ["motion/review/review.json"]}, sends)

    def test_shipped_checks_are_used_by_catalog_test(self):
        sys.path.insert(0, str(Path(__file__).parent))
        import scene_render_test
        self.assertIs(scene_render_test.scene_test, scene_render.scene_test)
        self.assertIs(scene_render_test.hold_problems, scene_render.hold_problems)

    def test_selected_checks_use_beat_duration_and_hold_times(self):
        folder = self.reel / "motion/reel-good-world"
        html = re.sub(r'data-duration="[^"]+"', 'data-duration="2"', (folder / "scene.html").read_text())
        with (patch.object(scene_render, "project") as project,
              patch.object(scene_render, "base_checks") as base,
              patch.object(scene_render, "seek_checks") as seek,
              contextlib.redirect_stdout(io.StringIO())):
            scene_render.scene_test("reel-good-world", self.reel, {}, self.reel / "net.jsonl", False, "review",
                scenes_dir=self.reel / "motion", html_override=html, fill_override={"text": "Selected", "t1": 1.4})
        self.assertEqual(project.call_args.args[2], html)
        self.assertEqual(base.call_args.args[4:6], (60, 2.0))
        self.assertEqual(base.call_args.args[6]["text"], "Selected")
        self.assertEqual(base.call_args.args[7]["text"], "W" * 12)
        self.assertEqual(base.call_args.args[7]["t1"], 1.4)
        self.assertEqual(seek.call_args.args[1], 60)
        self.assertEqual(seek.call_args.args[2]["t1"], 1.4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
