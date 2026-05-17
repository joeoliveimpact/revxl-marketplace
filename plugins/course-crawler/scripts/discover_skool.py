"""
discover_skool.py ... turn a Skool classroom into the canonical course layout.

Skool is a Next.js app. Every classroom page embeds the ENTIRE course tree in
its <script id="__NEXT_DATA__"> ... titles, the lesson writeup (`desc`, a
ProseMirror doc), the single correct `videoLink`, and `resources` (reference
links + downloadable files). So ONE captured classroom page = the whole course,
with exact per-lesson data. No lesson-by-lesson navigation, no DOM scraping, no
sidebar/nav pollution.

Two modes:

  --from-page <captured.html> <course_dir>
      Primary path. Parse __NEXT_DATA__ from a browser-captured classroom page
      and write the canonical layout. Each lesson gets a CLEAN synthetic HTML
      (title + desc-as-HTML + the one video as an embed + resource links) so
      scrape_course.py produces clean Markdown, exact links, and exactly one
      video per lesson with zero code changes.

  <course_dir> <harvest.json>
      Fallback path (kept for non-Next.js or hand-harvested cases). See
      persist() and SKOOL_RECIPE.

How to run:
  python ${CLAUDE_SKILL_DIR}/../scripts/discover_skool.py --from-page page.html ./scraped/<slug>
  python ${CLAUDE_SKILL_DIR}/../scripts/discover_skool.py --recipe
"""

import argparse
import html as _html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Windows consoles default to cp1252; force UTF-8 so emoji/arrows never crash
# a print(). No-op where already UTF-8 or not reconfigurable.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


SKOOL_RECIPE = """\
SKOOL CLASSROOM HARVEST (preferred: --from-page)

Skool embeds the whole course in <script id="__NEXT_DATA__">. So:
  1. Drive the chosen browser backend to the classroom URL while logged in
     (cookies for skool.com must exist; the page must fully render).
  2. Save the rendered page HTML (superpowers-chrome auto-captures NNN-*.html).
  3. Run:  discover_skool.py --from-page <that .html> ./scraped/<slug>
That single page contains EVERY module + lesson with title, writeup (desc),
videoLink, and resources. No need to click each lesson.

Fallback (no __NEXT_DATA__ / non-Skool SPA): assemble the harvest JSON by hand
(shape in persist()'s docstring) and pass it positionally.
"""


# --- ProseMirror (Skool `desc`) -> HTML -----------------------------------

def _marks_wrap(text: str, marks: list) -> str:
    t = _html.escape(text)
    for mk in marks or []:
        mt = mk.get("type")
        if mt == "bold":
            t = f"<strong>{t}</strong>"
        elif mt == "italic":
            t = f"<em>{t}</em>"
        elif mt == "code":
            t = f"<code>{t}</code>"
        elif mt == "link":
            href = (mk.get("attrs") or {}).get("href", "")
            t = f'<a href="{_html.escape(href)}">{t}</a>'
    return t


def _pm_nodes_to_html(nodes: list) -> str:
    out = []
    for n in nodes or []:
        typ = n.get("type")
        content = n.get("content") or []
        attrs = n.get("attrs") or {}
        if typ == "heading":
            lvl = min(max(int(attrs.get("level", 2)), 1), 6)
            out.append(f"<h{lvl}>{_pm_inline(content)}</h{lvl}>")
        elif typ == "paragraph":
            out.append(f"<p>{_pm_inline(content)}</p>")
        elif typ == "image":
            src = attrs.get("src") or attrs.get("originalSrc") or ""
            alt = _html.escape(attrs.get("alt") or "")
            if src:
                out.append(f'<img src="{_html.escape(src)}" alt="{alt}">')
        elif typ in ("bulletList", "orderedList"):
            tag = "ul" if typ == "bulletList" else "ol"
            items = "".join(f"<li>{_pm_nodes_to_html(li.get('content') or [])}</li>"
                            for li in content)
            out.append(f"<{tag}>{items}</{tag}>")
        elif typ == "listItem":
            out.append(_pm_nodes_to_html(content))
        elif typ == "blockquote":
            out.append(f"<blockquote>{_pm_nodes_to_html(content)}</blockquote>")
        elif typ == "codeBlock":
            out.append(f"<pre><code>{_pm_inline(content)}</code></pre>")
        elif typ == "horizontalRule":
            out.append("<hr>")
        elif typ == "hardBreak":
            out.append("<br>")
        elif content:
            out.append(_pm_nodes_to_html(content))
    return "\n".join(out)


