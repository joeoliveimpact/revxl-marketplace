"""Rank suggested fixes only: layout_check's hard coverage block still stands.

This library is deliberately not a discoverable phase check. It never grants
permission to render covered captions or overrides the layout check.
"""
import re

FUNCTION_WORDS = set("a an the of for to in on at by with from and or but as if so it its is was are were be been this that these those i you we they".split())


def verdict(word, sentence, covered_pct, neighbours=None):
    """Return pass/escalate for a proposed fix, using coverage in 0..100 units.

    word can be text or {text, key, key_letters}. neighbours is a sequence of
    adjacent coverage percentages, or {covered_pct} objects.
    """
    data = word if isinstance(word, dict) else {"text": word}
    token = re.sub(r"^\W+|\W+$", "", str(data.get("text", data.get("word", ""))).lower())
    # 1. Function words can be expendable; never assume content words are.
    function = token in FUNCTION_WORDS
    # 2. Removing exactly one instance must leave a readable phrase with at
    # least two content words. This is a conservative proxy for judgement.
    tokens = re.findall(r"\b[\w']+\b", sentence.lower())
    if token in tokens:
        tokens.remove(token)
        reads = sum(t not in FUNCTION_WORDS for t in tokens) >= 2
    else:
        reads = False
    # 3. Severe lost meaning, adjacent losses, and damaged key letters rank
    # first for repair, even when the token is a function word.
    adjacent = [n.get("covered_pct", 0) if isinstance(n, dict) else n for n in (neighbours or [])]
    if (covered_pct >= 50 and any(n >= 50 for n in adjacent)) or (
            covered_pct >= 65 and (data.get("key") or data.get("key_letters"))):
        return "escalate"
    if covered_pct < 65:
        return "pass"
    if function and reads:
        return "pass"
    return "escalate" if covered_pct >= 80 or not reads else "pass"
