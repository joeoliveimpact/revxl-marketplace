"""Grade one reel-scripter walk transcript against RUBRIC.md. Usage: py -3.12 grade.py run1.jsonl

Reads <state>/logs/<name> and <state>/proj; <state> is RS_WALK_STATE (default
<home>/rs-walk-state), the same folder run-mt2.sh writes to. The gate it re-runs is the one
in this repo, found from this file's own location."""
import json, os, re, sys
from pathlib import Path

D = Path(os.environ.get("RS_WALK_STATE") or Path.home() / "rs-walk-state")
GATE = Path(__file__).resolve().parents[3] / "plugins/shortform-superengine/skills/reel-scripter/structure_gate.py"
raw = (D / "logs" / sys.argv[1]).read_text("utf-8", errors="replace")
ev = [json.loads(l) for l in raw.splitlines() if l.strip().startswith("{")]
init = next((e for e in ev if e.get("type") == "system" and e.get("subtype") == "init"), {})
res = next((e for e in reversed(ev) if e.get("type") == "result"), {})

plugins = init.get("plugins", [])
skills = init.get("skills", []) or init.get("slash_commands", [])
print("V1 plugins:", [(p.get("name"), p.get("path")) for p in plugins])
print("V1 skills loaded:", len(skills), "| marketplaces paths in transcript:", raw.count(".claude/plugins/marketplaces/") + raw.count(".claude\\\\plugins\\\\marketplaces\\\\"))

calls, writes, order, bash_writes = [], [], [], []
for e in ev:
    if e.get("type") != "assistant":
        continue
    for c in e["message"]["content"]:
        if c.get("type") == "tool_use":
            name, inp = c["name"], c.get("input", {})
            if name == "Skill":
                calls.append(inp.get("skill") or inp.get("command"))
                order.append(f"Skill:{calls[-1]}")
            elif name in ("Write", "Edit", "NotebookEdit"):
                writes.append(inp.get("file_path", ""))
                order.append(f"{name}:{Path(inp.get('file_path', '')).name}")
            elif name in ("Bash", "PowerShell") and re.search(r"(>|tee )[^>]*\.(md|json)", inp.get("command", "")):
                bash_writes.append(inp.get("command", "")[:160].replace(chr(10), " "))
                order.append("BashWrite")
            elif name == "AskUserQuestion":
                order.append("AskUserQuestion")
        elif c.get("type") == "text" and re.search(r"Checkpoint [0-3]", c.get("text", "")):
            order.append("text:" + ",".join(sorted(set(re.findall(r"Checkpoint [0-3]", c["text"])))))

print("\nSequence:", " > ".join(order))
print("\nSkill calls:", calls)
has = lambda n: any(s and s.split(":")[-1] == n for s in calls)
for rid, n, req in (("R1", "angles", True), ("R2", "rehooks", True), ("R3", "hook", True), ("R4", "polarize", False), ("R4", "viral", False)):
    print(f"{rid} {n}: {'called' if has(n) else 'NOT called'}{'' if req else ' (conditional)'}")
scratch = str(D).replace("\\", "/").lower()
script = [w for w in writes if "/scripts/" in w.replace("\\", "/")]
outside = [w for w in writes if not w.replace("\\", "/").lower().startswith(scratch) and scratch not in w.replace("\\", "/").lower()]
print("R5 script files written:", script)
print("R6 writes outside scratch:", outside or "none")
print("R5b script files on disk:", [p.name for p in (D / "proj" / "scripts").glob("*.md")])
print("R6b Bash/PowerShell writes (check targets by eye):"); [print("   ", b) for b in bash_writes]
import subprocess
prov = D / "proj" / "reel-build" / "provenance.md"
print("provenance.md:", prov.read_text("utf-8-sig").splitlines() if prov.exists() else "missing")
for sk in (D / "proj" / "scripts").glob("*.skeleton.md"):
    print("Skeleton from: lines:", [l for l in sk.read_text("utf-8").splitlines() if l.lower().startswith(("from:", "angle_from:"))])
    r = subprocess.run([sys.executable, str(GATE), str(sk)], capture_output=True, text=True)
    print(f"Gate re-run on {sk.name} (passes only on the skeleton whose passed: line provenance.md holds): exit {r.returncode}"); print("   " + r.stdout.strip().replace(chr(10), chr(10) + "   "))
gate_runs = [e for e in ev if e.get("type") == "user" and "Seams: " in json.dumps(e)]
print("Gate outputs seen in transcript (Seams: lines):", len(gate_runs))
print(f"\nresult: subtype={res.get('subtype')} turns={res.get('num_turns')} cost=${res.get('total_cost_usd')} is_error={res.get('is_error')}")
print("final text:", (res.get("result") or "")[-600:])
