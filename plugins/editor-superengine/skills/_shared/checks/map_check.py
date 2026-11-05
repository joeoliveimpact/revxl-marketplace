#!/usr/bin/env python3
"""Pre-render check: the word map still matches the cut, every kept word's place in the cut is right to 6 ms, and
the cut says what the client picked on the Cut Board.

    <editor python> -X utf8 -I map_check.py <reel_dir>      exit 1 on any block, 0 when clean

Module contract (H-B6): PHASE = "pre"; run(ctx) returns [{check, level: "block"|"warn", msg, where}],
ctx = {reel_dir, fps, cuts, beats, render}. run() writes nothing. Only ctx["reel_dir"] is read: the check reads
the edit map the cut was made from (word_map.pick_map: the board take's map, else work/edit_map.json), that take's
cuts.json in the same folder (work/cuts.json, or work/take2/cuts.json for a ruling on take 2), work/word_map.json,
and when present cut-board.config.json + cut-selection.json and tweak-board.config.json, from disk, because
staleness is a test on the files themselves. With no edit map (no word alignment on this computer), the folder's
tx.json word times stand in (word_map.sources).
Run alone, it also writes <reel>/work/map_check.json = {"blocks": [...], "warns": [...]} (the findings, each with
its plain-English msg; empty lists when clean) on every run.

Blocks:
  word-map-missing   no work/word_map.json (or the take's cuts.json missing, any input unreadable, or the
                     board ruling doesn't name one take)
  word-map-stale     cuts.json or the edit map changed after the map was written (sha256 in the map), or the
                     ruling now points the cut at another edit map or another take's cuts.json
  word-missing       a kept word (recomputed by word_map.build from the current files) is not in the map
  word-twice         a word sits in two segments, or the map lists it twice
  word-not-kept      the map lists a word the cut drops
  word-wrong-piece   the map puts a word in a different segment than the cut does
  word-time          a word's output start or end is off by more than 6 ms from
                     out_in_f/fps + (src_t - src_in_f/fps) / speed
Quote checks, only when cut-board.config.json and cut-selection.json both exist. The quote is, per line in
cut-selection.json order that is not dropped and has a pick, the picked attempt's words minus the struck ones
(rm[pick]), as edit-map ids through cfg.takes[take].words[i].id; "[...]" events and words the edit map marks
unresolved (never in the cut) are left out.
  quote-missing      a picked word is in no piece of the cut
  quote-twice        a picked word is in two pieces
  quote-extra        a piece holds a word no picked line has (a moved cut edge, or a struck word still in)
  quote-order        picked words play out of script order (piece order, then board anchor time inside a piece)
  board-unreadable   cut-board.config.json / cut-selection.json don't fit together (a pick or word index the board lacks)
Tweak check, only when tweak-board.config.json exists: each words[] {id, w, t} against the word map's out_anchor
(the board anchor, parakeet_start, in output time; make_tweaks.py places words from it).
  tweak-time         |t - out_anchor| over 6 ms (block); an id the word map doesn't keep is a warn (tweak-word)
  Only while the Tweak Board was built from this cuts.json (its cuts_sha256, stamped by make_tweaks.py). A board
  from an older cut (a Stage 9 round moved the cut) or with no stamp: no tweak check, one warn (tweak-stale).
Warns, never blocks:
  no-word-times      no edit map and no tx.json word times at all: nothing is checked (the only finding)
"""
import json, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[2] / "reel-first-cuts" / "scripts"))
from win_encoding import ensure_utf8_output  # noqa: E402
import word_map  # noqa: E402

PHASE = "pre"
TOL = 0.006
RERUN = " Rerun word_map.py on this reel before rendering."
OLD_TWEAK = "Tweak Board is from an older cut, rebuild it to re-check timing"


def _hit(check, msg, where):
    return dict(check=check, level="block", msg=msg, where=where)


