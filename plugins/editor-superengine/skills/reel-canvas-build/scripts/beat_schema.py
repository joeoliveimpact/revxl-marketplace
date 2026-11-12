"""The one validator for what the Beat Map and Sketches boards save (stdlib only).

A beat is one stretch of the cut: exactly {id, start_f, end_f, speech_anchor, layout, value,
scene, broll, transition}, timed in output frames. Word marks [{w, mark}] tag words of the
cut's word list (w = list position) as num, key, emph or cta. The beat map document
(videos/<reel>/beat-map.state.json) holds the beats, marks, Claude's proposed picks and user
notes; the sketches document (videos/<reel>/sketches.state.json) holds the rough preview, the
directions (the user picks one) and the per-beat sketches.
Later steps import this module instead of re-checking the shapes themselves.

  beat_schema.py check <beat-map.state.json> [--words <words.json>]
  beat_schema.py check-sketches <sketches.state.json> [--beat-map <beat-map.state.json>]
  beat_schema.py --selftest
"""
import argparse
import copy
import json
import math
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import transitions

SCHEMA = 1  # bump only when a saved file's shape changes; old files then fail loudly, not silently
LAYOUTS = ("full", "split", "stack", "pip", "overlay")  # H-R1's fixed set; overlay alone may overlap
MARKS = ("num", "key", "emph", "cta")  # H-M20's fixed set, meanings below
# num  = a number said aloud (a counter or value can show it)
# key  = a key word of the line
# emph = a word to stress (S6c word punches and S8 captions read emph/key as suggestions)
# cta  = a call-to-action word
BEAT_KEYS = ("id", "start_f", "end_f", "speech_anchor", "layout", "value", "scene", "broll", "transition")
ANCHOR_KEYS = ("text", "w0", "w1")
MARK_KEYS = ("w", "mark")
MAP_KEYS = ("schema", "reel", "fps", "words", "beats", "word_marks", "proposed", "notes", "needs", "sent_at",
            "edit_style", "caption_style", "loops", "transitions", "cta_reminder", "holds")
OPTIONAL_MAP_KEYS = ("edit_style", "caption_style", "loops", "transitions", "cta_reminder", "holds")  # Optional document choices; old Sends stay valid.
PROPOSED_KEYS = ("layout", "value", "shows", "why")  # Claude's original pick per beat; the board highlights changes
OPTIONAL_PROPOSED_KEYS = ("check",)  # A plain reason to review a beat; absent in old files.
DEFAULT_WORDS = "work/edit_map.cut.json"  # H-S4b-5: re-transcribed cut words, S3 edit-map shape, index from 0
SKETCHES_KEYS = ("schema", "reel", "rough", "directions", "pick", "sketches", "note", "sent_at", "locked_at", "scenes", "storyboard")
DIRECTION_KEYS = ("id", "name", "why", "frames", "note")  # the user picks ONE direction
SKETCH_KEYS = ("id", "beat", "title", "media", "note")  # one per-beat preview
SHOW_MAX = 60  # longest bad value quoted in a message, so one bad blob can't flood the output
# scene is null or {id: non-empty str, slots: {str: str}, params?: {str: number|str|bool}}.
# Scene files, transcript numbers and duration are checked by scene_check, independently of this shape.
# broll is null or {src, in, out, fit, ledger_id}; frames are at the cut's fps.
# transition (G5) follows transitions.MENU; cut membership is checked at render time.


class SchemaError(ValueError):
    """Raised by the validate_* functions; .problems is the list of plain-English problems."""

    def __init__(self, problems):
        self.problems = [problems] if isinstance(problems, str) else list(problems)
        super().__init__("; ".join(self.problems))


def _show(v):
    s = repr(v)
    return s if len(s) <= SHOW_MAX else s[:SHOW_MAX - 3] + "..."


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _keys(obj, wanted, where, optional=()):
    """Missing and unknown keys of an object, or 'not an object'. Empty list = keys are right."""
    if not isinstance(obj, dict):
        return [f"{where} {_show(obj)} is not an object; use {{{', '.join(wanted)}}}"]
    out = []
    missing = [k for k in wanted if k not in obj and k not in optional]
    unknown = [k for k in obj if k not in wanted]
    if missing:
        out.append(f"{where} is missing {', '.join(missing)}; add them")
    if unknown:
        out.append(f"{where} has unknown keys {', '.join(map(str, unknown))}; remove them "
                   f"(allowed: {', '.join(wanted)})")
    return out


def _norm(text):
    """Case, punctuation and spacing don't count; the words themselves do."""
    s = " ".join(text.split()).casefold().replace("’", "'")
    return " ".join("".join(c for c in s if c.isalnum() or c in " '").split())


def _iso_problems(v, where):
    """null, or an ISO 8601 timestamp (a trailing Z is fine)."""
    if v is None:
        return []
    try:
        datetime.fromisoformat(v.replace("Z", "+00:00"))
        return []
    except (AttributeError, ValueError):
        return [f"{where} {_show(v)} is not an ISO 8601 timestamp; use e.g. '2026-11-04T15:30:00Z' or null"]


