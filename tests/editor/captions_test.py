"""Caption contract checks; all fixtures live in temporary folders."""
import copy
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "plugins/editor-superengine/skills/reel-captions/scripts/captions.py"
SPEC = importlib.util.spec_from_file_location("captions", SCRIPT)
captions = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(captions)
SOURCE_HOME = captions.rt.state_dir()


def words(text, step=0.2):
    return [{"word": w, "start": i * step, "end": i * step + step * 0.8}
            for i, w in enumerate(text.split())]


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8"))


def fixture(reel, items, style=None, beats=None, marks=None):
    send = {"beats": beats or [], "word_marks": marks or []}
    if style is not None:
        send["caption_style"] = style
    put(reel / captions.SEND, send)
    put(reel / captions.DEFAULT_WORDS, {"words": items})
    put(reel / "work/cuts.json", {"fps": 30, "segments": [{"out_in_f": 0, "out_out_f": 180}]})


def expect_stop(code, fn, contains=None):
    try:
        fn()
    except captions.Stop as e:
        assert e.code == code, (e.code, e.lines)
        if contains:
            assert contains in "\n".join(e.lines), e.lines
    else:
        raise AssertionError("Expected a plain stop")


def style_checks(tmp):
    state, reel = tmp / "state", tmp / "reel"
    with patch.object(captions.rt, "state_dir", return_value=state):
        fixture(reel, words("say this."))
        expect_stop(1, lambda: captions.plan(reel), captions.ASK)
        put(state / "styles/default.json", {"caption_style": {"style": "boxed"}})
        expect_stop(1, lambda: captions.pick_style(reel), captions.ASK)
        captions.saved_style.pick(reel, "default")
        assert captions.pick_style(reel) == ({"style": "boxed"}, "saved")
        assert captions.plan(reel)["style"]["style"] == "boxed"
        fixture(reel, words("say this."), {"style": "clean"})
        assert captions.pick_style({"caption_style": {"style": "clean"}})[1] == "reel"
        assert captions.plan(reel)["style"]["style"] == "clean"
        for bad in ({"style": "unknown"}, {"style": []}, {"style": "clean", "accent": "red"},
                    {"style": "clean", "line_breaks": 1}, {"style": "clean", "min_read_s": True},
                    {"style": "clean", "min_read_s": float("nan")}, {"style": "clean", "typo": True}):
            expect_stop(2, lambda b=bad: captions.check_style(b), "caption_style")
        defaults = captions.check_style({"style": "clean"})
        assert defaults["under_small_overlays"] and defaults["line_breaks"]
        assert not defaults["echo_suppression"] and defaults["min_read_s"] == 0.35


def brand_checks(tmp):
    state, reel = tmp / "brand-state", tmp / "brand-reel"
    with patch.object(captions.rt, "state_dir", return_value=state):
        fixture(reel, words("say this."), {"style": "clean"})
        put(state / "styles/default.json", {"accent": "#E0218A"})
        assert captions.plan(reel)["style"]["accent"] == captions.DEFAULTS["accent"]
        captions.saved_style.pick(reel, "default")
        assert captions.plan(reel)["style"]["accent"] == "#E0218A"
        fixture(reel, words("say this."), {"style": "clean", "accent": "#123abc"})
        assert captions.plan(reel)["style"]["accent"] == "#123abc"
        put(state / "styles/default.json", {"accent": "#E0218A", "caption_style": {"style": "boxed"}})
        fixture(reel, words("say this."))
        assert captions.plan(reel)["style"]["accent"] == "#E0218A"
        for accent in ("magenta", "#123", "#E0218A\n", None, [], 123):
            put(state / "styles/default.json", {"accent": accent, "caption_style": {"style": "boxed"}})
            assert captions.plan(reel)["style"]["accent"] == captions.DEFAULTS["accent"]


def plant_brand_font(plugin):
    """Alias a copy of shipped OFL Inter in a scratch scene's normal font source."""
    fonts = plugin / "runtime/fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCRIPT.parents[3] / "runtime/fonts/Inter-Regular.woff2",
                 fonts / "Caption-Test.woff2")
    scene = plugin / "scenes/hook-title/scene.html"
    scene.parent.mkdir(parents=True, exist_ok=True)
    page = scene.read_text(encoding="utf-8") if scene.is_file() else ""
    scene.write_bytes((page + '\n<style>@font-face {font-family: "Caption Test"; '
                       'src: url("./fonts/Caption-Test.woff2"); font-weight: 400;}</style>\n').encode("utf-8"))
    return "Caption Test"


