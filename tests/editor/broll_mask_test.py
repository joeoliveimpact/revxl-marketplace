"""BL.2 privacy checks. Run --data-only, or one heavy --case under the heavy lock.

Uses the installed tools from EDITOR_SE_HOME. Fixtures are disposable; no fonts,
image packages or browser are needed for the five data cases.
"""
import argparse
import contextlib
import hashlib
import importlib
import io
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_engine_test as engine

sys.path.insert(0, str(engine.SCRIPTS))
import beat_schema

BOX_PX = (120, 900, 360, 240)
CONTROL = (600, 900, 360, 240)
BOX = dict(x=120 / 1080, y=900 / 1920, w=360 / 1080, h=240 / 1920, kind="blur")
DATA = ("schema", "masked-copy", "range", "check-mutant", "still")
HEAVY = ("render-preview", "render-master", "render-trials", "render-handoff-overlay", "fail-closed")


def mask_mod():
    return importlib.import_module("broll_mask")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, data=None):
    result = subprocess.run([str(a) for a in args], input=data, capture_output=True,
                            env=engine.rt.python_env(), timeout=300)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")[-1000:]
    return result.stdout


def pattern():
    """Two identical fields of 6-10 pixel glyph-like strokes, made with bytes only."""
    frame = bytearray([128]) * (1080 * 1920)
    for x0, y0, w, h in (BOX_PX, CONTROL):
        for y in range(h):
            for x in range(w):
                ink = (x % 32 < 8 or y % 40 < 6 or (x % 32 < 24 and 16 <= y % 40 < 24))
                frame[(y0 + y) * 1080 + x0 + x] = 0 if ink else 255
    return bytes(frame)


def clip(reel):
    target = reel / "broll/ingested/text.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    # Loop one raw frame, so the fixture stays small in memory and on disk.
    run([engine.rt.tool("ffmpeg"), "-v", "error", "-y", "-f", "rawvideo", "-pixel_format", "gray",
         "-video_size", "1080x1920", "-framerate", "25", "-i", "pipe:0", "-vf", "loop=99:1:0",
         "-frames:v", "100", "-c:v", "libx264", "-crf", "8", "-pix_fmt", "yuv420p", "-threads", "1", target], pattern())
    return target


def doc():
    return dict(schema=1, reel=engine.REEL, fps=25, words=beat_schema.DEFAULT_WORDS,
                beats=[engine.beat("b_001", 0, 100, 0, 7)], word_marks=[], proposed={}, notes={}, needs="", sent_at=None)


def bad_masks():
    yield "object", [], "object"
    yield "clip id", {"b_001": []}, "clip"
    yield "list", {"f03": {}}, "list"
    yield "box object", {"f03": [None]}, "object"
    yield "missing", {"f03": [{"x": 0}]}, "missing"
    for changes, line in (({"extra": 1}, "unknown"), ({"kind": "pixel"}, "blur or fill"),
                          ({"x": True}, "numbers"), ({"y": float("nan")}, "numbers"),
                          ({"w": 0}, "positive"), ({"h": -1}, "positive"),
                          ({"x": -0.1}, "inside"), ({"y": -0.1}, "inside"),
                          ({"w": 1}, "inside"), ({"h": 1}, "inside"),
                          ({"from": 1}, "both"), ({"to": 2}, "both"),
                          ({"from": -1, "to": 2}, "before"), ({"from": 2, "to": 2}, "before"),
                          ({"from": 3, "to": 2}, "before"), ({"from": False, "to": 2}, "before"),
                          ({"from": 1, "to": float("inf")}, "before")):
        yield repr(changes), {"f03": [dict(BOX, **changes)]}, line


def schema_case(root):
    base = doc()
    assert not beat_schema.beat_map_problems(base)
    for masks in ({}, {"f03": []}, {"f03": [BOX, dict(BOX, kind="fill", **{"from": 1, "to": 2})]},
                  {"f03": [dict(BOX, x=0, y=0, w=1.0000005, h=1)]}):
        assert not beat_schema.beat_map_problems(dict(base, broll_masks=masks))
    for name, masks, line in bad_masks():
        problems = beat_schema.beat_map_problems(dict(base, broll_masks=masks))
        assert any(line in p for p in problems), (name, line, problems)


