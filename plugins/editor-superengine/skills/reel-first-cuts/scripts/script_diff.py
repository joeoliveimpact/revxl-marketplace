#!/usr/bin/env python3
"""script_diff.py: line the client's script up against the transcript and fix brand names the speech model misheard.

usage: python script_diff.py <script.txt> work/edit_map.json [--map editor/word-fixes.json] [--never "Cling,Veo"]

Both texts are split into words and lined up with difflib (case and edge punctuation ignored).
- Under 25 % of the shorter text lines up, the script is probably the wrong one: it warns, changes nothing, exits 1.
- A small replaced run (up to 3 heard words against up to 3 script words) is fixed when the script words are
  brand-like and sound close to what was heard. Brand-like = a capital mid-sentence (never "I"), a capital inside the
  word (ChatGPT), a digit, or a word word-fixes.json already knows (a fixes or phrases value, a cta keyword).
  Same-length runs are fixed word by word. A run with fewer heard words gets the extra script words joined onto its
  last heard word. Up to 3 heard words for 1 script word ("Data Dog" for "Datadog") are merged into one word; any
  other run with more heard words than script words goes to REVIEW.
- Every other difference goes to the REVIEW list. A heard word on the --never list (the client's) is never changed.
Fixes go through fix_words.py --at / --merge (word index), so an edit map gets its word_list_hash recomputed and
validated and a .prev copy is kept. Writes script_diff.json next to the edit map (work/script_diff.json).
Exit 0 = done, 1 = low-match warning (nothing changed), 2 = bad input or fix_words refused the fix.
"""
import argparse, difflib, json, os, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import runtime as rt  # noqa: E402
import fix_words as fw  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

MIN_MATCH = 0.25   # share of the shorter text that must line up before anything is fixed
MAX_RUN = 3        # longest replaced run (heard words, script words) that may be fixed
CLOSE = 0.7        # sound-alike ratio a fix needs
NOT_BRAND = {"i", "i'm", "i'll", "i've", "i'd"}


def script_words(text):
    """[(word, brand-like by its shape)]. A new line, or a word ending in . ! ? or an ellipsis, starts a sentence."""
    out = []
    for line in text.splitlines():
        start = True
        for raw in line.split():
            c = fw.core(raw)
            if not c:
                continue
            caps = c[0].isupper() and not start and c.lower() not in NOT_BRAND
            out.append((c, bool(caps or re.search(r"\d", c) or re.search(r"[a-z][A-Z]", c))))
            start = raw.rstrip("\"')]”’").endswith((".", "!", "?", "…"))
    return out


def sound(t):
    """Rough sound key: letters and digits only, lower case, doubled letters once ("Datadogg" = "Datadog")."""
    return re.sub(r"(.)\1+", r"\1", re.sub(r"[^a-z0-9]", "", t.lower()))


def close(a, b):
    return difflib.SequenceMatcher(None, sound(a), sound(b)).ratio() >= CLOSE


def known_words(fm):
    vals = list((fm.get("fixes") or {}).values()) + list((fm.get("phrases") or {}).values())
    vals += [x for k in fm.get("cta") or [] for x in str(k).split()]
    return {fw.core(str(v)).lower() for v in vals if fw.core(str(v))}


def diff(words, script, known, never):
    """(match share, fixes, review, never_kept). Fixes are {at, id, heard, new}; `at` = index in the word list.
    A merge fix also carries `merge`: the indexes of the heard words it joins into one (`at` = the first)."""
    idx = [i for i, w in enumerate(words) if fw.core(w[fw.key(w)])]
    heard = [fw.core(words[i][fw.key(words[i])]) for i in idx]
    sm = difflib.SequenceMatcher(None, [h.lower() for h in heard], [c.lower() for c, _ in script], autojunk=False)
    match = sum(b.size for b in sm.get_matching_blocks()) / max(1, min(len(heard), len(script)))
    fixes, review, kept = [], [], []
    if match < MIN_MATCH:
        return match, fixes, review, kept
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        h, s = heard[i1:i2], [c for c, _ in script[j1:j2]]
        brand = [shape or c.lower() in known for c, shape in script[j1:j2]]
        item = dict(at=idx[i1:i2], heard=" ".join(h), script=" ".join(s))
        if op != "replace":
            review.append(dict(item, why="said, not in the script" if h else "in the script, not said"))
            continue
        if len(h) > MAX_RUN or len(s) > MAX_RUN:
            review.append(dict(item, why="a longer rewrite"))
            continue
        if len(s) == 1 < len(h) and brand[0] and close("".join(h), s[0]) and idx[i2 - 1] - idx[i1] == len(h) - 1:
            rec = dict(at=idx[i1], merge=idx[i1:i2], id=words[idx[i1]].get("id"), heard=" ".join(h), new=s[0])
            (kept if any(x.lower() in never for x in h) else fixes).append(rec)
            continue
        if len(h) == len(s):
            todo = [(k, s[k]) for k in range(len(h)) if brand[k] and close(h[k], s[k])]
        elif len(h) < len(s) and all(brand) and close("".join(h), "".join(s)):
            todo = [(k, s[k]) for k in range(len(h) - 1)] + [(len(h) - 1, " ".join(s[len(h) - 1:]))]
        else:
            todo = []
        for k, new in todo:
            if new == h[k]:   # a join an earlier run already made ("Eleven Labs" heard as one word)
                continue
            i = idx[i1 + k]
            rec = dict(at=i, id=words[i].get("id"), heard=h[k], new=new)
            (kept if h[k].lower() in never else fixes).append(rec)
        if len(todo) < len(h):
            if len(h) > len(s) and all(brand) and close("".join(h), "".join(s)):
                why = "a brand heard as more words than the script has; only N words into 1 are merged, fix it by hand"
            else:
                why = "not a brand-like word that sounds close"
            review.append(dict(item, why=why))
    return match, fixes, review, kept


