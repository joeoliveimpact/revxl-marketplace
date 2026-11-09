"""Learn small saved-style changes at preview approval (stdlib only)."""
import json
import math
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cut_timing import GUARD_MS, pause_default

NOTE = "Your style's learning history couldn't be read, so I left it unchanged."
KEYS = {"look.strength": .05, "look.id": None, "caption_style.style": None,
        "edit_style.punch_scale": .01, "music.bed_gain_db": .5,
        "cut.pause_ms": 10, "cut.nudge_ms": 10}


def _store(style):
    import saved_style as ss
    index = ss._index(for_write=True)
    name = ss._style_id(index, style)
    row = index["styles"][name]
    return name, row["label"], ss.path(name).with_suffix(".learn.json"), row["created"]


def _fresh(created):
    return dict(schema=1, style_created=created, reels=[],
                auto=dict(on=False, declined_reel=None, offered_reel=None), learned=[])


def _read(target, created):
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _fresh(created)
    except (OSError, ValueError, RecursionError):
        raise ValueError(NOTE) from None
    try:
        if (data["schema"] != 1 or not isinstance(data["reels"], list) or
                not isinstance(data["learned"], list) or type(data["auto"]["on"]) is not bool):
            raise ValueError()
        for key in ("declined_at", "declined_reel", "offered_reel"):
            value = data["auto"].get(key)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError()
        for row in data["reels"]:
            if (not all(isinstance(row[k], str) for k in ("reel", "preview", "at", "why")) or
                    row["mode"] not in ("normal", "auto") or type(row["big"]) is not bool or
                    not isinstance(row["changes"], list)):
                raise ValueError()
            for change in row["changes"]:
                if (not isinstance(change["source"], str) or type(change["small"]) is not bool or
                        not isinstance(change["detail"], str) or
                        change["key"] is not None and change["key"] not in KEYS):
                    raise ValueError()
        for row in data["learned"]:
            if (row["key"] not in KEYS or not isinstance(row["at"], str) or
                    not isinstance(row["reels"], list) or not row["reels"] or
                    any(type(i) is not int or not 0 <= i < len(data["reels"]) for i in row["reels"]) or
                    "from" not in row or "to" not in row):
                raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise ValueError(NOTE) from None
    if data.get("style_created") != created:
        import os
        import saved_style as ss
        style_path = target.with_name(target.name.removesuffix(".learn.json") + ".json")
        archive = ss._next_archive_path(style_path).with_suffix(".learn.json")
        os.replace(target, archive)
        return _fresh(created)
    data["auto"].setdefault("declined_reel", None)
    data["auto"].setdefault("offered_reel", None)
    return data


