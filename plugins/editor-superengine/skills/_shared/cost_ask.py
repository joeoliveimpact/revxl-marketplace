"""Ask before paying (hard rule: consent and money). Stdlib only.

The rule every caller follows: nothing that costs money runs without --yes, and Claude passes --yes only after the
client said yes to the plan_text() lines. A caller run without --yes refuses (refuse_without_yes, exit 3) and calls
nothing.

The ledger, <reel>/work/paid-jobs.json, remembers every paid job by job_key() (the service, the input file's bytes
and the settings). The same input with the same settings is never paid for twice: find_reusable() hands back a
result whose file still matches its recorded sha256, and find_pending() finds a job that was paid for but never
downloaded, so the caller fetches it instead of starting a new one.

  python cost_ask.py --selftest
"""
import hashlib, json, os, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

REFUSAL = ("This step costs money, so it did not run. Show the client the plan first, and run it again with "
           "--yes only after they say yes.")


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def job_key(service, input_path, settings):
    """sha256 of the service, the input file's sha256 and the settings as canonical JSON."""
    canon = json.dumps(settings, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256("\0".join([service, file_sha256(input_path), canon]).encode("utf-8")).hexdigest()


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(ledger):
    try:
        data = json.loads(Path(ledger).read_text(encoding="utf-8"))
        return data if isinstance(data.get("jobs"), dict) else {"jobs": {}}
    except (OSError, ValueError, AttributeError):
        return {"jobs": {}}


def _good(entry):
    r, sha = entry.get("result"), entry.get("result_sha256")
    return bool(r and sha and Path(r).is_file() and file_sha256(r) == sha)


def find_reusable(ledger, key):
    """The entry whose result file still exists and still matches its stored sha256, else None."""
    e = load(ledger)["jobs"].get(key)
    return e if e and _good(e) else None


def find_pending(ledger, key):
    """An entry with a job id but no good result (paid for, not yet downloaded), else None."""
    e = load(ledger)["jobs"].get(key)
    return e if e and e.get("job_id") and not _good(e) else None


def plan_text(service, what, cost_line):
    """The plain lines Claude shows the client before anything paid runs."""
    return "\n".join(["This step uses %s, which costs money." % service,
                      "What will run: %s." % what,
                      "Expected cost: %s." % cost_line,
                      "Say yes to go ahead."])


def refuse_without_yes(yes):
    """None when the client said yes; otherwise prints the refusal and returns exit code 3."""
    if yes:
        return None
    print(REFUSAL)
    return 3


def record(ledger, key, **fields):
    """Merge fields (service, what, expected_cost, yes_at, job_id, status, result, result_sha256, ...) into the
    key's entry and write the ledger whole (.tmp then os.replace), so a crash never leaves half a file."""
    data = load(ledger)
    e = data["jobs"].setdefault(key, {})
    e.update(fields, updated_at=now())
    p = Path(ledger)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_bytes((json.dumps(data, indent=1) + "\n").encode("utf-8"))
    os.replace(tmp, p)
    return e


def selftest():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        src, res, led = d / "in.wav", d / "out.wav", d / "work" / "paid-jobs.json"
        src.write_bytes(b"input bytes")
        settings = {"b": 1, "a": [1, 2]}
        key = job_key("svc", src, settings)
        assert key == job_key("svc", src, {"a": [1, 2], "b": 1}), "settings order must not change the key"
        assert key != job_key("svc", src, {"a": [1, 2], "b": 2}), "other settings, other key"
        assert refuse_without_yes(False) == 3, "no yes: the caller refuses"
        assert refuse_without_yes(True) is None
        assert find_reusable(led, key) is None and find_pending(led, key) is None, "empty ledger: nothing to reuse"
        record(led, key, service="svc", job_id="job-1", status="started", yes_at=now())
        assert find_pending(led, key)["job_id"] == "job-1", "paid, not downloaded: pending"
        res.write_bytes(b"result bytes")
        record(led, key, result=str(res), result_sha256=file_sha256(res), status="done")
        assert find_reusable(led, key)["job_id"] == "job-1", "a good result is reused"
        assert find_pending(led, key) is None
        res.write_bytes(b"result bytez")
        assert find_reusable(led, key) is None, "changed bytes: not reused"
        assert find_pending(led, key)["job_id"] == "job-1", "changed bytes: download again, never pay again"
        assert not (led.parent / "paid-jobs.json.tmp").exists() and b"\r" not in led.read_bytes()
    print("cost_ask selftest: ok")
    return 0


def main(argv=None):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    if "--selftest" in (sys.argv[1:] if argv is None else argv):
        return selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
