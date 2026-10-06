#!/bin/bash
# Reset the walk state before a run, for one fixture: rebuild its project from its seed (no scripts/), clear scripts[], angles_unpicked[] and open_loops in that brand's state file, point its project_path at the project, and set the marker's active_brand to that brand. Idempotent. <state> = RS_WALK_STATE, default $HOME/rs-walk-state. usage: bash reset.sh [gut|contra]
#   gut (default): seed-proj/ from this folder -> <state>/proj, brand fixturebrand
#   contra: <state>/fixtures/contra-seed (kept outside the repo) -> <state>/proj-contra, brand contrabrand
D="$(cd "$(dirname "$0")" && pwd)"; S="$(cygpath -m "${RS_WALK_STATE:-$HOME/rs-walk-state}")"
case "${1:-gut}" in
  gut) SRC="$D/seed-proj"; P="$S/proj"; B=fixturebrand;;
  contra) SRC="$S/fixtures/contra-seed"; P="$S/proj-contra"; B=contrabrand;;
  *) echo "refuse: unknown fixture $1 (gut or contra)"; exit 2;;
esac
F="$S/home/.claude/shortform-superengine/state/$B.json"; M="$S/home/.claude/shortform-superengine/.superengine"
[ -d "$SRC" ] && [ -f "$F" ] && [ -f "$M" ] || { echo "refuse: $SRC, $F or $M missing (set RS_WALK_STATE)"; exit 2; }
rm -rf "$P" && mkdir -p "$P" && cp -R "$SRC/." "$P/" && rm -rf "$P/scripts" || exit 1
PYTHONIOENCODING=utf-8 py -3.12 - "$F" "$P" "$M" "$B" <<'EOF' || exit 1
import json, sys
f, proj, m, brand = sys.argv[1:]
def rw(p, fix, indent=2):
    with open(p, encoding="utf-8") as h:
        d = json.load(h)
    fix(d)
    with open(p, "w", encoding="utf-8", newline="\n") as h:
        json.dump(d, h, indent=indent)
        h.write("\n")
def state(d):
    d["scripts"], d["angles_unpicked"], d["open_loops"] = [], [], []
    d["project_path"] = proj
rw(f, state)
rw(m, lambda d: d.update(active_brand=brand, brand=brand), None)
EOF
echo "reset: $P rebuilt from $SRC; scripts, angles_unpicked, open_loops cleared and project_path set to $P in $F; active_brand $B in $M"
