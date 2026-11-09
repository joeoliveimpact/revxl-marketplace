#!/usr/bin/env python3
"""Stage 4 -> render: write work/word_map.json, where every kept word lands in the cut, before anything renders.

    <editor python> -X utf8 -I word_map.py <reel_dir>

Reads : the edit map the cut was made from (build_edit_map.py: the source word times). With
        <reel>/cut-board.config.json and <reel>/cut-selection.json both present, that is cfg.takes[take].edit_map
        (relative to the reel folder) for the one take the kept lines picked, the map selection_to_edl.py hands
        gaps.py; otherwise work/edit_map.json. And that take's cuts.json (gaps.py snap_cuts: fps, speed, frame
        segments), which sits in the edit map's folder: work/cuts.json for the first take, work/take2/cuts.json for
        take 2 (SKILL.md Stage 0: each take has its own folder, passed to selection_to_edl.py as -o). With no edit
        map there (no word alignment on this computer, e.g. a Mac), that folder's tx.json word times stand in. With
        no word times at all it says so, writes nothing and exits 0: the cut can still render.
Writes: <reel>/work/word_map.json
        {version, cuts, cuts_sha256, edit_map, edit_map_sha256, fps, speed,
         words: [{id, word, seg, src_start, src_end, out_start, out_end, parakeet_start, out_anchor}]}
        (cuts and edit_map are the paths relative to the reel; edit_map is work/tx.json when tx.json stood in)

Cuts with a takes entry read the merged work/cuts.json and each take's map, even for one take and regardless
of the board ruling. edit_map and edit_map_sha256 then hold take-keyed dictionaries; words carry take and
source_id, with id qualified as tN:<source_id>. Plain single-take fields and IDs keep their existing shape.

A word is kept when its source `start` falls inside a segment's source span, except an unpicked onset in the
last frame whose word runs past the segment's end (outward rounding's sliver). work/edl.json supplies the user's
picked source ranges; with no readable EDL, start-based membership applies without a sliver exemption.
`start` (the edit map's aligned start) is the anchor gaps.py places cuts from: overlaps() (gaps.py:146-147) and
keep_edge_words() (gaps.py:160-183) test the edit map's start/end, never parakeet_start, and words with status
"unresolved" (not in the audio) are dropped before any of that (gaps.py:433), so they are dropped here too.
Output time of a source time t in its segment: out_in_f/fps + (t - src_in_f/fps) / speed, speed from cuts.json
(1.0 when absent). out_anchor is the same formula on parakeet_start, the board anchor the Cut Board, the
80 ms drift guard and make_tweaks.py place words from; out_start (the aligned start) is the render map. A word whose start sits in two segments (overlapping segments) is listed once per segment, so
map_check.py can block it. The two sha256 fields are of the input files' bytes: the map is stale once either changes,
and it is stale too once the board points the cut at another edit map or another take's cuts.json.
"""
import hashlib, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402

NO_TIMES = "No word timings on this computer, so the word check was skipped; the cut can still render"

EPS = 0.0005   # times are stored to the millisecond


def in_span(t, a, b):
    """Half-open [a, b): a time on a shared boundary belongs to the span that starts there (H-S17W2-3)."""
    return a - EPS <= t < b - EPS


def kept_in(word, s0, s1, fps, picked=None):
    """Start-based membership; only a known unpicked word can be an outward-rounding sliver."""
    return in_span(word["start"], s0, s1) and not (
        picked is not None and not any(in_span(word["start"], a, b) for a, b in picked)
        and word["end"] > s1 and s1 - word["start"] < 1 / fps + EPS)


def read_edl(path):
    """Parsed user ranges, or None when no readable EDL is known. An empty EDL is known to pick nothing."""
    try:
        edl = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(edl, list) or any(
            not isinstance(c, dict) or not all(isinstance(c.get(k), (int, float)) for k in ("src_in", "src_out"))
            for c in edl):
        return None
    return edl


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(cuts, edit_map, edl=None):
    """The word map's body from parsed cuts, edit map and optional user EDL (no file reads, no hashes)."""
    fps, speed = cuts["fps"], cuts.get("speed", 1.0)
    if "takes" in edit_map:
        out = []
        for k, s in enumerate(cuts["segments"]):
            n = str(s.get("take", 1))
            take_edl = None if edl is None else [c for c in edl if str(c.get("take", 1)) == n]
            one = build(dict(fps=fps, speed=speed, segments=[s]), edit_map["takes"][n], take_edl)
            for w in one["words"]:
                w.update(seg=k, take=int(n), source_id=w["id"], id=word_id(n, w["id"]))
                out.append(w)
        return dict(version=1, fps=fps, speed=speed, words=out)
    words = [w for w in edit_map["words"] if w.get("status") != "unresolved"]
    picked = None if edl is None else [(c["src_in"], c["src_out"]) for c in edl]
    out = []
    for w in words:
        for k, s in enumerate(cuts["segments"]):
            s0, s1, c0 = s["src_in_f"] / fps, s["src_out_f"] / fps, s["out_in_f"] / fps
            if kept_in(w, s0, s1, fps, picked):
                out.append(dict(id=w["id"], word=w["word"].strip(), seg=k, src_start=w["start"], src_end=w["end"],
                                out_start=round(c0 + (w["start"] - s0) / speed, 6),
                                out_end=round(c0 + (w["end"] - s0) / speed, 6), parakeet_start=w["parakeet_start"],
                                out_anchor=round(c0 + (w["parakeet_start"] - s0) / speed, 6)))
    return dict(version=1, fps=fps, speed=speed, words=out)


def word_id(take, ident):
    """Edit-map IDs are local to a recording. Qualify them only for a mixed reel."""
    return "t%s:%s" % (take, ident)


