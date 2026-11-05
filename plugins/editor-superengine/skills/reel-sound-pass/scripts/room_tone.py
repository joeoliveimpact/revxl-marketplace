"""Room tone (F-15): any gap the sound pass inserts is filled with the recording's own quiet, never digital silence.

A voice track shorter than the picture, or the few milliseconds an alignment adds, gets real room tone: the
quietest stretch (at least 0.4 s) of the recording that is not digital silence, looped with short crossfades.
Never generated silence, never zero padding.

  room_tone.py check <file> [<file> ...]
      lists every digital-silence run (50 ms or more of samples under 1e-6) in each file's sound;
      exit 1 when any file has one, 0 when none does.
"""
import argparse, sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _media import SR, decode  # noqa: E402

SILENT = 1e-6        # a sample this small is digital silence
RUN_S = 0.05         # a run this long is a hole a listener hears as dead air
MIN_S = 0.4          # the shortest stretch of room tone worth looping
BLOCK_S = 0.01
XFADE_S = 0.02


class NoRoomTone(Exception):
    pass


def _frames(x):
    return x if x.ndim == 2 else x[:, None]


def find(x, sr=SR):
    """(start, end) samples of the quietest stretch of at least MIN_S in x that holds no digital silence."""
    x = _frames(x)
    b = int(sr * BLOCK_S)
    w = int(round(MIN_S / BLOCK_S))
    nb = len(x) // b
    if nb < w:
        raise NoRoomTone("the recording is shorter than %.1f s" % MIN_S)
    blocks = x[:nb * b].astype(np.float64).reshape(nb, b, -1)
    power = (blocks ** 2).mean(axis=(1, 2))
    dead = (np.abs(blocks).max(axis=(1, 2)) < SILENT).astype(np.int64)
    cp = np.concatenate([[0.0], np.cumsum(power)])
    cd = np.concatenate([[0], np.cumsum(dead)])
    mean = (cp[w:] - cp[:-w]) / w
    ok = (cd[w:] - cd[:-w]) == 0
    if not ok.any():
        raise NoRoomTone("the recording has no stretch of real room sound")
    i = int(np.argmin(np.where(ok, mean, np.inf)))
    return i * b, (i + w) * b


def fill(x, n, sr=SR):
    """n frames of room tone looped from x's quietest stretch, joined with short equal-power crossfades."""
    x = _frames(x)
    if n <= 0:
        return np.zeros((0, x.shape[1]), np.float32)
    s, e = find(x, sr)
    seg = x[s:e].astype(np.float64)
    L, f = len(seg), int(sr * XFADE_S)
    ramp = np.linspace(0, np.pi / 2, f)
    win = np.ones(L)
    win[:f], win[-f:] = np.sin(ramp), np.cos(ramp)
    out = np.zeros((n + L, x.shape[1]))
    pos, step = 0, L - f
    while pos < n:
        piece = seg * win[:, None]
        if pos == 0:
            piece[:f] = seg[:f]          # the first piece starts at full level, right after the recording
        out[pos:pos + L] += piece
        pos += step
    return out[:n].astype(np.float32)


def silent_runs(x, sr=SR):
    """[(start_s, end_s)] of every digital-silence run of RUN_S or longer."""
    quiet = np.abs(_frames(x)).max(axis=1) < SILENT
    edges = np.diff(np.concatenate([[0], quiet.astype(np.int8), [0]]))
    starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
    return [(round(a / sr, 3), round(z / sr, 3)) for a, z in zip(starts, ends) if z - a >= RUN_S * sr]


def main(argv=None):
    from win_encoding import ensure_utf8_output
    ensure_utf8_output()
    ap = argparse.ArgumentParser(description="Room tone check: find dead-silent holes in a voice track or mix.")
    ap.add_argument("cmd", choices=["check"])
    ap.add_argument("files", nargs="+")
    a = ap.parse_args(argv)
    bad = 0
    for f in a.files:
        runs = silent_runs(decode(f))
        if runs:
            bad += 1
            print("%s: %d dead-silent stretch(es), first at %.2f-%.2f s" % (Path(f).name, len(runs), *runs[0]))
        else:
            print("%s: no dead-silent stretches" % Path(f).name)
    return 1 if bad else 0


if __name__ == "__main__":
    from _media import guarded
    sys.exit(guarded(main))
