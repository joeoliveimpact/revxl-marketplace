# Changed from shorts-studio gate/check.py (MIT): explicit 20-test coverage table, indexed cut-word sync, stdlib audio measurement and ffmpeg silence detection, saved layouts instead of Apple Vision, warning-only silent holds.
"""The Windows half of the 20-test gate; nothing is written.

python gate_check.py <reel_dir> [--render <mp4>]   exit 1 on any block
python gate_check.py --list                     one line per source test

H-B6: PHASE = "post"; run(ctx) returns [{check, level, msg, where, at}].
ctx = {reel_dir, fps, cuts, beats, render}. Only the two ported tests return
rows. Covered tests belong to their existing modules; skipped tests require
uninstalled image tools or enforce the source creator's taste/brand rules.

Sync uses work/edit_map.cut.json words[w0].start, in OUTPUT seconds, and the
FPS in cuts.json. make_beat_map.build_doc() starts the opening tiled beat at
frame zero to cover the lead-in; only that non-overlay opening is exempt.
Later tiled beats and overlays start at rounded word times. The reference
allows up to three frames early and two late; no other offset is applied.

Silent holds only suggest a cut or B-roll. Like the reference, the threshold
is the 90th percentile of mono 16 kHz, 50 ms RMS levels minus 22 dB, floored
at -55 dB; the minimum hold is 0.2 s. ffmpeg silencedetect measures the spans.
Opening (start <=0.3 s) and closing (end >=duration-0.6 s) silences are exempt.
Intersect each silence with contiguous visible a-roll intervals; covered
time cannot join separate holds. Saved scale_track keys override beat layouts.
Scenes/B-roll cover a-roll except foreground pip. Like compose.py, layout
moves use the higher endpoint's layer at the start, then the destination's
layer at the end; whole-state keys take effect in that same timeline. Without
a saved track or active beat, the default a-roll layout is full. This tests
the declared composition, not whether a face is actually present in footage.
Missing/unreadable media or layout inputs warn that silence was not checked.
"""
import argparse
from array import array
from fractions import Fraction
import json
import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

PHASE = "post"
GATE_TESTS = {
    "words_per_screen": {"status": "skipped", "reason": "Source creator's word-count taste rule does not fit the user's reels."},
    "text_chips_on_speaker": {"status": "skipped", "reason": "Source creator's label-chip taste rule does not fit the user's reels."},
    "not_grey": {"status": "skipped", "reason": "Source creator's colour taste rule does not fit the user's reels."},
    "accent_colours": {"status": "skipped", "reason": "Source creator's brand-colour rule does not fit the user's reels."},
    "graphic_size": {"status": "skipped", "reason": "Source creator's graphic-size taste rule does not fit the user's reels."},
    "not_empty": {"status": "skipped", "reason": "Source creator's graphic-fill taste rule does not fit the user's reels."},
    "text_margin": {"status": "covered", "modules": ("caption_check.py", "layout_check.py")},
    "text_centred": {"status": "skipped", "reason": "Source creator's centred-headline taste rule does not fit the user's reels."},
    "face_clear": {"status": "covered", "modules": ("face_text_check.py", "layout_check.py")},
    "no_camera_zoom": {"status": "skipped", "reason": "Source creator's no-punch-in taste rule does not fit the user's reels."},
    "no_camera_drift": {"status": "skipped", "reason": "Source creator's no-camera-move taste rule does not fit the user's reels."},
    "no_fast_zoom": {"status": "skipped", "reason": "Needs Apple Vision face reading."},
    "no_naked_jump_cut": {"status": "skipped", "reason": "Needs Apple Vision face reading."},
    "face_visible": {"status": "skipped", "reason": "Needs Apple Vision face reading and OpenCV, which the editor does not install."},
    "eyes_on_lens": {"status": "skipped", "reason": "Needs Apple Vision face reading."},
    "no_silent_stare": {"status": "ported"},
    "no_sparkle_stars": {"status": "skipped", "reason": "Source creator's decorative-star taste rule does not fit the user's reels."},
    "pacing": {"status": "covered", "modules": ("pacing_check.py",)},
    "layout_holds": {"status": "skipped", "reason": "Source creator's layout-duration taste rule does not fit the user's reels."},
    "sync": {"status": "ported"},
}
SYNC_EARLY_FRAMES, SYNC_LATE_FRAMES = 3, 2
SILENCE_MIN_S, SILENCE_DB_BELOW_SPEECH = 0.2, 22
SAMPLE_RATE, HOP = 16000, 800
ERRORS = (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError,
          ZeroDivisionError, OverflowError, subprocess.SubprocessError)


