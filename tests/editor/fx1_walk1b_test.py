#!/usr/bin/env python3
"""FX1 rounds 7/8/9: short spoken lines, frame rounding and kept-word slivers.

usage: python tests/editor/fx1_walk1b_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 only when no checks fail.
"""
import argparse, hashlib, json, os, re, shlex, shutil, subprocess, sys, tempfile, wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
P = REPO / "plugins/editor-superengine"
S = P / "skills/reel-first-cuts/scripts"
sys.path.insert(0, str(P / "skills/_shared"))
sys.path.insert(0, str(S))
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)
    return ok


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(json.dumps(obj, indent=1).encode("utf-8"))


def run(script, args, d):
    return subprocess.run([sys.executable, "-X", "utf8", "-I", str(script), *map(str, args)], cwd=d,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)


def board(d, reel):
    return run(S / "make_board.py", ["--script", "script.md", "--take", "1:work/edit_map.json:work/tx.16k.wav",
                                   "--shots", "shots.json", "--reel", reel, "-o", d], d)


def tweak_board(d, reel):
    # Same word mapping as make_tweaks, without a video or waveform.
    import word_map
    cuts = read(d / "work/cuts.json")
    em = read(d / "work/edit_map.json")
    edl = word_map.read_edl(d / "work/edl.json")
    write(d / "tweak-board.config.json", dict(
        reel=reel, version="v1", edit_map="work/edit_map.json", take=1,
        cuts_sha256=hashlib.sha256((d / "work/cuts.json").read_bytes()).hexdigest(),
        words=[dict(id=w["id"], w=w["word"], t=round(w["out_start"], 3))
               for w in word_map.build(cuts, em, edl=edl)["words"]]))
    write(d / "tweak-selection.json", dict(reel=reel, version="v1", marks=[]))


def tweak_sliver(scratch):
    d = Path(tempfile.mkdtemp(prefix="fx1-tweak-sliver-", dir=scratch))
    work = d / "work"
    cuts = dict(fps=30, speed=1.0, segments=[
        dict(src_in_f=30, src_out_f=60, out_in_f=0, out_out_f=30)])
    write(work / "cuts.json", cuts)
    cut = [dict(id=1, type="cut", a=0.5, b=0.6)]
    for label, start, end, edl, marks, alternate, want in (
            ("held OUT unpicked", 1.98, 2.2, [dict(src_in=1.0, src_out=1.98)], [], False,
             [dict(src_in=1.0, src_out=1.98)]),
            ("held OUT picked", 1.98, 2.2, [dict(src_in=1.0, src_out=2.2)], [], False,
             [dict(src_in=1.0, src_out=2.0)]),
            ("held IN unpicked", 0.8, 1.02, [dict(src_in=1.02, src_out=2.0)], [], False,
             [dict(src_in=1.02, src_out=2.0)]),
            ("trimmed OUT unpicked", 1.98, 2.2, [dict(src_in=1.0, src_out=1.98)], cut, False,
             [dict(src_in=1.0, src_out=1.5), dict(src_in=1.6, src_out=1.98)]),
            ("trimmed IN unpicked", 0.8, 1.02, [dict(src_in=1.02, src_out=2.0)], cut, False,
             [dict(src_in=1.02, src_out=1.5), dict(src_in=1.6, src_out=2.0)]),
            ("alternate output reads previous work EDL", 1.98, 2.2,
             [dict(src_in=1.0, src_out=1.98)], [], True, [dict(src_in=1.0, src_out=1.98)]),
            ("empty previous EDL", 1.98, 2.2, [], [], False, [dict(src_in=1.0, src_out=1.98)]),
            ("missing previous EDL", 1.98, 2.2, None, [], False, [dict(src_in=1.0, src_out=2.0)]),
            ("unreadable previous EDL", 1.98, 2.2, "invalid", [], False,
             [dict(src_in=1.0, src_out=2.0)])):
        write(work / "edit_map.json", dict(words=[dict(
            id="w_edge", word="edge", start=start, end=end, parakeet_start=start, status="aligned")]))
        if edl is None:
            (work / "edl.json").unlink(missing_ok=True)
        elif isinstance(edl, str):
            (work / "edl.json").write_bytes(b"not JSON")
        else:
            write(work / "edl.json", edl)
        tweak_board(d, d.name)
        write(d / "tweak-selection.json", dict(reel=d.name, version="v1", marks=marks))
        out = d / "alternate" if alternate else work
        args = ["tweak-selection.json", "work"] + (["--out", out] if alternate else [])
        p = run(S / "tweaks_to_edl.py", args, d)
        if not ck("tweak-sliver: " + label + " Send accepted", p.returncode == 0, p.stdout + p.stderr):
            continue
        ck("tweak-sliver: " + label + " EDL", read(out / "edl.json") == want, read(out / "edl.json"))
        ck("tweak-sliver: " + label + " hold", ("--hold 1.000000:2.000000" in p.stdout)
           if not marks else "--hold" not in p.stdout, p.stdout + p.stderr)


