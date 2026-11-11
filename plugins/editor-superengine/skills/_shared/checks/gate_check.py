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
    "face_clear": {"status": "covered", "modules": ("face_text_check.py", "layout_check.py", "overlay_face_check.py")},
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


def selftest():
    import tempfile
    from unittest.mock import patch
    sys.path.insert(0, str(HERE))
    import layout_check
    with tempfile.TemporaryDirectory() as home:
        reel = Path(home)
        (reel / "work").mkdir()
        def save(name, data):
            (reel / name).write_text(json.dumps(data), encoding="utf-8")
        save("work/cuts.json", {"fps": "25/1", "segments": [{"out_in_f": 0, "out_out_f": 100}]})
        head = (200, 600, 880, 1900)
        face = {"track": {"total_f": 100, "keys": [{"f": 0}], "tweens": []},
                "segments": [(0, 100)], "boxes": {0: head}, "median_box": head,
                "layouts": {"full": (0, 0, 1080, 1920)}, "stills": [], "notes": []}
        hook = dict(text="Hi", start_f=0, end_f=50, spoken=False, word_count=1, shown_words=[])
        for start, y, expected in ((0, 610, None), (49, 610, None), (0, 850, "word-covered"),
                                   (50, 610, "word-covered"), (0, 670, "caption-on-face")):
            chunk = dict(i=0, start_f=start, end_f=start + 10, text="Hi", box=[60, y, 960, y + 134],
                         words=[dict(w=0, text="Hi", start_f=start, mark=None, punch=False)])
            save("work/captions.json", {"style": {"style": "clean"}, "chunks": [chunk], "hooks": [hook]})
            with patch.object(layout_check.placer, "load_ctx", return_value=face):
                rows = layout_check.run({"reel_dir": reel})
            if expected is None:
                assert not any(r["level"] == "block" for r in rows), rows
            else:
                assert any(r["check"] == expected for r in rows), (start, y, rows)
        # The Send still names a scene, but this render drew a different-text plain hook.
        save("beat-map-selection.json", {"beats": [{"start_f": 0, "end_f": 100,
             "speech_anchor": {"text": "Claude just killed Instagram."}, "scene": {"id": "hf-hook-title"}}]})
        head = (200, 404, 880, 1580)
        face.update(boxes={0: head}, median_box=head)
        record = dict(schema=1, kind="plain", text="Watch this before you post", start_f=0, end_f=100,
                      box=[90, 280, 930, 445.6], spoken=False, words_shown=0)
        for y, expected in ((1336, None), (850, "word-covered")):
            chunk = dict(i=0, start_f=22, end_f=32, text="Hi", box=[60, y, 960, y + 134],
                         words=[dict(w=0, text="Hi", start_f=22, mark=None, punch=False)])
            # No legacy hooks in this document: ignoring hook.json must fail the low-caption case.
            save("work/captions.json", {"style": {"style": "clean"}, "chunks": [chunk]})
            save("work/hook.json", record)
            with patch.object(layout_check.placer, "load_ctx", return_value=face):
                rows = layout_check.run({"reel_dir": reel})
            if expected is None:
                assert not any(r["level"] == "block" for r in rows), rows
                (reel / "work/hook.json").unlink()
                with patch.object(layout_check.placer, "load_ctx", return_value=face):
                    legacy = layout_check.run({"reel_dir": reel})
                assert any(r["check"] in ("word-covered", "caption-on-face") for r in legacy), legacy
            else:
                assert any(r["check"] == expected for r in rows), rows
        # A saved fitted scene is a hook obstacle even without legacy doc hooks.
        head = (200, 700, 880, 1450)
        face.update(boxes={0: head}, median_box=head)
        record.update(kind="scene", text="Nobody tells you this about editing",
                      end_f=50, box=[60, 220, 960, 660])
        save("work/hook.json", record)
        for start, y, collision in ((0, 300, True), (0, 1336, False), (50, 300, False)):
            chunk = dict(i=0, start_f=start, end_f=start + 10, text="Hi", box=[60, y, 960, y + 134],
                         words=[dict(w=0, text="Hi", start_f=start, mark=None, punch=False)])
            save("work/captions.json", {"style": {"style": "clean"}, "chunks": [chunk]})
            with patch.object(layout_check.placer, "load_ctx", return_value=face):
                rows = layout_check.run({"reel_dir": reel})
            assert any(r["check"] == "text-collision" and r["level"] == "block" for r in rows) == collision, rows
        # Only a kept, fitted hf-hook-title is a scene hook for placement and QA.
        head = (200, 700, 880, 1250)
        face.update(boxes={0: head}, median_box=head)
        for scene_id, y, collision in (("hook-title", 1336, False), ("hf-hook-title", 300, True)):
            beat = dict(start_f=0, end_f=75, scene=dict(id=scene_id,
                        slots={"title": "Nobody tells you this about editing"}, params={}))
            inp = dict(beats=[beat], hooks=[])
            layout_check.compose.place_hook_titles(inp, face)
            save("beat-map-selection.json", {"beats": [beat]})
            save("work/hook.json", layout_check.compose.hook_record(inp))
            chunk = dict(i=0, start_f=10, end_f=20, text="Hi", box=[60, y, 960, y + 134],
                         words=[dict(w=0, text="Hi", start_f=10, mark=None, punch=False)])
            save("work/captions.json", {"style": {"style": "clean"}, "chunks": [chunk]})
            with patch.object(layout_check.placer, "load_ctx", return_value=face):
                rows = layout_check.run({"reel_dir": reel})
            blocks = [r for r in rows if r["level"] == "block"]
            if collision:
                assert any(r["check"] == "text-collision" and r["at"] == 0.4 for r in blocks), rows
            else:
                assert not blocks, rows
    print("selftest ok")
    return 0


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reel_dir", nargs="?", type=Path)
    ap.add_argument("--render", type=Path)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
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
