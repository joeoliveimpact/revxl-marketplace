#!/usr/bin/env python3
"""report_to_joe.py - send a scrubbed client report to Joe's REVXL relay, or keep it locally.

Standard library only. Claude runs it from a skill in a non-interactive shell:
  python report_to_joe.py draft --plugin P --plugin-version V --summary S (--body-file F | --body-stdin)
                                [--client-label L] [--error-code C] [--local-dir D]
  python report_to_joe.py send <draft.json> [--local-dir D]   # the client said Send
  python report_to_joe.py skip <draft.json>                   # the client said Skip
  python report_to_joe.py --selftest                          # offline checks, never the real relay

Exit codes: 0 sent or skipped, 2 usage error, 3 saved locally (not sent).
The REVXL Vault key (env VAULT_API_KEY, else ~/.config/revxl/vault_api_key) only ever goes
into the x-api-key header. It is never printed, logged, or written to a file.
Relay contract: output/orchestrator-mode/09.26.26/phase-1/RELAY.md
"""
import argparse, hashlib, json, os, re, string, sys, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOCAL_DIR = "higgsfield/reports"  # the only plugin-specific line: other plugins change this
VAULT_KEY_FILE = ".config/revxl/vault_api_key"  # relative to HOME
KEY_FILES = [VAULT_KEY_FILE, ".config/openrouter/api_key"]  # scrubbed from reports; other plugins extend this list
RELAY_URL = "https://n8n.engineforimpact.com/webhook/revxl-client-report"  # env REVXL_RELAY_URL overrides
TIMEOUT = 90  # RELAY.md: a 502/503 can take ~70 s
USER_AGENT = "revxl-report/0.1"  # Cloudflare blocks the default Python-urllib User-Agent
BODY_MAX = 51200
MARKER = "\n\n…[truncated by report_to_joe.py]"
LIMITS = {"plugin": 64, "plugin_version": 32, "summary": 200, "body": None,
          "client_label": 100, "error_code": 64, "created_at": 64}
REQUIRED = ("plugin", "plugin_version", "summary", "body")
HOME = Path.home()      # the selftest points this at a temp dir
USE_REGISTRY = True     # also scan the Windows user environment, like hf_rest.py's creds()
RED = "[REDACTED]"
# PAT only as a whole _-separated word: plain "contains PAT" would also match PATH, HOMEPATH, CUDA_PATH ...
SECRET_NAME = re.compile(r"(KEY|SECRET|TOKEN|PASSWORD|PASS)$|API_KEY|CREDENTIAL|WEBHOOK|AUTH|PRIVATE"
                         r"|(^|_)PAT(_|$)|(^|_)KEY(_|$)", re.I)  # KEY as a whole word anywhere, e.g. HF_KEY_ID
VAULT_KEY_SHAPE = re.compile(r"vk_[A-Za-z0-9_-]{8,}")
FRAG_FROM, FRAG_MIN = 24, 16  # live values >= 24 chars: any >= 16-char piece of them is redacted too
_COLON = r"(?::|%3A)"         # id/secret separator, plain or URL-encoded
_HEX = r"(?<![0-9a-f])[0-9a-f]{24,}(?![0-9a-f])"  # hex-only lookarounds: \b fails next to _, \n escapes, non-ASCII


def _id_secret(id_rx):
    """<id>:<secret>. The secret must be >= 32 chars with a digit (HF secrets are 64 hex); whitespace at the
    colon only when it is hex. So "<uuid>:insufficient_credits" and "Key settings:aspect_ratio_16_9" survive.
    A live, configured key stays covered by the exact-value and fragment rules."""
    return (id_rx + r"(?:" + _COLON + r"(?=[a-z_\-]*[0-9])[a-z0-9_\-]{32,}"
            + r"|\s*" + _COLON + r"\s*(?=[a-f]*[0-9])[0-9a-f]{32,})")


# Left boundary for token prefixes (sk-, gh*_, eyJ): not glued to a letter/digit, so slugs like task-/whisk-/
# highs_ survive. A preceding escape still counts as a boundary: JSON/repr \n \r \t, URL %XX, PowerShell `n `t,
# and \uXXXX. Accepted misses: sk- right after a word ("mykeysk-...") looks exactly like a slug.
_LB = r"(?:(?<![a-z0-9])|(?<=\\[nrt])|(?<=%[0-9a-f]{2})|(?<=`[nt])|(?<=\\u[0-9a-f]{4}))"
_LB_JWT = _LB.replace("(?<![a-z0-9])", r"(?<![a-z0-9_\-])")  # JWT: also no _ or -, so it can't restart in a run
PATTERNS = [(re.compile(p, re.I), r) for p, r in (
    # header forms: keep the header name, drop the value (hf_rest.py sends "Authorization: Key id:secret")
    (r"(authorization[\"']?\s*[:=]\s*[\"']?)[^\"'\r\n]+", r"\1" + RED),
    (r"((?:x-api-key|x-n8n-api-key|hf-api-key|hf-secret)[\"']?\s*[:=]\s*[\"']?)[^\"'\s]+", r"\1" + RED),
    (_id_secret(r"(?<![a-z])Key(?:\s+|%20)[a-z0-9_\-]{8,}"), RED),  # Key <id>:<secret>
    (_id_secret(r"\b[0-9a-z]{8}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{12}"), RED),  # HF <uuid>:<secret>
    (_HEX, RED),  # bare hex run: an HF secret (64) or its wrapped continuation; git SHAs / sha256 go too (fail-safe)
    (r"Bearer\s+[^\s\"']+", RED),
    (r"vk_[a-z0-9_\-]{8,}", RED),
    (_LB + r"sk-[a-z0-9_\-]{16,}", RED),
    (_LB + r"(?:gh[posur]_|github_pat_)[a-z0-9_]{16,}", RED),  # GitHub tokens
    # JWT (e.g. an n8n API key). Boundary + bounded segments keep it linear (was quadratic on "eyJeyJeyJ...")
    (_LB_JWT + r"eyJ[a-z0-9_\-]{7,4093}\.[a-z0-9_\-]{10,4096}\.[a-z0-9_\-]{10,4096}", RED),
)]
_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)  # length-preserving lower()


