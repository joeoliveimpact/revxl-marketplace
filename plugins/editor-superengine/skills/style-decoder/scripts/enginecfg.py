#!/usr/bin/env python3
"""style-decoder config resolution.

ONE function: cfg() — deep-merged config, first hit wins:
    1. $EDITOR_SUPERENGINE_CONFIG (explicit path; hard error if set but missing)
    2. .claude/editor-superengine.json   (optional override file in the workspace)
    3. DEFAULTS below

Paths are relative to the cwd (the client's workspace). Everything the decoder
writes lands under data_dir, except paths the user passes on the command line.
Nothing here reads or adds keys to editor/editor.config.json.

Scripts read config for DEFAULTS only; explicit CLI flags always win.
"""
from __future__ import annotations

import copy
import json
import os

DEFAULTS = {
    "data_dir": os.path.join("editor", "style-decoder"),
    "style": {                       # style-decoder — decode reels into style systems
        "library_dir": "",           # "" = <data_dir>/styles
        "scene_threshold": 0.30,     # ffmpeg scene-detect gate (cuts.json = candidates only)
        "frame_budget": 120,         # max frames Claude reads in the decode phase
        "merge_tolerance": 0.30,     # numeric param divergence before a merge conflict
    },
    "designsystem": {                # the swappable LOOK layer
        "registry_dir": "",          # "" = <data_dir>/designsystems; fonts at <registry_dir>/_fonts
    },
}

CONFIG_PATH = os.path.join(".claude", "editor-superengine.json")


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def cfg() -> dict:
    p = os.environ.get("EDITOR_SUPERENGINE_CONFIG")
    if p:
        if not os.path.exists(p):
            raise SystemExit(f"EDITOR_SUPERENGINE_CONFIG set but file missing: {p}")
    else:
        p = CONFIG_PATH if os.path.exists(CONFIG_PATH) else None
    if not p:
        return copy.deepcopy(DEFAULTS)
    with open(p, encoding="utf-8") as f:
        try:
            user = json.load(f)
        except json.JSONDecodeError as e:
            raise SystemExit(f"config parse error in {p}: {e}")
    return _merge(DEFAULTS, user)


if __name__ == "__main__":
    print(json.dumps(cfg(), indent=2))
