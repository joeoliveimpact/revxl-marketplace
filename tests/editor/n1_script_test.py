#!/usr/bin/env python3
"""N1.3 check for reel-first-cuts' script check (script_diff.py): brand names the speech model misheard get fixed
from the client's script, a wrong script warns and changes nothing, a word on the client's never list stays.
H-N1-5: a brand heard as 2-3 words for 1 script word is merged into one word by fix_words.py --merge (port 1).

usage: python tests/editor/n1_script_test.py [scratch-dir] [--case NAME]
Prints PASS/FAIL per check; exit 0 = every check passed. Cases: fix, merge, wrong, never (all by default, a few
seconds). Run it with the editor's venv Python (EDITOR_SE_HOME's state): it imports build_edit_map (numpy) to build
and check edit maps, like ports_test.py. script_diff.py and fix_words.py run as `python -X utf8 -I` under the same
venv Python. Fixtures are synthetic JSON built here; no media.
"""
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPTS = REPO / "plugins" / "editor-superengine" / "skills" / "reel-first-cuts" / "scripts"
sys.path.insert(0, str(REPO / "plugins" / "editor-superengine" / "skills" / "_shared"))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

ENV = rt.python_env()
PY = rt.tool("python") if Path(rt.tool("python")).exists() else sys.executable
fails = []

# The take as heard: "Alderstone" misheard once as one word and once as two (merged, H-N1-5), "Brindle" as "Brindel",
# "trailway" (a word word-fixes.json knows) as "trailaway", and a plain wording change (clip / video) that must go to
# REVIEW. Then one line per gate: than/then (sounds close, not brand-like), Nema/Trailway (brand-like, doesn't sound
# close), a 4:4 run of close brands (over the 3:3 limit), now/Know (capital only because it starts a sentence),
# MapGlow at a sentence start (CamelCase), vexa3 in lower case (digit), Meadowlabs heard as one word (join), and a
# 3:3 run of close brands (fixed word by word).
HEARD = ("so today I tried Alderston and Brindel to make a clip. then I used trailaway to make a clip. "
         "next we open Alder Stone again. it was better than ever. we also tried Nema today. "
         "the four we tested were Nemma Brindlle Tovvi Rillo in May. now we wrap up. mapglo wrote the captions. "
         "the shots came from vexa for free. music came out of Meadowlabs as usual. "
         "we compared Nemma Brindlle Tovvi last week.")
SCRIPT = ("So today I tried Alderstone and Brindle to make a clip.\nThen I used trailway to make a video.\n"
          "Next we open Alderstone again.\nIt was better then ever.\nWe also tried Trailway today.\n"
          "The four we tested were Nema Brindle Tovi Rilo in May.\nKnow we wrap up.\nMapGlow wrote the captions.\n"
          "The shots came from vexa3 for free.\nMusic came out of Meadow Labs as usual.\n"
          "We compared Nema Brindle Tovi last week.\n")
# Under 25 % match, but "I tried Alderstone and" lines up with the take: without the guard, Alderston would be fixed.
WRONG = ("Bake the bread at two hundred degrees for an hour.\nLet it cool on a Rack, then slice it thin.\n"
         "I tried Alderstone and butter on top.\nServe it warm with soup and salt.\n")
FIXES = {"fixes": {"trailweigh": "trailway"}, "phrases": {}, "cta": []}
# F29: a fix applies to every occurrence of the heard word, and one run fixes what a second run would (Rillo)
FIXED = [4, 6, 14, 22, 40, 41, 42, 43, 50, 58, 65, 70, 71, 72]   # fix records' `at`, by index in the edit map as read


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def bem():
    sys.path.insert(0, str(SCRIPTS))
    import build_edit_map   # numpy: the editor's Python
    return build_edit_map


def edit_map(text, gaps=None, silences=()):
    """A valid S3-shape edit map: one word per token, 0.3 s long, 0.35 s apart (gaps = {index: extra seconds})."""
    words, t = [], 0.5
    for k, w in enumerate(text.split()):
        t += (gaps or {}).get(k, 0.0)
        words.append({"id": "w_%04d" % k, "word": " " + w, "start": round(t, 3), "end": round(t + 0.3, 3),
                      "parakeet_start": round(t, 3), "status": "aligned", "score_min": -1.0})
        t += 0.35
    m = {"version": 1, "duration": words[-1]["end"] + 1.0, "audio_sha256": "0" * 64,
         "calibration": {"threshold_db": -48.0}, "word_list_hash": None, "events": [],
         "silences": [{"id": "s_%04d" % k, "start": s, "end": e} for k, (s, e) in enumerate(silences)], "words": words}
    b = bem()
    m["word_list_hash"] = b.word_list_hash(b.board_sequence(m))
    return m