def sliver_threshold(scratch):
    import word_map
    d = Path(tempfile.mkdtemp(prefix="fx1-sliver-threshold-", dir=scratch))
    write(d / "probe.json", dict(out_rate=30))
    write(d / "envelope.json", dict(db=[-60.0] * 400, win_s=0.01))
    write(d / "segments.json", [[1.0, 2.0]])
    cuts = dict(fps=30, segments=[dict(src_in_f=30, src_out_f=60, out_in_f=0, out_out_f=30)])
    for label, extra, kept in (("exactly one frame", 0.0, False),
                               ("within EPS", 0.00025, False), ("beyond EPS", 0.00075, True)):
        start = 2.0 - 1 / 30 - extra
        em = dict(words=[dict(id="w_edge", word="struck", start=start, end=2.2, parakeet_start=start)])
        edl = [dict(src_in=1.0, src_out=start)]
        write(d / "edit_map.json", em)
        write(d / "edl.json", edl)
        m = word_map.build(cuts, em, edl)
        ck("sliver-threshold: " + label + " word map", [w["word"] for w in m["words"]]
           == (["struck"] if kept else []), m)
        p = run(S / "boundary_audit.py", [d, d / "edit_map.json"], d)
        ck("sliver-threshold: " + label + " audit agrees", p.returncode == (1 if kept else 0)
           and (("INSIDE 'struck'" in p.stdout) if kept else "flagged 0" in p.stdout), p.stdout + p.stderr)


