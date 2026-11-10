"""Refresh the editor hub from disk; the page never runs tools.

<editor python> -X utf8 -I hub_rows.py [--root <workspace>]
Optional hub/cockpit-state.json holds {baseline: <milliseconds>, acked: {...}} exported by the Cockpit mod
from the Cockpit store. Without a baseline, logic.ts defines no open Sends. No private store is guessed.
"""
import argparse
import ast
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / "_shared")]
import runtime as rt
import saved_style
import style_learn
from win_encoding import ensure_utf8_output
from board_sync import is_real, load_manifest, workspace_paths

STRING = r"(?:'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")"
REEL = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_. -]{0,119}$")
MASTER = re.compile(r"^.+ master - \d{2}\.\d{2}\.\d{2}\.mp4$", re.I)


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as e:
        raise ValueError(f"Could not read {Path(path).name}: {e}") from e


def mtime(path):
    try:
        return path.stat().st_mtime * 1000 if path.is_file() else None
    except OSError:
        return None


def files(folder):
    return [p for p in folder.iterdir() if p.is_file() and is_real(p) and not re.search(r"\.(tmp|prev)$", p.name, re.I)] if folder.is_dir() and is_real(folder) else []


def field(text, key):
    hit = re.search(r"\b" + re.escape(key) + r": (" + STRING + ")", text)
    return ast.literal_eval(hit[1]) if hit else None


def cockpit_rules(plugin_root=rt.PLUGIN_ROOT):
    """Read the actual declarative STAGES/SENDS. Refuse an unfamiliar rule instead of drifting silently.

    This is a deliberately small reader for logic.ts's data declarations, not a JavaScript evaluator.
    The headless proof executes logic.ts independently with Node and compares the resulting stage.
    """
    text = (Path(plugin_root) / "hooks/mod/logic.ts").read_text(encoding="utf-8")
    block = text.split("export const STAGES:", 1)[1].split("= [", 1)[1].split("\n]", 1)[0]
    stages = []
    for entry in re.split(r"\n  (?=\{ name:)", block.strip()):
        name = field(entry, "name")
        if not name:
            raise ValueError("Cockpit STAGES declaration changed; update the hub rule reader")
        rule = entry.split("rule: {", 1)[1].split(" }, action:", 1)[0]
        stage = {"name": name, "id": field(entry, "action"), "head": field(entry, "head"),
                 "hint": field(entry, "sub"), "optional": "optional: true" in entry}
        if "never: true" in rule:
            stage["rule"] = {"never": True}
        elif "json:" in rule:
            when = re.fullmatch(r"json: (" + STRING + r"), (?:(missing: true), )?when: s => (?:!!s\.(\w+)|s\.(\w+) != null)", rule.strip())
            if not when:
                raise ValueError(f"Unrecognised Cockpit JSON rule for {name}")
            stage["rule"] = {"json": ast.literal_eval(when[1]), "missing": bool(when[2]),
                             "property": when[3] or when[4], "test": "truthy" if when[3] else "not-null"}
        else:
            primary, *alternative = rule.split(", or: {", 1)
            match = re.fullmatch(r"in: (" + STRING + r"), match: (?:/(.+)/([i]*)|(MASTER))"
                                 r"(?:, (video: true|applied: (\[[^\]]*\])))?", primary.strip())
            if not match:
                raise ValueError(f"Unrecognised Cockpit file rule for {name}")
            master = bool(match[4])
            stage["rule"] = {"in": ast.literal_eval(match[1]), "pattern": MASTER.pattern if master else match[2],
                             "ignore_case": master or "i" in match[3], "video": match[5] == "video: true"}
            if match[6]:
                stage["rule"]["applied"] = ast.literal_eval(match[6])
            if alternative:
                other = re.fullmatch(r" in: ('[^']+'), match: /(.+)/([i]*) }", alternative[0])
                if not other:
                    raise ValueError(f"Unrecognised Cockpit alternative rule for {name}")
                stage["rule"]["or"] = {"in": ast.literal_eval(other[1]), "pattern": other[2],
                                       "ignore_case": "i" in other[3], "video": False}
        stages.append(stage)
    block = text.split("export const SENDS:", 1)[1].split("= [", 1)[1].split("\n]", 1)[0]
    sends = []
    for line in block.splitlines():
        if "{ file:" in line:
            sends.append({"file": field(line, "file"), "board": field(line, "board"),
                          "downstream": ast.literal_eval(re.search(r"downstream: (\[[^\]]*\])", line)[1])})
    return stages, sends


