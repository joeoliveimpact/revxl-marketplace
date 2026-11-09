"""One saved-style store, option table and plain-words readback (stdlib only)."""
import argparse
import copy
import datetime as dt
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
    _field("controls", "simple", "editor.config.json", [], "Controls", "text"),
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
    _field("transitions.sfx_pair", None, "saved style", ["beat", "reel", "saved", "ask"], "Transition sound", "bool"),
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
    _field("cut.pause_ms", None, "saved style", ["reel", "saved", "ask"], "Pause between lines", "number"),
    _field("cut.nudge_ms", None, "saved style", ["reel", "saved", "ask"], "Cut timing", "number"),
    _field("music.bed_gain_db", None, "saved style", ["reel", "saved", "ask"], "Music level", "number"),
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
    if _row["key"] == "cut.nudge_ms":
        _row.update(min=0, max=150)


def path(name=None):
    if name is None:
        name = active_name()
    # Dotted sibling stems, including archived siblings, are never style ids.
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9-]+(?:@v[1-9][0-9]*)?", name):
        raise ValueError("Use a style name with lowercase letters, digits and dashes, optionally followed by @v and a version number.")
    return runtime.state_dir() / "styles" / (name + ".json")


def load(reel=None, *, name=None, for_write=False):
    """Read a reel's own pick, or an explicitly named style for management."""
    if name is not None:
        return _read(name, for_write=for_write)
    if reel is None:
        return {}
    index = _index(for_write=for_write)
    current = index["picks"].get(str(Path(reel).resolve()))
    chosen = current["style"] if current else None
    data = _read(chosen, for_write=for_write) if chosen else {}
    # Recommendations are available before a style pick too; never borrow saved choices or write them back.
    if not for_write and "picks" not in data:
        picks = _read("default").get("picks") if chosen != "default" else None
        if picks is not None:
            data["picks"] = copy.deepcopy(picks)
    return data


def _read(name, *, for_write=False):
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


INDEX_NOTE = "Your saved style names couldn't be read, so I'll ask you to choose again."
INDEX_WRITE_NOTE = "Your saved style names can't be read, so I didn't change them. Ask Claude to repair them."
_index_noted = set()


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _blank(value):
    return value is None or value in ([], {}, "") or isinstance(value, dict) and all(_blank(v) for v in value.values())


def _has_choices(data, *, ignore_style_id=False):
    ignored = ("schema", "picks", "style_id") if ignore_style_id else ("schema", "picks")
    return any(not _blank(v) for k, v in data.items() if k not in ignored)


def _empty_index():
    return dict(schema=1, default=None, styles={}, archived={}, archived_created={}, picks={}, active_reel=None)


