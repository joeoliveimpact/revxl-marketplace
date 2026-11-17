"""SX.1 proof: automatic effect levels, bake, board parity and useful mix failures.

Run with EDITOR_SE_HOME=<state> <state python> -X utf8 -I tests/editor/sx_level_test.py [--case NAME].
Synthetic media only; no network and no changes to the installed editor state.
"""
import argparse, ast, contextlib, io, json, math, re, subprocess, sys, tempfile
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
import numpy as np

PLUGIN = Path(__file__).resolve().parents[2] / "plugins/editor-superengine"
S = PLUGIN / "skills/reel-sound-pass/scripts"
sys.path.insert(0, str(S))
import _media as M
import bake, measure_sfx, mix_check

results = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % detail), flush=True)
    results.append(bool(ok))


def write(path, obj):
    path.write_bytes((json.dumps(obj, indent=1) + "\n").encode("utf-8"))


def tone(seconds, amp=0.4):
    t = np.arange(round(seconds * M.SR)) / M.SR
    x = amp * np.sin(2 * np.pi * 1000 * t)
    return np.stack([x, x], 1).astype(np.float32)


def fixture(root):
    (root / "sfx").mkdir()
    (root / "beds").mkdir()
    M.write_wav(root / "sfx/short.wav", tone(0.15))
    M.write_wav(root / "sfx/steady.wav", tone(0.6))
    x = tone(0.6, 0.0001)
    x[100:110] = 0.95
    M.write_wav(root / "sfx/click.wav", x)
    subprocess.run([M.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "color=s=32x32:r=30:d=3",
                    "-f", "lavfi", "-i", "sine=f=220:d=3", "-c:v", "mpeg4", "-c:a", "pcm_s16le",
                    "-shortest", str(root / "locked.mov")], check=True)
    (root / "work/renders").mkdir(parents=True)
    subprocess.run([M.ffmpeg(), "-v", "error", "-y", "-i", str(root / "locked.mov"),
                    "-c:v", "copy", "-c:a", "aac", str(root / "work/renders/master-fixture.mp4")], check=True)


def cues(root):
    out = []
    for i, name in enumerate(("click.wav", "steady.wav", "short.wav")):
        peak = float(20 * np.log10(np.abs(M.decode(root / "sfx" / name)).max()))
        out.append(dict(id="c%d" % i, file=name, time=0.5 + i * 0.8, beat="Beat %d" % i,
                        source_peak_dbfs=peak, gain_db=round(-1 - peak, 1), gain_by_hand=False))
    return out


def baked(root, rows, **extra):
    write(root / "sound-selection.json", dict(cues=rows, **extra))
    before = (root / "sound-selection.json").read_bytes()
    placement = bake.bake(root, root / "locked.mov")
    ck("bake leaves the Send untouched", (root / "sound-selection.json").read_bytes() == before)
    return placement, json.loads((root / "sound/levels.json").read_text(encoding="utf-8"))


def case_short(root, L):
    own = L.own_loudness(root / "sfx/short.wav")
    p = L.plan([cues(root)[2]], {"short.wav": own})
    ck("short: 150 ms has finite loudness and a plan row", math.isfinite(own) and len(p["cues"]) == 1)
    ck("short: empty plan has no target", L.plan([], {}) == dict(target=None, auto_level=True, cues=[]))
    unknown = dict(cues(root)[2], source_peak_dbfs=None)
    q = L.plan([unknown], {"short.wav": own})["cues"][0]
    ck("short: unknown peak has no ceiling", q["ceiling"] is None and q["gain"] == q["wanted"] and not q["capped"])
    cached = {"hits": [dict(file="short.wav", max_m_lufs=-23.4)]}
    write(root / "sfx_measured.json", cached)
    ck("short: cached measurement is preferred", L.level(root, [cues(root)[2]], True)["cues"][0]["own"] == -23.4)


