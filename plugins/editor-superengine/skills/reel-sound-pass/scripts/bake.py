"""Bake the client's Sound Board ruling (sound-selection.json) into stems, exactly as the board played it.

  bake.py --reel <reel> [--video <locked.mp4>]

Reads <reel>/sound-selection.json (the board's Send) and the sounds the board used (<reel>/sfx/, <reel>/beds/).
No selection yet (or no sound library): voice only. Writes into <reel>/sound/:
  voice.wav  the picture's own sound, untouched (room tone fills any stretch where it is shorter than the picture)
  sfx.wav    every kept cue, placed to the sample: its file starts peak_s (the cue's, else 0) before the cue's
             time, so the hit lands on the time; a start before 0 trims the file's head instead
  music.wav  the bed (music_fit.place): entry, exit, slide, fades, level, music stops and the speech dip baked in
  sum.wav    voice + sfx + music at unity
  cues/      one clip per cue (gain, length cap and fade baked in, silence up to the exact sample), for an editor
             that places clips on frames, and placement.json (frame, lane, clip) for the same
All float32, 48 kHz, stereo, one length (the picture's). The frame rate is the real one: work/cuts.json fps, else
the picture's.

Checks (any failure stops with exit 1): sum == voice + sfx + music exactly; the sfx stem is exactly its cues; every
cue's own sound is there in its window; the voice is bit-exact to the picture's sound; music is silent inside every
music stop.
"""
import argparse, json, re, sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _media import SR, decode, write_wav, probe, find_picture, workspace, write_json  # noqa: E402
import music_fit, room_tone  # noqa: E402


class BakeError(Exception):
    pass


def lin(db):
    return 10 ** (db / 20)


def read_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def fps_of(reel, picture):
    cuts = read_json(reel / "work" / "cuts.json") or {}
    return float(cuts.get("fps") or probe(picture)["fps"])


def cue_clip(reel, c, fps):
    """(first frame, first sample, clip with sub-frame silence in front, sound only) for one kept cue. The sound starts
    at time - peak_s (the hit lands on time); before 0, its head is trimmed. length_s and the fade count from the
    file's own start."""
    x = decode(reel / "sfx" / c["file"])
    n = len(x)
    if c.get("length_s") and 0 < c["length_s"] * SR < n:
        n = int(round(c["length_s"] * SR))
    x = x[:n] * np.float32(lin(c.get("gain_db") or 0))
    if c.get("end_mode") == "fade":
        f = int(round(min(max(c.get("fade_out_s") or 0.25, 0.02) * SR, n)))
        x[n - f:] *= np.linspace(1, 0, f, dtype=np.float32)[:, None]
    t0 = c["time"] - float(c.get("peak_s") or 0)              # where the file starts
    if t0 < 0:
        x, t0 = x[int(round(-t0 * SR)):], 0.0
    f0 = int(np.floor(t0 * fps + 1e-9))                       # the frame the clip sits on
    s0 = int(round(f0 / fps * SR))
    pad = int(round(t0 * SR)) - s0                            # sub-frame offset as silence
    return f0, s0, np.vstack([np.zeros((pad, 2), np.float32), x]), x


