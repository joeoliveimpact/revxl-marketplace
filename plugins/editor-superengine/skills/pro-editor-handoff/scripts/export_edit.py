# Changed from shorts-studio scripts/export_edit.py (MIT): use cut frames and original sound, generate subtitles, remove rendering and muxing.
"""FCP7 timeline export and frame-accurate SRT captions for a finished reel."""
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import segments_to_fcpxml as fcpx


def reel_rate(reel):
    # Read the real cut master; cuts.json historically stores an inexact float at NTSC rates.
    cuts = fcpx.read(reel / "work/cuts.json")
    tag = ("%.2fx" % cuts.get("speed", 1)).replace(".", "")
    master = reel / "work/renders" / f"master-{tag}.mp4"
    return fcpx.fpsmod.as_fraction(fcpx.fpsmod.resolve_fps(master))


def milliseconds(frame, rate):
    return math.floor(Fraction(int(frame)) * 1000 / rate + Fraction(1, 2))


def timecode(ms):
    if ms < 0:
        raise ValueError("A caption starts before the reel")
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    seconds, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def write_srt(reel, out):
    rate = reel_rate(reel)
    chunks = [c for c in fcpx.read(reel / "work/captions.json", {}).get("chunks", []) if c.get("text", "").strip()]
    entries = []
    for i, c in enumerate(chunks):
        end = min(c["end_f"], chunks[i + 1]["start_f"]) if i + 1 < len(chunks) else c["end_f"]
        start_ms, end_ms = milliseconds(c["start_f"], rate), milliseconds(end, rate)
        if start_ms >= end_ms:
            raise ValueError("A caption has no time after removing overlaps")
        text = c["text"].strip().replace("\r\n", "\n").replace("\r", "\n")
        entries.append(f"{i + 1}\n{timecode(start_ms)} --> {timecode(end_ms)}\n{text}\n\n")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes("".join(entries).encode("utf-8"))
    return {"entries": len(entries)}


def srt_entries(path):
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()
    if not text:
        return []
    entries = []
    pattern = r"(\d{2,}):([0-5]\d):([0-5]\d),(\d{3}) --> (\d{2,}):([0-5]\d):([0-5]\d),(\d{3})"
    for block in re.split(r"\n\s*\n", text):
        lines = block.splitlines()
        match = re.fullmatch(pattern, lines[1]) if len(lines) >= 3 else None
        if not match or not "\n".join(lines[2:]).strip():
            raise ValueError("A subtitle entry has an invalid timecode or no words")
        values = list(map(int, match.groups()))
        times = [(v[0] * 3600 + v[1] * 60 + v[2]) * 1000 + v[3] for v in (values[:4], values[4:])]
        entries.append((int(lines[0]), *times))
    return entries


def check_srt(path) -> list[str]:
    problems, previous = [], -1
    try:
        for i, (index, start, end) in enumerate(srt_entries(Path(path)), 1):
            if index != i:
                problems.append("Subtitle indices must run from 1 without gaps")
            if start >= end or start < previous:
                problems.append("Subtitle times are reversed or overlap")
            previous = end
    except Exception as e:
        problems.append("Couldn't check the captions: " + " ".join(str(e).split())[:150])
    return problems


def node(parent, tag, text=None, **attrs):
    el = ET.SubElement(parent, tag, attrs)
    if text is not None:
        el.text = str(text)
    return el


