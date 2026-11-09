#!/usr/bin/env python3
"""Stage 3/4 gate, source coordinates: every segment boundary against the words AND the envelope.

    python boundary_audit.py <work dir> <edit map.json>

Fails (exit 1) on any boundary that lies INSIDE an aligned word, or that has speech energy above
the take's calibrated speech floor (probe.json, overridden by `--hot`) within `--reach` s just OUTSIDE
the cut (a word edge the cut amputated). A flagged run prints the concrete re-derive step. The transcript
round-trip cannot see either (a sheared tail still transcribes); the envelope alone cannot name
the word. Exit 0 when every boundary is clean.
Only windows shortened by an adjacent dropped word use the take's sustained-speech run instead of a peak.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import word_map  # noqa: E402


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("work"); ap.add_argument("editmap")
    ap.add_argument("--hot", type=float, default=None, help="dB: override the take's calibrated speech floor")
    ap.add_argument("--edl", default=None, help="default: <work>/edl.json; used for re-derive instructions")
    ap.add_argument("--reach", type=float, default=0.08, help="s: how far outside the cut to look")
    a = ap.parse_args()
    W = Path(a.work)
    probe = json.loads((W / "probe.json").read_text(encoding="utf-8")) if (W / "probe.json").exists() else {}
    need = (probe.get("calibration") or {}).get("speech_run_windows", 6)
    source = "--hot"
    if a.hot is None:
        a.hot = (probe.get("calibration") or {}).get("speech_db")
        source = "this take's calibration"
        if a.hot is None:
            a.hot, source = -38.0, "default, no calibration found"
    env = json.loads((W / "envelope.json").read_text(encoding="utf-8")); db, win = env["db"], env["win_s"]
    segs = json.loads((W / "segments.json").read_text(encoding="utf-8"))
    em = json.loads(Path(a.editmap).read_text(encoding="utf-8"))
    words = [w for w in em["words"] if w.get("status") != "unresolved"]
    kept = [w for w in words if any(word_map.in_span(w["start"], s0, s1) for s0, s1 in segs)]
    dropped = [w for w in em["words"] if w.get("status") == "unresolved"
               or not any(word_map.in_span(w["start"], s0, s1) for s0, s1 in segs)]

    def pk(x, y):
        if x > y:
            return -120.0
        lo, hi = max(0, int(x / win)), min(len(db) - 1, int(y / win))
        return max(db[lo:hi + 1]) if hi >= lo else -120.0

    def sustained(x, y):
        if x > y:
            return False
        lo, hi = max(0, int(x / win)), min(len(db) - 1, int(y / win))
        run = 0
        for d in db[lo:hi + 1]:
            run = run + 1 if d > a.hot else 0
            if run >= need:
                return True
        return False

    bad, edges = [], []
    for k, (s0, s1) in enumerate(segs):
        for side, t in (("IN", s0), ("OUT", s1)):
            shortened = False
            if side == "OUT":
                lo, hi = t + 0.005, t + a.reach
                omitted = [w["start"] for w in dropped if t - 0.010 <= w["start"] <= t + a.reach]
                if omitted and not any(w["start"] < t + a.reach and w["end"] > t for w in kept):
                    hi = min(omitted) - 0.005
                    shortened = True
            else:
                lo, hi = t - a.reach, t - 0.005
                omitted = [w["end"] for w in dropped if t - a.reach <= w["end"] <= t + 0.010]
                if omitted and not any(w["start"] < t and w["end"] > t - a.reach for w in kept):
                    lo = max(omitted) + 0.005
                    shortened = True
            out = pk(lo, hi)
            w = next((w for w in words if w["start"] < t < w["end"]), None)
            if w:
                bad.append("seg%02d %-3s %8.3f INSIDE '%s' [%s-%s]" % (k, side, t, w["word"].strip(), w["start"], w["end"]))
                edges.append((k, t))
            elif out > a.hot and (not shortened or sustained(lo, hi)):
                near = min(words, key=lambda w: min(abs(w["start"] - t), abs(w["end"] - t)))
                bad.append("seg%02d %-3s %8.3f %5.1f dB just outside (nearest '%s' %s-%s)" % (k, side, t, out, near["word"].strip(), near["start"], near["end"]))
                edges.append((k, t))
    print("boundaries %d | flagged %d | level %.1f dB (%s)" % (2 * len(segs), len(bad), a.hot, source))
    print("\n".join("  " + b for b in bad))
    if bad:
        edl_p = Path(a.edl) if a.edl else W / "edl.json"
        if not edl_p.exists():
            spans = list(dict.fromkeys("%.3f:%.3f" % tuple(segs[k]) for k, _ in edges))
            print("No EDL found at %s: re-run Stage 4's gaps.py line with --hold %s for each flagged segment, "
                  "then run this audit again." % (edl_p, ",".join(spans)))
        else:
            edl = json.loads(edl_p.read_text(encoding="utf-8"))
            holds, lines, board_cut = [], [], False
            for _, t in edges:
                cut = next((c for c in edl if c["src_in"] + 0.15 < t < c["src_out"] - 0.15), None)
                if cut is not None:
                    span = "%.3f:%.3f" % (cut["src_in"], cut["src_out"])
                    if span not in holds:
                        holds.append(span)
                else:
                    board_cut = True
                    cut = min(edl, key=lambda c: min(abs(c["src_in"] - t), abs(c["src_out"] - t))) if edl else {}
                    if cut.get("line") is not None and cut["line"] not in lines:
                        lines.append(cut["line"])
            if holds:
                print("To re-derive: re-run Stage 4's gaps.py line with these cuts held whole (append to any --hold already on it):")
                print("  --hold " + ",".join(holds))
                print("then run this audit again.")
            if board_cut:
                label = " (line %s)" % ", ".join(map(str, lines)) if lines else ""
                print("A board cut sits on speech%s: rebuild that board and ask the client for a new Send on those lines." % label)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
