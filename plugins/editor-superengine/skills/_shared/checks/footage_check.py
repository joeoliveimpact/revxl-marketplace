#!/usr/bin/env python3
"""Own the reel's footage/ledger.json; verify recording bytes and half-open source intervals.

Standard library only. Paths written by add are reel-relative POSIX paths inside the reel,
absolute outside it. Ledger reads resolve relative paths at the reel and recover moved clips.
"""
import argparse, hashlib, json, os, sys
from functools import lru_cache
from pathlib import Path


def normalized(path):
    return os.path.normcase(os.path.abspath(path))


def asset(reel_dir, path, resolved=None):
    p = Path(path)
    reel = Path(reel_dir).resolve()
    local = reel / p
    if not p.is_absolute() and local.is_file():
        return local.resolve()
    if p.is_absolute() and not p.resolve().is_relative_to(reel):
        resolved = resolve_rows(reel, rows(reel)) if resolved is None else resolved
        # Stored probe/take paths may predate both the move and relative ledger rows.
        candidates = [(r, clip) for r, clip in resolved
                      if os.path.normcase(Path(r["path"]).name) == os.path.normcase(p.name)]
        exact = [(r, clip) for r, clip in candidates
                 if Path(r["path"]).is_absolute() and normalized(r["path"]) == normalized(p)]
        if not exact and len(candidates) > 1:
            # Same-named recordings: bind only to the one whose folder tail matches the stored path best,
            # and never guess between two equally good matches (a wrong take would pass its own sha).
            scored = [(_tail(p, clip.relative_to(reel)) if clip.resolve().is_relative_to(reel) else 0, row, clip)
                      for row, clip in candidates]
            best = max(score for score, _, _ in scored)
            top = [(row, clip) for score, row, clip in scored if score == best]
            candidates = top if len(top) == 1 and best > 1 else []
        for row, clip in exact or candidates:
            if not clip.resolve().is_relative_to(reel) or not clip.is_file():
                continue
            if row.get("size") is not None and clip.stat().st_size != row["size"]:
                continue
            if digest(clip) == row["sha256"]:
                return clip
    if p.is_file():
        return p.resolve()
    return p if p.is_absolute() else Path(reel_dir) / p


def _tail(stored, local):
    """How many trailing path parts (file name, then folders) two paths share."""
    count = 0
    for old, new in zip(reversed(Path(stored).parts), reversed(Path(local).parts)):
        if os.path.normcase(old) != os.path.normcase(new):
            break
        count += 1
    return count


def digest(path):
    p = Path(path).resolve()
    stat = p.stat()
    return _digest(str(p), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=512)
def _digest(path, mtime_ns, size):
    """Reuse bytes only while the path, modification time and size are unchanged."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def name_index(reel):
    index = {}
    for candidate in reel.rglob("*"):
        if candidate.is_file() and candidate.resolve().is_relative_to(reel):
            index.setdefault(os.path.normcase(candidate.name), []).append(candidate)
    return index


def resolve_rows(reel_dir, ledger):
    """Share one name index across all rows in this read-only check."""
    reel = Path(reel_dir).resolve()
    index = name_index(reel) if any(Path(r["path"]).is_absolute() and
                                   not Path(r["path"]).resolve().is_relative_to(reel) for r in ledger) else {}
    return [(r, locate(reel, r, index)) for r in ledger]


def locate(reel_dir, row, index=None):
    """Prefer a verified reel-local copy; otherwise keep the stored path without writing it.

    Old rows have no size, so only those rows fall back to name + SHA-256.
    New rows filter by name and size before hashing any candidates.
    """
    reel, p = Path(reel_dir).resolve(), Path(row["path"])
    if not p.is_absolute():
        return reel / p
    if p.resolve().is_relative_to(reel):
        return p
    candidates = []
    index = name_index(reel) if index is None else index
    for candidate in index.get(os.path.normcase(p.name), []):
        if row.get("size") is not None and candidate.stat().st_size != row["size"]:
            continue
        # Prefer the original relative tail even when the reel itself was renamed.
        tail = 0
        for old, new in zip(reversed(p.parts), reversed(candidate.relative_to(reel).parts)):
            if os.path.normcase(old) != os.path.normcase(new):
                break
            tail += 1
        candidates.append((-tail, candidate.as_posix(), candidate))
    for _, _, candidate in sorted(candidates):
        if digest(candidate) == row["sha256"]:
            return candidate
    return p


def missing_clip(path):
    return ("This B-roll clip isn't in the reel folder any more: %s. "
            "Put it back in the reel's broll folder, or remove it from the Beat Map." % Path(path).name)


def changed_clip(path):
    return ("This B-roll clip changed after it was added: %s. "
            "Put the original clip back, or remove it from the Beat Map." % Path(path).name)


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
    reel = Path(reel_dir).resolve()
    resolved = p.resolve()
    stored = resolved.relative_to(reel).as_posix() if resolved.is_relative_to(reel) else str(p)
    row = dict(id=ident, sha256=sha, path=stored, size=p.stat().st_size,
               role=role, origin=origin, licence=licence)
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
        resolved = resolve_rows(reel_dir, ledger)
        out, verified, spans = [], {}, {}
        for use in uses:
            p = asset(reel_dir, use["path"], resolved)
            key, name = normalized(p), p.name
            if key not in verified:
                matches = [r for r, clip in resolved if normalized(clip) == key]
                same_name = [r for r, clip in resolved
                             if os.path.normcase(Path(r["path"]).name) == os.path.normcase(name)]
                row = (matches or same_name or [{}])[0]
                role = row.get("role", use.get("role"))
                if not p.is_file():
                    out.append("this recording is missing: %s" % name if role == "aroll"
                               else missing_clip(p))
                    verified[key] = None
                elif not matches and same_name:
                    out.append("this recording changed after it was logged: %s" % name if role == "aroll"
                               else changed_clip(p))
                    verified[key] = None
                elif len(matches) != 1:
                    out.append("log exactly one footage ledger entry for %s with footage_check.py add" % name)
                    verified[key] = None
                elif digest(p) != matches[0]["sha256"]:
                    out.append("this recording changed after it was logged: %s" % name if role == "aroll"
                               else changed_clip(p))
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
    return [dict(path=takes[str(s.get("take", 1))]["raw"] if takes else raw, role="aroll",
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