def brand_font_checks(tmp):
    state, reel, plugin = tmp / "font-state", tmp / "font-reel", tmp / "font-plugin"
    family = plant_brand_font(plugin)
    fixture(reel, words("say this."))
    put(state / "styles/default.json", {"font": family, "caption_style": {"style": "clean"}})
    with patch.object(captions.rt, "state_dir", return_value=state), \
            patch.object(captions.scene_check, "SCENES", plugin / "scenes"), \
            patch.object(captions.scene_check, "FONTS", plugin / "runtime/fonts"):
        captions.saved_style.pick(reel, "default")
        doc = captions.plan(reel)
        css, _, _ = captions.layer(doc, [(100, 1200, 900, 1400)] * len(doc["chunks"]), 1, str)
        assert 'font-family: "Caption Test", "Inter";' in css, css
        assert captions.scene_check.font_faces(css)[family] == ["./fonts/Caption-Test.woff2"]
        assert not any("isn't available for captions" in n for n in doc["notes"])


def brand_font_missing_checks(tmp):
    state, reel, plugin = tmp / "missing-font-state", tmp / "missing-font-reel", tmp / "missing-font-plugin"
    family = plant_brand_font(plugin)
    fixture(reel, words("say this."))
    with patch.object(captions.rt, "state_dir", return_value=state), \
            patch.object(captions.scene_check, "SCENES", plugin / "scenes"), \
            patch.object(captions.scene_check, "FONTS", plugin / "runtime/fonts"):
        # A declaration without a file and an undeclared family both fall back.
        (plugin / "runtime/fonts/Caption-Test.woff2").unlink()
        for font in (family, "Missing Brand"):
            put(state / "styles/default.json", {"font": font, "caption_style": {"style": "clean"}})
            captions.saved_style.pick(reel, "default")
            doc = captions.plan(reel)
            for _ in range(2):
                css, _, _ = captions.layer(doc, [(100, 1200, 900, 1400)] * len(doc["chunks"]), 1, str)
            assert 'font-family: "Inter";' in css and '"Caption Test"' not in css
            assert doc["notes"] == [f"Your brand font {font} isn't available for captions yet, so they use Inter."]


def reel_beats_saved_checks(tmp):
    state, reel = tmp / "accent-state", tmp / "accent-reel"
    fixture(reel, words("say this."))
    put(state / "styles/default.json", {"accent": "#E0218A", "caption_style": {"style": "boxed"}})
    put(reel / captions.PICKER_SEND, {"caption_style": {"style": "bold-pop", "accent": "#123abc"}})
    with patch.object(captions.rt, "state_dir", return_value=state):
        doc = captions.plan(reel)
        assert doc["style"]["style"] == "bold-pop" and doc["style"]["accent"] == "#123abc"


def chunk_checks(tmp):
    items = words("a quick mid phrase layout switch here.", 0.08)
    chunks = captions.chunk(items, 30, [5], 90)
    assert all(1 <= c["w1"] - c["w0"] + 1 <= 3 for c in chunks)
    assert all(not c["start_f"] < 5 < c["end_f"] for c in chunks)
    assert all(not c["w0"] < 2 <= c["w1"] for c in chunks)
    assert all(a["end_f"] <= b["start_f"] for a, b in zip(chunks, chunks[1:]))
    assert all(isinstance(c[k], int) for c in chunks for k in ("start_f", "end_f"))
    assert captions.chunk(words("Hi, there", 0.4), 30, [], 90)[0]["w1"] == 0
    assert captions.chunk(words("Hi, there", 0.4), 30, [], 90, False)[0]["w1"] == 1
    expect_stop(2, lambda: captions.chunk(words("bad time"), 0, [], 30))
    expect_stop(2, lambda: captions.chunk(words("past end", 10), 30, [], 5))