def data_case(name, root):
    if name == "schema":
        return schema_case(root)
    reel = root / name
    reel.mkdir()
    source = clip(reel)
    if name == "still":
        return still_case(reel, source)
    sent = doc()
    sent["beats"][0]["broll"] = dict(src=source.relative_to(reel).as_posix(), ledger_id="f03", fit="cover", **{"in": 0, "out": 100})
    sent["broll_masks"] = {"f03": [BOX]}
    engine.wj(reel / "beat-map-selection.json", sent)
    mask = mask_mod()
    rel = source.relative_to(reel).as_posix()
    assert mask.masked_copy(reel, rel, []) == source
    if name == "check-mutant":
        problems = mask.check(reel, rel, [BOX], source)
        assert problems and "Box 1 on clip f03" in problems[0] and "still readable" in problems[0], problems
        return
    boxes = [dict(BOX, kind="fill", **{"from": 1, "to": 2})] if name == "range" else [BOX]
    target = mask.masked_copy(reel, rel, boxes)
    assert target.is_file()
    assert not mask.check(reel, rel, boxes, target)
    if name == "range":
        for t in (1.2, 1.8):
            pixels = mask.gray_region(target, BOX_PX, t)
            assert sum(pixels) / len(pixels) <= 16
        for t in (0.4, 2.6):
            before = mask.edge_energy_of(source, BOX_PX, t)
            assert abs(mask.edge_energy_of(target, BOX_PX, t) / before - 1) <= .1
        return
    first_hash, stamp = digest(target), target.stat().st_mtime_ns
    assert mask.masked_copy(reel, rel, boxes) == target
    assert target.stat().st_mtime_ns == stamp and digest(target) == first_hash
    target.unlink()  # A fresh encode must also be identical, not just a cache hit.
    assert digest(mask.masked_copy(reel, rel, boxes)) == first_hash
    before, after = (mask.edge_energy_of(p, BOX_PX, 1.5) for p in (source, target))
    assert after <= before * .1 or after <= 1.5, (before, after)
    before, after = (mask.edge_energy_of(p, CONTROL, 1.5) for p in (source, target))
    assert abs(after / before - 1) <= .1, (before, after)
    target.write_bytes(b"interrupted")
    assert digest(mask.masked_copy(reel, rel, boxes)) == first_hash


def still_case(reel, source):
    ingest = engine.load("broll_ingest", engine.PLUGIN / "skills/reel-broll/scripts")
    (reel / "work").mkdir()
    engine.wj(reel / "work/cuts.json", dict(fps=25, takes={"1": {"raw": str(source)}},
              segments=[dict(take=1, src_in_f=0, src_out_f=100, out_in_f=0, out_out_f=100)]))
    image = reel / "broll/slide.png"
    run([engine.rt.tool("ffmpeg"), "-v", "error", "-i", source, "-frames:v", "1", image])
    for frames in (75, 250):
        if frames == 75:
            engine.wj(reel / "beat-map.state.json", {"beats": [dict(start_f=0, end_f=25), dict(start_f=25, end_f=100)]})
        else:
            (reel / "beat-map.state.json").unlink()
            (reel / "broll/ingested/slide.mp4").unlink()
            (reel / "footage/ledger.json").unlink()
        assert ingest.ingest(reel) == 0
        record = json.loads((reel / "broll/clips.json").read_text())["clips"][0]
        assert record["still"] is True and record["name"] == image.name
        assert record["src"] == "broll/ingested/slide.mp4" and record["frames"] == frames, record
        row = next(r for r in ingest.footage_check.rows(reel) if r["id"] == record["ledger_id"])
        assert row["path"] == record["src"] and row["sha256"] == digest(reel / record["src"])
        assert (record["width"], record["height"]) == (1080, 1920)
    (reel / "broll/broken.png").write_bytes(b"broken image")
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        assert ingest.ingest(reel) == 0  # Unreadable own footage is skipped, as for videos.
    assert "skipped broken.png: the video could not be read or prepared" in said.getvalue()
    records = json.loads((reel / "broll/clips.json").read_text())["clips"]
    assert all(r["name"] != "broken.png" for r in records)


