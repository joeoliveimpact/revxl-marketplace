"""N5: validate and render trial reels from one approved cut, one declared change each.

Claude runs plan --reel-dir REEL --spec FILE, then render --reel-dir REEL [--only ID].
All generated files live in trials/. --selftest needs no media tools.
"""
import argparse
import contextlib
import copy
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE.parents[2]
sys.path[:0] = [str(P / "skills/reel-canvas-build/scripts"), str(P / "skills/_shared"),
               str(P / "skills/_shared/checks"), str(P / "skills/caption-writer/scripts")]
try:
    import compose
    import beat_schema
    import saved_style
    import loop_check
    from check_caption import numbers
    FORBIDDEN = re.compile(json.loads((HERE.parent / "boards/trials/wording.json").read_text(encoding="utf-8")), re.I)
except Exception:
    print("The trial-reel tools could not load; restore the editor installation and try again.")
    sys.exit(1)

CHANGES = {"opening": {"scene", "slots", "params"}, "hook": {"hook_text"},
           "reframe": {"field", "value"}, "grade": {"look", "strength"}}
MATCH_MAD = 2.0  # 8-bit RGB, downsampled to 160x284; codec noise tolerance, not a taste score
DIFFER_MAD = .1
REVIEW_FILES = {"trials.state.json", "trials.state.json.prev", "trials-selection.json",
                "trials.state.json.tmp", "trials.state.json.prev.tmp", "trials-selection.json.tmp"}


class Stop(Exception):
    """One plain line, never raw tool output or a traceback."""


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError("non-finite JSON number")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique, parse_constant=invalid_constant)
    except (OSError, ValueError):
        raise Stop("A required reel file could not be read; restore it or Send its board again.") from None


def save(path, doc):
    compose.write_json(Path(path), doc)