def mark_checks(tmp):
    reel = tmp / "marks"
    items = words("one two three four five. next sentence.", 0.08)
    fixture(reel, items, {"style": "clean"}, marks=[{"w": i, "mark": "emph"} for i in (0, 1, 2, 4)])
    doc = captions.plan(reel)
    punched = [w["w"] for c in doc["chunks"] for w in c["words"] if w["punch"]]
    assert punched == [0, 1, 2], punched  # one three-word run, one punch event
    assert any("one punch" in n for n in doc["notes"]), doc["notes"]
    assert next(w for c in doc["chunks"] for w in c["words"] if w["w"] == 4)["mark"] == "emph"
    runs = captions.pick_marks([w["word"] for w in items], [{"w": i, "mark": "emph"} for i in (0, 1, 2)])
    assert runs == [{"w0": 0, "w1": 2, "mark": "emph"}], runs
    fixture(reel, words("one two. three four.", 0.08), {"style": "clean"},
            marks=[{"w": 0, "mark": "key"}, {"w": 2, "mark": "emph"}])
    assert sum(w["punch"] for c in captions.plan(reel)["chunks"] for w in c["words"]) == 2
    fixture(reel, words("30 days. act now.", 0.08), {"style": "clean"},
            marks=[{"w": 0, "mark": "num"}, {"w": 3, "mark": "cta"}])
    assert not any(w["punch"] for c in captions.plan(reel)["chunks"] for w in c["words"])
    expect_stop(2, lambda: captions.pick_marks(["x"], [{"w": True, "mark": "emph"}]))


def truth_checks(tmp):
    reel = tmp / "truth"
    # A slower take would normally close the first pair. Keep the truthful run together.
    fixture(reel, words("this doesn't work.", 0.3), {"style": "clean"}, marks=[{"w": 2, "mark": "emph"}])
    assert captions.pick_marks(["this", "doesn't", "work."], [{"w": 2, "mark": "emph"}]) == [
        {"w0": 1, "w1": 2, "mark": "emph"}]
    doc = captions.plan(reel)
    for c in doc["chunks"]:
        if any(w["w"] == 2 and (w["mark"] or w["punch"]) for w in c["words"]):
            assert any(w["w"] == 1 and w["mark"] == "emph" for w in c["words"]), c
    # A truthful run that can't fit one caption loses its stress (a plain note), never its qualifier; no stop.
    fixture(reel, words("only if you post daily.", 0.1), {"style": "clean"}, marks=[{"w": 4, "mark": "emph"}])
    doc = captions.plan(reel)
    assert not any(w["mark"] or w["punch"] for c in doc["chunks"] for w in c["words"]), doc["chunks"]
    assert any("only if you post daily." in n for n in doc["notes"]), doc["notes"]
    fixture(reel, words("this doesn't work.", 0.3), {"style": "clean"},
            beats=[{"start_f": 0, "end_f": 18, "layout": "full"},
                   {"start_f": 18, "end_f": 180, "layout": "split"}],
            marks=[{"w": 2, "mark": "emph"}])
    doc = captions.plan(reel)
    assert not any(w["mark"] or w["punch"] for c in doc["chunks"] for w in c["words"]), doc["chunks"]
    assert any("doesn't work." in n for n in doc["notes"]), doc["notes"]


def coverage_checks(tmp):
    reel = tmp / "coverage"
    items = words("say this. other words.", 0.4)
    items.insert(1, {"word": " ", "start": 0.1, "end": 0.12})
    for i, w in enumerate(items):
        w["id"] = f"w_{i * 10:04d}"  # ids may skip numbers; output w is the list position
    beat = {"start_f": 0, "end_f": 180, "layout": "full",
            "scene": {"id": "callout", "slots": {"text": "say this."}}}
    for extra, why in (({}, "empty"), ({"echo_suppression": True}, "echo"),
                       ({"under_small_overlays": False}, "overlay")):
        fixture(reel, items, {"style": "clean", **extra}, [beat])
        doc = captions.plan(reel)
        positions = [w["w"] for c in doc["chunks"] for w in c["words"]] + [d["w"] for d in doc["declared_drops"]]
        assert sorted(positions) == list(range(len(items))), positions
        assert any(d["why"] == why for d in doc["declared_drops"]), doc
    # A partial overlap is not enough to claim the scene repeats the full caption.
    beat["start_f"], beat["end_f"] = 1, 4
    fixture(reel, items, {"style": "clean", "echo_suppression": True}, [beat])
    assert not any(d["why"] == "echo" for d in captions.plan(reel)["declared_drops"])
    fixture(reel, items, {"style": "none"})
    doc = captions.plan(reel)
    assert not doc["chunks"]
    assert doc["style"] == {"style": "none"}
    assert doc["declared_drops"] == [{"w": i, "why": "captions off"} for i in range(len(items))]
    fixture(reel, words("quick words.", 0.02), {"style": "clean"})
    assert any("short" in n for n in captions.plan(reel)["notes"])
    assert not (reel / "work/captions.json").exists()  # planning is read-only
    captions.write(reel, doc)
    assert b"\r" not in (reel / "work/captions.json").read_bytes()


