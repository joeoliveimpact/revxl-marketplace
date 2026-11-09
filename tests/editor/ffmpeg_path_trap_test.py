#!/usr/bin/env python3
"""FT.1 check: transcribe_words.py runs the editor's own ffmpeg/ffprobe (runtime.tool), never a PATH lookup.

usage: python -X utf8 -I tests/editor/ffmpeg_path_trap_test.py [--from STATE] [--script transcribe_words.py]
--from    an installed editor state folder to copy ffmpeg/ffprobe out of (default: the A2 fw test state)
--script  the transcribe_words.py under test (default: this repo's; pass an old copy to see it fail)

Copies only state.json and the two binaries it names into a temp state, sets EDITOR_SE_HOME to it, puts a
TRAP folder first on PATH (fake ffmpeg/ffprobe that write a marker and exit 97) and strips every real ffmpeg
folder from PATH. Makes a 2.5 s tone clip with the state's ffmpeg, then calls audio_tracks, extract,
mean_loudness and sound_end, and runs main() up to just past its ffmpeg/ffprobe check (a --probe for another
file stops it there; no model loads). Prints PASS/FAIL per check; exit 0 = all passed. The temp folder is deleted.
"""
import argparse, importlib.util, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPT = REPO / "plugins" / "editor-superengine" / "skills" / "reel-first-cuts" / "scripts" / "transcribe_words.py"
SRC = Path("C:/Work/_scratch/editor-superengine-0.2.0/a2/doctor-test-r2/state-fw")
WIN = sys.platform == "win32"
fails = []


def ck(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  [%s]" % (detail,)))
    if not ok:
        fails.append(name)


def copy_state(src, dst, with_ffmpeg=True):
    """dst gets state.json (ffmpeg component dropped when with_ffmpeg is False) and, if kept, its two binaries."""
    st = json.loads((src / "state.json").read_text(encoding="utf-8"))
    bins = st["components"]["ffmpeg"]["bins"]
    if with_ffmpeg:
        for rel in (bins["ffmpeg"], bins["ffprobe"]):
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / rel, dst / rel)   # plain copy, never a link
            os.chmod(dst / rel, 0o755)
    else:
        st["components"].pop("ffmpeg")
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "state.json").write_text(json.dumps(st), encoding="utf-8")
    return dst / bins["ffmpeg"]


def make_trap(trap, marker):
    trap.mkdir()
    for t in ("ffmpeg", "ffprobe"):
        if WIN:   # .cmd for PATHEXT lookups (shutil.which), extensionless for anything that tries the bare name
            body = '@echo %s %%*>>"%s"\r\n@exit /b 97\r\n' % (t, marker)
            for name in (t + ".cmd", t + ".bat", t):
                (trap / name).write_bytes(body.encode())
        else:
            (trap / t).write_text('#!/bin/sh\necho %s "$@" >> "%s"\nexit 97\n' % (t, marker))
            os.chmod(trap / t, 0o755)


def clean_path(trap):
    names = ("ffmpeg.exe", "ffprobe.exe", "ffmpeg", "ffprobe")
    keep = [d for d in os.environ.get("PATH", "").split(os.pathsep)
            if d and not any(Path(d, n).is_file() for n in names)]
    return os.pathsep.join([str(trap)] + keep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", type=Path, default=SRC)
    ap.add_argument("--script", type=Path, default=SCRIPT)
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="ffmpeg-trap-"))
    try:
        run(a, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d failed" % len(fails) if fails else "all passed")
    return 1 if fails else 0


def run(a, tmp):
    state, nostate, trap, marker = tmp / "state", tmp / "state-noff", tmp / "TRAP", tmp / "trap-hit.txt"
    real = copy_state(a.src, state)
    copy_state(a.src, nostate, with_ffmpeg=False)
    make_trap(trap, marker)
    os.environ["PATH"] = clean_path(trap)
    os.environ["EDITOR_SE_HOME"] = str(state)
    w = shutil.which("ffmpeg") or ""
    ck("setup: a bare ffmpeg lookup now finds the TRAP (%s)" % w, w and Path(w).parent == trap, w)

    clip, wav = tmp / "tone.wav", tmp / "tone.16k.wav"
    p = subprocess.run([str(real), "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                        "-af", "apad=pad_dur=1.5", "-ac", "1", "-ar", "48000", str(clip)],
                       capture_output=True, text=True)
    ck("setup: the state's own ffmpeg makes the 2.5 s tone clip", p.returncode == 0 and clip.exists(), p.stderr[-300:])

    spec = importlib.util.spec_from_file_location("tw_under_test", a.script)
    tw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tw)

    def call(fn):
        try:
            return True, fn()
        except BaseException as e:   # extract() calls sys.exit on failure
            return False, "%s: %s" % (type(e).__name__, e)

    ok, got = call(lambda: tw.audio_tracks(clip))
    ck("audio_tracks (ffprobe) counts 1 track (%s)" % (got,), ok and got == 1, got)
    ok, got = call(lambda: tw.extract(clip, 0, wav))
    ck("extract (ffmpeg) writes the 16 kHz wav", ok and wav.exists(), got)
    ok, got = call(lambda: tw.mean_loudness(wav))
    ck("mean_loudness (ffmpeg) reads a real level (%s dB)" % (got,), ok and isinstance(got, float) and -45 < got < 0, got)
    ok, got = call(lambda: tw.sound_end(wav, 2.5))
    ck("sound_end (ffmpeg) finds the tone end near 1.0 s (%s)" % (got,), ok and got is not None and abs(got - 1.0) < 0.1, got)

    # main(): a --probe naming another file stops it right after the ffmpeg/ffprobe check (exit 1), before any model
    probe = tmp / "probe.json"
    probe.write_text(json.dumps({"input": str(tmp / "other.wav")}), encoding="utf-8")
    for label, st, want_rc, want in (("installed tools", state, 1, "describes"),
                                     ("tools missing from the state", nostate, 3, "ffmpeg is missing")):
        env = dict(os.environ, EDITOR_SE_HOME=str(st), EDITOR_SE_TX_CHILD="1")
        p = subprocess.run([sys.executable, "-X", "utf8", "-I", str(a.script), str(clip), "--probe", str(probe),
                            "-o", str(tmp / "out" / "tx.json")], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, cwd=str(tmp), timeout=60)
        ck("main() tool check, %s: exit %d and says '%s' (got exit %d)" % (label, want_rc, want, p.returncode),
           p.returncode == want_rc and want in p.stderr, p.stderr[-300:])

    hits = marker.read_text(errors="replace").strip() if marker.exists() else ""
    ck("the TRAP ffmpeg/ffprobe never ran", not hits, hits[-300:])


if __name__ == "__main__":
    sys.exit(main())
