"""Shared cut timing defaults (milliseconds; stdlib only)."""

GUARD_MS = 70


def pause_default(value):
    """Use the style's valid pause, else the next Cut Board's 150 ms default."""
    return value if type(value) in (int, float) and 40 <= value <= 600 else 150
