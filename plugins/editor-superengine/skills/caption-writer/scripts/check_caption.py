"""Check a caption draft before the client sees it (stdlib only).

  check_caption.py --caption videos/<reel>/caption.md --source <transcript.txt>
                   [--cta "<phrase>" ...] [--no-dashes] [--json] [--selftest]

Reads only the audience-facing text: markdown heading lines ("# ...") and <!-- comments --> are skipped.
1 numbers   every number in the caption (1,000 / 3x / 50% / $5k, and the words two..twenty, hundred,
            thousand, million) must appear in the source after the same normalisation. Fill-ins like
            [your number] and URLs are skipped. # ponytail: values only, so "3x" passes when the
            source says "3" anywhere; tighten to value+suffix if that lets real inventions through.
2 emphasis  each **bold** span must be truthful (emphasis.py, TRI-6); the truthful span is suggested.
3 cta       each --cta phrase (repeatable) appears word for word (whitespace and curly quotes normalised).
4 dashes    with --no-dashes, no em or en dash.
Exit 0 clean, 1 with one plain line per problem, 2 when a file can't be read. --json is for Claude only.
"""
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.path.insert(0, str(PLUGIN / "skills" / "_shared"))
sys.path.insert(0, str(HERE))
from win_encoding import ensure_utf8_output  # noqa: E402
from emphasis import tokenize, truthful_span, is_truthful  # noqa: E402

SMALL = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen twenty".split())}
SMALL.pop("zero")
SMALL.pop("one")  # "one CTA", "the one thing": ordinary caption English, not a claim
MULT = {"hundred": 100, "thousand": 1000, "million": 1000000}
NUM = re.compile(r"(?<![\w#])[$£€]?(\d[\d,]*(?:\.\d+)?)(%|x|k|m|b)?(?!\w)", re.I)
SUFFIX = {"k": 1000, "m": 1000000, "b": 1000000000}


