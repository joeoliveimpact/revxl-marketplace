#!/usr/bin/env python3
"""Fetch a public Instagram post/carousel's slides + metadata. Single file, stdlib + instaloader.

Usage:
    python carousel_fetch.py <post-url> <work-dir> [--session /path/to/session-file]

stdout: ONE json object →
    ok:true  → {ok, shortcode, username, caption, taken_at, likes, comments,
                is_carousel, slides:[{index, kind, file}], message?}
    ok:false → {ok, error, message}   # invalid_url | login_required | rate_limited |
                                      # private | not_found | network | unknown

Derived from the caroustealer ig_fetch module (REVXL, 06.02.26), flattened to one file for plugin
bundling. Requires: Python 3.10+, `pip install instaloader`.

Conduct: public posts only; ~1 anonymous request per 30s (Instagram throttles hard — a
rate_limited result means WAIT, not retry). Downloaded media is personal research input only;
scraping may violate Instagram's ToS. Optional session file (throwaway account) via --session
for reliability; never use a main account.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_SHORTCODE_RE = re.compile(
    r"^https?://(?:www\.)?instagram\.com/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)/?(?:\?.*)?$",
    re.IGNORECASE,
)
_VIDEO_EXTS = {".mp4", ".mov"}
_PHOTO_EXTS = {".jpg", ".jpeg", ".webp", ".heic", ".png"}


def extract_shortcode(url: str) -> str | None:
    m = _SHORTCODE_RE.match(url.strip()) if isinstance(url, str) else None
    return m.group(1) if m else None


def _kind_for(p: Path) -> str | None:
    ext = p.suffix.lower()
    if ext in _VIDEO_EXTS:
        return "video"
    if ext in _PHOTO_EXTS:
        return "photo"
    return None


def _collect_slides(work_dir: Path) -> list[dict]:
    files = [p for p in work_dir.iterdir() if p.is_file() and _kind_for(p)]

    # natural sort so slide _2 precedes _10
    def key(p: Path):
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", p.name)]

    files.sort(key=key)
    return [{"index": i, "kind": _kind_for(p), "file": p.name} for i, p in enumerate(files)]


def _fail(error: str, message: str) -> dict:
    return {"ok": False, "error": error, "message": message}


def fetch(url: str, work_dir: Path, session_file: Path | None = None) -> dict:
    shortcode = extract_shortcode(url)
    if shortcode is None:
        return _fail("invalid_url", "Not an Instagram post/reel/tv URL.")

    try:
        import instaloader
        from instaloader import exceptions as ig_exc
    except ImportError:
        return _fail("unknown", "instaloader not installed — run: pip install instaloader")

    L = instaloader.Instaloader(
        download_video_thumbnails=False,
        save_metadata=False,
        compress_json=False,
        post_metadata_txt_pattern="",
    )

    note = None
    if session_file and Path(session_file).exists():
        try:
            L.load_session_from_file(Path(session_file).stem or None, filename=str(session_file))
        except Exception:
            note = "Session file could not be loaded; continuing anonymously."

    try:
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=work_dir)
        slides = _collect_slides(work_dir)

        def safe(getter):
            try:
                return getter()
            except Exception:
                return None

        taken = safe(lambda: post.date_utc)
        out = {
            "ok": True,
            "shortcode": shortcode,
            "username": safe(lambda: post.owner_username),
            "caption": safe(lambda: post.caption),
            "taken_at": taken.isoformat() if taken else None,
            "likes": safe(lambda: post.likes),
            "comments": safe(lambda: post.comments),
            "is_carousel": bool(safe(lambda: post.typename == "GraphSidecar")),
            "slides": slides,
        }
        if note:
            out["message"] = note
        return out

    except ig_exc.LoginRequiredException:
        return _fail("login_required", "Instagram is blocking anonymous access. Wait a few minutes or add --session.")
    except ig_exc.TooManyRequestsException:
        return _fail("rate_limited", "Rate limited. Wait a few minutes before the next pull.")
    except ig_exc.PrivateProfileNotFollowedException:
        return _fail("private", "This account is private. Hard stop — no workarounds.")
    except (ig_exc.ProfileNotExistsException, ig_exc.PostChangedException):
        return _fail("not_found", "Post not found — deleted or bad link.")
    except ig_exc.ConnectionException as exc:
        text = str(exc).lower()
        if any(k in text for k in ("login_required", "401", "please wait")):
            return _fail("login_required", "Instagram is blocking anonymous access. Wait a few minutes or add --session.")
        if any(k in text for k in ("429", "too many", "rate")):
            return _fail("rate_limited", "Rate limited. Wait a few minutes before the next pull.")
        if "not found" in text or "404" in text:
            return _fail("not_found", "Post not found — deleted or bad link.")
        return _fail("network", "Couldn't reach Instagram. Check the connection and retry.")
    except Exception:
        return _fail("unknown", "Unexpected error fetching this post.")


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    session = None
    if "--session" in argv:
        i = argv.index("--session")
        if i + 1 < len(argv):
            session = Path(argv[i + 1])
            args = [a for a in args if a != argv[i + 1]]
    if len(args) != 2:
        print(json.dumps(_fail("invalid_url", "Usage: carousel_fetch.py <post-url> <work-dir> [--session FILE]")))
        return 1
    url, work_dir = args[0], Path(args[1])
    work_dir.mkdir(parents=True, exist_ok=True)
    result = fetch(url, work_dir, session)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
