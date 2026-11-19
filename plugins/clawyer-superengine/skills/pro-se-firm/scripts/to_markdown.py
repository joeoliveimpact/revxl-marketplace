"""
to_markdown.py — the firm's Markdown Maker.

Converts case documents (PDF, images, DOCX, TXT, CSV, etc.) into clean Markdown the firm can read and recall.
Mirrors the common doc->markdown pipeline: MarkItDown first, OCR fallback (PyMuPDF + Tesseract) for scanned PDFs and
images, pypdf as a last resort. Each output gets a `<!-- source: ... | method: ... -->` header so provenance is clear.

PORTABLE & GRACEFUL: every backend is optional. If one isn't installed, the script reports what to install and tries
the next. It never crashes the whole run because one library is missing.

Usage:
    python to_markdown.py <file-or-folder> [output_dir]
        <file-or-folder>  a single document, or a folder (recursed)
        [output_dir]      where the .md files go (default: ./md next to the input)

Recommended install (for full coverage):
    pip install markitdown pymupdf pytesseract pillow pypdf
    plus the Tesseract OCR engine on the system (Windows: C:\\Program Files\\Tesseract-OCR\\tesseract.exe)
OCR is only needed for SCANNED PDFs and images; text-based PDFs work with MarkItDown alone.
"""
import os, re, sys, hashlib

MIN_TEXT = 40          # if MarkItDown yields less than this, treat the PDF as scanned -> OCR
OCR_MAX_PAGES = 80
IMG_EXT   = {".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff", ".bmp"}
SKIP_EXT  = {".mp3", ".mp4", ".m4a", ".wav", ".mov", ".aac", ".zip", ".heic"}  # media: separate transcription pass

# ---- optional backends (import lazily so a missing one doesn't break the rest) ----
def _try_markitdown():
    try:
        from markitdown import MarkItDown
        return MarkItDown()
    except Exception:
        return None

def _has(mod):
    try:
        __import__(mod); return True
    except Exception:
        return False

_MID = _try_markitdown()
_HAS_FITZ = _has("fitz")
_HAS_TESS = _has("pytesseract")
_HAS_PIL  = _has("PIL")
_HAS_PYPDF = _has("pypdf")

def _sanitize(s): return re.sub(r"[^A-Za-z0-9.-]", "_", s)

def _md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def _ocr_pdf(path):
    if not (_HAS_FITZ and _HAS_TESS and _HAS_PIL):
        return None
    import fitz, pytesseract
    from PIL import Image
    doc = fitz.open(path); out = []
    for i, page in enumerate(doc):
        if i >= OCR_MAX_PAGES:
            out.append(f"\n[... truncated after {OCR_MAX_PAGES} pages ...]"); break
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        out.append(pytesseract.image_to_string(img))
    doc.close()
    return "\n\n".join(out)

def _pypdf_text(path):
    if not _HAS_PYPDF:
        return None
    from pypdf import PdfReader
    try:
        return "\n\n".join((pg.extract_text() or "") for pg in PdfReader(path).pages)
    except Exception:
        return None

def extract(path, ext):
    """Return (text, method) or (None, reason)."""
    if ext in IMG_EXT:
        if _HAS_TESS and _HAS_PIL:
            import pytesseract; from PIL import Image
            return pytesseract.image_to_string(Image.open(path)), "ocr_image"
        return None, "needs pytesseract+pillow+Tesseract for image OCR"
    if ext == ".pdf":
        if _MID:
            try:
                t = _MID.convert(path).text_content or ""
                if len(t.strip()) >= MIN_TEXT:
                    return t, "markitdown"
            except Exception:
                pass
        ocr = _ocr_pdf(path)
        if ocr and ocr.strip():
            return ocr, "ocr_pdf"
        pp = _pypdf_text(path)
        if pp and pp.strip():
            return pp, "pypdf"
        return None, "scanned PDF with no OCR backend (install pymupdf+pytesseract+pillow+Tesseract)"
    # everything else: let MarkItDown try (docx, pptx, xlsx, html, txt, csv, ...)
    if _MID:
        try:
            return (_MID.convert(path).text_content or ""), "markitdown"
        except Exception as e:
            return None, f"markitdown failed: {e}"
    # plain-text fallback
    if ext in {".txt", ".md", ".csv"}:
        return open(path, encoding="utf-8", errors="replace").read(), "raw"
    return None, "no backend (pip install markitdown)"

def collect(target):
    if os.path.isfile(target):
        return [target]
    files = []
    for root, _, names in os.walk(target):
        for n in names:
            files.append(os.path.join(root, n))
    return files

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    target = sys.argv[1]
    base = target if os.path.isdir(target) else os.path.dirname(os.path.abspath(target))
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(base, "md")
    os.makedirs(out_dir, exist_ok=True)

    if not _MID:
        print("NOTE: MarkItDown not installed (pip install markitdown). Falling back to OCR/pypdf where possible.")
    if not (_HAS_FITZ and _HAS_TESS and _HAS_PIL):
        print("NOTE: OCR stack incomplete (need pymupdf + pytesseract + pillow + the Tesseract engine). "
              "Scanned PDFs/images may be skipped.")

    files = collect(target)
    done = skipped = failed = 0
    seen = set()
    for full in files:
        ext = os.path.splitext(full)[1].lower()
        name = os.path.basename(full)
        if ext in SKIP_EXT:
            print(f"  [media-skip ] {name}"); skipped += 1; continue
        d = _md5(full)
        if d in seen:
            print(f"  [dup-skip   ] {name}"); continue
        seen.add(d)
        try:
            text, method = extract(full, ext)
            if not text:
                print(f"  [skip       ] {name} :: {method}"); skipped += 1; continue
            rel = os.path.relpath(full, base) if os.path.isdir(target) else name
            outfn = _sanitize(rel) + ".md"
            with open(os.path.join(out_dir, outfn), "w", encoding="utf-8") as w:
                w.write(f"<!-- source: {rel} | method: {method} -->\n\n")
                w.write(text.strip() + "\n")
            print(f"  [{method:11}] {name} ({len(text.strip())} chars) -> {outfn}")
            done += 1
        except Exception as e:
            print(f"  [FAIL       ] {name} :: {e}"); failed += 1

    print(f"\nDONE. converted={done}, skipped={skipped}, failed={failed}. Output: {out_dir}")

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
