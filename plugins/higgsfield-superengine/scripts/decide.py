#!/usr/bin/env python3
"""decide.py - the optional Jev caller for the higgsfield-superengine plugin. Standard library only, Python 3.9+.

  python decide.py [--in FILE] [--timeout SECONDS]   one Jev Decisions request. The request JSON comes from FILE
                                                     (no --in, or "-" = stdin): {"state": ..., "questions": {...}}
  python decide.py --selftest                        offline checks against a local mock of OpenRouter

Jev = TypeSafe's decision model (pinned typesafe/jev-1.13-20260917) via the OpenRouter Decisions API. It is
OPTIONAL: nothing may depend on it. Every run prints exactly ONE ASCII JSON line on stdout, nothing on stderr, and
exits 0:
  {"result": "jev", "answers": {<question id>: <answer>}, "cost": <usd or null>, "ms": <milliseconds>}
  {"result": "no-jev", "reason": "<why>"}   the caller carries on with its normal non-Jev path
Reasons: declined, no_key, bad_key, bad_input, bad_base_url, timeout, network, redirect, bad_request (400/413),
auth (401/403), busy (402 in-flight budget), credits (other 402), rate_limited (429), server (5xx incl. 524/529),
unexpected_status, bad_answer (not JSON, wrong model, an answer missing or out of range, or the key echoed back),
internal.
Import use: decide(request_dict, timeout) returns the same dict and never raises.
Key: env OPENROUTER_API_KEY, else ~/.config/openrouter/api_key (BOM + whitespace stripped). A decline recorded as
the file ~/.config/openrouter/jev_declined wins over any key: no key read, no network call.
Safety: the key travels only in an unredirected Authorization header, and redirects are refused anyway. It is never
printed or logged; failures report a reason word only. Model and provider {zdr: true, data_collection: "deny"} are
always set here; the caller cannot override them.
Timeout: a hard wall-clock deadline (default 2.5 s for the routing hook; --timeout up to 10 for callers outside a
hook). No retries, except ONE for an in-flight-budget 402 whose Retry-After fits inside the deadline.
HF_SUPERENGINE_JEV_BASE replaces https://openrouter.ai with a loopback http mock (selftest only).
"""
import http.client
import json
import math
import os
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MODEL = "typesafe/jev-1.13-20260917"
PROVIDER = {"zdr": True, "data_collection": "deny"}
BASE, PATH = "https://openrouter.ai", "/api/alpha/decisions"
BASE_ENV, KEY_ENV = "HF_SUPERENGINE_JEV_BASE", "OPENROUTER_API_KEY"
DECLINE_FILE = "jev_declined"  # sits next to api_key; shared by every plugin that offers Jev
DEFAULT_TIMEOUT, MAX_TIMEOUT = 2.5, 10.0
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
TYPES = {"noul", "choice", "score"}
KEY_RE = re.compile(r"[A-Za-z0-9._~+/=-]{8,512}")  # JSON-safe, header-safe
USER_AGENT = "higgsfield-superengine-decide/0.1"


def no(reason):
    return {"result": "no-jev", "reason": reason}


def cfg_dir():
    return Path.home() / ".config" / "openrouter"


def read_key():
    k = os.environ.get(KEY_ENV, "").strip()
    if not k:
        try:
            k = (cfg_dir() / "api_key").read_bytes().decode("utf-8-sig").strip()
        except (OSError, ValueError):
            k = ""
    return k


def base_url():
    b = os.environ.get(BASE_ENV)
    if not b:
        return BASE
    u = urllib.parse.urlsplit(b)
    if u.scheme == "http" and u.hostname in LOOPBACK and u.username is None and not (u.path.strip("/") or u.query
                                                                                      or u.fragment):
        return b.rstrip("/")
    return None  # never send the key anywhere but OpenRouter or a loopback mock


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def valid_request(req):
    if not isinstance(req, dict) or not isinstance(req.get("state"), (str, dict, list)):
        return False
    qs = req.get("questions")
    if not (isinstance(qs, dict) and qs):
        return False
    for qid, q in qs.items():
        if not (qid and isinstance(q, dict) and q.get("type") in TYPES):
            return False
        if q["type"] == "choice" and not (isinstance(q.get("criteria"), dict) and q["criteria"]):
            return False
    return True


