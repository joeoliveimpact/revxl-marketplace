#!/usr/bin/env python3
"""ledger.py - the spend ledger for the higgsfield-superengine plugin. Standard library only, Python 3.9+.

  python ledger.py check   <usd|unknown>                    would this amount fit under the silent cap now?
  python ledger.py reserve <usd|unknown> --id ID [--force] [--stamp PATH]
                                                            cap check + pending entry, in one locked step. PATH = the
                                                            absolute spend-guard stamp file this reservation pays for
  python ledger.py settle  ID [--usd ACTUAL]                open entry -> settled at ACTUAL (else the reserved amount)
  python ledger.py refund  ID [--reason WHY]                open entry -> refunded ($0). WHY: job_nsfw, job_failed,
                                                            job_canceled, not_sent, ... ([a-z0-9_], default refunded)
  python ledger.py balance set <usd>                        the balance read off the console; 0 after a 403
                                                            "Insufficient credits"
  python ledger.py status                                   totals + the open entries
  python ledger.py --selftest

Every command prints one JSON line (ASCII); "class" is the outcome. Exit codes: 0 ok (check/reserve: it fits, or
--force); 1 local error (lock timeout, corrupt store, I/O, pricing.py missing): fail closed, treat as "does not
fit"; 2 usage, bad input, unknown or duplicate id; 3 over the cap, or needs_ask for the amount "unknown" (check,
or reserve without --force; nothing written).
Store, one per user account (Joe 09.29.26, per the 09.25 design): ~/.config/higgsfield-superengine/ledger.json
(HF_SUPERENGINE_LEDGER_DIR overrides the folder; the selftest uses it). Created if missing, rewritten atomically
(temp file + os.replace) while holding an OS lock on ledger.lock in the same folder (msvcrt.locking on Windows,
fcntl.flock on POSIX; the OS drops it when the holder exits, so there is no stale lock to clean up).
Rules:
  counted        pending / assumed_charged = the reserved amount; settled = actual; refunded = 0.
  24 h spend     counted amounts of entries created in the trailing 24 h.
  known balance  the recorded balance minus the counted amounts of entries created since it was recorded (>= 0).
  cap            pricing.cap_usd(known balance) = min($5, 25%); unknown balance (never set) -> UNKNOWN_BALANCE_CAP.
  fits           pricing.fits_cap(): 24 h spend + amount <= cap (landing exactly on the cap fits).
  unknown        no price figure is always an ask: check / reserve without --force refuse (exit 3, needs_ask);
                 reserve --force (the client approved) reserves UNKNOWN_RESERVE ($5).
  startup        every command first marks pending entries older than PENDING_TTL (2 h, above hf_rest's longest
                 wait of 3600 s) as assumed_charged at the reserved amount. settle / refund still correct them.
  release        ... and first refunds (reason not_sent) a pending entry older than STAMP_RELEASE whose --stamp file
                 still sits unmoved in stamps/ and is too old to be used (> STAMP_DEAD s): hf_rest submit MOVES a
                 stamp it consumes, so a stamp left in place was never spent (a denied ask, a headless auto-deny).
                 A missing stamp file keeps the entry (spent, or unknown: overcount, never undercount).
"""
import json, math, os, re, sys, time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import pricing  # same folder; importing it has no side effects
except Exception:  # fail closed: every command refuses with pricing_unavailable
    pricing = None
if os.name == "nt":
    import msvcrt
else:
    import fcntl

DIR_ENV = "HF_SUPERENGINE_LEDGER_DIR"
KIND = "hf-superengine-ledger"
DAY = 24 * 3600
PENDING_TTL = 2 * 3600       # seconds; longer than any hf_rest wait (3600 s)
UNKNOWN_BALANCE_CAP = 1.0    # dollars per rolling 24 h while no balance was ever recorded (Joe decision pending)
UNKNOWN_RESERVE = 5.0        # dollars reserved for "unknown" = pricing.CAP_USD (asserted in the selftest)
LOCK_TIMEOUT = 10.0          # seconds
STAMP_DEAD = 62.0            # seconds: hf_rest's 60 s stamp life + its 2 s clock skew allowance
STAMP_RELEASE = 90.0         # seconds after the reservation before an unspent stamp releases it
STATES = ("pending", "assumed_charged", "settled", "refunded")
OPEN = ("pending", "assumed_charged")
AMOUNT_RE = re.compile(r"[0-9]{1,9}(\.[0-9]{1,9})?")
ID_RE = re.compile(r"[A-Za-z0-9._:-]{1,80}")
WORD_RE = re.compile(r"[a-z0-9_]{1,40}")
USAGE = ("usage: ledger.py check <usd|unknown> | reserve <usd|unknown> --id ID [--force] [--stamp PATH] | "
         "settle ID [--usd X] | "
         "refund ID [--reason WHY] | balance set <usd> | status | --selftest")