def fresh(S, name):
    d = S / name
    shutil.rmtree(d, ignore_errors=True)
    (d / "work").mkdir(parents=True)
    (d / "editor").mkdir()
    (d / "editor" / "word-fixes.json").write_bytes(json.dumps(FIXES).encode("utf-8"))
    (d / "script.txt").write_bytes(SCRIPT.encode("utf-8"))
    (d / "wrong.txt").write_bytes(WRONG.encode("utf-8"))
    em = d / "work" / "edit_map.json"
    em.write_bytes(json.dumps(edit_map(HEARD), indent=1).encode("utf-8"))
    return d, em


def run(d, *args, name="script_diff.py"):
    return subprocess.run([str(PY), "-X", "utf8", "-I", str(SCRIPTS / name)] + [str(x) for x in args],
                          cwd=d, env=ENV, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=150)


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def texts(em):
    return [w["word"].strip() for w in load(em).get("words", [])]


def by_id(em):
    """Word text by its index in the ORIGINAL map: ids survive a merge, list positions after it shift."""
    ws = {w["id"]: w["word"].strip() for w in load(em).get("words", [])}
    return lambda k: ws.get("w_%04d" % k)


def rev(out, at, script, why=None):
    return any(r["at"] == at and r["script"] == script and (why is None or r["why"] == why)
               for r in out.get("review", []))


def case_fix(S, a):
    d, em = fresh(S, "fix")
    before, orig = texts(em), em.read_bytes()
    w0 = json.loads(orig)["words"]
    p = run(d, d / "script.txt", em)          # word-fixes.json from the default place (cwd/editor)
    out = load(d / "work" / "script_diff.json")
    t, after = by_id(em), texts(em)
    ck("fix: exits 0", p.returncode == 0, p.stdout + p.stderr)
    ck("fix: script_diff.json written with the match share", out.get("match", 0) >= 0.25 and out.get("warn") is None,
       out)
    ck("fix: 'Alderston' -> 'Alderstone' from the script (mid-sentence capital)", t(4) == "Alderstone", t(4))
    ck("fix: 'Brindel' -> 'Brindle'", t(6) == "Brindle", t(6))
    ck("fix: 'trailaway' -> 'trailway' (lower case, but word-fixes.json knows it)", t(14) == "trailway", t(14))
    ck("fix: 'mapglo' -> 'MapGlow' (CamelCase, at a sentence start)", t(50) == "MapGlow", t(50))
    ck("fix: 'vexa' -> 'vexa3' (a digit, lower case)", t(58) == "vexa3", t(58))
    ck("fix: 'Meadowlabs' -> 'Meadow Labs' (fewer heard words: joined onto the heard word)",
       t(65) == "Meadow Labs", t(65))
    ck("fix: a 3:3 run of close brands is fixed word by word ('Nemma Brindlle Tovvi' -> 'Nema Brindle Tovi')",
       [t(70), t(71), t(72)] == ["Nema", "Brindle", "Tovi"]
       and [f.get("merge") for f in out.get("fixes", []) if f["at"] in (70, 71, 72)] == [None] * 3, out.get("fixes"))
    # H-N1-5: 2 heard words for 1 script word become one word through fix_words.py --merge
    m = load(em)
    mw = (m.get("words") or [{}] * 23)[22]
    ck("fix: 'Alder Stone' -> one 'Alderstone' word at the original index 22 (id kept, the 2nd word gone)",
       after[22:23] == ["Alderstone"] and mw.get("id") == "w_0022" and t(23) is None
       and len(after) == len(before) - 1, (after[21:24], mw.get("id"), len(after), len(before)))
    ck("fix: the merged word starts at the first word's start and ends at the second word's end",
       mw.get("start") == w0[22]["start"] and mw.get("parakeet_start") == w0[22]["parakeet_start"]
       and mw.get("end") == w0[23]["end"], (mw, w0[22], w0[23]))
    ck("fix: the merge is listed as one fix with the indexes it joined",
       any(f["at"] == 22 and f.get("merge") == [22, 23] and f["new"] == "Alderstone" and f["heard"] == "Alder Stone"
           for f in out.get("fixes", [])), out.get("fixes"))
    ck("fix: the fixes are listed by word index", [f["at"] for f in out.get("fixes", [])] == FIXED, out.get("fixes"))
    changed = [k for k in range(len(before)) if before[k] != t(k)]
    ck("fix: no other word changed", changed == [4, 6, 14, 22, 23, 40, 41, 42, 43, 50, 58, 65, 70, 71, 72], changed)
    ck("fix: 'than' / 'then' (sounds close, not brand-like) goes to REVIEW, unchanged",
       t(28) == "than" and rev(out, [28], "then"), out.get("review"))
    ck("fix: 'Nema' / 'Trailway' (brand-like, doesn't sound close) goes to REVIEW, unchanged",
       t(33) == "Nema" and rev(out, [33], "Trailway"), out.get("review"))
    ck("fix: a 4:4 run is over the 3:3 limit, but its repeated heard words take their confirmed fixes and the "
       "last brand then lines up 1:1 in the same run (F29)",
       [t(k) for k in range(40, 44)] == ["Nema", "Brindle", "Tovi", "Rilo"]
       and not any(40 in r["at"] for r in out.get("review", [])), out.get("review"))
    ck("fix: 'now' / 'Know' (capital only at a sentence start) goes to REVIEW, unchanged",
       t(46) == "now" and rev(out, [46], "Know"), out.get("review"))
    ck("fix: 'clip' / 'video' (not brand-like) goes to REVIEW, not fixed",
       t(18) == "clip." and any(r["heard"] == "clip" and r["script"] == "video" for r in out.get("review", [])),
       out.get("review"))
    errs = bem().validate(m) if m else ["no map"]
    ck("fix: the edit map still validates with a recomputed word_list_hash", not errs and
       m.get("word_list_hash") != json.loads(orig)["word_list_hash"], errs)
    prev = em.with_name(em.name + ".prev")
    ck("fix: the previous edit map is kept as .prev", prev.exists() and prev.read_bytes() == orig)
    # only script_diff.json: the edit map is written by fix_words.py (text mode, so CRLF on Windows; not N1's file)
    ck("fix: no CR in script_diff.json", b"\r" not in (d / "work" / "script_diff.json").read_bytes())
    fixed = em.read_bytes()
    p2 = run(d, d / "script.txt", em)
    ck("fix: a second run finds nothing left to fix", p2.returncode == 0 and load(d / "work" / "script_diff.json")
       .get("fixes") == [] and em.read_bytes() == fixed, p2.stdout + p2.stderr)


