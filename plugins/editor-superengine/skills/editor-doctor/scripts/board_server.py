"""The editor boards' local server (S4a): one per workspace, stdlib only.

Claude starts it in the background from the client's workspace folder, never the client:
  <editor python> -X utf8 -I board_server.py [--root <workspace>] [--idle 300] [--grace 900]
It copies the boards first (board_sync.py), then prints one line, "Editor boards: http://127.0.0.1:<port>/".
A live server for the same workspace is reused: the line names it and this process exits.

URLs (the same whatever editor.config.json `paths` says; the disk folders come from `paths`):
  GET/HEAD /editor/<board>/<file>          shared board copy, <paths.editor>/<board>/ (boards in boards.json only)
  GET/HEAD /videos/<reel>/<file>           the reel's files, <paths.videos>/<reel>/ (HTTP Range -> 206, for seeking)
  POST     /videos/<reel>/__state?name=<board>   writes <paths.videos>/<reel>/<board>.state.json, one .prev kept
  POST     /videos/<reel>/__save?board=<board>&name=<file>   writes a Send output listed in boards.json "writes"
  POST     /heartbeat                      keeps the server alive; answers {"ok": true, "id": ...}
Every request needs Host 127.0.0.1:<port> or localhost:<port>. Every POST needs the matching Origin and
Content-Type application/json, a JSON body of at most 2 MB, and an existing reel folder (never created).
JSON, HTML and JS are sent with Cache-Control: no-store. Binds 127.0.0.1 only.
It exits on its own after --idle seconds without a heartbeat, or --grace seconds when no board ever opens.
Port: ports.board in editor/editor.config.json (8747), else any free port. <paths.editor>/.board-server.json
names the running server (url, port, pid, id). Exit 1 with a plain "✗ Editor boards: ..." line when it can't start.
"""
import argparse, http.server, json, os, re, secrets, shutil, sys, threading, time, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
import board_sync  # noqa: E402

DEFAULT_PORT = 8747
MAX_BODY = 2 * 1024 * 1024
DRAIN_MAX = 8 * MAX_BODY  # ponytail: bigger bodies are refused unread; the client may then see a reset, not the 413
REEL = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_. -]{0,119}$")
INFO = ".board-server.json"


def inside(path, top):
    a, b = os.path.normcase(path), os.path.normcase(top)
    try:
        return os.path.commonpath([a, b]) == b
    except ValueError:  # different drives
        return False


def safe_reel(reel):
    return bool(REEL.match(reel)) and not reel.endswith((".", " "))


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    # Windows SO_REUSEADDR lets a second socket take a port that is already listening, which would hide a busy port.
    allow_reuse_address = sys.platform != "win32"

    def __init__(self, addr, root, boards, editor_dir, videos_dir):
        super().__init__(addr, Handler)
        self.root, self.boards = root, boards
        self.editor_dir, self.videos_dir = str(editor_dir), str(videos_dir)
        self.id = secrets.token_hex(8)
        self.lock = threading.Lock()  # ponytail: one lock for every state write; per-file locks if boards ever contend
        self.started = self.last_beat = time.monotonic()
        self.beaten = False

    def touch(self):
        self.last_beat, self.beaten = time.monotonic(), True


