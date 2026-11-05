"""The music bed's one fit path: where its strongest section starts, where it sits on the cut, its level, and the
fixed dip under speech. Standard library + numpy; bake.py and new_board.py call it.

  suggest_entry(src, sr, cut_len)  the track position (s) where its strongest section starts
  place(reel, bed, N, dur, voice)  (music stem, placement detail) for the board's bed pick
  bed_grid(reel, file)             the bed's beat grid (beat_grid.grid), cached in work/beats/; None: no steady beat

Level: the board's level is relative to the voice, so the applied gain is
(the voice stem's integrated LUFS - the bed's integrated LUFS) + level_db (-18 suggested), both measured the same
way (ffmpeg ebur128, gated BS.1770). The bed's LUFS is the stretch that plays (from offset_s for the bed's play
length); under 3 s, or unmeasurable, the whole track. The bed then sits level_db under the voice in any final, however loud the
recording is. No voice stem, or one that can't be measured: the old anchor, the bed normalised to -14 LUFS.
The bed is never looped: when the track runs out it has already faded out. The cut is never fitted to the bed.
The dip is a fixed gain envelope from the transcript's speech spans (-duck_db inside speech, 80 ms in, 300 ms out,
linear in dB), never a signal-driven compressor. Its exact breakpoints go into placement.json so an editor can
rebuild it as volume keyframes on the original bed file.
Beat-sync (the board's option, off by default): the track start (offset_s) snaps to the nearest beat of the bed's
grid, and when the track would run out before the cut ends it steps back whole bars (4 beats) until it lasts, but
never before the first bar start. A track beat b then plays at reel time entry_s + (b - offset_s). The cut never
moves; only the music does.
"""
import hashlib, json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _media import SR, decode, loudness, write_json  # noqa: E402
import beat_grid  # noqa: E402

REF_LUFS, LEVEL_DB = -14.0, -18.0
DUCK_DB, DUCK_MIN = 6.0, 4.0
ATTACK_S, RELEASE_S = 0.08, 0.3
STEP_S = 0.5    # entry candidates every half second
MIN_PLAY_S = 3.0  # a played stretch shorter than this is measured as the whole track
GAP_S = 0.3     # words closer than this are one stretch of speech


def lin(db):
    return 10 ** (np.asarray(db, np.float64) / 20)


