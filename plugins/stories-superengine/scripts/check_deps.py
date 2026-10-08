#!/usr/bin/env python3
"""Check (and, with --install, set up) what the Stories Superengine needs on this computer.

Usage:
    python check_deps.py             # status JSON; exit 0 = ready, 3 = something missing
    python check_deps.py --install   # installs what's missing, for this user only (no admin), then re-checks

Needs: Python 3.9+, the Playwright browser library + its Chromium (renders the frames), and on
Windows the tzdata package (time zones for scheduling). Publishing tools (composio, a Metricool
connection) are checked by the stories-setup skill, not here.
"""
import importlib.util
import json
import os
import subprocess
import sys


def chromium_ok():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


def tz_ok():
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo("America/New_York")
        return True
    except Exception:
        return False


def status():
    has_pw = importlib.util.find_spec("playwright") is not None
    return {
        "python": {"ok": sys.version_info >= (3, 9), "version": sys.version.split()[0],
                   "fix": "install Python 3.9 or newer"},
        "playwright": {"ok": has_pw, "fix": "pip install --user playwright"},
        "chromium": {"ok": has_pw and chromium_ok(), "fix": "python -m playwright install chromium (~150 MB, one time)"},
        "timezones": {"ok": tz_ok(), "fix": "pip install --user tzdata"},
    }


def install(s):
    pip = [sys.executable, "-m", "pip", "install", "--user", "--quiet", "--disable-pip-version-check"]
    steps = []
    if not s["playwright"]["ok"]:
        steps.append(pip + ["playwright"])
    if not s["timezones"]["ok"]:
        steps.append(pip + ["tzdata"])
    if not s["chromium"]["ok"]:
        steps.append([sys.executable, "-m", "playwright", "install", "chromium"])
    for cmd in steps:
        print("  installing:", " ".join(cmd[2:]), flush=True)
        r = subprocess.run(cmd, timeout=900, env=dict(os.environ))
        if r.returncode:
            print(f"  that step failed (exit {r.returncode}).")


if __name__ == "__main__":
    s = status()
    if "--install" in sys.argv and not all(v["ok"] for v in s.values()):
        if not s["python"]["ok"]:
            sys.exit("Python is older than 3.9. Install a newer Python first.")
        install(s)
        # Re-check in a fresh Python: packages installed this run aren't visible to this process.
        r = subprocess.run([sys.executable, __file__], timeout=300, env=dict(os.environ))
        sys.exit(r.returncode)
    print(json.dumps(s, indent=1))
    missing = [k for k, v in s.items() if not v["ok"]]
    print("\nREADY: every tool is installed." if not missing else f"\nMISSING: {', '.join(missing)}. Run check_deps.py --install.")
    sys.exit(0 if not missing else 3)
