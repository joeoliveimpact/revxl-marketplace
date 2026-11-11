"""Offline scene suggestions, filled only with the words said in one beat.

scene_fill.py catalog --reel-dir videos/<reel>
scene_fill.py suggest --reel-dir videos/<reel> --beat b_001 --scene counter
scene_fill.py --selftest
"""
import argparse
import json
import math
import re
import shutil
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(P / "scripts"))
sys.path.insert(0, str(P / "skills/_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
from beat_schema import load_words, safe_relpath, validate_beat_map  # noqa: E402
import scene_check  # noqa: E402
import placer  # noqa: E402
import three_d_placement  # noqa: E402


def _scene_dir(sid):
    if not isinstance(sid, str) or not safe_relpath(sid) or "/" in sid or sid in (".", ".."):
        raise ValueError("Choose a scene from the catalog.")
    return scene_check.SCENES / sid


def catalog():
    """Metadata from scene.json for exactly the scenes scene_check allows to ship."""
    out = []
    for folder in sorted(scene_check.SCENES.iterdir()):
        if not folder.is_dir() or scene_check.scene_problems(folder):
            continue
        spec = json.loads((folder / "scene.json").read_text(encoding="utf-8"))
        if spec["category"] == "cover-title": continue
        item = {k: spec[k] for k in ("id", "kind", "category", "dur")}
        item["slots"] = [{"name": n, "maxChars": s["maxChars"]} for n, s in spec["slots"].items()]
        item["params"] = [dict(name=n, **{k: p[k] for k in ("type", "min", "max", "enum", "default") if k in p})
                          for n, p in spec["params"].items()]
        item["preview"] = (folder / "preview.png").as_posix()
        out.append(item)
    return out


def suggest(scene_id, beat, words, fps, head=None):
    """Return an honest fill, or None when words, duration or scene rules don't fit."""
    return _suggest(scene_id, beat, words, fps, head)[0]


def why_not(scene_id, beat, words, fps, head=None):
    """Return the first reason a card cannot be filled, or None when it fits."""
    return _suggest(scene_id, beat, words, fps, head)[1]


def _plain_number(value):
    """Keep the shortest decimal value, expanding any exponent for typing."""
    if value == int(value):
        return str(int(value))
    return format(Decimal(repr(value)), "f")


def _duration(value):
    shown = round(value, 1)
    return f"{_plain_number(shown)} {'second' if shown == 1 else 'seconds'}"


def _suggest(scene_id, beat, words, fps, head=None):
    """One set of checks supplies both the fill and the explanation."""
    folder = _scene_dir(scene_id)
    if scene_check.scene_problems(folder):
        return None, "This card is unavailable. Pick another card or ask Claude to check it."
    spec = json.loads((folder / "scene.json").read_text(encoding="utf-8"))
    if not isinstance(fps, (int, float)) or isinstance(fps, bool) or not math.isfinite(fps) or fps <= 0:
        raise ValueError("The beat map needs a positive fps.")
    seconds = (beat["end_f"] - beat["start_f"]) / fps
    if not spec["dur"][0] <= seconds <= spec["dur"][1]:
        length = "short" if seconds < spec["dur"][0] else "long"
        return None, (f"This beat is too {length} at {_duration(seconds)}; this card needs "
                      f"{_duration(spec['dur'][0])} to {_duration(spec['dur'][1])}. "
                      "Pick another card, or ask Claude to change this beat's length.")
    anchor = beat["speech_anchor"]
    w0, w1 = anchor["w0"], anchor["w1"]
    if not (isinstance(w0, int) and isinstance(w1, int) and 0 <= w0 <= w1 < len(words)):
        raise ValueError("The beat's words are outside the cut transcript.")
    heard = [w.strip() for w in words[w0:w1 + 1]]
    number_scene = spec["category"] in (*scene_check.NUMBER_SCENES, "stat")
    value = beat.get("value")
    heard_numbers = scene_check.numbers(" ".join(heard))
    rebuild = " Then Send and ask Claude to rebuild the scene choices."
    if number_scene and (not isinstance(value, (int, float)) or isinstance(value, bool)
                         or not math.isfinite(value)):
        if heard_numbers:
            return None, (f'No number is set on this beat. Set "Number shown" on the Beat Map for this beat to '
                          f'{_plain_number(heard_numbers[0][0])}, a number you say here.' + rebuild)
        return None, ('This card needs a number you say in this beat. Numbers said as words, like "three", '
                      'are not picked up. Set "Number shown" on the Beat Map to the number; setting it alone will not enable this card. '
                      'Ask Claude to check the spoken number in the transcript.' + rebuild)
    if number_scene and not scene_check.said(value, heard_numbers):
        return None, (f'The number set, {_plain_number(value)}, must match a number you say in this beat. '
                      'Change "Number shown" on the Beat Map or pick another card.' + rebuild)
    # Keep a stat's big-number slot as the actual number said, rather than a prefix of the sentence.
    stat_text = None
    if spec["category"] in ("stat-card", "stat"):
        match = next((m for m in scene_check.NUM.finditer(" ".join(heard))
                      if scene_check.said(value, scene_check.numbers(m.group(0)))), None)
        stat_text = match.group(0) if match else None
    tokens = " ".join(heard).split()
    # Preserve listed order unless it leaves a required slot empty; only then retry.
    for order in (spec["slots"].items(),
                  sorted(spec["slots"].items(), key=lambda s: s[1].get("required") is not True)):
        slots, pos = {name: "" for name in spec["slots"]}, 0
        for name, slot in order:
            if stat_text is not None and name in ("stat", "value", "number"):
                if len(stat_text) > slot["maxChars"]:
                    return None, "The number is too long for this card. Pick a card with more room for it."
                slots[name] = stat_text
                continue
            start = pos
            while pos < len(tokens) and len(" ".join(tokens[start:pos + 1])) <= slot["maxChars"]:
                pos += 1
            slots[name] = " ".join(tokens[start:pos])
        if all(s.get("required") is not True or slots[n].strip() for n, s in spec["slots"].items()):
            break
    params = {}
    if spec["category"] == "3d" and head is not None:
        clear = three_d_placement.clear_places(spec, head)
        if not clear:
            return None, "This shot is too tight for the 3D card; pick another card."
        default = spec["params"]["place"]["default"]
        params["place"] = default if default in clear else clear[0]
    if number_scene and "value" in spec["params"]:
        params["value"] = value
    fill = {"id": scene_id, "slots": slots, "params": params}
    problems = scene_check.fill_problems(scene_id, dict(beat, scene=fill), words=heard)
    if problems:
        if problems[0].startswith("the counter would show"):
            return None, "The number is too long for this card. Pick a card with more room for it."
        problem = problems[0]
        for name in spec["slots"]:
            problem = problem.replace(f"slot {name} ", f'The "{name}" text box ', 1)
        for name in spec["params"]:
            problem = problem.replace(f"param {name} ", f'The "{name}" setting ', 1)
        problem = re.sub(r"\s*\((?:F-\d+|VES-\d+[^)]*)\)", "", problem).replace("this scene", "this card")
        return None, problem
    return fill, None


def _reel_path(reel, rel):
    if not safe_relpath(rel):
        raise ValueError("Scene files need a path inside the reel folder.")
    path = reel / rel
    if not path.resolve().is_relative_to(reel.resolve()):
        raise ValueError("A scene file points outside the reel folder.")
    return path


def write_catalog(reel_dir, beats, words, fps):
    """Write the reel-local catalog, preview copies and per-beat suggestions."""
    reel = Path(reel_dir)
    if not reel.is_dir():
        raise ValueError("The reel folder doesn't exist; choose an existing videos/<reel> folder.")
    items = catalog()
    fills = {b["id"]: {} for b in beats}
    reasons = {b["id"]: {} for b in beats}
    # The initial board has no Send/style/anchors yet; that is an unknown head.
    try:
        placement = dict(placer.load_ctx(reel), beats=beats)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        placement = None
    for b in beats:
        try:
            head = placer.visible_head_box_at(placement, b["start_f"], b["end_f"] - 1) if placement is not None else None
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            head = None
        for item in items:
            fill, reason = _suggest(item["id"], b, words, fps, head)
            if fill is not None:
                fills[b["id"]][item["id"]] = fill
            else:
                reasons[b["id"]][item["id"]] = reason
    _reel_path(reel, "scenes").mkdir(exist_ok=True)
    for item in items:
        rel = f"scenes/{item['id']}.png"
        shutil.copyfile(_scene_dir(item["id"]) / "preview.png", _reel_path(reel, rel))
        item["preview"] = rel
    for rel, data in (("scenes/catalog.json", items), ("scenes/suggest.json", fills), ("scenes/why.json", reasons)):
        _reel_path(reel, rel).write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def _load_reel(reel_dir):
    reel = Path(reel_dir)
    if not reel.is_dir():
        raise ValueError("The reel folder doesn't exist; choose an existing videos/<reel> folder.")
    state = _reel_path(reel, "beat-map.state.json")
    sent = _reel_path(reel, "beat-map-selection.json")
    path = sent if sent.is_file() and (not state.is_file() or sent.stat().st_mtime_ns > state.stat().st_mtime_ns) else state
    if not path.is_file():
        raise ValueError("This reel has no beat map yet; build the beat map first.")
    doc = json.loads(path.read_text(encoding="utf-8"))
    words = load_words(_reel_path(reel, "work/edit_map.cut.json"))
    validate_beat_map(doc, words)
    return reel, doc, words


def selftest():
    words = "We helped 47 people make a clear reel today with a useful example".split()
    beat = {"id": "b_001", "start_f": 0, "end_f": 120, "value": 47,
            "speech_anchor": {"w0": 0, "w1": len(words) - 1}}
    for spoken, title, kicker in (
            ("Stop editing like this today", "Stop editing like this today", ""),
            ("Stop editing like this today and start making clear reels",
             "start making clear reels", "Stop editing like this today and"),
            ("Stop editing like this today and start making clear reels with a useful example today",
             "start making clear reels with a useful example", "Stop editing like this today and")):
        hook_words = spoken.split()
        hook_beat = dict(beat, speech_anchor={"w0": 0, "w1": len(hook_words) - 1})
        hook = suggest("hook-title", hook_beat, hook_words, 30)
        assert hook is not None, "hook-title must fill its required title"
        assert hook["slots"] == {"kicker": kicker, "title": title}
        assert list(hook["slots"]) == ["kicker", "title"]
    assert json.dumps(suggest("lower-third", beat, words, 30)) == json.dumps({
        "id": "lower-third", "slots": {"name": "We helped 47 people make a",
                                        "title": "clear reel today with a useful example"}, "params": {}})
    items = catalog()
    assert items, "no shippable scenes"
    for item in items:
        fill = suggest(item["id"], beat, words, 30)
        if fill is not None:
            assert not scene_check.fill_problems(item["id"], dict(beat, scene=fill), words=words)
            remaining = words[:]
            spec = json.loads((_scene_dir(item["id"]) / "scene.json").read_text(encoding="utf-8"))
            assert list(fill["slots"]) == list(spec["slots"])
            for slot in item["slots"]:
                text = fill["slots"][slot["name"]]
                assert len(text) <= slot["maxChars"]
                if item["category"] in ("stat-card", "stat") and slot["name"] in ("stat", "value", "number"):
                    assert text == "47"
                    continue
                used = text.split()
                assert used == remaining[:len(used)]
                remaining = remaining[len(used):]
        assert suggest(item["id"], dict(beat, end_f=1), words, 30) is None
    counter = suggest("counter", beat, words, 30)
    assert counter["params"] == {"value": 47}
    assert suggest("counter", dict(beat, value=48), words, 30) is None
    for item in items:
        if item["category"] in ("stat-card", "stat"):
            assert suggest(item["id"], dict(beat, value=48), words, 30) is None
            assert suggest(item["id"], beat, words, 30) is not None
    assert suggest("counter", beat, ["forty-seven"] * len(words), 30) is None
    assert scene_check.fill_problems("counter", dict(counter, slots={"label": "x" * 31}), words=words)
    assert scene_check.fill_problems("counter", dict(counter, params={"value": 48}), words=words)
    with tempfile.TemporaryDirectory() as tmp:
        reel = Path(tmp)
        write_catalog(reel, [beat], words, 30)
        saved = json.loads((reel / "scenes/catalog.json").read_text(encoding="utf-8"))
        assert len(saved) == len(items)
        assert all((reel / s["preview"]).is_file() for s in saved)
        assert json.loads((reel / "scenes/suggest.json").read_text(encoding="utf-8"))["b_001"]["counter"] == counter
        for rel in ("../escape", "C:/escape", "/escape", "scenes/../../escape"):
            try:
                _reel_path(reel, rel)
            except ValueError:
                pass
            else:
                raise AssertionError("unsafe scene path accepted")
    print("selftest ok")
    return 0


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Fill scenes from the words said in a beat, offline.")
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for cmd in ("catalog", "suggest"):
        parser = sub.add_parser(cmd)
        parser.add_argument("--reel-dir", required=True)
        if cmd == "suggest":
            parser.add_argument("--beat", required=True)
            parser.add_argument("--scene", required=True)
    a = ap.parse_args(argv)
    try:
        if a.selftest:
            return selftest()
        if a.cmd:
            reel, doc, words = _load_reel(a.reel_dir)
            if a.cmd == "catalog":
                write_catalog(reel, doc["beats"], words, doc["fps"])
                print(f"Scene catalog ready for {len(doc['beats'])} beats.")
            else:
                beat = next((b for b in doc["beats"] if b["id"] == a.beat), None)
                if beat is None:
                    raise ValueError("That beat isn't in this reel's beat map.")
                print(json.dumps(suggest(a.scene, beat, words, doc["fps"]), ensure_ascii=False))
            return 0
        ap.print_help()
        return 2
    except Exception as e:
        print("Couldn't prepare the scenes: " + " ".join(str(e).split()))
        return 2


if __name__ == "__main__":
    sys.exit(main())
