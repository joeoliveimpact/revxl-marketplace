# Changed from shorts-studio scripts/learn.py (MIT): per-client saved style, Standing notes, "Could not be matched".
"""Keep a client's exact words beside choices that apply to every reel."""
import argparse
import copy
import datetime
import json
import sys
import uuid
from pathlib import Path

# Claude runs this file with -I, which leaves the script folder off sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import saved_style


def choice(key, raw):
    row = next((row for row in saved_style.FIELDS
                if row["key"] == key and row["where"] == "saved style"), None)
    if row is None:
        raise ValueError("Choose a setting from the saved style; this setting cannot be a Standing note.")
    try:
        value = json.loads(raw)
    except ValueError:
        raise ValueError("Give the setting's value as valid JSON, with text in double quotes.") from None
    if value is None:
        raise ValueError("Choose a value for this Standing note; remove the note to leave the setting unset.")
    candidate = {}
    set_choice(candidate, key, value)
    saved_style.validate(candidate)
    return value


def set_choice(data, key, value):
    parts = key.split(".")
    for part in parts[:-1]:
        if data.get(part) is None:
            data[part] = {}
        if not isinstance(data[part], dict):
            raise ValueError("This setting needs an object of choices in the saved style.")
        data = data[part]
    data[parts[-1]] = value


def clear_choice(data, key):
    parts = key.split(".")
    parents = []
    for part in parts[:-1]:
        child = data.get(part)
        if not isinstance(child, dict):
            return
        parents.append((data, part))
        data = child
    data.pop(parts[-1], None)
    for parent, part in reversed(parents):
        if parent[part]:
            break
        del parent[part]


def apply_note(data, notes, note, key, value):
    note.update(key=key, value=value, status="matched")
    if note in notes:
        notes.remove(note)
    notes.append(note)
    rebuild(data, notes)


def rebuild(data, notes):
    """Parent keys replace child keys, regardless of age; the newest note on the same key wins.

    Recompute after removal so earlier notes become active and no replacement points at a removed note.
    """
    matched = [n for n in notes if n["status"] == "matched"]
    for note in matched:
        clear_choice(data, note["key"])
        note.pop("replaced_by", None)
    for note in matched:
        candidates = [(i, n) for i, n in enumerate(matched)
                      if n["key"] == note["key"] or note["key"].startswith(n["key"] + ".")]
        _, winner = min(candidates, key=lambda item: (item[1]["key"].count("."), -item[0]))
        if winner is not note:
            note["replaced_by"] = winner["id"]
        else:
            set_choice(data, note["key"], copy.deepcopy(note["value"]))


