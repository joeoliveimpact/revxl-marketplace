"""TRI-1 smoke: print one check mark and read one non-ASCII file name with stdout captured to a file.
usage: <venv python> smoke_utf8.py <empty-dir>
"""
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins/editor-superengine/skills/_shared"))
from win_encoding import ensure_utf8_output  # noqa: E402

NAME = "café ✓ 日本.txt"


def main():
    ensure_utf8_output()
    d = Path(sys.argv[1])
    (d / NAME).write_bytes("contents ok".encode("utf-8"))
    assert NAME in os.listdir(d), os.listdir(d)
    print(f"✓ read {NAME}: {(d / NAME).read_text(encoding='utf-8')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
