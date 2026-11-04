"""F3 check: flags what a coach must never see in a reply (file names, paths, JSON,
STATUS or FIX lines, script names). Prints one line per hit, location and kind only.

usage: python coach_lines_check.py [reply.txt]     (no file: reads stdin)
       python coach_lines_check.py --selftest
exit:  0 clean, 1 hits (or a failed selftest)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills/_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402

EXT = r"(?:json|md|py|txt|mp4|mov|wav|html|csv|sh|ps1|lock|toml|ya?ml)"
SCRIPT_EXT = {"py", "sh", "ps1"}
SEP = r"[\\/]"
SEG = r"[\w.-]+"

STATUS = re.compile(r"^[ \t]*(?:STATUS|FIX) .*$", re.M)
JSON = re.compile(r"[\[{]\s*\"[^\"\n]*\"\s*:")
WEB_URL = re.compile(r"https?://\S+")  # a web link may be shown; file:// is still checked below
PATH = re.compile(
    r"\$\{CLAUDE_PLUGIN_ROOT\}(?:" + SEP + SEG + r")*" + SEP + r"?"
    r"|(?<![\w])(?:[A-Za-z]:" + SEP + r"|\.{1,2}" + SEP + r"|~" + SEP + r"|" + SEP + r")?"
    + SEG + r"(?:" + SEP + SEG + r")+" + SEP + r"?")
FILE = re.compile(r"(?<![\w.-])[\w-]+(?:\.[\w-]+)*\.(" + EXT + r")\b", re.I)


def is_path(tok):
    """`and/or`, `24/7` and dates like `11/04/26` are prose, not paths."""
    if tok.startswith("${CLAUDE_PLUGIN_ROOT}"):
        return True
    if re.match(r"(?:[A-Za-z]:|\.{1,2}|~)?" + SEP, tok) or re.search(SEP + "$", tok):
        return True
    segs = [s for s in re.split(SEP, tok) if s]
    if all(s.isdigit() for s in segs):
        return False
    return len(segs) >= 3 or any(FILE.fullmatch(s) for s in segs)


def check(text):
    """Return [(line, col, kind)]. Each hit is blanked out so a path isn't also counted as a file name."""
    hits = []
    buf = [text]

    def scan(rx, kind_of, keep=lambda m: True):
        def repl(m):
            if not keep(m):
                return m.group(0)
            kind = kind_of(m)
            if kind:
                line = buf[0].count("\n", 0, m.start()) + 1
                col = m.start() - (buf[0].rfind("\n", 0, m.start()) + 1) + 1
                hits.append((line, col, kind))
            return re.sub(r"[^\n]", " ", m.group(0))
        buf[0] = rx.sub(repl, buf[0])

    scan(STATUS, lambda m: "STATUS or FIX line")
    scan(JSON, lambda m: "JSON")
    scan(WEB_URL, lambda m: None)
    scan(PATH, lambda m: "path", keep=lambda m: is_path(m.group(0)))
    scan(FILE, lambda m: "script name" if m.group(1).lower() in SCRIPT_EXT else "file name")
    return sorted(hits)


def selftest():
    clean = ("Your first cut is ready. It runs 1.5 s shorter, e.g. the pause after point two is gone, "
             "about 10.5 seconds in all. Have a listen and/or tell me what to change. "
             "Here's the page: https://example.com/teardown\nSaved on 11/04/26, 24/7 support.")
    cases = [
        ("clean reply", clean, set()),
        ("file name", "I saved it as teardown.md for you.", {"file name"}),
        ("JSON", 'The setup says {"needs": ["python"]} so we are fine.', {"JSON"}),
        ("STATUS line", "Checked.\nSTATUS ffmpeg ok 6.1\nAll good.", {"STATUS or FIX line"}),
        ("path", "It lives in ${CLAUDE_PLUGIN_ROOT}/skills/reel-teardown now.", {"path"}),
        ("home path", "The key is at ~/.config/socialcrawl/api_key.", {"path"}),
        ("windows path", r"Look in C:\work\cuts for it.", {"path"}),
        ("script name", "I ran check_deps.py and it passed.", {"script name"}),
    ]
    failed = [name for name, text, want in cases if {k for _, _, k in check(text)} != want]
    if failed:
        print("SELFTEST FAIL: " + ", ".join(failed))
        return 1
    print("SELFTEST PASS")
    return 0


def main():
    ensure_utf8_output()
    args = sys.argv[1:]
    if args == ["--selftest"]:
        return selftest()
    text = Path(args[0]).read_text(encoding="utf-8") if args else sys.stdin.read()
    hits = check(text)
    for line, col, kind in hits:
        print(f"line {line}, col {col}: {kind}")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
