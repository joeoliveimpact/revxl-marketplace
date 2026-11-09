#!/usr/bin/env python3
"""Tweak Board marks (tweak-selection.json in the reel folder) -> a new source-coordinate EDL + the gaps.py
command, ready for Stage 4 and a re-render.

    <editor python> -X utf8 -I tweaks_to_edl.py <reel>/tweak-selection.json <reel>/work \
        [--config <reel>/tweak-board.config.json] [--out <work dir>]

The cut-time -> source-time map is work/cuts.json's frames: a cut-time t inside segment [out_in_f, out_out_f) is
source time src_in_f/fps + (t - out_in_f/fps) * speed. Cut marks are ranges in CUT time; each is mapped back and
subtracted from the segment(s) it falls in. Tighten/loosen marks become --protect ranges around the source moment
(cap = the chosen ms). Notes are printed for the human. Writes <out>/edl.json and prints the gaps.py command with
--words (the take's edit map), --speed (the board's speed, else the cut's) and --beat (the Cut Board's beat_ms from
cut-selection.json next to the selection, else 0.300). Pauses use the Cut Board's selected default, else its
config default; without either they keep gaps.py's defaults. Cut timing uses the active saved style.

Only the segments a mark touches are re-gapped. Every other segment goes in as --hold of its own source span, so
gaps.py keeps it whole and a Send with no marks gives back the cut's own cuts.json. A cut mark touches the segments
its range overlaps; a tighten/loosen mark touches the segments its --protect range overlaps; a note touches none.

Drift guard: every word time in tweak-board.config.json (words[].t, cut time) must sit within 80 ms of that
word's out_start (aligned start) in word_map.build for this cut and edit map; a missing word or drift fails with one plain line, exit 3.
"""
import argparse, json, os, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
sys.path.insert(0, str(HERE))
import word_map  # noqa: E402
from make_tweaks import cut_map  # noqa: E402

DRIFT = 0.080
GAPS = '"${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/gaps.py"'