def bake(reel, picture):
    """Writes the stems and returns placement (dict). Raises BakeError on a failed check."""
    reel, picture = Path(reel), Path(picture)
    sel = read_json(reel / "sound-selection.json") or {}
    info = probe(picture)
    dur, fps = info["dur"], fps_of(reel, picture)
    N = int(round(dur * SR))
    out = reel / "sound"
    (out / "cues").mkdir(parents=True, exist_ok=True)

    src = decode(picture)
    pad = max(0, N - len(src))
    voice = src[:N] if not pad else np.vstack([src, room_tone.fill(src, pad)])

    sfx = np.zeros((N, 2), np.float32)
    place, lanes_end, own = [], [], []
    for c in sorted(sel.get("cues", []), key=lambda c: c["time"]):
        f0, s0, clip, x = cue_clip(reel, c, fps)
        lane = next((i for i, e in enumerate(lanes_end) if e <= s0), None)
        if lane is None:
            lane = len(lanes_end)
            lanes_end.append(0)
        lanes_end[lane] = s0 + len(clip)
        name = "%s %s.wav" % (re.sub(r'[\\/:*?"<>|.,]', "", str(c.get("id", ""))),
                              re.sub(r'[\\/:*?"<>|.,]', "", c.get("beat", "")).strip())   # safe file names
        write_wav(out / "cues" / name.strip(), clip)
        e = min(N, s0 + len(clip))
        if e > s0:
            sfx[s0:e] += clip[:e - s0]
        own.append((s0, clip[:max(0, e - s0)]))
        place.append({"id": c.get("id"), "beat": c.get("beat", ""), "file": "cues/" + name.strip(), "frame": f0,
                      "start_sample": s0, "lane": lane, "time": c["time"],
                      "peak_s": float(c.get("peak_s") or 0), "seconds": round(len(clip) / SR, 4),
                      "peak_dbfs": round(float(20 * np.log10(np.abs(x).max() + 1e-12)), 2)})

    b = sel.get("bed") or {}
    write_wav(out / "voice.wav", voice)                       # first: the bed's level is set against it
    music, bed_info = music_fit.place(reel, b, N, dur, out / "voice.wav")
    total = voice + sfx + music
    for name, x in (("sfx", sfx), ("music", music), ("sum", total)):
        write_wav(out / (name + ".wav"), x)

    # ---- checks, on the files as written
    got = {k: decode(out / (k + ".wav")) for k in ("voice", "sfx", "music", "sum")}
    if any(len(v) != N for v in got.values()):
        raise BakeError("a stem is not exactly the picture's length")
    if not np.array_equal(got["sum"], got["voice"] + got["sfx"] + got["music"]):
        raise BakeError("sum.wav is not exactly voice + sfx + music")
    n = min(len(src), N)
    if not np.array_equal(got["voice"][:n], src[:n]):
        raise BakeError("voice.wav is not bit-exact to the picture's sound")
    rebuilt = np.zeros((N, 2), np.float32)
    for s0, clip in own:
        rebuilt[s0:s0 + len(clip)] += clip
    if not np.array_equal(got["sfx"], rebuilt):
        raise BakeError("sfx.wav is not exactly its cues")
    for (s0, clip), p in zip(own, place):
        others = rebuilt.copy()
        others[s0:s0 + len(clip)] -= clip
        alone = got["sfx"][s0:s0 + len(clip)] - others[s0:s0 + len(clip)]
        if len(clip) == 0 or np.abs(clip).max() < 1e-6 or np.abs(alone - clip).max() > 1e-5:
            raise BakeError("cue %s (%s) is missing from the sound effects" % (p["id"], p["beat"]))
    for s in b.get("stops", []) if b.get("file") else []:
        inside = got["music"][int(s["start_s"] * SR) + 1:int(s["end_s"] * SR)]
        if inside.size and np.abs(inside).max() != 0:
            raise BakeError("the music is not silent inside the stop at %.2f s" % s["start_s"])

    placement = {"fps": fps, "sr": SR, "dur": dur, "samples": N, "lanes": len(lanes_end),
                 "voice": {"file": "voice.wav", "room_tone_s": round(pad / SR, 3)},
                 "bed": dict({"file": "music.wav", "frame": 0, "source": None, "gain_db": b.get("gain_db"), "stops": []},
                             **(bed_info or {})),
                 "cues": place}
    write_json(out / "placement.json", placement)
    print("Baked %d sound effect%s on %d lane%s, %s, %.3f s%s." % (
        len(place), "" if len(place) == 1 else "s", len(lanes_end), "" if len(lanes_end) == 1 else "s",
        "music: " + b["file"] if b.get("file") else "no music", N / SR,
        " (room tone filled the last %.2f s)" % (pad / SR) if pad else ""))
    return placement


def main(argv=None):
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Bake the Sound Board ruling into stems.")
    ap.add_argument("--reel", required=True)
    ap.add_argument("--video", help="the picture-locked video (default: the board's picture, else the newest master)")
    a = ap.parse_args(argv)
    reel = workspace()[1] / a.reel
    picture = find_picture(reel, a.video)
    if not reel.is_dir() or not picture or not picture.is_file():
        print("Couldn't find the reel folder or its picture-locked video. Pass --video with the locked video.")
        return 2
    try:
        bake(reel, picture)
    except (BakeError, room_tone.NoRoomTone) as e:
        print("The sound stems failed a check: %s. Nothing was mixed." % e)
        return 1
    return 0


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main))