def layer_checks(tmp):
    reel = tmp / "layer"
    t = lambda f: f"{f / 30:.6f}".rstrip("0").rstrip(".") or "0"
    for style in captions.STYLES:
        fixture(reel, words("<tag> & today. second phrase.", 0.15), {"style": style, "accent": "#123abc"},
                marks=[{"w": 1, "mark": "emph"}])
        doc = captions.plan(reel)
        boxes = {c["i"]: (100, 1200, 900, 1400) for c in doc["chunks"]}
        css, layers, tl = captions.layer(doc, boxes, 2 / 3, t)
        source = css + "\n".join(layers + tl)
        assert 'font-family: "Inter"' in css and "z-index: 600" in source
        assert all(s not in source for s in ("@keyframes", "translateX", "onComplete", "repeat: -1", "text-transform"))
        assert all(w == "400" for w in re.findall(r"font-weight:\s*(\d+)", source))
        assert "#123abc" in source
        assert "&amp;" in source and ("&lt;TAG&gt;" if captions.STYLES[style]["case"] == "upper" else "&lt;tag&gt;") in source
        assert source.count("xPercent: -50") == len(doc["chunks"])
        for c in doc["chunks"]:
            assert f'tl.set("#cap-{c["i"]}", {{autoAlpha: 0}}, {t(c["end_f"])});' in tl
        assert any("immediateRender: false" in line for line in tl if "fromTo" in line)
        assert captions.band_h(captions.STYLES[style]) > captions.STYLES[style]["size"]
        # Same result when a caller supplies a dense box list; fallback notes survive unchanged.
        doc["notes"].append("The least-covering safe spot was used.")
        captions.layer(doc, list(boxes.values()), 1, t)
        assert "The least-covering safe spot was used." in doc["notes"]
        narrow = copy.deepcopy(doc)
        captions.layer(narrow, {c["i"]: (100, 1200, 180, 1400) for c in doc["chunks"]}, 1, t)
        assert any("smaller" in n for n in narrow["notes"])
        if style == "karaoke":
            assert "opacity: 0.55" in css
            assert all(any(f'#cap-{c["i"]}-w-{w["w"]}' in line and line.startswith("tl.set")
                           and line.endswith(f', {t(w["start_f"])});') for line in tl)
                       for c in doc["chunks"] for w in c["words"])
        for line in tl:
            if "tl.fromTo" in line:
                duration = float(re.search(r"duration: ([0-9.]+)", line)[1])
                start = float(re.search(r", ([0-9.]+)\);$", line)[1])
                assert abs(duration * 30 - round(duration * 30)) < 0.0001
                assert abs(start * 30 - round(start * 30)) < 0.0001
        # A three-word run creates one animated wrapper, not three punches.
        fixture(reel, words("a bright moment.", 0.08), {"style": style},
                marks=[{"w": i, "mark": "emph"} for i in range(3)])
        grouped = captions.plan(reel)
        _, _, group_tl = captions.layer(grouped, [(100, 1200, 900, 1400)], 1, t)
        assert sum("tl.fromTo" in line and "-punch-" in line for line in group_tl) == 1


