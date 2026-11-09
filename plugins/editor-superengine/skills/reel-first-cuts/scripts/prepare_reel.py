"""Create a reel's recording folder or prepare its single raw take; never move or replace a source."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "editor-doctor/scripts"))
from board_sync import is_real, workspace_paths
from win_encoding import ensure_utf8_output


def prepare(root, name):
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_. -]{0,119}", name) or name.endswith((".", " ")):
        raise ValueError("Use a reel name starting with a letter, number or underscore; no trailing dot or space")
    _, videos = workspace_paths(Path(root).resolve())
    folder = videos / name
    raw = folder / "raw"
    if not all(is_real(p) for p in (videos, folder, raw, folder / "RAW.mp4")):
        raise ValueError("A recording path is a link; left untouched")
    raw.mkdir(parents=True, exist_ok=True)
    top = folder / "RAW.mp4"
    sources = sorted(p for p in raw.iterdir() if p.is_file() and is_real(p)
                     and p.suffix.lower() in (".mp4", ".mov", ".m4v", ".mkv"))
    if len(sources) > 1:
        return {"mode": "several", "folder": str(folder), "sources": [str(p) for p in sources]}
    if top.is_file():
        return {"mode": "single", "folder": str(folder), "sources": [str(top)]}
    if len(sources) == 1:
        # Exclusive creation protects an existing raw even if another process created it since the check.
        with sources[0].open("rb") as src, top.open("xb") as dest:
            try:
                shutil.copyfileobj(src, dest)
            except OSError:
                dest.close()
                top.unlink()
                raise
        shutil.copystat(sources[0], top)
        return {"mode": "single", "folder": str(folder), "sources": [str(top)]}
    return {"mode": "record", "folder": str(folder),
            "drop_folder": str(raw), "sources": [str(p) for p in sources]}


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reel")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    try:
        print(json.dumps(prepare(args.root, args.reel), ensure_ascii=False))
        return 0
    except (OSError, ValueError) as e:
        print(f"Could not prepare the recording: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
