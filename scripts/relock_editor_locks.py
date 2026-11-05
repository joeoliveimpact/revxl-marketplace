# relock_editor_locks.py: DEV-ONLY (repo tooling, not shipped). Re-locks the editor-doctor Python locks with uv 0.13.5.
"""Re-lock faster-whisper / parakeet-cpu / parakeet-gpu .lock.txt with one pinned uv and refuse silent drift.

    python -X utf8 -I scripts/relock_editor_locks.py [lock dir] [--uv PATH] [--check] [--accept]
    python -X utf8 -I scripts/relock_editor_locks.py --selftest

lock dir defaults to plugins/editor-superengine/skills/editor-doctor/scripts/python in this repo (the .in files + locks).

Why uv 0.13.5 and not the installer's 0.13.6: uv 0.13.6 (uv PR #22935) evaluates platform_machine as "AMD64" for
x86-64 Windows (--python-platform x86_64-pc-windows-msvc). huggingface-hub 0.36.2's hf-xet marker lists only lowercase
names (x86_64, amd64, arm64, aarch64), so under 0.13.6 the marker is false and hf-xet silently drops out of
parakeet-gpu.lock.txt. 0.13.5 still says "x86_64" and keeps all three lock bodies byte-identical.
The installer's own `uv pip sync` stays on uv 0.13.6: it only installs a finished lock, and the gpu lock has no markers.

This script refuses any uv binary that isn't the pinned 0.13.5 build (sha256 of the release zip and of uv.exe).
Each lock is re-made in a temp dir with the exact flags its own header names, and -o points at a copy of the
COMMITTED lock so uv keeps its pins (a fresh resolve drifts: filelock and nvidia-cudnn-cu12 moved on 11.04.26).
Bodies (everything after the leading # header) are compared package by package:
  dropped or changed package -> exit 1 and nothing is written, unless --accept
  added package              -> reported, allowed (an .in edit)
--check compares only and never writes. A lock whose body is identical is never rewritten: install.py records the
whole-file sha256 of the lock and check_deps.py compares it, so a header-only change would force every install to
re-install. A lock whose body changed is rewritten with its header's "(uv X, MM.DD.YY)" set to this uv and today.
"""
import argparse, datetime, hashlib, os, re, shlex, shutil, subprocess, sys, tempfile, urllib.request, zipfile
from pathlib import Path

UV_VERSION = "0.13.5"
UV_ZIP_URL = f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/uv-x86_64-pc-windows-msvc.zip"
UV_ZIP_SHA256 = "a38b8d1902b7cfbc76b423ba1bb456f623f42064cdc72628b6075b89afd1019a"  # = GitHub's .sha256 file
UV_EXE_SHA256 = "f45d1cb9d9140ca6d3f4005fdfc0ebeccf849fd04d1dc85804155cb923f1597b"  # uv.exe in that zip (= PyPI wheel's)
LOCKS = ("faster-whisper", "parakeet-cpu", "parakeet-gpu")
DEFAULT_LOCKDIR = Path(__file__).resolve().parent.parent / "plugins/editor-superengine/skills/editor-doctor/scripts/python"


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def split_lock(text):
    """-> (header lines, body text). Header = the leading lines starting with '#'."""
    lines = text.splitlines(keepends=True)
    n = 0
    while n < len(lines) and lines[n].startswith("#"):
        n += 1
    return lines[:n], "".join(lines[n:])


def header_args(header, name):
    """The `uv pip compile ...` args from the header, minus the source file (that's appended back as name.in)."""
    joined = " ".join(h.lstrip("#").strip() for h in header)
    m = re.search(r"`uv pip compile ([^`]+)`", joined)
    if not m:
        raise SystemExit(f"{name}.lock.txt: its header doesn't name a `uv pip compile ...` command, so it can't be re-made.")
    args = shlex.split(m.group(1))
    if args[-1] != f"{name}.in":
        raise SystemExit(f"{name}.lock.txt: its header command doesn't end with {name}.in.")
    return args[:-1]


def packages(body):
    """{name: block text}; a block starts at a line with no leading space (name==ver [; marker] \\)."""
    out, cur = {}, None
    for line in body.splitlines(keepends=True):
        if line.strip() and not line[0].isspace():
            cur = re.split(r"[=;\s]", line, maxsplit=1)[0].lower()
            out[cur] = ""
        if cur is None:
            raise SystemExit("lock body starts with an indented line; can't read it.")
        out[cur] += line
    return out


def compare(old_body, new_body):
    old, new = packages(old_body), packages(new_body)
    return (sorted(old.keys() - new.keys()), sorted(k for k in old.keys() & new.keys() if old[k] != new[k]),
            sorted(new.keys() - old.keys()))