def broll_backing_checks(tmp):
    reel = tmp / "backing"
    items = words("one. two. three. four.", 1)
    # Full overlap, partial overlap, and touching exclusive edges respectively.
    beats = [{"start_f": 0, "end_f": 30, "layout": "full", "broll": {"id": "own"}},
             {"start_f": 42, "end_f": 72, "layout": "full", "broll": {"id": "ai"}},
             {"start_f": 72, "end_f": 180, "layout": "full", "broll": None}]
    for style in captions.STYLES:
        fixture(reel, items, {"style": style}, beats=beats)
        doc = captions.plan(reel)
        assert [bool(c.get("backing")) for c in doc["chunks"]] == (
            [False] * 4 if style == "boxed" else [True, True, True, False]), "B-roll overlaps need backing"
        boxes = [(100, 1200, 900, 1400)] * 4
        css, layers, _ = captions.layer(doc, boxes, 0.5, lambda f: str(f / 30))
        markup = "\n".join(layers)
        if style == "boxed":
            assert 'class="caption backed"' not in markup and '.caption.backed' not in css
            assert 'background: rgba(0,0,0,0.72); border-radius: 8px;' in css
        else:
            assert markup.count('class="caption backed"') == 3
            assert 'class="caption" id="cap-3"' in markup
            assert '.caption.backed {background: rgba(0,0,0,0.6); border-radius: 8px;}' in css
            assert 'padding: 8px;' in css and 'text-shadow:' in css
            if style == "bold-pop":
                assert '-webkit-text-stroke: 1.5px #000000;' in css
        captions.write(reel, doc)
        assert json.loads((reel / "work/captions.json").read_text(encoding="utf-8")) == doc
        # Compose's resolved beats (also used by the Look Picker) take precedence.
        resolved = captions.plan(reel, render_beats=[dict(b, broll=None) for b in beats])
        assert not any(c.get("backing") for c in resolved["chunks"])
    picker = captions.picker_doc(reel)
    for sid, look in picker["looks"].items():
        assert ('backed' in look["html"]["accent"]) == (sid != "boxed")
        assert 'marker-mode' in look["html"]["marker"], "Backed picker captions need marker mode too"
    # Hand-off's subtitle export accepts the persisted field without changing timing/text.
    sys.path.insert(0, str(SCRIPT.parents[2] / "pro-editor-handoff/scripts"))
    import export_edit
    srt = reel / "handoff/captions.srt"
    with patch.object(export_edit, "reel_rate", return_value=30):
        summary = export_edit.write_srt(reel, srt)
    assert summary["entries"] == 4 and not export_edit.check_srt(srt)


def cli_checks(tmp):
    reel = tmp / "cli"
    fixture(reel, words("this doesn't work."))
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert captions.main(["plan", "--reel-dir", str(reel)]) == 1
    assert output.getvalue().strip() == captions.ASK
    assert not (reel / "work/captions.json").exists()
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert captions.main(["marks", "--reel-dir", str(reel), "--candidates", '[{"w": 2, "mark": "emph"}]']) == 0
    assert json.loads(output.getvalue()) == [{"w": 1, "mark": "emph"}, {"w": 2, "mark": "emph"}]
    fixture(reel, words("hello world."), {"style": "clean"})
    with contextlib.redirect_stdout(io.StringIO()):
        assert captions.main(["plan", "--reel-dir", str(reel)]) == 0
    assert (reel / "work/captions.json").is_file()


