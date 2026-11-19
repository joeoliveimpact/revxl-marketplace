#!/usr/bin/env python3
"""UserPromptSubmit hook: remind the firm to classify and route this turn. Silent outside a Clawyer workspace.

Kept short on purpose: a long injection gets deprioritised. Text from pro-se-firm v1.7.0's firm-dispatch.sh
(c) 2026 Mic H., MIT; moved to Python so it needs no second shell.
"""
import os
import sys
from pathlib import Path

try:
    ws = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    if (ws / "firm.config.json").exists():
        try:
            import json
            family = json.loads((ws / "firm.config.json").read_text(encoding="utf-8")).get("case_type") == "family-law"
        except Exception:
            family = False
        council = ("3. If it is an adverse or court document, run the 15-member Review Council (COUNCIL.md; agents are "
                   if family else
                   "3. This is not a family case: skip family-law roles and rows. Run the 15-member Review Council only "
                   "on a court order, a filed paper, something to sign, or our own filing (COUNCIL.md; agents are ")
        print(
            "[CLAWYER DISPATCH - run before answering]\n"
            "1. Classify this turn's input per ROUTING.md: whose is it (OURS / OTHER SIDE'S / COURT'S) and what type.\n"
            "2. Fire the roles ROUTING.md maps to that type, without asking the person to name them.\n"
            + council +
            "named clawyer-superengine:council-a1-ruling-match through clawyer-superengine:council-a15-adversarial-red-team).\n"
            "4. Run the Verification Partner (clawyer-superengine:verification-partner) on anything to be relied on or sent out; "
            "it is a blocking gate.\n"
            "5. If classification is unclear or a gate cannot be satisfied, ask one targeted question. Do not guess.\n"
            "6. Nothing gets filed or sent without the person's explicit approval."
        )
except Exception:
    pass
sys.exit(0)
