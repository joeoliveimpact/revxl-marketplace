"""INT13-A: real synthetic sound chain, remix safety, frame guard and review key.

Run with the editor Python -X utf8 -I; --case selects one independent regression.
"""
import argparse
import contextlib
import importlib.util
import io
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
PLUGIN = REPO / "plugins/editor-superengine"
S = PLUGIN / "skills/reel-sound-pass/scripts"
sys.path.insert(0, str(S))
import _media as M
import bake
import mix
import numpy as np

sys.path.insert(0, str(PLUGIN / "skills/reel-canvas-build/scripts"))
import compose
import hub_rows
import sound_picture
import render_check

spec = importlib.util.spec_from_file_location("sound_fixtures", Path(__file__).with_name("sound_pass_test.py"))
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
fixtures.M, fixtures.SR = M, M.SR

LENGTH_MESSAGE = ("The preview and the cut have different lengths, so the sound can't be lined up. "
                  "Remake the preview, then mix again.")
SOUND_CHANGED = ("Your sound changed after you OK'd the preview. "
                 "Claude will remake the preview for you to OK.")


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(obj) + "\n").encode("utf-8"))


def fixture(root):
    reel = root / "videos/reel-01"
    cut = reel / "work/renders/master-100x.mp4"
    cut.parent.mkdir(parents=True)
    (reel / "renders").mkdir()
    write(root / "editor/editor.config.json", {"paths": {"editor": "editor", "videos": "videos"}})
    write(reel / "work/cuts.json", {"fps": 30, "speed": 1})
    fixtures.make_picture(cut, fixtures.voice_like(3), 3, root)
    preview = reel / "renders/reel-01 Preview 720p - INT13.mp4"
    make_preview(preview, cut, 3)
    os.utime(cut, (100, 100))
    os.utime(preview, (200, 200))
    M.write_wav(reel / "sfx/hit.wav", fixtures.tone(0.4, 1507, level=0.15))
    write(reel / "sound-selection.json", {"auto_level": False, "cues": [
        {"id": "hit", "beat": "The hit", "file": "hit.wav", "time": 1.2,
         "gain_db": -3, "gain_by_hand": True}]})
    return reel, cut, preview


def make_preview(path, audio, seconds):
    # Different pixels ensure a preview hash cannot accidentally equal the cut's.
    subprocess.run([M.ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i",
                    "color=c=red:s=64x64:r=30:d=%s" % seconds, "-i", str(audio),
                    "-map", "0:v", "-map", "1:a", "-t", str(seconds), "-c:v", "libx264",
                    "-preset", "ultrafast", "-c:a", "aac", str(path)], check=True)


def mixed(root, reel):
    output = io.StringIO()
    with contextlib.chdir(root), contextlib.redirect_stdout(output):
        rc = mix.main(["--reel", reel.name, "--voice", "free"])
    assert rc == 0, output.getvalue()
    return json.loads((reel / "sound/mix-report.json").read_text(encoding="utf-8"))


def compose_fixture(root):
    reel, cut, _ = fixture(root)
    write(reel / "work/cuts.json", {"fps": 30, "speed": 1, "segments": [
        {"src_in_f": 0, "src_out_f": 90, "out_in_f": 0, "out_out_f": 90}]})
    write(reel / "work/edit_map.cut.json", {"words": [
        {"id": "w_0000", "word": "Listen", "start": 0, "end": .5}]})
    write(reel / compose.SEND, {"schema": 1, "reel": reel.name, "fps": 30,
        "words": "work/edit_map.cut.json", "beats": [
            {"id": "b_001", "start_f": 0, "end_f": 90,
             "speech_anchor": {"text": "Listen", "w0": 0, "w1": 0},
             "layout": "full", "value": None, "scene": None, "broll": None, "transition": None}],
        "word_marks": [], "proposed": {}, "notes": {}, "needs": "", "sent_at": "2026-11-16T10:00:00Z",
        "edit_style": {"style": "punch-in", "punch_scale": 1,
                       "moves": {"opening_settle": False, "follow_cam": False}},
        "caption_style": {"style": "none"}})
    return reel, cut


