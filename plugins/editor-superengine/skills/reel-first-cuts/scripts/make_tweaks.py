#!/usr/bin/env python3
"""Build tweak-board.config.json for the Tweak Board: the rendered cut, its waveform, the cut-time -> source-time
map, and the words in cut time so a mark reads as intent.

    <editor python> -X utf8 -I make_tweaks.py --cut <reel>/work/renders/master-100x.mp4 --work <reel>/work \
        --config <reel>/cut-board.config.json --take 1 [--version v1] -o <reel folder>

The map comes from work/cuts.json exactly, one row per segment: [cut_in, cut_out, src_in, src_out] =
[out_in_f/fps, out_out_f/fps, src_in_f/fps, src_out_f/fps]. A word at source time s in a segment sits at
cut_in + (s - src_in) / speed in the cut. The cut and the edit map are stored relative to the reel folder (<o>);
the board loads them from /videos/<reel>/<path>. The board's speed list opens at the cut's own speed (cuts.json).
Writes <o>/tweak-board.config.json. Peaks: 40 bins/s, max |sample| per bin, normalised.
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402
sys.path.insert(0, str(HERE))
from make_board import reel_rel  # noqa: E402

SPEEDS = [1.0, 1.1, 1.15, 1.2]
SETUP = "The editor's setup isn't finished: its video tools are missing. Run the editor setup (editor-doctor), then try again."
FFMPEG = FFPROBE = None


def die(m):
    print("ERROR: %s" % m, file=sys.stderr)
    raise SystemExit(2)


def find_tools():
    """ffmpeg/ffprobe come from the editor's install (_shared/runtime.py), never PATH."""
    global FFMPEG, FFPROBE
    try:
        FFMPEG, FFPROBE = rt.tool("ffmpeg"), rt.tool("ffprobe")
    except (KeyError, OSError, ValueError):
        die(SETUP)
    if not (Path(FFMPEG).exists() and Path(FFPROBE).exists()):
        die(SETUP)


def peaks(mp4, bins_per_s=40):
    tmp = Path(mp4).with_suffix(".peaks.wav")
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(mp4), "-ac", "1", "-ar", "16000", "-f", "wav", str(tmp)], check=True, timeout=600)
    with wave.open(str(tmp)) as w:
        sr, n = w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    tmp.unlink(missing_ok=True)
    hop = sr // bins_per_s
    nb = len(x) // hop
    p = np.abs(x[: nb * hop]).reshape(nb, hop).max(1)
    p = p / max(p.max(), 1e-6)
    return [round(float(v), 3) for v in p]


def cut_map(cuts):
    """[cut_in, cut_out, src_in, src_out] per cuts.json segment, in seconds, exactly from its frames."""
    fps = cuts["fps"]
    return [[s["out_in_f"] / fps, s["out_out_f"] / fps, s["src_in_f"] / fps, s["src_out_f"] / fps] for s in cuts["segments"]]


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut", required=True, help="the rendered cut, inside the reel folder")
    ap.add_argument("--work", required=True)
    ap.add_argument("--config", required=True, help="the Cut Board's cut-board.config.json")
    ap.add_argument("--take", required=True)
    ap.add_argument("--version", default="v1")
    ap.add_argument("-o", "--out", required=True, help="the reel folder: tweak-board.config.json is written here")
    a = ap.parse_args()
    find_tools()

    out = Path(a.out)
    for p, why in ((Path(a.work) / "cuts.json", "run gaps.py first"), (Path(a.config), "build the Cut Board first"),
                   (Path(a.cut), "render the cut first")):
        if not p.is_file():
            die("%s is missing: %s" % (p.as_posix(), why))
    cuts = json.loads((Path(a.work) / "cuts.json").read_text(encoding="utf-8"))
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    if str(a.take) not in cfg.get("takes", {}):
        die("take %s is not on this Cut Board (takes: %s)" % (a.take, ", ".join(cfg.get("takes", {})) or "none"))
    tk = cfg["takes"][str(a.take)]
    words = [w for w in tk["words"] if not w["word"].startswith("[")]
    fps, speed = cuts["fps"], cuts["speed"]
    cmap = cut_map(cuts)
    cut_words = []
    for c0, c1, s0, s1 in cmap:
        for w in words:
            if s0 <= w["start"] < s1:
                cut_words.append(dict(id=w["id"], w=w["word"].strip(), t=round(c0 + (w["start"] - s0) / speed, 3)))
    pk = peaks(a.cut)
    work = Path(a.work)
    listen = (work / "listen.txt").read_text(encoding="utf-8") if (work / "listen.txt").exists() else ""
    edit_map = reel_rel(Path(a.config).parent / tk["edit_map"], out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "tweak-board.config.json").write_text(json.dumps(dict(
        reel=cfg["reel"], version=a.version, video=reel_rel(a.cut, out), edit_map=edit_map, take=int(a.take),
        duration=round(cmap[-1][1], 6), fps=fps, ship_speed=speed, speed_options=sorted(set(SPEEDS + [speed])),
        bins_per_s=40, peaks=pk, map=cmap, words=cut_words, listen=listen,
        presets=[["Tight", 0], ["150", 150], ["250", 250], ["500", 500], ["Breathe", 800]],
    )), encoding="utf-8")
    print(f"{cfg['reel']} {a.version}: {cmap[-1][1]:.2f}s · {len(cmap)} segments · {len(cut_words)} words · "
          f"peaks {len(pk)} -> {out / 'tweak-board.config.json'}")


if __name__ == "__main__":
    main()