def picker_style_checks(tmp):
    reel, state = tmp / "picker-style", tmp / "picker-state"
    with patch.object(captions.rt, "state_dir", return_value=state):
        fixture(reel, words("our own words."))
        expect_stop(1, lambda: captions.pick_style(reel), captions.ASK)
        put(state / "styles/default.json", {"caption_style": {"style": "boxed"}})
        expect_stop(1, lambda: captions.pick_style(reel), captions.ASK)
        captions.saved_style.pick(reel, "default")
        assert captions.pick_style(reel) == ({"style": "boxed"}, "saved")
        picker = {"caption_style": {"style": "bold-pop"}, "sent_at": "2026-11-05T10:00:00-05:00"}
        put(reel / "look-picker-selection.json", picker)
        assert captions.plan(reel)["style"]["style"] == "bold-pop"  # picker alone
        bm = {"beats": [], "caption_style": {"style": "clean"}, "sent_at": "2026-11-05T14:59:00+00:00"}
        put(reel / captions.SEND, bm)
        assert captions.plan(reel)["style"]["style"] == "bold-pop"  # compare instants, not strings
        bm["sent_at"] = "2026-11-05T15:01:00+00:00"
        put(reel / captions.SEND, bm)
        assert captions.plan(reel)["style"]["style"] == "clean"
        picker["caption_style"] = {"style": "none"}
        picker["sent_at"] = "2026-11-05T15:02:00Z"
        put(reel / "look-picker-selection.json", picker)
        assert captions.plan(reel)["style"] == {"style": "none"}
        put(reel / "look-picker-selection.json", {"sent_at": "2026-11-05T16:00:00Z"})
        assert captions.plan(reel)["style"]["style"] == "clean"  # a Send without a caption choice is ignored
        assert captions.pick_style(bm) == ({"style": "clean"}, "reel")
    defaults = captions.check_style({"style": "clean"})
    assert defaults["mark_look"] == "accent" and defaults["loud_emphasis"] is False
    assert captions.check_style({"style": "clean", "mark_look": "marker", "loud_emphasis": True})
    for extra in ({"mark_look": "circle"}, {"mark_look": []}, {"loud_emphasis": 1}):
        expect_stop(2, lambda e=extra: captions.check_style({"style": "clean", **e}), "caption_style")


def marker_width_checks(tmp):
    reel = tmp / "marker"
    fixture(reel, words("this doesn't work.", 0.3), {"style": "clean", "mark_look": "marker"},
            marks=[{"w": 2, "mark": "emph"}])
    doc = captions.plan(reel)
    boxes = [(100, 1200, 900, 1400)] * len(doc["chunks"])
    css, markup, tl = captions.layer(doc, boxes, 1, lambda f: str(f / 30))
    page = "".join(markup)
    assert page.count('class="cap-marker"') == 1
    assert re.search(r'class="cap-marker"[^>]*>.*?doesn&#x27;t.*?work\..*?</span></span>', page)
    assert sum('scaleX' in line and 'tl.fromTo' in line for line in tl) == 1
    assert any('scaleX: 0' in line and 'scaleX: 1' in line and 'immediateRender: false' in line
               and line.endswith(', 0.3);') for line in tl)
    assert 'left center' in "".join(tl) and '@keyframes' not in css
    assert sum('tl.fromTo' in line and '-punch-' in line for line in tl) == 1
    fixture(reel, words("bright and clear.", 0.08), {"style": "clean", "mark_look": "marker"},
            marks=[{"w": 0, "mark": "key"}, {"w": 2, "mark": "emph"}])
    two = captions.plan(reel)
    _, two_html, two_tl = captions.layer(two, boxes, 1, str)
    assert "".join(two_html).count('class="cap-marker"') == 2
    assert sum('-punch-' in line and 'fromTo' in line for line in two_tl) == 1
    fixture(reel, words("work."), {"style": "clean", "mark_look": "marker"},
            marks=[{"w": 0, "mark": "emph"}])
    zero = captions.plan(reel)
    _, _, zero_tl = captions.layer(zero, boxes, 1, str)
    assert any('scaleX: 1' in line and 'immediateRender: true' in line and line.startswith('tl.set')
               and line.endswith(', 0);') for line in zero_tl)
    table = tmp / "char-widths.json"
    fixture(reel, words("WWW"), {"style": "clean"})
    with patch.object(captions, "CHAR_WIDTHS", table):
        normal = captions.plan(reel)
        _, original, _ = captions.layer(normal, [(100, 1200, 600, 1400)], 1, str)
        put(table, {"units_per_em": 1000, "widths": {"W": 4000}, "default": 600})
        wide = captions.plan(reel)
        _, fitted, _ = captions.layer(wide, [(100, 1200, 600, 1400)], 1, str)
        size = lambda lines: float(re.search(r'font-size: ([0-9.]+)px', "".join(lines))[1])
        assert size(fitted) < size(original) and any("smaller" in n for n in wide["notes"])
        assert captions.text_width_em("W?") == 4.6  # missing glyph retains the old estimate


