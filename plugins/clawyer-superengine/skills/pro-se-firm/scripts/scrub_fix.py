#!/usr/bin/env python3
"""
scrub_fix.py — auto-enforce the firm's no-dash / no-semicolon rule on a filing.

Instruction alone does not stop the model from emitting em dashes, so this
mechanically rewrites them. It is conservative and writes a SEPARATE *_scrubbed.md
plus a change log, so a human reviews before filing (never silently ship a filing).

USAGE:
  python scrub_fix.py <file.md>            # writes <file>_scrubbed.md + prints changes
  python scrub_fix.py <file.md> --inplace  # overwrite the file (use with care)

RULES APPLIED:
  - em dash (—), en dash (–), " -- ", " - " (dash-as-pause)  -> ". " before a capital,
    else ", "  (so an appositive becomes a comma, a sentence break becomes a period)
  - semicolon -> ". " and capitalize the next letter (a semicolon joins clauses)
  - hyphens INSIDE words/numbers (self-represented, 2024-1234, pp. 1-40) are untouched
  - colons are left alone (flagged by scrub_check for human confirmation)
"""
import sys, re

def repl_dash(m):
    after = m.group("after")
    if after and after.isupper():
        return ". " + after
    return ", " + (after or "")

def fix(text):
    changes = []
    # unicode em/en dash with optional surrounding spaces, capture next char
    def track(pattern, fn, label):
        nonlocal text
        new, n = re.subn(pattern, fn, text)
        if n:
            changes.append(f"{label}: {n}")
        text = new
    # em/en dash (with or without spaces)
    track(r"\s*[—–]\s*(?P<after>\S)", repl_dash, "em/en dash")
    # double hyphen used as dash
    track(r"\s+--\s+(?P<after>\S)", repl_dash, "double-hyphen dash")
    # spaced single hyphen used as a pause (not a list bullet: requires non-space before)
    track(r"(?<=\S)\s+-\s+(?P<after>\S)", repl_dash, "spaced-hyphen dash")
    # semicolon -> period + capitalize next letter
    def repl_semi(m):
        after = m.group("after")
        return ". " + (after.upper() if after else "")
    track(r"\s*;\s*(?P<after>\S)?", repl_semi, "semicolon")
    return text, changes

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: scrub_fix.py <file.md> [--inplace]"); sys.exit(2)
    path = args[0]
    inplace = "--inplace" in sys.argv
    src = open(path, encoding="utf-8").read()
    fixed, changes = fix(src)
    out = path if inplace else re.sub(r"\.md$", "_scrubbed.md", path)
    open(out, "w", encoding="utf-8", newline="\n").write(fixed)
    print(f"wrote: {out}")
    print("changes:", ", ".join(changes) if changes else "none")
    print("Now run scrub_check.py on the output and READ it — confirm grammar before filing.")

if __name__ == "__main__":
    main()
