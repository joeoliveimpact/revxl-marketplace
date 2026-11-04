#!/usr/bin/env python3
"""style-decoder — audio layer.

    python styleaudio.py <style-slug> <src-id>

Measured audio facts -> sources/<src-id>/audio.json:
  - loudness timeline (EBU R128 momentary, ~100ms grid) + integrated LUFS
  - music-presence heuristic: energy floor during speech gaps (needs
    sources/<src-id>/transcript.json; without it, speech and music are UNKNOWN)
  - music-bed delta: avg momentary loudness in speech gaps vs during speech
    (a crude ducking signal — positive delta = bed rises when speech stops)
  - SFX transient candidates: momentary-loudness jumps >= JUMP_LU within 300ms,
    timestamps only

Heuristics, deliberately labeled: every derived field carries "method". What
this script cannot know (music genre/vibe, SFX character) stays HUMAN-INPUT in
the spec — nothing here listens, it only measures levels. Contract:
styleaudio-contract.md.

transcript.json may be either word shape: {"words":[{startTimeMs,endTimeMs}]} or the
reel-first-cuts shape {"words":[{start,end}]} (seconds).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stylespec  # noqa: E402  (also puts skills/_shared on sys.path)
from win_encoding import ensure_utf8_output  # noqa: E402

JUMP_LU = 6.0        # momentary jump that flags an SFX transient candidate
GAP_MIN_S = 0.4      # speech gap long enough to sample the bed
MUSIC_FLOOR_LUFS = -35.0


def ebur128_timeline(video: str) -> tuple[list[tuple[float, float]], float | None]:
    """[(t, momentary_lufs)], integrated_lufs."""
    r = subprocess.run(
        [stylespec.tool("ffmpeg"), "-hide_banner", "-i", video, "-af", "ebur128", "-f", "null", "-"],
        capture_output=True, text=True, timeout=600)
    tl = []
    for m in re.finditer(r"t:\s*([0-9.]+)\s+TARGET.*?M:\s*(-?[0-9.]+)", r.stderr):
        tl.append((round(float(m.group(1)), 2), float(m.group(2))))
    integ = None
    matches = re.findall(r"I:\s*(-?[0-9.]+)\s*LUFS", r.stderr)
    if matches:
        integ = float(matches[-1])  # last = final integrated value (early ones are warm-up)
    return tl, integ


def speech_spans(transcript: str) -> list[tuple[float, float]]:
    if not os.path.exists(transcript):
        return []
    with open(transcript, encoding="utf-8") as f:
        words = json.load(f).get("words", [])
    if words and "startTimeMs" not in words[0]:          # reel-first-cuts: seconds
        return [(float(w["start"]), float(w["end"])) for w in words]
    return [(w["startTimeMs"] / 1000, w["endTimeMs"] / 1000) for w in words]


def main() -> None:
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug")
    ap.add_argument("src")
    args = ap.parse_args()

    d = os.path.join(stylespec.style_dir(args.slug), "sources", args.src)
    video = os.path.join(d, "source.mp4")
    if not os.path.exists(video):
        sys.exit(f"no source.mp4 in {d}")

    tl, integrated = ebur128_timeline(video)
    if not tl:
        sys.exit("ebur128 produced no timeline — no audio stream?")

    spans = speech_spans(os.path.join(d, "transcript.json"))

    def in_speech(t: float) -> bool:
        return any(a - 0.05 <= t <= b + 0.05 for a, b in spans)

    # gaps >= GAP_MIN_S between consecutive words, plus the lead-in and outro tail
    # (fast talkers leave no mid-speech gaps — the music bed shows at the edges)
    gaps = []
    dur = stylespec.fingerprint(video).get("duration") or (tl[-1][0] if tl else 0)
    if spans:
        if spans[0][0] >= GAP_MIN_S:
            gaps.append((0.0, spans[0][0]))
        for (a0, a1), (b0, _b1) in zip(spans, spans[1:]):
            if b0 - a1 >= GAP_MIN_S:
                gaps.append((a1, b0))
        if dur - spans[-1][1] >= GAP_MIN_S:
            gaps.append((spans[-1][1], dur))

    gap_m = [m for t, m in tl if any(g0 <= t <= g1 for g0, g1 in gaps) and m > -70]
    speech_m = [m for t, m in tl if in_speech(t) and m > -70]

    music: dict = {"method": "energy floor in speech gaps >= %.0f LUFS" % MUSIC_FLOOR_LUFS}
    if not spans:
        music.update({"present": "UNKNOWN",
                      "note": "no transcript.json — speech not located, so music is unknown"})
    elif not gap_m:
        music.update({"present": "UNKNOWN", "note": "no usable speech gaps"})
    else:
        avg_gap = sum(gap_m) / len(gap_m)
        music["present"] = bool(avg_gap > MUSIC_FLOOR_LUFS)
        music["gap_avg_lufs"] = round(avg_gap, 1)
        if speech_m:
            music["bed_delta_lu"] = round(avg_gap - sum(speech_m) / len(speech_m), 1)

    # transient candidates: big momentary jumps within ~300ms
    transients = []
    for (t0, m0), (t1, m1) in zip(tl, tl[3:]):  # ~300ms apart on the 100ms grid
        if m1 - m0 >= JUMP_LU and m1 > -30:
            if not transients or t1 - transients[-1] > 0.5:
                transients.append(round(t1, 2))

    out = {
        "speech": ({"words": len(spans), "source": "transcript.json"} if spans else
                   {"words": "UNKNOWN", "note": "no transcript — speech not located"}),
        "integrated_lufs": integrated,
        "momentary_grid_s": round(tl[1][0] - tl[0][0], 2) if len(tl) > 1 else None,
        "music": music,
        "sfx_transient_candidates": {
            "method": f"momentary jump >= {JUMP_LU} LU within 300ms",
            "times": transients,
        },
        "timeline_1s": [
            {"t": t, "m": m} for t, m in tl if abs(t - round(t)) < 0.05
        ],
    }
    with open(os.path.join(d, "audio.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"[audio] integrated {integrated} LUFS · music present: {music.get('present')} · "
          f"{len(transients)} transient candidate(s) -> audio.json")


if __name__ == "__main__":
    main()
