#!/usr/bin/env python3
"""check_routing.py ... the no-dead-end gate for shortform-superengine.

Run it directly, from any working directory:

    python3 plugins/shortform-superengine/scripts/check_routing.py

It is also `scripts/validate.py`'s `routing` section, which imports `collect()`
below, so `python3 scripts/validate.py --section routing` runs this exact code.
CI and local can never drift.

ERRORS (exit 1, printed as GitHub ::error annotations):

  1. placement   every Next-moves block header starts before byte 20,000, and
                 every SKILL.md over 12,000 bytes starts its `## Terminal paths`
                 heading inside the top third. A block below the compaction cut
                 stops existing mid-session, which is how a skill loses its
                 routing without any error anywhere.
  2. structure   every skills/*/SKILL.md carries `## Prereq (E0)` and
                 `## Terminal paths`, and no block header sits outside that
                 section (the section ends at the next `## ` heading).
  3. registry    every block cites a ledger id (E0b, E<n>, F<n>) in its header
                 line or on the first non-blank line under it; every cited id
                 has a row in journey-map.md; every happy-path and failure row
                 names a skill that exists.
  4. endpoints   every anchored SocialCrawl path this plugin names in a .md or
                 .py file has a row in socialcrawl-endpoints.md, and no row
                 names the retired search/reels alias (unbackticked here on
                 purpose: this file is scanned by its own rule).
  5. catalog     the marketplace entry's description starts with `v<version> `
                 for the version that same entry declares.
  6. counts      both READMEs' skill counts equal the number of skills shipped.

WARNINGS (annotate, never fail): a `Say: "<phrase>"` whose phrase resolves to no
SKILL.md frontmatter and no journey-map roster row. A line carrying
"(if installed)" is exempt, because its target ships in a later release.

Two measurement decisions, stated because the verdict depends on them:

  * Byte offsets are computed on the file's bytes with CRLF normalised to LF.
    The working tree is CRLF and the CI checkout is LF, and a gate that gave two
    different answers on the same content would be worse than no gate.
  * Fenced code blocks (``` fences) are skipped when finding headers, phrases
    and endpoint paths. shortform-next ships three worked example renders that
    contain real block headers; they are illustrations, not routing.

Stdlib only, Python 3.9+.
"""

import json
import re
import sys
from pathlib import Path

# Allow-list. This gate encodes ONE plugin's routing contract; it is not a
# house-wide rule and must never quietly start judging its neighbours.
PLUGINS = {"shortform-superengine"}

REPO = Path(__file__).resolve().parents[3]

BLOCK_CUT = 20000          # the compaction re-injection cut, in bytes
TOP_THIRD_FROM = 12000     # files smaller than this only owe the 20,000 rule
EXPECTED_SKILLS = None     # counted from disk, never hardcoded
RETIRED_ALIAS = "search/reels"

# Block header grammar (routing.md "Grammar the scanner accepts"):
#   **Next moves**
#   **Next moves ... empty week**
#   **Next moves ... plan written (E21)**
#   **Next moves (after a roster op)**
RX_HEADER = re.compile(r"^\*\*Next moves(?:\s*(?:\.\.\.|[(:])[^*\n]*)?\*\*")
RX_ID = re.compile(r"\b(E0b|E[0-9]+|F[0-9]+)\b")
RX_ROW_ID = re.compile(r"^\|\s*`?(E0b|E[0-9]+|F[0-9]+)`?\s*\|")

# Endpoint paths are matched ONLY when anchored, so prose like "search/Content"
# or a skill name after a slash can never masquerade as an endpoint.
EP_SEGMENTS = "instagram|search|prism|tiktok|google_news|google_trends|reddit|credits"
RX_ENDPOINT = re.compile(
    r"(?:`|/v1/|socialcrawl\.dev/)((?:" + EP_SEGMENTS + r")(?:/[A-Za-z0-9_-]+)+)")

# Say: "phrase" / Say later: "phrase" / later, say: "phrase", either quote style.
RX_SAY = re.compile(r"(?:say(?:\s+later)?:|later,\s*say:)\s*(\"|'|“|‘)", re.I)
QUOTE_CLOSE = {'"': '"', "'": "'", "“": "”", "‘": "’"}


def _lf_text(path):
    """File contents with CRLF normalised to LF (see the module docstring)."""
    return path.read_bytes().replace(b"\r\n", b"\n").decode("utf-8", "replace")


def _byte_offset(text, char_index):
    return len(text[:char_index].encode("utf-8"))


def _lines(text):
    """[(char_start, line, in_fence)] for every line. A ``` line is itself fenced."""
    out = []
    pos = 0
    fenced = False
    for line in text.split("\n"):
        opens = line.lstrip().startswith("```")
        out.append((pos, line, fenced or opens))
        if opens:
            fenced = not fenced
        pos += len(line) + 1
    return out


