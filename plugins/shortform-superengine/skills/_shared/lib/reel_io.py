"""Shared I/O + parsing helpers for the Content Superengine core<->format seam.

NEW helpers only. analyze.py keeps its OWN inline fix()/med() — these are intentionally
NOT extracted from it, to protect the byte-identical EWH regression gate (see _shared/tests).
Consumed by reel-scripter/scripting_brief.py and future format engines that read the
analysis-data.json contract. No format engine imports analyze.py directly.
"""
import json
import os
import re
import statistics as st


def J(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fix(t):
    """Best-effort mojibake repair (mirrors analyze.py's inline fix)."""
    if not t:
        return ""
    try:
        import ftfy
        return ftfy.fix_text(t)
    except Exception:
        try:
            return t.encode("latin-1", "ignore").decode("utf-8", "ignore")
        except Exception:
            return t


def med(xs):
    return st.median(xs) if xs else 0


def load_config(root):
    """Load the analysis config superset (analysis-config.json) or legacy tiers.json.

    Tries the superset filename first so a project can carry the richer config; falls
    back to the legacy name so EWH (tiers.json only) stays on the identical code path.
    """
    for name in ("analysis-config.json", "tiers.json"):
        p = os.path.join(root, name)
        if os.path.exists(p):
            return J(p)
    raise FileNotFoundError(f"no analysis-config.json or tiers.json in {root}")


def load_analysis_json(root):
    """Load the core->format interface emitted by competitor-cross-reference/analyze.py."""
    return J(os.path.join(root, "analysis-data.json"))


def parse_transcript_header(text):
    """Parse a harvested transcript file into its header fields + spoken body.

    Expected shape (written by creator-strategy-harvest / the gather step):
        # <group> | <rank> | <N> views | <L>L <C>C
        # reel: https://www.instagram.com/reel/<shortcode>/
        # audio_src: ... | backend: ...
        # caption_hook: <first caption line>

        ## SPOKEN TRANSCRIPT
        <body...>

    Returns a dict; any missing field is None (views defaults to 0). Robust to
    files that omit lines — only the '## ' divider is required to split body.
    """
    out = {
        "group": None, "rank": None, "views": 0, "likes": None, "comments": None,
        "url": None, "shortcode": None, "caption_hook": None, "transcript": "",
    }
    lines = text.split("\n")
    body_start = len(lines)
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("## "):
            body_start = i + 1
            break
        if not s.startswith("#"):
            continue
        h = s.lstrip("#").strip()
        hl = h.lower()
        if hl.startswith("reel:"):
            url = h.split(":", 1)[1].strip()
            out["url"] = url
            m = re.search(r"/reel/([^/]+)/", url)
            if m:
                out["shortcode"] = m.group(1)
        elif hl.startswith("caption_hook:"):
            out["caption_hook"] = h.split(":", 1)[1].strip()
        elif hl.startswith("audio_src"):
            continue
        elif "|" in h:  # first metadata line
            parts = [p.strip() for p in h.split("|")]
            if parts:
                out["group"] = parts[0]
            for p in parts[1:]:
                if p.startswith(("best", "worst", "#")):
                    out["rank"] = p
                mv = re.search(r"([\d,]+)\s*views", p)
                if mv:
                    out["views"] = int(mv.group(1).replace(",", ""))
                mlc = re.search(r"([\d,]+)\s*L\s+([\d,]+)\s*C", p)
                if mlc:
                    out["likes"] = int(mlc.group(1).replace(",", ""))
                    out["comments"] = int(mlc.group(2).replace(",", ""))
    out["transcript"] = "\n".join(lines[body_start:]).strip()
    return out