def short_lines(scratch):
    # The real main() owns the attempt loop; a three-second PCM fixture avoids any media tools.
    import build_edit_map
    d = Path(tempfile.mkdtemp(prefix="fx1-short-lines-", dir=scratch))
    (d / "work").mkdir()
    wav = d / "work/tx.16k.wav"
    with wave.open(str(wav), "wb") as f:
        f.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        f.writeframes(b"\0\0" * 48000)
    words = [dict(id="w_%04d" % i, word=w, start=s, end=e, parakeet_start=s, status="aligned")
             for i, (w, s, e) in enumerate((("Free", 0.5, 0.7), ("account.", 0.7, 1.0),
                                            ("See?", 2.0, 2.2)))]
    em = dict(duration=3.0, audio_sha256=build_edit_map.audio_sha256(str(wav)), calibration={},
              words=words, events=[dict(id="v_0000", word="[breath]", start=2.4, end=2.5)], silences=[])
    em["word_list_hash"] = build_edit_map.word_list_hash(build_edit_map.board_sequence(em))
    write(d / "work/edit_map.json", em)
    write(d / "shots.json", dict(vocab=["talking head"], default="talking head"))
    (d / "script.md").write_bytes(b"# Test script\n---\nFree account.\nSee?\n")
    p = board(d, d.name)
    if not ck("short-lines: real board builds", p.returncode == 0, p.stdout + p.stderr):
        return
    lines = read(d / "cut-board.config.json")["lines"]
    for text, count in (("Free account.", 2), ("See?", 1)):
        line = next(l for l in lines if l["text"] == text)
        ck("short-lines: %d-word line has one real attempt" % count,
           len(line["attempts"]) == 1 and len(line["attempts"][0]["words"]) == count
           and line["attempts"][0]["text"] == text, line)
    # A fuzzy anchor can match two long words of a six-word line; it is still only a fragment.
    from make_board import find_anchors
    words[0]["word"], words[1]["word"] = "extraordinary", "connection"
    em["word_list_hash"] = build_edit_map.word_list_hash(build_edit_map.board_sequence(em))
    write(d / "work/edit_map.json", em)
    (d / "script.md").write_bytes(b"# Test script\n---\nA I I extraordinary connection now.\nSee?\n")
    p = board(d, d.name)
    if not ck("short-lines: fragment board builds", p.returncode == 0, p.stdout + p.stderr):
        return
    cfg = read(d / "cut-board.config.json")
    line = cfg["lines"][0]
    ck("short-lines: two-word fragment really anchors the six-word line",
       any(wi == 0 for wi, _ in find_anchors(line["anchor"], cfg["takes"]["1"]["words"])), line)
    ck("short-lines: two-word fragment is not a long-line attempt",
       line["attempts"] == [] and line["default"] is None, line)


def snap(scratch):
    from gaps import snap_cuts
    words = [dict(start=114.48, end=114.56), dict(start=114.56, end=114.64)]
    cuts = snap_cuts([(114.56, 116.0)], 30, words=words)
    ck("snap: IN rounds outward before kept you", cuts["segments"] == [
        dict(src_in_f=3436, src_out_f=3480, out_in_f=0, out_out_f=44)], cuts)
    for word, start, end, next_word, next_start, next_end, want in (
            ("And", 92.54, 92.62, "now", 92.68, 92.80, 2779),
            ("it's", 136.18, 136.26, "time", 136.28, 136.40, 4088)):
        cuts = snap_cuts([(end, next_end + 1.0)], 30, words=[
            dict(word=word, start=start, end=end), dict(word=next_word, start=next_start, end=next_end)])
        ck("snap: IN chooses clean frame after unpicked " + word,
           cuts["segments"][0]["src_in_f"] == want, cuts)
    for end in (10.05, 10.06):
        cuts = snap_cuts([(9.0, end)], 30, words=[
            dict(start=9.5, end=10.0), dict(start=10.05, end=10.2)])
        ck("snap: OUT at %.2f falls back outward when nearest is in speech" % end,
           cuts["segments"][0]["src_out_f"] == 302, cuts)
    cuts = snap_cuts([(1.02, 2.0)], 30, words=[dict(start=1.2, end=1.5)])
    ck("snap: nearest inward IN in silence", cuts["segments"][0]["src_in_f"] == 31, cuts)
    cuts = snap_cuts([(1.01, 2.0)], 30, words=[dict(start=1.2, end=1.5)])
    ck("snap: nearest outward IN in silence", cuts["segments"][0]["src_in_f"] == 30, cuts)
    cuts = snap_cuts([(1.0, 2.01)], 30, words=[dict(start=2.02, end=2.2)])
    ck("snap: OUT cannot swallow a following word start", cuts["segments"] == [
        dict(src_in_f=30, src_out_f=60, out_in_f=0, out_out_f=30)], cuts)
    cuts = snap_cuts([(1.02, 2.0)], 30, words=[dict(start=1.01, end=1.2)])
    ck("snap: IN falls back outward even across an earlier word start",
       cuts["segments"][0]["src_in_f"] == 30, cuts)
    # Nearest is in silence here, but would pull a whole short word's start into the piece.
    cuts = snap_cuts([(1.0, 2.02)], 30, words=[dict(start=2.021, end=2.025)])
    ck("snap: nearest cannot pull a word start into the piece; falls back outward",
       cuts["segments"][0]["src_out_f"] == 61, cuts)
    cuts = snap_cuts([(55.0, 56.04)], 30, words=[
        dict(word="you", start=55.98, end=56.04), dict(word="how", start=56.06, end=56.14)])
    ck("snap: sub-frame gap OUT rounds outward without clipping you",
       cuts["segments"][0]["src_out_f"] == 1682, cuts)
    cuts = snap_cuts([(1.0, 2.01)], 30, words=[dict(start=1.0, end=2.01)])
    ck("snap: unguarded OUT rounds outward", cuts["segments"][0]["src_out_f"] == 61, cuts)
    cuts = snap_cuts([(1.0, 2.0)], 30, words=[dict(start=1.0, end=2.0), dict(start=2.0, end=2.2)])
    ck("snap: exact frame edges stay exact", cuts["segments"][0]["src_in_f"] == 30
       and cuts["segments"][0]["src_out_f"] == 60, cuts)
    # Hand-calculated legacy round(), merge and keep behavior, including speed output frames.
    pieces = [(0.01, 0.09), (0.09, 0.14), (1.01, 1.08), (2.001, 2.002), (3.001, 3.002)]
    expected = dict(fps=30, speed=2.0, segments=[
        dict(src_in_f=0, src_out_f=4, out_in_f=0, out_out_f=2),
        dict(src_in_f=30, src_out_f=32, out_in_f=2, out_out_f=3),
        dict(src_in_f=90, src_out_f=91, out_in_f=3, out_out_f=4)])
    for kwargs in ({}, {"words": ()}):
        cuts = snap_cuts(pieces, 30, speed=2.0, keep={4}, **kwargs)
        ck("snap: legacy rounding with %s" % kwargs, cuts == expected, cuts)


