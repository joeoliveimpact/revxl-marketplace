"""Shared helpers for the Python jobs: config with defaults, private/atomic writes, status files,
the notify command, the failure alert, and the lock.

Config: --config, else $FEWZHUN_BOX_CONFIG, else /etc/fewzhun-box/brain.json.
Only the keys the Python side reads get defaults here (root, timezone, spokes, graph, harvest, claude).
"""
import copy, datetime as dt, json, os, shlex, subprocess, sys
from zoneinfo import ZoneInfo

try:
    import fcntl
except ImportError:          # Windows dev box (selftest only)
    fcntl = None

DEFAULT_CONFIG = "/etc/fewzhun-box/brain.json"
CHILD_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

DEFAULTS = {
    "root": "/opt/fewzhun-box",
    "code_root": "/opt/fewzhun-box-app",
    "timezone": "UTC",
    "spokes": {},
    "graph": {"enabled": True, "graphify_version": "0.9.112", "backend": "claude-cli", "time": "03:30",
              "graphify": None, "min_nodes": 1},
    "harvest": {
        "enabled": False, "time": "02:30", "cutoff": None, "max_drafts": 12, "budget_chars": 60000,
        "item_chars": 6000, "sources": [], "notify": None, "approvers": [], "known_hosts": ["github.com"],
        "secret_patterns": [], "taps_file": None,
        "schema": {
            "types": ["rule", "fact", "process", "system", "decision", "lesson", "daily"],
            "folders": {"rule": "10-Rules", "fact": "20-Facts", "process": "30-Processes", "system": "40-Systems",
                        "decision": "50-Decisions", "lesson": "60-Lessons", "daily": "90-Daily"},
            "applies_to": ["all-agents", "humans", "build"],
            "sot_policy": {"rule": "strict", "fact": "strict", "process": "strict", "decision": "strict",
                           "system": "decay", "lesson": "blended", "daily": "blended"},
        },
        "promote": {"repo": None, "on_promote": {"status": "active", "last_verified": "{today}"}},
    },
    "claude": {"bin": "claude", "run_as": None, "credentials": None, "token_file": None, "idle_cmd": None, "busy_url": None,
               "min_token_minutes": 60, "max_run_minutes": 15, "model": "haiku", "retries": 12,
               "retry_minutes": 5},
}


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(out.get(k), dict) and isinstance(v, dict) else v
    return out


def load_config(path=None):
    path = path or os.environ.get("FEWZHUN_BOX_CONFIG") or DEFAULT_CONFIG
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError("config must be a JSON object")
    for key in ("claude", "graph", "harvest", "spokes"):
        if key in raw and not isinstance(raw[key], dict):
            raise ValueError(f"{key} config must be an object")
    cfg = _merge(DEFAULTS, raw)
    cfg["_path"] = os.path.abspath(path)
    return cfg


def p(cfg, *parts):
    """A path under <root>."""
    return os.path.join(cfg["root"], *parts)


def tz(cfg):
    return ZoneInfo(cfg.get("timezone") or "UTC")


def now(cfg):
    return dt.datetime.now(tz(cfg))


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def write_private(path, text):
    """0600, overwrite. Used inside 0700 staging dirs."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def refuse_symlink(path):
    if os.path.islink(path):
        raise OSError(f"refusing symlink target: {path}")


def write_atomic(path, text, mode=0o640):
    """Exclusive, no-follow temp file + fsync + rename; refuse symlink targets."""
    refuse_symlink(path)
    tmp = f"{path}.tmp{os.getpid()}"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            if os.name == "posix":
                os.fchmod(f.fileno(), mode)
                os.fchown(f.fileno(), -1, os.stat(os.path.dirname(os.path.abspath(path))).st_gid)
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        refuse_symlink(path)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_status(cfg, job, ok, **kw):
    """<root>/status/<job>.json: {ok, ts, ...}. Last run wins; a failure always carries a reason."""
    d = p(cfg, "status")
    os.makedirs(d, mode=0o750, exist_ok=True)
    data = {"ok": bool(ok), "ts": stamp(), **kw}
    if cfg.get("claude", {}).get("token_file") is not None:
        data["auth_note"] = "long-lived token: expiry not checked"
    write_atomic(os.path.join(d, f"{job}.json"), json.dumps(data, indent=1, default=str) + "\n")
    return data


def read_status(cfg, job):
    try:
        path = "/var/lib/fewzhun-box/status/sync.json" if job == "sync" else p(cfg, "status", f"{job}.json")
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def child_env(**extra):
    """Explicit env for helper commands, never the caller's (no stray keys or tokens ride along).
    SYSTEMROOT keeps Windows children (selftest) working; it is absent on Linux."""
    env = {"PATH": CHILD_PATH, "LANG": "C.UTF-8",
           "HOME": os.environ.get("HOME") or "/"}
    if os.name == "nt":
        env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", r"C:\Windows")
    env.update(extra)
    return env


def _argv(cmd):
    return cmd if isinstance(cmd, list) else shlex.split(cmd)


def notify(cfg, payload):
    """Runs harvest.notify (no shell) with the payload as JSON on stdin. Returns True when it exited 0,
    None when no notify command is configured. Never raises."""
    cmd = cfg["harvest"].get("notify")
    if not cmd:
        return None
    try:
        r = subprocess.run(_argv(cmd), input=json.dumps(payload, ensure_ascii=False), text=True, timeout=120,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, encoding="utf-8", env=child_env())
    except Exception as e:
        print(f"notify failed: {type(e).__name__}", file=sys.stderr)
        return False
    if r.returncode:
        print(f"notify exited {r.returncode}: {(r.stderr or '').strip()[:200]}", file=sys.stderr)
    return r.returncode == 0


def alert(cfg, job, max_age_s=6 * 3600):
    """Run by fewzhun-box-alert@<job>.service when a nightly unit fails. If the job left no fresh failure
    status (it crashed or was killed first), writes one, then sends one alert line through notify."""
    s = read_status(cfg, job)
    fresh = False
    if s and not s.get("ok"):
        try:
            age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(s["ts"])).total_seconds()
            fresh = age < max_age_s
        except (KeyError, ValueError):
            pass
    if not fresh:
        s = write_status(cfg, job, False, reason=f"the {job} unit failed without writing a status "
                                                 f"(see journalctl -u fewzhun-box-{job})")
    msg = f"fewzhun-box {job} FAILED: {str(s.get('reason'))[:200]}"
    notify(cfg, {"kind": "alert", "job": job, "reason": s.get("reason"), "ts": s.get("ts"), "text": msg})
    return msg


class Lock:
    """Exclusive lock file. POSIX flock; on Windows (selftest only) a no-op: one process at a time there."""

    def __init__(self, directory, name=".lock"):
        self.path = os.path.join(directory, name)

    def __enter__(self):
        self.f = open(self.path, "a")
        if fcntl:
            fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        if fcntl:
            fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


if __name__ == "__main__":
    # python3 boxlib.py alert <job> [--config PATH]   (used by fewzhun-box-alert@.service)
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["alert"])
    ap.add_argument("job")
    ap.add_argument("--config")
    a = ap.parse_args()
    if not a.job.replace("-", "").isalnum():
        sys.exit("job must be a plain name")
    print(alert(load_config(a.config), a.job))
