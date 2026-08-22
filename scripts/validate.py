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
  plugin_integrity
                mechanical per-plugin checks: ${CLAUDE_PLUGIN_ROOT} paths
                resolve, reference docs aren't orphaned, no bare sibling
                slash-commands in prose, advertised commands exist, no
                absolute machine paths, hooks wired to real scripts, and
                skills/references stay under their word ceilings

Only plugins listed in marketplace.json are validated (the catalog is the
source of truth; WIP folders under plugins/ are skipped).

Exit code 0 = all good, 1 = at least one error (errors printed, GitHub
::error:: annotations included so CI surfaces them inline).
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MKT = REPO / ".claude-plugin" / "marketplace.json"

# --- plugin_integrity ------------------------------------------------------

# Per-check severity. "error" fails the build; "warning" annotates only.
# sibling_slash and word_ceiling start as warnings: they surface 50+ real but
# pre-existing defects across seven plugins, and turning every release PR red
# on legacy debt is worse than tracking it. Promoting one to a hard gate once
# its backlog is cleared is a one-word flip here.
SEVERITY = {
    "dead_ref": "error",
    "orphan_ref": "warning",
    "sibling_slash": "warning",
    "advertised_cmd": "error",
    "abs_path": "error",
    "hooks": "error",
    "word_ceiling": "warning",
}

# Slash-commands a plugin may advertise without shipping commands/<name>.md:
# Claude Code built-ins that plugin docs legitimately reference.
EXTERNALLY_PROVIDED_COMMANDS = {
    "goal", "loop", "schedule", "clear", "resume", "continue",
    "model", "permissions", "help", "verify", "mcp",
}

# Dirs whose *.md count as shipped plugin prose (excludes README/CHANGELOG,
# where a "${CLAUDE_PLUGIN_ROOT}/references/..." ellipsis is prose, not a path).
DOC_DIRS = ("skills", "references", "agents", "commands")

# House standard is 1500-2000 words; ceilings carry headroom so only real
# bloat trips them.
SKILL_WORD_CEILING = 2200
REFERENCE_WORD_CEILING = 1800

# Absolute machine paths that must never ship. Bare "C:\" is deliberately NOT
# listed: it matches legitimate docs (the standard Windows Edge install path,
# a doubled-backslash "C:\\Users\\...\\server.js" placeholder). "C:\Users" is
# the actual leaked-home-directory signature.
ABS_PATH_PATTERNS = ("C:\\Users", "C:/Users", "/Users/", "/home/")