def audience_lines(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return [ln for ln in text.splitlines() if not re.match(r"^\s*#{1,6}\s", ln)]


def _fmt(v):
    return ("%f" % v).rstrip("0").rstrip(".")


def numbers(text):
    """{normalised value: as written} for every number in text."""
    text = re.sub(r"\[[^\]]*\]|https?://\S+|www\.\S+", " ", text.replace("**", ""))
    found = {}
    for m in NUM.finditer(text):
        v = float(m.group(1).replace(",", "")) * SUFFIX.get((m.group(2) or "").lower(), 1)
        after = re.match(r"\s+(hundred|thousand|million)\b", text[m.end():], re.I)
        if after:
            v *= MULT[after.group(1).lower()]
        found.setdefault(_fmt(v), m.group(0))
    words = re.findall(r"[a-z]+|[^a-z\s]+", text.lower())
    i = 0
    while i < len(words):
        if words[i] in SMALL or words[i] in MULT:
            j, total, cur = i, 0, 0
            while j < len(words) and (words[j] in SMALL or words[j] in MULT):
                w = words[j]
                if w in SMALL:
                    cur += SMALL[w]
                elif w == "hundred":
                    cur = max(cur, 1) * 100
                else:
                    total, cur = total + max(cur, 1) * MULT[w], 0
                j += 1
            if not (i > 0 and re.fullmatch(r"[\d.,]+", words[i - 1]) and words[i] in MULT):
                found.setdefault(_fmt(total + cur), " ".join(words[i:j]))
            i = j
        else:
            i += 1
    return found


def bold_spans(line):
    """(words, [(start, end), ...]) for each **...** run in one line."""
    words, spans, on, cur = [], [], False, None
    for tok in tokenize(line):
        parts = tok.split("**")
        bold_here = False
        for k, part in enumerate(parts):
            if k:
                on = not on
            if on and re.search(r"\w", part):
                bold_here = True
        idx = len(words)
        words.append(tok.replace("**", ""))
        if bold_here:
            if cur is None:
                cur = [idx, idx + 1]
            else:
                cur[1] = idx + 1
        if cur is not None and (not on or not bold_here):
            spans.append(tuple(cur))
            cur = None
    if cur is not None:
        spans.append(tuple(cur))
    return words, spans


def norm_quotes(s):
    s = s.replace("**", "").translate(str.maketrans("“”‘’", "\"\"''"))
    return re.sub(r"\s+", " ", s).strip()


def problems(caption, source, ctas=(), no_dashes=False):
    lines = audience_lines(caption)
    text = "\n".join(lines)
    out = []
    have = numbers(source)
    for v, shown in numbers(text).items():
        if v not in have:
            out.append(("numbers", f'"{shown}" isn\'t in the transcript or what the client gave. '
                                   f"Remove it or write a fill-in like [your number]."))
    for line in lines:
        words, spans = bold_spans(line)
        for s, e in spans:
            if not is_truthful(words, s, e):
                ts, te = truthful_span(words, s, e)
                out.append(("emphasis", f'The bold on "{" ".join(words[s:e])}" marks half a truth. '
                                        f'Bold "{" ".join(words[ts:te])}" instead.'))
    for cta in ctas or ():
        if norm_quotes(cta) not in norm_quotes(text):
            out.append(("cta", f'"{cta}" from the reel isn\'t in the caption word for word.'))
    if no_dashes:
        n = sum(text.count(d) for d in "—–")
        if n:
            out.append(("dashes", f"The caption has {n} long dash(es). Swap them for a period or comma."))
    return [{"check": c, "message": m} for c, m in out]


def selftest():
    src = "I tried posting more. This doesn't work. My clients got 3x more leads in 30 days."
    cases = [
        ("clean", "Posting more doesn't work. My clients got 3x more leads in 30 days.", None, False, []),
        ("invented 10x", "This gets you 10x more leads.", None, False, ["numbers"]),
        ("ten clients", "I helped ten clients do this.", None, False, ["numbers"]),
        ("one is not a number", "This was the one thing that changed.", None, False, []),
        ("fill-in skipped", "I helped [your number] clients.", None, False, []),
        ("half negation", "Posting more doesn't **work**.", None, False, ["emphasis"]),
        ("whole negation", "Posting more **doesn't work**.", None, False, []),
        ("condition", "It grows only if you **post daily**.", None, False, ["emphasis"]),
        ("unit inside", "You get **3x** more leads.", None, False, []),
        ("unit alone", "**3x**", None, False, []),
        ("contrast", "You need not more posts but **better hooks**.", None, False, ["emphasis"]),
        ("not..but", "You need **not** more posts but better hooks.", None, False, ["emphasis"]),
        ("whole contrast", "**Not more posts but better hooks.**", None, False, []),
        ("cta missing", "Comment GUIDE for it.", ['Comment "HOOKS"'], False, ["cta"]),
        ("cta present", "Comment “HOOKS” for it.", ['Comment "HOOKS"'], False, []),
        ("two ctas, one missing", "Comment HOOKS for it.", ["HOOKS", "The Hook Guide"], False, ["cta"]),
        ("two ctas present", "Comment HOOKS for The Hook Guide.", ["HOOKS", "The Hook Guide"], False, []),
        ("dash off", "Posting more — it doesn't work.", None, False, []),
        ("dash on", "Posting more — it doesn't work.", None, True, ["dashes"]),
        ("heading skipped", "## Option 7\nPosting more doesn't work.", None, False, []),
    ]
    failed = []
    for name, cap, cta, nd, want in cases:
        got = [p["check"] for p in problems(cap, src, cta, nd)]
        if got != want:
            failed.append(f"{name}: wanted {want}, got {got}")
    p = problems("Posting more doesn't **work**.", src)
    if not p or '"doesn\'t work."' not in p[0]["message"]:
        failed.append(f"half negation suggestion: {p}")
    if failed:
        print("SELFTEST FAIL\n" + "\n".join(failed))
        return 1
    print("SELFTEST PASS")
    return 0


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--caption")
    ap.add_argument("--source")
    ap.add_argument("--cta", action="append", default=[])
    ap.add_argument("--no-dashes", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.caption and a.source):
        ap.error("--caption and --source are required")
    try:
        cap = Path(a.caption).read_text(encoding="utf-8")
        src = Path(a.source).read_text(encoding="utf-8")
    except OSError as e:
        print(f"Couldn't read {e.filename}.")
        return 2
    found = problems(cap, src, a.cta, a.no_dashes)
    if a.json:
        print(json.dumps(found, ensure_ascii=False))
    else:
        for p in found:
            print(p["message"])
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
