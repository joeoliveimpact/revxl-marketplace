#!/usr/bin/env python3
"""Stage 3/4 gate, source coordinates: every segment boundary against the words AND the envelope.

    python boundary_audit.py <work dir> <edit map.json>

Fails (exit 1) on any boundary that lies INSIDE an aligned word, or that has speech energy above
`--hot` dB within `--reach` s just OUTSIDE the cut (a word edge the cut amputated). The transcript
round-trip cannot see either (a sheared tail still transcribes); the envelope alone cannot name
the word. Exit 0 when every boundary is clean.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("work"); ap.add_argument("editmap")
    ap.add_argument("--hot", type=float, default=-38.0, help="dB: energy this loud just outside a cut is a word edge")
    ap.add_argument("--reach", type=float, default=0.08, help="s: how far outside the cut to look")
    a = ap.parse_args()
    W = Path(a.work)
    env = json.loads((W / "envelope.json").read_text(encoding="utf-8")); db, win = env["db"], env["win_s"]
    segs = json.loads((W / "segments.json").read_text(encoding="utf-8"))
    em = json.loads(Path(a.editmap).read_text(encoding="utf-8"))
    words = [w for w in em["words"] if w.get("status") != "unresolved"]

    def pk(x, y):
        lo, hi = max(0, int(x / win)), min(len(db) - 1, int(y / win))
        return max(db[lo:hi + 1]) if hi >= lo else -120.0

    bad = []
    for k, (s0, s1) in enumerate(segs):
        for side, t, out in (("IN", s0, pk(s0 - a.reach, s0 - 0.005)), ("OUT", s1, pk(s1 + 0.005, s1 + a.reach))):
            w = next((w for w in words if w["start"] < t < w["end"]), None)
            if w:
                bad.append("seg%02d %-3s %8.3f INSIDE '%s' [%s-%s]" % (k, side, t, w["word"].strip(), w["start"], w["end"]))
            elif out > a.hot:
                near = min(words, key=lambda w: min(abs(w["start"] - t), abs(w["end"] - t)))
                bad.append("seg%02d %-3s %8.3f %5.1f dB just outside (nearest '%s' %s-%s)" % (k, side, t, out, near["word"].strip(), near["start"], near["end"]))
    print("boundaries %d | flagged %d" % (2 * len(segs), len(bad)))
    print("\n".join("  " + b for b in bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