def ledger_dir():
    """Resolved on every call, so the env override also works after import."""
    return Path(os.environ.get(DIR_ENV) or os.path.expanduser("~/.config/higgsfield-superengine"))


def ledger_file():
    return ledger_dir() / "ledger.json"


class Fail(Exception):
    def __init__(self, cls, message, code):
        super().__init__(cls)
        self.cls, self.message, self.code = cls, message, code


@contextmanager
def locked():
    ledger_dir().mkdir(parents=True, exist_ok=True)
    with open(ledger_dir() / "ledger.lock", "a+b") as f:
        end = time.monotonic() + LOCK_TIMEOUT
        while True:
            try:
                if os.name == "nt":
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() > end:
                    raise Fail("lock_timeout", f"Another ledger call held the lock for over {LOCK_TIMEOUT:g} s. "
                                               "Nothing was changed; try again.", 1)
                time.sleep(0.01)
        try:
            yield
        finally:
            if os.name == "nt":
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            # POSIX: closing the file drops the flock


def _num(x, low=0.0):
    return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x) and x >= low


def _entry_ok(e):
    return (isinstance(e, dict) and isinstance(e.get("id"), str) and bool(ID_RE.fullmatch(e["id"]))
            and e.get("state") in STATES and _num(e.get("reserved")) and _num(e.get("created_at"), -math.inf)
            and (_num(e.get("actual")) if e["state"] in ("assumed_charged", "settled") else True)
            and isinstance(e.get("stamp", ""), str))


def _bad_constant(name):
    raise ValueError(name)


def load():
    try:
        raw = ledger_file().read_bytes()
    except FileNotFoundError:
        return {"v": 1, "kind": KIND, "balance": None, "balance_at": None, "entries": []}
    try:
        d = json.loads(raw.decode("utf-8"), parse_constant=_bad_constant)
        ok = (isinstance(d, dict) and d.get("v") == 1 and d.get("kind") == KIND
              and isinstance(d.get("entries"), list) and all(_entry_ok(e) for e in d["entries"])
              and ((d.get("balance") is None and d.get("balance_at") is None)
                   or (_num(d.get("balance")) and _num(d.get("balance_at"), -math.inf))))
    except (ValueError, RecursionError):
        ok = False
    if not ok:
        raise Fail("ledger_corrupt", f"{ledger_file().as_posix()} is unreadable or malformed. Nothing was changed, and "
                                     "nothing fits the cap until it is fixed. Ask the client before moving it aside "
                                     "(a fresh ledger forgets the last 24 h of spend).", 1)
    return d


def save(d):
    target = ledger_file()
    tmp = target.with_name(f"ledger.{os.getpid()}.tmp")
    try:
        with open(tmp, "wb") as f:
            f.write((json.dumps(d, indent=1, ensure_ascii=True) + "\n").encode("ascii"))
            f.flush()
            os.fsync(f.fileno())
        for i in range(20):  # OneDrive / antivirus can hold the target open for a moment (Windows sharing errors)
            try:
                os.replace(tmp, target)
                return
            except PermissionError:
                if i == 19:
                    raise
                time.sleep(0.05)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def counted(e):
    return 0.0 if e["state"] == "refunded" else e["reserved"] if e["state"] == "pending" else e["actual"]


def _unspent(stamp, now):
    """The stamp file is still in stamps/ and too old for hf_rest submit to accept: it can never be spent."""
    try:
        return now - os.stat(stamp).st_mtime > STAMP_DEAD
    except OSError:  # moved (consumed) or unreachable: keep the reservation
        return False


def sweep(d, now):
    """The startup rule. Returns True if an entry changed."""
    free = [e for e in d["entries"] if e["state"] == "pending" and isinstance(e.get("stamp"), str)
            and now - e["created_at"] > STAMP_RELEASE and _unspent(e["stamp"], now)]
    for e in free:
        e.update(state="refunded", actual=0.0, updated_at=now, reason="not_sent")
    old = [e for e in d["entries"] if e["state"] == "pending" and now - e["created_at"] > PENDING_TTL]
    for e in old:
        e.update(state="assumed_charged", actual=e["reserved"], updated_at=now, reason="pending_over_2h")
    return bool(old or free)