def key_files():
    return [HOME / p for p in KEY_FILES]


def _registry_env():
    """Windows user environment (HKCU\\Environment), the same fallback hf_rest.py's creds() uses."""
    items = {}
    if os.name != "nt":
        return items
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            i = 0
            while True:
                try:
                    name, val, _ = winreg.EnumValue(k, i)
                except OSError:
                    break
                items[name] = val
                i += 1
    except OSError:
        pass
    return items


def _env_items():
    items = dict(os.environ)
    if USE_REGISTRY:
        for n, v in _registry_env().items():
            items.setdefault(n, v)
    return items


def _secret_values():
    vals = {v.strip() for n, v in _env_items().items() if isinstance(v, str) and SECRET_NAME.search(n)}
    for f in key_files():
        try:
            txt = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        vals.add(txt.strip())
        vals.update(txt.split())  # each line of a key file broken across lines
    return sorted((v for v in vals if len(v) >= 8), key=len, reverse=True)  # longest first


def _redact_fragments(text, values):
    """Redact every >= FRAG_MIN-char piece of each live value >= FRAG_FROM chars (e.g. a secret split
    across two lines). ASCII case-insensitive."""
    low, hit = text.translate(_ASCII_LOWER), bytearray(len(text))
    windows = {v[i:i + FRAG_MIN] for v in (x.translate(_ASCII_LOWER) for x in values if len(x) >= FRAG_FROM)
               for i in range(len(v) - FRAG_MIN + 1)}
    for w in windows:
        j = low.find(w)
        while j != -1:
            hit[j:j + FRAG_MIN] = b"\x01" * FRAG_MIN
            j = low.find(w, j + 1)
    if not any(hit):
        return text
    out, i = [], 0
    for m in re.finditer(rb"\x01+", bytes(hit)):
        out += [text[i:m.start()], RED]
        i = m.end()
    return "".join(out) + text[i:]


def scrub(text, secrets=None):
    # patterns FIRST: replacing a live id first would break the "Key <id>:<secret>" shape and let the secret through
    for rx, rep in PATTERNS:
        text = rx.sub(rep, text)
    secrets = _secret_values() if secrets is None else secrets
    for v in secrets:
        text = text.replace(v, RED)
    return _redact_fragments(text, secrets)


def cut16(s, mx):
    """Cut to mx UTF-16 code units (the relay is JavaScript), never splitting a surrogate pair."""
    n = 0
    for i, ch in enumerate(s):
        n += 2 if ord(ch) > 0xFFFF else 1
        if n > mx:
            return s[:i]
    return s


def clean(raw):
    """Scrub + cut, repeated until nothing changes, so a draft is a fixpoint and send's re-clean never alters
    what the client approved. Each pass scrubs BEFORE it cuts, so a cut can't leave half a key unredacted."""
    secrets = _secret_values()
    out = _clean_once(_precut(raw), secrets)
    for _ in range(10):  # normally stable after 1-2 passes; a pass can only add redactions or trim
        nxt = _clean_once(out, secrets)
        if nxt == out:
            break
        out = nxt
    return out


def _precut(raw):
    """Runtime cap: hard-cut every field at 4x its limit before any scrubbing, then back off to the last
    whitespace so no half token (half a key) is left at the cut. The normal scrub-then-cut still runs after."""
    out = dict(raw)
    for f, mx in LIMITS.items():
        v = raw.get(f)
        if not isinstance(v, str):
            continue
        if mx:
            cut = cut16(v, 4 * mx)
        elif len(v.encode("utf-8")) > 4 * BODY_MAX:
            cut = v.encode("utf-8")[:4 * BODY_MAX].decode("utf-8", "ignore")
        else:
            continue
        if cut != v:
            ws = max(cut.rfind(c) for c in " \t\r\n")
            cut = cut[:ws] if ws > 0 else cut  # ponytail: one 4x-limit token with no whitespace is kept as cut
            out[f] = cut + (MARKER if not mx else "")
    return out


def _clean_once(raw, secrets):
    out = {}
    for f, mx in LIMITS.items():
        v = raw.get(f)
        if v is None or str(v) == "":
            continue
        v = scrub(str(v), secrets)
        if mx:
            v = cut16(v, mx)
        elif len(v.encode("utf-8")) > BODY_MAX:
            room = BODY_MAX - len(MARKER.encode("utf-8"))
            v = v.encode("utf-8")[:room].decode("utf-8", "ignore") + MARKER  # "ignore" drops a split char
        out[f] = v
    return out


def vault_key():
    key = (os.environ.get("VAULT_API_KEY") or "").strip()
    if not key:
        try:
            key = (HOME / VAULT_KEY_FILE).read_text(encoding="utf-8").strip()
        except (OSError, UnicodeDecodeError):
            key = ""
    return key or None


def write_new(folder, stem, suffix, text):
    """Create a new file; never overwrite (adds -1, -2, ...)."""
    folder.mkdir(parents=True, exist_ok=True)
    i = 0
    while True:
        p = folder / f"{stem}{f'-{i}' if i else ''}{suffix}"
        try:
            with open(p, "x", encoding="utf-8", newline="\n") as f:
                f.write(text)
            return p.resolve()
        except FileExistsError:
            i += 1


def safe_name(s, n):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s)[:n].strip(" .") or "report"