def _pm_inline(content: list) -> str:
    parts = []
    for c in content or []:
        if c.get("type") == "text":
            parts.append(_marks_wrap(c.get("text", ""), c.get("marks")))
        elif c.get("type") == "hardBreak":
            parts.append("<br>")
        elif c.get("content"):
            parts.append(_pm_inline(c["content"]))
    return "".join(parts)


def desc_to_html(desc: str) -> str:
    """Skool `desc` is '[v2]' + a ProseMirror JSON array (or plain text)."""
    if not desc:
        return ""
    body = desc[4:] if desc.startswith("[v2]") else desc
    try:
        nodes = json.loads(body)
        if isinstance(nodes, dict):
            nodes = nodes.get("content", [])
        return _pm_nodes_to_html(nodes)
    except (ValueError, TypeError):
        return f"<p>{_html.escape(desc)}</p>"


# --- video link -> an embed form find_video_sources will detect -----------

def video_embed(url: str) -> str | None:
    if not url:
        return None
    u = url.split("&views=")[0]
    host = (urlparse(u).hostname or "").lower()
    if "youtube.com" in host or "youtu.be" in host:
        vid = None
        if "youtu.be/" in u:
            vid = u.rsplit("/", 1)[-1]
        else:
            q = parse_qs(urlparse(u).query)
            vid = (q.get("v") or [None])[0]
        if vid:
            return f"https://www.youtube.com/embed/{vid[:11]}"
    if "vimeo.com" in host:
        m = re.search(r"vimeo\.com/(\d+)", u)
        if m:
            return f"https://player.vimeo.com/video/{m.group(1)}"
    # loom/wistia/etc. already detected in their native share/embed form
    return u


def slugify(text: str, max_len: int = 80) -> str:
    s = re.sub(r"[^\w\-]+", "-", (text or "").lower()).strip("-")
    return s[:max_len] or "untitled"


# --- __NEXT_DATA__ -> canonical layout ------------------------------------

def _walk_course(node, mod_order, mod_title, acc):
    """Skool course tree: internal nodes are modules, leaves are lessons."""
    kids = node.get("children") or []
    if not kids and "course" in node:
        acc.append((mod_order, mod_title, node["course"]))
        return
    for i, c in enumerate(kids, start=1):
        c_kids = c.get("children") or []
        if c_kids:
            title = (c.get("course", {}).get("metadata", {}) or {}).get("title") \
                or c.get("course", {}).get("name") or f"Module {i}"
            _walk_course(c, i, title, acc)
        else:
            _walk_course(c, mod_order, mod_title, acc)