def run(args):
    p = subprocess.run([str(a) for a in args], env=rt.python_env(), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=60)
    if p.returncode:
        raise ValueError(f"Video tool failed: {p.stderr.strip()[-400:]}")
    return p.stdout


def video_info(path):
    return json.loads(run([rt.tool("ffprobe"), "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type", "-of", "json", path]))


def filmstrip(src, out):
    if src is None:
        return []
    out.mkdir(parents=True, exist_ok=True)
    if not is_real(out):
        raise ValueError("The filmstrip folder is a link; left untouched")
    stamp = {"source": str(src), "mtime_ns": src.stat().st_mtime_ns}
    frames = [out / f"{i:02d}.jpg" for i in range(12)]
    if any(not is_real(f) for f in frames):
        raise ValueError("A filmstrip frame is a link; left untouched")
    previous = read(out / ".source.json", {})
    if (previous.get("source") != stamp["source"] or previous.get("mtime_ns", -1) < stamp["mtime_ns"]
            or not all(f.is_file() for f in frames)):
        duration = float(video_info(src).get("format", {}).get("duration", 0))
        for i, f in enumerate(frames):
            t = min(max(0, duration - 0.08), duration * (i + 0.5) / 12)
            run([rt.tool("ffmpeg"), "-v", "error", "-y", "-threads", "2", "-ss", f"{t:.5f}", "-i", src,
                 "-frames:v", "1", "-vf", "scale=240:-2", "-threads", "2", "-q:v", "4", "-update", "1", f])
            if not f.is_file():
                raise ValueError("The render did not yield a filmstrip frame")
        (out / ".source.json").write_bytes((json.dumps(stamp) + "\n").encode("utf-8"))
    return [f"/editor/hub/frames/{quote(out.name)}/{f.name}" for f in frames]


def stage_done(rule, folders, reel):
    if "or" in rule and stage_done(rule["or"], folders, reel):
        return True
    if rule.get("never"):
        return False
    if "json" in rule:
        absent = object()
        try:
            obj = read(reel / rule["json"], absent)
        except (OSError, ValueError):
            return False
        if obj is absent:
            try:
                (reel / rule["json"]).lstat()
            except FileNotFoundError:
                return rule.get("missing", False)
            except OSError:
                return False
            return False
        value = obj.get(rule["property"]) if isinstance(obj, dict) else None
        return value is not None if rule["test"] == "not-null" else bool(value)
    pattern = re.compile(rule["pattern"], re.I if rule["ignore_case"] else 0)
    for path in folders[rule["in"]]:
        if pattern.search(path.name):
            if "applied" in rule:
                at = mtime(path)
                applied = [mtime(p) for rel in rule["applied"]
                           for p in folders.get(rel.split("/", 1)[0] if "/" in rel else "root", []) if p == reel / rel]
                if at is None or not any(t is not None and t >= at for t in applied):
                    continue
            if not rule["video"]:
                return True
            if path.stat().st_size:
                try:
                    if any(s.get("codec_type") == "video" for s in video_info(path).get("streams", [])):
                        return True
                except ValueError:  # Cockpit probe unknown counts as done, a successful no-video does not
                    return True
    return False


def open_sends(reel, sends, baseline, acked):
    if not isinstance(baseline, (int, float)):
        return []
    out = []
    for send in sends:
        at = mtime(reel / send["file"])
        ack = acked.get(f"{reel.name}/{send['file']}")
        downstream = max([mtime(reel / p) or float("-inf") for p in send["downstream"]] or [float("-inf")])
        if at is not None and at > baseline and at > (ack if isinstance(ack, (int, float)) else float("-inf")) and at > downstream:
            out.append(dict(send, mtimeMs=at))
    return sorted(out, key=lambda s: -s["mtimeMs"])