def run(ctx):
    reel = Path(ctx["reel_dir"])
    work = reel / "work"
    try:
        rel = word_map.pick_map(reel)
    except (ValueError, KeyError, IndexError, TypeError) as e:
        return [_hit("word-map-missing", "Can't tell which transcript the cut was made from: %s." % e + RERUN,
                     "cut-selection.json")]
    map_p = work / "word_map.json"
    try:
        crel, src, em = word_map.sources(reel, rel)
    except (ValueError, KeyError, TypeError) as e:
        return [_hit("word-map-missing", "The word map or its inputs can't be read (%s)." % e + RERUN, rel)]
    if src is None:   # no word times at all (no word alignment on this computer): skip, never block the render
        return [dict(check="no-word-times", level="warn", msg=word_map.NO_TIMES, where=rel)]
    cuts_p, em_p = reel / crel, reel / src
    for p in (cuts_p, map_p):
        if not p.exists():
            what = "No word map yet" if p is map_p else "Can't check the words: %s is missing" % crel
            return [_hit("word-map-missing", what + "." + RERUN, str(p))]
    try:
        cuts, m = (json.loads(p.read_text(encoding="utf-8")) for p in (cuts_p, map_p))
        got = m["words"]
    except (ValueError, KeyError, TypeError) as e:
        return [_hit("word-map-missing", "The word map or its inputs can't be read (%s)." % e + RERUN, str(map_p))]
    if (m.get("cuts") != crel or m.get("cuts_sha256") != word_map.sha(cuts_p) or m.get("edit_map") != src
            or m.get("edit_map_sha256") != word_map.sha(em_p)):
        return [_hit("word-map-stale", "The word map is out of date: the cut list (%s) or the transcript "
                     "(%s) changed after it was written." % (crel, src) + RERUN, str(map_p))]

    want = word_map.build(cuts, em)["words"]
    out, where = [], lambda w: "work/word_map.json: %s" % w["id"]
    cw, cg = Counter(w["id"] for w in want), Counter(w["id"] for w in got)
    twice = {i for i in cw | cg if cw[i] > 1 or cg[i] > 1}
    for i in sorted(twice):
        w = next(x for x in want + got if x["id"] == i)
        pieces = sorted({x["seg"] + 1 for x in want + got if x["id"] == i})
        out.append(_hit("word-twice", "'%s' shows up twice in the cut (pieces %s); a word belongs in one piece only."
                        % (w["word"], ", ".join(map(str, pieces))), where(w)))
    W, G = {w["id"]: w for w in want}, {w["id"]: w for w in got}
    for i, w in W.items():
        if i not in G:
            out.append(_hit("word-missing", "'%s' is kept in the cut but missing from the word map." % w["word"]
                            + RERUN, where(w)))
    for i, g in G.items():
        w = W.get(i)
        if w is None:
            out.append(_hit("word-not-kept", "'%s' is in the word map but the cut drops it." % g["word"] + RERUN,
                            where(g)))
        elif i not in twice and g.get("seg") != w["seg"]:
            out.append(_hit("word-wrong-piece", "'%s' is mapped to piece %s but sits in piece %d of the cut."
                            % (w["word"], g.get("seg", -1) + 1, w["seg"] + 1) + RERUN, where(w)))
        elif i not in twice:
            for k in ("out_start", "out_end"):
                off = abs(float(g.get(k, 1e9)) - w[k])
                if off > TOL + 1e-9:
                    out.append(_hit("word-time", "'%s' %s at %.3f s in the word map but belongs at %.3f s in the cut "
                                    "(%.0f ms off; the limit is 6 ms)." % (w["word"], k[4:] + "s", float(g.get(k, -1)),
                                                                          w[k], off * 1000) + RERUN, where(w)))
                    break
    try:
        b = word_map.board(reel)
        if b is not None:
            out += quote_checks(*b, em, want)
    except (ValueError, KeyError, IndexError, TypeError) as e:
        out.append(_hit("board-unreadable", "The Cut Board ruling can't be read (%s), so the cut can't be checked "
                        "against the picks." % e, "cut-selection.json"))
    return out + tweak_checks(reel, want, cuts_p)


def quote(cfg, sel, em):
    """The picked words in script order, [(line id, word id, word)], and {word id: line id} of the struck ones."""
    unresolved = {w["id"] for w in em["words"] if w.get("status") == "unresolved"}
    by_id = {ln["id"]: ln for ln in cfg["lines"]}
    q, struck = [], {}
    for l in sel["lines"]:
        if l.get("drop") or l.get("pick") is None:
            continue
        att = by_id[l["id"]]["attempts"][l["pick"]]
        rm = set(l.get("rm", {}).get(str(l["pick"]), []))
        seq = cfg["takes"][str(att["take"])]["words"]
        for w in att["words"]:
            bw = seq[w["i"]]
            if str(bw["word"]).strip().startswith("[") or bw["id"] in unresolved:
                continue
            if w["i"] in rm:
                struck.setdefault(bw["id"], l["id"])
            else:
                q.append((l["id"], bw["id"], str(bw["word"]).strip()))
    return q, struck


