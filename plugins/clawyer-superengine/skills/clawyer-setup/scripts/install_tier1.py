#!/usr/bin/env python3
"""Tier 1 installer for firm-setup v1.5.0.

Installs the five Tier-1 tools (no human action required):
  1. PaddleOCR + PaddlePaddle (with runtime-tuning caveat)
  2. Microsoft Presidio (analyzer + anonymizer)
  3. spaCy + en_core_web_lg
  4. NotebookLM CLI (binary only; browser login is Tier 2)
  5. Ollama (winget on Windows, brew on Mac)

Idempotent. Skips anything already installed. Prints plain status lines and a
JSON report at the end. Never invents capability. Each block records what it
attempted, and what landed, so the caller can update FIRM-TOOLING-INVENTORY.md.
"""
import json
import os
import platform
import shutil
import subprocess
import sys


def have(cmd):
    return shutil.which(cmd) is not None


def run(cmd, check=False):
    """Run a command, return (rc, stdout+stderr). Never raises on non-zero unless check."""
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True)
        out = (p.stdout or "") + (p.stderr or "")
        if check and p.returncode != 0:
            print(out)
        return p.returncode, out
    except Exception as e:
        return 1, str(e)


def pip_install(pkgs, label):
    pkgs_list = pkgs if isinstance(pkgs, list) else [pkgs]
    print(f"  installing {label} ...")
    rc, out = run([sys.executable, "-m", "pip", "install", "--upgrade"] + pkgs_list)
    ok = rc == 0
    print(f"  {'OK ' if ok else 'FAIL'}  {label}")
    return ok, out[-2000:] if not ok else ""


def pip_have(mod):
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def install_paddle():
    """PaddleOCR + PaddlePaddle. CPU wheel by default. Runtime tuning is the user's first launch."""
    print("\n[1/5] PaddleOCR + PaddlePaddle")
    if pip_have("paddleocr") and pip_have("paddle"):
        print("  OK   already installed")
        return {"status": "already-installed", "note": "runtime tuning may still be needed on first launch"}
    ok1, err1 = pip_install("paddlepaddle", "paddlepaddle (CPU)")
    ok2, err2 = pip_install("paddleocr", "paddleocr")
    return {
        "status": "installed" if (ok1 and ok2) else "failed",
        "paddlepaddle": ok1,
        "paddleocr": ok2,
        "note": "First launch may need runtime tuning (model download + CPU/threading).",
        "errors": [e for e in (err1, err2) if e],
    }


def install_presidio():
    print("\n[2/5] Microsoft Presidio")
    if pip_have("presidio_analyzer") and pip_have("presidio_anonymizer"):
        print("  OK   already installed")
        return {"status": "already-installed"}
    ok1, err1 = pip_install("presidio-analyzer", "presidio-analyzer")
    ok2, err2 = pip_install("presidio-anonymizer", "presidio-anonymizer")
    return {
        "status": "installed" if (ok1 and ok2) else "failed",
        "analyzer": ok1,
        "anonymizer": ok2,
        "errors": [e for e in (err1, err2) if e],
    }


def install_spacy():
    print("\n[3/5] spaCy + en_core_web_lg")
    have_spacy = pip_have("spacy")
    if not have_spacy:
        ok, err = pip_install("spacy", "spacy")
        if not ok:
            return {"status": "failed", "spacy": False, "error": err}
    # check the lg model
    try:
        import spacy  # noqa: F401
        rc, out = run([sys.executable, "-m", "spacy", "validate"])
        if "en_core_web_lg" in out and "OK" in out:
            print("  OK   en_core_web_lg already present")
            return {"status": "already-installed"}
    except Exception:
        pass
    print("  downloading en_core_web_lg (this is the big model, ~750MB) ...")
    rc, out = run([sys.executable, "-m", "spacy", "download", "en_core_web_lg"])
    ok = rc == 0
    print(f"  {'OK ' if ok else 'FAIL'}  en_core_web_lg")
    return {"status": "installed" if ok else "failed", "model": "en_core_web_lg", "ok": ok, "log_tail": out[-1000:] if not ok else ""}


def install_notebooklm_cli():
    """Pip-install the CLI binary. Browser login is Tier 2 (handled separately)."""
    print("\n[4/5] NotebookLM CLI (binary only, login is later)")
    # The NotebookLM CLI is a Python package; create the dedicated venv used by the firm's setup
    home = os.path.expanduser("~")
    venv_dir = os.path.join(home, ".notebooklm-venv")
    py = os.path.join(venv_dir, "Scripts", "python.exe") if platform.system() == "Windows" else os.path.join(venv_dir, "bin", "python")
    if os.path.exists(py):
        print(f"  OK   venv already at {venv_dir}")
        # ensure the cli is installed inside it
        rc, out = run([py, "-m", "pip", "show", "notebooklm"])
        if rc == 0:
            return {"status": "already-installed", "venv": venv_dir}
    else:
        print(f"  creating venv at {venv_dir} ...")
        rc, out = run([sys.executable, "-m", "venv", venv_dir])
        if rc != 0:
            return {"status": "failed", "step": "venv-create", "error": out[-1000:]}
    print("  installing notebooklm CLI into venv ...")
    rc, out = run([py, "-m", "pip", "install", "--upgrade", "notebooklm"])
    ok = rc == 0
    if not ok:
        # Fallback: the published name may differ. Mark as TODO so the user knows to retry.
        return {
            "status": "failed",
            "venv": venv_dir,
            "note": "pip install notebooklm failed. The CLI may be published under a different package name; check the project repo and retry. Browser login (Tier 2) is separately handled.",
            "error": out[-1500:],
        }
    print("  OK   notebooklm CLI installed (login is Tier 2)")
    return {"status": "installed", "venv": venv_dir, "next": "Tier 2 browser login (see tier-walkthrough.md)"}


def install_ollama():
    print("\n[5/5] Ollama (local LLM runtime)")
    if have("ollama"):
        print("  OK   already installed")
        return {"status": "already-installed"}
    osname = platform.system()
    if osname == "Windows":
        if not have("winget"):
            return {"status": "blocked", "reason": "winget not available on this machine"}
        print("  installing via winget ...")
        rc, out = run("winget install -e --id Ollama.Ollama --accept-source-agreements --accept-package-agreements")
    elif osname == "Darwin":
        if not have("brew"):
            return {"status": "blocked", "reason": "Homebrew not installed. Install brew first, then re-run."}
        print("  installing via brew ...")
        rc, out = run("brew install ollama")
    else:
        return {"status": "blocked", "reason": f"unsupported OS {osname}"}
    ok = rc == 0
    print(f"  {'OK ' if ok else 'FAIL'}  ollama")
    return {"status": "installed" if ok else "failed", "log_tail": out[-1000:] if not ok else ""}


def main():
    print("=== Firm Setup v1.5.0 - Tier 1 auto-install ===")
    print(f"OS: {platform.system()} | Python {platform.python_version()}")
    report = {
        "os": platform.system(),
        "python": platform.python_version(),
        "tier1": {
            "paddleocr": install_paddle(),
            "presidio": install_presidio(),
            "spacy": install_spacy(),
            "notebooklm_cli": install_notebooklm_cli(),
            "ollama": install_ollama(),
        },
    }
    print("\n---SUMMARY---")
    for k, v in report["tier1"].items():
        print(f"  {v.get('status','?'):>20}  {k}")
    print("\n---JSON---")
    print(json.dumps(report, indent=2))
    # exit 0 always; the caller reads JSON to decide what to retry
    return 0


if __name__ == "__main__":
    sys.exit(main())