def totals(d, now):
    spent = sum(counted(e) for e in d["entries"] if e["created_at"] > now - DAY)
    known = None
    if d.get("balance") is not None:
        since = sum(counted(e) for e in d["entries"] if e["created_at"] >= d["balance_at"])
        known = max(0.0, d["balance"] - since)
    cap = pricing.cap_usd(known)
    return spent, known, (UNKNOWN_BALANCE_CAP if cap is None else cap), ("unknown_balance" if cap is None else
                                                                         "balance")


def _r(x):
    return None if x is None else round(x, 7)


def _out(cmd, d, now, **kw):
    spent, known, cap, basis = totals(d, now)
    o = {"ok": True, "command": cmd, "class": "ok", "spent_24h": _r(spent), "cap_usd": _r(cap), "cap_basis": basis,
         "headroom_usd": _r(max(0.0, cap - spent)), "balance": _r(known), "balance_recorded": d.get("balance"),
         "balance_at": d.get("balance_at"), "open_entries": sum(e["state"] in OPEN for e in d["entries"])}
    o.update(kw)
    return o


def _fits(d, usd, now):
    spent, known, _, _ = totals(d, now)
    f = pricing.fits_cap(usd, spent, known)
    return (round(spent + usd, 6) <= round(UNKNOWN_BALANCE_CAP, 6)) if f is None else f


def _args(args, npos, flags=(), switches=()):
    pos, opt, it = [], {}, iter(args)
    for a in it:
        if a in flags and a not in opt:
            opt[a] = next(it, None)
            if opt[a] is None:
                raise Fail("usage", USAGE, 2)
        elif a in switches and a not in opt:
            opt[a] = True
        elif a.startswith("--"):
            raise Fail("usage", USAGE, 2)
        else:
            pos.append(a)
    if len(pos) != npos:
        raise Fail("usage", USAGE, 2)
    return pos, opt


def _amount(s, unknown_ok=True):
    """-> (dollars, amount_known)"""
    if unknown_ok and s == "unknown":
        return UNKNOWN_RESERVE, False
    if not AMOUNT_RE.fullmatch(s):
        raise Fail("bad_input", "Amounts are plain dollars such as 0.12 (no sign, exponent or $)"
                                + (", or unknown." if unknown_ok else "."), 2)
    return float(s), True


def _id(s):
    if not ID_RE.fullmatch(s):
        raise Fail("bad_input", "An id is 1-80 characters from A-Z a-z 0-9 . _ : -", 2)
    return s


def _open_entry(d, eid):
    return next((e for e in d["entries"] if e["id"] == eid and e["state"] in OPEN), None)


def _needs_ask():
    return Fail("needs_ask", "No price figure: this is always an ask (a real click). Nothing was reserved; if the "
                             "client approves, reserve unknown --force.", 3)


def cmd_check(args, now):
    (amt,), _ = _args(args, 1)
    usd, known = _amount(amt)
    if not known:
        raise _needs_ask()
    with locked():
        d = load()
        if sweep(d, now):
            save(d)
        if _fits(d, usd, now):
            return 0, _out("check", d, now, usd=usd, fits=True, message="Fits under the silent cap.")
        return 3, _out("check", d, now, ok=False, usd=usd, fits=False, **{"class": "over_cap"},
                       message="Over the silent cap: ask the client (a real click).")


def cmd_reserve(args, now):
    (amt,), o = _args(args, 1, flags=("--id", "--stamp"), switches=("--force",))
    if "--id" not in o:
        raise Fail("usage", USAGE, 2)
    eid, (usd, known), force = _id(o["--id"]), _amount(amt), o.get("--force", False)
    if not known and not force:
        raise _needs_ask()
    with locked():
        d = load()
        swept = sweep(d, now)
        dup = _open_entry(d, eid)
        if dup:
            if swept:
                save(d)
            raise Fail("duplicate_id", f"An open entry already uses this id ({dup['state']}, "
                                       f"${dup['reserved']}). Settle or refund it first. Nothing was reserved.", 2)
        fits = _fits(d, usd, now)
        if not fits and not force:
            if swept:
                save(d)
            return 3, _out("reserve", d, now, ok=False, usd=usd, fits=False, **{"class": "over_cap"},
                           message="Over the silent cap: nothing was reserved. Ask the client (a real click); "
                                   "if they approve, reserve again with --force.")
        e = {"id": eid, "state": "pending", "reserved": usd, "amount_known": known, "actual": None,
             "forced": bool(force), "created_at": now, "updated_at": now, "reason": None}
        if "--stamp" in o:
            e["stamp"] = o["--stamp"]
        d["entries"].append(e)
        save(d)
        return 0, _out("reserve", d, now, usd=usd, fits=fits, entry=e,
                       message="Reserved." if fits else "Reserved over the cap (--force: the client approved).")