def bad_answer(resp, questions):
    """Ported from the REVUP Jev runner (jev_batch.mjs badAnswer). None = the answer is usable."""
    if not isinstance(resp, dict) or resp.get("model") != MODEL:
        return "model"
    ans = resp.get("answers")
    if not isinstance(ans, dict):
        return "answers"
    for qid, q in questions.items():
        x, t = ans.get(qid), q["type"]
        if not isinstance(x, dict):
            return qid
        if t == "noul" and not (_num(x.get("noul")) and 0 <= x["noul"] <= 1):
            return qid
        if t == "choice":
            p = x.get("probabilities")
            if not (isinstance(x.get("choice"), str) and x["choice"] in q["criteria"] and isinstance(p, dict)
                    and any(_num(v) for v in p.values())):
                return qid
        if t == "score" and not _num(x.get("score")):
            return qid
    return None


def _no_constant(name):
    raise ValueError(f"{name} is not valid JSON")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # a 3xx becomes an HTTPError and is never followed


_OPENER = urllib.request.build_opener(_NoRedirect)


def _post(url, key, body, timeout):
    """-> (status, headers, raw bytes, None) or (None, None, None, 'timeout'|'network'). Never raises."""
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json", "User-Agent": USER_AGENT})
    req.add_unredirected_header("Authorization", "Bearer " + key)
    try:
        try:
            with _OPENER.open(req, timeout=timeout) as r:
                return r.status, r.headers, r.read(), None
        except urllib.error.HTTPError as e:  # 3xx (never followed), 4xx, 5xx
            try:
                raw = e.read()
            except (OSError, http.client.HTTPException):
                raw = b""
            return e.code, e.headers, raw, None
    except (OSError, http.client.HTTPException) as e:
        timed_out = isinstance(e, socket.timeout) or isinstance(getattr(e, "reason", None), socket.timeout)
        return None, None, None, "timeout" if timed_out else "network"


def _json(raw):
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=_no_constant)
    except (ValueError, RecursionError):
        return None


def _status_reason(status, raw):
    if 200 <= status < 300:
        return None
    if 300 <= status < 400:
        return "redirect"
    if status in (400, 413):
        return "bad_request"
    if status in (401, 403):
        return "auth"
    if status == 402:
        err = _json(raw)
        meta = err.get("error", {}).get("metadata", {}) if isinstance(err, dict) else {}
        in_flight = isinstance(meta, dict) and meta.get("limit_source") == "openrouter_in_flight_budget"
        return "busy" if in_flight else "credits"
    if status == 429:
        return "rate_limited"
    return "server" if status >= 500 else "unexpected_status"


def _retry_after(hdrs):
    try:
        s = float(hdrs.get("Retry-After", ""))
    except (TypeError, ValueError, AttributeError):
        return None
    return s if math.isfinite(s) and s >= 0 else None


