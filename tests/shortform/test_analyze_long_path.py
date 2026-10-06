# analyze.py in a long project folder on Windows. usage: python tests/shortform/test_analyze_long_path.py (prints OK or fails)
# A tiny invented fixture in a 230-character folder: the profile file sits past 260 characters, so a read
# that misses the \\?\ form (or joins it with forward slashes) loses the competitor's followers or crashes.
# A network (UNC) folder past 150 characters stops with exit 10 and a plain message, before any read.
import json, os, shutil, subprocess, sys, tempfile

if os.name != "nt":
    print("SKIP: Windows-only (no 260-character limit here)")
    sys.exit(0)

A = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "plugins", "shortform-superengine",
                 "skills", "competitor-cross-reference", "analyze.py")
X = lambda p: "\\\\?\\" + p                                      # write the fixture past 260 characters


def reel(i, views):
    return {"post": {"url": "https://www.instagram.com/reel/r%03d/" % i,
                     "content": {"text": "Why your mornings fail %d" % i, "duration_seconds": 20},
                     "engagement": {"views": views, "likes": 10, "comments": 1},
                     "published_at": "2026-09-%02dT12:00:00Z" % (i % 28 + 1)}}


def put(path, obj):
    os.makedirs(X(os.path.dirname(path)), exist_ok=True)
    with open(X(path), "w", encoding="utf-8") as f:
        json.dump(obj, f)


def run(project):
    r = subprocess.run([sys.executable, A, project], capture_output=True, text=True, timeout=120,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    return r.returncode, r.stdout + r.stderr


base = tempfile.mkdtemp()
try:
    d = os.path.join(base, "p" * (229 - len(base)))               # 230 characters
    assert len(d) == 230, len(d)
    put(os.path.join(d, "tiers.json"), {"client": "me", "client_followers": 1000, "LARGE": [], "MED": ["comp"],
                                        "SMALL": []})
    put(os.path.join(d, "source", "reels-full.json"), {"reels": [reel(i, 500) for i in range(5)]})
    put(os.path.join(d, "source", "competitors", "reels", "comp.json"),
        {"reels": [reel(i + 10, 1000 * (i + 1)) for i in range(5)]})
    prof = os.path.join(d, "source", "competitors", "profiles", "comp.json")
    put(prof, {"data": {"author": {"followers": 4321}}})
    assert len(prof) > 260, len(prof)

    code, out = run(d)
    assert code == 0, (code, out[-800:])
    with open(X(os.path.join(d, "analysis-data.json")), encoding="utf-8") as f:
        cr = {c["handle"]: c for c in json.load(f)["creators"]}
    assert cr["comp"]["followers"] == 4321, cr["comp"]           # the profile past 260 characters was read
    assert cr["comp"]["stats"]["n"] == 5 and cr["me"]["stats"]["n"] == 5, cr
    print("OK long local folder (%d characters, deepest file %d)" % (len(d), len(prof)))

    unc = "\\\\nohost\\share\\" + "u" * 150
    code, out = run(unc)
    assert code == 10, (code, out[-800:])
    assert "network folder with a long path" in out and "Traceback" not in out, out[-800:]
    print("OK long network folder -> exit 10, plain message")
finally:
    shutil.rmtree(X(base), ignore_errors=True)
