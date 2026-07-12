"""qc_pdf.py — basic quality-control check for a PDF file."""


def check(pdf_path: str) -> dict:
    """Return ``{"pages": int, "ok": bool, "warnings": [str]}`` for *pdf_path*."""
    import fitz

    doc = fitz.open(pdf_path)
    pages = doc.page_count
    warnings: list[str] = []
    if pages == 0:
        warnings.append("zero pages")
    return {"pages": pages, "ok": not warnings, "warnings": warnings}