def _nonempty_str(v, where, what="a non-empty string"):
    if isinstance(v, str) and v.strip():
        return []
    return [f"{where} {_show(v)} is not {what}; set it"]


def scene_problems(scene, where="scene", *, nullable=True):
    """The saved fill shape only; no dependency on the scene catalog."""
    if scene is None and nullable:
        return []
    out = _keys(scene, ("id", "slots", "params"), where, ("params",))
    if not isinstance(scene, dict):
        return out
    if "id" in scene:
        out += _nonempty_str(scene["id"], f"{where}.id")
    for field in ("slots", "params"):
        if field not in scene:
            continue
        values = scene[field]
        if not isinstance(values, dict):
            out.append(f"{where}.{field} is not an object; use name and value pairs")
            continue
        for key, value in values.items():
            if not isinstance(key, str):
                out.append(f"{where}.{field} has a non-text name; use text names")
            valid = isinstance(value, str) if field == "slots" else isinstance(value, (str, bool)) or _is_num(value)
            if not valid:
                kind = "text" if field == "slots" else "a number, text or boolean"
                out.append(f"{where}.{field}[{_show(key)}] is not {kind}; change it")
    return out


def broll_problems(broll, where="broll"):
    """A whole-frame source range; beat_problems checks its length against the beat."""
    if broll is None:
        return []
    out = _keys(broll, ("src", "in", "out", "fit", "ledger_id"), where)
    if not isinstance(broll, dict):
        return out
    out += _rel_path_problems(broll.get("src"), where + ".src")
    for k in ("in", "out"):
        if not (_is_int(broll.get(k)) and broll[k] >= 0):
            out.append(f"{where}.{k} is not a frame; use a whole number >= 0")
    if all(_is_int(broll.get(k)) for k in ("in", "out")) and broll["in"] >= broll["out"]:
        out.append(f"{where} must end after it starts; use 0 <= in < out")
    if broll.get("fit") not in ("cover", "blur-fill"):
        out.append(f"{where}.fit must be cover or blur-fill; pick one")
    if not (isinstance(broll.get("ledger_id"), str) and re.fullmatch(r"f\d{2,}", broll["ledger_id"])):
        out.append(f"{where}.ledger_id must name a footage row like f01; ingest the clip first")
    return out


def beat_problems(beat, words=None, *, where="beat", fps=None):
    """Problems with one beat. `words` (the cut's word list) turns on the speech_anchor index/text checks."""
    out = _keys(beat, BEAT_KEYS, where)
    if not isinstance(beat, dict):
        return out
    b = beat
    if "id" in b and not (isinstance(b["id"], str) and re.fullmatch(r"\S+", b["id"])):
        out.append(f"{where}.id {_show(b['id'])} is not a beat id; use a non-empty string with no spaces, e.g. 'b_001'")
    for k in ("start_f", "end_f"):
        if k in b and not (_is_int(b[k]) and b[k] >= 0):
            out.append(f"{where}.{k} {_show(b[k])} is not a frame; use a whole number >= 0")
    if _is_int(b.get("start_f")) and _is_int(b.get("end_f")) and b["start_f"] > b["end_f"]:
        out.append(f"{where}.start_f {b['start_f']} is after end_f {b['end_f']}; make start_f <= end_f")
    if "speech_anchor" in b:
        a = b["speech_anchor"]
        bad = _keys(a, ANCHOR_KEYS, f"{where}.speech_anchor")
        out += bad
        if not bad:
            ok = True
            if not isinstance(a["text"], str):
                out.append(f"{where}.speech_anchor.text {_show(a['text'])} is not text; use the words w0..w1 say")
                ok = False
            for k in ("w0", "w1"):
                if not (_is_int(a[k]) and a[k] >= 0):
                    out.append(f"{where}.speech_anchor.{k} {_show(a[k])} is not a word index; use a whole number >= 0")
                    ok = False
            if ok and a["w0"] > a["w1"]:
                out.append(f"{where}.speech_anchor.w0 {a['w0']} is after w1 {a['w1']}; make w0 <= w1")
                ok = False
            if ok and words is not None:
                if a["w1"] >= len(words):
                    out.append(f"{where}.speech_anchor.w1 {a['w1']} is past the word list ({len(words)} words); "
                               f"use an index below {len(words)}")
                else:
                    said = " ".join(w.strip() for w in words[a["w0"]:a["w1"] + 1])
                    if _norm(a["text"]) != _norm(said):
                        out.append(f"{where}.speech_anchor.text {_show(a['text'])} does not match words "
                                   f"{a['w0']}..{a['w1']} {_show(said)}; use those words or fix w0/w1")
    if "layout" in b and b["layout"] not in LAYOUTS:
        out.append(f"{where}.layout {_show(b['layout'])} is not a layout; use one of {', '.join(LAYOUTS)}")
    if "value" in b and not (b["value"] is None or _is_num(b["value"])):
        out.append(f"{where}.value {_show(b['value'])} is not a number; use a number or null")
    if "scene" in b:
        out += scene_problems(b["scene"], f"{where} ({_show(b.get('id'))}).scene")
    if "broll" in b:
        out += broll_problems(b["broll"], f"{where}.broll")
        br = b["broll"]
        if (isinstance(br, dict) and all(_is_int(br.get(k)) for k in ("in", "out"))
                and all(_is_int(b.get(k)) for k in ("start_f", "end_f"))
                and br["out"] - br["in"] != b["end_f"] - b["start_f"]):
            out.append(f"{where}.broll must play for the whole beat; set out - in to end_f - start_f")
    out += transitions.beat_problems(b, fps)
    return out


