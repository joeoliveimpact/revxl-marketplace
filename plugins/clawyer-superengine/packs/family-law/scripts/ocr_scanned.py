#!/usr/bin/env python
"""OCR scanned case PDFs with Surya (GPU). Writes <name>.ocr.md next to the source.

Usage:
  python scripts/ocr_scanned.py <file.pdf> [file2.pdf ...]
  python scripts/ocr_scanned.py --scan          # find every image-only PDF under evidence/ and list it
  python scripts/ocr_scanned.py --all           # OCR every image-only PDF found

Why Surya and not tesseract: transformer-based, far better on phone screenshots,
handwriting and stamped court documents, and it uses the local CUDA GPU.
"""
import sys, os, glob, time

EVIDENCE = __import__("json").load(open(__import__("os").path.join(__import__("os").environ.get("CLAUDE_PROJECT_DIR") or ".", "firm.config.json"), encoding="utf-8"))["paths"]["evidence"]
DPI = 200


def page_needs_ocr(page, min_chars=400):
    """A page is image-only if it has little text but carries an image."""
    txt = page.get_text().strip()
    return len(txt) < min_chars and len(page.get_images(full=True)) > 0


def find_scanned(root=EVIDENCE):
    import fitz
    out = []
    for p in glob.glob(os.path.join(root, "**", "*.pdf"), recursive=True):
        try:
            d = fitz.open(p)
        except Exception:
            continue
        n = sum(1 for pg in d if page_needs_ocr(pg))
        if n:
            out.append((p, n, len(d)))
        d.close()
    return sorted(out, key=lambda x: -x[1])


_PRED = {}


def predictors():
    if not _PRED:
        from surya.foundation import FoundationPredictor
        from surya.recognition import RecognitionPredictor
        from surya.detection import DetectionPredictor
        fp = FoundationPredictor()
        _PRED["rec"] = RecognitionPredictor(fp)
        _PRED["det"] = DetectionPredictor()
    return _PRED["rec"], _PRED["det"]


def ocr_pdf(path):
    import fitz
    from PIL import Image
    rec, det = predictors()
    doc = fitz.open(path)
    lines_out = [f"# OCR — {os.path.basename(path)}", "",
                 "> Machine OCR (Surya). **Unverified.** Confirm any quoted language "
                 "against the page image before it is relied on or filed.", ""]
    for i, page in enumerate(doc):
        native = page.get_text().strip()
        if not page_needs_ocr(page):
            lines_out += [f"## Page {i+1} — native text", "", native, ""]
            continue
        pix = page.get_pixmap(dpi=DPI)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        res = rec([img], det_predictor=det)[0]
        text = "\n".join(ln.text for ln in res.text_lines)
        lines_out += [f"## Page {i+1} — OCR", "", text or "_(no text recovered)_", ""]
    doc.close()
    out = os.path.splitext(path)[0] + ".ocr.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))
    return out, len("\n".join(lines_out))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    if args[0] in ("--scan", "--all"):
        found = find_scanned()
        print(f"{len(found)} PDFs contain image-only pages:\n")
        for p, n, tot in found:
            print(f"  {n:3}/{tot:<3} pp  {p}")
        if args[0] == "--scan":
            sys.exit(0)
        targets = [p for p, _, _ in found]
    else:
        targets = args

    print(f"\nOCR on {len(targets)} file(s)...\n", flush=True)
    for p in targets:
        t0 = time.time()
        try:
            out, size = ocr_pdf(p)
            print(f"  OK  {size:7} B  {time.time()-t0:5.1f}s  {out}", flush=True)
        except Exception as e:
            print(f"  ERR {type(e).__name__}: {str(e)[:120]}  {p}", flush=True)
