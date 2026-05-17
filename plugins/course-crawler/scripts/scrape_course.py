"""
scrape_course.py ... one-command course scraper producing a CLEAN per-course tree.

What this does (plain English):
  Point it at a course folder that already has metadata/lesson_urls.json (from
  discovery, or discover_skool.py for Skool). For every lesson it:
    1. Refreshes cookies from the running browser session (any backend).
    2. Gets the lesson HTML ... a fresh httpx GET, OR the pre-rendered HTML
       captured during SPA discovery (Skool) when the manifest points at one.
    3. Writes clean Markdown            -> written/<NN-module>/<lesson>.md
    4. Writes categorized reference links -> links/<NN-module>/<lesson>.md
    5. Downloads attachments             -> assets/<NN-module>/<lesson>/
    6. Records video sources for later   -> metadata/video_sources.json
  Raw HTML is NOT saved unless --keep-html is given (it was the old "mess").

What it expects:
  - metadata/lesson_urls.json (flat list). Each entry: module_order,
    module_title, category_id, post_id, title, url, and optionally
    rendered_html (relative path), links[], attachments[] (pre-harvested).
  - A live browser session for cookie refresh, OR a manually-pasted
    metadata/cookies.txt (then pass --no-refresh).

Clean output tree:
  written/<NN-module>/<lesson>.md       clean Markdown
  links/<NN-module>/<lesson>.md         categorized reference links
  assets/<NN-module>/<lesson>/          downloaded attachments
  metadata/cookies.txt                  refreshed/pasted cookies
  metadata/video_sources.json           video URLs found
  metadata/scrape_report.json           what worked / what failed
  metadata/raw/<NN-module>/<lesson>.html  ONLY if --keep-html

How to run:
  ~/.iss/venv/bin/python ${CLAUDE_SKILL_DIR}/../scripts/scrape_course.py ./scraped/<slug>
  ... --no-refresh         use an existing/pasted cookies.txt, don't touch the browser
  ... --keep-html          also save raw HTML under metadata/raw/
"""

import argparse
import json
import re
import subprocess
import sys
import time
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import trafilatura


# --- helpers --------------------------------------------------------------

# Windows consoles default to cp1252; force UTF-8 so emoji/arrows never crash
# a print(). No-op where already UTF-8 or not reconfigurable.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def slugify(text: str, max_len: int = 80) -> str:
    """Filesystem-safe slug. Lowercase, hyphenated, alphanumeric + hyphens."""
    s = re.sub(r"[^\w\-]+", "-", (text or "").lower()).strip("-")
    return s[:max_len] or "untitled"


def load_cookies(path: Path) -> httpx.Cookies:
    """Load a Netscape cookies.txt into an httpx Cookies object."""
    jar = MozillaCookieJar(str(path))
    jar.load(ignore_discard=True, ignore_expires=True)
    cookies = httpx.Cookies()
    for c in jar:
        cookies.set(c.name, c.value, domain=c.domain, path=c.path)
    return cookies