def _write(target, data):
    import saved_style as ss
    ss._atomic(target, (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"))


def _doc(reel, name):
    try:
        data = json.loads((reel / name).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, RecursionError):
        return {}


def _rows(data, key):
    value = data.get(key, [])
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _num(value):
    return type(value) in (int, float) and math.isfinite(value)


def _id(row):
    value = row.get("id")
    return value if isinstance(value, (str, int)) else None


def changes(reel, style):
    """Compare each Send with its own proposal; absent boards contribute nothing."""
    import saved_style as ss
    result = []

    def add(source, small, detail, key=None, **numbers):
        result.append(dict(source=source, key=key, small=small, detail=detail, **numbers))

    def pause(proposed, sent, source="cut-board.pause", **extra):
        # selection_to_edl.cap_of uses a 9-second cap for "as spoken".
        # Retain that intent as well as the numeric caps for later timing learning.
        if proposed is None:
            proposed, extra["proposed_as_spoken"] = 9000, True
        if sent is None:
            sent, extra["sent_as_spoken"] = 9000, True
        if _num(proposed) and _num(sent) and proposed != sent:
            delta = sent - proposed
            add(source, abs(delta) <= 150, "a pause was changed",
                proposed_ms=proposed, sent_ms=sent, delta_ms=delta, **extra)

    cfg = _doc(reel, "cut-board.config.json")
    selection = _doc(reel, "cut-selection.json")
    if "gap_default_ms" in cfg and "gap_default_ms" in selection:
        pause(cfg["gap_default_ms"], selection["gap_default_ms"], source="cut-board.pause_default")
    default_pause = next((c for c in result if c["source"] == "cut-board.pause_default"), None)
    if default_pause is not None:
        default_pause.update(key="cut.pause_ms", delta=default_pause["delta_ms"])
    proposals = {_id(row): row for row in _rows(cfg, "lines") if _id(row) is not None}
    for row in _rows(selection, "lines"):
        proposal = proposals.get(_id(row))
        if proposal is None:
            continue
        line, default = row.get("id"), proposal.get("default")
        if row.get("drop") and default is not None:
            add("cut-board.drop", False, "a cut was removed", line=line)
        elif not row.get("drop"):
            if default is None:
                add("cut-board.restore", False, "a line was restored", line=line)
            elif row.get("pick", default) != default:
                add("cut-board.take", False, "a take was swapped", line=line,
                    **{"from": default, "to": row.get("pick")})
        gap = row.get("gap_after", {})
        if (isinstance(gap, dict) and "gap_default_ms" in cfg and
                gap.get("mode") == "override" and "ms" in gap):
            proposed = cfg.get("gap_default_ms")
            pause(proposed, gap.get("ms"), line=line, mode=gap["mode"])
        sil = row.get("sil", {})
        attempt = row.get("pick", default)
        if isinstance(sil, dict) and "gap_default_ms" in cfg and not row.get("drop") and attempt is not None:
            caps = sil.get(str(attempt), {})
            if isinstance(caps, dict):
                for silence, sent in caps.items():
                    pause(cfg.get("gap_default_ms"), sent, line=line, mode="override", attempt=attempt, silence=silence)
    tweak = _doc(reel, "tweak-selection.json")
    tweak_cfg = _doc(reel, "tweak-board.config.json")
    fps = tweak_cfg.get("fps")
    if not (_num(fps) and fps > 0):
        fps = _doc(reel, "work/cuts.json").get("fps")
    if not (_num(fps) and fps > 0):
        fps = ss._get(_doc(reel, "work/probe.json"), "fps.measured_fps")
    edge_tolerance = .5 / fps if _num(fps) and fps > 0 else 1 / 60
    cmap = tweak_cfg.get("map", [])
    joins = []
    if tweak.get("version") is not None and tweak.get("version") == tweak_cfg.get("version") and isinstance(cmap, list):
        for left, right in zip(cmap, cmap[1:]):
            if (isinstance(left, list) and isinstance(right, list) and len(left) == len(right) == 4
                    and all(_num(v) for v in left + right) and abs(left[1] - right[0]) <= 1e-6):
                joins.append(left[1])
    for mark in _rows(tweak, "marks"):
        kind = mark.get("kind", mark.get("type"))
        if kind == "cut" and _num(mark.get("a")) and _num(mark.get("b")):
            a, b = sorted((mark["a"], mark["b"]))
            # One endpoint anchors the join; the other trims at most 150 ms on just one side.
            matches = []
            if 0 < b - a <= .150 + 1e-6:
                for join in joins:
                    tail = abs(b - join) <= edge_tolerance and 0 < join - a <= .150 + 1e-6
                    head = abs(a - join) <= edge_tolerance and 0 < b - join <= .150 + 1e-6
                    if tail != head:
                        matches.append((join, "tail" if tail else "head"))
            if len(matches) == 1:
                join, edge = matches[0]
                delta = round((b - a) * 1000 * (-1 if edge == "tail" else 1), 6)
                add("tweak.edge", True, "a cut edge was trimmed", key="cut.nudge_ms", join_s=join, edge=edge,
                    nudge_ms=delta, delta=delta, a_s=mark["a"], b_s=mark["b"], version=tweak["version"])
            else:
                add("tweak.cut", False, "a cut was added", a_s=mark["a"], b_s=mark["b"], version=tweak.get("version"))
        elif kind in ("tight", "loose") and _num(mark.get("a")):
            ms = mark.get("ms", 150 if kind == "tight" else 500)
            if _num(ms):
                add("tweak." + kind, True, "a pause was changed", a_s=mark["a"], ms=ms)
    # Keep every client mark, but attach only one same-direction signal per key per reel.
    pause_rows = [c for c in result if c["source"] in ("tweak.tight", "tweak.loose")]
    base = selection.get("gap_default_ms", cfg.get("gap_default_ms", 150))
    if default_pause is None and pause_rows and _num(base):
        deltas = [c["ms"] - base for c in pause_rows]
        if all(d > 0 for d in deltas) or all(d < 0 for d in deltas):
            pause_rows[0].update(key="cut.pause_ms", delta=sum(deltas) / len(deltas))
    bm = _doc(reel, "beat-map-selection.json")
    proposed = _doc(reel, "beat-map.state.json").get("proposed", {})
    for beat in _rows(bm, "beats"):
        old = proposed.get(_id(beat)) if isinstance(proposed, dict) else None
        if isinstance(old, dict) and "layout" in beat and beat["layout"] != old.get("layout"):
            add("beat-map.layout", False, "a layout was changed", beat=beat.get("id"),
                **{"from": old.get("layout"), "to": beat["layout"]})
    for source, key, sent in (
            ("beat-map.punch_scale", "edit_style.punch_scale", ss._get(bm, "edit_style.punch_scale")),
            ("look-picker.caption", "caption_style.style", ss._get(_doc(reel, "look-picker-selection.json"), "caption_style.style")),
            ("grade.look", "look.id", ss._get(_doc(reel, "grade-selection.json"), "look.id")),
            ("grade.strength", "look.strength", ss._get(_doc(reel, "grade-selection.json"), "look.strength"))):
        old = ss._get(style, key)
        if old is not None and sent is not None and old != sent:
            numeric = KEYS[key] is not None
            if numeric and not (_num(old) and _num(sent)):
                continue
            if not numeric and not (isinstance(old, str) and isinstance(sent, str)):
                continue
            add(source, True, {"look.id": "the grade look was changed", "look.strength": "the grade strength was changed",
                "caption_style.style": "the caption look was changed", "edit_style.punch_scale": "the punch-in size was changed"}[key],
                key=key, style_value=old, sent_value=sent, **({"delta": sent - old} if numeric else {}))
    cfg = _doc(reel, "config.json")
    sound = _doc(reel, "sound-selection.json")
    old, sent = ss._get(cfg, "bed_default.gain_db"), ss._get(sound, "bed.gain_db")
    if _num(old) and _num(sent) and old != sent:
        delta = sent - old
        add("sound.bed", abs(delta) <= 3, "the music level changed by more than 3 dB" if abs(delta) > 3 else "the music level was changed",
            key="music.bed_gain_db", proposed_db=old, sent_db=sent, delta_db=delta)
    cues = {_id(row): row for row in _rows(cfg, "cues") if _id(row) is not None}
    for cue in _rows(sound, "cues"):
        old = cues.get(_id(cue), {}).get("time")
        sent = cue.get("time")
        if _num(old) and _num(sent) and old != sent:
            delta = round((sent - old) * 1000, 6)
            add("sound.cue", abs(delta) <= 150, "a sound moved", cue=cue.get("id"),
                proposed_s=old, sent_s=sent, delta_ms=delta)
    return result


def _threshold(workspace=None):
    import saved_style as ss
    if workspace is None:
        return 3
    root = Path(workspace)
    cfg = _doc(root, str(ss.runtime.config_path(root)))
    if not cfg:
        cfg = _doc(root, "editor.config.json")
    value = ss._get(cfg, "auto_edit.unlock_after")
    return value if type(value) is int and value >= 1 else 3


def _good(data):
    count = 0
    for row in reversed(data["reels"]):
        if row["big"]:
            break
        count += 1
    return count


def status(style, *, workspace=None):
    _, label, target, created = _store(style)
    data = _read(target, created)
    count, threshold = _good(data), _threshold(workspace)
    return dict(label=label, good_in_a_row=count, threshold=threshold,
                ready=count >= threshold, on=data["auto"]["on"])


def _offer(data, label, threshold):
    count = _good(data)
    current = len(data["reels"]) - 1
    declined, offered = (data["auto"][key] for key in ("declined_reel", "offered_reel"))
    if (count >= threshold and not data["auto"]["on"] and
            (declined is None or min(count, current - declined) >= 3) and
            (offered is None or min(count, current - offered) >= 3)):
        data["auto"]["offered_reel"] = current
        return f"{label} is ready for Auto edit: the last {count} reels needed only small tweaks. Turn it on?"
    return None


def _round(value, step):
    unit = Decimal(str(step))
    return float((Decimal(str(value)) / unit).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * unit)


def _learn(data, style, name, label, target):
    import saved_style as ss
    lines = []
    for key, step in KEYS.items():
        after = max((max(row["reels"]) for row in data["learned"] if row["key"] == key), default=-1)
        indexes = list(range(len(data["reels"]) - 3, len(data["reels"])))
        if indexes[0] <= after:
            continue
        rows = [[c for c in data["reels"][i]["changes"] if c["key"] == key and c["small"]] for i in indexes]
        if key == "cut.nudge_ms":
            signals = []
            for reel_rows in rows:
                deltas = [c.get("delta") for c in reel_rows
                          if c["source"] == "tweak.edge" and c.get("edge") == "head"
                          and _num(c.get("delta")) and c["delta"] > 0]
                signals.append([dict(delta=sum(deltas) / len(deltas))] if deltas else [])
            rows = signals
        if any(len(row) != 1 for row in rows):
            continue
        rows = [row[0] for row in rows]
        old = ss._get(style, key)
        if step is not None:
            deltas = [row.get("delta_db" if key == "music.bed_gain_db" else "delta") for row in rows]
            if not all(_num(d) for d in deltas) or not (all(d > 0 for d in deltas) or all(d < 0 for d in deltas)):
                continue
            delta = _round(sum(deltas) / 3, step)
            # Music may not have been saved before AE-2; its board retains the proposal.
            if old is None and key == "music.bed_gain_db":
                old = rows[-1]["proposed_db"]
            if old is None and key in ("cut.pause_ms", "cut.nudge_ms"):
                old = 150 if key == "cut.pause_ms" else 0
            if not _num(old) or not delta:
                continue
            new = round(old + delta, 8)
            if key in ("cut.pause_ms", "cut.nudge_ms"):
                lo, hi = (40, 600) if key == "cut.pause_ms" else (0, 150)
                new = min(hi, max(lo, new))
                if key == "cut.nudge_ms":
                    # Pause learning above has already updated this approval's style.
                    pause_ms = pause_default(ss._get(style, "cut.pause_ms"))
                    new = min(new, max(0, pause_ms - 2 * GUARD_MS))
                    if new <= old or new == 0:
                        continue
                if new == old:
                    continue
                delta = new - old
            if key == "cut.pause_ms":
                words = f"{'tighten' if delta < 0 else 'loosen'} pauses about {abs(delta):g} ms"
            elif key == "cut.nudge_ms":
                words = f"trim cuts about {new:g} ms later"
            elif key == "music.bed_gain_db":
                words = f"turn the music {'down' if delta < 0 else 'up'} about {abs(delta):g} dB"
            elif key == "look.strength":
                words = f"turn the grade strength {'down' if delta < 0 else 'up'} about {abs(delta) * 100:g}%"
            else:
                words = f"make the punch-ins {'smaller' if delta < 0 else 'larger'} by about {abs(delta):g}"
            line = f"I noticed you {words}, so {label} now does that."
        else:
            values = [row.get("sent_value") for row in rows]
            if not all(isinstance(v, str) for v in values) or len(set(values)) != 1:
                continue
            new = values[0]
            if old == new:
                continue
            words = ss.pick_label(new) + (" captions" if key == "caption_style.style" else " for the grade")
            line = f"I noticed you pick {words}, so {label} now uses {'them' if key == 'caption_style.style' else 'that look'}."
        parts = key.split(".")
        if not isinstance(style.get(parts[0]), dict):
            style[parts[0]] = {}
        style[parts[0]][parts[1]] = new
        data["learned"].append(dict(key=key, **{"from": old, "to": new}, at=ss._now(), reels=indexes))
        lines.append(line)
    if lines:
        _write(target, data)
        ss.save(style, name, archive=True)
    return lines


def record_approval(reel):
    import saved_style as ss
    reel = Path(reel).resolve()
    current = ss.pick_for(reel)
    if not current or current["how"] not in ("saved", "auto"):
        return []
    preview = _doc(reel, "work/render-ok.json").get("preview")
    if not isinstance(preview, str) or not preview:
        return []
    name, label, target, created = _store(current["style"])
    try:
        data = _read(target, created)
    except ValueError:
        print(NOTE, file=sys.stderr)
        return []
    if any(row["reel"] == str(reel) and row["preview"] == preview for row in data["reels"]):
        return []
    style = ss.load(name=name, for_write=True)
    edits = changes(reel, style)
    why = next((c["detail"] for c in edits if not c["small"]), "")
    if not why and sum(c["small"] for c in edits) > 5:
        why = "more than 5 small changes"
    data["reels"].append(dict(reel=str(reel), preview=preview, at=ss._now(),
        mode="auto" if current["how"] == "auto" else "normal", changes=edits, big=bool(why), why=why))
    try:
        workspace = ss._workspace(reel)
    except ValueError:
        workspace = None
    threshold = _threshold(workspace)
    previous = target.read_bytes() if target.exists() else None
    try:
        lines = _learn(data, style, name, label, target)
    except (OSError, ValueError):
        if previous is None:
            target.unlink(missing_ok=True)
        else:
            ss._atomic(target, previous)
        raise
    if current["how"] == "auto" and why:
        data["auto"]["on"] = False
        lines.append(f"Auto edit is off for {label}: this reel needed a bigger change ({why}). {threshold} more smooth reels turn it back on.")
    offer = _offer(data, label, threshold)
    if offer:
        lines.append(offer)
    _write(target, data)
    return lines


def set_auto(style, on, *, workspace=None):
    import saved_style as ss
    _, label, target, created = _store(style)
    data = _read(target, created)
    if workspace is None:
        index = ss._index()
        current = index["picks"].get(index["active_reel"])
        if current:
            try:
                workspace = ss._workspace(Path(current["reel"]))
            except ValueError:
                pass
    threshold = _threshold(workspace)
    if on and _good(data) < threshold:
        raise ValueError(f"Auto edit needs {threshold} smooth reels in a row for {label} before it can turn on.")
    data["auto"]["on"] = bool(on)
    if on:
        data["auto"]["declined_reel"] = None
        data["auto"]["offered_reel"] = None
    _write(target, data)
    return f"Auto edit is {'on' if on else 'off'} for {label}."


def decline(style):
    _, label, target, created = _store(style)
    data = _read(target, created)
    data["auto"]["declined_reel"] = len(data["reels"]) - 1 if data["reels"] else None
    data["auto"]["offered_reel"] = None
    _write(target, data)
    return f"I'll ask about Auto edit for {label} after more smooth reels."


def main(argv=None):
    import saved_style as ss
    ap = ss._Parser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("record").add_argument("reel")
    auto = sub.add_parser("auto")
    auto.add_argument("style")
    auto.add_argument("on", choices=("on", "off"))
    auto.add_argument("--workspace")
    sub.add_parser("decline").add_argument("style")
    show = sub.add_parser("status")
    show.add_argument("style", nargs="?")
    show.add_argument("--workspace")
    try:
        args = ap.parse_args(argv)
        if args.command == "record":
            for line in record_approval(args.reel):
                print(line)
        elif args.command == "auto":
            print(set_auto(args.style, args.on == "on", workspace=args.workspace))
        elif args.command == "decline":
            print(decline(args.style))
        else:
            for name in [args.style] if args.style else [s["id"] for s in ss.styles()]:
                row = status(name, workspace=args.workspace)
                print(f"{row['label']}: Auto edit {'on' if row['on'] else 'off'}, {row['good_in_a_row']} smooth reels in a row; {row['threshold']} needed.")
    except (OSError, ValueError) as error:
        print(str(error) if isinstance(error, ValueError) else "I couldn't read or save your style's learning history.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