def _exchange(url, key, body, questions, t0, deadline):
    for attempt in (0, 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return no("timeout")
        status, hdrs, raw, err = _post(url, key, body, remaining)
        if err:
            return no(err)
        reason = _status_reason(status, raw)
        if reason == "busy" and attempt == 0:
            ra = _retry_after(hdrs)
            if ra is not None and ra < deadline - time.monotonic():
                time.sleep(ra)
                continue
        if reason:
            return no(reason)
        resp = _json(raw)
        if resp is None or bad_answer(resp, questions):
            return no("bad_answer")
        answers = {q: resp["answers"][q] for q in questions}
        if key in json.dumps(answers):
            return no("bad_answer")  # an answer that echoes the key is never passed on
        usage = resp.get("usage")
        cost = usage.get("cost") if isinstance(usage, dict) else None
        return {"result": "jev", "answers": answers, "cost": cost if _num(cost) else None,
                "ms": int((time.monotonic() - t0) * 1000)}
    return no("busy")


def decide(request, timeout=DEFAULT_TIMEOUT):
    """One Jev request -> the result dict. Never raises; any failure is a no-jev result."""
    t0 = time.monotonic()
    try:
        if (cfg_dir() / DECLINE_FILE).exists():
            return no("declined")
        if not (valid_request(request) and _num(timeout) and 0 < timeout <= MAX_TIMEOUT):
            return no("bad_input")
        key = read_key()
        if not key:
            return no("no_key")
        if not KEY_RE.fullmatch(key):
            return no("bad_key")
        base = base_url()
        if base is None:
            return no("bad_base_url")
        try:
            body = json.dumps({"model": MODEL, "state": request["state"], "questions": request["questions"],
                               "provider": PROVIDER}, ensure_ascii=True, allow_nan=False).encode("ascii")
        except (TypeError, ValueError, RecursionError):
            return no("bad_input")
        box = {}

        def work():
            try:
                box["r"] = _exchange(base + PATH, key, body, request["questions"], t0, t0 + timeout)
            except Exception:
                box["r"] = no("internal")

        th = threading.Thread(target=work, daemon=True)
        th.start()
        th.join(max(0.0, t0 + timeout - time.monotonic()))
        # ponytail: a slow-drip server leaves the daemon thread reading until its socket timeout; exit ends it
        return box.get("r") or no("timeout")
    except Exception:
        return no("internal")


def emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main(argv):
    req, timeout = None, DEFAULT_TIMEOUT
    try:
        src, it = "-", iter(argv)
        for a in it:
            if a == "--in":
                src = next(it)
            elif a == "--timeout":
                timeout = float(next(it))
            else:
                raise ValueError("unknown argument")
        raw = sys.stdin.buffer.read() if src == "-" else Path(src).read_bytes()
        req = json.loads(raw.decode("utf-8-sig"), parse_constant=_no_constant)
    except (StopIteration, ValueError, OSError, RecursionError):
        req = None  # decide() still checks the decline first, then answers bad_input
    emit(decide(req, timeout))
    return 0


def selftest():
    import shutil
    import subprocess
    import tempfile
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    FAKE, FAKE2 = "sk-or-v1-selftestFAKEkey0123456789abcdef", "sk-or-v1-selftestFAKEenv9876543210fedcba"
    Q = {"gen": {"type": "noul", "instructions": "Is `prompt` asking for an AI image or video?",
                 "criteria": {"true": "It asks to create a picture or video.", "false": "Anything else."}},
         "skill": {"type": "choice", "instructions": "Which skill fits `prompt`?",
                   "criteria": {"static-ads": "A static ad image.", "none": "No skill fits."}},
         "fit": {"type": "score", "instructions": "How well does `prompt` fit?", "criteria": ["poor", "good"]}}
    REQ = {"state": {"prompt": "make a static ad for a red running shoe"}, "questions": Q}

    def good(**over):
        r = {"id": "gen-dec-1", "model": MODEL, "provider": "TypeSafe",
             "answers": {"gen": {"type": "noul", "noul": 0.97},
                         "skill": {"type": "choice", "choice": "static-ads", "confidence": 0.8,
                                   "probabilities": {"static-ads": 0.9, "none": 0.1}},
                         "fit": {"type": "score", "score": 0.9, "probabilities": {"0": 0.1, "1": 0.9}}},
             "usage": {"cost": 0.00002, "input_tokens": 300, "output_tokens": 40}}
        r.update(over)
        return json.dumps(r).encode()

    in_flight = json.dumps({"error": {"code": 402, "message": "busy",
                                      "metadata": {"limit_source": "openrouter_in_flight_budget"}}}).encode()
    st = {"mode": "ok", "hits": [], "target_hits": [], "busy_left": 0}
    results, outputs = [], []

    def check(name, ok):
        results.append(ok)
        print(("PASS " if ok else "FAIL ") + name)

    class Target(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            st["target_hits"].append(dict(self.headers))
            self.send_response(200)
            self.end_headers()

        do_GET = do_POST

    class Mock(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def reply(self, code, body=b"", headers=()):
            self.send_response(code)
            for k, v in headers:
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            st["hits"].append((self.path, self.headers.get("Authorization"), self.rfile.read(n)))
            m = st["mode"]
            try:
                if m == "ok":
                    self.reply(200, good())
                elif m == "slow":
                    time.sleep(3.2)
                    self.reply(200, good())
                elif m == "drip":
                    body = good()
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    for b in body[:20]:
                        self.wfile.write(bytes([b]))
                        self.wfile.flush()
                        time.sleep(0.3)
                elif m.startswith("redirect"):
                    self.reply(int(m[8:]), headers=[("Location", f"http://127.0.0.1:{tport}{PATH}")])
                elif m == "busy_then_ok":
                    if st["busy_left"] > 0:
                        st["busy_left"] -= 1
                        self.reply(402, in_flight, [("Retry-After", "0")])
                    else:
                        self.reply(200, good())
                else:
                    code, body, hdrs = MODES[m]
                    self.reply(code, body, hdrs)
            except OSError:
                pass  # the client gave up (timeout cases)

    MODES = {
        "http500": (500, b'{"error":{"code":500}}', []), "http524": (524, b"", []), "http529": (529, b"x", []),
        "nonjson": (200, b"<html>hello</html>", []), "garbled": (200, good()[:40], []),
        "wrongmodel": (200, good(model="typesafe/jev-1.13"), []),
        "missing": (200, good(answers={"gen": {"type": "noul", "noul": 0.5}}), []),
        "noul_range": (200, good(answers={"gen": {"type": "noul", "noul": 1.5}, "skill": {}, "fit": {}}), []),
        "offchoice": (200, good(answers={"gen": {"type": "noul", "noul": 0.5},
                                         "skill": {"type": "choice", "choice": "made-up", "probabilities": {"x": 1}},
                                         "fit": {"type": "score", "score": 1}}), []),
        "nan": (200, good().replace(b'"noul": 0.97', b'"noul": NaN'), []),
        "echo": (200, good(answers={"gen": {"type": "noul", "noul": 0.5, "note": FAKE},
                                    "skill": {"type": "choice", "choice": "none", "probabilities": {"none": 1}},
                                    "fit": {"type": "score", "score": 1}}), []),
        "http400": (400, b'{"error":{"code":400}}', []), "http413": (413, b"", []),
        "http401": (401, b'{"error":{"code":401}}', []), "http403": (403, b"", []),
        "http402": (402, b'{"error":{"code":402,"message":"Insufficient credits"}}', []),
        "busy": (402, in_flight, []), "busy_long": (402, in_flight, [("Retry-After", "30")]),
        "http429": (429, b"", [("Retry-After", "1")]), "http404": (404, b"", []),
    }

    tmp = Path(tempfile.mkdtemp(prefix="decide-selftest-"))
    home = tmp / "home"
    cfg = home / ".config" / "openrouter"
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Mock)
    tsrv = ThreadingHTTPServer(("127.0.0.1", 0), Target)
    port, tport = srv.server_address[1], tsrv.server_address[1]
    for s in (srv, tsrv):
        s.daemon_threads = True
        threading.Thread(target=s.serve_forever, daemon=True).start()

    def run(mode="ok", env_key=None, stdin=None, args=(), base=None):
        st["mode"], st["hits"], st["target_hits"] = mode, [], []
        env = {k: v for k, v in os.environ.items() if k not in (KEY_ENV, BASE_ENV)}
        env.update(HOME=str(home), USERPROFILE=str(home), PYTHONDONTWRITEBYTECODE="1",
                   **{BASE_ENV: base or f"http://127.0.0.1:{port}"})
        if env_key is not None:
            env[KEY_ENV] = env_key
        data = json.dumps(REQ).encode() if stdin is None else stdin
        t = time.monotonic()
        p = subprocess.run([sys.executable, os.path.abspath(__file__), *args], input=data, env=env,
                           capture_output=True, timeout=30)
        el = time.monotonic() - t
        out, err = p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")
        outputs.append(out + err)
        lines = out.splitlines()
        one_line = len(lines) == 1 and out.endswith("\n") and err == "" and p.returncode == 0
        try:
            res = json.loads(lines[0]) if one_line else {}
        except ValueError:
            res, one_line = {}, False
        check(f"[{mode}] stdout is exactly one JSON line, stderr empty, exit 0", one_line)
        return res, el

    def reason_is(res, want, name):
        check(f"{name}: no-jev reason {want} (got {res.get('reason', res.get('result'))})",
              res == no(want) if want else res.get("result") == "jev")

    try:
        cfg.mkdir(parents=True)
        # no key, no decline: no network call
        res, _ = run("ok")
        reason_is(res, "no_key", "no key anywhere")
        check("no key: the mock got 0 requests", st["hits"] == [])

        # key file with a BOM and CRLF whitespace
        (cfg / "api_key").write_bytes(b"\xef\xbb\xbf  " + FAKE.encode() + b"\r\n")
        res, _ = run("ok")
        reason_is(res, None, "normal answer (key from file)")
        check("normal: answers for every question, cost + ms present",
              set(res.get("answers", {})) == set(Q) and res.get("cost") == 0.00002 and isinstance(res.get("ms"), int))
        path, auth, body = st["hits"][0] if st["hits"] else (None, None, b"{}")
        sent = json.loads(body)
        check("request: POST path, Bearer key stripped of BOM/whitespace",
              path == PATH and auth == "Bearer " + FAKE and len(st["hits"]) == 1)
        check("request: pinned model, provider zdr + data_collection deny, state + questions passed through",
              sent.get("model") == MODEL and sent.get("provider") == PROVIDER and sent.get("state") == REQ["state"]
              and sent.get("questions") == Q)

        res, _ = run("ok", env_key=FAKE2)
        check("env OPENROUTER_API_KEY wins over the key file",
              res.get("result") == "jev" and st["hits"] and st["hits"][0][1] == "Bearer " + FAKE2)

        p = tmp / "req.json"
        p.write_bytes(json.dumps(REQ).encode())
        res, _ = run("ok", args=("--in", str(p), "--timeout", "10"), stdin=b"")
        reason_is(res, None, "--in FILE and --timeout 10")

        res, el = run("slow")
        reason_is(res, "timeout", "server answers after 3.2 s")
        check(f"slow: gave up near 2.5 s (took {el:.2f} s incl. startup)", 2.4 <= el < 3.2)
        res, el = run("drip")
        reason_is(res, "timeout", "server drips the body a byte every 0.3 s")
        check(f"drip: hard deadline holds (took {el:.2f} s incl. startup)", 2.4 <= el < 3.2)

        for m, want in [("http500", "server"), ("http524", "server"), ("http529", "server"),
                        ("nonjson", "bad_answer"), ("garbled", "bad_answer"), ("wrongmodel", "bad_answer"),
                        ("missing", "bad_answer"), ("noul_range", "bad_answer"), ("offchoice", "bad_answer"),
                        ("nan", "bad_answer"), ("echo", "bad_answer"), ("http400", "bad_request"),
                        ("http413", "bad_request"), ("http401", "auth"), ("http403", "auth"),
                        ("http402", "credits"), ("busy", "busy"), ("busy_long", "busy"),
                        ("http429", "rate_limited"), ("http404", "unexpected_status")]:
            res, _ = run(m)
            reason_is(res, want, m)
        check("busy with Retry-After 30 (past the deadline): not retried", len(st["hits"]) == 1)
        st["busy_left"] = 1
        res, _ = run("busy_then_ok")
        reason_is(res, None, "in-flight 402 + Retry-After 0: one retry, then the answer")
        check("busy_then_ok: exactly 2 requests", len(st["hits"]) == 2)
        st["busy_left"] = 5
        res, _ = run("busy_then_ok")
        reason_is(res, "busy", "in-flight 402 twice: only one retry")
        check("busy twice: exactly 2 requests", len(st["hits"]) == 2)

        for code in ("301", "302", "303", "307", "308"):
            res, _ = run("redirect" + code)
            reason_is(res, "redirect", f"HTTP {code} redirect")
            check(f"redirect {code}: the target got 0 requests (so never the key)", st["target_hits"] == [])

        res, _ = run("ok", base="https://example.com")
        reason_is(res, "bad_base_url", "non-loopback base URL override")
        res, _ = run("ok", stdin=b"not json")
        reason_is(res, "bad_input", "stdin is not JSON")
        res, _ = run("ok", stdin=json.dumps({"state": "x", "questions": {}}).encode())
        reason_is(res, "bad_input", "no questions")
        res, _ = run("ok", args=("--timeout", "11"))
        reason_is(res, "bad_input", "--timeout above 10")
        check("bad input: the mock got 0 requests", st["hits"] == [])
        res, _ = run("ok", env_key="sk-or bad key")
        reason_is(res, "bad_key", "key with a space")

        (cfg / DECLINE_FILE).write_bytes(b"")
        res, _ = run("ok", env_key=FAKE2)
        reason_is(res, "declined", "decline recorded (a key is also present)")
        check("declined: the mock got 0 requests", st["hits"] == [])
        res, _ = run("ok", stdin=b"not json")
        reason_is(res, "declined", "decline recorded, bad input")

        leaks = [o for o in outputs if FAKE in o or FAKE2 in o or "selftestFAKE" in o]
        check(f"key scan: neither fake key in any of {len(outputs)} stdout/stderr captures", not leaks)
    except Exception as e:
        check(f"selftest ran to the end (aborted by {type(e).__name__}: {e})", False)
    finally:
        for s in (srv, tsrv):
            s.shutdown()
            s.server_close()
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"{sum(results)}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(selftest())
    sys.exit(main(sys.argv[1:]))
