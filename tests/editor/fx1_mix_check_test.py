#!/usr/bin/env python3
"""FX1 round 12: judge cues on their loudest placed half-second, and explain failed mixes.

usage: python tests/editor/fx1_mix_check_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 only when no checks fail.
The real reel comes only from EDITOR_SE_TEST_REEL_W2C and is copied before use.
"""
import argparse, ast, contextlib, io, json, os, shutil, sys, tempfile, wave
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np

REPO = Path(__file__).resolve().parents[2]
P = REPO / "plugins/editor-superengine"
S = P / "skills/reel-sound-pass/scripts"
sys.path.insert(0, str(S))
import mix_check
import _media as M

SR = M.SR
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)), flush=True)
    if not ok:
        fails.append(name)
    return ok


def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes((json.dumps(obj, indent=1) + "\n").encode("utf-8"))


def wav(p, x):
    # PCM quantization supplies a realistic noise floor without faking decode or check.
    p.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.rint(np.clip(x, -1, 32767 / 32768) * 32768).astype("<i2")
    with wave.open(str(p), "wb") as f:
        f.setparams((2, 2, SR, 0, "NONE", "not compressed"))
        f.writeframes(pcm.tobytes())


def old_window(c, N, *placed):
    # Frozen base rule: the mutation must fail on exactly the same delivered samples.
    s = int(round(max(0.0, c["time"] - c.get("peak_s", 0)) * SR))
    e = min(N, s + int(min(c["seconds"], 0.5) * SR))
    return s, e


