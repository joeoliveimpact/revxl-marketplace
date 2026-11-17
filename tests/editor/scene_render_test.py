#!/usr/bin/env python3
"""Catalog and reel render proof; implementation ships with reel-canvas-build."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] /
                       "plugins/editor-superengine/skills/reel-canvas-build/scripts"))
import scene_render

if __name__ == "__main__":
    sys.exit(scene_render.main())
else:
    # Preserve the test module's public helpers and patch points for the MB2 proofs.
    sys.modules[__name__] = scene_render