def get_uv(tmp, given):
    # ponytail: Windows x64 only, the pin is uv's x86_64-pc-windows-msvc build; add per-platform sha pins if a
    # non-Windows dev ever has to re-lock.
    if sys.platform != "win32":
        raise SystemExit(f"this script only pins uv {UV_VERSION}'s Windows x64 build; run it on Windows. Nothing was changed.")
    if given:
        exe = Path(given)
    else:
        z = tmp / "uv.zip"
        print(f"downloading uv {UV_VERSION} ...")
        with urllib.request.urlopen(UV_ZIP_URL, timeout=60) as resp:
            z.write_bytes(resp.read())
        if sha256(z) != UV_ZIP_SHA256:
            raise SystemExit(f"the uv {UV_VERSION} download doesn't match its pinned sha256; nothing was changed.")
        exe = tmp / "uv.exe"
        exe.write_bytes(zipfile.ZipFile(z).read("uv.exe"))
    if not exe.is_file() or sha256(exe) != UV_EXE_SHA256:
        raise SystemExit(f"{exe} is not the pinned uv {UV_VERSION} (sha256 differs); nothing was changed.")
    return exe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lockdir", nargs="?", default=str(DEFAULT_LOCKDIR))
    ap.add_argument("--uv", help="a uv.exe already on disk (still sha256-checked)")
    ap.add_argument("--check", action="store_true", help="compare only, never write")
    ap.add_argument("--accept", action="store_true", help="write even when a package was dropped or changed")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    src = Path(a.lockdir)
    stamp = datetime.date.today().strftime("%m.%d.%y")
    refused, results = False, []
    with tempfile.TemporaryDirectory(prefix="relock-") as t:
        tmp = Path(t)
        uv = get_uv(tmp, a.uv)
        env = dict(os.environ, UV_NO_CONFIG="1", UV_CACHE_DIR=str(tmp / "cache"))
        for name in LOCKS:
            old_text = (src / f"{name}.lock.txt").read_text(encoding="utf-8")
            header, old_body = split_lock(old_text)
            work = tmp / name
            work.mkdir()
            for f in src.glob("*.in"):
                shutil.copy2(f, work)
            (work / f"{name}.lock.txt").write_text(old_text, encoding="utf-8", newline="\n")
            cmd = [str(uv), "pip", "compile", *header_args(header, name), f"{name}.in", "-o", f"{name}.lock.txt", "-q"]
            r = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=600)
            if r.returncode != 0:
                raise SystemExit(f"{name}: uv pip compile failed (exit {r.returncode}); nothing was changed.\n{r.stderr.strip()}")
            new_head, new_body = split_lock((work / f"{name}.lock.txt").read_text(encoding="utf-8"))
            if new_head:
                raise SystemExit(f"{name}: uv wrote a header despite --no-header; nothing was changed.")
            dropped, changed, added = compare(old_body, new_body)
            bad = bool(dropped or changed)
            refused |= bad and not a.accept
            word = "IDENTICAL" if old_body == new_body else ("REFUSED" if bad and not a.accept else "CHANGED")
            print(f"{name}: {word}" + "".join(f"\n  {k}: {', '.join(v)}" for k, v in
                  (("dropped", dropped), ("changed", changed), ("added", added)) if v))
            new_header = [re.sub(r"\(uv [0-9.]+, \d\d\.\d\d\.\d\d\)", f"(uv {UV_VERSION}, {stamp})", h) for h in header]
            results.append((name, "".join(new_header) + new_body, old_body == new_body))
    if refused:
        print(f"Refused: uv {UV_VERSION} dropped or changed a package (above). Nothing was written. "
              "Re-run with --accept only if that change is wanted.")
        return 1
    if a.check:
        print("check only: nothing was written.")
        return 0
    for name, text, same in results:
        if not same:  # identical bodies keep the committed file (header + whole-file sha) untouched
            (src / f"{name}.lock.txt").write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {name}.lock.txt (uv {UV_VERSION}, {stamp})")
    return 0


def selftest():
    h, b = split_lock("# x `uv pip compile --universal --only-binary :all: a.in` (uv 0.8.3, 11.04.26)\n"
                      "a==1 \\\n    --hash=sha256:aa\nb==2 ; platform_machine == 'amd64' \\\n    --hash=sha256:bb\n")
    assert len(h) == 1 and b.startswith("a==1")
    assert header_args(h, "a") == ["--universal", "--only-binary", ":all:"]
    assert compare(b, b) == ([], [], [])
    assert compare(b, "a==1 \\\n    --hash=sha256:aa\n") == (["b"], [], [])
    assert compare(b, "a==1 \\\n    --hash=sha256:ab\nb==2 ; platform_machine == 'amd64' \\\n    --hash=sha256:bb\n") == ([], ["a"], [])
    assert compare(b, b + "c==3 \\\n    --hash=sha256:cc\n") == ([], [], ["c"])
    assert (DEFAULT_LOCKDIR / "parakeet-gpu.lock.txt").is_file(), DEFAULT_LOCKDIR
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