def _index(*, for_write=False):
    target = path("default").with_name("_index.json")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if (not isinstance(data, dict) or data.get("schema") != 1 or
                not isinstance(data.get("styles"), dict) or not isinstance(data.get("archived"), dict)):
            raise ValueError()
        for name, row in data["styles"].items():
            if (not re.fullmatch(r"[a-z0-9-]+", name) or not isinstance(row, dict) or
                    not isinstance(row.get("label"), str) or not isinstance(row.get("created"), str)):
                raise ValueError()
        if data.get("default") is not None and data["default"] not in data["styles"]:
            raise ValueError()
        if any(not re.fullmatch(r"[a-z0-9-]+", k) or not isinstance(v, str) for k, v in data["archived"].items()):
            raise ValueError()
        archived_created = data.get("archived_created", {})
        if (not isinstance(archived_created, dict) or
                any(not re.fullmatch(r"[a-z0-9-]+", k) or not isinstance(v, str)
                    for k, v in archived_created.items())):
            raise ValueError()
        picks = data.get("picks", {})
        if not isinstance(picks, dict):
            raise ValueError()
        # Old installations hold exactly one reel's pick; reading never persists migration.
        current = data.get("current")
        if current is not None:
            if not isinstance(current, dict) or not isinstance(current.get("reel"), str):
                raise ValueError()
            current = {**current, "how": current.get("how", "saved" if current.get("style") else "fresh"),
                       "at": current.get("at", "")}
            picks = {current["reel"]: current, **picks}
        for reel, pick in picks.items():
            if (not isinstance(reel, str) or not isinstance(pick, dict) or pick.get("reel") != reel or
                    not isinstance(pick.get("at"), str) or pick.get("how") not in ("saved", "auto", "fresh", "copy") or
                    (pick.get("how") in ("saved", "auto") and pick.get("style") not in data["styles"]) or
                    (pick.get("how") not in ("saved", "auto") and pick.get("style") is not None)):
                raise ValueError()
        active = data.get("active_reel", current["reel"] if current else None)
        if active is not None and (not isinstance(active, str) or active not in picks):
            raise ValueError()
        return {**{key: value for key, value in data.items() if key != "current"},
                "archived_created": archived_created, "default": data.get("default"),
                "picks": picks, "active_reel": active}
    except FileNotFoundError:
        data = _empty_index()
        for item in sorted(target.parent.glob("*.json")):
            # The dot in <id>.<kind> (or <id>@vN.<kind>) excludes siblings.
            if not re.fullmatch(r"[a-z0-9-]+", item.stem):
                continue
            try:
                choices = json.loads(item.read_text(encoding="utf-8"))
            except (OSError, ValueError, RecursionError):
                continue
            if isinstance(choices, dict) and _has_choices(choices):
                data["styles"][item.stem] = dict(label="Style 1" if item.stem == "default" else pick_label(item.stem),
                    created=dt.datetime.fromtimestamp(item.stat().st_mtime, dt.timezone.utc).isoformat())
        if data["styles"]:
            data["default"] = "default" if "default" in data["styles"] else min(
                data["styles"], key=lambda k: data["styles"][k]["created"])
        return data
    except (OSError, ValueError, TypeError, RecursionError):
        if for_write:
            raise UnreadableStyleError(INDEX_WRITE_NOTE) from None
        if target not in _index_noted:
            print(INDEX_NOTE, file=sys.stderr)
            _index_noted.add(target)
        return _empty_index()


