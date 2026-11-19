#!/usr/bin/env python3
"""
ocr_pdf.py - turn any PDF (text-based OR scanned) into clean markdown.

Smart: it uses the PDF's embedded text layer when there is one (fast, exact),
and only OCRs (Tesseract) the pages that are scanned images. This is the firm's
"everything becomes markdown" tool for PDFs the plain text-extractor can't read.

Usage:
  python ocr_pdf.py <input.pdf> [output.md]

Requires: PyMuPDF (fitz), pytesseract, and Tesseract installed.
"""
import os
import re
import sys
import tempfile

import fitz  # PyMuPDF
import pytesseract

# Point at the Tesseract binary if it is not already on PATH.
for cand in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
             r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
    if os.path.exists(cand):
        pytesseract.pytesseract.tesseract_cmd = cand
        break

MIN_TEXT = 200  # real body text per page. Raised from 30 on 2026-07-29.

# Court scans carry a burned-in MEC header line on every page. At the old threshold of 30
# characters that header alone counted as "this page has text", so entire scanned ORDERS
# were skipped by OCR and came out unreadable. Doc [N], the operative temporary order,
# extracted 520 characters across 6 pages and every one of them was a header. Strip the
# boilerplate before deciding whether a page needs OCR.
BOILERPLATE = re.compile(
    r"(Case:\s*\d+CH\d+:[^\n]*|Document\s*#?:?\s*\d+|Filed:\s*\d{2}/\d{2}/\d{4}"
    r"|Page\s+\d+\s+of\s+\d+|SHIRLEY ANNE EDWARDS[^\n]*)",
    re.I)


def real_text(t):
    """Page text with court boilerplate removed, for the has-text decision only."""
    return BOILERPLATE.sub("", t or "").strip()


def page_to_text(page):
    t = (page.get_text("text") or "").strip()
    if len(real_text(t)) >= MIN_TEXT:
        return t, "text"
    pix = page.get_pixmap(dpi=300)
    tmp = os.path.join(tempfile.gettempdir(), "ocr_page.png")
    pix.save(tmp)
    ocr = (pytesseract.image_to_string(tmp) or "").strip()
    # keep whichever actually carries content
    return (ocr, "ocr") if len(real_text(ocr)) > len(real_text(t)) else (t, "text")


def main():
    if len(sys.argv) < 2:
        print("usage: python ocr_pdf.py <input.pdf> [output.md]")
        return 2
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + ".md"
    doc = fitz.open(src)
    parts = []
    modes = []
    for i, page in enumerate(doc):
        txt, mode = page_to_text(page)
        modes.append(mode)
        parts.append("## Page %d\n\n%s" % (i + 1, txt))
    parts.append("## Source\n\n%s | %d pages | via ocr_pdf.py" % (os.path.basename(src), doc.page_count))
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n\n".join(parts) + "\n")
    print("wrote %s (%d pages; %d via text layer, %d via OCR)"
          % (out, doc.page_count, modes.count("text"), modes.count("ocr")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
