"""Turn Claude's beat plan into the reel's Beat Map board file (stdlib only).

Claude writes a small plan (which words start each beat, its layout and number); this script
does the frame math from the cut's word times and work/cuts.json, checks the result with
beat_schema, and writes videos/<reel>/beat-map.state.json for the Beat Map board.

  make_beat_map.py --reel-dir <videos/<reel>> --plan <plan.json> [--words work/edit_map.cut.json]
                   [--cuts work/cuts.json] [--replace]
  make_beat_map.py --selftest

plan.json: {beats:[{w0, w1, layout, value?, shows?, why?, check?}], word_marks?:[{w, mark}]}
Non-overlay beats tile the whole reel in plan order (increasing w0); overlay beats sit on top,
timed by their own words.
"""
import argparse
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE))
from win_encoding import ensure_utf8_output  # noqa: E402
import beat_schema  # noqa: E402
import saved_style  # noqa: E402

OUT_NAME = "beat-map.state.json"
PREV_NAME = OUT_NAME + ".prev"  # same backup name the board server uses
REFUSE = ("This reel already has a beat map with the user's edits in it. Re-run with --replace only after "
          "the user agrees; the old one is kept as beat-map.state.json.prev.")


class Fail(Exception):
    """One plain line for the user; main prints it as '✗ <line>' and exits 1."""


def _read_json(path, what, fix):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Fail(f"The {what} {path} is missing; {fix}")
    except (OSError, ValueError) as e:
        raise Fail(f"The {what} {path} can't be read as JSON ({e}); {fix}")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _total_frames(cuts, path):
    fps = cuts.get("fps") if isinstance(cuts, dict) else None
    segs = cuts.get("segments") if isinstance(cuts, dict) else None
    if not (_num(fps) and fps > 0):
        raise Fail(f"The cut list {path} has no usable fps; re-run the cut step to rebuild it")
    if not (isinstance(segs, list) and segs and all(isinstance(s, dict) and _num(s.get("out_out_f")) for s in segs)):
        raise Fail(f"The cut list {path} has no segments with out_out_f; re-run the cut step to rebuild it")
    # out_out_f is end-exclusive (the first frame after the segment), so the last one is the reel's frame count.
    return fps, int(max(s["out_out_f"] for s in segs))


def _word_time(items, i, key, path):
    t = items[i].get(key) if isinstance(items[i], dict) else None
    if not _num(t):
        raise Fail(f"The word list {path} has no {key} time for word {i}; re-run the transcribe step for the cut")
    return t


def build_doc(reel_dir, plan, words, items, words_rel, words_path, fps, total):
    if not isinstance(plan, dict) or not isinstance(plan.get("beats"), list) or not plan["beats"]:
        raise Fail("The plan has no beats list; give it {beats:[{w0, w1, layout, ...}]}")
    n = len(words)
    for i, pb in enumerate(plan["beats"]):
        ok = isinstance(pb, dict) and all(isinstance(pb.get(k), int) and not isinstance(pb.get(k), bool)
                                          for k in ("w0", "w1"))
        if not ok or not (0 <= pb["w0"] <= pb["w1"] < n):
            raise Fail(f"Plan beat {i} needs whole-number w0 <= w1 inside the word list (0..{n - 1})")
    tiled = [pb for pb in plan["beats"] if pb.get("layout") != "overlay"]
    if not tiled:
        raise Fail("The plan has only overlay beats; at least one other beat must cover the reel")
    for a, b in zip(tiled, tiled[1:]):
        if b["w0"] <= a["w0"]:
            raise Fail(f"Plan beats must go in speaking order: a beat at word {b['w0']} follows one at word {a['w0']}")

    starts = [0] + [round(_word_time(items, pb["w0"], "start", words_path) * fps) for pb in tiled[1:]]
    timed = []  # (start_f, 0 tiled / 1 overlay, plan order, end_f, plan beat)
    for k, pb in enumerate(tiled):
        timed.append((starts[k], 0, k, starts[k + 1] if k + 1 < len(tiled) else total, pb))
    for k, pb in enumerate(plan["beats"]):
        if pb.get("layout") == "overlay":
            s = min(round(_word_time(items, pb["w0"], "start", words_path) * fps), total)
            e = min(round(_word_time(items, pb["w1"], "end", words_path) * fps), total)
            timed.append((s, 1, k, e, pb))
    timed.sort(key=lambda t: t[:3])

    beats, proposed = [], {}
    for i, (s, _, _, e, pb) in enumerate(timed, 1):
        bid = f"b_{i:03d}"
        text = " ".join(w.strip() for w in words[pb["w0"]:pb["w1"] + 1])
        beats.append({"id": bid, "start_f": s, "end_f": e,
                      "speech_anchor": {"text": text, "w0": pb["w0"], "w1": pb["w1"]},
                      "layout": pb.get("layout"), "value": pb.get("value"),
                      "scene": None, "broll": None, "transition": None})
        proposed[bid] = {"layout": pb.get("layout"), "value": pb.get("value"),
                         "shows": pb.get("shows", ""), "why": pb.get("why", "")}
        if isinstance(pb.get("check"), str) and pb["check"].strip():
            proposed[bid]["check"] = pb["check"].strip()
    return {"schema": beat_schema.SCHEMA, "reel": Path(reel_dir).resolve().name, "fps": fps, "words": words_rel,
            "beats": beats, "word_marks": plan.get("word_marks", []), "proposed": proposed, "notes": {},
            "needs": "", "sent_at": None}


