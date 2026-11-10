"""N5 trial reels proof.

Usage: <editor python> -X utf8 -I tests/editor/trials_test.py --case NAME|all
Set EDITOR_SE_HOME to the editor state. Cases: selftest, spec, loops, render,
openings, reframe, wording, hub, scene. Prints PASS/FAIL per check. Media cases self-lock
with --wait 600 --min-gb 3; exit 75/76 means blocked. Uses synthetic media only.
"""
import argparse
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from itertools import combinations
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
P = HERE.parents[1] / "plugins/editor-superengine"
sys.path[:0] = [str(HERE), str(P / "skills/reel-trials/scripts")]
import trials
import beat_schema
import loop_check

CASES = ("selftest", "footage", "spec", "loops", "render", "openings", "reframe", "wording", "hub", "scene", "style_context")
HEAVY = Path("C:/Workspaces/Content Studio/output/scripts/heavy_lock.py")
FAILS = []
WORDING_CASES = (("A" + "/B test", False), ("a" + "-b test", False),
                 ("A" + "-B testing", False), ("A" + "/B-test", False),
                 ("ab" + "-test", False), ("AB" + " test", False),
                 ("A" + " / B test", False), ("ab" + "tested", False),
                 ("a" + "-b tests", False), ("ab" + "test", False),
                 ("about test", True), ("a bit testing", True),
                 ("c" + "abtest" + "ing", True))


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (": " + str(detail) if detail and not ok else ""), flush=True)
    if not ok:
        FAILS.append(name)


