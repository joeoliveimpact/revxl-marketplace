"""INT13-B: placement, first-beat hook and style-consistent world face slots."""
import contextlib
import copy
import io
import json
import os
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motion_review_test as fixture
import world_scene_layout_test as world

sys.path.insert(0, str(fixture.P / "skills/editor-doctor/scripts"))
import hub_rows as hub

review = fixture.review
compose = review.compose


class MotionOrder(unittest.TestCase):
    setUp = fixture.ReviewTests.setUp
    write = fixture.ReviewTests.write

    def command(self, name, *args):
        with (patch.object(sys, "argv", ["motion_review.py", name, "--reel-dir", str(self.reel), *args]),
              contextlib.redirect_stdout(io.StringIO()) as out,
              contextlib.redirect_stderr(io.StringIO())):
            try:
                result = review.main()
            except SystemExit as error:
                result = error.code
        return result, out.getvalue()

    def two_scenes(self):
        original = self.reel / "motion/reel-good-world"
        self.send["edit_style"] = {"style": "punch-in", "punch_scale": 1.2}
        self.send["beats"][0]["scene"] = None
        self.send["beats"].append(dict(self.send["beats"][0], id="b_002", start_f=120,
                                        end_f=240, cover_face=False))
        for i in (1, 2):
            sid = f"reel-b00{i}-world"
            folder = self.reel / "motion" / sid
            shutil.copytree(original, folder)
            page = (folder / "scene.html").read_text(encoding="utf-8")
            (folder / "scene.html").write_bytes(page.replace("reel-good-world", sid).encode("utf-8"))
            spec = review.read(folder / "scene.json")
            spec.update(id=sid, category=sid, source=f"Own scene for beat b_00{i}")
            review.write_json(folder / "scene.json", spec)
        shutil.rmtree(original)
        self.write("beat-map-selection.json", self.send)
        self.write("beat-map.state.json", dict(self.send, notes={"keep": "state only"}))

    def test_place(self):
        self.two_scenes()
        before = {name: review.read(self.reel / name) for name in
                  ("beat-map.state.json", "beat-map-selection.json")}
        code, output = self.command("place")
        self.assertEqual(code, 0, output)
        self.assertEqual(output, "Placed 2 scenes on the Beat Map.\n")
        for name, old in before.items():
            placed = review.read(self.reel / name)
            for i, beat in enumerate(placed["beats"], 1):
                self.assertEqual(review.scene_check.fill_problems(beat["scene"]["id"], beat, reel=self.reel), [])
                self.assertEqual(beat["scene"], {"id": f"reel-b00{i}-world",
                                                "slots": {"text": "Clear world"}, "params": {}})
                beat["scene"] = old["beats"][i - 1]["scene"]
            self.assertEqual(placed, old)
        own = [item for item in review.read(self.reel / "scenes/catalog.json") if item.get("reel")]
        self.assertEqual([(item["id"], item["beats"]) for item in own],
                         [("reel-b001-world", ["b_001"]), ("reel-b002-world", ["b_002"])])
        # A missing peer document is seeded from the existing board document.
        for missing in before:
            (self.reel / missing).unlink()
            self.assertEqual(self.command("place")[0], 0)
            self.assertEqual(len(review.read(self.reel / missing)["beats"]), 2)
        # Unknown beats refuse before either document or the catalog is rewritten.
        self.write("motion/reel-b002-world/scene.json", dict(
            review.read(self.reel / "motion/reel-b002-world/scene.json"), source="Own scene for beat b_999"))
        paths = [self.reel / name for name in (*before, "scenes/catalog.json")]
        raw = [path.read_bytes() for path in paths]
        code, output = self.command("place")
        self.assertNotEqual(code, 0)
        self.assertIn("b_999", output)
        self.assertEqual([path.read_bytes() for path in paths], raw)

    def test_replace(self):
        self.two_scenes()
        before = {}
        for name in ("beat-map.state.json", "beat-map-selection.json"):
            doc = review.read(self.reel / name)
            doc["beats"][0]["scene"] = {"id": "callout", "slots": {"title": "Old words"},
                                         "params": {"value": 5}}
            self.write(name, doc)
            before[name] = doc
        code, output = self.command("place")
        self.assertEqual(code, 0, output)
        self.assertEqual(output, "Placed 2 scenes on the Beat Map.\n")
        for name, old in before.items():
            doc = review.read(self.reel / name)
            beat = doc["beats"][0]
            self.assertEqual(beat["scene"], {"id": "reel-b001-world",
                                            "slots": {"text": "Clear world"}, "params": {}})
            self.assertEqual(review.scene_check.fill_problems(beat["scene"]["id"], beat, reel=self.reel), [])
            for placed, previous in zip(doc["beats"], old["beats"]):
                placed["scene"] = previous["scene"]
            self.assertEqual(doc, old)
        # Placing the same scene again retains the user's valid text and timings.
        for name in before:
            doc = review.read(self.reel / name)
            doc["beats"][0]["scene"].update(slots={"text": "world"}, params={"t1": 1.4})
            self.write(name, doc)
        saved = {name: review.read(self.reel / name) for name in before}
        self.assertEqual(self.command("place")[0], 0)
        self.assertEqual({name: review.read(self.reel / name) for name in before}, saved)

    def test_invalid_fill_leaves_both_maps_unchanged(self):
        self.two_scenes()
        paths = [self.reel / name for name in ("beat-map.state.json", "beat-map-selection.json")]
        original = [path.read_bytes() for path in paths]
        for invalid in paths:
            with self.subTest(document=invalid.name):
                for path, data in zip(paths, original):
                    path.write_bytes(data)
                doc = review.read(invalid)
                doc["beats"][0]["scene"] = {"id": "reel-b001-world",
                                             "slots": {"text": "x" * 13}, "params": {}}
                review.write_json(invalid, doc)
                before = [path.read_bytes() for path in paths]
                code, output = self.command("place")
                self.assertNotEqual(code, 0, output)
                self.assertIn("b_001", output)
                self.assertNotIn("Placed ", output)
                self.assertEqual([path.read_bytes() for path in paths], before)

    def test_resend(self):
        self.two_scenes()
        self.assertEqual(self.command("place")[0], 0)
        board = (fixture.P / "skills/reel-canvas-build/boards/beat-map/index.html").read_text(encoding="utf-8")
        # The board loads state first, saves doc and posts JSON.stringify(doc).
        self.assertIn("doc = await bc.load();", board)
        self.assertIn("const s = await bc.save(doc);", board)
        self.assertIn("body: JSON.stringify(doc)", board)
        doc = review.read(self.reel / "beat-map.state.json")
        doc["beats"][0]["cover_face"] = True
        doc["sent_at"] = "2026-11-16T12:00:00Z"
        self.write("beat-map-selection.json", doc)
        sent = review.read(self.reel / "beat-map-selection.json")
        self.assertEqual([b["scene"]["id"] for b in sent["beats"]],
                         ["reel-b001-world", "reel-b002-world"])
        self.assertIs(sent["beats"][0]["cover_face"], True)
        self.assertEqual(sent["edit_style"], self.send["edit_style"])

    def test_motion_writes_do_not_reopen_beat_map_send(self):
        self.two_scenes()
        send = self.reel / "beat-map-selection.json"
        stamp = 1_700_000_000_000_000_000
        os.utime(send, ns=(stamp, stamp))
        self.write("sketches.state.json", {"locked_at": "2026-11-16T12:00:00Z"})
        _, sends = hub.cockpit_rules()
        beat_sends = [s for s in sends if s["file"] == send.name]
        acked = {f"{self.reel.name}/{send.name}": hub.mtime(send)}
        for action in (lambda: self.command("place"),
                       lambda: self.command("style", "--style", "layout-switch"),
                       lambda: review.record_saved_style(self.reel)):
            # Exercise the saved-style copy too, rather than its early return.
            doc = review.read(send)
            doc.pop("edit_style", None)
            self.write(send.name, doc)
            os.utime(send, ns=(stamp, stamp))
            with (patch.object(compose.styles, "pick_style", return_value=({"style": "punch-in"}, [])),
                  contextlib.redirect_stdout(io.StringIO())):
                action()
            self.assertEqual(hub.open_sends(self.reel, beat_sends, 0, acked), [])
            self.assertEqual(send.stat().st_mtime_ns, stamp)
        # A real board Send still opens, even with the same JSON choices.
        self.write(send.name, review.read(send))
        self.assertEqual(len(hub.open_sends(self.reel, beat_sends, 0, acked)), 1)
        # Internal writes must also leave an unacted user Send open.
        self.assertEqual(self.command("place")[0], 0)
        self.assertEqual(len(hub.open_sends(self.reel, beat_sends, 0, acked)), 1)

    def test_style_keeps_board_state_in_sync(self):
        self.two_scenes()
        state = self.reel / "beat-map.state.json"
        before = review.read(state)
        code, output = self.command("style", "--style", "layout-switch")
        self.assertEqual(code, 0, output)
        expected = dict(before, edit_style={"style": "layout-switch"})
        self.assertEqual(review.read(state), expected)
        self.assertEqual(review.read(self.reel / "beat-map-selection.json")["edit_style"], expected["edit_style"])
        # No board state yet is valid; style must not require a hand-written peer.
        state.unlink()
        self.assertEqual(self.command("style", "--style", "punch-in")[0], 0)

    def test_zero(self):
        self.send.update(edit_style={"style": "punch-in"})
        self.send["beats"][0]["scene"] = None
        self.write("beat-map-selection.json", self.send)
        with patch.object(review, "heavy_job", lambda label: contextlib.nullcontext()):
            code, output = self.command("build")
        self.assertNotEqual(code, 0)
        self.assertIn("No motion scenes are on the Beat Map yet. Run place first.", output)
        self.assertFalse((self.reel / "motion/review/review.json").exists())

    def test_none_cleared(self):
        self.write("beat-map-selection.json", dict(self.send, edit_style={"style": "punch-in"}))
        self.assertEqual(self.command("none")[0], 0)
        selection = self.reel / "motion-review-selection.json"
        stages, _ = hub.cockpit_rules()
        rule = next(stage["rule"] for stage in stages if stage["name"] == "Motion")
        self.assertTrue(hub.stage_done(rule, {}, self.reel))

        def media(reel, entry, work):
            self.assertFalse(selection.exists(), "Clear the no-motion choice before rendering.")

        with (patch.object(review, "heavy_job", lambda label: contextlib.nullcontext()),
              patch.object(review, "build_media", side_effect=media)):
            code, output = self.command("build")
        self.assertEqual(code, 0, output)
        self.assertFalse(selection.exists())
        self.assertIn("Your earlier 'no motion graphics' choice is cleared, because this reel now has scenes to review.",
                      output.splitlines())
        self.assertEqual(len(review.read(self.reel / "motion/review/review.json")["cards"]), 1)
        self.assertFalse(hub.stage_done(rule, {}, self.reel))

    def test_none_kept(self):
        self.write("beat-map-selection.json", dict(self.send, edit_style={"style": "punch-in"}))
        selection = self.reel / "motion-review-selection.json"
        for leave in (True, False):
            for none in (False, True):
                with self.subTest(leave=leave, none=none):
                    self.write(selection.name, {"none": none, "sections": [
                        {"scene": "reel-good-world", "beat": "b_001", "leave": leave,
                         "note": "Keep these review notes"}], "sent_at": "2026-11-16T12:00:00Z"})
                    before = selection.read_bytes()
                    with (patch.object(review, "heavy_job", lambda label: contextlib.nullcontext()),
                          patch.object(review, "build_media")):
                        code, output = self.command("build")
                    self.assertEqual(code, 0, output)
                    self.assertEqual(selection.read_bytes(), before)
                    self.assertNotIn("choice is cleared", output)

    def test_hook(self):
        self.send.update(hook={"scene": {"id": "reel-ignored-hook"}}, hook_scene="reel-ignored-too")
        self.write("beat-map-selection.json", self.send)
        self.write("work/word_map.json", {"words": [
            {"id": "w_0001", "word": "Clear", "out_start": 1.4, "out_end": 1.6}]})
        self.assertEqual([(e["beat"], e["scene"]) for e in review.entries(self.reel)],
                         [("b_001", "reel-good-world")])
        code, output = self.command("times", "--beat", "b_001", "--words", "w_0001")
        self.assertEqual(code, 0, output)
        self.assertEqual(json.loads(output), {"t1": 1.4})

    def test_style_first(self):
        self.send.pop("edit_style", None)
        self.write("beat-map-selection.json", self.send)
        with (patch.object(compose.styles.saved_style, "load", return_value={}),
              patch.object(review, "heavy_job", lambda label: contextlib.nullcontext()),
              patch.object(review, "build_media") as media):
            code, output = self.command("build")
        self.assertNotEqual(code, 0)
        self.assertEqual(output.strip(), "Pick the editing style first, then build the motion.")
        media.assert_not_called()

    def test_review_face(self):
        (self.reel / "work/renders").mkdir(parents=True)
        (self.reel / "work/renders/master-fixture.mp4").write_bytes(b"fixture")
        beat = self.send["beats"][0]
        beat["layout"] = "pip"
        original = review.read(self.reel / "motion/reel-good-world/scene.json")
        for style in ("punch-in", "layout-switch"):
            for kind in ("world", "overlay"):
                with self.subTest(style=style, kind=kind):
                    self.send["edit_style"] = {"style": style}
                    self.write("beat-map-selection.json", self.send)
                    spec = dict(original, kind=kind)
                    if kind != "world":
                        for key in ("holds", "area", "caption_band"):
                            spec.pop(key, None)
                    self.write("motion/reel-good-world/scene.json", spec)
                    work = self.reel / f"temp-{style}-{kind}"
                    work.mkdir()
                    with (patch.object(review.sr, "make_env", return_value=({}, work / "net.jsonl")),
                          patch.object(review.sr, "scene_test"),
                          patch.object(review.sr, "probe", return_value={"nb_read_frames": 120}),
                          patch.object(review.sr, "caption_band_ranges", return_value=[]),
                          patch.object(review.sr, "kill_warm"), patch.object(review, "run_media") as media,
                          patch.object(compose, "face_layout", wraps=compose.face_layout) as decision,
                          patch.object(compose, "layout", wraps=compose.layout) as geometry):
                        review.build_media(self.reel, review.entries(self.reel)[0], work)
                    graph = media.call_args_list[-1].args[0]
                    graph = graph[graph.index("-filter_complex") + 1]
                    expected = "pip" if kind == "world" or style == "layout-switch" else "full"
                    decision.assert_called_once()
                    self.assertEqual(decision.call_args.args[1]["style"], style)
                    self.assertEqual(compose.face_layout(beat, self.send["edit_style"], self.reel), expected)
                    if expected == "pip":
                        x, y, w, h = compose.layout(expected, 1)["box"]
                        self.assertIn(f"scale={w}:{h}:force_original_aspect_ratio=increase", graph)
                        self.assertIn(f"[graphic][face]overlay={x}:{y}", graph)
                    else:
                        self.assertNotIn("[graphic][face]overlay=", graph)
                    # Both renderers must resolve their geometry through the shared decision.
                    self.assertIn(unittest.mock.call(expected, 1), geometry.call_args_list)


