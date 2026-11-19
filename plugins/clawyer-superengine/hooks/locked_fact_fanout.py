#!/usr/bin/env python3
"""PostToolUse hook (Edit/Write): when case-profile.md changes, inject the fan-out checklist.

Silent outside a Clawyer workspace. Non-blocking; swallows every error. The matter folder comes from
firm.config.json (paths.matter_home).
"""
import json
import os
import sys
from pathlib import Path

try:
    payload = json.load(sys.stdin)
    ws = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    M = json.loads((ws / "firm.config.json").read_text(encoding="utf-8"))["paths"]["matter_home"]
    path = (payload.get("tool_input", {}) or {}).get("file_path", "") or ""
    if "case-profile" in path.replace("\\", "/").lower():
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "[LOCKED-FACT FAN-OUT] case-profile.md was just edited. "
                "If a CASE FACT was locked (not metadata, scaffold, or a config value), "
                "run the fan-out THIS SESSION without being asked: "
                "(a) update " + M + "/matter.md, the source of truth, and carry the confidence tag "
                "([CONFIRMED] / [CLIENT-STATED] / [UNVERIFIED] / CONFIRM-BEFORE-CITING) with the fact; "
                "(b) if the fact is dated, fold it into " + M + "/chronology.md as a row tied to its proving "
                "exhibit, marked [PROOF GAP] if no document yet supports it; "
                "(c) if it contradicts anything on the record, log both sides with cites in "
                + M + "/contradiction-log.md; "
                "(d) if it bears on a witness's reliability, update " + M + "/credibility-list.md: show the dated "
                "instances, let the court name the pattern, never characterize it ourselves; "
                "(e) if no document yet proves it, add it to the retrieval queue in handoff.md rather than relying "
                "on it; "
                "(f) run the clawyer-superengine:verification-partner gate before the fact is relied on in any draft, and "
                "clawyer-superengine:council-a4-citation-authority before any authority it rests on is cited. "
                "A locked fact that has not fanned out by session end is a defect."
            ),
        }}))
except Exception:
    pass
sys.exit(0)
