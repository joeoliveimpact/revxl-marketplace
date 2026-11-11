"""Package an approved reel and prepare/check its native Resolve MCP hand-off."""
import ast
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import segments_to_fcpxml as fcpx
import export_edit

rt = fcpx.rt
Stop = fcpx.Stop


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def compose_module():
    # Match placer's import: the module must be registered for captions' circular import.
    import compose
    return compose


def approved(reel):
    compose = compose_module()
    latest = compose.latest_preview(reel / "renders")
    ok = fcpx.read(reel / compose.OK_FILE, {})
    problem = compose.ok_problem(ok, latest.name if latest else None, latest.stat().st_mtime if latest else 0)
    if problem:
        raise Stop(1, problem)
    return compose


def baked_note(spans, rate):
    if not spans:
        return ""

    def clock(frame):
        tenths = round(Fraction(frame) / rate * 10)
        minutes, remainder = divmod(tenths, 600)
        return f"{minutes}:{remainder // 10:02d}.{remainder % 10}"

    labels = {"pip": "picture-in-picture", "overlay": "blurred card", "transition": "transition"}
    parts = [f'{clock(s["start_f"])}-{clock(s["end_f"])} (' +
             " and ".join(labels[name] for name in s["layout"].split("+")) + ")" for s in spans]
    # Counts timeline parts (back-to-back transitions merge into one part); the labels name what each holds.
    names = {name for s in spans for name in s["layout"].split("+")}
    moves, layouts = "transition" in names, bool(names - {"transition"})
    what = ("layout and transition movement" if moves and layouts else
            "transition movement" if moves else "layout")
    noun, own = ("part uses", "its") if len(spans) == 1 else ("parts use", "their")
    return f"note: {len(spans)} {noun} the finished picture because {own} {what} can't be rebuilt in an editor: " + ", ".join(parts)


def derive_media(reel, aroll, master=None):
    """Separate streams so Resolve cannot duplicate or redistribute the voice."""
    outdir = reel / "handoff"
    outdir.mkdir(exist_ok=True)
    date = datetime.now().strftime("%m.%d.%y")
    paths = {"picture": outdir / f"{reel.name} Picture - {date}.mp4",
             "voice": outdir / f"{reel.name} Voice - {date}.wav"}
    rate = fcpx.fpsmod.as_fraction(fcpx.fpsmod.resolve_fps(aroll))
    total = fcpx.fpsmod.frame_count(aroll)
    source = fcpx.probe(aroll)
    if not source["audio"]:
        raise Stop(1, "The baked a-roll must contain its own voice")

    def convert(source_path, target, options):
        result = subprocess.run([rt.tool("ffmpeg"), "-v", "error", "-y", "-i", str(source_path),
                                 *options, str(target)], capture_output=True, timeout=300)
        if result.returncode:
            raise Stop(1, f"Couldn't separate the media for {target.name}")

    convert(aroll, paths["picture"], ["-map", "0:v:0", "-an", "-c:v", "copy"])
    # A fractional-rate reel can end between 48 kHz samples. Cover that boundary
    # with at most one extra sample, while keeping all XML times exact.
    samples = math.ceil(Fraction(total * 48000, 1) / rate)
    convert(aroll, paths["voice"], ["-map", "0:a:0", "-vn", "-af",
            f"aresample=48000,apad,atrim=end_sample={samples}", "-c:a", "pcm_s24le", "-ar", "48000"])
    problems = fcpx.picture_problems(paths["picture"], total, rate)
    problems += fcpx.voice_problems(paths["voice"], total, rate, source["channels"])
    if master:
        paths["master_picture"] = outdir / f"{reel.name} Master Picture - {date}.mp4"
        convert(master, paths["master_picture"], ["-map", "0:v:0", "-an", "-c:v", "copy"])
        problems += fcpx.picture_problems(paths["master_picture"], total, rate)
    if problems:
        raise Stop(1, "; ".join(problems))
    return paths