class PipWorld(unittest.TestCase):
    setUp = world.WorldSceneLayout.setUp
    save_beats = world.WorldSceneLayout.save_beats
    inputs = world.WorldSceneLayout.inputs

    def test_pip_face(self):
        self.spec.update(area="full", caption_band=[1320, 1470])
        review.write_json(self.scene / "scene.json", self.spec)
        self.beats[0].update(start_f=17, end_f=61, layout="pip")
        self.beats[1].update(start_f=61)
        self.beats.insert(0, dict(id="before", start_f=0, end_f=17, layout="full", scene=None,
                                 speech_anchor=dict(text="", w0=0, w1=0)))
        self.save_beats()
        self.track["keys"].append(dict(f=40, scale=1.2, ox=.3, oy=.4, layout="full"))
        self.track["tweens"] = [dict(prop="scale", start_f=8, end_f=90,
            **{"from": 1, "to": 1.3}, ease="power2.inOut", id="crossing punch")]
        review.write_json(self.reel / "work/scale_track.json", self.track)
        ctx = world.placer.load_ctx(self.reel)
        baseline = dict(ctx, world_slots=[])
        x, y, w, h = compose.layout("pip", 1)["box"]
        want = world.placer._map(ctx["median_box"], (x, y, w, h), 1, (.5, .5))
        for frame in range(17, 61):
            self.assertEqual(world.placer.head_box_at(ctx, frame, frame), want)
        for frame in (16, 61):
            self.assertEqual(world.placer.head_box_at(ctx, frame, frame),
                             world.placer.head_box_at(baseline, frame, frame))
        inp = self.inputs()
        old = copy.deepcopy(inp)
        old["beats"][1]["scene"] = None
        before = compose.main_html(old, 1080, 1920, [])
        after = compose.main_html(inp, 1080, 1920, [(self.beats[1], "world")])
        self.assertIn('"data-world-face": "pip"', after)
        self.assertIn(f"translate({x:g}px, {y:g}px) !important; width: {w:g}px !important; height: {h:g}px", after)
        for frame, name in ((17, "pip"), (61, "")):
            self.assertIn(f'"data-world-face": "{name}"', after)
            self.assertTrue(any('"data-world-face"' in line and line.endswith(
                ", " + compose.at(frame, 30) + ");") for line in after.splitlines()))
        def timeline(page):
            return "\n".join(line for line in page.splitlines() if "tl." in line
                             and "#aroll-" in line and "data-world-face" not in line).encode()
        self.assertEqual(timeline(before), timeline(after))
        self.assertNotIn("data-world-face", before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