def _atomic(target, raw):
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=target.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = stream.name
            stream.write(raw)
        os.replace(temporary, target)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def _write_index(data):
    _index(for_write=True)
    _atomic(path("default").with_name("_index.json"),
            (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def _next_style(index):
    labels = {row["label"].casefold() for row in index["styles"].values()}
    number = 1
    while (f"style {number}" in labels or path(f"style-{number}").exists() or
           any(re.fullmatch(rf"style-{number}@v[1-9][0-9]*(?:\.[a-z]+)?\.json", item.name)
               for item in path("default").parent.glob(f"style-{number}@v*.json"))):
        # Styles and their archives reserve the number; unarchived siblings do not.
        number += 1
    return f"style-{number}", f"Style {number}"


def active_name(reel=None):
    index = _index()
    # The management cursor keeps show/notes usable; reel readers never use it.
    key = str(Path(reel).resolve()) if reel is not None else index["active_reel"]
    current = index["picks"].get(key)
    return (current["style"] if current else index["default"] if reel is None else None) or "default"


def pick_for(reel):
    return _index()["picks"].get(str(Path(reel).resolve()))


def _style_id(index, name, *, new=False):
    if isinstance(name, str):
        if name in index["styles"]:
            return name
        matches = [key for key, row in index["styles"].items() if row["label"].casefold() == name.casefold()]
        if len(matches) == 1:
            return matches[0]
        # Keep the frozen brief's explicit --name newid creation path.
        if not matches and new and re.fullmatch(r"[a-z0-9-]+", name):
            return name
    raise ValueError("That saved style was not found. Choose one of your saved styles.")


def styles():
    index = _index()
    return [dict(id=name, label=row["label"], default=name == index["default"])
            for name, row in sorted(index["styles"].items(), key=lambda item: item[1]["created"])]


def rename(name, label):
    index = _index(for_write=True)
    name = _style_id(index, name)
    row = index["styles"][name]
    label = label.strip() if isinstance(label, str) else ""
    if not 1 <= len(label) <= 40 or "\n" in label or "\r" in label:
        raise ValueError("Choose a name from 1 to 40 characters, on one line.")
    if any(k != name and v["label"].casefold() == label.casefold() for k, v in index["styles"].items()):
        raise ValueError("That name is already used. Choose a different name.")
    row["label"] = label
    _write_index(index)
    return label


def set_default(name):
    index = _index(for_write=True)
    name = _style_id(index, name)
    label = index["styles"][name]["label"]
    index["default"] = name
    _write_index(index)
    return label


def delete(name):
    index = _index(for_write=True)
    name = _style_id(index, name)
    label = index["styles"][name]["label"]
    data = load(name=name, for_write=True)
    target = path(name)
    archive = _archive(target, siblings=True) if target.exists() else None
    sibling_archive = archive or _next_archive_path(target)
    moved = []
    try:
        for source, destination in _sibling_moves(target, sibling_archive):
            os.replace(source, destination)
            moved.append((source, destination))
        if archive:
            target.unlink()
            if name == "default" and "picks" in data:
                _atomic(target, (json.dumps(dict(schema=1, picks=data["picks"]), indent=2) + "\n").encode("utf-8"))
        index["archived"][name] = label
        index["archived_created"][name] = index["styles"][name]["created"]
        del index["styles"][name]
        if index["default"] == name:
            index["default"] = max(index["styles"], key=lambda k: index["styles"][k]["created"], default=None)
        index["picks"] = {key: pick for key, pick in index["picks"].items() if pick["style"] != name}
        if index["active_reel"] not in index["picks"]:
            index["active_reel"] = None
        _write_index(index)
    except (OSError, ValueError):
        for source, destination in reversed(moved):
            os.replace(destination, source)
        if archive:
            os.replace(archive, target)
        raise
    return label


def picker_lines(reel):
    index = _index()
    key = str(Path(reel).resolve())
    current = index["picks"].get(key)
    if current:
        if current["how"] == "auto":
            return [f'Auto edit with {index["styles"][current["style"]]["label"]}. Say stop anytime.']
        if current["how"] == "saved":
            return [f'This reel uses {index["styles"][current["style"]]["label"]}.']
        return ["This reel starts fresh." if current["how"] == "fresh" else "This reel copies a reel you like."]
    if index["default"]:
        import style_learn
        try:
            workspace = _workspace(Path(reel).resolve())
        except ValueError:
            workspace = None
        try:
            auto = style_learn.status(index["default"], workspace=workspace)
        except (OSError, ValueError):
            auto = None
        if auto and auto["on"]:
            index["picks"][key] = dict(reel=key, style=index["default"], how="auto", at=_now())
            index["active_reel"] = key
            _write_index(index)
            return [f'Auto edit with {auto["label"]}. Say stop anytime.']
    return ["Which style for this reel?", *[f'- {row["label"]}' +
            (" (your default, recommended)" if row["default"] else "")
            for row in sorted(styles(), key=lambda row: not row["default"])],
            "- Start fresh" + (" (recommended)" if not index["styles"] else ""), "- Copy a reel I like"]


def pick(reel, choice):
    index = _index(for_write=True)
    key = str(Path(reel).resolve())
    if isinstance(choice, str) and choice.casefold() == "normal":
        current = index["picks"].get(key)
        if not current or current["how"] not in ("saved", "auto"):
            raise ValueError("Choose a saved style for this reel before switching to normal mode.")
        choice = current["style"]
    how = choice.casefold() if isinstance(choice, str) and choice.casefold() in ("fresh", "copy") else "saved"
    if how == "saved":
        choice = _style_id(index, choice)
        label = index["styles"][choice]["label"]
    index["picks"][key] = dict(reel=key, style=choice if how == "saved" else None, how=how, at=_now())
    index["active_reel"] = key
    _write_index(index)
    return (f"This reel uses {label}." if how == "saved" else
            "This reel starts fresh: I'll ask about each choice." if how == "fresh" else
            "Send me the reel you like. I'll measure its style, save it as a new style and use it on this reel.")


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
        if value is not None and "min" in row and not row["min"] <= value <= row["max"]:
            raise ValueError(f"{row['plain']} must be between {row['min']} and {row['max']} ms.")


def decoded_choices(spec):
    """Map measured decoder findings to editor choices without changing the spec."""
    if not isinstance(spec, dict):
        raise ValueError("That decoded style needs an object of findings. Decode it again before saving it.")
    data, unmapped = {}, []
    remaining = copy.deepcopy(spec)

    def forget(key):
        parts = key.split(".")
        parent = _get(remaining, ".".join(parts[:-1])) if len(parts) > 1 else remaining
        if isinstance(parent, dict):
            parent.pop(parts[-1], None)

    def text(value):
        return (isinstance(value, str) and bool(value.strip()) and
                not value.strip().upper().startswith(("UNKNOWN", "HUMAN-INPUT")))

    editor = _get(spec, "adapters.editor")
    if isinstance(editor, dict):
        for source, dest, plain in (("edit_style", "edit_style.style", "Editing style"),
                                    ("caption_style", "caption_style.style", "Caption look"),
                                    ("look", "look.id", "Grade look")):
            value = editor.get(source)
            allowed = next(row["allowed"] for row in FIELDS if row["key"] == dest)
            if text(value) and value in allowed:
                data[source] = {"id": value, "strength": 1.0} if source == "look" else {"style": value}
            elif source in editor:
                unmapped.append(plain + " could not be matched")
            forget("adapters.editor." + source)

    roles = _get(remaining, "typography.roles")
    if isinstance(roles, list):
        defaults = [role for role in roles if isinstance(role, dict) and role.get("caption_default") is True]
        if len(defaults) == 1 and text(defaults[0].get("closest_available")):
            role = defaults[0]
            data["font"] = role["closest_available"]
            # Role formatting still needs a report; evidence and identifiers are bookkeeping.
            for key in ("closest_available", "caption_default", "id", "evidence", "observed_in", "confidence"):
                role.pop(key, None)
            if _blank(role):
                roles.remove(role)

    tokens = _get(remaining, "color.tokens")
    if isinstance(tokens, list):
        for token in tokens:
            if (isinstance(token, dict) and isinstance(token.get("role"), str) and
                    "accent" in token["role"].casefold() and isinstance(token.get("hex"), str) and
                    re.fullmatch(r"#[0-9A-Fa-f]{6}", token["hex"])):
                data["accent"] = token["hex"]
                data.setdefault("caption_style", {})["accent"] = token["hex"]
                for key in ("hex", "role", "id"):
                    token.pop(key, None)
                if _blank(token):
                    tokens.remove(token)
                break

    ms = _get(spec, "typography.caption_mechanics.min_group_duration_ms")
    if _valid(ms, "number") and ms > 0:
        data.setdefault("caption_style", {})["min_read_s"] = ms / 1000
        forget("typography.caption_mechanics.min_group_duration_ms")

    transitions = spec.get("transitions")
    if isinstance(transitions, list):
        allowed, details = set(), False
        for transition in transitions:
            kind = transition.get("type") if isinstance(transition, dict) else None
            if isinstance(kind, str) and kind in ("cut", "hard cut", "none"):
                continue
            if isinstance(kind, str) and kind in ("whip", "zoom", "glitch", "flash", "fade", "push", "wipe", "shader"):
                allowed.add(kind)
                details = details or any(not _blank(value) for key, value in transition.items()
                                         if key not in ("type", "id", "evidence", "observed_in", "confidence"))
            else:
                # Only human-readable type names, never arbitrary paths or serialized objects.
                label = pick_label(kind) if isinstance(kind, str) and re.fullmatch(r"[A-Za-z0-9]+(?:[ -][A-Za-z0-9]+)*", kind) else "unrecognised"
                unmapped.append("Transition type: " + label)
        if allowed:
            data["transitions"] = {"allowed": sorted(allowed)}
        if details:
            unmapped.append("Transition timing and placement")
        forget("transitions")

    # Pacing is shot statistics / speech distributions, not a chosen pause between lines.
    pacing = spec.get("pacing")
    if not _blank(pacing):
        median = _get(spec, "pacing.median_shot_s")
        unmapped.append(f"Shot rhythm (median shot {median:g} s)" if _valid(median, "number") else "Shot rhythm and speech pacing")
    forget("pacing")

    labels = {
        "canvas": "Screen layouts", "canvas.aspect": "Canvas shape", "canvas.safe_zones_px": "Screen safe zones",
        "canvas.layout_modes": "Screen layouts", "canvas.layout_grammar": "Layout rules",
        "canvas.layout_timeline": "Layout sequence", "canvas.layout_grammar_mode_sequence": "Layout order",
        "canvas.layout_timeline_ref": "Layout timeline", "canvas.overlay_treatments": "Overlay treatments",
        "typography": "Typography", "typography.roles": "Typography roles and formatting",
        "typography.caption_mechanics": "Caption grouping and timing",
        "typography.caption_content_rules": "Caption wording rules",
        "color": "Colour choices", "color.tokens": "Other colour tokens and details", "color.skins": "Colour skins",
        "motion": "Motion rules", "motion.rules": "Motion rules", "motion.audio_synced_rules": "Audio-synced motion rules",
        "motion.text_animation": "Text animation", "structure": "Story structure",
        "structure.beats": "Structure beats", "structure.patterns": "Structure patterns", "structure.screens": "Structure screens",
        "assets": "Assets", "assets.recurring_motifs": "Recurring assets", "assets.panel_content_types": "Panel content",
        "assets.panel_treatments": "Panel treatments", "audio": "Audio", "audio.music": "Audio music",
        "audio.sfx": "Audio sound effects", "audio.loudness": "Audio loudness",
        "ingredients": "Required assets", "adapters": "Build instructions",
        "adapters.editor": "Other editor choices", "adapters.hyperframes": "Animation build instructions",
        "adapters.human_editor": "Human editor instructions", "transitions": "Transition findings",
        "one_liner": "Style description",
    }
    # Report every remaining non-empty group, including future decoder extensions.
    # Metadata describes the decode, not a finding to carry into an editor setting.
    for group in sorted(remaining):
        if group in ("spec_version", "style", "sources", "merge_log"):
            continue
        value = remaining[group]
        children = sorted(value.items()) if isinstance(value, dict) else [(None, value)]
        for key, finding in children:
            if _blank(finding):
                continue
            dotted = group + "." + key if key is not None else group
            label = labels.get(dotted, labels.get(group, "Additional decoder findings"))
            count = f" ({len(finding)})" if isinstance(finding, list) else ""
            unmapped.append(label + count)
    validate(data)
    return data, unmapped


def _siblings(target):
    pattern = re.escape(target.stem) + r"\.([a-z]+)\.json"
    return {match[1]: item for item in sorted(target.parent.glob(target.stem + ".*.json"))
            if (match := re.fullmatch(pattern, item.name)) and item.is_file()}


def _sibling_moves(target, archive):
    return [(item, archive.with_name(f"{archive.stem}.{kind}.json")) for kind, item in _siblings(target).items()]


def _next_archive_path(target):
    version = 1
    while True:
        archive = target.with_name(f"{target.stem}@v{version}.json")
        if not archive.exists() and not _siblings(archive):
            return archive
        version += 1


def _archive(target, *, siblings=False):
    while True:
        archive = _next_archive_path(target)
        try:
            with archive.open("xb") as stream:
                stream.write(target.read_bytes())
            return archive
        except FileExistsError:
            continue


def save(data, name="default", *, archive=False, make_default=True):
    if name is None:
        path("")  # Only reads accept None as the active style.
    target = path(name)
    if "@" in name:
        raise ValueError("Archived styles are read-only. Restore this version to make it current.")
    load(name=name, for_write=True)
    index = _index(for_write=True)
    validate(data)
    if name not in index["styles"] and _has_choices(data):
        label = index["archived"].get(name)
        if not label or any(row["label"].casefold() == label.casefold() for row in index["styles"].values()):
            _, label = _next_style(index)
        index["styles"][name] = dict(label=label, created=index["archived_created"].get(name, _now()))
        if make_default and index["default"] is None:
            index["default"] = name
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
                archived = _archive(target)
                decoded = _siblings(target).get("decoded")
                if decoded is not None:
                    _atomic(archived.with_name(f"{archived.stem}.decoded.json"), decoded.read_bytes())
        os.replace(temporary, target)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)
    _write_index(index)


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
    _index(for_write=True)
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
    load(name=current_name, for_write=True)
    siblings = {kind: item.read_bytes() for kind, item in _siblings(target).items()}
    if current.exists():
        archive = _archive(current, siblings=True)
        for source, destination in _sibling_moves(current, archive):
            os.replace(source, destination)
    save(data, current_name)
    for kind, raw in siblings.items():
        _atomic(current.with_name(f"{current.stem}.{kind}.json"), raw)
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
    transitions = ", ".join(map(label, allowed)) or "whole menu" if isinstance(allowed, list) else missing
    if value("transitions.sfx_pair") is not None:
        transitions += ", sounds on" if value("transitions.sfx_pair") else ", sounds off"
    attempt = value("cut.default_attempt")
    lines = [f"Caption look: {caption}", f"Brand accent: {colour(value('accent', missing))}",
            f"Brand font: {value('font', missing)}", f"Grade look: {grade}", f"Editing style: {editing}",
            f"Transitions: {transitions}", f"Retake choice: {label(attempt) + ' attempt' if attempt else missing}"]
    if value("style_id"):
        if not value("caption_style.style"):
            lines.pop(0)
        lines.insert(1 if value("caption_style.style") else 0,
                     f"Decoded style: {label(value('style_id'))} (from your style decoder)")
    if value("music.bed_gain_db") is not None:
        lines.append(f"Music level: {value('music.bed_gain_db'):g} dB")
    if value("cut.pause_ms") is not None:
        lines.append(f"Pause between lines: {value('cut.pause_ms'):g} ms")
    if value("cut.nudge_ms") is not None:
        nudge = min(150, max(0, value("cut.nudge_ms")))
        if nudge:
            lines.append(f"Cut timing: {nudge:g} ms later")
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


def _workspace_skill(workspace, data, label):
    target = workspace / ".claude/skills/my-editing-style/SKILL.md"
    separate = False
    if target.exists() and SKILL_MARKER not in target.read_text(encoding="utf-8").splitlines():
        target = target.with_name("SKILL.new.md")
        separate = True
        if target.exists() and SKILL_MARKER not in target.read_text(encoding="utf-8").splitlines():
            raise ValueError("Your existing skill and suggested version are hand-made. Keep one aside before saving again.")
    text = "\n".join([
        "---", "name: my-editing-style",
        'description: Holds the client\'s saved editing choices and standing notes for editor-superengine. Use when the client says "use my style" or "edit this my way"; for anything else start at editor-superengine:editor-start-here.',
        "---", "", SKILL_MARKER, "", "# My editing style", "",
        "Treat the saved choices and Standing notes below as the client's preferences. "
        'In normal mode, at the start of each reel Claude asks one question, "Which style for this reel?", listing your saved styles by name '
        'with the default as the recommended pick, plus "Copy a reel I like" and "Start fresh". '
        "A saved style applies only to the reel it was picked for; a new reel gets the style picker. "
        "For Auto edit, follow the style picker in editor-superengine:editor-start-here, including its Auto edit line.", "",
        f"## Your default style: {label}", "", *readback(data), "", "## Run the edit in this order", "",
        "Invoke editor-superengine:editor-start-here first; it runs the style picker. "
        "Then run the edit in its pipeline order, invoking each skill it names; "
        "finish with the before-posting check: the references/qa-check.md of editor-superengine:reel-canvas-build.",
        "", "Keep the client's Standing notes in their own words. Explain anything under Could not be matched "
        "and ask which part of the edit it means. Never invent a match.", ""])
    if len(text.split()) >= 600:
        raise ValueError("These saved choices and notes are too long for the workspace skill. Shorten the notes before saving again.")
    return target, text.replace("\r\n", "\n").replace("\r", "\n"), separate


def _refresh_workspace_skill(workspace, create):
    if workspace is None:
        return False
    workspace = Path(workspace).resolve()
    target = workspace / ".claude/skills/my-editing-style/SKILL.md"
    if not create and not target.is_file():
        return False
    index = _index(for_write=True)
    default = index["default"]
    data = load(name=default, for_write=True) if default else {}
    label = index["styles"][default]["label"] if default else "none saved"
    target, text, separate = _workspace_skill(workspace, data, label)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(text.encode("utf-8"))
    return separate


def save_from_reel(reel_dir, name=None, workspace=None, from_decoded=None):
    """Save this reel as a new style, or update an explicitly named style."""
    reel = Path(reel_dir).resolve()
    if not reel.is_dir():
        raise ValueError("This reel folder was not found. Choose an existing reel and try again.")
    workspace = Path(workspace).resolve() if workspace is not None else _workspace(reel)
    if from_decoded is not None:
        if (not from_decoded or from_decoded in (".", "..") or any(c in from_decoded for c in "/\\:") or not
                (workspace / "editor/style-decoder/styles" / from_decoded / "style-spec.json").is_file()):
            raise ValueError("That decoded style was not found in this workspace. Decode it here before saving it.")
    spec, mapped, unmapped = {}, {}, []
    if from_decoded is not None:
        try:
            spec = json.loads((workspace / "editor/style-decoder/styles" / from_decoded / "style-spec.json").read_text(encoding="utf-8"))
        except (OSError, ValueError, RecursionError):
            raise ValueError("That decoded style could not be read. Decode it again before saving it.") from None
        mapped, unmapped = decoded_choices(spec)
    index = _index(for_write=True)
    new = name is None
    if new:
        name, label = _next_style(index)
        data = {}
    else:
        name = _style_id(index, name, new=True)
        data = load(name=name, for_write=True)
        label = index["styles"].get(name, {}).get("label") or index["archived"].get(name)
        if not label or any(k != name and v["label"].casefold() == label.casefold() for k, v in index["styles"].items()):
            _, label = _next_style(index)
    for key, value in mapped.items():
        data[key] = {**data[key], **value} if isinstance(value, dict) and isinstance(data.get(key), dict) else copy.deepcopy(value)
    bm = _reel_doc(reel, "beat-map-selection.json")
    picker = _reel_doc(reel, "look-picker-selection.json")
    if isinstance(bm.get("transitions"), dict):
        choices = {key: copy.deepcopy(bm["transitions"][key]) for key in ("allowed", "sfx_pair")
                   if key in bm["transitions"]}
        data["transitions"] = {**data.get("transitions", {}), **choices}
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
    gain = _get(_reel_doc(reel, "sound-selection.json"), "bed.gain_db")
    if gain is not None:
        data["music"] = {**(data.get("music") or {}), "bed_gain_db": gain}
    if from_decoded is not None:
        data["style_id"] = from_decoded
    if not _has_choices(data, ignore_style_id=from_decoded is not None):
        if from_decoded is not None:
            current = pick_for(reel)
            if current is None or current["how"] == "copy":
                pick(reel, "fresh")
            raise ValueError("Nothing in that decoded style matches an editor setting yet, so I didn't save it. This reel starts fresh: I'll ask about each choice.")
        raise ValueError("This reel has no choices to save yet. Send a board first.")
    _workspace_skill(workspace, data, label)
    save(data, name, archive=True, make_default=from_decoded is None)
    if from_decoded is not None:
        provenance = dict(schema=1, slug=from_decoded, spec_version=spec.get("spec_version"),
                          spec_status=_get(spec, "style.status"), mapped=sorted(mapped),
                          unmapped=unmapped, saved_at=_now())
        _atomic(path(name).with_name(f"{name}.decoded.json"),
                (json.dumps(provenance, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        current = pick_for(reel)
        if current is None or current["how"] == "copy":
            pick(reel, name)
    separate = _refresh_workspace_skill(workspace, create=True)
    print("\n".join(readback(data)))
    for line in unmapped:
        print("Not copied (the editor has no setting for this yet): " + line)
    if from_decoded is not None and _get(spec, "style.status") != "approved":
        print("This decoded style is still a draft.")
    if separate:
        print("I kept your hand-made skill and wrote a separate suggested version beside it.")
    print(f"Saved as {label}. Want a different name for it?" if new else f"Updated {label}.")
    return data


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("Choose a saved-style command and give all its choices. Use --help for the choices.")


def main(argv=None):
    ap = _Parser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    show = sub.add_parser("show")
    show.add_argument("name", nargs="?")
    restorer = sub.add_parser("restore")
    restorer.add_argument("name")
    sub.add_parser("fields")
    sub.add_parser("list")
    setter = sub.add_parser("set")
    setter.add_argument("key")
    setter.add_argument("json")
    target = setter.add_mutually_exclusive_group(required=True)
    target.add_argument("--reel")
    target.add_argument("--style")
    writer = sub.add_parser("save-from-reel")
    writer.add_argument("reel_dir")
    writer.add_argument("--name")
    writer.add_argument("--workspace")
    writer.add_argument("--from-decoded")
    renamer = sub.add_parser("rename")
    renamer.add_argument("id")
    renamer.add_argument("label")
    try:
        workspace = _workspace(Path.cwd())
    except ValueError:
        workspace = None
    renamer.add_argument("--workspace", default=workspace)
    for command in ("set-default", "delete"):
        parser = sub.add_parser(command)
        parser.add_argument("id")
        parser.add_argument("--workspace", default=workspace)
    sub.add_parser("picker").add_argument("reel")
    picking = sub.add_parser("pick")
    picking.add_argument("reel")
    picking.add_argument("choice")
    try:
        args = ap.parse_args(argv)
        if args.command == "show":
            name = args.name
            # Keep explicit archive reads; current styles accept either a name or an id.
            if name is not None and not re.fullmatch(r"[a-z0-9-]+@v[1-9][0-9]*", name):
                name = _style_id(_index(), name)
            print("\n".join(readback(load(name=name or active_name()))))
        elif args.command == "restore":
            print("\n".join(readback(restore(args.name))))
        elif args.command == "list":
            for row in styles():
                target = path(row["id"])
                versions = sum(1 for item in target.parent.glob(target.stem + "@v*.json")
                               if re.fullmatch(re.escape(target.stem) + r"@v[1-9][0-9]*", item.stem))
                archived = f" ({versions} archived versions)" if versions else ""
                default = " (default)" if row["default"] else ""
                print(f'{row["label"]}{default}: {readback(load(name=row["id"]))[0]}{archived}')
            index = _index()
            for name, label in index["archived"].items():
                if name in index["styles"]:
                    continue
                versions = [int(item.stem.split("@v")[1]) for item in path(name).parent.glob(name + "@v*.json")
                            if re.fullmatch(re.escape(name) + r"@v[1-9][0-9]*", item.stem)]
                if versions:
                    print(f"Archived: {label} (restore with {name}@v{max(versions)})")
        elif args.command == "set":
            index = _index(for_write=True)
            if args.reel is not None:
                current = index["picks"].get(str(Path(args.reel).resolve()))
                if not current or not current["style"]:
                    raise ValueError("This reel has no saved style picked; pick one first, then try again.")
                name = current["style"]
            else:
                name = _style_id(index, args.style, new=args.style == "default" and not index["styles"])  # only the very first store may be created
            if not any(row["key"] == args.key and row["where"] == "saved style" for row in FIELDS):
                raise ValueError("Choose a saved-style field from the fields list.")
            try:
                value = json.loads(args.json)
            except (ValueError, RecursionError):
                raise ValueError("Give the saved choice as valid JSON.") from None
            data = load(name=name, for_write=True)
            parent = data
            parts = args.key.split(".")
            for part in parts[:-1]:
                if not isinstance(parent.get(part), dict):
                    parent[part] = {}
                parent = parent[part]
            parent[parts[-1]] = value
            save(data, name, archive=True)
            label = _index()["styles"].get(name, {}).get("label", "none saved")
            print(f"Updated {label}.")
        elif args.command == "save-from-reel":
            save_from_reel(args.reel_dir, args.name, args.workspace, args.from_decoded)
        elif args.command == "rename":
            print(f"Renamed to {rename(args.id, args.label)}.")
        elif args.command == "set-default":
            print(f"{set_default(args.id)} is now your default.")
        elif args.command == "delete":
            index = _index(for_write=True)
            name = _style_id(index, args.id)
            previous = index["default"]
            missing = not path(name).exists()
            label = delete(name)
            print(f"{label} was already gone; I removed it from your list." if missing else
                  f"{label} is archived; you can restore it any time.")
            index = _index()
            if previous == name and index["default"]:
                print(f'{index["styles"][index["default"]]["label"]} is now your default.')
        elif args.command == "picker":
            print("\n".join(picker_lines(args.reel)))
        elif args.command == "pick":
            print(pick(args.reel, args.choice))
        else:
            for row in FIELDS:
                default = json.dumps(row["default"], ensure_ascii=False, sort_keys=True)
                ladder = " > ".join(row["ladder"]) or "n/a (setup)"
                print(f"{row['key']} | {default} | {row['where']} | {ladder}")
        if args.command in ("rename", "set-default", "delete"):
            try:
                _refresh_workspace_skill(args.workspace, create=False)
            except (OSError, ValueError):
                print("Your style change is saved, but I couldn't refresh your workspace skill. Save it again to refresh it.")
    except OSError:
        print("I couldn't read or save your style choices. Check that the editor can open them and try again.", file=sys.stderr)
        return 2
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