def marks_problems(marks, words=None):
    if not isinstance(marks, list):
        return [f"word_marks {_show(marks)} is not a list; use [] or a list of {{w, mark}}"]
    out, seen, prev = [], set(), None
    for i, m in enumerate(marks):
        where = f"word_marks[{i}]"
        bad = _keys(m, MARK_KEYS, where)
        out += bad
        if bad:
            continue
        if m["mark"] not in MARKS:
            out.append(f"{where}.mark {_show(m['mark'])} is not a mark; use one of {', '.join(MARKS)}")
        w = m["w"]
        if not (_is_int(w) and w >= 0):
            out.append(f"{where}.w {_show(w)} is not a word index; use a whole number >= 0")
            continue
        if words is not None and w >= len(words):
            out.append(f"{where}.w {w} is past the word list ({len(words)} words); use an index below {len(words)}")
        elif words is not None:
            text = words[w].get("word", "") if isinstance(words[w], dict) else words[w]
            # Blank or dash-only rows carry nothing to mark; symbols said aloud (&, %, +) stay markable.
            if isinstance(text, str) and not text.replace("—", " ").replace("–", " ").strip():
                out.append(f"{where}.w {w} marks {_show(text)}, which has no spoken word; mark a spoken word")
        if w in seen:
            out.append(f"{where}.w {w} is marked twice; keep one mark per word")
        elif prev is not None and w < prev:
            out.append(f"{where}.w {w} comes after w {prev}; sort word_marks by w")
        seen.add(w)
        prev = w if prev is None else max(prev, w)
    return out


def safe_relpath(p):
    """True for a non-empty path inside the reel folder: forward slashes, no '..', no leading / or \\, no drive."""
    return (isinstance(p, str) and bool(p.strip()) and "\\" not in p and not p.startswith("/")
            and not re.match(r"[A-Za-z]:", p) and ".." not in p.split("/"))


def _rel_path_problems(p, where):
    if safe_relpath(p):
        return []
    return [f"{where} {_show(p)} is not a plain relative path; use forward slashes inside the reel folder, "
            f"no '..', no leading '/', no drive letter"]


def _beat_keyed_problems(obj, name, beat_ids, check_value):
    """`proposed` / `notes`: an object keyed by existing beat ids; check_value(value, where) -> problems."""
    if not isinstance(obj, dict):
        return [f"{name} {_show(obj)} is not an object; use {{}} or {{<beat id>: ...}}"]
    out = []
    for k, v in obj.items():
        where = f"{name}[{k!r}]"
        if beat_ids is not None and k not in beat_ids:
            out.append(f"{name} key {_show(k)} is not a beat id in beats; use an existing beat id or remove it")
        out += check_value(v, where)
    return out


def _proposed_value_problems(v, where):
    out = _keys(v, PROPOSED_KEYS + OPTIONAL_PROPOSED_KEYS, where, OPTIONAL_PROPOSED_KEYS)
    if out:
        return out
    if v["layout"] not in LAYOUTS:
        out.append(f"{where}.layout {_show(v['layout'])} is not a layout; use one of {', '.join(LAYOUTS)}")
    if not (v["value"] is None or _is_num(v["value"])):
        out.append(f"{where}.value {_show(v['value'])} is not a number; use a number or null")
    for k in ("shows", "why"):
        if not isinstance(v[k], str):
            out.append(f"{where}.{k} {_show(v[k])} is not text; use a string")
    if "check" in v:
        check = v["check"]
        if not (isinstance(check, str) and "\n" not in check and "\r" not in check and 1 <= len(check.strip()) <= 200):
            out.append(f"{where}.check must be one line of text with 1 to 200 characters after trimming")
    return out


def _note_value_problems(v, where):
    return [] if isinstance(v, str) else [f"{where} {_show(v)} is not text; use a string"]


