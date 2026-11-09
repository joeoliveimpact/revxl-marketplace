#!/usr/bin/env python3
"""Check the finished Master's frames, sound and possible picture softness.

Usage: python render_check.py <reel_dir> [--render <mp4>]
Without --render, use the newest renders/* Master - *.mp4 by modification time.
Exit 1 on any block, otherwise 0. The check writes nothing.

H-B6: PHASE = "post"; run(ctx) returns [{check, level, msg, where}], with
ctx = {reel_dir, fps, cuts, beats, render}. Use ctx['render'] when supplied;
cuts and beats may be supplied by the caller, otherwise read from this reel.
Blocks: no-render, frame-count, streams, av-length, fps, sound-changed.
Unreadable inputs block as cuts-unreadable or render-unreadable. Missing or
unreadable original sound warns as sound-unchecked. Softness only warns (soft),
with `at` in seconds, using scale_track warnings or above-ceiling scale spans.
Tools come from the editor runtime; no compose or rendering modules are imported.
"""
import argparse
import json
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

PHASE = "post"
TUNING = HERE.parents[2] / "reel-canvas-build/references/tuning.json"


def row(check, level, msg, where, **extra):
    return dict(check=check, level=level, msg=msg, where=str(where), **extra)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def command(name, *args):
    p = subprocess.run([rt.tool(name), *map(str, args)], env=rt.python_env(),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=600)
    if p.returncode:
        raise ValueError("the media tool could not read the file")
    return p.stdout


def packet_md5(path, stream):
    """Same packet hash as compose: stream copy preserves it, re-encoding changes it."""
    value = command("ffmpeg", "-nostdin", "-v", "error", "-i", path,
                    "-map", "0:" + stream, "-c", "copy", "-f", "md5", "-").strip()
    if not re.fullmatch(r"MD5=[0-9a-fA-F]{32}", value):
        raise ValueError("the sound fingerprint could not be read")
    return value


def audio_source(reel, cuts):
    """Re-derive load_inputs + choose_audio's master-tier path, without heavy imports."""
    tag = ("%.2fx" % cuts["speed"]).replace(".", "")
    master = reel / "work/renders" / ("master-" + tag + ".mp4")
    final = reel / "sound/final.mp4"
    try:
        report = read(reel / "sound/mix-report.json")
    except (OSError, ValueError):
        report = None
    # A passed mix is used only when its video fingerprint matches this cut.
    if isinstance(report, dict) and final.is_file() and report.get("pass") is True:
        if not master.is_file():
            return None  # Cannot establish which sound compose would choose.
        if report.get("video_md5") == packet_md5(master, "v"):
            return final
    return master if master.is_file() else None


def soft_rows(reel, rate, beats):
    path = reel / "work/scale_track.json"
    if not path.is_file():
        return []
    try:
        track, tuning = read(path), read(TUNING)
        ceiling = float(tuning["softness_ceiling"])
        track_rate = Fraction(str(track.get("fps", rate)))
        if ceiling <= 0 or track_rate <= 0:
            raise ValueError("invalid softness ceiling or frame rate")
        samples = [(k["f"], k["scale"]) for k in track.get("keys", [])]
        for t in track.get("tweens", []):
            if t.get("prop") == "scale":
                samples.extend(((t["start_f"], t["from"]), (t["end_f"], t["to"])))
        samples = sorted(set((float(f), float(scale)) for f, scale in samples if float(scale) > ceiling))
        warnings = track.get("warnings") or []
        times = []
        if warnings:
            if not beats:
                try:
                    beats = read(reel / "beat-map-selection.json").get("beats", [])
                except (OSError, ValueError, AttributeError):
                    beats = []
            for warning in warnings:
                if isinstance(warning, dict):
                    if "at" in warning:
                        times.append(float(warning["at"]))
                        continue
                    frame = warning.get("start_f", warning.get("f", 0))
                else:
                    # styles.ceiling_notes emits 'softness: beat <id> reaches <scale>'.
                    match = re.search(r"softness: beat (.+) reaches ([0-9.]+)", str(warning))
                    frame = 0
                    if match:
                        beat = next((b for b in beats if b.get("id") == match[1]), {})
                        start = beat.get("start_f", 0)
                        end = beat.get("end_f", float("inf"))
                        frame = next((f for f, scale in samples if start <= f < end
                                      and abs(scale - float(match[2])) < 1e-4), start)
                times.append(float(frame) / float(track_rate))
        else:
            times = [f / float(track_rate) for f, _ in samples]
        return [row("soft", "warn", "The picture is zoomed past %gx around %g s, so it may look soft. "
                    "Ask Claude to zoom less there if it bothers you." % (ceiling, at), path, at=at)
                for at in times]
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ZeroDivisionError):
        return [row("soft", "warn", "The zoom notes could not be read; rebuild the editing style to check "
                    "whether the picture may look soft.", path)]


