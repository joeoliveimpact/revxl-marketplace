#!/usr/bin/env python3
"""Run the real gaps.py once per consecutive take run; merge without joining across recordings.

--take N:folder:edit_map.json may contain Windows drive letters.
--protect accepts N:from:to:cap for mixed takes (unqualified ranges apply to every take).
"""
import argparse, json, math, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE.parents[1] / "_shared/checks"))
from win_encoding import ensure_utf8_output
from cut_timing import GUARD_MS
import footage_check


def lookup(timemap, out_f):
    """Map fps's last due joined frame into its half-open source segment.

    fps rounds each incoming timestamp j/speed to nearest (half away from zero),
    then keeps the last frame whose rounded timestamp is <= out_f. Thus
    j < (out_f + 0.5) * speed, capped at the final joined frame at EOF.
    Output segment bounds describe the cut, not where fps changes source files.
    """
    segs = timemap["segments"]
    if not segs or not 0 <= out_f < segs[-1]["out_out_f"]:
        raise ValueError("that output frame is outside the reel")
    total = sum(s["src_out_f"] - s["src_in_f"] for s in segs)
    j = min(total - 1, math.ceil((out_f + .5) * timemap["speed"]) - 1)
    before = 0
    for s in timemap["segments"]:
        length = s["src_out_f"] - s["src_in_f"]
        if before <= j < before + length:
            return s["file"], s["src_in_f"] + j - before
        before += length
    raise ValueError("that output frame is outside the reel")


def write_timemap(work, cuts, raw=None, reel_dir=None, take=1):
    work = Path(work)
    reel = Path(reel_dir) if reel_dir is not None else work.parent
    ledger = footage_check.rows(reel)
    resolved = footage_check.resolve_rows(reel, ledger)
    hashes = {footage_check.normalized(path): r["sha256"] for r, path in resolved}
    takes, segs = cuts.get("takes") or {}, []
    for s in cuts["segments"]:
        n = s.get("take", take)
        file = takes[str(n)]["raw"] if takes else raw
        segs.append(dict(out_in_f=s["out_in_f"], out_out_f=s["out_out_f"], take=n, file=file,
                         sha256=hashes.get(footage_check.normalized(footage_check.asset(reel, file, resolved))) if file else None,
                         src_in_f=s["src_in_f"], src_out_f=s["src_out_f"]))
    doc = dict(fps=cuts["fps"], speed=cuts.get("speed", 1.0), segments=segs)
    (work / "timemap.json").write_bytes((json.dumps(doc, indent=1) + "\n").encode("utf-8"))
    return doc


