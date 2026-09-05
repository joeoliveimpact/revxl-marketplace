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
                absolute machine paths, hooks wired to real scripts,
                skills/references stay under their word ceilings, and no
                SKILL.md exceeds the token ceiling

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
    "token_ceiling": "error",
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

# Hard ceiling, unlike the word ceilings above. 5000 tokens is the documented
# per-skill cap for re-injecting skill bodies after context compaction: a
# SKILL.md over it is silently truncated mid-session, keeping only its start,
# so the back half of the skill stops existing with no error anywhere.
# Tokens are ESTIMATED as bytes/4 ... this is a cheap approximation, not an
# exact tokenizer count, and the failure message says so so the number stays
# auditable from the file alone.
SKILL_TOKEN_CEILING = 5000
SKILL_TOKEN_ESTIMATE_NOTE = "estimated as bytes/4, not an exact tokenizer count"

# Skills knowingly over SKILL_TOKEN_CEILING, keyed "<plugin>/<skill>" with the
# reason it is recorded rather than fixed. A waiver is a tracked exception, not
# an exemption from the problem: anything over the ceiling and NOT listed here
# fails the build.
TOKEN_CEILING_WAIVERS = {
    # Baseline recorded 2026-09-01 when this gate was introduced. Every entry below
    # was ALREADY over the ceiling before the gate existed, so blocking on them would
    # stop unrelated work in six other plugins rather than catching new bloat. They
    # are tracked in Linear, not buried here ... see SKLLPLG-255.
    #
    # A waiver is a recorded exception with an owner, never a silent pass. Do not add
    # to this list to get a red run green; trim the skill instead.
    "workspace-superengine/session-closeout":
        "11445 est; was 11256 before 0.13.0 added its compaction guard. Reordering "
        "was tried and measurably moved zero sections above the cut, so it was "
        "reverted; the guard is the fix. Trim to <5000 tracked in SKLLPLG-245",
    "workspace-superengine/session-continue":
        "7013 est; was 6860 before the compaction guard. Same measured result as "
        "closeout ... reorder reverted. Trim to <5000 tracked in SKLLPLG-245",
    "workspace-superengine/session-start":
        "6860 est; was 6164 before 0.13.0's read guard and compaction guard. "
        "Already over at HEAD. Trim to <5000 tracked in SKLLPLG-245",
    "socialcrawl-superengine/socialcrawl":
        "8590 est; pre-existing 2026-09-01 baseline, untriaged. SKLLPLG-255",
    "profile-optimization-superengine/profile-ig-audit":
        "7753 est; pre-existing 2026-09-01 baseline, untriaged. SKLLPLG-255",
    "shortform-superengine/reel-scripter":
        "7159 est; pre-existing 2026-09-01 baseline, untriaged. SKLLPLG-255",
    "profile-optimization-superengine/profile-fb-audit":
        "7000 est; pre-existing 2026-09-01 baseline, untriaged. SKLLPLG-255",
    "shortform-superengine/competitor-cross-reference":
        "6227 est; pre-existing 2026-09-01 baseline, untriaged. SKLLPLG-255",
    "focus-group-superengine/focus-group-run":
        "5735 est; pre-existing 2026-09-01 baseline, untriaged. SKLLPLG-255",
    "shortform-superengine/onboarding":
        "5425 est; pre-existing 2026-09-01 baseline, untriaged. SKLLPLG-255",
}

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


def check_version_parity() -> list[str]:
    """Every catalogue entry's version must equal its plugin.json version.

    Guards the failure mode found 09.04.26: three of sixteen plugins had a
    catalogue version that did not match plugin.json (shortform 0.3.1/0.3.2,
    course-crawler 0.5.0/0.7.0, lead-magnet 0.1.0/0.1.1). The bump is manual
    in two files (docs/plugin-conventions.md) and nothing enforced it, so
    fixes committed here sat in the repo and never reached an installed
    client. Runs inside the `plugins` section so CI needs no workflow change.
    Missing or invalid plugin.json is check_plugins() job and is skipped here.
    """
    errs: list[str] = []
    m = json.loads(MKT.read_text(encoding="utf-8"))
    n = 0
    for p in m.get("plugins", []):
        name, cat_ver = p.get("name"), p.get("version")
        pj = REPO / p["source"] / ".claude-plugin" / "plugin.json"
        if not pj.exists():
            continue
        try:
            man_ver = json.loads(pj.read_text(encoding="utf-8")).get("version")
        except Exception:
            continue
        if cat_ver != man_ver:
            rel = pj.relative_to(REPO).as_posix()
            errs.append(f"::error file={rel}::{name}: plugin.json version {man_ver} "
                        f"!= marketplace.json {cat_ver} (bump BOTH; docs/plugin-conventions.md)")
        else:
            n += 1
    if not errs:
        print(f"OK version parity: {n} plugin.json == marketplace.json")
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
    errs.extend(check_version_parity())
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
                # Trailing dots and ellipses are prose, not path. House style uses
                # "..." for a pause, so a reference cited mid-sentence captures as
                # "references/mine.md..." here, and a changelog placeholder can
                # capture as "references/" plus a lone U+2026. Windows silently
                # STRIPS trailing dots when resolving a path, so 37 of these
                # resolved fine locally and the check only failed once this section
                # started running on Linux in CI. A real filename never ends in a
                # dot or an ellipsis, so stripping both is safe.
                rel = m.group(1).rstrip(".\u2026")
                if not rel or rel.endswith("/"):
                    continue
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

        # 8. token ceiling (hard gate, unlike 7): a SKILL.md over the
        #    compaction re-injection cap is silently truncated mid-session.
        for sk in sorted(d.glob("skills/*/SKILL.md")):
            est = len(sk.read_bytes()) // 4
            if est <= SKILL_TOKEN_CEILING:
                continue
            if f"{name}/{sk.parent.name}" in TOKEN_CEILING_WAIVERS:
                continue
            emit("token_ceiling", f"plugins/{name}/{sk.relative_to(d).as_posix()}",
                 f"SKILL.md is ~{est} tokens ({SKILL_TOKEN_ESTIMATE_NOTE}), over "
                 f"the {SKILL_TOKEN_CEILING}-token ceiling ... it will be silently "
                 f"truncated when skill bodies are re-injected after compaction. "
                 f"Trim it, or record it in TOKEN_CEILING_WAIVERS with a reason.")

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
