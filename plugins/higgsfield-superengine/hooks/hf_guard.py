#!/usr/bin/env python3
"""hf_guard.py - the PreToolUse hook of the higgsfield-superengine plugin. Standard library only, Python 3.9+.

  hf_guard.py hook                      the hook (hooks.json): one PreToolUse JSON on stdin -> a decision or nothing
  hf_guard.py hook --only-on win32|posix   the same, but silent (exit 0) on the other OS: hooks.json starts it
                                        with py on Windows and through hf-guard.sh on Mac/Linux
  hf_guard.py --selftest                offline checks: real hook processes fed real-shaped hook JSON

Spend guard (Bash, PowerShell, Monitor, Write, Edit). Commands that do not touch Higgsfield pass untouched.
  hf_rest.py submit  estimate record matches + fresh -> pricing.py -> ledger.py reserve -> stamp (CONTRACT v1):
                     priced and under the cap -> stamp "allow" + allow; over the cap or an ask verdict -> reserve
                     (--force) + stamp "ask" + ask (a real click; bypassPermissions honors a hook's ask, proven
                     10.05.26); dontAsk (nobody can be asked) -> deny + log, nothing reserved or stamped.
                     Anything wrong -> deny.
  deny               api.higgsfield.ai, the higgsfield CLI / SDK, any other way into hf_rest (import, -c, -m,
                     chaining, a script that mentions it), anything touching higgsfield/.spend-guard/ or
                     ~/.config/higgsfield-superengine/, HF_SUPERENGINE_LEDGER_DIR, ad-hoc `import ledger`.
v0.1.4 (Mac report 10.05.26) removed the transcript checks (real call, prompt shown: they raced the transcript
write on Mac Desktop) and the no-look screen guard. Showing the prompt first is a skill instruction now.
Every decision carries hookEventName + permissionDecisionReason. A deny also exits 2 (blocks even if the JSON were
dropped). Internal error: deny if the call touches Higgsfield, else pass.
"""
import hashlib, json, os, re, sys, time
from pathlib import Path

sys.dont_write_bytecode = True  # importing hf_rest/pricing/ledger must not leave __pycache__ in the plugin
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
SHELLS = {"Bash", "PowerShell", "Monitor"}
MARKERS = ("higgsfield", "hf_rest", "spend-guard", "hf_superengine", "hf_guard")
LEDGER_IMPORT = re.compile(r"\b(import|from)\s+ledger\b|import_module\(\s*['\"]ledger")
CONFIG_DIR = re.compile(r"\.config[\\/]+higgsfield-superengine")
GUARD_NAMES = re.compile(r"ledger\.(json|lock)|no-look\.json")
SDK = ("higgsfield_client", "higgsfield-client", "@higgsfield/")
CLI_RE = re.compile(r"higgsfield(-cli)?(\.(exe|cmd|bat|ps1))?")
SEG_RE = re.compile(r"\|\||&&|\$\(|[;|&\n\r(`]")
LAUNCH = {"sudo", "exec", "command", "env", "call", "start", "npx", "bunx", "pnpx", "pnpm", "yarn", "dlx", "-y",
          "--yes", "uvx", "pipx", "run"}
INTERP = re.compile(r"(?i)(?:.*[\\/])?(python(?:3(?:\.\d+)?)?|py)(?:\.exe)?")
PYFLAG = re.compile(r"-B|-u|-\d+(?:\.\d+)?(?:-(?:32|64))?")
BASH_PY = '"$(cat higgsfield/.python)"'  # the 3.6 recorded-interpreter forms (find-python.ps1)
PS_PY = re.compile(r"(?i)&\s*\(\s*get-content\s+-raw\s+-encoding\s+utf8\s+higgsfield[\\/]\.python\s*\)")
BAD = {False: set("$`;&|<>(){}#*?[]~\\\n\r"), True: set("$`;&|<>(){}@,#%\n\r")}  # outside quotes: bash / PS
TAIL = re.compile(r"\s+2>&1\s*$")

SPEND = ("Blocked by the higgsfield-superengine spend guard: ")
PLAIN = ('run hf_rest.py as ONE plain command from the workspace folder: python "<plugin>/scripts/hf_rest.py" '
         "<command> <args> (no cd, &&, ;, pipes, redirects, variables, python -c/-m, or importing it).")


def out(kind, reason, event="PreToolUse"):
    return {"hookSpecificOutput": {"hookEventName": event, "permissionDecision": kind,
                                   "permissionDecisionReason": reason[:1000]}}


def deny(reason):
    return out("deny", SPEND + reason)


# ---- 4.1 spend guard: files -------------------------------------------------------------------------------------

def guarded_path(p, cwd=None):
    """The path as written, normalized (./ and ../ folded), and resolved against the session folder (symlinks
    followed): any of them inside a guarded folder counts. Codex review 10.01.26: ".config/./higgsfield-superengine"
    slipped past a check on the raw text."""
    cands = {p, os.path.normpath(p)} if p else set()
    try:
        q = Path(os.path.expanduser(p))
        if not q.is_absolute():
            q = (Path(cwd) if isinstance(cwd, str) and cwd else Path.cwd()) / q
        cands.add(str(q.resolve()))
    except (OSError, ValueError, RuntimeError):
        pass
    for c in cands:
        n = c.replace("\\", "/").lower()
        if re.search(r"(^|/)\.spend-guard(/|$)", n) or re.search(r"(^|/)\.config/+higgsfield-superengine(/|$)", n):
            return True
    return False