@contextlib.contextmanager
def synthetic_render(root, cut):
    # Keep approval, hashing, source selection, mux and final validation real.
    # Only the browser renderer, machine lock, unrelated QA and learning are bypassed.
    import style_learn
    media_tools = {name: compose.rt.tool(name) for name in ("ffmpeg", "ffprobe")}
    with (contextlib.chdir(root),
          patch.object(compose, "hf_render", side_effect=lambda proj, out, *a, **kw: shutil.copyfile(cut, out)),
          patch.object(compose, "heavy_job", side_effect=lambda *a, **kw: contextlib.nullcontext()),
          patch.object(compose.rt, "hyperframes_env", return_value={}),
          patch.object(compose.rt, "state_dir", return_value=root / "state"),
          patch.object(compose.rt, "tool", side_effect=lambda name, *a: media_tools[name]),
          patch.object(compose, "kill_warm"), patch.object(compose, "qa_pre_or_stop"),
          patch.object(style_learn, "record_approval", return_value=[])):
        yield


def composed(reel, command, *args):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        rc = compose.main([command, "--reel-dir", str(reel), *args])
    return rc, output.getvalue()


def preview_ok(reel, *, review=False):
    rc, output = composed(reel, "preview")
    assert rc == 0, output
    preview = compose.latest_preview(reel / "renders")
    write(reel / "review.json", {"approve": True, "preview": preview.name})
    rc, output = composed(reel, "ok", *(["--from-review"] if review else []))
    assert rc == 0, output
    return json.loads((reel / compose.OK_FILE).read_text(encoding="utf-8"))


def changed_mix(root, reel):
    final = reel / "sound/final.mp4"
    before = hashlib.sha256(final.read_bytes()).hexdigest()
    original_times = final.stat()
    selection = json.loads((reel / "sound-selection.json").read_text(encoding="utf-8"))
    selection["cues"][0]["gain_db"] = 3
    write(reel / "sound-selection.json", selection)
    mixed(root, reel)
    os.utime(final, ns=(original_times.st_atime_ns, original_times.st_mtime_ns))
    assert hashlib.sha256(final.read_bytes()).hexdigest() != before, "fixture did not change the mix"


def master_refused(reel):
    before = {p: p.read_bytes() for p in (reel / "renders").glob("* Master - *.mp4")}
    rc, output = composed(reel, "master")
    assert rc != 0, "master accepted sound that was not OK'd"
    assert output.splitlines()[-1] == SOUND_CHANGED, output
    assert "Traceback" not in output
    assert {p: p.read_bytes() for p in (reel / "renders").glob("* Master - *.mp4")} == before


def case_remix_after_ok(root):
    reel, cut = compose_fixture(root)
    mixed(root, reel)
    with synthetic_render(root, cut):
        preview_ok(reel)
        changed_mix(root, reel)
        master_refused(reel)
        # OKing the old preview again must not bless the current unheard mix.
        rc, output = composed(reel, "ok", "--from-review")
        assert rc == 0, output
        master_refused(reel)
    # Shared QA must block even a Master stream-copied from the new mix.
    master = reel / "renders/reel-01 Master - INT13.mp4"
    assert compose.mux_audio(cut, reel / "sound/final.mp4", master)[0] == 0
    hits = render_check.run({"reel_dir": reel, "render": master})
    assert any(h["level"] == "block" and h["msg"] == SOUND_CHANGED for h in hits), hits


def case_reok(root):
    reel, cut = compose_fixture(root)
    mixed(root, reel)
    with synthetic_render(root, cut):
        first = preview_ok(reel)
        changed_mix(root, reel)
        master_refused(reel)
        second = preview_ok(reel, review=True)
        final = reel / "sound/final.mp4"
        expected = hashlib.sha256(final.read_bytes()).hexdigest()
        assert second.get("mix_sha256") == expected, "review OK did not retain the preview's mix hash"
        assert first.get("mix_sha256") != expected, "the two previews approved the same mix"
        rc, output = composed(reel, "master")
        assert rc == 0, output
        master = reel / json.loads(output.splitlines()[-1])["out"]
        assert compose.packet_md5(master, "a") == compose.packet_md5(final, "a")
        assert not [h for h in render_check.run({"reel_dir": reel, "render": master}) if h["level"] == "block"]


def case_no_sound(root):
    reel, cut = compose_fixture(root)
    with synthetic_render(root, cut):
        preview_ok(reel)
        rc, output = composed(reel, "master")
        assert rc == 0, output
        summary = json.loads(output.splitlines()[-1])
        assert summary["audio"] == "cut", output
        assert compose.packet_md5(reel / summary["out"], "a") == compose.packet_md5(cut, "a")


def case_old_ok(root):
    reel, cut = compose_fixture(root)
    mixed(root, reel)
    with synthetic_render(root, cut):
        ok = preview_ok(reel)
        ok.pop("mix_sha256", None)
        write(reel / compose.OK_FILE, ok)
        master_refused(reel)


