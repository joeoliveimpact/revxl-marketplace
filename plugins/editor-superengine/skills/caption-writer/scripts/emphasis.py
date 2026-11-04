"""TRI-6: an emphasised span is the smallest truthful run of words (stdlib only, no I/O).

The one copy of this rule. caption-writer's check_caption.py imports it, and so does the
reel-captions word-mark picker, so bold in a caption and a punched word burned into the video
follow the same rule. Keep this API stable:

    tokenize(text) -> list[str]
        Words split on whitespace (and em/en dashes). Punctuation stays attached ("work."),
        contractions stay whole ("doesn't"). Call it per line: a line break is not seen as a
        clause boundary once lines are joined.
    truthful_span(words, start, end) -> tuple[int, int]
        Half-open word indices. Returns the smallest span that contains [start, end) and is
        truthful. Repeats these expansions until nothing changes:
          negation   a negation within 2 words before the span (not, no, never, without,
                     any n't word, ...) joins the span: "doesn't work", never "work".
          condition  a condition word earlier in the same clause (if, unless, only, until,
                     except, when) pulls the span back to it: "only if you post daily".
          numbers    a number takes its unit and a unit takes its number ("30 days",
                     "ten clients"), plus a currency sign or qualifier right before the number
                     (over, under, up to, only, about, ...): "up to $5k".
          contrast   a contrast word in the span, right after it, or up to 2 words before it
                     (but, than, instead, vs, versus, rather, or a "not" with a "but" later in
                     its clause) widens the span to the whole clause on both sides:
                     "not more posts but better hooks".
        Expansions never cross clause punctuation (. , ; : ! ?).
    is_truthful(words, start, end) -> bool
        True when truthful_span returns the span unchanged.
"""
import re

NEGATIONS = {"not", "no", "never", "none", "nobody", "nothing", "nowhere", "neither", "nor",
             "without", "cannot", "hardly", "barely"}
_NT = re.compile(r"^(?:ca|do|does|did|is|are|was|were|wo|should|could|would|have|has|had|ai|must|need)nt$")
CONDITIONS = {"if", "unless", "only", "until", "except", "when"}
CONTRASTS = {"but", "than", "instead", "vs", "versus", "rather"}
QUALIFIERS = {"over", "under", "only", "about", "around", "nearly", "almost", "roughly", "just"}
PAIR_QUALIFIERS = {("up", "to"), ("at", "least"), ("at", "most")}
CURRENCY = {"$", "£", "€"}
NUMBER_WORDS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
                "eighteen", "nineteen", "twenty", "hundred", "thousand", "million"}
UNITS = {"x", "%", "k", "percent", "times", "hundred", "thousand", "million", "billion",
         "second", "seconds", "sec", "secs", "minute", "minutes", "min", "mins", "hour", "hours",
         "hr", "hrs", "day", "days", "week", "weeks", "month", "months", "year", "years",
         "dollars", "bucks", "usd", "followers", "views", "clients", "customers", "leads",
         "sales", "calls", "reels", "posts", "subscribers", "likes", "comments", "people",
         "students", "members", "pounds", "lbs", "kg", "steps", "miles", "km", "words"}
_NUM = re.compile(r"^[$£€]?\d[\d,]*(?:\.\d+)?(?:%|x|k|m|b)?$")
_CLAUSE_END = ".,;:!?…"


def tokenize(text):
    return [w for w in re.split(r"[\s—–]+", text) if w]


def _bare(word):
    w = word.replace("**", "").replace("’", "'").lower()
    return w.strip("\"'()[]{}*_.,;:!?“”‘…")


def _ends_clause(word):
    w = word.replace("**", "").rstrip("\"')]}*_”’")
    return bool(w) and w[-1] in _CLAUSE_END and _bare(word) != "vs"


def _is_neg(b):
    return b in NEGATIONS or b.endswith("n't") or bool(_NT.match(b))


def _is_num(b):
    return bool(_NUM.match(b)) or b in NUMBER_WORDS


def _left_ok(words, i):
    """True when word i-1 is in the same clause as word i."""
    return i > 0 and not _ends_clause(words[i - 1])


def _clause_start(words, i):
    while _left_ok(words, i):
        i -= 1
    return i


def _clause_end(words, i):
    """Half-open end of the clause holding word i-1."""
    while i < len(words) and not _ends_clause(words[i - 1]):
        i += 1
    return i


def truthful_span(words, start, end):
    if not (0 <= start < end <= len(words)):
        raise ValueError("span must satisfy 0 <= start < end <= len(words)")
    b = [_bare(w) for w in words]
    s, e = start, end
    while True:
        s0, e0 = s, e
        # negation within 2 words before, same clause
        i = s
        for _ in range(2):
            if not _left_ok(words, i):
                break
            i -= 1
            if _is_neg(b[i]):
                s = i
        # condition word earlier in the clause
        for j in range(_clause_start(words, s), s):
            if b[j] in CONDITIONS:
                s = j
                break
        # numbers and units
        for j in range(s, e):
            if _is_num(b[j]) and j + 1 == e and e < len(words) and not _ends_clause(words[j]) \
                    and b[e] in UNITS:
                e += 1
            if b[j] in UNITS and j == s and _left_ok(words, s) and _is_num(b[s - 1]):
                s -= 1
        for j in range(s, e):
            if _is_num(b[j]):
                if j == s and _left_ok(words, s) and (b[s - 1] in QUALIFIERS or b[s - 1] in CURRENCY):
                    s -= 1
                elif j == s and s >= 2 and _left_ok(words, s) and _left_ok(words, s - 1) \
                        and (b[s - 2], b[s - 1]) in PAIR_QUALIFIERS:
                    s -= 2
                break
        # contrast
        near = list(range(s, e))
        if e < len(words) and not _ends_clause(words[e - 1]):
            near.append(e)
        i = s
        for _ in range(2):
            if not _left_ok(words, i):
                break
            i -= 1
            near.append(i)
        if any(b[j] in CONTRASTS or (b[j] == "not" and "but" in b[j + 1:_clause_end(words, j + 1)])
               for j in near):
            s, e = _clause_start(words, s), _clause_end(words, e)
        if (s, e) == (s0, e0):
            return s, e


def is_truthful(words, start, end):
    return truthful_span(words, start, end) == (start, end)
