"""Focused offline regressions for install-time guard failures. Python 3.11+, stdlib only."""
import copy, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "py"))
import boxlib, claude_guard, graph_job


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fbx-guard-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.token = "test-long-lived-secret-value"
        self.token_path = self.root / "token"
        self.token_path.write_text(self.token + "\n", encoding="utf-8")
        self.token_path.chmod(0o600)
        self.cfg = copy.deepcopy(boxlib.DEFAULTS)
        self.cfg["root"] = str(self.root)
        self.cfg["claude"].update(bin=sys.executable, token_file=str(self.token_path), retries=12, retry_minutes=5)

    def test_token_env_only_absolute_bin_and_status_note(self):
        self.assertEqual(claude_guard.preflight(self.cfg), [])
        cmd = claude_guard.build_cmd(self.cfg, "SYS")
        self.assertEqual(cmd[0], sys.executable)
        self.assertNotIn(self.token, json.dumps(cmd))
        self.assertEqual(claude_guard.claude_env(self.cfg)["CLAUDE_CODE_OAUTH_TOKEN"], self.token)
        fake = self.root / "fake.py"
        fake.write_text('''import json, os, sys
token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
assert token and token not in " ".join(sys.argv)
print(json.dumps({"type":"system", "subtype":"init", "tools":[], "mcp_servers":[], "model":"haiku"}))
print(json.dumps({"type":"result", "result":"env only", "is_error":False}))
''', encoding="utf-8")
        self.cfg["claude"]["bin"] = [sys.executable, str(fake)]
        with patch.dict(os.environ, {"CLAUDE_CODE_OAUTH_TOKEN": "caller-token", "ANTHROPIC_API_KEY": "caller-key"}):
            self.assertNotIn("ANTHROPIC_API_KEY", claude_guard.claude_env(self.cfg))
            self.assertEqual(claude_guard.run_claude(self.cfg, "SYS", "input")["result"], "env only")
        boxlib.write_status(self.cfg, "graph", True)
        status = (self.root / "status/graph.json").read_text()
        self.assertIn("long-lived token: expiry not checked", status)
        self.assertNotIn(self.token, status)
        self.assertNotIn(str(self.token_path), status)

    def test_permanent_refusals_do_not_retry(self):
        cases = [
            {"token_file": str(self.root / "missing")},
            {"token_file": None, "credentials": str(self.root / "missing")},
            {"bin": str(self.root / "missing")},
            {"bin": "claude"},
            {"model": None},
            {"retries": "bad"},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                cfg = copy.deepcopy(self.cfg)
                cfg["claude"].update(changes)
                with patch.object(claude_guard.time, "sleep") as sleep, patch.object(claude_guard.subprocess, "Popen") as child:
                    with self.assertRaises(claude_guard.GuardRefused) as refusal:
                        claude_guard.wait_ready(cfg, "graph")
                    self.assertEqual(refusal.exception.exit_code, 2)
                    sleep.assert_not_called()
                    child.assert_not_called()
                self.assertNotIn(self.token, (self.root / "status/graph.json").read_text())

    def test_unreadable_token_does_not_retry(self):
        with patch("builtins.open", side_effect=PermissionError), patch.object(boxlib, "write_status"), patch.object(claude_guard.time, "sleep") as sleep:
            with self.assertRaises(claude_guard.GuardRefused) as refusal:
                claude_guard.wait_ready(self.cfg, "graph")
            self.assertEqual(refusal.exception.exit_code, 2)
            sleep.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "POSIX file permissions")
    def test_token_requires_0600(self):
        self.token_path.chmod(0o644)
        with self.assertRaisesRegex(claude_guard.GuardRefused, "0600"):
            claude_guard.preflight(self.cfg)

    def test_transient_refusals_retry(self):
        self.cfg["claude"].update(retries=3, retry_minutes=0)
        with patch.object(claude_guard, "preflight", return_value=["agent_busy=1"]) as checks, patch.object(claude_guard.time, "sleep") as sleep:
            with self.assertRaises(claude_guard.GuardRefused) as refusal:
                claude_guard.wait_ready(self.cfg, "graph")
            self.assertEqual(refusal.exception.exit_code, 1)
            self.assertEqual(checks.call_count, 3)
            self.assertEqual(sleep.call_count, 2)

    def test_guard_and_graph_cli_exit_2_on_permanent_refusal(self):
        self.cfg["claude"]["token_file"] = str(self.root / "missing")
        self.cfg["spokes"] = {"s1": {"folders": ["10-Rules"], "decay": False}}
        (self.root / "spokes" / "s1").mkdir(parents=True, exist_ok=True)
        (self.root / "spokes" / "s1" / "n.md").write_text("---\nstatus: active\n---\nnote\n", encoding="utf-8", newline="\n")
        cfg_file = self.root / "brain.json"
        cfg_file.write_text(json.dumps(self.cfg), encoding="utf-8")
        for module, args in [(claude_guard, ["check"]), (graph_job, [])]:
            with self.subTest(module=module.__name__):
                r = subprocess.run([sys.executable, "-B", module.__file__, *args, "--config", str(cfg_file)], capture_output=True, text=True, timeout=10)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIn("token_file", r.stderr)
                self.assertNotIn(self.token, r.stdout + r.stderr)

    def test_graph_error_line_keeps_full_error_and_exit_code(self):
        error = "fewzhun-box guard: refused: " + "details " * 100 + "end"
        output = error + "\n" + "progress complete\n" * 50
        self.assertEqual(graph_job.error_line(output), error)
        code = "print(" + repr(error) + "); print('progress complete\\n' * 50); raise SystemExit(2)"
        rc, tail, timed_out = claude_guard.run_guarded([sys.executable, "-c", code], boxlib.child_env(), str(self.root), 10)
        self.assertEqual(rc, 2)
        self.assertFalse(timed_out)
        self.assertEqual(graph_job.error_line(tail), error)


if __name__ == "__main__":
    unittest.main(verbosity=2)
