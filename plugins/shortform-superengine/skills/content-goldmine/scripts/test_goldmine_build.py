# Self-check for the CTA rule. Run: python test_goldmine_build.py (prints OK or fails loudly).
# Cases come from the 08.28 hand review of 3,405 captions.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from goldmine_build import detect_cta

CASES = [
    ('Comment "STACK" and I will send it', (True, "STACK", "quoted")),
    ("Comment «COOK» for the recipe", (True, "COOK", "quoted")),
    ('Comment "Now" for the link', (True, "Now", "quoted")),          # quoted beats the stop list
    ("Comment **HQ** below", (True, "HQ", "bold")),
    ("Comment MIKA for AI tools", (True, "MIKA", "bare_caps")),        # non-greedy filler
    ("Comment — GUIDE for the link", (True, "GUIDE", "bare_caps")),
    ("Comment Bottleneck below and I'll send it", (True, "Bottleneck", "bare_below")),
    ("Comment Cowork for my free starter guide", (True, "Cowork", "bare_word_payoff")),
    ("Comment Cowork for fun", (False, None, None)),                  # no payoff word
    ("comment below if you agree", (False, None, None)),              # generic ask
    ('Dm me "Closer" for the link', (False, None, None)),             # dm is not an anchor
    ("Comment AI and I'll send it", (False, None, None)),             # stop word, known miss
    ("", (False, None, None)),
]

bad = [(c, want, detect_cta(c)) for c, want in CASES if detect_cta(c) != want]
for c, want, got in bad:
    print("FAIL %r: want %s, got %s" % (c, want, got))
assert not bad, "%d CTA cases failed" % len(bad)
print("OK %d CTA cases" % len(CASES))
