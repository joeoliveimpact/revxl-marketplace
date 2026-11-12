"""FN-2b replacement contracts, using real temporary reel files (stdlib only)."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] /
          "plugins/editor-superengine/skills/reel-canvas-build/scripts/make_beat_map.py")
SPEC = importlib.util.spec_from_file_location("make_beat_map", SCRIPT)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
schema = builder.beat_schema


def put(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8"))


class KeepPicks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.reel = Path(self.tmp.name) / "demo"
        (self.reel / "work").mkdir(parents=True)
        self.words = "Three big wins today We grew forty percent Please sign up now".split()
        put(self.reel / schema.DEFAULT_WORDS, {"words": [
            {"word": w, "start": i * 0.5, "end": i * 0.5 + 0.4}
            for i, w in enumerate(self.words)]})
        put(self.reel / "work/cuts.json", {"fps": 30, "segments": [{"out_out_f": 180}]})
        self.plan = {"beats": [
            {"w0": 0, "w1": 3, "layout": "full", "value": 3},
            {"w0": 4, "w1": 7, "layout": "split"},
            {"w0": 8, "w1": 11, "layout": "stack"}]}
        self.planf = self.reel / "work/plan.json"
        self.out = self.reel / builder.OUT_NAME
        self.invoke(replace=False)

    def invoke(self, replace=True):
        put(self.planf, self.plan)
        args = ["--reel-dir", str(self.reel), "--plan", str(self.planf)]
        if replace:
            args.append("--replace")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = builder.main(args)
        self.assertEqual(code, 0, buf.getvalue())
        doc = json.loads(self.out.read_text(encoding="utf-8"))
        schema.validate_beat_map(doc, self.words)
        self.assertTrue(buf.getvalue().splitlines()[-1].startswith("✓ Beat map ready:"))
        self.assertNotIn(b"\r", self.out.read_bytes())
        return doc, buf.getvalue()

    def picks(self, indexes=(0,)):
        doc = json.loads(self.out.read_text(encoding="utf-8"))
        for i in indexes:
            beat = doc["beats"][i]
            beat.update(scene={"id": "callout", "slots": {"text": "Keep this"}},
                        broll={"src": "broll/own.mp4", "in": 0,
                               "out": beat["end_f"] - beat["start_f"], "fit": "cover", "ledger_id": "f01"},
                        transition={"type": "fade", "edge": "in", "at_cut_frame": None, "dur_frames": 3},
                        layout="pip", value=9)
            doc["notes"][beat["id"]] = "Please keep this note"
        doc["sent_at"] = "2026-11-01T12:00:00Z"
        schema.validate_beat_map(doc, self.words)
        put(self.out, doc)
        return doc

    def test_K1_same_plan_keeps_all_picks(self):
        old = self.picks()
        before = self.out.read_bytes()
        doc, said = self.invoke()
        self.assertEqual(doc["beats"][0], old["beats"][0])
        self.assertEqual(doc["notes"], old["notes"])
        self.assertEqual(doc["proposed"]["b_001"]["layout"], "full")
        self.assertEqual(doc["proposed"]["b_001"]["value"], 3)
        self.assertIsNone(doc["sent_at"])
        self.assertEqual((self.reel / builder.PREV_NAME).read_bytes(), before)
        self.assertEqual(said.splitlines()[:-1], ["Kept your picks on 1 of 1 beats."])

    def test_K2_changed_words_report_each_lost_pick(self):
        old = self.picks((0, 1))
        self.plan["beats"][1]["w1"] = 6
        doc, said = self.invoke()
        self.assertEqual(doc["beats"][0], old["beats"][0])
        self.assertIsNone(doc["beats"][1]["scene"])
        self.assertIn("Kept your picks on 1 of 2 beats.", said)
        for name in ("B-roll", "scene", "transition", "layout", "number", "note"):
            self.assertTrue(any(name.lower() in line.lower() and '"We grew forty percent"' in line
                                and "words changed" in line for line in said.splitlines()), said)
        self.assertNotIn("b_00", said)

    def test_K3_changed_duration_only_drops_broll(self):
        old = self.picks()
        self.plan["beats"][1]["w0"] = 5
        doc, said = self.invoke()
        self.assertIsNone(doc["beats"][0]["broll"])
        self.assertEqual(doc["beats"][0]["scene"], old["beats"][0]["scene"])
        self.assertEqual(doc["notes"], old["notes"])
        self.assertIn("B-roll", said)
        self.assertIn("different length", said)

    def test_K4_absent_plan_marks_keep_only_matched_words(self):
        old = json.loads(self.out.read_text())
        old["word_marks"] = [{"w": 1, "mark": "key"}, {"w": 7, "mark": "emph"}]
        put(self.out, old)
        self.plan["beats"][1]["w1"] = 6
        doc, said = self.invoke()
        self.assertEqual(doc["word_marks"], [{"w": 1, "mark": "key"}])
        self.assertIn('"percent"', said)
        self.assertIn("mark", said.lower())

    def test_K4_explicit_plan_marks_win_and_report_old_marks(self):
        old = json.loads(self.out.read_text())
        old["word_marks"] = [{"w": 1, "mark": "key"}, {"w": 7, "mark": "emph"}]
        put(self.out, old)
        self.plan["word_marks"] = [{"w": 1, "mark": "key"}, {"w": 8, "mark": "cta"}]
        doc, said = self.invoke()
        self.assertEqual(doc["word_marks"], self.plan["word_marks"])
        self.assertIn('"percent"', said)
        self.assertIn("new plan", said)
        self.assertNotIn('"big"', said)

    def test_K5_unreadable_old_document_keeps_backup_and_reports(self):
        for bad in (b"{broken", b"[]", b"null", b"\xff", b"[" * 3000 + b"]" * 3000):
            with self.subTest(old=bad[:20], length=len(bad)):
                self.out.write_bytes(bad)
                _, said = self.invoke()
                self.assertEqual((self.reel / builder.PREV_NAME).read_bytes(), bad)
                self.assertEqual(len(said.splitlines()), 2, said)
                self.assertIn("old picks could not be read", said.lower())

    def test_K6_document_choices_are_carried(self):
        old = json.loads(self.out.read_text())
        choices = {"edit_style": {"style": "punch-in"}, "caption_style": {"style": "clean"},
                   "transitions": {"allowed": ["fade"], "sfx_pair": False},
                   "cta_reminder": {"at_s": 4, "hold_s": 1, "gain": 1, "keyword": "GO"},
                   "holds": [{"at_f": 40, "reason": "Let it land"}],
                   "loops": [{"question": "How?", "on_screen": "How?", "setup_f": 0,
                              "updates_f": [30], "closure_f": 90, "closure_words": "We grew", "cta_f": 150}]}
        old.update(choices)
        schema.validate_beat_map(old, self.words)
        put(self.out, old)
        doc, _ = self.invoke()
        for key, value in choices.items():
            self.assertEqual(doc.get(key), value, key)

    def test_K7_first_build_and_refusal_are_unchanged(self):
        self.assertFalse((self.reel / builder.PREV_NAME).exists())
        before = self.out.read_bytes()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = builder.main(["--reel-dir", str(self.reel), "--plan", str(self.planf)])
        self.assertEqual(code, 1)
        self.assertIn(builder.REFUSE, buf.getvalue())
        self.assertEqual(self.out.read_bytes(), before)
        self.assertFalse((self.reel / builder.PREV_NAME).exists())

    def test_plan_defaults_change_and_notes_follow_renumbered_beats(self):
        old = self.picks((1,))
        self.plan["beats"][0].update(layout="stack", value=40)
        self.plan["beats"].insert(1, {"w0": 1, "w1": 2, "layout": "overlay"})
        doc, said = self.invoke()
        self.assertEqual((doc["beats"][0]["layout"], doc["beats"][0]["value"]), ("stack", 40))
        self.assertEqual(doc["notes"], {"b_003": old["notes"]["b_002"]})
        self.assertEqual(doc["beats"][2]["scene"], old["beats"][1]["scene"])
        self.assertNotIn("Couldn't keep", said)

    def test_deleted_beat_reports_all_picks(self):
        self.picks((1,))
        del self.plan["beats"][1]
        _, said = self.invoke()
        self.assertIn("no longer exists", said)
        self.assertEqual(sum("Couldn't keep" in line for line in said.splitlines()), 6)

    def test_invalid_values_roll_back_individually(self):
        old = self.picks()
        old["beats"][0]["scene"] = {"id": "callout", "slots": {"text": 42}}
        old["edit_style"] = "invalid"
        old["notes"]["b_001"] = 42
        put(self.out, old)
        doc, said = self.invoke()
        self.assertIsNone(doc["beats"][0]["scene"])
        self.assertEqual(doc["beats"][0]["broll"], old["beats"][0]["broll"])
        self.assertNotIn("edit_style", doc)
        self.assertEqual(doc["notes"], {})
        for name in ("scene", "editing style", "note"):
            self.assertIn(name, said)
        self.assertNotIn("edit_style", said)
        self.assertNotIn("b_001", said)

    def test_matching_text_and_overlay_kind_must_agree(self):
        for change in ("text", "overlay"):
            with self.subTest(change=change):
                old = self.picks()
                if change == "text":
                    old["beats"][0]["speech_anchor"]["text"] = "Different words were here"
                else:
                    old["beats"][0]["layout"] = "overlay"
                put(self.out, old)
                doc, said = self.invoke()
                self.assertIsNone(doc["beats"][0]["scene"])
                self.assertIn("Couldn't keep", said)
                reason = "the beat's words changed" if change == "text" else "the beat's layout type changed"
                self.assertIn(reason, said)
                if change == "overlay":
                    self.assertNotIn("the beat's words changed", said)

    def test_document_beat_keys_remap_and_missing_references_report(self):
        old = json.loads(self.out.read_text())
        old["edit_style"] = {"beats": {"b_002": {"scale": 1.1}}}
        old["needs"] = "Please add a chart"
        put(self.out, old)
        self.plan["beats"].insert(1, {"w0": 1, "w1": 2, "layout": "overlay"})
        doc, said = self.invoke()
        self.assertEqual(doc.get("edit_style"), {"beats": {"b_003": {"scale": 1.1}}})
        self.assertEqual(doc["needs"], "Please add a chart")
        self.assertNotIn("Couldn't keep", said)
        del self.plan["beats"][2]
        doc, said = self.invoke()
        self.assertNotIn("edit_style", doc)
        self.assertIn("editing style", said)
        self.assertNotIn("edit_style", said)
        self.assertIn("no longer exists", said)

    def test_empty_old_needs_stays_empty_without_a_warning(self):
        doc, said = self.invoke()
        self.assertEqual(doc["needs"], "")
        self.assertNotIn("Couldn't keep", said)

    def test_gap_mark_kept_only_when_every_old_beat_matches(self):
        self.plan["beats"][0]["w1"] = 1
        old, _ = self.invoke()
        mark = {"w": 2, "mark": "emph"}
        old["word_marks"] = [mark]
        put(self.out, old)
        doc, said = self.invoke()
        self.assertEqual(doc["word_marks"], [mark])
        self.assertNotIn("Couldn't keep", said)
        self.plan["beats"][1]["w1"] = 6
        doc, said = self.invoke()
        self.assertEqual(doc["word_marks"], [])
        self.assertIn('mark on "wins"', said)
        self.assertIn("words changed", said)

    def test_gap_mark_outside_word_list_is_reported(self):
        old = json.loads(self.out.read_text())
        old["word_marks"] = [{"w": 12, "mark": "emph"}]
        put(self.out, old)
        doc, said = self.invoke()
        self.assertEqual(doc["word_marks"], [])
        self.assertIn("Couldn't keep your mark", said)

    def test_document_choices_use_plain_names_and_document_reasons(self):
        for key, name, value in (
                ("edit_style", "editing style", []),
                ("caption_style", "caption look", {"beats": {"b_002": {}}}),
                ("loops", "open loops", "invalid"),
                ("transitions", "transition settings", {"allowed": ["invalid"]}),
                ("cta_reminder", "keyword reminder", {}),
                ("holds", "holds", [{}]),
                ("needs", "note to Claude", 42)):
            with self.subTest(choice=key):
                self.invoke()
                old = json.loads(self.out.read_text())
                old[key] = value
                put(self.out, old)
                original_beats = self.plan["beats"]
                self.plan["beats"] = [original_beats[0], original_beats[-1]]
                try:
                    doc, said = self.invoke()
                finally:
                    self.plan["beats"] = original_beats
                self.assertIn(f"Couldn't keep your {name}:", said)
                if key != "holds":
                    self.assertNotIn(f"your {key}:", said)
                self.assertNotIn("for this beat", said)
                if key == "needs":
                    self.assertEqual(doc["needs"], "")
                else:
                    self.assertNotIn(key, doc)

    def test_unreadable_anchor_is_named_a_beat(self):
        for text in ("", "   ", None):
            with self.subTest(text=text):
                old = self.picks()
                old["beats"][0]["speech_anchor"]["text"] = text
                put(self.out, old)
                _, said = self.invoke()
                self.assertIn("Couldn't keep your scene on a beat:", said)
                self.assertNotIn('on ""', said)

    def test_invalid_old_marks_do_not_drop_valid_marks(self):
        old = json.loads(self.out.read_text())
        old["word_marks"] = [{"w": 1, "mark": "key"}, {"w": 2, "mark": "invalid"}]
        put(self.out, old)
        doc, said = self.invoke()
        self.assertEqual(doc["word_marks"], [{"w": 1, "mark": "key"}])
        self.assertIn('"wins"', said)
        self.assertIn("mark", said)


if __name__ == "__main__":
    unittest.main(verbosity=2)
