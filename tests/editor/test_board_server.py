"""Tests for board_server.py + board_sync.py (S4a). Assert-based, stdlib only, temp folders only.

  <editor python> -X utf8 -I tests/editor/test_board_server.py   (any Python 3.10+ works; exit 0 = every assert held)
"""
import http.client, json, os, shutil, socket, subprocess, sys, tempfile, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills/editor-doctor/scripts"
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
import check_deps  # noqa: E402  (writes editor.config.json the way the doctor does)
import board_server as bs  # noqa: E402
import board_sync  # noqa: E402

SERVER = HERE / "board_server.py"
procs = []


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def server_pid(p):
    """The pid of the live server that p started: p itself, or, on Windows, p's one live child. A Windows venv's
    python.exe is a launcher that re-runs the real interpreter as a child, so there p.pid is not the server."""
    assert p.poll() is None, f"the server process {p.pid} is not running"
    if os.name != "nt":
        return p.pid
    import ctypes
    from ctypes import wintypes

    class Entry(ctypes.Structure):  # PROCESSENTRY32W
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]

    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    k.Process32FirstW.argtypes = k.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(Entry))
    k.CloseHandle.argtypes = (wintypes.HANDLE,)
    snap = k.CreateToolhelp32Snapshot(2, 0)  # TH32CS_SNAPPROCESS: every live process
    assert snap not in (None, ctypes.c_void_p(-1).value), f"couldn't list processes (error {ctypes.get_last_error()})"
    kids, e = [], Entry()
    e.dwSize = ctypes.sizeof(Entry)
    try:
        ok = k.Process32FirstW(snap, ctypes.byref(e))
        while ok:
            # conhost.exe: the console Windows gives p when the test itself runs without one, never the server
            if e.th32ParentProcessID == p.pid and e.szExeFile.lower() != "conhost.exe":
                kids.append(e.th32ProcessID)
            ok = k.Process32NextW(snap, ctypes.byref(e))
    finally:
        k.CloseHandle(snap)
    assert len(kids) <= 1, f"the server process {p.pid} has more than one child process: {kids}"
    return kids[0] if kids else p.pid


def workspace(td, name, port):
    ws = td / name
    check_deps.atomic_write(rt.config_path(ws), json.dumps({"ports": {"board": port}}))
    assert check_deps.write_config(ws, engine=None, nle="none")
    assert rt.read_config(ws)["paths"] == {"editor": "editor", "videos": "videos"}
    (ws / "videos" / "reel-1").mkdir(parents=True)
    return ws


