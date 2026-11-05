"""The music library and the reel's licence row. Claude runs it from the client's workspace folder.

  music_pick.py list
      every track: the starter pack (editor/sound/beds/, catalogue beds.json) and the client's own library
      (editor/music/, catalogue library.json): title, mood, length, where it came from, licence status.
  music_pick.py add-free <file> --title T --author A --licence L --licence-url U [--attribution X] [--mood M]
      a track from a free library. Copied into editor/music/ with its sha256 and the licence exactly as the
      download page showed it. Refused without the licence, author or licence page link. A CC-BY licence gets the
      standard attribution line when none is given. Non-commercial (NC) or no-derivatives (ND) licences get a
      plain warning.
  music_pick.py add-own <file> --title T [--mood M]
      the client's own track; it can't go in a final until they tick "I have the rights" on the Sound Board.
  music_pick.py pick <reel>
      after the board's Send: writes videos/<reel>/music.json for the picked bed, and credits.txt when the licence
      asks for a credit line (ready for the post caption). No bed: removes both. A rights tick on an own track is
      kept in music.json and in the library. A track with no catalogue row gets licence null (the final refuses it).
"""
import argparse, json, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _media import workspace, write_json  # noqa: E402
import cost_ask, measure_sfx, music_fit  # noqa: E402
sys.path.insert(0, str(HERE.parents[1] / "_shared" / "checks"))
from licence_rows import gaps, needs_attribution  # noqa: E402

LABEL = {"pack": "Starter pack", "free": "Free library", "own": "Your track"}


def read(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def paths(editor_dir):
    """(pack beds folder, its catalogue, client music folder, its catalogue)."""
    beds, music = Path(editor_dir) / "sound" / "beds", Path(editor_dir) / "music"
    return beds, beds / "beds.json", music, music / "library.json"


def catalogues(editor_dir):
    """(pack rows, client rows), each {file: row}."""
    _, pj, _, lj = paths(editor_dir)
    return read(pj) or {}, read(lj) or {}


def lookup(editor_dir, name):
    pack, lib = catalogues(editor_dir)
    return dict(lib.get(name) or pack.get(name) or {})


def status(row):
    missing = gaps(row)
    if missing:
        return "needs a licence row (missing %s)" % ", ".join(missing)
    if row.get("origin") == "own" and row.get("rights_confirmed") is not True:
        return "needs the rights tick on the board"
    return "licence ok"


def mmss(s):
    return "%d:%02d" % divmod(int(round(s or 0)), 60)


def cmd_list(a):
    beds, _, music, _ = paths(workspace()[0])
    pack, lib = catalogues(workspace()[0])
    n = 0
    for folder, cat in ((beds, pack), (music, lib)):
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if f.is_file() and f.suffix.lower() in measure_sfx.SOUND_EXT:
                row = cat.get(f.name) or {"origin": "pack" if folder == beds else None}
                print("%s | %s | %s | %s | %s" % (row.get("title") or f.stem, row.get("mood") or "-",
                                                  mmss(measure_sfx.duration(f)), LABEL.get(row.get("origin"), "unknown"),
                                                  status(row)))
                n += 1
    if not n:
        print("No music yet. Add a free track or use your own.")
    return 0


def add(src, row):
    """Copies src into editor/music/ and writes its library row; an exit code."""
    beds, _, music, lj = paths(workspace()[0])
    src = Path(src)
    if not src.is_file():
        print("Couldn't find the track %s." % src.name)
        return 1
    if (music / src.name).exists() or (beds / src.name).exists():
        print("The music library already has a track named %s. Rename the file and add it again." % src.name)
        return 1
    music.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, music / src.name)
    lib = read(lj) or {}
    lib[src.name] = dict(row, sha256=cost_ask.file_sha256(music / src.name), added=cost_ask.now())
    write_json(lj, lib)
    print("Added %s (%s)." % (row["title"], LABEL[row["origin"]]))
    return 0