def _squash(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def _frontmatter(text):
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else ""


def _table_ids(text):
    """{id: row} for every markdown table row whose first cell is a ledger id."""
    rows = {}
    for line in text.split("\n"):
        m = RX_ROW_ID.match(line.strip())
        if m:
            rows[m.group(1)] = line.strip()
    return rows


def _section(text, heading):
    """(start_char, end_char) of a `## heading` section, or None."""
    lines = _lines(text)
    start = None
    for pos, line, fenced in lines:
        if fenced:
            continue
        if start is None and line.strip() == heading:
            start = pos
        elif start is not None and line.startswith("## "):
            return (start, pos)
    return (start, len(text)) if start is not None else None


def collect():
    """(errors, warnings, stats). Both lists hold ready-to-print annotations."""
    errors = []
    warnings = []
    stats = {"skills": 0, "blocks": 0, "endpoints": 0, "phrases": 0}

    for plugin in sorted(PLUGINS):
        root = REPO / "plugins" / plugin
        if not root.is_dir():
            errors.append("::error::%s: plugin folder not found" % plugin)
            continue

        skills = sorted(root.glob("skills/*/SKILL.md"))
        skill_names = set(p.parent.name for p in skills)
        stats["skills"] += len(skills)

        shared = root / "skills" / "_shared" / "references"
        jmap_path = shared / "journey-map.md"
        ep_path = shared / "socialcrawl-endpoints.md"
        jmap = _lf_text(jmap_path) if jmap_path.exists() else ""
        if not jmap:
            errors.append("::error file=plugins/%s/skills/_shared/references/journey-map.md"
                          "::journey-map.md missing; every routing id is unresolvable" % plugin)
        ledger = _table_ids(jmap)

        # --- 3b. registry rows must name a skill that exists ------------------
        for label in ("### Happy path", "### Failure edges"):
            block = jmap.split(label, 1)
            if len(block) < 2:
                if jmap:
                    errors.append("::error file=plugins/%s/skills/_shared/references/journey-map.md"
                                  "::missing the '%s' table" % (plugin, label))
                continue
            for line in block[1].split("\n"):
                if line.startswith("### ") or line.startswith("## "):
                    break
                m = RX_ROW_ID.match(line.strip())
                if not m:
                    continue
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                frm = cells[1] if len(cells) > 1 else ""
                word = re.match(r"[`*]*([A-Za-z][A-Za-z0-9-]*)", frm)
                if not word:
                    continue
                name = word.group(1)
                if name.lower() in ("any", "a", "an", "the"):
                    continue  # a generic row ("any skill, prereq missing")
                if name not in skill_names:
                    errors.append(
                        "::error file=plugins/%s/skills/_shared/references/journey-map.md"
                        "::registry row %s names skill '%s', which has no "
                        "skills/%s/SKILL.md" % (plugin, m.group(1), name, name))

        # --- per-skill checks -------------------------------------------------
        say_haystack = [_squash(jmap.split("## Edge registry", 1)[0])]
        for sk in skills:
            say_haystack.append(_squash(_frontmatter(_lf_text(sk))))
        haystack = " | ".join(say_haystack)

        for sk in skills:
            rel = "plugins/%s/%s" % (plugin, sk.relative_to(root).as_posix())
            text = _lf_text(sk)
            size = len(text.encode("utf-8"))
            lines = _lines(text)

            # 2. structure
            for heading in ("## Prereq (E0)", "## Terminal paths"):
                if not any(ln.strip() == heading and not f for _, ln, f in lines):
                    errors.append("::error file=%s::missing the '%s' heading "
                                  "(routing.md: every skill names its door and "
                                  "writes every ending)" % (rel, heading))
            tp = _section(text, "## Terminal paths")

            # 1. placement of the section itself
            if tp and size > TOP_THIRD_FROM:
                start_b = _byte_offset(text, tp[0])
                if start_b >= size // 3:
                    errors.append(
                        "::error file=%s::'## Terminal paths' starts at byte %d of %d; "
                        "a file over %d bytes must start it inside the top third "
                        "(under byte %d) so the blocks survive a compaction"
                        % (rel, start_b, size, TOP_THIRD_FROM, size // 3))

            for pos, line, fenced in lines:
                if fenced or not RX_HEADER.match(line):
                    continue
                stats["blocks"] += 1
                off = _byte_offset(text, pos)

                # 1. placement of each block
                if off >= BLOCK_CUT:
                    errors.append(
                        "::error file=%s::Next-moves block at byte %d is past the "
                        "%d-byte compaction cut; it stops existing mid-session"
                        % (rel, off, BLOCK_CUT))

                # 2. blocks live under Terminal paths
                if tp and not (tp[0] <= pos < tp[1]):
                    errors.append(
                        "::error file=%s::Next-moves block at byte %d sits outside "
                        "the '## Terminal paths' section (bytes %d to %d)"
                        % (rel, off, _byte_offset(text, tp[0]), _byte_offset(text, tp[1])))

                # 3. every block cites a ledger id
                ids = RX_ID.findall(line)
                if not ids:
                    for p2, l2, f2 in lines:
                        if p2 <= pos or f2:
                            continue
                        if not l2.strip():
                            continue
                        ids = RX_ID.findall(l2)
                        break
                if not ids:
                    errors.append(
                        "::error file=%s::Next-moves block at byte %d cites no "
                        "journey-map id; put (E<n>) / (F<n>) in the header or on "
                        "the first line under it" % (rel, off))
                for i in ids:
                    if i not in ledger:
                        errors.append(
                            "::error file=%s::block at byte %d cites %s, which has "
                            "no row in journey-map.md" % (rel, off, i))

            # warnings: unresolved Say: phrases
            for idx, (pos, line, fenced) in enumerate(lines):
                if fenced:
                    continue
                for m in RX_SAY.finditer(line):
                    q = m.group(1)
                    tail = line[m.end():]
                    close = tail.find(QUOTE_CLOSE[q])
                    if close == -1 and idx + 1 < len(lines):
                        tail = tail + " " + lines[idx + 1][1].strip()
                        close = tail.find(QUOTE_CLOSE[q])
                    if close == -1:
                        continue
                    phrase = _squash(tail[:close])
                    stats["phrases"] += 1
                    if "(if installed)" in line.lower():
                        continue
                    if phrase and phrase not in haystack:
                        warnings.append(
                            "::warning file=%s::Say: \"%s\" resolves to no skill "
                            "description and no journey-map roster row"
                            % (rel, tail[:close].strip()))

        # --- 4. endpoint table closure ---------------------------------------
        table = _lf_text(ep_path) if ep_path.exists() else ""
        if not table:
            errors.append("::error file=plugins/%s/skills/_shared/references/"
                          "socialcrawl-endpoints.md::endpoints table missing" % plugin)
        listed = set()
        for line in table.split("\n"):
            if not line.startswith("|"):
                continue
            first = line.strip().strip("|").split("|")[0].strip().strip("`")
            if "/" in first and re.match(r"^(" + EP_SEGMENTS + r")/", first):
                listed.add(first)
        if RETIRED_ALIAS in listed:
            errors.append("::error file=plugins/%s/skills/_shared/references/"
                          "socialcrawl-endpoints.md::`%s` is a retired alias, not an "
                          "endpoint; the real call is instagram/search/reels"
                          % (plugin, RETIRED_ALIAS))
        seen = {}
        for f in sorted(list(root.rglob("*.md")) + list(root.rglob("*.py"))):
            if f.name == "CHANGELOG.md":     # a changelog may quote retired history
                continue
            body = _lf_text(f)
            for pos, line, fenced in _lines(body):
                if fenced:
                    continue
                for m in RX_ENDPOINT.finditer(line):
                    seen.setdefault(m.group(1), f)
        stats["endpoints"] = len(seen)
        for path, where in sorted(seen.items()):
            if path not in listed:
                errors.append(
                    "::error file=plugins/%s/%s::endpoint `%s` is called or "
                    "documented here but has no row in socialcrawl-endpoints.md"
                    % (plugin, where.relative_to(root).as_posix(), path))

        # --- 5. catalog description prefix -----------------------------------
        mkt_path = REPO / ".claude-plugin" / "marketplace.json"
        try:
            mkt = json.loads(mkt_path.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append("::error file=.claude-plugin/marketplace.json::%s" % e)
            mkt = {"plugins": []}
        entry = next((p for p in mkt.get("plugins", []) if p.get("name") == plugin), None)
        if entry is None:
            errors.append("::error file=.claude-plugin/marketplace.json::"
                          "no catalog entry for %s" % plugin)
        else:
            want = "v%s " % entry.get("version")
            if not (entry.get("description") or "").startswith(want):
                errors.append(
                    "::error file=.claude-plugin/marketplace.json::%s description must "
                    "start with '%s' (clients read the version off the catalog card)"
                    % (plugin, want))

        # --- 6. README skill counts ------------------------------------------
        n = len(skills)
        root_readme = (REPO / "README.md").read_text(encoding="utf-8")
        row = next((ln for ln in root_readme.splitlines()
                    if "plugins/%s/" % plugin in ln), None)
        if row is None:
            errors.append("::error file=README.md::no catalog row for %s" % plugin)
        elif "**%d skills.**" % n not in row:
            errors.append("::error file=README.md::%s row must say '**%d skills.**' "
                          "(skills/*/SKILL.md on disk: %d)" % (plugin, n, n))
        pr = root / "README.md"
        if not pr.exists():
            errors.append("::error file=plugins/%s/README.md::missing" % plugin)
        elif "**%d skills**" % n not in pr.read_text(encoding="utf-8"):
            errors.append("::error file=plugins/%s/README.md::must say '**%d skills**' "
                          "(skills/*/SKILL.md on disk: %d)" % (plugin, n, n))

    return errors, warnings, stats


def summary(stats):
    return ("%d skills, %d Next-moves blocks, %d Say: phrases, %d endpoint paths"
            % (stats["skills"], stats["blocks"], stats["phrases"], stats["endpoints"]))


def main():
    errors, warnings, stats = collect()
    for w in warnings:
        print(w)
    print("check_routing: %s | %d error(s), %d warning(s)"
          % (summary(stats), len(errors), len(warnings)))
    if errors:
        print("")
        for e in errors:
            print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
