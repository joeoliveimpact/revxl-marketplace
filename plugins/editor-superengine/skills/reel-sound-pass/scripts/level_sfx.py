"""Match picked effects by maximum momentary loudness, keeping hand levels and clean peaks.

  level_sfx.py --reel <reel>
"""
import argparse, json, re, statistics, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _media import ffmpeg, workspace  # noqa: E402


def own_loudness(path):
    """Maximum momentary LUFS; padding lets even sub-400 ms hits fill the meter's window."""
    p = subprocess.run([ffmpeg(), "-nostdin", "-hide_banner", "-i", str(path),
                        "-af", "apad=pad_dur=1,ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    values = [float(v) for v in re.findall(r"M:\s*(-?[\d.]+)", p.stderr) if float(v) > -70]
    if p.returncode:
        raise ValueError("No loudness measured for %s; check that the effect contains audible sound." % path)
    return max(values) if values else None


def is_by_hand(cue):
    if "gain_by_hand" in cue:
        return bool(cue["gain_by_hand"])
    peak = cue.get("source_peak_dbfs")
    return peak is not None and abs(cue.get("gain_db", 0) - round(-1 - peak, 1)) > 0.05


def plan(cues, own_by_file, auto_level=True):
    values = [own_by_file[c["file"]] + c.get("gain_db", 0) for c in cues if own_by_file.get(c["file"]) is not None]
    target = statistics.median(values) if values else None
    rows = []
    for c in cues:
        own, was = own_by_file.get(c["file"]), c.get("gain_db", 0)
        skipped = own is None
        wanted = round(target - own, 1) if not skipped else None
        peak = c.get("source_peak_dbfs")
        ceiling = round(-1 - peak, 1) if peak is not None else None
        by_hand = is_by_hand(c)
        active = bool(auto_level) and not by_hand and not skipped
        capped = active and ceiling is not None and wanted > ceiling
        gain = min(wanted, ceiling) if active and ceiling is not None else wanted if active else was
        rows.append(dict(id=c.get("id"), file=c["file"], own=round(own, 1) if not skipped else None, was=was, wanted=wanted,
                         ceiling=ceiling, gain=gain, capped=capped, by_hand=by_hand, skipped=skipped))
    return dict(target=round(target, 1) if target is not None else None, auto_level=bool(auto_level), cues=rows)


def level(reel, cues, auto_level=True):
    reel = Path(reel)
    measured = reel / "sfx_measured.json"
    hits = json.loads(measured.read_text(encoding="utf-8")).get("hits", []) if measured.is_file() else []
    cached = {h["file"]: h["max_m_lufs"] for h in hits if "max_m_lufs" in h}
    own = {}
    for c in cues:
        file = c["file"]
        if file not in own:
            own[file] = cached[file] if file in cached else own_loudness(reel / "sfx" / file)
    return plan(cues, own, auto_level)


def main(argv=None):
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Match effect levels from the Sound Board Send.")
    ap.add_argument("--reel", required=True)
    reel = workspace()[1] / ap.parse_args(argv).reel
    selection = json.loads((reel / "sound-selection.json").read_text(encoding="utf-8"))
    p = level(reel, selection.get("cues", []), selection.get("auto_level", True))
    print("Target: %s LUFS (maximum momentary); matching %s." % (p["target"], "on" if p["auto_level"] else "off"))
    for c in p["cues"]:
        if c["skipped"]:
            print("%s %s: skipped (too quiet to measure), gain kept at %+.1f dB" % (c["id"], c["file"], c["gain"]))
            continue
        print("%s %s: own %.1f, was %+.1f -> %+.1f dB%s%s" % (
            c["id"], c["file"], c["own"], c["was"], c["gain"],
            " capped" if c["capped"] else "", " (set by hand)" if c["by_hand"] else ""))
    return 0


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main))