def from_page(course_dir: Path, page_html: str) -> dict:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                  page_html, re.S)
    if not m:
        raise SystemExit("No __NEXT_DATA__ in this page. Is it a logged-in "
                         "Skool classroom page? Use the fallback harvest path.")
    data = json.loads(m.group(1))
    pp = data["props"]["pageProps"]
    root = pp.get("course") or pp.get("renderData", {}).get("course")
    if not root:
        raise SystemExit("No course tree in __NEXT_DATA__.")
    course_title = (root.get("course", {}).get("metadata", {}) or {}).get("title") \
        or root.get("course", {}).get("name") or "Skool Course"

    acc: list = []
    _walk_course({"children": root["children"]}, 1, "Lessons", acc)

    meta = course_dir / "metadata"
    rendered = meta / "rendered"
    rendered.mkdir(parents=True, exist_ok=True)

    flat: list[dict] = []
    seen_mods: dict[int, str] = {}
    for order, mtitle, course in acc:
        md = course.get("metadata", {}) or {}
        title = md.get("title") or course.get("name") or "untitled"
        seen_mods.setdefault(order, mtitle)
        m_dirname = f"{order:02d}-{slugify(mtitle, 60)}"
        (rendered / m_dirname).mkdir(parents=True, exist_ok=True)
        lesson_slug = slugify(title)

        # resources -> reference links + downloadable files
        links, attachments = [], []
        res = md.get("resources") or []
        if isinstance(res, str):
            try:
                res = json.loads(res)
            except ValueError:
                res = []
        for r in res:
            if r.get("link"):
                links.append(r["link"])
            elif r.get("file_id"):
                # Skool serves resource files from this host pattern.
                attachments.append({
                    "url": f"https://api.skool.com/files/{r['file_id']}",
                    "file_name": r.get("file_name", r["file_id"]),
                })

        # Clean synthetic HTML: title + writeup + one video + resource links.
        embed = video_embed(md.get("videoLink", ""))
        a_links = "".join(
            f'<p><a href="{_html.escape(u)}">{_html.escape(u)}</a></p>'
            for u in links)
        a_files = "".join(
            f'<p><a href="{_html.escape(a["url"])}">{_html.escape(a["file_name"])}</a></p>'
            for a in attachments)
        video_html = (f'<iframe src="{_html.escape(embed)}"></iframe>'
                      if embed else "")
        body = (f"<!DOCTYPE html><html><head><title>{_html.escape(title)}</title>"
                f"</head><body><article><h1>{_html.escape(title)}</h1>"
                f"{video_html}{desc_to_html(md.get('desc',''))}"
                f"{a_links}{a_files}</article></body></html>")
        rel = (rendered / m_dirname / f"{lesson_slug}.html")
        rel.write_text(body, encoding="utf-8")

        flat.append({
            "module_order": order,
            "module_title": mtitle,
            "category_id": root.get("course", {}).get("id", ""),
            "post_id": course.get("id") or slugify(title),
            "title": title,
            "url": "",  # body is self-contained; nothing to re-fetch
            "rendered_html": str(rel.relative_to(course_dir)),
            "links": links,
            "attachments": [a["url"] for a in attachments],
        })

    (meta / "course_manifest.json").write_text(
        json.dumps({"course_title": course_title,
                    "modules": list(seen_mods.items()),
                    "lessons": len(flat)}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    (meta / "lesson_urls.json").write_text(
        json.dumps(flat, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"course_title": course_title, "lessons": len(flat),
            "modules": len(seen_mods),
            "lesson_urls": str(meta / "lesson_urls.json")}


# --- fallback: hand-assembled harvest -------------------------------------

def persist(course_dir: Path, harvest: dict) -> dict:
    """Fallback for non-Next.js SPAs. harvest = {community, course_id,
    course_title, modules:[{module_order, module_title, lessons:[{post_id,
    title, url, body_html, links[], attachments[]}]}]}."""
    meta = course_dir / "metadata"
    rendered = meta / "rendered"
    rendered.mkdir(parents=True, exist_ok=True)
    flat: list[dict] = []
    for module in harvest.get("modules", []):
        m_order = module.get("module_order", 99)
        m_title = module.get("module_title", "module")
        m_dirname = f"{m_order:02d}-{slugify(m_title, 60)}"
        (rendered / m_dirname).mkdir(parents=True, exist_ok=True)
        for lesson in module.get("lessons", []):
            title = lesson.get("title") or lesson.get("post_id") or "untitled"
            lesson_slug = slugify(title)
            (rendered / m_dirname / f"{lesson_slug}.html").write_text(
                lesson.get("body_html") or "", encoding="utf-8")
            flat.append({
                "module_order": m_order, "module_title": m_title,
                "category_id": harvest.get("course_id", ""),
                "post_id": lesson.get("post_id") or slugify(title),
                "title": title, "url": lesson.get("url", ""),
                "rendered_html": str((rendered / m_dirname / f"{lesson_slug}.html")
                                     .relative_to(course_dir)),
                "links": lesson.get("links", []),
                "attachments": lesson.get("attachments", []),
            })
    (meta / "course_manifest.json").write_text(
        json.dumps(harvest, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8")
    (meta / "lesson_urls.json").write_text(
        json.dumps(flat, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8")
    return {"lessons": len(flat), "modules": len(harvest.get("modules", []))}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Skool classroom -> canonical course layout.")
    parser.add_argument("--from-page", nargs=2, metavar=("PAGE_HTML", "COURSE_DIR"),
                        help="Parse __NEXT_DATA__ from a captured classroom page")
    parser.add_argument("course_dir", nargs="?", help="(fallback) course folder")
    parser.add_argument("harvest_json", nargs="?", help="(fallback) harvest JSON")
    parser.add_argument("--recipe", action="store_true", help="Print the recipe")
    args = parser.parse_args()

    if args.recipe:
        print(SKOOL_RECIPE)
        return 0

    if args.from_page:
        page_html_path, course_dir = args.from_page
        course_dir = Path(course_dir).expanduser().resolve()
        page_html = Path(page_html_path).expanduser().read_text(
            encoding="utf-8", errors="replace")
        r = from_page(course_dir, page_html)
        print(json.dumps(r, indent=2, ensure_ascii=False))
        print(f"\n{r['lessons']} lessons / {r['modules']} modules from one page. "
              f"Now run scrape_course.py {course_dir} --no-refresh")
        return 0

    if args.course_dir and args.harvest_json:
        course_dir = Path(args.course_dir).expanduser().resolve()
        harvest = json.loads(Path(args.harvest_json).expanduser()
                             .read_text(encoding="utf-8"))
        print(json.dumps(persist(course_dir, harvest), indent=2))
        return 0

    print(SKOOL_RECIPE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
