#!/usr/bin/env python3
"""Generic Mississippi chancery filing PDF engine (portable — no case facts).

Produces a court-formatted PDF: letter 8.5x11, Times New Roman 12pt, 1-inch
margins, double-spaced body, caption block, numbered paragraphs, page numbers,
and a Certificate of Service on its own page. This matches common MS chancery
norms; ALWAYS verify the exact format against the user's own court (the firm
checks an opposing filing or the local rule).

How the firm uses it: fill the CAPTION and CONTENT placeholders below from the
user's `case-profile.md` and the specific filing the firm drafted, then run it.
The values shown here are PLACEHOLDERS, not anyone's real data. Do not hard-code
a real party, address, cause number, judge, or counsel into this shipped engine,
keep case facts in the user's workspace (case-profile.md / a case-specific copy).
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph,
                                Spacer, Table, TableStyle, PageBreak)
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfgen import canvas
import sys

# ============================================================================
# FILL THESE FROM case-profile.md + the drafted filing (placeholders only here)
# ============================================================================
CASE = {
    "court_line": "IN THE CHANCERY COURT OF {{COUNTY}} COUNTY, MISSISSIPPI",
    "district_line": "{{JUDICIAL DISTRICT}}",
    "plaintiff": "{{PLAINTIFF NAME}}",
    "defendant": "{{DEFENDANT NAME}}",
    "cause_no": "CAUSE NO. {{CAUSE NUMBER}}",
    "judge": "{{JUDGE NAME}}",
    "filing_title_1": "{{FILING TITLE LINE 1}}",
    "filing_title_2": "{{FILING TITLE LINE 2 (optional)}}",
}
# Pro-se signer block (from case-profile.md). Initials only for the minor child.
SIGNER = [
    "_________________________________",
    "{{PARTY NAME}}, Pro Se {{ROLE: Plaintiff/Defendant}}",
    "{{STREET ADDRESS}}",
    "{{CITY}}, {{STATE}} {{ZIP}}",
    "{{PHONE}}",
    "{{EMAIL}}",
]
# Numbered body paragraphs (the firm inserts the drafted, scrubbed text here).
CONTENT_PARAGRAPHS = [
    "1. {{First numbered factual or argument paragraph. The firm fills these "
    "from the drafted filing. Declarations beat arguments; calendars beat "
    "narratives; one issue per filing.}}",
    "2. {{Second numbered paragraph.}}",
]
# People served (from case-profile.md): opposing counsel, GAL, etc.
SERVICE_LIST = [
    ["{{OPPOSING COUNSEL NAME}}", "Counsel for {{PARTY}}, MS Bar No. {{BAR NO}}",
     "{{ADDRESS}}", "{{CITY, STATE ZIP}}", "Email: {{EMAIL}}"],
]
OUT = sys.argv[1] if len(sys.argv) > 1 else "outputs/filing.pdf"
# ============================================================================

SERIF = "Times-Roman"
BOLD = "Times-Bold"

body = ParagraphStyle("body", fontName=SERIF, fontSize=12, leading=18, alignment=TA_JUSTIFY, spaceAfter=6)
num = ParagraphStyle("num", parent=body, leftIndent=0.4*inch, firstLineIndent=-0.4*inch)
center_bold = ParagraphStyle("cb", fontName=BOLD, fontSize=12, leading=15, alignment=TA_CENTER)
title = ParagraphStyle("title", fontName=BOLD, fontSize=12, leading=16, alignment=TA_CENTER, spaceBefore=8, spaceAfter=8)
heading = ParagraphStyle("heading", fontName=BOLD, fontSize=12, leading=18, alignment=TA_LEFT, spaceBefore=8, spaceAfter=2)
sig = ParagraphStyle("sig", fontName=SERIF, fontSize=12, leading=14, alignment=TA_LEFT)


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *a, **k):
        canvas.Canvas.__init__(self, *a, **k)
        self._saved = []

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._saved)
        for s in self._saved:
            self.__dict__.update(s)
            self.setFont("Times-Roman", 11)
            self.drawCentredString(letter[0] / 2.0, 0.5 * inch, f"Page {self._pageNumber} of {n}")
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)


def caption(flow):
    flow.append(Paragraph(CASE["court_line"], center_bold))
    if CASE["district_line"]:
        flow.append(Paragraph(CASE["district_line"], center_bold))
    flow.append(Spacer(1, 14))
    data = [
        [Paragraph(CASE["plaintiff"] + ",", body), Paragraph("", body)],
        [Paragraph("", body), Paragraph("PLAINTIFF", sig)],
        [Paragraph("VERSUS", body), Paragraph(CASE["cause_no"], sig)],
        [Paragraph("", body), Paragraph("", body)],
        [Paragraph(CASE["defendant"] + ",", body), Paragraph("DEFENDANT", sig)],
    ]
    t = Table(data, colWidths=[3.7*inch, 2.8*inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    flow.append(t)
    flow.append(Spacer(1, 6))
    flow.append(Paragraph(CASE["judge"], sig))
    flow.append(Spacer(1, 16))


def sigblock(flow):
    for line in SIGNER:
        flow.append(Paragraph(line, sig))


def build():
    flow = []
    caption(flow)
    flow.append(Paragraph(CASE["filing_title_1"], title))
    if CASE["filing_title_2"]:
        flow.append(Paragraph(CASE["filing_title_2"], title))
    flow.append(HRFlowable(width="100%", thickness=0.5, spaceBefore=2, spaceAfter=10, color="black"))
    for p in CONTENT_PARAGRAPHS:
        flow.append(Paragraph(p, num))
    flow.append(Spacer(1, 14))
    flow.append(Paragraph("Respectfully submitted this the ____ day of __________, 20__.", sig))
    flow.append(Spacer(1, 18))
    sigblock(flow)

    # Certificate of Service on its own page
    flow.append(PageBreak())
    caption(flow)
    flow.append(Paragraph("CERTIFICATE OF SERVICE", title))
    flow.append(HRFlowable(width="100%", thickness=0.5, spaceBefore=2, spaceAfter=10, color="black"))
    flow.append(Paragraph("I, {{PARTY NAME}}, Pro Se, hereby certify that I have this day served a true and correct copy of the foregoing upon the following by {{method, e.g., electronic mail}}.", body))
    flow.append(Spacer(1, 8))
    for block in SERVICE_LIST:
        for ln in block:
            flow.append(Paragraph(ln, sig))
        flow.append(Spacer(1, 10))
    flow.append(Spacer(1, 8))
    flow.append(Paragraph("This the ____ day of __________, 20__.", sig))
    flow.append(Spacer(1, 18))
    sigblock(flow)

    doc = SimpleDocTemplate(OUT, pagesize=letter,
                            leftMargin=inch, rightMargin=inch, topMargin=inch, bottomMargin=inch,
                            title="MS Chancery Filing")
    doc.build(flow, canvasmaker=NumberedCanvas)
    print("WROTE", OUT)


if __name__ == "__main__":
    build()