def case_merge(S, a):
    """fix_words.py --merge on its own: punctuation, 3:1, --at in the same run, refusals, a tx.json's `i`."""
    d = S / "merge"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    empty = d / "empty.json"
    empty.write_bytes(b"{}")
    em = d / "edit_map.json"
    em.write_bytes(json.dumps(edit_map("we use Cedar Fox, and North Ember Set daily"), indent=1).encode("utf-8"))
    w0 = load(em)["words"]
    p = run(d, em, "--map", empty, "--merge", '{"2-3": "Cedarfox", "5-7": "NorthEmberSet"}', "--at", '{"8": "nightly"}',
            name="fix_words.py")
    m = load(em)
    ws = m.get("words", [])
    ck("merge: 2:1 and 3:1 merges plus an --at fix in one run, punctuation kept ('Fox,' -> 'Cedarfox,')",
       p.returncode == 0 and [w["word"].strip() for w in ws] == ["we", "use", "Cedarfox,", "and", "NorthEmberSet",
                                                                 "nightly"], (p.returncode, ws, p.stderr[-300:]))
    ck("merge: ids of the first words kept, times = first start / last end",
       [w["id"] for w in ws] == ["w_0000", "w_0001", "w_0002", "w_0004", "w_0005", "w_0008"]
       and ws[2]["start"] == w0[2]["start"] and ws[2]["end"] == w0[3]["end"]
       and ws[4]["start"] == w0[5]["start"] and ws[4]["end"] == w0[7]["end"], ws)
    errs = bem().validate(m) if m else ["no map"]
    ck("merge: validate() passes on the merged map", not errs, errs)
    ok = em.read_bytes()
    for bad in ('{"1-2": "x", "2-3": "y"}', '{"3-3": "x"}', '{"4-99": "x"}', '{"4": "x"}', '{"2-1": "x"}'):
        p = run(d, em, "--map", empty, "--merge", bad, name="fix_words.py")
        ck("merge: span %s refused (exit 2), nothing written" % bad, p.returncode == 2 and em.read_bytes() == ok,
           (p.returncode, p.stderr[-200:]))
    # a merge across a pause: the merged span would swallow a silence island, so validate() refuses it
    sm = d / "sil" / "edit_map.json"
    sm.parent.mkdir()
    sm.write_bytes(json.dumps(edit_map("one two three", gaps={2: 1.0}, silences=[(1.4, 2.0)]), indent=1)
                   .encode("utf-8"))
    sorig = sm.read_bytes()
    p = run(d, sm, "--map", empty, "--merge", '{"1-2": "twothree"}', name="fix_words.py")
    ck("merge: a span across a silence fails validate(): exit 2, map unchanged, no .prev",
       not bem().validate(json.loads(sorig)) and p.returncode == 2 and sm.read_bytes() == sorig
       and not sm.with_name(sm.name + ".prev").exists(), (p.returncode, p.stderr[-300:]))
    tx = d / "tx.json"
    tx.write_bytes(json.dumps({"words": [{"i": 0, "text": "Cedar", "start": 0.1, "end": 0.4},
                                         {"i": 1, "text": "Fox.", "start": 0.5, "end": 0.8},
                                         {"i": 2, "text": "Done", "start": 0.9, "end": 1.2}]}).encode("utf-8"))
    p = run(d, tx, "--map", empty, "--merge", '{"0-1": "Cedarfox"}', name="fix_words.py")
    tw = load(tx).get("words", [])
    ck("merge: a tx.json (`text` key) merges too and its `i` is renumbered",
       p.returncode == 0 and tw == [{"i": 0, "text": "Cedarfox.", "start": 0.1, "end": 0.8},
                                    {"i": 1, "text": "Done", "start": 0.9, "end": 1.2}], (tw, p.stderr[-200:]))


