"""Pick the next client answer for a walk turn. Usage:
    py -3.12 respond.py <answers file> <turn.jsonl>   the answer to the last assistant text in that turn
    py -3.12 respond.py <answers file> --open         the opening message
    py -3.12 respond.py <answers file> -              the answer to plain text read from stdin (dry run)

Answers file: one rule per line, `<regex> ==> <answer>`; `#` lines and blank lines are
skipped. `OPEN ==> ...` is the first message, `DEFAULT ==> ...` the answer when no rule
matches. Rules are tried in file order, case-insensitive, dot matches newline; first match
wins. Two passes: first against the tail of the text (the ask sits at the end), then against
the whole text (a checkpoint heading sits at the top).

Refuses (exit 2) when any answer carries a phrase the plugin's trigger hook routes to another
skill: the patterns are read from the plugin under test, hooks/skill-trigger.sh, so a stray
nudge cannot enter a walk. The opening message may route to reel-scripter; nothing else may.
"""
import json, re, sys
from pathlib import Path

TAIL = 700  # ponytail: fixed tail window; widen if a model puts long notes after its ask
HOOK = Path(__file__).resolve().parents[3] / "plugins/shortform-superengine/hooks/skill-trigger.sh"
FLAGS = re.I | re.S


def load(path):
    rules, special = [], {}
    for n, ln in enumerate(Path(path).read_text("utf-8-sig").splitlines(), 1):
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        if " ==> " not in ln:
            sys.exit(f"refuse: {path} line {n} has no ' ==> '")
        rx, ans = (s.strip() for s in ln.split(" ==> ", 1))
        if rx in ("OPEN", "DEFAULT"):
            special[rx] = ans
        else:
            rules.append((re.compile(rx, FLAGS), ans))
    if set(special) != {"OPEN", "DEFAULT"}:
        sys.exit(f"refuse: {path} needs one OPEN and one DEFAULT line")
    return rules, special


def guard(rules, special):
    """Every answer against every trigger pattern in the hook, except the opening message
    against the reel-scripter one (that is the route a walk starts on)."""
    if not HOOK.exists():
        print(f"refuse: no trigger hook at {HOOK}", file=sys.stderr)
        sys.exit(2)
    pats = dict(re.findall(r"^([A-Z_]+)='(.*)'\s*$", HOOK.read_text("utf-8"), re.M))
    if "POLARIZE" not in pats:
        print("refuse: the trigger hook has no POLARIZE line to guard against", file=sys.stderr)
        sys.exit(2)
    answers = [("OPEN", special["OPEN"]), ("DEFAULT", special["DEFAULT"])] + [(r.pattern, a) for r, a in rules]
    for who, ans in answers:
        for name, p in pats.items():
            if who == "OPEN" and name == "REEL_SCRIPTER":
                continue
            if re.search(p, ans, re.I):
                print(f"refuse: answer for {who!r} matches the hook's {name} pattern, so the walk "
                      f"would get a {name.lower()} nudge: {ans!r}", file=sys.stderr)
                sys.exit(2)


def last_text(jsonl):
    text = ""
    for ln in Path(jsonl).read_text("utf-8", errors="replace").splitlines():
        if not ln.strip().startswith("{"):
            continue
        e = json.loads(ln)
        if e.get("type") == "assistant":
            for c in e.get("message", {}).get("content", []):
                if c.get("type") == "text" and c.get("text", "").strip():
                    text = c["text"]
        elif e.get("type") == "result" and not text:
            text = e.get("result") or ""
    return text


def pick(rules, special, text):
    for scope in (text[-TAIL:], text):
        for rx, ans in rules:
            if rx.search(scope):
                return ans
    return special["DEFAULT"]


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    rules, special = load(sys.argv[1])
    guard(rules, special)
    src = sys.argv[2]
    if src == "--open":
        print(special["OPEN"])
    else:
        print(pick(rules, special, sys.stdin.read() if src == "-" else last_text(src)))
