"""Tiny local web server for the renderers.

Serves two folders under one origin so a page can load the plugin's design system and the
story's own files without copying anything:
    /plugin/...  -> the plugin root (renderer pages, design system)
    /job/...     -> the story folder (story.json, card.json, photos, avatar)
Bound to 127.0.0.1 on a free port. Nothing leaves the machine except the CDN/font requests the
pages themselves make.
"""
import functools
import http.server
import pathlib
import posixpath
import threading
import urllib.parse

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent.parent


class _Handler(http.server.SimpleHTTPRequestHandler):
    roots = {}

    def log_message(self, *a):
        pass

    def translate_path(self, path):
        path = urllib.parse.unquote(urllib.parse.urlsplit(path).path)
        parts = [p for p in posixpath.normpath(path).split("/") if p and p not in (".", "..")]
        if not parts or parts[0] not in self.roots:
            return str(PLUGIN_ROOT / "__missing__")
        base = self.roots[parts[0]].resolve()
        target = base.joinpath(*parts[1:]).resolve()
        if base != target and base not in target.parents:   # no escaping the served folder
            return str(PLUGIN_ROOT / "__missing__")
        return str(target)


def serve(job_dir):
    """Start the server; returns (server, base_url). Call server.shutdown() when done."""
    handler = type("H", (_Handler,), {"roots": {"plugin": PLUGIN_ROOT, "job": pathlib.Path(job_dir)}})
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_port}"


FONT_JS = """([fam, w, italic]) => [...document.fonts].some(f => {
  if (f.family.replace(/["']/g, '') !== fam || f.status !== 'loaded') return false;
  if (italic && f.style !== 'italic') return false;
  const [lo, hi = lo] = String(f.weight).split(' ').map(Number);
  return w >= lo && w <= hi;
})"""
