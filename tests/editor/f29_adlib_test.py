#!/usr/bin/env python3
"""F29: ad-libbed lines stay pickable and repeated mishearings all get fixed.

usage: <editor python> -X utf8 -I tests/editor/f29_adlib_test.py [scratch-dir] [--case NAME]
Prints PASS/FAIL per check; exit 0 = every check passed. Cases: align, notsaid, spoken, diff, mutant.
Uses the synthetic JSON fixture and imports make_board / script_diff directly; no media, runs in seconds.
"""
import argparse, json, sys, tempfile
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPTS = REPO / "plugins" / "editor-superengine" / "skills" / "reel-first-cuts" / "scripts"
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPTS))
import make_board as mb  # noqa: E402
import script_diff as sd  # noqa: E402

FIXTURE = HERE / "fixtures" / "f29"
SCRIPT = FIXTURE / "script-locked.md"
DATA = json.loads((FIXTURE / "words.json").read_text(encoding="utf-8"))
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def anchors(lines, words):
    if hasattr(mb, "take_anchors"):
        return mb.take_anchors(lines, words)
    return sorted((wi, ln["id"], sc) for ln in lines for wi, sc in mb.find_anchors(ln["anchor"], words))


def missing(lines, words):
    found = {lid for _, lid, _ in anchors(lines, words)}
    return [ln["id"] for ln in lines if ln["id"] not in found]


def case_align(S, a):
    lines, words = mb.script_lines(SCRIPT), DATA["board_words"]
    placed = getattr(mb, "aligned_starts", lambda *_: {})(lines, words)
    found = {ln["id"] for ln in lines if mb.find_anchors(ln["anchor"], words)} | set(placed)
    ck("align: all 20 script lines are placed (20/20)", len(lines) == len(found) == 20,
       [ln["id"] for ln in lines if ln["id"] not in found])
    for lid, text in (("L01", "Grab"), ("L10", "Bronze"), ("L18", "Nearby")):
        wi = placed.get(lid, (-1, 0))[0]
        ck("align: %s starts at %s" % (lid, text), wi >= 0 and words[wi]["word"] == text
           and (lid != "L01" or wi == 0), (wi, words[wi]["word"]))
    anc = anchors(lines, words)
    ck("align: main's anchors contain each line exactly once in script order",
       [lid for _, lid, _ in anc] == ["L%02d" % i for i in range(1, 21)], anc)
    extra = getattr(mb, "spoken_only", lambda *_: None)(lines, words, anc)
    ck("align: the full script produces no spoken-only lines", extra == [], extra)
    original = [(wi, ln["id"], sc) for ln in lines for wi, sc in mb.find_anchors(ln["anchor"], words)]
    ck("align: existing anchors are unchanged", all(hit in anc for hit in original), anc)


def changed_lines(S, name, texts):
    path = S / ("f29-" + name + ".md")
    path.write_bytes(("\n".join(texts) + "\n").encode("utf-8"))
    return mb.script_lines(path)


def case_notsaid(S, a):
    texts = [ln["text"] for ln in mb.script_lines(SCRIPT)]
    texts.insert(9, "Quartz dragons guard invisible staircases beneath frozen oceans.")
    lines = changed_lines(S, "notsaid", texts)
    absent = missing(lines, DATA["board_words"])
    ck("notsaid: only the invented line has no anchor; all 20 spoken lines remain", absent == ["L10"], absent)
    html = (SCRIPTS.parent / "boards" / "cut-board" / "index.html").read_text(encoding="utf-8")
    ck("notsaid: board text says 'not said: no take has this line'",
       "not said: no take has this line" in html and "no attempt found in any take" not in html)