def package(reel, which="all"):
    compose = compose_module()
    if not any(p.is_file() and compose.MASTER_RE.fullmatch(p.name) for p in (reel / "renders").glob("*")):
        raise Stop(1, "There's no final video yet. Make the final video, then package it.")
    compose = approved(reel)
    approval = fcpx.read(reel / compose.OK_FILE)
    if "hook_text" not in approval:
        raise Stop(1, "This reel's approval is from before hook text was saved; re-run the master render, then package again.")
    latest = compose.latest_preview(reel / "renders")
    preview = {"name": latest.name, "sha256": digest(latest), "mtime_ns": latest.stat().st_mtime_ns}
    outdir = reel / "handoff"
    outdir.mkdir(exist_ok=True)
    previous = fcpx.read(outdir / "handoff.json", {})
    rendered = {}
    wanted = ("aroll", "overlay", "captions") if which == "all" else () if which == "none" else (which,)
    for layer in wanted:
        try:
            rendered[layer] = compose.render(reel, "master", approval["hook_text"], layers=layer)
        except compose.Stop as e:
            raise Stop(e.code, " ".join(e.lines)) from None
    # Reusing a layer is explicit; never quietly substitute the cut master without its camera moves.
    paths = {}
    for layer in ("aroll", "overlay", "captions"):
        summary = rendered.get(layer) or previous.get("layers", {}).get(layer)
        if summary:
            path = (reel / summary["out"]).resolve()
            if not path.is_relative_to(outdir.resolve()) or not path.is_file():
                raise Stop(1, f"The saved {layer} layer is missing; package all layers again")
            if layer not in rendered:
                if previous.get("schema") != 2:
                    raise Stop(1, "The saved layers predate separate captions; package all layers again")
                old_hash = previous.get("sha256", {}).get(path.name)
                if not old_hash or digest(path) != old_hash:
                    raise Stop(1, f"The saved {layer} layer changed; package all layers again")
                if previous.get("cuts_sha256") != digest(reel / "work/cuts.json"):
                    raise Stop(1, "The cuts changed; package all layers again")
                if previous.get("approved_preview") != preview:
                    raise Stop(1, "The approved preview changed; package all layers again")
            paths[layer] = path
            rendered[layer] = summary
    if any(layer not in paths for layer in ("aroll", "overlay", "captions")):
        raise Stop(1, "Make all three picture layers first: package all layers")
    aroll, overlay, captions = (paths[k] for k in ("aroll", "overlay", "captions"))
    model = fcpx.load_model(reel, aroll, overlay, captions)
    master = next((a["path"] for a in model["assets"] if a["id"] == model["master"]), None)
    derived = derive_media(reel, aroll, master)
    fcpxml = outdir / f"{reel.name} - Resolve.fcpxml"
    fcp7 = outdir / f"{reel.name} - FCP7.xml"
    srt = outdir / f"{reel.name} - Captions.srt"
    summaries = {"fcpxml": fcpx.write(reel, aroll, overlay, fcpxml, captions=captions, **derived),
                 "fcp7": export_edit.write_fcp7(reel, aroll, overlay, fcp7, captions=captions)}
    files = [*paths.values(), *derived.values(), fcpxml, fcp7]
    problems = fcpx.check(fcpxml) + export_edit.check_fcp7(fcp7)
    if fcpx.read(reel / "work/captions.json", {}).get("chunks"):
        summaries["srt"] = export_edit.write_srt(reel, srt)
        files.append(srt)
        problems.extend(export_edit.check_srt(srt))
    else:
        srt.unlink(missing_ok=True)
    if problems:
        raise Stop(1, "; ".join(problems))
    baked = summaries["fcpxml"]["baked_spans"]
    note = baked_note(baked, 1 / fcpx.seconds(summaries["fcpxml"]["format"]["frameDuration"]))
    manifest = {"schema": 2, "layers": rendered, "summaries": summaries,
                "derived": {k: p.relative_to(reel).as_posix() for k, p in derived.items()},
                "baked_spans": baked, "baked_note": note,
                "approved_preview": preview,
                "cuts_sha256": digest(reel / "work/cuts.json"),
                "sha256": {p.name: digest(p) for p in files}}
    # The manifest describes payload hashes; it cannot contain a SHA256 of its own final bytes.
    save(outdir / "handoff.json", manifest)
    if note:
        print(note)
    return manifest


