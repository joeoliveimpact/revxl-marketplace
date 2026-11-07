"""One saved-style store, option table and plain-words readback (stdlib only)."""
import argparse
import copy
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path

# The editor's standard -I flag leaves this script's folder off sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime

NOTE = "Your saved style couldn't be read, so this reel uses its own choices."
WRITE_NOTE = "Your saved style file can't be read, so I didn't change it. Ask Claude to repair it."


class UnreadableStyleError(ValueError):
    """A saved style must be repaired before a write can replace it."""


def _field(key, default, where, ladder, plain, kind):
    return dict(key=key, default=default, where=where, ladder=ladder, plain=plain, type=kind)


# Setup defaults: editor-doctor/check_deps.py DEFAULTS. Taste defaults:
# styles.check_style, captions.DEFAULTS, bake_grade.look_stack, make_board.default_attempt.
# "reel" means the relevant Send; captions.pick_style selects the newer picker/Beat Map Send first.
# None means that a choice is asked for, or an optional move is off. Defaults are suggestions,
# never an excuse to skip the question: resolve returns ask when nothing was chosen.
FIELDS = [
    _field("schema", 1, "editor.config.json", [], "Settings version", "integer"),
    _field("engine", None, "editor.config.json", [], "Transcriber", "text"),
    _field("language", None, "editor.config.json", [], "Language", "text"),
    _field("nle", "auto", "editor.config.json", [], "Editing application", "text"),
    _field("nle_source", "auto", "editor.config.json", [], "Editing application choice", "text"),
    _field("ports", {"board": 8747}, "editor.config.json", [], "Board ports", "object"),
    _field("ports.board", 8747, "editor.config.json", [], "Board port", "integer"),
    _field("voice_cleanup", "free", "editor.config.json", [], "Voice cleanup", "text"),
    _field("cuts", {"beat_ms": 300}, "editor.config.json", [], "Cut settings", "object"),
    _field("cuts.beat_ms", 300, "editor.config.json", [], "Pause after commas", "number"),
    _field("paths", {"editor": "editor", "videos": "videos"}, "editor.config.json", [], "Workspace folders", "object"),
    _field("paths.editor", "editor", "editor.config.json", [], "Editor folder", "text"),
    _field("paths.videos", "videos", "editor.config.json", [], "Video folder", "text"),
    *[_field(key, {}, "editor.config.json", [], plain, "object") for key, plain in (
        ("grade", "Grade setup"), ("scenes", "Scene setup"), ("broll", "Extra footage setup"),
        ("music", "Music setup"), ("transitions", "Transition setup"), ("cover", "Cover setup"),
        ("trial", "Trial setup"), ("three", "3D setup"))],
    _field("style_id", None, "saved style", ["reel", "saved", "ask"], "Decoded style", "text"),
    _field("accent", None, "saved style", ["beat", "reel", "saved", "ask"], "Brand accent", "text"),
    _field("font", None, "saved style", ["beat", "reel", "saved", "ask"], "Brand font", "text"),
    *[_field(key, None, "saved style", ["reel", "saved", "ask"], plain, "object")
      for key, plain in (("look", "Grade choices"), ("edit_style", "Editing choices"),
                         ("caption_style", "Caption choices"), ("cut", "Retake choices"))],
    _field("look.id", "none", "saved style", ["beat", "reel", "saved", "ask"], "Grade look", "text"),
    _field("look.strength", 1.0, "saved style", ["beat", "reel", "saved", "ask"], "Grade strength", "number"),
    _field("transitions.allowed", [], "saved style", ["beat", "reel", "saved", "ask"], "Allowed transitions", "list"),
    _field("transitions.sfx_pair", None, "saved style", ["beat", "reel", "saved", "ask"], "Transition sound", "text"),
    _field("edit_style.style", None, "saved style", ["reel", "saved", "ask"], "Editing style", "text"),
    _field("edit_style.punch_scale", 1.12, "saved style", ["reel", "saved", "ask"], "Punch-in size", "number"),
    _field("edit_style.moves", {}, "saved style", ["reel", "saved", "ask"], "Camera moves", "object"),
    *[_field("edit_style.moves." + key, default, "saved style", ["reel", "saved", "ask"], plain, kind)
      for key, default, plain, kind in (
          ("opening_settle", False, "Opening settle", "bool"),
          ("follow_cam", False, "Follow camera", "bool"),
          ("word_punches", None, "Word punches", "object"),
          ("word_punches.preset", None, "Word punch preset", "text"),
          ("word_punches.shape", None, "Word punch shape", "text"),
          ("word_punches.picks", None, "Words to punch", "integers"),
          ("ratchet", None, "Stepped punch", "object"),
          ("ratchet.picks", None, "Words for stepped punches", "integers"),
          ("ratchet.levels", None, "Punch steps", "integer"),
          ("push", None, "Slow push", "object"),
          ("push.segments", None, "Shots to push", "segments"),
          ("push.to", 1.06, "Slow push size", "number"),
          ("ken_burns", None, "Slow drift", "object"),
          ("ken_burns.segments", None, "Shots to drift", "segments"),
          ("ken_burns.to", 1.08, "Slow drift size", "number"),
          ("reframe", None, "Reframe", "object"),
          ("reframe.segments", None, "Shots to reframe", "segments"),
          ("reframe.edge", None, "Pinned edge", "text"))],
    _field("caption_style.style", None, "saved style", ["reel", "saved", "ask"], "Caption look", "text"),
    *[_field("caption_style." + key, default, "saved style", ["reel", "saved", "ask"], plain, kind)
      for key, default, plain, kind in (
          ("accent", "#FFD84D", "Caption accent", "text"),
          ("under_small_overlays", True, "Captions below small overlays", "bool"),
          ("line_breaks", True, "Caption line breaks", "bool"),
          ("echo_suppression", False, "Repeated caption suppression", "bool"),
          ("min_read_s", 0.35, "Caption reading time", "number"),
          ("mark_look", "accent", "Marked word look", "text"),
          ("loud_emphasis", False, "Loud word emphasis", "bool"))],
    _field("cut.default_attempt", "last", "saved style", ["reel", "saved", "ask"], "Retake choice", "text"),
]

