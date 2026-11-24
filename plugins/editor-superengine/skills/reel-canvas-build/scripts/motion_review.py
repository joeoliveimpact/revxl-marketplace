"""Build the Motion review cards, or apply the user's Send. Scenes run one at a time."""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import math
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scene_render as sr
import scene_fill

compose, scene_check, rt = sr.compose, sr.compose.scene_check, sr.rt
from heavy_job import heavy_job, HeavyJobError
import gpu
# Per render pass; the build lane replaces this rate after measuring a full run.
SECONDS_PER_SCENE_SECOND = 5  # measured 11.16.26: 188 s for one 4.2 s scene, 11 passes (~4.1); rounded up


def read(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def write_json(path, obj, *, preserve_mtime=False):
    stamp = path.stat() if preserve_mtime and path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes((json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    if stamp is not None:
        # An internal edit is not a new user Send in the Cockpit's mtime-based inbox.
        os.utime(tmp, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    tmp.replace(path)


def scene_folder(reel, sid):
    scene_check._check_id(sid)
    if not sid.startswith("reel-"):
        raise ValueError("Motion review only writes reel scenes.")
    folder = reel / "motion" / sid
    if not folder.resolve().is_relative_to((reel / "motion").resolve()):
        raise ValueError("The scene folder points outside this reel's motion folder.")
    return folder


def scene_sha(folder):
    return hashlib.sha256((folder / "scene.html").read_bytes()).hexdigest()


def is_locked(folder):
    try:
        return (folder / "locked").read_text(encoding="utf-8").strip() == scene_sha(folder)
    except FileNotFoundError:
        return False


def entries(reel):
    send = read(reel / "beat-map-selection.json")
    if not isinstance(send, dict) or not isinstance(send.get("beats"), list):
        raise ValueError("The Beat Map Send is missing; Send the Beat Map first.")
    rate = Fraction(str(send["fps"]))
    if rate <= 0:
        raise ValueError("The Beat Map frame rate must be positive.")
    beats = sorted(send["beats"], key=lambda b: b["start_f"])
    compose.check_word_params(beats, rate, reel)
    out, seen = [], set()
    for beat in beats:
        fill = beat.get("scene")
        if not fill or not fill.get("id", "").startswith("reel-"):
            continue
        sid = fill["id"]
        if sid in seen:
            continue  # One card per scene, at its first timed use.
        seen.add(sid)
        scene_folder(reel, sid)
        start, end = float(beat["start_f"] / rate), float(beat["end_f"] / rate)
        if not math.isfinite(start + end) or start < 0 or end <= start:
            raise ValueError(f"{sid}: the beat needs a positive time range.")
        out.append(dict(scene=sid, beat=beat["id"], start_s=start, end_s=end, _beat=beat, _rate=rate))
    return out


def place(reel):
    paths = [reel / "beat-map.state.json", reel / "beat-map-selection.json"]
    docs = [read(path) for path in paths]
    base = next((doc for doc in docs if isinstance(doc, dict) and isinstance(doc.get("beats"), list)), None)
    if base is None:
        raise ValueError("The Beat Map is missing; make the Beat Map first.")
    docs = [copy.deepcopy(base) if doc is None else doc for doc in docs]
    for doc in docs:
        if not isinstance(doc, dict) or not isinstance(doc.get("beats"), list):
            raise ValueError("The Beat Map cannot be read; make the Beat Map again.")
    placed = {}
    for folder in sorted((reel / "motion").glob("reel-*")):
        if not folder.is_dir():
            continue
        scene_folder(reel, folder.name)
        spec = read(folder / "scene.json", {})
        named = set(re.findall(r"(?<![\w-])b_[0-9]+(?![\w-])", spec.get("source", "")))
        if len(named) != 1:
            raise ValueError(f"Scene {folder.name} must name one beat in its source.")
        bid = named.pop()
        if any(sum(b.get("id") == bid for b in doc["beats"]) != 1 for doc in docs):
            raise ValueError(f"Scene {folder.name} names beat {bid}, which is not in the Beat Map.")
        if bid in placed:
            raise ValueError(f"More than one scene names beat {bid}; keep one scene for this beat.")
        placed[bid] = folder.name
    # Check every scene before writing either document; retain fills only for the same scene.
    words = scene_fill.load_words(reel / "work/edit_map.cut.json")
    rate = float(Fraction(str(base["fps"])))
    for doc in docs:
        for beat in doc["beats"]:
            sid = placed.get(beat["id"])
            if sid:
                old = beat.get("scene") or {}
                if old.get("id") != sid:
                    old = {}
                beat["scene"] = dict(old, id=sid)
                if "slots" not in old or "params" not in old:
                    fill = scene_fill.suggest(sid, beat, words, rate, reel=reel)
                    if fill is None:
                        raise ValueError(f"Scene {sid} cannot fit beat {beat['id']}; rebuild the scene for this beat.")
                    for key in ("slots", "params"):
                        beat["scene"].setdefault(key, fill[key])
                anchor = beat["speech_anchor"]
                problems = scene_check.fill_problems(sid, beat, reel=reel,
                    words=words[anchor["w0"]:anchor["w1"] + 1])
                if problems:
                    raise ValueError(f"The scene on beat {beat['id']} needs fixing: {'; '.join(problems)}")
    for path, doc in zip(paths, docs):
        write_json(path, doc, preserve_mtime=path.name == "beat-map-selection.json")
    scene_fill.write_catalog(reel, docs[1]["beats"], words, rate)
    print(f"Placed {len(placed)} scenes on the Beat Map.")
    return 0


def editing_style(reel):
    try:
        choice, _ = compose.styles.pick_style(read(reel / "beat-map-selection.json"), reel=reel, remember=False)
    except compose.styles.Stop:
        choice = None
    if (not isinstance(choice, dict) or choice.get("style") not in compose.styles.STYLES
            or any(key not in compose.styles.STYLE_KEYS for key in choice)):
        raise ValueError("Pick the editing style first, then build the motion.")
    return choice


def estimate_text(items, reel):
    scene_seconds, passes = 0, 0
    for entry in items:
        selected_duration = entry["end_s"] - entry["start_s"]
        duration, per_fill = selected_duration, 5
        try:
            folder = scene_folder(reel, entry["scene"])
            spec = read(folder / "scene.json", {})
            # Each fill: default + worst-case text + seek with 1 and 2 workers.
            per_fill = 4
            if spec.get("kind") == "world":
                per_fill += 1  # Slot-only hold render.
            elif spec.get("kind") == "takeover" or (spec.get("kind") == "overlay" and "dy" in spec["params"]):
                per_fill += 2  # Short/worst full fills, or the two dy variants.
            html = (folder / "scene.html").read_text(encoding="utf-8")
            tag = re.search(r'data-composition-id="%s"[^>]*' % re.escape(entry["scene"]), html)
            match = re.search(r'data-duration="([\d.]+)"', tag.group(0)) if tag else None
            duration = float(match.group(1)) if match else selected_duration
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass  # The builder reports invalid scene metadata per scene after the estimate.
        # Both authored and selected fills get all checks; the loop is one more pass.
        scene_seconds += per_fill * (duration + selected_duration) + selected_duration
        passes += 2 * per_fill + 1
    seconds = math.ceil(scene_seconds * SECONDS_PER_SCENE_SECOND)
    return (f"About {seconds} seconds for {len(items)} scene{'s' if len(items) != 1 else ''} "
            f"({SECONDS_PER_SCENE_SECOND:g} seconds per scene second per render pass; "
            f"{passes} render passes total), one scene at a time.")


def run_media(args):
    rc, stdout, stderr = sr.ost.run([rt.tool("ffmpeg"), "-v", "error", "-y", *args], timeout=600)
    if rc:
        raise ValueError("Could not make the review media: " + sr.ost.tail(stdout + stderr))


class CaptionBandError(ValueError):
    def __init__(self, lines):
        super().__init__("\n".join(lines))
        self.lines = lines


def caption_band_lines(reel, beat, rate, ranges):
    """Report each crossing with cut-timed words overlapping its half-open reel range."""
    if not ranges:
        return []
    words = compose.cut_words(reel)
    beat_start, beat_end = beat["start_f"] / rate, beat["end_f"] / rate
    lines = []
    for first, last in ranges:
        start, end = (beat["start_f"] + first) / rate, (beat["start_f"] + last) / rate
        shown = []
        for word in words:
            word_start = Fraction(str(word["out_start"]))
            word_end = Fraction(str(word.get("out_end", word["out_start"])))
            if (beat_start <= word_start < beat_end and word_start < end and
                    (word_end > start or start <= word_start < end)):
                shown.append(word["word"])
        lines.append(f"Beat {beat['id']}: from {float(start):.2f} to {float(end):.2f} s the graphic crosses "
                     f"the caption band, under the words '{' '.join(shown)}'. Move it out of the band.")
    return lines


def build_media(reel, entry, work):
    sid = entry["scene"]
    edit_style = entry.get("_edit_style") or editing_style(reel)
    folder = scene_folder(reel, sid)
    env, log = sr.make_env(work)
    before = len(sr.fails)
    try:
        sr.scene_test(sid, work, env, log, False, "review", scenes_dir=reel / "motion")
        if len(sr.fails) != before:
            raise ValueError("; ".join(sr.fails[before:]))
        # Render the selected fill at the beat's duration for judging it in the real picture.
        beat, rate = entry["_beat"], entry["_rate"]
        spec = read(folder / "scene.json")
        if spec.get("kind") == "world":
            problem = compose.world_area_problem(beat, spec, reel)
            if problem:
                raise ValueError(problem)
        project = work / "selected"
        compose.scene_project(project, beat, rate, reel)
        fill = sr.fills(spec, sid)[0]
        fill.update(beat["scene"].get("slots", {}))
        fill.update(beat["scene"].get("params", {}))
        selected = work / "selected-check"
        selected.mkdir()
        sr.scene_test(sid, selected, env, log, False, "review", scenes_dir=reel / "motion",
                      html_override=(project / "index.html").read_text(encoding="utf-8"), fill_override=fill, fps=rate)
        mov = selected / f"{sid}.mov"
        frames = int(sr.probe(mov).get("nb_read_frames") or 0)
        if frames < 1:
            raise ValueError("The scene render has no frames.")
        if "caption_band" in spec:
            ranges = sr.caption_band_ranges(mov, beat["end_f"] - beat["start_f"], spec["caption_band"], spec["area"])
            lines = caption_band_lines(reel, beat, rate, ranges)
            if lines:
                raise CaptionBandError(lines)
        if len(sr.fails) != before:
            raise ValueError("; ".join(sr.fails[before:]))
        review = reel / "motion/review"
        review.mkdir(parents=True, exist_ok=True)
        run_media(["-i", mov, "-vf", f"select=eq(n\\,{frames - 1}),scale=270:480:flags=lanczos,format=rgba",
                   "-frames:v", "1", folder / "preview.png"])
        run_media(["-i", mov, "-vf", "select=eq(n\\,0),scale=270:480:flags=lanczos,format=rgba",
                   "-frames:v", "1", review / (sid + "-start.png")])
        masters = list((reel / "work/renders").glob("master-*.mp4"))
        if not masters:
            raise ValueError("The cut has no master picture; build the cut before Motion review.")
        master = max(masters, key=lambda p: p.stat().st_mtime_ns)
        x, y, w, h = compose.world_area(spec.get("area", "full"))
        duration = compose.ts(beat["end_f"] - beat["start_f"], rate)
        # Native 1080 geometry first, then downsample the whole composite. Never squeeze an area scene.
        filters = f"[0:v]trim=duration={duration},setpts=PTS-STARTPTS,scale=1080:1920"
        face_name = compose.face_layout(beat, edit_style, reel)
        fx, fy, fw, fh = compose.layout(face_name, 1)["box"]
        if face_name == "pip":
            filters += (f",split[base][picture];[picture]scale={fw}:{fh}:force_original_aspect_ratio=increase,"
                        f"crop={fw}:{fh}[face];[1:v]setpts=PTS-STARTPTS[scene];"
                        f"[base][scene]overlay={x}:{y}:shortest=1[graphic];"
                        f"[graphic][face]overlay={fx}:{fy}:shortest=1,")
        else:
            if face_name != "full":
                filters += (f",split[base][picture];[picture]scale={fw}:{fh}:force_original_aspect_ratio=increase,"
                            f"crop={fw}:{fh}[face];[base][face]overlay={fx}:{fy}:shortest=1")
            filters += f"[base];[1:v]setpts=PTS-STARTPTS[scene];[base][scene]overlay={x}:{y}:shortest=1,"
        filters += "scale=720:1280:flags=lanczos,setsar=1[out]"
        run_media(["-ss", str(entry["start_s"]), "-i", master, "-i", mov, "-filter_complex", filters,
                   "-map", "[out]", "-t", duration, "-r", compose.fpsmod.parse_fps(str(rate)),
                   "-frames:v", str(beat["end_f"] - beat["start_f"]), "-an", *gpu.h264(23, "medium"), "-pix_fmt", "yuv420p",
                   "-movflags", "+faststart", review / (sid + "-loop.mp4")])
    finally:
        sr.kill_warm()
        del sr.fails[before:]


def review_problems(doc):
    if not isinstance(doc, dict) or doc.get("schema") != 1 or not isinstance(doc.get("cards"), list):
        return ["Review needs schema 1 and cards."]
    problems = []
    for card in doc["cards"]:
        if (not isinstance(card, dict) or
            not all(isinstance(card.get(k), str) and card[k] for k in ("scene", "beat", "title", "built", "start", "loop")) or
            card.get("state") not in ("new", "rebuilt", "locked") or card.get("checks") != "passed" or
            not all(isinstance(card.get(k), (int, float)) and not isinstance(card[k], bool) and math.isfinite(card[k])
                    for k in ("start_s", "end_s")) or card["start_s"] < 0 or card["end_s"] <= card["start_s"]):
            problems.append("Invalid review card.")
    return problems


def build(reel):
    items = entries(reel)
    if not items:
        print("No motion scenes are on the Beat Map yet. Run place first.")
        return 1
    selection_path = reel / "motion-review-selection.json"
    selection = read(selection_path)
    if isinstance(selection, dict) and selection.get("none") is True and selection.get("sections") == []:
        selection_path.unlink()
        print("Your earlier 'no motion graphics' choice is cleared, because this reel now has scenes to review.")
    try:
        edit_style = editing_style(reel)
    except ValueError as error:
        print(str(error))
        return 1
    for entry in items:
        entry["_edit_style"] = edit_style
    pending = [e for e in items if not is_locked(scene_folder(reel, e["scene"]))]
    print(estimate_text(pending, reel), flush=True)
    target = reel / "motion/review/review.json"
    previous = {(e["scene"], e["beat"]): e for e in read(target, {"cards": []})["cards"]}
    notes = {(s.get("scene"), s.get("beat")) for s in read(reel / "motion-review-selection.json", {"sections": []})["sections"]
             if isinstance(s.get("note"), str) and s["note"].strip() and not s.get("leave")}
    cards, failed = [], False
    with heavy_job("Motion review"):
        for entry in items:
            sid = entry["scene"]
            folder = scene_folder(reel, sid)
            try:
                old = previous.get((sid, entry["beat"]))
                if is_locked(folder):
                    if not old:
                        raise ValueError("The locked scene has no review card; unlock it to build the review media.")
                    card = dict(old, state="locked", start_s=entry["start_s"], end_s=entry["end_s"])
                else:
                    problems = scene_check.scene_problems(folder)
                    if problems:
                        raise ValueError("; ".join(problems))
                    with tempfile.TemporaryDirectory(prefix="motion-review-") as tmp:
                        with contextlib.redirect_stdout(io.StringIO()):
                            build_media(reel, entry, Path(tmp))
                    spec = read(folder / "scene.json")
                    card = {k: entry[k] for k in ("scene", "beat", "start_s", "end_s")}
                    card.update(title=spec.get("title") or sid.replace("-", " "), built=spec["source"],
                                start=f"motion/review/{sid}-start.png", loop=f"motion/review/{sid}-loop.mp4",
                                state="rebuilt" if old and (sid, entry["beat"]) in notes else "new", checks="passed")
                cards.append(card)
            except CaptionBandError as e:
                failed = True
                for line in e.lines:
                    print(line)
            except Exception as e:
                failed = True
                print(f"{sid}: failed - {' '.join(str(e).split())}")
        doc = {"schema": 1, "reel": reel.name, "generated_at": datetime.now(timezone.utc).isoformat(), "cards": cards}
        problems = review_problems(doc)
        if problems:
            raise ValueError("; ".join(problems))
        write_json(target, doc)
        send = read(reel / "beat-map-selection.json")
        words = scene_fill.load_words(reel / "work/edit_map.cut.json")
        scene_fill.write_catalog(reel, send["beats"], words, float(Fraction(str(send["fps"]))))
    return 1 if failed else 0


def none(reel):
    write_json(reel / "motion-review-selection.json",
               {"none": True, "sections": [], "sent_at": datetime.now(timezone.utc).isoformat()})
    print("Recorded no motion graphics for this reel.")
    return 0


def apply(reel):
    doc = read(reel / "motion-review-selection.json")
    if not isinstance(doc, dict) or not isinstance(doc.get("sections"), list):
        raise ValueError("The Motion review Send is missing; Send the Motion review first.")
    # Validate everything before writing any locks.
    actions = []
    for section in doc["sections"]:
        folder = scene_folder(reel, section["scene"])
        sha = scene_sha(folder)
        note = section.get("note", "")
        if not isinstance(note, str) or not isinstance(section.get("leave"), bool):
            raise ValueError("Every Motion review section needs a note and Leave it choice.")
        actions.append((section, folder, sha, note.strip()))
    for section, folder, sha, note in actions:
        if section["leave"]:
            lock = folder / "locked"
            if not lock.exists() or lock.read_text(encoding="utf-8").strip() != sha:
                lock.write_bytes((sha + "\n").encode("ascii"))
        elif note:
            print(f"{section['scene']}: {note}")
    record_saved_style(reel)
    return 0


STYLE_ASK = "Ask the user once: punch-ins on jump cuts, or layout switches? Then record it with motion_review.py style --reel-dir <reel> --style punch-in|layout-switch."


def record_saved_style(reel):
    path = reel / "beat-map-selection.json"
    send = read(path)
    if not isinstance(send, dict):
        print("The Beat Map Send is missing; Send the Beat Map first.")
        return
    if "edit_style" in send:
        return
    try:
        edit_style, _ = compose.styles.pick_style(send, reel=reel, remember=False)
        if (not isinstance(edit_style, dict) or edit_style.get("style") not in compose.styles.STYLES
                or any(key not in compose.styles.STYLE_KEYS for key in edit_style)):
            print(STYLE_ASK)
            return
    except compose.styles.Stop:
        print(STYLE_ASK)
        return
    send["edit_style"] = edit_style
    write_json(path, send, preserve_mtime=True)
    print("Copied the saved editing style into the Beat Map Send.")


def times(reel, beat_id, word_ids):
    send = read(reel / "beat-map-selection.json")
    if not isinstance(send, dict) or not isinstance(send.get("beats"), list):
        raise ValueError("The Beat Map Send is missing; Send the Beat Map first.")
    beats = [b for b in send["beats"] if b.get("id") == beat_id]
    if len(beats) != 1:
        raise ValueError(f"Beat {beat_id} must appear exactly once in the Beat Map.")
    ids = word_ids.split(",")
    if not all(re.fullmatch(r"w_[0-9]{4,}", wid) for wid in ids):
        raise ValueError("Give comma-separated word ids like w_0013,w_0016.")
    rate = compose.fpsmod.as_fraction(str(send["fps"]))
    params = {f"t{i}": compose.word_param(beats[0], compose.cut_word(reel, wid), rate)
              for i, wid in enumerate(ids, 1)}
    print(json.dumps(params))
    return 0


def style(reel, choice):
    if choice not in compose.styles.STYLES:
        raise ValueError("Editing style must be punch-in or layout-switch.")
    path = reel / "beat-map-selection.json"
    send = read(path)
    if not isinstance(send, dict):
        raise ValueError("The Beat Map Send is missing; Send the Beat Map first.")
    state_path = reel / "beat-map.state.json"
    state = read(state_path)
    if state is not None and not isinstance(state, dict):
        raise ValueError("The Beat Map cannot be read; make the Beat Map again.")
    send["edit_style"] = {"style": choice}
    write_json(path, send, preserve_mtime=True)
    if state is not None:
        state["edit_style"] = send["edit_style"]
        write_json(state_path, state)
    return 0


def selftest():
    with tempfile.TemporaryDirectory(prefix="motion-review-selftest-") as tmp:
        reel = Path(tmp)
        folder = reel / "motion/reel-test"
        folder.mkdir(parents=True)
        (folder / "scene.html").write_bytes(b"fixture")
        write_json(reel / "motion-review-selection.json", {"sections": [
            {"scene": "reel-test", "beat": "b_001", "note": "", "leave": True}]})
        assert not is_locked(folder)
        apply(reel)
        stamp = (folder / "locked").stat().st_mtime_ns
        apply(reel)
        assert is_locked(folder) and (folder / "locked").stat().st_mtime_ns == stamp
        (folder / "scene.html").write_bytes(b"edited")
        assert not is_locked(folder)
        card = dict(scene="reel-test", beat="b_001", title="Test", built="Test world", start_s=0, end_s=4,
                    start="motion/review/reel-test-start.png", loop="motion/review/reel-test-loop.mp4",
                    state="new", checks="passed")
        assert not review_problems({"schema": 1, "cards": [card]})
        assert review_problems({"schema": 1, "cards": [dict(card, checks="failed")]})
        write_json(folder / "scene.json", {"kind": "world"})
        (folder / "scene.html").write_bytes(b'<div data-composition-id="reel-test" data-duration="4"></div>')
        assert estimate_text([card], reel) == (
            f"About {math.ceil(44 * SECONDS_PER_SCENE_SECOND)} seconds for 1 scene "
            f"({SECONDS_PER_SCENE_SECOND:g} seconds per scene second per render pass; "
            "11 render passes total), one scene at a time.")
    print("motion_review selftest ok")
    return 0


def main():
    compose.ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("build", "apply", "none", "place"):
        sub.add_parser(name).add_argument("--reel-dir", type=Path, required=True)
    times_parser = sub.add_parser("times")
    times_parser.add_argument("--reel-dir", type=Path, required=True)
    times_parser.add_argument("--beat", required=True)
    times_parser.add_argument("--words", required=True)
    style_parser = sub.add_parser("style")
    style_parser.add_argument("--reel-dir", type=Path, required=True)
    style_parser.add_argument("--style", choices=compose.styles.STYLES, required=True)
    args = ap.parse_args()
    try:
        if args.selftest:
            return selftest()
        if not args.cmd:
            ap.print_help()
            return 2
        if args.cmd == "style":
            return style(args.reel_dir.resolve(), args.style)
        if args.cmd == "times":
            return times(args.reel_dir.resolve(), args.beat, args.words)
        return globals()[args.cmd](args.reel_dir.resolve())
    except HeavyJobError as e:
        print(str(e))
        return 1
    except (OSError, ValueError, KeyError, TypeError) as e:
        print("Motion review stopped: " + " ".join(str(e).split()))
        return 1


if __name__ == "__main__":
    sys.exit(main())