def to_src(t, cmap, speed):
    for c0, c1, s0, s1 in cmap:
        if word_map.in_span(t, c0, c1):
            return max(s0, min(s1, s0 + (t - c0) * speed))
    if abs(t - cmap[-1][1]) <= word_map.EPS:
        return cmap[-1][3]
    # past either end: the nearer segment edge
    c0, c1, s0, s1 = min(cmap, key=lambda x: min(abs(x[0] - t), abs(x[1] - t)))
    return s0 if abs(c0 - t) < abs(c1 - t) else s1


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("selection")
    ap.add_argument("work")
    ap.add_argument("--config", default=None, help="default: tweak-board.config.json next to the selection")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    sel = json.loads(Path(a.selection).read_text(encoding="utf-8"))
    cfg_p = Path(a.config) if a.config else Path(a.selection).parent / "tweak-board.config.json"
    cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
    if "version" not in sel:
        print("REFUSED: this Tweak Board is from an older round; rebuild it with make_tweaks.py and the next --version, "
              "then ask for a new Send", file=sys.stderr)
        sys.exit(3)
    if sel["version"] != cfg.get("version"):
        print(f"REFUSED: these marks were made on another cut ({sel.get('version')}, the board is {cfg.get('version')}), "
              "so run make_tweaks.py again with the next --version and ask for a new Send", file=sys.stderr)
        sys.exit(3)
    work = Path(a.work)
    cuts = json.loads((work / "cuts.json").read_text(encoding="utf-8"))
    fps, speed = cuts["fps"], cuts["speed"]
    cmap = cut_map(cuts)
    segs = [[s0, s1] for _, _, s0, s1 in cmap]

    em_p = cfg_p.parent / cfg["edit_map"]
    edit_map = json.loads(em_p.read_text(encoding="utf-8"))
    previous_edl = word_map.read_edl(work / "edl.json")
    expected = {}
    for w in word_map.build(cuts, edit_map, previous_edl)["words"]:
        expected.setdefault(w["id"], w["out_start"])
    for w in cfg["words"]:
        if w.get("id") not in expected or abs(w["t"] - expected[w["id"]]) > DRIFT:
            print(f"REFUSED: the Tweak Board has '{w['w']}' at {w['t']:.3f} s in the cut but "
                  + (f"{cfg['edit_map']} puts it at {expected[w['id']]:.3f} s in this cut "
                     f"({abs(w['t'] - expected[w['id']]) * 1000:.0f} ms apart, over {DRIFT * 1000:.0f} ms)"
                     if w.get("id") in expected else f"{cfg['edit_map']} has no such word")
                  + ": rebuild the board with make_tweaks.py", file=sys.stderr)
            sys.exit(3)

    cuts_s, cut_spans, protect, notes, touched = [], [], [], [], set()
    for m in sel.get("marks", []):
        if m["type"] == "cut" and m.get("b") is not None:
            a0, b0 = sorted([m["a"], m["b"]])
            cut_spans.append((a0, b0))
            # a cut range may span a segment join: subtract per segment
            for k, (c0, c1, s0, s1) in enumerate(cmap):
                lo, hi = max(a0, c0), min(b0, c1)
                if hi - lo > 0.005:
                    cuts_s.append([s0 + (lo - c0) * speed, min(s1, s0 + (hi - c0) * speed)])
                    touched.add(k)
        elif m["type"] in ("tight", "loose"):
            st = to_src(m["a"], cmap, speed)
            cap = max(0.03, m.get("ms", 150) / 1000.0)
            protect.append(f"{st - 0.35:.3f}:{st + 0.35:.3f}:{cap:.3f}")
            touched |= {k for k, (s0, s1) in enumerate(segs) if s0 < st + 0.35 and s1 > st - 0.35}
        elif m["type"] == "note":
            notes.append(f"{m['a']:.2f}s  {m.get('text', '')}")
    cuts_s.sort()
    edl, hold = [], []
    for k, (s0, s1) in enumerate(segs):
        if k not in touched:
            edl.append(dict(src_in=round(s0, 6), src_out=round(s1, 6)))
            hold.append(f"{s0:.6f}:{s1:.6f}")
            continue
        t0 = s0
        for c0, c1 in cuts_s:
            if c1 <= t0 or c0 >= s1:
                continue
            if c0 - t0 > 0.04:
                edl.append(dict(src_in=round(t0, 6), src_out=round(c0, 6)))
            t0 = max(t0, c1)
        if s1 - t0 > 0.04:
            edl.append(dict(src_in=round(t0, 6), src_out=round(s1, 6)))
    if previous_edl is not None:
        picked = [(c["src_in"], c["src_out"]) for c in previous_edl]
        # Snapped slivers must not become new picks, including on held segments.
        # Leave holds at their original frame spans so the inward EDL stays held.
        for c in edl:
            s0, s1 = c["src_in"], c["src_out"]
            for w in edit_map["words"]:
                if w.get("status") == "unresolved" or word_map.kept_in(w, s0, s1, fps, picked=picked):
                    continue
                if s0 <= w["start"] < s1 and s1 - w["start"] < 1 / fps + word_map.EPS:
                    c["src_out"] = min(c["src_out"], w["start"])
                if w["start"] < s0 < w["end"] and w["end"] - s0 < 1 / fps + word_map.EPS:
                    c["src_in"] = max(c["src_in"], w["end"])
    out = Path(a.out or a.work); out.mkdir(parents=True, exist_ok=True)
    (out / "edl.json").write_text(json.dumps(edl, indent=1), encoding="utf-8")
    record = work / "tweak-cuts.json"
    try:
        data = json.loads(record.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("invalid tweak-cut record")
        if data.get("version") == 1:
            rounds = {"?": data["words"]}
        elif data.get("version") == 2:
            rounds = data["rounds"]
        else:
            raise ValueError("unknown tweak-cut version")
        if not isinstance(rounds, dict) or any(
                not isinstance(name, str) or not isinstance(words, dict)
                or any(not isinstance(i, str) or not isinstance(w, str) for i, w in words.items())
                for name, words in rounds.items()):
            raise ValueError("invalid tweak-cut rounds")
    except (OSError, ValueError, KeyError, TypeError):
        rounds = {}
    rounds[sel["version"]] = {w["id"]: w["w"] for w in cfg["words"]
                              if any(word_map.in_span(w["t"], a0, b0) for a0, b0 in cut_spans)}
    if any(rounds.values()):
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=work, prefix=".tweak-cuts-", suffix=".tmp", delete=False) as f:
                temp = Path(f.name)
                f.write(json.dumps(dict(version=2, rounds=rounds), ensure_ascii=False, indent=1).encode("utf-8"))
            os.replace(temp, record)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
    else:
        record.unlink(missing_ok=True)
    removed = sum(c1 - c0 for c0, c1 in cuts_s)
    print(f"{len(sel.get('marks', []))} marks: {len(cuts_s)} cut ranges ({removed:.2f}s removed), {len(protect)} pause "
          f"rulings, {len(notes)} notes -> {len(edl)} cuts in {out / 'edl.json'} ({len(hold)} untouched segments held)")
    cut_sel = Path(a.selection).parent / "cut-selection.json"
    cut_sel = json.loads(cut_sel.read_text(encoding="utf-8")) if cut_sel.is_file() else {}
    beat_ms = cut_sel.get("beat_ms")
    cmd = (f'<editor python> -X utf8 -I {GAPS} "{work.as_posix()}" --edl "{(out / "edl.json").as_posix()}" '
           f'--words "{em_p.as_posix()}" --speed {sel.get("speed") or speed} '
           f'--beat {(beat_ms if beat_ms is not None else 300) / 1000:.3f}')
    cut_cfg = Path(a.selection).parent / "cut-board.config.json"
    cut_cfg = json.loads(cut_cfg.read_text(encoding="utf-8")) if cut_cfg.is_file() else {}
    if "gap_default_ms" in cut_sel or "gap_default_ms" in cut_cfg:
        ms = cut_sel.get("gap_default_ms", cut_cfg.get("gap_default_ms"))
        join = 9.0 if ms is None else ms / 1000.0
        cmd += f" --internal {join:.3f} --join {join:.3f}"
    import saved_style
    nudge = saved_style._get(saved_style.load(cfg_p.parent), "cut.nudge_ms")
    if nudge is not None:
        nudge = min(150, max(0, nudge))
        cmd += f" --nudge {nudge / 1000:.3f}"
    if protect:
        cmd += " --protect " + ",".join(protect)
    if hold:
        cmd += " --hold " + ",".join(hold)
    print(cmd)
    for n in notes:
        print("  note:", n)


if __name__ == "__main__":
    main()
