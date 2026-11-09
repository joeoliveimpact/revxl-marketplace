#!/usr/bin/env python3
"""N1.2b check: reworded retakes on the Cut Board (H-UI-10, H-HUB-1, H-N1-4).

usage: python tests/editor/n1_board_test.py <scratch-dir> [--case NAME]
Prints PASS/FAIL per check; exit 0 = every check passed. --case runs one case (each one runs in under 150 s).
Cases: config, send, reload.

The fixture reel: boards_test.py's six-sentence window of S3's REEL_018 take, one take, with two sentences reworded
in a copy of its edit map (same times, same audio): the 5-word sentence after "And you don't have to be techie." now
says "You don't have techie skills." (a reworded retake of it, inside line L03's read), and the 12-word sentence after
it says "So, never, never pay for this, it is free to set up." (emphasis, never a retake). The script leaves the
reworded sentence out, so both reads of L03 sit in one attempt. Words after the window are left out of the map.

- config: make_board.py writes attempts[].review on L03 with exactly the two sentences' board indices; nothing of
  them is struck by default; the "never, never" line and every other line carry no review hit; the default
  selection passes selection_to_edl's board_hash check and keeps both sentences.
- send: through the real hub's Cut Board tab (the boards.json route), the flag text shows, "Keep first" then Send:
  cut-selection.json rm["0"] of L03 holds exactly the second sentence's indices, and selection_to_edl.py + gaps.py
  cut the second sentence and keep the first.
- reload: a new browser reopens the board; the struck words and the "Keep first" choice still show.
H-LOCK-1: headless Chrome only through boards_test's browse() (heavy_lock.py --min-gb 3; exit 75/76 = unproven).
"""
import argparse, json, shutil, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import boards_test as bt  # noqa: E402  (S4b.3's helpers: setup, server, browse, cut, selection, the real hub)

cs, ck, G = bt.cs, bt.ck, bt.G
REWORD = ["You", "don't", "have", "techie", "skills."]
NEVER = "So, never, never pay for this, it is free to set up.".split()
FLAG = "Said twice in different words: pick one"
L, J = 2, 0                      # line L03, its one attempt


def planted(name):
    """The reel with the planted reworded retake: (reel dir, config, the window's six sentences as map words)."""
    d = G["videos"] / name
    shutil.rmtree(d, ignore_errors=True)
    (d / "work").mkdir(parents=True)
    for n in bt.FX_FILES:
        shutil.copyfile(bt.FX / n, d / "work" / n)
    m = cs.load(bt.FX / "edit_map.json")
    se = bt.sentences(m)
    assert [len(s) for s in se] == [3, 3, 7, 5, 12, 8], [len(s) for s in se]
    for s, new in ((se[3], REWORD), (se[4], NEVER)):
        for w, t in zip(s, new):
            w["word"] = t
    m["words"] = m["words"][:m["words"].index(se[5][-1]) + 1]
    b = bt.bem()
    m["word_list_hash"] = b.word_list_hash(b.board_sequence(m))
    assert not b.validate(m), b.validate(m)
    bt.write(d / "work/edit_map.json", m)
    (d / "script.md").write_text("# Test script\n---\n" + "".join(" ".join(w["word"] for w in s) + "\n"
                                                             for k, s in enumerate(se) if k != 3), encoding="utf-8")
    bt.write(d / "shots.json", {"vocab": ["talking head", "screen"], "default": "talking head"})
    p = bt.script("make_board.py", "--script", d / "script.md",
                  "--take", "1:%s:%s" % (d / "work/edit_map.json", d / "work/tx.16k.wav"),
                  "--shots", d / "shots.json", "--reel", name, "-o", d)
    ck("%s: make_board.py builds cut-board.config.json (5 lines, 1 take)" % name,
       p.returncode == 0 and (d / "cut-board.config.json").is_file(), (p.returncode, p.stdout[-300:], p.stderr[-500:]))
    return d, cs.load(d / "cut-board.config.json"), se


def board_i(cfg, words):
    ix = {w["id"]: k for k, w in enumerate(cfg["takes"]["1"]["words"])}
    return [ix[w["id"]] for w in words]


def seeded(a):
    """The words the page's seedRm() strikes on a fresh board (sub_retakes only)."""
    return {w["i"] for w in a["words"] if any(sr["src_from"] - 0.01 <= w["s"] < sr["src_to"] - 0.01 for sr in a["sub_retakes"])}


