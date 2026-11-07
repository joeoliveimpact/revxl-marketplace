#!/usr/bin/env python3
"""S7.3: caption placement over a built real 60-second cut (stdlib only).

The lane runs this under its shared heavy lock after merging S7.1:
  <editor python> -X utf8 -I tests/editor/placer_real_test.py --reel-dir <reel> --out <dir>
Only --out and a temporary scratch reel are written. No cut or anchor is made.
Proof colours: yellow = protected head envelope; cyan = placed caption band.
The three required frames and every fallback span's middle frame are drawn.
"""
import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from editor_test_state import isolated_home

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "plugins/editor-superengine/skills/reel-canvas-build/scripts"
sys.path.insert(0, str(SCRIPTS))
import placer  # noqa: E402
import styles  # noqa: E402
import runtime as rt  # noqa: E402  (styles adds the shared scripts directory)

WIDTH, HEIGHT = 1080, 1920


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(doc, indent=2, allow_nan=False) + "\n").encode("utf-8"))


def has_punches(style):
    if not isinstance(style, dict) or style.get("style") != "punch-in":
        return False
    punches = (style.get("moves") or {}).get("word_punches")
    return isinstance(punches, dict) and bool(punches.get("picks"))


def pick_words(reel, cuts, send, rate):
    """Prefer the build's four stress marks; otherwise use four real sentences.

    Unlike styles_render_test.planted_send, retain the supplied words and beats.
    Require room for the complete dramatic gesture, including its hold.
    """
    words = read_json(reel / "work/edit_map.cut.json")["words"]
    sentences = styles.sentence_of([w["word"] for w in words])
    marked = [m["w"] for m in send.get("word_marks", []) if m.get("mark") == "emph"]
    preset = styles.PRESETS["dramatic"]
    length = sum(round(Fraction(str(preset[k])) * rate) for k in ("in_s", "hold_s", "out_s"))
    picks, used, spans = [], set(), []
    for w in dict.fromkeys(marked + list(range(len(words)))):
        start = words[w].get("start")
        if not isinstance(start, (int, float)) or not math.isfinite(start):
            continue
        frame = round(Fraction(str(start)) * rate)
        segment = next((s for s in cuts["segments"] if s["out_in_f"] <= frame < s["out_out_f"]), None)
        if segment is None or sentences[w] in used:
            continue
        on = max(segment["out_in_f"], round((Fraction(str(start)) - styles.ONSET_LEAD) * rate))
        end = on + length
        if end >= segment["out_out_f"] or any(on <= b and end >= a for a, b in spans):
            continue
        picks.append(w)
        used.add(sentences[w])
        spans.append((on, end))
        if len(picks) == 4:
            return sorted(picks)
    raise ValueError("Four word punches in different sentences do not fit this cut; no words were invented.")


def prepare(reel, scratch, cuts, rate):
    """Give the frozen path-based APIs a scratch copy, never modify the input reel."""
    for relative in ("work/cuts.json", styles.ANCHORS, styles.SEND, "work/edit_map.cut.json"):
        destination = scratch / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(reel / relative, destination)
    send = read_json(scratch / styles.SEND)
    planted = not has_punches(send.get("edit_style"))
    if planted:
        picks = pick_words(scratch, cuts, send, rate)
        send["edit_style"] = {"style": "punch-in", "punch_scale": 1.12, "moves": {
            "word_punches": {"preset": "dramatic", "shape": "eased", "picks": picks}}}
        write_json(scratch / styles.SEND, send)
        print("Info: planted punch-in style and four dramatic eased word punches on the scratch reel.")
    saved = reel / styles.TRACK
    if saved.is_file() and not planted:
        track = read_json(saved)
        expected = styles.check_style(send["edit_style"], "reel", len(
            read_json(scratch / "work/edit_map.cut.json")["words"]))
        assert track["style"] == expected, "The saved scale track differs from the Send; plan it again."
        source = "existing scale track"
    else:
        track = styles.plan(scratch, fps=f"{rate.numerator}/{rate.denominator}")
        source = "scratch plan with planted style" if planted else "scratch plan from Send"
    assert has_punches(track["style"]), "The proof needs punch-in style with word punches."
    write_json(scratch / styles.TRACK, track)
    ctx = placer.load_ctx(scratch)
    return ctx, source


def eased(progress, name):
    """The GSAP eases emitted by the frozen styles planner (power2 is cubic)."""
    if name == "none":
        return progress
    if name == "power2.out":
        return 1 - (1 - progress) ** 3
    if name == "power2.inOut":
        return 4 * progress ** 3 if progress < .5 else 1 - (-2 * progress + 2) ** 3 / 2
    if name == "sine.inOut":
        return (1 - math.cos(math.pi * progress)) / 2
    raise ValueError("The proof does not know the track's easing: " + name)