def case_wrong(S, a):
    d, em = fresh(S, "wrong")
    orig = em.read_bytes()
    p = run(d, d / "wrong.txt", em)
    out = load(d / "work" / "script_diff.json")
    ck("wrong: exits 1 with an 'is this the right script?' warning",
       p.returncode == 1 and "right script" in p.stdout and "right script" in (out.get("warn") or ""), p.stdout)
    ck("wrong: match is under 25 %", out.get("match", 1) < 0.25, out.get("match"))
    ck("wrong: nothing fixed, nothing listed", out.get("fixes") == [] and out.get("review") == [], out)
    ck("wrong: the edit map is byte-identical and no .prev written",
       em.read_bytes() == orig and not em.with_name(em.name + ".prev").exists())


def case_never(S, a):
    d, em = fresh(S, "never")
    p = run(d, d / "script.txt", em, "--map", d / "editor" / "word-fixes.json", "--never", "Brindel,Stone")
    out = load(d / "work" / "script_diff.json")
    t = by_id(em)
    ck("never: exits 0", p.returncode == 0, p.stdout + p.stderr)
    ck("never: 'Brindel' (on the never list) stays", t(6) == "Brindel", t(6))
    ck("never: a merge holding a never-list word ('Alder Stone') stays as two words",
       [t(22), t(23)] == ["Alder", "Stone"], [t(22), t(23)])
    ck("never: both are reported as kept, not as fixes",
       [f["at"] for f in out.get("never_kept", [])] == [6, 22]
       and not {6, 22} & {f["at"] for f in out.get("fixes", [])}, out)
    ck("never: other brand fixes still apply", t(4) == "Alderstone" and t(14) == "trailway", [t(4), t(14)])
    p2 = run(d, d / "script.txt", em, "--map", d / "nope.json")
    ck("never: a --map that doesn't exist exits 2", p2.returncode == 2, p2.stdout + p2.stderr)


CASES = {"fix": case_fix, "merge": case_merge, "wrong": case_wrong, "never": case_never}


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch", nargs="?")
    ap.add_argument("--case", choices=CASES)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="n1-") as scratch:
        S = Path(a.scratch or scratch).resolve()
        S.mkdir(parents=True, exist_ok=True)
        for name, fn in CASES.items():
            if not a.case or a.case == name:
                fn(S, a)
        print("%d check(s) failed: %s" % (len(fails), ", ".join(fails)) if fails else "all checks passed")
        return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
