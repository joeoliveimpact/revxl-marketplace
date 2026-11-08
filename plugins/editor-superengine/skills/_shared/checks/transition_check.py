"""Pre-render G5 transition check; also runs alone on a reel folder."""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "reel-canvas-build/scripts"))
from win_encoding import ensure_utf8_output
import effect_gate
import transitions
import saved_style

PHASE = "pre"


def run(ctx):
    reel = Path(ctx["reel_dir"])
    where = str(reel / "beat-map-selection.json")
    row = lambda level, msg: {"check": "transition", "level": level, "msg": " ".join(msg.splitlines()), "where": where}
    try:
        read = lambda name: json.loads((reel / name).read_text(encoding="utf-8"))
        bm = read("beat-map-selection.json") if ctx.get("beats") is None else {"beats": ctx["beats"]}
        if ctx.get("beats") is not None and (reel / "beat-map-selection.json").is_file():
            bm["transitions"] = read("beat-map-selection.json").get("transitions")
        cuts = ctx.get("cuts")
        if cuts is None:
            cuts = read("work/cuts.json")
        beats = bm["beats"]
        fps = ctx.get("fps") or cuts.get("fps") or bm.get("fps")
        frames = [s["out_in_f"] for s in cuts["segments"][1:]]
        allowed, _ = saved_style.resolve("transitions.allowed", reel=bm, saved=saved_style.load(reel))
        bad = transitions.options_problems(bm.get("transitions")) + transitions.problems(beats, frames, fps, allowed)
        if not bad:
            bad = effect_gate.check(transitions.spans(beats), frames, str(fps), cuts["segments"][-1]["out_out_f"])
        rows = [row("block", msg) for msg in bad]
        if sum(b.get("transition") is not None for b in beats) > 3:
            rows.append(row("warn", "2-3 usually reads cleanest; keep more if they fit this reel"))
        return rows
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
        return [row("block", "The transition check could not read the reel: " + str(error))]


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reel_dir")
    args = ap.parse_args()
    rows = run({"reel_dir": args.reel_dir})
    for row in rows:
        print(f"{row['level']} transition: {row['msg']} ({row['where']})")
    if not rows:
        print("Transition check: nothing to fix.")
    return int(any(row["level"] == "block" for row in rows))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        print("The transition check stopped; check the reel's work files and try again.")
        sys.exit(1)