def word_map_sliver(scratch):
    import word_map
    d = Path(tempfile.mkdtemp(prefix="fx1-word-map-sliver-", dir=scratch))
    words = [dict(id="w_%04d" % i, word=w, start=s, end=e, parakeet_start=s)
             for i, (w, s, e) in enumerate((("you", 55.98, 56.04), ("how", 56.06, 56.14)))]
    # Frame 1682 is 56.067 s to the millisecond; only a sliver of 'how' is in the piece.
    cuts = dict(fps=30, segments=[dict(src_in_f=1650, src_out_f=1682, out_in_f=0, out_out_f=32)])
    edl = [dict(src_in=55.0, src_out=56.04)]
    m = word_map.build(cuts, dict(words=words), edl)
    ck("word-map-sliver: how onset sliver is omitted, you is kept",
       [w["word"] for w in m["words"]] == ["you"], m)
    for label, start, end, want in (
            ("two frames before end stays kept", 56.0, 56.14, ["long"]),
            ("last-frame word ending inside stays kept", 56.04, 56.06, ["long"]),
            ("last-frame word ending on boundary stays kept", 56.04, 1682 / 30, ["long"])):
        word = dict(id="w_long", word="long", start=start, end=end, parakeet_start=start)
        m = word_map.build(cuts, dict(words=[word]), edl)
        ck("word-map-sliver: " + label, [w["word"] for w in m["words"]] == want, m)
    write(d / "probe.json", dict(out_rate=30))
    write(d / "envelope.json", dict(db=[-60.0] * 5700, win_s=0.01))
    write(d / "segments.json", [[55.0, 1682 / 30]])
    write(d / "edit_map.json", dict(words=words))
    write(d / "edl.json", edl)
    p = run(S / "boundary_audit.py", [d, d / "edit_map.json"], d)
    ck("word-map-sliver: audit agrees on dropped how and kept you", p.returncode == 0
       and "flagged 0" in p.stdout and "INSIDE" not in p.stdout, p.stdout + p.stderr)
    # Empty timings still report hot boundaries, including board advice, without naming a word.
    write(d / "edit_map.json", dict(words=[]))
    write(d / "envelope.json", dict(db=[-4.8] * 5700, win_s=0.01))
    write(d / "edl.json", [dict(src_in=55.0, src_out=1682 / 30, line="L07")])
    p = run(S / "boundary_audit.py", [d, d / "edit_map.json"], d)
    ck("word-map-sliver: empty word list reports hot edges without crashing", p.returncode == 1
       and "flagged 2" in p.stdout and "Line L07:" in p.stdout
       and "nearest '" not in p.stdout and "Traceback" not in p.stderr, p.stdout + p.stderr)