def case_config(S, a):
    d, cfg, se = planted("config")
    lines = cfg.get("lines", [])
    if not ck("config: 5 lines, L03 has one attempt", len(lines) == 5 and len(lines[L]["attempts"]) == 1,
              [(l["id"], len(l["attempts"])) for l in lines]):
        return
    att = lines[L]["attempts"][J]
    first, second = board_i(cfg, se[2]), board_i(cfg, se[3])
    ck("config: both sentences sit inside L03's read (%s)" % att["text"],
       set(first + second) <= {w["i"] for w in att["words"]}, att["text"])
    rv = att.get("review")
    ck("config: L03 attempts[0].review = one hit, first = %s, second = %s (board i)" % (first, second),
       isinstance(rv, list) and len(rv) == 1 and rv[0].get("first") == first and rv[0].get("second") == second, rv)
    ck("config: the hit has a plain why line (%s)" % (rv[0].get("why") if rv else None),
       bool(rv) and isinstance(rv[0].get("why"), str) and len(rv[0]["why"]) > 10)
    ck("config: board i is not repeat_check's own list position (first i %s)" % first[:1], first[0] != 0)
    ck("config: nothing of the hit is struck by default (sub_retakes %s, seeded %s)" % (att["sub_retakes"], sorted(seeded(att))),
       not (seeded(att) & set(first + second)))
    nv = lines[3]
    ck("config: the 'never, never' line (%s) has no review hit and no sub-retake" % nv["attempts"][0]["text"][:40],
       "never, never" in nv["attempts"][0]["text"] and all(x.get("review") == [] and x["sub_retakes"] == [] for x in nv["attempts"]))
    others = [(l["id"], k) for i, l in enumerate(lines) for k, x in enumerate(l["attempts"]) if i != L and x.get("review")]
    ck("config: no other line has a review hit", not others, others)
    bt.write(d / "cut-selection.json", bt.selection(cfg, drop=()))
    p = bt.script("selection_to_edl.py", d / "cut-selection.json", d / "cut-board.config.json")
    edl = cs.load(d / "work/edl.json")
    ck("config: the default selection passes selection_to_edl (board_hash holds with review in the config)",
       p.returncode == 0, (p.returncode, p.stderr[-300:]))
    t0, t1 = se[2][0]["start"], se[3][0]["start"]
    inside = lambda t: any(e["line"] == "L03" and e["src_in"] <= t < e["src_out"] for e in edl if isinstance(edl, list))
    ck("config: ... and its EDL keeps both sentences (never auto-cut)", inside(t0) and inside(t1), edl)


KEEP_FIRST = '[data-keep="%d:%d:0:first"]' % (L, J)


def case_send(S, a):
    d, cfg, se = planted("send")
    bt.refresh_hub()
    first, second = board_i(cfg, se[2]), board_i(cfg, se[3])
    want = "s.lines[%d].rm['%d'] && s.lines[%d].rm['%d'].length===%d" % (L, J, L, J, len(second))
    out = bt.browse([{"do": "goto", "path": "/editor/hub/?reel=send", "waitFn": "window.Hub && Hub.ready"},
                     {"do": "click", "sel": "#tab-cut-board"},
                     dict(do="frame", sel=".frame iframe", **bt.CUT_READY),
                     {"do": "eval", "js": "(document.querySelector('[data-review=\"%d:%d:0\"] .rflag')||{}).textContent" % (L, J)},
                     {"do": "eval", "js": "JSON.stringify(S.lines[%d].rm)" % L},
                     {"do": "click", "sel": KEEP_FIRST},
                     {"do": "waitState", "board": "cut-board", "js": want},
                     {"do": "eval", "js": "[...document.querySelectorAll('.w.rm[data-w^=\"%d:%d:\"]')].map(e=>+e.dataset.w.split(':')[2])" % (L, J)},
                     {"do": "click", "sel": "#send"}, {"do": "waitText", "sel": "#saved", "re": "saved cut-selection\\.json|FAILED"},
                     {"do": "top"}, {"do": "eval", "js": "document.querySelector('.frame iframe').getAttribute('src')"}],
                    "n1-send")
    r = out["reads"]
    if not ck("send: the page answered every read", len(r) == 4, r):
        return
    ck("send: the Cut Board opened in the hub's frame at /editor/cut-board/?reel=send", r[3] == "/editor/cut-board/?reel=send", r[3])
    ck("send: L03 shows the flag '%s'" % r[0], r[0] == FLAG)
    rm0 = json.loads(r[1] or "{}").get(str(J), [])
    ck("send: before the click nothing of the hit is struck (rm %s)" % rm0, not set(rm0) & set(first + second))
    ck("send: after 'Keep first' the page strikes the second sentence's words %s" % r[2], sorted(r[2]) == second, r[2])
    sel = cs.load(d / "cut-selection.json")
    got = ((sel.get("lines") or [{}] * 5)[L].get("rm") or {}).get(str(J))
    ck("send: cut-selection.json L03 rm['0'] is exactly the second sentence %s (%s)" % (second, got),
       got is not None and sorted(got) == second)
    p, g, argv = bt.cut(d, d / "cut-selection.json")
    if not ck("send: selection_to_edl.py and the gaps.py command it printed run",
              p.returncode == 0 and g is not None and g.returncode == 0, (p.stderr[-300:], g and g.stderr[-300:])):
        return
    cuts = cs.load(d / "work/cuts.json")
    fps = cuts["fps"]
    out2 = [(w["word"], round(cs.kept_in(cuts, w["start"], w["end"]), 3)) for w in se[3]]
    in1 = [(w["word"], round(cs.kept_in(cuts, w["start"], w["end"]) / (w["end"] - w["start"]), 2)) for w in se[2]]
    ck("send: every word of the second sentence is out of cuts.json (kept s, at most a frame: %s)" % out2,
       all(k <= 1.0 / fps + 1e-6 for _, k in out2))
    ck("send: every word of the first sentence is in it (share of each word kept: %s)" % in1, all(k >= 0.8 for _, k in in1))