def loud_checks(tmp):
    reel = tmp / "loud"
    items = words("this doesn't work.", 0.3)
    fixture(reel, items, {"style": "clean", "loud_emphasis": True})
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert captions.suggest_loud(reel, items) == []
    assert len(err.getvalue().strip().splitlines()) == 1
    put(reel / "work/cuts.json", {"fps": 30, "speed": 2, "segments": [
        {"out_in_f": 0, "out_out_f": 180, "src_in_f": 300, "src_out_f": 660}]})
    db = [-30] * 2200
    db[1130] = -10  # output .65 s maps to source 11.30 s (not output .65 s)
    db[65] = 0  # a decoy on the wrong timeline
    put(reel / "work/envelope.json", {"win_s": 0.01, "db": db})
    candidates = captions.suggest_loud(reel, items)
    assert candidates == [{"w": 2, "mark": "emph"}], candidates
    assert captions.pick_marks(items, candidates) == [{"w0": 1, "w1": 2, "mark": "emph"}]
    doc = captions.plan(reel)
    assert [w["w"] for c in doc["chunks"] for w in c["words"] if w["mark"]] == [1, 2]
    assert any("loud" in n.lower() for n in doc["notes"])
    bm = json.loads((reel / captions.SEND).read_text())
    bm["word_marks"] = [{"w": 0, "mark": "key"}]
    put(reel / captions.SEND, bm)
    assert [w["w"] for c in captions.plan(reel)["chunks"] for w in c["words"] if w["mark"]] == [0]
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert captions.main(["marks", "--reel-dir", str(reel), "--loud"]) == 0
    assert json.loads(output.getvalue()) == [{"w": 1, "mark": "emph"}, {"w": 2, "mark": "emph"}]
    # A word crossing an edit reads only the two retained source ranges, not the removed gap.
    crossing = [{"word": "quiet", "start": 0, "end": 0.1},
                {"word": "soft", "start": 0.1, "end": 0.2},
                {"word": "loud", "start": 0.4, "end": 0.6}]
    put(reel / "work/cuts.json", {"fps": 30, "speed": 1, "segments": [
        {"out_in_f": 0, "out_out_f": 15, "src_in_f": 30, "src_out_f": 45},
        {"out_in_f": 15, "out_out_f": 30, "src_in_f": 90, "src_out_f": 105}]})
    db = [-30] * 400
    db[305] = -10
    put(reel / "work/envelope.json", {"win_s": 0.01, "db": db})
    assert captions.suggest_loud(reel, crossing) == [{"w": 2, "mark": "emph"}]
    db[305], db[200] = -30, 0  # removed source gap must not stress the crossing word
    put(reel / "work/envelope.json", {"win_s": 0.01, "db": db})
    assert captions.suggest_loud(reel, crossing) == []
    (reel / "work/envelope.json").unlink()
    bm["word_marks"] = []
    put(reel / captions.SEND, bm)
    assert len(captions.plan(reel)["notes"]) == 1


def picker_doc_checks(tmp):
    reel = tmp / "picker-doc"
    fixture(reel, words("our own words. this doesn't work.", 0.08), {"style": "clean"},
            beats=[{"layout": "split", "start_f": 30, "end_f": 90}], marks=[{"w": 5, "mark": "emph"}])
    doc = captions.picker_doc(reel)
    assert doc["schema"] == 1 and doc["reel"] == reel.name and doc["fps"] == 30
    assert set(doc["frames"]) == set(doc["layouts"]) == set(captions.beat_schema.LAYOUTS)
    assert doc["layouts"]["full"]["box"] == [0, 0, 1080, 1920]
    assert doc["sample"]["text"] == "this doesn't work."
    assert set(doc["looks"]) == set(captions.STYLES)
    for sid, look in doc["looks"].items():
        assert look["pop"]["seconds"] == captions.STYLES[sid]["pop"]["frames"] / 30
        assert set(look["html"]) == {"accent", "marker"}
        assert 'class="caption"' in look["html"]["accent"]
        assert 'class="cap-marker"' in look["html"]["marker"]
        assert 'visibility: hidden' not in look["html"]["accent"]
    assert any("lowest safe" in n for n in doc["notes"])
    assert doc["current"]["style"] == "clean" and doc["options"]["loud_emphasis"] is False
    assert len(doc["tips"]) >= 3 and all(isinstance(tip, str) for tip in doc["tips"])
    assert captions.picker_times(reel) == {name: (2 if name == "split" else 1.5)
                                         for name in captions.beat_schema.LAYOUTS}
    with contextlib.redirect_stdout(io.StringIO()) as output:
        assert captions.main(["picker", "--reel-dir", str(reel)]) == 2
    assert output.getvalue().strip() == "make the cut first"
    (reel / captions.SEND).unlink()
    fixture(reel, words("our own words."))
    assert captions.picker_doc(reel)["current"] is None  # picker can help choose the first look


