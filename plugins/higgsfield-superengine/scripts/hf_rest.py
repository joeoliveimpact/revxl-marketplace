#!/usr/bin/env python3
"""hf_rest.py - Higgsfield REST client for the higgsfield-superengine plugin. Standard library only, Python 3.9+.

  python hf_rest.py check                              free auth test (a cost estimate); prints AUTH OK
  python hf_rest.py estimate <endpoint> <body.json>    free cost estimate; writes the estimate record, prints its price
  python hf_rest.py submit   <endpoint> <body.json>    PAID. Refuses unless a matching estimate record AND a
                                                       fresh one-time stamp from the spend-guard hook exist
  python hf_rest.py wait     <request_id> [--endpoint EP] [--timeout SECONDS]   poll until done or timeout
  python hf_rest.py download <request_id> [--out DIR]  save a completed job's files
  python hf_rest.py upload   <file>                    upload a reference file, print its public_url
  python hf_rest.py --selftest                         offline checks against a local mock of the API

Every command prints one JSON object; "class" is the machine-readable outcome (check adds an AUTH line).
Exit codes: 0 ok, 1 API/network/job error (see "class"), 2 usage or local input error,
            3 refused (spend gate or HF_SUPERENGINE_DRY_RUN), 4 wait timed out (the job may still be running).
Files, relative to the current folder (the client's workspace):
  higgsfield/<YYYY-MM-DD>/   downloads + log.jsonl
  higgsfield/.spend-guard/   estimates/ (written by estimate), stamps/ (written by the spend-guard hook),
                             used/ (stamps consumed by submit). The rules are in _gate().
Key: HF_API_KEY_ID + HF_API_KEY_SECRET from the environment, else the Windows user environment
     (HKCU\\Environment), else on macOS the Keychain (beta, untested). Never printed, logged or written.
Env: HF_SUPERENGINE_DRY_RUN=1   refuse submit, and skip the saved-key lookup (Windows registry / macOS Keychain)
     HF_SUPERENGINE_API_BASE    base URL of a local mock (loopback http only), e.g. http://127.0.0.1:8123
"""
import argparse, hashlib, http.client, json, math, os, random, re, secrets, shutil, sys, time
import urllib.error, urllib.parse, urllib.request
from collections import namedtuple
from datetime import datetime
from pathlib import Path

API = "https://api.higgsfield.ai"
BASE_ENV, DRY_ENV = "HF_SUPERENGINE_API_BASE", "HF_SUPERENGINE_DRY_RUN"
USER_AGENT = "higgsfield-plugin/0.1"  # Cloudflare answers 403 "error code: 1010" to the default Python-urllib UA
ROOT = Path("higgsfield")             # relative to the current folder
GUARD = ROOT / ".spend-guard"
STAMP_TTL, ESTIMATE_TTL, SKEW = 60, 30 * 60, 2  # seconds
TERMINAL = {"completed", "failed", "nsfw", "canceled"}
REFUNDED = {"failed", "nsfw", "canceled"}  # docs: failed and nsfw are not charged; a canceled request is refunded
ESTIMATE_ALIAS = {"v1/custom-references": "soul-id"}  # Soul ID training: /estimate/v1/custom-references is 404
STATUS_PATH = {"v1/custom-references": "/v1/custom-references/{}"}  # training is polled here, not /requests/
UPLOAD_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
                ".gif": "image/gif", ".wav": "audio/wav", ".mp4": "video/mp4"}  # docs: supported content types
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
ENDPOINT_RE = re.compile(r"[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)*")
ID_RE = re.compile(r"[A-Za-z0-9-]{8,64}")
KEY_RE = re.compile(r"[A-Za-z0-9._~+/=-]{8,256}")
HEX32 = re.compile(r"[0-9a-f]{32}")

# wait: default timeout per endpoint, in seconds. Measured = submit-to-terminal on Joe's REST key in the 09.24.26
# runs (output/data/hf-test-log.jsonl timestamps, 3 jobs in flight so queueing is included; Soul ID from
# results2.json). Rule: 3x the measured max, rounded up to 5 minutes; then every workflow of one model shares that
# model's highest value (Seedance 2.5 t2v: 3000 alone, 3600 like r2v). Unmeasured image endpoints get 600 s;
# unmeasured video endpoints and anything unknown get 3600 s (the slowest measured family).
WAIT_MEASURED = {
    "z-image/turbo": 300,                               # max 11 s, n=6
    "higgsfield-ai/soul/v2/standard": 300,              # max 93 s, n=4
    "marketing-studio/image": 300,                      # max 48 s, n=2
    "marketing-studio/image/flare": 300,                # 54 s, n=1
    "kling-video/v3.0/std/text-to-video": 600,          # max 196 s, n=4
    "minimax/h3/text-to-video": 900,                    # max 235 s, n=2
    "v1/custom-references": 1800,                       # Soul ID training, 578 s, n=1
    "bytedance/seedance-2.5/text-to-video": 3600,       # max 971 s, n=5 (3000 alone; the model's 3600)
    "bytedance/seedance-2.5/reference-to-video": 3600,  # max 1118 s, n=9
}
IMAGE_PREFIXES = ("alibaba/qwen-image", "higgsfield-ai/soul/", "ideogram/", "marketing-studio/image", "recraft/",
                  "xai/grok-imagine-image", "z-image/")

ADVICE = {
    "ok": "OK.",
    "redirect_refused": "The API answered with a redirect. Not followed: it would forward your key to another address.",
    "invalid_credentials": "The key is missing or invalid (401). Run the higgsfield-setup skill.",
    "insufficient_credits": "Out of API credits (403 Insufficient credits). Top up in the Higgsfield Console.",
    "cloudflare_1010": "Blocked by Cloudflare (403, error code 1010): a plugin bug (User-Agent), not your account.",
    "forbidden": "403 without 'Insufficient credits': not treated as out of credits. Reason unknown.",
    "concurrency_limit": "Too many jobs running (400). No job was created: safe to resubmit once a running job ends.",
    "bad_request": "Request rejected (400). Fix the parameters.",
    "not_found": "Not found (404). Check the endpoint or the request id.",
    "validation_error": "The body failed validation (422). Fix the parameters.",
    "model_blocked": "The model is temporarily blocked (423). Try later.",
    "model_unavailable": "The model is disabled or not ready (503). Try later.",
    "server_error": "Higgsfield server error (5xx). Try later.",
    "unexpected_status": "Unexpected HTTP status.",
    "network_error": "No answer from the API (network error, timeout or dropped connection).",
    "non_json": "The API answered 2xx, but not with a JSON object.",
    "unexpected_response": "The API answered 2xx JSON without the expected fields.",
}
POLL_THROUGH = {"network_error", "non_json", "server_error", "model_unavailable"}  # wait keeps polling on these
JOB_ADVICE = {
    "completed": "Done. Next: download {}.",
    "failed": "Generation failed. Not charged (refunded).",
    "nsfw": "Rejected by content moderation (nsfw). Not charged (refunded). Rephrase one thing and try again.",
    "canceled": "Canceled before processing. Refunded.",
}
GATE_REASONS = {
    "no_estimate": "No estimate on file for this exact endpoint and body. Run estimate with the same endpoint "
                   "and body file first.",
    "estimate_unreadable": "The estimate record could not be read. Run estimate again.",
    "estimate_invalid": "The estimate record is malformed. Run estimate again.",
    "estimate_mismatch": "The estimate record does not match this endpoint and body. Run estimate again.",
    "estimate_stale": "The estimate is older than 30 minutes. Run estimate again.",
    "estimate_clock_skew": "The estimate record is dated in the future (clock skew). Run estimate again.",
    "no_stamp": "No spend-guard stamp for this estimate. Only the spend-guard hook writes stamps, when submit "
                "runs; without the hook, submit always refuses. Do not create or edit stamp files.",
    "stamp_unreadable": "The spend-guard stamp could not be read.",
    "stamp_invalid": "The spend-guard stamp is malformed.",
    "stamp_mismatch": "The spend-guard stamp was written for a different estimate. Run estimate, then submit again.",
    "stamp_expired": "The spend-guard stamp is older than 60 seconds. Run submit again so the hook re-checks it.",
    "stamp_clock_skew": "The spend-guard stamp is dated in the future (clock skew).",
    "stamp_reused": "This spend-guard stamp was already used. Each stamp authorises one submit.",
    "stamp_needs_ask": "This estimate has no price (the /estimate call failed), so only an 'ask' stamp (the "
                       "client's click) can authorise it.",
    "stamp_consume_failed": "The spend-guard stamp could not be consumed safely.",
}

Resp = namedtuple("Resp", "status payload cid cls error")
_LIVE = set()  # key values seen in this process: replaced by [REDACTED] in everything printed or written
_clock, _sleep = time.monotonic, time.sleep  # the selftest swaps in a fake clock


class Fail(Exception):
    def __init__(self, cls, message, code=1, **extra):
        super().__init__(cls)
        self.cls, self.message, self.code, self.extra = cls, message, code, extra


def dry_run():
    return os.environ.get(DRY_ENV, "").strip().lower() not in ("", "0", "false", "no", "off")