def loops_problems(doc, words=None, timed_words=None):
    """Optional output-frame ledger. Timed cut words prove the closure inside its window.

    Callers holding only word strings can check wording but cannot prove its time;
    the pre-render loop check always supplies the timed cut word list.
    """
    if "loops" not in doc:
        return []
    rows = doc["loops"]
    if not isinstance(rows, list):
        return ["Open loops must be a list of ledger rows, or be left out."]
    out = []
    fps = doc.get("fps")
    beats = doc.get("beats") if isinstance(doc.get("beats"), list) else []
    total = max((b.get("end_f", 0) for b in beats
                 if isinstance(b, dict) and _is_int(b.get("end_f"))), default=0)
    keys = ("question", "on_screen", "setup_f", "updates_f", "closure_f", "closure_words", "cta_f")
    for i, row in enumerate(rows):
        where = f"Open loop {i + 1}"
        bad = _keys(row, keys, where)
        if bad:
            out += bad
            continue
        for key in ("question", "on_screen", "closure_words"):
            out += _nonempty_str(row[key], f"{where} {key}")
        setup, closure, cta, updates = (row[k] for k in ("setup_f", "closure_f", "cta_f", "updates_f"))
        if (not _is_int(setup) or not _is_int(closure) or not 0 <= setup < closure or
                not isinstance(updates, list) or not all(_is_int(f) and setup < f < closure for f in updates) or
                any(a >= b for a, b in zip(updates, updates[1:])) or
                cta is not None and (not _is_int(cta) or cta <= closure)):
            out.append(f"{where}: keep setup before every update, updates before closure, and closure before the call to action.")
            continue
        if total and (closure >= total or cta is not None and cta >= total):
            out.append(f"{where}: keep closure and the call to action inside this cut.")
        if not isinstance(row["closure_words"], str) or not row["closure_words"].strip():
            continue
        spoken = None
        if timed_words is not None:
            if not _is_num(fps) or fps <= 0 or not isinstance(timed_words, list):
                out.append(f"{where}: the cut needs timed words and a frame rate to prove the closure.")
                continue
            selected = []
            valid = True
            for word in timed_words:
                if not (isinstance(word, dict) and isinstance(word.get("word"), str) and
                        _is_num(word.get("start")) and _is_num(word.get("end")) and word["end"] >= word["start"]):
                    valid = False
                    break
                if setup <= word["start"] * fps and word["end"] * fps <= closure:
                    selected.append(word["word"])
            if not valid:
                out.append(f"{where}: restore the cut's timed word list to prove the closure.")
                continue
            spoken = " ".join(selected)
        elif words is not None:
            spoken = " ".join(words)
        if spoken is not None and (" " + _norm(row["closure_words"]) + " ") not in (" " + _norm(spoken) + " "):
            out.append(f"{where}: the closure words must be said between setup and closure in this reel.")
    return out


def beat_map_problems(doc, words=None, timed_words=None):
    """Problems with a whole beat map document. `words` = the cut's word list (see load_words)."""
    out = _keys(doc, MAP_KEYS, "beat map", OPTIONAL_MAP_KEYS)
    if not isinstance(doc, dict):
        return out
    if "schema" in doc and not (_is_int(doc["schema"]) and doc["schema"] == SCHEMA):
        out.append(f"schema {_show(doc['schema'])} is not {SCHEMA}; set schema to {SCHEMA}")
    if "reel" in doc:
        out += _nonempty_str(doc["reel"], "reel", "a reel name")
    if "fps" in doc and not (_is_num(doc["fps"]) and doc["fps"] > 0):
        out.append(f"fps {_show(doc['fps'])} is not a frame rate; use the master's fps from work/cuts.json")
    if "words" in doc:
        out += _rel_path_problems(doc["words"], "words")
    if "sent_at" in doc:
        out += _iso_problems(doc["sent_at"], "sent_at")
    if "word_marks" in doc:
        out += marks_problems(doc["word_marks"], words)
    if "edit_style" in doc and not isinstance(doc["edit_style"], dict):
        out.append(f"edit_style {_show(doc['edit_style'])} is not an object; use {{\"style\": ...}} or leave it out")
    if "cta_reminder" in doc:
        reminder = doc["cta_reminder"]
        if (not isinstance(reminder, dict) or
                not all(_is_num(reminder.get(k)) for k in ("at_s", "hold_s", "gain")) or
                not isinstance(reminder.get("keyword"), str) or len(reminder["keyword"]) > 16):
            out.append("cta_reminder needs numeric at_s, hold_s and gain, and a keyword string of at most 16 characters; fix it or leave it out")
    if "holds" in doc:
        holds = doc["holds"]
        if (not isinstance(holds, list) or any(
                not isinstance(h, dict) or not _is_int(h.get("at_f")) or
                not isinstance(h.get("reason"), str) or not h["reason"].strip() for h in holds)):
            out.append("holds needs a list of integer at_f and non-empty reason text; fix the rows or leave it out")
    out += transitions.options_problems(doc.get("transitions"))
    if "needs" in doc and not isinstance(doc["needs"], str):
        out.append(f"needs {_show(doc['needs'])} is not text; use a string (may be empty)")
    beats = doc.get("beats")
    beats_ok = isinstance(beats, list)
    if "beats" in doc and not beats_ok:
        out.append(f"beats {_show(beats)} is not a list; use [] or a list of beats")
    out += _beat_map_beats_problems(beats if beats_ok else [], words, doc.get("fps"))
    beat_ids = {b["id"] for b in beats if isinstance(b, dict) and isinstance(b.get("id"), str)} if beats_ok else None
    if "proposed" in doc:
        out += _beat_keyed_problems(doc["proposed"], "proposed", beat_ids, _proposed_value_problems)
    if "notes" in doc:
        out += _beat_keyed_problems(doc["notes"], "notes", beat_ids, _note_value_problems)
    return out + loops_problems(doc, words, timed_words)


