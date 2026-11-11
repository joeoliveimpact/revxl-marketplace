"""Judge every overlay card's measured visible pixels against the protected face."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "reel-canvas-build/scripts"))
import compose
import placer
from check import PLACEMENT_NOT_JUDGED

PHASE = "pre"


def run(ctx):
    reel = Path(ctx["reel_dir"])
    beats = ctx.get("beats")
    if beats is None:
        try:
            beats = json.loads((reel / "beat-map-selection.json").read_text(encoding="utf-8")).get("beats", [])
        except FileNotFoundError:
            return []
    entries = compose.read_scene_boxes(reel / "work/scene-boxes.json")
    rows, unjudged, face = [], False, None
    for number, beat in enumerate(beats, 1):
        scene = beat.get("scene")
        if not scene:
            continue
        spec = json.loads((compose.scene_check.SCENES / scene["id"] / "scene.json").read_text(encoding="utf-8"))
        if spec["kind"] != "overlay":
            continue
        # 3d-head-band owns every 3D card, even with a measured box: one block per card.
        if spec.get("category") == "3d":
            continue
        entry = compose.matching_scene_box(entries, beat["id"], scene)
        if entry is None or entry.get("kind") != "overlay":
            unjudged = True
            continue
        if entry["box"] is None:
            # Transparent renders and explicit omissions are clear only after hash validation.
            continue
        if not (reel / compose.styles.ANCHORS).is_file():
            continue
        if face is None:
            face = dict(placer.load_ctx(reel), beats=beats)
        head = placer.visible_head_box_at(face, beat["start_f"], beat["end_f"] - 1)
        if head is not None and placer.hits(entry["box"], placer.face_band(head), placer.CAPTION_PAD):
            advice = f'On the Beat Map, open beat {number} and press "Remove scene", or pick another card'
            reset_param = "dy"  # The Beat Map labels editable controls with param.name.
            if (scene.get("params") or {}).get(reset_param, 0) != 0:
                advice += (f', or set "{reset_param}" back to 0 on that beat '
                           'so the card can be moved for you')
            rows.append(dict(check="card-on-face", level="block",
                msg=f"The {compose.scene_title(scene['id'])} card covers your eyes or mouth on beat {number}.",
                advice=advice + ".",
                where=f"beat {number}", at=float(beat["start_f"] / (ctx.get("fps") or face["fps"]))))
    if unjudged:
        rows.append(dict(check="placement-not-judged", level="block", msg=PLACEMENT_NOT_JUDGED,
                         advice="Make the preview again, then OK it.", where="work/scene-boxes.json"))
    return rows