def record_pick(key, value, *, note=None, style="default"):
    """Remember a choice without applying it; words belong only to an unchanged value."""
    value = choice(key, json.dumps(value, ensure_ascii=False))
    automatic = note is None
    try:
        data = saved_style.load(name=style, for_write=True)
        previous = saved_style.recommendation(key, data)
        if note is None:
            note = previous["note"] if previous and previous["value"] == value else ""
        current = data.get("picks", {}).get(key)
        if current and current["value"] == value and current["note"] == note:
            return
        data.setdefault("picks", {})[key] = dict(value=value, note=note,
            at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        saved_style.save(data, style)
    except saved_style.UnreadableStyleError:
        if not automatic:
            raise
        print(saved_style.NOTE, file=sys.stderr)


def pick_lines(data):
    labels = {row["key"]: row["plain"].lower() for row in saved_style.FIELDS}
    output = []
    for key, pick in data.get("picks", {}).items():
        what = "captions" if key == "caption_style.style" else labels[key]
        output.append(f'Last time you picked {saved_style.pick_label(pick["value"])} for {what}'
                      f' - your words: "{pick["note"]}"')
    return output


def lines(data, ids=False):
    notes = data.get("standing_notes", [])
    labels = {row["key"]: row["plain"] for row in saved_style.FIELDS
              if row["where"] == "saved style"}
    output = ["Standing notes:"] if any(note["status"] == "matched" for note in notes) else []
    for note in notes:
        if note["status"] != "matched":
            continue
        if "replaced_by" in note:
            parent = next((n for n in notes if n["id"] == note["replaced_by"]), None)
            replaced = (f'replaced by note {note["replaced_by"]}' if ids else
                        "replaced by a parent setting's note" if parent and parent["key"] != note["key"]
                        else "replaced by a newer note")
            prefix = f'Note {note["id"]}: ' if ids else ""
            output.append(f'{prefix}"{note["note"]}" ({replaced})')
        else:
            value = note["value"]
            plain = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            prefix = f'Note {note["id"]}: ' if ids else ""
            output.append(f'{prefix}Always: {labels[note["key"]]} = {plain} (your words: "{note["note"]}")')
    output.append("Could not be matched:")
    for note in notes:
        if note["status"] == "unmatched":
            prefix = f'Note {note["id"]}: ' if ids else ""
            output.append(f'{prefix}"{note["note"]}". '
                          "I couldn't tie this to a setting; tell me which part of the edit it's about.")
    return output


def parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--style", default=saved_style.active_name())
    sub = ap.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add")
    add.add_argument("note")
    mode = add.add_mutually_exclusive_group(required=True)
    mode.add_argument("--key")
    mode.add_argument("--unmatched", action="store_true")
    add.add_argument("--value")
    listing = sub.add_parser("list")
    listing.add_argument("--ids", action="store_true", help="include note ids for Claude")
    pick = sub.add_parser("pick")
    pick.add_argument("key")
    pick.add_argument("--value", required=True)
    pick.add_argument("--note", required=True)
    sub.add_parser("picks")
    match = sub.add_parser("match")
    match.add_argument("id")
    match.add_argument("--key", required=True)
    match.add_argument("--value", required=True)
    remove = sub.add_parser("remove")
    remove.add_argument("id")
    for command in sub.choices.values():
        command.add_argument("--style", default=argparse.SUPPRESS)
    return ap


def main(argv=None):
    ap = parser()
    args = ap.parse_args(argv)
    if args.command == "add":
        if args.unmatched and args.value is not None:
            ap.error("Leave out the value when a note could not be matched.")
        if not args.unmatched and args.value is None:
            ap.error("Give this setting's value with --value.")
    try:
        value = (choice(args.key, args.value)
                 if args.command in ("match", "pick") or args.command == "add" and not args.unmatched else None)
        data = saved_style.load(name=args.style, for_write=args.command not in ("list", "picks"))
        if args.command == "list":
            print("\n".join(lines(data, args.ids)))
            return 0
        if args.command == "picks":
            print("\n".join(pick_lines(data)))
            return 0
        if args.command == "pick":
            record_pick(args.key, value, note=args.note, style=args.style)
            print("Remembered for next time; I'll still ask.")
            return 0
        notes = data.setdefault("standing_notes", [])
        if args.command == "add":
            note = dict(id=uuid.uuid4().hex, note=args.note, key=None, value=None,
                        added=datetime.datetime.now(datetime.timezone.utc).isoformat(), status="unmatched")
            if not args.unmatched:
                apply_note(data, notes, note, args.key, value)
            else:
                notes.append(note)
        else:
            note = next((note for note in notes if str(note["id"]) == args.id), None)
            if note is None:
                raise ValueError("That Standing note was not found. List the notes and use its id.")
            if args.command == "match":
                if note["status"] != "unmatched":
                    raise ValueError("This note is already matched. Add a new note to change its setting.")
                apply_note(data, notes, note, args.key, value)
            else:
                if note["status"] == "matched":
                    clear_choice(data, note["key"])
                notes.remove(note)
                rebuild(data, notes)
        saved_style.save(data, args.style)
        print('Standing note '
              + ("removed; earlier notes on this setting apply again, otherwise I'll ask."
                 if args.command == "remove" else "saved."))
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