def digest(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def text_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from text_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from text_values(item)


def honest(value):
    if any(FORBIDDEN.search(text) for text in text_values(value)):
        raise Stop("Use honest trial-reel wording; remove the audience-experiment claim.")


def no_retiming(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if re.search(r"(?:^|[._-])(speed|fps|cuts?|segments?)(?:$|[._-])", key, re.I) and key != "segments":
                raise Stop("Trial reels cannot change speed, frame rate or cuts; keep the approved voice untouched.")
            # Camera-move segment selectors are allowed; they never change the cut list.
            if key == "segments" and not (item == "all" or isinstance(item, list)):
                raise Stop("Use the existing shots for a camera move; never change the cut list.")
            no_retiming(item)
    elif isinstance(value, list):
        for item in value:
            no_retiming(item)


def truthful(text, source):
    heard = numbers(source)
    for value, shown in numbers(text).items():
        if value not in heard:
            raise Stop(f'The number "{shown}" was not said in this reel; use the speaker\'s own numbers.')


def source_words(reel):
    for rel in (beat_schema.DEFAULT_WORDS, "work/words.json"):
        path = reel / rel
        if path.is_file():
            doc = read(path)
            words = doc.get("words") if isinstance(doc, dict) else None
            if not isinstance(words, list) or not all(isinstance(w, dict) and isinstance(w.get("word"), str) for w in words):
                raise Stop("The reel needs its own spoken word list before making trials.")
            return " ".join(w["word"] for w in words)
    raise Stop("The reel needs its own spoken word list before making trials.")


def first_beat(doc):
    beats = doc.get("beats") if isinstance(doc, dict) else None
    first = next((b for b in beats or [] if isinstance(b, dict) and b.get("start_f") == 0), None)
    if first is None:
        raise Stop("The approved Beat Map needs a beat at frame zero before making trials.")
    return first


def put(doc, field, value):
    parts = field.split(".")
    current = doc
    for part in parts[:-1]:
        if current.get(part) is None:
            current[part] = {}
        if not isinstance(current[part], dict):
            raise Stop("The chosen editing field has no object to hold it; choose an existing field.")
        current = current[part]
    current[parts[-1]] = copy.deepcopy(value)


def apply_version(doc, version):
    """The entire Send is preserved except the ONE declared field; hook/grade are render inputs."""
    changed = copy.deepcopy(doc)
    if version["change"] == "opening":
        first_beat(changed)["scene"] = (None if version["scene"] is None else
                                      {"id": version["scene"], "slots": copy.deepcopy(version["slots"]),
                                       "params": copy.deepcopy(version.get("params", {}))})
    elif version["change"] == "reframe":
        put(changed, version["field"], version["value"])
    return changed


def validate_spec(spec, doc, source, current_look):
    honest(spec)
    no_retiming(spec)
    if not isinstance(spec, dict) or set(spec) != {"versions"}:
        raise Stop("Give the trial spec one versions list, with two to four versions.")
    versions = spec["versions"]
    if not isinstance(versions, list) or not 2 <= len(versions) <= 4:
        raise Stop("Choose two to four trial versions, each changing one thing.")
    first = first_beat(doc)
    fields = {row["key"]: row for row in saved_style.FIELDS}
    seen = set()
    for version in versions:
        if not isinstance(version, dict):
            raise Stop("Each trial version needs an id and exactly one declared change.")
        ident, change = version.get("id"), version.get("change")
        if not isinstance(ident, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", ident) or ident == "base" or ident in seen:
            raise Stop("Give each trial a unique short id such as t1; base is reserved.")
        seen.add(ident)
        if not isinstance(change, str) or change not in CHANGES:
            raise Stop("Declare exactly one change: opening, hook, reframe or grade.")
        if set(version) - {"id", "change", "note", *CHANGES[change]}:
            raise Stop("Each version may change only its declared thing; remove the extra fields.")
        if "note" in version and not isinstance(version["note"], str):
            raise Stop("A trial note must be plain text.")
        if change == "hook":
            text = version.get("hook_text")
            if not isinstance(text, str) or not text.strip() or len(text) > compose.HOOK_MAX_CHARS:
                raise Stop(f"Use a spoken hook title of at most {compose.HOOK_MAX_CHARS} characters.")
            if first.get("scene") is not None:
                raise Stop("This opening uses a scene, so its plain hook title is hidden; choose an opening trial instead.")
            if " ".join(text.split()) == " ".join(first["speech_anchor"]["text"].split()):
                raise Stop("That hook is unchanged; choose different truthful words.")
            truthful(text, source)
        elif change == "opening":
            if "scene" not in version:
                raise Stop("Choose an opening scene, or null for the plain hook title.")
            sid = version["scene"]
            if sid is None:
                if version.get("slots") not in (None, {}) or version.get("params") not in (None, {}):
                    raise Stop("A plain hook title has no scene slots or parameters.")
            else:
                if not isinstance(sid, str) or not re.fullmatch(r"[a-z0-9-]+", sid):
                    raise Stop("Choose an opening scene from the editor's scene catalog.")
                fill = {"id": sid, "slots": version.get("slots"), "params": version.get("params", {})}
                issues = compose.scene_check.fill_problems(sid, fill, words=source.split())
                if issues:
                    raise Stop("The opening scene needs a valid fill: " + " ".join(issues))
                if compose.scene_check.scene_problems(P / "scenes" / sid):
                    raise Stop("That opening scene is not ready in the installed catalog; finish its scene proof first.")
                scene_spec = read(P / "scenes" / sid / "scene.json")
                duration = (first["end_f"] - first["start_f"]) / doc["fps"]
                if not scene_spec["dur"][0] <= duration <= scene_spec["dur"][1]:
                    raise Stop("That scene does not fit the approved opening's length; choose another scene.")
                if sid == "slots":
                    starts = version.get("params", {}).get("section_starts", scene_spec["params"]["section_starts"]["default"])
                    if any(float(t) >= duration for t in starts.split(",")):
                        raise Stop("The slots section starts do not fit this opening; choose another opening scene.")
                for text in version["slots"].values():
                    truthful(text, source)
            if first_beat(apply_version(doc, version))["scene"] == first.get("scene"):
                raise Stop("That opening is unchanged; choose another scene or fill.")
        elif change == "reframe":
            field = version.get("field")
            if not isinstance(field, str) or not field.startswith("edit_style.") or field not in fields or "value" not in version:
                raise Stop("Choose exactly one edit_style field from the saved-style fields and its value.")
            row, value = fields[field], version["value"]
            if not saved_style._valid(value, row["type"]) or "allowed" in row and value not in row["allowed"]:
                raise Stop("That editing field needs a value from its saved-style options.")
            changed = apply_version(doc, version)
            saved_style.validate({"edit_style": changed["edit_style"]})
            try:
                compose.styles.check_style(changed["edit_style"], "reel", len(source.split()))
            except compose.styles.Stop:
                raise Stop("That camera choice cannot be rendered; choose a complete editing-field value.") from None
            if changed == doc:
                raise Stop("That editing field is unchanged; choose another value.")
        elif change == "grade":
            look = version.get("look")
            if not isinstance(look, str) or look not in fields["look.id"]["allowed"] or look == current_look:
                raise Stop("Choose a saved-style colour look different from this reel's current look.")
            strength = version.get("strength", 1.0)
            if type(strength) not in (int, float) or not math.isfinite(strength) or not 0 < strength <= 1:
                raise Stop("Choose a colour strength above zero and at most one.")
    return copy.deepcopy(spec)


def approved(reel):
    preview = compose.latest_preview(reel / "renders")
    ok = read(reel / compose.OK_FILE) if (reel / compose.OK_FILE).is_file() else None
    problem = compose.ok_problem(ok, preview.name if preview else None, preview.stat().st_mtime if preview else 0)
    if problem:
        raise Stop(problem)


def current_look(reel):
    for rel in ("grade.json", "grade-selection.json"):
        if (reel / rel).is_file():
            look = read(reel / rel).get("look")
            if isinstance(look, dict) and isinstance(look.get("id"), str):
                return look["id"]
    saved = saved_style.load(reel)
    return (saved.get("look") or {}).get("id", "none")


def hashes(reel):
    """Fingerprint every original input/approval and the shared taste choices. Never follow symlinks."""
    found = {}
    for folder, dirs, files in os.walk(reel, followlinks=False):
        root = Path(folder)
        if root == reel:
            dirs[:] = [name for name in dirs if name != "trials"]
        for name in dirs + files:
            if (root / name).is_symlink():
                raise Stop("Trial inputs must be regular files; remove linked reel inputs before making trials.")
        for name in files:
            if root == reel and name in REVIEW_FILES:
                continue  # Client review is an output of these trials, never a render input.
            path = root / name
            found[path.relative_to(reel).as_posix()] = digest(path)
    pick = saved_style.pick_for(reel)
    style = saved_style.path(pick["style"]) if pick and pick["style"] else None
    found["@saved-style"] = digest(style) if style is not None and style.is_file() else None
    return found


def safe_trials(reel):
    """Keep every write under the real reel, including on retries with pre-existing folders."""
    root = reel / "trials"
    if root.is_symlink() or root.exists() and not root.is_dir():
        raise Stop("The trial folder must be a regular folder inside this reel.")
    for folder, dirs, files in os.walk(root, followlinks=False):
        if any((Path(folder) / name).is_symlink() for name in dirs + files):
            raise Stop("Remove linked files from this reel's trial folder before continuing.")


def report_file(reel, row):
    ident, rel = row.get("id"), row.get("file")
    if (not isinstance(ident, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", ident) or
            not isinstance(rel, str) or not rel.startswith("trials/" + ident + "/") or
            any(part in ("", ".", "..") or "\\" in part or ":" in part for part in rel.split("/")) or
            not rel.endswith(".mp4")):
        raise Stop("The saved trial report has an invalid file path; plan the trials again.")
    return reel / rel


def plan(reel, spec_path):
    safe_trials(reel)
    doc = read(reel / compose.SEND)
    source = source_words(reel)
    spec = validate_spec(read(spec_path), doc, source, current_look(reel))
    approved(reel)
    compose.load_inputs(reel)
    loop_rows = loop_check.run({"reel_dir": reel})
    if loop_rows:
        raise Stop(loop_rows[0]["msg"])
    honest(doc)
    spec.update(schema=1, base_hashes=hashes(reel), current_look=current_look(reel))
    honest(spec)
    save(reel / "trials/trials.json", spec)
    # Old reports cannot describe a newly planned set, even if ids happen to match.
    (reel / "trials/trials-report.json").unlink(missing_ok=True)
    return spec


def scratch_render(reel, doc, hook, destination):
    """compose owns its side effects inside an independent, disposable copy of the reel."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="inputs-", dir=destination.parent) as temp:
        scratch = Path(temp) / reel.name

        def ignore(folder, names):
            if Path(folder) == reel:
                return [name for name in names if name in ("trials", "renders")]
            return [name for name in names if name == "render-tmp"]

        shutil.copytree(reel, scratch, ignore=ignore, copy_function=shutil.copy2)
        save(scratch / compose.SEND, doc)
        # Both import-time callers and caption placement share the same compose module.
        summary = compose.render(scratch, "preview", hook, remember_choices=False, style_reel=reel)
        rendered = scratch / summary["out"]
        if not rendered.is_file():
            raise Stop("The trial preview did not produce a file; retry this version.")
        os.replace(rendered, destination)


def grade(base, version, destination):
    sys.path.insert(0, str(P / "skills/reel-grade/scripts"))
    import bake_grade
    import apply_grade
    lattice, _, _ = bake_grade.bake({"look": {"id": version["look"], "strength": version.get("strength", 1.0)}})
    import numpy as np
    if np.allclose(lattice, bake_grade.identity_lattice(33)):
        raise Stop("That look cannot change the already baked base preview; choose another colour look.")
    cube = destination.parent / "look.cube"
    bake_grade.write_cube(cube, lattice, 33, "Trial colour look")
    apply_grade.apply(base, cube, destination)


def frame_differences(base, trial, count):
    """Every frame, bounded memory. Small RGB decode avoids a many-GB comparison buffer."""
    import numpy as np
    args = [compose.rt.tool("ffmpeg"), "-v", "error", "-i"]
    tail = ["-map", "0:v:0", "-vf", "scale=160:284", "-pix_fmt", "rgb24", "-vsync", "0", "-f", "rawvideo", "-"]
    processes = []
    try:
        for path in (base, trial):
            processes.append(subprocess.Popen([*args, str(path), *tail], stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, env=compose.rt.python_env()))
        size, values = 160 * 284 * 3, []
        for _ in range(count):
            frames = [proc.stdout.read(size) for proc in processes]
            if any(len(frame) != size for frame in frames):
                raise Stop("A trial frame could not be compared; the unfinished version was deleted.")
            a, b = (np.frombuffer(frame, dtype=np.uint8).astype(np.int16) for frame in frames)
            values.append(float(np.abs(a - b).mean()))
        if any(proc.stdout.read(1) for proc in processes):
            raise Stop("A trial has extra picture frames; the unfinished version was deleted.")
        if any(proc.wait(timeout=60) for proc in processes):
            raise Stop("The trial picture check could not finish; retry this version.")
        return values
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            proc.stdout.close()


def verify(base, trial, change, opening_f):
    frames = compose.fpsmod.frame_count(base)
    other = compose.fpsmod.frame_count(trial)
    fps = compose.fpsmod.resolve_fps(base)
    same_rate = compose.fpsmod.resolve_fps(trial) == fps
    audio = compose.packet_md5(base, "a")
    same_audio = bool(audio) and compose.packet_md5(trial, "a") == audio
    checks = {"frames_equal": frames == other, "fps_equal": same_rate, "audio_equal": same_audio,
              "picture_ok": False, "match_mad_limit": MATCH_MAD}
    if not all((frames == other, same_rate, same_audio)):
        return checks
    values = frame_differences(base, trial, frames)
    if change == "unchanged":
        checks["base_matches_approved"] = all(value <= MATCH_MAD for value in values)
        checks["max_mad"] = max(values, default=0.0)
        checks["picture_ok"] = checks["base_matches_approved"]
    elif change in ("opening", "hook"):
        window = min(opening_f, frames)
        if change == "hook":
            window = min(window, round(compose.HOOK_MAX_S * compose.fpsmod.as_fraction(fps)))
        inside, after = values[:window], values[window:]
        checks.update(opening_differs=bool(inside) and max(inside) > DIFFER_MAD,
                      after_matches=all(value <= MATCH_MAD for value in after),
                      after_max_mad=max(after, default=0.0), opening_max_mad=max(inside, default=0.0))
        checks["picture_ok"] = checks["opening_differs"] and checks["after_matches"]
    else:
        # A local punch is not evidence of a whole-reel change. Require differences
        # in each temporal third, allowing unmoving frames at a move's boundary.
        thirds = [values[i * frames // 3:(i + 1) * frames // 3] for i in range(3)]
        checks["differs_throughout"] = all(part and max(part) > DIFFER_MAD for part in thirds)
        checks["third_max_mad"] = [max(part, default=0.0) for part in thirds]
        checks["picture_ok"] = checks["differs_throughout"]
    return checks


def describe(version):
    change = version["change"]
    if change == "opening":
        return "Opening scene: " + (version["scene"] or "plain hook title")
    if change == "hook":
        return "Hook title: " + version["hook_text"]
    if change == "reframe":
        row = next(row for row in saved_style.FIELDS if row["key"] == version["field"])
        return row["plain"] + ": " + json.dumps(version["value"], ensure_ascii=False)
    return "Colour look: " + version["look"]


def record(reel, path, ident, change, checks):
    return {"id": ident, "change": change, "file": path.relative_to(reel).as_posix(), "sha256": digest(path),
            "frames": compose.fpsmod.frame_count(path), "fps": compose.fpsmod.resolve_fps(path),
            "audio_md5": compose.packet_md5(path, "a"), "checks": checks}


def render(reel, only=None):
    safe_trials(reel)
    root = reel / "trials"
    planned = read(root / "trials.json")
    approved(reel)
    if planned.get("base_hashes") != hashes(reel):
        raise Stop("The approved reel inputs changed after planning; plan the trials again.")
    doc = read(reel / compose.SEND)
    versions = validate_spec({"versions": planned.get("versions")}, doc, source_words(reel), planned["current_look"])["versions"]
    if only is not None and only not in {row["id"] for row in versions}:
        raise Stop("That trial id is not in this plan; choose one of its versions.")
    day = datetime.now().strftime("%m.%d.%y")
    report_path = root / "trials-report.json"
    previous = read(report_path) if report_path.is_file() else {}
    report = {"schema": 1, "plan_sha256": digest(root / "trials.json"), "opening_f": first_beat(doc)["end_f"],
              "versions": []}
    if previous.get("plan_sha256") == report["plan_sha256"]:
        report["versions"] = previous.get("versions", [])
    base_row = previous.get("base") if previous.get("plan_sha256") == report["plan_sha256"] else None
    if base_row and base_row.get("id") != "base":
        raise Stop("The saved base trial is invalid; plan the trials again.")
    base = report_file(reel, base_row) if base_row else root / "base" / f"{reel.name} Trial base - {day}.mp4"
    if not (base_row and base.is_file() and digest(base) == base_row["sha256"]):
        base.unlink(missing_ok=True)
        try:
            scratch_render(reel, doc, None, base)
            if not compose.packet_md5(base, "a"):
                raise Stop("The base trial has no sound packets; make the base preview again.")
        except BaseException:
            base.unlink(missing_ok=True)
            raise
        report["versions"] = []
    try:
        preview = compose.latest_preview(reel / "renders")
        base_checks = verify(preview, base, "unchanged", report["opening_f"])
        if not all(base_checks[key] for key in ("frames_equal", "fps_equal", "audio_equal", "picture_ok")):
            raise Stop("The base no longer matches the approved preview; rebuild and approve that preview, then plan trials again.")
    except BaseException:
        base.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)
        raise
    retained = []
    for row in report["versions"]:
        path = report_file(reel, row)
        declared = next((v for v in versions if v["id"] == row["id"]), None)
        if path.is_file() and row.get("sha256") == digest(path) and row.get("declared") == declared:
            retained.append(row)
    report["versions"] = retained
    save(root / "base" / compose.SEND, doc)
    report["base"] = record(reel, base, "base", "unchanged", base_checks)
    save(report_path, report)
    for version in versions:
        ident = version["id"]
        if only is not None and only != ident:
            continue
        destination = root / ident / f"{reel.name} Trial {ident} - {day}.mp4"
        destination.parent.mkdir(parents=True, exist_ok=True)
        report["versions"] = [row for row in report["versions"] if row["id"] != ident]
        save(report_path, report)
        try:
            save(destination.parent / compose.SEND, apply_version(doc, version))
            if version["change"] == "grade":
                grade(base, version, destination)
            else:
                scratch_render(reel, apply_version(doc, version), version.get("hook_text"), destination)
            checks = verify(base, destination, version["change"], report["opening_f"])
            if not all(checks[key] for key in ("frames_equal", "fps_equal", "audio_equal", "picture_ok")):
                raise Stop(f'Trial {ident} failed its voice, timing or picture check; its file was deleted.')
            if planned["base_hashes"] != hashes(reel):
                raise Stop("The reel inputs changed during rendering; the unfinished version was deleted.")
            row = record(reel, destination, ident, version["change"], checks)
            row.update(description=describe(version), declared=version)
            report["versions"].append(row)
            honest(report)
            save(report_path, report)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
    return report


def selftest():
    doc = {"fps": 30, "beats": [{"start_f": 0, "end_f": 60, "scene": None,
                               "speech_anchor": {"text": "Clear cuts"}}],
           "edit_style": {"style": "punch-in", "punch_scale": 1.18}}
    good = {"versions": [{"id": "t1", "change": "hook", "hook_text": "3 clear cuts"},
                         {"id": "t2", "change": "grade", "look": "warm"}]}
    validate_spec(good, doc, "3 clear cuts", "none")
    mutants = []
    for fields in ({"look": "warm"}, {"speed": 1.02}, {"fps": 24}, {"hook_text": "5x easier"},
                   {"note": "A" + "/B" + " test"}, {"hook_text": "a" + "btest"}):
        bad = copy.deepcopy(good)
        bad["versions"][0].update(fields)
        mutants.append(bad)
    for bad in mutants:
        try:
            validate_spec(bad, doc, "3 clear cuts", "none")
        except Stop:
            continue
        raise Stop("A trial spec self-check failed.")
    print("selftest ok")
    return 0


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Stop("The trial request is incomplete; Claude should supply the reel and spec or trial id.")


def main(argv=None):
    ap = Parser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="command")
    planner = sub.add_parser("plan")
    planner.add_argument("--reel-dir", required=True, type=Path)
    planner.add_argument("--spec", required=True, type=Path)
    renderer = sub.add_parser("render")
    renderer.add_argument("--reel-dir", required=True, type=Path)
    renderer.add_argument("--only")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.command is None:
        raise Stop("Choose plan or render for this trial reel.")
    reel = args.reel_dir.resolve()
    # Tool chatter may contain client text or multiple errors. Only our plain summary leaves this entry point.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        result = plan(reel, args.spec) if args.command == "plan" else render(reel, args.only)
    count = len(result["versions"])
    print(f"{count} trial versions {'planned' if args.command == 'plan' else 'ready'}.")
    return 0


def guarded():
    try:
        return main()
    except Stop as error:
        line = " ".join(str(error).split())
        print(line if not FORBIDDEN.search(line) else "Remove the audience-experiment wording and try again.")
        return 1
    except KeyboardInterrupt:
        print("Trial-reel work was stopped; retry when ready.")
        return 1
    except SystemExit as error:
        return error.code
    except Exception:
        print("The trial-reel step could not finish; check the reel inputs and editor setup, then retry.")
        return 1


if __name__ == "__main__":
    sys.exit(guarded())
