#!/usr/bin/env python3
"""Read-only environment check for the firm-setup skill.

Reports what is already installed vs missing so the setup skill installs ONLY the
gaps. Changes nothing. Safe to run any time. Prints a human summary and a JSON
block the assistant can parse.

Run with whatever Python exists: `python check_environment.py` (or `py ...` on
Windows). If Python itself is missing, that IS the first install gap.
"""
import json
import os
import platform
import shutil
import sys

HOME = os.path.expanduser("~")


def have(cmd):
    return shutil.which(cmd) is not None


def have_tesseract():
    """Tesseract on PATH or in a common Windows/macOS install location (its
    installer often does not add itself to PATH; the firm calls it by full path)."""
    if have("tesseract"):
        return True
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/opt/homebrew/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/usr/bin/tesseract",
    ]
    return any(os.path.exists(c) for c in candidates)


def have_browser():
    """A Chromium browser on PATH or in a common Windows/macOS install location."""
    if have("chrome") or have("msedge") or have("google-chrome") or have("chromium"):
        return True
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app",
        "/Applications/Microsoft Edge.app",
    ]
    return any(os.path.exists(c) for c in candidates)


def venv_ok(path):
    p = os.path.join(HOME, path)
    # a usable venv has a python executable under Scripts (win) or bin (unix)
    return (
        os.path.isfile(os.path.join(p, "Scripts", "python.exe"))
        or os.path.isfile(os.path.join(p, "bin", "python"))
    )


def pip_pkg(mod):
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def main():
    report = {
        "os": platform.system(),
        "python": {
            "present": True,
            "version": platform.python_version(),
        },
        "command_line_tools": {
            "git": have("git"),
            "tesseract": have_tesseract(),
            "chrome_or_edge": have_browser(),
            "winget": have("winget"),
            "brew": have("brew"),
        },
        "venvs": {
            "notebooklm": venv_ok(".notebooklm-venv"),
            "scraper": venv_ok(".scraper-venv"),
            "project_exporter": venv_ok(os.path.join(".claude-project-exporter", "venv")),
        },
        # packages checked in the CURRENT interpreter (firm filing tools live here)
        "packages_main": {
            "reportlab": pip_pkg("reportlab"),
            "pdfminer": pip_pkg("pdfminer"),
            "spellchecker": pip_pkg("spellchecker"),
            "pdfplumber": pip_pkg("pdfplumber"),
            "pymupdf": pip_pkg("fitz"),
            "pytesseract": pip_pkg("pytesseract"),
        },
        # these usually live in the scraper venv, not the main interpreter; presence
        # here is a bonus, absence is expected if they are in the venv
        "packages_optional": {
            "markitdown": pip_pkg("markitdown"),
            "seleniumbase": pip_pkg("seleniumbase"),
        },
    }

    # workspace files (run from the workspace root to be meaningful)
    cwd = os.getcwd()
    report["workspace"] = {
        "cwd": cwd,
        "firm_config": os.path.isfile(os.path.join(cwd, "firm.config.json")),
        "case_profile": os.path.isfile(os.path.join(cwd, "case-profile.md")),
        "case_checklist": os.path.isfile(os.path.join(cwd, "CASE-CHECKLIST.md")),
        "is_git_repo": os.path.isdir(os.path.join(cwd, ".git")),
    }

    # build the gap list = the things setup still needs to do
    gaps = []
    clt = report["command_line_tools"]
    if not clt["git"]:
        gaps.append("git")
    if not clt["tesseract"]:
        gaps.append("tesseract (OCR for scanned documents)")
    if not clt["chrome_or_edge"]:
        gaps.append("a Chromium browser (for legal-site research)")
    for name, ok in report["venvs"].items():
        if not ok:
            gaps.append(f"{name} venv")
    for name, ok in report["packages_main"].items():
        if not ok:
            gaps.append(f"python package: {name}")
    if not report["workspace"]["firm_config"]:
        gaps.append("workspace files (clawyer-setup writes them with clawyer_init.py)")
    report["gaps"] = gaps
    report["ready"] = len(gaps) == 0

    print("=== Firm setup - environment check ===")
    print(f"OS: {report['os']} | Python {report['python']['version']}")
    print("\nCommand-line tools:")
    for k, v in clt.items():
        print(f"  {'OK ' if v else 'MISSING'}  {k}")
    print("\nFeature venvs:")
    for k, v in report["venvs"].items():
        print(f"  {'OK ' if v else 'MISSING'}  {k}")
    print("\nFiling packages (this interpreter):")
    for k, v in report["packages_main"].items():
        print(f"  {'OK ' if v else 'MISSING'}  {k}")
    print("\nWorkspace:")
    for k, v in report["workspace"].items():
        print(f"  {v}  {k}")
    print("\nGAPS TO CLOSE:" if gaps else "\nNo gaps. Environment looks ready.")
    for g in gaps:
        print(f"  - {g}")

    print("\n---JSON---")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