def start(ws, *flags):
    p = subprocess.Popen([sys.executable, "-X", "utf8", "-I", str(SERVER), "--root", str(ws), *flags],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
    procs.append(p)
    t = threading.Timer(20, p.kill)  # a hung start fails the test instead of blocking it
    t.start()
    line = p.stdout.readline().strip()
    t.cancel()
    assert line.startswith("Editor boards: http://127.0.0.1:") and line.endswith("/"), line
    return p, int(line.rsplit(":", 1)[1].rstrip("/"))


def req(port, method, path, body=None, headers=None, host=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
    c.putheader("Host", host or f"127.0.0.1:{port}")
    for k, v in (headers or {}).items():
        c.putheader(k, v)
    if body is not None:
        c.putheader("Content-Length", str(len(body)))
    c.endheaders(body)
    r = c.getresponse()
    out = (r.status, dict(r.getheaders()), r.read())
    c.close()
    return out


def post(port, path, body=b'{"v": 1}', origin="default", ctype="application/json"):
    h = {}
    if origin:
        h["Origin"] = f"http://127.0.0.1:{port}" if origin == "default" else origin
    if ctype:
        h["Content-Type"] = ctype
    return req(port, "POST", path, body, h)


def junction(target, link):
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
    else:
        os.symlink(target, link, target_is_directory=True)


def wait_exit(p, secs):
    try:
        return p.wait(secs)
    except subprocess.TimeoutExpired:
        return None


def server_checks(td):
    port = free_port()
    ws = workspace(td, "ws", port)
    reel = ws / "videos" / "reel-1"
    data = bytes(range(256)) * 4
    (reel / "clip.bin").write_bytes(data)
    (ws / "editor" / "cut-board").mkdir(parents=True)
    (ws / "editor" / "cut-board" / "index.html").write_text("<p>board</p>", encoding="utf-8")
    secret = b"TOP-SECRET-OUTSIDE"
    (td / "secret.txt").write_bytes(secret)
    (ws / "secret.txt").write_bytes(secret)
    p, got = start(ws)
    assert got == port, (got, port)
    info = json.loads((ws / "editor" / ".board-server.json").read_text(encoding="utf-8"))
    assert info["port"] == port and info["url"] == f"http://127.0.0.1:{port}/"
    want = server_pid(p)
    assert info["pid"] == want, f".board-server.json names pid {info['pid']}, but the running server is pid {want}"
    st = f"/videos/reel-1/__state?name=cut-board"

    # Host gate on every request
    assert req(port, "GET", "/videos/reel-1/clip.bin")[0] == 200
    assert req(port, "GET", "/videos/reel-1/clip.bin", host="localhost:%d" % port)[0] == 200
    assert req(port, "GET", "/videos/reel-1/clip.bin", host="evil.example:%d" % port)[0] == 403
    assert req(port, "GET", "/videos/reel-1/clip.bin", host="127.0.0.1:1")[0] == 403
    # POST gates
    assert post(port, st, origin="http://evil.example")[0] == 403, "forged Origin"
    assert post(port, st, origin=f"http://127.0.0.1:{port + 1}")[0] == 403, "other port's Origin"
    assert post(port, st, origin=None)[0] == 403, "missing Origin"
    assert post(port, st, ctype="text/plain")[0] == 403, "text/plain"
    assert post(port, st, ctype=None)[0] == 403, "no Content-Type"
    assert post(port, st, body=b"not json")[0] == 400, "non-JSON body"
    assert post(port, st, body=b"")[0] == 400, "empty body"
    assert post(port, st, body=b"{" + b" " * bs.MAX_BODY + b"}")[0] == 413, "oversized body"
    assert req(port, "PUT", st, b"{}", {"Origin": "http://evil.example", "Content-Type": "application/json"})[0] == 403
    assert not (reel / "cut-board.state.json").exists(), "a refused POST wrote nothing"
    # valid POST: written atomically, one .prev kept
    s, h, b = post(port, st, body=b'{"v": 1}', ctype="application/json; charset=utf-8")
    assert s == 200 and json.loads(b)["ok"], (s, b)
    assert (reel / "cut-board.state.json").read_bytes() == b'{"v": 1}'
    assert post(port, st, body=b'{"v": 2}')[0] == 200
    assert (reel / "cut-board.state.json").read_bytes() == b'{"v": 2}'
    assert (reel / "cut-board.state.json.prev").read_bytes() == b'{"v": 1}'
    assert post(port, st, body=b'{"v": 3}', origin=f"http://localhost:{port}")[0] == 200
    assert (reel / "cut-board.state.json.prev").read_bytes() == b'{"v": 2}', "exactly one .prev, the previous"
    assert not list(reel.glob("*.tmp"))
    s, h, b = req(port, "GET", "/videos/reel-1/cut-board.state.json")
    assert s == 200 and b == b'{"v": 3}' and h.get("Cache-Control") == "no-store", h
    assert post(port, "/videos/no-such-reel/__state?name=cut-board")[0] == 404
    assert not (ws / "videos" / "no-such-reel").exists(), "never creates a reel folder"
    assert post(port, "/videos/reel-1/__state?name=not-a-board")[0] == 403
    assert post(port, "/videos/reel-1/__state?name=../x")[0] == 403
    assert post(port, "/videos/%2e%2e/__state?name=cut-board")[0] in (403, 404)
    # __save: a Send output listed in the board's boards.json "writes"
    sv = "/videos/reel-1/__save?board=cut-board&name=cut-selection.json"
    assert post(port, sv, body=b'{"sent": 1}')[0] == 200
    assert (reel / "cut-selection.json").read_bytes() == b'{"sent": 1}' and not list(reel.glob("*.tmp"))
    assert post(port, sv, origin="http://evil.example")[0] == 403, "forged Origin on __save"
    assert post(port, sv, ctype="text/plain")[0] == 403
    for q in ("board=cut-board&name=other.json", "board=cut-board&name=selection.json", "board=hub&name=selection.json", "board=nope&name=selection.json",
              "board=cut-board&name=../selection.json", "board=cut-board&name=%2e%2e%2fselection.json",
              "board=cut-board&name=sub/selection.json", "board=cut-board&name=.selection.json",
              "board=cut-board&name=.board-version", "name=selection.json", "board=cut-board",
              "board=cut-board&name=selection.json&name=x.json"):
        assert post(port, "/videos/reel-1/__save?" + q)[0] == 403, q
    assert post(port, "/videos/no-such-reel/__save?board=cut-board&name=cut-selection.json")[0] == 404
    assert not (ws / "videos" / "no-such-reel").exists() and (reel / "cut-selection.json").read_bytes() == b'{"sent": 1}'
    assert not (reel / "selection.json").exists(), "no shared selection.json"
    assert post(port, "/videos/reel-1/__nope?name=cut-board")[0] == 404
    # GET only inside whitelisted board folders and reel folders
    assert req(port, "GET", "/editor/cut-board/")[0] == 200
    s, h, _ = req(port, "GET", "/editor/cut-board?reel=reel-1")
    assert s == 301 and h["Location"] == "/editor/cut-board/?reel=reel-1", (s, h)
    refused = ["/editor/not-a-board/index.html", "/editor/editor.config.json", "/editor/.board-server.json",
               "/secret.txt", "/", "/videos/", "/videos/reel-1/", "/videos/reel-1/../../secret.txt",
               "/videos/reel-1/%2e%2e/%2e%2e/secret.txt", "/videos/reel-1/..%2f..%2fsecret.txt",
               "/videos/%2e%2e/secret.txt", "/editor/cut-board/%2e%2e/%2e%2e/secret.txt",
               "/videos/reel-1/..%5c..%5csecret.txt", "/videos/reel-1/.hidden", "/videos/reel-1/missing.bin"]
    for path in refused:
        s, _, b = req(port, "GET", path)
        assert s in (403, 404) and secret not in b, (path, s)
    try:
        os.symlink(td / "secret.txt", reel / "link.txt")
        linked = True
    except (OSError, NotImplementedError) as e:
        linked = False
        print(f"note: symlink escape case skipped, this OS refused to create the link ({e.__class__.__name__})")
    if linked:
        s, _, b = req(port, "GET", "/videos/reel-1/link.txt")
        assert s == 403 and secret not in b, s
    # HTTP Range (video seeking)
    s, h, b = req(port, "GET", "/videos/reel-1/clip.bin", headers={"Range": "bytes=10-19"})
    assert s == 206 and h["Content-Range"] == f"bytes 10-19/{len(data)}" and b == data[10:20], (s, h)
    s, h, b = req(port, "GET", "/videos/reel-1/clip.bin", headers={"Range": "bytes=-5"})
    assert s == 206 and b == data[-5:] and h["Content-Range"] == f"bytes {len(data) - 5}-{len(data) - 1}/{len(data)}"
    s, h, _ = req(port, "GET", "/videos/reel-1/clip.bin", headers={"Range": "bytes=5000-"})
    assert s == 416 and h["Content-Range"] == f"bytes */{len(data)}"
    s, h, b = req(port, "GET", "/videos/reel-1/clip.bin")
    assert s == 200 and h["Accept-Ranges"] == "bytes" and b == data
    # a second start for the same workspace reuses the live server
    p2, port2 = start(ws)
    assert port2 == port and wait_exit(p2, 15) == 0
    p.terminate()
    p.wait(10)
    return 7


def port_busy_checks(td):
    port = free_port()
    ws = workspace(td, "ws-busy", port)
    with socket.socket() as blocker:
        blocker.bind(("127.0.0.1", port))
        blocker.listen(1)
        p, got = start(ws)
        assert got != port, "fell back to a free port"
        info = json.loads((ws / "editor" / ".board-server.json").read_text(encoding="utf-8"))
        assert info["port"] == got and info["url"] == f"http://127.0.0.1:{got}/"
        assert req(got, "GET", "/videos/reel-1/x")[0] == 404
        p.terminate()
        p.wait(10)
    return 1


def idle_checks(td):
    ws = workspace(td, "ws-idle", free_port())
    p, port = start(ws, "--idle", "1.5", "--grace", "60")
    s, _, b = post(port, "/heartbeat", body=b"{}")
    assert s == 200 and json.loads(b)["ok"]
    assert post(port, "/heartbeat", body=b"{}", origin="http://evil.example")[0] == 403
    assert wait_exit(p, 15) == 0, "exits after the idle timeout"
    assert not (ws / "editor" / ".board-server.json").exists(), "removes its info file on exit"
    p, port = start(ws, "--idle", "60", "--grace", "1")
    assert wait_exit(p, 15) == 0, "exits after the start-up grace when no board opens"
    return 2


def sync_checks(td):
    plug = td / "plugin"
    (plug / ".claude-plugin").mkdir(parents=True)
    (plug / ".claude-plugin" / "plugin.json").write_text('{"version": "0.1.0"}', encoding="utf-8")
    for rel in ("skills/editor-doctor/scripts/boards.json", "skills/editor-doctor/assets/board-client.js"):
        (plug / rel).parent.mkdir(parents=True, exist_ok=True)
        (plug / rel).write_bytes((rt.PLUGIN_ROOT / rel).read_bytes())
    tpl = plug / "skills" / "reel-first-cuts" / "boards" / "cut-board"
    (tpl / "lib").mkdir(parents=True)
    (tpl / "index.html").write_bytes(b"<p>v1</p>")
    (tpl / "lib" / "math.js").write_bytes(b"// v1")
    ws = workspace(td, "ws-sync", free_port())
    (ws / "editor" / ".gitignore").write_bytes(b"mine.log")
    (ws / "videos" / ".gitignore").write_bytes(b"raw/")
    notes = board_sync.sync(ws, plug)
    assert "cut-board: copied (your saved work is untouched)" in notes, notes
    assert "sound-board: not built yet, nothing to copy" in notes and len(notes) == 9, notes
    assert not (ws / "editor" / "sound-board").exists()
    gi = (ws / "editor" / ".gitignore").read_bytes()
    assert gi == b"mine.log\n.board-server.json\n*.prev\n*.tmp\n", gi
    gv = (ws / "videos" / ".gitignore").read_bytes()
    assert gv == b"raw/\n*selection.json\n*.state.json\n*.prev\n", gv
    board = ws / "editor" / "cut-board"
    assert (board / "board-client.js").read_bytes() == (rt.PLUGIN_ROOT / "skills/editor-doctor/assets/board-client.js").read_bytes()
    stamp = json.loads((board / ".board-version").read_text(encoding="utf-8"))
    assert stamp["version"] == "0.1.0" and len(stamp["hash"]) == 64
    # a stale copy: old stamp, a state file, its .prev and a user file; the template moved on
    keep = {"cut-board.state.json": b'{"mine": 1}', "cut-board.state.json.prev": b'{"mine": 0}', "my-notes.txt": b"hands off"}
    for n, b in keep.items():
        (board / n).write_bytes(b)
    (board / ".board-version").write_text('{"version": "0.0.1", "hash": "old"}', encoding="utf-8")
    (tpl / "index.html").write_bytes(b"<p>v2</p>")
    old = time.time() - 3600
    for n in keep:
        os.utime(board / n, (old, old))
    before = {n: (board / n).stat().st_mtime_ns for n in keep}
    assert "cut-board: refreshed (your saved work is untouched)" in board_sync.sync(ws, plug)
    assert (board / "index.html").read_bytes() == b"<p>v2</p>" and (board / "lib" / "math.js").read_bytes() == b"// v1"
    for n, b in keep.items():
        assert (board / n).read_bytes() == b and (board / n).stat().st_mtime_ns == before[n], n
    new = json.loads((board / ".board-version").read_text(encoding="utf-8"))
    assert new["version"] == "0.1.0" and new["hash"] != stamp["hash"]
    # a current stamp: nothing rewritten
    files = [f for f in board.rglob("*") if f.is_file()] + [ws / "editor" / ".gitignore"]
    for f in files:
        os.utime(f, (old, old))
    snap = {f: (f.read_bytes(), f.stat().st_mtime_ns) for f in files}
    assert "cut-board: up to date" in board_sync.sync(ws, plug)
    assert {f: (f.read_bytes(), f.stat().st_mtime_ns) for f in files} == snap
    assert sorted(f for f in board.rglob("*") if f.is_file()) == sorted(f for f in files if f.parent != ws / "editor")
    # a link planted in a board copy is skipped with a warning; its target is never written
    victim = td / "victim.txt"
    victim.write_bytes(b"victim")
    (tpl / "app.js").write_bytes(b"// template")
    try:
        os.symlink(victim, board / "app.js")
        os.symlink(td, board / "lib2", target_is_directory=True)
        (tpl / "lib2").mkdir()
        (tpl / "lib2" / "victim.txt").write_bytes(b"// template")
    except (OSError, NotImplementedError) as e:
        print(f"note: board-copy symlink case skipped, this OS refused to create the link ({e.__class__.__name__})")
        return 3
    notes = board_sync.sync(ws, plug)
    assert "⚠ cut-board: skipped app.js, it is a link to somewhere else (left as it is)" in notes, notes
    assert "⚠ cut-board: skipped lib2/victim.txt, it is a link to somewhere else (left as it is)" in notes, notes
    assert victim.read_bytes() == b"victim" and (board / "app.js").is_symlink()
    assert json.loads((board / ".board-version").read_text(encoding="utf-8")) == new, "no re-stamp while a file is skipped"
    (board / "app.js").unlink()
    os.rmdir(board / "lib2") if os.name == "nt" else (board / "lib2").unlink()
    assert "cut-board: refreshed (your saved work is untouched)" in board_sync.sync(ws, plug)
    assert (board / "app.js").read_bytes() == b"// template" and victim.read_bytes() == b"victim"
    ext = td / "outside-board"
    ext.mkdir()
    (ws / "editor" / "tweak-board").symlink_to(ext, target_is_directory=True)
    (plug / "skills/reel-first-cuts/boards/tweak-board").mkdir(parents=True)
    (plug / "skills/reel-first-cuts/boards/tweak-board/index.html").write_bytes(b"x")
    assert "⚠ tweak-board: skipped, its folder is a link to somewhere else (left as it is)" in board_sync.sync(ws, plug)
    assert not list(ext.iterdir())
    return 4


def junction_checks(td):
    """A junction (Windows; a symlink elsewhere) as a board folder or the editor folder: nothing written through it.
    Runs after sync_checks, reusing its fake plugin (cut-board + tweak-board templates)."""
    plug = td / "plugin"
    tpl = plug / "skills/reel-first-cuts/boards/tweak-board"
    tpl.mkdir(parents=True, exist_ok=True)  # sync_checks may have stopped before making it
    (tpl / "index.html").write_bytes(b"x")
    ws = workspace(td, "ws-junction", free_port())
    ext = td / "junction-target"
    ext.mkdir()
    junction(ext, ws / "editor" / "tweak-board")
    notes = board_sync.sync(ws, plug)
    assert "⚠ tweak-board: skipped, its folder is a link to somewhere else (left as it is)" in notes, notes
    assert not list(ext.iterdir()), "nothing written into the junction's target"
    assert "cut-board: copied (your saved work is untouched)" in notes, "a normal board folder still syncs"
    assert (ws / "editor" / "cut-board" / ".board-version").exists()
    ws2 = workspace(td, "ws-junction-editor", free_port())
    real_editor = td / "real-editor"
    shutil.move(str(ws2 / "editor"), str(real_editor))
    junction(real_editor, ws2 / "editor")
    before = sorted(p.name for p in real_editor.iterdir())
    assert board_sync.sync(ws2, plug) == ["⚠ boards: skipped, the editor folder is a link to somewhere else (left as it is)"]
    assert sorted(p.name for p in real_editor.iterdir()) == before, "nothing written into a junctioned editor folder"
    r = subprocess.run([sys.executable, "-X", "utf8", "-I", str(SERVER), "--root", str(ws2)], capture_output=True,
                       text=True, encoding="utf-8", timeout=30)
    assert r.returncode != 0 and r.stdout.strip() == ("✗ Editor boards: the editor folder is a link to somewhere else, "
                                                      "so the boards won't start."), (r.returncode, r.stdout)
    assert sorted(p.name for p in real_editor.iterdir()) == before, "the server wrote nothing into the junction's target"
    return 3


def main():
    ensure_utf8_output()
    n = 0
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        try:
            n += server_checks(td) + port_busy_checks(td) + idle_checks(td) + sync_checks(td) + junction_checks(td)
        finally:
            for p in procs:
                if p.poll() is None:
                    p.kill()
                    p.wait(10)
                p.stdout.close()
    print(f"ok test_board_server.py: {n} check groups passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
