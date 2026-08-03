#!/usr/bin/env python3
"""
validate.py ... the single source of truth for marketplace validation.

CI (.github/workflows/validate-plugins.yml) calls THIS script, and so should
you, locally, before every push:

    python scripts/validate.py            # run all checks
    python scripts/validate.py --section frontmatter

Because CI and local run the exact same code, a green local run == green CI.
This closes the gap where the SKILL.md YAML-frontmatter check only existed in
CI (inline heredoc) and not locally, so unquoted-colon frontmatter could be
pushed and only fail after the fact.

Checks (mirror the three former CI jobs exactly):
  marketplace   .claude-plugin/marketplace.json is valid JSON + required fields
  plugins       every published plugin folder has the required files/structure
  frontmatter   every published SKILL.md frontmatter parses as YAML + has
                name/description, description >= 30 chars
  readme        root README catalog table lists every published plugin at its
                current version + names the catalog version (main page can't
                silently fall behind releases)

Only plugins listed in marketplace.json are validated (the catalog is the
source of truth; WIP folders under plugins/ are skipped).

Exit code 0 = all good, 1 = at least one error (errors printed, GitHub
::error:: annotations included so CI surfaces them inline).
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MKT = REPO / ".claude-plugin" / "marketplace.json"


def _published() -> set[str]:
    m = json.loads(MKT.read_text(encoding="utf-8"))
    return {Path(p["source"]).name for p in m["plugins"]}


def check_marketplace() -> list[str]:
    errs: list[str] = []
    try:
        m = json.loads(MKT.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"::error file=.claude-plugin/marketplace.json::Invalid JSON: {e}"]
    for f in ("name", "description", "owner", "plugins"):
        if f not in m:
            errs.append(f"::error file=.claude-plugin/marketplace.json::Missing required field: {f}")
    for p in m.get("plugins", []):
        if "name" not in p or "source" not in p:
            errs.append(f"::error::Plugin entry missing name or source: {p}")
    if not errs:
        print(f"OK marketplace.json valid ({len(m.get('plugins', []))} plugins)")
    return errs


def check_plugins() -> list[str]:
    errs: list[str] = []
    published = _published()
    root = REPO / "plugins"
    if not root.exists():
        return ["::error::No plugins/ directory found"]
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name not in published:
            continue
        name = d.name
        for f in (".claude-plugin/plugin.json", "README.md", "CHANGELOG.md", "LICENSE"):
            if not (d / f).exists():
                errs.append(f"::error::{name}: missing {f}")
        pj = d / ".claude-plugin" / "plugin.json"
        if pj.exists():
            try:
                data = json.loads(pj.read_text(encoding="utf-8"))
                for field in ("name", "description", "version"):
                    if field not in data:
                        errs.append(f"::error::{name}: plugin.json missing {field}")
            except Exception as e:
                errs.append(f"::error::{name}: plugin.json invalid: {e}")
        has_skill = (d / "skills").exists() and any((d / "skills").rglob("SKILL.md"))
        has_agent = (d / "agents").exists() and any((d / "agents").glob("*.md"))
        if not (has_skill or has_agent):
            errs.append(f"::error::{name}: no skills or agents found")
        else:
            print(f"OK {name}: structure"
                  f"{' +skills' if has_skill else ''}{' +agents' if has_agent else ''}")
    return errs


def check_frontmatter() -> list[str]:
    import yaml  # pyyaml; CI installs it, locally: pip install pyyaml
    errs: list[str] = []
    for name in sorted(_published()):
        for sk in (REPO / "plugins" / name).rglob("SKILL.md"):
            rel = sk.relative_to(REPO)
            try:
                content = sk.read_text(encoding="utf-8")
                if not content.startswith("---"):
                    errs.append(f"::error::{rel}: no frontmatter")
                    continue
                end = content.find("---", 3)
                if end == -1:
                    errs.append(f"::error::{rel}: malformed frontmatter")
                    continue
                fm = yaml.safe_load(content[3:end])
                if not isinstance(fm, dict):
                    errs.append(f"::error::{rel}: frontmatter is not a mapping")
                    continue
                if "name" not in fm:
                    errs.append(f"::error::{rel}: frontmatter missing name")
                if "description" not in fm:
                    errs.append(f"::error::{rel}: frontmatter missing description")
                if fm.get("description") and len(fm["description"]) < 30:
                    errs.append(f"::error::{rel}: description too short (<30 chars)")
            except Exception as e:
                errs.append(f"::error::{rel}: parse error: {e}")
    if not errs:
        print("OK all published SKILL.md frontmatter parses")
    return errs


def check_readme() -> list[str]:
    """Root README must stay in lockstep with the catalog.

    Guards the failure mode where a release bumps marketplace.json but the
    main page keeps advertising stale plugins/versions (found 08.02.26: README
    listed 2 of 16 plugins, one under a dead name). Every published plugin
    must appear in README.md's catalog table with its current version, and
    the catalog version itself must be named.
    """
    errs: list[str] = []
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    m = json.loads(MKT.read_text(encoding="utf-8"))
    cat_ver = m.get("metadata", {}).get("version") or m.get("version")
    if cat_ver and f"`{cat_ver}`" not in readme:
        errs.append(f"::error file=README.md::catalog version {cat_ver} not named in README (update 'catalog `x.y.z`' line)")
    for p in m.get("plugins", []):
        name, ver = p["name"], p.get("version")
        line = next((ln for ln in readme.splitlines() if f"plugins/{name}/" in ln), None)
        if line is None:
            errs.append(f"::error file=README.md::published plugin '{name}' missing from README catalog table")
        elif ver and f"| {ver} |" not in line:
            errs.append(f"::error file=README.md::'{name}' README row version != catalog ({ver})")
    if not errs:
        print(f"OK README catalog table matches marketplace.json ({len(m.get('plugins', []))} plugins, catalog {cat_ver})")
    return errs


SECTIONS = {
    "marketplace": check_marketplace,
    "plugins": check_plugins,
    "frontmatter": check_frontmatter,
    "readme": check_readme,
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Marketplace validation (CI == local).")
    ap.add_argument("--section", choices=[*SECTIONS, "all"], default="all")
    args = ap.parse_args()
    todo = SECTIONS if args.section == "all" else {args.section: SECTIONS[args.section]}
    all_errs: list[str] = []
    for name, fn in todo.items():
        print(f"== {name} ==")
        all_errs += fn()
    if all_errs:
        print("\n-- ERRORS --")
        for e in all_errs:
            print(e)
        return 1
    print("\nAll validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