def goldmine(root):
    """Pointer is authoritative: an unfinished/new run must not expose an earlier run's numbers."""
    roots = [root]
    # The shortform plugin's active-brand state, read only and only when explicitly present.
    home = Path.home() / ".claude" / "shortform-superengine"
    marker = read(home / ".superengine", {})
    brand = marker.get("active_brand") or marker.get("brand")
    if isinstance(brand, str) and re.fullmatch(r"[\w-]+", brand):
        state = read(home / "state" / f"{brand}.json", {})
        if state.get("project_path"):
            roots.append(Path(state["project_path"]))
    for local in (root / "shortform-state.json", root / ".shortform-superengine/state.json"):
        state = read(local, {})
        if state.get("project_path"):
            roots.append(Path(state["project_path"]))
    for project in roots:
        pointer = read(project / "reel-build/goldmine-run.json")
        if not isinstance(pointer, dict):
            continue
        def export(path):
            if not isinstance(path, str) or not path:
                return None
            # goldmine_build.py writes basenames into its pointer; prefixed/absolute paths also occur in exports.
            target = Path(path)
            return read(project / "reel-build" / target if len(target.parts) == 1 else project / target)
        pop = export((pointer.get("compute") or {}).get("popularity"))
        manifest = export(pointer.get("manifest"))
        if not isinstance(pop, dict) or not isinstance(pop.get("corpus", {}).get("reels_total"), (int, float)):
            return None
        # Name breakouts by their hook line (never the hook category); odd shapes fall back, never crash the hub.
        listed = manifest.get("breakouts") if isinstance(manifest, dict) else None
        titles = {b["id"]: b.get("hook_line") for b in listed if isinstance(b, dict) and isinstance(b.get("id"), str)
                  and isinstance(b.get("hook_line"), str) and b["hook_line"].strip()} if isinstance(listed, list) else {}
        rows = pop.get("breakout_ranking")
        ranking = [dict(x, title=x.get("title") or titles.get(x.get("shortcode") if isinstance(x.get("shortcode"), str)
                                                              else None)) if isinstance(x, dict) else x
                   for x in rows] if isinstance(rows, list) else []
        return {"n": pop["corpus"]["reels_total"], "breakouts": manifest.get("count", 0) if manifest else 0,
                "corpus": pop["corpus"], "ranking": ranking,
                "retrieval": export((pointer.get("compute") or {}).get("retrieval")),
                "hooks": export((pointer.get("reads") or {}).get("proven_hooks"))}
    return None


def plain_health(status, nle):
    labels = {"machine": "This computer", "python": "The editor's Python", "ffmpeg": "Video tools",
              "node": "Motion renderer runtime", "hyperframes": "Motion renderer", "chrome": "Render browser",
              "cutout-model": "Cutout model", "rvm": "Cutout for moving shots", "transcriber": "Transcriber",
              "align": "Word timing", "engine": "Transcription engine", "nle": "Editor hand-off",
              "config": "Editor settings", "gpu": "Graphics card"}
    rows = []
    for row in status:
        if not isinstance(row, dict):
            rows.append(row)
            continue
        component = row.get("component", "")
        label = component.replace("-", " ")
        label = labels.get(component, label[:1].upper() + label[1:])
        if component.startswith("model-"):
            label = "Transcription model"
        elif component.startswith("resolve-"):
            label = "DaVinci Resolve" + {"resolve-edition": " edition", "resolve-version": " version",
                                        "resolve-scripting": " scripting"}.get(component, "")
        detail = re.sub(r" \[test masks: [^\]]*\]", "", row.get("detail", ""))
        if re.fullmatch(r"(?:.*: )?\d+ file\(s\) match their sha256", detail):
            detail = "Downloaded and checked."
        elif "missing or damaged:" in detail:
            detail = "Some of its files are missing or damaged."
        elif row.get("level") == "ok":
            if component == "machine":
                detail = re.sub(r" \(\d+(?:\.\d+){2,}\)", "", detail)
                detail = re.sub(r"\b(\d+)\.\d+(?:\.\d+)+\b", r"\1", detail)
                detail = re.sub(r"\s+\b(?:AMD64|arm64|x86_64)\b", "", detail, flags=re.I)
            elif component == "nle":
                detail = {"none": "No editor hand-off chosen (you can ask for one later).",
                          "mcp": "Files for another editor", "resolve": "DaVinci Resolve"}.get(detail.split(" ", 1)[0], detail)
            else:
                detail = {"config": "Your editor settings are up to date.",
                          "transcriber": "Installed and working.", "rvm": "Ready.",
                          "ffmpeg": "Ready.", "node": "Ready.", "hyperframes": "Ready.",
                          "chrome": "Ready.", "python": "Ready.", "engine": "Ready."}.get(component, detail)
        if row.get("level") != "ok":
            detail = re.sub(r"(?:[^\s,;()\"']*[\\/])+[^\s,;()\"']*[\w-]|(?<![\w.])[\w.-]+\.[A-Za-z][A-Za-z0-9]*",
                            "a settings file", detail)
        rows.append(dict(component=component, label=label, level=row.get("level"), detail=detail,
                         fix=row.get("fix"), matters=not (component.startswith("resolve-") and nle != "resolve")))
    return rows


