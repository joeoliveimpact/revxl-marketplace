# Markdown Intake — read every document as markdown first

The firm reads text, not memory. Before the Records Analyst, Order Integrity Reviewer, or any specialist analyzes a
document (a PDF order, a transcript, a co-parenting-app export, a bank statement, a photo of a filing), that document
must be in **clean markdown**. Scanned PDFs and images are invisible until they're converted — never analyze them from
guesswork.

## How to convert

**Prefer the user's own converter if they have one.** Many users already have a doc-to-markdown pipeline installed
(MarkItDown + an OCR engine). If the case profile or workspace points to one, use it and keep its output convention.

**Otherwise use the bundled Markdown Maker:** `scripts/to_markdown.py`.

```
python scripts/to_markdown.py <file-or-folder> [output_dir]
```

- Converts PDF, images, DOCX, XLSX, PPTX, HTML, TXT, CSV → markdown.
- Method order: **MarkItDown** for text-based files → **OCR (PyMuPDF + Tesseract)** for scanned PDFs and images →
  **pypdf** as a last resort.
- Writes each file to an `md/` folder with a provenance header: `<!-- source: <path> | method: <how> -->`.
- Output named after the source so it's easy to trace back.

## Requirements (graceful if missing)

- Full coverage: `pip install markitdown pymupdf pytesseract pillow pypdf` **plus** the Tesseract OCR engine on the
  system (Windows default: `C:\Program Files\Tesseract-OCR\tesseract.exe`).
- OCR (PyMuPDF + Tesseract) is only needed for **scanned** PDFs and images. Text-based PDFs convert with MarkItDown
  alone. If a backend is missing, the script says what to install and tries the next one — it won't crash the run.

## Discipline (so markdown stays trustworthy as evidence)

- **Keep the provenance header.** The `source` + `method` line tells you whether text came from a clean extract or from
  OCR — OCR can misread, so anything tagged `ocr_pdf` / `ocr_image` should be spot-checked against the original before a
  quote is used in a filing. Tag uncertain OCR text `[CONFIRM AGAINST SOURCE]`.
- **Don't paraphrase from a scan.** If a contradiction or an order's wording turns on exact text, verify the markdown
  against the original page — OCR errors are not the witness's words.
- **One source = one markdown file.** Don't merge documents; the Records Analyst and Order Integrity Reviewer need each
  document quotable on its own.
- **Large documents:** the converter caps OCR at a page limit; if a file is truncated, note the coverage line (what was
  read vs. skipped) per the large-input rule.

## When to run it

- A new order, transcript, or filing arrives → convert before analyzing.
- Building the chronology or a contradiction log → convert the whole document set first, then read.
- Preparing exhibits → convert so each exhibit's text is searchable and quotable.

End any intake run by telling the user where the markdown landed and which files (if any) were skipped for lack of an
OCR backend, so nothing silently goes unread.
