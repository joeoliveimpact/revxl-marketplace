#!/usr/bin/env python3
"""No-leak gate — run BEFORE packaging or sharing the skill / marketplace bundle.

It refuses to pass (exit 1) if it finds any of the user's personal identifiers,
any email/phone/SSN that looks real, or any case-data file that has sneaked into
the shippable directory. This is the mechanical guarantee that nothing personal
ships, instead of relying on a human to remember to look.

Usage:
  python scripts/check_no_pii.py <dir-to-check> [more dirs...]
Examples:
  python scripts/check_no_pii.py .claude/skills/mississippi
  python scripts/check_no_pii.py outputs/final/marketplace

Patterns come from scripts/pii_patterns.txt (gitignored, never shipped). Exit 0
= clean and safe to share. Exit 1 = STOP, a leak was found, fix it first.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATTERNS_FILE = os.path.join(HERE, "pii_patterns.txt")

TEXT_EXT = {".md", ".py", ".json", ".txt", ".yml", ".yaml", ".html", ".csv", ".js"}

# Case-data files/dirs that must never live inside a shippable skill directory.
FORBIDDEN_NAMES = {"case-profile.md", "case-checklist.md"}
FORBIDDEN_DIRS = {"evidence", "knowledge base"}

EMAIL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# Public help lines that SHOULD ship (not personal info). Digits only; a leading 1 is ignored.
SAFE_PHONES = {
    # crisis / DV hotlines
    "8007997233", "8004224453", "8006624357", "8002738255", "988", "741741", "911",
    # public MS legal-aid resource lines (free help the firm hands the user)
    "6019609581", "6018825001",
}


def is_safe_phone(s):
    d = re.sub(r"\D", "", s)
    if d.startswith("1") and len(d) == 11:
        d = d[1:]
    return d in SAFE_PHONES


# The author's display NAME (only) may appear in intentional attribution/legal files.
# This never permits the email, address, cause number, or any opposing party's name.
ATTRIBUTION_NAMES = {"[your-attribution-name]"}  # names allowed ONLY in plugin.json/LICENSE fields
ATTRIBUTION_FILES = {"license", "license.md", "license.txt", "disclaimer.md", "notice", "notice.md"}


def allowed_attribution(path, line, pat):
    if pat not in ATTRIBUTION_NAMES:
        return False
    base = os.path.basename(path).lower()
    if base in ATTRIBUTION_FILES:
        return True
    if base in {"plugin.json", "marketplace.json"} and '"name"' in line.lower():
        return True
    return False
# lines that are obviously template placeholders, not real data
PLACEHOLDER_HINT = re.compile(r"\{\{|e\.g\.|placeholder|sample|example|xxxx|\.\.\.@|your[ -]?name|@example\.")


def load_patterns():
    pats = []
    if os.path.exists(PATTERNS_FILE):
        for line in open(PATTERNS_FILE, encoding="utf-8"):
            s = line.strip()
            if s and not s.startswith("#"):
                pats.append(s.lower())
    return pats


def scan_dir(root, pats):
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        # forbidden case-data directories inside a shippable dir
        for d in list(dirnames):
            if d.lower() in FORBIDDEN_DIRS:
                hits.append((os.path.join(dirpath, d), 0, f"FORBIDDEN case-data directory '{d}/' inside shippable dir"))
        for fn in filenames:
            if fn.lower() in FORBIDDEN_NAMES:
                hits.append((os.path.join(dirpath, fn), 0, f"FORBIDDEN case-data file '{fn}' inside shippable dir"))
            ext = os.path.splitext(fn)[1].lower()
            if ext not in TEXT_EXT:
                continue
            path = os.path.join(dirpath, fn)
            try:
                for i, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
                    low = line.lower()
                    for p in pats:
                        if p in low:
                            if allowed_attribution(path, line, p):
                                continue
                            hits.append((path, i, f"identifier '{p}': {line.strip()[:120]}"))
                    is_placeholder = bool(PLACEHOLDER_HINT.search(low))
                    if not is_placeholder:
                        for rx, label in ((EMAIL_RE, "email"), (PHONE_RE, "phone"), (SSN_RE, "SSN")):
                            m = rx.search(line)
                            if m:
                                if label == "phone" and is_safe_phone(m.group(0)):
                                    continue
                                hits.append((path, i, f"{label}-like '{m.group(0)}': {line.strip()[:120]}"))
            except Exception as e:
                hits.append((path, 0, f"could not read ({e})"))
    return hits


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    targets = sys.argv[1:]
    if not targets:
        print("usage: python scripts/check_no_pii.py <dir> [dir...]")
        return 2
    pats = load_patterns()
    if not pats:
        print(f"WARNING: no patterns loaded from {PATTERNS_FILE} (identifier check disabled; regex checks still run)")
    all_hits = []
    for t in targets:
        if not os.path.exists(t):
            print(f"  skip (not found): {t}")
            continue
        all_hits += scan_dir(t, pats)
    if all_hits:
        print(f"\n[BLOCKED] {len(all_hits)} possible leak(s) found. DO NOT SHARE until fixed:\n")
        for path, ln, why in all_hits:
            loc = f"{path}:{ln}" if ln else path
            print(f"  {loc}\n      {why}")
        print("\nFix each, then re-run. (If a hit is a false positive, narrow the pattern or mark the line as a placeholder.)")
        return 1
    print(f"\n[CLEAN] No personal info found in: {', '.join(targets)}. Safe to package/share.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