def find_video_sources(html: str) -> list[dict]:
    """Find video source patterns in raw HTML. We don't download here, just
    record what's present so process_videos.py can take over.

    Detects: Wistia, Vimeo (incl. Pro/OTT), YouTube, Vidalytics, VdoCipher
    (DRM-flagged), JW Player, Bunny.net Stream, Mux, Kaltura, Loom, HLS
    (.m3u8), DASH (.mpd), and direct HTML5 <video>/<source> tags
    (mp4/webm/mov/m4v). VdoCipher is marked drm_protected so downstream
    code skips with a clean message instead of failing on a broken download."""
    sources: list[dict] = []
    seen: set[str] = set()

    def add(src: dict) -> None:
        key = src.get("url") or json.dumps(src, sort_keys=True)
        if key not in seen:
            seen.add(key)
            sources.append(src)

    # Wistia (Kajabi default). Two real-world forms: the iframe/medias/async
    # URL (fast.wistia.net/embed/iframe/<id>, *.wistia.com/medias/<id>) and the
    # wistia_async_<id> div-class form. IDs are 8-12 alphanumeric chars.
    for m in re.finditer(r"wistia\.(?:net|com)/(?:embed/)?(?:iframe|medias|async)/([a-z0-9]{8,12})", html, re.I):
        wid = m.group(1)
        add({"type": "wistia", "wistia_id": wid,
             "url": f"https://fast.wistia.net/embed/iframe/{wid}"})
    for m in re.finditer(r"wistia_async_([a-z0-9]{8,12})", html, re.I):
        wid = m.group(1)
        add({"type": "wistia", "wistia_id": wid,
             "url": f"https://fast.wistia.net/embed/iframe/{wid}"})

    # Vimeo (public + Pro/OTT share the same embed pattern).
    for m in re.finditer(r"player\.vimeo\.com/video/(\d+)", html):
        vid = m.group(1)
        add({"type": "vimeo", "vimeo_id": vid,
             "url": f"https://player.vimeo.com/video/{vid}"})

    # YouTube embeds (handles youtube-nocookie too).
    for m in re.finditer(r"youtube(?:-nocookie)?\.com/embed/([A-Za-z0-9_-]{11})", html):
        yid = m.group(1)
        add({"type": "youtube", "youtube_id": yid,
             "url": f"https://www.youtube.com/watch?v={yid}"})

    # Vidalytics ... very common on paid info-marketer courses.
    for m in re.finditer(r"vidalytics\.com/embeds/([A-Za-z0-9_-]+)", html, re.I):
        add({"type": "vidalytics", "id": m.group(1), "url": m.group(0)})

    # VdoCipher ... DRM-locked, yt-dlp cannot retrieve. Flag for clean skip.
    for m in re.finditer(r"player\.vdocipher\.com/v2/\?otp=[^&\"'\s<>]+(?:&playbackInfo=[^&\"'\s<>]+)?", html, re.I):
        add({"type": "vdocipher", "url": m.group(0),
             "drm_protected": True,
             "note": "DRM-locked (VdoCipher). Manual capture only."})
    for m in re.finditer(r"vdocipher\.com/(?:api/meta|otp)/([A-Za-z0-9]+)", html, re.I):
        add({"type": "vdocipher", "id": m.group(1), "url": m.group(0),
             "drm_protected": True,
             "note": "DRM-locked (VdoCipher). Manual capture only."})

    # JW Player (used by many news + LMS sites).
    for m in re.finditer(r"(?:content|cdn)\.jwplat(?:form|er)\.com/(?:videos|players|manifests)/([A-Za-z0-9]+)", html, re.I):
        add({"type": "jwplayer", "id": m.group(1), "url": m.group(0)})

    # Bunny.net Stream.
    for m in re.finditer(r"iframe\.mediadelivery\.net/(?:embed|play)/(\d+)/([A-Za-z0-9-]+)", html, re.I):
        lib, vid = m.group(1), m.group(2)
        add({"type": "bunny_stream", "library_id": lib, "video_id": vid,
             "url": f"https://iframe.mediadelivery.net/embed/{lib}/{vid}"})

    # Mux (modern SaaS).
    for m in re.finditer(r"stream\.mux\.com/([A-Za-z0-9]+)", html, re.I):
        pid = m.group(1)
        add({"type": "mux", "playback_id": pid,
             "url": f"https://stream.mux.com/{pid}.m3u8"})

    # Kaltura (academic / EdTech).
    for m in re.finditer(r"cdnapisec\.kaltura\.com/p/(\d+)/sp/\d+/embedIframeJs/uiconf_id/\d+/partner_id/\d+\?[^\"']*entry_id=([A-Za-z0-9_]+)", html, re.I):
        add({"type": "kaltura", "partner_id": m.group(1), "entry_id": m.group(2),
             "url": m.group(0)})

    # Loom (often embedded in informal courses).
    for m in re.finditer(r"loom\.com/(?:embed|share)/([A-Za-z0-9]+)", html, re.I):
        lid = m.group(1)
        add({"type": "loom", "id": lid, "url": f"https://www.loom.com/share/{lid}"})

    # HLS (.m3u8) and DASH (.mpd) ... generic catch for custom players.
    for m in re.finditer(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', html, re.I):
        add({"type": "hls", "url": m.group(1)})
    for m in re.finditer(r'["\'](https?://[^"\']+\.mpd[^"\']*)["\']', html, re.I):
        add({"type": "dash", "url": m.group(1)})

    # Direct HTML5 <source>/<video> tags ... broaden beyond mp4.
    for m in re.finditer(r'<(?:source|video)[^>]+src=["\']([^"\']+\.(mp4|webm|mov|m4v))[^"\']*["\']', html, re.I):
        add({"type": "direct", "format": m.group(2).lower(), "url": m.group(1)})

    return sources


# Reference-link categories. Order matters (first match wins).
_LINK_RULES = [
    ("github", re.compile(r"https?://(?:www\.)?github\.com/", re.I)),
    ("google_docs", re.compile(r"https?://(?:docs|drive|sheets|slides|forms)\.google\.com/", re.I)),
    ("notion", re.compile(r"https?://(?:www\.)?notion\.(?:so|site)/", re.I)),
    ("loom", re.compile(r"https?://(?:www\.)?loom\.com/", re.I)),
    ("airtable", re.compile(r"https?://(?:www\.)?airtable\.com/", re.I)),
    ("figma", re.compile(r"https?://(?:www\.)?figma\.com/", re.I)),
]

# Files we treat as downloadable course materials.
_ASSET_EXT = ("pdf", "zip", "docx", "xlsx", "pptx", "csv", "key",
              "doc", "xls", "ppt", "pages", "numbers", "epub")
_ASSET_RE = re.compile(
    r'href=["\']([^"\']+\.(?:' + "|".join(_ASSET_EXT) + r')(?:\?[^"\']*)?)["\']',
    re.I,
)
# Only real anchor links, not <link rel=stylesheet>/<script src> chrome.
_HREF_RE = re.compile(r'<a\b[^>]*?\bhref=["\'](https?://[^"\']+)["\']', re.I)
# Page-infrastructure hosts/extensions that are never "reference material".
_INFRA_HOST = re.compile(
    r"(?:fonts\.googleapis\.com|fonts\.gstatic\.com|assets\.skool\.com|"
    r"\.cloudfront\.net|googletagmanager\.com|google-analytics\.com|"
    r"facebook\.(?:com|net)/tr|cdn\.jsdelivr\.net|unpkg\.com)", re.I)
_INFRA_EXT = re.compile(r"\.(?:css|ico|woff2?|ttf|svg|png|jpe?g|gif|webp|js)(?:\?|$)", re.I)


def extract_reference_links(html: str, base_url: str, page_host: str) -> dict:
    """Categorize off-page reference links (GitHub/Google/Notion/etc.).
    Same-host links are skipped (they're course nav, not references)."""
    out: dict[str, list[str]] = {}
    for m in _HREF_RE.finditer(html or ""):
        url = m.group(1)
        host = urlparse(url).hostname or ""
        if page_host and page_host in host:
            continue  # internal nav, not a reference
        if _INFRA_HOST.search(url) or _INFRA_EXT.search(url):
            continue  # fonts/analytics/static assets, not reference material
        cat = "other"
        for name, rx in _LINK_RULES:
            if rx.match(url):
                cat = name
                break
        out.setdefault(cat, [])
        if url not in out[cat]:
            out[cat].append(url)
    return out


def merge_links(extracted: dict, pre: list[str]) -> dict:
    """Fold pre-harvested links (from discover_skool) into the categorized map."""
    for url in pre or []:
        cat = "other"
        for name, rx in _LINK_RULES:
            if rx.match(url):
                cat = name
                break
        extracted.setdefault(cat, [])
        if url not in extracted[cat]:
            extracted[cat].append(url)
    return extracted


def links_section(links: dict) -> tuple[str, int]:
    """Return a '## Reference links' Markdown block to append to the lesson
    body (empty string if none), plus the link count."""
    total = sum(len(v) for v in links.values())
    if not total:
        return "", 0
    lines = ["", "## Reference links", ""]
    for cat in sorted(links):
        urls = links[cat]
        if not urls:
            continue
        lines.append(f"### {cat}")
        lines += [f"- {u}" for u in urls]
        lines.append("")
    return "\n".join(lines), total


def find_attachments(html: str, base_url: str) -> list[str]:
    urls = []
    for m in _ASSET_RE.finditer(html or ""):
        u = urljoin(base_url, m.group(1))
        if u not in urls:
            urls.append(u)
    return urls


def download_attachments(client: httpx.Client, urls: list[str], dest: Path) -> list[dict]:
    results = []
    if not urls:
        return results
    dest.mkdir(parents=True, exist_ok=True)
    for u in urls:
        name = Path(urlparse(u).path).name or "file"
        target = dest / name
        try:
            r = client.get(u, timeout=60.0)
            if r.status_code == 200 and r.content:
                target.write_bytes(r.content)
                results.append({"url": u, "file": str(target),
                                "bytes": len(r.content), "status": "ok"})
            else:
                results.append({"url": u, "status": f"http_{r.status_code}"})
        except Exception as e:
            results.append({"url": u, "status": "error", "error": str(e)})
    return results


def refresh_cookies(course_dir: Path, domain_filter: str | None) -> Path:
    """Call dump_cookies.py to refresh the cookie file from the live browser
    session (any backend exposing a CDP port)."""
    cookie_file = course_dir / "metadata" / "cookies.txt"
    cookie_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(Path(__file__).resolve().parent / "dump_cookies.py"), str(cookie_file)]
    if domain_filter:
        cmd += ["--domain", domain_filter]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise RuntimeError("Cookie refresh failed. Is a browser session open? "
                           "If you pasted cookies manually, re-run with --no-refresh.")
    print(result.stdout.strip())
    return cookie_file