def first_audible_window(c, N, one, cue_start, cue_end):
    # Frozen 07fc83d rule: a quiet swell can qualify long before its useful hit.
    win = SR // 100
    starts = np.arange(cue_start, cue_end, win)
    audible = np.array([], dtype=int)
    if len(starts):
        power = np.add.reduceat(one[cue_start:cue_end] ** 2, starts - cue_start)
        power /= np.minimum(win, cue_end - starts)
        audible = starts[(power > 0) & (power >= power.max() * 10 ** (-40.0 / 10))]
    if len(audible):
        s = int(audible[0])
        e = min(N, cue_end, s + SR // 2)
    else:
        s = int(round(max(0.0, c["time"] - c.get("peak_s", 0)) * SR))
        e = min(N, cue_end, s + int(min(c["seconds"], 0.5) * SR))
    return s, e


def old_corr(final, sound, cue_id, window=old_window):
    placement = json.loads((sound / "placement.json").read_text(encoding="utf-8"))
    y = M.decode(final).astype(np.float64).mean(1)
    N = len(y)
    voice = mix_check.fit(N, M.decode(sound / "voice-mixed.wav").astype(np.float64).mean(1))
    bed = mix_check.fit(N, M.decode(sound / placement["bed"]["file"]).astype(np.float64).mean(1))
    lanes = [np.zeros(N) for _ in range(placement["lanes"])]
    for c in placement["cues"]:
        x = M.decode(sound / c["file"]).astype(np.float64).mean(1)
        one = np.zeros(N)
        start = c["start_sample"]
        end = min(N, start + len(x))
        one[start:end] = x[:max(0, end - start)]
        lanes[c["lane"]] += one
        if c["id"] == cue_id:
            target, target_one, target_start, target_end = c, one, start, end
    A = np.stack([voice] + lanes + [bed], 1)
    g, *_ = np.linalg.lstsq(A, y, rcond=None)
    s, e = window(target, N, target_one, target_start, target_end)
    own = (g[1 + target["lane"]] * target_one)[s:e]
    rest = (y - A @ g)[s:e] + own
    return float(np.corrcoef(rest, own)[0, 1]) if e - s > 1 and np.std(own) > 0 else 0.0


def result(final, sound):
    return mix_check.check(final, sound / "voice-mixed.wav", sound)


def survival(label, sound, present, missing):
    r = result(present, sound)
    ck(label + ": audible cues pass", r["pass"] and all(c["corr"] >= 0.9 for c in r["cues"]),
       [(c["id"], c["corr"]) for c in r["cues"]])
    corr = old_corr(present, sound, "c4")
    ck(label + ": old window rejects the same late cue", np.isfinite(corr) and corr < 0.9, corr)
    r = result(missing, sound)
    ck(label + ": absent late cue fails", not r["pass"] and any(
        c["id"] == "c4" and c["corr"] < 0.9 for c in r["weak_cues"]),
       [(c["id"], c["corr"]) for c in r["cues"]])


def synthetic(scratch):
    sound = Path(tempfile.mkdtemp(prefix="fx1-mix-synthetic-", dir=scratch)) / "sound"
    rng = np.random.default_rng(17)
    t = np.arange(7 * SR) / SR
    voice = 0.12 * np.sin(2 * np.pi * 173 * t) + rng.normal(0, 0.005, len(t))
    bed = 0.02 * np.sin(2 * np.pi * 61 * t)
    hit_t = np.arange(int(0.3 * SR)) / SR
    hit = 0.3 * np.sin(2 * np.pi * 1507 * hit_t) * np.sin(np.pi * hit_t / 0.3)
    late = np.concatenate([rng.normal(0, 10 ** (-70 / 20), int(0.59 * SR)), hit])
    ordinary = 0.2 * np.sin(2 * np.pi * 997 * hit_t)
    swell_t = np.arange(int(1.3 * SR)) / SR
    envelope = np.where(swell_t < 1, 10 ** ((-35 + 35 * swell_t) / 20),
                        np.exp(-10 * (swell_t - 1)))
    swell = 0.03 * np.sin(2 * np.pi * 2179 * swell_t) * envelope
    stereo = lambda x: np.stack([x, x], 1)
    for name, x in (("voice-mixed.wav", voice), ("music.wav", bed),
                    ("cues/late.wav", late), ("cues/ordinary.wav", ordinary),
                    ("cues/swell.wav", swell)):
        wav(sound / name, stereo(x))
    cues = []
    for cue_id, beat, file, start in (("c4", '"10"', "cues/late.wav", SR),
                                      ("c1", '"start"', "cues/ordinary.wav", 3 * SR),
                                      ("swell", '"swell"', "cues/swell.wav", int(4.5 * SR))):
        x = M.decode(sound / file)
        peak = int(np.argmax(np.abs(x.mean(1)))) / SR
        cues.append(dict(id=cue_id, beat=beat, file=file, start_sample=start, lane=0,
                         time=start / SR + peak, peak_s=peak, seconds=len(x) / SR))
    write(sound / "placement.json", dict(lanes=1, bed=dict(file="music.wav"), cues=cues))
    # The low gain makes -70 dB file noise fall below PCM's noise floor; the hit remains clear.
    base = M.decode(sound / "voice-mixed.wav") + M.decode(sound / "music.wav")
    late_mix = np.zeros_like(base)
    swell_mix = np.zeros_like(base)
    for c in cues:
        x = M.decode(sound / c["file"]) * np.float32(0.01)
        start = c["start_sample"]
        if c["id"] == "c4":
            late_mix[start:start + len(x)] += x
        elif c["id"] == "swell":
            swell_mix[start:start + len(x)] += x
        else:
            base[start:start + len(x)] += x
    wav(sound / "present.wav", base + late_mix + swell_mix)
    wav(sound / "missing.wav", base + swell_mix)
    survival("synthetic", sound, sound / "present.wav", sound / "missing.wav")
    for label, window in (("first audible", first_audible_window), ("old", old_window)):
        corr = old_corr(sound / "present.wav", sound, "swell", window)
        ck("synthetic: %s window rejects the same swell cue" % label,
           np.isfinite(corr) and corr < 0.9, corr)
    r = result(sound / "present.wav", sound)
    ck("synthetic: present swell passes", any(c["id"] == "swell" and c["corr"] >= 0.9 for c in r["cues"]))
    wav(sound / "missing-swell.wav", base + late_mix)
    r = result(sound / "missing-swell.wav", sound)
    ck("synthetic: absent swell fails", not r["pass"] and any(
        c["id"] == "swell" and c["corr"] < 0.9 for c in r["weak_cues"]))
    cues.append(dict(id="end", beat='"end"', file="cues/ordinary.wav", start_sample=len(base) - 2,
                     lane=0, time=(len(base) - 2) / SR, peak_s=0, seconds=len(ordinary) / SR))
    write(sound / "placement.json", dict(lanes=1, bed=dict(file="music.wav"), cues=cues))
    r = result(sound / "present.wav", sound)
    ck("synthetic: two-sample missing end cue is weak", not r["pass"] and any(
        c["id"] == "end" and c["corr"] == 0.0 and c.get("too_short") is True for c in r["weak_cues"]))
    present_end = M.decode(sound / "present.wav")
    present_end[-2:] += np.float32(0.01) * M.decode(sound / "cues/ordinary.wav")[:2]
    wav(sound / "present-end.wav", present_end)
    r = result(sound / "present-end.wav", sound)
    ck("synthetic: two-sample present end cue is weak", not r["pass"] and any(
        c["id"] == "end" and c["corr"] == 0.0 and c.get("too_short") is True for c in r["weak_cues"]))


def message(scratch):
    # Run the actual reporting branch alone, avoiding a fake of the whole mastering pipeline.
    tree = ast.parse((S / "mix.py").read_text(encoding="utf-8"))
    run = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run")
    branch = next(n for n in reversed(run.body) if isinstance(n, ast.If) and isinstance(n.test, ast.UnaryOp)
                  and isinstance(n.test.op, ast.Not) and isinstance(n.test.operand, ast.Subscript)
                  and isinstance(n.test.operand.value, ast.Name) and n.test.operand.value.id == "report")
    wrapper = ast.parse("def report_line(report):\n    pass\n")
    wrapper.body[0].body = [branch]
    namespace = {}
    exec(compile(ast.fix_missing_locations(wrapper), "mix-report-line", "exec"), namespace)
    fallback = ("Until the mix passes, the preview and the final video use your voice "
                "without music or sound effects.")
    for label, cues in (("one cue", [dict(id="c4", beat='"10"')]),
                         ("several cues", [dict(id="c4", beat='"10"'), dict(id="c9", beat='"next"')]),
                         ("music level", [])):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            rc = namespace["report_line"]({"pass": False, "mix_check": {"weak_cues": cues}})
        line = stream.getvalue()
        ck("message: " + label + " names beats without ids", rc == 1 and all(c["beat"] in line for c in cues)
           and "c4" not in line and "c9" not in line and "cue " not in line)
        ck("message: " + label + " explains the fallback", fallback in line)
        ck("message: " + label + " gives a next step", "Sound Board" in line and "mix again" in line
           and (("music level" in line and "voice" in line) if not cues else "another sound" in line))


def real_walk2c(scratch):
    value = os.environ.get("EDITOR_SE_TEST_REEL_W2C", "")
    source = Path(value) if value else None
    if source is None or not source.is_dir():
        print("SKIP real-walk2c: set EDITOR_SE_TEST_REEL_W2C to run this case")
        return
    sound = Path(tempfile.mkdtemp(prefix="fx1-mix-walk2c-", dir=scratch)) / "sound"
    sound.mkdir()
    for name in ("placement.json", "music.wav", "voice-mixed.wav", "final.mp4"):
        shutil.copyfile(source / "sound" / name, sound / name)
    shutil.copytree(source / "sound/cues", sound / "cues")
    placement = json.loads((sound / "placement.json").read_text(encoding="utf-8"))
    if not ck("real-walk2c: source placement has c1 only", [c["id"] for c in placement["cues"]] == ["c1"]):
        return
    y = M.decode(sound / "final.mp4")
    voice = M.decode(sound / "voice-mixed.wav")
    late = M.decode(sound / "cues/c4 10.wav")
    # Place the hit in a voiced stretch, clear of every existing cue.
    peak = int(np.argmax(np.abs(late.mean(1))))
    candidates = [s for s in range(0, min(len(y), len(voice)) - len(late), SR // 2)
                  if all(s + len(late) <= c["start_sample"] or s >= c["start_sample"] + int(c["seconds"] * SR)
                         for c in placement["cues"])]
    if not ck("real-walk2c: room for a separate voiced cue", bool(candidates)):
        return
    start = max(candidates, key=lambda s: float(np.mean(voice[s + peak:s + len(late)] ** 2)))
    ck("real-walk2c: added cue is in speech", float(np.sqrt(np.mean(voice[start + peak:start + len(late)] ** 2))) > 0.01)
    placement["cues"].append(dict(id="c4", beat='"10"', file="cues/c4 10.wav", lane=0,
                                  start_sample=start, seconds=len(late) / SR,
                                  time=(start + peak) / SR, peak_s=peak / SR))
    write(sound / "placement.json", placement)
    added = y.copy()
    added[start:start + len(late)] += np.float32(0.47) * late
    # Float WAV preserves the decoded delivery's residual and the measured cue gain.
    M.write_wav(sound / "present.wav", added)
    M.write_wav(sound / "missing.wav", y)
    survival("real-walk2c", sound, sound / "present.wav", sound / "missing.wav")

    def place_extra(cue_id, file, x):
        peak = int(np.argmax(np.abs(x.mean(1))))
        candidates = [s for s in range(0, min(len(y), len(voice)) - len(x), SR // 2)
                      if all(s + len(x) <= c["start_sample"] or
                             s >= c["start_sample"] + int(round(c["seconds"] * SR))
                             for c in placement["cues"])]
        if not ck("real-walk2c: room for " + cue_id, bool(candidates)):
            return None
        start = max(candidates, key=lambda s: float(np.mean(voice[s:s + len(x)] ** 2)))
        ck("real-walk2c: " + cue_id + " is in speech",
           float(np.sqrt(np.mean(voice[start:start + len(x)] ** 2))) > 0.01)
        placement["cues"].append(dict(id=cue_id, beat='"%s"' % cue_id, file=file, lane=0,
                                      start_sample=start, seconds=len(x) / SR,
                                      time=(start + peak) / SR, peak_s=peak / SR))
        return start

    pack = source.parent.parent / "editor/sound"
    pack_file = next((p for stem in ("riser-reverse", "hit-braam-epic")
                      for p in sorted(pack.rglob(stem + ".*")) if p.is_file()), None)
    if pack_file is None:
        print("SKIP real-walk2c swell: neither riser-reverse nor hit-braam-epic exists in the reel workspace pack")
    else:
        file = "cues/swell" + pack_file.suffix
        shutil.copyfile(pack_file, sound / file)
        swell = M.decode(sound / file)
        start = place_extra("swell", file, swell)
        if start is None:
            return
        # Match c4's baked peak and its measured delivered gain (0.47 linear).
        gain = 0.47 * float(np.max(np.abs(late))) / float(np.max(np.abs(swell)))
        added[start:start + len(swell)] += np.float32(gain) * swell
        write(sound / "placement.json", placement)
        M.write_wav(sound / "present-swell.wav", added)
        r = result(sound / "present-swell.wav", sound)
        ck("real-walk2c: present swell passes", r["pass"] and any(
            c["id"] == "swell" and c["corr"] >= 0.9 for c in r["cues"]),
           [(c["id"], c["corr"]) for c in r["cues"]])
        corr = old_corr(sound / "present-swell.wav", sound, "swell", first_audible_window)
        ck("real-walk2c: first audible window rejects the same swell cue", np.isfinite(corr) and corr < 0.9, corr)

    if place_extra("planted-missing", "cues/c4 10.wav", late) is None:
        return
    write(sound / "placement.json", placement)
    M.write_wav(sound / "planted-missing.wav", added)
    r = result(sound / "planted-missing.wav", sound)
    ck("real-walk2c: planted missing cue fails", not r["pass"] and any(
        c["id"] == "planted-missing" and c["corr"] < 0.9 for c in r["weak_cues"]),
       [(c["id"], c["corr"]) for c in r["cues"]])


CASES = {"synthetic": synthetic, "message": message, "real-walk2c": real_walk2c}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=sorted(CASES))
    a = ap.parse_args()
    scratch = Path(a.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    for name, fn in CASES.items():
        if a.case in (None, name):
            try:
                fn(scratch)
            except Exception as e:
                # Source reel paths must never leak through an exception's text.
                ck(name + ": ran without crashing", False, type(e).__name__)
    print("\n%d failed" % len(fails) if fails else "\nall passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
