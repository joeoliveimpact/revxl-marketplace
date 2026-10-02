#!/usr/bin/env python3
"""hf_guard.py - the PreToolUse hooks of the higgsfield-superengine plugin. Standard library only, Python 3.9+.

  hf_guard.py hook                      the hook (hooks.json): one PreToolUse JSON on stdin -> a decision or nothing
  hf_guard.py no-look on|off|status     the no-look flag (higgsfield-setup). "off" is the client's confirmation:
                                        the hook turns that command into a real click ("ask")
  hf_guard.py --selftest                offline checks: real hook processes fed real-shaped hook JSON

4.1 Spend guard (Bash, PowerShell, Monitor, Write, Edit). Commands that do not touch Higgsfield pass untouched.
  hf_rest.py submit  estimate record matches + fresh -> pricing.py -> ledger.py reserve -> stamp (CONTRACT v1):
                     priced and under the cap -> stamp "allow" + allow; over the cap or an ask verdict -> reserve
                     (--force) + stamp "ask" + ask (a real click); nobody to ask (dontAsk, bypassPermissions, or
                     no permission_mode) -> deny + log, nothing reserved or stamped. Anything wrong -> deny.
                     Real call only: the event's transcript must hold this exact tool call (same tool_use_id and
                     command) still pending, so a hand-built event piped into `hf_guard.py hook` never stamps.
  deny               api.higgsfield.ai, the higgsfield CLI / SDK, any other way into hf_rest (import, -c, -m,
                     chaining, a script that mentions it), anything touching higgsfield/.spend-guard/ or
                     ~/.config/higgsfield-superengine/, HF_SUPERENGINE_LEDGER_DIR, ad-hoc `import ledger`.
4.2 No-look guard (Claude_Browser, computer-use, claude-in-chrome, Claude_Preview tools), flag = no-look.json in
  the per-user folder (ledger.ledger_dir()): "on" < 10 min -> deny every tool; "on" older -> ask (deny when nobody
  is watching); "leaving" (after the confirmed "off") -> only navigate passes, and it clears the flag.
Every decision carries hookEventName + permissionDecisionReason. A deny also exits 2 (blocks even if the JSON were
dropped). Internal error: deny if the call touches Higgsfield (or is a browser tool), else pass.
"""
import hashlib, json, os, re, secrets, sys, time
from pathlib import Path

sys.dont_write_bytecode = True  # importing hf_rest/pricing/ledger must not leave __pycache__ in the plugin
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
ATTENDED = {"default", "acceptEdits", "plan", "auto"}  # someone can answer an "ask"
NO_LOOK_TTL = 600  # seconds a fresh flag blocks outright; after that every look asks
BROWSER_RE = re.compile(r"^mcp__(Claude_Browser|computer[-_]use|claude-in-chrome|Claude_Preview)__")
NAVIGATE = {"mcp__Claude_Browser__navigate", "mcp__claude-in-chrome__navigate"}  # text-only result, no screenshot
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


def cfg_dir():
    """Same folder as ledger.ledger_dir(): the per-user plugin folder (the selftest checks they agree)."""
    return Path(os.environ.get("HF_SUPERENGINE_LEDGER_DIR") or os.path.expanduser("~/.config/higgsfield-superengine"))


def flag_path():
    return cfg_dir() / "no-look.json"


# ---- 4.2 no-look ------------------------------------------------------------------------------------------------

def read_flag():
    """None = no flag. Raises on an unreadable or malformed flag (the caller denies)."""
    try:
        raw = flag_path().read_bytes()
    except FileNotFoundError:
        return None
    f = json.loads(raw.decode("utf-8"))
    if not (isinstance(f, dict) and f.get("state") in ("on", "leaving") and isinstance(f.get("set_at"), (int, float))
            and not isinstance(f.get("set_at"), bool)):
        raise ValueError("malformed no-look flag")
    return f


def write_flag(state):
    p = flag_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f"{p.name}.{secrets.token_hex(3)}.tmp")
    tmp.write_bytes(json.dumps({"v": 1, "kind": "hf-superengine-no-look", "state": state,
                                "set_at": time.time()}).encode())
    os.replace(tmp, p)


