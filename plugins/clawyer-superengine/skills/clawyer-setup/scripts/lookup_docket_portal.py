#!/usr/bin/env python3
"""Look up the user's state/county docket portal from state-docket-portals.yaml.

Reads case-profile.md (if present in the workspace) for state + county, OR takes
them as args. Returns a JSON block the firm-setup walkthrough can consume.

Usage:
  python lookup_docket_portal.py --workspace <dir>
  python lookup_docket_portal.py --state Mississippi --county Harrison

If PyYAML is not installed, falls back to a minimal hand-parser for the small
subset of YAML this file uses. The bundled state-docket-portals.yaml sticks to
that subset deliberately.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# the YAML lives next to the pro-se-firm references, two levels up from firm-setup/scripts
DEFAULT_YAML = os.path.normpath(os.path.join(HERE, "..", "..", "pro-se-firm", "references", "state-docket-portals.yaml"))


def load_yaml(path):
    try:
        import yaml  # type: ignore
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        # minimal fallback for the small schema we use
        return _mini_yaml_load(path)


def _mini_yaml_load(path):
    """Tiny YAML reader. Handles only the structure used by state-docket-portals.yaml.
    Never invents data: if it cannot parse a value, returns None for that field."""
    data = {"states": []}
    current_state = None
    current_county = None
    in_signup = False
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # state block start
        m = re.match(r"^\s{2}-\s+state:\s*\"?(.+?)\"?\s*$", line)
        if m:
            current_state = {"state": m.group(1), "counties": []}
            data["states"].append(current_state)
            current_county = None
            in_signup = False
            continue
        # county block start
        m = re.match(r"^\s{6}-\s+name:\s*\"?(.+?)\"?\s*$", line)
        if m and current_state is not None:
            current_county = {"name": m.group(1), "signup_steps": []}
            current_state["counties"].append(current_county)
            in_signup = False
            continue
        # signup step item
        m = re.match(r"^\s{10}-\s+\"?(.+?)\"?\s*$", line)
        if m and current_county is not None and in_signup:
            current_county["signup_steps"].append(m.group(1))
            continue
        # key: value (state-level or county-level)
        m = re.match(r"^(\s+)(\w+):\s*(.*)$", line)
        if m:
            indent, key, val = len(m.group(1)), m.group(2), m.group(3).strip()
            val = val.strip().strip('"')
            if val == "null" or val == "":
                val_parsed = None
            else:
                try:
                    val_parsed = int(val)
                except ValueError:
                    val_parsed = val
            target = None
            if indent == 4 and current_state is not None:
                target = current_state
            elif indent == 8 and current_county is not None:
                target = current_county
            if target is not None:
                if key == "signup_steps":
                    in_signup = True
                else:
                    in_signup = False
                    target[key] = val_parsed
    return data


def read_case_profile(workspace):
    """Best-effort: parse state and county out of case-profile.md."""
    path = os.path.join(workspace, "case-profile.md")
    if not os.path.exists(path):
        return None, None
    text = open(path, "r", encoding="utf-8", errors="ignore").read().lower()
    state = None
    county = None
    m = re.search(r"state[:\s\*\-]+([a-z ]{3,40})", text)
    if m:
        state = m.group(1).strip().title().split("\n")[0]
    m = re.search(r"county[:\s\*\-]+([a-z ]{3,40})", text)
    if m:
        county = m.group(1).strip().title().split("\n")[0]
    return state, county


def lookup(data, state, county):
    if not data or "states" not in data:
        return {"branch": "no-data", "state": state, "county": county}
    state_norm = (state or "").strip().lower()
    county_norm = (county or "").strip().lower()
    state_entry = next((s for s in data["states"] if s.get("state", "").lower() == state_norm), None)
    if not state_entry:
        return {
            "branch": "state-not-found",
            "state": state,
            "county": county,
            "prompt": "I do not have your state's court-records portal on file. Paste your county's docket URL or say you do not have one.",
        }
    counties = state_entry.get("counties") or []
    county_entry = next((c for c in counties if c.get("name", "").lower() == county_norm), None) if county_norm else None
    if county_entry:
        return {
            "branch": "both-found",
            "state": state_entry.get("state"),
            "system_name": state_entry.get("system_name"),
            "system_url": state_entry.get("system_url"),
            "county": county_entry.get("name"),
            "portal_url": county_entry.get("portal_url"),
            "cost_usd_year": county_entry.get("cost_usd_year"),
            "cost_note": county_entry.get("cost_note"),
            "signup_steps": county_entry.get("signup_steps") or [],
        }
    return {
        "branch": "state-found-county-not-found",
        "state": state_entry.get("state"),
        "system_name": state_entry.get("system_name"),
        "system_url": state_entry.get("system_url"),
        "county": county,
        "prompt": "I have your state's portal but not your specific county. Paste your county clerk's docket URL.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=None)
    ap.add_argument("--state", default=None)
    ap.add_argument("--county", default=None)
    ap.add_argument("--yaml", default=DEFAULT_YAML)
    args = ap.parse_args()

    state = args.state
    county = args.county
    if args.workspace and (not state or not county):
        cps, cpc = read_case_profile(args.workspace)
        state = state or cps
        county = county or cpc

    if not os.path.exists(args.yaml):
        print(json.dumps({"error": f"YAML not found at {args.yaml}"}))
        return 1
    data = load_yaml(args.yaml)
    result = lookup(data, state, county)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