def files(ti, cwd=None):
    fp = ti.get("file_path")
    fp = fp if isinstance(fp, str) else ""
    if guarded_path(fp, cwd):
        return deny("the spend guard's files (higgsfield/.spend-guard/) and the per-user folder "
                    "(~/.config/higgsfield-superengine: the ledger) are written only by the plugin's scripts. "
                    "Do not create, edit, move or delete them.")
    text = "\n".join(v for v in (ti.get("content"), ti.get("new_string")) if isinstance(v, str))
    if not fp.lower().endswith(".md") and ("hf_rest" in text or (LEDGER_IMPORT.search(text) and "higgsfield" in
                                                                  text.lower())):
        return deny("a file (other than .md) that mentions hf_rest, or imports the plugin's ledger, cannot be "
                    "written: code that wraps them would skip the spend gate. " + PLAIN)
    return None


# ---- 4.1 spend guard: shell commands ----------------------------------------------------------------------------

def cli_used(cmd):
    for seg in SEG_RE.split(cmd):
        words = seg.split()
        while words and (words[0].lower() in LAUNCH or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=\S*", words[0])):
            words = words[1:]
        if words and CLI_RE.fullmatch(re.split(r"[\\/]", words[0].strip("'\""))[-1].lower()):
            return True
    return False


def split_plain(s, ps):
    """Tokens of a plain command, or None if it uses anything a shell would expand, chain or redirect."""
    toks, cur, have, i = [], "", False, 0
    while i < len(s):
        c = s[i]
        if c in "\"'":
            j = s.find(c, i + 1)
            if j < 0:
                return None
            body = s[i + 1:j]
            if c == '"' and ("$" in body or "`" in body or (not ps and ("\\\\" in body or body.endswith("\\")))):
                return None
            if j + 1 < len(s) and s[j + 1] in "\"'":
                return None  # adjacent quotes ('it''s', "a""b") parse differently per shell
            cur, have, i = cur + body, True, j + 1
        elif c in " \t":
            if have:
                toks.append(cur)
            cur, have, i = "", False, i + 1
        elif c in BAD[ps]:
            return None
        else:
            cur, have, i = cur + c, True, i + 1
    if have:
        toks.append(cur)
    return None if "--%" in toks else toks


def plain(cmd, ps):
    """-> (script, args) for `<python> [flags] <script> <args...>`, else None."""
    s = TAIL.sub("", cmd.strip())
    known = False
    if not ps and s.startswith(BASH_PY + " "):
        s, known = s[len(BASH_PY):], True
    elif ps and PS_PY.match(s):
        s, known = s[PS_PY.match(s).end():], True
    elif ps and s.startswith("&"):
        s = s[1:]  # PowerShell call operator
    toks = split_plain(s, ps)
    if not toks:
        return None
    if not known:
        if not INTERP.fullmatch(toks[0]):
            return None
        toks = toks[1:]
    while toks and PYFLAG.fullmatch(toks[0]):
        toks = toks[1:]
    return (toks[0], toks[1:]) if toks else None


SCRIPT_MAX = 4 * 1024 * 1024


def wraps_guard(cmd, ps, cwd):
    """`python <file>` where the file (any extension, outside this plugin) mentions the submit script, the guard or
    its files: it could feed the hook a made-up event or race a stamp (Codex review 10.01.26: `python attack.md`)."""
    p = plain(cmd, ps)
    if not p:
        return False
    try:
        f = Path(os.path.expanduser(p[0]))
        f = (f if f.is_absolute() else Path(cwd if isinstance(cwd, str) and cwd else ".") / f).resolve()
        if f.parent in (SCRIPTS.resolve(), HERE.resolve()):
            return False  # the plugin's own scripts
        with open(f, "rb") as h:
            text = h.read(SCRIPT_MAX).decode("utf-8", "replace").lower()
    except (OSError, ValueError, RuntimeError):
        return False
    return any(m in text for m in ("hf_rest", "hf_guard", "spend-guard")) or \
        bool(LEDGER_IMPORT.search(text) and "higgsfield" in text)


def shell(cmd, ps, cwd, mode, ev=None):
    if wraps_guard(cmd, ps, cwd):
        return deny("that script mentions the plugin's submit script, guard or ledger; scripts may not wrap them. "
                    + PLAIN)
    low = cmd.lower()
    if not any(m in low for m in MARKERS) and not LEDGER_IMPORT.search(cmd):
        return None
    if "api.higgsfield.ai" in low:
        return deny("direct calls to api.higgsfield.ai skip the price check and the spend cap. Use the plugin's "
                    "hf_rest.py (estimate, then submit).")
    if any(m in low for m in SDK) or cli_used(cmd):
        return deny("the higgsfield CLI and SDKs skip the price check and the spend cap. Use the plugin's hf_rest.py.")
    if "spend-guard" in low or CONFIG_DIR.search(cmd) or GUARD_NAMES.search(low) or \
            (".config" in low and "higgsfield-superengine" in low):  # ".config/./higgsfield-superengine" and the like
        return deny("the spend guard's files (higgsfield/.spend-guard/) and the per-user folder "
                    "(~/.config/higgsfield-superengine: the ledger) are touched only by the plugin's "
                    "scripts. Do not read-modify, move or delete them from a command.")
    if "hf_superengine_ledger_dir" in low:
        return deny("HF_SUPERENGINE_LEDGER_DIR cannot be set from a command (it would point the spend ledger at an "
                    "empty folder).")
    if LEDGER_IMPORT.search(cmd):
        if any(m in low for m in MARKERS) or in_plugin(cwd):
            return deny("importing the plugin's ledger from ad-hoc Python is not allowed. Use the plain "
                        "python \"<plugin>/scripts/ledger.py\" <command> CLI.")
        return None
    if "hf_rest" not in low and "hf_guard" not in low:
        return None  # e.g. ls higgsfield/<date>, python ".../ledger.py" status
    p = plain(cmd, ps)
    name = re.split(r"[\\/]", p[0])[-1].lower() if p else ""
    if name == "hf_rest.py":
        if p[1][:1] != ["submit"]:
            return None
        return submit(p[0], p[1][1:], cwd, mode, ev)
    if name == "hf_guard.py":
        return None
    return deny("hf_rest.py and hf_guard.py may not be imported, wrapped or chained. " + PLAIN)


def in_plugin(cwd):
    try:
        return isinstance(cwd, str) and Path(cwd).resolve().is_relative_to(HERE.parent)
    except (AttributeError, OSError, ValueError):  # is_relative_to is 3.9+
        return False


def amt(x):
    return f"{x:.9f}".rstrip("0").rstrip(".")


def submit(script, args, cwd, mode, ev=None):
    if len(args) != 2:
        return deny("submit takes exactly <endpoint> <body.json>. " + PLAIN)
    if not (isinstance(cwd, str) and os.path.isdir(cwd)):
        return deny("the hook got no usable working folder, so it cannot find the estimate. Nothing was stamped.")
    os.chdir(cwd)  # hf_rest resolves higgsfield/ and the body file against the folder the command runs in
    try:
        same = Path(script).read_bytes() == (SCRIPTS / "hf_rest.py").read_bytes()
    except OSError:
        same = False
    if not same:
        return deny("that hf_rest.py is not this plugin's copy. Run the plugin's own scripts/hf_rest.py.")
    sys.path.insert(0, str(SCRIPTS))
    import hf_rest, ledger, pricing
    if hf_rest.dry_run():
        return deny("HF_SUPERENGINE_DRY_RUN is set: no paid submit. Nothing was stamped or reserved.")
    try:
        ep = hf_rest.endpoint_arg(args[0])
        params, canon = hf_rest.load_params(args[1])
    except hf_rest.Fail as f:
        return deny(f.message)
    key = hf_rest.estimate_key(ep, canon)
    rec_path = hf_rest.guard_file("estimates", key)
    try:
        raw = rec_path.read_bytes()
        rec = json.loads(raw.decode("utf-8"))
    except FileNotFoundError:
        return deny(hf_rest.GATE_REASONS["no_estimate"])
    except (OSError, ValueError):
        return deny(hf_rest.GATE_REASONS["estimate_invalid"])
    psha = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    age = hf_rest._age(rec.get("created_at"), time.time()) if isinstance(rec, dict) else None
    if not isinstance(rec, dict) or (rec.get("v"), rec.get("kind"), rec.get("estimate_key"), rec.get("endpoint"),
                                     rec.get("params_sha256")) != (1, "hf-superengine-estimate", key, ep, psha) \
            or hf_rest._canon(rec.get("params")) != canon or age is None:
        return deny(hf_rest.GATE_REASONS["estimate_mismatch"])
    if not -hf_rest.SKEW <= age <= hf_rest.ESTIMATE_TTL:
        return deny(hf_rest.GATE_REASONS["estimate_stale" if age > 0 else "estimate_clock_skew"])

    v = pricing.price_bytes(raw)
    base = {"event": "spend_guard", "endpoint": ep, "estimate_key": key, "permission_mode": mode, "code": v["code"]}

    def finish(result, **kw):
        hf_rest._log(dict(base, decision=result["hookSpecificOutput"]["permissionDecision"], **kw))
        return result

    def stamp(decision, reason, usd):
        try:
            st = hf_rest.write_stamp(rec_path, decision)
            ok = json.loads(st.read_bytes().decode("utf-8")).get("record_sha256") == v["record_sha256"]
        except Exception:
            st, ok = hf_rest.guard_file("stamps", key), False
        if not ok:
            ledger.run(["refund", key, "--reason", "not_sent"])  # before the unlink: a missing stamp reads as spent
            try:
                st.unlink()
            except OSError:
                pass
            return finish(deny("the estimate record changed while it was being priced. Run estimate, then submit "
                               "again. Nothing was stamped."), usd=usd)
        return finish(out(decision, reason), usd=usd)

    def ledger_trouble(o):
        if o.get("class") == "duplicate_id":
            return finish(deny("an earlier submit of this exact request is still open in the ledger. If it was never "
                               "sent (a declined ask), it is released automatically about 90 s after it was stamped "
                               f"(or now: ledger.py refund {key} --reason not_sent); if it ran, wait for it and "
                               "settle it. Then submit again."))
        return finish(deny(f"the spend ledger could not be checked ({o.get('class')}: {o.get('message')}). Nothing "
                           "was stamped or reserved."))

    fig = v["display_usd"]
    held = ["--stamp", os.path.abspath(hf_rest.guard_file("stamps", key))]  # the ledger releases it if never spent
    price = f"about ${fig:.4f}".rstrip("0").rstrip(".") if fig is not None else "an unknown amount"
    if not v["ask"]:
        code, o = ledger.run(["reserve", amt(v["usd"]), "--id", key] + held)
        if code == 0:
            return stamp("allow", f"Higgsfield spend check: ${v['usd']} fits under the silent cap (24 h spend "
                                  f"${o.get('spent_24h')} of ${o.get('cap_usd')}). Reserved; stamp written.", v["usd"])
        if not (code == 3 and o.get("class") == "over_cap"):
            return ledger_trouble(o)
        why = (f"over the silent cap: ${o.get('spent_24h')} already spent in 24 h, cap ${o.get('cap_usd')} "
               f"({o.get('cap_basis')})")
    else:
        why = v["reason"]
    if mode == "dontAsk":  # every other mode shows the ask (bypassPermissions too: it honors a hook's ask)
        return finish(deny(f"{ep} costs {price} and needs the client's click ({why}), but nobody can be asked in "
                           f"permission mode {mode!r}. Nothing was sent, stamped or reserved."))
    code, o = ledger.run(["reserve", amt(fig) if fig is not None else "unknown", "--id", key, "--force"] + held)
    if code != 0:
        return ledger_trouble(o)
    return stamp("ask", f"Higgsfield spend check (higgsfield-superengine): {ep} costs {price}. Needs your OK: {why}. "
                        "Allow runs this ONE generation (answer within 60 seconds, or it has to be re-run); Deny "
                        "spends nothing.", fig)


# ---- entry ------------------------------------------------------------------------------------------------------

def hook(raw):
    data = json.loads(raw)
    tool = data.get("tool_name")
    ti = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    mode = data.get("permission_mode")
    if not isinstance(tool, str):
        return None
    if tool in ("Write", "Edit"):
        return files(ti, data.get("cwd"))
    if tool in SHELLS and isinstance(ti.get("command"), str):
        return shell(ti["command"], tool == "PowerShell", data.get("cwd"), mode, data)
    return None


def run_hook():
    raw = sys.stdin.buffer.read().decode("utf-8", "replace")
    try:
        result = hook(raw)
    except Exception as e:  # fail closed only where Higgsfield is involved
        low = raw.lower()
        result = None
        if any(m in low for m in MARKERS):
            result = deny(f"internal error in the hook ({type(e).__name__}), so this call is refused to be safe. "
                          "Nothing was stamped.")
    if result is None:
        return 0
    sys.stdout.write(json.dumps(result))
    if result["hookSpecificOutput"]["permissionDecision"] == "deny":
        sys.stderr.write(result["hookSpecificOutput"]["permissionDecisionReason"])
        return 2
    return 0


def main(argv):
    if argv == ["hook"]:
        return run_hook()
    if argv[:2] == ["hook", "--only-on"] and len(argv) == 3 and argv[2] in ("win32", "posix"):
        # hooks.json starts the guard twice (py on Windows, sh on Mac/Linux); exactly one of them decides
        here = "win32" if sys.platform == "win32" else "posix"
        return run_hook() if argv[2] == here else 0
    if argv[:1] == ["no-look"]:  # removed in 0.1.4; a no-op so an older setup step does not error
        print(json.dumps({"ok": True, "command": "no-look", "state": "clear",
                          "message": "The no-look guard was removed in 0.1.4; nothing to do."}))
        return 0
    if argv == ["--selftest"]:
        return selftest()
    print(__doc__)
    return 2


# ---- selftest ---------------------------------------------------------------------------------------------------

def selftest():
    """Offline. Temp workspace + temp per-user folder; hook processes get real-shaped JSON on stdin; hf_rest talks to a
    local mock that counts requests. Never the real API, key or ledger."""
    import shutil, subprocess, tempfile, threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    results = []
    me, hf = str(Path(__file__).resolve()), str(SCRIPTS / "hf_rest.py")
    tmp = Path(tempfile.mkdtemp(prefix="hf-guard-selftest-"))
    ws, cfg, home = tmp / "ws", tmp / "cfg", tmp / "home"
    for d in (ws, home):
        d.mkdir()
    hits = []

    class Mock(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n)
            hits.append(self.path)
            if self.path.startswith("/estimate/"):
                if b"five-hundred" in body:
                    self.send_response(500)
                    self.end_headers()
                    return
                ans = {"type": "estimate", "usd": "0.015", "credits": 3, "discount": None}
            else:
                ans = {"request_id": "req-selftest-0001", "status": "queued"}
            data = json.dumps(ans).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Mock)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    env = dict(os.environ, HF_SUPERENGINE_LEDGER_DIR=str(cfg), HF_SUPERENGINE_API_BASE=f"http://127.0.0.1:"
               f"{srv.server_address[1]}", HF_API_KEY_ID="selftestKEYid0001", HF_API_KEY_SECRET="selftestSECRETabcdef01",
               USERPROFILE=str(home), HOME=str(home), PYTHONDONTWRITEBYTECODE="1")
    env.pop("HF_SUPERENGINE_DRY_RUN", None)
    pycache_before = (SCRIPTS / "__pycache__").exists(), (HERE / "__pycache__").exists()

    def check(name, ok, detail=""):
        results.append(bool(ok))
        print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   [{detail}]"))

    def py(args, cwd=ws, extra=None):
        e = dict(env, **(extra or {}))
        r = subprocess.run([sys.executable, "-B"] + args, cwd=str(cwd), env=e, capture_output=True, timeout=60)
        return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")

    seq = [0]

    def ev(tool, ti, mode="default", cwd=ws, drop_mode=False):
        """A real-shaped event. Its transcript is empty on purpose: on Mac Desktop the tool_use row lands after
        PreToolUse fires (report 10.05.26), and the guard must not depend on it."""
        seq[0] += 1
        tp = tmp / "transcript.jsonl"
        tp.touch()
        d = {"session_id": "selftest", "transcript_path": str(tp), "cwd": str(cwd),
             "permission_mode": mode, "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti,
             "tool_use_id": f"toolu_selftest{seq[0]:04d}"}
        if drop_mode:
            d.pop("permission_mode")
        return d

    shapes_ok = []

    def run(event, proc_cwd=tmp, extra=None, args=("hook",)):
        e = dict(env, **(extra or {}))
        r = subprocess.run([sys.executable, "-B", me, *args], input=json.dumps(event).encode(), cwd=str(proc_cwd),
                           env=e, capture_output=True, timeout=60)
        text = r.stdout.decode("utf-8", "replace").strip()
        if not text:
            return r.returncode, None, ""
        o = json.loads(text)
        h = o.get("hookSpecificOutput", {})
        shapes_ok.append(h.get("hookEventName") == "PreToolUse" and isinstance(h.get("permissionDecisionReason"), str)
                         and h.get("permissionDecisionReason") and h.get("permissionDecision") in ("allow", "deny", "ask")
                         and (r.returncode == 2) == (h.get("permissionDecision") == "deny"))
        return r.returncode, h.get("permissionDecision"), h.get("permissionDecisionReason", "")

    def bash(cmd, **kw):
        return run(ev("Bash", {"command": cmd, "description": "x"}, **kw))

    def body(name, obj):
        (ws / name).write_text(json.dumps(obj), encoding="utf-8")
        return name

    def estimate(ep, name):
        return py([hf, "estimate", ep, name])

    def sub_cmd(ep, name, py_tok=None):
        return f'{py_tok or "python"} "{hf}" submit {ep} {name}'

    def stamp_of(ep, name):
        sys.path.insert(0, str(SCRIPTS))
        import hf_rest
        _, canon = hf_rest.load_params(ws / name)
        key = hf_rest.estimate_key(ep, canon)
        p = ws / hf_rest.guard_file("stamps", key)
        return key, (json.loads(p.read_text(encoding="utf-8")) if p.exists() else None), p

    def ledger(*a):
        c, o, _ = py([str(SCRIPTS / "ledger.py")] + list(a))
        return c, json.loads(o)

    try:
        ep = "z-image/turbo"
        # --- done-test: with no hook, submit refuses (the stamp gate) --------------------------------------------
        b1 = body("b1.json", {"prompt": "a red mug on a table"})
        c, o, _ = estimate(ep, b1)
        n0 = len(hits)
        c, o, e = py([hf, "submit", ep, b1])
        j = json.loads(o)
        check("D1 done-test: hook removed -> hf_rest submit refuses (exit 3 spend_gate_refused no_stamp), 0 POSTs",
              c == 3 and j.get("class") == "spend_gate_refused" and j.get("reason") == "no_stamp" and len(hits) == n0,
              o[:200])

        # --- under the cap: allow + stamp + reservation; the stamp then works for exactly one submit ------------
        c, d, r = bash(sub_cmd(ep, b1))
        key, st, stp = stamp_of(ep, b1)
        c2, led = ledger("status")
        ent = [x for x in led.get("entries", []) if x["id"] == key]
        check("S1 valid estimate under the cap -> allow, stamp 'allow' written (CONTRACT fields), $0.015 reserved",
              d == "allow" and c == 0 and st and st["decision"] == "allow" and st["estimate_key"] == key and
              len(st["nonce"]) == 32 and ent and abs(ent[0]["reserved"] - 0.015) < 1e-9, f"{d} {r} {st} {ent}")
        n0 = len(hits)
        c, o, e = py([hf, "submit", ep, b1])
        check("S2 hf_rest submit with that stamp -> exit 0, exactly 1 POST; a second submit refuses (no_stamp)",
              c == 0 and len(hits) == n0 + 1 and py([hf, "submit", ep, b1])[0] == 3 and len(hits) == n0 + 1, o[:200])
        ledger("settle", key)

        # --- hook cwd: the body and records resolve against the input cwd, not the hook process's folder --------
        c, d, r = run(ev("PowerShell", {"command": sub_cmd(ep, b1)}), proc_cwd=home)
        check("S3 PowerShell submit, hook process started elsewhere -> resolves against input cwd -> allow",
              d == "allow", f"{d} {r}")
        ledger("refund", key, "--reason", "not_sent")

        # --- unattended modes --------------------------------------------------------------------------------
        c, d, r = bash(sub_cmd(ep, b1), mode="bypassPermissions")
        check("S4 bypassPermissions + under the cap -> allow (the silent cap needs no click)", d == "allow", r)
        ledger("refund", key, "--reason", "not_sent")

        # --- over the cap -> ask, reserved with --force ----------------------------------------------------------
        ledger("balance", "set", "0.04")  # cap = 25% = $0.01 < $0.015
        c, d, r = bash(sub_cmd(ep, b1))
        key, st, stp = stamp_of(ep, b1)
        _, led = ledger("status")
        ent = [x for x in led.get("entries", []) if x["id"] == key]
        check("S5 over the cap -> ask (reason shows the price), stamp 'ask', forced reservation $0.015",
              d == "ask" and c == 0 and st["decision"] == "ask" and "0.015" in r and ent and ent[0]["forced"],
              f"{d} {r} {ent}")
        ledger("refund", key, "--reason", "not_sent")
        stp.unlink()
        for mode, drop in (("bypassPermissions", False), ("default", True)):
            c, d, r = bash(sub_cmd(ep, b1), mode=mode, drop_mode=drop)
            key, st, stp = stamp_of(ep, b1)
            check(f"S6 over the cap, permission_mode {'missing' if drop else mode} -> ask (a real click; bypass "
                  "honors a hook's ask), stamp 'ask'", d == "ask" and c == 0 and st and st["decision"] == "ask",
                  f"{d} {r}")
            ledger("refund", key, "--reason", "not_sent")
            stp.unlink()
        c, d, r = bash(sub_cmd(ep, b1), mode="dontAsk")
        _, led = ledger("status")
        log = (ws / "higgsfield" / time.strftime("%Y-%m-%d") / "log.jsonl").read_text(encoding="utf-8")
        logged = [x for x in map(json.loads, log.splitlines()) if x.get("event") == "spend_guard" and
                  x.get("decision") == "deny" and x.get("permission_mode") == "dontAsk"]
        check("S6 over the cap, permission_mode dontAsk (nobody can be asked) -> deny, no stamp, nothing reserved, "
              "deny logged", d == "deny" and c == 2 and stamp_of(ep, b1)[1] is None and not led["entries"] and logged,
              f"{d} {r}")
        ledger("balance", "set", "100")

        # --- an ask verdict (5xx estimate: unpriced) -> ask + reserve unknown ($5) ---------------------------------
        b2 = body("b2.json", {"prompt": "five-hundred"})
        estimate(ep, b2)
        c, d, r = bash(sub_cmd(ep, b2))
        key2, st, stp = stamp_of(ep, b2)
        _, led = ledger("status")
        ent = [x for x in led["entries"] if x["id"] == key2]
        check("S7 unpriced estimate (HTTP 500) -> ask, stamp 'ask', reserve unknown --force = $5",
              d == "ask" and st["decision"] == "ask" and ent and ent[0]["reserved"] == 5.0 and
              not ent[0]["amount_known"], f"{d} {r} {ent}")
        c, d, r = bash(sub_cmd(ep, b2))
        check("S8 same request again while its entry is open -> deny duplicate (refund/settle first)",
              d == "deny" and "refund" in r, r)
        ledger("refund", key2, "--reason", "not_sent")

        # --- a declined ask releases its reservation; a consumed one keeps it ----------------------------------
        def age_all(ep_, name_, secs):
            k, _, sp = stamp_of(ep_, name_)
            if sp.exists():
                os.utime(sp, (time.time() - secs, time.time() - secs))
            d = json.loads((cfg / "ledger.json").read_text(encoding="utf-8"))
            for x in d["entries"]:
                if x["id"] == k and x["state"] == "pending":
                    x["created_at"] -= secs
            (cfg / "ledger.json").write_text(json.dumps(d), encoding="utf-8")
            return k

        c, d, r = bash(sub_cmd(ep, b2))  # the unpriced request: ask, reserves $5
        k = age_all(ep, b2, 100)  # the client clicked Deny; 100 s pass; nothing ran
        _, led = ledger("status")
        ent = [x for x in json.loads((cfg / "ledger.json").read_text())["entries"] if x["id"] == k][-1]
        check("S16 ask declined (stamp never consumed) -> after the stamp life the reservation is released "
              "(refunded not_sent); the same request can be asked again", d == "ask" and ent["state"] == "refunded"
              and ent["reason"] == "not_sent" and bash(sub_cmd(ep, b2))[1] == "ask", f"{d} {ent}")
        n0 = len(hits)
        c, o, e = py([hf, "submit", ep, b2])  # the client clicked Allow: submit consumes the ask stamp
        k = age_all(ep, b2, 100)
        _, led = ledger("status")
        ent = [x for x in led["entries"] if x["id"] == k]
        check("S17 ask approved (stamp consumed, 1 POST) -> the reservation stays pending after the stamp life",
              c == 0 and len(hits) == n0 + 1 and ent and ent[0]["state"] == "pending", f"{c} {o[:150]} {ent}")
        c, o = ledger("refund", k, "--reason", "not_sent")
        _, led = ledger("status")
        check("S18 after a submit used the stamp, 'refund not_sent' is refused (exit 3 stamp_consumed), entry stays",
              c == 3 and o.get("class") == "stamp_consumed" and
              [x for x in led["entries"] if x["id"] == k][0]["state"] == "pending", f"{c} {o}")
        ledger("refund", k, "--reason", "job_failed")

        # --- refusals on the submit path ----------------------------------------------------------------------
        b3 = body("b3.json", {"prompt": "never estimated"})
        check("S9 no estimate on file -> deny", bash(sub_cmd(ep, b3))[1] == "deny")
        fake = ws / "hf_rest.py"
        fake.write_bytes((SCRIPTS / "hf_rest.py").read_bytes() + b"\n# edited\n")
        check("S10 an edited copy of hf_rest.py -> deny", bash(f'python "{fake}" submit {ep} {b1}')[1] == "deny")
        check("S11 HF_SUPERENGINE_DRY_RUN in the hook's env -> deny",
              run(ev("Bash", {"command": sub_cmd(ep, b1)}), extra={"HF_SUPERENGINE_DRY_RUN": "1"})[1] == "deny")
        check("S12 submit chained after cd -> deny", bash(f'cd "{ws}" && ' + sub_cmd(ep, b1))[1] == "deny")
        ok1 = bash(sub_cmd(ep, b1, BASH_PY))[1] == "allow"
        ledger("refund", key, "--reason", "not_sent")
        ok2 = run(ev("PowerShell", {"command": sub_cmd(ep, b1, "& (Get-Content -Raw -Encoding UTF8 "
                                                                "higgsfield\\.python)")}))[1] == "allow"
        ledger("refund", key, "--reason", "not_sent")
        check("S13 recorded-interpreter forms accepted: bash \"$(cat higgsfield/.python)\", PS & (Get-Content ...)",
              ok1 and ok2)
        stamp_of(ep, b1)[2].unlink(missing_ok=True)
        (cfg / "ledger.json").write_text("not json", encoding="utf-8")
        c, d, r = bash(sub_cmd(ep, b1))
        check("S14 corrupt ledger -> deny (fail closed), no stamp", d == "deny" and stamp_of(ep, b1)[1] is None, r)
        (cfg / "ledger.json").unlink()
        # in-process: the record changes between pricing and stamping -> the stamp is removed, the reservation refunded
        import hf_rest
        real_ws, old_cwd, old_env = hf_rest.write_stamp, os.getcwd(), dict(os.environ)

        def racing_write_stamp(path, decision, now=None):
            p = Path(path)
            p.write_bytes(p.read_bytes().replace(b'"created_at": ', b'"created_at":  '))  # same record, new bytes
            return real_ws(path, decision, now)
        try:
            os.environ.update(HF_SUPERENGINE_LEDGER_DIR=str(cfg))
            os.environ.pop("HF_SUPERENGINE_DRY_RUN", None)
            hf_rest.write_stamp = racing_write_stamp
            res = submit(hf, [ep, b1], str(ws), "default", ev("Bash", {"command": sub_cmd(ep, b1)}))
        finally:
            hf_rest.write_stamp = real_ws
            os.chdir(old_cwd)
            os.environ.clear()
            os.environ.update(old_env)
        _, led = ledger("status")
        check("S15 record changed between pricing and stamping -> deny, stamp removed, reservation refunded",
              res["hookSpecificOutput"]["permissionDecision"] == "deny" and stamp_of(ep, b1)[1] is None and
              not led["entries"], res)

        # --- Mac Desktop race (report 10.05.26): no transcript row for the submit is fine -------------------------
        c, d, r = bash(sub_cmd(ep, b1))
        k_m = stamp_of(ep, b1)[0]
        ledger("refund", k_m, "--reason", "not_sent")
        stamp_of(ep, b1)[2].unlink(missing_ok=True)
        e_none = ev("Bash", {"command": sub_cmd(ep, b1)})
        e_none.pop("transcript_path")
        c2, d2, r2 = run(e_none)
        ledger("refund", k_m, "--reason", "not_sent")
        stamp_of(ep, b1)[2].unlink(missing_ok=True)
        check("M1 the transcript has no row for this submit yet (Mac race), or no transcript_path -> allow under "
              "the cap", d == "allow" and d2 == "allow", f"{d} {r} | {d2} {r2}")

        # --- deny list ------------------------------------------------------------------------------------------
        denies = [
            ("Bash", 'curl -s -X POST https://api.higgsfield.ai/v1/text2image -H "Authorization: Key $HF_API_KEY_ID"'),
            ("PowerShell", 'Invoke-WebRequest -Uri "https://API.Higgsfield.ai/requests/x" -Method Post'),
            ("Bash", "higgsfield generate --model soul 'a cat'"),
            ("Bash", "npx @higgsfield/cli auth login"),
            ("Bash", "pip install higgsfield-client"),
            ("Bash", 'python -c "import hf_rest; hf_rest.call(\'POST\', \'/x\', b\'{}\')"'),
            ("Bash", f'python - <<EOF\nimport sys; sys.path.insert(0, r"{SCRIPTS}")\nimport hf_rest\nEOF'),
            ("PowerShell", f'python -m hf_rest submit {ep} b1.json'),
            ("Bash", "echo '{}' > higgsfield/.spend-guard/stamps/abc.json"),
            ("PowerShell", "Move-Item higgsfield\\.spend-guard\\used\\x.json higgsfield\\.spend-guard\\stamps\\x.json"),
            ("PowerShell", "Remove-Item -Recurse $HOME\\.config\\higgsfield-superengine"),
            ("Bash", "rm ~/.config/higgsfield-superengine/ledger.json"),
            ("Bash", f'HF_SUPERENGINE_LEDGER_DIR=/tmp/x python "{SCRIPTS}/ledger.py" status'),
            ("Bash", f'python -c "import sys; sys.path.insert(0, r\'{SCRIPTS}\'); import ledger"'),
            ("Monitor", f'python "{hf}" submit {ep} b1.json | tee out.txt'),
        ]
        for tool, cmd in denies:
            c, d, r = run(ev(tool, {"command": cmd}))
            check(f"X {tool}: {cmd[:70]!r} -> deny", d == "deny" and c == 2, f"{d} {r}")
        for tool, ti in (("Write", {"file_path": str(ws / "higgsfield" / ".spend-guard" / "stamps" / "a.json"),
                                    "content": "{}"}),
                         ("Edit", {"file_path": str(home / ".config" / "higgsfield-superengine" / "no-look.json"),
                                   "old_string": "on", "new_string": "leaving"}),
                         ("Write", {"file_path": str(ws / "go.py"), "content": "import hf_rest\nhf_rest.call()"}),
                         ("Write", {"file_path": str(home) + "/.config/./higgsfield-superengine/ledger.json",
                                    "content": "{}"}),
                         ("Edit", {"file_path": str(ws / "x" / ".." / "higgsfield" / ".spend-guard" / "s.json"),
                                   "old_string": "a", "new_string": "b"})):
            c, d, r = run(ev(tool, ti))
            check(f"X {tool} {ti['file_path'][-48:]} -> deny", d == "deny", r)
        (ws / "attack.md").write_text(f'import sys; sys.path.insert(0, r"{SCRIPTS}"); import hf_rest', encoding="utf-8")
        (ws / "notes.md").write_text("print('hello')", encoding="utf-8")
        c, d, r = bash('python attack.md')
        c2, d2, r2 = bash('py -3 notes.md')
        check("X `python attack.md` (a script of any extension that mentions hf_rest) -> deny; a plain script -> "
              "untouched; `python \"<plugin>/scripts/...\"` stays allowed (P below)", d == "deny" and d2 is None,
              f"{d} {d2}")
        c, d, r = bash(f'echo x > "{home}/.config/./higgsfield-superengine/no-look.json"')
        check("X a command touching .config/./higgsfield-superengine -> deny", d == "deny", r)

        # --- pass-through ---------------------------------------------------------------------------------------
        passes = [("Bash", "npm test"), ("Bash", "git status && ls -la"), ("PowerShell", "Get-ChildItem"),
                  ("Bash", "ls higgsfield/2026-09-29"), ("Bash", f'python "{hf}" estimate {ep} b1.json'),
                  ("PowerShell", f'& python "{hf}" wait req-selftest-0001 --timeout 540 2>&1'),
                  ("Bash", f'python "{SCRIPTS}/ledger.py" refund {key} --reason not_sent'),
                  ("Bash", 'python -c "import ledger"'), ("Bash", "curl https://docs.higgsfield.ai/llms-full.txt")]
        for tool, cmd in passes:
            c, d, r = run(ev(tool, {"command": cmd}))
            check(f"P {tool}: {cmd[:60]!r} -> untouched (no output, exit 0)", d is None and c == 0, f"{c} {d} {r}")
        for tool, ti in (("Write", {"file_path": str(ws / "notes.md"), "content": "run hf_rest.py estimate"}),
                         ("Read", {"file_path": str(ws / "b1.json")}), ("Monitor", {"ws": {"url": "wss://x.test"}}),
                         ("mcp__Claude_Browser__computer", {"action": "screenshot"}),
                         ("mcp__memory__create_entities", {})):
            c, d, r = run(ev(tool, ti))
            check(f"P {tool} -> untouched", d is None and c == 0, f"{c} {d} {r}")
        c, d, r = run({"garbage": True})
        check("P a malformed hook input with no Higgsfield marker -> untouched", d is None and c == 0)
        r2 = subprocess.run([sys.executable, "-B", me, "hook"], input=b'{"tool_name":"Bash","tool_input":{"command":'
                            b'"curl api.higgsfield.ai"', cwd=str(tmp), env=env, capture_output=True, timeout=60)
        check("F unparsable hook input that mentions Higgsfield -> deny (fail closed), exit 2",
              r2.returncode == 2 and b'"deny"' in r2.stdout)

        # --- plumbing -------------------------------------------------------------------------------------------
        here, other = ("win32", "posix") if sys.platform == "win32" else ("posix", "win32")
        probe = ev("Bash", {"command": "echo api.higgsfield.ai", "description": "x"})
        check(f"O1 hook --only-on {here} (this OS) decides like plain hook: the raw-API echo is denied",
              run(probe, args=("hook", "--only-on", here))[:2] == (2, "deny") == run(probe)[:2])
        r_other = subprocess.run([sys.executable, "-B", me, "hook", "--only-on", other], input=json.dumps(probe)
                                 .encode(), cwd=str(tmp), env=env, capture_output=True, timeout=60)
        check(f"O2 hook --only-on {other} (the other OS) is silent: exit 0, no output, so one guard decides per OS",
              r_other.returncode == 0 and not r_other.stdout.strip() and not r_other.stderr.strip())
        check("H every decision carried hookEventName + permissionDecisionReason (and deny <=> exit 2): "
              f"{len(shapes_ok)} decisions", shapes_ok and all(shapes_ok))
        hj = json.loads((HERE / "hooks.json").read_text(encoding="utf-8"))
        pre = hj["hooks"]["PreToolUse"]
        m_all = [re.compile(g["matcher"]) if not re.fullmatch(r"[\w|, -]+", g["matcher"]) else
                 (lambda s, names=[x.strip() for x in re.split(r"[|,]", g["matcher"])]: s in names) for g in pre]

        def fires(name):
            return any(m(name) if callable(m) else m.search(name) for m in m_all)

        cmds = [h for g in pre for h in g["hooks"]]
        check("H hooks.json: guard fires for Bash/PowerShell/Monitor/Write/Edit, not for Read or browser/screen "
              "tools (no-look removed in 0.1.4); timeout 30 > the 10 s ledger lock; UserPromptSubmit NOT registered",
              all(fires(t) for t in ("Bash", "PowerShell", "Monitor", "Write", "Edit")) and not fires("Read")
              and not fires("mcp__Claude_Browser__computer") and not fires("mcp__computer-use__screenshot")
              and all(sorted((h["command"], tuple(h["args"])) for h in g["hooks"]) == sorted([
                  ("py", ("-3", "-B", "${CLAUDE_PLUGIN_ROOT}/hooks/hf_guard.py", "hook", "--only-on", "win32")),
                  ("sh", ("${CLAUDE_PLUGIN_ROOT}/hooks/hf-guard.sh",))]) for g in pre)
              and all(h["timeout"] >= 30 for h in pre[0]["hooks"]) and "UserPromptSubmit" not in hj["hooks"])
        launcher = (HERE / "hf-guard.sh").read_text(encoding="utf-8")
        check("H hf-guard.sh starts hf_guard.py with hook --only-on posix and stands down unless Darwin/Linux",
              'hook --only-on posix' in launcher and "Darwin|Linux" in launcher)
        check("H no __pycache__ created in the plugin", pycache_before == ((SCRIPTS / "__pycache__").exists(),
                                                                           (HERE / "__pycache__").exists()))
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
