#!/usr/bin/env python3
# Rebuilt from Shorts Studio, scripts/qa.py (its "cuts remove only silence" and "no murmur between words" checks,
# :71-93). MIT License, Copyright (c) 2026 Claude Video Studio contributors (full text in LICENSES/NOTICE).
# changed: runs on the plan, not a rendered final: cuts.json frames at its own fps (not 30), edl.json, probe.py's
# 10 ms source envelope and S3's edit map; only silence trims inside one EDL cut are checked (the client's own edits
# between cuts are skipped); murmurs are searched in the kept audio; standalone script with --json and an exit code.
"""Cut QA - did the gap plan remove only silence, and is any murmur left in the kept audio?

    python cut_qa.py work/ --words work/edit_map.json [--edl work/edl.json] [--json work/cut-qa.json]

Reads work/cuts.json (whole frames at its fps), the EDL (default work/edl.json), work/envelope.json (probe.py's
10 ms dB windows of the chosen track) and the source edit map. All levels are against p90, the 90th percentile of
the whole envelope.

silence-only  A removed span that lies inside one EDL cut is a silence trim gaps.py made: it FAILS when 4 or more
              of its windows are above p90 - 18 dB (40 ms of voice). Spans between EDL cuts are the client's own
              edits and are skipped.
murmur        Inside the kept audio, a run of 28+ windows (0.28 s) between p90 - 24 and p90 - 9 dB is flagged when
              no edit-map word covers more than half of it, or a covering word is over 0.8 s long.

Each line gives the source time and the output frame. Exit 0 = clean, 1 = a check failed or a murmur was flagged,
2 = could not read the inputs.
"""
import argparse, json, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402

VOICE_DB, VOICE_WINDOWS = 18.0, 4                  # removed audio: windows above p90-18 dB; 4 of them = 40 ms
MID_LO, MID_HI, MID_WINDOWS = 24.0, 9.0, 28        # murmur band p90-24 .. p90-9 dB, 28 windows = 0.28 s
COVER, LONG_WORD = 0.5, 0.8


def removed_spans(segs, edl, fps):
    """(a, b, out_frame) in source seconds for everything the cut list drops inside the EDL's range."""
    out, t, f = [], edl[0]["src_in"], 0
    for s in segs:
        a = s["src_in_f"] / fps
        if a > t + 1e-9:
            out.append((t, a, f))
        t, f = max(t, s["src_out_f"] / fps), s["out_out_f"]
    if edl[-1]["src_out"] > t + 1e-9:
        out.append((t, edl[-1]["src_out"], f))
    return out


def check(cuts, edl, env, words):
    fps, speed, segs = cuts["fps"], cuts["speed"], cuts["segments"]
    db, win = np.asarray(env["db"], dtype=float), env["win_s"]
    p90 = float(np.percentile(db, 90))
    half = 0.5 / fps                                # a snapped edge sits up to half a frame from the EDL's
    idx = lambda t: max(0, min(len(db), int(round(t / win))))
    R = []

    for a, b, f in removed_spans(segs, edl, fps):
        inside = any(c["src_in"] - half <= a and b <= c["src_out"] + half for c in edl)
        r = dict(check="silence-only", src=[round(a, 3), round(b, 3)], out_frame=f)
        if not inside:
            R.append(dict(r, result="skip", why="between EDL cuts (the client's own edit)"))
            continue
        n = int((db[idx(a):idx(b)] > p90 - VOICE_DB).sum())
        R.append(dict(r, result="fail" if n >= VOICE_WINDOWS else "pass", voice_windows=n))

    mid = (db > p90 - MID_LO) & (db < p90 - MID_HI)
    for s in segs:
        lo, hi = idx(s["src_in_f"] / fps), idx(s["src_out_f"] / fps)
        k = lo
        while k < hi:
            if not mid[k]:
                k += 1
                continue
            j = k
            while j < hi and mid[j]:
                j += 1
            if j - k >= MID_WINDOWS:
                a, b = k * win, j * win
                cov = [w for w in words if min(b, w["end"]) - max(a, w["start"]) > COVER * (b - a)]
                if not cov or any(w["end"] - w["start"] > LONG_WORD for w in cov):
                    R.append(dict(check="murmur", result="flag", src=[round(a, 3), round(b, 3)],
                                  out_frame=s["out_in_f"] + round((a * fps - s["src_in_f"]) / speed),
                                  words=[w["word"].strip() for w in cov]))
            k = j
    return R, p90


def line(r, p90):
    a, b = r["src"]
    if r["check"] == "murmur":
        why = ("covered by a word over %.1f s: %s" % (LONG_WORD, " ".join(r["words"])) if r["words"]
               else "no word covers it")
        return "FLAG murmur: %.2f s of quiet voice at source %.3f-%.3f s, out frame %d (%s)" % (
            b - a, a, b, r["out_frame"], why)
    if r["result"] == "skip":
        return "SKIP silence-only: %.3f-%.3f s removed at out frame %d lies %s" % (a, b, r["out_frame"], r["why"])
    return "%s silence-only: %.3f-%.3f s removed at out frame %d, %d ms over %.1f dB" % (
        r["result"].upper(), a, b, r["out_frame"], 10 * r["voice_windows"], p90 - VOICE_DB)


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Cut QA: silence-only trims and murmurs.")
    ap.add_argument("work")
    ap.add_argument("--words", required=True, help="the source edit map (S3's edit_map.json)")
    ap.add_argument("--edl", help="default work/edl.json")
    ap.add_argument("--json", help="write the results here")
    a = ap.parse_args()
    w = Path(a.work)
    try:
        cuts = json.loads((w / "cuts.json").read_text(encoding="utf-8"))
        edl = json.loads(Path(a.edl or w / "edl.json").read_text(encoding="utf-8"))
        env = json.loads((w / "envelope.json").read_text(encoding="utf-8"))
        em = json.loads(Path(a.words).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("cut QA could not read its inputs: %s" % e, file=sys.stderr)
        return 2
    if not cuts.get("segments") or not edl:
        print("cut QA needs a cuts.json with segments and an EDL with cuts", file=sys.stderr)
        return 2
    words = [x for x in em["words"] if x.get("status") != "unresolved"]
    R, p90 = check(cuts, edl, env, words)
    print("cut QA: %d removed span(s), p90 %.1f dB, %s fps" % (sum(r["check"] == "silence-only" for r in R), p90,
                                                              cuts["fps"]))
    for r in R:
        print(line(r, p90))
    bad = [r for r in R if r["result"] in ("fail", "flag")]
    if a.json:
        Path(a.json).write_text(json.dumps({"p90_db": round(p90, 2), "results": R}, indent=1), encoding="utf-8")
    print("cut QA: %d problem(s)" % len(bad) if bad else "cut QA: clean")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
