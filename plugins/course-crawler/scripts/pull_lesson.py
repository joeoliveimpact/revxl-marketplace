"""
pull_lesson.py ... fetch one page and save it as a clean local archive.

What this does (plain English):
  You hand it a URL (and optionally a cookies file if the page is behind a
  login). It downloads the page, strips nav/footer/ads/sidebars, and saves:
    - <slug>.md         clean Markdown (trafilatura)
    - <slug>.links.md   categorized reference links (only if any found)
    - <slug>_assets/    downloaded attachments (only if any found)
    - <slug>.json       small metadata (title/author/date/source)
  Raw HTML is saved ONLY with --keep-html. No LLM in the loop (zero tokens).

  Link/attachment extraction reuses the exact helpers scrape_course.py uses,
  so single-page and course output stay consistent.

How to run:
  ~/.iss/venv/bin/python ${CLAUDE_SKILL_DIR}/../scripts/pull_lesson.py "https://..."
  ... --cookies ~/.iss/sessions/<domain>.txt
  ... --out ./scraped/<slug>/written --keep-html
"""

import argparse
import json
import sys
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from urllib.parse import urlparse

import httpx
import trafilatura

# Reuse the canonical extraction helpers (sibling module).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scrape_course import (  # noqa: E402
    slugify, extract_reference_links, merge_links, write_links_md,
    find_attachments, download_attachments,
)


# Windows consoles default to cp1252; force UTF-8 so non-ASCII never crashes
# a print(). No-op where already UTF-8 or not reconfigurable.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def load_cookies(path: Path) -> httpx.Cookies:
    jar = MozillaCookieJar(str(path))
    jar.load(ignore_discard=True, ignore_expires=True)
    cookies = httpx.Cookies()
    for c in jar:
        cookies.set(c.name, c.value, domain=c.domain, path=c.path)
    return cookies


def page_slug(url: str, title: str | None) -> str:
    base = title or urlparse(url).path.strip("/").replace("/", "-") or "page"
    return slugify(base, 80)


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull a single page into a clean archive.")
    parser.add_argument("url", help="Page URL")
    parser.add_argument("--cookies", default=None, help="Netscape cookies.txt (for logged-in pages)")
    parser.add_argument("--out", default="output/lessons", help="Output directory")
    parser.add_argument("--keep-html", action="store_true",
                        help="Also save raw HTML (off by default)")
    parser.add_argument("--user-agent",
                        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        help="User-Agent string to send")
    args = parser.parse_args()

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cookies = None
    if args.cookies:
        cookie_path = Path(args.cookies).expanduser().resolve()
        if not cookie_path.exists():
            print(f"Error: cookies file not found ... {cookie_path}", file=sys.stderr)
            return 1
        cookies = load_cookies(cookie_path)
        print(f"Loaded {len(cookies)} cookies from {cookie_path.name}")

    print(f"Fetching: {args.url}")
    with httpx.Client(headers={"User-Agent": args.user_agent}, cookies=cookies,
                      follow_redirects=True, timeout=30.0) as client:
        resp = client.get(args.url)
        if resp.status_code != 200:
            print(f"Error: HTTP {resp.status_code} ... {resp.reason_phrase}", file=sys.stderr)
            return 1
        html = resp.text
        print(f"Downloaded {len(html):,} bytes")

        markdown = trafilatura.extract(
            html, output_format="markdown",
            include_links=True, include_images=True, include_tables=True,
            with_metadata=True,
        )
        meta_obj = trafilatura.extract_metadata(html)
        metadata = meta_obj.as_dict() if meta_obj else {}
        if not markdown:
            print("Warning: trafilatura found no main content. Likely a JS-rendered "
                  "SPA ... use the browser backend to render it instead.", file=sys.stderr)

        title = metadata.get("title") if metadata else None
        slug = page_slug(args.url, title)
        host = urlparse(args.url).hostname or ""

        if markdown:
            (out_dir / f"{slug}.md").write_text(markdown, encoding="utf-8")

        links = merge_links(extract_reference_links(html, args.url, host), [])
        n_links = write_links_md(links, out_dir / f"{slug}.links.md", title or slug)

        asset_urls = find_attachments(html, args.url)
        assets = download_attachments(client, asset_urls, out_dir / f"{slug}_assets")

    (out_dir / f"{slug}.json").write_text(
        json.dumps({"source_url": args.url, **metadata}, indent=2, default=str),
        encoding="utf-8")
    if args.keep_html:
        (out_dir / f"{slug}.html").write_text(html, encoding="utf-8")

    n_assets = sum(1 for a in assets if a.get("status") == "ok")
    print("\nDone.")
    if markdown:
        print(f"  Markdown: {out_dir / f'{slug}.md'}  ({len(markdown):,} chars)")
    if n_links:
        print(f"  Links:    {out_dir / f'{slug}.links.md'}  ({n_links})")
    if n_assets:
        print(f"  Assets:   {out_dir / f'{slug}_assets'}  ({n_assets})")
    print(f"  Metadata: {out_dir / f'{slug}.json'}")
    if args.keep_html:
        print(f"  Raw HTML: {out_dir / f'{slug}.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
