#!/usr/bin/env python3
"""clawyer_init.py - write a Clawyer workspace's own files.

The plugin installs OUTSIDE the person's folder, so the files that belong to their case are created here,
in the folder they opened. Claude runs this for them; the person never types it. Standard library only.

  python clawyer_init.py init --state "Ohio" --county "Franklin" --court "Court of Common Pleas" \
                              --matter "Acme unpaid invoice" --case-type business
  python clawyer_init.py add-matter --name "Maple Street lease"
  python clawyer_init.py status
  python clawyer_init.py --selftest

Nothing is ever overwritten. A second run only fills in what is missing. Exit 0 = done, 2 = bad arguments.
"""
import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
TEMPLATES = PLUGIN / "templates"
CASE_TYPES = {  # case type -> packs switched on
    "family-law": ["family-law"],
    "tax": [],
    "business": [],
    "other": [],
}
GITIGNORE = """# Clawyer: your case stays on your computer. Do not remove these lines.
firm.config.json
case-profile.md
matters/
legal-sources/
output/
.clawyer/
handoff.md
CASE-CHECKLIST.md
MASTER-INDEX.md
CASE-FILE-INDEX.md
*.zip
"""


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:60] or "matter"


def workspace(arg) -> Path:
    return Path(arg or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def write_new(path: Path, text: str, log: dict):
    """Create a file only if it is not there. Never overwrite the person's work."""
    if path.exists():
        log["kept"].append(path.name)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    log["created"].append(path.name)


def copy_matter(ws: Path, slug: str, name: str, log: dict) -> Path:
    dest = ws / "matters" / slug
    if dest.exists():
        log["kept"].append(f"matters/{slug}/")
        return dest
    shutil.copytree(TEMPLATES / "matter", dest)
    m = dest / "matter.md"
    m.write_text(m.read_text(encoding="utf-8").replace("# Matter — [TOPIC]", f"# Matter — {name}"), encoding="utf-8")
    log["created"].append(f"matters/{slug}/")
    return dest


def cmd_init(a) -> int:
    ws = workspace(a.workspace)
    ws.mkdir(parents=True, exist_ok=True)
    log = {"workspace": str(ws), "created": [], "kept": []}
    slug = slugify(a.matter)
    home = f"matters/{slug}"
    cfg = {
        "_comment": "Written by Clawyer setup. Names, places and case numbers live here and in case-profile.md, nowhere else.",
        "clawyer_version": "0.1.0",
        "case_type": a.case_type,
        "packs": CASE_TYPES[a.case_type],
        "matter": {"name": a.matter, "cause_no": a.cause_no or "", "final_trial": a.trial_date or "", "issues_reserved": []},
        "paths": {"matter_home": home, "evidence": f"{home}/evidence", "drafts": f"{home}/filings-drafts",
                  "final": f"{home}/filings-final", "legal_sources": "legal-sources"},
        "notebooks": {"_comment": "Optional. Your own NotebookLM notebook id. Leave blank if you do not use one.",
                      "authority_library": "", "overflow": []},
        "jurisdiction": {"state": a.state, "county": a.county, "court": a.court or "",
                         "secondary": a.secondary or ""},
    }
    write_new(ws / "firm.config.json", json.dumps(cfg, indent=2) + "\n", log)
    copy_matter(ws, slug, a.matter, log)
    for d in ("legal-sources", "output", ".clawyer/reports"):
        (ws / d).mkdir(parents=True, exist_ok=True)
    for f in sorted((TEMPLATES / "firm-layer").glob("*.md")):
        write_new(ws / f.name, f.read_text(encoding="utf-8"), log)
    profile = (TEMPLATES / "case-profile-starter.md").read_text(encoding="utf-8")
    for k, v in {"{STATE}": a.state, "{COUNTY}": a.county, "{COURT}": a.court or "[CONFIRM]",
                 "{MATTER}": a.matter, "{CASE_TYPE}": a.case_type, "{CAUSE_NO}": a.cause_no or "[none yet]"}.items():
        profile = profile.replace(k, v)
    write_new(ws / "case-profile.md", profile, log)
    write_new(ws / "CLAUDE.md", (TEMPLATES / "workspace-CLAUDE.md").read_text(encoding="utf-8"), log)
    gi = ws / ".gitignore"
    if gi.exists():
        cur = gi.read_text(encoding="utf-8")
        if "firm.config.json" not in cur:  # add our lines to theirs; never replace their file
            gi.write_text(cur.rstrip("\n") + "\n\n" + GITIGNORE, encoding="utf-8")
            log["created"].append(".gitignore (lines added)")
        else:
            log["kept"].append(".gitignore")
    else:
        write_new(gi, GITIGNORE, log)
    log["matter_home"] = home
    log["packs"] = cfg["packs"]
    print(json.dumps(log, indent=2))
    return 0


def cmd_add_matter(a) -> int:
    ws = workspace(a.workspace)
    if not (ws / "firm.config.json").exists():
        print("NOT SET UP: firm.config.json is missing here. Run the clawyer-setup skill first.")
        return 2
    log = {"workspace": str(ws), "created": [], "kept": []}
    dest = copy_matter(ws, slugify(a.name), a.name, log)
    log["matter_home"] = dest.relative_to(ws).as_posix()
    print(json.dumps(log, indent=2))
    return 0


def cmd_status(a) -> int:
    ws = workspace(a.workspace)
    out = {"workspace": str(ws), "set_up": (ws / "firm.config.json").exists()}
    if out["set_up"]:
        try:
            cfg = json.loads((ws / "firm.config.json").read_text(encoding="utf-8"))
            out.update(case_type=cfg.get("case_type"), packs=cfg.get("packs", []),
                       state=cfg.get("jurisdiction", {}).get("state"),
                       matter_folder_exists=(ws / cfg["paths"]["matter_home"]).is_dir())
        except Exception as e:  # a broken config is reported, never guessed around
            out["error"] = f"firm.config.json could not be read: {e}"
    out["case_profile"] = (ws / "case-profile.md").exists()
    print(json.dumps(out, indent=2))
    return 0


def selftest() -> int:
    """The one runnable check: fails if init stops creating, starts overwriting, or mis-routes a pack."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td) / "ws"
        ns = argparse.Namespace(workspace=str(ws), state="Ohio", county="Franklin", court="Common Pleas",
                                matter="Acme Unpaid Invoice!", case_type="business", cause_no=None,
                                trial_date=None, secondary=None)
        devnull = open(os.devnull, "w")
        old, sys.stdout = sys.stdout, devnull
        try:
            assert cmd_init(ns) == 0
            cfg = json.loads((ws / "firm.config.json").read_text(encoding="utf-8"))
            assert cfg["paths"]["matter_home"] == "matters/acme-unpaid-invoice", cfg["paths"]
            assert cfg["packs"] == [] and cfg["jurisdiction"]["state"] == "Ohio"
            for f in ("case-profile.md", "CLAUDE.md", ".gitignore", "ROUTING.md", "COUNCIL.md",
                      "matters/acme-unpaid-invoice/matter.md", "matters/acme-unpaid-invoice/evidence/README.md"):
                assert (ws / f).exists(), f"missing {f}"
            assert "Ohio" in (ws / "case-profile.md").read_text(encoding="utf-8")
            # second run must not overwrite the person's edits
            (ws / "case-profile.md").write_text("MY EDITS", encoding="utf-8")
            ns.state = "Texas"
            assert cmd_init(ns) == 0
            assert (ws / "case-profile.md").read_text(encoding="utf-8") == "MY EDITS"
            assert json.loads((ws / "firm.config.json").read_text(encoding="utf-8"))["jurisdiction"]["state"] == "Ohio"
            # family law switches the pack on
            ws2 = Path(td) / "fam"
            ns2 = argparse.Namespace(**{**vars(ns), "workspace": str(ws2), "case_type": "family-law"})
            assert cmd_init(ns2) == 0
            assert json.loads((ws2 / "firm.config.json").read_text(encoding="utf-8"))["packs"] == ["family-law"]
            assert cmd_add_matter(argparse.Namespace(workspace=str(ws), name="Maple Street lease")) == 0
            assert (ws / "matters/maple-street-lease/matter.md").exists()
            assert cmd_add_matter(argparse.Namespace(workspace=str(Path(td) / "empty"), name="x")) == 2
        finally:
            sys.stdout = old
            devnull.close()
    print("SELFTEST OK")
    return 0


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()
    ap = argparse.ArgumentParser(description="Write a Clawyer workspace's own files.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--state", required=True)
    i.add_argument("--county", required=True)
    i.add_argument("--court", default="")
    i.add_argument("--matter", required=True)
    i.add_argument("--case-type", required=True, choices=sorted(CASE_TYPES))
    i.add_argument("--cause-no", default="")
    i.add_argument("--trial-date", default="", help="YYYY-MM-DD, only if a date is set")
    i.add_argument("--secondary", default="", help='a second body of law, e.g. "federal" for an IRS matter')
    i.add_argument("--workspace", default="")
    i.set_defaults(fn=cmd_init)
    m = sub.add_parser("add-matter")
    m.add_argument("--name", required=True)
    m.add_argument("--workspace", default="")
    m.set_defaults(fn=cmd_add_matter)
    s = sub.add_parser("status")
    s.add_argument("--workspace", default="")
    s.set_defaults(fn=cmd_status)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
