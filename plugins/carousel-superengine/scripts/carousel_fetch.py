#!/usr/bin/env python3
"""Fetch every slide of an Instagram post/carousel via the authenticated mobile API.

Plain English: Instagram killed anonymous fetching in mid-2026 (403 login_required),
and instaloader's web path is dead even with a login. The ONE path that still returns
every slide is Instagram's own mobile app API — hit while logged in. This script reads
the Instagram cookies the client exported once with the Cookie-Editor browser extension
(a plain JSON array, saved during setup), asks `i.instagram.com` for the post, and
downloads each slide. No password lives here; the cookie file is the only secret, and it
stays on the client's machine.

Usage:
    python carousel_fetch.py <post-url> <work-dir> --session /path/to/ig_session.json

    --session is REQUIRED — it's the Cookie-Editor export (JSON array of the client's
    instagram.com cookies, incl. sessionid). Anonymous fetch no longer works. See
    references/ig-cookie-setup.md for the 2-minute capture walk-through.

stdout: ONE json object (contract unchanged from v0.1.0 so teardown consumes it as-is) →
    ok:true  → {ok, shortcode, username, caption, taken_at, likes, comments,
                is_carousel, slides:[{index, kind, file}], message?}
    ok:false → {ok, error, message}   # invalid_url | login_required | rate_limited |
                                       # private | not_found | network | unknown

Mechanism (proven live 2026-07-06, 8 slides): shortcode -> media pk (base64 decode) ->
GET https://i.instagram.com/api/v1/media/{pk}/info/ with header X-IG-App-ID + the session
cookies -> items[0].carousel_media[].image_versions2.candidates[0].url (photo) /
video_versions[0].url (video). Single media = [items[0]].

Requires: Python 3.10+, stdlib only — no pip install at all (capture is a cookie paste,
no browser automation). Conduct: per-client OWN cookies, tiny per-account volume, never a
shared account. Public + accessible posts only; downloaded media is personal research
input, not content to repost (scraping may violate Instagram's ToS — the user owns that
call). A login_required result means the cookies expired -> paste a fresh Cookie-Editor
export, don't retry-loop.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_SHORTCODE_RE = re.compile(
    r"^https?://(?:www\.)?instagram\.com/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)/?(?:\?.*)?$",
    re.IGNORECASE,
)
# Instagram media-id (pk) shortcode alphabet — base64 URL-safe order.
_B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
_APP_ID = "936619743392459"          # public Instagram mobile web app id
_UA = "Instagram 219.0.0.12.117 Android"


def extract_shortcode(url: str) -> str | None:
    m = _SHORTCODE_RE.match(url.strip()) if isinstance(url, str) else None
    return m.group(1) if m else None


def shortcode_to_pk(shortcode: str) -> int:
    pk = 0
    for ch in shortcode:
        pk = pk * 64 + _B64.index(ch)
    return pk


def _fail(error: str, message: str) -> dict:
    return {"ok": False, "error": error, "message": message}


def _cookie_header(session_file: Path) -> str | None:
    """Build a Cookie header from a Cookie-Editor export (a raw cookie array) or a
    {cookies:[...]} object. Returns None if no instagram sessionid cookie is present."""
    try:
        data = json.loads(Path(session_file).read_text(encoding="utf-8"))
    except Exception:
        return None
    cookies = data.get("cookies", data) if isinstance(data, dict) else data
    pairs, has_session = [], False
    for c in cookies or []:
        name, value = c.get("name"), c.get("value")
        dom = (c.get("domain") or "")
        if not name or value is None:
            continue
        if "instagram.com" not in dom and dom != "":
            continue
        pairs.append(f"{name}={value}")
        if name == "sessionid" and value:
            has_session = True
    return "; ".join(pairs) if has_session else None


def _api_get(pk: int, cookie: str) -> tuple[int, dict | None]:
    req = urllib.request.Request(
        f"https://i.instagram.com/api/v1/media/{pk}/info/",
        headers={
            "User-Agent": _UA,
            "X-IG-App-ID": _APP_ID,
            "X-IG-Capabilities": "3brTvw==",
            "Accept": "*/*",
            "Accept-Language": "en-US",
            "Cookie": cookie,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return -1, None


def _download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            f.write(r.read())
        return dest.stat().st_size > 0
    except Exception:
        return False


def _node_media(node: dict) -> tuple[str, str, str] | None:
    """(url, kind, ext) for a media node, video preferred when present."""
    vids = node.get("video_versions") or []
    if vids and vids[0].get("url"):
        return vids[0]["url"], "video", ".mp4"
    cands = (node.get("image_versions2") or {}).get("candidates") or []
    if cands and cands[0].get("url"):
        return cands[0]["url"], "photo", ".jpg"
    return None


def fetch(url: str, work_dir: Path, session_file: Path | None) -> dict:
    shortcode = extract_shortcode(url)
    if shortcode is None:
        return _fail("invalid_url", "Not an Instagram post/reel/tv URL.")
    if not session_file or not Path(session_file).exists():
        return _fail("login_required",
                     "No Instagram cookies. Paste a fresh Cookie-Editor export (see ig-cookie-setup.md).")
    cookie = _cookie_header(session_file)
    if not cookie:
        return _fail("login_required",
                     "Cookies have no Instagram sessionid (expired or wrong export). Paste a fresh Cookie-Editor export.")

    try:
        pk = shortcode_to_pk(shortcode)
    except ValueError:
        return _fail("invalid_url", "Shortcode contains characters outside the Instagram alphabet.")

    status, payload = _api_get(pk, cookie)
    if status in (401, 403):
        return _fail("login_required", "Instagram rejected the cookies (expired). Paste a fresh Cookie-Editor export.")
    if status == 429:
        return _fail("rate_limited", "Rate limited. Wait a few minutes before the next pull.")
    if status == 404:
        return _fail("not_found", "Post not found — deleted, private, or bad link.")
    if payload is None:
        return _fail("network", "Couldn't reach Instagram or parse the response. Check the connection and retry.")

    items = payload.get("items") or []
    if not items:
        # IG returns 200 with no items for gated/removed media
        return _fail("not_found", "Instagram returned no media for this link (removed, private, or region-locked).")
    item = items[0]

    is_carousel = "carousel_media" in item
    nodes = item.get("carousel_media") or [item]
    slides = []
    for i, node in enumerate(nodes):
        media = _node_media(node)
        if not media:
            continue
        src, kind, ext = media
        fname = f"slide_{i:02d}{ext}"
        if _download(src, work_dir / fname):
            slides.append({"index": len(slides), "kind": kind, "file": fname})

    if not slides:
        return _fail("network", "Reached Instagram but no slide media could be downloaded (CDN links may have expired — retry).")

    def safe(getter):
        try:
            return getter()
        except Exception:
            return None

    taken = safe(lambda: int(item.get("taken_at")))
    cap = item.get("caption") or {}
    out = {
        "ok": True,
        "shortcode": shortcode,
        "username": safe(lambda: item["user"]["username"]),
        "caption": (cap.get("text") if isinstance(cap, dict) else None),
        "taken_at": datetime.fromtimestamp(taken, tz=timezone.utc).isoformat() if taken else None,
        "likes": safe(lambda: item.get("like_count")),
        "comments": safe(lambda: item.get("comment_count")),
        "is_carousel": bool(is_carousel),
        "slides": slides,
    }
    return out


def main(argv: list[str]) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows stdout is cp1252; captions carry emoji/unicode
    except Exception:
        pass
    args = [a for a in argv[1:] if not a.startswith("--")]
    session = None
    if "--session" in argv:
        i = argv.index("--session")
        if i + 1 < len(argv):
            session = Path(argv[i + 1])
            args = [a for a in args if a != argv[i + 1]]
    if len(args) != 2:
        print(json.dumps(_fail("invalid_url",
                               "Usage: carousel_fetch.py <post-url> <work-dir> --session FILE")))
        return 1
    url, work_dir = args[0], Path(args[1])
    work_dir.mkdir(parents=True, exist_ok=True)
    result = fetch(url, work_dir, session)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