def case_picture(root):
    reel, cut, preview = fixture(root)
    other_cut = cut.with_name("master-110x.mp4")
    shutil.copyfile(preview, other_cut)
    os.utime(other_cut, (150, 150))
    assert sound_picture.find_picture(reel) == preview
    assert sound_picture.picture_label(preview) == "Playing your preview: " + preview.name
    report = mixed(root, reel)
    assert report["video_md5"] == M.video_md5(cut), "mix records the preview instead of the cut"
    assert compose.audio_choice(report, M.video_md5(cut), True) == ("mix", None)
    assert M.video_md5(reel / "sound/final.mp4") == M.video_md5(cut)
    # The direct bake entry point must also ignore audition audio.
    bake.bake(reel, preview)
    voice = M.decode(reel / "sound/voice.wav")
    assert np.array_equal(voice, M.decode(cut)[:len(voice)]), "bake decodes the audition picture"
    # --video may identify an audition; it must never replace the cut master.
    with contextlib.chdir(root):
        assert bake.main(["--reel", reel.name, "--video", str(preview)]) == 0
    cut.unlink()
    with contextlib.chdir(root), contextlib.redirect_stdout(io.StringIO()):
        assert mix.main(["--reel", reel.name, "--video", str(preview)]) != 0


def case_remix(root):
    reel, cut, preview = fixture(root)
    mixed(root, reel)
    first = M.decode(reel / "sound/final.mp4")
    # A later composed preview already carries the previous mix.
    make_preview(preview, reel / "sound/final.mp4", 3)
    os.utime(preview, (2000000000, 2000000000))
    assert sound_picture.find_picture(reel) == preview
    mixed(root, reel)
    second = M.decode(reel / "sound/final.mp4")
    window = slice(round(1.2 * M.SR), round(1.6 * M.SR))
    t = np.arange(window.stop - window.start) / M.SR
    basis = np.exp(-2j * np.pi * 1507 * t)
    level = lambda x: abs(np.dot(x[window].mean(1), basis))
    assert abs(20 * np.log10(level(second) / level(first))) < 0.05, "remix changes the effect level"
    voice = M.decode(reel / "sound/voice.wav")
    assert np.array_equal(voice, M.decode(cut)[:len(voice)]), "remix input is not the cut's audio"


def case_frames(root):
    reel, cut, preview = fixture(root)
    packet_only = root / "no-frame-metadata.mkv"
    subprocess.run([M.ffmpeg(), "-v", "error", "-y", "-i", str(cut), "-map", "0:v:0",
                    "-c", "copy", str(packet_only)], check=True)
    check_output = subprocess.check_output

    def no_decode(command, *args, **kwargs):
        assert "-count_frames" not in command, "frame count decodes the entire video"
        return check_output(command, *args, **kwargs)

    with patch.object(M.subprocess, "check_output", side_effect=no_decode):
        assert M.frame_count(cut) == 90
        assert M.frame_count(packet_only) == 90
    make_preview(preview, cut, 2)
    os.utime(preview, (200, 200))
    output = io.StringIO()
    with contextlib.chdir(root), contextlib.redirect_stdout(output):
        rc = mix.main(["--reel", reel.name, "--voice", "free"])
    assert rc != 0, "mix accepted a preview with different frames"
    assert output.getvalue().strip() == LENGTH_MESSAGE, output.getvalue()
    assert not (reel / "sound").exists(), "refusal wrote sound outputs"
    output = io.StringIO()
    with contextlib.chdir(root), contextlib.redirect_stdout(output):
        assert bake.main(["--reel", reel.name]) != 0
    assert output.getvalue().strip() == LENGTH_MESSAGE
    assert not (reel / "sound").exists()


def case_missing_video(root):
    reel, cut, preview = fixture(root)
    message = "Couldn't find the reel folder or its cut video. Check the reel name, then try again."
    missing = reel / "missing.mp4"
    args = ["--reel", reel.name, "--video", str(missing)]
    output = io.StringIO()
    with contextlib.chdir(root), contextlib.redirect_stdout(output):
        assert mix.main(args) == 2
    assert output.getvalue().strip() == message, output.getvalue()
    child = subprocess.run([sys.executable, "-B", "-X", "utf8", "-I", str(S / "mix.py"), *args],
                           cwd=root, capture_output=True, text=True, encoding="utf-8")
    assert child.returncode == 2, child.stdout + child.stderr
    assert child.stdout.strip() == message and not child.stderr, child.stdout + child.stderr
    # Missing reels and cut masters follow the same bad-input contract.
    cut.unlink()
    for args in (["--reel", reel.name, "--video", str(preview)], ["--reel", "missing-reel"]):
        output = io.StringIO()
        with contextlib.chdir(root), contextlib.redirect_stdout(output):
            assert mix.main(args) == 2
        assert output.getvalue().strip() == message, output.getvalue()
    assert not (reel / "sound").exists()


