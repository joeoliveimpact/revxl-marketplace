#!/usr/bin/env python3
"""deps.py - check what Clawyer needs on this computer and install what is missing, without the person typing.

Run it with the interpreter that find-python recorded in .clawyer/.python:
  <python> deps.py check      read-only: what is here, what is missing, what each missing thing costs them
  <python> deps.py install    install the missing pieces, then check again
  <python> deps.py --selftest (no installs, no network)

It prints one JSON object. Each item has: name, what (plain words), status (ok | installed | missing | failed |
needs_person), and for anything not ok a "means" line Claude can say out loud. Nothing here needs an admin
password. Where the system itself may show a box (Windows "allow this app to make changes", Apple developer
tools), the item says so in "person_step", because that click is the person's.

Standard library only: this is the script that installs the other libraries.
"""
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys

# import name, pip name, what it is for (plain words), what breaks without it
PACKAGES = [
    ("markitdown", "markitdown", "reads Word, Excel, PowerPoint and typed PDFs", "I can't convert most documents to text"),
    ("fitz", "pymupdf", "reads PDF pages", "PDF reading falls back to a slower, weaker reader"),
    ("pypdf", "pypdf", "backup PDF reader", "no backup if the main PDF reader fails"),
    ("pdfminer", "pdfminer.six", "pulls text out of PDFs", "some PDFs come out with missing text"),
    ("reportlab", "reportlab", "builds court-ready PDFs", "I can't produce a print-ready PDF of a filing"),
    ("spellchecker", "pyspellchecker", "spell check for filings", "filings go out without the spelling gate"),
    ("PIL", "pillow", "opens photos and scans", "photos of documents can't be read"),
    ("pytesseract", "pytesseract", "connects to the scanned-page reader", "scanned pages can't be read"),
]
TESSERACT_PATHS = [r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                   os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
                   "/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract", "/usr/bin/tesseract"]
WINGET_FLAGS = ["--exact", "--silent", "--accept-package-agreements", "--accept-source-agreements"]


def have_module(name):
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def find_tool(name, extra=()):
    return shutil.which(name) or next((p for p in extra if p and os.path.exists(p)), None)