def pick_aware(scratch):
    import word_map
    d = Path(tempfile.mkdtemp(prefix="fx1-pick-aware-", dir=scratch))
    work = d / "work"
    word = dict(id="w_clip", word="clipped", start=1.98, end=2.4, parakeet_start=1.98)
    em = dict(words=[word])
    cuts = dict(fps=30, speed=1.0, segments=[
        dict(src_in_f=30, src_out_f=60, out_in_f=0, out_out_f=30)])
    write(work / "cuts.json", cuts)
    write(work / "segments.json", [[1.0, 2.0]])
    write(work / "edit_map.json", em)
    write(work / "envelope.json", dict(db=[-60.0] * 400, win_s=0.01))
    picked = [dict(src_in=1.0, src_out=2.4, line="L07")]
    unpicked = [dict(src_in=1.0, src_out=1.98, line="L07")]
    for label, edl, want in (("picked", picked, ["clipped"]),
                             ("unpicked", unpicked, []), ("empty EDL", [], []),
                             ("missing EDL", None, ["clipped"]),
                             ("unreadable EDL", "invalid", ["clipped"])):
        if edl is None:
            (work / "edl.json").unlink(missing_ok=True)
        elif isinstance(edl, str):
            (work / "edl.json").write_bytes(b"not JSON")
        else:
            write(work / "edl.json", edl)
        p = run(S / "boundary_audit.py", [work, work / "edit_map.json"], d)
        ck("pick-aware: " + label + " audit", p.returncode == (1 if want else 0)
           and (("INSIDE 'clipped'" in p.stdout) if want else "flagged 0" in p.stdout), p.stdout + p.stderr)
        p = run(S / "word_map.py", [d], d)
        if not ck("pick-aware: " + label + " word map written", p.returncode == 0, p.stdout + p.stderr):
            continue
        m = read(work / "word_map.json")
        ck("pick-aware: " + label + " membership", [w["word"] for w in m["words"]] == want, m)
        p = run(P / "skills/_shared/checks/map_check.py", [d], d)
        ck("pick-aware: " + label + " map check agrees", p.returncode == 0, p.stdout + p.stderr)
    # --edl is the authority even when the default file says otherwise.
    write(work / "edl.json", unpicked)
    write(d / "picked-edl.json", [dict(src_in=1.0, src_out=2.0, line="L07")])
    p = run(S / "boundary_audit.py", [work, work / "edit_map.json", "--edl", d / "picked-edl.json"], d)
    ck("pick-aware: audit honors explicit EDL", p.returncode == 1
       and "INSIDE 'clipped'" in p.stdout and "Line L07:" in p.stdout, p.stdout + p.stderr)
    write(work / "edl.json", picked)
    write(d / "unpicked-edl.json", unpicked)
    p = run(S / "boundary_audit.py", [work, work / "edit_map.json", "--edl", d / "unpicked-edl.json"], d)
    ck("pick-aware: explicit EDL can omit the sliver", p.returncode == 0
       and "flagged 0" in p.stdout, p.stdout + p.stderr)
    # Overlapping source times in another take cannot turn an unpicked word into a picked one.
    mixed = dict(cuts, segments=[dict(cuts["segments"][0], take=1), dict(cuts["segments"][0], take=2)])
    m = word_map.build(mixed, dict(takes={"1": em, "2": em}), [dict(picked[0], take=2)])
    ck("pick-aware: EDL picks stay within their take", [w["id"] for w in m["words"]] == ["t2:w_clip"], m)