def checked_manifest(reel):
    outdir = reel / "handoff"
    manifest = fcpx.read(outdir / "handoff.json")
    if manifest.get("schema") != 2 or any(k not in manifest.get("layers", {}) for k in ("aroll", "overlay", "captions")):
        raise Stop(1, "Package all three picture layers before preparing the Resolve hand-off")
    for key in ("picture", "voice", *(("master_picture",) if manifest.get("baked_spans") else ())):
        relative = manifest.get("derived", {}).get(key)
        if not relative or Path(relative).name not in manifest["sha256"]:
            raise Stop(1, "Package the separate Picture and Voice files before preparing the Resolve hand-off")
    for name, sha in manifest["sha256"].items():
        path = (outdir / name).resolve()
        if not path.is_relative_to(outdir.resolve()) or not path.is_file() or digest(path) != sha:
            raise Stop(1, "A hand-off file is missing or changed; package the reel again")
    problems = fcpx.check(outdir / f"{reel.name} - Resolve.fcpxml")
    if problems:
        raise Stop(1, "; ".join(problems))
    return manifest


def picture_covers(reel, track, cuts):
    """Reuse the compositor's gate, underlay and layout geometry; do not render."""
    compose = compose_module()
    beats = fcpx.read(reel / compose.SEND, {}).get("beats", [])
    covers = compose.picture_covers(beats, cuts.get("fps"))
    total = cuts["segments"][-1]["out_out_f"]
    full = compose.layout("full", 1)["box"]

    def changed(name):
        return compose.layout(name, 1)["box"] != full

    keys = sorted(track.get("keys", []), key=lambda k: k["f"])
    moves = sorted((t for t in track.get("tweens", []) if t["prop"] == "layout"), key=lambda t: t["start_f"])
    edges = sorted({0, total, *(k["f"] for k in keys),
                    *(m[k] for m in moves for k in ("start_f", "end_f"))})
    for start, end in zip(edges, edges[1:]):
        last = max((k for k in keys if k["f"] <= start), key=lambda k: k["f"], default={"f": -1})
        names = [last.get("layout", "full")]
        for move in moves:
            if last["f"] <= move["start_f"] <= start:
                names = [move["to"]] if start >= move["end_f"] else [move["from"], move["to"]]
        if any(changed(name) for name in names):
            covers.append((start, end, "another layout"))
    if track.get("style", {}).get("style") == "layout-switch":
        covers += [(b["start_f"], b["end_f"], "another layout") for b in beats if changed(b["layout"])]
    return covers


