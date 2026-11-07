#!/usr/bin/env python3
"""Synthetic, media-free proof of the pre-render caption truth check (HF-4).

Usage: python tests/editor/caption_check_test.py <scratch-dir> [--case NAME]
Print PASS/FAIL lines; exit 0 only when all checks pass. Fixtures use the real
captions.plan(), then plant one fault. Standalone checks use -X utf8 -I.
"""
import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from editor_test_state import isolated_home

REPO = Path(__file__).resolve().parents[2]
SKILLS = REPO / "plugins/editor-superengine/skills"
CHECK = SKILLS / "_shared/checks/caption_check.py"
sys.path.insert(0, str(SKILLS / "_shared"))
import runtime as rt  # noqa: E402
from win_encoding import ensure_utf8_output  # noqa: E402

FPS, TOTAL = 30, 120
CASES = {
    "clean": None, "word": "caption-word", "swap": None,
    "lost": "caption-word-lost", "declared": None, "typed": "caption-time",
    "drift": None, "grid": "caption-grid", "pastend": "caption-past-end",
    "offframe": "caption-off-frame", "edge": None, "nocaps": None,
    "off": None, "twice": "caption-word-twice", "unreadable": "caption-file",
    "chunk-time": "caption-time", "chunk-grid": "caption-grid",
    "chunk-drift": None, "chunk-anchor": "caption-time",
    "word-end-grid": "caption-grid", "empty-span": "caption-past-end",
    "edge8": "caption-off-frame", "right": "caption-off-frame",
    "top": "caption-off-frame", "bottom": "caption-off-frame",
    "punctuation": None, "symbols": None, "reverse-swap": None,
    "wrong-position": ("caption-word", "caption-word-lost"), "integer-float": None,
    "drift-boundary": None, "drift-over": "caption-time",
    "round-at": "caption-word", "negative-start": "caption-past-end", "start-at-end": "caption-past-end",
}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8"))


def fixture(root, name, captions):
    reel = root / name
    text = "We save fifteen percent and feel okay today."
    if name == "symbols":
        text = "one two fifteen percent and dollars okay today."
    elif name == "reverse-swap":
        text = "We save 15% and feel okay today."
    words = [{"id": f"source_{100 + i}", "word": t,
              "start": (6 + i * 9) / FPS, "end": (12 + i * 9) / FPS}
             for i, t in enumerate(text.split())]
    put(reel / "work/edit_map.cut.json", {"words": words})
    cuts = {"fps": FPS, "segments": [{"src_in_f": 0, "src_out_f": TOTAL,
                                      "out_in_f": 0, "out_out_f": TOTAL}]}
    put(reel / "work/cuts.json", cuts)
    put(reel / "beat-map-selection.json", {
        "beats": [], "word_marks": [],
        "caption_style": {"style": "none" if name == "off" else "clean",
                          "accent": "#FFD84D"},
    })
    doc = captions.plan(reel)
    for chunk in doc["chunks"]:
        chunk["box"] = [100, 1200, 980, 1340]
    return reel, doc, words, cuts