def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("work")
    ap.add_argument("--edl", required=True)
    ap.add_argument("--take", action="append", required=True)
    for name, default in (("internal", .150), ("join", .150), ("beat-join", .320), ("lead", .080),
                          ("tail", .100), ("guard", GUARD_MS / 1000), ("min-island", .500), ("min-gap", .100)):
        ap.add_argument("--" + name, type=float, default=default)
    ap.add_argument("--beat", type=float)
    ap.add_argument("--nudge", type=float, default=0.)
    ap.add_argument("--speed", type=float, default=1.)
    ap.add_argument("--protect", default="")
    ap.add_argument("--hold", default="")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    reel = work.parent
    if not math.isfinite(a.speed) or not .5 <= a.speed <= 2:
        raise ValueError("choose a speed from 0.5 to 2.0")
    sources, probes = {}, {}
    for spec in a.take:
        match = re.fullmatch(r"(\d+):(.+?):((?:[A-Za-z]:)?[^:]+\.json)", spec)
        if not match:
            raise ValueError("each --take needs N:folder:edit_map.json")
        n, folder, em = match.groups()
        n = str(int(n))
        if n in sources:
            raise ValueError("each take must be named once")
        folder, em = Path(folder).resolve(), Path(em).resolve()
        if em.parent != folder:
            raise ValueError("a take's work folder must hold its edit map")
        p = json.loads((folder / "probe.json").read_text(encoding="utf-8"))
        probes[n] = p
        sources[n] = dict(raw=p["input"], work=folder.relative_to(reel).as_posix(), edit_map=em.relative_to(reel).as_posix())
    rates = [float(p["fps"]["measured_fps"]) for p in probes.values()]
    # ponytail: one frame rate per reel; per-take fps conform when a client needs it
    if any(not math.isfinite(r) or r <= 0 for r in rates) or max(rates) / min(rates) > 1.005 + 1e-12:
        raise ValueError("these recordings have different frame rates (over 0.5% apart); use one frame rate per reel")
    if len({p["out_rate"] for p in probes.values()}) != 1:
        raise ValueError("these takes need the same master frame rate; probe them again with one --out-rate")
    edl = json.loads(Path(a.edl).read_text(encoding="utf-8"))
    runs = []
    for entry in edl:
        n = str(entry.get("take", 1))
        if n not in sources:
            raise ValueError("the cut names take %s but no --take supplies it" % n)
        if not runs or runs[-1][0] != n:
            runs.append((n, []))
        runs[-1][1].append(entry)
    if not runs:
        raise ValueError("the selection emits no cuts")
    protected = {n: [] for n in sources}
    for part in filter(None, a.protect.split(",")):
        fields = part.split(":")
        if len(fields) == 4:
            n, *span = fields
            protected[n].append(":".join(span))
        elif len(fields) == 3:
            for spans in protected.values():
                spans.append(part)
        else:
            raise ValueError("a protected pause needs take:from:to:cap")
    work.mkdir(parents=True, exist_ok=True)
    combined, offset, source, fps, speed = [], 0, 0, None, None
    for k, (n, entries) in enumerate(runs, 1):
        run = work / "runs" / ("r%02d" % k)
        run.mkdir(parents=True, exist_ok=True)
        folder = reel / sources[n]["work"]
        for name in ("probe.json", "envelope.json"):
            shutil.copyfile(folder / name, run / name)
        (run / "edl.json").write_bytes(json.dumps(entries, indent=1).encode("utf-8"))
        cmd = [sys.executable, "-X", "utf8", "-I", str(HERE / "gaps.py"), str(run), "--edl", str(run / "edl.json"),
               "--words", str(reel / sources[n]["edit_map"]), "--speed", str(a.speed)]
        for name in ("internal", "join", "beat-join", "lead", "tail", "guard", "min-island", "min-gap"):
            cmd += ["--" + name, str(getattr(a, name.replace("-", "_")))]
        if a.beat is not None:
            cmd += ["--beat", str(a.beat)]
        if a.nudge:
            cmd += ["--nudge", str(a.nudge)]
        if protected[n]:
            cmd += ["--protect", ",".join(protected[n])]
        if a.hold:
            cmd += ["--hold", a.hold]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode:
            raise ValueError(next(iter((p.stderr or p.stdout).strip().splitlines()), "the gap step stopped"))
        c = json.loads((run / "cuts.json").read_text(encoding="utf-8"))
        if fps is not None and (fps != c["fps"] or speed != c["speed"]):
            raise ValueError("the take runs have different speeds or master frame rates")
        fps, speed = c["fps"], c["speed"]
        # out frames on the cumulative SOURCE frames, gaps.py's own single-take rule (round(S/speed)), so the merged
        # list lands where the render's one joined re-time puts each cut; per-run offsets drift a frame at speed
        for s in c["segments"]:
            length = s["src_out_f"] - s["src_in_f"]
            combined.append(dict(s, take=int(n), out_in_f=round(source / speed), out_out_f=round((source + length) / speed)))
            source += length
        offset = combined[-1]["out_out_f"] if combined else 0
    cuts = dict(fps=fps, speed=speed, segments=combined,
                takes={n: {k: sources[n][k] for k in ("raw", "work")} for n in sorted(sources, key=int)})
    (work / "cuts.json").write_bytes((json.dumps(cuts, indent=1) + "\n").encode("utf-8"))
    for name in ("gap-plan.txt", "listen.txt"):
        text = "\n\n".join("Take %s, run %d\n%s" % (n, k, (work / "runs" / ("r%02d" % k) / name).read_text(encoding="utf-8"))
                             for k, (n, _) in enumerate(runs, 1))
        (work / name).write_bytes(text.encode("utf-8"))
    write_timemap(work, cuts, reel_dir=reel)
    print("wrote %s: %d take runs, %d frames; timemap.json records every source" % (work / "cuts.json", len(runs), offset))
    # Stage 3's boundary audit reads segments.json: a mixed cut has one per run, so a leftover single-take
    # work/segments.json would audit an old cut; remove it and name the per-run audits instead
    (work / "segments.json").unlink(missing_ok=True)
    print("boundary audits (Stage 3, one per run):")
    for k, (n, _) in enumerate(runs, 1):
        print('<editor python> -X utf8 -I "%s" "%s" "%s"' % ((HERE / "boundary_audit.py").as_posix(),
              (work / "runs" / ("r%02d" % k)).as_posix(), (reel / sources[n]["edit_map"]).as_posix()))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e).strip().splitlines()[0] or "the take step could not finish", file=sys.stderr)
        sys.exit(2)