def _beat_map_beats_problems(beats, words, fps=None):
    """Each beat, unique ids, sorted by start_f, and no overlap except overlays."""
    out, good, ids = [], [], set()
    for i, b in enumerate(beats or []):
        bad = beat_problems(b, words, where=f"beats[{i}]", fps=fps)
        out += bad
        if isinstance(b, dict) and isinstance(b.get("id"), str):
            if b["id"] in ids:
                out.append(f"beats[{i}].id {_show(b['id'])} is used twice; give each beat its own id")
            ids.add(b["id"])
        if isinstance(b, dict) and _is_int(b.get("start_f")) and _is_int(b.get("end_f")):
            good.append((i, b))
    prev = None
    for i, b in good:
        if prev is not None and b["start_f"] < prev[1]["start_f"]:
            out.append(f"beats[{i}].start_f {b['start_f']} is before beats[{prev[0]}].start_f "
                       f"{prev[1]['start_f']}; sort beats by start_f")
        prev = (i, b)
    # end_f is exclusive: a beat may start on the frame the previous one ends. Overlays may overlap anything.
    solid = [(i, b) for i, b in good if b.get("layout") != "overlay"]
    for (i, a), (j, b) in zip(solid, solid[1:]):
        if a["end_f"] > b["start_f"]:
            out.append(f"beats[{j}] starts at {b['start_f']} before beats[{i}] ends at {a['end_f']}; "
                       f"move one, or make it an overlay")
    return out


def sketches_problems(doc, beat_map=None):
    """Problems with a sketches document. Pass the beat map to check each sketch's beat id exists."""
    out = _keys(doc, SKETCHES_KEYS, "sketches doc", ("scenes", "storyboard"))
    if not isinstance(doc, dict):
        return out
    if "schema" in doc and not (_is_int(doc["schema"]) and doc["schema"] == SCHEMA):
        out.append(f"schema {_show(doc['schema'])} is not {SCHEMA}; set schema to {SCHEMA}")
    if "reel" in doc:
        out += _nonempty_str(doc["reel"], "reel", "a reel name")
    for k in ("sent_at", "locked_at"):
        if k in doc:
            out += _iso_problems(doc[k], k)
    if doc.get("locked_at") is not None and doc.get("pick") is None:
        out.append("locked_at is set but no direction is picked; pick one before locking")
    if "note" in doc and not isinstance(doc["note"], str):
        out.append(f"note {_show(doc['note'])} is not text; use a string (may be empty)")
    if "rough" in doc and doc["rough"] is not None:
        out += _rel_path_problems(doc["rough"], "rough")
    beat_ids = None
    if isinstance(beat_map, dict) and isinstance(beat_map.get("beats"), list):
        beat_ids = {b["id"] for b in beat_map["beats"] if isinstance(b, dict) and isinstance(b.get("id"), str)}
    if "scenes" in doc:
        out += _beat_keyed_problems(doc["scenes"], "scenes", beat_ids,
                                   lambda v, where: scene_problems(v, where, nullable=False))
    if "storyboard" in doc:
        storyboard = doc["storyboard"]
        if not isinstance(storyboard, dict) or not isinstance(storyboard.get("beats"), dict):
            out.append("storyboard must be an object with a beats object")
        else:
            def storyboard_value(v, where):
                fields = ("in", "out", "ease_in", "ease_out")
                problems = _keys(v, fields, where, fields)
                if isinstance(v, dict):
                    for key, value in v.items():
                        if not isinstance(value, str) or not value.strip() or len(value) > 24:
                            problems.append(f"{where}.{key} must be non-empty text of at most 24 characters")
                return problems
            out += _beat_keyed_problems(storyboard["beats"], "storyboard.beats", beat_ids, storyboard_value)
    direction_ids = None
    for name, keys in (("directions", DIRECTION_KEYS), ("sketches", SKETCH_KEYS)):
        if name not in doc:
            continue
        items = doc[name]
        if not isinstance(items, list):
            out.append(f"{name} {_show(items)} is not a list; use [] or a list")
            continue
        ids = set()
        for i, it in enumerate(items):
            where = f"{name}[{i}]"
            bad = _keys(it, keys, where)
            out += bad
            if bad:
                continue
            out += _nonempty_str(it["id"], f"{where}.id")
            if isinstance(it["id"], str):
                if it["id"] in ids:
                    out.append(f"{where}.id {_show(it['id'])} is used twice; give each its own id")
                ids.add(it["id"])
            for k in ("name", "why", "note") if name == "directions" else ("title", "note"):
                if not isinstance(it[k], str):
                    out.append(f"{where}.{k} {_show(it[k])} is not text; use a string (may be empty)")
            if name == "directions":
                if not isinstance(it["frames"], list):
                    out.append(f"{where}.frames {_show(it['frames'])} is not a list; use a list of paths")
                else:
                    for j, f in enumerate(it["frames"]):
                        out += _rel_path_problems(f, f"{where}.frames[{j}]")
                continue
            out += _nonempty_str(it["beat"], f"{where}.beat", "a beat id")
            if beat_ids is not None and isinstance(it["beat"], str) and it["beat"] not in beat_ids:
                out.append(f"{where}.beat {_show(it['beat'])} is not a beat in the beat map; use one of its beat ids")
            if it["media"] is not None:
                out += _rel_path_problems(it["media"], f"{where}.media")
        if name == "directions":
            direction_ids = ids
    if "pick" in doc and doc["pick"] is not None:
        if not isinstance(doc["pick"], str):
            out.append(f"pick {_show(doc['pick'])} is not a direction id; use one of the directions' ids or null")
        elif direction_ids is not None and doc["pick"] not in direction_ids:
            out.append(f"pick {_show(doc['pick'])} is not a direction id; use one of the directions' ids or null")
    return out