def sound_pack_installed(editor):
    library = editor / "sound"
    try:
        index = read(library / "library-index.json", {})
        entries = index.get("files") if isinstance(index, dict) else None
        return isinstance(entries, dict) and bool(entries) and all(
            isinstance(name, str) and (library / name).resolve().is_relative_to(library.resolve())
            and (library / name).is_file() and is_real(library / name) for name in entries)
    except (OSError, ValueError):
        return False


def build(root, plugin_root=rt.PLUGIN_ROOT):
    root = Path(root).resolve()
    editor, videos = workspace_paths(root)
    hub = editor / "hub"
    if not is_real(editor) or not is_real(hub) or not is_real(videos):
        raise ValueError("Editor or videos folder is a link; left untouched")
    hub.mkdir(parents=True, exist_ok=True)
    pack_installed = sound_pack_installed(editor)
    manifest = load_manifest(plugin_root)
    boards = [dict(id=k, label=v["tab"]["label"], stages=v["tab"]["stages"], order=v["tab"]["order"],
                   built=(editor / k / "index.html").is_file() and is_real(editor / k / "index.html"))
              for k, v in manifest.items() if "tab" in v]
    boards.sort(key=lambda b: b["order"])
    stages, sends = cockpit_rules(plugin_root)
    snapshot = read(hub / "cockpit-state.json", {})
    now = dt.datetime.now(dt.timezone.utc)
    rows = []
    for reel in sorted(videos.iterdir() if videos.is_dir() else []):
        if not reel.is_dir() or not is_real(reel) or not REEL.fullmatch(reel.name) or reel.name.endswith((".", " ")):
            continue
        folders = {f: files(reel if f == "root" else reel / f) for f in ("root", "raw", "work", "renders", "sound")}
        done = [stage_done(s["rule"], folders, reel) for s in stages]
        cur = next(i for i, s in enumerate(stages) if not s["optional"] and not done[i])
        sound_pass_ran = done[next(i for i, s in enumerate(stages) if s["id"] == "sound")]
        ready_to_post = stages[cur]["id"] == "post" and done[next(i for i, s in enumerate(stages) if s["id"] == "master")]
        render_files = [p for p in folders["renders"] + folders["work"] + folders["root"] + folders["raw"] + files(reel / "work/renders")
                        if p.suffix.lower() == ".mp4" and p.stat().st_size]
        masters = [p for p in folders["renders"] if MASTER.fullmatch(p.name) and p.stat().st_size]
        previews = [p for p in folders["renders"] if p.match("* Preview 720p - *.mp4")
                    and not p.name.endswith(".partial.mp4")]
        preview = max(previews, key=lambda p: p.stat().st_mtime, default=None)
        render = max(masters or render_files, key=lambda p: p.stat().st_mtime_ns, default=None)
        url = lambda p: f"/videos/{quote(reel.name)}/" + quote(p.relative_to(reel).as_posix(), safe="/") if p else ""
        frames = filmstrip(render, hub / "frames" / reel.name)
        state = {k: {"saved_at": mtime(reel / f"{k}.state.json"),
                     "sends": {n: mtime(reel / n) for n in v.get("writes", [])}} for k, v in manifest.items()}
        beat = read(reel / "beat-map.state.json", {}) or {}
        try:
            sketches = read(reel / "sketches.state.json", {}) or {}
        except (OSError, ValueError):
            sketches = {}
        sound = read(reel / "sound-board.state.json", {}) or {}
        cues = sound.get("cues", [])
        voice_only_done = not cues and any(p.name == "final.mp4" for p in folders["sound"])
        chosen = read(reel / "sound-selection.json")
        placed = read(reel / "sound/placement.json")
        sound_voice_only = sound_pass_ran and (
            not chosen.get("cues") and not (chosen.get("bed") or {}).get("file") if isinstance(chosen, dict)
            else not placed.get("cues") and not (placed.get("bed") or {}).get("source") if isinstance(placed, dict)
            else voice_only_done)
        render_label = ("No render yet" if render is None else "Final master" if render in masters
                        else "Preview (720p)" if render in previews
                        else "First cut" if render.parent == reel / "work/renders" and render.match("master-*x.mp4")
                        else "Your recording" if render == reel / "RAW.mp4" or render.parent == reel / "raw"
                        else "Latest render")
        blocks = (read(reel / "work/map_check.json", {}) or {}).get("blocks", [])
        open_ = open_sends(reel, sends, snapshot.get("baseline"), snapshot.get("acked") or {})
        activity = max([mtime(p) for ps in folders.values() for p in ps] or [0])
        board_for = lambda *actions: next((b["id"] for b in boards if any(a in b["stages"] for a in actions)), None)
        lane = lambda label, key, value, total, board: dict(label=label, layer=key, done=int(value), total=total, board=board)
        lanes = [lane("Picture", "picture", (reel / "work/cuts.json").is_file(), 1, board_for("cut")),
                 lane("Motion", "motion", bool(beat.get("sent_at")) + bool(sketches.get("locked_at")), 2, board_for("motion")),
                 lane("Captions", "captions", any(p.suffix in (".ass", ".srt", ".vtt") and "caption" in p.name.lower()
                                                  for p in folders["work"] + folders["root"]) or (reel / "work/captions.json").is_file(), 1, board_for("captions")),
                 lane("Grade", "grade", (reel / "grade.json").is_file(), 1, board_for("grade")),
                 lane("Sound", "sound", 1 if voice_only_done else sum(bool(c.get("state")) for c in cues),
                      1 if voice_only_done else len(cues), board_for("sound")),
                 lane("Mix and master", "master", bool(masters), 1, "review")]
        rows.append(dict(id=reel.name, title=reel.name, stage=stages[cur]["name"], stage_id=stages[cur]["id"],
                         cur=cur, done=done, waiting_on="claude" if open_ else "you", open_sends=open_,
                         activity=activity, idle=now.timestamp()*1000-activity > 7*86400000,
                         frames=frames, render_url=url(render), render_label=render_label,
                         sound_board=(reel / "config.json").is_file() and is_real(reel / "config.json"),
                         sound_pack_installed=pack_installed, sound_pass_ran=sound_pass_ran,
                         sound_voice_only=sound_voice_only,
                         ready_to_post=ready_to_post,
                         master_url=url(max(masters, key=lambda p: p.stat().st_mtime_ns, default=None)),
                         preview_name=preview.name if preview else "", preview_url=url(preview),
                         cover_url=url(reel / "cover.jpg") if (reel / "cover.json").is_file() and (reel / "cover.jpg").is_file() else "",
                         qa=read(reel / "work/qa.json"), blocks=blocks, boards=state, lanes=lanes))
    # Use an existing hub state owner when available; sorting/selection does not move the workspace preference.
    owners = [r["id"] for r in rows if (videos / r["id"] / "hub.state.json").is_file()]
    cfg = rt.read_config(root)
    nle = cfg.get("nle", "none")
    controls = cfg.get("controls")
    return dict(schema=1, refreshed=now.isoformat(), config={"nle": nle,
                "controls": controls if controls in ("simple", "advanced") else "simple"},
                state_reel=next(iter(owners), rows[0]["id"] if rows else None), stages=stages, boards=boards,
                reels=rows, styles=style_rows(root),
                health=plain_health((read(root / "editor/.platform.json", {}) or {}).get("status", []), nle), goldmine=goldmine(root))


def style_rows(root):
    rows = saved_style.styles()
    for row in rows:
        try:
            row["auto"] = style_learn.status(row["id"], workspace=root)
        except (OSError, ValueError):
            row["auto"] = dict(ready=False, on=False, good_in_a_row=0, threshold=style_learn._threshold(root))
    return rows


def main(argv=None):
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    a = ap.parse_args(argv)
    try:
        data = build(a.root)
        editor, _ = workspace_paths(Path(a.root).resolve())
        dest = editor / "hub/hub-data.json"
        if not is_real(dest) or not is_real(dest.with_suffix(".json.tmp")):
            raise ValueError("Hub data is a link; left untouched")
        tmp = dest.with_suffix(".json.tmp")
        tmp.write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        os.replace(tmp, dest)
        print(f"Editor hub refreshed: {len(data['reels'])} reels, {len(data['boards'])} board tabs")
        return 0
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as e:
        print(f"Editor hub refresh failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
