"""Licence rows (pre-render check): used music and footage have the licence rows they need.

  run(ctx) -> [{check, level: "block"|"warn", msg, where}]    ctx = {reel_dir, fps, cuts, beats, render}
  python checks/licence_rows.py <reel_dir>                     prints the rows; exit 1 on any block

No bed in sound-selection.json: no rows. Otherwise music.json must name the bed, its sha256 must match the file in
<reel>/beds/, and the row must be complete for its origin: pack (the starter pack), free (a free library: author
and licence page link too; a CC-BY licence also needs its attribution line, in credits.txt as well) or own (the
client's own track: only after they ticked "I have the rights").
"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cost_ask import file_sha256  # noqa: E402
import footage_check  # noqa: E402

PHASE = "pre"
CHECK = "licence_rows"
ORIGINS = ("pack", "free", "own")


def needs_attribution(licence):
    """CC-BY family: a "BY" token or "Creative Commons Attribution".
    ponytail: name heuristic; a licence table would be the upgrade if odd names turn up."""
    lic = licence or ""
    return bool(re.search(r"(?<![A-Za-z])BY(?![A-Za-z])", lic)) or "creative commons attribution" in lic.lower()


def gaps(row):
    """Plain names of what a library or music.json row is missing (the rights tick not counted)."""
    out = []
    if not (row.get("licence") or "").strip():
        out.append("the licence name")
    if row.get("origin") == "free":
        if not row.get("author"):
            out.append("the author")
        if not row.get("licence_url"):
            out.append("the licence page link")
    if needs_attribution(row.get("licence")) and not (row.get("attribution") or "").strip():
        out.append("the attribution line the licence asks for")
    if row.get("origin") not in ORIGINS:
        out.append("where the track came from")
    return out


def _read(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def footage(ctx):
    """Used B-roll and logged a-roll takes, independently of the sound pass."""
    reel = Path(ctx["reel_dir"])
    beats = ctx.get("beats")
    if beats is None:
        beats = (_read(reel / "beat-map-selection.json") or {}).get("beats", [])
    clips = [b["broll"] for b in beats if b.get("broll")]
    if not clips and not (reel / "footage" / "ledger.json").exists():
        return []

    def block(msg, where="footage/ledger.json"):
        return {"check": CHECK, "level": "block", "msg": msg, "where": where}

    try:
        ledger = footage_check.rows(reel)
        used, out = {}, []
        for clip in clips:
            matches = [r for r in ledger if r.get("id") == clip["ledger_id"] and
                       footage_check.normalized(footage_check.asset(reel, r["path"])) ==
                       footage_check.normalized(reel / clip["src"])]
            if len(matches) != 1:
                out.append(block(f"the footage {clip['src']} has no matching licence row"))
            else:
                used[matches[0]["id"]] = matches[0]
        cuts = ctx.get("cuts") or _read(reel / "work" / "cuts.json") or {}
        probe = _read(reel / "work" / "probe.json")
        raw = probe.get("input") if isinstance(probe, dict) else None
        raw = raw if isinstance(raw, str) and raw.strip() else None
        if cuts.get("segments") and not (cuts.get("takes") or raw):
            out.append(block("the cut's recording could not be found; restore its source details before making the final",
                             "work/probe.json"))
        if cuts.get("segments") and (cuts.get("takes") or raw):
            for use in footage_check.cut_uses(cuts, raw):
                key = footage_check.normalized(footage_check.asset(reel, use["path"]))
                matches = [r for r in ledger if footage_check.normalized(footage_check.asset(reel, r["path"])) == key]
                if len(matches) != 1:
                    out.append(block(f"the recording {Path(use['path']).name} has no matching licence row"))
                else:
                    used[matches[0]["id"]] = matches[0]
        for row in used.values():
            missing = []
            if not str(row.get("licence") or "").strip():
                missing.append("a licence")
            if row.get("origin") == "ai" and not str(row.get("job_id") or "").strip():
                missing.append("the AI job id")
            if missing:
                out.append(block(f"the footage row {row['id']} needs {' and '.join(missing)}"))
        return list({row["msg"]: row for row in out}.values())
    except (OSError, ValueError, KeyError, TypeError) as e:
        return [block("the footage licence rows could not be checked: " + str(e).splitlines()[0])]


def run(ctx):
    return footage(ctx) + music(ctx)


def music(ctx):
    reel = Path(ctx["reel_dir"])
    bed = ((_read(reel / "sound-selection.json") or {}).get("bed") or {}).get("file")
    if not bed:
        return []

    def block(msg, where="music.json"):
        return {"check": CHECK, "level": "block", "msg": msg, "where": where}

    m = _read(reel / "music.json")
    if not m or m.get("file") != bed:
        return [block("the music %s has no licence row yet" % bed)]
    rows = []
    src = reel / "beds" / bed
    if not src.is_file() or m.get("sha256") != file_sha256(src):
        rows.append(block("the music file %s isn't the one its licence row was written for" % bed, "beds/" + bed))
    missing = gaps(m)
    if missing:
        rows.append(block("the licence row for %s is missing %s" % (bed, ", ".join(missing))))
    att = (m.get("attribution") or "").strip()
    if needs_attribution(m.get("licence")) and att:
        credits = reel / "credits.txt"
        if not credits.is_file() or att not in credits.read_text(encoding="utf-8"):
            rows.append(block("the credit line for %s isn't in credits.txt" % bed, "credits.txt"))
    if m.get("origin") == "own" and m.get("rights_confirmed") is not True:
        rows.append(block("%s is the client's own track and the \"I have the rights\" box isn't ticked" % bed))
    return rows


def main(argv=None):
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: licence_rows.py <reel folder>")
        return 2
    rows = run({"reel_dir": argv[0], "fps": None, "cuts": None, "beats": None, "render": None})
    for r in rows:
        print("%s: %s (%s)" % (r["level"], r["msg"], r["where"]))
    if not rows:
        print("Licence rows: nothing missing.")
    return 1 if any(r["level"] == "block" for r in rows) else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "reel-sound-pass" / "scripts"))
    from _media import guarded
    sys.exit(guarded(main))