def write_fcp7(reel, aroll, overlay, out, captions=None):
    model = fcpx.load_model(reel, aroll, overlay, captions)
    root = ET.Element("xmeml", version="4")
    seq = node(root, "sequence", id="seq")
    node(seq, "name", reel.name)
    node(seq, "duration", model["total"])
    rate = model["rate"]

    def add_rate(parent):
        r = node(parent, "rate")
        node(r, "timebase", round(rate))
        node(r, "ntsc", "TRUE" if rate.denominator == 1001 and rate.numerator % 1000 == 0 else "FALSE")

    add_rate(seq)
    media = node(seq, "media")
    video, audio = node(media, "video"), node(media, "audio")
    audio_format = node(node(audio, "format"), "samplecharacteristics")
    node(audio_format, "depth", 16)
    node(audio_format, "samplerate", 48000)
    group = node(node(audio, "outputs"), "group")
    node(group, "index", 1)
    node(group, "numchannels", 2)
    node(group, "downmix", 0)
    for channel in (1, 2):
        node(node(group, "channel"), "index", channel)
    fmt = node(node(video, "format"), "samplecharacteristics")
    add_rate(fmt)
    node(fmt, "width", model["width"])
    node(fmt, "height", model["height"])
    node(fmt, "pixelaspectratio", "square")
    v1, v2, v3 = node(video, "track"), node(video, "track"), node(video, "track")
    a1, a2 = node(audio, "track"), node(audio, "track")
    used, serial = set(), 0
    assets = {a["id"]: a for a in model["assets"]}

    def file_ref(parent, ref):
        asset = assets[ref]
        f = node(parent, "file", id=ref)
        if ref in used:
            return
        used.add(ref)
        node(f, "name", asset["path"].name)
        node(f, "pathurl", asset["path"].as_uri())
        add_rate(f)
        node(f, "duration", round(asset["duration"] * rate))
        m = node(f, "media")
        if asset["video"]:
            sc = node(node(m, "video"), "samplecharacteristics")
            add_rate(sc)
            node(sc, "width", asset["width"])
            node(sc, "height", asset["height"])
            node(sc, "pixelaspectratio", "square")
        if asset["audio"]:
            au = node(m, "audio")
            sc = node(au, "samplecharacteristics")
            node(sc, "depth", 16)
            node(sc, "samplerate", asset["sample_rate"])
            node(au, "channelcount", asset["channels"])

    def item(track, ref, start, end, source_in, channel=None, gain=None, fade_out=0):
        nonlocal serial
        serial += 1
        clip = node(track, "clipitem", id=f"clip-{serial}")
        node(clip, "name", assets[ref]["path"].name)
        node(clip, "enabled", "TRUE")
        node(clip, "duration", round(assets[ref]["duration"] * rate))
        add_rate(clip)
        for key, value in (("start", start), ("end", end), ("in", source_in), ("out", source_in + end - start)):
            node(clip, key, value)
        file_ref(clip, ref)
        if channel is not None:
            src = node(clip, "sourcetrack")
            node(src, "mediatype", "audio")
            node(src, "trackindex", channel)
        if gain is not None:
            effect = node(node(clip, "filter"), "effect")
            for key, value in (("name", "Audio Levels"), ("effectid", "audiolevels"), ("effectcategory", "audiolevels"),
                               ("effecttype", "audiolevels"), ("mediatype", "audio")):
                node(effect, key, value)
            param = node(effect, "parameter")
            node(param, "parameterid", "level")
            node(param, "name", "Level")
            level = f"{10 ** (float(gain) / 20):.12g}"
            if fade_out:
                fade_frames = min(end - start, max(1, round(fade_out * rate)))
                points = {source_in: level, source_in + end - start - fade_frames: level, source_in + end - start: "0"}
                for frame, value in sorted(points.items()):
                    key = node(param, "keyframe")
                    node(key, "when", frame)
                    node(key, "value", value)
            else:
                node(param, "value", level)
        return clip

    def link_items(items):
        for clip in items:
            for peer in items:
                link = node(clip, "link")
                node(link, "linkclipref", peer.get("id"))
                node(link, "groupindex", 1)

    voice_channels = assets[model["aroll"]]["channels"]
    for channel, track in enumerate((a1, a2), 1):
        node(track, "outputchannelindex", channel)
        if channel == 1 and voice_channels == 1:
            node(track, "outputchannelindex", 2)

    for s in model["segments"]:
        a, b = s["out_in_f"], s["out_out_f"]
        linked = [item(v1, model["aroll"], a, b, a)]
        channels = assets[model["aroll"]]["channels"]
        for track, channel in ((a1, 1), (a2, 2)):
            if channel <= channels:
                linked.append(item(track, model["aroll"], a, b, a, channel))
        link_items(linked)
    if model["overlay"]:
        item(v2, model["overlay"], 0, model["total"], 0)
    if model["captions"]:
        item(v3, model["captions"], 0, model["total"], 0)
    if model["baked_spans"]:
        v4 = node(video, "track")
        for span in model["baked_spans"]:
            clip = item(v4, model["master"], span["start_f"], span["end_f"], span["start_f"])
            source = node(clip, "sourcetrack")
            node(source, "mediatype", "video")
            node(source, "trackindex", 1)
    # FCP7 audio clipitems select one source channel each. Preserve stereo using paired tracks.
    sound_tracks = {}
    for lane in sorted({c["lane"] for c in model["beds"] + model["effects"]}, reverse=True):
        channels = max(assets[c["ref"]]["channels"] for c in model["beds"] + model["effects"] if c["lane"] == lane)
        sound_tracks[lane] = [node(audio, "track") for _ in range(channels)]
        for channel, track in enumerate(sound_tracks[lane], 1):
            node(track, "outputchannelindex", (channel - 1) % 2 + 1)
            if channels == 1:
                node(track, "outputchannelindex", 2)
    for clip in model["beds"] + model["effects"]:
        a, b, si = (round(t * rate) for t in (clip["offset"], clip["offset"] + clip["duration"], clip["start"]))
        linked = []
        for channel, track in enumerate(sound_tracks[clip["lane"]], 1):
            if channel <= assets[clip["ref"]]["channels"]:
                linked.append(item(track, clip["ref"], a, b, si, channel, clip["gain"],
                                   clip["fade_out"] if clip["lane"] <= -2 else 0))
        link_items(linked)
    fcpx.save_xml(root, out, "xmeml")
    return {"segments": len(model["segments"]), "overlay": int(bool(overlay)), "captions": int(bool(captions)), "bed_clips": len(model["beds"]),
            "sfx": len(model["effects"])}