RX_PLUGIN_ROOT = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s`\"'\)\]\},;:*]+)")
RX_HOOK_SCRIPT = re.compile(r"[^\s\"']*\.(?:py|sh|js|mjs|cjs|ps1)")

# Advertised slash-commands. Deliberately narrow -- backticked `/name`, bold
# **/name**, or a "- /name" bullet -- so file paths and URL fragments can't
# masquerade as command references.
RX_CMD_TICK = re.compile(r"`/([a-z][a-z0-9-]*[a-z0-9])`")
RX_CMD_BOLD = re.compile(r"\*\*/([a-z][a-z0-9-]*[a-z0-9])\*\*")
RX_CMD_BULLET = re.compile(r"^\s*[-*]\s+/([a-z][a-z0-9-]*[a-z0-9])(?![\w-])", re.M)


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


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _body_after_frontmatter(text: str) -> str:
    """Everything after the closing --- of YAML frontmatter (or all of it).

    A skill naming its own triggers in frontmatter is legitimate; the same
    string in prose is a bare slash-command.
    """
    if not text.startswith("---"):
        return text
    end = text.find("---", 3)
    return text[end + 3:] if end != -1 else text


def _doc_mds(plugin: Path):
    for sub in DOC_DIRS:
        d = plugin / sub
        if d.exists():
            yield from sorted(d.rglob("*.md"))


def check_plugin_integrity() -> list[str]:
    """Mechanical integrity of every published plugin.

    Catches the defect classes a human reviewer misses on a release PR: dead
    ${CLAUDE_PLUGIN_ROOT} paths, reference docs nothing links to, bare sibling
    slash-commands in prose, advertised commands that resolve nowhere, leaked
    absolute machine paths, broken hook wiring, and word-count bloat.

    Severity per check comes from SEVERITY; warnings print but never fail.
    """
    errs: list[str] = []

    def emit(key: str, rel: str, msg: str) -> None:
        if SEVERITY[key] == "error":
            errs.append(f"::error file={rel}::{msg}")
        else:
            print(f"::warning file={rel}::{msg}")

    for name in sorted(_published()):
        d = REPO / "plugins" / name
        if not d.is_dir():
            continue
        pre = len(errs)

        # 1. every ${CLAUDE_PLUGIN_ROOT}/<relpath> must resolve
        for md in _doc_mds(d):
            for m in RX_PLUGIN_ROOT.finditer(_read(md)):
                rel = m.group(1)
                if not (d / rel).exists():
                    emit("dead_ref", f"plugins/{name}/{md.relative_to(d).as_posix()}",
                         f"dead reference path ${{CLAUDE_PLUGIN_ROOT}}/{rel}")

        # 2. reference docs nothing else in the plugin points at
        refdir = d / "references"
        if refdir.exists():
            others = list(d.rglob("*.md"))
            for rf in sorted(refdir.glob("*.md")):
                rel = rf.relative_to(d).as_posix()
                incoming = sum(1 for o in others
                               if o.resolve() != rf.resolve() and rel in _read(o))
                if incoming == 0:
                    emit("orphan_ref", f"plugins/{name}/{rel}",
                         "orphan reference doc (0 incoming references)")

        # 3. bare sibling slash-commands in body text
        skill_dirs = {p.parent.name for p in d.glob("skills/*/SKILL.md")}
        targets = list(d.glob("skills/*/SKILL.md"))
        if refdir.exists():
            targets += sorted(refdir.glob("*.md"))
        for f in targets:
            own = f.parent.name if f.name == "SKILL.md" else None
            body = _body_after_frontmatter(_read(f))
            for sk in sorted(skill_dirs):
                if sk == own:
                    continue
                # not preceded by word char / . / / / \ / - so that relative
                # paths like ../sibling/SKILL.md don't read as commands
                rx = re.compile(r"(?<![\w./\\-])/" + re.escape(sk) + r"(?![\w-])")
                if rx.search(body):
                    emit("sibling_slash",
                         f"plugins/{name}/{f.relative_to(d).as_posix()}",
                         f"bare sibling slash-command /{sk} in body text")

        # 4. advertised slash-commands must resolve to something shipped
        advertised: set[str] = set()
        rm = d / "README.md"
        sources = [_read(rm)] if rm.exists() else []
        pj = d / ".claude-plugin" / "plugin.json"
        if pj.exists():
            try:
                sources.append(json.loads(_read(pj)).get("description", "") or "")
            except Exception:
                pass  # plugin.json validity is check_plugins()' job
        for text in sources:
            for rx in (RX_CMD_TICK, RX_CMD_BOLD, RX_CMD_BULLET):
                advertised |= set(rx.findall(text))
        for cmd in sorted(advertised):
            if cmd in EXTERNALLY_PROVIDED_COMMANDS:
                continue
            # skills surface as slash-invocables; commands/ routers are optional
            if (d / "commands" / f"{cmd}.md").exists():
                continue
            if (d / "skills" / cmd / "SKILL.md").exists():
                continue
            emit("advertised_cmd", f"plugins/{name}/README.md",
                 f"advertised command /{cmd} has no commands/{cmd}.md "
                 f"or skills/{cmd}/SKILL.md")

        # 5. no absolute machine paths in shipped files
        for f in sorted(list(d.rglob("*.md")) + list(d.rglob("*.json"))):
            if f.name == "CHANGELOG.md":  # may quote history
                continue
            text = _read(f)
            for pat in ABS_PATH_PATTERNS:
                if pat in text:
                    emit("abs_path", f"plugins/{name}/{f.relative_to(d).as_posix()}",
                         f"absolute machine path ({pat}) in shipped file")
                    break

        # 6. hooks.json parses and every script it names exists
        hj = d / "hooks" / "hooks.json"
        if hj.exists():
            try:
                data = json.loads(_read(hj))
            except Exception as e:
                emit("hooks", f"plugins/{name}/hooks/hooks.json", f"invalid JSON: {e}")
            else:
                for m in RX_HOOK_SCRIPT.finditer(json.dumps(data)):
                    rel = (m.group(0)
                           .replace("${CLAUDE_PLUGIN_ROOT}/", "")
                           .replace("\\\\", "/")
                           .replace("\\", "/")
                           .lstrip("/"))
                    if not (d / rel).exists():
                        emit("hooks", f"plugins/{name}/hooks/hooks.json",
                             f"hook script not found: {rel}")

        # 7. word ceilings
        for sk in sorted(d.glob("skills/*/SKILL.md")):
            w = len(_read(sk).split())
            if w > SKILL_WORD_CEILING:
                emit("word_ceiling", f"plugins/{name}/{sk.relative_to(d).as_posix()}",
                     f"SKILL.md is {w} words (ceiling {SKILL_WORD_CEILING})")
        if refdir.exists():
            for rf in sorted(refdir.glob("*.md")):
                w = len(_read(rf).split())
                if w > REFERENCE_WORD_CEILING:
                    emit("word_ceiling", f"plugins/{name}/{rf.relative_to(d).as_posix()}",
                         f"reference is {w} words (ceiling {REFERENCE_WORD_CEILING})")

        if len(errs) == pre:
            print(f"OK {name}: integrity")
    return errs


SECTIONS = {
    "marketplace": check_marketplace,
    "plugins": check_plugins,
    "frontmatter": check_frontmatter,
    "readme": check_readme,
    "plugin_integrity": check_plugin_integrity,
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