def plant(name, doc, words):
    if name == "off":
        return
    chunk = doc["chunks"][0]
    word = chunk["words"][1]  # Not the chunk's first word: timing faults stay isolated.
    if name == "word":
        word["text"] = "spend"
    elif name == "swap":
        for c in doc["chunks"]:
            for w in c["words"]:
                if w["w"] == 2:
                    w["text"] = "15%"
            c["words"] = [w for w in c["words"] if w["w"] != 3]
    elif name in ("lost", "declared"):
        chunk["words"].remove(word)
        if name == "declared":
            doc["declared_drops"].append({"w": word["w"], "why": "client choice"})
    elif name in ("typed", "drift"):
        word["start_f"] += 4 if name == "typed" else 2
    elif name == "grid":
        word["start_f"] = 12.5
    elif name == "pastend":
        chunk["end_f"] = TOTAL + 1
    elif name in ("offframe", "edge", "edge8"):
        chunk["box"][0] = {"offframe": -10, "edge": -5, "edge8": -8}[name]
    elif name == "twice":
        doc["declared_drops"].append({"w": word["w"], "why": "client choice"})
    elif name == "chunk-time":
        chunk["start_f"] += 4
    elif name in ("chunk-drift", "chunk-anchor"):
        chunk["start_f"] += 2 if name == "chunk-drift" else 4
        chunk["words"][0]["start_f"] += 2
    elif name == "chunk-grid":
        chunk["end_f"] += 0.5
    elif name == "word-end-grid":
        word["end_f"] = word["start_f"] + 0.5
    elif name == "empty-span":
        chunk["end_f"] = chunk["start_f"]
    elif name in ("right", "top", "bottom"):
        edge, value = {"right": (2, 1088), "top": (1, -8), "bottom": (3, 1928)}[name]
        chunk["box"][edge] = value
    elif name == "punctuation":
        for c in doc["chunks"]:
            for w in c["words"]:
                w["text"] = "\u201c" + w["text"].upper() + "!\u201d"
    elif name == "symbols":
        replacements = {0: "1", 1: "2", 2: "15", 3: "%", 4: "&", 5: "$", 6: "OK"}
        for c in doc["chunks"]:
            for w in c["words"]:
                w["text"] = replacements.get(w["w"], w["text"])
    elif name == "reverse-swap":
        for c in doc["chunks"]:
            for w in c["words"]:
                if w["w"] == 2:
                    w["text"] = "fifteen percent"
    elif name == "wrong-position":
        word["w"] = 200
    elif name == "integer-float":
        for c in doc["chunks"]:
            for entry in [c, *c["words"]]:
                for key in ("start_f", "end_f"):
                    if key in entry:
                        entry[key] = float(entry[key])
    elif name in ("drift-boundary", "drift-over"):
        # With a transcript anchor 14.1, frame 17 is exactly 80 ms + half a frame away.
        words[word["w"]]["start"] = 14.1 / FPS
        word["start_f"] = 17 if name == "drift-boundary" else 18
    elif name == "round-at":
        word["text"] = "spend"
        words[word["w"]]["start"] = 0.512345
    elif name in ("negative-start", "start-at-end"):
        # Keep drift within tolerance, so only the range check can catch it.
        word["start_f"] = -1 if name == "negative-start" else TOTAL
        words[word["w"]]["start"] = word["start_f"] / FPS
    for c in doc["chunks"]:
        c["text"] = " ".join(w["text"] for w in c["words"])


@isolated_home()
def main():
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    args = ap.parse_args()
    scratch = Path(args.scratch).resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    # Each run owns a fresh subtree; never remove a caller's scratch files.
    root = Path(tempfile.mkdtemp(prefix="caption-check-", dir=scratch))
    captions = module("captions", SKILLS / "reel-captions/scripts/captions.py")
    checker = module("caption_check", CHECK)
    candidate = rt.tool("python")
    python = candidate if Path(candidate).is_file() else sys.executable
    failures = []

    def ck(label, ok, detail=""):
        print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  [{detail}]"))
        if not ok:
            failures.append(label)

    ck("contract: pre-render module", checker.PHASE == "pre")
    for name in [args.case] if args.case else CASES:
        try:
            reel, doc, words, cuts = fixture(root, name, captions)
            plant(name, doc, words)
            put(reel / "work/edit_map.cut.json", {"words": words})
            put(reel / "work/cuts.json", cuts)
            path = reel / "work/captions.json"
            if name == "unreadable":
                path.write_bytes(b"{broken\n")
            elif name != "nocaps":
                captions.write(reel, doc)
            before = {p: p.read_bytes() for p in reel.rglob("*") if p.is_file()}
            # Wrong context values ensure the saved cut supplies fps and duration.
            rows = checker.run({"reel_dir": reel, "fps": 99, "cuts": {}, "beats": [], "render": None})
            expected = CASES[name]
            wanted = [] if expected is None else [expected] if isinstance(expected, str) else list(expected)
            kinds = [r["check"] for r in rows]
            ck(name + ": findings", kinds == wanted, rows)
            level = "warn" if name == "twice" else "block"
            ck(name + ": row contract", all(
                r["level"] == level and isinstance(r["msg"], str) and r["msg"]
                and "\n" not in r["msg"] and "\r" not in r["msg"]
                and isinstance(r["where"], str) and r["where"].startswith("caption ")
                and ("at" not in r or isinstance(r["at"], float)) for r in rows), rows)
            ck(name + ": seek times rounded", all("at" not in r or r["at"] == round(r["at"], 2) for r in rows), rows)
            if name == "round-at":
                ck(name + ": exact rounded seek time", len(rows) == 1 and rows[0].get("at") == .51, rows)
            result = subprocess.run([str(python), "-X", "utf8", "-I", str(CHECK), str(reel)],
                                    capture_output=True, text=True, encoding="utf-8", timeout=30)
            exit_code = 1 if expected and level == "block" else 0
            ck(name + ": standalone exit", result.returncode == exit_code,
               (result.returncode, result.stdout, result.stderr))
            ck(name + ": standalone plain lines", not result.stderr
               and all(kind in result.stdout for kind in wanted), (result.stdout, result.stderr))
            after = {p: p.read_bytes() for p in reel.rglob("*") if p.is_file()}
            ck(name + ": read only", before == after)
        except Exception as exc:
            ck(name + ": runs without error", False, repr(exc))
    print(f"\n{len(failures)} failed" if failures else "\nall passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
