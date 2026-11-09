#!/usr/bin/env python3
"""The reel's QA entry point: run the discovered checks and save the hub's rows.

    python -X utf8 -I check.py <reel_dir> [--phase pre|post|all] [--render <mp4>]

Default phase is pre. Post checks need a render, explicitly given or the newest
renders/* Master - *.mp4. Exit 1 on any block, else 0. Writes work/qa.json
atomically as UTF-8 with LF endings. Review aids write their files in work/qa.

Module contract (H-B6): PHASE = "pre"|"post"; run(ctx) returns a list of
{check, level, msg, where}, optionally at (seconds). ctx is built once and holds
{reel_dir: Path, fps: Fraction|None, cuts: dict|None, beats: list|None,
render: Path|None}. Each saved row also names its module. Libraries are skipped.
"""
import argparse
import importlib.util
import json
import math
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "reel-canvas-build" / "scripts"))
from win_encoding import ensure_utf8_output  # noqa: E402
from fps import as_fraction  # noqa: E402


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def build_context(reel_dir, render=None):
    reel = Path(reel_dir).resolve()
    cuts = read_json(reel / "work/cuts.json")
    beat_map = read_json(reel / "beat-map-selection.json")
    return dict(reel_dir=reel, fps=as_fraction(cuts["fps"]) if cuts is not None else None,
                cuts=cuts, beats=beat_map.get("beats") if beat_map is not None else None, render=render)


def crashed(path):
    return dict(check=path.stem + "-crashed", level="block",
                msg="The %s check broke before it finished. Claude will report this." % path.stem,
                where=path.name, module=path.stem)


def run_checks(ctx, phase):
    """Import in filename order; for all, finish pre checks before any post check."""
    modules, findings = [], []
    for path in sorted(HERE.glob("*.py")):
        if path.name == "check.py":
            continue
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[path.stem] = mod
            spec.loader.exec_module(mod)
            if getattr(mod, "PHASE", None) in ("pre", "post") and callable(getattr(mod, "run", None)):
                modules.append((path, mod))
        except (Exception, SystemExit):
            findings.append(crashed(path))
    for selected in (("pre", "post") if phase == "all" else (phase,)):
        if selected == "post" and ctx["render"] is None:
            continue
        for path, mod in modules:
            if mod.PHASE != selected:
                continue
            try:
                rows = [dict(row, module=path.stem) for row in mod.run(ctx)]
                for row in rows:
                    if not {"check", "level", "msg"} <= row.keys():
                        raise ValueError("The check returned an invalid row")
                    if row["level"] not in ("block", "warn"):
                        row["level"] = "warn"
                    at = row.pop("at", None)
                    if isinstance(at, (int, float)) and not isinstance(at, bool) and math.isfinite(at):
                        row["at"] = round(at, 2)
                findings.extend(rows)
            except (Exception, SystemExit):
                findings.append(crashed(path))
    return findings


def write_report(reel, report):
    work = reel / "work"
    work.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=work,
                                         prefix=".qa-", suffix=".tmp", delete=False) as stream:
            temp = Path(stream.name)
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temp, work / "qa.json")
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reel_dir", type=Path)
    ap.add_argument("--phase", choices=("pre", "post", "all"), default="pre")
    ap.add_argument("--render", type=Path)
    args = ap.parse_args(argv)
    reel = args.reel_dir.resolve()
    render = args.render.resolve() if args.render is not None else None
    if render is None and args.phase in ("post", "all"):
        candidates = [p for p in (reel / "renders").glob("* Master - *.mp4") if p.is_file()]
        render = max(candidates, key=lambda p: (p.stat().st_mtime_ns, p.name), default=None)
    if render is not None and not render.is_file():
        render = None
    findings = []
    if args.phase in ("post", "all") and render is None:
        findings.append(dict(check="render-missing", level="block",
                             msg="No finished video to check yet. Make the final video first, then run the check again.",
                             where="renders", module="check"))
    post_ran = False
    try:
        ctx = build_context(reel, render)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        findings.append(dict(check="inputs-unreadable", level="block",
                             msg="The cut list or Beat Map could not be read. Restore these files and run QA again.",
                             where="work/cuts.json, beat-map-selection.json", module="check"))
    else:
        findings.extend(run_checks(ctx, args.phase))
        post_ran = args.phase in ("post", "all") and render is not None
    if not findings:
        findings = [dict(check="all-clear", level="pass", msg="Every check passed.", module="check")]
    blocks = sum(row["level"] == "block" for row in findings)
    warns = sum(row["level"] == "warn" for row in findings)
    report = dict(phase=args.phase, ran_at=datetime.now().astimezone().isoformat(),
                  render=render.name if render is not None else None, blocks=blocks, warns=warns, checks=findings)
    if post_ran:
        try:
            index = reel / "work/qa/index.json"
            if index.is_file() and index.stat().st_mtime_ns >= render.stat().st_mtime_ns:
                report["aids"] = read_json(index)
        except (OSError, ValueError):
            pass  # Optional review tooling must not prevent the QA report.
    write_report(reel, report)
    print("QA: %d blocks, %d warnings (%s)" % (blocks, warns, args.phase))
    for row in findings:
        if row["level"] in ("block", "warn"):
            print("%s  %s  %s" % (row["level"].upper(), row["check"], row["msg"]))
    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