def case_silent(root, L):
    M.write_wav(root / "sfx/silent.wav", np.zeros((7200, 2), np.float32))
    M.write_wav(root / "sfx/near-silent.wav", tone(0.6, 0.0001))
    rows = [dict(id="silent", file="silent.wav", beat="Silent beat", time=0.5, gain_db=-11.25,
                 source_peak_dbfs=None, gain_by_hand=False),
            dict(id="near", file="near-silent.wav", beat="Quiet beat", time=1.3, gain_db=4.125,
                 source_peak_dbfs=-80, gain_by_hand=False),
            dict(cues(root)[1], time=2.1, gain_db=12)]
    ck("silent: silence and -80 dBFS return no loudness",
       all(L.own_loudness(root / "sfx" / c["file"]) is None for c in rows[:2]))
    uncached = L.level(root, rows, True)
    ck("silent: uncached effects are skipped", [c["skipped"] for c in uncached["cues"]] == [True, True, False])
    measure_sfx.measure_dir(root)
    measured = json.loads((root / "sfx_measured.json").read_text(encoding="utf-8"))
    hits = {c["file"]: c for c in measured["hits"]}
    ck("silent: library measurement writes null for both quiet effects",
       all("max_m_lufs" in hits[c["file"]] and hits[c["file"]]["max_m_lufs"] is None for c in rows[:2]))
    with patch.object(L, "own_loudness", side_effect=AssertionError("cached null must not be re-measured")):
        cached = L.level(root, rows, True)
        placement, p = baked(root, rows)
    ck("silent: cached nulls are honored", cached == uncached == p)
    ck("silent: baked quiet gains stay exactly as sent",
       [c["gain_db"] for c in placement["cues"][:2]] == [c["gain_db"] for c in rows[:2]])
    ck("silent: placement carries skipped booleans from the level plan",
       [c.get("skipped") for c in placement["cues"]] == [True, True, False]
       and all(isinstance(c.get("skipped"), bool) for c in placement["cues"]))
    ck("silent: skipped rows have null own/wanted and no cap",
       all(c["skipped"] and c["own"] is None and c["wanted"] is None and not c["capped"] for c in p["cues"][:2]))
    normal = L.plan(rows[2:], {rows[2]["file"]: hits[rows[2]["file"]]["max_m_lufs"]})
    ck("silent: normal cue is levelled with unchanged target", p["target"] == normal["target"]
       and p["cues"][2] == normal["cues"][0] and placement["cues"][2]["gain_db"] != rows[2]["gain_db"])
    all_quiet, quiet_plan = baked(root, rows[:2])
    ck("silent: all skipped cues bake with no target", quiet_plan["target"] is None
       and all(c["skipped"] for c in quiet_plan["cues"])
       and [c["gain_db"] for c in all_quiet["cues"]] == [c["gain_db"] for c in rows[:2]])
    output = io.StringIO()
    with patch.object(L, "workspace", return_value=(root.parent, root.parent)), contextlib.redirect_stdout(output):
        rc = L.main(["--reel", root.name])
    ck("silent: CLI prints skipped cues without crashing", rc == 0 and "skipped" in output.getvalue())
    try:
        L.own_loudness(root / "sfx/missing.wav")
    except (ValueError, RuntimeError):
        ck("silent: missing file remains an error", True)
    else:
        ck("silent: missing file remains an error", False)


def case_peaky(root, L):
    rows = cues(root)
    placement, p = baked(root, rows)
    click = p["cues"][0]
    ck("peaky: wanted gain exceeds ceiling and is capped", click["wanted"] > click["ceiling"]
       and click["capped"] and click["gain"] == click["ceiling"], click)
    peak = 20 * np.log10(np.abs(M.decode(root / "sound" / placement["cues"][0]["file"])).max())
    ck("peaky: baked click stays <= -0.9 dBFS", peak <= -0.9, peak)
    ck("peaky: placement reports automatic cap", placement["cues"][0]["auto"] and placement["cues"][0]["capped"])


def by_hand_inputs(root, L):
    rows = cues(root)
    rows[0].update(gain_db=-7.25, gain_by_hand=True)
    rows.append(dict(rows[1], id="hand-default", beat="Hand at default", time=2.4, gain_by_hand=True))
    own = {c["file"]: L.own_loudness(root / "sfx" / c["file"]) for c in rows}
    return rows, own