def apply(em, fixes):
    """Runs fix_words.py --at / --merge on the edit map. An empty map file keeps word-fixes.json out of this run, so the
    only changes are the ones listed here (word-fixes.json is applied by fix_words.py on its own)."""
    fd, empty = tempfile.mkstemp(suffix=".json")
    os.write(fd, b"{}")
    os.close(fd)
    try:
        at = json.dumps({str(f["at"]): f["new"] for f in fixes if "merge" not in f}, ensure_ascii=False)
        mg = json.dumps({"%d-%d" % (f["merge"][0], f["merge"][-1]): f["new"] for f in fixes if "merge" in f},
                        ensure_ascii=False)
        return subprocess.run([sys.executable, "-X", "utf8", "-I", str(HERE / "fix_words.py"), str(em), "--map", empty,
                               "--at", at, "--merge", mg], env=rt.python_env(), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=300)
    finally:
        os.unlink(empty)


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Fix misheard brand names in an edit map from the client's script.")
    ap.add_argument("script", help="the client's script, a text file")
    ap.add_argument("edit_map", help="work/edit_map.json (or edit_map.cut.json)")
    ap.add_argument("--map", help="word-fixes.json (default <paths.editor>/word-fixes.json)")
    ap.add_argument("--never", default="", help="comma-separated heard words the client never wants changed")
    a = ap.parse_args()

    em = Path(a.edit_map)
    doc = json.loads(em.read_text(encoding="utf-8"))
    words = doc["words"] if isinstance(doc, dict) else doc
    mp = Path(a.map) if a.map else fw.default_map()
    if a.map and not mp.exists():
        print("no such map: %s" % mp, file=sys.stderr)
        return 2
    fm = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    never = {fw.core(x).lower() for x in a.never.split(",") if fw.core(x)}
    script = script_words(Path(a.script).read_text(encoding="utf-8"))

    match, fixes, review, kept = diff(words, script, known_words(fm), never)
    out = dict(script=str(a.script), edit_map=str(em), match=round(match, 3), warn=None, fixes=fixes, review=review,
               never_kept=kept)
    rc = 0
    if match < MIN_MATCH:
        out["warn"] = ("only %d%% of the script lines up with what was said. Is this the right script? Nothing was "
                       "changed." % round(match * 100))
        rc = 1
    elif fixes:
        p = apply(em, fixes)
        out["applied"] = p.returncode == 0
        if p.returncode:
            out["error"] = (p.stderr or p.stdout).strip()[-800:]
            rc = 2

    dest = em.parent / "script_diff.json"
    dest.write_bytes(json.dumps(out, ensure_ascii=False, indent=1).encode("utf-8"))
    print("script match: %d%%" % round(match * 100))
    if out["warn"]:
        print("WARNING: " + out["warn"])
    for f in fixes:
        where = "words %d-%d" % (f["merge"][0], f["merge"][-1]) if "merge" in f else "word %d" % f["at"]
        print("fix: %s %r -> %r%s" % (where, f["heard"], f["new"], "" if out.get("applied") else " (NOT applied)"))
    for f in kept:
        print("never list, kept: word %d %r (script says %r)" % (f["at"], f["heard"], f["new"]))
    for r in review:
        print("REVIEW: heard %r / script %r (%s)" % (r["heard"], r["script"], r["why"]))
    if out.get("error"):
        print("fix_words refused, nothing written:\n" + out["error"], file=sys.stderr)
    print("wrote %s" % dest)
    return rc


if __name__ == "__main__":
    sys.exit(main())
