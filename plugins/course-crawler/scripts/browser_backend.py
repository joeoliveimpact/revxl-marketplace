r"""
browser_backend.py ... report which agentic-browser backends are usable.

What this does (plain English):
  The plugin can drive a browser through more than one backend. This script
  inspects what's installed/running on this machine and prints a JSON report
  the skill uses to decide which backend to use (and what to offer if none
  work). It does NOT pick the backend ... the skill does that, because only
  the model can see which `mcp__<server>__*` tools are loaded this session.

  This script only covers the parts a shell can actually check:
    - is the browser-use venv binary installed (from /setup)?
    - is there a Chromium running with a remote-debugging port (any backend)?
    - is the `claude` CLI available to list configured MCP servers?

Backends, in the order the skill should prefer them:
  1. superpowers-chrome  ... tool `mcp__plugin_superpowers-chrome_chrome__use_browser`
                             present in-session. Zero setup. Preferred.
  2. browser-use         ... `mcp__browser-use__*` tools present; binary at
                             ~/.iss/venv (Mac/Linux) or %USERPROFILE%\.iss\venv.
  3. playwright          ... a Playwright MCP if the user has one configured.
  None of the above       ... fall back to manual cookie paste (see /login),
                              or offer to run /setup to install browser-use.

How to run:
  python ${CLAUDE_SKILL_DIR}/../scripts/browser_backend.py
  python ${CLAUDE_SKILL_DIR}/../scripts/browser_backend.py --json

Why this exists:
  Centralizes the shell-checkable signals so every skill that needs a browser
  (login, course discovery) asks the same questions the same way, and the
  fallback story is consistent.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Reuse the cross-platform CDP discovery already written for cookie dumping
# instead of duplicating the ps/Get-CimInstance logic.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from dump_cookies import find_cdp_port
except Exception:  # pragma: no cover - dump_cookies imports httpx/websockets
    find_cdp_port = None


# Windows consoles default to cp1252; force UTF-8 so non-ASCII never crashes
# a print(). No-op where already UTF-8 or not reconfigurable.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def venv_python() -> Path:
    """Path to the per-user venv's Python, OS-aware. May not exist yet."""
    iss = Path.home() / ".iss" / "venv"
    if platform.system() == "Windows":
        return iss / "Scripts" / "python.exe"
    return iss / "bin" / "python"


def browser_use_binary() -> Path:
    iss = Path.home() / ".iss" / "venv"
    if platform.system() == "Windows":
        return iss / "Scripts" / "browser-use.exe"
    return iss / "bin" / "browser-use"


def running_cdp_port() -> int | None:
    """A debuggable Chromium may have been launched by ANY backend (browser-use
    or superpowers-chrome). If we find one, dump_cookies.py can capture from it
    no matter who started it."""
    if find_cdp_port is None:
        return None
    try:
        return find_cdp_port()
    except Exception:
        return None


def configured_mcps() -> list[str]:
    """If the `claude` CLI is on PATH, list configured MCP servers. This is a
    best-effort hint only ... the authoritative check (which mcp tools are
    actually loaded this session) is done by the skill/model, not here."""
    claude = shutil.which("claude")
    if not claude:
        return []
    try:
        r = subprocess.run([claude, "mcp", "list"], capture_output=True,
                            text=True, timeout=10)
        if r.returncode != 0:
            return []
        names = []
        for line in r.stdout.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            names.append(line.split(":", 1)[0].strip())
        return names
    except Exception:
        return []


def build_report() -> dict:
    bu_bin = browser_use_binary()
    mcps = configured_mcps()
    port = running_cdp_port()

    report = {
        "os": platform.system(),
        "venv_python": str(venv_python()),
        "venv_python_exists": venv_python().exists(),
        "browser_use": {
            "binary": str(bu_bin),
            "installed": bu_bin.exists(),
        },
        "configured_mcps_hint": mcps,
        "running_cdp_port": port,
        # The skill should also check its own in-session tool list for these:
        "skill_should_check_tools": [
            "mcp__plugin_superpowers-chrome_chrome__use_browser",
            "mcp__browser-use__*",
        ],
        "preference_order": ["superpowers-chrome", "browser-use", "playwright"],
        "fallbacks": [
            "If a chosen backend errors, try the next in preference_order.",
            "If none are available, use the manual cookie-paste path in /login.",
            "Offer to run /setup to install browser-use as a last resort.",
        ],
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Report usable browser backends.")
    parser.add_argument("--json", action="store_true", help="Emit raw JSON only.")
    args = parser.parse_args()

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(json.dumps(report, indent=2))
    print()
    print("Backend guidance:")
    if report["running_cdp_port"]:
        print(f"  - A debuggable Chromium is live on port {report['running_cdp_port']}; "
              "cookie capture will work regardless of which backend started it.")
    if report["browser_use"]["installed"]:
        print("  - browser-use is installed (from /setup).")
    else:
        print("  - browser-use NOT installed; /setup would add it.")
    print("  - The skill must still confirm which mcp__* browser tools are "
          "actually loaded this session and pick per preference_order.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