def assert_by_hand_plan(rows, p):
    hand, auto = p["cues"][3], p["cues"][1]
    assert rows[3]["gain_db"] == rows[1]["gain_db"] == round(-1 - rows[3]["source_peak_dbfs"], 1)
    assert p["cues"][0]["gain"] == -7.25 and p["cues"][0]["by_hand"]
    assert hand["by_hand"] and hand["gain"] == rows[3]["gain_db"] and not hand["capped"], hand
    assert not auto["by_hand"] and auto["gain"] != rows[1]["gain_db"], auto


def case_by_hand(root, L):
    rows, own = by_hand_inputs(root, L)
    planned = L.plan(rows, own)
    assert_by_hand_plan(rows, planned)
    ck("by_hand: explicit flag preserves default gain while sibling is levelled", True)
    placement, p = baked(root, rows)
    ck("by_hand: bake uses the asserted plan", p == planned)
    ck("by_hand: exact gain survives bake", placement["cues"][0]["gain_db"] == -7.25)
    ck("by_hand: default hand gain survives bake, automatic sibling is levelled",
       placement["cues"][3]["gain_db"] == rows[3]["gain_db"] and not placement["cues"][3]["auto"]
       and placement["cues"][1]["gain_db"] == p["cues"][1]["gain"]
       and placement["cues"][1]["gain_db"] != rows[1]["gain_db"] and placement["cues"][1]["auto"])
    ck("by_hand: no automatic cap or level", p["cues"][0]["by_hand"] and not p["cues"][0]["capped"]
       and not placement["cues"][0]["auto"])
    expected = round(float(np.median([own[c["file"]] + c["gain_db"] for c in rows])), 1)
    ck("by_hand: hand gain still counts in median", p["target"] == expected)


def case_mutant_flag(root, L):
    rows, own = by_hand_inputs(root, L)
    assert_by_hand_plan(rows, L.plan(rows, own))
    original = L.is_by_hand

    def heuristic_only(cue):
        peak = cue.get("source_peak_dbfs")
        return peak is not None and abs(cue.get("gain_db", 0) - round(-1 - peak, 1)) > 0.05

    rejected = False
    with patch.object(L, "is_by_hand", heuristic_only):
        try:
            assert_by_hand_plan(rows, L.plan(rows, own))
        except AssertionError:
            rejected = True
    ck("mutant_flag: by_hand plan assertions reject heuristic-only mutant", rejected)
    ck("mutant_flag: is_by_hand restored", L.is_by_hand is original)


def case_old_send(root, L):
    rows = cues(root)[:2]
    for c in rows:
        del c["gain_by_hand"]
    rows[0]["gain_db"] -= 3
    placement, p = baked(root, rows)
    ck("old_send: only untouched cue is automatic", [c["auto"] for c in placement["cues"]] == [False, True])
    ck("old_send: hand tweak stays, untouched is levelled", p["cues"][0]["gain"] == rows[0]["gain_db"]
       and p["cues"][1]["gain"] != rows[1]["gain_db"])
    ck("old_send: explicit false overrides old heuristic", not L.is_by_hand(dict(rows[0], gain_by_hand=False)))


def case_auto_off(root, L):
    rows = cues(root)
    rows[1].update(gain_db=-4.125, gain_by_hand=True)
    rows[2].update(gain_db=-2)
    placement, p = baked(root, rows, auto_level=False)
    ck("auto_off: every sent gain survives", [c["gain_db"] for c in placement["cues"]] == [c["gain_db"] for c in rows])
    ck("auto_off: no cap or automatic flags", not p["auto_level"]
       and all(not c["auto"] and not c["capped"] for c in placement["cues"]))


