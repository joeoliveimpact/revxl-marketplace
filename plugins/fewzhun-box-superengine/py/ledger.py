"""Harvest ledger: which source items were already fed, and what happened to them.

Shape (<staging>/ledger.json):
  {"marks": {"<source>": [ts, id]},          newest item fed so far, per source (keyset order)
   "refs":  {"<ref>": {"state": S, "date": "YYYY-MM-DD", "draft": "<id>|"}},
   "approvals_read": N}                     lines of approvals.jsonl already applied
States: drafted | no-claim | blocked | dropped | approved | rejected.
Any ref in "refs" is never fed to the model again, whatever its state.
"""
import json

import boxlib

STATES = ("drafted", "no-claim", "blocked", "dropped", "approved", "rejected")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            led = json.load(f)
    except FileNotFoundError:
        led = {}
    led.setdefault("marks", {})
    led.setdefault("refs", {})
    led.setdefault("approvals_read", 0)
    return led


def save(path, led):
    """Atomic write, so a crash never leaves half a ledger."""
    boxlib.write_atomic(path, json.dumps(led, indent=1, sort_keys=True), mode=0o600)


def mark(led, ref, state, date, draft=""):
    assert state in STATES, state
    led["refs"][ref] = {"state": state, "date": date, "draft": draft}