def cmd_add_free(a):
    missing = [n for n, v in (("the licence name", a.licence), ("the author", a.author),
                              ("the licence page link", a.licence_url)) if not (v or "").strip()]
    if missing:
        print("A free track needs its licence exactly as the download page shows it. Missing: %s. Nothing was added."
              % ", ".join(missing))
        return 1
    att = a.attribution
    if not att and needs_attribution(a.licence):
        att = '"%s" by %s, licensed under %s (%s)' % (a.title, a.author, a.licence, a.licence_url)
    lic = a.licence
    if re.search(r"(?<![A-Za-z])NC(?![A-Za-z])|non-?commercial", lic, re.I):
        print("Heads up: this licence is non-commercial, so a reel that promotes a business may not be allowed.")
    if re.search(r"(?<![A-Za-z])ND(?![A-Za-z])|no-?derivatives?", lic, re.I):
        print("Heads up: this licence allows no derivatives, and trimming or fading the track may count as a change.")
    row = {"title": a.title, "origin": "free", "author": a.author, "licence": lic, "licence_url": a.licence_url,
           "rights_confirmed": False}
    if a.mood:
        row["mood"] = a.mood
    if att:
        row["attribution"] = att
    return add(a.file, row)


def cmd_add_own(a):
    row = {"title": a.title, "origin": "own", "author": None, "licence": "Your own track", "licence_url": None,
           "rights_confirmed": False}
    if a.mood:
        row["mood"] = a.mood
    return add(a.file, row)


def pick(reel, editor_dir):
    """Writes reel/music.json (+ credits.txt) for the board's bed; returns the music row, or None without a bed."""
    reel = Path(reel)
    b = ((read(reel / "sound-selection.json") or {}).get("bed") or {})
    mj, cr = reel / "music.json", reel / "credits.txt"
    if not b.get("file"):
        mj.unlink(missing_ok=True)
        cr.unlink(missing_ok=True)
        return None
    f = b["file"]
    row = lookup(editor_dir, f)
    rights = row.get("rights_confirmed") is True or b.get("rights_confirmed") is True
    if row.get("origin") == "own" and rights and row.get("rights_confirmed") is not True:
        lj = paths(editor_dir)[3]
        lib = read(lj) or {}
        if f in lib:
            lib[f]["rights_confirmed"] = True
            write_json(lj, lib)
    src = reel / "beds" / f
    music = {"file": f, "sha256": cost_ask.file_sha256(src) if src.is_file() else None, "origin": row.get("origin"),
             "title": row.get("title"), "author": row.get("author"), "licence": row.get("licence"),
             "licence_url": row.get("licence_url"), "attribution": row.get("attribution"),
             "start": b.get("offset_s") or 0,   # the track position the bed plays from
             "level_db": music_fit.LEVEL_DB if b.get("gain_db") is None else b["gain_db"],
             "duck_db": music_fit.duck_depth(b.get("duck_db"))[0], "rights_confirmed": rights}
    write_json(mj, music)
    if needs_attribution(music["licence"]) and music["attribution"]:
        cr.write_bytes((music["attribution"] + "\n").encode("utf-8"))
    else:
        cr.unlink(missing_ok=True)
    return music


def cmd_pick(a):
    editor_dir, videos = workspace()
    reel = videos / a.reel
    if not reel.is_dir():
        print("There is no reel folder named %s." % a.reel)
        return 2
    m = pick(reel, editor_dir)
    if not m:
        print("No music picked on the board, so the reel has no music row.")
        return 0
    print("Music: %s (%s), %s." % (m["title"] or m["file"], LABEL.get(m["origin"], "unknown source"), status(m)))
    if (reel / "credits.txt").is_file():
        print("Credit line for the post caption: %s" % m["attribution"])
    return 0


def main(argv=None):
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="The music library and the reel's licence row.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    f = sub.add_parser("add-free")
    f.add_argument("file")
    f.add_argument("--title", required=True)
    for k in ("--author", "--licence", "--licence-url", "--attribution", "--mood"):
        f.add_argument(k)
    o = sub.add_parser("add-own")
    o.add_argument("file")
    o.add_argument("--title", required=True)
    o.add_argument("--mood")
    sub.add_parser("pick").add_argument("reel")
    a = ap.parse_args(argv)
    return {"list": cmd_list, "add-free": cmd_add_free, "add-own": cmd_add_own, "pick": cmd_pick}[a.cmd](a)


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main))