def quote_checks(cfg, sel, em, want):
    q, struck = quote(cfg, sel, em)
    segs = {}
    for w in want:
        segs.setdefault(w["id"], []).append(w)
    line_of = {wid: lid for lid, wid, _ in q}
    out, where = [], lambda lid, wid: "cut-selection.json: %s %s" % (lid, wid)
    for lid, wid, word in q:
        n = len(segs.get(wid, []))
        if n == 0:
            out.append(_hit("quote-missing", "line %s: the word '%s' was picked but is not in the cut." % (lid, word),
                            where(lid, wid)))
        elif n > 1:
            out.append(_hit("quote-twice", "line %s: the word '%s' was picked once but plays twice in the cut "
                            "(pieces %s)." % (lid, word, ", ".join(str(x["seg"] + 1) for x in segs[wid])),
                            where(lid, wid)))
    for w in want:
        if w["id"] in line_of:
            continue
        if w["id"] in struck:
            out.append(_hit("quote-extra", "line %s: the word '%s' was struck but is still in the cut."
                            % (struck[w["id"]], w["word"]), where(struck[w["id"]], w["id"])))
            continue
        near = [x for x in want if x["seg"] == w["seg"] and x["id"] in line_of]
        if near:
            lid = line_of[min(near, key=lambda x: abs(x["src_start"] - w["src_start"]))["id"]]
            out.append(_hit("quote-extra", "line %s: the cut also keeps the word '%s', which is not in the picked "
                            "words (a cut edge has moved)." % (lid, w["word"]), where(lid, w["id"])))
        else:
            out.append(_hit("quote-extra", "the cut keeps the word '%s' (piece %d), which is in no picked line."
                            % (w["word"], w["seg"] + 1), "work/cuts.json: piece %d %s" % (w["seg"] + 1, w["id"])))
    prev = None
    for lid, wid, word in q:
        if len(segs.get(wid, [])) != 1:
            continue
        x = segs[wid][0]
        key = (x["seg"], x["parakeet_start"])   # pieces play in cuts.json order; inside one, by board anchor
        if prev is not None and key < prev[0]:
            out.append(_hit("quote-order", "line %s: the word '%s' plays before '%s' (line %s) in the cut, but the "
                            "picks put it after." % (lid, word, prev[2], prev[1]), where(lid, wid)))
        prev = (key, lid, word)
    return out


def tweak_checks(reel, want, cuts_p):
    p = reel / "tweak-board.config.json"
    if not p.exists():
        return []
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
        tw = [(x["id"], str(x["w"]), float(x["t"])) for x in cfg["words"]]
    except (ValueError, KeyError, TypeError) as e:
        return [_hit("tweak-time", "The Tweak Board file can't be read (%s); rebuild it (make_tweaks.py) from this cut."
                     % e, str(p))]
    if cfg.get("cuts_sha256") != word_map.sha(cuts_p):   # built from an older cut (or unstamped): its times can't match
        return [dict(check="tweak-stale", level="warn", msg=OLD_TWEAK, where=str(p))]
    W, out = {}, []
    for w in want:
        W.setdefault(w["id"], w)
    for wid, word, t in tw:
        where = "tweak-board.config.json: %s" % wid
        w = W.get(wid)
        if w is None:
            out.append(dict(check="tweak-word", level="warn", where=where,
                            msg="The Tweak Board shows '%s' at %.3f s, but the cut map doesn't keep that word; "
                                "check it by ear." % (word, t)))
            continue
        off = abs(t - w["out_anchor"])
        if off > TOL + 1e-9:
            out.append(_hit("tweak-time", "The Tweak Board shows '%s' at %.3f s but the cut has it at %.3f s (%.0f ms "
                            "off; the limit is 6 ms). Rebuild the Tweak Board (make_tweaks.py) from this cut."
                            % (word, t, w["out_anchor"], off * 1000), where))
    return out


def main():
    ensure_utf8_output()
    if len(sys.argv) != 2:
        raise SystemExit("usage: map_check.py <reel_dir>")
    hits = run(dict(reel_dir=sys.argv[1], fps=None, cuts=None, beats=None, render=None))
    work = Path(sys.argv[1]) / "work"
    if work.is_dir():   # H-N1-10: the block reasons, for whoever reports them; never written by run()
        report = {k: [h for h in hits if h["level"] == lv] for k, lv in (("blocks", "block"), ("warns", "warn"))}
        (work / "map_check.json").write_bytes(json.dumps(report, ensure_ascii=False, indent=1).encode("utf-8"))
    for h in hits:
        print("%s  %s  %s  (%s)" % (h["level"].upper(), h["check"], h["msg"], h["where"]))
    blocks = sum(h["level"] == "block" for h in hits)
    skipped = any(h["check"] == "no-word-times" for h in hits)
    print("map check: %s" % ("%d block(s): fix these before rendering" % blocks if blocks
                             else "skipped, no word timings; nothing blocks the render" if skipped
                             else "clean, every kept word is in the word map at the right time"))
    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
