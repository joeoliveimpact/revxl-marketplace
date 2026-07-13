"""extract_assets.py — extract colors and images from a PDF via fitz/PIL."""

import os
import collections


def extract(pdf_path: str, out_dir: str | None = None) -> dict:
    """Return ``{"colors": [hex...], "images": [path...]}`` from *pdf_path*.

    Images are saved as PNG files under *out_dir* (defaults to a sibling
    ``assets/`` folder next to *pdf_path*).  The colors list is derived from
    the dominant palette of the first page cover thumbnail (PIL color counter).
    """
    import fitz  # PyMuPDF
    from PIL import Image

    doc = fitz.open(pdf_path)

    if out_dir is None:
        base = os.path.splitext(pdf_path)[0]
        out_dir = base + "_assets"
    os.makedirs(out_dir, exist_ok=True)

    # --- image extraction (ported from extract_peptide_assets.py) ---
    saved_paths: list[str] = []
    seen: dict[int, int] = {}
    for pno in range(doc.page_count):
        for img in doc.get_page_images(pno):
            xref = img[0]
            if xref in seen:
                continue
            seen[xref] = pno
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                fn = os.path.join(out_dir, f"img_p{pno + 1:02d}_x{xref}.png")
                pix.save(fn)
                saved_paths.append(fn)
            except Exception:
                pass

    # --- dominant color extraction from cover page ---
    colors: list[str] = []
    if doc.page_count > 0:
        pm = doc[0].get_pixmap(dpi=72)
        img = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
        small = img.resize((80, 100))
        cnt = collections.Counter(small.getdata())
        for rgb, _ in cnt.most_common(10):
            colors.append(f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}")

    return {"colors": colors, "images": saved_paths}