def brew():
    return next((b for b in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew") if os.path.exists(b)), shutil.which("brew"))


def run(cmd, timeout=900):
    """Run a command quietly. Returns (ok, last line of output). Never raises."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8", "PIP_DISABLE_PIP_VERSION_CHECK": "1"})
        tail = ((r.stderr or r.stdout or "").strip().splitlines() or [""])[-1][:300]
        return r.returncode == 0, tail
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:300]


def check():
    items = []
    for mod, pip_name, what, means in PACKAGES:
        ok = have_module(mod)
        items.append({"name": pip_name, "kind": "package", "what": what, "status": "ok" if ok else "missing",
                      **({} if ok else {"means": means})})
    tess = find_tool("tesseract", TESSERACT_PATHS)
    items.append({"name": "tesseract", "kind": "tool", "what": "the free reader for scanned pages and photos",
                  "status": "ok" if tess else "missing",
                  **({"path": tess} if tess else {"means": "scanned pages and photos can't be read; typed documents are fine"})})
    git = find_tool("git", [r"C:\Program Files\Git\cmd\git.exe"])
    bash = find_tool("bash", [r"C:\Program Files\Git\bin\bash.exe"])
    ok = bool(git and bash)
    items.append({"name": "git", "kind": "tool", "what": "runs Clawyer's start-of-session reminders",
                  "status": "ok" if ok else "missing",
                  **({} if ok else {"means": "the case does not load by itself at the start of a session; I load it by hand"})})
    return items


def pip_install(names):
    base = [sys.executable, "-m", "pip", "install", "--quiet"]
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    user = [] if in_venv else ["--user"]
    ok, tail = run(base + user + names)
    if not ok and "externally-managed-environment" in tail:
        # Homebrew and some Linux Pythons refuse plain pip. A per-user install with this flag touches only
        # the person's own folder, never the system's packages.
        ok, tail = run(base + user + ["--break-system-packages"] + names)
    return ok, tail


def install_tool(name):
    """Returns (status, note). status: installed | failed | needs_person."""
    sysname = platform.system()
    if sysname == "Windows":
        winget = shutil.which("winget")
        if not winget:
            return "needs_person", "Windows' App Installer is missing. They install 'App Installer' from the Microsoft Store, then setup runs again."
        if name == "git":
            ok, tail = run([winget, "install", "--id", "Git.Git", "--scope", "user"] + WINGET_FLAGS)
            if not ok:  # some Git builds have no per-user installer
                ok, tail = run([winget, "install", "--id", "Git.Git"] + WINGET_FLAGS)
        else:
            ok, tail = run([winget, "install", "--id", "UB-Mannheim.TesseractOCR"] + WINGET_FLAGS)
        return ("installed", "") if ok else ("failed", tail)
    if sysname == "Darwin":
        b = brew()
        if name == "git":
            return "needs_person", ("Apple shows a box offering to install its developer tools the first time git is used. "
                                    "They click Install and wait for it to finish, then setup runs again.")
        if not b:
            return "needs_person", ("No Homebrew on this Mac, so the scanned-page reader can't be installed for them. "
                                    "Typed documents work without it. Offer to carry on.")
        ok, tail = run([b, "install", "tesseract"])
        return ("installed", "") if ok else ("failed", tail)
    return "needs_person", f"Install {name} with this system's package manager."


def install():
    before = check()
    missing_pkgs = [i["name"] for i in before if i["kind"] == "package" and i["status"] == "missing"]
    notes = {}
    if missing_pkgs:
        ok, tail = pip_install(missing_pkgs)
        if not ok:  # one bad package must not block the rest: retry one at a time
            for n in missing_pkgs:
                ok1, tail1 = pip_install([n])
                if not ok1:
                    notes[n] = ("failed", tail1)
    for i in before:
        if i["kind"] == "tool" and i["status"] == "missing":
            notes[i["name"]] = install_tool(i["name"])
    importlib.invalidate_caches()
    after = check()
    was_missing = {i["name"] for i in before if i["status"] == "missing"}
    for i in after:
        n = i["name"]
        if i["status"] == "ok" and n in was_missing:
            i["status"] = "installed"
        elif i["status"] == "missing" and n in notes:
            st, note = notes[n]
            if st == "installed":  # installed, but not visible to this session yet
                i["status"], i["person_step"] = "needs_person", "Installed. They quit Claude completely and open it again in this folder so it is picked up."
            elif st == "needs_person":
                i["status"], i["person_step"] = "needs_person", note
            else:
                i["status"], i["error"] = "failed", note
    return after


def report(items):
    bad = [i for i in items if i["status"] not in ("ok", "installed")]
    print(json.dumps({"python": sys.executable, "python_version": "%d.%d.%d" % sys.version_info[:3],
                      "system": platform.system(), "ready": not bad, "not_ready": [i["name"] for i in bad],
                      "items": items}, indent=2))
    return 0


def selftest():
    items = check()
    names = [i["name"] for i in items]
    assert names[-2:] == ["tesseract", "git"] and len(items) == len(PACKAGES) + 2, names
    assert all(i["status"] in ("ok", "missing") for i in items)
    assert all("means" in i for i in items if i["status"] == "missing"), "every missing item must say what it costs"
    assert have_module("json") and not have_module("no_such_module_clawyer")
    assert find_tool("no-such-tool-clawyer") is None
    ok, tail = run([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert ok is False                                   # a failed command is reported, never raised
    assert run(["no-such-binary-clawyer"])[0] is False
    print("SELFTEST OK")
    return 0


def main():
    a = sys.argv[1:]
    if "--selftest" in a:
        return selftest()
    if a == ["check"]:
        return report(check())
    if a == ["install"]:
        return report(install())
    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