def _close(args, now, cmd):
    (eid,), o = _args(args, 1, flags=("--usd",) if cmd == "settle" else ("--reason",))
    eid = _id(eid)
    if cmd == "settle":
        actual = _amount(o["--usd"], unknown_ok=False)[0] if "--usd" in o else None
    else:
        why = o.get("--reason", "refunded")
        if not WORD_RE.fullmatch(why):
            raise Fail("bad_input", "A refund reason is 1-40 characters from a-z 0-9 _", 2)
    with locked():
        d = load()
        swept = sweep(d, now)
        e = _open_entry(d, eid)
        if not e:
            if swept:
                save(d)
            raise Fail("unknown_id", "No open (pending or assumed_charged) entry has this id. Nothing was changed.", 2)
        if cmd == "settle":
            e.update(state="settled", actual=e["reserved"] if actual is None else actual, updated_at=now,
                     reason="actual" if actual is not None else "reserved_amount")
        elif why == "not_sent" and e.get("stamp") and not os.path.exists(e["stamp"]):
            # submit MOVES the stamp it consumes, so a missing stamp means the job was sent (Codex review 10.01.26:
            # submit, then "refund not_sent", reset the cap). Use the job's real outcome as the reason instead.
            if swept:
                save(d)
            raise Fail("stamp_consumed", "This job's stamp was used by a submit, so it was sent. Refund it only with "
                       "its real outcome: rejected (Higgsfield refused the request), insufficient_credits, job_nsfw, "
                       "job_failed or job_canceled. Nothing was changed.", 3)
        else:
            e.update(state="refunded", actual=0.0, updated_at=now, reason=why)
        save(d)
        return 0, _out(cmd, d, now, entry=e, message="Settled." if cmd == "settle" else "Refunded.")


def cmd_balance(args, now):
    (sub, amt), _ = _args(args, 2)
    if sub != "set":
        raise Fail("usage", USAGE, 2)
    usd = _amount(amt, unknown_ok=False)[0]
    with locked():
        d = load()
        sweep(d, now)
        d["balance"], d["balance_at"] = usd, now
        save(d)
        return 0, _out("balance", d, now, message=f"Balance recorded: ${usd:g}.")


def cmd_status(args, now):
    _args(args, 0)
    with locked():
        d = load()
        if sweep(d, now):
            save(d)
        return 0, _out("status", d, now, entries=[e for e in d["entries"] if e["state"] in OPEN])


COMMANDS = {"check": cmd_check, "reserve": cmd_reserve, "settle": lambda a, n: _close(a, n, "settle"),
            "refund": lambda a, n: _close(a, n, "refund"), "balance": cmd_balance, "status": cmd_status}


def run(argv, now=None):
    """-> (exit code, output dict). The CLI prints the dict; a Python caller (the hook) can use it directly."""
    cmd = argv[0] if argv else None
    try:
        if pricing is None:
            raise Fail("pricing_unavailable", "pricing.py could not be imported from the ledger's folder. Nothing "
                                              "fits the cap until it is restored.", 1)
        if cmd not in COMMANDS:
            raise Fail("usage", USAGE, 2)
        return COMMANDS[cmd](argv[1:], time.time() if now is None else now)
    except Fail as f:
        return f.code, {"ok": False, "command": cmd, "class": f.cls, "message": f.message}
    except OSError as e:
        return 1, {"ok": False, "command": cmd, "class": "local_io_error",
                   "message": f"{type(e).__name__} on the ledger store. Nothing fits the cap until this is fixed."}
    except Exception as e:
        return 1, {"ok": False, "command": cmd, "class": "internal_error", "message": f"Unexpected {type(e).__name__}."}


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    code, obj = run(argv)
    print(json.dumps(obj, ensure_ascii=True, separators=(",", ":")))
    return code