def check_fcp7(path) -> list[str]:
    problems = []
    try:
        root = ET.parse(path).getroot()
        if root.tag != "xmeml" or root.get("version") != "4":
            problems.append("The hand-off must be FCP7 XML version 4")
        for url in root.findall(".//pathurl"):
            if not fcpx.uri_path(url.text).is_file():
                problems.append("Referenced file is missing")
        seq = root.find("sequence")
        cursor = 0
        for clip in seq.findall("media/video/track")[0].findall("clipitem"):
            a, b = int(clip.findtext("start")), int(clip.findtext("end"))
            if a != cursor or b <= a:
                problems.append("The a-roll cuts are not back to back")
            cursor += b - a
        if cursor != int(seq.findtext("duration")):
            problems.append("The a-roll durations do not sum to the reel length")
        tracks = seq.findall("media/video/track")
        files = {f.get("id"): f.findtext("pathurl") for f in root.findall(".//file") if f.find("pathurl") is not None}
        master_refs = set()
        for track in tracks[1:3]:
            for clip in track.findall("clipitem"):
                if tuple(int(clip.findtext(k)) for k in ("start", "end", "in", "out")) != (0, cursor, 0, cursor):
                    problems.append("A transparent layer has incorrect frames")
        for clip in (tracks[3].findall("clipitem") if len(tracks) > 3 else []):
            a, b, si, so = (int(clip.findtext(k)) for k in ("start", "end", "in", "out"))
            if a < 0 or b <= a or b > cursor or si != a or so != b or clip.findtext("sourcetrack/mediatype") != "video":
                problems.append("A baked Master span has incorrect frames or includes audio")
            master_refs.add(clip.find("file").get("id"))
        if master_refs:
            base = int(seq.findtext("rate/timebase"))
            rate = Fraction(base * 1000, 1001) if seq.findtext("rate/ntsc") == "TRUE" else Fraction(base)
            for ref in master_refs:
                problems.extend(fcpx.master_problems(fcpx.uri_path(files[ref]), cursor, rate))
    except Exception as e:
        problems.append("Couldn't check the FCP7 XML: " + " ".join(str(e).split())[:150])
    return problems


def main():
    ap = fcpx.Parser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    srt = sub.add_parser("srt")
    srt.add_argument("--reel-dir", type=Path, required=True)
    srt.add_argument("--out", type=Path, required=True)
    fcp = sub.add_parser("fcp7")
    fcp.add_argument("--reel-dir", type=Path, required=True)
    fcp.add_argument("--aroll", type=Path, required=True)
    fcp.add_argument("--overlay", type=Path)
    fcp.add_argument("--captions", type=Path)
    fcp.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    summary = write_srt(a.reel_dir, a.out) if a.cmd == "srt" else write_fcp7(a.reel_dir, a.aroll, a.overlay, a.out, a.captions)
    issues = check_srt(a.out) if a.cmd == "srt" else check_fcp7(a.out)
    if issues:
        raise fcpx.Stop(1, "; ".join(issues))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(fcpx.guarded(main))