def _pick_label(beat):
    anchor = beat.get("speech_anchor")
    text = anchor.get("text", "") if isinstance(anchor, dict) else ""
    text = " ".join(text.split()[:5]) if isinstance(text, str) else ""
    return '"' + text.replace('"', "'") + '"' if text else "a beat"


def _carry_reason(problem):
    """Translate validator diagnostics without exposing ids, paths or saved JSON."""
    if "whole beat" in problem:
        return "the beat is now a different length"
    if "dur_frames" in problem:
        return "the transition's duration does not fit the beat's length or frame rate"
    if "not a beat id" in problem:
        return "the beat no longer exists"
    if "slots" in problem:
        return "the scene's text fields are not valid"
    if "relative path" in problem:
        return "the media path must stay inside the reel folder"
    if "marked twice" in problem:
        return "that word already has a mark"
    if "sort word_marks" in problem:
        return "the marks are not in word order"
    if "not a mark" in problem:
        return "that kind of mark is not supported"
    if "no spoken word" in problem:
        return "there is no spoken word there"
    if "past the word list" in problem:
        return "the word no longer exists"
    if "not text" in problem:
        return "the saved choice must be text"
    if "not a number" in problem:
        return "the saved number is not valid"
    if "not a layout" in problem:
        return "that layout is not supported"
    if "not an object" in problem:
        return "the saved choice is not in the required format"
    if "closure words" in problem:
        return "the loop's closure words are no longer spoken in the reel"
    if "inside this cut" in problem:
        return "the loop's closing time is outside the new cut"
    if "setup before" in problem:
        return "the loop's setup, updates and closure are not in time order"
    if "missing" in problem:
        return "the saved choice is missing required information"
    if "unknown" in problem:
        return "the saved choice contains unsupported settings"
    if "needs an overlay layout" in problem:
        return "the transition needs an overlay layout, scene or B-roll"
    if "needs a scene" in problem:
        return "the transition needs a scene"
    if "transition" in problem.lower():
        return "the saved transition settings are not valid"
    if "cta_reminder" in problem:
        return "the reminder needs valid timing, gain and a short keyword"
    if "holds" in problem:
        return "each hold needs a whole frame and a reason"
    return "the saved choice does not meet the beat map's format requirements"