def case_parity(root, L):
    import runtime as rt
    html = (S.parent / "boards/sound-board/index.html").read_text(encoding="utf-8")
    block = re.search(r"/\* level-rule:start \*/(.*?)/\* level-rule:end \*/", html, re.S)
    ck("parity: marked self-contained rule exists", block is not None)
    if not block:
        return
    rows = cues(root)
    own = {c["file"]: L.own_loudness(root / "sfx" / c["file"]) for c in rows}
    cases = [(rows, own, True), (rows, own, False), ([], {}, True),
             ([dict(c, gain_by_hand=True) for c in rows], own, True),
             ([dict(c, source_peak_dbfs=None) for c in rows], own, True),
             ([{k: v for k, v in c.items() if k != "gain_by_hand"} for c in rows], own, True)]
    # Exact half ties exercise the same one-decimal rounding in both languages.
    cases.append(([dict(rows[0], gain_db=0.25), dict(rows[1], gain_db=0.25)],
                  {rows[0]["file"]: -30, rows[1]["file"]: -10}, True))
    quiet = dict(rows[0], id="silent", file="silent.wav", gain_db=-11.25)
    cases.extend([([*rows, quiet], dict(own, **{"silent.wav": None}), True),
                  ([quiet], {"silent.wav": None}, True), ([quiet], {}, True),
                  ([*rows, quiet], dict(own, **{"silent.wav": None}), False)])
    js = block[1] + "\nconst cases=" + json.dumps(cases) + ";console.log(JSON.stringify(cases.map(c=>levelPlan(...c))));"
    p = subprocess.run([rt.tool("node"), "-e", js], capture_output=True, text=True, check=True)
    ck("parity: target, gains, caps and all rows match Python", json.loads(p.stdout) == [L.plan(*c) for c in cases], p.stdout)


def report_line():
    tree = ast.parse((S / "mix.py").read_text(encoding="utf-8"))
    run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run")
    branch = next(n for n in reversed(run.body) if isinstance(n, ast.If) and isinstance(n.test, ast.UnaryOp)
                  and isinstance(n.test.operand, ast.Subscript) and isinstance(n.test.operand.value, ast.Name)
                  and n.test.operand.value.id == "report")
    wrapper = ast.parse("def report_line(report):\n    pass\n")
    wrapper.body[0].body = [branch]
    namespace = {}
    exec(compile(ast.fix_missing_locations(wrapper), "report-line", "exec"), namespace)
    return namespace["report_line"]


def case_why(root, L):
    sound = root / "sound"
    (sound / "cues").mkdir(parents=True)
    n = 3 * M.SR
    rng = np.random.default_rng(10)
    voice = rng.normal(0, 0.12, (n, 2)).astype(np.float32)
    final = voice + rng.normal(0, 0.002, (n, 2)).astype(np.float32)
    M.write_wav(sound / "voice.wav", voice)
    M.write_wav(sound / "music.wav", np.zeros_like(voice))
    M.write_wav(root / "final.wav", final)
    placement = dict(lanes=3, bed=dict(file="music.wav"), cues=[])
    for i, name in enumerate(("Clipped beat", "Masked beat", "Premaster beat")):
        x = tone(0.2, 0.01)
        if i == 0:
            x[30, 0] = 1.0  # one channel only: mono averaging must not hide clipping
        file = "cues/%d.wav" % i
        M.write_wav(sound / file, x)
        placement["cues"].append(dict(id="private%d" % i, beat=name, file=file, lane=i,
                                      start_sample=i * M.SR, time=i, seconds=0.2))
    premaster = final.copy()
    premaster[2 * M.SR + 40, 1] = -1.01
    M.write_wav(sound / "premaster.wav", premaster)
    write(sound / "placement.json", placement)
    r = mix_check.check(root / "final.wav", sound / "voice.wav", sound)
    ck("why: clip, mask and premaster clipping distinguished", [c.get("why") for c in r["weak_cues"]]
       == ["clipped", "masked", "clipped"], r["weak_cues"])
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        rc = report_line()({"pass": False, "mix_check": r})
    text = output.getvalue()
    ck("why: message names beats and reasons, never ids", rc == 1 and "clipped" in text and "masked" in text
       and all(c["beat"] in text and c["id"] not in text for c in r["weak_cues"]), text)
    (sound / "premaster.wav").unlink()
    r = mix_check.check(root / "final.wav", sound / "voice.wav", sound)
    ck("why: absent premaster still classifies clip and mask", [c.get("why") for c in r["weak_cues"]]
       == ["clipped", "masked", "masked"])