def run(ctx):
    reel = Path(ctx["reel_dir"])
    render = ctx.get("render")
    if render is None:
        candidates = [p for p in (reel / "renders").glob("* Master - *.mp4") if p.is_file()]
        render = max(candidates, key=lambda p: (p.stat().st_mtime_ns, p.name), default=None)
    if render is None or not Path(render).is_file():
        return [row("no-render", "block", "There is no finished Master to check; render the Master first.",
                    render or reel / "renders")]
    render = Path(render)
    cuts_path = reel / "work/cuts.json"
    try:
        cuts = ctx.get("cuts")
        if cuts is None:
            cuts = read(cuts_path)
        rate = Fraction(str(cuts["fps"]))
        total = cuts["segments"][-1]["out_out_f"]
        if rate <= 0 or not isinstance(total, int) or total < 0:
            raise ValueError("invalid cut length or frame rate")
    except (OSError, ValueError, KeyError, IndexError, TypeError, ZeroDivisionError):
        return [row("cuts-unreadable", "block", "The cut list cannot be read; make the cut again before "
                    "checking the Master.", cuts_path)]
    out = []
    try:
        info = json.loads(command("ffprobe", "-v", "error", "-count_frames", "-show_entries",
                                  "stream=codec_type,nb_read_frames,avg_frame_rate,duration", "-of", "json", render))
        streams = info["streams"]
        if not isinstance(streams, list):
            raise ValueError("invalid stream list")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return [row("render-unreadable", "block", "The Master could not be opened for checking; check the "
                    "editor setup and render it again.", render)]
    kinds = [s.get("codec_type") for s in streams]
    if len(kinds) != 2 or kinds.count("video") != 1 or kinds.count("audio") != 1:
        out.append(row("streams", "block", "The Master needs exactly one picture track and one sound track; "
                       "render it again.", render))
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is not None:
        try:
            count = int(video["nb_read_frames"])
            if count != total:
                out.append(row("frame-count", "block", "The Master has %d frames, but the cut list calls for "
                               "%d; render it again from this cut." % (count, total), render))
        except (KeyError, ValueError, TypeError):
            out.append(row("frame-count", "block", "The Master's frames could not be counted against the "
                           "cut list's %d frames; render it again." % total, render))
        try:
            got_rate = Fraction(video["avg_frame_rate"])
            # Cuts stores a numeric rate; allow only its floating-point rounding.
            if got_rate <= 0 or abs(float(got_rate - rate)) > 1e-6:
                out.append(row("fps", "block", "The Master runs at %g frames per second, but the cut list "
                               "calls for %g; render it at the cut's rate." % (float(got_rate), float(rate)), render))
        except (KeyError, ValueError, TypeError, ZeroDivisionError):
            out.append(row("fps", "block", "The Master's frame rate could not be read; render it again at "
                           "the cut's frame rate.", render))
    if video is not None and audio is not None:
        try:
            vd, ad = Fraction(video["duration"]), Fraction(audio["duration"])
            if abs(vd - ad) > 1 / rate:
                out.append(row("av-length", "block", "The sound lasts %.3f s and the picture lasts %.3f s, "
                               "more than one frame apart; render them together again." % (float(ad), float(vd)), render))
        except (KeyError, ValueError, TypeError, ZeroDivisionError):
            out.append(row("av-length", "block", "The sound and picture lengths could not be read; render "
                           "them together again.", render))
    if audio is not None:
        try:
            source = audio_source(reel, cuts)
            if source is None:
                raise ValueError("no original sound")
            original = packet_md5(source, "a:0")
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
            out.append(row("sound-unchecked", "warn", "The original sound could not be found or read, so its "
                           "match is unchecked; restore the cut master and sound files to check it.", reel / "work/renders"))
        else:
            try:
                changed = packet_md5(render, "a:0") != original
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                out.append(row("render-unreadable", "block", "The Master's sound could not be checked; "
                               "render it again.", render))
            else:
                if changed:
                    out.append(row("sound-changed", "block", "The Master's sound changed after the sound was "
                                   "chosen; render it again while copying the original sound unchanged.", render))
    return out + soft_rows(reel, rate, ctx.get("beats"))


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reel_dir", type=Path)
    ap.add_argument("--render", type=Path)
    args = ap.parse_args()
    hits = run(dict(reel_dir=args.reel_dir, render=args.render))
    for hit in hits:
        print("%s  %s  %s  (%s)" % (hit["level"].upper(), hit["check"], hit["msg"], hit["where"]))
    blocks = sum(h["level"] == "block" for h in hits)
    print("render check: %d block(s), %d warning(s)" % (blocks, len(hits) - blocks))
    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