class Handler(http.server.SimpleHTTPRequestHandler):
    server_version = "EditorBoards/1"
    timeout = 15  # a client that stops sending mid-request can't hold a thread forever
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json",
                      ".html": "text/html", ".css": "text/css", ".svg": "image/svg+xml"}  # Windows registry can say text/plain

    def log_message(self, *args):
        pass

    def end_headers(self):
        # state, config and the pages that read them must never come from the browser cache
        if self.path.split("?")[0].endswith((".json", ".html", ".js", "/")):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    # ---- gates -----------------------------------------------------------------------------------------
    def _allowed(self, name):
        port = self.server.server_address[1]
        ok = {f"127.0.0.1:{port}", f"localhost:{port}"} if name == "Host" else \
             {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}
        vals = self.headers.get_all(name) or []
        return len(vals) == 1 and vals[0] in ok

    def _host_ok(self):
        if self._allowed("Host"):
            return True
        self.send_error(403, "Host must be 127.0.0.1 or localhost on this port")
        return False

    # ---- GET / HEAD --------------------------------------------------------------------------------------
    def do_GET(self):
        if self._host_ok():
            super().do_GET()

    def do_HEAD(self):
        if self._host_ok():
            super().do_HEAD()

    def list_directory(self, path):
        self.send_error(404, "File not found")
        return None

    def _target(self):
        """Real path of an allowed file, or None after the error was sent."""
        raw = self.path.split("?", 1)[0].split("#", 1)[0]
        try:
            p = urllib.parse.unquote(raw, errors="strict")
        except UnicodeDecodeError:
            self.send_error(400, "Bad path")
            return None
        parts = p.split("/")
        if parts[0] != "" or "\\" in p or "\0" in p:
            self.send_error(403, "Forbidden")
            return None
        parts = parts[1:]
        slash = len(parts) > 1 and parts[-1] == ""
        if slash:
            parts = parts[:-1]
        if len(parts) < 2 or any(s == "" or s.startswith(".") or ":" in s for s in parts):
            self.send_error(403, "Forbidden")
            return None
        top, name = parts[0], parts[1]
        if top == "editor" and name in self.server.boards:
            base_top = self.server.editor_dir
        elif top == "videos" and safe_reel(name):
            base_top = self.server.videos_dir
        else:
            self.send_error(403, "Forbidden")
            return None
        real_top = os.path.realpath(base_top)
        real_base = os.path.realpath(os.path.join(base_top, name))
        full = os.path.realpath(os.path.join(base_top, *parts[1:]))
        if not (inside(real_base, real_top) and inside(full, real_base)):  # symlinks resolved, then checked
            self.send_error(403, "Forbidden")
            return None
        if os.path.isdir(full):
            if not slash:
                q = self.path.partition("?")[2]
                self.send_response(301)
                self.send_header("Location", raw + "/" + ("?" + q if q else ""))
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            full = os.path.join(full, "index.html")
        elif slash:
            full = ""
        if not os.path.isfile(full):
            self.send_error(404, "File not found")
            return None
        return full

    def send_head(self):
        path = self._target()
        if path is None:
            return None
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None
        size = os.fstat(f.fileno()).st_size
        rng = self.headers.get("Range")
        if not rng:
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Accept-Ranges", "bytes")  # advertise Range so the browser seeks video with it
            self.send_header("Content-Length", str(size))
            self.end_headers()
            return f
        m = re.match(r"bytes=(\d*)-(\d*)", rng.strip())
        if not m or not (m.group(1) or m.group(2)):
            f.close()
            self.send_error(400, "Malformed Range header")
            return None
        if m.group(1):
            start = int(m.group(1))
            end = min(int(m.group(2)) if m.group(2) else size - 1, size - 1)
        else:  # suffix form: bytes=-N is the LAST n bytes
            start, end = max(0, size - int(m.group(2))), size - 1
        if start >= size or end < start:
            f.close()
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        f.seek(start)
        return _Bounded(f, end - start + 1)

    # ---- POST and other writes ------------------------------------------------------------------------------
    def _read_body(self):
        """The body, or None when it is over MAX_BODY. Always read first, so an early refusal can't reset the socket."""
        try:
            n = max(0, int(self.headers.get("Content-Length") or 0))
        except ValueError:
            n = 0
        if n <= MAX_BODY:
            return self.rfile.read(n)
        while 0 < n <= DRAIN_MAX:
            chunk = self.rfile.read(min(n, 65536))
            if not chunk:
                break
            n -= len(chunk)
        return None

    def _write_gate(self, body):
        if not self._host_ok():
            return False
        if not self._allowed("Origin"):
            self.send_error(403, "Origin must be this board server")
            return False
        if self.headers.get_content_type() != "application/json":
            self.send_error(403, "Content-Type must be application/json")
            return False
        if body is None:
            self.send_error(413, f"Body must be at most {MAX_BODY} bytes")
            return False
        return True

    def _refuse_write(self):
        if self._write_gate(self._read_body()):
            self.send_error(405, "Only POST is supported")

    do_PUT = do_DELETE = do_PATCH = _refuse_write

    def do_POST(self):
        body = self._read_body()
        if not self._write_gate(body):
            return
        try:
            json.loads(body.decode("utf-8"))  # reject anything that is not JSON
        except (UnicodeDecodeError, ValueError):
            self.send_error(400, "Body must be UTF-8 JSON")
            return
        route, _, query = self.path.partition("?")
        if route == "/heartbeat":
            self.server.touch()
            return self._json({"ok": True, "id": self.server.id})
        parts = urllib.parse.unquote(route).split("/")
        if len(parts) != 4 or parts[:2] != ["", "videos"] or parts[3] not in ("__state", "__save"):
            self.send_error(404, "No such endpoint")
            return
        q = urllib.parse.parse_qs(query, keep_blank_values=True)
        one = {k: v[0] for k, v in q.items() if len(v) == 1}
        boards = self.server.boards
        if parts[3] == "__state":  # ?name=<board>  ->  <board>.state.json, one .prev kept
            ok = set(q) == {"name"} == set(one) and one["name"] in boards
            fname, keep_prev = one.get("name", "") + ".state.json", True
        else:  # ?board=<board>&name=<file>  ->  <file>, a Send output listed in that board's boards.json "writes"
            fname, keep_prev = one.get("name", ""), False
            ok = (set(q) == {"board", "name"} == set(one) and one["board"] in boards
                  and fname in boards[one["board"]].get("writes", [])
                  and not fname.startswith(".") and not any(c in fname for c in "/\\:") and ".." not in fname)
        if not ok or not safe_reel(parts[2]):
            self.send_error(403, "board and name must be listed in boards.json and the reel one plain folder name")
            return
        real_top = os.path.realpath(self.server.videos_dir)
        folder = os.path.realpath(os.path.join(self.server.videos_dir, parts[2]))
        if not inside(folder, real_top) or os.path.normcase(folder) == os.path.normcase(real_top) or not os.path.isdir(folder):
            self.send_error(404, "No such reel folder")
            return
        dest = os.path.join(folder, fname)
        if os.path.islink(dest):
            self.send_error(403, "Forbidden")
            return
        with self.server.lock:
            with open(dest + ".tmp", "wb") as fh:
                fh.write(body)
            if keep_prev and os.path.exists(dest):  # copy, so a crash between steps never leaves the board without a state file
                shutil.copyfile(dest, dest + ".prev.tmp")
                os.replace(dest + ".prev.tmp", dest + ".prev")
            os.replace(dest + ".tmp", dest)  # atomic: a crash never leaves half a file
        self.server.touch()
        self._json({"ok": True, "wrote": f"videos/{parts[2]}/{fname}", "bytes": len(body)})

    def _json(self, obj):
        msg = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)


