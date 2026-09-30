#!/bin/bash
# Reset the walk state before a run: rebuild <state>/proj from seed-proj (no scripts/) and clear scripts[], angles_unpicked[] and open_loops in the fixture brand's state file, and point its project_path at <state>/proj. Idempotent. <state> = RS_WALK_STATE, default $HOME/rs-walk-state. usage: bash reset.sh
D="$(cd "$(dirname "$0")" && pwd)"; S="$(cygpath -m "${RS_WALK_STATE:-$HOME/rs-walk-state}")"
F="$S/home/.claude/shortform-superengine/state/fixturebrand.json"
[ -d "$D/seed-proj" ] && [ -f "$F" ] || { echo "refuse: seed-proj or $F missing (set RS_WALK_STATE)"; exit 2; }
rm -rf "$S/proj" && mkdir -p "$S/proj" && cp -R "$D/seed-proj/." "$S/proj/" && rm -rf "$S/proj/scripts" || exit 1
PYTHONIOENCODING=utf-8 py -3.12 - "$F" "$S/proj" <<'EOF' || exit 1
import json, sys
p = sys.argv[1]
with open(p, encoding="utf-8") as f:
    d = json.load(f)
d["scripts"], d["angles_unpicked"], d["open_loops"] = [], [], []
d["project_path"] = sys.argv[2]
with open(p, "w", encoding="utf-8", newline="\n") as f:
    json.dump(d, f, indent=2)
    f.write("\n")
EOF
echo "reset: $S/proj rebuilt from seed-proj; scripts, angles_unpicked, open_loops cleared and project_path set to $S/proj in $F"
