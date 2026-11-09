#!/usr/bin/env python3
"""cut-selection.json (the client's ruling from the Cut Board) -> the EDL that gaps.py / render.py consume.

    <editor python> -X utf8 -I selection_to_edl.py <reel>/cut-selection.json <reel>/cut-board.config.json [-o <reel>/work]

Writes work/edl.json ([{src_in, src_out, line, take}] in reel order) and prints the gap command: --internal/--join/
--beat-join from the pause default, --protect ranges for every pause ruled individually (line gaps and internal
silences alike), --words with the take's edit map, --beat from the board's "Pause after commas" and the
selection's --speed. Every drop is a run of removed words (the page seeds the repeat detector's proposals into the
same list) subtracted from the attempt. Mixed rulings print takes.py to plan each recording separately.

Drift guard: every word time the board config carries (takes[n].words[].start, each attempt's words[].s) must sit
within 80 ms of the same word in the take's edit map (its cut anchor, as board_sequence() gives it). One that
doesn't fails with one plain line, exit 3: the board was built on other word times than the cut will use.
"""
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402

# the board fingerprint and the board sequence have one home: build_edit_map.py in this folder (H-R16)
sys.path.insert(0, str(HERE))
from build_edit_map import board_hash, board_sequence  # noqa: E402

DRIFT = 0.080
GAPS = '"${CLAUDE_PLUGIN_ROOT}/skills/reel-first-cuts/scripts/gaps.py"'
TAKES = GAPS.replace("gaps.py", "takes.py")


def cap_of(ms):
    return 9.0 if ms is None else max(0.03, ms / 1000.0)


def drift(cfg, reel_dir, take):
    """The first board word time more than DRIFT off its edit-map word, as one plain line; None when all hold."""
    tk = cfg["takes"][str(take)]
    em = json.loads((reel_dir / tk["edit_map"]).read_text(encoding="utf-8"))
    ref = {x["id"]: x["start"] for x in board_sequence(em)}   # words at parakeet_start, the cut anchor
    times = [(w.get("id"), w["word"], w["start"]) for w in tk["words"]]
    for ln in cfg["lines"]:
        for att in ln["attempts"]:
            if att["take"] == int(take):
                times += [(tk["words"][w["i"]].get("id"), w["w"], w["s"]) for w in att["words"]]
    for wid, word, t in times:
        if wid not in ref:
            return f"the board word '{str(word).strip()}' ({wid}) is not in {tk['edit_map']}: rebuild the board"
        if abs(t - ref[wid]) > DRIFT:
            return (f"the board has '{str(word).strip()}' at {t:.3f} s but {tk['edit_map']} has it at {ref[wid]:.3f} s "
                    f"({abs(t - ref[wid]) * 1000:.0f} ms apart, over {DRIFT * 1000:.0f} ms): rebuild the board")
    return None


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("selection")
    ap.add_argument("config")
    ap.add_argument("-o", "--work", default=None, help="default: the work folder next to the config")
    ap.add_argument("--allow-unhashed", action="store_true",
                    help="run a selection or config made before the word-list hash guard; says so in the output")
    a = ap.parse_args()
    sel = json.loads(Path(a.selection).read_text(encoding="utf-8"))
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    reel_dir = Path(a.config).parent
    work = Path(a.work) if a.work else reel_dir / "work"
    by_id = {ln["id"]: ln for ln in cfg["lines"]}
    default_ms = sel.get("gap_default_ms", cfg["gap_default_ms"])

    kept = [l for l in sel["lines"] if not l.get("drop") and l.get("pick") is not None]
    edl, protect = [], {}
    for l in kept:
        att = by_id[l["id"]]["attempts"][l["pick"]]
        pause = protect.setdefault(att["take"], [])
        n0 = len(edl)   # segments this line emits start here
        j = str(l["pick"])
        drops = []
        # removed words: each run -> [in-point of its first word, in-point of the next kept word)
        rm = set(l.get("rm", {}).get(j, []))
        run = None
        for n, w in enumerate(att["words"]):
            gone = w["i"] in rm
            if gone and run is None:
                run = n
            if not gone and run is not None:
                drops.append([att["words"][run]["cin"], w["cin"]]); run = None
        if run is not None:
            drops.append([att["words"][run]["cin"], att["src_out"]])
        drops.sort()
        merged = []
        for d0, d1 in drops:
            if merged and d0 <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], d1)
            else:
                merged.append([d0, d1])
        t = att["src_in"]
        for d0, d1 in merged:
            if d0 - t > 0.05:
                edl.append(dict(src_in=round(t, 3), src_out=round(d0, 3), line=l["id"]))
            t = max(t, d1)
        if att["src_out"] - t > 0.05:
            edl.append(dict(src_in=round(t, 3), src_out=round(att["src_out"], 3), line=l["id"]))
        # A kept segment ends at the silence island right after its LAST kept word. Audio past that
        # island (the pause before a struck run, a long wordless stretch between two kept words) is a
        # drop, not a pause: seconds of humming loud enough to clear the speech floor were once protected
        # by gaps.py as speech, and the cut ran 42% silence.
        island_after = {}
        for sv in sorted(att.get("silences", []), key=lambda sv: sv["a"]):
            island_after.setdefault(sv.get("after"), sv["a"])   # FIRST island after the word
        for seg in edl[n0:]:
            last = [w for w in att["words"] if w["i"] not in rm and seg["src_in"] <= w["cin"] < seg["src_out"]]
            if not last:
                continue
            isl = island_after.get(last[-1]["i"])
            if isl is not None and seg["src_in"] < isl < seg["src_out"]:
                seg["src_out"] = round(isl, 3)
        # pause rulings inside the read
        for k, sv in enumerate(att.get("silences", [])):
            ms = l.get("sil", {}).get(j, {}).get(str(k), "default")
            if ms != "default":
                pause.append(f"{sv['a'] - 0.05:.3f}:{sv['a'] + 0.05:.3f}:{cap_of(ms):.3f}")
        # pause ruling after the line
        g = l.get("gap_after")
        if g and g.get("mode") == "override" and len(edl) > n0:   # a fully struck line emits nothing, so it owns no boundary
            so = edl[-1]["src_out"]
            pause.append(f"{so - 0.3:.3f}:{so + 0.05:.3f}:{cap_of(g.get('ms')):.3f}")
        for seg in edl[n0:]:
            seg["take"] = att["take"]

    # A fully struck line plays nothing and needs no source guards.
    emitting = {seg["line"] for seg in edl}
    takes = {by_id[l["id"]]["attempts"][l["pick"]]["take"] for l in kept if l["id"] in emitting}
    if not takes:
        sys.exit("REFUSED: the selection emits no cuts (every picked line is struck or dropped).")
    for take in sorted(takes):
        bad = drift(cfg, reel_dir, take)
        if bad:
            print(f"REFUSED: {bad}", file=sys.stderr)
            sys.exit(3)
        ruling_guard(cfg, sel, take, a.allow_unhashed)

    work.mkdir(parents=True, exist_ok=True)
    (work / "edl.json").write_bytes(json.dumps(edl, indent=1).encode("utf-8"))
    take = min(takes)
    src = cfg["takes"][str(take)]["wav"]
    dur = sum(c["src_out"] - c["src_in"] for c in edl)
    label = f"take {take}" if len(takes) == 1 else "takes " + ", ".join(map(str, sorted(takes)))
    print(f"{label} · {len(edl)} cuts · {dur:.1f}s of speech before gaps · source {src}")
    join = default_ms / 1000.0
    cmd = (f'<editor python> -X utf8 -I {GAPS if len(takes) == 1 else TAKES} "{work.as_posix()}" '
           f'--edl "{(work / "edl.json").as_posix()}" '
           f"--internal {join:.3f} --join {join:.3f} --beat-join {max(join, 0.32):.3f}")
    import saved_style
    nudge = saved_style._get(saved_style.load(reel_dir), "cut.nudge_ms")
    if nudge is not None:
        nudge = min(150, max(0, nudge))
        cmd += f" --nudge {nudge / 1000:.3f}"
    if len(takes) == 1:
        cmd += f' --words "{(reel_dir / cfg["takes"][str(take)]["edit_map"]).as_posix()}"'
    else:
        for n in sorted(takes):
            em = reel_dir / cfg["takes"][str(n)]["edit_map"]
            cmd += f' --take "{n}:{em.parent.as_posix()}:{em.as_posix()}"'
    if sel.get("beat_ms") is not None:
        cmd += f" --beat {sel['beat_ms'] / 1000.0:.3f}"
    cmd += f" --speed {sel.get('speed', 1.0)}"
    ranges = protect.get(take, []) if len(takes) == 1 else [f"{n}:{p}" for n in sorted(takes) for p in protect.get(n, [])]
    if ranges:
        cmd += " --protect " + ",".join(ranges)
    print(cmd)
    print("shots: " + (", ".join(f"{l['id']}={l['shot']}" for l in sel["lines"] if l.get("shot")) or "none"))