def case_reload(S, a):
    d, cfg, se = planted("reload")
    second = board_i(cfg, se[3])
    want = "s.lines[%d].rm['%d'] && s.lines[%d].rm['%d'].length===%d" % (L, J, L, J, len(second))
    bt.browse([dict(do="goto", path="/editor/cut-board/?reel=reload", **bt.CUT_READY), {"do": "click", "sel": KEEP_FIRST},
               {"do": "waitState", "board": "cut-board", "js": want},
               {"do": "click", "sel": "#send"}, {"do": "waitText", "sel": "#saved", "re": "saved cut-selection\\.json|FAILED"}],
              "n1-reload-1")
    out = bt.browse([dict(do="goto", path="/editor/cut-board/?reel=reload", **bt.CUT_READY),
                     {"do": "eval", "js": "JSON.stringify(S.lines[%d].rm)" % L},
                     {"do": "eval", "js": "[...document.querySelectorAll('.w.rm[data-w^=\"%d:%d:\"]')].map(e=>+e.dataset.w.split(':')[2])" % (L, J)},
                     {"do": "eval", "js": "[...document.querySelectorAll('[data-keep^=\"%d:%d:0:\"]')].map(b=>[b.textContent,b.classList.contains('on'),b.getAttribute('aria-pressed')])" % (L, J)},
                     {"do": "eval", "js": "(document.querySelector('[data-review=\"%d:%d:0\"] .rflag')||{}).textContent" % (L, J)}],
                    "n1-reload-2")
    r = out["reads"]
    if not ck("reload: the page answered every read", len(r) == 4, r):
        return
    rm = json.loads(r[0] or "{}").get(str(J), [])
    ck("reload: a new browser (no local copy) has L03 rm['0'] = the second sentence %s (%s)" % (second, rm), sorted(rm) == second)
    ck("reload: the struck words on the page are the second sentence's (%s)" % r[1], sorted(r[1]) == second)
    ck("reload: the choice shows: only 'Keep first' is on (%s)" % r[2],
       r[2] == [["Keep first", True, "true"], ["Keep second", False, "false"], ["Keep both", False, "false"]])
    ck("reload: the flag still shows", r[3] == FLAG, r[3])


CASES = {"config": case_config, "send": case_send, "reload": case_reload}


def main():
    cs.ensure_utf8_output()
    ap = argparse.ArgumentParser()
    ap.add_argument("scratch")
    ap.add_argument("--case", choices=list(CASES))
    a = ap.parse_args()
    S = Path(a.scratch).resolve()
    S.mkdir(parents=True, exist_ok=True)
    bt.setup(S)
    state_json = Path(bt.rt.state_dir()) / "state.json"
    before = bt.sha(state_json)
    try:
        for name in [a.case] if a.case else list(CASES):
            t0 = time.time()
            print("-- %s" % name)
            CASES[name](S, a)
            print("   (%s: %.0f s)" % (name, time.time() - t0))
    finally:
        if G.get("server"):
            G["server"].kill()
            G["server"].wait(10)
            G["server"].stdout.close()
        shutil.rmtree(S / "profiles", ignore_errors=True)
        for f in G["videos"].glob("*/work/tx.16k.wav"):
            f.unlink()
    ck("state.json sha256 unchanged (%s, %s)" % (before[:12], state_json), bt.sha(state_json) == before)
    print("\n%d failed" % len(bt.fails) if bt.fails else "\nall passed")
    return 1 if bt.fails else 0


if __name__ == "__main__":
    sys.exit(main())