def command(script, *args, cwd=None):
    return subprocess.run([sys.executable, "-X", "utf8", "-I", "-B", str(script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd,
                          env=trials.compose.rt.python_env(), timeout=2400)


def pure_reel(root):
    words = "Clear cuts make edits easy to finish today with 3 ideas".split()
    reel = root / "videos/REEL_A"
    doc = {"schema": 1, "reel": "REEL_A", "fps": 30, "words": "work/edit_map.cut.json",
           "beats": [{"id": "b1", "start_f": 0, "end_f": 60,
                      "speech_anchor": {"text": " ".join(words), "w0": 0, "w1": len(words) - 1},
                      "layout": "full", "value": None, "scene": None, "broll": None, "transition": None}],
           "word_marks": [], "proposed": {}, "notes": {}, "needs": "", "sent_at": None,
           "edit_style": {"style": "punch-in", "punch_scale": 1.18}, "caption_style": {"style": "none"}}
    trials.save(reel / "beat-map-selection.json", doc)
    trials.save(reel / "work/edit_map.cut.json", {"words": [
        {"word": word, "start": i * .12, "end": i * .12 + .1} for i, word in enumerate(words)]})
    return reel, doc, " ".join(words)


def spec_rows():
    return [{"id": "t1", "change": "opening", "scene": "hook-title",
             "slots": {"kicker": "Clear cuts", "title": "Make edits easy"}, "params": {}},
            {"id": "t2", "change": "hook", "hook_text": "Finish today"},
            {"id": "t3", "change": "grade", "look": "warm", "strength": .8}]


def refused(spec, doc, source):
    try:
        trials.validate_spec(spec, doc, source, "none")
    except trials.Stop as error:
        return str(error)
    return ""


def check_wording_payloads():
    for index, (text, allowed) in enumerate(WORDING_CASES):
        for label, payload in (("hook_text", {"versions": [{"hook_text": text}]}),
                               ("selection note", {"versions": [{"id": "t1", "choice": "keep", "note": text}]})):
            try:
                trials.honest(payload)
                accepted = True
            except trials.Stop:
                accepted = False
            ck(f"wording {index} {label}", accepted == allowed)


def case_selftest(root):
    for script in (trials.HERE / "trials.py", trials.compose.HERE / "compose.py",
                   trials.compose.HERE / "beat_schema.py"):
        p = command(script, "--selftest")
        ck(script.name + " selftest", p.returncode == 0 and "selftest ok" in p.stdout, p.stdout + p.stderr)
    with patch.object(trials.compose.styles.standing_notes, "record_pick") as remember:
        trials.compose.styles.pick_style({"edit_style": {"style": "punch-in"}}, remember=False)
        ck("scratch camera planning never records a taste pick", not remember.called)
    case_loops(root)


def case_footage(root):
    fc = trials.compose.footage_check
    for mode in ("logged", "legacy", "no_broll", "unlogged"):
        reel, doc, _ = pure_reel(root / mode)
        clip = reel / "footage/own.mp4"
        clip.parent.mkdir(parents=True)
        clip.write_bytes(b"your own B-roll")
        ident = fc.add(reel, clip, role="broll", origin="own", licence="own") if mode in ("logged", "legacy") else "f01"
        if mode == "legacy":
            rows = fc.rows(reel)
            rows[0]["path"] = str(clip)
            rows[0].pop("size", None)
            trials.save(reel / "footage/ledger.json", rows)
        if mode != "no_broll":
            doc["beats"][0].update(start_f=90, end_f=120,
                broll={"src": "footage/own.mp4", "in": 0, "out": 30, "ledger_id": ident})
        ledger = reel / "footage/ledger.json"
        before = ledger.read_bytes() if ledger.exists() else None

        def render(scratch, tier, hook, **kwargs):
            trials.compose.broll_plan({"reel_dir": scratch, "beats": doc["beats"],
                                      "rate": 30, "total": 300, "cut_frames": []})
            output = scratch / "renders/preview.mp4"
            output.parent.mkdir()
            output.write_bytes(b"preview")
            return {"out": "renders/preview.mp4"}

        with patch.object(trials.compose, "render", side_effect=render), \
                patch.object(trials.compose.fpsmod, "frame_count", return_value=30):
            for ident in ("t1", "t2", "t3"):
                destination = reel / "trials" / ident / "preview.mp4"
                try:
                    trials.scratch_render(reel, doc, None, destination)
                except trials.compose.Stop as error:
                    ck(mode + " " + ident + " ledger check", mode == "unlogged"
                       and "log exactly one footage ledger entry" in str(error), str(error))
                    ck("unlogged clip never renders", not destination.exists())
                else:
                    ck(mode + " " + ident + " ledger check", mode != "unlogged"
                       and destination.read_bytes() == b"preview")
        ck(mode + " source ledger unchanged", (ledger.read_bytes() if ledger.exists() else None) == before)


def case_style_context(root):
    from editor_test_state import isolated_home
    with isolated_home():
        reel, doc, _ = pure_reel(root)
        ss = trials.saved_style
        ss.save({"accent": "#123ABC"}, "chosen")
        ss.pick(reel, "chosen")
        destination = reel / "trials/t1/preview.mp4"

        def render(scratch, tier, hook, **kwargs):
            assert kwargs.get("style_reel") == reel, "Trial lost the source reel's pick"
            assert ss.load(scratch) == {}, "Scratch folder silently inherited a pick"
            assert ss.load(kwargs["style_reel"])["accent"] == "#123ABC"
            output = scratch / "renders/preview.mp4"
            output.parent.mkdir(parents=True)
            output.write_bytes(b"preview")
            return {"out": "renders/preview.mp4"}

        with patch.object(trials.compose, "render", side_effect=render):
            trials.scratch_render(reel, doc, None, destination)
        ck("trial scratch keeps explicit source style context", destination.read_bytes() == b"preview")
        assert len(ss._index()["picks"]) == 1, "Trial left a temporary reel pick behind"
        before = trials.hashes(reel)
        ss.save({"accent": "#ABCDEF"}, "other")
        ss.pick(root / "other-reel", "other")
        ss.set_default("other")
        assert trials.hashes(reel) == before, "Another reel's pick changed trial inputs"
        ss.save({"accent": "#ABCDEF"}, "chosen")
        assert trials.hashes(reel) != before, "A changed chosen style did not invalidate the trial"
        ck("trial hashes follow this reel's chosen style", True)


def case_spec(root):
    check_wording_payloads()
    reel, doc, source = pure_reel(root)
    good = {"versions": spec_rows()}
    ck("valid three changes", not refused(good, doc, source))
    for label, key, value in (("two changes", "hook_text", "extra"), ("speed", "speed", 1.02),
                              ("fps", "fps", 24), ("cuts", "cuts", [])):
        bad = copy.deepcopy(good)
        bad["versions"][0][key] = value
        ck(label + " refused", bool(refused(bad, doc, source)))
    for hook, allowed in (("5x easier", False), ("3 ideas", True)):
        bad = copy.deepcopy(good)
        bad["versions"][1]["hook_text"] = hook
        line = refused(bad, doc, source)
        ck("hook number " + hook, not line if allowed else "5x" in line, line)
    for index, (text, allowed) in enumerate(WORDING_CASES):
        for field in ("hook_text", "note"):
            candidate = copy.deepcopy(good)
            candidate["versions"][1][field] = text
            line = refused(candidate, doc, source)
            ck(f"spec wording {index} {field}", not line if allowed else "honest" in line, line)
    for mutation in ({"id": "../escape"}, {"id": "base"}, {"change": ["hook", "grade"]},
                     {"hook_text": doc["beats"][0]["speech_anchor"]["text"]}):
        bad = copy.deepcopy(good)
        bad["versions"][1].update(mutation)
        ck("invalid or unchanged trial refused", bool(refused(bad, doc, source)))
    for row in good["versions"]:
        changed = trials.apply_version(doc, row)
        if row["change"] == "opening":
            expected = copy.deepcopy(doc)
            expected["beats"][0]["scene"] = {"id": row["scene"], "slots": row["slots"], "params": {}}
            ck("opening changes only scene", changed == expected)
        else:
            ck(row["change"] + " leaves Send unchanged", changed == doc)
    bad_spec = root / "bad-spec.json"
    trials.save(bad_spec, {"versions": [dict(spec_rows()[1], hook_text="5x easier"), spec_rows()[2]]})
    p = command(trials.HERE / "trials.py", "plan", "--reel-dir", reel, "--spec", bad_spec)
    ck("failed command has one line and no traceback", p.returncode != 0 and
       len((p.stdout + p.stderr).strip().splitlines()) == 1 and "Traceback" not in p.stdout + p.stderr)
    ck("invalid plan writes nothing", not (reel / "trials/trials.json").exists())
    with patch.object(trials.saved_style, "path", return_value=root / "saved-style.json"):
        before = trials.hashes(reel)
        for name in ("trials.state.json", "trials.state.json.prev", "trials.state.json.tmp",
                     "trials.state.json.prev.tmp", "trials-selection.json", "trials-selection.json.tmp"):
            trials.save(reel / name, {"versions": [{"id": "t1", "choice": "keep", "note": "Clear opening"}]})
        ck("trial review and Send do not invalidate base hashes", trials.hashes(reel) == before)


def case_loops(root):
    reel, doc, source = pure_reel(root)
    words = source.split()
    ck("old Send remains valid", not beat_schema.beat_map_problems(doc, words))
    ck("absent ledger does nothing", loop_check.run({"reel_dir": reel}) == [])
    row = {"question": "What helps?", "on_screen": "List", "setup_f": 0, "updates_f": [10, 20],
           "closure_f": 45, "closure_words": "finish today", "cta_f": 50}
    good = dict(doc, loops=[row])
    trials.save(reel / "beat-map-selection.json", good)
    ck("good ledger schema", not beat_schema.beat_map_problems(good, words))
    ck("good ledger QA", loop_check.run({"reel_dir": reel}) == [])
    for label, changes in (("closure before setup", {"closure_f": 0}),
                           ("CTA before closure", {"cta_f": 30}),
                           ("update after closure", {"updates_f": [46]}),
                           ("unsaid closure", {"closure_words": "never spoken"}),
                           ("late spoken closure", {"closure_f": 15, "updates_f": [], "cta_f": 50})):
        mutant = dict(good, loops=[dict(row, **changes)])
        trials.save(reel / "beat-map-selection.json", mutant)
        timed = trials.read(reel / "work/edit_map.cut.json")["words"]
        ck(label + " schema", bool(beat_schema.beat_map_problems(mutant, words, timed)))
        ck(label + " QA", bool(loop_check.run({"reel_dir": reel})))


def media_fixture(root):
    from handoff_test import fixture
    from editor_test_state import copy_tool_state
    original_state = trials.compose.rt.state_dir()
    reel, master = fixture(root)
    # The shared fixture's first beat is 1.4 s; the title scene requires 1.5 s.
    doc = trials.read(reel / "beat-map-selection.json")
    doc["beats"][0]["end_f"] = 48
    doc["beats"][1]["start_f"] = 48
    doc["caption_style"] = {"style": "none"}
    trials.save(reel / "beat-map-selection.json", doc)
    home = copy_tool_state(original_state, root / "tool-state", packages=True)
    return reel, home


def protected(reel):
    return {str(p.relative_to(reel)): trials.digest(p) for p in reel.rglob("*")
            if p.is_file() and "trials" not in p.relative_to(reel).parts}


def render_case(root, rows, *, compare_openings=False):
    reel, home = media_fixture(root)
    spec = root / "spec.json"
    trials.save(spec, {"versions": rows})
    with patch.dict(os.environ, EDITOR_SE_HOME=str(home)):
        # The shared fixture supplies a stand-in approval. Establish an actual
        # composed, approved 720p base before measuring protection or variations.
        for action in ("preview", "ok"):
            p = command(trials.compose.HERE / "compose.py", action, "--reel-dir", reel, cwd=root)
            ck("real base " + action, p.returncode == 0, p.stdout + p.stderr)
            if p.returncode:
                return
        before = protected(reel)
        for args in (("plan", "--reel-dir", reel, "--spec", spec), ("render", "--reel-dir", reel)):
            p = command(trials.HERE / "trials.py", *args, cwd=root)
            ck("trials " + args[0], p.returncode == 0, p.stdout + p.stderr)
            if p.returncode:
                return
        report = trials.read(reel / "trials/trials-report.json")
        base = report["base"]
        ck("every requested version rendered", [row["id"] for row in report["versions"]] ==
           [row["id"] for row in rows])
        ck("base file inside trials", (reel / base["file"]).is_file() and base["file"].startswith("trials/base/"))
        for row in report["versions"]:
            path = reel / row["file"]
            ck(row["id"] + " file in trials", path.is_file() and row["file"].startswith("trials/" + row["id"] + "/"))
            ck(row["id"] + " SHA", trials.digest(path) == row["sha256"])
            ck(row["id"] + " frames equal", row["frames"] == base["frames"])
            ck(row["id"] + " audio identical", row["audio_md5"] == base["audio_md5"])
            checks = trials.verify(reel / base["file"], path, row["change"], report["opening_f"])
            ck(row["id"] + " independent picture/audio checks", all(checks[k] for k in
               ("frames_equal", "fps_equal", "audio_equal", "picture_ok")), checks)
            if compare_openings:
                declared = next(version for version in rows if version["id"] == row["id"])
                expected = trials.read(reel / "trials/base/beat-map-selection.json")
                if declared["change"] == "opening":
                    expected["beats"][0]["scene"] = {"id": declared["scene"], "slots": declared["slots"],
                                                      "params": declared.get("params", {})}
                ck(row["id"] + " exactly one declared field", row["declared"] == declared and
                   trials.read(path.parent / "beat-map-selection.json") == expected)
                ck(row["id"] + " opening differs and later frames match", checks["opening_differs"] and
                   checks["after_matches"] and report["opening_f"] < base["frames"], checks)
        if compare_openings:
            for left, right in combinations(report["versions"], 2):
                values = trials.frame_differences(reel / left["file"], reel / right["file"], base["frames"])
                inside = values[:report["opening_f"]]
                ck(left["id"] + "/" + right["id"] + " distinct openings",
                   bool(inside) and sum(inside) / len(inside) > trials.DIFFER_MAD, inside)
        # Re-plan after a source mutation must invalidate all previously reported outputs.
        original = (reel / "beat-map-selection.json").read_bytes()
        mutant = trials.read(reel / "beat-map-selection.json")
        mutant["needs"] = "Revised"
        trials.save(reel / "beat-map-selection.json", mutant)
        p = command(trials.HERE / "trials.py", "render", "--reel-dir", reel, "--only", rows[0]["id"], cwd=root)
        ck("stale inputs refused", p.returncode != 0 and "changed" in p.stdout)
        (reel / "beat-map-selection.json").write_bytes(original)
        first_row = report["versions"][0]
        first_path = reel / first_row["file"]
        import shutil
        def unchanged_picture(reel_dir, doc, hook, destination):
            shutil.copyfile(reel_dir / base["file"], destination)
        try:
            with patch.object(trials, "scratch_render", unchanged_picture):
                trials.render(reel, only=first_row["id"])
            ck("failed picture comparison refused", False)
        except trials.Stop:
            ck("failed picture comparison deletes version file", not first_path.exists())
            failed = trials.read(reel / "trials/trials-report.json")
            ck("failed version removed from report", first_row["id"] not in [r["id"] for r in failed["versions"]])
    ck("all original files byte identical; no new renders", protected(reel) == before)
    case_wording(root)


def case_render(root):
    render_case(root, spec_rows())


def case_openings(root):
    render_case(root, [
        {"id": "o1", "change": "opening", "scene": "hook-title",
         "slots": {"kicker": "Clear cuts", "title": "Make edits easy"}, "params": {"entrance": "none"}},
        {"id": "o2", "change": "opening", "scene": "slots",
         "slots": {"label1": "Clear cuts", "label2": "Finish today", "label3": "", "label4": "",
                   "label5": "", "label6": ""}, "params": {"count": 2, "section_starts": "0.4,1.0"}},
        {"id": "o3", "change": "hook", "hook_text": "Finish today"}], compare_openings=True)


def case_reframe(root):
    render_case(root, [{"id": "r1", "change": "reframe", "field": "edit_style.moves.push",
                        "value": {"segments": "all", "to": 1.15}},
                       {"id": "r2", "change": "hook", "hook_text": "Make edits easy"}])


def case_wording(root):
    check_wording_payloads()
    paths = list((P / "skills/reel-trials").rglob("*")) + list((P / "scenes/slots").rglob("*"))
    paths += [P / "skills/reel-canvas-build/boards/beat-map/index.html"]
    paths += list(root.rglob("trials/*.json")) + list(root.rglob("trials/*/*.json"))
    bad = []
    for path in paths:
        if path.is_file() and path.suffix in (".md", ".html", ".json", ".py"):
            if trials.FORBIDDEN.search(path.read_text(encoding="utf-8")):
                bad.append(path.name)
    ck("honest wording in shipped files and outputs", not bad, bad)


def case_scene(root):
    import scene_check
    if not (P / "scenes/slots/preview.png").is_file():
        p = command(HERE / "scene_render_test.py", "--scene", "slots", "--part", "base", "--write-previews")
        ck("render real slots preview", p.returncode == 0, p.stdout + p.stderr)
    problems = scene_check.scene_problems(P / "scenes/slots")
    ck("slots scene contract and real preview", not problems, problems)
    fill = {"id": "slots", "slots": {"label1": "Clear cuts", "label2": "Easy edits",
            "label3": "", "label4": "", "label5": "", "label6": ""},
            "params": {"count": 2, "section_starts": "1,2"}}
    ck("valid optional slots fill", not scene_check.fill_problems("slots", fill, words=["Clear", "cuts"]))
    fill["slots"]["label1"] = "5x easier"
    ck("slots unsaid number blocked", any("5x" in s for s in scene_check.fill_problems("slots", fill, words=["Clear"])))


def case_hub(root):
    import hub_test
    p = hub_test.Proof(root)
    try:
        reel = p.videos / "reel-01"
        for ident in ("base", "t1", "t2"):
            dst = reel / "trials" / ident / "trial.mp4"
            dst.parent.mkdir(parents=True)
            import shutil
            shutil.copyfile(p.clip, dst)
        trials.save(reel / "trials/trials-report.json", {"base": {"id": "base", "file": "trials/base/trial.mp4"},
                    "versions": [{"id": "t1", "change": "hook", "description": "Hook title: Clear cuts",
                                  "file": "trials/t1/trial.mp4"},
                                 {"id": "t2", "change": "grade", "description": "Colour look: warm",
                                  "file": "trials/t2/trial.mp4"}]})
        p.refresh()
        actions = [{"do": "click", "sel": "#tab-trials"},
                   {"do": "frame", "sel": "#panel iframe", "wait": "#versions video"}]
        note_actions = []
        for index, (text, allowed) in enumerate(WORDING_CASES):
            if allowed:
                continue
            note_actions.extend([{"do": "set", "sel": "#note-t1", "value": text},
                {"do": "click", "sel": "#send"},
                {"do": "eval", "js": "JSON.stringify({blocked:document.querySelector('#status').dataset.state==='error',valid:validWords()})"}])
        results = p.browse(actions + [{"do": "set", "sel": "#choice-t1", "value": "keep"},
                                     {"do": "set", "sel": "#choice-t2", "value": "skip"}] + note_actions)
        for index, result in enumerate(results):
            ck(f"board refuses selection note {index}", result["blocked"] and not result["valid"] and
               not (reel / "trials-selection.json").exists())
        data = p.browse(actions + [{"do": "eval", "js": "JSON.stringify({n:document.querySelectorAll('video').length,"
             "muted:Array.from(document.querySelectorAll('video'),v=>v.muted)})"},
             {"do": "set", "sel": "#choice-t1", "value": "keep"},
             {"do": "set", "sel": "#choice-t2", "value": "skip"},
             {"do": "set", "sel": "#note-t1", "value": "Clear opening"},
             {"do": "click", "sel": "#watch-opening"}, {"do": "click", "sel": "#send"},
             {"do": "waitFn", "js": "document.querySelector('#status').dataset.state==='sent'"}])[0]
        ck("Trial reels tab plays base and versions", data["n"] == 3 and all(data["muted"]))
        selection = trials.read(reel / "trials-selection.json")
        ck("keep/skip and note Send", selection["versions"] == [
            {"id": "t1", "choice": "keep", "note": "Clear opening"}, {"id": "t2", "choice": "skip", "note": ""}])
        p.browse([{"do": "set", "sel": "#request-detail", "value": "Three openings from these words"},
                  {"do": "click", "sel": "[data-skill=trial]"},
                  {"do": "waitFn", "js": "Hub.pending===0"}])
        request = trials.read(reel / "hub-requests.json")[-1]
        ck("existing trial button routes", request["skill"] == "trial" and
           "`trial` | Invoke `editor-superengine:reel-trials`" in
           (p.plugin / "skills/editor-doctor/references/hub.md").read_text(encoding="utf-8"))
    finally:
        p.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", choices=(*CASES, "all"), default="all")
    ap.add_argument("--locked", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()
    blocked = 0
    for name in CASES if args.case == "all" else (args.case,):
        if name in ("render", "openings", "reframe", "scene") and not args.locked:
            if not HEAVY.is_file():
                print("BLOCKED " + name + ": heavy_lock.py is missing", flush=True)
                blocked = 75
                continue
            p = command(HEAVY, "--wait", "600", "--min-gb", "3", "--", sys.executable,
                        "-X", "utf8", "-I", Path(__file__), "--case", name, "--locked")
            print(p.stdout + p.stderr, end="")
            if p.returncode in (75, 76):
                blocked = p.returncode
            else:
                ck(name + " locked proof", p.returncode == 0)
            continue
        try:
            with tempfile.TemporaryDirectory(prefix="editor-n5-") as temp:
                globals()["case_" + name](Path(temp))
        except Exception as error:
            if type(error).__name__ == "Blocked":
                print("BLOCKED " + name + ": shared browser lock unavailable", flush=True)
                blocked = 75
            else:
                ck(name, False, str(error))
    print(f"{len(FAILS)} failed" + (f", blocked exit {blocked}" if blocked else ""))
    return 1 if FAILS else blocked


if __name__ == "__main__":
    sys.exit(main())
