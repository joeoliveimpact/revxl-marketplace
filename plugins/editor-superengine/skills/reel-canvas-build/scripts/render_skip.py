#!/usr/bin/env python3
"""Compose preview/master/layers only when their inputs changed since success."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "_shared")]
from win_encoding import ensure_utf8_output
import runtime as rt
import saved_style
import compose

P = HERE.parents[2]
MEDIA = {".mp4", ".mov", ".mkv", ".webm", ".wav", ".mp3", ".m4a", ".png", ".jpg", ".jpeg", ".webp"}
OUTPUTS = {".render-fp.json", "scale_track.json", "qa.json", "long-silences.json", "intake.json", "look-picker.json"}


def fingerprint(reel, tier, hook_text, layers):
    """Content for authored files, size/mtime for media; never hash render outputs.

    Include all plugin sources/runtime/templates, not just scenes currently
    selected: a dependency change must invalidate the successful render.
    """
    reel = Path(reel).resolve()
    h = hashlib.sha256()

    def add(label, path, *, stat_only=False):
        h.update(label.encode("utf-8") + b"\0")
        if not path.is_file():
            h.update(b"missing\0")
        elif stat_only:
            st = path.stat()
            h.update(f"{st.st_size}:{st.st_mtime_ns}".encode("ascii") + b"\0")
        else:
            h.update(path.read_bytes() + b"\0")

    h.update(json.dumps(dict(tier=tier, hook_text=hook_text, layers=layers,
                             tiers=compose.TIERS, quality=compose.QUALITY), sort_keys=True).encode("utf-8"))
    inputs = []
    for path in reel.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(reel)
        if rel.parts[0] in ("renders", "handoff") or "render-tmp" in rel.parts or "qa" in rel.parts:
            continue
        if path.name in OUTPUTS or path.name.endswith((".tmp", ".partial.mp4", ".partial.mov")):
            continue
        if path.suffix.lower() in (".json", ".cube", ".html", ".css", ".js", ".txt", ".srt", ".vtt", ".ass", ".svg") or path.suffix.lower() in MEDIA:
            inputs.append(path)
    # work/renders is intentionally included: its cut master is an input.
    for path in sorted(inputs):
        add("reel/" + path.relative_to(reel).as_posix(), path, stat_only=path.suffix.lower() in MEDIA)
    # B-roll is valid regardless of filename extension, or where within the
    # reel it was stored. Follow the actual references as well as the walk.
    send = reel / "beat-map-selection.json"
    if send.is_file():
        for beat in json.loads(send.read_text(encoding="utf-8")).get("beats", []):
            src = (beat.get("broll") or {}).get("src")
            if src:
                add("broll/" + str(src), reel / src, stat_only=True)
    # A changed or deleted preview revokes the existing master approval.
    if tier == "master" and layers == "all":
        for path in sorted((reel / "renders").glob("* Preview 720p - *.mp4")):
            add("approval-preview/" + path.name, path, stat_only=True)
    for path in sorted(P.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            add("plugin/" + path.relative_to(P).as_posix(), path)
    style_dir = saved_style.path().parent
    for path in sorted(style_dir.glob("*.json")):
        add("styles/" + path.name, path)
    add("runtime-state", rt.state_dir() / "state.json")
    # Workspace configuration can change the sound and asset selection.
    add("workspace-config", rt.config_path())
    return h.hexdigest()


def render(reel, tier, hook_text=None, *, force=False, keep_project=False, layers="all"):
    reel = Path(reel).resolve()
    if layers != "all":
        tier = "master"
    state = reel / "work/.render-fp.json"
    fp = fingerprint(reel, tier, hook_text, layers)
    try:
        old = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    output = reel / str(old.get("out", ""))
    if not force and old.get("fp") == fp and output.is_file():
        print(f"Render unchanged; kept {old['out']}.")
        return dict(out=old["out"], skipped=True)
    result = compose.render(reel, tier, hook_text, keep_project=keep_project, layers=layers)
    if not isinstance(result, dict) or not (reel / result.get("out", "")).is_file():
        raise ValueError("The render did not produce a finished output; no fingerprint was saved.")
    # Compose can save caption plans, approval metadata and remembered choices.
    # Fingerprint their settled values, so those writes do not cause a loop.
    settled = fingerprint(reel, tier, hook_text, layers)
    state.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=state.parent, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write((json.dumps(dict(fp=settled, out=result["out"]), indent=2) + "\n").encode("utf-8"))
        os.replace(temporary, state)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return dict(result, skipped=False)


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tier", choices=("preview", "master"))
    ap.add_argument("--reel-dir", type=Path, required=True)
    ap.add_argument("--hook-text")
    ap.add_argument("--layers", choices=("all", "aroll", "overlay", "captions"), default="all")
    ap.add_argument("--keep-project", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    try:
        result = render(a.reel_dir, a.tier, a.hook_text, force=a.force, keep_project=a.keep_project, layers=a.layers)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except compose.Stop as e:
        print("\n".join(e.lines))
        return e.code
    except (OSError, ValueError) as e:
        print(str(e).strip().splitlines()[0])
        return 2


if __name__ == "__main__":
    sys.exit(main())