def fingerprint(key):
    return f"{hashlib.sha256(key.encode('utf-8')).hexdigest()[:8]} (first 8 hex of the key's SHA-256)"


def save_local(payload, local_dir, reason, fp, now=None):
    """fp: fingerprint(key), "(no key)" or "(malformed key)". reason is scrubbed here too."""
    now = now or datetime.now()  # local time (the relay uses America/New_York)
    reason = scrub(reason)
    text = (f"# {payload['summary']}\n\n"
            f"- **Plugin:** {payload['plugin']} {payload['plugin_version']}\n"
            f"- **Client:** {payload.get('client_label') or '(not given)'}\n"
            f"- **Key fingerprint:** {fp}\n"
            f"- **Error code:** {payload.get('error_code') or '(none)'}\n"
            f"- **Created at (client):** {payload.get('created_at') or '(not given)'}\n"
            f"- **Not sent because:** {reason}\n\n---\n\n{payload['body']}\n")
    stem = f"{now:%Y-%m-%d %H%M} - {safe_name(payload['plugin'], 40)} - {safe_name(payload['summary'], 60)}"
    return write_new(Path(local_dir), stem, ".md", text)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None  # following a redirect would forward x-api-key to another URL; a 3xx is a failure


def post(payload, key):
    """Return (response_dict, None) on success, or (None, reason). Reasons never contain the key."""
    req = urllib.request.Request(
        os.environ.get("REVXL_RELAY_URL") or RELAY_URL, method="POST",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"X-Revxl-Report": "v1", "x-api-key": key, "Content-Type": "application/json",
                 "User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=TIMEOUT) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        err = ""
        try:
            err = str(json.loads(e.read().decode("utf-8")).get("error") or "")[:64]
        except Exception:
            pass
        tail = " (redirect not followed)" if 300 <= e.code < 400 else ""
        return None, f"HTTP {e.code}{' ' + err if err else ''}{tail}"
    except urllib.error.URLError as e:  # OS error text only (e.g. "No connection could be made ...")
        r = e.reason
        detail = f": {r.strerror}" if isinstance(r, OSError) and r.strerror else ""
        return None, f"no connection ({type(r).__name__}{detail})"
    except Exception as e:  # timeout, reset, bad header value ... type name only: the message may echo a header
        return None, f"request failed ({type(e).__name__})"
    if status != 200:
        return None, f"HTTP {status} (expected 200)"
    try:
        data = json.loads(raw.decode("utf-8"))
    except ValueError:
        return None, "HTTP 200 but the response was not JSON"
    if not (isinstance(data, dict) and data.get("ok") is True):
        return None, "HTTP 200 but ok was not true"
    return data, None


def missing(payload):
    return [f for f in REQUIRED if not payload.get(f, "").strip()]


def cmd_draft(a):
    if a.body_stdin:
        body = sys.stdin.buffer.read().decode("utf-8", "replace")
    else:
        try:
            body = Path(a.body_file).read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"ERROR: cannot read body file: {e}", file=sys.stderr)
            return 2
    payload = clean({"plugin": a.plugin, "plugin_version": a.plugin_version, "summary": a.summary,
                     "body": body, "client_label": a.client_label, "error_code": a.error_code,
                     "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    if missing(payload):
        print(f"ERROR: empty required field(s): {', '.join(missing(payload))}", file=sys.stderr)
        return 2
    slug = re.sub(r"[^a-z0-9]+", "-", payload["summary"].lower()).strip("-")[:40] or "report"
    try:
        path = write_new(Path(a.local_dir) / "drafts", f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{slug}",
                         ".json", json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    except OSError as e:  # e.g. a reports path past the Windows 260-character limit: one line, no traceback
        print(f"ERROR: cannot write the draft ({type(e).__name__}). Check the reports folder is writable and its "
              "path is not near the Windows 260-character limit. Nothing was sent.", file=sys.stderr)
        return 2
    print(f"DRAFT: {path}")
    print("----- PREVIEW: exactly what would be sent to Joe -----")
    print(f"Plugin: {payload['plugin']} {payload['plugin_version']}")
    print(f"Summary: {payload['summary']}")
    print(f"Client: {payload.get('client_label', '(not given)')}")
    print(f"Error code: {payload.get('error_code', '(none)')}")
    print(f"Created at: {payload['created_at']}")
    print(f"Body:\n{payload['body']}")
    print("----- END PREVIEW -----")
    print(f'NEXT: show this preview to the client and ask Send or Skip. Then run '
          f'`report_to_joe.py send "{path}"` or `report_to_joe.py skip "{path}"`.')
    return 0


def _load_draft(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, ValueError) as e:
        print(f"ERROR: cannot read draft: {e}", file=sys.stderr)
        return None
    print("ERROR: draft is not a JSON object", file=sys.stderr)
    return None


def cmd_send(a):
    raw = _load_draft(a.draft)
    if raw is None:
        return 2
    payload = clean(raw)  # re-scrub: defence in depth
    if payload != raw:  # a draft from `draft` is a fixpoint, so this means it was edited or the env changed
        print("NOTICE: the send-time re-scrub changed the approved draft; sending the more-redacted version.")
    if missing(payload):
        print(f"ERROR: draft has empty required field(s): {', '.join(missing(payload))}", file=sys.stderr)
        return 2
    key = vault_key()
    if not key:
        data, reason, fp = None, "no vault key", "(no key)"
    elif not VAULT_KEY_SHAPE.fullmatch(key):  # e.g. a line break inside it; never put it in a header
        data, reason, fp = None, "vault key malformed", "(malformed key)"
    else:
        (data, reason), fp = post(payload, key), fingerprint(key)
    if data:
        print(f"SENT: {data.get('name', '(no name)')} (Drive id {data.get('id', '?')})")
        Path(a.draft).unlink()
        return 0
    reason = scrub(reason)
    path = save_local(payload, a.local_dir, reason, fp)  # save before deleting the draft
    print(f"SAVED LOCALLY: {path}")
    print(f"Reason: {reason}")
    Path(a.draft).unlink()
    return 3


def cmd_skip(a):
    try:
        Path(a.draft).unlink()
    except OSError as e:
        print(f"ERROR: cannot delete draft: {e}", file=sys.stderr)
        return 2
    print("SKIPPED (nothing sent, nothing kept)")
    return 0


def main(argv):
    if argv[:1] == ["--selftest"]:
        return selftest()
    ap = argparse.ArgumentParser(prog="report_to_joe.py", description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true", help="run offline checks")
    sub = ap.add_subparsers(dest="cmd")
    d = sub.add_parser("draft")
    d.add_argument("--plugin", required=True)
    d.add_argument("--plugin-version", required=True)
    d.add_argument("--summary", required=True)
    g = d.add_mutually_exclusive_group(required=True)
    g.add_argument("--body-file")
    g.add_argument("--body-stdin", action="store_true")
    d.add_argument("--client-label")
    d.add_argument("--error-code")
    d.add_argument("--local-dir", default=DEFAULT_LOCAL_DIR)
    s = sub.add_parser("send")
    s.add_argument("draft")
    s.add_argument("--local-dir", default=DEFAULT_LOCAL_DIR)
    k = sub.add_parser("skip")
    k.add_argument("draft")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.cmd:
        ap.print_help()
        return 2
    return {"draft": cmd_draft, "send": cmd_send, "skip": cmd_skip}[a.cmd](a)


def selftest():
    """Offline: temp dirs, a fake HOME, fake keys, a local http.server. Never the real key or relay."""
    import contextlib, io, socket, tempfile, threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    global HOME, USE_REGISTRY
    USE_REGISTRY = False
    for n in list(os.environ):  # drop real secrets from this process only, so nothing real is read
        if SECRET_NAME.search(n) or n == "REVXL_RELAY_URL":
            del os.environ[n]
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"
    tmp = Path(tempfile.mkdtemp(prefix="rtj-selftest-"))
    HOME, empty_home, reports = tmp / "home", tmp / "empty-home", tmp / "reports"
    empty_home.mkdir()
    VAULT, FILE_VAULT = "vk_selftestVAULTenv0123456789abcdef", "vk_selftestVAULTfile9876543210zyx"
    OR_FILE = "sk-or-v1-selftestFILEopenrouter0123456789"
    env = {"HF_API_KEY_ID": "0f8e2a1c-3b4d-4e5f-8a9b-0c1d2e3f4a5b",
           "HF_API_KEY_SECRET": hashlib.sha256(b"selftest").hexdigest(),
           "N8N_API_KEY": "n8nFakeApiKeyValue12345", "OPENROUTER_API_KEY": "sk-or-v1-selftestENVor0123456789ab",
           "VAULT_API_KEY": VAULT, "MY_TOKEN": "shortTokenPrefix12",
           "MY_LONG_SECRET": "shortTokenPrefix12EXTRA99", "DB_PASSWORD": "hunter2hunter2"}
    os.environ.update(env)
    for f, v in zip(key_files(), (FILE_VAULT, OR_FILE)):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(v + "\n", encoding="utf-8")
    uuid2, sec2 = "22222222-3333-4444-5555-666666666666", "bee5" * 16  # R4: id:secret needs a digit
    planted = ["vk_patternOnlyVault12345", "sk-patternOnlyOpenAI1234567890", "Bearer bearerPatternTok.en123",
               "Key 11111111-2222-3333-4444-555555555555:" + "c0ffee" * 8, f"{uuid2}:{sec2}",
               "Authorization: Key hfidPatternOnly1:hfsecretPatternOnly1234", "x-api-key: customApiKeyNoPrefix99"]
    leaks = list(env.values()) + [FILE_VAULT, OR_FILE, "vk_patternOnlyVault12345", "sk-patternOnlyOpenAI1234567890",
             "bearerPatternTok.en123", "11111111-2222-3333-4444-555555555555", "c0ffee" * 8, uuid2, sec2,
             "hfidPatternOnly1", "hfsecretPatternOnly1234", "customApiKeyNoPrefix99", "EXTRA99"]

    state = {"mode": "200", "seen": []}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            state["seen"].append((self.path, self.headers, body))
            if state["mode"] == "302":
                self.send_response(302)
                self.send_header("Location", "/other")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            code, out = {"200": (200, {"ok": True, "id": "fileid123", "name": "selftest-ok.md"}),
                         "401": (401, {"ok": False, "error": "invalid_key", "message": "bad key"}),
                         "503": (503, {"ok": False, "error": "key_check_unavailable", "message": "down"}),
                         "text": (200, None)}[state["mode"]]
            data = b"<html>not json</html>" if out is None else json.dumps(out).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        do_GET = do_POST

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    good_url = f"http://127.0.0.1:{srv.server_address[1]}/webhook/revxl-client-report"
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    closed_url = f"http://127.0.0.1:{s.getsockname()[1]}/x"
    s.close()

    results, captured = [], []

    def check(name, cond):
        results.append(bool(cond))
        print(f"{'PASS' if cond else 'FAIL'}  {name}")

    def run(*args):
        o, e = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(o), contextlib.redirect_stderr(e):
            try:
                code = main(list(args))
            except SystemExit as x:
                code = x.code
        captured.append(o.getvalue() + e.getvalue())
        return code, o.getvalue()

    def draft(summary="selftest report", body="## What happened\nA test.", *extra):
        bf = tmp / "body.txt"
        bf.write_text(body, encoding="utf-8")
        code, out = run("draft", "--plugin", "selftest-plugin", "--plugin-version", "0.0.1", "--summary", summary,
                        "--body-file", str(bf), "--local-dir", str(reports), *extra)
        path = Path(out.splitlines()[0].split("DRAFT: ", 1)[1]) if code == 0 else None
        return code, out, path

    def mds():
        return sorted(reports.glob("*.md"))

    def send(path, mode, url=None):
        state["mode"] = mode
        os.environ["REVXL_RELAY_URL"] = url or good_url
        before = set(mds())
        code, out = run("send", str(path), "--local-dir", str(reports))
        new = sorted(set(mds()) - before)
        return code, out, (new[0].read_text(encoding="utf-8") if new else None)

    # 1. scrubber across every field, draft JSON, preview and local .md (via a 503 = 3c)
    body = "## What happened\nMulti-byte: café 漢字 😀\n" + "\n".join(planted + list(env.values()) + [FILE_VAULT, OR_FILE])
    code, out, p = draft(f"Guard failed vk_patternOnlyVault12345 {env['N8N_API_KEY']}", body,
                         "--client-label", "Acme hunter2hunter2", "--error-code", f"HF_402 {env['HF_API_KEY_SECRET']}")
    djson = p.read_text(encoding="utf-8") if p else ""
    check("1  draft exit 0 and draft file written", code == 0 and p and p.exists())
    check("1  no planted secret in draft JSON", djson and not any(x in djson for x in leaks))
    check("1  no planted secret in preview", "[REDACTED]" in out and not any(x in out for x in leaks))
    check("1  key containing another key fully redacted", "EXTRA99" not in djson and "shortTokenPrefix12" not in djson)
    check("1  non-secret text kept", "café 漢字 😀" in djson and "Authorization: [REDACTED]" in djson)
    code, out, md = send(p, "503")
    check("3c 503 -> exit 3 + local .md", code == 3 and md and "SAVED LOCALLY" in out)
    check("3c reason names 503", md and "Not sent because:** HTTP 503 key_check_unavailable" in md)
    check("1  no planted secret in local .md", md and not any(x in md for x in leaks))
    check("1  .md has key fingerprint of the vault key",
          md and f"Key fingerprint:** {hashlib.sha256(VAULT.encode()).hexdigest()[:8]}" in md)
    check("3c draft deleted", not p.exists())

    # 2. truncation
    big = "abc é 漢 😀 " * 3750  # 3750 * 16 bytes = 60,000 bytes, multi-byte chars included
    code, out, p = draft("x" * 300, big)
    dj = json.loads(p.read_text(encoding="utf-8"))
    b = dj["body"].encode("utf-8")
    check("2  truncated body <= 51,200 bytes", len(big.encode()) == 60000 and len(b) <= BODY_MAX)
    check("2  valid UTF-8 and ends with marker", b.decode("utf-8") == dj["body"] and dj["body"].endswith(MARKER))
    check("2  summary cut to 200 chars", len(dj["summary"]) == 200)
    run("skip", str(p))

    # 3a. 200 ok
    n0 = len(state["seen"])
    code, out, p = draft()
    code, out, md = send(p, "200")
    path, h, sent = state["seen"][-1]
    check("3a 200 -> exit 0, SENT, draft deleted, no local file",
          code == 0 and "SENT: selftest-ok.md (Drive id fileid123)" in out and not p.exists() and md is None)
    check("3a relay saw X-Revxl-Report v1 + correct x-api-key + JSON + real UA",
          len(state["seen"]) == n0 + 1 and h.get("X-Revxl-Report") == "v1" and h.get("x-api-key") == VAULT
          and h.get("Content-Type") == "application/json" and "Python-urllib" not in (h.get("User-Agent") or ""))
    check("3a posted body is the relay payload", json.loads(sent)["plugin"] == "selftest-plugin")

    # 3b. 401
    code, out, p = draft()
    code, out, md = send(p, "401")
    check("3b 401 -> exit 3, local .md with 401 invalid_key", code == 3 and md and "401 invalid_key" in md)

    # 3d. 302 not followed
    code, out, p = draft()
    code, out, md = send(p, "302")
    check("3d 302 -> exit 3 + local .md", code == 3 and md and "HTTP 302" in md)
    check("3d redirect target never requested", all(x[0] != "/other" for x in state["seen"]))

    # 3e. connection refused
    code, out, p = draft()
    code, out, md = send(p, "200", closed_url)
    check("3e closed port -> exit 3 + local .md", code == 3 and md and "no connection" in md)

    # 3f. no vault key
    del os.environ["VAULT_API_KEY"]
    HOME = empty_home
    n0 = len(state["seen"])
    code, out, p = draft()
    code, out, md = send(p, "200")
    check("3f no key -> exit 3, 'no vault key', nothing posted",
          code == 3 and md and "Not sent because:** no vault key" in md and "(no key)" in md
          and len(state["seen"]) == n0)
    HOME = tmp / "home"
    os.environ["VAULT_API_KEY"] = VAULT

    # extra: non-JSON 200
    code, out, p = draft()
    code, out, md = send(p, "text")
    check("3+ non-JSON 200 -> exit 3 + local .md", code == 3 and md and "not JSON" in md)

    # 4. skip
    code, out, p = draft()
    code, out = run("skip", str(p))
    check("4  skip -> exit 0, draft deleted", code == 0 and not p.exists() and "SKIPPED" in out)

    # R1. revision-1 regressions (orch-checker c1_break / c1_interplay). Live HF id + secret are in env.
    def leaked(text, core, w=12):
        return any(core[i:i + w] in text for i in range(len(core) - w + 1))
    ID, SEC = env["HF_API_KEY_ID"], env["HF_API_KEY_SECRET"]
    OTHER, OTHER2 = hashlib.sha256(b"other").hexdigest(), hashlib.sha256(b"other2").hexdigest()
    extra_env = {"GITHUB_PAT": "ghpFakePatValue0123456789", "HF_CREDENTIALS": "credValueNoPattern0123",
                 "SLACK_WEBHOOK_URL": "https://hooks.example.test/services/ZZwebhookSecret123",
                 "MY_AUTH_HEADER": "authValueNoPattern4567", "SSH_PRIVATE_THING": "privValueNoPattern8901",
                 "HF_KEY_ID_ONLY": "idValueNoShape44556677"}
    os.environ.update(extra_env)
    ORL = env["OPENROUTER_API_KEY"]
    ID2, W = "33333333-4444-5555-6666-777777777777", hashlib.sha256(b"wrapped").hexdigest()  # never live
    r1 = [  # (name, text, cores that must not survive, even as 12-char pieces)
        ("live id + other UPPERCASE secret", f"Key {ID}:{OTHER.upper()}", [OTHER.upper(), ID]),
        ("live secret split across lines", f"Key {ID}:{SEC[:30]}\n{SEC[30:]}", [SEC, ID]),
        ("bare non-live 64-hex secret", f"secret {OTHER2} end", [OTHER2]),
        ("URL-encoded header", f"Authorization%3A%20Key%20{ID}%3A{OTHER}", [OTHER, ID]),
        ("URL-encoded id%3Asecret", f"?cred={ID}%3A{OTHER}", [OTHER]),
        ("spaced Key id : secret", f"Key {ID} : {OTHER}", [OTHER]),
        ("same id, older secret (bare)", f"{ID}:{OTHER}", [OTHER]),
        ("uppercase VK_ prefix", "VK_upperVaultKey12345678", ["upperVaultKey12345678"]),
        ("live sk-or key split across lines", f"{ORL[:16]}\n{ORL[16:]}", [ORL]),
        ("R2 non-live Key id:secret wrapped across lines", f"Key {ID2}:{W[:30]}\n{W[30:]}", [W]),
        ("R2 non-live bare id:secret wrapped across lines", f"{ID2}:{W[:30]}\n{W[30:]}", [W]),
        ("R2 non-live secret wrapped at 40 (24-char tail)", f"Authorization: Key {ID2}:{W[:40]}\n{W[40:]}", [W]),
    ] + [(f"env name {n}", f"value={v};", [v]) for n, v in extra_env.items()]
    for name, text, cores in r1:
        out = scrub(text)
        check(f"R1 scrub: {name}", not any(leaked(out, c) for c in cores))
    check("R1 PAT is word-bounded: PATH / HOMEPATH / CUDA_PATH are not secret names",
          not any(SECRET_NAME.search(n) for n in ("PATH", "HOMEPATH", "CUDA_PATH", "PSModulePath")))
    check("R2 KEY is word-bounded: KEYBOARD_LAYOUT / TURNKEY_DIR / MONKEYPATCH are not secret names",
          not any(SECRET_NAME.search(n) for n in ("KEYBOARD_LAYOUT", "TURNKEY_DIR", "MONKEYPATCH")))
    # same inputs end to end: draft JSON, preview and local .md (503)
    code, out, p = draft("R1 regressions", "\n".join(t for _, t, _ in r1))
    djson = p.read_text(encoding="utf-8")
    code2, out2, md = send(p, "503")
    allcores = [c for _, _, cs in r1 for c in cs]
    check("R1 no R1 secret in draft JSON / preview / local .md",
          md and not any(leaked(x, c) for x in (djson, out, md) for c in allcores))
    check("R1 .md fingerprint line has the relay's suffix", "(first 8 hex of the key's SHA-256)" in md)
    for n in extra_env:
        del os.environ[n]

    # R1. registry code path (monkeypatched reader; the real registry is never read)
    real_reader = _registry_env
    globals()["_registry_env"] = lambda: {"REG_ONLY_SECRET": "regOnlyValue0123456789"}
    USE_REGISTRY = True
    check("R1 registry-only secret redacted", "regOnlyValue0123456789" not in scrub("x regOnlyValue0123456789 y"))
    USE_REGISTRY = False
    globals()["_registry_env"] = real_reader
    check("R1 registry scan off again", "regOnlyValue0123456789" in scrub("x regOnlyValue0123456789 y"))

    # R1. vault key broken by a line break: nothing posted, reason "vault key malformed", halves scrubbed
    H1, H2 = "vk_brokenHalfOne1234", "brkHalf2x9"  # H2 < 16 chars: only the line split catches it
    broken_home = tmp / "broken-home"
    (broken_home / VAULT_KEY_FILE).parent.mkdir(parents=True)
    (broken_home / VAULT_KEY_FILE).write_text(f"{H1}\n{H2}\n", encoding="utf-8")
    del os.environ["VAULT_API_KEY"]
    HOME = broken_home
    n0 = len(state["seen"])
    code, out, p = draft("R1 broken key", f"pasted key:\n{H1}\n{H2}\nend")
    djson = p.read_text(encoding="utf-8")
    code, out2, md = send(p, "200")
    check("R1 malformed vault key -> exit 3, 'vault key malformed', nothing posted",
          code == 3 and md and "Not sent because:** vault key malformed" in md and "(malformed key)" in md
          and len(state["seen"]) == n0)
    check("R1 both halves of the malformed key scrubbed", not any(h in x for h in (H1, H2) for x in (djson, out, md)))
    _, reason = post({"plugin": "p"}, f"{H1}\n{H2}")  # http.client's ValueError message would echo the header
    check("R1 exception text never echoed into the reason", reason == "request failed (ValueError)")
    HOME = tmp / "home"
    os.environ["VAULT_API_KEY"] = VAULT

    # R1. field limits in UTF-16 code units (JavaScript .length), no split surrogate pair
    code, out, p = draft("😀" * 150, "b", "--client-label", "😀" * 60 + "x")
    dj = json.loads(p.read_text(encoding="utf-8"))
    check("R1 summary / client_label cut to 200 / 100 UTF-16 units",
          dj["summary"] == "😀" * 100 and dj["client_label"] == "😀" * 50)
    run("skip", str(p))

    # R3. positives: never-live shapes (ID2 / W are not in env or key files)
    SKN = "sk-or-v1-NotLiveOpenRouterKey0123456789XYZ"
    GH = "NotLiveGithubToken0123456789abcdefghij"
    JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJub3QtbGl2ZS1uOG4ifQ.NotLiveSignatureAbc0123456789"
    r3 = [
        ("hex after underscore", f"{ID2}_{W}", W), ("hex then _old", f"{W}_old", W),
        ("hex after JSON \\n escape", json.dumps({"log": "auth failed\n" + W}), W),
        ("hex after JSON \\t escape", json.dumps({"row": "SECRET\t" + W}), W),
        ("hex after non-ASCII letter", "é" + W, W), ("hex inside CJK prose", "你的密钥是" + W + "，请保密", W),
        ("<uuid>: <hex secret> (space ok when hex >= 32)", f"{ID2}: {W}", W),
        ("sk- after JSON \\n escape", json.dumps({"log": "line1\n" + SKN}), SKN[9:]),
        ("ghp_ token", f"token ghp_{GH}", GH), ("GHP_ upper", f"GHP_{GH.upper()}", GH.upper()),
        ("gho_ token", f"gho_{GH}", GH), ("ghs_ token", f"ghs_{GH}", GH),
        ("github_pat_ token", f"github_pat_11AB_{GH}", GH),
        ("JWT", f"n8n key {JWT} end", JWT), ("X-N8N-API-KEY header", "X-N8N-API-KEY: opaqueN8nKeyValue123", "opaqueN8nKeyValue123"),
    ]
    for name, text, core in r3:
        check(f"R3 scrub: {name}", not leaked(scrub(text), core))
    # R3. negatives: ordinary report lines must survive untouched
    U4 = "7c3d9e2f-1a4b-4c6d-9e8f-5a6b7c8d9e0f"  # shares no 16-char piece with the live fake HF id
    keep = [f"- {U4}: insufficient_credits", f"job {U4}: nsfw_content_detected_by_filter",
            f"YAML:\n  {U4}:\n    status_message_long_text: ok", f"request_id {U4}",
            "Key settings: aspect_ratio=16:9, resolution=1080p", "The primary key constraint: violation detected",
            "Key takeaways: something important happened", "Key parameters: resolution",
            "https://github.com/org/repo/blob/main/src/task-management-dashboard.tsx", "Branch: task-1234-fix-spend-guard-refusal",
            "Saved to disk-usage-report-2026.md", "The mask-inpainting-generation step failed.",
            "https://pypi.org/project/flask-restful-extensions/", "See the risk-assessment-framework-v2 doc.",
            "ask-me-anything-thread-2026-09-28 is a slug", "Short SHA 3f2a1b4 is kept"]
    for t in keep:
        check(f"R3 kept intact: {t.splitlines()[0][:60]}", scrub(t) == t)

    # R3. clean() is a fixpoint. This body needs a 2nd pass: the cut puts "Bearer" right before the
    # truncation marker, which then matches "Bearer\s+..." (pass 1 saw 'Bearer"', no match).
    room = BODY_MAX - len(MARKER.encode("utf-8"))
    edge = {"plugin": "p", "plugin_version": "1", "summary": "s", "body": "z" * (room - 6) + 'Bearer"' + "x" * 1000}
    secrets = _secret_values()
    once = _clean_once(edge, secrets)
    fixed = clean(edge)
    check("R3 edge body needs a second pass (the test exercises the loop)", _clean_once(once, secrets) != once)
    check("R3 clean() output is a fixpoint", _clean_once(fixed, secrets) == fixed and clean(fixed) == fixed
          and len(fixed["body"].encode("utf-8")) <= BODY_MAX)
    straddle = clean({"plugin": "p", "plugin_version": "1", "summary": "s",
                      "body": "z" * (room - 20) + W + "z" * 1000})  # W straddles the truncation point
    check("R3 scrub happens before the cut (no key half left at the truncation point)",
          not leaked(straddle["body"], W) and straddle["body"].endswith(MARKER))
    # a normal draft sends with no notice; a hand-edited draft gets the notice and the more-redacted text is sent
    code, out, p = draft("R3 fixpoint", "plain body")
    code, out, md = send(p, "200")
    check("R3 normal draft -> no NOTICE", code == 0 and "NOTICE" not in out)
    hand = reports / "drafts" / "hand-edited.json"
    hand.write_text(json.dumps({"plugin": "p", "plugin_version": "1", "summary": "hand edited",
                                "body": "added later: vk_handEditedKey12345"}), encoding="utf-8")
    code, out, md = send(hand, "200")
    check("R3 hand-edited draft -> NOTICE + more-redacted text sent",
          code == 0 and "NOTICE: the send-time re-scrub changed" in out
          and b"vk_handEditedKey12345" not in state["seen"][-1][2] and b"[REDACTED]" in state["seen"][-1][2])

    # R4. token boundaries after escapes (never-live fakes), ghu_/ghr_, and the negatives that must survive
    SKP = "sk-proj-R4NonHexOpenAIstyleKeyAbCdEfGhIjKlMnOp"
    BT = chr(96)  # PowerShell backtick
    r4 = [("sk- after %20", "Authorization%3A%20Bearer%20" + SKP), ("sk- after %3D", "key%3D" + SKP),
          ("sk- in %22..%22", "%22" + SKP + "%22"), ("sk- after %0A", "line1%0A" + SKP),
          ("sk- after PowerShell `n", "line1" + BT + "n" + SKP), ("sk- after PowerShell `t", "a" + BT + "t" + SKP),
          ("sk- after \\u0022", "\\u0022" + SKP + "\\u0022"), ("sk- in quotes", '"' + SKP + '"'),
          ("ghu_ token", f"ghu_{GH}"), ("ghr_ token", f"ghr_{GH}"),
          ("JWT after JSON \\n", json.dumps({"log": "k\n" + JWT})), ("JWT after %20", "token%20" + JWT)]
    for name, text in r4:
        core = SKP[3:] if "sk-" in name else (GH if "gh" in name else JWT)
        check(f"R4 scrub: {name}", not leaked(scrub(text), core))
    keep4 = ["whisk-api-integration-tests-v2", "kiosk-mode-generation-pipeline", "desk-booking-application-v2",
             "highs_and_lows_of_the_generation_week", "num_highs_in_generation_batch = 3",
             "def laughs_per_minute_counter(self): pass", f"req {U4}:insufficient_credits",
             f"{U4}:content_policy_violation", f"https://api.example.test/v1/jobs/{U4}:download_original_file",
             "Key settings:aspect_ratio_16_9", "The primary key constraint:violation_detected"]
    for t in keep4:
        check(f"R4 kept intact: {t[:60]}", scrub(t) == t)

    # R4. runtime pre-cap at 4x each limit, backing off to whitespace so no half key is left at that cut
    pre = 4 * BODY_MAX
    beyond = clean({"plugin": "p", "plugin_version": "1", "summary": "s",
                    "body": "Authorization: " + "y" * (5 * BODY_MAX) + "\nBEYOND-4X-LIMIT"})
    check("R4 content beyond 4x the body limit never reaches the output", "BEYOND-4X-LIMIT" not in beyond["body"])
    half = clean({"plugin": "p", "plugin_version": "1", "summary": "s",
                  "body": "Authorization: " + "y" * (pre - 34) + "\n" + SKP + " tail"})  # SKP straddles the 4x cut
    check("R4 no half key left at the 4x pre-cut", not leaked(half["body"], SKP[3:]))

    # R4. timing: adversarial bodies (the old JWT rule took ~3 s per pass on 51,200 B of "eyJ", quadratic)
    import time
    def fill(unit, n=BODY_MAX):
        return (unit * (n // len(unit) + 1))[:n]
    adversarial = {"eyJ repeated": fill("eyJ"), "eyJ + long run": "eyJ" + "a" * (BODY_MAX - 3),
                   "%20eyJ repeated": fill("%20eyJ"), "\\neyJ repeated": fill("\\neyJ"), "sk- repeated": fill("sk-"),
                   "%3Dsk- repeated": fill("%3Dsk-"), "ghp_ repeated": fill("ghp_"), "Key word: repeated": fill("Key aaaaaaaa: "),
                   "uuid: repeated": fill(U4 + ":"), "uuid:<letters> repeated": fill(U4 + ":" + "a" * 40 + " "),
                   "hex 23 + g": fill("0123456789abcdef0123456g"), "%3A repeated": fill("%3A")}
    worst = (0.0, "")
    for name, body in adversarial.items():
        t0 = time.perf_counter()
        clean({"plugin": "p", "plugin_version": "1", "summary": body[:300], "body": body})
        worst = max(worst, (time.perf_counter() - t0, name))
    check(f"R4 timing: worst 51,200-byte adversarial body {worst[0]:.3f}s < 0.75 s (target 0.5; {worst[1]})",
          worst[0] < 0.75)
    t0 = time.perf_counter()
    big = clean({"plugin": "p", "plugin_version": "1", "summary": "s", "body": fill("eyJ", 1024 * 1024)})
    dt = time.perf_counter() - t0
    check(f"R4 timing: 1 MB 'eyJ' body {dt:.3f}s < 3 s (target 3), result within the byte limit",
          dt < 3 and len(big["body"].encode("utf-8")) <= BODY_MAX)

    # 6. filename collision
    pl = {"plugin": "a/b", "plugin_version": "1", "summary": 'same: "name"?', "body": "x"}
    now = datetime(2026, 9, 28, 12, 0)
    f1 = save_local(pl, tmp / "collide", "r1", "(no key)", now)
    f2 = save_local(pl, tmp / "collide", "r2", "(no key)", now)
    check("6  collision -> '-1' suffix, first file untouched",
          f1.name == "2026-09-28 1200 - a_b - same_ _name__.md" and f2.name == "2026-09-28 1200 - a_b - same_ _name__-1.md"
          and "r1" in f1.read_text(encoding="utf-8"))

    # 7. a reports folder that can't be created (one 300-char folder name is too long on every OS)
    code, out, _ = draft("long path", "x", "--local-dir", str(tmp / ("r" * 300)))
    check("7  over-long reports path -> exit 2, one ERROR line, no traceback", code == 2 and out == ""
          and captured[-1].startswith("ERROR: cannot write the draft") and captured[-1].count("\n") == 1)

    # 5. the fake vault key never appears in output or any file written (key fixtures excluded)
    files = [f for d in (reports, tmp / "collide") for f in d.rglob("*") if f.is_file()]
    blobs = captured + [f.read_text(encoding="utf-8", errors="replace") for f in files]
    check("5  fake vault keys absent from all stdout/stderr and files",
          not any(k in blob for blob in blobs for k in (VAULT, FILE_VAULT, H1, H2)))
    check("5  every draft cleaned up", not list((reports / "drafts").glob("*.json")))

    srv.shutdown()
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
