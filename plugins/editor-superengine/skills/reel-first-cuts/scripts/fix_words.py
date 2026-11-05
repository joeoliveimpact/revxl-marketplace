#!/usr/bin/env python3
# Ported from Shorts Studio, scripts/fix_words.py. MIT License, Copyright (c) 2026 Claude Video Studio contributors
# (full text in LICENSES/NOTICE).
# changed: reads an edit map or a tx.json (`word` or `text`); fixes come from <paths.editor>/word-fixes.json or --map
# (no --fix); case-insensitive matching; phrase fixes (VES-8); --at by list index; an edit map's word_list_hash is
# recomputed and validated; one <name>.prev kept; --cta-check; UTF-8 output; --merge joins N words into 1.
"""fix_words.py: correct words the speech model heard wrong (names, products, jargon) before they become captions.

usage: python fix_words.py work/edit_map.cut.json [--map editor/word-fixes.json] [--at '{"175": "agentic"}']
                          [--merge '{"40-41": "Datadog"}']
       python fix_words.py work/edit_map.cut.json --cta-check

The map (default <paths.editor>/word-fixes.json, from editor/editor.config.json; else editor/word-fixes.json):
  {"fixes": {"old": "new"}, "phrases": {"<context words> <old>": "<new>"}, "cta": ["KEYWORD", ...]}
fixes    replace a word everywhere (matched without punctuation, case-insensitive).
phrases  replace only the LAST word of a matching word sequence: "comment guy": "GUIDE" turns "guy." into
         "GUIDE." only right after "comment".
--at     replaces one word by its list index (from 0), for one-off mistakes.
--merge  joins consecutive words "first-last" (list indexes, inclusive) into one word: "Data Dog" -> "Datadog".
         It keeps the first word's id, start and other fields, takes the last word's end, the first word's leading
         and the last word's trailing punctuation, and renumbers an `i` field. All indexes in one run (--at and
         --merge) refer to the file as read; a merge wins over --at and fixes on its words. A span out of range,
         under 2 words or overlapping another exits 2 with nothing written.
Punctuation that was on the old word stays on the new one. The file is updated in place and the previous one is
kept as <name>.prev. An edit map gets its word_list_hash recomputed, so validate() still passes.
--cta-check changes nothing: it prints one line per cta keyword and exits 1 when any is missing from the words.
"""
import argparse, json, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402


def core(t):
    return re.sub(r"^[^\w']+|[^\w']+$", "", t)


def key(w):
    return "word" if "word" in w else "text"


def at_seq(cores, seq):
    """Start indexes where the word sequence `seq` (lower-case cores) appears in `cores`."""
    n = len(seq)
    return [i for i in range(len(cores) - n + 1) if n and cores[i:i + n] == seq]


def fix(words, fixes, phrases, at):
    """Returns how many words changed. Precedence per word: --at, then a phrase, then a fix."""
    cores = [core(w[key(w)]).lower() for w in words]
    want = {}
    for ph, new in phrases.items():
        seq = [core(x).lower() for x in ph.split()]
        for i in at_seq(cores, seq):
            want.setdefault(i + len(seq) - 1, new)
    fixes = {core(k).lower(): v for k, v in fixes.items()}
    n = 0
    for i, w in enumerate(words):
        t = w[key(w)]
        c = core(t)
        new = at.get(i) or want.get(i) or fixes.get(c.lower())
        if new and new != c:
            w[key(w)] = t.replace(c, new, 1) if c else new
            n += 1
    return n


def merge(words, spans):
    """Joins each span {(first, last): new} of consecutive words into one word, in place. Returns how many spans were
    merged; raises ValueError (nothing changed) on a span out of range, under 2 words, or overlapping another."""
    taken = set()
    for a, b in spans:
        if not 0 <= a < b < len(words) or taken & set(range(a, b + 1)):
            raise ValueError("bad span %d-%d for %d words" % (a, b, len(words)))
        taken |= set(range(a, b + 1))
    for (a, b), new in sorted(spans.items(), reverse=True):
        head = re.match(r"[^\w']*", words[a][key(words[a])]).group()
        tail = re.search(r"[^\w']*$", words[b][key(words[b])]).group()
        words[a][key(words[a])] = head + new + tail
        words[a]["end"] = words[b]["end"]
        del words[a + 1:b + 1]
    if spans:
        for k, w in enumerate(words):
            if "i" in w:
                w["i"] = k
    return len(spans)


def missing_cta(words, cta):
    cores = [core(w[key(w)]).lower() for w in words]
    return [k for k in cta if not at_seq(cores, [core(x).lower() for x in str(k).split()])]


def default_map():
    return Path.cwd() / ((rt.read_config().get("paths") or {}).get("editor") or "editor") / "word-fixes.json"


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Fix misheard words in an edit map or tx.json.")
    ap.add_argument("words")
    ap.add_argument("--map", help="word-fixes.json (default <paths.editor>/word-fixes.json)")
    ap.add_argument("--at", default="{}", help='one word by list index, e.g. \'{"175": "agentic"}\'')
    ap.add_argument("--merge", default="{}", help='consecutive words into one, e.g. \'{"40-41": "Datadog"}\'')
    ap.add_argument("--cta-check", action="store_true", help="check every cta keyword is present; change nothing")
    a = ap.parse_args()

    path = Path(a.words)
    doc = json.loads(path.read_text(encoding="utf-8"))
    words = doc["words"] if isinstance(doc, dict) else doc
    mp = Path(a.map) if a.map else default_map()
    fm = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    if a.map and not mp.exists():
        print("no such map: %s" % mp, file=sys.stderr)
        return 2

    if a.cta_check:
        cta = fm.get("cta") or []
        gone = missing_cta(words, cta)
        for k in cta:
            print(("CTA missing: %s" if k in gone else "CTA present: %s") % k)
        if not cta:
            print("no cta keywords in %s" % mp)
        return 1 if gone else 0

    at = {int(k): v for k, v in json.loads(a.at).items()}
    try:
        spans = {tuple(int(x) for x in k.split("-", 1)): v for k, v in json.loads(a.merge).items()}
        n = fix(words, fm.get("fixes") or {}, fm.get("phrases") or {}, at) + merge(words, spans)
    except ValueError as e:
        print("--merge: %s; nothing written" % e, file=sys.stderr)
        return 2
    if n:
        if isinstance(doc, dict) and "word_list_hash" in doc:
            import build_edit_map as bem   # numpy: the editor's Python
            doc["word_list_hash"] = bem.word_list_hash(bem.board_sequence(doc))
            errs = bem.validate(doc)
            if errs:
                print("the fixed edit map does not validate, nothing written:\n  " + "\n  ".join(errs[:10]),
                      file=sys.stderr)
                return 2
        shutil.copyfile(path, path.with_name(path.name + ".prev"))
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("fixed %d word(s) in %s" % (n, path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