def case_spoken(S, a):
    texts = [ln["text"] for ln in mb.script_lines(SCRIPT)]
    del texts[6]
    lines = changed_lines(S, "spoken", texts)
    words = DATA["board_words"]
    absent = missing(lines, words)
    ck("spoken: all 19 remaining script lines are anchored", len(lines) == 19 and not absent, absent)
    takes = {"1": {"words": words, "anchors": anchors(lines, words)}}
    if hasattr(mb, "add_spoken_lines"):
        mb.add_spoken_lines(lines, takes)
    extras = [ln for ln in lines if ln.get("spoken_only")]
    ck("spoken: the removed line becomes S01 with transcript text and label",
       len(extras) == 1 and all(extras[0].get(k) == v for k, v in
                              dict(id="S01", text="Bells mark noon.", label="Bells mark noon", anchor="Bells mark noon.").items()),
       extras)
    anc = takes["1"]["anchors"]
    ids = [lid for _, lid, _ in anc]
    ck("spoken: the extra anchor is between L06 and L07 at word 55 with score 0.0",
       ids == ["L%02d" % i for i in range(1, 7)] + ["S01"] + ["L%02d" % i for i in range(7, 20)]
       and (55, "S01", 0.0) in anc, anc)
    ck("spoken: the extra line is inserted between the script lines on the board",
       [ln["id"] for ln in lines] == ids, [ln["id"] for ln in lines])

    # an ad-lib sentence right before an ad-libbed (aligned) line is its own line, not the aligned line's start
    texts = [ln["text"] for ln in mb.script_lines(SCRIPT)]
    del texts[16]
    lines = changed_lines(S, "adlib-before-aligned", texts)
    takes = {"1": {"words": words, "anchors": anchors(lines, words)}}
    getattr(mb, "add_spoken_lines", lambda *_: None)(lines, takes)
    extras = [ln["text"] for ln in lines if ln.get("spoken_only")]
    start = {lid: words[wi]["word"] for wi, lid, _ in takes["1"]["anchors"]}
    ck("spoken: a sentence said before an ad-libbed line is listed on its own and the line still starts at Nearby",
       extras == ["Lanterns illuminate arched masonry nightly."] and start.get("L17") == "Nearby",
       (extras, start.get("L17")))
    # a script that covers only part of the take lists no spoken-only lines outside it (boards_test's window fixtures)
    texts = [ln["text"] for ln in mb.script_lines(SCRIPT)][4:8]
    lines = changed_lines(S, "window", texts)
    takes = {"1": {"words": words, "anchors": anchors(lines, words)},
             "2": {"words": words, "anchors": anchors(lines, words)}}
    getattr(mb, "add_spoken_lines", lambda *_: None)(lines, takes)
    ck("spoken: a script window of 4 lines in a 2-take board adds no spoken-only line",
       [ln["id"] for ln in lines] == ["L01", "L02", "L03", "L04"], [ln["id"] for ln in lines])


def velorakit_fixes():
    result = sd.diff(DATA["heard_words"], sd.script_words(SCRIPT.read_text(encoding="utf-8")), set(), set())
    return [(f["at"], f["new"]) for f in result[1] if f["heard"] == "Velorakit"]


def case_diff(S, a):
    fixes = velorakit_fixes()
    ck("diff: all three Velorakit occurrences get the same Velora Kit fix",
       fixes == [(3, "Velora Kit"), (21, "Velora Kit"), (171, "Velora Kit")], fixes)
    words = [{"id": str(i), "word": w} for i, w in enumerate("we use Velorakit then Velorakit".split())]
    script = sd.script_words("We use Velora Kit then Velora Kit")
    _, fixes, _, kept = sd.diff(words, script, set(), {"velorakit"})
    ck("diff: never-listed occurrences stay kept", not fixes and [f["at"] for f in kept] == [2, 4], (fixes, kept))
    _, fixes, review, _ = sd.diff(DATA["heard_words"], sd.script_words(SCRIPT.read_text(encoding="utf-8")), set(), set())
    ck("diff: fixes stay sorted and the partly resolved review is retained",
       [f["at"] for f in fixes] == sorted(f["at"] for f in fixes) and any(3 in r["at"] for r in review), review)
    ck("diff: a reworded run over 3 words still goes to REVIEW as a longer rewrite, unchanged",
       any(r["at"] == [74, 75, 76] and r["why"] == "a longer rewrite" for r in review)
       and not any(f["at"] in (74, 75, 76) for f in fixes), review)


def case_mutant(S, a):
    lines, words = mb.script_lines(SCRIPT), DATA["board_words"]
    with patch.object(mb, "aligned_starts", return_value={}, create=True):
        absent = missing(lines, words)
    ck("mutant: disabling alignment exposes L01/L10/L18", absent == ["L01", "L10", "L18"], absent)
    with patch.object(sd, "propagate_fixes", return_value=None, create=True):
        fixes = velorakit_fixes()
    ck("mutant: disabling propagation leaves only index 21 fixed", fixes == [(21, "Velora Kit")], fixes)


CASES = {"align": case_align, "notsaid": case_notsaid, "spoken": case_spoken, "diff": case_diff, "mutant": case_mutant}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch", nargs="?")
    ap.add_argument("--case", choices=CASES)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="f29-") as scratch:
        S = Path(a.scratch or scratch).resolve()
        S.mkdir(parents=True, exist_ok=True)
        for name, fn in CASES.items():
            if not a.case or a.case == name:
                fn(S, a)
        print("%d check(s) failed: %s" % (len(fails), ", ".join(fails)) if fails else "all checks passed")
        return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
