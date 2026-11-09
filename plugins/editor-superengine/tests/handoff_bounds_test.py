"""Fast handoff timing regressions; no media tools or third-party dependencies."""
import importlib.util
import json
import sys
import tempfile
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[1] / "skills/pro-editor-handoff/scripts/segments_to_fcpxml.py"
spec = importlib.util.spec_from_file_location("segments_to_fcpxml", SCRIPT)
fcpx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fcpx)
RATE, END = Fraction(30), Fraction(176, 3)


def refused(fn):
    try:
        fn()
    except ValueError as exc:
        assert str(exc) == "An original sound clip extends beyond its source or the reel", exc
    else:
        raise AssertionError("out-of-bounds clip was accepted")


def model(root, *, entry=0, exit_s="58.6667", stops=(), cue=None, source_duration=Fraction(100)):
    for name in ("work", "sound", "beds", "sfx"):
        (root / name).mkdir(exist_ok=True)
    for name in ("aroll.mp4", "beds/bed.wav", "sfx/effect.wav"):
        (root / name).touch()
    documents = {
        "work/cuts.json": {"fps": 30, "segments": [{"out_in_f": 0, "out_out_f": 1760}]},
        "sound/placement.json": {
            "bed": {"source": "beds/bed.wav", "entry_s": str(entry), "exit_s": str(exit_s),
                    "offset_s": 1, "level": {"gain_db_applied": -12}, "stops": stops},
            "cues": [{"id": "effect", "lane": 0}] if cue else []},
        "sound-selection.json": {"cues": [{"id": "effect", "file": "effect.wav", **cue}] if cue else []}}
    for name, data in documents.items():
        (root / name).write_bytes(json.dumps(data).encode("utf-8"))

    def probe(path):
        picture = path.name == "aroll.mp4"
        return dict(path=path.resolve(), duration=END if picture else source_duration,
                    video=picture, audio=True, width=1080 if picture else 0,
                    height=1920 if picture else 0, channels=2, sample_rate=48000, audio_codec="pcm_s16le")

    # Only media inspection is stubbed; load_model reads real placement/cut files.
    with patch.object(fcpx, "probe", side_effect=probe), \
            patch.object(fcpx.fpsmod, "resolve_fps", return_value=30), \
            patch.object(fcpx.fpsmod, "frame_count", return_value=1760):
        return fcpx.load_model(root, root / "aroll.mp4", None)


def walk_1c(root):
    bed = model(root)["beds"][0]
    assert bed["offset"] == 0 and bed["duration"] == END, bed


def bed_real_overrun(root):
    refused(lambda: model(root, exit_s=END + Fraction(1, 50)))  # 0.6 frame


def effect_end_trim(root):
    offset = Fraction(2800001, 48000)
    effect = model(root, cue={"time": float(offset), "length_s": "0.3466458333333333"})["effects"][0]
    assert effect["offset"] == offset, effect
    assert effect["offset"] + effect["duration"] == END, effect


def effect_sample_offset(root):
    effect = model(root, cue={"time": "1.0000208333333333", "length_s": 1})["effects"][0]
    assert effect["offset"] == Fraction(48001, 48000) and effect["duration"] == 1, effect


def source_bounds(root):
    clip = dict(offset=Fraction(1), start=Fraction(2), duration=Fraction(3), fade_out=Fraction(3))
    before = clip.copy()
    fitted = fcpx.fit_clip(clip, END, Fraction(5) - Fraction(1, 75), RATE)
    assert fitted["duration"] == Fraction(224, 75), fitted  # source overrun: 0.4 frame
    assert fitted["fade_out"] == Fraction(224, 75), fitted
    assert clip == before and fitted is not clip, "fit_clip mutated its input"
    refused(lambda: fcpx.fit_clip(clip, END, Fraction(5) - Fraction(1, 15), RATE))
    # A reel trim must not hide a larger source overrun (or vice versa).
    refused(lambda: fcpx.fit_clip(clip, Fraction(4) - Fraction(1, 75), Fraction(5) - Fraction(1, 15), RATE))
    refused(lambda: fcpx.fit_clip(clip, Fraction(4) - Fraction(1, 15), Fraction(5) - Fraction(1, 75), RATE))


def rounded_endpoint_tolerance(root):
    # Grid snapping already fixes the bed. Exercise the rounded endpoint directly
    # too, so removing fit_clip's tolerance rejects this walk-1c-shaped input.
    clip = dict(offset=Fraction(0), start=Fraction(0), duration=Fraction("58.6667"))
    assert fcpx.fit_clip(clip, END, Fraction(100), RATE)["duration"] == END


def half_frame_boundaries(root):
    half = Fraction(1, 60)
    for field in ("offset", "start"):
        clip = dict(offset=Fraction(0), start=Fraction(0), duration=Fraction(1))
        clip[field] = -half
        assert fcpx.fit_clip(clip, END, Fraction(100), RATE)[field] == 0
        clip[field] -= Fraction(1, 48000)
        refused(lambda: fcpx.fit_clip(clip, END, Fraction(100), RATE))
    for reel_end, source_end in ((Fraction(1), END), (END, Fraction(1))):
        clip = dict(offset=Fraction(0), start=Fraction(0), duration=1 + half)
        assert fcpx.fit_clip(clip, reel_end, source_end, RATE)["duration"] == 1
        clip["duration"] += Fraction(1, 48000)
        refused(lambda: fcpx.fit_clip(clip, reel_end, source_end, RATE))


def bed_grid_and_sync(root):
    beds = model(root, entry="0.01", exit_s="1.014", stops=[
        {"start_s": "0.99", "end_s": "1.01"}])["beds"]
    # The second part rounds to zero duration and disappears.
    assert len(beds) == 1, beds
    assert beds[0]["offset"] == 0 and beds[0]["duration"] == 1, beds
    assert beds[0]["start"] == Fraction(99, 100), beds  # same -0.01 s shift as offset
    assert fcpx.on_grid(Fraction(1, 60), RATE) == 0  # ties to even
    assert fcpx.on_grid(Fraction(1, 20), RATE) == Fraction(1, 15)
    assert fcpx.on_grid(Fraction("1.001"), Fraction(30000, 1001)) == Fraction(1001, 1000)


def main():
    failures = []
    with tempfile.TemporaryDirectory(prefix="handoff-bounds-") as home:
        for case in (walk_1c, bed_real_overrun, effect_end_trim, effect_sample_offset,
                     source_bounds, rounded_endpoint_tolerance, half_frame_boundaries, bed_grid_and_sync):
            root = Path(home) / case.__name__
            root.mkdir()
            try:
                case(root)
            except Exception as exc:
                failures.append(case.__name__)
                print(f"FAIL {case.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        return 1
    print("handoff bounds test ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