def source_sha(reel, src):
    return {n: sha(Path(reel) / p) for n, p in src.items()} if isinstance(src, dict) else sha(Path(reel) / src)


def board(reel_dir):
    """(cut-board.config.json, cut-selection.json) parsed, or None when the reel has no board ruling."""
    cfg_p, sel_p = Path(reel_dir) / "cut-board.config.json", Path(reel_dir) / "cut-selection.json"
    if not (cfg_p.exists() and sel_p.exists()):
        return None
    return json.loads(cfg_p.read_text(encoding="utf-8")), json.loads(sel_p.read_text(encoding="utf-8"))


def pick_map(reel_dir):
    """The cut's takes maps first, else the board take's map, else work/edit_map.json, relative to the reel.
    A takes cut or mixed ruling returns {take: map}; missing takes or maps raise a plain ValueError or KeyError."""
    p = Path(reel_dir) / "work/cuts.json"
    if p.exists():
        cuts = json.loads(p.read_text(encoding="utf-8"))
        if cuts.get("takes"):
            return {n: t.get("edit_map", (Path(t["work"]) / "edit_map.json").as_posix())
                    for n, t in cuts["takes"].items()}
    b = board(reel_dir)
    if b is None:
        return "work/edit_map.json"
    cfg, sel = b
    by_id = {ln["id"]: ln for ln in cfg["lines"]}
    takes = set()
    for l in sel["lines"]:
        if l.get("drop") or l.get("pick") is None:
            continue
        att = by_id[l["id"]]["attempts"][l["pick"]]
        rm = set(l.get("rm", {}).get(str(l["pick"]), []))
        if any(w["i"] not in rm for w in att["words"]):   # a fully struck line plays nothing (selection_to_edl.py)
            takes.add(str(att["take"]))
    if not takes:
        raise ValueError("the picked lines emit no words")
    if len(takes) > 1:
        return {n: Path(cfg["takes"][n]["edit_map"]).as_posix() for n in sorted(takes, key=int)}
    take = takes.pop()
    if take not in cfg["takes"] or not cfg["takes"][take].get("edit_map"):
        raise ValueError("the Cut Board has no edit map for take %s" % take)
    return Path(cfg["takes"][take]["edit_map"]).as_posix()


def tx_map(tx):
    """An edit map's words from a tx.json, for a computer without word alignment (e.g. a Mac). tx.json has one time
    per word, so the aligned start is its start and the board anchor (parakeet_start) is that same time. Ids follow
    align_words.py (w_<index in tx.json>); "[...]" events and words without a start and an end are left out."""
    out = []
    for i, w in enumerate(tx.get("words") or []):
        t = str(w.get("word", w.get("text", "")))
        if not t.strip().startswith("[") and all(isinstance(w.get(k), (int, float)) for k in ("start", "end")):
            out.append(dict(id="w_%04d" % i, word=t, start=w["start"], end=w["end"], parakeet_start=w["start"]))
    return {"words": out}


def sources(reel_dir, rel):
    """(cuts, words, edit map) for the edit map path pick_map gave: the take's cuts.json and the word list, both
    relative to the reel folder, and that word list as an edit map. The cut sits in the edit map's folder. With no
    edit map there, that folder's tx.json stands in; words and edit map are None when neither has word times."""
    if isinstance(rel, dict):
        paths, maps = {}, {}
        for n, path in rel.items():
            _, src, em = sources(reel_dir, path)
            if src is None:
                raise ValueError("take %s has no word times; transcribe it before checking this mixed cut" % n)
            paths[n], maps[n] = src, em
        return "work/cuts.json", paths, {"takes": maps}
    reel, folder = Path(reel_dir), Path(rel).parent
    cuts = (folder / "cuts.json").as_posix()
    if (reel / rel).exists():
        return cuts, rel, json.loads((reel / rel).read_text(encoding="utf-8"))
    tx = (folder / "tx.json").as_posix()
    if (reel / tx).exists():
        em = tx_map(json.loads((reel / tx).read_text(encoding="utf-8")))
        if em["words"]:
            return cuts, tx, em
    return cuts, None, None


def write(reel_dir):
    """Writes work/word_map.json and returns it; None (nothing written) when there are no word times."""
    cuts, src, em = sources(reel_dir, pick_map(reel_dir))
    if src is None:
        return None
    cuts_p = Path(reel_dir) / cuts
    m = build(json.loads(cuts_p.read_text(encoding="utf-8")), em, read_edl(Path(reel_dir) / "work/edl.json"))
    m = dict(version=m.pop("version"), cuts=cuts, cuts_sha256=sha(cuts_p), edit_map=src,
             edit_map_sha256=source_sha(reel_dir, src), **m)
    (Path(reel_dir) / "work" / "word_map.json").write_bytes(json.dumps(m, ensure_ascii=False, indent=1).encode("utf-8"))
    return m


def main():
    ensure_utf8_output()
    if len(sys.argv) != 2:
        raise SystemExit("usage: word_map.py <reel_dir>")
    reel = Path(sys.argv[1])
    try:
        rel = pick_map(reel)
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise SystemExit("ERROR: can't tell which edit map the cut was made from (%s)" % e)
    cuts, src, _ = sources(reel, rel)
    if src is None:
        print(NO_TIMES)
        return
    if not (reel / cuts).exists():
        raise SystemExit("ERROR: %s is missing: run gaps.py first" % (reel / cuts))
    m = write(reel)
    print("word_map.json: %d kept words in %d segments, speed %s, cut %s, edit map %s" % (
        len(m["words"]), len({w["seg"] for w in m["words"]}), m["speed"], cuts, src))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("the word map could not be written: " + str(e).splitlines()[0], file=sys.stderr)
        sys.exit(2)