def lesson_slug_for(lesson: dict) -> str:
    """Slug from the MANIFEST title (not trafilatura's) so scrape_course and
    process_videos always compute the identical folder/file name."""
    return slugify(lesson.get("title") or lesson.get("post_id") or "untitled", 60)


def lesson_dir_for(course_dir: Path, lesson: dict) -> Path:
    """Canonical lesson-centric path: <course>/NN-<module>/NN-<lesson>/.
    Shared by scrape_course and process_videos -> one folder per lesson."""
    mo = lesson.get("module_order", 1)
    lo = lesson.get("lesson_order", 1)
    m = f"{mo:02d}-{slugify(lesson.get('module_title', 'lessons'), 60)}"
    return course_dir / m / f"{lo:02d}-{lesson_slug_for(lesson)}"


def pull_one(client: httpx.Client, lesson: dict, course_dir: Path,
             keep_html: bool) -> dict:
    """Fetch/parse one lesson, write everything for it into ONE lesson folder."""
    url = lesson.get("url", "")
    ldir = lesson_dir_for(course_dir, lesson)
    lesson_slug = lesson_slug_for(lesson)

    # SPA discovery (Skool) gives us pre-rendered HTML on disk; prefer it,
    # because a fresh GET of a SPA URL just returns the empty shell.
    rendered_rel = lesson.get("rendered_html")
    if rendered_rel:
        rendered_path = course_dir / rendered_rel
        try:
            html = rendered_path.read_text(encoding="utf-8")
            fetch_status = "rendered"
        except Exception as e:
            return {"url": url, "status": "rendered_missing", "error": str(e)}
    else:
        try:
            resp = client.get(url, timeout=30.0)
        except Exception as e:
            return {"url": url, "status": "fetch_error", "error": str(e)}
        if resp.status_code != 200:
            return {"url": url, "status": f"http_{resp.status_code}"}
        html = resp.text
        fetch_status = "fetched"

    # with_metadata=False: we add our own clean "# {title}" H1; trafilatura's
    # YAML frontmatter would duplicate the title.
    markdown = trafilatura.extract(
        html, output_format="markdown",
        include_links=True, include_images=True, include_tables=True,
        with_metadata=False,
    ) or ""
    title = lesson.get("title") or lesson.get("post_id") or "untitled"
    page_host = urlparse(url).hostname or ""

    # Reference links: extract from page + merge pre-harvested, append as a
    # section to the SAME lesson .md (one file: text + links).
    links = merge_links(extract_reference_links(html, url, page_host),
                        lesson.get("links", []))
    section, n_links = links_section(links)

    ldir.mkdir(parents=True, exist_ok=True)
    body = f"# {title}\n\n{markdown}".rstrip() + ("\n" + section if section else "\n")
    (ldir / f"{lesson_slug}.md").write_text(body, encoding="utf-8")

    # downloads/ ... downloaded materials (page + pre-harvested), in-folder.
    asset_urls = find_attachments(html, url or "")
    for a in lesson.get("attachments", []):
        if a not in asset_urls:
            asset_urls.append(a)
    asset_results = download_attachments(client, asset_urls, ldir / "downloads")

    videos = find_video_sources(html)

    # Raw HTML only on explicit opt-in, kept in machine-only metadata/raw/.
    if keep_html:
        raw = course_dir / "metadata" / "raw" / ldir.relative_to(course_dir)
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.with_suffix(".html").write_text(html, encoding="utf-8")

    return {
        "url": url, "status": "ok", "title": title,
        "module": lesson.get("module_title"), "lesson_dir": str(ldir),
        "fetch": fetch_status,
        "markdown_chars": len(markdown),
        "links_found": n_links,
        "attachments": asset_results,
        "videos": videos,
    }


