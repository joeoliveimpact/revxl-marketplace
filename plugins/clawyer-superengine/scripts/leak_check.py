#!/usr/bin/env python
"""Fail if personal or case details are in the files this plugin ships.

Run from the plugin folder before every release:
    python scripts/leak_check.py
Pass names, a county and case numbers as extra terms (matched in any letter case):
    python scripts/leak_check.py Smith "Cook County" 2026-D-12345

It scans every file git would publish under the current folder. Two files are skipped, each for a stated
reason: this script (it holds the patterns) and scripts/report_to_joe.py (the REVXL failure-report helper,
copied from the marketplace, which has to name the REVXL relay address it posts to).
"""
import re
import subprocess
import sys

SKIP = ("leak_check.py", "scripts/report_to_joe.py")
BLOCK = [
    r"C:[\\/]+Users[\\/]+[A-Za-z0-9]",  # a real Windows user folder ({USER} placeholders pass)
    r"/c/Users/",
    r"/home/[a-z]",
    r"Claude-Workspaces",              # upstream author's machine path
    r"linear\.app/",
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",  # account/notebook ids
    r"1d2999a0|69084fde|86fc52a3",     # upstream author's notebook ids
    r"\b\d{2}-CV-\d{4,}",              # a real cause number shape left in upstream scripts
] + [re.escape(a) for a in sys.argv[1:]]

listed = subprocess.run(
    ["git", "ls-files", "-co", "--exclude-standard"],
    capture_output=True, text=True,
).stdout.splitlines()

hits = 0
scanned = 0
for f in listed:
    if not f or f.replace("\\", "/").endswith(SKIP):
        continue
    try:
        text = open(f, encoding="utf-8").read()
    except Exception:
        continue
    scanned += 1
    for n, line in enumerate(text.splitlines(), 1):
        for pat in BLOCK:
            if re.search(pat, line, re.I):
                hits += 1
                print("%s:%d: [%s] %s" % (f, n, pat[:30], line.strip()[:100]))

if not scanned:  # an empty scan is a broken check, never a pass
    print("LEAK CHECK: FAILED, no files scanned (run it from inside the plugin folder of a git checkout)")
    sys.exit(1)
print("LEAK CHECK: FAILED, %d hit(s) in %d files" % (hits, scanned) if hits else "LEAK CHECK: clean (%d files)" % scanned)
sys.exit(1 if hits else 0)
