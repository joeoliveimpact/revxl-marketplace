#!/usr/bin/env python3
"""
scrub_check.py — enforce the firm's anti-AI scrubber on filings.

Flags what the scrubber bans: em dashes, en dashes, dash-as-pause, semicolons,
non-required colons, and AI-tell phrases. Exit code 1 if any hard violation.

USAGE:
  python scrub_check.py <file-or-dir> [--phrases]
    --phrases  also report AI-tell phrases (warnings, not hard fails)

HARD fails: em dash (U+2014), en dash (U+2013), " -- " or " - " used as a pause,
semicolons. Colons are reported as warnings (many are legitimate: caption labels,
list lead-ins, times like 9:00, citations) so a human confirms each.
"""
import sys, re, os
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HARD = {
    "em dash (—)": re.compile(r"—"),
    "en dash (–)": re.compile(r"–"),
    "double hyphen dash (--)": re.compile(r"--"),
    "spaced-hyphen dash ( - )": re.compile(r"(?<=\S) - (?=\S)"),
    "semicolon": re.compile(r";"),
}
# colon that is NOT a time (9:00), NOT a list/label lead-in at line end, NOT a URL
COLON_WARN = re.compile(r"(?<=[A-Za-z]):(?=\s)(?!//)")
PHRASES = [
    "delve", "moreover", "furthermore", "in conclusion", "a testament to",
    "navigate the complexities", "it's worth noting", "it is worth noting",
    "important to remember", "i want to be clear", "i understand that",
    "certainly!", "great question", "rest assured",
]

def is_list_marker(line, idx):
    # a hyphen at the start of a (trimmed) line is a markdown bullet, not a dash
    stripped = line[:idx].strip()
    return stripped == "" and line[idx] == "-"

def check_file(path, do_phrases):
    text = open(path, encoding="utf-8", errors="replace").read()
    lines = text.splitlines()
    hard_hits, colon_hits, phrase_hits = [], [], []
    for n, line in enumerate(lines, 1):
        low = line.lower()
        for label, rx in HARD.items():
            for m in rx.finditer(line):
                if label.startswith("spaced") or "double" in label:
                    if is_list_marker(line, m.start()):
                        continue
                hard_hits.append((n, label, line.strip()[:90]))
        for m in COLON_WARN.finditer(line):
            # skip times and obvious label lead-ins (word(s) then colon at clause)
            colon_hits.append((n, line.strip()[:90]))
        if do_phrases:
            for p in PHRASES:
                if p in low:
                    phrase_hits.append((n, p, line.strip()[:90]))
    return hard_hits, colon_hits, phrase_hits

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_phrases = "--phrases" in sys.argv
    if not args:
        print("usage: scrub_check.py <file-or-dir> [--phrases]"); sys.exit(2)
    target = args[0]
    files = []
    if os.path.isdir(target):
        for root, _, fs in os.walk(target):
            for f in fs:
                if f.endswith(".md"):
                    files.append(os.path.join(root, f))
    else:
        files = [target]
    total_hard = 0
    for path in sorted(files):
        hard, colons, phrases = check_file(path, do_phrases)
        if not hard and not colons and not phrases:
            print(f"CLEAN  {path}")
            continue
        print(f"\n=== {path} ===")
        if hard:
            total_hard += len(hard)
            print(f"  HARD VIOLATIONS: {len(hard)}")
            for n, label, snip in hard[:12]:
                print(f"    L{n} [{label}]  {snip}")
        if colons:
            print(f"  colon warnings (confirm each is required): {len(colons)}")
        if do_phrases and phrases:
            print(f"  AI-tell phrases: {len(phrases)}")
            for n, p, snip in phrases[:8]:
                print(f"    L{n} '{p}'  {snip}")
    print(f"\nTOTAL HARD VIOLATIONS: {total_hard}")
    sys.exit(1 if total_hard else 0)

if __name__ == "__main__":
    main()