def validate_beat_map(doc, words=None, timed_words=None):
    problems = beat_map_problems(doc, words, timed_words)
    if problems:
        raise SchemaError(problems)


def validate_sketches(doc, beat_map=None):
    problems = sketches_problems(doc, beat_map)
    if problems:
        raise SchemaError(problems)


def load_words(path):
    """Word strings from an S3 word list, in list order; a mark's w / an anchor's w0,w1 is the list position.

    Accepts transcribe_words {text, words:[{word,...}]} or an edit map {words:[{id, word,...}], ...}.
    Ids are not checked: S3's w_NNNN ids may skip numbers, and words are never renumbered.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SchemaError(f"word list {path} can't be read ({e}); point --words at the cut's word list JSON")
    items = data.get("words") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        raise SchemaError(f"word list {path} has no 'words' list; use S3's transcribe_words or edit map JSON")
    out = []
    for i, it in enumerate(items):
        if not (isinstance(it, dict) and isinstance(it.get("word"), str)):
            raise SchemaError(f"word list {path} words[{i}] {_show(it)} has no 'word' text; fix or regenerate the list")
        out.append(it["word"])
    return out


def _read_doc(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SchemaError(f"{path} can't be read as JSON ({e})")


def _report(problems, ok_line=None):
    """ok_line is a function so it only runs on a valid doc (whose keys are then known to exist)."""
    if problems:
        for p in problems:
            print(f"✗ {p}")
        return 1
    print(ok_line())
    return 0


def cmd_check(path, words_path=None):
    try:
        doc = _read_doc(path)
        words, timed_words = None, None
        if words_path:
            words = load_words(words_path)
            timed_words = _read_doc(words_path).get("words")
        elif isinstance(doc, dict) and not _rel_path_problems(doc.get("words"), "words"):
            beside = Path(path).resolve().parent / doc["words"]
            if beside.is_file():
                words = load_words(beside)
                timed_words = _read_doc(beside).get("words")
    except SchemaError as e:
        return _report(e.problems)
    return _report(beat_map_problems(doc, words, timed_words),
                   lambda: f"ok: {len(doc['beats'])} beats, {len(doc['word_marks'])} word marks")


def cmd_check_sketches(path, beat_map_path=None):
    try:
        doc = _read_doc(path)
        beat_map = _read_doc(beat_map_path) if beat_map_path else None
    except SchemaError as e:
        return _report(e.problems)
    return _report(sketches_problems(doc, beat_map),
                   lambda: f"ok: {len(doc['sketches'])} sketches, {len(doc['directions'])} directions")


def selftest():
    words = ["Three", "big", "wins,", "today.", "Go", "now!"]
    good = {
        "schema": 1, "reel": "demo", "fps": 30, "words": DEFAULT_WORDS,
        "beats": [
            {"id": "b_001", "start_f": 0, "end_f": 30, "speech_anchor": {"text": "three big wins", "w0": 0, "w1": 2},
             "layout": "full", "value": 3, "scene": None, "broll": None, "transition": None},
            {"id": "b_002", "start_f": 10, "end_f": 50, "speech_anchor": {"text": "today", "w0": 3, "w1": 3},
             "layout": "overlay", "value": None, "scene": {"id": "callout", "slots": {"text": "today"}}, "broll": None, "transition": None},
            {"id": "b_003", "start_f": 30, "end_f": 60, "speech_anchor": {"text": "Go now", "w0": 4, "w1": 5},
             "layout": "split", "value": 2.5, "scene": None, "broll": None, "transition": None},
        ],
        "word_marks": [{"w": 0, "mark": "num"}, {"w": 2, "mark": "key"}, {"w": 5, "mark": "cta"}],
        "proposed": {"b_001": {"layout": "split", "value": 3, "shows": "a counter to 3", "why": "a number said aloud"}},
        "notes": {"b_003": "make this punchier"},
        "needs": "",
        "sent_at": None,
    }
    sketches = {"schema": 1, "reel": "demo", "rough": "work/rough.mp4",
                "directions": [{"id": "d1", "name": "Bold", "why": "fast reel", "frames": ["work/d1/f1.png"], "note": ""},
                               {"id": "d2", "name": "Calm", "why": "", "frames": [], "note": ""}],
                "pick": "d1",
                "sketches": [{"id": "s1", "beat": "b_001", "title": "3 wins", "media": None, "note": ""}],
                "note": "", "sent_at": None, "locked_at": None}

    def m(fn):
        d = copy.deepcopy(good)
        fn(d)
        return d

    def drop_id(d):
        del d["beats"][0]["id"]

    def both(d, k, v):
        d["beats"][0][k] = v

    cases = [  # (name, problems, substring a failure must contain; None = must pass)
        ("scene params", scene_problems({"id": "x", "slots": {"s": ""},
                                         "params": {"n": 3, "s": "x", "b": True}}), None),
        ("scene missing id", beat_map_problems(m(lambda d: both(d, "scene", {"slots": {}}))), "b_001').scene is missing id"),
        ("scene non-string slot", beat_map_problems(m(lambda d: both(d, "scene", {"id": "x", "slots": {"s": 1}}))), ".slots['s']"),
        ("scene unknown key", beat_map_problems(m(lambda d: both(d, "scene", {"id": "x", "slots": {}, "extra": 1}))), "unknown keys extra"),
        ("sketches scene", sketches_problems(dict(sketches, scenes={"b_001": {"id": "x", "slots": {}}}), good), None),
        ("sketches scene unknown beat", sketches_problems(dict(sketches, scenes={"b_999": {"id": "x", "slots": {}}}), good), "scenes key 'b_999'"),
        ("valid map", beat_map_problems(good, words), None),
        ("proposed without check", beat_map_problems(good, words), None),
        ("proposed with check", beat_map_problems(m(lambda d: d["proposed"]["b_001"].update(
            check="I wanted the graphic alone here.")), words), None),
        ("proposed check trimmed length", beat_map_problems(m(lambda d: d["proposed"]["b_001"].update(
            check="  " + "x" * 200 + "  ")), words), None),
        ("proposed check one character", beat_map_problems(m(lambda d: d["proposed"]["b_001"].update(check="x")), words), None),
        ("valid map, no words", beat_map_problems(good), None),
        ("map with an edit_style object", beat_map_problems(m(lambda d: d.update(edit_style={"style": "punch-in"})),
                                                            words), None),
        ("edit_style not an object", beat_map_problems(m(lambda d: d.update(edit_style="punch-in")), words),
         "edit_style 'punch-in' is not an object"),
        ("beat with no id", beat_map_problems(m(drop_id), words), "missing id"),
        ("unknown layout", beat_map_problems(m(lambda d: both(d, "layout", "grid")), words),
         "beats[0].layout 'grid' is not a layout; use one of full, split, stack, pip, overlay"),
        ("start_f > end_f", beat_map_problems(m(lambda d: both(d, "start_f", 40)), words), "is after end_f"),
        ("unknown key", beat_map_problems(m(lambda d: both(d, "color", "red")), words), "unknown keys color"),
        ("overlapping non-overlay", beat_map_problems(m(lambda d: both(d, "end_f", 31)), words), "before beats[0] ends"),
        ("duplicate mark w", beat_map_problems(m(lambda d: d["word_marks"].append({"w": 5, "mark": "key"})), words),
         "marked twice"),
        ("unsorted marks", beat_map_problems(m(lambda d: d["word_marks"].append({"w": 1, "mark": "key"})), words),
         "sort word_marks"),
        ("unknown mark", beat_map_problems(m(lambda d: d["word_marks"][0].update(mark="bold")), words), "is not a mark"),
        ("mark w out of range", beat_map_problems(m(lambda d: d["word_marks"].append({"w": 6, "mark": "key"})), words),
         "past the word list"),
        ("mark without a spoken word", marks_problems([{"w": 0, "mark": "emph"}], [{"word": "—"}]),
         "word_marks[0].w 0 marks '—', which has no spoken word; mark a spoken word"),
        ("anchor text mismatch", beat_map_problems(
            m(lambda d: d["beats"][0]["speech_anchor"].update(text="three small wins")), words), "does not match words"),
        ("bool start_f", beat_map_problems(m(lambda d: both(d, "start_f", False)), words), "is not a frame"),
        ("words path with ..", beat_map_problems(m(lambda d: d.update(words="../x/words.json")), words),
         "not a plain relative path"),
        ("valid sketches", sketches_problems(sketches, good), None),
        ("sketch beat not in map", sketches_problems(
            dict(sketches, sketches=[dict(sketches["sketches"][0], beat="b_999")]), good), "not a beat in the beat map"),
        ("proposed key not a beat id", beat_map_problems(
            m(lambda d: d["proposed"].update(b_999=dict(d["proposed"]["b_001"]))), words), "proposed key 'b_999'"),
        ("map sent_at not ISO", beat_map_problems(m(lambda d: d.update(sent_at="yesterday")), words),
         "sent_at 'yesterday' is not an ISO 8601 timestamp"),
        ("map sent_at ISO with Z", beat_map_problems(m(lambda d: d.update(sent_at="2026-11-04T15:30:00Z")), words),
         None),
        ("sketches sent_at not ISO", sketches_problems(dict(sketches, sent_at="yesterday"), good),
         "sent_at 'yesterday' is not an ISO 8601 timestamp"),
        ("locked_at with no pick", sketches_problems(
            dict(sketches, pick=None, locked_at="2026-11-04T15:30:00Z"), good),
         "locked_at is set but no direction is picked; pick one before locking"),
        ("sent_at + locked_at + pick", sketches_problems(
            dict(sketches, sent_at="2026-11-04T15:00:00Z", locked_at="2026-11-04T15:30:00+00:00"), good), None),
        ("pick not a direction id", sketches_problems(dict(sketches, pick="d9"), good), "pick 'd9' is not a direction id"),
        ("frames path with ..", sketches_problems(
            dict(sketches, directions=[dict(sketches["directions"][0], frames=["../f1.png"])]), good),
         "directions[0].frames[0] '../f1.png' is not a plain relative path"),
    ]
    for name, value in (("null", None), ("empty", ""), ("blank", "  "), ("number", 3),
                        ("boolean", True), ("list", []), ("object", {}), ("newline", "one\ntwo"),
                        ("carriage return", "one\rtwo"), ("trailing newline", "one\n"),
                        ("too long", "x" * 201), ("trimmed too long", "  " + "x" * 201 + "  ")):
        cases.append(("proposed check " + name, beat_map_problems(m(
            lambda d: d["proposed"]["b_001"].update(check=value)), words),
            "check must be one line of text with 1 to 200 characters after trimming"))
    cases.extend([
        ("proposed check does not replace required keys", _proposed_value_problems(
            {"value": None, "shows": "", "why": "", "check": "Look here."}, "proposed"), "missing layout"),
        ("proposed still rejects unknown keys", _proposed_value_problems(
            dict(good["proposed"]["b_001"], extra="unknown"), "proposed"), "unknown keys extra"),
    ])
    clip = {"src": "broll/ingested/own.mp4", "in": 6, "out": 36, "fit": "cover", "ledger_id": "f01"}
    for name, changes, want in (
            ("cover", {}, None), ("blur-fill", {"fit": "blur-fill"}, None),
            ("unknown key", {"extra": 1}, "unknown keys"), ("stretch", {"fit": "stretch"}, "fit"),
            ("reversed", {"in": 40}, "end after"), ("short", {"out": 35}, "whole beat"),
            ("unsafe", {"src": "../x.mp4"}, "relative path"), ("float", {"in": 6.0}, "whole number"),
            ("negative", {"in": -1}, "whole number"), ("bad ledger id", {"ledger_id": "music01"}, "ledger_id")):
        cases.append(("broll " + name,
                      beat_map_problems(m(lambda d: both(d, "broll", dict(clip, **changes)))), want))
    cases.extend([("broll null", broll_problems(None), None),
                  ("broll not object", broll_problems("clip.mp4"), "not an object"),
                  ("broll missing keys", broll_problems({"src": "broll/x.mp4"}), "missing in, out, fit, ledger_id")])
    fails = []
    for name, problems, want in cases:
        if want is None and problems:
            fails.append(f"{name}: expected pass, got {problems}")
        elif want is not None and not any(want in p for p in problems):
            fails.append(f"{name}: expected a problem containing {want!r}, got {problems}")

    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / "work").mkdir()
        (t / "work" / "words.json").write_text(json.dumps({"text": " ".join(words), "words": [
            {"word": w, "start": i, "end": i + 1} for i, w in enumerate(words)]}), encoding="utf-8")
        edit_map = t / "edit-map.json"
        edit_map.write_text(json.dumps({"words": [{"id": f"w_{i:04d}", "word": w} for i, w in enumerate(words)]}),
                            encoding="utf-8")
        if load_words(t / "work" / "words.json") != words or load_words(edit_map) != words:
            fails.append("load_words: did not return the words in list order for both S3 shapes")
        bad = m(lambda d: d["beats"][0]["speech_anchor"].update(w1=9))
        (t / "beat-map.state.json").write_text(json.dumps(bad), encoding="utf-8")
        try:
            validate_beat_map(bad, load_words(t / "work" / "words.json"))
            fails.append("validate_beat_map: anchor past the word list did not raise SchemaError")
        except SchemaError as e:
            if not any("past the word list" in p for p in e.problems):
                fails.append(f"validate_beat_map: wrong problems {e.problems}")
        try:
            load_words(t / "beat-map.state.json")  # has a 'words' key, but it's a path string
            fails.append("load_words: a file with no words list did not raise")
        except SchemaError:
            pass

    if fails:
        for f in fails:
            print(f"selftest FAILED: {f}")
        return 1
    print("selftest ok")
    return 0


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Check a saved Beat Map or Sketches board file.")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="check a beat-map.state.json")
    c.add_argument("doc")
    c.add_argument("--words", help="the cut's word list JSON (default: the doc's 'words' path, e.g. work/edit_map.cut.json, if it exists)")
    s = sub.add_parser("check-sketches", help="check a sketches.state.json")
    s.add_argument("doc")
    s.add_argument("--beat-map", help="beat-map.state.json, to check each sketch's beat id exists")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.cmd == "check":
        return cmd_check(a.doc, a.words)
    if a.cmd == "check-sketches":
        return cmd_check_sketches(a.doc, a.beat_map)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
