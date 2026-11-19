#!/usr/bin/env python3
"""SessionStart hook: load the matter into context when this folder is a Clawyer workspace.

Silent in every other folder (the plugin is installed for the whole app, the case lives in one folder).
Any error is swallowed and it exits 0, so it can never break a session.
Based on pro-se-firm v1.7.0's session_start_loader.py (c) 2026 Mic H., MIT; reworked to run from a plugin.
"""
import datetime
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WS = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
PLUGIN = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent)


def main():
    cfg_path = WS / "firm.config.json"
    if not cfg_path.exists():
        return  # not a Clawyer folder: say nothing
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        print("CLAWYER: firm.config.json is here but cannot be read. Run the clawyer-setup skill to repair it.")
        return
    m = cfg.get("matter", {})
    j = cfg.get("jurisdiction", {})
    home = cfg.get("paths", {}).get("matter_home", "")
    packs = cfg.get("packs", []) or []
    out = [f"=== CLAWYER - {m.get('name', '(unnamed matter)')} ==="]
    where = ", ".join(x for x in (j.get("court"), f"{j.get('county')} County" if j.get("county") else "", j.get("state")) if x)
    out.append(f"Kind of case: {cfg.get('case_type', 'other')}. Where: {where or '[CONFIRM]'}. Matter folder: {home}")
    if j.get("secondary"):
        out.append(f"Second body of law: {j['secondary']}.")
    try:
        td = datetime.date.fromisoformat(m.get("final_trial", "")[:10])
        out.append(f"Hearing or trial date {td.isoformat()}: {(td - datetime.date.today()).days} days out.")
    except Exception:
        pass
    state = (j.get("state") or "").strip().lower()
    if state not in ("mississippi", "ms"):
        out.append(
            f"STATE RULE: this matter is in {j.get('state') or 'an unconfirmed state'}. Clawyer's built-in doctrine was "
            "written for Mississippi family court. Treat every rule number, case name, deadline, fee and form in the "
            "reference files as an example of what to look up. Cite nothing until that state's own version is found "
            "in an official source; tag the rest CONFIRM-BEFORE-CITING.")
    if "family-law" in packs:
        out.append(f"PACK ON: family-law. Its references are in {PLUGIN / 'packs' / 'family-law' / 'references'}; "
                   "the custody-premortem skill is the gate before anything goes out.")
    else:
        out.append("No pack is on. Family-law rows in the routing tables do not apply to this matter; "
                   "the legal-premortem skill is the gate before anything goes out.")
    # refresh the case index (quick, incremental); a missing dependency just skips it
    brain = PLUGIN / "skills" / "pro-se-firm" / "scripts" / "refresh_brain.py"
    if brain.exists() and home and (WS / home).is_dir():
        try:
            subprocess.run([sys.executable, str(brain)], cwd=str(WS), capture_output=True, text=True, timeout=40,
                           env={**os.environ, "CLAUDE_PROJECT_DIR": str(WS)})
            db = WS / home / "00_ADMIN" / "case-index" / "case.db"
            con = sqlite3.connect(db)
            n = con.execute("SELECT v FROM meta WHERE k='docs'").fetchone()
            con.close()
            if n:
                out.append(f"CASE INDEX: {n[0]} documents indexed. Search the whole case before asking the person: "
                           f"python \"{PLUGIN / 'skills' / 'pro-se-firm' / 'scripts' / 'ask_case.py'}\" \"<question>\"")
        except Exception:
            pass
    for name, header in (("handoff.md", "## P0"), ("CASE-CHECKLIST.md", "Open This Session")):
        try:
            txt = (WS / name).read_text(encoding="utf-8", errors="ignore")
            i = txt.find(header)
            if i >= 0:
                out.append("")
                out.extend(l for l in txt[i:i + 1200].splitlines()[:10] if l.strip())
        except Exception:
            pass
    out.append("")
    out.append("Facts come only from case-profile.md and the matter folder. Use the clawyer-superengine:pro-se-firm skill for case "
               "work. The person never types a command: run every script yourself.")
    print("\n".join(out))


try:
    main()
except Exception:
    if os.environ.get("HOOK_DEBUG"):
        import traceback
        traceback.print_exc()
sys.exit(0)
