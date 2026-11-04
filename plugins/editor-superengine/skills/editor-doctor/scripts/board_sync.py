"""Copy the boards' templates into the client's workspace (S4a), stdlib only.

Claude runs it from the client's workspace folder (board_server.py also runs it at every start):
  <editor python> -X utf8 -I board_sync.py [--root <workspace>]
For every board in boards.json whose template folder exists (skills/<owning-skill>/boards/<board>/), it copies the
template plus assets/board-client.js into <root>/<paths.editor>/<board>/ and stamps .board-version (plugin version +
content hash). A current stamp changes nothing. A stale or missing stamp overwrites only the template's own files and
board-client.js, then re-stamps; state files, *.prev and the client's own files are never touched or deleted.
It also keeps <root>/<paths.editor>/.gitignore ignoring .board-server.json, *.prev and *.tmp.
Prints one plain line per board. Never writes editor.config.json (the doctor owns it).
"""
import argparse, hashlib, json, os, sys
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
import runtime as rt  # noqa: E402

CLIENT = "board-client.js"
STAMP = ".board-version"
IGNORE = (".board-server.json", "*.prev", "*.tmp")


def load_manifest(plugin_root=rt.PLUGIN_ROOT):
    """{board: {"skill", "template"}}: the one board whitelist."""
    p = Path(plugin_root) / "skills" / "editor-doctor" / "scripts" / "boards.json"
    return json.loads(p.read_text(encoding="utf-8"))["boards"]


def workspace_paths(root):
    """(editor folder, videos folder) from editor.config.json `paths`, each checked to stay inside the workspace."""
    paths = rt.read_config(root).get("paths") or {}
    out = []
    for key in ("editor", "videos"):
        rel = paths.get(key) or key
        p = PurePosixPath(str(rel).replace("\\", "/"))
        if p.is_absolute() or ":" in str(rel) or not p.parts or any(s in ("", ".", "..") for s in p.parts):
            raise ValueError(f"paths.{key} in editor/editor.config.json must be a folder inside the workspace")
        out.append(Path(root).joinpath(*p.parts))
    return tuple(out)


def template_files(src):
    """Sorted relative paths of a template's files (dotfiles and __pycache__ left out)."""
    return sorted(p.relative_to(src).as_posix() for p in src.rglob("*")
                  if p.is_file() and not any(s.startswith(".") or s == "__pycache__" for s in p.relative_to(src).parts))


def stamp_for(src, files, client_bytes, version):
    h = hashlib.sha256()
    for rel in files:
        h.update(rel.encode("utf-8") + b"\0" + (src / rel).read_bytes() + b"\0")
    h.update(CLIENT.encode() + b"\0" + client_bytes)  # a new board-client.js refreshes every copy too
    return {"version": version, "hash": h.hexdigest()}


def write_gitignore(editor_dir):
    p = editor_dir / ".gitignore"
    old = p.read_bytes() if p.exists() else b""
    have = {ln.strip() for ln in old.decode("utf-8", "replace").splitlines()}
    missing = [ln for ln in IGNORE if ln not in have]
    if missing:
        sep = b"\n" if old and not old.endswith(b"\n") else b""
        p.write_bytes(old + sep + "".join(ln + "\n" for ln in missing).encode("utf-8"))


def safe_write(board_dir, rel, data):
    """Write board_dir/rel unless a link (or a path leaving the board folder) is in the way; False = skipped.
    ponytail: checked, then written; a link planted between the two steps is out of scope (local, single user)."""
    out, cur = board_dir / rel, board_dir
    for part in Path(rel).parts:
        cur = cur / part
        if cur.is_symlink():
            return False
    out.parent.mkdir(parents=True, exist_ok=True)
    top = os.path.normcase(os.path.realpath(board_dir))
    real = os.path.normcase(os.path.realpath(out))
    try:
        if os.path.commonpath([real, top]) != top or real == top:
            return False
    except ValueError:  # another drive
        return False
    out.write_bytes(data)
    return True


def is_real(p):
    """False when p is a link or junction (Python 3.12 is_symlink() misses junctions): its real path moved."""
    return os.path.normcase(os.path.realpath(p)) == os.path.normcase(os.path.abspath(p))


def sync(root, plugin_root=rt.PLUGIN_ROOT):
    """Returns one plain line per board."""
    root, plugin_root = Path(os.path.realpath(root)), Path(plugin_root)  # links above the workspace are fine
    editor_dir, _ = workspace_paths(root)
    version = json.loads((plugin_root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    client = (plugin_root / "skills" / "editor-doctor" / "assets" / CLIENT).read_bytes()
    editor_dir.mkdir(parents=True, exist_ok=True)
    if not is_real(editor_dir):
        return [f"⚠ boards: skipped, the {editor_dir.name} folder is a link to somewhere else (left as it is)"]
    write_gitignore(editor_dir)
    notes = []
    for board, entry in load_manifest(plugin_root).items():
        src = plugin_root / entry["template"]
        if not src.is_dir():
            notes.append(f"{board}: not built yet, nothing to copy")
            continue
        files = template_files(src)
        stamp = stamp_for(src, files, client, version)
        dest = editor_dir / board
        try:
            cur = json.loads((dest / STAMP).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cur = None
        if cur == stamp:
            notes.append(f"{board}: up to date")
            continue
        if not is_real(dest):
            notes.append(f"⚠ {board}: skipped, its folder is a link to somewhere else (left as it is)")
            continue
        dest.mkdir(exist_ok=True)
        skipped = [rel for rel, data in [(r, (src / r).read_bytes()) for r in files] + [(CLIENT, client)]
                   if not safe_write(dest, rel, data)]
        for rel in skipped:
            notes.append(f"⚠ {board}: skipped {rel}, it is a link to somewhere else (left as it is)")
        if skipped:  # no stamp, so the next sync tries again once the link is gone
            continue
        if not safe_write(dest, STAMP, (json.dumps(stamp) + "\n").encode("utf-8")):
            notes.append(f"⚠ {board}: skipped {STAMP}, it is a link to somewhere else (left as it is)")
            continue
        notes.append(f"{board}: {'copied' if cur is None else 'refreshed'} (your saved work is untouched)")
    return notes


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".", help="the client's workspace folder (default: cwd)")
    a = ap.parse_args(argv)
    try:
        for line in sync(Path(a.root).resolve()):
            print(line)
    except (OSError, ValueError, KeyError) as e:
        print(f"✗ Editor boards: copying the boards failed: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