def ruling_guard(cfg, sel, take, allow_unhashed):

    # Ruling guard: a ruling's indices (rm word i, pick attempt, sil silence k) only mean something against the
    # board it was made on. make_board.py stamps config.takes[n].word_list_hash and config.board_hash; the page
    # copies both into the selection when the ruling starts, never at save.
    want = cfg["takes"][str(take)].get("word_list_hash")
    got = (sel.get("word_list_hash") or {}).get(str(take))
    bwant, bgot = cfg.get("board_hash"), sel.get("board_hash")
    if bwant is not None and bwant != board_hash(cfg):
        sys.exit("REFUSED: cut-board.config.json was edited after make_board.py built it (board_hash no longer matches its contents).")
    # Every mismatch between fingerprints that ARE present is refused first; --allow-unhashed only ever waives
    # absence, never a detected mismatch.
    if None not in (want, got) and got != want:
        sys.exit(f"REFUSED: selection was ruled on word list {got[:12]} but config take {take} is {want[:12]}; "
                 "the board was rebuilt after ruling. Re-rule on the current board.")
    if None not in (bwant, bgot) and bgot != bwant:
        sys.exit(f"REFUSED: selection was ruled on board {bgot[:12]} but config is {bwant[:12]}: its recording, lines, "
                 "attempts or silences changed after ruling. Re-rule on the current board.")
    if None in (want, got, bwant, bgot):
        if not allow_unhashed:
            sys.exit(f"REFUSED: no ruling fingerprint for take {take} (made before the guard). Rebuild the board from an "
                     "edit map and re-rule, or pass --allow-unhashed to run it anyway.")
        print(f"WARNING --allow-unhashed: take {take} ruling indices NOT verified against the board.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("the selection could not be read: " + str(e).splitlines()[0], file=sys.stderr)
        sys.exit(2)
