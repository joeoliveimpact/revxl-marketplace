#!/usr/bin/env python3
"""clawyer_smoke.py - run clawyer-superengine's setup path on a real Mac or Windows machine.

Why: 0.1.0 and 0.1.1 shipped with the Mac path never run on a Mac, the Tesseract install never run on
Windows, and the hooks only tried by hand. This runs what setup runs, in the order setup runs it, and
fails if a step a client depends on fails.

  python .github/scripts/clawyer_smoke.py               # everything, including real installs (CI)
  python .github/scripts/clawyer_smoke.py --no-install  # skip `deps.py install` (safe on your own PC)

REQUIRED checks fail the job. INFO checks are printed and never fail it: they depend on the network or on
which `bash` a machine happens to find, and are there to be read.

What a hosted runner cannot prove (say so in any release note that leans on this):
  - the runner account is an administrator, so "no admin password" is NOT tested here
  - Git is already installed on every runner, so deps.py's Git install is NOT exercised
  - hooks are run the way hooks.json writes them, but not inside the Claude desktop app
"""
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugins" / "clawyer-superengine"
WIN = platform.system() == "Windows"
RESULTS = []  # (required, ok, name, detail)


def run(cmd, cwd=None, stdin="", env=None, timeout=900):
    try:
        r = subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env={**os.environ, **(env or {})})
        return r.returncode, r.stdout or "", r.stderr or ""
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, "", f"{type(e).__name__}: {e}"


def record(name, ok, detail="", required=True):
    RESULTS.append((required, bool(ok), name, detail.strip()[-600:]))
    print(f"{'PASS' if ok else ('FAIL' if required else 'INFO-FAIL')}  {name}\n      {detail.strip()[-600:]}", flush=True)


def tail(out, err):
    return (out.strip()[-300:] + " | " + err.strip()[-300:]).strip(" |")