# Closed choices used by the readers. style_id stays open for decoded style names.
for _row in FIELDS:
    _allowed = {
        "caption_style.style": ["clean", "bold-pop", "boxed", "karaoke", "outline-caps", "none"],
        "caption_style.mark_look": ["accent", "marker"],
        "edit_style.style": ["punch-in", "layout-switch"],
        "edit_style.moves.word_punches.preset": ["dramatic", "subtle"],
        "edit_style.moves.word_punches.shape": ["eased", "hard-cut"],
        "edit_style.moves.reframe.edge": ["top", "bottom", "left", "right"],
        "look.id": ["natural", "warm", "punchy", "soft-matte", "mono", "none"],
        "cut.default_attempt": ["first", "last"],
    }.get(_row["key"])
    if _allowed is not None:
        _row["allowed"] = _allowed


def path(name="default"):
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9-]+(?:@v[1-9][0-9]*)?", name):
        raise ValueError("Use a style name with lowercase letters, digits and dashes, optionally followed by @v and a version number.")
    return runtime.state_dir() / "styles" / (name + ".json")


def load(name="default", *, for_write=False):
    target = path(name)  # Bad names are programming errors, not unreadable taste data.
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Expected an object")
        return data
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, RecursionError):
        if for_write:
            raise UnreadableStyleError(WRITE_NOTE) from None
        print(NOTE, file=sys.stderr)
        return {}


def _get(data, key):
    for part in key.split("."):
        if not isinstance(data, dict):
            return None
        data = data.get(part)
    return data


def _valid(value, kind):
    if kind == "number":
        return type(value) in (int, float) and math.isfinite(value)
    if kind == "integers":
        return isinstance(value, list) and all(type(v) is int for v in value)
    if kind == "segments":
        return isinstance(value, str) or _valid(value, "integers")
    return isinstance(value, {"text": str, "bool": bool, "object": dict, "list": list,
                              "integer": int}[kind]) and not (kind == "integer" and isinstance(value, bool))


