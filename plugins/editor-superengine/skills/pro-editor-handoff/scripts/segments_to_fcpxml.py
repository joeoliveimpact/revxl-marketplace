"""Editable cut points and original sound, expressed in FCPXML 1.10."""
import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE.parents[1] / "reel-canvas-build/scripts"))
import runtime as rt
import fps as fpsmod
from win_encoding import ensure_utf8_output


class Stop(Exception):
    def __init__(self, code, line):
        super().__init__(line)
        self.code = code


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Stop(2, "Check the hand-off options: " + message)


def guarded(fn):
    try:
        ensure_utf8_output()
        return fn()
    except Stop as e:
        print(str(e).splitlines()[0])
        return e.code
    except Exception as e:
        detail = " ".join(str(e).split())[:220]
        print(f"The editor hand-off stopped: {detail or type(e).__name__}.")
        return 1


def read(path, default=None):
    if default is not None and not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def rational(value):
    return Fraction(str(value))


def on_grid(t, rate):
    """Snap to the nearest reel frame, rounding half-frame ties to even."""
    return Fraction(round(t * rate), rate)


def fit_clip(clip, reel_end, source_duration, rate):
    """Return a fitted copy, allowing at most half a frame at either boundary."""
    clip = clip.copy()
    tolerance = Fraction(1, 2) / rate
    error = "An original sound clip extends beyond its source or the reel"
    if clip["offset"] < -tolerance or clip["start"] < -tolerance:
        raise ValueError(error)
    clip["offset"] = max(Fraction(0), clip["offset"])
    clip["start"] = max(Fraction(0), clip["start"])
    # Check both overruns before trimming, so one trim cannot hide the other.
    if clip["offset"] + clip["duration"] - reel_end > tolerance \
            or clip["start"] + clip["duration"] - source_duration > tolerance:
        raise ValueError(error)
    clip["duration"] = min(clip["duration"], reel_end - clip["offset"], source_duration - clip["start"])
    if clip["duration"] <= 0:
        raise ValueError(error)
    for key in ("fade_in", "fade_out"):
        if key in clip:
            clip[key] = min(clip[key], clip["duration"])
    return clip


def stamp(value):
    value = rational(value)
    return f"{value.numerator}/{value.denominator}s"


def seconds(text):
    if not text or not text.endswith("s"):
        raise ValueError("invalid XML time")
    return Fraction(text[:-1])


def uri_path(uri):
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        raise ValueError("media must use a file URI")
    path = url2pathname(parsed.path)
    if parsed.netloc:
        path = "//" + parsed.netloc + path
    return Path(path)


def original(reel, relative, folder):
    path = (reel / relative).resolve()
    if not path.is_relative_to((reel / folder).resolve()) or not path.is_file():
        raise ValueError(f"The original {folder} file is missing or outside its folder")
    return path


