#!/usr/bin/env python3
"""Sync brand-brain's 9 shared body files from the canonical workspace source
into both marketplace bundles (email flat refs dir, shortform per-skill refs dir).

SKILL.md is NOT synced - each bundle carries an adapted router (own frontmatter,
tie-in sections). Edit those per-bundle by hand.

Usage (from repo root or anywhere):
  python scripts/sync-brand-brain.py --check   # dry-run: diff transformed source vs bundles
  python scripts/sync-brand-brain.py           # write transformed source into bundles

Transform per destination: '@references/' and '@tasks/' -> plugin-root prefix
(both bundles flatten tasks+references into one dir), LF -> CRLF.
Run --check before any version bump; a diff means source and bundles drifted.
"""
import sys
from pathlib import Path

SRC = Path(r"C:\Users\joeol\OneDrive\Desktop\Cowork and Antigravity\REVUP Claude Skill Archtiect\brand-brain\skill")
REPO = Path(__file__).resolve().parent.parent
DESTS = {
    "email": (REPO / "plugins/email-sequence-superengine/references/brand-brain",
              "${CLAUDE_PLUGIN_ROOT}/references/brand-brain/"),
    "shortform": (REPO / "plugins/shortform-superengine/skills/brand-brain/references",
                  "${CLAUDE_PLUGIN_ROOT}/skills/brand-brain/references/"),
    "carousel": (REPO / "plugins/carousel-superengine/references/brand-brain",
                 "${CLAUDE_PLUGIN_ROOT}/references/brand-brain/"),
}
FILES = [("tasks", n) for n in ("mine.md", "refresh.md", "interview.md")] + \
        [("references", n) for n in ("artifacts.md", "extraction.md", "freshness.md",
                                     "signature-bits.md", "source-ladder.md", "speaker-separation.md")]

def read(p: Path) -> str:
    return p.read_bytes().decode("utf-8")

def transform(lf_text: str, prefix: str) -> str:
    out = lf_text.replace("@references/", prefix).replace("@tasks/", prefix)
    return out.replace("\n", "\r\n")

def first_diff_line(a: str, b: str) -> int:
    for i, (la, lb) in enumerate(zip(a.splitlines(), b.splitlines()), 1):
        if la != lb:
            return i
    return min(len(a.splitlines()), len(b.splitlines())) + 1

def main() -> None:
    check = "--check" in sys.argv
    diffs = 0
    for sub, name in FILES:
        lf_text = read(SRC / sub / name).replace("\r\n", "\n")
        for dest_name, (dest_dir, prefix) in DESTS.items():
            expected = transform(lf_text, prefix)
            dest = dest_dir / name
            current = read(dest) if dest.exists() else ""
            if check:
                if current != expected:
                    diffs += 1
                    print(f"DIFF {dest_name}/{name} (first differing line: {first_diff_line(current, expected)})")
            elif current != expected:
                dest.write_bytes(expected.encode("utf-8"))
                print(f"wrote {dest_name}/{name}")
    if check:
        print(("FAIL: %d file(s) differ" % diffs) if diffs else "OK: all bundle files match transformed source")
        sys.exit(1 if diffs else 0)
    print("sync complete (SKILL.md per-bundle, edit by hand)")

main()