def proof_selection(reel):
    """Pick middle eligible plain/settled punch frames, and explain missing proofs."""
    cuts = fcpx.read(reel / "work/cuts.json")
    total = cuts["segments"][-1]["out_out_f"]
    track = fcpx.read(reel / "work/scale_track.json", {})
    keys = sorted(track.get("keys", []), key=lambda k: k["f"])
    tweens = sorted((t for t in track.get("tweens", []) if t["prop"] == "scale"), key=lambda t: t["start_f"])
    baked = fcpx.read(reel / "handoff/handoff.json").get("baked_spans", [])
    covers = picture_covers(reel, track, cuts)
    covered = {"unpunched": set(), "punched": set()}
    plain, punched = [], []
    for frame in range(total):
        if any(s["start_f"] <= frame < s["end_f"] for s in baked):
            continue
        last = max((k for k in keys if k["f"] <= frame), key=lambda k: k["f"], default={"f": -1, "scale": 1})
        scale = float(last["scale"])
        moving = False
        for tween in tweens:
            if tween["start_f"] < last["f"] or tween["start_f"] > frame:
                continue
            if frame >= tween["end_f"]:
                scale = float(tween["to"])
            else:
                # An interval is plain only if BOTH ends are plain. Pick the punch proof
                # from its settled key/endpoint so easing cannot create a false candidate.
                moving = True
                scale = max(float(tween["from"]), float(tween["to"]))
        kind = "unpunched" if abs(scale - 1) < 1e-6 else "punched" if scale >= 1.05 and not moving else None
        if kind:
            reasons = {reason for start, end, reason in covers if start <= frame < end}
            if reasons:
                covered[kind].update(reasons)
            else:
                (plain if kind == "unpunched" else punched).append(frame)
    frames = {kind: candidates[len(candidates) // 2] for kind, candidates in
              (("unpunched", plain), ("punched", punched)) if candidates}
    return frames, frame_notes(frames, covered)


def proof_frames(reel):
    return proof_selection(reel)[0]


def frame_notes(frames, covered=None):
    notes = []
    for kind, description in (("unpunched", "unpunched"), ("punched", "settled punched")):
        if kind in frames:
            continue
        reasons = (covered or {}).get(kind)
        if reasons:
            notes.append(f"The {kind} picture check was skipped: every {description} frame outside finished-picture spans "
                         "is covered by " + " or ".join(sorted(reasons)) + ".")
        else:
            notes.append(f"The {kind} comparison was skipped because this reel has no {description} frame outside finished-picture spans")
    return notes


def snippet(body):
    body = textwrap.dedent(body).strip()
    script = "try:\n" + textwrap.indent(body, "    ") + '\nexcept Exception as error:\n    result = {"ok": False, "error": " ".join(str(error).split())[:220]}\n'
    check_snippet(script)
    return script


def check_snippet(script):
    tree = ast.parse(script)
    assigned = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(a.name not in ("time", "json") for a in node.names):
            raise ValueError("A native step imports a forbidden module")
        if isinstance(node, ast.ImportFrom) and node.module not in ("time", "json"):
            raise ValueError("A native step imports a forbidden module")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("open", "exec", "eval", "__import__"):
            raise ValueError("A native step uses forbidden file or code access")
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id == "result":
            assigned = True
    if not assigned or "open(" in script:
        raise ValueError("A native step must set result without file access")


def native_steps(reel, manifest, project_name=None):
    outdir = (reel / "handoff").resolve()
    fmt = manifest["summaries"]["fcpxml"]["format"]
    rate = 1 / fcpx.seconds(fmt["frameDuration"])
    base = project_name or f"{reel.name} hand-off {datetime.now().strftime('%m.%d.%y')}"
    frames, notes = proof_selection(reel)
    stills = [{"frame": n, "path": str(outdir / f"resolve-still-{n}.png")} for n in frames.values()]
    srt = outdir / f"{reel.name} - Captions.srt"
    has_srt = srt.name in manifest["sha256"]
    steps = []

    def add(id_, say, body, timeout=60):
        steps.append({"id": id_, "say": say, "script": snippet(body), "timeout": timeout})

    add("ready", "I'm checking Resolve Studio and waiting for its project library.", '''
        import time
        product = resolve.GetProductName()
        version = resolve.GetVersion()
        if "studio" not in str(product).lower() or tuple(int(n) for n in version[:2]) < (21, 1):
            raise ValueError("The hand-off needs DaVinci Resolve Studio 21.1 or newer")
        manager = resolve.GetProjectManager()
        deadline = time.monotonic() + 50
        databases = manager.GetDatabaseList()
        while not databases and time.monotonic() < deadline:
            time.sleep(0.25)
            databases = manager.GetDatabaseList()
        if not databases:
            raise ValueError("Resolve's project library is still loading; ask me again once it is ready")
        result = {"ok": True, "product": product, "version": list(version)}
    ''')
    add("project", "I'm creating a new project for this hand-off.", f'''
        manager = resolve.GetProjectManager()
        base = {base!r}
        names = set(manager.GetProjectListInCurrentFolder() or [])
        name, suffix = base, 2
        while name in names:
            name, suffix = base + " (" + str(suffix) + ")", suffix + 1
        created = manager.CreateProject(name)
        if not created:
            raise ValueError("Resolve couldn't create a new project; no existing project was opened")
        project = resolve.GetProjectManager().GetCurrentProject()
        if not project or project.GetName() != name:
            raise ValueError("Resolve did not open the newly created project")
        result = {{"ok": True, "name": name, "created": True}}
    ''')
    add("import", "I'm bringing in the cut picture, separate layers and original sound.", f'''
        project = resolve.GetProjectManager().GetCurrentProject()
        if not project or project.GetTimelineCount() != 0:
            raise ValueError("The import needs the empty project just created for this hand-off")
        timeline = project.GetMediaPool().ImportTimelineFromFile(
            {str(outdir / f'{reel.name} - Resolve.fcpxml')!r},
            {{"importSourceClips": True, "sourceClipsPath": {str(outdir)!r}}})
        if not timeline:
            raise ValueError("Resolve could not import the timeline")
        if not project.SetCurrentTimeline(timeline):
            raise ValueError("Resolve could not select the imported timeline")
        width = timeline.GetSetting("timelineResolutionWidth")
        height = timeline.GetSetting("timelineResolutionHeight")
        project_width = project.GetSetting("timelineResolutionWidth")
        project_height = project.GetSetting("timelineResolutionHeight")
        if (str(width), str(height)) != ({str(fmt['width'])!r}, {str(fmt['height'])!r}):
            if not timeline.SetSetting("useCustomSettings", "1"):
                raise ValueError("Resolve refused custom timeline settings")
            if not timeline.SetSetting("timelineResolutionWidth", {str(fmt['width'])!r}) or not timeline.SetSetting("timelineResolutionHeight", {str(fmt['height'])!r}):
                raise ValueError("Resolve refused the timeline size")
        result = {{"ok": True, "width": timeline.GetSetting("timelineResolutionWidth"),
                  "height": timeline.GetSetting("timelineResolutionHeight"),
                  "frame_rate": timeline.GetSetting("timelineFrameRate"),
                  "project_width": project_width, "project_height": project_height}}
    ''')
    add("captions", "I'm keeping the editable captions file in the Media Pool for one drag onto a subtitle track.", f'''
        project = resolve.GetProjectManager().GetCurrentProject()
        if not project or not project.GetCurrentTimeline():
            raise ValueError("The new hand-off timeline is not open")
        imported = project.GetMediaPool().ImportMedia([{str(srt)!r}]) if {has_srt!r} else []
        if {has_srt!r} and not imported:
            raise ValueError("Resolve could not import the editable captions file into the Media Pool")
        result = {{"ok": True, "imported": [clip.GetName() for clip in imported], "skipped": {not has_srt!r}}}
    ''')
    add("report", "I'm checking the tracks, linked files, music level and available picture frames.", f'''
        project = resolve.GetProjectManager().GetCurrentProject()
        timeline = project.GetCurrentTimeline() if project else None
        if not timeline:
            raise ValueError("The new hand-off timeline is not open")
        items = []
        for kind in ("video", "audio", "subtitle"):
            for track in range(1, int(timeline.GetTrackCount(kind) or 0) + 1):
                for item in timeline.GetItemListInTrack(kind, track) or []:
                    media = item.GetMediaPoolItem()
                    properties = media.GetClipProperty() if media else {{}}
                    properties = properties or {{}}
                    offline = str(properties.get("Offline", "")).lower() in ("true", "1", "yes") or str(properties.get("Status", "")).lower() == "offline"
                    items.append({{"kind": kind, "track": track, "name": item.GetName(),
                                  "start": item.GetStart(), "end": item.GetEnd(), "media_pool": bool(media),
                                  "media_path": properties.get("File Path", ""), "offline": offline,
                                  "volume_db": item.GetProperty("AudioVolume") if kind == "audio" else None}})
        pool = []
        folders = [project.GetMediaPool().GetRootFolder()]
        while folders:
            folder = folders.pop()
            folders.extend(folder.GetSubFolderList() or [])
            for clip in folder.GetClipList() or []:
                pool.append({{"name": clip.GetName(), "path": clip.GetClipProperty("File Path")}})
        stills = {stills!r}
        start = int(timeline.GetStartFrame())
        nominal = {round(rate)!r}
        for still in stills:
            frame = start + still["frame"]
            seconds, ff = divmod(frame, nominal)
            minutes, ss = divmod(seconds, 60)
            hh, mm = divmod(minutes, 60)
            timecode = "%02d:%02d:%02d:%02d" % (hh, mm, ss, ff)
            if not timeline.SetCurrentTimecode(timecode):
                raise ValueError("Resolve could not select a frame for picture verification")
            still["exported"] = bool(project.ExportCurrentFrameAsStill(still["path"]))
        result = {{"ok": True, "width": timeline.GetSetting("timelineResolutionWidth"),
                  "height": timeline.GetSetting("timelineResolutionHeight"), "frame_rate": timeline.GetSetting("timelineFrameRate"),
                  "project_width": project.GetSetting("timelineResolutionWidth"),
                  "project_height": project.GetSetting("timelineResolutionHeight"),
                  "start_frame": start, "items": items, "pool": pool, "stills": stills, "notes": {notes!r}}}
    ''')
    steps[-1]["notes"] = notes
    return steps


def resolve_steps(reel, project_name=None):
    if rt.read_config().get("nle") != "resolve":
        raise Stop(3, "The Resolve hand-off isn't set up on this editor")
    manifest = checked_manifest(reel)
    steps = native_steps(reel, manifest, project_name)
    save(reel / "handoff/resolve-steps.json", steps)
    return steps


def normal_path(path):
    return os.path.normcase(str(Path(path).resolve()))


def read_frame(path, frame=0):
    import numpy as np
    p = subprocess.run([rt.tool("ffmpeg"), "-v", "error", "-i", str(path), "-vf",
                        f"select=eq(n\\,{frame}),scale=1080:1920", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, timeout=90)
    if p.returncode or len(p.stdout) != 1080 * 1920 * 3:
        raise ValueError("A picture proof frame could not be decoded")
    return np.frombuffer(p.stdout, dtype=np.uint8).astype(np.float32)


def verify_result(reel, manifest, results):
    import numpy as np
    summary = manifest["summaries"]["fcpxml"]
    fmt = summary["format"]
    problems, differences = [], {}
    frames, notes = proof_selection(reel)
    for id_ in ("ready", "project", "import", "captions", "report"):
        step = results.get(id_, {})
        if step.get("ok") is not True:
            problems.append(f"Resolve step {id_} failed: " + " ".join(str(step.get("error", "no successful result")).split())[:220])
    if problems:
        return {"problems": problems, "frame_differences": differences, "notes": notes}
    ready = results["ready"]
    if "studio" not in str(ready.get("product", "")).lower() or tuple(int(n) for n in ready.get("version", [])[:2]) < (21, 1):
        problems.append("The hand-off needs DaVinci Resolve Studio 21.1 or newer")
    if results["project"].get("created") is not True:
        problems.append("Resolve did not confirm a newly created project")
    report = results["report"]
    if (str(report.get("width")), str(report.get("height"))) != (str(fmt["width"]), str(fmt["height"])):
        problems.append("The imported timeline size does not match the reel")
    try:
        rate = float(str(report["frame_rate"]).replace(" DF", ""))
        if not math.isfinite(rate) or abs(rate - float(1 / fcpx.seconds(fmt["frameDuration"]))) > .001:
            problems.append("The imported timeline frame rate does not match the reel")
    except (ValueError, TypeError, KeyError):
        problems.append("Resolve did not report the timeline frame rate")
    items = report.get("items", [])
    expected_paths = {normal_path(p) for p in summary["paths"]}
    ar = normal_path(reel / manifest["layers"]["aroll"]["out"])
    for item in items:
        path = item.get("media_path")
        if path and normal_path(path) == ar:
            problems.append("An imported timeline item references the A-roll mp4")
        if not item.get("media_pool") or item.get("offline") is not False or not path or not Path(path).is_file():
            problems.append("An imported timeline item is offline or has no linked media")
        elif normal_path(path) not in expected_paths:
            problems.append("An imported timeline item references an unexpected media file")
    video = [i for i in items if i.get("kind") == "video"]
    start = float(report.get("start_frame", 0))
    cuts = fcpx.read(reel / "work/cuts.json")["segments"]
    picture = normal_path(reel / manifest["derived"]["picture"])
    v1 = sorted((i for i in video if i.get("track") == 1), key=lambda i: i["start"])
    if len(v1) != summary["segments"] or len(v1) != len(cuts) or any(
            normal_path(i["media_path"]) != picture or abs(i["start"] - start - s["out_in_f"]) > .1
            or abs(i["end"] - start - s["out_out_f"]) > .1 for i, s in zip(v1, cuts)):
        problems.append("The imported Picture file does not have an item at every cut")
    total = cuts[-1]["out_out_f"]
    for layer, track in (("overlay", 2), ("captions", 3)):
        clips = [i for i in video if i.get("track") == track]
        path = normal_path(reel / manifest["layers"][layer]["out"])
        if len(clips) != 1 or any(normal_path(i["media_path"]) != path or abs(i["start"] - start) > .1
                                   or abs(i["end"] - start - total) > .1 for i in clips):
            problems.append(f"The imported timeline is missing its {layer} layer on its own track")
    spans = manifest.get("baked_spans", [])
    baked = sorted((i for i in video if i.get("track") == 4), key=lambda i: i["start"])
    if len(baked) != len(spans) or any(normal_path(i["media_path"]) != normal_path(summary["master"])
            or abs(i["start"] - start - s["start_f"]) > .1 or abs(i["end"] - start - s["end_f"]) > .1
            for i, s in zip(baked, spans)):
        problems.append("The imported timeline is missing its finished-picture spans on track four")
    if len(video) != len(cuts) + 2 + len(spans) or any(i.get("kind") not in ("video", "audio") for i in items):
        problems.append("The imported timeline contains unexpected picture or subtitle items")
    audio = [i for i in items if i.get("kind") == "audio"]
    voice = normal_path(reel / manifest["derived"]["voice"])
    a1 = [i for i in audio if i.get("track") == 1]
    if len(a1) != 1 or any(normal_path(i["media_path"]) != voice or abs(i["start"] - start) > .1
                           or abs(i["end"] - start - total) > .1 for i in a1) \
            or any(normal_path(i["media_path"]) == voice and i.get("track") != 1 for i in items):
        problems.append("The imported voice must be one continuous Voice WAV item alone on audio track one")
    counts = {}
    for item in audio:
        key = normal_path(item["media_path"])
        counts[key] = counts.get(key, 0) + 1
    expected_audio = {normal_path(p): n for p, n in summary["audio_items"].items()}
    if counts != expected_audio:
        problems.append("The imported audio is missing voice, music or original sound-effect items")
    bed = fcpx.read(reel / "sound/placement.json", {}).get("bed") or {}
    if bed.get("source"):
        bed_path = normal_path(reel / bed["source"])
        if not any(normal_path(item["media_path"]) == bed_path for item in audio):
            problems.append("The imported music bed is missing")
        for item in audio:
            if normal_path(item["media_path"]) == bed_path:
                try:
                    volume = float(item["volume_db"])
                    if not math.isfinite(volume) or abs(volume - float(bed["level"]["gain_db_applied"])) > .05:
                        problems.append("The imported music bed volume does not match its applied level")
                except (ValueError, TypeError, KeyError):
                    problems.append("Resolve did not report the music bed volume")
    srt = reel / "handoff" / f"{reel.name} - Captions.srt"
    if srt.name in manifest["sha256"] and not any(c.get("path") and normal_path(c["path"]) == normal_path(srt)
                                                 for c in report.get("pool", [])):
        problems.append("The editable SRT is missing from the Media Pool")
    stills = report.get("stills", [])
    if len(stills) != len(frames):
        problems.append("Resolve did not export all requested still frames")
    cut = reel / "work/renders" / ("master-" + ("%.2fx" % fcpx.read(reel / "work/cuts.json").get("speed", 1)).replace(".", "") + ".mp4")
    for kind, frame in frames.items():
        expected = reel / "handoff" / f"resolve-still-{frame}.png"
        matches = [s for s in stills if s.get("frame") == frame and s.get("exported") is True
                   and s.get("path") and normal_path(s["path"]) == normal_path(expected)]
        if len(matches) != 1 or not expected.is_file():
            problems.append("A requested Resolve still is missing or was not exported")
            continue
        image = read_frame(expected)
        reference = read_frame(reel / manifest["layers"]["aroll"]["out"], frame) if kind == "unpunched" else read_frame(cut, frame)
        differences[kind] = float(np.mean(np.abs(image - reference)))
    if differences.get("unpunched", 0) >= 6:
        problems.append("The unpunched Resolve still does not match the Master-quality a-roll")
    if "punched" in differences and (differences["punched"] <= 12 or differences["punched"] <= 3 * differences.get("unpunched", 0)):
        problems.append("The punched Resolve still does not show the expected camera move")
    return {"problems": list(dict.fromkeys(problems)), "frame_differences": differences, "notes": notes}


def resolve_check(reel, result_file):
    report = {"problems": [], "notes": []}
    try:
        manifest = checked_manifest(reel)
        results = fcpx.read(result_file)
        report.update(verify_result(reel, manifest, results))
        report["resolve"] = results.get("report", {})
        if any(Path(p).suffix.lower() == ".mp3" and "sfx" in Path(p).parts for p in manifest["summaries"]["fcpxml"]["paths"]):
            report["notes"].append("Resolve may play MP3 sound-effect originals about 50 ms late")
    except Exception as error:
        report["problems"].append(" ".join(str(error).split())[:220] or "The Resolve result could not be checked")
    save(reel / "handoff/resolve-report.json", report)
    if report["problems"]:
        raise Stop(1, "; ".join(report["problems"]))
    for note in report["notes"]:
        print("note: " + note)
    return report



def selftest():
    for rate, want in ((Fraction(30), "1/30s"), (Fraction(25), "1/25s"), (Fraction(30000, 1001), "1001/30000s")):
        if fcpx.stamp(1 / rate) != want:
            raise ValueError("Rational frame duration failed")
    with tempfile.TemporaryDirectory() as temp:
        reel = Path(temp) / "REEL_A"
        save(reel / "work/captions.json", {"chunks": [
            {"start_f": 1, "end_f": 20, "text": "First"}, {"start_f": 15, "end_f": 30, "text": "Next"},
            {"start_f": 30, "end_f": 35, "text": " "}]})
        srt = reel / "captions.srt"
        with patch.object(export_edit, "reel_rate", return_value=Fraction(30000, 1001)):
            summary = export_edit.write_srt(reel, srt)
        if export_edit.check_srt(srt) or summary["entries"] != 2 or "00:00:00,033 --> 00:00:00,501" not in srt.read_text():
            raise ValueError("Subtitle rounding or overlap clipping failed")
        srt.write_bytes(b"1\n00:00:00,000 --> 00:00:01,000\nA\n\n2\n00:00:00,500 --> 00:00:02,000\nB\n\n")
        if not export_edit.check_srt(srt):
            raise ValueError("Subtitle overlap check failed")
        model = {"name": "REEL_A", "rate": Fraction(30), "total": 60, "width": 1080, "height": 1920,
                 "assets": [{"id": "r2", "path": reel / "picture.mp4", "duration": Fraction(2),
                             "video": True, "audio": False, "channels": 0, "sample_rate": 48000},
                            {"id": "r3", "path": reel / "voice.wav", "duration": Fraction(2),
                             "video": False, "audio": True, "channels": 2, "sample_rate": 48000}],
                 "picture": "r2", "voice": "r3", "overlay": None, "beds": [], "effects": [],
                 "segments": [{"out_in_f": 0, "out_out_f": 30}, {"out_in_f": 30, "out_out_f": 60}]}
        root = fcpx.build_tree(model)
        clips = root.findall(".//spine/asset-clip")
        pictures = root.findall('.//spine/asset-clip/asset-clip[@lane="1"]')
        if len(clips) != 1 or clips[0].get("ref") != "r3" or fcpx.seconds(clips[0].get("duration")) != 2 \
                or len(pictures) != 2 or sum(fcpx.seconds(c.get("duration")) for c in pictures) != 2:
            raise ValueError("Synthetic FCPXML voice and picture cuts failed")
        save(reel / "work/cuts.json", {"segments": [{"out_in_f": 0, "out_out_f": 60}]})
        save(reel / "work/scale_track.json", {"keys": [{"f": 0, "scale": 1}, {"f": 30, "scale": 1.18}], "tweens": []})
        save(reel / "handoff/handoff.json", {"baked_spans": []})
        if proof_frames(reel) != {"unpunched": 15, "punched": 45}:
            raise ValueError("Proof frames without a coverage frame rate failed")
        manifest = {"summaries": {"fcpxml": {"format": {"width": 1080, "height": 1920, "frameDuration": "1/30s"}}}, "sha256": {}}
        steps = native_steps(reel, manifest)
        if [s["id"] for s in steps] != ["ready", "project", "import", "captions", "report"]:
            raise ValueError("Native step order failed")
        for step in steps:
            check_snippet(step["script"])
            if not 0 < step["timeout"] <= 60:
                raise ValueError("Native step timeout failed")
        for bad in ('import os\nresult = {}', 'from pathlib import Path\nresult = {}', 'result = open("x")', 'value = 1'):
            try:
                check_snippet(bad)
            except ValueError:
                pass
            else:
                raise ValueError("A forbidden native snippet passed")
    print("selftest ok")
    return 0


def main():
    ap = fcpx.Parser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("package")
    p.add_argument("--reel-dir", required=True, type=Path)
    p.add_argument("--which", choices=("all", "aroll", "overlay", "captions", "none"), default="all")
    p = sub.add_parser("resolve-steps")
    p.add_argument("--reel-dir", required=True, type=Path)
    p.add_argument("--project")
    p = sub.add_parser("resolve-check")
    p.add_argument("--reel-dir", required=True, type=Path)
    p.add_argument("--result", required=True, type=Path)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.cmd:
        raise Stop(2, "Choose package, resolve-steps or resolve-check for the editor hand-off")
    if a.cmd == "resolve-steps":
        steps = resolve_steps(a.reel_dir.resolve(), a.project)
        print("Resolve hand-off steps: " + ", ".join(s["id"] for s in steps) + "; saved in handoff/resolve-steps.json")
        return 0
    result = package(a.reel_dir.resolve(), a.which) if a.cmd == "package" else resolve_check(a.reel_dir.resolve(), a.result.resolve())
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(fcpx.guarded(main))