def case_review_key(root):
    reel = root / "videos/reel-01"
    preview = reel / "renders/reel-01 Preview 720p - INT13.mp4"
    write(root / "editor/editor.config.json", {})
    for path, at in ((preview, 100), (reel / "sound/final.mp4", 200)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
        os.utime(path, (at, at))
    with patch.object(hub_rows, "filmstrip", return_value=[]), patch.object(hub_rows, "goldmine", return_value=None), \
            patch.object(hub_rows, "style_rows", return_value=[]):
        row = hub_rows.build(root)["reels"][0]
    assert row.get("preview_label") == "Latest mix", "display label is missing"
    assert row["preview_name"] == preview.name, "display label replaced the approval key"
    assert row["preview_url"].endswith("/sound/final.mp4")
    # Execute the actual review page script, including its Approve handler.
    script = (PLUGIN / "skills/editor-doctor/boards/hub/review.js").read_text(encoding="utf-8")
    harness = """
const elements = new Map();
const document = {getElementById(id) {
  if (!elements.has(id)) elements.set(id, {value:'', scrollIntoView(){}, append(){}, querySelectorAll(){return []}});
  return elements.get(id);
}};
const window = {}, location = {search:'?reel=reel-01'};
const HubIO = {json:async p=>p.includes('hub-data')?{reels:[ROW]}:{}, base:()=>'',
  send:async(reel,file,body)=>{console.log(JSON.stringify({label:document.getElementById('render-label').textContent,body}));},
  status(){}};
SCRIPT
setImmediate(async()=>{if (!window.ReviewReady) throw Error('review did not load');
  await document.getElementById('approve').onclick();});
""".replace("ROW", json.dumps(row)).replace("SCRIPT", script)
    p = subprocess.run([M.rt.tool("node"), "-"], input=harness, capture_output=True, text=True, check=True)
    sent = json.loads(p.stdout)
    assert sent["label"] == "Latest mix"
    write(reel / "review.json", sent["body"])
    review = json.loads((reel / "review.json").read_text(encoding="utf-8"))
    assert compose.review_problem(review, compose.latest_preview(reel / "renders").name) is None


def case_chain(root):
    reel, cut = compose_fixture(root)
    mixed(root, reel)
    with synthetic_render(root, cut):
        preview_ok(reel)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        kind, source = compose.choose_audio(reel, {"master": cut, "rate": 30, "cuts": {}, "beats": []}, "master")
    assert kind == "mix" and source == reel / "sound/final.mp4", output.getvalue()
    assert compose.STALE_MIX not in output.getvalue()
    master = reel / "renders/reel-01 Master - INT13.mp4"
    rc, _, err = compose.mux_audio(cut, source, master)
    assert rc == 0, err
    assert compose.packet_md5(master, "a") == compose.packet_md5(source, "a"), "master lost the mix audio"
    assert compose.packet_md5(master, "a") != compose.packet_md5(cut, "a"), "master kept voice only"


def main():
    names = ("picture", "remix", "frames", "review_key", "chain", "missing_video",
             "remix_after_ok", "reok", "no_sound", "old_ok")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", choices=names)
    args = ap.parse_args()
    failed = skipped = passed = 0
    try:
        subprocess.run([M.ffmpeg(), "-version"], capture_output=True, check=True)
        has_ffmpeg = True
    except (OSError, KeyError, RuntimeError, subprocess.CalledProcessError):
        has_ffmpeg = False
    for name in (args.case,) if args.case else names:
        if not has_ffmpeg and name != "review_key":
            print("SKIP %s: ffmpeg is absent" % name, flush=True)
            skipped += 1
            continue
        try:
            with tempfile.TemporaryDirectory(prefix="int13-sound-") as tmp:
                globals()["case_" + name](Path(tmp))
            passed += 1
            print("PASS " + name, flush=True)
        except Exception as e:
            failed += 1
            print("FAIL %s: %s: %s" % (name, type(e).__name__, e), flush=True)
    print("%d passed, %d failed, %d skipped" % (passed, failed, skipped))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
