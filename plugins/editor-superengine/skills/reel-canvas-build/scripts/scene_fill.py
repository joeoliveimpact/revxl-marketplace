"""Offline scene suggestions, filled only with the words said in one beat.

scene_fill.py catalog --reel-dir videos/<reel>
scene_fill.py suggest --reel-dir videos/<reel> --beat b_001 --scene counter
scene_fill.py --selftest
"""
import argparse
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
P = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(P / "scripts"))
sys.path.insert(0, str(P / "skills/_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
from beat_schema import load_words, safe_relpath, validate_beat_map  # noqa: E402
import scene_check  # noqa: E402


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


def suggest(scene_id, beat, words, fps):
    """Return an honest fill, or None when words, duration or scene rules don't fit."""
    folder = _scene_dir(scene_id)
    if scene_check.scene_problems(folder):
        return None
    spec = json.loads((folder / "scene.json").read_text(encoding="utf-8"))
    if not isinstance(fps, (int, float)) or isinstance(fps, bool) or not math.isfinite(fps) or fps <= 0:
        raise ValueError("The beat map needs a positive fps.")
    seconds = (beat["end_f"] - beat["start_f"]) / fps
    if not spec["dur"][0] <= seconds <= spec["dur"][1]:
        return None
    anchor = beat["speech_anchor"]
    w0, w1 = anchor["w0"], anchor["w1"]
    if not (isinstance(w0, int) and isinstance(w1, int) and 0 <= w0 <= w1 < len(words)):
        raise ValueError("The beat's words are outside the cut transcript.")
    heard = [w.strip() for w in words[w0:w1 + 1]]
    number_scene = spec["category"] in (*scene_check.NUMBER_SCENES, "stat")
    value = beat.get("value")
    if number_scene and (not isinstance(value, (int, float)) or isinstance(value, bool)
                         or not math.isfinite(value) or not scene_check.said(value, scene_check.numbers(" ".join(heard)))):
        return None
    # Keep a stat's big-number slot as the actual number said, rather than a prefix of the sentence.
    stat_text = None
    if spec["category"] in ("stat-card", "stat"):
        match = next((m for m in scene_check.NUM.finditer(" ".join(heard))
                      if scene_check.said(value, scene_check.numbers(m.group(0)))), None)
        stat_text = match.group(0) if match else None
    tokens = " ".join(heard).split()
    slots, pos = {}, 0
    for name, slot in spec["slots"].items():
        if stat_text is not None and name in ("stat", "value", "number"):
            if len(stat_text) > slot["maxChars"]:
                return None
            slots[name] = stat_text
            continue
        start = pos
        while pos < len(tokens) and len(" ".join(tokens[start:pos + 1])) <= slot["maxChars"]:
            pos += 1
        slots[name] = " ".join(tokens[start:pos])
    params = {}
    if number_scene and "value" in spec["params"]:
        value = beat.get("value")
        if (not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value)
                or not scene_check.said(value, scene_check.numbers(" ".join(heard)))):
            return None
        params["value"] = value
    fill = {"id": scene_id, "slots": slots, "params": params}
    if scene_check.fill_problems(scene_id, dict(beat, scene=fill), words=heard):
        return None
    return fill


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
    for b in beats:
        for item in items:
            fill = suggest(item["id"], b, words, fps)
            if fill is not None:
                fills[b["id"]][item["id"]] = fill
    _reel_path(reel, "scenes").mkdir(exist_ok=True)
    for item in items:
        rel = f"scenes/{item['id']}.png"
        shutil.copyfile(_scene_dir(item["id"]) / "preview.png", _reel_path(reel, rel))
        item["preview"] = rel
    for rel, data in (("scenes/catalog.json", items), ("scenes/suggest.json", fills)):
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
    items = catalog()
    assert items, "no shippable scenes"
    for item in items:
        fill = suggest(item["id"], beat, words, 30)
        if fill is not None:
            assert not scene_check.fill_problems(item["id"], dict(beat, scene=fill), words=words)
            remaining = words[:]
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
