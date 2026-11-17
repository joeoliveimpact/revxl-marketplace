"""No-render proof of the single shared heavy-job lock."""
import ast
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from fractions import Fraction
from unittest.mock import patch

P = Path(__file__).resolve().parents[2] / "plugins/editor-superengine"
sys.path.insert(0, str(P / "skills/_shared"))
try:
    import heavy_job as hj
except ModuleNotFoundError:
    hj = None

FREE_RAM_MB = hj.free_ram_mb if hj else None


def shipped_lock_modules(root):
    paths = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))):
            # Match path components, including f-string fragments, without treating
            # dependency manifests (*.lock.txt) or threading.Lock as file locks.
            lock_path = (isinstance(node, ast.Constant) and isinstance(node.value, str)
                         and (re.search(r"\.lock(?:$|[/\\])", node.value)
                              or "locks" in node.value.replace("\\", "/").split("/")))
            name = (node.id if isinstance(node, ast.Name) else
                    node.attr if isinstance(node, ast.Attribute) else
                    node.name if isinstance(node, ast.alias) else "")
            if lock_path or name in ("O_EXCL", "CREATE_NEW", "locking", "flock"):
                paths.append(path.relative_to(root).as_posix())
                break
    return paths


class HeavyJobTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(hj, "The shared heavy-job module is missing")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        for mock in (patch.dict(os.environ, EDITOR_SE_HOME=str(self.home)),
                     patch.object(hj, "free_ram_mb", return_value=8192),
                     patch.object(hj.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(
                         40 * 2**30, 20 * 2**30, 20 * 2**30))):
            mock.start()
            self.addCleanup(mock.stop)
        self.lock = self.home / "locks/heavy.lock"

    def stale(self):
        # An actual exited process, rather than a guessed unused pid.
        proc = subprocess.Popen([sys.executable, "-I", "-c", "pass"])
        proc.wait(timeout=10)
        self.lock.parent.mkdir(exist_ok=True)
        self.lock.write_text(json.dumps(dict(pid=proc.pid, label="crashed job", started=0)), encoding="utf-8")

    def test_metadata_home_override_and_cleanup_on_error(self):
        with self.assertRaisesRegex(RuntimeError, "render failed"):
            with hj.heavy_job("Preview"):
                data = json.loads(self.lock.read_text())
                self.assertEqual(data["pid"], os.getpid())
                self.assertEqual(data["label"], "Preview")
                self.assertGreater(data["started"], 0)
                raise RuntimeError("render failed")
        self.assertFalse(self.lock.exists())
        self.assertEqual(list(self.lock.parent.iterdir()), [])

    def test_next_job_starts_while_old_waiter_handle_is_still_open(self):
        observer = None
        try:
            with hj.heavy_job("First"):
                observer = hj._open_lock(self.lock, create=False)
            # Windows unlink defers deletion while this handle is open. Retirement
            # must free the lock's name immediately so the next job can create it.
            with hj.heavy_job("Second"):
                self.assertEqual(json.loads(self.lock.read_text())["label"], "Second")
        finally:
            if observer is not None:
                observer.close()

    def test_second_job_waits_and_announces_first_label_once(self):
        held, release, done = threading.Event(), threading.Event(), threading.Event()
        errors = []

        def first():
            try:
                with hj.heavy_job("First preview"):
                    held.set()
                    if not release.wait(5):
                        raise RuntimeError("Test did not release first job")
            except BaseException as error:
                errors.append(error)

        def second():
            try:
                with hj.heavy_job("Master"):
                    done.set()
            except BaseException as error:
                errors.append(error)

        with contextlib.redirect_stdout(io.StringIO()) as said:
            owner = threading.Thread(target=first)
            waiter = threading.Thread(target=second)
            owner.start()
            self.assertTrue(held.wait(3))
            waiter.start()
            try:
                self.assertFalse(done.wait(1), "Second job entered while the first held the lock")
            finally:
                release.set()
                owner.join(5)
                waiter.join(5)
        self.assertFalse(owner.is_alive() or waiter.is_alive())
        self.assertEqual(errors, [])
        self.assertTrue(done.is_set())
        self.assertEqual(said.getvalue().splitlines(), [
            "Another editor job is running (First preview); yours is queued and starts when it finishes."])
        self.assertFalse(self.lock.exists())

    def test_queue_waits_for_owner_metadata_before_announcing_label(self):
        created, initialize, queued = threading.Event(), threading.Event(), threading.Event()
        release = threading.Event()
        original = hj._open_lock
        errors = []

        class Output(io.StringIO):
            def write(self, text):
                if text.startswith("Another editor job"):
                    queued.set()
                return super().write(text)

        def slow_create(path, create):
            stream = original(path, create)
            if create and not created.is_set():
                created.set()
                initialize.wait(3)
            return stream

        def worker(label):
            try:
                with hj.heavy_job(label):
                    if label == "First preview":
                        release.wait(3)
            except BaseException as error:
                errors.append(error)

        with (patch.object(hj, "_open_lock", side_effect=slow_create),
              contextlib.redirect_stdout(Output()) as said):
            first = threading.Thread(target=worker, args=("First preview",))
            second = threading.Thread(target=worker, args=("Master",))
            first.start()
            self.assertTrue(created.wait(3))
            second.start()
            try:
                announced_too_soon = queued.wait(.2)
                initialize.set()
                self.assertTrue(queued.wait(3))
            finally:
                initialize.set()
                release.set()
                first.join(5)
                second.join(5)
        self.assertFalse(announced_too_soon, "Queued before the owner published its label")
        self.assertEqual(errors, [])
        self.assertEqual(said.getvalue().splitlines(), [
            "Another editor job is running (First preview); yours is queued and starts when it finishes."])

    def test_dead_pid_clears_and_proceeds(self):
        self.stale()
        with hj.heavy_job("Recovered"):
            self.assertEqual(json.loads(self.lock.read_text())["label"], "Recovered")
        self.assertEqual(list(self.lock.parent.iterdir()), [])

    def test_legacy_mb5_dead_pid_clears(self):
        self.stale()
        pid = json.loads(self.lock.read_text())["pid"]
        self.lock.write_text(str(pid) + "\n")
        with hj.heavy_job("Recovered"):
            self.assertEqual(json.loads(self.lock.read_text())["label"], "Recovered")

    def test_crash_before_metadata_is_recovered(self):
        self.lock.parent.mkdir()
        self.lock.touch()
        os.utime(self.lock, (1, 1))
        with hj.heavy_job("Recovered"):
            self.assertEqual(json.loads(self.lock.read_text())["label"], "Recovered")

    def test_nested_trial_render_keeps_one_lock_and_outer_label(self):
        with hj.heavy_job("Trial reels"):
            original = self.lock.read_bytes()
            inode = self.lock.stat().st_ino
            with hj.heavy_job("Preview"):
                self.assertEqual(self.lock.read_bytes(), original)
                self.assertEqual(self.lock.stat().st_ino, inode)
            self.assertTrue(self.lock.exists())
        self.assertFalse(self.lock.exists())

    def test_ram_and_disk_refusals(self):
        for ram, disk, message in ((2048, 20, "3 GB free RAM"), (3071, 20, "3 GB free RAM"),
                                   (3072, 9, "10 GB free disk")):
            with (self.subTest(message=message),
                  patch.object(hj, "free_ram_mb", return_value=ram),
                  patch.object(hj.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(
                      40 * 2**30, (40 - disk) * 2**30, disk * 2**30)),
                  self.assertRaises(hj.HeavyJobError) as error):
                with hj.heavy_job("Refused"):
                    self.fail("Resource refusal did not stop the job")
            self.assertIn(message, str(error.exception))
            self.assertEqual(len(str(error.exception).splitlines()), 1)
            self.assertFalse(self.lock.exists())

    def test_darwin_vm_stat_counts_free_and_inactive_pages(self):
        # Includes active/speculative pages to catch accidentally counting all RAM.
        for size, expected in ((4096, 3072), (16384, 12288)):
            output = (f"Mach Virtual Memory Statistics: (page size of {size} bytes)\n"
                      "Pages free:                               262144.\n"
                      "Pages active:                             900000.\n"
                      "Pages inactive:                           524288.\n"
                      "Pages speculative:                        100000.\n")
            with (self.subTest(size=size), patch.object(hj.sys, "platform", "darwin"),
                  patch("subprocess.check_output", return_value=output)):
                # setUp replaces the reader for the lock tests; call the real reader here.
                self.assertEqual(FREE_RAM_MB(), expected)

    def test_darwin_unreadable_memory_proceeds_and_warns_once(self):
        for failure in (OSError("vm_stat unavailable"), subprocess.CalledProcessError(1, "vm_stat"),
                        subprocess.TimeoutExpired("vm_stat", 5)):
            with (self.subTest(failure=type(failure).__name__), patch.object(hj.sys, "platform", "darwin"),
                  patch("subprocess.check_output", side_effect=failure),
                  patch.object(hj, "free_ram_mb", FREE_RAM_MB),
                  contextlib.redirect_stdout(io.StringIO()) as said):
                self.assertIsNone(hj.free_ram_mb())
                with hj.heavy_job("Trial reels"):
                    with hj.heavy_job("Preview"):
                        self.assertEqual(json.loads(self.lock.read_text())["label"], "Trial reels")
            self.assertEqual(said.getvalue().splitlines(), ["Couldn't read free memory; going ahead."])
            self.assertFalse(self.lock.exists())

    def test_darwin_malformed_vm_stat_is_unknown(self):
        for output in ("not vm_stat", "Mach Virtual Memory Statistics: (page size of 4096 bytes)\n"):
            with (self.subTest(output=output), patch.object(hj.sys, "platform", "darwin"),
                  patch("subprocess.check_output", return_value=output)):
                self.assertIsNone(FREE_RAM_MB())

    def test_memory_first_becomes_unknown_in_nested_render_warns_once(self):
        with (patch.object(hj, "free_ram_mb", side_effect=[8192, 8192, None, None]),
              contextlib.redirect_stdout(io.StringIO()) as said):
            with hj.heavy_job("Trial reels"):
                for _ in range(2):
                    with hj.heavy_job("Preview"):
                        self.assertTrue(self.lock.exists())
        self.assertEqual(said.getvalue().splitlines(), ["Couldn't read free memory; going ahead."])

    def test_linux_free_memory_reader(self):
        with (patch.object(hj.sys, "platform", "linux"),
              patch.object(hj.os, "sysconf", create=True,
                           side_effect=lambda key: {"SC_AVPHYS_PAGES": 1048576, "SC_PAGE_SIZE": 4096}[key])):
            self.assertEqual(FREE_RAM_MB(), 4096)

    @unittest.skipUnless(sys.platform == "win32", "Windows memory API")
    def test_windows_free_memory_reader(self):
        import ctypes

        def memory_status(pointer):
            pointer._obj.avail_phys = 5 * 2**30
            return 1

        with patch.object(ctypes.windll.kernel32, "GlobalMemoryStatusEx", side_effect=memory_status):
            self.assertEqual(FREE_RAM_MB(), 5120)

    def test_unknown_memory_keeps_compose_at_one_worker(self):
        sys.path.insert(0, str(P / "skills/reel-canvas-build/scripts"))
        import compose
        for gpu in (False, True):
            self.assertEqual(compose.master_budget(None, gpu)[0], 1)

    def test_resources_rechecked_after_queue(self):
        queued = threading.Event()
        errors, entered = [], []

        class Output(io.StringIO):
            def write(self, text):
                if text.startswith("Another editor job"):
                    queued.set()
                return super().write(text)

        def waiter():
            try:
                with hj.heavy_job("Queued"):
                    entered.append(True)
            except BaseException as error:
                errors.append(error)

        with (patch.object(hj, "free_ram_mb", return_value=8192) as ram,
              contextlib.redirect_stdout(Output())):
            with hj.heavy_job("First"):
                thread = threading.Thread(target=waiter)
                thread.start()
                self.assertTrue(queued.wait(3))
                ram.return_value = 3071
            thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(entered, [])
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], hj.HeavyJobError)
        self.assertIn("3 GB free RAM", str(errors[0]))
        self.assertFalse(self.lock.exists())

    def test_timeout_after_two_hours_keeps_owner_lock(self):
        self.lock.parent.mkdir()
        data = json.dumps(dict(pid=os.getpid(), label="Still running", started=1))
        self.lock.write_text(data)
        with (patch.object(hj.time, "monotonic", side_effect=[0, 60, 7199, 7200]),
              patch.object(hj.time, "sleep") as sleep,
              contextlib.redirect_stdout(io.StringIO()) as said,
              self.assertRaises(hj.HeavyJobError) as error):
            with hj.heavy_job("Queued"):
                self.fail("Timed-out job entered")
        self.assertEqual(sleep.call_count, 2)
        self.assertTrue(all(call.args[0] > 0 for call in sleep.call_args_list))
        self.assertIn("2 hours", str(error.exception))
        self.assertEqual(len(str(error.exception).splitlines()), 1)
        self.assertEqual(len(said.getvalue().splitlines()), 1)
        self.assertEqual(self.lock.read_text(), data)

    def test_two_stale_waiters_never_remove_fresh_lock(self):
        for _ in range(8):
            self.stale()
            both_open = threading.Barrier(2)
            original = hj._open_lock
            rename = Path.rename
            local = threading.local()
            rename_started = threading.Event()
            errors, entered = [], []
            active = 0
            counter = threading.Lock()

            def racing_open(path, create):
                stream = original(path, create)
                if not create and not getattr(local, "opened", False):
                    local.opened = True
                    both_open.wait(timeout=3)
                return stream

            def delayed_rename(path, target):
                # Pause after the first stale identity check. Without the inode
                # guard, the other waiter can replace it with a fresh live lock.
                if path == self.lock and not rename_started.is_set():
                    rename_started.set()
                    time.sleep(.1)
                return rename(path, target)

            def worker(label):
                nonlocal active
                try:
                    with hj.heavy_job(label):
                        with counter:
                            active += 1
                            self.assertEqual(active, 1, "Heavy jobs overlapped")
                        entered.append(label)
                        time.sleep(.15)
                        self.assertEqual(json.loads(self.lock.read_text())["label"], label,
                                         "A stale waiter removed the fresh lock")
                        with counter:
                            active -= 1
                except BaseException as error:
                    errors.append(error)

            with (patch.object(hj, "_open_lock", side_effect=racing_open),
                  patch.object(Path, "rename", delayed_rename),
                  contextlib.redirect_stdout(io.StringIO())):
                workers = [threading.Thread(target=worker, args=(label,)) for label in ("A", "B")]
                for thread in workers:
                    thread.start()
                for thread in workers:
                    thread.join(5)
            self.assertFalse(any(thread.is_alive() for thread in workers))
            self.assertEqual(errors, [])
            self.assertCountEqual(entered, ["A", "B"])
            self.assertFalse(self.lock.exists())

    def test_one_shipped_lock_and_all_renderers_import_it(self):
        for path in P.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            data = path.read_bytes().replace(b"\\", b"/")
            self.assertNotIn(b"C:/Work/_scratch", data, str(path))
        self.assertEqual(shipped_lock_modules(P), ["skills/_shared/heavy_job.py"])
        for relative in ("reel-canvas-build/scripts/compose.py", "reel-canvas-build/scripts/motion_review.py",
                         "reel-trials/scripts/trials.py"):
            self.assertIn("from heavy_job import", (P / "skills" / relative).read_text())

    def test_one_lock_guard_rejects_renamed_compose_lock_mutants(self):
        relative = "skills/reel-canvas-build/scripts/compose.py"
        shared = "skills/_shared/heavy_job.py"
        root = self.home / "plugin"
        for name in (relative, shared):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(P / name, root / name)
        original = (root / relative).read_text(encoding="utf-8")
        mutants = ('other = rt.state_dir() / "locks" / "compose.lock"',
                   'other = Path("compose.lock")',
                   'other = os.path.join(rt.state_dir(), "locks", "compose.pid")',
                   'other = Path("locks/compose.pid")',
                   'other = os.O_EXCL', 'other = CREATE_NEW',
                   'msvcrt.locking(fd, 1, 1)', 'fcntl.flock(fd, 2)')
        for mutant in mutants:
            with self.subTest(mutant=mutant):
                (root / relative).write_bytes((original + "\n" + mutant + "\n").encode("utf-8"))
                self.assertEqual(shipped_lock_modules(root), [shared, relative])

    def test_trials_entry_keeps_queue_visible_and_reuses_lock(self):
        sys.path.insert(0, str(P / "skills/reel-trials/scripts"))
        import trials

        held, release = threading.Event(), threading.Event()
        errors = []

        def owner():
            try:
                with hj.heavy_job("Master"):
                    held.set()
                    release.wait(3)
            except BaseException as error:
                errors.append(error)

        def render(reel, only, status):
            self.assertEqual(json.loads(self.lock.read_text())["label"], "Trial reels")
            with trials.compose.heavy_job("Preview"):
                self.assertEqual(json.loads(self.lock.read_text())["label"], "Trial reels")
            return {"versions": []}

        thread = threading.Thread(target=owner)
        with contextlib.redirect_stdout(io.StringIO()) as said:
            thread.start()
            self.assertTrue(held.wait(3))
            timer = threading.Timer(.3, release.set)
            timer.start()
            try:
                with patch.object(trials, "render", side_effect=render):
                    self.assertEqual(trials.main(["render", "--reel-dir", str(self.home)]), 0)
            finally:
                release.set()
                timer.join(3)
                thread.join(3)
        self.assertEqual(errors, [])
        self.assertEqual(said.getvalue().splitlines(), [
            "Another editor job is running (Master); yours is queued and starts when it finishes.",
            "0 trial versions ready."])
        self.assertFalse(self.lock.exists())

    def test_compose_locks_preview_and_master_after_planning(self):
        sys.path.insert(0, str(P / "skills/reel-canvas-build/scripts"))
        import compose
        sys.path.insert(0, str(P / "skills/reel-captions/scripts"))
        import captions

        class AtRender(Exception):
            pass

        def plan(*args, **kwargs):
            self.assertFalse(self.lock.exists(), "Cheap planning took the heavy-job lock")
            return []

        def render_boundary(*args, **kwargs):
            self.assertEqual(json.loads(self.lock.read_text())["pid"], os.getpid())
            raise AtRender()

        for tier in ("preview", "master"):
            with self.subTest(tier=tier), contextlib.ExitStack() as stack:
                inp = dict(beats=[], scened=[], fps="30", rate=Fraction(30), total=30,
                           hook_f=0, hooks=[], hook_text="", master=self.home / "cut.mp4")
                for target, name, options in (
                        (compose, "load_inputs", dict(return_value=inp)),
                        (compose, "probe_inputs", {}),
                        (compose.styles, "plan", dict(return_value=dict(warnings=[], spans=[]))),
                        (compose, "plan", dict(side_effect=plan)),
                        (compose, "qa_pre_or_stop", {}),
                        (compose, "ok_problem", dict(return_value=None)),
                        (compose, "placement_hooks", dict(return_value=[])),
                        (compose, "hook_captions", {}),
                        (compose, "footage_licences", {}),
                        (captions, "plan", dict(return_value=dict(chunks=[], notes=[]))),
                        (captions, "write", {}),
                        (compose, "choose_audio", dict(return_value=("cut", self.home / "cut.mp4"))),
                        (compose.rt, "hyperframes_env", dict(return_value={})),
                        (compose, "write_omitted_scene_boxes", dict(side_effect=render_boundary))):
                    stack.enter_context(patch.object(target, name, **options))
                media = stack.enter_context(patch.object(compose, "hf_render"))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                with self.assertRaises(AtRender):
                    compose.render(self.home, tier, None)
                media.assert_not_called()
                self.assertFalse(self.lock.exists(), "Render failure left the lock behind")


if __name__ == "__main__":
    unittest.main(verbosity=2)