def speech_spans(reel):
    """[{start_s, end_s}] where the voice speaks, in the cut's time, from work/cut/tx-cut.json; None without one."""
    try:
        words = json.loads((Path(reel) / "work" / "cut" / "tx-cut.json").read_text(encoding="utf-8"))["words"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    spans = []
    for w in sorted((w for w in words if w.get("start") is not None and w.get("end") is not None),
                    key=lambda w: w["start"]):
        if spans and w["start"] - spans[-1]["end_s"] < GAP_S:
            spans[-1]["end_s"] = round(max(spans[-1]["end_s"], w["end"]), 3)
        else:
            spans.append({"start_s": round(w["start"], 3), "end_s": round(w["end"], 3)})
    return spans or None


def suggest_entry(src, sr, cut_len):
    """Start (s) of the loudest stretch of min(cut_len, track) seconds, in 0.5 s steps. A window of cut_len that
    fits inside the track always leaves cut_len of track after the entry; a track shorter than the cut starts at 0.
    ponytail: unweighted mean power, not K-weighted short-term loudness; weight it if picks feel bass-heavy."""
    x = np.asarray(src, np.float64)
    b = int(STEP_S * sr)
    nb = len(x) // b
    if nb == 0:
        return 0.0
    p = (x[:nb * b] ** 2).reshape(nb, -1).mean(1)
    w = max(1, min(nb, int(round(cut_len / STEP_S))))
    c = np.concatenate([[0.0], np.cumsum(p)])
    return round(float(np.argmax(c[w:] - c[:-w])) * STEP_S, 3)


def duck_depth(v):
    """(dip in dB, plain note or None): unset is 6; under 4 is raised to 4."""
    d = DUCK_DB if v is None else float(v)
    if d < DUCK_MIN:
        return DUCK_MIN, "The dip under the voice was raised from %g to %g dB, the smallest dip used." % (d, DUCK_MIN)
    return d, None


def keyframes(spans, depth, dur):
    """[{t_s, gain_db}]: the dip's exact breakpoints in reel time, linear in dB between them (0 outside speech).
    Speech stretches whose ramps would overlap stay dipped across the gap."""
    groups = []
    for s in sorted(spans or [], key=lambda s: s["start_s"]):
        a, z = s["start_s"], s["end_s"]
        if groups and a - ATTACK_S <= groups[-1][1] + RELEASE_S:
            groups[-1][1] = max(groups[-1][1], z)
        else:
            groups.append([a, z])
    kf = []
    for a, z in groups:
        kf += [(a - ATTACK_S, 0.0), (a, -depth), (z, -depth), (z + RELEASE_S, 0.0)]
    if not kf:
        return []
    kt, kg = [k[0] for k in kf], [k[1] for k in kf]
    out = [(t, g) for t, g in kf if 0 <= t <= dur]
    if kt[0] < 0:
        out.insert(0, (0.0, float(np.interp(0.0, kt, kg))))
    if kt[-1] > dur:
        out.append((dur, float(np.interp(dur, kt, kg))))
    return [{"t_s": round(t, 4), "gain_db": round(g, 4)} for t, g in out]


def envelope_db(kf, t):
    """The dip in dB at times t, rebuilt from keyframes."""
    if not kf:
        return np.zeros(len(t))
    return np.interp(t, [k["t_s"] for k in kf], [k["gain_db"] for k in kf])


def bed_loudness(path, offset, length):
    """(integrated LUFS, "played"|"whole"): the stretch of the track from offset for length s, else the whole track
    (stretch under MIN_PLAY_S or unmeasurable). The whole track can be -inf (silent)."""
    if length >= MIN_PLAY_S:
        try:
            v = loudness(path, "atrim=start=%.3f:duration=%.3f" % (max(0.0, offset), length))[0]
            if np.isfinite(v) and v > -70:
                return v, "played"
        except (IndexError, ValueError):
            pass
    return loudness(path)[0], "whole"


def bed_grid(reel, file):
    """The beat grid of <reel>/beds/<file>, or None (no steady beat, or it couldn't be read). Cached in
    <reel>/work/beats/<file>.json, keyed by the file's sha256, so the board and the bake read the same grid."""
    path = Path(reel) / "beds" / file
    cache = Path(reel) / "work" / "beats" / (file + ".json")
    try:
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        c = json.loads(cache.read_text(encoding="utf-8")) if cache.is_file() else {}
        if c.get("sha256") == sha:
            return c.get("grid")
        g = beat_grid.grid(path)
    except Exception:  # noqa: BLE001  (no grid is the answer to anything unreadable; never a crash)
        return None
    write_json(cache, {"sha256": sha, "grid": g})
    return g


def snap(reel, b, entry, offset, track_s, cut_end):
    """(track start, beat detail or None) for beat-sync: the nearest beat, then whole bars back until the track lasts
    to cut_end (or the first bar start is reached). Prints a plain line when it moved by bars or found no beat."""
    g = bed_grid(reel, b["file"])
    if not g:
        print("No steady beat was found in %s, so the music starts where the board set it." % b["file"])
        return offset, None
    p, ph, down = g["period_s"], g["phase_s"], g["downbeat_s"]
    o = ph + max(0, round((offset - ph) / p)) * p
    bars = 0
    while entry + track_s - o < cut_end - 1e-6 and o - 4 * p >= down - 1e-6:
        o -= 4 * p
        bars += 1
    if bars:
        print("The music starts %d bar%s earlier so it lasts the whole reel." % (bars, "" if bars == 1 else "s"))
    o = round(o, 4)
    return o, {"bpm": g["bpm"], "period_s": p, "phase_s": ph, "downbeat_s": down, "offset_from_s": offset,
               "offset_s": o}


def place(reel, b, N, dur, voice=None):
    """(music stem float32 N x 2, placement detail dict or None). Entry/exit/offset/fades/stops as the board played
    them, then the level (against the voice stem file `voice`) and the dip. Prints a plain line for a raised dip, a
    missing transcript or a voice that couldn't be measured."""
    stem = np.zeros((N, 2), np.float32)
    if not b or not b.get("file"):
        return stem, None
    path = Path(reel) / "beds" / b["file"]
    src = decode(path)
    t = np.arange(N) / SR
    entry, offset = b.get("entry_s") or 0, b.get("offset_s") or 0
    beat = None
    if b.get("beat_sync"):
        offset, beat = snap(reel, b, entry, offset, len(src) / SR, min(b.get("exit_s") or dur, dur))
    exit_ = min(b.get("exit_s") or dur, dur, entry + len(src) / SR - offset)   # the track's end: never looped
    bed_lufs, scope = bed_loudness(path, offset, exit_ - entry)
    if not np.isfinite(bed_lufs):
        print("The music bed %s is silent, so there is no music." % b["file"])
        return stem, None
    level = LEVEL_DB if b.get("gain_db") is None else float(b["gain_db"])
    voice_lufs = loudness(voice)[0] if voice and Path(voice).is_file() else float("-inf")
    if not np.isfinite(voice_lufs):
        print("The voice track couldn't be measured, so the music level is set against standard loudness instead.")
        voice_lufs = None
    gain = ((REF_LUFS if voice_lufs is None else voice_lufs) - bed_lufs) + level
    pos = np.round((offset + (t - entry)) * SR).astype(np.int64)
    ok = (t >= entry) & (t < exit_) & (pos >= 0) & (pos < len(src))
    stem[ok] = src[pos[ok]]
    env = np.ones(N)
    fi, fo = b.get("fade_in_s") or 0, b.get("fade_out_s") or 0
    if fi > 0:
        env = np.minimum(env, np.clip((t - entry) / fi, 0, 1))
    if fo > 0:                                                # the fade ends where the track does
        env = np.minimum(env, np.clip((exit_ - t) / fo, 0, 1))
    for s in b.get("stops", []):                              # fade out ENDS at start, fade in STARTS at end
        a_, z, sfo, sfi = s["start_s"], s["end_s"], s.get("fade_out_s") or 0, s.get("fade_in_s") or 0
        k = np.ones(N)
        if sfo > 0:
            m = (t >= a_ - sfo) & (t < a_)
            k[m] = (a_ - t[m]) / sfo
        k[(t >= a_) & (t < z)] = 0
        if sfi > 0:
            m = (t >= z) & (t < z + sfi)
            k[m] = (t[m] - z) / sfi
        env = np.minimum(env, k)

    depth, note = duck_depth(b.get("duck_db"))
    if note:
        print(note)
    spans = speech_spans(reel)
    if not spans:
        print("There is no transcript of the cut, so the music won't dip under the voice.")
    kf = keyframes(spans, depth, dur)
    env = env * lin(gain + envelope_db(kf, t))
    stem = (stem * env.astype(np.float32)[:, None]).astype(np.float32)
    info = {"source": "beds/" + b["file"], "entry_s": entry, "exit_s": round(exit_, 4), "offset_s": offset,
            "fade_in_s": fi, "fade_out_s": fo, "stops": b.get("stops", []),
            "level": {"level_db": level, "voice_lufs": voice_lufs, "bed_lufs": bed_lufs,
                      "bed_lufs_scope": scope, "gain_db_applied": round(gain, 3)},
            "duck": {"depth_db": depth, "attack_s": ATTACK_S, "release_s": RELEASE_S, "spans": spans or [],
                     "keyframes": kf},
            "beat": beat}
    return stem, info