def remembered_unpicked_checks(tmp):
    reel, state = tmp / "reel", tmp / "state"
    put(state / "state.json", {"components": {"fixture": {"bins": {
        key: captions.rt.tool(key, SOURCE_HOME) for key in ("ffmpeg", "ffprobe")}}}})
    fixture(reel, words("our own words stay here."))
    put(reel / "work/cuts.json", {"fps": 30, "speed": 1, "segments": [
        {"src_in_f": 0, "src_out_f": 180, "out_in_f": 0, "out_out_f": 180}]})
    master = reel / "work/renders/master-100x.mp4"
    master.parent.mkdir(parents=True)
    with patch.dict(os.environ, {"EDITOR_SE_HOME": str(state)}):
        result = subprocess.run([sys.executable, "-X", "utf8", "-I",
            str(SCRIPT.parents[2] / "_shared/standing_notes.py"), "pick", "caption_style.style",
            "--value", '"boxed"', "--note", "Keep it framed"], capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == 0, result.stdout + result.stderr
        # Another reel's saved choices must not become this reel's current look or brand.
        captions.saved_style.save({"caption_style": {"style": "karaoke"}, "accent": "#123ABC",
                                   "edit_style": {"style": "layout-switch"}}, "other")
        captions.saved_style.pick(tmp / "other-reel", "other")
        result = subprocess.run([captions.rt.tool("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
            "color=c=gray:s=64x64:r=30:d=6", "-frames:v", "180", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(master)], capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == 0, result.stderr
        result = subprocess.run([sys.executable, "-X", "utf8", "-I", str(SCRIPT), "picker", "--reel-dir", str(reel)],
                                capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == 0, result.stdout + result.stderr
        doc = json.loads((reel / "work/look-picker.json").read_text(encoding="utf-8"))
        assert doc["recommended"] is not None, "An unpicked reel lost its remembered look"
        assert doc["recommended"]["value"] == "boxed" and doc["recommended"]["note"] == "Keep it framed"
        assert doc["current"] is None
        assert all((reel / file).is_file() for file in doc["frames"].values())
        assert not (reel / "look-picker-selection.json").exists()
        assert not (reel / "work/captions.json").exists()
        assert captions.saved_style.pick_for(reel) is None
        loaded = captions.saved_style.load(reel)
        assert set(loaded) == {"picks"}, "Saved choices leaked into an unpicked reel"
        assert captions.saved_style.load(reel, for_write=True) == {}
        assert captions.check_style({"style": "clean"}, reel=reel)["accent"] == "#FFD84D"
        expect_stop(1, lambda: captions.plan(reel), "Last time you picked Boxed")


def main():
    failed = 0
    with tempfile.TemporaryDirectory() as tmp:
        for check in (style_checks, brand_checks, brand_font_checks, brand_font_missing_checks,
                      reel_beats_saved_checks, chunk_checks, mark_checks, truth_checks, coverage_checks, layer_checks,
                      broll_backing_checks, cli_checks, picker_style_checks, marker_width_checks, loud_checks, picker_doc_checks,
                      remembered_unpicked_checks):
            root = Path(tmp) / check.__name__
            root.mkdir()
            # Every check starts without earlier picks; children inherit the same scratch home.
            with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / "no-saved-style")}):
                try:
                    check(root)
                    print(f"PASS {check.__name__}")
                except Exception as e:
                    failed += 1
                    print(f"FAIL {check.__name__}: {type(e).__name__}: {e}")
    return int(bool(failed))


if __name__ == "__main__":
    sys.exit(main())