# --- main ----------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape a course into a clean per-course tree.")
    parser.add_argument("course_dir", help="Path to the course folder (e.g. ./scraped/<slug>)")
    parser.add_argument("--domain", default=None,
                        help="Domain string to filter cookies to (e.g. eastwesthealing.com)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds between requests (default: 1.0, be polite)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only process the first N lessons (testing/partial)")
    parser.add_argument("--no-refresh", action="store_true",
                        help="Use existing metadata/cookies.txt; don't touch the browser")
    parser.add_argument("--keep-html", action="store_true",
                        help="Also save raw HTML under metadata/raw/ (off by default)")
    parser.add_argument("--user-agent",
                        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    args = parser.parse_args()

    course_dir = Path(args.course_dir).expanduser().resolve()
    manifest_path = course_dir / "metadata" / "lesson_urls.json"
    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found. Run discovery first "
              f"(or discover_skool.py for Skool).", file=sys.stderr)
        return 1

    lessons = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Safety: older manifests may lack lesson_order. Assign it by position
    # within each module (same order process_videos will see).
    if any("lesson_order" not in l for l in lessons):
        ctr: dict = {}
        for l in lessons:
            mo = l.get("module_order", 1)
            ctr[mo] = ctr.get(mo, 0) + 1
            l.setdefault("lesson_order", ctr[mo])
    if args.limit:
        lessons = lessons[:args.limit]
    print(f"Loaded {len(lessons)} lessons from {manifest_path}")

    cookie_file = course_dir / "metadata" / "cookies.txt"
    if args.no_refresh:
        if not cookie_file.exists():
            print(f"--no-refresh set but {cookie_file} is missing. "
                  f"Run /login (manual paste) first.", file=sys.stderr)
            return 1
        print(f"Using existing cookies: {cookie_file}")
    else:
        first_url = next((l.get("url") for l in lessons if l.get("url")), None)
        domain = args.domain or (urlparse(first_url).hostname if first_url else None)
        print(f"Refreshing cookies for domain '{domain}' from the live browser session...")
        cookie_file = refresh_cookies(course_dir, domain)
    cookies = load_cookies(cookie_file)

    results = []
    all_videos = []
    start = time.time()

    with httpx.Client(headers={"User-Agent": args.user_agent}, cookies=cookies,
                      follow_redirects=True, timeout=30.0) as client:
        for i, lesson in enumerate(lessons, start=1):
            print(f"  [{i:>2}/{len(lessons)}] {lesson.get('url') or lesson.get('title')}")
            result = pull_one(client, lesson, course_dir, args.keep_html)
            results.append(result)
            if result["status"] == "ok":
                for v in result["videos"]:
                    all_videos.append({**v, "post_id": lesson.get("post_id"),
                                       "lesson_title": result["title"]})
                n_assets = sum(1 for a in result["attachments"] if a.get("status") == "ok")
                print(f"        ok ... {result['markdown_chars']:,} chars MD, "
                      f"{result['links_found']} links, {n_assets} assets, "
                      f"{len(result['videos'])} video src ({result['fetch']})")
            else:
                print(f"        FAILED ... {result['status']}")
            if i < len(lessons):
                time.sleep(args.delay)

    elapsed = time.time() - start
    ok = sum(1 for r in results if r["status"] == "ok")

    (course_dir / "metadata" / "scrape_report.json").write_text(
        json.dumps({"run_seconds": round(elapsed, 1), "total": len(results),
                    "ok": ok, "failed": len(results) - ok,
                    "keep_html": args.keep_html, "results": results},
                   indent=2, default=str),
        encoding="utf-8")
    (course_dir / "metadata" / "video_sources.json").write_text(
        json.dumps(all_videos, indent=2, default=str), encoding="utf-8")

    print()
    print("=" * 60)
    print(f"Done in {elapsed:.1f}s ... {ok}/{len(results)} lessons OK")
    print(f"  Course tree: {course_dir}  (NN-module/NN-lesson/<lesson>.md + downloads/)")
    print(f"  Videos found: {len(all_videos)} (metadata/video_sources.json)")
    print(f"  Report:       {course_dir / 'metadata' / 'scrape_report.json'}")
    return 0 if ok == len(results) else 2


if __name__ == "__main__":
    sys.exit(main())