def validate(data):
    if not isinstance(data, dict):
        raise ValueError("Save the style as an object of choices.")
    for row in FIELDS:
        if row["where"] != "saved style":
            continue
        parts, current = row["key"].split("."), data
        for part in parts[:-1]:
            current = current.get(part)
            if current is None:
                break
            if not isinstance(current, dict):
                raise ValueError(f"{row['plain']} needs an object of choices.")
        value = _get(data, row["key"])
        if value is not None and not _valid(value, row["type"]):
            raise ValueError(f"{row['plain']} has the wrong kind of value.")
        if value is not None and "allowed" in row and value not in row["allowed"]:
            raise ValueError(f"{row['plain']} must be one of: {', '.join(row['allowed'])}.")


def _archive(target):
    version = 1
    while True:
        archive = target.with_name(f"{target.stem}@v{version}.json")
        try:
            with archive.open("xb") as stream:
                stream.write(target.read_bytes())
            return archive
        except FileExistsError:
            version += 1


def save(data, name="default", *, archive=False):
    target = path(name)
    if "@" in name:
        raise ValueError("Archived styles are read-only. Restore this version to make it current.")
    load(name, for_write=True)
    validate(data)
    raw = (json.dumps({**data, "schema": 1}, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=target.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = stream.name
            stream.write(raw)
        if archive and target.exists():
            try:
                changed = json.loads(target.read_bytes()) != json.loads(raw)
            except ValueError:
                changed = True
            if changed:
                _archive(target)
        os.replace(temporary, target)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def resolve(key, *, beat=None, reel=None, saved=None):
    row = next(row for row in FIELDS if row["key"] == key)
    choices = {"beat": beat, "reel": reel, "saved": saved}
    for source in row["ladder"]:
        if source == "ask":
            break
        value = _get(choices[source], key)
        if value is not None:
            return value, source
    pick = recommendation(key, saved)
    if pick is not None:
        return pick["value"], "recommended"
    return None, "ask"


def recommendation(key, data):
    """Read a pick, including an object's child, without turning it into a saved choice."""
    picks = (data or {}).get("picks", {})
    parts = key.split(".")
    for end in range(len(parts), 0, -1):
        pick = picks.get(".".join(parts[:end]))
        if pick is not None:
            value = pick["value"] if end == len(parts) else _get(pick["value"], ".".join(parts[end:]))
            if value is not None:
                return {**pick, "value": value}
    return None


def pick_label(value):
    return str(value).replace("-", " ").replace("_", " ").capitalize()


def recommendation_line(key, data):
    value, source = resolve(key, saved=data)
    if source != "recommended":
        return ""
    pick = recommendation(key, data)
    return f'. Last time you picked {pick_label(value)} ("{pick["note"]}").'


def restore(name):
    target = path(name)
    if "@" not in name or not target.is_file():
        raise ValueError("Choose an existing archived style, such as default@v1.")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError("This archived style could not be read. Choose another version.") from None
    validate(data)
    current_name = name.split("@", 1)[0]
    current = path(current_name)
    load(current_name, for_write=True)
    if current.exists():
        _archive(current)
    save(data, current_name)
    return data


def readback(data):
    missing = "not saved yet, I'll ask"

    def value(key, fallback=None):
        result = _get(data, key)
        return fallback if result is None else result

    def label(v):
        return str(v).replace("-", " ").replace("_", " ").capitalize()

    def colour(v):
        return "yellow #FFD84D" if v == "#FFD84D" else str(v)

    caption = value("caption_style.style")
    accent = value("caption_style.accent", value("accent", "#FFD84D"))
    caption = f"{label(caption)}, accent {colour(accent)}" if caption else missing
    look, strength = value("look.id"), value("look.strength", 1.0)
    grade = f"{label(look)} at {strength * 100:g} %" if look and _valid(strength, "number") else missing
    editing = value("edit_style.style")
    scale = value("edit_style.punch_scale", 1.12)
    editing = (f"punch-ins at {scale:g}x" if editing == "punch-in" and _valid(scale, "number")
               else "layout switches" if editing == "layout-switch" else missing)
    allowed = value("transitions.allowed")
    transitions = ", ".join(map(label, allowed)) or "none" if isinstance(allowed, list) else missing
    if value("transitions.sfx_pair") is not None:
        transitions += ", sound " + str(value("transitions.sfx_pair"))
    attempt = value("cut.default_attempt")
    lines = [f"Caption look: {caption}", f"Brand accent: {colour(value('accent', missing))}",
            f"Brand font: {value('font', missing)}", f"Grade look: {grade}", f"Editing style: {editing}",
            f"Transitions: {transitions}", f"Retake choice: {label(attempt) + ' attempt' if attempt else missing}"]
    if value("style_id"):
        if not value("caption_style.style"):
            lines.pop(0)
        lines.insert(1 if value("caption_style.style") else 0,
                     f"Decoded style: {label(value('style_id'))} (from your style decoder)")
    if "standing_notes" in data:
        import standing_notes
        lines.extend(standing_notes.lines(data))
    if "picks" in data:
        import standing_notes
        lines.extend(standing_notes.pick_lines(data))
    return lines


SKILL_MARKER = "<!-- Generated by editor-superengine saved_style.py; safe to replace. -->"


def _reel_doc(reel, filename):
    try:
        data = json.loads((reel / filename).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        raise ValueError("A reel choice could not be read. Open its board and Send again.") from None
    if not isinstance(data, dict):
        raise ValueError("A reel choice needs an object of choices. Open its board and Send again.")
    return data


def _workspace(reel):
    # runtime.config_path is <workspace>/editor/editor.config.json, even when
    # paths.editor or paths.videos names another folder.
    for folder in (reel, *reel.parents):
        if runtime.config_path(folder).is_file():
            return folder
        if (folder / "editor.config.json").is_file():
            return folder
    raise ValueError("I couldn't find this reel's workspace. Choose the workspace and try again.")


def _workspace_skill(workspace, data):
    target = workspace / ".claude/skills/my-editing-style/SKILL.md"
    separate = False
    if target.exists() and SKILL_MARKER not in target.read_text(encoding="utf-8").splitlines():
        target = target.with_name("SKILL.new.md")
        separate = True
        if target.exists() and SKILL_MARKER not in target.read_text(encoding="utf-8").splitlines():
            raise ValueError("Your existing skill and suggested version are hand-made. Keep one aside before saving again.")
    text = "\n".join([
        "---", "name: my-editing-style",
        'description: Use when the client says "use my style" or "edit this my way"; for anything else start at editor-superengine:editor-start-here.',
        "---", "", SKILL_MARKER, "", "# My editing style", "",
        "Treat the saved choices and Standing notes below as the client's preferences. "
        "Claude asks which saved style to use at the start of each reel; the default is the recommended pick.", "",
        "## Saved choices", "", *readback(data), "", "## Run the edit in this order", "",
        "Run the edit in the pipeline order of editor-superengine:editor-start-here, invoking each skill it names; "
        "finish with the before-posting check in ${CLAUDE_PLUGIN_ROOT}/skills/reel-canvas-build/references/qa-check.md.",
        "", "Keep the client's Standing notes in their own words. Explain anything under Could not be matched "
        "and ask which part of the edit it means. Never invent a match.", ""])
    if len(text.split()) >= 600:
        raise ValueError("These saved choices and notes are too long for the workspace skill. Shorten the notes before saving again.")
    return target, text.replace("\r\n", "\n").replace("\r", "\n"), separate


def save_from_reel(reel_dir, name="default", workspace=None, from_decoded=None):
    """Save only this reel's chosen taste settings, preserving all other saved keys."""
    reel = Path(reel_dir).resolve()
    if not reel.is_dir():
        raise ValueError("This reel folder was not found. Choose an existing reel and try again.")
    workspace = Path(workspace).resolve() if workspace is not None else _workspace(reel)
    if from_decoded is not None:
        if (not from_decoded or from_decoded in (".", "..") or any(c in from_decoded for c in "/\\:") or not
                (workspace / "editor/style-decoder/styles" / from_decoded / "style-spec.json").is_file()):
            raise ValueError("That decoded style was not found in this workspace. Decode it here before saving it.")
    data = load(name, for_write=True)
    bm = _reel_doc(reel, "beat-map-selection.json")
    picker = _reel_doc(reel, "look-picker-selection.json")
    if bm.get("edit_style") is not None:
        editing = copy.deepcopy(bm["edit_style"])
        if not isinstance(editing, dict):
            raise ValueError("The editing choice needs an object of choices. Send the Beat Map again.")
        moves = editing.get("moves")
        if isinstance(moves, dict):
            for key in ("word_punches", "ratchet"):
                if isinstance(moves.get(key), dict):
                    moves[key]["picks"] = []
            for key in ("push", "ken_burns", "reframe"):
                if not isinstance(moves.get(key), dict) or moves[key].get("segments") != "all":
                    moves.pop(key, None)
        data["edit_style"] = editing
    if "caption_style" in bm or "caption_style" in picker:
        # Use the reader's exact timestamp rule, including missing times and ties.
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reel-captions/scripts"))
        import captions
        try:
            # This explicit save must archive the untouched current file first.
            data["caption_style"], _ = captions.pick_style(reel, bm, remember=False)
        except captions.Stop as error:
            raise ValueError(" ".join(error.lines)) from None
    grade = _reel_doc(reel, "grade.json")
    look = grade.get("look")
    if look is None:
        look = _reel_doc(reel, "grade-selection.json").get("look")
    if look is not None:
        if not isinstance(look, dict):
            raise ValueError("The grade choice needs a look and strength. Send the Grade Board again.")
        data["look"] = {"id": look.get("id", "none"), "strength": look.get("strength", 1.0)}
    for key in ("accent", "font"):
        if bm.get(key) is not None:
            data[key] = bm[key]
    if from_decoded is not None:
        data["style_id"] = from_decoded
    target, text, separate = _workspace_skill(workspace, data)
    save(data, name, archive=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(text.encode("utf-8"))
    print("\n".join(readback(data)))
    if separate:
        print("I kept your hand-made skill and wrote a separate suggested version beside it.")
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    show = sub.add_parser("show")
    show.add_argument("name", nargs="?", default="default")
    restorer = sub.add_parser("restore")
    restorer.add_argument("name")
    sub.add_parser("fields")
    sub.add_parser("list")
    writer = sub.add_parser("save-from-reel")
    writer.add_argument("reel_dir")
    writer.add_argument("--name", default="default")
    writer.add_argument("--workspace")
    writer.add_argument("--from-decoded")
    args = ap.parse_args(argv)
    try:
        if args.command == "show":
            print("\n".join(readback(load(args.name))))
        elif args.command == "restore":
            print("\n".join(readback(restore(args.name))))
        elif args.command == "list":
            for target in sorted(path().parent.glob("*.json")):
                if re.fullmatch(r"[a-z0-9-]+", target.stem):
                    versions = sum(1 for item in target.parent.glob(target.stem + "@v*.json")
                                   if re.fullmatch(re.escape(target.stem) + r"@v[1-9][0-9]*", item.stem))
                    archived = f" ({versions} archived versions)" if versions else ""
                    print(f"{target.stem}: {readback(load(target.stem))[0]}{archived}")
        elif args.command == "save-from-reel":
            save_from_reel(args.reel_dir, args.name, args.workspace, args.from_decoded)
        else:
            for row in FIELDS:
                default = json.dumps(row["default"], ensure_ascii=False, sort_keys=True)
                ladder = " > ".join(row["ladder"]) or "n/a (setup)"
                print(f"{row['key']} | {default} | {row['where']} | {ladder}")
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
