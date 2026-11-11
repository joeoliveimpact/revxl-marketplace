#!/usr/bin/env python3
"""Measured overlay face QA. Usage: python tests/editor/overlay_face_check_test.py <scratch-dir>."""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1] / "plugins/editor-superengine"
sys.path.insert(0, str(PLUGIN / "skills/reel-canvas-build/scripts"))
sys.path.insert(0, str(PLUGIN / "skills/_shared/checks"))
import compose
import scene_fill
import overlay_face_check as overlay
import check as qa

fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  [{detail}]"))
    if not ok:
        fails.append(name)


def save(path, doc):
    path.write_bytes((json.dumps(doc, indent=2) + "\n").encode("utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch", type=Path)
    args = ap.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="overlay-face-", dir=args.scratch) as home:
        reel = Path(home)
        (reel / "work").mkdir()
        scene = dict(id="cta-reminder", slots={"keyword": "NOTES"}, params={})
        beat = dict(id="b_001", start_f=30, end_f=150, layout="full", scene=scene)
        save(reel / "beat-map-selection.json", dict(fps=30, beats=[beat]))
        save(reel / "work/cuts.json", dict(fps=30, segments=[dict(out_in_f=0, out_out_f=150)]))
        save(reel / "work/scale_track.json", dict(fps=30, total_f=150,
             style={"style": "punch-in"}, keys=[dict(f=0, scale=1, ox=.5, oy=.5, layout="full")], tweens=[]))
        save(reel / "work/anchors.json", dict(segments=[dict(seg=0, samples=[dict(f=0, x=.5, y=.5,
             box=[24 / 1080, 410 / 1920, 1056 / 1080, 1668 / 1920])])]))
        ctx = qa.build_context(reel)
        ctx["beats"] = [beat]
        path = reel / "work/scene-boxes.json"

        def measured(box, rendered=None):
            compose.write_scene_boxes(path, {beat["id"]: compose.scene_box_entry(
                scene, rendered or scene, box, "overlay")})

        measured([80, 1150, 600, 1320])
        rows = overlay.run(ctx)
        ck("mouth overlap: one timed card block", len(rows) == 1 and rows[0]["check"] == "card-on-face"
           and rows[0]["level"] == "block" and rows[0]["at"] == 1.0, rows)
        ck("mouth overlap: beat and displayed card name", len(rows) == 1 and
           rows[0]["msg"] == "The Cta reminder card covers your eyes or mouth on beat 1.", rows)
        board = (PLUGIN / "skills/reel-canvas-build/boards/beat-map/index.html").read_text(encoding="utf-8")
        label = re.search(r'class: "remove-scene", text: "([^"]+)"', board).group(1)
        ck("advice quotes the board's exact button label", len(rows) == 1 and
           f'press "{label}"' in rows[0]["advice"] and "open beat 1" in rows[0]["advice"], rows)
        ck("grouped refusal keeps card advice", len(rows) == 1 and rows[0]["advice"] in compose.qa_block_lines(rows)[0])
        cover = dict(id="cover", start_f=30, end_f=150, layout="full", scene=None,
                     broll={"fit": "cover"})
        for fit in ("cover", "blur-fill"):
            cover["broll"]["fit"] = fit
            save(reel / "beat-map-selection.json", dict(fps=30, beats=[beat, cover]))
            ctx["beats"] = [beat, cover]
            ck(fit + ": covered crossing box has no face row", overlay.run(ctx) == [])
        cover["end_f"] = 149
        save(reel / "beat-map-selection.json", dict(fps=30, beats=[beat, cover]))
        ck("one uncovered frame still protects the face", [r["check"] for r in overlay.run(ctx)] == ["card-on-face"])
        cover["end_f"] = 150
        save(reel / "beat-map-selection.json", dict(fps=30, beats=[beat, cover]))
        save(reel / "work/scale_track.json", dict(fps=30, total_f=150,
             style={"style": "layout-switch"}, keys=[dict(f=0, scale=1, ox=.5, oy=.5, layout="pip")], tweens=[]))
        measured([780, 250, 980, 400])
        ck("foreground PIP protects its mapped face over B-roll", [r["check"] for r in overlay.run(ctx)] == ["card-on-face"])
        save(reel / "work/scale_track.json", dict(fps=30, total_f=150,
             style={"style": "punch-in"}, keys=[dict(f=0, scale=1, ox=.5, oy=.5, layout="full")], tweens=[]))
        save(reel / "beat-map-selection.json", dict(fps=30, beats=[beat]))
        ctx["beats"] = [beat]
        param_label = re.search(r'text: param\.(\w+) \+ \(locked \? "[^"]*" : ""\)', board).group(1)
        catalog_scene = next(s for s in scene_fill.catalog() if s["id"] == scene["id"])
        reset_param = next(p for p in catalog_scene["params"] if p["name"] == "dy")
        # dy is editable, so the board uses the param field without the locked-control suffix.
        reset_label = reset_param[param_label]
        for dy in (-200, 200, 0):
            scene["params"]["dy"] = dy
            measured([80, 1150, 600, 1320])
            found = overlay.run(ctx)
            ck(f"explicit dy {dy}: reset advice only for non-zero moves", len(found) == 1 and
               (f'or set "{reset_label}" back to 0 on that beat so the card can be moved for you.'
                in found[0]["advice"]) == (dy != 0), found)
            if dy != 0:
                quoted = re.search(r'or set "([^"]+)" back to 0', found[0]["advice"]) if len(found) == 1 else None
                ck("reset advice quotes the board-rendered number control", quoted is not None and
                   quoted.group(1) == reset_label and reset_param["type"] == "number", found)
        del scene["params"]["dy"]
        measured([80, 250, 600, 420])
        ck("clear box", overlay.run(ctx) == [])
        measured(None)
        ck("transparent scene", overlay.run(ctx) == [])
        path.unlink()
        rows = overlay.run(ctx)
        ck("missing box file: not judged", [r["check"] for r in rows] == ["placement-not-judged"], rows)
        ck("cards alone: shared preview sentence", len(rows) == 1 and
           rows[0]["msg"] == qa.PLACEMENT_NOT_JUDGED, rows)
        compose.write_scene_boxes(path, {})
        ck("missing beat: not judged", [r["check"] for r in overlay.run(ctx)] == ["placement-not-judged"])
        measured([80, 250, 600, 420])
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["beats"][beat["id"]]["fill"] = "stale"
        save(path, doc)
        ck("stale fill: not judged", [r["check"] for r in overlay.run(ctx)] == ["placement-not-judged"])
        measured([80, 250, 600, 420], dict(scene, params={"dy": -900}))
        ck("automatic dy: current measured fill", overlay.run(ctx) == [])
        scene["slots"]["keyword"] = "GUIDE"
        ck("changed input fill: not judged", [r["check"] for r in overlay.run(ctx)] == ["placement-not-judged"])
        scene["slots"]["keyword"] = "NOTES"
        for sid in ("hf-callout", "hf-hook-title"):
            scene["id"] = sid
            measured([80, 1150, 600, 1320])
            found = overlay.run(ctx)
            ck(sid + ": measured face overlap blocks", len(found) == 1 and
               found[0]["check"] == "card-on-face", found)
        scene["id"] = "glass-card-3d"
        measured([80, 1150, 600, 1320])
        ck("3D measured overlap: owned only by 3d-head-band", overlay.run(ctx) == [])
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["beats"][beat["id"]]["fill"] = "stale"
        save(path, doc)
        ck("3D stale measurement: still owned by 3d-head-band", overlay.run(ctx) == [])
        scene["id"] = "cta-reminder"
        measured([80, 1150, 600, 1320])
        (reel / "work/anchors.json").unlink()
        ck("no anchors: no block or crash", overlay.run(ctx) == [])
        scene["id"] = "hook-title"
        path.unlink()
        ck("takeover: no measurement needed", overlay.run(ctx) == [])
        ctx["beats"] = [dict(beat, scene=None)]
        ck("no scene: no measurement needed", overlay.run(ctx) == [])
        ctx["beats"] = [beat]
        scene["id"] = "glass-card-3d"
        ck("3D without box: existing check owns it", overlay.run(ctx) == [])
        for sid in ("hf-callout", "hf-hook-title"):
            scene["id"] = sid
            ck(sid + ": missing render remains not judged", [r["check"] for r in overlay.run(ctx)]
               == ["placement-not-judged"])
            for rendered in (scene, dict(scene, params={"top": 220})):
                entry = compose.scene_box_entry(scene, rendered, None, "overlay")
                entry["omitted"] = True
                compose.write_scene_boxes(path, {beat["id"]: entry})
                ck(sid + ": omitted matching fill is clear", overlay.run(ctx) == [])
                scene["slots"]["keyword"] = "GUIDE"
                ck(sid + ": omitted stale source is not judged", [r["check"] for r in overlay.run(ctx)]
                   == ["placement-not-judged"])
                scene["slots"]["keyword"] = "NOTES"
                entry["fill"] = "stale"
                compose.write_scene_boxes(path, {beat["id"]: entry})
                ck(sid + ": omitted stale render is not judged", [r["check"] for r in overlay.run(ctx)]
                   == ["placement-not-judged"])
            path.unlink()
        # Both owners can be unjudged, but the runner must emit only one row.
        unjudged = dict(check="placement-not-judged", level="block", msg="Caption positions missing.")
        merged = qa.merge_placement_rows([unjudged, dict(unjudged, msg="Card positions missing.")])
        ck("captions and cards: one not-judged row", len(merged) == 1 and
           merged[0]["msg"] == qa.PLACEMENT_NOT_JUDGED, merged)
        lines = compose.qa_block_lines(merged)
        ck("captions and cards: one grouped line and one preview sentence", len(lines) == 1 and
           lines[0].count(qa.PLACEMENT_NOT_JUDGED) == 1, lines)
    print(f"{len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