def probe(path):
    result = subprocess.run([rt.tool("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    if result.returncode:
        raise ValueError(f"Couldn't read the media in {path.name}")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s["codec_type"] == "video"), {})
    audio = next((s for s in streams if s["codec_type"] == "audio"), {})
    durations = [rational(s["duration_ts"]) * rational(s["time_base"]) for s in streams
                 if s.get("duration_ts") not in (None, "N/A") and s.get("time_base")]
    duration = max(durations) if durations else rational(data["format"]["duration"])
    return {"path": path.resolve(), "duration": duration, "video": bool(video), "audio": bool(audio),
            "width": int(video.get("width", 0)), "height": int(video.get("height", 0)),
            "channels": int(audio.get("channels", 0)), "sample_rate": int(audio.get("sample_rate", 48000)),
            "audio_codec": audio.get("codec_name")}


def bed_parts(bed):
    """Keep the source playhead moving across silent stops, including their edge fades."""
    entry, exit_ = rational(bed["entry_s"]), rational(bed["exit_s"])
    cursor, fade_in = entry, rational(bed.get("fade_in_s") or 0)
    parts = []
    for stop in sorted(bed.get("stops", []), key=lambda s: rational(s["start_s"])):
        a, b = max(entry, rational(stop["start_s"])), min(exit_, rational(stop["end_s"]))
        if b <= a:
            continue
        if a < cursor:
            raise ValueError("Music stops overlap")
        if a > cursor:
            parts.append((cursor, a, fade_in, rational(stop.get("fade_out_s") or 0)))
        cursor, fade_in = b, rational(stop.get("fade_in_s") or 0)
    if cursor < exit_:
        parts.append((cursor, exit_, fade_in, rational(bed.get("fade_out_s") or 0)))
    return parts


def sfx_timing(picked, source_duration):
    """Match cue_clip's 48 kHz trim and onset before its frame-alignment padding."""
    samples = round(source_duration * 48000)
    limit = float(picked.get("length_s") or 0) * 48000
    length = round(limit) if 0 < limit < samples else samples
    t0 = float(picked["time"]) - float(picked.get("peak_s") or 0)
    source_start = round(-t0 * 48000) if t0 < 0 else 0
    offset = 0 if t0 < 0 else round(t0 * 48000)
    duration = Fraction(length - source_start, 48000)
    if duration <= 0:
        raise ValueError("A sound effect finishes before the reel starts")
    fade = Fraction(0)
    if picked.get("end_mode") == "fade":
        fade = min(max(rational(picked.get("fade_out_s") or 0.25), Fraction(1, 50)), duration)
    return {"offset": Fraction(offset, 48000), "start": Fraction(source_start, 48000), "duration": duration,
            "gain": rational(picked.get("gain_db") or 0), "fade_in": Fraction(0), "fade_out": fade, "keys": []}


def load_model(reel, aroll, overlay, captions=None):
    cuts = read(reel / "work/cuts.json")
    rate = fpsmod.as_fraction(fpsmod.resolve_fps(aroll))
    segments = cuts["segments"]
    cursor = 0
    for s in segments:
        if s["out_in_f"] != cursor or s["out_out_f"] <= cursor:
            raise ValueError("The cut segments must be positive and back to back")
        cursor = s["out_out_f"]
    if not cursor or fpsmod.frame_count(aroll) != cursor:
        raise ValueError("The baked a-roll does not match the cut length")
    if abs(float(rate) - float(cuts["fps"])) > 0.001:
        raise ValueError("The cut and baked a-roll frame rates differ")
    assets = {}

    def asset(path):
        path = path.resolve()
        if path not in assets:
            assets[path] = dict(probe(path), id=f"r{len(assets) + 2}")
        return assets[path]["id"]

    ar = asset(aroll)
    picture = assets[aroll.resolve()]
    if (picture["width"], picture["height"]) != (1080, 1920) or not picture["audio"]:
        raise ValueError("The baked a-roll must be 1080x1920 with its own voice")
    ov = asset(overlay) if overlay else None
    cap = asset(captions) if captions else None
    for layer in (overlay, captions):
        if not layer:
            continue
        p = assets[layer.resolve()]
        if (p["width"], p["height"]) != (picture["width"], picture["height"]) or p["audio"] \
                or fpsmod.as_fraction(fpsmod.resolve_fps(layer)) != rate or fpsmod.frame_count(layer) != cursor:
            raise ValueError("The transparent layer does not match the a-roll")
    import compose
    track = read(reel / "work/scale_track.json", {"keys": [], "tweens": [], "style": {}})
    beats = read(reel / "beat-map-selection.json", {}).get("beats", [])
    baked = compose.baked_spans(track, beats, cursor)
    try:
        master_path = compose.require_baked_master(reel, baked, cursor, rate)
    except compose.Stop as e:
        raise Stop(e.code, " ".join(e.lines)) from None
    master = asset(master_path) if master_path else None
    placement = read(reel / "sound/placement.json", {})
    bed = placement.get("bed") or {}
    beds, effects = [], []
    notes = []
    if bed.get("mode") == "carve":
        note = "The music's voice carve is applied only in our render; Resolve gets the simpler dip."
        notes.append(note)
    if bed.get("source"):
        ref = asset(original(reel, bed["source"], "beds"))
        gain = rational(bed["level"]["gain_db_applied"])
        keys = sorted((rational(k["t_s"]), rational(k["gain_db"])) for k in bed.get("duck", {}).get("keyframes", []))
        for a, b, fi, fo in bed_parts(bed):
            # The source-start expression below shifts by exactly the same amount as a.
            a, b = on_grid(a, rate), on_grid(b, rate)
            if b == a:
                continue
            selected = [(t - a, gain + db) for t, db in keys if a <= t <= b]
            # On a split, preserve interpolation at its new boundaries as well as the original volume points.
            for edge in (a, b):
                if keys and keys[0][0] < edge < keys[-1][0] and not any(t == edge - a for t, _ in selected):
                    left = max(k for k in keys if k[0] < edge)
                    right = min(k for k in keys if k[0] > edge)
                    db = left[1] + (right[1] - left[1]) * (edge - left[0]) / (right[0] - left[0])
                    selected.append((edge - a, gain + db))
            beds.append({"ref": ref, "offset": a, "start": rational(bed["offset_s"]) + a - rational(bed["entry_s"]),
                         "duration": b - a, "gain": gain, "fade_in": min(fi, b - a), "fade_out": min(fo, b - a),
                         "keys": sorted(selected), "lane": -1})
    selection = {c["id"]: c for c in read(reel / "sound-selection.json", {}).get("cues", [])}
    for cue in placement.get("cues", []):
        picked = selection[cue["id"]]
        relative = Path(picked["file"])
        if relative.parts[0] != "sfx":
            relative = Path("sfx") / relative
        ref = asset(original(reel, relative, "sfx"))
        source = next(p for p in assets.values() if p["id"] == ref)
        effects.append({"ref": ref, "lane": -2 - int(cue["lane"]), **sfx_timing(picked, source["duration"])})
    for clips in (beds, effects):
        for i, clip in enumerate(clips):
            source = next(p for p in assets.values() if p["id"] == clip["ref"])
            clips[i] = fit_clip(clip, cursor / rate, source["duration"], rate)
    return {"name": reel.name, "rate": rate, "total": cursor, "segments": segments, "assets": list(assets.values()),
            "aroll": ar, "overlay": ov, "captions": cap, "beds": beds, "effects": effects,
            "width": picture["width"], "height": picture["height"], "master": master, "baked_spans": baked,
            "notes": notes}


def db_text(value):
    # dB is a level, not a time; a finite decimal is the editor's interchange representation.
    return f"{float(value):.9f}".rstrip("0").rstrip(".") + "dB"


def build_tree(model):
    root = ET.Element("fcpxml", version="1.10")
    res = ET.SubElement(root, "resources")
    ET.SubElement(res, "format", id="r1", frameDuration=stamp(1 / model["rate"]),
                  width=str(model["width"]), height=str(model["height"]), colorSpace="1-1-1")
    for a in model["assets"]:
        attrs = {"id": a["id"], "name": a["path"].name, "start": "0s", "duration": stamp(a["duration"]),
                 "hasVideo": str(int(a["video"])), "hasAudio": str(int(a["audio"]))}
        if a["video"]:
            attrs["format"] = "r1"
        if a["audio"]:
            attrs.update(audioSources="1", audioChannels=str(a["channels"]), audioRate=str(a["sample_rate"]))
        item = ET.SubElement(res, "asset", attrs)
        ET.SubElement(item, "media-rep", kind="original-media", src=a["path"].as_uri())
    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", name="Editor hand-off")
    project = ET.SubElement(event, "project", name=model["name"])
    seq = ET.SubElement(project, "sequence", format="r1", duration=stamp(model["total"] / model["rate"]),
                        tcStart="0s", tcFormat="NDF", audioLayout="stereo", audioRate="48k")
    spine = ET.SubElement(seq, "spine")
    anchor = ET.SubElement(spine, "asset-clip", ref=model["voice"], name="Voice", offset="0s", start="0s",
                           duration=stamp(model["total"] / model["rate"]), audioRole="dialogue")
    for s in model["segments"]:
        ET.SubElement(anchor, "asset-clip", ref=model["picture"], name="Picture", lane="1",
                      offset=stamp(s["out_in_f"] / model["rate"]), start=stamp(s["out_in_f"] / model["rate"]),
                      duration=stamp((s["out_out_f"] - s["out_in_f"]) / model["rate"]))
    if model["overlay"]:
        ET.SubElement(anchor, "asset-clip", ref=model["overlay"], name="Overlay", lane="2", offset="0s", start="0s",
                      duration=stamp(model["total"] / model["rate"]), srcEnable="video")
    if model.get("captions"):
        ET.SubElement(anchor, "asset-clip", ref=model["captions"], name="Captions", lane="3", offset="0s", start="0s",
                      duration=stamp(model["total"] / model["rate"]), srcEnable="video")
    for span in model.get("baked_spans", []):
        ET.SubElement(anchor, "asset-clip", ref=model["master"], name="Finished picture", lane="4", srcEnable="video",
                      offset=stamp(span["start_f"] / model["rate"]), start=stamp(span["start_f"] / model["rate"]),
                      duration=stamp((span["end_f"] - span["start_f"]) / model["rate"]))
    for clip in model["beds"] + model["effects"]:
        node = ET.SubElement(anchor, "asset-clip", ref=clip["ref"], lane=str(clip["lane"]),
                             offset=stamp(clip["offset"]), start=stamp(clip["start"]), duration=stamp(clip["duration"]),
                             srcEnable="audio", audioRole="music" if clip["lane"] == -1 else "effects")
        volume = ET.SubElement(node, "adjust-volume", amount=db_text(clip["gain"]))
        if clip["keys"] or clip["fade_in"] or clip["fade_out"]:
            param = ET.SubElement(volume, "param", name="amount")
            for tag, key in (("fadeIn", "fade_in"), ("fadeOut", "fade_out")):
                if clip[key]:
                    ET.SubElement(param, tag, type="linear", duration=stamp(clip[key]))
            if clip["keys"]:
                anim = ET.SubElement(param, "keyframeAnimation")
                for t, gain in clip["keys"]:
                    ET.SubElement(anim, "keyframe", time=stamp(t), value=db_text(gain), interp="linear", curve="linear")
    return root


def save_xml(root, out, doctype):
    ET.indent(root, space="  ")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes((f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE {doctype}>\n' +
                     ET.tostring(root, encoding="unicode") + "\n").encode("utf-8"))


def write(reel: Path, aroll: Path, overlay: Path | None, out: Path, captions: Path | None = None,
          *, picture: Path, voice: Path, master_picture: Path | None = None) -> dict:
    model = load_model(reel, aroll, overlay, captions)
    problems = picture_problems(picture, model["total"], model["rate"])
    source = next(a for a in model["assets"] if a["id"] == model["aroll"])
    problems += voice_problems(voice, model["total"], model["rate"], source["channels"])
    if model["baked_spans"]:
        if not master_picture:
            raise ValueError("The baked spans need a picture-only Master copy")
        problems += picture_problems(master_picture, model["total"], model["rate"])
    if problems:
        raise ValueError("; ".join(problems))

    def asset(path):
        ref = f'r{len(model["assets"]) + 2}'
        model["assets"].append(dict(probe(path), id=ref))
        return ref

    model["picture"], model["voice"] = asset(picture), asset(voice)
    unused = {model["aroll"], model["master"]}
    model["master"] = asset(master_picture) if model["baked_spans"] else None
    model["assets"] = [a for a in model["assets"] if a["id"] not in unused]
    save_xml(build_tree(model), out, "fcpxml")
    for note in model["notes"]:
        print(note)
    by_ref = {a["id"]: str(a["path"]) for a in model["assets"]}
    audio_items = {by_ref[model["voice"]]: 1}
    for clip in model["beds"] + model["effects"]:
        path = by_ref[clip["ref"]]
        audio_items[path] = audio_items.get(path, 0) + 1
    return {"segments": len(model["segments"]), "overlay": int(bool(model["overlay"])),
            "captions": int(bool(model["captions"])), "bed_clips": len(model["beds"]),
            "keyframes": sum(len(c["keys"]) for c in model["beds"]), "sfx": len(model["effects"]),
            "format": {"width": model["width"], "height": model["height"], "frameDuration": stamp(1 / model["rate"])},
            "paths": [str(a["path"]) for a in model["assets"]], "audio_items": audio_items,
            "baked_spans": model["baked_spans"], "master": by_ref.get(model["master"]),
            "picture": by_ref[model["picture"]], "voice": by_ref[model["voice"]], "notes": model["notes"]}


def picture_problems(path, total, rate):
    if not path.is_file():
        return ["The referenced Picture file is missing: " + path.name]
    info = probe(path)
    if not info["video"] or info["audio"] or (info["width"], info["height"]) != (1080, 1920) \
            or fpsmod.as_fraction(fpsmod.resolve_fps(path)) != rate or fpsmod.frame_count(path) != total \
            or info["duration"] != total / rate:
        return ["The picture-only file does not match the a-roll frames or duration: " + path.name]
    return []


def voice_problems(path, total, rate, channels=None):
    if not path.is_file():
        return ["The referenced Voice WAV is missing"]
    info = probe(path)
    if path.suffix.lower() != ".wav" or info["video"] or not info["audio"] \
            or info["audio_codec"] != "pcm_s24le" or info["sample_rate"] != 48000 \
            or (channels is not None and info["channels"] != channels) \
            or not 0 <= info["duration"] - total / rate < Fraction(1, 48000):
        return ["The Voice WAV must preserve the channels and cover the reel at 24-bit 48 kHz within one sample"]
    return []


def master_problems(path, total, rate):
    if not path.is_file():
        return ["The referenced Master file is missing"]
    import compose
    if not compose.MASTER_RE.fullmatch(path.name):
        return ["A baked span must reference the finished Master file"]
    try:
        if fpsmod.as_fraction(fpsmod.resolve_fps(path)) != rate or fpsmod.frame_count(path) != total:
            return ["The referenced Master frame count or frame rate does not match the reel"]
    except (OSError, ValueError):
        return ["The referenced Master's frames could not be read"]
    return []


def check(out) -> list[str]:
    problems = []
    try:
        reel = Path(out).resolve().parent.parent
        root = ET.parse(out).getroot()
        if root.tag != "fcpxml" or root.get("version") != "1.10":
            problems.append("The hand-off must be FCPXML 1.10")
        assets = {a.get("id"): a for a in root.findall("resources/asset")}
        formats = {f.get("id"): f for f in root.findall("resources/format")}
        for rep in (el for el in root.iter() if el.get("src") is not None):
            path = uri_path(rep.get("src", ""))
            normal = unquote(rep.get("src", "")).replace("\\", "/").lower()
            if not path.is_file():
                problems.append("Referenced file is missing: " + path.name)
            if path.suffix.lower() == ".srt":
                problems.append("The SRT must stay separate from the FCPXML")
            if "/sound/music.wav" in normal or "/sound/cues/" in normal or "/sound/sfx.wav" in normal:
                problems.append("The hand-off references a rendered sound file")
        seq = root.find(".//sequence")
        fmt = formats[seq.get("format")]
        step = seconds(fmt.get("frameDuration"))
        if step <= 0 or (fmt.get("width"), fmt.get("height")) != ("1080", "1920"):
            problems.append("The hand-off format does not match the master")
        spine, cursor = seq.find("spine"), Fraction(0)
        voices = spine.findall("asset-clip")
        if len(spine) != 1 or len(voices) != 1:
            raise ValueError("The spine must contain exactly one continuous Voice WAV clip")
        first = voices[0]
        total = seconds(seq.get("duration"))
        voice_path = uri_path(assets[first.get("ref")].find("media-rep").get("src"))
        if not voice_path.name.startswith(reel.name + " Voice - ") or any(seconds(first.get(k)) != 0 for k in ("offset", "start")) \
                or seconds(first.get("duration")) != total or first.get("lane") is not None:
            problems.append("The spine must reference the Voice WAV over the whole reel from zero")
        if sum(c.get("ref") == first.get("ref") for c in root.findall(".//asset-clip")) != 1:
            problems.append("The Voice WAV must appear only once in the timeline")
        problems.extend(voice_problems(voice_path, total / step, 1 / step))
        cuts = read(reel / "work/cuts.json")["segments"]
        pictures = first.findall('asset-clip[@lane="1"]')
        if len(pictures) != len(cuts):
            problems.append("The Picture clips must match the cut segments")
        picture_refs = {c.get("ref") for c in pictures}
        if len(picture_refs) != 1:
            problems.append("All cuts must reference the same Picture file")
        for ref in picture_refs:
            path = uri_path(assets[ref].find("media-rep").get("src"))
            if not path.name.startswith(reel.name + " Picture - ") or path.suffix.lower() != ".mp4":
                problems.append("The cuts must reference the Picture mp4")
            problems.extend(picture_problems(path, total / step, 1 / step))
        for index, clip in enumerate(pictures):
            duration = seconds(clip.get("duration"))
            if seconds(clip.get("offset")) != cursor or seconds(clip.get("start")) != cursor or duration <= 0:
                problems.append("The Picture cuts are not back to back in output time")
            if index < len(cuts) and (seconds(clip.get("offset")) != cuts[index]["out_in_f"] * step
                    or duration != (cuts[index]["out_out_f"] - cuts[index]["out_in_f"]) * step):
                problems.append("A Picture clip does not match its cut segment")
            if assets[clip.get("ref")].get("format") != seq.get("format"):
                problems.append("A clip has a format mismatch")
            if (duration / step).denominator != 1:
                problems.append("A Picture cut is not on a frame")
            cursor += duration
        if cursor != total:
            problems.append("The Picture durations do not sum to the reel length")
        for asset in assets.values():
            path = uri_path(asset.find("media-rep").get("src"))
            if path.name.startswith(reel.name + " A-roll - ") or asset.get("hasVideo") == "1" and asset.get("hasAudio") == "1":
                problems.append("The FCPXML must not reference the A-roll mp4 or other combined picture and sound")
        master_refs = set()
        for lane in ("2", "3"):
            for clip in root.findall(f'.//asset-clip[@lane="{lane}"]'):
                if clip.get("srcEnable") != "video" or seconds(clip.get("offset")) != 0 \
                        or seconds(clip.get("start")) != 0 or seconds(clip.get("duration")) != cursor:
                    problems.append("A transparent layer has incorrect frames or includes audio")
                if assets[clip.get("ref")].get("format") != seq.get("format"):
                    problems.append("A transparent layer has a format mismatch")
        for clip in root.findall('.//asset-clip[@lane="4"]'):
            a, start, duration = (seconds(clip.get(k)) for k in ("offset", "start", "duration"))
            if clip.get("srcEnable") != "video" or a != start or a < 0 or duration <= 0 \
                    or a + duration > cursor or (a / step).denominator != 1 or (duration / step).denominator != 1:
                problems.append("A baked Master span has incorrect frames or includes audio")
            if assets[clip.get("ref")].get("format") != seq.get("format"):
                problems.append("A baked Master span has a format mismatch")
            master_refs.add(clip.get("ref"))
        for ref in master_refs:
            path = uri_path(assets[ref].find("media-rep").get("src"))
            if not path.name.startswith(reel.name + " Master Picture - ") or path.suffix.lower() != ".mp4":
                problems.append("A baked Master span must reference the picture-only Master copy")
            problems.extend(picture_problems(path, total / step, 1 / step))
        for clip in root.findall(".//asset-clip"):
            asset = assets[clip.get("ref")]
            if seconds(clip.get("duration")) <= 0 or seconds(clip.get("start")) < 0 \
                    or seconds(clip.get("start")) + seconds(clip.get("duration")) > seconds(asset.get("duration")):
                problems.append("A clip extends beyond its media")
    except Exception as e:
        problems.append("Couldn't check the FCPXML: " + " ".join(str(e).split())[:150])
    return problems


def main():
    ap = Parser(description=__doc__)
    ap.add_argument("--reel-dir", required=True, type=Path)
    ap.add_argument("--aroll", required=True, type=Path)
    ap.add_argument("--picture", required=True, type=Path)
    ap.add_argument("--voice", required=True, type=Path)
    ap.add_argument("--master-picture", type=Path)
    ap.add_argument("--overlay", type=Path)
    ap.add_argument("--captions", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    summary = write(a.reel_dir.resolve(), a.aroll.resolve(), a.overlay.resolve() if a.overlay else None, a.out,
                    a.captions.resolve() if a.captions else None, picture=a.picture.resolve(), voice=a.voice.resolve(),
                    master_picture=a.master_picture.resolve() if a.master_picture else None)
    issues = check(a.out)
    if issues:
        raise Stop(1, "; ".join(issues))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(guarded(main))