class _Bounded:
    """Wraps a file so copyfile() stops after the requested slice."""

    def __init__(self, fh, remaining):
        self.fh, self.remaining = fh, remaining

    def read(self, n=-1):
        if self.remaining <= 0:
            return b""
        if n is None or n < 0 or n > self.remaining:
            n = self.remaining
        data = self.fh.read(n)
        self.remaining -= len(data)
        return data

    def close(self):
        self.fh.close()


def live_server(info_path):
    """URL of a running server for this workspace (proved by its heartbeat id), else None."""
    try:
        info = json.loads(info_path.read_text(encoding="utf-8"))
        base = f"http://127.0.0.1:{int(info['port'])}"
        req = urllib.request.Request(base + "/heartbeat", data=b"{}", method="POST",
                                     headers={"Origin": base, "Content-Type": "application/json"})
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=3) as r:  # never a proxy
            return info["url"] if json.loads(r.read()).get("id") == info["id"] else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def watchdog(httpd, idle, grace):
    while True:
        time.sleep(0.25)
        now = time.monotonic()
        if (httpd.beaten and now - httpd.last_beat > idle) or (not httpd.beaten and now - httpd.started > grace):
            httpd.shutdown()
            return


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="the client's workspace folder (default: cwd)")
    ap.add_argument("--idle", type=float, default=300, help="seconds without a heartbeat before it stops")
    ap.add_argument("--grace", type=float, default=900, help="seconds to wait for the first heartbeat")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    try:
        editor_dir, videos_dir = board_sync.workspace_paths(root)
        boards = board_sync.load_manifest()
        if not board_sync.is_real(editor_dir):  # never bind or write through a link or junction
            print(f"✗ Editor boards: the {editor_dir.name} folder is a link to somewhere else, so the boards won't start.", flush=True)
            return 1
        board_sync.sync(root)
    except (OSError, ValueError, KeyError) as e:
        print(f"✗ Editor boards: couldn't prepare the boards: {e}", flush=True)
        return 1
    info_path = editor_dir / INFO
    url = live_server(info_path)
    if url:
        print(f"Editor boards: {url}", flush=True)
        return 0
    try:
        port = int((rt.read_config(root).get("ports") or {}).get("board") or DEFAULT_PORT)
        if not 0 < port < 65536:
            port = DEFAULT_PORT
    except (TypeError, ValueError):
        port = DEFAULT_PORT
    try:
        try:
            httpd = Server(("127.0.0.1", port), root, boards, editor_dir, videos_dir)
        except OSError:  # busy: any free port
            httpd = Server(("127.0.0.1", 0), root, boards, editor_dir, videos_dir)
    except OSError as e:
        print(f"✗ Editor boards: couldn't open a local port: {e}", flush=True)
        return 1
    port = httpd.server_address[1]
    url = f"http://127.0.0.1:{port}/"
    tmp = info_path.with_name(INFO + ".tmp")
    tmp.write_text(json.dumps({"url": url, "port": port, "pid": os.getpid(), "id": httpd.id}) + "\n", encoding="utf-8")
    os.replace(tmp, info_path)
    print(f"Editor boards: {url}", flush=True)
    threading.Thread(target=watchdog, args=(httpd, a.idle, a.grace), daemon=True).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        try:
            if json.loads(info_path.read_text(encoding="utf-8")).get("id") == httpd.id:
                info_path.unlink()
        except (OSError, ValueError):
            pass
    print("Editor boards stopped: no board was open.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
