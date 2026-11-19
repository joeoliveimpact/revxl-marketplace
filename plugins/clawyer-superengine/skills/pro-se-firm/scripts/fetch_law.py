#!/usr/bin/env python3
"""
fetch_law.py — pull a statute / rule / case page VERBATIM, beating the common
403 blockers (FindLaw, Justia) that stop plain fetches. Tries a browser-UA
requests GET first, then falls back to `curl -sL --compressed` (the documented
work-around). Strips HTML to readable text.

Binary/PDF handling added 2026-08-07 (W2 find): a PDF response is written to
disk byte-for-byte instead of being run through the HTML-to-text stripper,
which silently corrupted it.

Usage:
  python scripts/fetch_law.py <url>
  python scripts/fetch_law.py <url> --save legal-sources/<name>.txt
"""
import sys, subprocess, argparse, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

def is_binary_doc(ctype, raw):
    """True for a PDF response: Content-Type says pdf, or body starts with %PDF."""
    if ctype and "pdf" in ctype.lower():
        return True
    return bool(raw) and raw[:5] == b"%PDF-"

def via_requests(url):
    try:
        import requests
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en"},
                         timeout=30)
        if r.status_code == 200 and r.content:
            if is_binary_doc(r.headers.get("Content-Type", ""), r.content):
                return r.content, f"requests {r.status_code} [binary]"
            return r.text, f"requests {r.status_code}"
        return None, f"requests {r.status_code}"
    except Exception as e:
        return None, f"requests-error {e}"

def via_curl(url):
    try:
        r = subprocess.run(["curl", "-sL", "--compressed", "-A", UA, url],
                           capture_output=True, timeout=45)
        raw = r.stdout or b""
        if not raw:
            return None, "curl"
        if is_binary_doc(None, raw):
            return raw, "curl [binary]"
        return raw.decode("utf-8", "replace"), "curl"
    except Exception as e:
        return None, f"curl-error {e}"

def to_text(html):
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for t in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            t.decompose()
        txt = soup.get_text("\n")
    except Exception:
        txt = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
        txt = re.sub(r"(?s)<[^>]+>", " ", txt)
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"\n\s*\n\s*\n+", "\n\n", txt)
    return txt.strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--save", default=None)
    a = ap.parse_args()
    payload, how = via_requests(a.url)
    if not payload:
        payload2, how2 = via_curl(a.url); how = f"{how} -> {how2}"
        payload = payload2
    if not payload:
        print(f"FETCH FAILED ({how}) for {a.url}"); sys.exit(1)

    # Binary/PDF: write bytes unchanged. Never through to_text().
    if isinstance(payload, bytes):
        if not a.save:
            print(f"BINARY/PDF response ({how}), {len(payload)} bytes. "
                  f"Re-run with --save <path.pdf> to write it to disk unchanged.")
            sys.exit(1)
        from pathlib import Path
        p = Path(a.save); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)
        print(f"saved {len(payload)} bytes (binary, unmodified) -> {a.save}  ({how})")
        return

    html = payload
    txt = to_text(html)
    header = f"# Fetched verbatim ({how})\n# Source: {a.url}\n\n"
    if a.save:
        from pathlib import Path
        p = Path(a.save); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(header + txt, encoding="utf-8")
        print(f"saved {len(txt)} chars -> {a.save}  ({how})")
    else:
        print(header + txt[:6000] + ("\n...[truncated; use --save for full]" if len(txt) > 6000 else ""))

if __name__ == "__main__":
    main()