def fixture(root):
    ws, reel = engine.make_reel(root, src=engine.STATIC_SRC, scene=False)
    source = clip(reel)
    compose = engine.compose_mod()
    ident = compose.footage_check.add(reel, source, role="broll", origin="own", licence="own")
    master = reel / "work/renders/master-100x.mp4"
    compose.footage_check.add(reel, master, role="aroll", origin="own", licence="own")
    engine.wj(reel / "work/probe.json", {"input": str(master)})
    beat = engine.beat("b_001", 0, 100, 0, 7)
    beat["broll"] = dict(src=source.relative_to(reel).as_posix(), ledger_id=ident, fit="cover", **{"in": 0, "out": 100})
    engine.write_send(reel, [beat], 25)
    sent = json.loads((reel / compose.SEND).read_text())
    sent["broll_masks"] = {ident: [BOX]}
    engine.wj(reel / compose.SEND, sent)
    return reel, compose, sent


def master_ok(reel, compose):
    preview = engine.dummy_preview(reel)
    engine.wj(reel / compose.OK_FILE, {"ok_at": datetime.now().astimezone().isoformat(), "preview": preview.name})


def render_case(name, root):
    reel, compose, sent = fixture(root)
    mask = mask_mod()
    if name == "fail-closed":
        for failure in ("missing", "check"):
            # With the check mutant, the real masked copy must first be made.
            ctx = patch.object(mask, "masked_copy", return_value=reel / "absent.mp4") if failure == "missing" else patch.object(mask, "check", return_value=["Box 1 is still readable"])
            with ctx:
                try:
                    compose.render(reel, "preview", engine.HOOK)
                except compose.Stop as error:
                    assert error.code == 1 and "nothing was rendered" in " ".join(error.lines).lower()
                    assert "clip " in " ".join(error.lines) and "Re-open" in " ".join(error.lines)
                else:
                    raise AssertionError("privacy failure allowed a render")
            assert not list((reel / "renders").glob("*.mp4"))
        return
    trials = engine.load("trials", engine.PLUGIN / "skills/reel-trials/scripts") if name == "render-trials" else None
    if trials:
        trials.compose = compose
    tier = "preview" if name in ("render-preview", "render-trials") else "master"
    energies = []
    for mutant in (False, True):
        if tier == "master":
            master_ok(reel, compose)
        with patch.object(compose, "masked_broll", side_effect=lambda r, inp, b: r / b["broll"]["src"]) if mutant else patch.object(compose, "masked_broll", wraps=compose.masked_broll):
            if trials:
                output = reel / ("trials/mutant/output.mp4" if mutant else "trials/normal/output.mp4")
                trials.scratch_render(reel, sent, engine.HOOK, output)
            else:
                summary = compose.render(reel, tier, engine.HOOK, layers="overlay" if name == "render-handoff-overlay" else "all")
                output = reel / summary["out"]
                if not mutant:
                    assert summary["masked"] and all(len(h) == 64 for h in summary["masked"].values())
            scale = 720 / 1080 if tier == "preview" else 1
            fields = [tuple(round(v * scale) for v in b) for b in (BOX_PX, CONTROL)]
            energies.append([mask.edge_energy_of(output, b, 1.5) for b in fields])
    normal, mutant = energies
    assert mutant[0] > 1.5 and normal[0] <= .15 * mutant[0], energies
    assert normal[1] >= .5 * mutant[1], energies


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--data-only", action="store_true")
    mode.add_argument("--case", choices=DATA + HEAVY)
    ap.add_argument("--tmp", type=Path, default=Path(tempfile.gettempdir()))
    args = ap.parse_args()
    cases = DATA if args.data_only else (args.case,) if args.case else DATA + HEAVY
    failures = []
    # Tool state is read only; renders get an isolated copy of user choices/packages.
    with engine.isolated_home(packages=any(c in HEAVY for c in cases)):
        with tempfile.TemporaryDirectory(prefix="broll-mask-", dir=args.tmp) as temp:
            for name in cases:
                root = Path(temp) / name
                root.mkdir()
                try:
                    data_case(name, root) if name in DATA else render_case(name, root)
                    print("PASS " + name, flush=True)
                except Exception as error:
                    print(f"FAIL {name}: {type(error).__name__}: {error}", flush=True)
                    failures.append(name)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