def _read(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _row(check, level, msg, where, at=0.0):
    return dict(check=check, level=level, msg=msg, where=str(where), at=float(at))


def _fraction(value):
    if isinstance(value, bool):
        raise ValueError("not a time")
    return Fraction(str(value))


def _sync(reel, beats, rate):
    opening = next((b for b in beats if b.get("layout") != "overlay"), None)
    anchored = [b for b in beats if b.get("speech_anchor") is not None
                and not (b is opening and b.get("start_f") == 0)]
    if not anchored:
        return []
    path = reel / "work/edit_map.cut.json"
    try:
        words = _read(path)["words"]
        if not isinstance(words, list):
            raise ValueError("no words")
    except ERRORS:
        return [_row("sync", "block", "The cut's word times could not be read. Restore the cut word list, "
                     "then check the beat timing again.", path)]
    rows = []
    for beat in anchored:
        at = 0.0
        where = "beat %s" % beat.get("id", "unknown")
        try:
            start = _fraction(beat["start_f"])
            if start < 0 or start.denominator != 1:
                raise ValueError("not a frame")
            at = float(start / rate)
            index = beat["speech_anchor"]["w0"]
            if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(words):
                raise ValueError("no anchor word")
            word_start = _fraction(words[index]["start"])
            if word_start < 0:
                raise ValueError("negative word time")
            offset = start - word_start * rate
        except ERRORS:
            rows.append(_row("sync", "block", "This beat's start or speech word could not be read. "
                             "Update its start and speech word on the Beat Map, then check again.", where, at))
            continue
        if offset < -SYNC_EARLY_FRAMES or offset > SYNC_LATE_FRAMES:
            direction = "late" if offset > 0 else "early"
            rows.append(_row("sync", "block", f"This beat starts {float(abs(offset)):.1f} frames {direction} "
                             "for its speech word. Move its start to no more than three frames early or two frames late.", where, at))
    return rows


def _command(name, *args):
    return subprocess.run([rt.tool(name), *map(str, args)], env=rt.python_env(),
                          capture_output=True, check=True, timeout=120)


def _silences(render):
    info = json.loads(_command("ffprobe", "-v", "error", "-show_entries",
                              "stream=codec_type:format=duration", "-of", "json", render).stdout)
    duration = float(info["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("no duration")
    if not any(s.get("codec_type") == "audio" for s in info["streams"]):
        raise ValueError("no audio")
    raw = _command("ffmpeg", "-nostdin", "-v", "error", "-i", render,
                   "-vn", "-ac", "1", "-ar", SAMPLE_RATE, "-f", "s16le", "-").stdout
    samples = array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    levels = sorted(10 * math.log10(sum(s * s for s in samples[i:i + HOP])
                                   / HOP / 32768 ** 2 + 1e-12)
                    for i in range(0, len(samples) - HOP + 1, HOP))
    if not levels:
        raise ValueError("no audio samples")
    # Linear interpolation matches numpy.percentile(..., 90) in the reference.
    pos = (len(levels) - 1) * .9
    lo, hi = math.floor(pos), math.ceil(pos)
    speech = levels[lo] + (levels[hi] - levels[lo]) * (pos - lo)
    threshold = max(speech - SILENCE_DB_BELOW_SPEECH, -55)
    log = _command("ffmpeg", "-nostdin", "-hide_banner", "-v", "info", "-i", render,
                   "-vn", "-af", f"aformat=channel_layouts=mono,silencedetect=noise={threshold:.6f}dB:d={SILENCE_MIN_S}",
                   "-f", "null", "-").stderr.decode("utf-8", errors="replace")
    spans, start = [], None
    for match in re.finditer(r"\bsilence_(start|end):\s*([+-]?[0-9]+(?:\.[0-9]+)?(?:e[+-]?[0-9]+)?)", log):
        kind, value = match[1], float(match[2])
        if kind == "start":
            start = value
        elif start is not None:
            spans.append((max(0.0, start), min(value, duration)))
            start = None
    if start is not None:
        spans.append((max(0.0, start), duration))
    return [(a, b) for a, b in spans if a > .3 and b < duration - .6
            and b - a >= SILENCE_MIN_S - 1e-6]


def _visible_holds(start, end, beats, track, rate):
    """Split on every relevant frame boundary, then join adjacent visible pieces."""
    moves = [t for t in track.get("tweens", []) if t.get("prop") == "layout"]
    # compose.main_html adds the whole-state sets before the moves. A move's
    # stacking changes therefore win ties on their start/end frames. Its end
    # still applies when an unrelated whole-state key occurred inside it.
    events = [(k["f"], 0, i, k["layout"]) for i, k in enumerate(track.get("keys", []))]
    for i, move in enumerate(moves):
        above = "pip" if "pip" in (move["from"], move["to"]) else move["from"]
        events.extend(((move["start_f"], 1, i * 2, above),
                       (move["end_f"], 1, i * 2 + 1, move["to"])))
    events.sort(key=lambda event: event[:3])
    bounds = {start, end}
    for item in beats:
        bounds.update(float(_fraction(item[k]) / rate) for k in ("start_f", "end_f"))
    bounds.update(float(_fraction(event[0]) / rate) for event in events)
    points = sorted(t for t in bounds if start <= t <= end)
    holds = []
    for a, b in zip(points, points[1:]):
        frame = (a + b) / 2 * float(rate)
        active = [beat for beat in beats if beat["start_f"] <= frame < beat["end_f"]]
        layout = active[-1].get("layout", "full") if active else "full"
        for event in events:
            if event[0] > frame:
                break
            layout = event[3]
        covered = any(beat.get("scene") or beat.get("broll") for beat in active)
        if layout not in ("full", "split", "stack", "pip", "overlay"):
            raise ValueError("unknown layout")
        if covered and layout != "pip":
            continue
        if holds and abs(holds[-1][1] - a) < 1e-9:
            holds[-1][1] = b
        else:
            holds.append([a, b])
    return [(a, b) for a, b in holds if b - a >= SILENCE_MIN_S - 1e-6]


def run(ctx):
    reel = Path(ctx["reel_dir"])
    rows = []
    try:
        cuts = ctx.get("cuts")
        if cuts is None:
            cuts = _read(reel / "work/cuts.json", {})
        rate = _fraction(cuts.get("fps") or ctx.get("fps"))
        if rate <= 0:
            raise ValueError("no frame rate")
        beats = ctx.get("beats")
        if beats is None:
            beats = _read(reel / "beat-map-selection.json", {}).get("beats", [])
        rows.extend(_sync(reel, beats, rate))
    except ERRORS:
        return [_row("sync", "block", "The cut list or Beat Map could not be read. "
                     "Restore them and check the beat timing again.", reel)]
    render = ctx.get("render")
    try:
        if render is None:
            render = max((reel / "renders").glob("* Master - *.mp4"),
                         key=lambda p: (p.stat().st_mtime_ns, p.name), default=None)
        if render is None or not Path(render).is_file():
            raise ValueError("no finished video")
        track = _read(reel / "work/scale_track.json", {})
        holds = [hold for start, end in _silences(render)
                 for hold in _visible_holds(start, end, beats, track, rate)]
        rows.extend(_row("no_silent_stare", "warn", f"The speaker stays on screen without speech for {b - a:.1f} seconds. "
                         "Consider a cut or B-roll here.", render, a) for a, b in holds)
    except ERRORS:
        rows.append(_row("no_silent_stare", "warn", "Silent holds could not be checked. Make the final video, "
                         "check its audio and saved layouts, and check the editor's video tools before trying again.",
                         render or reel / "renders"))
    return rows


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reel_dir", nargs="?", type=Path)
    ap.add_argument("--render", type=Path)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        for name, entry in GATE_TESTS.items():
            detail = " + ".join(entry.get("modules", ())) or entry.get("reason", "runs here")
            print(f"{name} {entry['status']} {detail}")
        return 0
    if args.reel_dir is None:
        ap.error("give a reel folder or use --list")
    rows = run(dict(reel_dir=args.reel_dir, render=args.render))
    for row in rows:
        print(f"{row['level'].upper()}  {row['check']}  {row['msg']}  ({row['where']}, {row['at']:.2f}s)")
    if not rows:
        print("Gate check: no findings.")
    return 1 if any(row["level"] == "block" for row in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
