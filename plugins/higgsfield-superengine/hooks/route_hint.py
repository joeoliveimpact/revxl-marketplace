#!/usr/bin/env python3
"""route_hint.py - the routing hint (plan 4.3) of the higgsfield-superengine plugin: a UserPromptSubmit hook.
Standard library only, Python 3.9+.

OFF until Jev passes Phase 6: it is NOT registered in hooks.json, so it never runs (and a hook that failed to start
would show a notice on every prompt). To switch it on, add this to hooks.json "hooks":
  "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "py",
                        "args": ["-3", "-B", "${CLAUDE_PLUGIN_ROOT}/hooks/route_hint.py"], "timeout": 5}]}]
What it does: reads the hook JSON on stdin. A cheap word filter runs first, so ordinary prompts never reach the
network. Then ONE Jev call via scripts/decide.py (2.5 s deadline): the average of 3 "is a generation wanted" Nouls
(cut at GATE) plus a Choice across the plugin's skills. If both pass, it adds one factual line of additionalContext
naming the skill; Claude still decides. Anything else (no match, no-jev, bad input, any error) prints nothing and
exits 0. GATE and MIN_PROB are placeholders for Phase 6 to tune (R3: average of ~3 action Nouls, cut 0.30).
  route_hint.py --selftest    offline checks against a local mock of OpenRouter (decide.py's loopback override)
"""
import json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
GATE, MIN_PROB = 0.30, 0.50
FILTER = re.compile(r"(?i)\b(images?|pictures?|pics?|photos?|videos?|clips?|ads?|adverts?|thumbnails?|ugc|renders?|"
                    r"visuals?|reels?|banners?|posters?|(?:pack)?shots?|photograph(?:s|ed|y)?|portraits?|icons?|pngs?|"
                    r"film(?:s|ed|ing)?|testimonials?|reveals?|scenes?|higgsfield|seedance|kling|flare|wan|minimax|pixverse|hailuo)\b")
SKILLS = {
    "static-ads": "a static ad image (social or display ad creative)",
    "ugc-video-ads": "a UGC-style video ad (a person talking to camera about a product)",
    "product-shots": "a product photo or packshot",
    "thumbnails": "a YouTube or video thumbnail",
    "image-prompting": "any other AI image generation, or writing an image prompt",
    "video-prompting": "any other AI video generation, or writing a video prompt",
    "none": "not a request to create or plan an AI image or video",
}


def noul(text):
    return {"type": "noul", "instructions": text,
            "criteria": {"true": "Yes: the user wants that made or planned now.", "false": "No, or only talking about it."}}


QUESTIONS = {
    "gen_image": noul("Does `prompt` ask for an AI-generated image to be created?"),
    "gen_video": noul("Does `prompt` ask for an AI-generated video to be created?"),
    "gen_visual": noul("Does `prompt` want a visual asset (ad, thumbnail, product shot, UGC clip) generated?"),
    "skill": {"type": "choice", "instructions": "Which skill best fits `prompt`?", "criteria": SKILLS},
}


def hint(data):
    """-> the additionalContext line, or None."""
    prompt = data.get("prompt") if isinstance(data, dict) else None
    if not isinstance(prompt, str) or not FILTER.search(prompt):
        return None
    sys.path.insert(0, str(SCRIPTS))
    import decide
    r = decide.decide({"state": {"prompt": prompt[:4000]}, "questions": QUESTIONS})
    if r.get("result") != "jev":
        return None
    a = r["answers"]
    gate = sum(a[q]["noul"] for q in ("gen_image", "gen_video", "gen_visual")) / 3
    choice = a["skill"]["choice"]
    prob = a["skill"]["probabilities"].get(choice)
    if gate < GATE or choice == "none" or not isinstance(prob, (int, float)) or prob < MIN_PROB:
        return None
    return (f"Routing hint (higgsfield-superengine): this request looks like {SKILLS[choice]}. The skill "
            f"higgsfield-superengine:{choice} covers it. Use it only if it fits.")


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    try:
        line = hint(json.loads(sys.stdin.buffer.read().decode("utf-8", "replace")))
    except Exception:
        line = None  # a hint is optional: never a notice, never a block
    if line:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                            "additionalContext": line}}))
    return 0