def audit_sliver(scratch):
    d = Path(tempfile.mkdtemp(prefix="fx1-audit-sliver-", dir=scratch))
    write(d / "envelope.json", dict(db=[-60.0] * 400, win_s=0.01))
    word = dict(word="dropped", start=1.8, end=2.0)
    write(d / "edit_map.json", dict(words=[word]))
    write(d / "segments.json", [[1.973, 3.0]])
    write(d / "edl.json", [dict(src_in=2.0, src_out=3.0)])

    def audit():
        return run(S / "boundary_audit.py", [d, d / "edit_map.json"], d)

    for label, probe, cuts, clean in (
            ("probe rate wins", {"out_rate": 30}, {"fps": 60}, True),
            ("cuts rate fallback", {}, {"fps": 30}, True),
            ("shorter frame still flags", {"out_rate": 60}, {"fps": 30}, False),
            ("default 30 fps", {}, None, True)):
        write(d / "probe.json", probe)
        if cuts is None:
            (d / "cuts.json").unlink(missing_ok=True)
        else:
            write(d / "cuts.json", cuts)
        p = audit()
        ck("audit-sliver: " + label, p.returncode == (0 if clean else 1)
           and ("INSIDE 'dropped'" not in p.stdout if clean else "INSIDE 'dropped'" in p.stdout),
           p.stdout + p.stderr)
    # The same IN boundary must flag once the word's start is kept in another segment.
    write(d / "segments.json", [[1.7, 1.9], [1.973, 3.0]])
    write(d / "edl.json", [dict(src_in=1.7, src_out=1.9, line="L14"),
                           dict(src_in=1.973, src_out=3.0, line="L15")])
    p = audit()
    ck("audit-sliver: kept word still flags at the same IN", p.returncode == 1
       and re.search(r"seg01 IN\s+1\.973 INSIDE 'dropped'", p.stdout) is not None, p.stdout + p.stderr)
    advice = ("Line L15: a cut the user made on the Cut Board sits on the word 'dropped'. "
              "Put back the struck word next to it on the Cut Board and press Send again, "
              "or keep this cut and listen to it on the review page before rendering.")
    ck("audit-sliver: board advice names line, word and actionable choices", advice in p.stdout
       and "rebuild that board" not in p.stdout, p.stdout + p.stderr)
    # A word starting before a tiny piece is not kept; its OUT sliver is also allowed.
    write(d / "segments.json", [[1.81, 1.827]])
    write(d / "edl.json", [dict(src_in=1.81, src_out=1.827)])
    p = audit()
    ck("audit-sliver: dropped word's OUT sliver is not flagged", "seg00 OUT" not in p.stdout, p.stdout + p.stderr)
    write(d / "segments.json", [[1.81, 1.85]])
    p = audit()
    ck("audit-sliver: OUT beyond one frame still flags", "seg00 OUT" in p.stdout
       and "INSIDE 'dropped'" in p.stdout, p.stdout + p.stderr)
    # An overlapping dropped sliver must not hide a kept word at that same boundary.
    write(d / "segments.json", [[1.85, 1.95], [1.973, 3.0]])
    write(d / "edl.json", [dict(src_in=1.85, src_out=3.0)])
    write(d / "edit_map.json", dict(words=[word, dict(word="kept", start=1.9, end=2.1)]))
    p = audit()
    ck("audit-sliver: kept overlap still flags", re.search(r"seg01 IN\s+1\.973 INSIDE 'kept'", p.stdout)
       is not None, p.stdout + p.stderr)
    # Outward rounding can leave the dropped word's energy beyond the old 10 ms slack.
    write(d / "probe.json", dict(out_rate=30))
    for side, segment, omitted, kept, hot in (
            ("IN", [1.973, 3.0], dict(word="provide", start=1.8, end=2.0, status="unresolved"),
             dict(word="you", start=2.0, end=2.3), (180, 200)),
            ("OUT", [1.0, 2.027], dict(word="provide", start=2.0, end=2.2, status="unresolved"),
             dict(word="you", start=1.7, end=2.0), (200, 220))):
        db = [-60.0] * 400
        db[hot[0]:hot[1]] = [-4.8] * (hot[1] - hot[0])
        write(d / "envelope.json", dict(db=db, win_s=0.01))
        write(d / "segments.json", [segment])
        write(d / "edl.json", [dict(src_in=kept["start"], src_out=kept["end"])])
        write(d / "edit_map.json", dict(words=[omitted, kept]))
        p = audit()
        ck("audit-sliver: %s ignores dropped energy within one frame" % side,
           p.returncode == 0 and "flagged 0" in p.stdout, p.stdout + p.stderr)


