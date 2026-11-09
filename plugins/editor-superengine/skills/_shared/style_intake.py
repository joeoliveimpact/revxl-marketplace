#!/usr/bin/env python3
"""Save a style's origin and named colours beside the saved style file."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from win_encoding import ensure_utf8_output
import saved_style


def path(ident):
    return saved_style.path(ident).with_suffix(".intake.json")


def save(ident, origin, colours):
    if origin not in ("client", "reference", "default"):
        raise ValueError("Choose client, reference or default as the style origin.")
    if not isinstance(colours, list) or any(not isinstance(c, dict) or
            not re.fullmatch(r"#[0-9a-fA-F]{6}", str(c.get("hex", ""))) or
            not isinstance(c.get("meaning"), str) or not c["meaning"].strip() for c in colours):
        raise ValueError("Each colour needs a six-digit hex and a short meaning.")
    doc = dict(origin=origin, colours=[dict(hex=c["hex"], meaning=c["meaning"]) for c in colours])
    target = path(ident)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write((json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    if len(colours) > 5:
        print(f"Warning: this style has {len(colours)} colours. Which should we drop to reach five? All are kept for now.")
    print(readback(ident))
    return doc


def read(ident):
    target = path(ident)
    return json.loads(target.read_text(encoding="utf-8")) if target.is_file() else None


def readback(ident):
    doc = read(ident)
    if doc is None:
        return "Style intake has not been saved yet."
    colours = "; ".join(f"{c['hex']}: {c['meaning']}" for c in doc["colours"]) or "no colours"
    return f"Style {ident} came from {doc['origin']}; colours: {colours}."


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    writer = sub.add_parser("save")
    writer.add_argument("id")
    writer.add_argument("document", type=Path, help="JSON with origin and colours")
    sub.add_parser("read").add_argument("id")
    a = ap.parse_args(argv)
    try:
        if a.command == "save":
            doc = json.loads(a.document.read_text(encoding="utf-8"))
            save(a.id, doc["origin"], doc["colours"])
        else:
            print(readback(a.id))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(str(e).strip().splitlines()[0])
        return 2


if __name__ == "__main__":
    sys.exit(main())
