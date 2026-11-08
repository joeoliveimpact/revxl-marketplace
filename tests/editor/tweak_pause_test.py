"""Tweak Send retains the reel's pause default: <scratch>; no media rendering."""
import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills/reel-first-cuts/scripts"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value) + "\n").encode("utf-8"))


def run(name, *args):
    result = subprocess.run([sys.executable, "-X", "utf8", "-I", str(SCRIPTS / name), *map(str, args)],
                            capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def case_pause(root):
    work = root / "work"
    words = [dict(id="w_0000", word="Hello", start=.5, end=1.5),
             dict(id="w_0001", word="again", start=2.5, end=3.2)]
    for w in words:
        w["parakeet_start"] = w["start"]
    write(work / "edit_map.json", dict(words=words, events=[], silences=[]))
    write(work / "cuts.json", dict(fps=1000, speed=1, segments=[
        dict(src_in_f=0, src_out_f=4000, out_in_f=0, out_out_f=4000)]))
    write(work / "probe.json", dict(out_rate=1000, fps=dict(measured_fps=1000), input=str(root / "source.wav"),
        calibration=dict(gap_db=-50, speech_db=-40, speech_run_windows=3)))
    db = [-60] * 500
    for w in words:
        for i in range(round(w["start"] * 100), round(w["end"] * 100)):
            db[i] = -20
    write(work / "envelope.json", dict(win_s=.01, db=db))
    write(root / "tweak-board.config.json", dict(version="v1", edit_map="work/edit_map.json", words=[]))
    # Touch the segment without imposing an explicit pause ruling on its internal gap.
    write(root / "tweak-selection.json", dict(version="v1", marks=[dict(type="cut", a=.05, b=.1)]))

    def send():
        text = run("tweaks_to_edl.py", root / "tweak-selection.json", work)
        cmd = next(line for line in text.splitlines() if line.startswith("<editor python>"))
        args = shlex.split(cmd[cmd.index(' "' + work.as_posix() + '"'):])
        run("gaps.py", *args)
        cuts = json.loads((work / "cuts.json").read_text(encoding="utf-8"))
        pieces = cuts["segments"]
        pause = pieces[0]["src_out_f"] / 1000 - 1.5 + 2.5 - pieces[1]["src_in_f"] / 1000
        return cmd, (work / "cuts.json").read_bytes(), pause

    original = (work / "cuts.json").read_bytes()
    cmd, legacy, pause = send()
    assert "--internal" not in cmd and "--join" not in cmd and "--nudge" not in cmd
    assert abs(pause - .15) < 1e-8
    # Config supplies 300 ms; an explicit selection takes precedence over that config.
    for cfg, selection in ((300, {}), (150, {"gap_default_ms": 300})):
        (work / "cuts.json").write_bytes(original)
        write(root / "cut-board.config.json", {"gap_default_ms": cfg})
        write(root / "cut-selection.json", selection)
        cmd, _, pause = send()
        assert "--internal 0.300 --join 0.300" in cmd and abs(pause - .3) < 1e-8
    # An explicit legacy default produces the same actual cuts as no default anywhere.
    (work / "cuts.json").write_bytes(original)
    write(root / "cut-selection.json", {})
    cmd, explicit, _ = send()
    assert explicit == legacy
    # Active timing is forwarded by the Tweak reader; unset timing was omitted above.
    sys.path.insert(0, str(SCRIPTS.parents[1] / "_shared"))
    import saved_style
    saved_style.save({"cut": {"nudge_ms": 40}}, "style-1")
    (work / "cuts.json").write_bytes(original)
    cmd, _, _ = send()
    assert "--nudge 0.040" in cmd
    # The Cut Board reader forwards the same active timing on single and mixed takes.
    take = dict(edit_map="work/edit_map.json", wav="source.wav", words=[])
    config = dict(gap_default_ms=150, takes={"1": take}, lines=[dict(id="one", attempts=[
        dict(take=1, src_in=0, src_out=4, words=[])])])
    selection = dict(lines=[dict(id="one", pick=0)])
    for mixed in (False, True):
        if mixed:
            config["takes"]["2"] = take
            config["lines"].append(dict(id="two", attempts=[dict(take=2, src_in=0, src_out=4, words=[])]))
            selection["lines"].append(dict(id="two", pick=0))
        write(root / "cut-board.config.json", config)
        write(root / "cut-selection.json", selection)
        text = run("selection_to_edl.py", root / "cut-selection.json", root / "cut-board.config.json", "--allow-unhashed")
        cmd = next(line for line in text.splitlines() if line.startswith("<editor python>"))
        assert "--nudge 0.040" in cmd and (("takes.py" in cmd) == mixed)
        if mixed:
            args = shlex.split(cmd[cmd.index(' "' + work.as_posix() + '"'):])
            run("takes.py", *args)
    # Readers clamp legacy or hand-edited values before printing their commands.
    for value, expected in ((-40, "0.000"), (190, "0.150")):
        saved_style.path("style-1").write_bytes(json.dumps({"cut": {"nudge_ms": value}}).encode("utf-8"))
        (work / "cuts.json").write_bytes(original)
        cmd, _, _ = send()
        assert f"--nudge {expected}" in cmd
        text = run("selection_to_edl.py", root / "cut-selection.json", root / "cut-board.config.json", "--allow-unhashed")
        assert f"--nudge {expected}" in text
    saved_style.save({}, "style-1")
    text = run("selection_to_edl.py", root / "cut-selection.json", root / "cut-board.config.json", "--allow-unhashed")
    assert "--nudge" not in text


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch")
    args = ap.parse_args()
    scratch = Path(args.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tweak-pause-", dir=scratch) as tmp:
        root = Path(tmp)
        with patch.dict(os.environ, {"EDITOR_SE_HOME": str(root / "state")}):
            case_pause(root / "reel")
    print("PASS tweak-pause\nall passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