def case_measure(root, L):
    M.write_wav(root / "beds/bed.wav", tone(0.8))
    measure_sfx.measure_dir(root)
    rows = json.loads((root / "sfx_measured.json").read_text(encoding="utf-8"))
    ck("measure: every hit has rounded max momentary loudness", all(isinstance(c.get("max_m_lufs"), float)
       and c["max_m_lufs"] == round(L.own_loudness(root / "sfx" / c["file"]), 1) for c in rows["hits"]))
    ck("measure: beds have no max_m_lufs", all("max_m_lufs" not in c for c in rows["beds"]))


def case_silent_msg(root, L):
    sound = root / "sound"
    (sound / "cues").mkdir(parents=True)
    rng = np.random.default_rng(11)
    voice = rng.normal(0, 0.12, (3 * M.SR, 2)).astype(np.float32)
    final = voice + rng.normal(0, 0.002, voice.shape).astype(np.float32)
    M.write_wav(sound / "voice.wav", voice)
    M.write_wav(sound / "music.wav", np.zeros_like(voice))
    M.write_wav(root / "final.wav", final)
    placement = dict(lanes=4, bed=dict(file="music.wav"), cues=[])
    for i, (beat, amp, skipped) in enumerate((("Silent beat", 0, None), ("Quiet beat", 0.0005, False),
                                              ("Skipped beat", 0.02, True), ("Masked beat", 0.02, False))):
        file = "cues/%d.wav" % i
        M.write_wav(sound / file, tone(0.2, amp))
        row = dict(id="private%d" % i, beat=beat, file=file, lane=i,
                   start_sample=i * M.SR // 2, time=i / 2, seconds=0.2)
        if skipped is not None:
            row["skipped"] = skipped
        placement["cues"].append(row)
    # A truly silent baked cue stays silent even when its premaster window clips.
    premaster = final.copy()
    premaster[40, 1] = 1.01
    M.write_wav(sound / "premaster.wav", premaster)
    write(sound / "placement.json", placement)
    r = mix_check.check(root / "final.wav", sound / "voice.wav", sound)
    ck("silent_msg: baked silence differs from skipped-but-audible masking",
       [c.get("why") for c in r["weak_cues"]] == ["silent", "silent", "masked", "masked"], r["weak_cues"])
    for cue in r["weak_cues"][:2]:
        beat = cue["beat"]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            rc = report_line()({"pass": False, "mix_check": {"weak_cues": [cue]}})
        text = output.getvalue()
        expected = "the sound effect on '%s' has no audible sound (pick another file for that moment on the Sound Board)" % beat
        ck("silent_msg: %s asks for another file without raise or masked" % beat,
           rc == 1 and expected in text and "masked" not in text.lower() and "raise" not in text.lower(), text)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        rc = report_line()({"pass": False, "mix_check": r})
    text = output.getvalue()
    ck("silent_msg: mixed report keeps silent advice separate from masked advice", rc == 1
       and all("the sound effect on '%s' has no audible sound (pick another file" % beat in text
               for beat in ("Silent beat", "Quiet beat"))
       and all("the sound effect on '%s' was masked" % beat in text
               and "the sound effect on '%s' has no audible sound" % beat not in text
               for beat in ("Skipped beat", "Masked beat")), text)


def main():
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    names = ["short", "silent", "silent_msg", "peaky", "by_hand", "mutant_flag", "old_send", "auto_off", "parity", "why", "measure"]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", choices=names + ["all"], default="all")
    a = ap.parse_args()
    for name in names if a.case == "all" else [a.case]:
        try:
            with tempfile.TemporaryDirectory(prefix="sx-level-") as tmp:
                root = Path(tmp)
                fixture(root)
                import level_sfx as L
                globals()["case_" + name](root, L)
        except Exception as e:
            ck(name + ": completed", False, "%s: %s" % (type(e).__name__, e))
    print("%d passed, %d failed" % (sum(results), len(results) - sum(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
