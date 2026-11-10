#!/usr/bin/env python3
"""Portable footage ledger proof; synthetic bytes only, no media tools required.

Run: python -X utf8 -I tests/editor/footage_ledger_test.py
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[2] / "plugins/editor-superengine"
sys.path[:0] = [str(PLUGIN / "skills/reel-canvas-build/scripts"),
               str(PLUGIN / "skills/reel-broll/scripts")]
import compose
import broll_ingest

fc = compose.footage_check
CONTENT = b"the user's own B-roll"
SHA = hashlib.sha256(CONTENT).hexdigest()


class FootageLedgerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="footage-ledger-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.reel = self.root / "original-reel"
        self.clip = self.reel / "broll/ingested/clip.mp4"
        self.clip.parent.mkdir(parents=True)
        self.clip.write_bytes(CONTENT)
        self.ident = fc.add(self.reel, self.clip, "broll", "own", "own")

    def legacy_move(self, with_size=False):
        ledger = fc.rows(self.reel)
        ledger[0]["path"] = str(self.clip)
        if with_size:
            ledger[0]["size"] = len(CONTENT)
        else:
            ledger[0].pop("size", None)  # Real old rows never recorded a size.
        (self.reel / "footage/ledger.json").write_bytes(
            (json.dumps(ledger) + "\n").encode("utf-8"))
        moved = self.root / "renamed-synced-reel"
        self.reel.rename(moved)
        self.reel = moved
        self.clip = moved / "broll/ingested/clip.mp4"

    def uses(self, path="broll/ingested/clip.mp4"):
        return [dict(path=path, src_in_f=0, src_out_f=30)]

    def plan(self):
        clip = {"src": "broll/ingested/clip.mp4", "in": 0, "out": 30,
                "ledger_id": self.ident}
        return {"reel_dir": self.reel, "rate": 30, "total": 300, "cut_frames": [],
                "beats": [{"id": "b_006", "start_f": 90, "end_f": 120, "broll": clip}]}

    def assert_accepted(self):
        before = (self.reel / "footage/ledger.json").read_bytes()
        self.assertEqual(fc.check(self.reel, self.uses()), [])
        # The actual compose beat check; only the media probe uses a test double.
        with patch.object(compose.fpsmod, "frame_count", return_value=30):
            compose.broll_plan(self.plan())
        self.assertEqual(compose.licence_rows.footage(self.plan()), [])
        self.assertEqual((self.reel / "footage/ledger.json").read_bytes(), before)

    def assert_missing(self, message=None):
        message = message or ("This B-roll clip isn't in the reel folder any more: clip.mp4. "
                              "Put it back in the reel's broll folder, or remove it from the Beat Map.")
        self.assertEqual(fc.check(self.reel, self.uses()), [message])
        # No ffprobe call (or traceback) should obscure the useful missing line.
        with patch.object(compose.fpsmod, "frame_count", side_effect=AssertionError("missing clip probed")):
            with self.assertRaises(compose.Stop) as stopped:
                compose.broll_plan(self.plan())
        self.assertIn(message, str(stopped.exception))
        self.assertEqual(stopped.exception.lines, ("BLOCK " + message,))
        self.assertNotIn("matching footage ledger row", str(stopped.exception))
        self.assertNotIn("Traceback", str(stopped.exception))
        work = self.reel / "work"
        work.mkdir()
        (work / "cuts.json").write_bytes(json.dumps({"segments": self.uses()}).encode("utf-8"))
        (work / "probe.json").write_bytes(b'{"input":"broll/ingested/clip.mp4"}')
        result = subprocess.run([sys.executable, "-X", "utf8", "-I", "-B", fc.__file__,
                                 "check", str(self.reel), str(work)],
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout.splitlines(), [message])
        self.assertEqual(result.stderr, "")

    def test_add_inside_writes_relative_posix_path(self):
        row = fc.rows(self.reel)[0]
        self.assertEqual(row["path"], "broll/ingested/clip.mp4")
        self.assertEqual(row["size"], len(CONTENT))
        self.assertEqual(row["sha256"], SHA)

    def test_copy_accepts_its_own_clip_and_compose_beat(self):
        copied = self.root / "copied-reel"
        shutil.copytree(self.reel, copied)
        self.reel = copied
        # A same-named relative path in cwd must not hijack a ledger row.
        previous = Path.cwd()
        try:
            os.chdir(self.root / "original-reel")
            self.assert_accepted()
        finally:
            os.chdir(previous)

    def test_moved_legacy_absolute_row_without_size_passes(self):
        self.legacy_move()
        self.assert_accepted()

    def test_moved_absolute_row_with_size_passes(self):
        self.legacy_move(with_size=True)
        self.assert_accepted()

    def test_deleted_moved_clip_has_one_plain_missing_line(self):
        self.legacy_move()
        self.clip.unlink()
        self.assert_missing()

    def test_same_name_same_size_other_bytes_is_refused(self):
        self.legacy_move()
        self.clip.write_bytes(b"x" * len(CONTENT))
        self.assert_missing("This B-roll clip changed after it was added: clip.mp4. "
                            "Put the original clip back, or remove it from the Beat Map.")

    def test_size_bearing_row_still_requires_matching_sha(self):
        self.legacy_move(with_size=True)
        self.clip.write_bytes(b"x" * len(CONTENT))
        # An unchanged original must not hide changed bytes in the current reel.
        original = Path(fc.rows(self.reel)[0]["path"])
        original.parent.mkdir(parents=True)
        original.write_bytes(CONTENT)
        self.assert_missing("This B-roll clip changed after it was added: clip.mp4. "
                            "Put the original clip back, or remove it from the Beat Map.")

    def test_relative_missing_clip_has_one_plain_missing_line(self):
        self.clip.unlink()
        self.assert_missing()

    def test_external_clip_keeps_absolute_path(self):
        external = self.root / "clip.mp4"
        external.write_bytes(b"external recording")
        ident = fc.add(self.reel, external, "broll", "own", "own")
        self.assertEqual(fc.rows(self.reel)[1]["path"], str(external))
        copied = self.root / "copied-with-external"
        shutil.copytree(self.reel, copied)
        self.reel = copied
        self.assertEqual(fc.check(self.reel, self.uses(str(external))), [])
        self.assertEqual(fc.locate(self.reel, fc.rows(self.reel)[1]), external)
        self.assertEqual(fc.asset(self.reel, str(external)), external)
        self.assertEqual(fc.add(self.reel, external, "broll", "own", "own"), ident)

    def test_existing_absolute_source_prefers_verified_local_clip(self):
        self.legacy_move()
        row = fc.rows(self.reel)[0]
        original = Path(row["path"])
        original.parent.mkdir(parents=True)
        original.write_bytes(CONTENT)
        self.assertEqual(fc.locate(self.reel, row), self.clip)

    def test_copy_with_old_absolute_ledger_accepts_local_clip_and_compose_beat(self):
        ledger = fc.rows(self.reel)
        ledger[0]["path"] = str(self.clip)
        ledger[0].pop("size")
        (self.reel / "footage/ledger.json").write_bytes(json.dumps(ledger).encode("utf-8"))
        copied = self.root / "copied-reel"
        shutil.copytree(self.reel, copied)
        original = self.clip
        self.reel, self.clip = copied, copied / "broll/ingested/clip.mp4"
        self.assertTrue(original.is_file())
        self.assert_accepted()
        self.assertEqual(fc.locate(copied, ledger[0]), self.clip)
        self.assertEqual(fc.asset(copied, original), self.clip)

    def test_stored_absolute_recordings_match_local_licence_rows_and_master(self):
        for copied in (False, True):
            for folder in ("", "raw"):
                for mixed in (False, True):
                    with self.subTest(copied=copied, folder=folder, mixed=mixed):
                        original = self.root / ("source-%s-%s-%s" % (copied, folder, mixed))
                        raw = original / folder / "RAW.mp4"
                        raw.parent.mkdir(parents=True)
                        raw.write_bytes(b"own a-roll recording")
                        fc.add(original, raw, "aroll", "own", "own")
                        ledger = fc.rows(original)
                        ledger[0]["path"] = str(raw)
                        ledger[0].pop("size")
                        (original / "footage/ledger.json").write_bytes(json.dumps(ledger).encode("utf-8"))
                        work = original / "work"
                        work.mkdir()
                        cuts = {"segments": self.uses(str(raw))}
                        if mixed:
                            cuts["takes"] = {"1": {"raw": str(raw)}}
                        (work / "probe.json").write_bytes(json.dumps({"input": str(raw)}).encode("utf-8"))
                        (work / "cuts.json").write_bytes(json.dumps(cuts).encode("utf-8"))
                        local = original.with_name(original.name + "-local")
                        if copied:
                            shutil.copytree(original, local)
                        else:
                            original.rename(local)
                        before = {p.relative_to(local): p.read_bytes() for p in local.rglob("*") if p.is_file()}
                        self.assertEqual(fc.check(local, fc.cut_uses(cuts, str(raw))), [])
                        self.assertEqual(fc.asset(local, raw), local / folder / "RAW.mp4")
                        ctx = {"reel_dir": local, "beats": [], "cuts": cuts}
                        self.assertEqual(compose.licence_rows.footage(ctx), [])
                        compose.footage_licences(ctx, "master")
                        after = {p.relative_to(local): p.read_bytes() for p in local.rglob("*") if p.is_file()}
                        self.assertEqual(after, before)

    def test_missing_unlogged_aroll_uses_recording_wording(self):
        uses = fc.cut_uses({"segments": self.uses()}, str(self.reel / "RAW.mp4"))
        self.assertEqual(fc.check(self.reel, uses), ["this recording is missing: RAW.mp4"])

    def test_old_probe_with_relative_ledger_prefers_local_recording(self):
        raw = self.reel / "raw/RAW.mp4"
        raw.parent.mkdir()
        raw.write_bytes(b"own a-roll")
        fc.add(self.reel, raw, "aroll", "own", "own")
        copied = self.root / "relative-ledger-copy"
        shutil.copytree(self.reel, copied)
        cuts = {"segments": self.uses(str(raw))}
        work = copied / "work"
        work.mkdir()
        (work / "probe.json").write_bytes(json.dumps({"input": str(raw)}).encode("utf-8"))
        self.assertEqual(fc.asset(copied, raw), copied / "raw/RAW.mp4")
        self.assertEqual(compose.licence_rows.footage({"reel_dir": copied, "cuts": cuts, "beats": []}), [])

    def test_recovery_indexes_once_and_hashes_only_name_size_candidates(self):
        for n in range(80):
            (self.reel / ("unrelated-%d.mp4" % n)).write_bytes(CONTENT)
        for name in ("second.mp4", "third.mp4"):
            clip = self.clip.with_name(name)
            clip.write_bytes(name.encode("utf-8"))
            fc.add(self.reel, clip, "broll", "own", "own")
        ledger = fc.rows(self.reel)
        for row in ledger:
            row["path"] = str(self.reel / row["path"])
        (self.reel / "footage/ledger.json").write_bytes(json.dumps(ledger).encode("utf-8"))
        moved = self.root / "many-files-reel"
        self.reel.rename(moved)
        self.reel, self.clip = moved, moved / "broll/ingested/clip.mp4"
        (moved / "clip.mp4").write_bytes(b"wrong size")
        expected = {moved / "broll/ingested" / name for name in ("clip.mp4", "second.mp4", "third.mp4")}
        digest, rglob = fc.digest, Path.rglob
        hashed, scans = [], []

        def candidate_digest(path):
            self.assertIn(Path(path), expected)
            hashed.append(Path(path))
            return digest(path)

        def scan(path, pattern):
            scans.append(path)
            return rglob(path, pattern)

        uses = [dict(path=str(p), src_in_f=0, src_out_f=30) for p in sorted(expected)]
        with patch.object(fc, "digest", side_effect=candidate_digest), patch.object(Path, "rglob", scan):
            self.assertEqual(fc.check(moved, uses), [])
        self.assertEqual(scans, [moved])
        self.assertEqual(set(hashed), expected)
        self.assertLessEqual(len(hashed), 2 * len(expected))

    def test_digest_cache_reuses_bytes_and_invalidates_on_stat_change(self):
        raw_hash = hashlib.sha256
        with patch.object(fc.hashlib, "sha256", wraps=raw_hash) as hashes:
            self.assertEqual(fc.digest(self.clip), SHA)
            self.assertEqual(fc.digest(self.clip), SHA)
            # add() may already have cached these bytes in setUp().
            self.assertLessEqual(hashes.call_count, 1)
            before = self.clip.stat()
            changed = b"z" * len(CONTENT)
            self.clip.write_bytes(changed)
            os.utime(self.clip, ns=(before.st_atime_ns, before.st_mtime_ns + 1000000000))
            self.assertEqual(fc.digest(self.clip), raw_hash(changed).hexdigest())
            self.assertEqual(fc.digest(self.clip), raw_hash(changed).hexdigest())
            self.assertLessEqual(hashes.call_count, 2)

    def test_recovery_filters_name_and_size_and_prefers_relative_tail(self):
        self.legacy_move(with_size=True)
        duplicate = self.reel / "a/clip.mp4"
        duplicate.parent.mkdir()
        duplicate.write_bytes(CONTENT)
        (self.reel / "wrong-name.mp4").write_bytes(CONTENT)
        (self.reel / "clip.mp4").write_bytes(b"short")
        digest = fc.digest

        def candidate_digest(path):
            self.assertEqual(Path(path).name, "clip.mp4")
            self.assertEqual(Path(path).stat().st_size, len(CONTENT))
            return digest(path)

        with patch.object(fc, "digest", side_effect=candidate_digest):
            self.assertEqual(fc.locate(self.reel, fc.rows(self.reel)[0]), self.clip)
        # Re-find even if the user also reorganised the clip inside the reel.
        self.clip.unlink()
        self.assertEqual(fc.locate(self.reel, fc.rows(self.reel)[0]), duplicate)

    def test_ingest_reuse_resolves_moved_legacy_row(self):
        self.legacy_move()
        ledger = fc.rows(self.reel)
        ledger[0].update(origin="ai", job_id="job-1")
        (self.reel / "footage/ledger.json").write_bytes(json.dumps(ledger).encode("utf-8"))
        clip = dict(self.plan()["beats"][0]["broll"], origin="ai", job_id="job-1", request_sha256="request-1")
        (self.reel / "broll/clips.json").write_bytes(json.dumps({"clips": [clip]}).encode("utf-8"))
        self.assertEqual(broll_ingest.reuse(self.reel, "request-1"), 0)


class SameNameTakesTest(unittest.TestCase):
    """Two recordings with one file name: a stored absolute path binds to its own take, never the other."""

    def test_copied_reel_binds_each_stored_take_to_its_own_folder(self):
        with tempfile.TemporaryDirectory(prefix="same-name-") as tmp:
            root = Path(tmp).resolve()
            reel = root / "reel"
            for name, body in (("a", b"take A"), ("b", b"take B")):
                (reel / name).mkdir(parents=True)
                (reel / name / "take.mp4").write_bytes(body)
                fc.add(reel, reel / name / "take.mp4", "aroll", "own", "own")
            copy = root / "copy"
            shutil.copytree(reel, copy)
            self.assertEqual(fc.asset(copy, str(reel / "b/take.mp4")), (copy / "b/take.mp4").resolve())
            self.assertEqual(fc.asset(copy, str(reel / "a/take.mp4")), (copy / "a/take.mp4").resolve())
            shutil.rmtree(reel)
            self.assertEqual(fc.asset(copy, str(reel / "b/take.mp4")), (copy / "b/take.mp4").resolve())
            # A stored path whose folder matches neither take is not guessed.
            stored = reel / "c/take.mp4"
            self.assertEqual(fc.asset(copy, str(stored)), stored)


if __name__ == "__main__":
    unittest.main(verbosity=2)