def main():
    install = "--no-install" not in sys.argv[1:]
    sys_py = sys.executable

    # 1. every script's own offline self-test
    for rel in ("scripts/clawyer_init.py", "scripts/deps.py", "scripts/report_to_joe.py",
                "skills/pro-se-firm/scripts/cite_lookup.py"):
        code, out, err = run([sys_py, str(PLUGIN / rel), "--selftest"])
        record(f"selftest {rel}", code == 0, tail(out, err))
    code, out, err = run([sys_py, "scripts/leak_check.py"], cwd=PLUGIN)
    record("leak_check.py finds nothing", code == 0, tail(out, err))

    case = Path(tempfile.mkdtemp(prefix="clawyer-case-"))
    empty = Path(tempfile.mkdtemp(prefix="clawyer-empty-"))

    # 2. find Python, launched exactly as clawyer-setup launches it
    if WIN:
        cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
               str(PLUGIN / "scripts" / "find-python.ps1")]
    else:
        cmd = ["sh", str(PLUGIN / "scripts" / "find-python.sh")]
    code, out, err = run(cmd, cwd=case)
    marker = case / ".clawyer" / ".python"
    py = marker.read_text(encoding="utf-8-sig").strip() if marker.exists() else ""
    record("find-python writes .clawyer/.python", code == 0 and bool(py), tail(out, err))
    c2, o2, e2 = run([py, "-c", "import sys; print(sys.version)"]) if py else (-1, "", "no interpreter recorded")
    record("the recorded Python runs", c2 == 0, tail(o2, e2))
    if c2 != 0:
        py = sys_py  # keep going so the rest of the path is still exercised

    # 3. dependencies: check, install, check again
    code, out, err = run([py, str(PLUGIN / "scripts" / "deps.py"), "check"])
    record("deps.py check prints its report", code == 0 and '"items"' in out, tail(out, err))
    if install:
        code, out, err = run([py, str(PLUGIN / "scripts" / "deps.py"), "install"], timeout=1800)
        try:
            rep = json.loads(out)
        except ValueError:
            rep = {}
        states = {i["name"]: i["status"] for i in rep.get("items", [])}
        record("deps.py install leaves everything ready", code == 0 and rep.get("ready") is True,
               json.dumps(states) + " " + json.dumps([i for i in rep.get("items", []) if i["status"] not in ("ok", "installed")])
               + " " + err[-200:])
        record("tesseract was installed by deps.py (not already there)", states.get("tesseract") == "installed",
               f"tesseract status: {states.get('tesseract')}", required=False)

    # 4. write a case folder, one per kind of case that switches packs differently
    for kind, ws in (("business", case), ("family-law", Path(tempfile.mkdtemp(prefix="clawyer-family-")))):
        code, out, err = run([py, str(PLUGIN / "scripts" / "clawyer_init.py"), "init", "--state", "Texas",
                              "--county", "Travis", "--matter", "Smoke Test Matter", "--case-type", kind,
                              "--workspace", str(ws)])
        record(f"clawyer_init init ({kind})", code == 0 and (ws / "firm.config.json").exists(), tail(out, err))
        code, out, err = run([py, str(PLUGIN / "scripts" / "clawyer_init.py"), "status", "--workspace", str(ws)])
        record(f"clawyer_init status ({kind})", code == 0, tail(out, err))

    # 5. hooks, with the command lines hooks.json ships
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    root = PLUGIN.as_posix()
    profile = (case / "case-profile.md").as_posix()
    stdin_for = {"SessionStart": "{}", "UserPromptSubmit": json.dumps({"prompt": "I got served"}),
                 "PostToolUse": json.dumps({"tool_name": "Edit", "tool_input": {"file_path": profile}})}
    git_bash = shutil.which("bash")
    if WIN:  # the Git for Windows bash, which is what deps.py installs Git to provide
        for cand in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
            if os.path.exists(cand):
                git_bash = cand
                break
    record("a bash exists for hooks to run under", bool(git_bash), f"bash: {git_bash}")
    for event, groups in hooks.items():
        line = groups[0]["hooks"][0]["command"].replace("${CLAUDE_PLUGIN_ROOT}", root)
        for label, ws, want_output in (("case folder", case, event != "PostToolUse" or None), ("other folder", empty, False)):
            env = {"CLAUDE_PLUGIN_ROOT": root, "CLAUDE_PROJECT_DIR": str(ws)}
            code, out, err = run([git_bash, "-c", line], cwd=ws, stdin=stdin_for[event], env=env, timeout=120) \
                if git_bash else (-1, "", "no bash")
            ok = code == 0 and (want_output is None or bool(out.strip()) == want_output)
            record(f"hook {event} in {label}: exit 0, {'speaks' if want_output else 'silent' if want_output is False else 'any output'}",
                   ok, f"exit {code}; {len(out)} chars out; {tail(out[:200], err)}")
        if WIN:  # what happens when the hook line is launched from Windows itself, where `bash` may be WSL's
            code, out, err = run(["powershell.exe", "-NoProfile", "-Command", line.replace('"', "'")],
                                 cwd=case, stdin=stdin_for[event],
                                 env={"CLAUDE_PLUGIN_ROOT": root, "CLAUDE_PROJECT_DIR": str(case)}, timeout=120)
            record(f"hook {event} launched from PowerShell (which bash does Windows find?)", code == 0,
                   f"exit {code}; where bash: {shutil.which('bash')}; {tail(out[:200], err)}", required=False)

    # 6. the citation checker against the live public database (network: INFO only)
    cite = str(PLUGIN / "skills" / "pro-se-firm" / "scripts" / "cite_lookup.py")
    code, out, err = run([py, cite, "--text", "Miranda v. Arizona, 384 U.S. 436 (1966)"], timeout=120)
    record("cite_lookup confirms a real case", code == 0, tail(out, err), required=False)
    code, out, err = run([py, cite, "--text", "Smith v. Jones, 999 U.S. 999 (2099)"], timeout=120)
    record("cite_lookup rejects a made-up case", code == 1, tail(out, err), required=False)

    failed = [r for r in RESULTS if r[0] and not r[1]]
    rows = "\n".join(f"| {'required' if req else 'info'} | {'pass' if ok else 'FAIL'} | {name} | {detail[:200].replace('|', '/').replace(chr(10), ' ')} |"
                     for req, ok, name, detail in RESULTS)
    summary = (f"## Clawyer smoke test: {platform.system()} {platform.release()}\n\n"
               f"{len(RESULTS) - len([r for r in RESULTS if not r[1]])} of {len(RESULTS)} passed, "
               f"{len(failed)} required failure(s).\n\n| kind | result | check | detail |\n|---|---|---|---|\n{rows}\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(summary)
    print(f"\n{len(failed)} required failure(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.exit(main())