def no_look(tool, mode):
    try:
        f = read_flag()
    except Exception:
        return out("deny", "No-look guard: the no-look flag is unreadable, so the screen is treated as showing an "
                           "API key. Ask the client to confirm the key is off screen, then run hf_guard.py no-look off.")
    if f is None:
        return None
    age = time.time() - f["set_at"]
    if f["state"] == "leaving":
        if tool in NAVIGATE:
            flag_path().unlink()
            return None  # navigating away (text-only result) completes the client's "off"
        return out("deny", "No-look guard: the client confirmed the key is off screen. Navigate the browser away from "
                           "the key page first (the navigate tool on its own); that clears the flag.")
    if age <= NO_LOOK_TTL:
        return out("deny", "No-look guard: an API key may be on screen (setup no-look window, "
                           f"{int(age)} s old). Do not look at the screen or page. Wait until the client says the "
                           "key is saved and off screen, then run hf_guard.py no-look off.")
    if mode not in ATTENDED:
        return out("deny", "No-look guard: the no-look window expired without the client's confirmation, and nobody "
                           "can be asked in this permission mode. Do not look at the screen.")
    return out("ask", "higgsfield-superengine no-look check: the setup no-look window expired without confirmation. "
                      "Is the API key off the screen? Allow lets Claude look at the browser/screen this once.")


def cmd_no_look(argv):
    if argv not in (["on"], ["off"], ["status"]):
        print(json.dumps({"ok": False, "class": "usage", "message": "usage: hf_guard.py no-look on|off|status"}))
        return 2
    try:
        if argv == ["on"]:
            write_flag("on")
        elif argv == ["off"] and read_flag_quiet() is not None:
            write_flag("leaving")
        f = read_flag_quiet()
    except OSError as e:
        print(json.dumps({"ok": False, "class": "local_io_error", "message": type(e).__name__}))
        return 1
    state = "clear" if f is None else ("expired" if f["state"] == "on" and time.time() - f["set_at"] > NO_LOOK_TTL
                                       else f["state"])
    msg = {"on": "No-look is ON: every browser/screen tool is blocked. Clear it only after the client confirms.",
           "expired": "No-look expired: every browser/screen tool asks first. Run no-look off after the client "
                      "confirms.",
           "leaving": "Client confirmed. Navigate the browser away from the key page (navigate tool); that clears it.",
           "clear": "No-look is off."}[state]
    print(json.dumps({"ok": True, "command": "no-look", "state": state, "message": msg}))
    return 0


def read_flag_quiet():
    try:
        return read_flag()
    except (ValueError, UnicodeDecodeError):
        return {"state": "on", "set_at": 0}  # malformed: treated as an expired "on"; "off" overwrites it


# ---- 4.1 spend guard: files -------------------------------------------------------------------------------------

def guarded_path(p):
    n = p.replace("\\", "/").lower()
    return re.search(r"(^|/)\.spend-guard(/|$)", n) or re.search(r"(^|/)\.config/+higgsfield-superengine(/|$)", n)


