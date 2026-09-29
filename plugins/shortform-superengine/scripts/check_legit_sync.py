#!/usr/bin/env python3
"""check_legit_sync.py ... proves the five Legit Content Skills copies match their master.

Each of hook, rehooks, viral, angles and polarize ships its method as
skills/<name>/references/legit-<name>.md, a byte-identical copy of the public
master's skills/<name>/SKILL.md. Nothing is normalised: an LF to CRLF flip is
drift, on purpose (.gitattributes keeps the copies LF).

    python3 plugins/shortform-superengine/scripts/check_legit_sync.py --master <legit-content-skills checkout>
        sha256 of every copy against the master SKILL.md. Exit 1 on drift, naming
        each copy. With no drift, (re)writes the pinned manifest beside this file:
        legit-sync-manifest.json, one sha256 per copy plus the master commit.
        A local release step: the master repo is not reachable from CI.

    python3 plugins/shortform-superengine/scripts/check_legit_sync.py --check-manifest
        No master needed. Every copy against the pinned manifest: exit 1 when a
        copy changed since the last sync.

    python3 plugins/shortform-superengine/scripts/check_legit_sync.py --selftest
        Builds a throwaway plugin and master, tampers one copy, expects exit 1.

Stdlib only, Python 3.9+.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

NAMES = ("hook", "rehooks", "viral", "angles", "polarize")
PLUGIN = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).resolve().with_name("legit-sync-manifest.json")


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _rel(n):
    return "skills/%s/references/legit-%s.md" % (n, n)


def drift_vs_master(plugin, master):
    bad = []
    for n in NAMES:
        c, m = plugin / _rel(n), master / "skills" / n / "SKILL.md"
        if not c.exists():
            bad.append("%s: copy missing (%s)" % (n, _rel(n)))
        elif not m.exists():
            bad.append("%s: master missing (skills/%s/SKILL.md)" % (n, n))
        elif _sha(c) != _sha(m):
            bad.append("%s: %s differs from master skills/%s/SKILL.md" % (n, _rel(n), n))
    return bad


def drift_vs_manifest(plugin, manifest):
    try:
        pinned = json.loads(manifest.read_text(encoding="utf-8"))["copies"]
    except (OSError, ValueError, KeyError) as e:
        return ["manifest unreadable (%s): %s" % (manifest.name, e)]
    bad = []
    for n in NAMES:
        c = plugin / _rel(n)
        if _rel(n) not in pinned:
            bad.append("%s: not pinned in the manifest" % n)
        elif not c.exists():
            bad.append("%s: copy missing (%s)" % (n, _rel(n)))
        elif _sha(c) != pinned[_rel(n)]:
            bad.append("%s: %s changed since the last sync" % (n, _rel(n)))
    return bad


def _master_commit(master):
    try:
        head = subprocess.run(["git", "-C", str(master), "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True, timeout=30).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(master), "status", "--porcelain", "--", "skills"],
                               check=True, capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return head + ("-dirty" if dirty else "")


def run_master(plugin, master, manifest):
    bad = drift_vs_master(plugin, master)
    for b in bad:
        print("DRIFT " + b)
    if bad:
        print("check_legit_sync: %d of %d copies drifted from the master" % (len(bad), len(NAMES)))
        return 1
    data = {"master_commit": _master_commit(master),
            "copies": {_rel(n): _sha(plugin / _rel(n)) for n in NAMES}}
    manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("check_legit_sync: %d copies match the master at %s; manifest pinned"
          % (len(NAMES), data["master_commit"]))
    return 0


def run_manifest(plugin, manifest):
    bad = drift_vs_manifest(plugin, manifest)
    for b in bad:
        print("DRIFT " + b)
    if bad:
        print("check_legit_sync: %d problem(s) against the pinned manifest" % len(bad))
        return 1
    print("check_legit_sync: %d copies match the pinned manifest" % len(NAMES))
    return 0


def selftest():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        plugin, master, man = t / "plugin", t / "master", t / "manifest.json"
        for n in NAMES:
            for p in (plugin / _rel(n), master / "skills" / n / "SKILL.md"):
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(("# %s\nline two\n" % n).encode("utf-8"))
        assert run_master(plugin, master, man) == 0
        assert run_manifest(plugin, man) == 0
        c = plugin / _rel("viral")
        c.write_bytes(c.read_bytes().replace(b"\n", b"\r\n"))   # an EOL flip is drift
        assert run_master(plugin, master, man) == 1
        assert run_manifest(plugin, man) == 1
        c.unlink()                                               # so is a missing copy
        assert run_manifest(plugin, man) == 1
    print("selftest: ok")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--master", type=Path, help="a legit-content-skills checkout")
    g.add_argument("--check-manifest", action="store_true")
    g.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.check_manifest:
        return run_manifest(PLUGIN, MANIFEST)
    return run_master(PLUGIN, a.master, MANIFEST)


if __name__ == "__main__":
    sys.exit(main())