def real_walk1b(scratch):
    value = os.environ.get("EDITOR_SE_TEST_REEL_W1B", "")
    source = Path(value) if value else None
    if source is None or not source.is_dir():
        print("SKIP real-walk1b: set EDITOR_SE_TEST_REEL_W1B to the S17 re-walk-1 reel folder to run this case")
        return
    d = Path(tempfile.mkdtemp(prefix="fx1-walk1b-", dir=scratch))
    for name in ("script.md", "shots.json", "cut-selection.json", "work/edit_map.json", "work/tx.16k.wav",
                 "work/probe.json", "work/envelope.json"):
        dest = d / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, dest)
    original = (d / "script.md").read_bytes()
    text = original.decode("utf-8")
    phrases = ("Free account.", "That's it.", "See?")
    head, sep, body = text.rpartition("\n---\n")
    if not sep:
        head, body = "", text
    for phrase in phrases:
        if not ck("real-walk1b: script contains " + phrase, phrase in body):
            return
        body = body.replace(phrase, "\n" + phrase + "\n")
    (d / "script.md").write_bytes(((head + sep if sep else "") + body).encode("utf-8"))
    p = board(d, source.name)
    if not ck("real-walk1b: split-line board builds", p.returncode == 0, p.stdout + p.stderr):
        return
    cfg = read(d / "cut-board.config.json")
    for phrase in phrases:
        lines = [l for l in cfg["lines"] if l["text"] == phrase]
        ck("real-walk1b: short line has an attempt: " + phrase,
           bool(lines) and all(l["attempts"] for l in lines), lines)
    (d / "script.md").write_bytes(original)
    p = board(d, source.name)
    if not ck("real-walk1b: original-script board builds", p.returncode == 0, p.stdout + p.stderr):
        return
    cfg, sel = read(d / "cut-board.config.json"), read(d / "cut-selection.json")
    sel["board_hash"] = cfg["board_hash"]
    line = next(l for l in sel["lines"] if l["id"] == "L15")
    line["pick"] = 1
    att = next(l for l in cfg["lines"] if l["id"] == "L15")["attempts"][1]

    def index(word, start):
        matches = [w["i"] for w in att["words"] if w["w"] == word and abs(w["s"] - start) < 0.1]
        if len(matches) != 1:
            raise ValueError("expected one board word %r near %.2f, got %s" % (word, start, matches))
        return matches[0]

    struck = [index("Okay,", 108.8), index("I", 110.8), index("provide", 110.96)]
    doubled = index("you", 114.56)
    scenarios = [("keep doubled you", line, 1, struck), ("strike doubled you", line, 1, struck + [doubled])]
    # Start this regression from the original selection, independently of the L15 variants.
    original_sel = read(d / "cut-selection.json")
    original_sel["board_hash"] = cfg["board_hash"]
    how_line = next(l for l in original_sel["lines"] if l["id"] == "L07")
    how_line["pick"] = 0
    att = next(l for l in cfg["lines"] if l["id"] == "L07")["attempts"][0]
    scenarios.append(("strike how", how_line, 0, [index("how", 56.06)]))
    for label, selected, pick, removed in scenarios:
        selected.setdefault("rm", {})[str(pick)] = removed
        if label == "strike how":
            sel = original_sel
        write(d / "cut-selection.json", sel)
        p = run(S / "selection_to_edl.py", ["cut-selection.json", "cut-board.config.json"], d)
        if not ck("real-walk1b: " + label + " selection to EDL", p.returncode == 0, p.stdout + p.stderr):
            continue
        command = next(l for l in p.stdout.splitlines() if l.startswith("<editor python>"))
        args = shlex.split(command[len("<editor python>"):].replace("${CLAUDE_PLUGIN_ROOT}", P.as_posix()))
        p = subprocess.run([sys.executable, *args], cwd=d, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180)
        if not ck("real-walk1b: " + label + " printed gaps command", p.returncode == 0, p.stdout + p.stderr):
            continue
        if label == "strike how":
            cuts = read(d / "work/cuts.json")
            print("INFO real-walk1b: strike how total cut frames %d" % sum(
                s["src_out_f"] - s["src_in_f"] for s in cuts["segments"]))
        p = run(S / "boundary_audit.py", [d / "work", d / "work/edit_map.json"], d)
        ck("real-walk1b: " + label + " audit clean", p.returncode == 0 and "flagged 0" in p.stdout
           and "INSIDE 'you'" not in p.stdout, p.stdout + p.stderr)
        p = run(S / "word_map.py", [d], d)
        if not ck("real-walk1b: " + label + " word map", p.returncode == 0, p.stdout + p.stderr):
            continue
        p = run(P / "skills/_shared/checks/map_check.py", [d], d)
        ck("real-walk1b: " + label + " map check", p.returncode == 0, p.stdout + p.stderr)
        if label == "strike how":
            before = (d / "work/cuts.json").read_bytes()
            tweak_board(d, source.name)
            p = run(S / "tweaks_to_edl.py", ["tweak-selection.json", "work"], d)
            if not ck("real-walk1b: no-mark v1 Send accepted", p.returncode == 0, p.stdout + p.stderr):
                continue
            command = next(l for l in p.stdout.splitlines() if l.startswith("<editor python>"))
            args = shlex.split(command[len("<editor python>"):].replace("${CLAUDE_PLUGIN_ROOT}", P.as_posix()))
            p = subprocess.run([sys.executable, *args], cwd=d, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=180)
            if not ck("real-walk1b: no-mark printed gaps command", p.returncode == 0, p.stdout + p.stderr):
                continue
            ck("real-walk1b: no-mark Send preserves cuts byte for byte",
               (d / "work/cuts.json").read_bytes() == before, p.stdout + p.stderr)
            gap_plan = (d / "work/gap-plan.txt").read_text(encoding="utf-8")
            ck("real-walk1b: no-mark Send does not re-pick how", "EDGE moved to keep 'how'" not in gap_plan,
               gap_plan)
            p = run(S / "word_map.py", [d], d)
            ck("real-walk1b: no-mark word map", p.returncode == 0, p.stdout + p.stderr)
            p = run(P / "skills/_shared/checks/map_check.py", [d], d)
            ck("real-walk1b: no-mark map check", p.returncode == 0, p.stdout + p.stderr)


CASES = {"short-lines": short_lines, "snap": snap, "word-map-sliver": word_map_sliver,
         "pick-aware": pick_aware, "audit-sliver": audit_sliver, "tweak-sliver": tweak_sliver,
         "sliver-threshold": sliver_threshold, "real-walk1b": real_walk1b}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=sorted(CASES))
    a = ap.parse_args()
    scratch = Path(a.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    for name, fn in CASES.items():
        if a.case in (None, name):
            try:
                fn(scratch)
            except Exception as e:
                ck(name, False, repr(e))
    print("\n%d failed" % len(fails) if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
