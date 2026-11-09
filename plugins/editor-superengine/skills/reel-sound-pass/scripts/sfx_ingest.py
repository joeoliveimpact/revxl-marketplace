"""The sound library (H-B7): fetch the pack, verify it, add one sound.

  sfx_ingest.py fetch [--manifest <json>]
      The pack manifest {url, sha256, bytes} comes from --manifest, else editor.config.json "sfx_pack", else the
      shipped pack.json. url null: there is no library yet, the mix ships voice only (exit 0). The download goes
      to a temp file; its size and sha256 are checked BEFORE anything is unpacked (mismatch: exit 1, the temp
      file is deleted, nothing unpacked). Then it unpacks into <paths.editor>/sound/ (no entry may land outside
      it) and records every file's sha256 in library-index.json.
  sfx_ingest.py verify
      every file in the library matches its recorded sha256 (exit 1 on any difference).
  sfx_ingest.py add <file>
      adds one sound: leading and trailing near-silence trimmed (50 dB under the sound's own peak, 10 ms kept
      each side), saved as WAV, measured and recorded in the index.
Runs from the client's workspace folder.
"""
import argparse, hashlib, json, os, sys, tempfile, urllib.request, zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _media import SR, decode, write_wav, workspace, write_json, rt  # noqa: E402
import cost_ask, measure_sfx  # noqa: E402
from safe_fetch import download, write_new  # noqa: E402

INDEX = "library-index.json"
TRIM_DB, KEEP_S = -50.0, 0.01
NO_LIBRARY = "There is no sound library yet, so the mix will be voice only."


def library():
    return workspace()[0] / "sound"


def load_index(lib):
    try:
        return json.loads((lib / INDEX).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"files": {}}


def library_files(lib):
    return sorted(p for p in lib.rglob("*") if p.is_file() and p.name != INDEX and not p.name.endswith(".tmp"))


def manifest(path):
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return rt.read_config().get("sfx_pack") or json.loads((HERE.parent / "pack.json").read_text(encoding="utf-8"))


def fetch(a):
    m = manifest(a.manifest)
    if not m.get("url"):
        print(NO_LIBRARY)
        return 0
    lib = library()
    fd, tmp = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    try:
        n = download(m["url"], tmp, m.get("bytes"))
        if n != m.get("bytes") or cost_ask.file_sha256(tmp) != m.get("sha256"):
            print("The sound library download didn't match what was expected (%s), so nothing was unpacked. "
                  "Try again later." % ("size" if n != m.get("bytes") else "checksum"))
            return 1
        top = lib.resolve()
        with zipfile.ZipFile(tmp) as z:
            names = [i for i in z.infolist() if not i.is_dir()]
            for i in names:
                dest = (lib / i.filename).resolve()
                if top not in dest.parents:
                    print("The sound library has a file that would land outside its folder, so nothing was unpacked.")
                    return 1
            lib.mkdir(parents=True, exist_ok=True)
            for i in names:
                dest = (lib / i.filename).resolve()
                dest.parent.mkdir(parents=True, exist_ok=True)
                write_new(dest, z.read(i))
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        print("The sound library couldn't be downloaded or opened: %s" % str(e).strip().splitlines()[0])
        return 1
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    index = {"pack": {"url": m["url"], "sha256": m["sha256"]},
             "files": {p.relative_to(lib).as_posix(): {"sha256": cost_ask.file_sha256(p)} for p in library_files(lib)}}
    write_json(lib / INDEX, index)
    print("Sound library ready: %d files." % len(index["files"]))
    return 0


def verify(a):
    lib = library()
    files = load_index(lib).get("files", {})
    if not files:
        print(NO_LIBRARY)
        return 1
    bad = []
    on_disk = {p.relative_to(lib).as_posix(): p for p in library_files(lib)}
    for rel, row in files.items():
        p = on_disk.get(rel)
        if not p or cost_ask.file_sha256(p) != row.get("sha256"):
            bad.append(rel)
    bad += [rel for rel in on_disk if rel not in files]
    if bad:
        print("%d sound library file(s) changed, went missing or were never recorded: %s" % (len(bad), ", ".join(sorted(bad)[:10])))
        return 1
    print("Sound library verified: %d files." % len(files))
    return 0


def trim(x):
    """x without its leading and trailing near-silence (relative to its own peak), KEEP_S kept each side."""
    level = np.abs(x).max(axis=1)
    peak = level.max()
    if peak <= 0:
        return None
    loud = np.flatnonzero(level > peak * 10 ** (TRIM_DB / 20))
    keep = int(KEEP_S * SR)
    return x[max(0, loud[0] - keep):min(len(x), loud[-1] + 1 + keep)]


def add(a):
    src = Path(a.file)
    lib = library()
    y = trim(decode(src))
    if y is None:
        print("%s is silent, so it wasn't added." % src.name)
        return 1
    lib.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sound-add-") as folder:
        encoded = Path(folder) / "sound.wav"
        write_wav(encoded, y)
        dest = write_new(lib / (src.stem + ".wav"), encoded.read_bytes())
    row = measure_sfx.measure(dest)
    index = load_index(lib)
    index.setdefault("files", {})[dest.relative_to(lib).as_posix()] = {"sha256": cost_ask.file_sha256(dest), **row}
    write_json(lib / INDEX, index)
    print("Added %s (%.2f s, peak %s dBFS)." % (dest.name, row["duration"] or 0, row["peak_dbfs"]))
    return 0


def main(argv=None):
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="The sound library: fetch, verify, add.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch").add_argument("--manifest")
    sub.add_parser("verify")
    sub.add_parser("add").add_argument("file")
    a = ap.parse_args(argv)
    return {"fetch": fetch, "verify": verify, "add": add}[a.cmd](a)


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main))
