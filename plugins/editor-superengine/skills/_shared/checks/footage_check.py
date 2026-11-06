#!/usr/bin/env python3
"""Own the reel's footage/ledger.json; verify recording bytes and half-open source intervals.

Standard library only. Paths written by add are absolute; relative ledger paths resolve at the reel.
"""
import argparse, hashlib, json, os, sys
from pathlib import Path


def normalized(path):
    return os.path.normcase(os.path.abspath(path))


def asset(reel_dir, path):
    p = Path(path)
    if p.is_file():
        return p.resolve()
    return p if p.is_absolute() else Path(reel_dir) / p


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rows(reel_dir):
    p = Path(reel_dir) / "footage" / "ledger.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list) or any(not isinstance(r, dict) for r in data):
        raise ValueError("the footage ledger needs a list of recordings")
    return data


def add(reel_dir, path, role, origin, licence, job_id=None):
    if role not in {"aroll", "broll"}:
        raise ValueError("the footage role must be aroll or broll")
    if origin not in {"own", "ai"}:
        raise ValueError("the footage origin must be own or ai")
    p = Path(path).absolute()
    sha, ledger = digest(p), rows(reel_dir)
    for r in ledger:
        if r["sha256"] == sha:
            return r["id"]
    ident = "f%02d" % (max([int(r["id"][1:]) for r in ledger] or [0]) + 1)
    row = dict(id=ident, sha256=sha, path=str(p), role=role, origin=origin, licence=licence)
    if job_id is not None:
        row["job_id"] = job_id
    ledger.append(row)
    out = Path(reel_dir) / "footage" / "ledger.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_bytes((json.dumps(ledger, indent=1) + "\n").encode("utf-8"))
    tmp.replace(out)
    return ident


def check(reel_dir, uses):
    """Return plain block lines. Two intervals touching at an endpoint do not overlap."""
    try:
        ledger = rows(reel_dir)
        out, verified, spans = [], {}, {}
        for use in uses:
            p = asset(reel_dir, use["path"])
            key, name = normalized(p), p.name
            if key not in verified:
                matches = [r for r in ledger if normalized(asset(reel_dir, r["path"])) == key]
                if len(matches) != 1:
                    out.append("log exactly one footage ledger entry for %s with footage_check.py add" % name)
                    verified[key] = None
                elif not p.is_file():
                    out.append("this recording is missing: %s" % name)
                    verified[key] = None
                elif digest(p) != matches[0]["sha256"]:
                    out.append("this recording changed after it was logged: %s" % name)
                    verified[key] = None
                else:
                    verified[key] = matches[0]["sha256"]
            sha = verified[key]
            a, b = use["src_in_f"], use["src_out_f"]
            if not (isinstance(a, int) and isinstance(b, int) and 0 <= a < b):
                out.append("the source frame range is invalid for %s" % name)
                continue
            if sha is not None:
                prev = spans.setdefault(sha, [])
                if any(a < y and x < b for x, y in prev):
                    out.append("the same part of %s is used twice" % name)
                prev.append((a, b))
        return list(dict.fromkeys(out))
    except (OSError, ValueError, KeyError, TypeError) as e:
        return ["the footage ledger could not be checked: " + str(e).splitlines()[0]]


def cut_uses(cuts, raw=None):
    takes = cuts.get("takes") or {}
    return [dict(path=takes[str(s.get("take", 1))]["raw"] if takes else raw,
                 src_in_f=s["src_in_f"], src_out_f=s["src_out_f"]) for s in cuts["segments"]]


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    a = sub.add_parser("add")
    a.add_argument("reel_dir"); a.add_argument("path")
    a.add_argument("--role", required=True); a.add_argument("--origin", required=True)
    a.add_argument("--licence", required=True); a.add_argument("--job-id")
    c = sub.add_parser("check")
    c.add_argument("reel_dir"); c.add_argument("work")
    args = ap.parse_args()
    try:
        if args.command == "add":
            print(add(args.reel_dir, args.path, args.role, args.origin, args.licence, args.job_id))
            return 0
        work = Path(args.work)
        cuts = json.loads((work / "cuts.json").read_text(encoding="utf-8"))
        raw = None if cuts.get("takes") else json.loads((work / "probe.json").read_text(encoding="utf-8"))["input"]
        blocks = check(args.reel_dir, cut_uses(cuts, raw))
        for line in blocks:
            print(line)
        return 3 if blocks else 0
    except (OSError, ValueError, KeyError, TypeError) as e:
        print("the footage step stopped: " + str(e).splitlines()[0])
        return 3


if __name__ == "__main__":
    sys.exit(main())
