"""Kill-and-resume test for S1a's downloader (Setup.download in editor-doctor/scripts/install.py).

usage: python tests/editor/resume_test.py   (stdlib only; needs curl on PATH; exit 0 = pass)
Serves an 8 MB random file on 127.0.0.1 at ~1 MB/s with Range support, kills the download once its
.part passes 30%, re-runs it, and checks the resume asked for exactly the bytes still missing.
S1C_INSTALL_PY=<path> points the test at another install.py (it needs pins.json beside it and ../../_shared).
"""
import hashlib, http.server, os, shutil, signal, subprocess, sys, tempfile, threading, time
from pathlib import Path

INSTALL_PY = os.environ.get("S1C_INSTALL_PY") or str(
    Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills/editor-doctor/scripts/install.py")
SIZE, CHUNK, RATE = 8 << 20, 64 << 10, 1 << 20
DATA = os.urandom(SIZE)
SHA = hashlib.sha256(DATA).hexdigest()
RANGES = []  # Range header of every request, None when absent

CHILD = """import importlib.util, os, sys
spec = importlib.util.spec_from_file_location("install", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.Setup(os.environ["EDITOR_SE_HOME"], "auto").download(sys.argv[2], sys.argv[3], sys.argv[4], "resume test file")
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        rng = self.headers.get("Range")
        RANGES.append(rng)
        start = 0
        if rng:
            start = int(rng.split("=", 1)[1].split("-", 1)[0])
            if start >= SIZE:
                self.send_response(416); self.send_header("Content-Range", f"bytes */{SIZE}"); self.end_headers()
                return
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{SIZE - 1}/{SIZE}")
        else:
            self.send_response(200)
        self.send_header("Content-Length", str(SIZE - start))
        self.end_headers()
        try:
            for i in range(start, SIZE, CHUNK):
                self.wfile.write(DATA[i:i + CHUNK])
                time.sleep(CHUNK / RATE)
        except OSError:  # the client was killed mid-transfer
            pass


def kill_tree(p):
    """Kill the Python child and the curl it started (killing Python alone leaves curl writing the .part)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    else:
        os.killpg(p.pid, signal.SIGKILL)
    p.wait()


def fail(msg):
    print(f"✗ resume test: {msg}")
    return 1


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tmp = Path(tempfile.mkdtemp(prefix="resume-test-"))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/blob.bin"
    dest = tmp / "downloads" / "blob.bin"
    part = dest.with_name(dest.name + ".part")
    env = dict(os.environ, EDITOR_SE_HOME=str(tmp / "state"), NO_PROXY="127.0.0.1", no_proxy="127.0.0.1")
    cmd = [sys.executable, "-X", "utf8", "-I", "-c", CHILD, INSTALL_PY, url, str(dest), SHA]
    try:
        print(f"install.py: {INSTALL_PY}")
        p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             start_new_session=os.name != "nt")
        deadline = time.time() + 60
        while not (part.exists() and part.stat().st_size > SIZE * 0.3):
            if p.poll() is not None:
                return fail(f"the first download ended (exit {p.returncode}) before 30% arrived: {p.stdout.read()!r}")
            if time.time() > deadline:
                kill_tree(p)
                return fail("the .part never passed 30% within 60 s")
            time.sleep(0.05)
        kill_tree(p)
        time.sleep(0.5)
        if not part.exists():
            return fail("the .part file is gone after the kill")
        killed = part.stat().st_size
        print(f"✓ killed the download at {killed:,} of {SIZE:,} bytes; the .part is still there")
        seen = len(RANGES)
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=120)
        if r.returncode != 0:
            return fail(f"the re-run exited {r.returncode}: {(r.stdout + r.stderr).strip()}")
        print(f"requests seen: {RANGES}")
        want = f"bytes={killed}-"
        if not RANGES[seen:] or RANGES[seen] != want:
            return fail(f"the re-run's first request asked for Range {RANGES[seen:seen + 1]}, expected {want!r}")
        print(f"✓ the re-run asked for Range: {want} (resumed, not restarted)")
        if not dest.exists() or hashlib.sha256(dest.read_bytes()).hexdigest() != SHA:
            return fail("the finished file is missing or its sha256 does not match")
        print("✓ the finished file's sha256 matches")
        if part.exists():
            return fail("a .part file was left behind")
        print("✓ no .part left")
        return 0
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
