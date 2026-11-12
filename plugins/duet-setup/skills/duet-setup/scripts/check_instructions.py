#!/usr/bin/env python3
"""Check a Duet channel instructions block before the person pastes it.

Run:  python3 scripts/check_instructions.py <file> [<file> ...] [--allow-dashes]
      python3 scripts/check_instructions.py --selftest

Each file holds one channel's instructions block, exactly as it will be pasted.
Prints the character count and every problem, then exits 0 if all files pass
and 1 if any fails. Em and en dashes fail by default; --allow-dashes lets them
through. Standard library only.
"""

import argparse
import re
import sys
from pathlib import Path

LIMIT = 2000  # Duet's channel instructions field holds at most 2,000 characters
HEADROOM = 1900  # warn above this, since the review round usually adds a line or two
# Unfilled template parts like <person>. Up to 200 characters, because some
# template parts are whole sentences (the tracker paragraph, the hard-rules line)
# and a 60-character cap let those through unfilled.
PLACEHOLDER = re.compile(r"<[^<>\n]{1,200}>")
RULES_POINTER = re.compile(r'memory under\s+"?Rules"?', re.IGNORECASE)
DASHES = {chr(0x2014): "em dash", chr(0x2013): "en dash"}


def utf16_length(text: str) -> int:
    """Length as a browser counts it, where some emoji take two units."""
    return len(text.encode("utf-16-le")) // 2


def assess(text: str, allow_dashes: bool = False):
    """Return (count, problems, warnings) for one instructions block."""
    text = text.strip("\n")
    count = max(len(text), utf16_length(text))
    problems, warnings = [], []

    if not text.strip():
        problems.append("the file is empty")
    if count > LIMIT:
        problems.append(
            f"{count} characters, {count - LIMIT} over the {LIMIT} limit. "
            "Move workflow detail to the Rules block, then shorten wording; never cut a hard limit."
        )
    elif count > HEADROOM:
        warnings.append(f"{count} characters leaves little room for review changes")

    for match in PLACEHOLDER.finditer(text):
        problems.append(f"unfilled template part {match.group(0)}; replace it with the real value")

    if not RULES_POINTER.search(text):
        warnings.append('no pointer to the Rules ("Your workflow rules are in your memory under "Rules"")')

    if not allow_dashes:
        for char, name in DASHES.items():
            hits = text.count(char)
            if hits:
                problems.append(f"{hits} {name}(es); use a comma, a colon or a full stop instead")

    return count, problems, warnings


def check(path: Path, allow_dashes: bool) -> bool:
    if path.is_dir():  # Windows reports a folder as PermissionError, so check first
        print(f"FAIL {path}: this is a folder. Pass the text file that holds one instructions block.")
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"FAIL {path}: file not found. Save the instructions block to this path first.")
        return False
    except IsADirectoryError:
        print(f"FAIL {path}: this is a folder. Pass the text file that holds one instructions block.")
        return False
    except PermissionError:
        print(f"FAIL {path}: no permission to read it. Save the block somewhere you can read, then run again.")
        return False
    except UnicodeDecodeError:
        print(f"FAIL {path}: not UTF-8 text. Save the block as plain text and run again.")
        return False

    count, problems, warnings = assess(text, allow_dashes)
    status = "FAIL" if problems else "PASS"
    print(f"{status} {path}: {count} of {LIMIT} characters")
    for item in problems:
        print(f"  problem: {item}")
    for item in warnings:
        print(f"  warning: {item}")
    return not problems


def selftest() -> int:
    pointer = 'Your workflow rules are in your memory under "Rules".'
    dashed = "You are Ledger" + chr(0x2014) + "Rosa's agent.\n" + pointer

    _, problems, _ = assess("a" * (LIMIT + 1) + "\n" + pointer)
    assert any("over the" in p for p in problems), "over-limit not caught"

    _, problems, _ = assess(dashed)
    assert any("em dash" in p for p in problems), "dash not caught by default"
    _, problems, _ = assess(dashed, allow_dashes=True)
    assert not problems, "--allow-dashes did not let the dash through"

    _, problems, _ = assess("You are <channel name>.\n" + pointer)
    assert any("<channel name>" in p for p in problems), "short placeholder not caught"

    long_part = '<Their own "never without asking" limits for this area, one line each, from planning question 2.>'
    assert len(long_part) > 62, "test placeholder is too short to test the widened pattern"
    _, problems, _ = assess("Hard rules:\n- " + long_part + "\n" + pointer)
    assert any("never without asking" in p for p in problems), "long placeholder not caught"

    _, problems, warnings = assess("You are Ledger, Rosa's bookkeeping agent.")
    assert not problems, f"clean block failed: {problems}"
    assert any("no pointer to the Rules" in w for w in warnings), "missing Rules pointer not warned"

    print("selftest: all checks passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Duet channel instructions blocks.")
    parser.add_argument("files", nargs="*", type=Path, help="one instructions block per file")
    parser.add_argument("--allow-dashes", action="store_true", help="let em and en dashes through")
    parser.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.files:
        parser.error("give at least one file, or --selftest")
    results = [check(path, args.allow_dashes) for path in args.files]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