def state_at(track, frame):
    """Compose's full-layout state, including a moving follow-cam origin.

    A tween starting at a key runs after that key, as in compose's timeline.
    """
    key = max((k for k in track["keys"] if k["f"] <= frame), key=lambda k: k["f"])
    values = {"scale": key["scale"], "origin": [key["ox"], key["oy"]], "layout": key["layout"]}
    for prop in values:
        move = max((t for t in track["tweens"] if t["prop"] == prop and t["start_f"] <= frame),
                   key=lambda t: t["start_f"], default=None)
        if move is not None and frame < move["end_f"]:
            if prop == "layout":
                raise ValueError("The proof needs the punch-in style's full layout.")
            p = eased((frame - move["start_f"]) / (move["end_f"] - move["start_f"]), move["ease"])
            a, b = move["from"], move["to"]
            values[prop] = ([x + (y - x) * p for x, y in zip(a, b)]
                            if isinstance(a, (list, tuple)) else a + (b - a) * p)
        elif move is not None and move["end_f"] > key["f"]:
            values[prop] = move["to"]
    return values if values["layout"] == "full" else None


def proof_frames(ctx, words, avoid=()):
    """avoid: (start_f, end_f) fallback spans; a clear frame is preferred, the first match otherwise (lane fix)."""
    track = ctx["track"]
    clear = lambda f: not any(a <= f <= e for a, e in avoid)

    def first(found):
        found = list(found)
        return next((f for f in found if clear(f)), found[0] if found else None)
    states = [(f, state_at(track, f)) for f in range(track["total_f"])]
    plain = first(f for f, s in states if s and math.isclose(s["scale"], 1))
    punch_scale = track["style"]["punch_scale"]
    punched = first(f for f, s in states if s and any(
        i % 2 and a < f < e - 1 for i, (a, e) in enumerate(ctx["segments"]))
        and s["scale"] > 1 and math.isclose(s["scale"], punch_scale))
    peak, peaks = None, []
    for into in track["tweens"]:
        match = re.fullmatch(r"punch (\d+) in", into["id"])
        if not match:
            continue
        back = next((t for t in track["tweens"] if t["id"] == f"punch {match[1]} out"), None)
        if back and into["end_f"] < back["start_f"]:
            for f in range(into["end_f"], back["start_f"]):
                state = state_at(track, f)
                if state and math.isclose(state["scale"], into["to"]):
                    peaks.append(f)
                    break
    peak = first(peaks)
    if peak is None and track["style"]["moves"]["word_punches"]["shape"] == "hard-cut":
        # Identify the word's own hard key, rather than another move's zoom.
        for w in track["style"]["moves"]["word_punches"]["picks"]:
            start = Fraction(str(words[w]["start"]))
            i = next(i for i, (a, e) in enumerate(ctx["segments"]) if a <= round(start * ctx["fps"]) < e)
            f = max(ctx["segments"][i][0], round((start - styles.ONSET_LEAD) * ctx["fps"]))
            state = state_at(track, f)
            baseline = punch_scale if i % 2 else 1
            if (any(k["f"] == f for k in track["keys"]) and state
                    and state["scale"] > baseline and f not in (plain, punched)):
                peak = f
                break
    assert None not in (plain, punched, peak), "The track needs unzoomed, punch-in and word-peak hold frames."
    assert len({plain, punched, peak}) == 3, "The proof needs three different frames."
    return zip("abc", (plain, punched, peak))


def draw_box(box, colour):
    x0, y0, x1, y1 = box
    return f"drawbox=x={x0:.4f}:y={y0:.4f}:w={x1 - x0:.4f}:h={y1 - y0:.4f}:color={colour}:t=5"