def selftest():
    import os, shutil, subprocess, tempfile, threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    sys.path.insert(0, str(SCRIPTS))
    import decide

    tmp = Path(tempfile.mkdtemp(prefix="route-hint-selftest-"))
    st = {"mode": "yes", "bodies": []}
    results = []

    def check(name, ok, detail=""):
        results.append(bool(ok))
        print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   [{detail}]"))

    class Mock(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            st["bodies"].append(json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0))))
            if st["mode"] == "500":
                self.send_response(500)
                self.end_headers()
                return
            g = {"yes": 0.9, "low": 0.1, "none": 0.9}[st["mode"]]
            ch = "none" if st["mode"] == "none" else "static-ads"
            ans = {q: {"type": "noul", "noul": g} for q in ("gen_image", "gen_video", "gen_visual")}
            ans["skill"] = {"type": "choice", "choice": ch, "confidence": 0.8, "probabilities": {ch: 0.85}}
            data = json.dumps({"id": "d1", "model": decide.MODEL, "answers": ans, "usage": {"cost": 1e-05}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Mock)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    env = dict(os.environ, OPENROUTER_API_KEY="sk-or-v1-routehintFAKE0123456789", USERPROFILE=str(tmp),
               HOME=str(tmp), HF_SUPERENGINE_JEV_BASE=f"http://127.0.0.1:{srv.server_address[1]}")

    def run(raw):
        n = len(st["bodies"])
        r = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve())], input=raw, env=env,
                           capture_output=True, timeout=30)
        return r.returncode, r.stdout.decode(), r.stderr.decode(), len(st["bodies"]) - n

    def ev(prompt):
        return json.dumps({"session_id": "s", "transcript_path": "t", "cwd": str(tmp), "permission_mode": "default",
                           "hook_event_name": "UserPromptSubmit", "prompt": prompt}).encode()

    try:
        c, o, e, n = run(ev("fix the failing unit test in parser.py"))
        check("R1 ordinary prompt -> nothing printed, no Jev call", (c, o, e, n) == (0, "", "", 0), (c, o, e, n))
        c, o, e, n = run(ev("make a static ad image for my red running shoe"))
        j = json.loads(o) if o else {}
        h = j.get("hookSpecificOutput", {})
        check("R2 generation prompt + Jev yes -> one additionalContext line naming higgsfield-superengine:static-ads",
              c == 0 and e == "" and n == 1 and h.get("hookEventName") == "UserPromptSubmit" and
              "higgsfield-superengine:static-ads" in h.get("additionalContext", ""), o)
        b = st["bodies"][-1]
        check("R3 the Jev request: pinned model, zdr, the prompt in state, 3 Nouls + the skill Choice",
              b.get("model") == decide.MODEL and b.get("provider", {}).get("zdr") is True and
              b["state"]["prompt"].startswith("make a static ad") and set(b["questions"]) == set(QUESTIONS), b)
        for mode, name in (("low", "R4 Jev says no (average Noul 0.1)"), ("none", "R5 Jev picks 'none'"),
                           ("500", "R6 Jev server error (no-jev)")):
            st["mode"] = mode
            c, o, e, n = run(ev("make a video ad for my shoe"))
            check(f"{name} -> nothing printed, exit 0", (c, o, e, n) == (0, "", "", 1), (c, o, e, n))
        st["mode"] = "yes"
        c, o, e, n = run(b"not json at all {")
        check("R7 unparsable hook input -> nothing printed, exit 0", (c, o, e, n) == (0, "", "", 0), (c, o, e))
        (tmp / ".config" / "openrouter").mkdir(parents=True)
        (tmp / ".config" / "openrouter" / "jev_declined").write_text("")
        c, o, e, n = run(ev("make a static ad image"))
        check("R8 Jev declined -> nothing printed, no Jev call", (c, o, e, n) == (0, "", "", 0), (c, o, e, n))
        hj = json.loads((Path(__file__).resolve().parent / "hooks.json").read_text(encoding="utf-8"))
        check("R9 OFF: hooks.json registers no UserPromptSubmit hook", "UserPromptSubmit" not in hj["hooks"])
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