def _remap_choice(value, old_ids, matches):
    """Remap dictionary keys only; ambiguous reference values are reported, not guessed."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in old_ids:
                if key not in matches:
                    raise ValueError("a referenced beat's words changed or the beat no longer exists")
                key = matches[key]["id"]
            result[key] = _remap_choice(item, old_ids, matches)
        return result
    if isinstance(value, list):
        return [_remap_choice(item, old_ids, matches) for item in value]
    if isinstance(value, str) and value in old_ids:
        raise ValueError("its beat reference cannot be carried safely in this format")
    return value


def _carry_marks(old, doc, words, pairs, plan_has_marks):
    lost = []
    marks = old.get("word_marks", [])
    if not isinstance(marks, list):
        return ["Couldn't keep your marks: the saved marks are not a list."]
    if not plan_has_marks:
        doc["word_marks"] = []
    for mark in marks:
        w = mark.get("w") if isinstance(mark, dict) else None
        valid_index = isinstance(w, int) and not isinstance(w, bool)
        word = words[w] if valid_index and 0 <= w < len(words) else "missing word"
        # Prefer the old anchor's word when the cut itself changed.
        for beat, _ in pairs:
            anchor = beat.get("speech_anchor", {})
            if (valid_index and isinstance(anchor, dict) and isinstance(anchor.get("w0"), int)
                    and isinstance(anchor.get("w1"), int) and anchor["w0"] <= w <= anchor["w1"]):
                tokens = str(anchor.get("text", "")).split()
                if w - anchor["w0"] < len(tokens):
                    word = tokens[w - anchor["w0"]]
                break
        label = '"' + " ".join(str(word).split()).replace('"', "'") + '"'
        if plan_has_marks:
            if mark not in doc["word_marks"]:
                lost.append(f"Couldn't keep your mark on {label}: the new plan supplies different marks.")
            continue
        matched = any(new is not None and valid_index
                      and beat["speech_anchor"]["w0"] <= w <= beat["speech_anchor"]["w1"]
                      for beat, new in pairs)
        if valid_index and 0 <= w < len(words) and pairs and all(new is not None for _, new in pairs):
            matched = True  # Unchanged beats also preserve marks in gaps between anchors.
        if not matched:
            lost.append(f"Couldn't keep your mark on {label}: the beat's words changed or the beat no longer exists.")
            continue
        candidate = doc["word_marks"] + [copy.deepcopy(mark)]
        problems = beat_schema.marks_problems(candidate, words)
        if problems:
            lost.append(f"Couldn't keep your mark on {label}: {_carry_reason(problems[0])}.")
        else:
            doc["word_marks"] = candidate
    return lost


def carry_picks(old, doc, words, fps, *, plan_has_marks=False):
    """Carry each independent choice, rolling back only the choice that fails validation."""
    old_beats = old.get("beats", [])
    old_beats = [b for b in old_beats if isinstance(b, dict)] if isinstance(old_beats, list) else []
    notes = old.get("notes", {})
    notes = notes if isinstance(notes, dict) else {}
    proposed = old.get("proposed", {})
    proposed = proposed if isinstance(proposed, dict) else {}
    pairs, used, matches = [], set(), {}
    for beat in old_beats:
        anchor = beat.get("speech_anchor")
        new = None
        if isinstance(anchor, dict) and all(k in anchor for k in ("w0", "w1", "text")):
            for i, candidate in enumerate(doc["beats"]):
                if (i not in used and candidate["speech_anchor"] == anchor
                        and (candidate["layout"] == "overlay") == (beat.get("layout") == "overlay")):
                    new = candidate
                    used.add(i)
                    if isinstance(beat.get("id"), str):
                        matches[beat["id"]] = new
                    break
        pairs.append((beat, new))

    kept, total, lost = 0, 0, []
    for beat, new in pairs:
        bid = beat.get("id")
        original = proposed.get(bid, {}) if isinstance(bid, str) else {}
        original = original if isinstance(original, dict) else {}
        picks = [(key, beat[key]) for key in ("scene", "broll", "transition") if beat.get(key) is not None]
        picks += [(key, beat[key]) for key in ("layout", "value")
                  if key in beat and beat[key] != original.get(key)]
        if isinstance(bid, str) and bid in notes:
            picks.append(("note", notes[bid]))
        if not picks:
            continue
        total += 1
        carried = False
        for key, value in picks:
            name = {"broll": "B-roll", "value": "number"}.get(key, key)
            reason = None
            if new is None:
                anchor = beat.get("speech_anchor", {})
                same_start = isinstance(anchor, dict) and any(
                    b["speech_anchor"]["w0"] == anchor.get("w0") for b in doc["beats"])
                reason = "the beat's words changed" if same_start else "the beat no longer exists"
                if isinstance(anchor, dict) and any(
                        b["speech_anchor"] == anchor
                        and (b["layout"] == "overlay") != (beat.get("layout") == "overlay")
                        for b in doc["beats"]):
                    reason = "the beat's layout type changed"
            elif key == "note":
                doc["notes"][new["id"]] = copy.deepcopy(value)
                problems = (beat_schema.beat_problems(new, words, fps=fps)
                            or beat_schema.beat_map_problems(doc, words))
                if problems:
                    del doc["notes"][new["id"]]
                    reason = _carry_reason(problems[0])
            else:
                before = new[key]
                new[key] = copy.deepcopy(value)
                problems = beat_schema.beat_problems(new, words, fps=fps)
                if problems:
                    new[key] = before
                    reason = _carry_reason(problems[0])
            if reason:
                lost.append(f"Couldn't keep your {name} on {_pick_label(beat)}: {reason}.")
            else:
                carried = True
        kept += int(carried)

    # Notes whose beat is absent from even the old beat list must not disappear silently.
    old_ids = {b["id"] for b in old_beats if isinstance(b.get("id"), str)}
    for bid in notes.keys() - old_ids:
        lost.append("Couldn't keep your note on a missing beat: the beat no longer exists.")
    lost += _carry_marks(old, doc, words, pairs, plan_has_marks)
    choices = {"edit_style": "editing style", "caption_style": "caption look", "loops": "open loops",
               "transitions": "transition settings", "cta_reminder": "keyword reminder",
               "holds": "holds", "needs": "note to Claude"}
    for key, name in choices.items():
        if key not in old or old[key] is None:
            continue
        if key in doc and not (key == "needs" and doc[key] == ""):
            if doc[key] != old[key]:
                lost.append(f"Couldn't keep your {name}: the new document already supplies this choice.")
            continue
        if key not in beat_schema.MAP_KEYS or (key not in beat_schema.OPTIONAL_MAP_KEYS and key != "needs"):
            lost.append(f"Couldn't keep your {name}: this document choice is not supported.")
            continue
        had_key, before = key in doc, doc.get(key)
        try:
            doc[key] = _remap_choice(old[key], old_ids, matches)
        except ValueError as e:
            lost.append(f"Couldn't keep your {name}: {e}.")
            continue
        problems = beat_schema.beat_map_problems(doc, words)
        if problems:
            if had_key:
                doc[key] = before
            else:
                del doc[key]
            lost.append(f"Couldn't keep your {name}: {_carry_reason(problems[0])}.")
    doc["sent_at"] = None
    return [f"Kept your picks on {kept} of {total} beats."] + lost


def _read_old_picks(path):
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(old, dict):
            return old, []
    except (OSError, ValueError, RecursionError):
        pass
    return None, ["Your old picks could not be read, so none were carried; the old file is kept as a backup."]


def run(reel_dir, plan_path, words_rel, cuts_rel, replace):
    reel = Path(reel_dir)
    if not reel.is_dir():
        raise Fail(f"The reel folder {reel} doesn't exist; point --reel-dir at videos/<reel>")
    words_path, cuts_path = reel / words_rel, reel / cuts_rel
    data = _read_json(words_path, "word list", "re-run the transcribe step for the cut, or point --words at it")
    try:
        words = beat_schema.load_words(words_path)
    except beat_schema.SchemaError as e:
        raise Fail(e.problems[0])
    cuts = _read_json(cuts_path, "cut list", "re-run the cut step, or point --cuts at it")
    plan = _read_json(plan_path, "plan", "write the plan JSON first")
    fps, total = _total_frames(cuts, cuts_path)
    out = reel / OUT_NAME
    old, carried = _read_old_picks(out) if out.exists() and replace else (None, [])
    doc = build_doc(reel, plan, words, data["words"], words_rel, words_path, fps, total)
    if old is not None:
        carried = carry_picks(old, doc, words, fps, plan_has_marks="word_marks" in plan)
    beat_schema.validate_beat_map(doc, words)  # raises SchemaError before anything is written
    if out.exists():
        if not replace:
            raise Fail(REFUSE)
        os.replace(out, reel / PREV_NAME)
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    # Board-only recommendations stay outside the schema-validated choices and never count as a Send.
    saved = saved_style.load(reel)
    _, source = saved_style.resolve("edit_style.style", saved=saved)
    recommended = saved_style.recommendation("edit_style.style", saved) if source == "recommended" else None
    (reel / "beat-map.config.json").write_bytes(
        (json.dumps({"recommended": recommended}, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    try:
        import scene_fill
        scene_fill.write_catalog(reel, doc["beats"], words, fps)
    except Exception:  # the beat map stays usable even when scenes couldn't be prepared
        print("Couldn't prepare the scene list for the boards, so the boards won't offer scenes; the beat map is fine.")
    for line in carried:
        print(line)
    print(f"✓ Beat map ready: {len(doc['beats'])} beats, {len(doc['word_marks'])} word marks.")
    return 0


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Build a reel's beat-map.state.json from Claude's beat plan.")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    ap.add_argument("--reel-dir", help="the reel folder, videos/<reel>")
    ap.add_argument("--plan", help="Claude's plan JSON")
    ap.add_argument("--words", default=beat_schema.DEFAULT_WORDS, help="cut word list, relative to --reel-dir")
    ap.add_argument("--cuts", default="work/cuts.json", help="cut list, relative to --reel-dir")
    ap.add_argument("--replace", action="store_true", help="overwrite an existing beat map, keeping it as .prev")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.reel_dir and a.plan):
        ap.print_help()
        return 2
    try:
        return run(a.reel_dir, a.plan, a.words, a.cuts, a.replace)
    except Fail as e:
        print(f"✗ {e}")
    except beat_schema.SchemaError as e:
        for p in e.problems:
            print(f"✗ {p}")
    return 1


def selftest():
    words = ["Three", "big", " wins,", "today.", "We", "grew", "40", "percent", "so", "sign", "up", "now!"]
    fails = []

    def quiet(argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(argv)
        return code, buf.getvalue()

    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)

        def reel(name):
            r = t / "videos" / name
            (r / "work").mkdir(parents=True)
            items = []
            for i, w in enumerate(words):
                st = round(0.2 + 0.6 * i, 3)
                items.append({"id": f"w_{i:04d}", "word": w, "start": st, "end": round(st + 0.5, 3),
                              "parakeet_start": st, "status": "aligned", "score_min": 0.9})
            (r / "work" / "edit_map.cut.json").write_text(json.dumps({"words": items}), encoding="utf-8")
            (r / "work" / "cuts.json").write_text(json.dumps({"fps": 30, "segments": [
                {"src_in_f": 0, "src_out_f": 120, "out_in_f": 0, "out_out_f": 120},
                {"src_in_f": 200, "src_out_f": 320, "out_in_f": 120, "out_out_f": 240}]}), encoding="utf-8")
            return r

        plan = {"beats": [
            {"w0": 0, "w1": 3, "layout": "full", "value": 3, "shows": "a counter to 3", "why": "a number said aloud",
             "check": "  I wanted the graphic alone here. Full screen keeps your face on screen.  "},
            {"w0": 4, "w1": 7, "layout": "split"},
            {"w0": 5, "w1": 6, "layout": "overlay", "value": 40},
            {"w0": 8, "w1": 11, "layout": "stack"}],
            "word_marks": [{"w": 6, "mark": "num"}, {"w": 11, "mark": "cta"}]}
        planf = t / "plan.json"
        planf.write_text(json.dumps(plan), encoding="utf-8")
        r = reel("demo")
        out = r / OUT_NAME
        code, said = quiet(["--reel-dir", str(r), "--plan", str(planf)])
        if code != 0 or not out.is_file():
            fails.append(f"build: exit {code}, output {said!r}")
        else:
            doc = json.loads(out.read_text(encoding="utf-8"))
            got = [(b["id"], b["start_f"], b["end_f"], b["layout"]) for b in doc["beats"]]
            want = [("b_001", 0, 78, "full"), ("b_002", 78, 150, "split"),
                    ("b_003", 96, 129, "overlay"), ("b_004", 150, 240, "stack")]
            if got != want:
                fails.append(f"tiling/overlay frames: got {got}, want {want}")
            if doc["beats"][0]["speech_anchor"] != {"text": "Three big wins, today.", "w0": 0, "w1": 3}:
                fails.append(f"anchor text: got {doc['beats'][0]['speech_anchor']}")
            if doc["word_marks"] != plan["word_marks"]:
                fails.append(f"marks not carried: {doc['word_marks']}")
            if doc["proposed"]["b_001"].get("check") != plan["beats"][0]["check"].strip():
                fails.append("plan check was not carried through and trimmed")
            if "check" in doc["proposed"]["b_002"]:
                fails.append("a beat without a plan check acquired the key")
            if doc["proposed"]["b_002"] != {"layout": "split", "value": None, "shows": "", "why": ""}:
                fails.append(f"proposed defaults: {doc['proposed']['b_002']}")
            if (doc["reel"], doc["fps"], doc["needs"], doc["notes"], doc["sent_at"]) != ("demo", 30, "", {}, None):
                fails.append("reel/fps/needs/notes/sent_at fields wrong")
            if b"\r" in out.read_bytes():
                fails.append("output has CR line endings")
            catalog_path, fills_path = r / "scenes/catalog.json", r / "scenes/suggest.json"
            reasons_path = r / "scenes/why.json"
            if not catalog_path.is_file() or not fills_path.is_file() or not reasons_path.is_file():
                fails.append("scene catalog, suggestions and reasons were not written")
            else:
                cat = json.loads(catalog_path.read_text(encoding="utf-8"))
                fills = json.loads(fills_path.read_text(encoding="utf-8"))
                if not cat or not all((r / s["preview"]).is_file() for s in cat):
                    fails.append("scene catalog has no scenes or missing preview copies")
                if not fills.get("b_001", {}).get("callout"):
                    fails.append("scene suggestions do not include the opening callout")

            before = out.read_bytes()
            code, said = quiet(["--reel-dir", str(r), "--plan", str(planf)])
            if code != 1 or REFUSE not in said or out.read_bytes() != before or (r / PREV_NAME).exists():
                fails.append(f"refusal on an existing file: exit {code}, output {said!r}")

            beats2 = [dict(plan["beats"][0], why="changed")] + plan["beats"][1:]
            planf.write_text(json.dumps(dict(plan, beats=beats2)), encoding="utf-8")
            code, said = quiet(["--reel-dir", str(r), "--plan", str(planf), "--replace"])
            prev = r / PREV_NAME
            if code != 0 or not prev.is_file() or prev.read_bytes() != before or \
                    json.loads(out.read_text(encoding="utf-8"))["proposed"]["b_001"]["why"] != "changed":
                fails.append(f"--replace: exit {code}, output {said!r}")

        bad = t / "bad.json"
        bad.write_text(json.dumps(dict(plan, beats=plan["beats"][:1] + [{"w0": 4, "w1": 11, "layout": "grid"}])),
                       encoding="utf-8")
        r2 = reel("other")
        code, said = quiet(["--reel-dir", str(r2), "--plan", str(bad)])
        if code != 1 or (r2 / OUT_NAME).exists() or "'grid' is not a layout" not in said:
            fails.append(f"unknown layout: exit {code}, output {said!r}")

        from unittest.mock import patch
        import scene_fill
        r3 = reel("catalog-failure")
        with patch.object(scene_fill, "write_catalog", side_effect=OSError("secret/full/path: raw OS detail")):
            code, said = quiet(["--reel-dir", str(r3), "--plan", str(planf)])
        line = "Couldn't prepare the scene list for the boards, so the boards won't offer scenes; the beat map is fine."
        if code != 0 or said.splitlines()[0] != line or "secret" in said or not (r3 / OUT_NAME).is_file():
            fails.append("catalog failure must be a plain line and leave a usable beat map")

    if fails:
        for f in fails:
            print(f"selftest FAILED: {f}")
        return 1
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