def render_proof(master, output, frame, state, head, band):
    scale = state["scale"]
    ox, oy = state["origin"]
    # Full-layout object-fit is identity. Scale the wrapper about its fractional
    # origin, then clip to its original box. RGB avoids chroma-aligned crop offsets.
    graph = (f"select='eq(n,{frame})',scale={WIDTH}:{HEIGHT}:flags=lanczos,format=rgb24,"
             f"scale={round(WIDTH * scale)}:{round(HEIGHT * scale)}:flags=lanczos,"
             f"crop={WIDTH}:{HEIGHT}:{(scale - 1) * ox * WIDTH:.6f}:"
             f"{(scale - 1) * oy * HEIGHT:.6f}:exact=1,setsar=1,"
             + draw_box(head, "yellow") + "," + draw_box(band, "cyan"))
    output.unlink(missing_ok=True)
    result = subprocess.run([str(rt.tool("ffmpeg")), "-hide_banner", "-loglevel", "error", "-y",
                             "-i", str(master), "-an", "-vf", graph, "-frames:v", "1",
                             "-update", "1", str(output)], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", env=rt.python_env(), timeout=180)
    if result.returncode or not output.is_file():
        raise RuntimeError("Could not extract the proof frame: " + result.stderr[-1800:])


def run(reel, out):
    if out == reel or out.is_relative_to(reel) or reel.is_relative_to(out):
        raise ValueError("The proof output and reel folders must be separate, without containing each other.")
    cuts = read_json(reel / "work/cuts.json")
    rate = Fraction(str(cuts["fps"]))
    total = cuts["segments"][-1]["out_out_f"]
    assert rate > 0 and Fraction(total) / rate == 60, "The real-take proof needs the complete 60-second cut."
    anchors = read_json(reel / styles.ANCHORS)
    samples = [p for s in anchors["segments"] for p in s["samples"]]
    assert samples and all(p.get("box") is not None for p in samples), (
        "The proof needs measured head boxes from S7.1; run the face anchors step after making the master.")
    tag = ("%.2fx" % cuts["speed"]).replace(".", "")
    master = reel / "work/renders" / f"master-{tag}.mp4"
    if not master.is_file():
        raise ValueError("The cut master is missing; build the reel before running this proof.")
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "placer-real.json"
    report_path.unlink(missing_ok=True)  # never leave a stale passing report
    with tempfile.TemporaryDirectory(prefix="placer-real-", dir=out) as folder:
        ctx, source = prepare(reel, Path(folder), cuts, rate)
        assert ctx["track"]["total_f"] == total, "The scale track must cover the entire cut."
        spans, bands, stops = [], [], []
        index, start = 0, 0
        while start < total:
            index += 1
            end = min(total, round(index * Fraction(3, 2) * rate)) - 1
            assert end >= start, "The caption window must contain at least one frame."
            span = {"start_f": start, "end_f": end}
            spans.append(span)
            try:
                band = placer.place(ctx, start, end)
            except placer.NoRoom as exc:
                stops.append({**span, "lines": list(exc.lines)})
                for line in exc.lines:
                    print(line, flush=True)
                print(f"Failed span: frames {start} to {end}.", flush=True)
            else:
                bands.append({**span, "box": band})
            start = end + 1
        fallbacks = ctx.get("fallbacks", [])
        if stops:
            write_json(report_path, {"status": "failed", "track_source": source, "spans": spans,
                                    "bands": bands, "NoRoom_count": len(stops), "stops": stops,
                                    "fallback_count": len(fallbacks), "fallbacks": fallbacks,
                                    "notes": ctx["notes"], "frames": []})
        assert not stops, "The whole-take guard requires zero NoRoom stops."
        print(f"Used fallback placement for {len(fallbacks)} of {len(spans)} spans.", flush=True)
        for fallback in fallbacks:
            print(f"Fallback span: frames {fallback['start_f']} to {fallback['end_f']}; "
                  f"head overlap {fallback['overlap_px']:.2f} square pixels.", flush=True)
        notes = ctx["notes"] + placer.ghosts(ctx, bands)
        for note in notes:
            print("Note: " + note, flush=True)
        frames = []
        words = read_json(reel / "work/edit_map.cut.json")["words"]
        checks = list(proof_frames(ctx, words, [(s["start_f"], s["end_f"]) for s in fallbacks]))
        checks.extend((f"fallback-{i}", (span["start_f"] + span["end_f"]) // 2)
                      for i, span in enumerate(fallbacks, 1))
        for label, frame in checks:
            state = state_at(ctx["track"], frame)
            band = next(b["box"] for b in bands if b["start_f"] <= frame <= b["end_f"])
            head = placer.head_box_at(ctx, frame, frame)
            assert head is not None, "Each proof frame must have a mapped head box."
            fallback = next((span for span in fallbacks if span["start_f"] <= frame <= span["end_f"]), None)
            if fallback is None:
                assert not placer.hits(band, head, placer.CAPTION_PAD), (
                    f"The caption band covers the head on proof frame {label}.")
            left, top, right, bottom = placer.SAFE
            assert left <= band[0] < band[2] <= right and top <= band[1] < band[3] <= bottom, (
                f"The caption band leaves the Instagram text-safe box on proof frame {label}.")
            kind = "fallback" if fallback is not None else "clear"
            output = out / f"proof-{label}-{kind}-f{frame}.png"
            render_proof(master, output, frame, state, head, band)
            frames.append({"label": label, "frame": frame, "scale": state["scale"],
                           "origin": state["origin"], "head_box": head, "band": band, "png": output.name,
                           "fallback_span": fallback})
            print(f"Passed proof frame {label} at frame {frame} with {kind} placement; "
                  "head yellow, caption cyan.", flush=True)
        write_json(report_path, {"status": "passed", "fps": str(rate), "total_f": total,
                                "track_source": source, "style": ctx["track"]["style"],
                                "spans": spans, "bands": bands, "NoRoom_count": len(stops),
                                "fallback_count": len(fallbacks), "fallbacks": fallbacks,
                                "notes": notes, "safe_box": placer.SAFE, "frames": frames})
    print(f"Passed placement across {len(spans)} spans with zero NoRoom stops, "
          f"{len(fallbacks)} fallback spans and {len(frames)} proof frames.")
    return 0


@isolated_home()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reel-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    return run(args.reel_dir.resolve(), args.out.resolve())


if __name__ == "__main__":
    try:
        sys.exit(main())
    except styles.Stop as exc:
        for line in exc.lines:
            print(line)
        sys.exit(1)
    except (AssertionError, OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        print("Failed placement proof: " + str(exc), flush=True)
        sys.exit(1)
