#!/usr/bin/env python3
"""Stage 2 on the no-board path (references/no-board-path.md): rank the trim candidates by DIRECTION.

    <editor python> -X utf8 -I line_score.py <reel_dir> [--labels work/line-labels.json]

This serves the no-board path only: on the board path the client picks lines on the Cut Board.
Reads : <reel>/work/line-labels.json, written by Claude, one record per trim candidate:
        {"lines": [{"id", "text", "src_in", "src_out", "direction": "forward"|"backward"|"neutral", "why"}]}
        A relative --labels path is read from the reel folder.
Writes: <reel>/work/line-table.md and prints it: a ranked table (rank, id, text, direction, why, verdict).
        backward -> "free cut", neutral -> "your call", forward -> "keep: it opens a loop the viewer stays for".
        Free cuts first, then your-call, then keeps; ties keep the input order.

Only backward-facing lines (they restate something already said) are free cuts. A forward line opens a loop the
viewer stays for, even when it carries no information, so it is never a free cut.
Never auto-applies: it writes no EDL, no cut selection and no other file. Then stop for the client's pick.
Exit 0 = table written, 2 = refused (missing or bad labels file; a line with no id, no direction or no why, an
unknown direction, or a repeated id). A refusal names the line ids and writes nothing.
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402

VERDICT = {"backward": "free cut", "neutral": "your call", "forward": "keep: it opens a loop the viewer stays for"}
ORDER = {"backward": 0, "neutral": 1, "forward": 2}


def problems(lines):
    """Plain-English reasons to refuse, one per problem, each naming the line id(s)."""
    out, seen, dup = [], set(), []
    for k, ln in enumerate(lines, 1):
        if not isinstance(ln, dict):
            out.append("line #%d is not a record" % k); continue
        lid = "" if ln.get("id") is None else str(ln["id"]).strip()
        name = lid or "line #%d" % k
        if not lid:
            out.append("%s has no id" % name)
        elif lid in seen and lid not in dup:
            dup.append(lid)
        seen.add(lid)
        d = ln.get("direction")
        if not str(d or "").strip():
            out.append("%s has no direction" % name)
        elif not isinstance(d, str) or d not in VERDICT:
            out.append("%s has an unknown direction %r (use forward, backward or neutral)" % (name, d))
        if not str(ln.get("why") or "").strip():
            out.append("%s has no why" % name)
    if dup:
        out.append("these ids repeat: %s" % ", ".join(dup))
    return out


def cell(v):
    return " ".join(str(v if v is not None else "").split()).replace("|", "\\|")


def table(lines):
    ranked = sorted(lines, key=lambda ln: ORDER[ln["direction"]])   # sorted() is stable: ties keep input order
    rows = ["| rank | id | text | direction | why | verdict |", "|---|---|---|---|---|---|"]
    for r, ln in enumerate(ranked, 1):
        rows.append("| %d | %s | %s | %s | %s | %s |" % (r, cell(ln["id"]), cell(ln.get("text")), ln["direction"],
                                                       cell(ln["why"]), VERDICT[ln["direction"]]))
    return "\n".join(rows) + "\n"


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Rank no-board trim candidates by direction (never auto-applies).")
    ap.add_argument("reel_dir")
    ap.add_argument("--labels", default="work/line-labels.json")
    a = ap.parse_args()
    reel = Path(a.reel_dir)
    src = reel / a.labels
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except OSError:
        print("refused: can't read the labels file %s. Write the trim candidates and their direction labels "
              "there first." % src, file=sys.stderr)
        return 2
    except ValueError as e:
        print("refused: %s is not valid JSON (%s)." % (src, e), file=sys.stderr)
        return 2
    lines = data.get("lines") if isinstance(data, dict) else None
    if not isinstance(lines, list) or not lines:
        print('refused: %s needs a non-empty "lines" list.' % src, file=sys.stderr)
        return 2
    bad = problems(lines)
    if bad:
        print("refused, nothing written. Fix these lines in %s:\n  - %s" % (src, "\n  - ".join(bad)), file=sys.stderr)
        return 2
    md = table(lines)
    out = reel / "work" / "line-table.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(md.encode("utf-8"))
    print(md + "\nwrote %s. Nothing is applied: stop for the client's pick." % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