def files(ti):
    fp = ti.get("file_path")
    fp = fp if isinstance(fp, str) else ""
    if guarded_path(fp):
        return deny("the spend guard's files (higgsfield/.spend-guard/) and the per-user folder "
                    "(~/.config/higgsfield-superengine: ledger, no-look flag) are written only by the plugin's scripts. "
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


def shell(cmd, ps, cwd, mode, ev=None):
    low = cmd.lower()
    if not any(m in low for m in MARKERS) and not LEDGER_IMPORT.search(cmd):
        return None
    if "api.higgsfield.ai" in low:
        return deny("direct calls to api.higgsfield.ai skip the price check and the spend cap. Use the plugin's "
                    "hf_rest.py (estimate, then submit).")
    if any(m in low for m in SDK) or cli_used(cmd):
        return deny("the higgsfield CLI and SDKs skip the price check and the spend cap. Use the plugin's hf_rest.py.")
    if "spend-guard" in low or CONFIG_DIR.search(cmd) or GUARD_NAMES.search(low):
        return deny("the spend guard's files (higgsfield/.spend-guard/) and the per-user folder "
                    "(~/.config/higgsfield-superengine: ledger, no-look flag) are touched only by the plugin's "
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
        if not real_call(ev, cmd):
            return deny("this submit is not a real pending tool call in this session's transcript (a hand-built "
                        "hook event, or a script calling the hook). Nothing was stamped or reserved. Run the submit "
                        "as its own tool call so the client sees the real permission prompt.")
        return submit(p[0], p[1][1:], cwd, mode)
    if name == "hf_guard.py":
        if p[1] == ["no-look", "off"]:
            if mode not in ATTENDED:
                return deny("no-look off needs the client's confirmation, and nobody can be asked in this permission "
                            "mode. The flag stays; it asks before every look once it expires.")
            return out("ask", "higgsfield-superengine no-look check: has the client finished with the API key, and "
                              "is it off the screen (dialog closed)? Allow = yes, Claude may navigate the browser away "
                              "and look again.")
        return None
    return deny("hf_rest.py and hf_guard.py may not be imported, wrapped or chained. " + PLAIN)


TRANSCRIPT_TAIL = 8 * 1024 * 1024  # bytes read from the end of the transcript; the pending call is near the end


def real_call(ev, cmd):
    """True only if the event's transcript holds this exact tool call (tool_use_id + command) with no result yet.
    A hand-built event fed to `hf_guard.py hook` (by a pipe or a runner script) either has no such call, or points at
    an older call that already has a result. Real events: Claude Code writes the tool_use before PreToolUse fires
    (checked 10.01.26 with a headless probe hook)."""
    # ponytail: protects only sessions where this hook runs; with the plugin disabled nothing guards the scripts
    tp, tid = (ev or {}).get("transcript_path"), (ev or {}).get("tool_use_id")
    if not (isinstance(tp, str) and tp and isinstance(tid, str) and tid):
        return False
    try:
        with open(tp, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - TRANSCRIPT_TAIL))
            lines = f.read().splitlines()
    except OSError:
        return False
    found = False
    for line in lines:
        try:
            o = json.loads(line)
        except ValueError:
            continue
        m = o.get("message") if isinstance(o, dict) else None
        content = m.get("content") if isinstance(m, dict) else None
        for c in content if isinstance(content, list) else ():
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use" and c.get("id") == tid:
                found = isinstance(c.get("input"), dict) and c["input"].get("command") == cmd
            elif c.get("type") == "tool_result" and c.get("tool_use_id") == tid:
                found = False  # that call already ran (or was refused): not the one pending now
    return found


def in_plugin(cwd):
    try:
        return isinstance(cwd, str) and Path(cwd).resolve().is_relative_to(HERE.parent)
    except (AttributeError, OSError, ValueError):  # is_relative_to is 3.9+
        return False


def amt(x):
    return f"{x:.9f}".rstrip("0").rstrip(".")


def submit(script, args, cwd, mode):
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
            try:
                st.unlink()
            except OSError:
                pass
            ledger.run(["refund", key, "--reason", "not_sent"])
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
    if mode not in ATTENDED:
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
    if BROWSER_RE.match(tool):
        return no_look(tool, mode)
    if tool in ("Write", "Edit"):
        return files(ti)
    if tool in SHELLS and isinstance(ti.get("command"), str):
        return shell(ti["command"], tool == "PowerShell", data.get("cwd"), mode, data)
    return None


def run_hook():
    raw = sys.stdin.buffer.read().decode("utf-8", "replace")
    try:
        result = hook(raw)
    except Exception as e:  # fail closed only where Higgsfield (or the screen) is involved
        low = raw.lower()
        result = None
        if any(m in low for m in MARKERS) or re.search(r'"tool_name"\s*:\s*"' + BROWSER_RE.pattern[1:], raw):
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
    if argv[:1] == ["no-look"]:
        return cmd_no_look(argv[1:])
    if argv == ["--selftest"]:
        return selftest()
    print(__doc__)
    return 2


# ---- selftest ---------------------------------------------------------------------------------------------------

def selftest():
    """Offline. Temp workspace + temp per-user folder; hook processes get real-shaped JSON on stdin; hf_rest talks to a
    local mock that counts requests. Never the real API, key, ledger or no-look flag."""
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

    def use(tid, tool, ti):
        return {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": tid, "name": tool, "input": ti}]}}

    def ev(tool, ti, mode="default", cwd=ws, drop_mode=False, lines=None):
        """A real-shaped event plus its transcript. lines(tid) overrides the transcript (default: this call pending)."""
        seq[0] += 1
        tid, tp = f"toolu_selftest{seq[0]:04d}", tmp / f"t{seq[0]}.jsonl"
        rows = lines(tid) if lines else [use(tid, tool, ti)]
        tp.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
        d = {"session_id": "selftest", "transcript_path": str(tp), "cwd": str(cwd),
             "permission_mode": mode, "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti,
             "tool_use_id": tid}
        if drop_mode:
            d.pop("permission_mode")
        return d

    shapes_ok = []

    def run(event, proc_cwd=tmp, extra=None):
        e = dict(env, **(extra or {}))
        r = subprocess.run([sys.executable, "-B", me, "hook"], input=json.dumps(event).encode(), cwd=str(proc_cwd),
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
        for mode, drop in (("dontAsk", False), ("bypassPermissions", False), ("default", True)):
            c, d, r = bash(sub_cmd(ep, b1), mode=mode, drop_mode=drop)
            _, led = ledger("status")
            log = (ws / "higgsfield" / time.strftime("%Y-%m-%d") / "log.jsonl").read_text(encoding="utf-8")
            logged = [x for x in map(json.loads, log.splitlines()) if x.get("event") == "spend_guard" and
                      x.get("decision") == "deny" and x.get("permission_mode") == (None if drop else mode)]
            check(f"S6 over the cap, permission_mode {'missing' if drop else mode} -> deny, no stamp, nothing "
                  "reserved, deny logged", d == "deny" and c == 2 and stamp_of(ep, b1)[1] is None and
                  not led["entries"] and logged, f"{d} {r}")
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
        ledger("refund", k, "--reason", "not_sent")

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
            res = submit(hf, [ep, b1], str(ws), "default")
        finally:
            hf_rest.write_stamp = real_ws
            os.chdir(old_cwd)
            os.environ.clear()
            os.environ.update(old_env)
        _, led = ledger("status")
        check("S15 record changed between pricing and stamping -> deny, stamp removed, reservation refunded",
              res["hookSpecificOutput"]["permissionDecision"] == "deny" and stamp_of(ep, b1)[1] is None and
              not led["entries"], res)

        # --- real call only: a hand-built hook event never stamps (JOI-016, 09.30.26) ---------------------------
        cmd1 = sub_cmd(ep, b1)
        pipe = f"echo '<event>' | python \"{me}\" hook"

        def clean():
            return stamp_of(ep, b1)[1] is None and not ledger("status")[1].get("entries")

        attacks = [
            ("R1 hand-built event piped into the hook (the newest call is the pipe) -> deny, nothing stamped",
             lambda tid: [use(tid + "x", "Bash", {"command": pipe})]),
            ("R2 replays the id of an older real submit that already has a result -> deny, nothing stamped",
             lambda tid: [use(tid, "Bash", {"command": cmd1}),
                          {"type": "user", "message": {"role": "user", "content": [
                              {"type": "tool_result", "tool_use_id": tid, "content": "denied", "is_error": True}]}},
                          use(tid + "x", "Bash", {"command": pipe})]),
            ("R3 same id, different command in the transcript -> deny",
             lambda tid: [use(tid, "Bash", {"command": cmd1 + " --x"})]),
            ("R4 a transcript with no tool calls (a runner script's) -> deny", lambda tid: []),
        ]
        for name, lines in attacks:
            c, d, r = run(ev("Bash", {"command": cmd1}, lines=lines))
            check(name, d == "deny" and c == 2 and clean(), f"{d} {r}")
        e5 = ev("Bash", {"command": cmd1})
        e5.pop("transcript_path")
        e6 = ev("Bash", {"command": cmd1})
        e6["transcript_path"] = str(tmp / "missing.jsonl")
        check("R5 no transcript_path, or the transcript file is missing -> deny, nothing stamped",
              run(e5)[1] == "deny" and run(e6)[1] == "deny" and clean())
        c, d, r = run(ev("Bash", {"command": cmd1}, lines=lambda tid: [{"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": tid, "name": "Bash", "input": {"command": cmd1}},
            {"type": "tool_use", "id": "toolu_other", "name": "Read", "input": {"file_path": "x"}}]}}]))
        check("R6 the real call inside a parallel batch (not the last tool_use) -> allow", d == "allow", f"{d} {r}")
        ledger("refund", key, "--reason", "not_sent")
        stamp_of(ep, b1)[2].unlink(missing_ok=True)

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
                         ("Write", {"file_path": str(ws / "go.py"), "content": "import hf_rest\nhf_rest.call()"})):
            c, d, r = run(ev(tool, ti))
            check(f"X {tool} {Path(ti['file_path']).name} -> deny", d == "deny", r)

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
                         ("mcp__memory__create_entities", {})):
            c, d, r = run(ev(tool, ti))
            check(f"P {tool} -> untouched", d is None and c == 0, f"{c} {d} {r}")
        c, d, r = run({"garbage": True})
        check("P a malformed hook input with no Higgsfield marker -> untouched", d is None and c == 0)
        r2 = subprocess.run([sys.executable, "-B", me, "hook"], input=b'{"tool_name":"Bash","tool_input":{"command":'
                            b'"curl api.higgsfield.ai"', cwd=str(tmp), env=env, capture_output=True, timeout=60)
        check("F unparsable hook input that mentions Higgsfield -> deny (fail closed), exit 2",
              r2.returncode == 2 and b'"deny"' in r2.stdout)

        # --- 4.2 no-look ----------------------------------------------------------------------------------------
        batch = ("mcp__Claude_Browser__browser_batch", {"actions": [{"name": "navigate", "input": {"url": "x"}},
                                                                   {"name": "computer", "input": {"action": "screenshot"}}]})
        shot = ("mcp__Claude_Browser__computer", {"action": "screenshot"})
        cu = ("mcp__computer-use__screenshot", {})
        chrome = ("mcp__claude-in-chrome__computer", {"action": "screenshot"})
        prev = ("mcp__Claude_Preview__preview_screenshot", {})
        nav = ("mcp__Claude_Browser__navigate", {"url": "about:blank"})
        c, d, r = run(ev(*shot))
        check("N0 no flag -> browser screenshot untouched", d is None and c == 0)
        c, o, e = py([me, "no-look", "on"])
        check("N1 no-look on -> state on, flag in the per-user folder (= ledger.ledger_dir())",
              json.loads(o)["state"] == "on" and (cfg / "no-look.json").exists() and
              py(["-c", f"import sys; sys.path.insert(0, r'{SCRIPTS}'); import ledger; print(ledger.ledger_dir())"])[1]
              .strip() == str(cfg))
        for t in (batch, shot, cu, chrome, prev, nav):
            c, d, r = run(ev(*t))
            check(f"N2 fresh flag: {t[0]} -> deny", d == "deny" and c == 2, f"{d} {r}")
        for t in (("Read", {"file_path": str(ws / "b1.json")}), ("mcp__memory__create_entities", {})):
            c, d, r = run(ev(*t))
            check(f"N3 fresh flag: unrelated tool {t[0]} -> not blocked", d is None and c == 0)
        check("N4 Bash 'hf_guard.py no-look off' -> ask (the client's click); in dontAsk -> deny",
              bash(f'python "{me}" no-look off')[1] == "ask" and
              bash(f'python "{me}" no-look off', mode="dontAsk")[1] == "deny")
        check("N5 no-look on / status commands -> untouched",
              bash(f'python "{me}" no-look on')[1] is None and bash(f'python "{me}" no-look status')[1] is None)
        f = json.loads((cfg / "no-look.json").read_text())
        f["set_at"] -= NO_LOOK_TTL + 5
        (cfg / "no-look.json").write_text(json.dumps(f))
        check("N6 expired flag -> ask before looking; nobody to ask (bypassPermissions) -> deny",
              run(ev(*shot))[1] == "ask" and run(ev(*batch, mode="bypassPermissions"))[1] == "deny")
        c, o, e = py([me, "no-look", "off"])
        check("N7 no-look off -> leaving: screenshot still denied, navigate passes and clears the flag",
              json.loads(o)["state"] == "leaving" and run(ev(*shot))[1] == "deny" and run(ev(*nav))[1] is None
              and not (cfg / "no-look.json").exists() and run(ev(*batch))[1] is None)
        (cfg / "no-look.json").write_text("{broken")
        check("N8 unreadable flag -> deny (fail closed); no-look off repairs it",
              run(ev(*cu))[1] == "deny" and json.loads(py([me, "no-look", "off"])[1])["state"] == "leaving")
        (cfg / "no-look.json").unlink()

        # --- plumbing -------------------------------------------------------------------------------------------
        check("H every decision carried hookEventName + permissionDecisionReason (and deny <=> exit 2): "
              f"{len(shapes_ok)} decisions", shapes_ok and all(shapes_ok))
        hj = json.loads((HERE / "hooks.json").read_text(encoding="utf-8"))
        pre = hj["hooks"]["PreToolUse"]
        m_all = [re.compile(g["matcher"]) if not re.fullmatch(r"[\w|, -]+", g["matcher"]) else
                 (lambda s, names=[x.strip() for x in re.split(r"[|,]", g["matcher"])]: s in names) for g in pre]

        def fires(name):
            return any(m(name) if callable(m) else m.search(name) for m in m_all)

        cmds = [h for g in pre for h in g["hooks"]]
        check("H hooks.json: guard fires for Bash/PowerShell/Monitor/Write/Edit + every browser tool, not for Read; "
              "timeout 30 > the 10 s ledger lock; UserPromptSubmit NOT registered (4.3 off)",
              all(fires(t) for t in ("Bash", "PowerShell", "Monitor", "Write", "Edit", batch[0], shot[0], cu[0],
                                     chrome[0], prev[0], "mcp__computer-use__computer_batch")) and not fires("Read")
              and all(h.get("args", [None])[-1] == "hook" and "${CLAUDE_PLUGIN_ROOT}/hooks/hf_guard.py" in h["args"]
                      for h in cmds) and pre[0]["hooks"][0]["timeout"] >= 30 and "UserPromptSubmit" not in hj["hooks"])
        check("H no __pycache__ created in the plugin", pycache_before == ((SCRIPTS / "__pycache__").exists(),
                                                                           (HERE / "__pycache__").exists()))
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