def selftest():
    """Offline: temp ledger folders (HF_SUPERENGINE_LEDGER_DIR), a fixed clock for the in-process checks, real
    processes (which inherit the override) for the lock and race. Never touches the real ~/.config ledger."""
    import shutil, subprocess, tempfile
    global LOCK_TIMEOUT
    me, home, saved_timeout, saved_env = os.path.abspath(__file__), os.getcwd(), LOCK_TIMEOUT, os.environ.get(DIR_ENV)
    real = Path(os.path.expanduser("~/.config/higgsfield-superengine"))
    real_before = sorted((q.name, q.stat().st_mtime_ns) for q in real.iterdir()) if real.is_dir() else None
    tmp, results, T0 = Path(tempfile.mkdtemp(prefix="ledger-selftest-")), [], 1_800_000_000.0

    def check(name, cond):
        results.append(bool(cond))
        print(("PASS  " if cond else "FAIL  ") + name)

    def ws(name):
        (tmp / name).mkdir()
        os.chdir(tmp / name)
        os.environ[DIR_ENV] = str(tmp / name / "ledger-dir")  # a folder that does not exist yet
        return tmp / name

    def R(*a, now=T0):
        return run(list(a), now=now)

    def store():
        return json.loads(ledger_file().read_text("utf-8"))

    def put(entries, balance=None, balance_at=None):
        ledger_dir().mkdir(parents=True, exist_ok=True)
        ledger_file().write_text(json.dumps({"v": 1, "kind": KIND, "balance": balance, "balance_at": balance_at,
                                    "entries": entries}), "utf-8")

    def ent(eid, state, reserved, created_at, actual=None):
        return {"id": eid, "state": state, "reserved": reserved, "amount_known": True, "actual": actual,
                "forced": False, "created_at": created_at, "updated_at": created_at, "reason": None}

    def cli(*a, cwd):
        p = subprocess.run([sys.executable, "-B", me, *a], cwd=cwd, capture_output=True, timeout=60,
                           env=dict(os.environ))
        lines = p.stdout.decode("ascii", "replace").splitlines()
        try:
            j = json.loads(lines[0]) if len(lines) == 1 else None
        except ValueError:
            j = None
        return p.returncode, j, p.stderr

    try:
        check("P0 pricing.py imported from this folder; UNKNOWN_RESERVE = pricing.CAP_USD = $5",
              pricing is not None and UNKNOWN_RESERVE == pricing.CAP_USD == 5.0)

        os.environ.pop(DIR_ENV, None)
        default = ledger_dir()
        os.environ[DIR_ENV] = ""
        empty = ledger_dir()
        ws("s1")
        check("P1 store: ~/.config/higgsfield-superengine/ledger.json by default (also when the override is empty); "
              "HF_SUPERENGINE_LEDGER_DIR overrides it",
              default == empty == Path(os.path.expanduser("~/.config/higgsfield-superengine"))
              and ledger_file() == tmp / "s1" / "ledger-dir" / "ledger.json")
        code, j = R("status")
        check("S1 fresh workspace: status -> spent 0, balance unknown, cap $1 (unknown_balance), no store written",
              code == 0 and j["spent_24h"] == 0 and j["balance"] is None and j["cap_usd"] == 1.0
              and j["cap_basis"] == "unknown_balance" and not ledger_file().exists())

        code, j = R("reserve", "0.30", "--id", "a")
        tmps = [p.name for p in ledger_dir().iterdir() if p.suffix == ".tmp"]
        check("A1 reserve creates the missing folder and writes ledger.json (valid JSON, entry pending), no temp file left",
              code == 0 and store()["entries"][0]["state"] == "pending" and not tmps)
        before, real_replace = ledger_file().read_bytes(), os.replace

        def broken_replace(*a):
            raise OSError("simulated disk error")
        os.replace = broken_replace
        try:
            code, j = R("reserve", "0.10", "--id", "b")
        finally:
            os.replace = real_replace
        check("A2 a failed write -> exit 1 local_io_error, the old store byte-identical, no temp file left",
              code == 1 and j["class"] == "local_io_error" and ledger_file().read_bytes() == before
              and not [p for p in ledger_dir().iterdir() if p.suffix == ".tmp"])

        ws("f1")
        R("reserve", "0.30", "--id", "a")
        code, j = R("settle", "a", "--usd", "0.25")
        check("F1 reserve 0.30 -> settle --usd 0.25: settled at the actual, 24 h spend 0.25",
              code == 0 and j["entry"]["state"] == "settled" and j["entry"]["actual"] == 0.25 and j["spent_24h"] == 0.25)
        R("reserve", "0.20", "--id", "b")
        code, j = R("refund", "b", "--reason", "job_nsfw")
        check("F2 reserve 0.20 -> refund --reason job_nsfw: refunded ($0), 24 h spend still 0.25",
              code == 0 and j["entry"]["state"] == "refunded" and j["entry"]["reason"] == "job_nsfw"
              and j["spent_24h"] == 0.25)
        R("reserve", "0.10", "--id", "c")
        code, j = R("settle", "c")
        check("F3 settle without --usd keeps the reserved amount (0.10)",
              code == 0 and j["entry"]["actual"] == 0.10 and j["spent_24h"] == 0.35)
        c1, j1 = R("settle", "a")
        c2, j2 = R("refund", "zzz")
        check("F4 settle a final entry / refund an unknown id -> exit 2 unknown_id",
              c1 == c2 == 2 and j1["class"] == j2["class"] == "unknown_id")
        c1, _ = R("reserve", "0.05", "--id", "c")
        n = len(store()["entries"])
        c2, j2 = R("reserve", "0.05", "--id", "c")
        check("F5 an id may be reused once its entry is final; a second OPEN entry with it -> exit 2 duplicate_id, "
              "nothing written", c1 == 0 and c2 == 2 and j2["class"] == "duplicate_id" and len(store()["entries"]) == n)
        c1, j1 = R("reserve", "unknown", "--id", "u")
        c2, j2 = R("reserve", "unknown", "--id", "u", "--force")
        check("F6 amount 'unknown' without --force -> exit 3 needs_ask; with --force (approved ask) reserves $5, "
              "amount_known false; 24 h spend 5.40", c1 == 3 and j1["class"] == "needs_ask" and c2 == 0 and j2["entry"]["reserved"] == 5.0
              and j2["entry"]["amount_known"] is False and j2["entry"]["forced"] is True and j2["spent_24h"] == 5.4)

        ws("f7")
        R("balance", "set", "100")
        c1, j1 = R("reserve", "unknown", "--id", "n")
        c2, j2 = R("check", "unknown")
        check("F7 $5 of headroom (balance 100): reserve unknown / check unknown without --force -> exit 3 needs_ask, "
              "nothing written", c1 == c2 == 3 and j1["class"] == j2["class"] == "needs_ask"
              and store()["entries"] == [])

        ws("t1")
        put([ent("old", "pending", 0.4, T0 - 3 * 3600), ent("young", "pending", 0.3, T0 - 1800)])
        code, j = R("status")
        st = {e["id"]: e for e in store()["entries"]}
        check("T1 startup rule: pending > 2 h -> assumed_charged at the reserved 0.40 (saved); 30 min -> still "
              "pending; both counted (0.70)",
              code == 0 and st["old"]["state"] == "assumed_charged" and st["old"]["actual"] == 0.4
              and st["young"]["state"] == "pending" and j["spent_24h"] == 0.7 and j["open_entries"] == 2)
        code, j = R("refund", "old", "--reason", "job_failed")
        check("T2 an assumed_charged entry can still be refunded -> 24 h spend 0.30",
              code == 0 and j["entry"]["state"] == "refunded" and j["spent_24h"] == 0.3)

        w = ws("t3")
        (w / "stamps").mkdir()
        for n in ("left", "fresh", "gone"):
            (w / "stamps" / n).write_text("{}")
            os.utime(w / "stamps" / n, (T0 - 100, T0 - (30 if n == "fresh" else 100)))
        (w / "stamps" / "gone").rename(w / "used-gone")  # what submit does when it consumes a stamp
        for n in ("left", "fresh", "gone"):
            R("reserve", "0.40", "--id", n, "--force", "--stamp", str(w / "stamps" / n), now=T0 - 95)
        R("reserve", "0.40", "--id", "plain", "--force", now=T0 - 95)
        c1, _ = R("status", now=T0 - 20)
        early = {e["id"]: e["state"] for e in store()["entries"]}
        code, j = R("status")
        st = {e["id"]: e for e in store()["entries"]}
        check("T3 release: an unspent stamp left in stamps/ -> refunded not_sent 90 s after the reservation (not "
              "before); a consumed (moved) stamp, a still-usable stamp, and an entry without --stamp stay pending",
              c1 == code == 0 and set(early.values()) == {"pending"} and st["left"]["state"] == "refunded"
              and st["left"]["reason"] == "not_sent" and st["left"]["actual"] == 0.0
              and [st[n]["state"] for n in ("gone", "fresh", "plain")] == ["pending"] * 3
              and j["spent_24h"] == 1.2 and "stamp" not in st["plain"])

        ws("w1")
        put([ent("d25", "settled", 1.0, T0 - 25 * 3600, 1.0), ent("d23", "settled", 0.2, T0 - 23 * 3600, 0.2)])
        c0, j0 = R("status")
        c1, _ = R("check", "0.80")
        c2, j2 = R("check", "0.81")
        check("W1 rolling 24 h: an entry 25 h old is not counted (spend 0.20); unknown-balance cap $1: 0.80 fits "
              "(exit 0), 0.81 -> exit 3 over_cap", j0["spent_24h"] == 0.2 and c1 == 0 and c2 == 3
              and j2["class"] == "over_cap")

        ws("b1")
        _, j100 = R("balance", "set", "100")
        _, j8 = R("balance", "set", "8")
        check("B1 balance set 100 -> cap $5; balance set 8 -> cap $2 (min($5, 25%))",
              j100["cap_usd"] == 5.0 and j8["cap_usd"] == 2.0 and j8["cap_basis"] == "balance")
        R("reserve", "1.00", "--id", "x", now=T0 + 1)
        c1, j1 = R("check", "0.75", now=T0 + 2)
        c2, _ = R("check", "0.76", now=T0 + 2)
        check("B2 spend since the balance read lowers the known balance: 8 - 1 = 7 -> cap 1.75 "
              "(= pricing.cap_usd(7)); 1 + 0.75 fits, 1 + 0.76 -> exit 3",
              j1["balance"] == 7.0 and j1["cap_usd"] == pricing.cap_usd(7.0) == 1.75 and c1 == 0 and c2 == 3)
        _, j = R("balance", "set", "8", now=T0 + 10)
        check("B3 a new balance read excludes earlier entries (known 8, cap 2) but the 24 h spend keeps them (1.00)",
              j["balance"] == 8.0 and j["cap_usd"] == 2.0 and j["spent_24h"] == 1.0)
        R("balance", "set", "0", now=T0 + 20)
        c1, j1 = R("check", "0.01", now=T0 + 21)
        n = len(store()["entries"])
        c2, _ = R("reserve", "0.01", "--id", "y", now=T0 + 21)
        n2 = len(store()["entries"])
        c3, _ = R("reserve", "0.01", "--id", "y", "--force", now=T0 + 21)
        check("B4 403 Insufficient credits -> balance set 0: cap $0, check 0.01 -> exit 3, reserve -> exit 3 with "
              "nothing written; --force still records it", j1["cap_usd"] == 0 and c1 == 3 and c2 == 3 and n2 == n
              and c3 == 0)

        ws("u1")
        c1, _ = R("check", "1.00")
        c2, _ = R("check", "1.01")
        R("reserve", "0.50", "--id", "p")
        c3, _ = R("check", "0.50")
        c4, _ = R("check", "0.51")
        check("U1 unknown balance -> fixed $1 cap: 1.00 fits, 1.01 not; after 0.50 reserved, 0.50 fits, 0.51 not",
              (c1, c2, c3, c4) == (0, 3, 0, 3))

        ws("x1")
        bad = {"not JSON": b"{nope", "a list": b"[]", "wrong kind": b'{"v":1,"kind":"x","entries":[]}',
               "NaN amount": json.dumps({"v": 1, "kind": KIND, "balance": None, "balance_at": None, "entries": [
                   ent("a", "pending", 1, T0)]}).replace('"reserved": 1', '"reserved": NaN').encode(),
               "entry without created_at": json.dumps({"v": 1, "kind": KIND, "balance": None, "balance_at": None,
                                                       "entries": [{"id": "a", "state": "pending",
                                                                    "reserved": 1}]}).encode(),
               "negative balance": json.dumps({"v": 1, "kind": KIND, "balance": -5, "balance_at": T0,
                                               "entries": []}).encode()}
        fails = []
        for label, raw in bad.items():
            ledger_dir().mkdir(parents=True, exist_ok=True)
            ledger_file().write_bytes(raw)
            c1, j1 = R("reserve", "0.01", "--id", "q")
            c2, _ = R("check", "0.01")
            if not (c1 == c2 == 1 and j1["class"] == "ledger_corrupt" and ledger_file().read_bytes() == raw):
                fails.append(label)
        check(f"X1 corrupt store ({', '.join(bad)}) -> exit 1 ledger_corrupt, file untouched" + (f" FAILED: {fails}" if fails
              else ""), not fails)

        ws("x2")
        cases = [("check", "-1"), ("check", "abc"), ("check", "1e3"), ("check", "nan"), ("check", "$1"),
                 ("check", ""), ("reserve", "0.1", "--id", "a b"), ("reserve", "0.1", "--id", "x" * 81),
                 ("refund", "a", "--reason", "Bad Reason"), ("balance", "set", "unknown"),
                 ("settle", "a", "--usd", "unknown")]
        got = [R(*c) for c in cases]
        use = [R(), R("bogus"), R("reserve", "0.1"), R("balance", "get", "1"), R("check", "1", "--force"),
               R("status", "extra"), R("reserve", "0.1", "--id")]
        check(f"X2 {len(cases)} bad amounts / ids / reasons -> exit 2 bad_input; {len(use)} malformed commands -> "
              "exit 2 usage; nothing written",
              all(c == 2 and j["class"] == "bad_input" for c, j in got)
              and all(c == 2 and j["class"] == "usage" for c, j in use) and not ledger_file().exists())

        ws("k1")
        LOCK_TIMEOUT = 0.3
        with locked():
            code, j = R("status")
        check("K1 lock held by another caller -> exit 1 lock_timeout, nothing changed",
              code == 1 and j["class"] == "lock_timeout" and not ledger_file().exists())
        holder = ("import importlib.util, sys, time\n"
                  "s = importlib.util.spec_from_file_location('ledger_hold', sys.argv[1])\n"
                  "m = importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
                  "with m.locked():\n"
                  "    open(sys.argv[2], 'w').close()\n"
                  "    time.sleep(60)\n")
        ready = tmp / "k1-ready"
        p = subprocess.Popen([sys.executable, "-B", "-c", holder, me, str(ready)], cwd=str(tmp / "k1"),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=dict(os.environ))
        try:
            t_end = time.time() + 20
            while not ready.exists() and time.time() < t_end and p.poll() is None:
                time.sleep(0.01)
            c1, j1 = R("status")
        finally:
            p.kill()
            p.wait(timeout=30)
        LOCK_TIMEOUT = 5.0
        c2, _ = R("reserve", "0.10", "--id", "k")
        check("K2 another PROCESS holding the lock blocks (lock_timeout); once it is killed the lock is gone "
              "(no stale lock): reserve -> exit 0", ready.exists() and c1 == 1 and j1["class"] == "lock_timeout"
              and c2 == 0)
        LOCK_TIMEOUT = saved_timeout

        d = ws("l1")
        out = [cli("status", cwd=d), cli("reserve", "0.40", "--id", "z", cwd=d), cli("reserve", "9", "--id", "big",
                                                                                     cwd=d),
               cli("bogus", cwd=d), cli("check", "0.60", cwd=d)]
        check("L1 CLI: one JSON line each, stderr empty; exit codes status 0, reserve 0, over the cap 3, "
              "usage 2, check 0", [c for c, _, _ in out] == [0, 0, 3, 2, 0]
              and all(j is not None and not e for _, j, e in out))

        racer = ("import importlib.util, os, sys, time\n"
                 "s = importlib.util.spec_from_file_location('ledger_race', sys.argv[1])\n"
                 "m = importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
                 "open(sys.argv[3], 'w').close()\n"
                 "while not os.path.exists(sys.argv[2]):\n"
                 "    time.sleep(0.0005)\n"
                 "sys.exit(m.main(sys.argv[4:]))\n")
        rounds = []
        for rnd in range(3):
            d = ws(f"race{rnd}")
            R("balance", "set", "100", now=None)
            go, ready = tmp / f"go{rnd}", [tmp / f"ready{rnd}-{i}" for i in range(8)]
            procs = [subprocess.Popen([sys.executable, "-B", "-c", racer, me, str(go), str(r), "reserve", "0.90",
                                       "--id", f"r{i}"], cwd=str(d), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      env=dict(os.environ))
                     for i, r in enumerate(ready)]
            try:
                t_end = time.time() + 30
                while time.time() < t_end and not all(r.exists() for r in ready) and \
                        all(pr.poll() is None for pr in procs):
                    time.sleep(0.01)
                go.touch()
                codes = [pr.wait(timeout=60) for pr in procs]
            finally:
                for pr in procs:
                    if pr.poll() is None:
                        pr.kill()
                    pr.communicate()
            es = store()["entries"]
            total = round(sum(e["reserved"] for e in es), 6)
            rounds.append((codes.count(0), codes.count(3), len(es), total))
        check(f"R1 8 processes reserve $0.90 at once against a $5 cap, 3 rounds -> exactly 5 reserved, 3 over_cap, "
              f"total $4.50 <= $5 each round {rounds}", all(r == (5, 3, 5, 4.5) for r in rounds))
    except Exception as e:
        check(f"selftest crashed: {type(e).__name__}: {e}", False)
    finally:
        LOCK_TIMEOUT = saved_timeout
        os.chdir(home)
        shutil.rmtree(tmp, ignore_errors=True)
        if saved_env is None:
            os.environ.pop(DIR_ENV, None)
        else:
            os.environ[DIR_ENV] = saved_env
    check("P2 the real ~/.config/higgsfield-superengine was not touched",
          real_before == (sorted((q.name, q.stat().st_mtime_ns) for q in real.iterdir()) if real.is_dir() else None))
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