def _keychain_creds():
    """macOS Keychain (BETA, untested on a real Mac): hf-key-box.py saves ONE generic password, value "id:secret"."""
    if sys.platform != "darwin":
        return None, None
    import subprocess
    try:
        r = subprocess.run(["security", "find-generic-password", "-s", "higgsfield-superengine", "-a", "HF_API_KEY",
                            "-w"], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None, None
    kid, sep, sec = r.stdout.strip().partition(":")
    return (kid, sec) if r.returncode == 0 and sep else (None, None)


def _registry_creds():
    """The saved key: the Windows user environment (HKCU\\Environment), where hf-key-box.ps1 saves it; on macOS
    the Keychain instead. The selftest replaces this whole function, so it never reads a real saved key."""
    if os.name != "nt":
        return _keychain_creds()
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            def get(name):
                try:
                    return winreg.QueryValueEx(k, name)[0]
                except OSError:
                    return None
            return get("HF_API_KEY_ID"), get("HF_API_KEY_SECRET")
    except OSError:
        return None, None


def creds():
    kid, sec = os.environ.get("HF_API_KEY_ID"), os.environ.get("HF_API_KEY_SECRET")
    if not (kid and sec) and not dry_run():  # DRY_RUN never reaches into the registry
        rid, rsec = _registry_creds()
        kid, sec = kid or rid, sec or rsec
    kid, sec = [v.strip() if isinstance(v, str) else v for v in (kid, sec)]
    _LIVE.update(v for v in (kid, sec) if isinstance(v, str) and len(v) >= 8)
    if not (kid and sec):
        raise Fail("no_key", "No Higgsfield key found. Run the higgsfield-setup skill.")
    if not (isinstance(kid, str) and isinstance(sec, str) and KEY_RE.fullmatch(kid) and KEY_RE.fullmatch(sec)):
        raise Fail("key_malformed", "The saved Higgsfield key has an unexpected format (a space, a line break or an "
                                    "odd character). Re-enter it with the higgsfield-setup skill. Nothing was sent.")
    return kid, sec


def api_base():
    base = os.environ.get(BASE_ENV)
    if not base:
        return API
    u = urllib.parse.urlsplit(base)
    if u.scheme == "http" and u.hostname in LOOPBACK and u.username is None and not (u.path.strip("/") or u.query
                                                                                      or u.fragment):
        return base.rstrip("/")
    raise Fail("bad_base_url", f"{BASE_ENV} must be a loopback mock such as http://127.0.0.1:8123. Refusing to "
                               "send the key anywhere else.", 2)


def _scrub(s):
    for v in sorted(_LIVE, key=len, reverse=True):
        s = s.replace(v, "[REDACTED]")
    return s


def emit(obj):
    print(_scrub(json.dumps(obj, indent=2, ensure_ascii=False)))


def day_dir():
    return ROOT / time.strftime("%Y-%m-%d")


def _log(event):
    """Append one scrubbed line to higgsfield/<date>/log.jsonl. Returns an error name, or None."""
    try:
        folder = day_dir()
        folder.mkdir(parents=True, exist_ok=True)
        line = json.dumps(dict(event, ts=datetime.now().astimezone().isoformat(timespec="seconds")),
                          ensure_ascii=False)
        with open(folder / "log.jsonl", "a", encoding="utf-8", newline="\n") as f:
            f.write(_scrub(line) + "\n")
    except OSError as e:
        return type(e).__name__
    return None


def _write_json(path, obj):
    """Atomic write (temp file + os.replace), so a reader never sees half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{secrets.token_hex(3)}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(_scrub(json.dumps(obj, indent=2, ensure_ascii=False)) + "\n")
    os.replace(tmp, path)


def _no_constant(name):
    raise ValueError(f"{name} is not valid JSON")


def canonical(params):
    """The exact text estimate and submit both send, and the text the estimate key is computed from."""
    return json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _canon(params):
    try:
        return canonical(params) if isinstance(params, dict) else None
    except (TypeError, ValueError):
        return None


def load_params(path):
    """Body file -> (params dict, canonical text). UTF-8 JSON object (a BOM is fine); NaN/Infinity refused."""
    try:
        params = json.loads(Path(path).read_bytes().decode("utf-8-sig"), parse_constant=_no_constant)
        canon = _canon(params)
    except (OSError, ValueError, RecursionError) as e:
        raise Fail("bad_input", f"Cannot read the body file as UTF-8 JSON ({type(e).__name__}).", 2)
    if canon is None:
        raise Fail("bad_input", "The body file must hold one JSON object with finite numbers.", 2)
    return params, canon


def endpoint_arg(s):
    ep = s.strip().strip("/")
    if not ENDPOINT_RE.fullmatch(ep):
        raise Fail("bad_input", "The endpoint must look like vendor/model/workflow (lowercase letters, digits, "
                                ". _ - and /).", 2)
    return ep


def estimate_key(endpoint, canon):
    return hashlib.sha256(f"hf-superengine-estimate-v1\n{endpoint}\n{canon}".encode("utf-8")).hexdigest()


def guard_file(kind, key):
    """estimates/ or stamps/ file for a key. Named by the first 32 hex only (Windows 260-char paths); the full
    64-hex key is inside the file and is what the gate compares."""
    return GUARD / kind / f"{key[:32]}.json"


def _job_id(s):
    if not ID_RE.fullmatch(s):
        raise Fail("bad_input", "That does not look like a request id.", 2)
    return s


def timeout_for(endpoint):
    if endpoint in WAIT_MEASURED:
        return WAIT_MEASURED[endpoint]
    return 600 if endpoint and endpoint.startswith(IMAGE_PREFIXES) else 3600


def classify(status, text):
    """Machine-readable class for an HTTP status and body text. status None = no HTTP answer at all."""
    if status is None:
        return "network_error"
    if 200 <= status < 300:
        return "ok"
    if 300 <= status < 400:
        return "redirect_refused"
    t = text.lower()
    if status == 403:  # only the body tells an empty balance from a Cloudflare block
        if "insufficient credits" in t:
            return "insufficient_credits"
        return "cloudflare_1010" if re.search(r"error code:?\s*1010\b", t) else "forbidden"
    if status == 400:  # docs: the concurrency limit is a 400, not a 429
        return "concurrency_limit" if "concurren" in t else "bad_request"
    named = {401: "invalid_credentials", 404: "not_found", 422: "validation_error", 423: "model_blocked",
             503: "model_unavailable"}
    return named.get(status) or ("server_error" if status >= 500 else "unexpected_status")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # a 3xx becomes an HTTPError: following it would forward the Authorization header


_OPENER = urllib.request.build_opener(_NoRedirect)


def call(method, path, body=None, timeout=60):
    """Authenticated API call. Never raises for HTTP or network trouble: the class says what happened."""
    kid, sec = creds()
    headers = {"Authorization": f"Key {kid}:{sec}", "User-Agent": USER_AGENT, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(api_base() + path, data=body, headers=headers, method=method)
    try:
        try:
            with _OPENER.open(req, timeout=timeout) as r:
                status, raw, hdrs = r.status, r.read(), r.headers
        except urllib.error.HTTPError as e:  # 3xx (never followed), 4xx, 5xx
            status, hdrs = e.code, e.headers
            try:
                raw = e.read()
            except (OSError, http.client.HTTPException):
                raw = b""
    except (OSError, http.client.HTTPException) as e:  # DNS, refused, timeout, reset, dropped connection
        return Resp(None, None, None, "network_error", type(e).__name__)
    text = raw.decode("utf-8", "replace")
    try:
        payload = json.loads(text)
    except (ValueError, RecursionError):
        payload = None
    cls = classify(status, text)
    if cls == "ok" and not isinstance(payload, dict):
        cls = "non_json"
    if payload is None and text:
        payload = {"raw": text[:500]}
    return Resp(status, payload, hdrs.get("X-Correlation-ID") if hdrs is not None else None, cls, None)


def _field(r, name):
    return r.payload.get(name) if isinstance(r.payload, dict) else None


# ---- spend gate --------------------------------------------------------------------------------------------
# <id> = the first 32 hex of the estimate key (guard_file); the full key is inside each file.
# estimates/<id>.json   written by `estimate`: {v, kind, estimate_key, endpoint, params, params_sha256,
#                       created_at, http, response}; kept for a 200 JSON answer or any 5xx, deleted otherwise.
# stamps/<id>.json      written by the spend-guard hook (write_stamp is the reference): {v, kind, estimate_key,
#                       endpoint, params_sha256, record_sha256, nonce, decision, created_at}.
# used/<nonce>.claim    created exclusively by submit before it sends anything: one stamp, one submit. Never removed.
# used/<nonce>.json     where submit then moves the stamp (an audit trail).

def _refuse(reason):
    raise Fail("spend_gate_refused", GATE_REASONS[reason] + " Nothing was sent; no credits spent.", 3,
               reason=reason)


def _read_obj(path, what):
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        _refuse("no_" + what)
    except OSError:
        _refuse(what + "_unreadable")
    try:
        obj = json.loads(raw.decode("utf-8"), parse_constant=_no_constant)
    except (ValueError, RecursionError):
        _refuse(what + "_invalid")
    if not isinstance(obj, dict):
        _refuse(what + "_invalid")
    return raw, obj


def _age(value, now):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return now - value


def _gate(endpoint, canon, key):
    """Refuse (Fail, exit 3) unless the matching estimate record and a fresh, unused hook stamp both check out.
    Returns (stamp_path, stamp_bytes, nonce)."""
    now = time.time()
    psha = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    rec_path, st_path = guard_file("estimates", key), guard_file("stamps", key)
    rec_raw, rec = _read_obj(rec_path, "estimate")
    if (rec.get("v"), rec.get("kind"), rec.get("estimate_key"), rec.get("endpoint"), rec.get("params_sha256")) != \
            (1, "hf-superengine-estimate", key, endpoint, psha) or _canon(rec.get("params")) != canon:
        _refuse("estimate_mismatch")
    age, status = _age(rec.get("created_at"), now), rec.get("http")
    if age is None or isinstance(status, bool) or not isinstance(status, int) or \
            not (status == 200 or 500 <= status <= 599):
        _refuse("estimate_invalid")
    if age < -SKEW:
        _refuse("estimate_clock_skew")
    if age > ESTIMATE_TTL:
        _refuse("estimate_stale")
    st_raw, st = _read_obj(st_path, "stamp")
    nonce = st.get("nonce")
    if (st.get("v"), st.get("kind")) != (1, "hf-superengine-stamp") or not isinstance(nonce, str) or \
            not HEX32.fullmatch(nonce) or st.get("decision") not in ("allow", "ask"):
        _refuse("stamp_invalid")
    if (st.get("estimate_key"), st.get("endpoint"), st.get("params_sha256"), st.get("record_sha256")) != \
            (key, endpoint, psha, hashlib.sha256(rec_raw).hexdigest()):
        _refuse("stamp_mismatch")
    age_c = _age(st.get("created_at"), now)
    if age_c is None:
        _refuse("stamp_invalid")
    try:
        age_m = now - st_path.stat().st_mtime  # a second clock: the file's own write time
    except OSError:
        _refuse("stamp_unreadable")
    if min(age_c, age_m) < -SKEW:
        _refuse("stamp_clock_skew")
    if max(age_c, age_m) > STAMP_TTL:
        _refuse("stamp_expired")
    if status != 200 and st.get("decision") != "ask":
        _refuse("stamp_needs_ask")
    return st_path, st_raw, nonce


def _consume(st_path, st_raw, nonce):
    # ponytail: used/ keeps two small files per paid submit (also an audit trail); prune old ones if it ever matters
    used = GUARD / "used" / f"{nonce}.json"
    try:
        used.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        _refuse("stamp_consume_failed")
    # The claim: an exclusive create has exactly one winner, on NTFS and POSIX alike. A rename is not a lock: on
    # Windows, racing renames of one stamp can all report success. The .claim is never removed, so the stamp stays
    # spent even if it is later moved or copied back into stamps/.
    try:
        os.close(os.open(used.with_suffix(".claim"), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        _refuse("stamp_reused")
    except OSError:
        _refuse("stamp_consume_failed")
    try:
        if used.exists():  # consumed by the round-0 version, which wrote no .claim
            _refuse("stamp_reused")
        # Up to ~1 s: on Windows a reader that has the stamp open (a losing racer, antivirus, OneDrive) blocks the
        # move with a sharing violation until it closes the file.
        for attempt in range(20):
            try:
                os.rename(st_path, used)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(0.05)
        same = used.read_bytes() == st_raw
    except OSError:
        _refuse("stamp_consume_failed")
    if not same:
        _refuse("stamp_consume_failed")


def write_stamp(record_path, decision, now=None):
    """Reference stamp writer for the spend-guard hook (Phase 4.1) and the selftest. hf_rest.py never calls it
    on its own, so without the hook submit always refuses. The stamp is bound to the exact record bytes."""
    if decision not in ("allow", "ask"):
        raise ValueError("decision must be 'allow' or 'ask'")
    record_path = Path(record_path)
    raw = record_path.read_bytes()
    rec = json.loads(raw.decode("utf-8"))
    stamp = {"v": 1, "kind": "hf-superengine-stamp", "estimate_key": rec["estimate_key"], "endpoint": rec["endpoint"],
             "params_sha256": rec["params_sha256"], "record_sha256": hashlib.sha256(raw).hexdigest(),
             "nonce": secrets.token_hex(16), "decision": decision, "created_at": time.time() if now is None else now}
    path = record_path.parent.parent / "stamps" / record_path.name
    _write_json(path, stamp)
    return path


# ---- commands ----------------------------------------------------------------------------------------------

def cmd_check(a):
    r = call("POST", "/estimate/z-image/turbo", canonical({"prompt": "a red mug on a table"}).encode())
    emit({"ok": r.cls == "ok", "command": "check", "class": r.cls, "http": r.status, "message": ADVICE[r.cls],
          "correlation_id": r.cid, "response": r.payload})
    print("AUTH OK" if r.cls == "ok" else "AUTH/REQUEST FAILED")
    return 0 if r.cls == "ok" else 1


def _price(rec_path):
    """pricing.py's verdict on the record just written: the same price_bytes call the spend-guard hook makes on
    those bytes (the hook then adds the cap). Shown to the client only; any failure here shows as an ask."""
    try:
        sys.dont_write_bytecode = True  # importing pricing must not leave __pycache__ in the plugin
        import pricing  # same folder (sys.path[0] when run as a script)
        v = pricing.price_bytes(rec_path.read_bytes())
    except Exception as e:
        v = {"ask": True, "usd": None, "display_usd": None, "code": "internal_error",
             "reason": f"could not price the record ({type(e).__name__})"}
    return {k: v.get(k) for k in ("usd", "display_usd", "ask", "code", "reason")}


def cmd_estimate(a):
    ep = endpoint_arg(a.endpoint)
    params, canon = load_params(a.body)
    key = estimate_key(ep, canon)
    rec_path = guard_file("estimates", key)
    r = call("POST", "/estimate/" + ESTIMATE_ALIAS.get(ep, ep), canon.encode("utf-8"))
    keep = r.cls == "ok" or (r.status is not None and r.status >= 500)  # a 5xx keeps an unpriced record: ask only
    try:
        if keep:
            _write_json(rec_path, {"v": 1, "kind": "hf-superengine-estimate", "estimate_key": key, "endpoint": ep,
                                   "params": params, "params_sha256": hashlib.sha256(canon.encode()).hexdigest(),
                                   "created_at": time.time(), "http": r.status, "response": r.payload,
                                   "input_video_s": input_video_s(params)})
        elif rec_path.exists():
            rec_path.unlink()  # a failed re-estimate must not leave an older record usable
    except OSError as e:
        raise Fail("local_io_error", f"Could not update the estimate record ({type(e).__name__}). Check the folder "
                                     "is writable and its path is not near the Windows 260-character limit. "
                                     "Submit will refuse until an estimate is recorded.")
    if r.cls == "ok":
        msg = "Estimate recorded. Show the price to the client; submit also needs the spend-guard hook's stamp."
    elif keep:
        msg = ADVICE[r.cls] + " An unpriced estimate record was kept: the spend guard must ask the client first."
    else:
        msg = ADVICE[r.cls] + " No estimate record kept."
    out = {"ok": r.cls == "ok", "command": "estimate", "class": r.cls, "http": r.status, "endpoint": ep,
           "estimate_key": key, "record": str(rec_path) if keep else None,
           "price": _price(rec_path) if keep else None, "message": msg, "correlation_id": r.cid, "response": r.payload}
    err = _log({"event": "estimate", "endpoint": ep, "estimate_key": key, "http": r.status, "class": r.cls,
                "correlation_id": r.cid, "response": r.payload})
    if err:
        out["log_error"] = err
    emit(out)
    return 0 if r.cls == "ok" else 1


def cmd_submit(a):
    if dry_run():
        _log({"event": "submit_refused", "reason": "dry_run", "endpoint": a.endpoint[:200]})
        raise Fail("dry_run_refused", f"{DRY_ENV} is set: submit refused. Nothing was sent; no key was read.", 3)
    ep = endpoint_arg(a.endpoint)
    params, canon = load_params(a.body)
    key = estimate_key(ep, canon)
    try:
        st_path, st_raw, nonce = _gate(ep, canon, key)
        creds()  # a missing or malformed key fails here, before the stamp is spent
        _consume(st_path, st_raw, nonce)
    except Fail as f:
        _log({"event": "submit_refused", "reason": f.extra.get("reason", f.cls), "endpoint": ep,
              "estimate_key": key})
        raise
    r = call("POST", "/" + ep, canon.encode("utf-8"))
    cls = r.cls
    job = (_field(r, "request_id") or _field(r, "id")) if cls == "ok" else None  # Soul ID training returns "id"
    if cls == "ok" and not (isinstance(job, str) and ID_RE.fullmatch(job)):
        cls, job = "unexpected_response", None
    safe = r.status is not None and 400 <= r.status < 500  # a 4xx is a synchronous rejection: no job exists
    if cls == "ok":
        msg = f"Submitted. Next: wait {job} --endpoint {ep}"
    else:
        msg = ADVICE[cls] + ("" if safe else " The job may or may not exist: do NOT resubmit. Check the Console "
                                             "or wait on a request id first.")
    out = {"ok": cls == "ok", "command": "submit", "class": cls, "http": r.status, "endpoint": ep,
           "estimate_key": key, "request_id": job, "safe_to_resubmit": safe, "message": msg,
           "correlation_id": r.cid, "response": r.payload}
    err = _log({"event": "submit", "endpoint": ep, "estimate_key": key, "http": r.status, "class": cls,
                "request_id": job, "correlation_id": r.cid})
    if err:
        out["log_error"] = err
    emit(out)
    return 0 if cls == "ok" else 1


def urls(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == "url" and isinstance(v, str):
                yield v
            else:
                yield from urls(v)
    elif isinstance(o, list):
        for v in o:
            yield from urls(v)


def backoff():
    delay = 2.0
    while True:
        yield delay + random.uniform(0, 0.5)
        delay = min(delay * 1.5, 10.0)


def cmd_wait(a):
    rid = _job_id(a.request_id)
    ep = endpoint_arg(a.endpoint) if a.endpoint else None
    limit = a.timeout if a.timeout is not None else timeout_for(ep)
    if not (math.isfinite(limit) and limit > 0):
        raise Fail("bad_input", "--timeout must be a positive number of seconds.", 2)
    path = STATUS_PATH.get(ep, "/requests/{}/status").format(rid)
    start, delays, blips, last = _clock(), backoff(), 0, None
    while True:
        r = call("GET", path, timeout=max(1.0, min(30.0, limit - (_clock() - start))))
        waited = _clock() - start
        base = {"command": "wait", "request_id": rid, "endpoint": ep, "seconds": round(waited),
                "timeout_seconds": limit, "blips": blips}
        if r.cls == "ok":
            last = r.payload.get("status")
            if last in TERMINAL:
                ok = last == "completed"
                out = dict(base, ok=ok, status=last, refunded=last in REFUNDED, safe_to_resubmit=not ok,
                           urls=list(dict.fromkeys(urls(r.payload))), error=r.payload.get("error"),
                           message=JOB_ADVICE[last].format(rid), correlation_id=r.cid, response=r.payload)
                out["class"] = "job_" + last
                break
        elif r.cls in POLL_THROUGH:  # docs: retry status GETs after network failures and 5xx
            blips += 1
            base["blips"] = blips
        else:
            out = dict(base, ok=False, http=r.status, safe_to_resubmit=False, correlation_id=r.cid,
                       response=r.payload, message=ADVICE[r.cls] + " The job's state is unknown: do NOT resubmit. "
                                                                  "Run wait again later or check the Console.")
            out["class"] = r.cls
            break
        if waited >= limit:
            out = dict(base, ok=False, last_status=last, safe_to_resubmit=False,
                       message=f"Not finished after {round(waited)} s. It may still be running and may still be "
                               "charged: do NOT resubmit. Run wait again.")
            out["class"] = "wait_timeout"
            break
        _sleep(min(next(delays), limit - waited))
    err = _log({"event": "wait", "request_id": rid, "endpoint": ep, "class": out["class"],
                "status": out.get("status", last), "seconds": out["seconds"], "blips": out["blips"]})
    if err:
        out["log_error"] = err
    emit(out)
    return 0 if out["ok"] else (4 if out["class"] == "wait_timeout" else 1)


def _url_ok(u):
    p = urllib.parse.urlsplit(u)
    return p.scheme == "https" or (p.scheme == "http" and p.hostname in LOOPBACK)


class _HopRefused(Exception):
    pass


class _CheckHops(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _url_ok(newurl):  # every redirect hop must pass the same rule as the first URL
            fp.close()
            raise _HopRefused()
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_DL_OPENER = urllib.request.build_opener(_CheckHops)


def _ext(u):
    s = Path(urllib.parse.urlsplit(u).path).suffix.lower()
    return s if re.fullmatch(r"\.[a-z0-9]{1,5}", s) else ".bin"


def _fetch(url, dest):
    """One output file. No credentials are sent, so a CDN redirect may be followed, but only while every hop passes
    _url_ok (an https URL must not bounce to plain http). Never overwrites."""
    if not _url_ok(url):
        return "refused (not an https URL)"
    if dest.exists():
        return "exists"
    part = dest.with_name(dest.name + ".part")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with _DL_OPENER.open(req, timeout=180) as r, open(part, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 20)
        os.replace(part, dest)
        return "saved"
    except _HopRefused:
        return "refused (redirected to a non-https URL)"
    except (OSError, http.client.HTTPException) as e:
        try:
            part.unlink()
        except OSError:
            pass
        code = getattr(e, "code", None)
        return f"failed ({type(e).__name__}{' ' + str(code) if isinstance(code, int) else ''})"


def cmd_download(a):
    rid = _job_id(a.request_id)
    r = call("GET", f"/requests/{rid}/status")
    status = _field(r, "status") if r.cls == "ok" else None
    if r.cls != "ok" or status != "completed":
        if r.cls != "ok":
            cls, msg = r.cls, ADVICE[r.cls]
        elif status in TERMINAL:
            cls, msg = "job_" + status, "Nothing to download: the job ended without output."
        else:
            cls, msg = "job_not_ready", "Nothing to download yet: run wait first."
        emit({"ok": False, "command": "download", "class": cls, "http": r.status, "request_id": rid,
              "status": status, "message": msg, "correlation_id": r.cid})
        return 1
    folder = Path(a.out) if a.out else day_dir()
    files = []
    for i, u in enumerate(dict.fromkeys(urls(r.payload))):
        dest = folder / f"{rid}{'' if i == 0 else '-' + str(i + 1)}{_ext(u)}"
        files.append({"url": u, "path": str(dest), "result": _fetch(u, dest)})
    ok = bool(files) and all(f["result"] in ("saved", "exists") for f in files)
    cls = "ok" if ok else ("no_outputs" if not files else "download_failed")
    out = {"ok": ok, "command": "download", "class": cls, "request_id": rid, "folder": str(folder), "files": files,
           "message": "Saved." if ok else "Some files were not saved; the URLs stay valid for at least 7 days."}
    err = _log({"event": "download", "request_id": rid, "class": cls, "files": files})
    if err:
        out["log_error"] = err
    emit(out)
    return 0 if ok else 1


def mp4_seconds(data):
    """An MP4's length in seconds from its moov/mvhd box (stdlib, no ffprobe). None if it can't be read."""
    def boxes(start, end):
        i = start
        while i + 8 <= end:
            size, typ, hdr = int.from_bytes(data[i:i + 4], "big"), data[i + 4:i + 8], 8
            if size == 1:
                size, hdr = int.from_bytes(data[i + 8:i + 16], "big"), 16
            elif size == 0:
                size = end - i
            if size < hdr or i + size > end:
                return
            yield typ, i + hdr, i + size
            i += size
    for typ, s, e in boxes(0, len(data)):
        if typ == b"moov":
            for t2, s2, e2 in boxes(s, e):
                if t2 == b"mvhd" and e2 - s2 >= 32:
                    v1 = data[s2] == 1  # version 1: 64-bit times; timescale at +20, duration at +24 (8 bytes)
                    scale = int.from_bytes(data[s2 + (20 if v1 else 12):s2 + (24 if v1 else 16)], "big")
                    dur = int.from_bytes(data[s2 + 24:s2 + 32] if v1 else data[s2 + 16:s2 + 20], "big")
                    return dur / scale if scale and 0 < dur / scale <= 3600 else None  # exact: pricing rounds UP
    return None


def upload_file(public_url):
    return GUARD / "uploads" / f"{hashlib.sha256(public_url.encode('utf-8')).hexdigest()[:32]}.json"


def input_video_s(params):
    """Total seconds of the request's input videos, when every one was uploaded by this plugin (upload records each
    length). None otherwise: pricing then assumes the table's maximum. A video key holding anything but URL strings
    also gives None."""
    found = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if "video" in str(k).lower() and v not in (None, "", [], {}):
                    vals = v if isinstance(v, list) else [v]
                    found.extend(vals if all(isinstance(u, str) for u in vals) else [None])
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(params)
    total = 0.0
    for u in found:
        try:
            rec = json.loads(upload_file(u).read_text(encoding="utf-8")) if isinstance(u, str) else None
        except (OSError, ValueError):
            rec = None
        s = rec.get("seconds") if isinstance(rec, dict) and rec.get("public_url") == u else None
        if isinstance(s, bool) or not isinstance(s, (int, float)) or not 0 < s <= 3600:
            return None
        total += s
    return total if found else None  # never rounded down (Codex review 10.01.26)


def cmd_upload(a):
    path = Path(a.file)
    ctype = UPLOAD_TYPES.get(path.suffix.lower())
    if not ctype:
        raise Fail("bad_input", "Unsupported file type. Higgsfield accepts " + " ".join(UPLOAD_TYPES) + ".", 2)
    try:
        data = path.read_bytes()
    except OSError as e:
        raise Fail("bad_input", f"Cannot read the file ({type(e).__name__}).", 2)
    r = call("POST", "/files/generate-upload-url", canonical({"content_type": ctype}).encode())
    up, pub = _field(r, "upload_url"), _field(r, "public_url")
    hdrs = _field(r, "upload_headers") or {"Content-Type": ctype}
    if r.cls != "ok" or not (isinstance(up, str) and _url_ok(up) and isinstance(pub, str) and isinstance(hdrs, dict)
                             and all(isinstance(k, str) and isinstance(v, str) for k, v in hdrs.items())):
        cls = r.cls if r.cls != "ok" else "unexpected_response"
        emit({"ok": False, "command": "upload", "class": cls, "http": r.status, "message": ADVICE[cls],
              "correlation_id": r.cid, "response": r.payload})
        return 1
    # the presigned URL gets only the headers Higgsfield returned, never the API key
    put, err_name = None, None
    try:
        try:
            with _OPENER.open(urllib.request.Request(up, data=data, method="PUT", headers=hdrs), timeout=120) as resp:
                put = resp.status
        except urllib.error.HTTPError as e:
            put = e.code
    except (OSError, http.client.HTTPException) as e:
        err_name = type(e).__name__
    ok = put is not None and 200 <= put < 300
    secs = mp4_seconds(data) if ok and ctype == "video/mp4" else None
    if secs:  # the price check reads this to price a video edit on its real length, not the 30 s maximum
        try:
            _write_json(upload_file(pub), {"v": 1, "kind": "hf-superengine-upload", "public_url": pub,
                                           "seconds": secs, "created_at": time.time()})
        except OSError:
            secs = None  # no record: pricing falls back to the maximum length
    out = {"ok": ok, "command": "upload", "class": "ok" if ok else "upload_failed", "put_http": put,
           "content_type": ctype, "public_url": pub if ok else None, "video_seconds": secs,
           "message": "Uploaded." if ok else f"The file upload failed ({err_name or put}). Try again."}
    err = _log({"event": "upload", "file": path.name, "content_type": ctype, "put_http": put, "public_url": pub})
    if err:
        out["log_error"] = err
    emit(out)
    return 0 if ok else 1


COMMANDS = {"check": cmd_check, "estimate": cmd_estimate, "submit": cmd_submit, "wait": cmd_wait,
            "download": cmd_download, "upload": cmd_upload}


def main(argv):
    if argv[:1] in (["--selftest"], ["selftest"]):
        return selftest()
    ap = argparse.ArgumentParser(prog="hf_rest.py", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("check")
    for name in ("estimate", "submit"):
        p = sub.add_parser(name)
        p.add_argument("endpoint")
        p.add_argument("body")
    p = sub.add_parser("wait")
    p.add_argument("request_id")
    p.add_argument("--endpoint")
    p.add_argument("--timeout", type=float)
    p = sub.add_parser("download")
    p.add_argument("request_id")
    p.add_argument("--out")
    sub.add_parser("upload").add_argument("file")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 2
    try:
        return COMMANDS[a.cmd](a)
    except Fail as f:
        emit(dict({"ok": False, "command": a.cmd, "class": f.cls, "message": f.message}, **f.extra))
        return f.code
    except Exception as e:  # never a traceback: an exception message can echo a header value
        emit({"ok": False, "command": a.cmd, "class": "internal_error",
              "message": f"Unexpected {type(e).__name__}. Details are withheld on purpose."})
        return 1


def selftest():
    """Offline: a temp workspace, fake keys and a local http.server mock of the API. Never the real API or key."""
    import collections, contextlib, io, socket, subprocess, tempfile, threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    global _registry_creds, _clock, _sleep
    me = os.path.abspath(__file__)  # the race's processes load this same file (before chdir; a mutant tests itself)
    fid, fsec = "5e1f7e57-0b1d-4c0d-8e1f-7e575e1f7e57", hashlib.sha256(b"hf_rest selftest key").hexdigest()
    gid, gsec = "0e9a7e57-0b1d-4c0d-8e1f-7e575e1f0000", hashlib.sha256(b"hf_rest selftest registry").hexdigest()
    names = ("HF_API_KEY_ID", "HF_API_KEY_SECRET", DRY_ENV, BASE_ENV, "NO_PROXY", "no_proxy")
    saved = ({n: os.environ.get(n) for n in names}, os.getcwd(), _registry_creds, _clock, _sleep)
    tmp = Path(tempfile.mkdtemp(prefix="hf-rest-selftest-"))
    state = {"hits": [], "status": {}, "registry": False, "reg_calls": 0}
    errors = {  # name -> (http, json body, text body); used for POST /estimate/err/<name> and POST /sub/<name>
        "401": (401, {"detail": "Invalid credentials"}, None),
        "403credits": (403, {"detail": "Insufficient credits"}, None),
        "1010": (403, None, "error code: 1010"),
        "403other": (403, {"detail": "Not enough permissions"}, None),
        "400conc": (400, {"detail": "Maximum number of concurrent requests (4) has been reached"}, None),
        "400": (400, {"detail": ": 'first_frame_url' is a required property"}, None),
        "404": (404, {"detail": "model_not_found"}, None),
        "422": (422, {"detail": [{"loc": ["body", "prompt"], "msg": "Field required", "type": "missing"}]}, None),
        "423": (423, {"detail": "Model is temporarily blocked"}, None),
        "500": (500, {"code": 500, "detail": "Internal Server Error"}, None),
        "503": (503, {"detail": "Model is disabled"}, None),
        "nonjson": (200, None, "<html>not json</html>"),
    }

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, obj=None, text=None, extra=()):
            data = (json.dumps(obj) if text is None else text).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json" if text is None else "text/plain")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Correlation-ID", "corr-selftest")
            for k, v in extra:
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def _hit(self, body=b""):
            state["hits"].append((self.command, self.path, self.headers.get("Authorization"), body))

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            self._hit(body)
            p, name = self.path, self.path.rsplit("/", 1)[-1]
            if p.startswith("/estimate/err/") or p.startswith("/sub/"):
                if name == "echo":
                    return self._send(400, {"detail": "bad header " + str(self.headers.get("Authorization"))})
                if name in ("302", "307"):
                    return self._send(int(name), {}, extra=[("Location", "/redirect-target")])
                if name == "drop":
                    self.close_connection = True  # no answer at all: the client sees a dropped connection
                    return None
                return self._send(*errors[name])
            if p.startswith("/estimate/"):
                return self._send(200, {"type": "estimate", "credits": "1.500", "usd": "0.094", "discount": None})
            if p == "/files/generate-upload-url":
                return self._send(200, {"upload_url": base + "/upload/x", "public_url": "https://cdn.example.test/in.png",
                                        "content_type": "image/png", "upload_headers": {"Content-Type": "image/png"}})
            return self._send(200, {"status": "queued", "request_id": f"{len(state['hits']):08d}-aaaa-4bbb-8ccc-"
                                                                     "dddddddddddd"})

        def do_PUT(self):
            self._hit(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
            self._send(200, {})

        def do_GET(self):
            self._hit()
            parts = self.path.strip("/").split("/")
            if parts[0] == "files":
                if parts[-1] == "hop-ok.png":  # a redirect hop that passes _url_ok (same loopback mock)
                    return self._send(302, {}, extra=[("Location", "/files/a.png")])
                if parts[-1] == "hop-http.png":  # a hop to plain http on a host _url_ok refuses
                    return self._send(302, {}, extra=[("Location", base.replace("127.0.0.1", "127.0.0.2")
                                                       + "/files/leak.png")])
                return self._send(200, text="BYTES " + self.path)
            rid = parts[1] if len(parts) == 3 and parts[0] == "requests" and parts[2] == "status" else \
                parts[2] if len(parts) == 3 and parts[:2] == ["v1", "custom-references"] else None
            seq = state["status"].get(rid)
            if not seq:
                return self._send(404, {"detail": "Request not found"})
            act = seq.pop(0) if len(seq) > 1 else seq[0]
            if act == "drop":
                self.close_connection = True
                return None
            return self._send(*act)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    closed = f"http://127.0.0.1:{s.getsockname()[1]}"
    s.close()
    results, outs, fake = [], [], {"t": 0.0, "sleeps": 0}

    def check(name, cond):
        results.append(bool(cond))
        print(f"{'PASS' if cond else 'FAIL'}  {name}")

    def run(*args):
        fake["sleeps"] = 0
        o, e = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(o), contextlib.redirect_stderr(e):
            try:
                code = main(list(args))
            except SystemExit as x:
                code = x.code
        outs.append(o.getvalue() + e.getvalue())
        try:
            return code, json.JSONDecoder().raw_decode(o.getvalue().lstrip())[0]
        except ValueError:
            return code, {}

    def fake_registry():
        state["reg_calls"] += 1
        return (gid, gsec) if state["registry"] else (None, None)

    def fake_sleep(d):
        fake["t"] += d
        fake["sleeps"] += 1
        if fake["sleeps"] > 500:  # a wait loop that never ends becomes a failure, not a hang
            raise RuntimeError("runaway wait loop")

    def bodyfile(name, obj):
        Path(name).write_text(json.dumps(obj), encoding="utf-8")
        return name

    def key_of(ep, bf):
        return estimate_key(endpoint_arg(ep), load_params(bf)[1])

    def rec_path(ep, bf):
        return guard_file("estimates", key_of(ep, bf))

    def stamp(ep, bf, decision="allow", age=0.0, mtime_age=None):
        p = write_stamp(rec_path(ep, bf), decision, now=time.time() - age)
        if mtime_age is not None:
            t = time.time() - mtime_age
            os.utime(p, (t, t))
        return p

    def posts(path):
        return sum(1 for h in state["hits"] if h[0] == "POST" and h[1] == path)

    def last_hit(path):
        return ([h for h in state["hits"] if h[1] == path] or [(None,) * 4])[-1]

    def edit_record(ep, bf, **changes):
        p = rec_path(ep, bf)
        d = json.loads(p.read_text(encoding="utf-8"))
        d.update(changes)
        p.write_text(json.dumps(d), encoding="utf-8")

    def refused(code, j, reason):
        return code == 3 and j.get("class") == "spend_gate_refused" and j.get("reason") == reason

    try:
        os.environ.update({"HF_API_KEY_ID": fid, "HF_API_KEY_SECRET": fsec, BASE_ENV: base,
                           "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"})
        os.environ.pop(DRY_ENV, None)
        _registry_creds, _clock, _sleep = fake_registry, (lambda: fake["t"]), fake_sleep
        ws = tmp / "ws"
        ws.mkdir()
        os.chdir(ws)
        EP, SUB = "vendor/model/text-to-image", "/vendor/model/text-to-image"
        A = bodyfile("a.json", {"prompt": "a red mug", "resolution": "1k", "n": 1})
        B = bodyfile("b.json", {"prompt": "a blue mug", "resolution": "1k", "n": 1})
        canon_a = load_params(A)[1].encode()

        code, j = run("check")
        check("S  check -> exit 0, class ok, AUTH OK (against the mock)", code == 0 and j.get("class") == "ok"
              and "AUTH OK" in outs[-1])

        # ---- spend gate
        code, j = run("estimate", EP, A)
        ra = rec_path(EP, A)
        check("G1 estimate -> exit 0 + record with http 200 and the params", code == 0 and ra.is_file()
              and json.loads(ra.read_text(encoding="utf-8"))["http"] == 200
              and json.loads(ra.read_text(encoding="utf-8"))["params"]["prompt"] == "a red mug")
        check("G1 estimate sent the canonical body", last_hit("/estimate/" + EP)[3] == canon_a)
        code, j = run("submit", EP, A)
        check("G2 no stamp -> refused (exit 3, no_stamp), nothing sent", refused(code, j, "no_stamp")
              and posts(SUB) == 0)
        stamp(EP, A, age=61, mtime_age=61)
        code, j = run("submit", EP, A)
        check("G3 stamp 61 s old -> refused stamp_expired", refused(code, j, "stamp_expired"))
        stamp(EP, A, age=0, mtime_age=120)
        code, j = run("submit", EP, A)
        check("G3 fresh created_at but file written 120 s ago -> refused stamp_expired",
              refused(code, j, "stamp_expired"))
        stamp(EP, A, age=-30)
        code, j = run("submit", EP, A)
        check("G4 stamp dated 30 s in the future -> refused stamp_clock_skew", refused(code, j, "stamp_clock_skew"))
        stamp(EP, A, age=0, mtime_age=-30)
        code, j = run("submit", EP, A)
        check("G4 stamp file mtime 30 s in the future -> refused stamp_clock_skew",
              refused(code, j, "stamp_clock_skew"))
        stamp(EP, A)
        code, j = run("submit", EP, B)
        check("G5 body B submitted, only A estimated + stamped -> refused no_estimate",
              refused(code, j, "no_estimate") and posts(SUB) == 0)
        run("estimate", EP, B)
        guard_file("stamps", key_of(EP, B)).write_bytes(stamp(EP, A).read_bytes())
        code, j = run("submit", EP, B)
        check("G5 A's stamp copied to B's stamp path -> refused stamp_mismatch", refused(code, j, "stamp_mismatch"))
        stamp(EP, B)
        run("estimate", EP, B)
        code, j = run("submit", EP, B)
        check("G5 record re-written after stamping (price may differ) -> refused stamp_mismatch",
              refused(code, j, "stamp_mismatch"))
        edit_record(EP, B, params={"prompt": "cheaper tampered params", "resolution": "1k", "n": 1})
        stamp(EP, B)
        code, j = run("submit", EP, B)
        check("G5 record params edited (hashes kept) -> refused estimate_mismatch",
              refused(code, j, "estimate_mismatch") and posts(SUB) == 0)
        good = json.loads(stamp(EP, A).read_text(encoding="utf-8"))
        sp = guard_file("stamps", key_of(EP, A))
        garbled = [("not JSON", b"{not json"), ("a JSON list", b"[]"), ("an empty file", b""),
                   ("not UTF-8", b"\xff\xfe{}"), ("created_at as text", dict(good, created_at=str(good["created_at"]))),
                   ("created_at NaN", dict(good, created_at=float("nan"))), ("created_at true", dict(good, created_at=True)),
                   ("no nonce", {k: v for k, v in good.items() if k != "nonce"}), ("short nonce", dict(good, nonce="ab12")),
                   ("decision deny", dict(good, decision="deny")), ("wrong kind", dict(good, kind="other"))]
        for label, data in garbled:
            sp.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())
            code, j = run("submit", EP, A)
            check(f"G6 garbled stamp ({label}) -> refused stamp_invalid, nothing sent",
                  refused(code, j, "stamp_invalid") and posts(SUB) == 0)
        sp.unlink()
        sp.mkdir()
        code, j = run("submit", EP, A)
        check("G6 a folder where the stamp should be -> refused stamp_unreadable", refused(code, j, "stamp_unreadable"))
        sp.rmdir()
        p = stamp(EP, A)
        nonce = json.loads(p.read_text(encoding="utf-8"))["nonce"]
        code, j = run("submit", EP, A)
        check("G7 valid stamp -> submitted (exit 0, class ok, request_id)", code == 0 and j.get("class") == "ok"
              and isinstance(j.get("request_id"), str))
        h = last_hit(SUB)
        check("G7 exactly 1 POST, same canonical body as the estimate, Key auth header",
              posts(SUB) == 1 and h[3] == canon_a and h[2] == f"Key {fid}:{fsec}")
        used = GUARD / "used" / f"{nonce}.json"
        check("G7 stamp consumed: moved to used/<nonce>.json", not p.exists() and used.is_file())
        code, j = run("submit", EP, A)
        check("G8 second submit with the same stamp gone -> refused no_stamp", refused(code, j, "no_stamp"))
        p.write_bytes(used.read_bytes())
        code, j = run("submit", EP, A)
        check("G8 the used stamp restored -> refused stamp_reused, still 1 POST",
              refused(code, j, "stamp_reused") and posts(SUB) == 1)
        p.unlink()
        claim, raw = used.with_suffix(".claim"), used.read_bytes()
        os.replace(used, p)  # moved back, not copied: only the .claim still says this stamp was spent
        code, j = run("submit", EP, A)
        check("G8 the used stamp MOVED back into stamps/ -> refused stamp_reused (the .claim stays), still 1 POST",
              refused(code, j, "stamp_reused") and posts(SUB) == 1 and claim.is_file())
        claim.unlink(missing_ok=True)  # what the round-0 version left behind: used/<nonce>.json and no .claim
        used.write_bytes(raw)
        p.write_bytes(raw)
        code, j = run("submit", EP, A)
        check("G8 used/<nonce>.json without a .claim (a round-0 consume), stamp back -> refused stamp_reused",
              refused(code, j, "stamp_reused") and posts(SUB) == 1)
        p.unlink(missing_ok=True)

        # ---- race (checker's B1): real processes released together on ONE valid stamp. Own workspace, so their
        # simultaneous log.jsonl appends stay out of L1.
        racer = ("import importlib.util as u, os, sys, time\n"
                 "s = u.spec_from_file_location('hf_rest', sys.argv[1])\n"
                 "m = u.module_from_spec(s)\n"
                 "s.loader.exec_module(m)\n"
                 "open(sys.argv[3], 'w').close()\n"
                 "while not os.path.exists(sys.argv[2]):\n"
                 "    time.sleep(0.0002)\n"
                 "sys.exit(m.main(sys.argv[4:]))\n")
        (tmp / "race").mkdir()
        os.chdir(tmp / "race")
        tally, per_round, bad_rounds = collections.Counter(), [], 0
        for rnd in range(10):  # a non-atomic claim leaks in about half of the rounds; 10 rounds miss it ~0.1% of runs
            rb = bodyfile(f"race{rnd}.json", {"prompt": f"race {rnd}"})
            run("estimate", EP, rb)
            stamp(EP, rb)
            go, ready, n0 = tmp / f"go{rnd}", [tmp / f"ready{rnd}-{i}" for i in range(8)], posts(SUB)
            procs = [subprocess.Popen([sys.executable, "-B", "-c", racer, me, str(go), str(r), "submit", EP, rb],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ))
                     for r in ready]
            try:
                t_end = time.time() + 20
                while time.time() < t_end and not all(r.exists() for r in ready) and \
                        all(pr.poll() is None for pr in procs):
                    time.sleep(0.01)
                go.touch()  # the barrier: every racer is spinning on this file
                got = []
                for pr in procs:
                    o, e = (x.decode("utf-8", "replace") for x in pr.communicate(timeout=60))
                    outs.append(o + e)
                    try:
                        jr = json.JSONDecoder().raw_decode(o.lstrip())[0]
                    except ValueError:
                        jr = {}
                    got.append((pr.returncode, jr.get("reason") or jr.get("class")))
            finally:
                for pr in procs:
                    if pr.poll() is None:
                        pr.kill()
            codes = [c for c, _ in got]
            tally.update(r for c, r in got if c != 0)
            per_round.append(posts(SUB) - n0)
            bad_rounds += not (per_round[-1] == 1 and codes.count(0) == 1 and codes.count(3) == len(codes) - 1
                               and any(r == "stamp_reused" for _, r in got))
        check(f"G14 race: 8 processes released together on one valid stamp, 10 rounds -> exactly 1 POST per round "
              f"{per_round}; the others refused {dict(tally)}", bad_rounds == 0)
        rb = bodyfile("held.json", {"prompt": "held open"})
        run("estimate", EP, rb)
        p = stamp(EP, rb)
        held = open(p, "rb")  # on Windows an open reader blocks the move (sharing violation) until it closes
        threading.Timer(0.3, held.close).start()
        n0 = posts(SUB)
        code, j = run("submit", EP, rb)
        check("G14 a reader holding the stamp open for 0.3 s -> submit waits for it: 1 POST, stamp moved",
              code == 0 and posts(SUB) - n0 == 1 and not p.exists())
        os.chdir(ws)
        edit_record(EP, A, created_at=time.time() - 31 * 60)
        stamp(EP, A)
        code, j = run("submit", EP, A)
        check("G9 estimate 31 min old -> refused estimate_stale", refused(code, j, "estimate_stale"))
        edit_record(EP, A, created_at=time.time() + 60)
        stamp(EP, A)
        code, j = run("submit", EP, A)
        check("G9 estimate dated in the future -> refused estimate_clock_skew", refused(code, j, "estimate_clock_skew"))
        code, j = run("estimate", "err/500", A)
        r500 = rec_path("err/500", A)
        check("G10 estimate 500 -> exit 1, unpriced record kept (http 500)", code == 1 and r500.is_file()
              and json.loads(r500.read_text(encoding="utf-8"))["http"] == 500)
        stamp("err/500", A, "allow")
        code, j = run("submit", "err/500", A)
        check("G10 unpriced record + 'allow' stamp -> refused stamp_needs_ask", refused(code, j, "stamp_needs_ask")
              and posts("/err/500") == 0)
        stamp("err/500", A, "ask")
        code, j = run("submit", "err/500", A)
        check("G10 unpriced record + 'ask' stamp -> submitted", code == 0 and posts("/err/500") == 1)
        rec_path("err/400", A).write_text("{}", encoding="utf-8")
        code, j = run("estimate", "err/400", A)
        check("G11 a failed (400) re-estimate deletes the old record", code == 1 and not rec_path("err/400", A).exists())
        deep = ws / "deep"
        deep = deep / ("d" * max(1, 170 - len(str(deep.resolve())) - 1))
        deep.mkdir(parents=True)
        os.chdir(deep)
        bodyfile("a.json", json.loads(Path(ws / A).read_text(encoding="utf-8")))
        code, j = run("estimate", EP, A)
        check(f"G13 estimate from a {len(str(Path.cwd()))}-char-deep folder writes its record (Windows 260-char paths)",
              code == 0 and rec_path(EP, A).is_file())
        os.chdir(ws)
        code, j = run("estimate", "v1/custom-references", A)
        check("G12 Soul ID estimate goes to /estimate/soul-id, record keyed to v1/custom-references",
              code == 0 and posts("/estimate/soul-id") == 1 and rec_path("v1/custom-references", A).is_file())
        code, j = run("estimate", "z-image/turbo", A)
        import pricing  # G15: estimate must print the hook's own verdict on the exact record bytes
        want = pricing.price_bytes(rec_path("z-image/turbo", A).read_bytes())
        check("G15 estimate prints pricing.py's verdict on its record (the hook's call): z-image/turbo $0.094, ask false",
              code == 0 and want["code"] == "priced" and want["usd"] == 0.094 and want["ask"] is False
              and j.get("price") == {k: want[k] for k in ("usd", "display_usd", "ask", "code", "reason")})

        # ---- redirects
        for name in ("302", "307"):
            code, j = run("estimate", "err/" + name, A)
            check(f"R  {name} redirect -> class redirect_refused, exit 1, target never requested",
                  code == 1 and j.get("class") == "redirect_refused"
                  and not any(h[1] == "/redirect-target" for h in state["hits"]))

        # ---- error classes
        for name, cls in (("401", "invalid_credentials"), ("403credits", "insufficient_credits"),
                          ("1010", "cloudflare_1010"), ("403other", "forbidden"), ("400conc", "concurrency_limit"),
                          ("400", "bad_request"), ("404", "not_found"), ("422", "validation_error"),
                          ("423", "model_blocked"), ("500", "server_error"), ("503", "model_unavailable"),
                          ("nonjson", "non_json")):
            code, j = run("estimate", "err/" + name, A)
            check(f"C  {errors[name][0]} {name} -> {cls}", code == 1 and j.get("class") == cls)
        check("C  classify: case-insensitive credits, 'error code:1010', empty 403, 502, 429",
              classify(403, '{"detail":"INSUFFICIENT CREDITS"}') == "insufficient_credits"
              and classify(403, "error code:1010") == "cloudflare_1010" and classify(403, "") == "forbidden"
              and classify(403, "error code: 10100") == "forbidden" and classify(502, "") == "server_error"
              and classify(429, "") == "unexpected_status")
        for name, cls, safe in (("400conc", "concurrency_limit", True), ("403credits", "insufficient_credits", True),
                                ("drop", "network_error", False), ("nonjson", "non_json", False),
                                ("500", "server_error", False)):
            run("estimate", "sub/" + name, A)
            stamp("sub/" + name, A)
            code, j = run("submit", "sub/" + name, A)
            check(f"C  submit {name} -> {cls}, safe_to_resubmit={safe}", code == 1 and j.get("class") == cls
                  and j.get("safe_to_resubmit") is safe and ("do NOT resubmit" in j.get("message", "")) is not safe)
        os.environ[BASE_ENV] = closed
        code, j = run("estimate", EP, A)
        check("C  closed port -> network_error, no traceback", code == 1 and j.get("class") == "network_error"
              and "Traceback" not in outs[-1])
        os.environ[BASE_ENV] = base

        # ---- wait
        img = {"status": "completed", "images": [{"url": base + "/files/a.png"}, {"url": base + "/files/b.jpg"}]}
        state["status"].update({
            "w1-blips-0001": [(500, {"code": 500, "detail": "Internal Server Error"}, None), "drop",
                              (200, None, "<html>cloudflare</html>"), (502, None, "Bad gateway"),
                              (200, {"status": "queued"}, None), (200, {"status": "in_progress"}, None),
                              (200, img, None)],
            "w2-nsfw-0001": [(200, {"status": "nsfw", "error": None}, None)],
            "w3-fail-0001": [(200, {"status": "failed", "error": "Generation failed"}, None)],
            "w3-cncl-0001": [(200, {"status": "canceled"}, None)],
            "w4-slow-0001": [(200, {"status": "in_progress"}, None)],
            "w5-down-0001": ["drop"],
            "w7-auth-0001": [(200, {"status": "queued"}, None), (401, {"detail": "Invalid credentials"}, None)],
            "w8-seed-0001": [(200, {"status": "completed", "video": {"url": base + "/files/v.mp4"}}, None)],
            "ref-train-0001": [(200, {"id": "ref-train-0001", "status": "in_progress"}, None),
                               (200, {"id": "ref-train-0001", "status": "completed"}, None)],
        })
        code, j = run("wait", "w1-blips-0001", "--endpoint", "z-image/turbo")
        check("W1 polls through 500, a dropped connection, a non-JSON 200 and a 502 -> job_completed",
              code == 0 and j.get("class") == "job_completed" and j.get("blips") == 4 and len(j.get("urls", [])) == 2)
        code, j = run("wait", "w2-nsfw-0001")
        check("W2 nsfw -> job_nsfw, refunded, exit 1", code == 1 and j.get("class") == "job_nsfw"
              and j.get("refunded") is True)
        code, j = run("wait", "w3-fail-0001")
        code2, j2 = run("wait", "w3-cncl-0001")
        check("W3 failed / canceled -> job_failed / job_canceled, both refunded",
              j.get("class") == "job_failed" and j.get("refunded") is True and j2.get("class") == "job_canceled"
              and j2.get("refunded") is True and code == code2 == 1)
        n0 = len(state["hits"])
        code, j = run("wait", "w4-slow-0001", "--timeout", "10")
        check("W4 still running at --timeout 10 -> exit 4, class wait_timeout, do NOT resubmit",
              code == 4 and j.get("class") == "wait_timeout" and j.get("safe_to_resubmit") is False
              and j.get("last_status") == "in_progress" and len(state["hits"]) - n0 >= 3)
        code, j = run("wait", "w5-down-0001", "--timeout", "10")
        check("W5 network down the whole time -> explicit wait_timeout (exit 4), no crash",
              code == 4 and j.get("class") == "wait_timeout" and j.get("blips", 0) >= 3)
        code, j = run("wait", "w6-none-0001")
        check("W6 404 -> stops with not_found, says do NOT resubmit", code == 1 and j.get("class") == "not_found"
              and "do NOT resubmit" in j.get("message", ""))
        code, j = run("wait", "w7-auth-0001")
        check("W7 401 while polling -> stops with invalid_credentials", code == 1
              and j.get("class") == "invalid_credentials")
        code, j = run("wait", "w8-seed-0001", "--endpoint", "bytedance/seedance-2.5/text-to-video")
        check("W8 per-model timeout: seedance-2.5 t2v -> 3600 s", code == 0 and j.get("timeout_seconds") == 3600)
        check("W8 timeout table: z-image 300, soul v2 300, kling std t2v 600, unmeasured image 600, video/unknown 3600",
              (timeout_for("z-image/turbo"), timeout_for("higgsfield-ai/soul/v2/standard"),
               timeout_for("kling-video/v3.0/std/text-to-video"), timeout_for("recraft/v4.1/text-to-image"),
               timeout_for("kling-video/v3.0/4k/text-to-video"), timeout_for(None)) == (300, 300, 600, 600, 3600, 3600))
        code, j = run("wait", "ref-train-0001", "--endpoint", "v1/custom-references")
        check("W9 Soul ID training polls /v1/custom-references/<id>", code == 0 and j.get("class") == "job_completed"
              and any(h[1] == "/v1/custom-references/ref-train-0001" for h in state["hits"]))

        # ---- download
        state["status"].update({
            "dl-good-0001": [(200, dict(img, audio={"url": base + "/files/a.png"}), None)],
            "dl-bad-00001": [(200, {"status": "completed", "images": [{"url": "http://example.invalid/x.png"}]}, None)],
            "dl-busy-0001": [(200, {"status": "in_progress"}, None)],
            "dl-hops-0001": [(200, {"status": "completed", "images": [{"url": base + "/files/hop-ok.png"},
                                                                      {"url": base + "/files/hop-http.png"}]}, None)],
        })
        day = day_dir()
        code, j = run("download", "dl-good-0001")
        fa, fb = day / "dl-good-0001.png", day / "dl-good-0001-2.jpg"
        check("D1 download -> 2 files (duplicate URL once) with the served bytes", code == 0 and j.get("class") == "ok"
              and fa.is_file() and fa.read_bytes() == b"BYTES /files/a.png" and fb.is_file()
              and fb.read_bytes() == b"BYTES /files/b.jpg"
              and len(j.get("files", [])) == 2)
        check("D1 file downloads carried no Authorization header",
              all(h[2] is None for h in state["hits"] if h[1].startswith("/files/")))
        code, j = run("download", "dl-good-0001")
        check("D2 second download -> 'exists', nothing overwritten or duplicated, no .part left",
              code == 0 and all(f["result"] == "exists" for f in j.get("files", []))
              and sorted(q.name for q in day.iterdir() if q.name.startswith("dl-")) == sorted([fa.name, fb.name]))
        n0 = len(state["hits"])
        code, j = run("download", "dl-bad-00001")
        check("D3 non-https URL -> refused, not fetched, exit 1", code == 1 and j.get("class") == "download_failed"
              and (j.get("files") or [{}])[0].get("result", "").startswith("refused") and len(state["hits"]) - n0 == 1)
        code, j = run("download", "dl-busy-0001")
        check("D4 job still running -> job_not_ready, exit 1", code == 1 and j.get("class") == "job_not_ready")
        code, j = run("download", "dl-hops-0001")
        fh = day / "dl-hops-0001.png"
        check("D5 redirect hops re-checked: an allowed hop is followed (bytes saved); a hop to plain http on another "
              "host -> refused, never requested", code == 1
              and [f.get("result") for f in j.get("files", [])] == ["saved", "refused (redirected to a non-https URL)"]
              and fh.is_file() and fh.read_bytes() == b"BYTES /files/a.png"
              and not (day / "dl-hops-0001-2.png").exists() and not any("leak" in h[1] for h in state["hits"]))

        # ---- upload
        Path("ref.png").write_bytes(b"\x89PNG fake")
        code, j = run("upload", "ref.png")
        put = last_hit("/upload/x")
        check("U1 upload -> public_url; the PUT carried the file and no Authorization",
              code == 0 and j.get("public_url") == "https://cdn.example.test/in.png" and put[3] == b"\x89PNG fake"
              and put[2] is None)
        Path("notes.txt").write_text("x", encoding="utf-8")
        code, j = run("upload", "notes.txt")
        check("U2 unsupported file type -> bad_input, exit 2", code == 2 and j.get("class") == "bad_input")

        def box(t, payload):
            return (8 + len(payload)).to_bytes(4, "big") + t + payload

        def mp4(version, scale, dur):  # ftyp + moov/mvhd; version 1 = 64-bit times and duration
            times = b"\0" * (16 if version else 8)
            d = dur.to_bytes(8 if version else 4, "big")
            return box(b"ftyp", b"isom\0\0\0\0") + box(b"moov", box(b"mvhd", bytes([version, 0, 0, 0]) + times
                                                               + scale.to_bytes(4, "big") + d + b"\0" * 80))
        check("U3 mp4_seconds reads mvhd v0 and v1 (3.7 s, 5.5 s); garbage and a missing moov -> None",
              mp4_seconds(mp4(0, 600, 2220)) == 3.7 and mp4_seconds(mp4(1, 1000, 5500)) == 5.5
              and mp4_seconds(mp4(0, 10000, 70004)) == 7.0004  # exact: pricing rounds up to 8 s
              and mp4_seconds(b"not an mp4") is None and mp4_seconds(box(b"ftyp", b"isom")) is None)
        Path("clip.mp4").write_bytes(mp4(1, 1000, 5500))
        code, j = run("upload", "clip.mp4")
        url = j.get("public_url")
        check("U4 mp4 upload records its length (video_seconds 5.5) in the guard folder; a request using it -> "
              "input_video_s 5.5; an unknown URL or a non-URL video value -> None (pricing then uses the max)",
              code == 0 and j.get("video_seconds") == 5.5 and upload_file(url).exists()
              and input_video_s({"video_url": url}) == 5.5 and input_video_s({"prompt": "x"}) is None
              and input_video_s({"video_url": url, "video_urls": ["https://other.test/v.mp4"]}) is None
              and input_video_s({"video": {"url": url}}) is None)

        # ---- DRY_RUN
        run("estimate", EP, A)
        p = stamp(EP, A)
        os.environ[DRY_ENV] = "1"
        n0 = posts(SUB)
        code, j = run("submit", EP, A)
        check("Y1 DRY_RUN + valid stamp -> refused (exit 3, dry_run_refused), nothing sent, stamp untouched",
              code == 3 and j.get("class") == "dry_run_refused" and posts(SUB) == n0 and p.exists())
        on = []
        for v in ("0", "false", "OFF", "no", "", "1", "true", "yes", "anything"):
            os.environ[DRY_ENV] = v
            on.append(dry_run())
        check("Y2 DRY_RUN parsing: 0/false/off/no/empty = off; anything else = on", on == [False] * 5 + [True] * 4)
        os.environ[DRY_ENV] = "1"
        del os.environ["HF_API_KEY_ID"], os.environ["HF_API_KEY_SECRET"]
        state["registry"], state["reg_calls"], n0 = True, 0, len(state["hits"])
        code, j = run("check")
        check("Y3 DRY_RUN skips the registry: no env key -> no_key, registry never read, nothing sent",
              code == 1 and j.get("class") == "no_key" and state["reg_calls"] == 0 and len(state["hits"]) == n0)
        del os.environ[DRY_ENV]
        code, j = run("check")
        check("Y4 without DRY_RUN the registry key is used", code == 0 and state["reg_calls"] == 1
              and state["hits"][-1][2] == f"Key {gid}:{gsec}")
        state["registry"] = False
        os.environ.update({"HF_API_KEY_ID": fid, "HF_API_KEY_SECRET": fsec[:20] + "\n" + fsec[20:]})
        n0 = len(state["hits"])
        code, j = run("check")
        check("K1 key with a line break inside -> key_malformed, nothing sent", code == 1
              and j.get("class") == "key_malformed" and len(state["hits"]) == n0)
        os.environ["HF_API_KEY_SECRET"] = fsec
        os.environ[BASE_ENV] = "https://api.example.test"
        code, j = run("check")
        check("K2 non-loopback HF_SUPERENGINE_API_BASE -> bad_base_url, nothing sent", code == 2
              and j.get("class") == "bad_base_url" and len(state["hits"]) == n0)
        os.environ[BASE_ENV] = base
        code, j = run("estimate", "err/echo", A)
        check("K3 an error body echoing the Authorization header is printed as [REDACTED]",
              last_hit("/estimate/err/echo")[2] == f"Key {fid}:{fsec}" and "[REDACTED]" in outs[-1]
              and fsec not in outs[-1] and fid not in outs[-1])
        code, j = run("submit", EP, "missing.json")
        check("K4 unreadable body file -> bad_input, exit 2, no traceback", code == 2 and j.get("class") == "bad_input"
              and "Traceback" not in outs[-1])

        # ---- log + key scan
        logf = day / "log.jsonl"
        events = [json.loads(line)["event"] for line in logf.read_text(encoding="utf-8").splitlines()]
        check("L1 higgsfield/<date>/log.jsonl: every line JSON; estimate, submit, refusals, wait, download, upload",
              {"estimate", "submit", "submit_refused", "wait", "download", "upload"} <= set(events))
        keys = (fid, fsec, gid, gsec)
        check("K5 no key in any output of any command", not any(k in o for k in keys for o in outs))
        files = [q for q in tmp.rglob("*") if q.is_file()]
        check(f"K5 no key in any of the {len(files)} files written", files and not any(
            k.encode() in q.read_bytes() for k in keys for q in files))
        check("K5 the mock did receive the key (so the scans mean something)",
              any(h[2] == f"Key {fid}:{fsec}" for h in state["hits"]))
    except Exception as e:
        check(f"selftest ran to the end (aborted by {type(e).__name__})", False)
    finally:
        srv.shutdown()
        srv.server_close()
        os.chdir(saved[1])
        for n, v in saved[0].items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
        _registry_creds, _clock, _sleep = saved[2], saved[3], saved[4]
        _LIVE.clear()
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        print(json.dumps({"ok": False, "class": "interrupted", "message": "Stopped by the user."}))
        sys.exit(130)
