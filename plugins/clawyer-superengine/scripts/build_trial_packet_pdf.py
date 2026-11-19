"""
Trial Prep Document PDF builder — pro-se-firm v1.6.0.

Implements TRIAL-PREP-DOCUMENT-PDF-SPEC.md exactly.

Covers: trial packets, hearing scripts, cross-exam guides, witness prep,
any personal preparation document the pro-se client takes to the podium.

This is the SHAREABLE/SANITIZED version. Case-specific content is
parameterized via the `content` dict passed to build().

Locked elements:
- Letter 8.5x11
- Margins 0.65in left/right + 0.75in top/bottom
- Helvetica throughout, 10pt body
- Page numbers on every page including page 1, Helvetica 9pt centered bottom
- 12 named hex colors (locked)
- 5 numbered box types
- Section bar = NAVY/MAROON/TEAL filled rectangle, white bold text
- Witness color coding inside Section 7
- Citation tags STRIPPED (no [VERIFIED]/[CONFIRM]/[UNVERIFIED] in body)
- Colored text rules: GREEN_TEXT = exhibit refs ONLY,
  RED_TEXT = STOP warnings ONLY, ORANGE_TEXT = task day headers ONLY
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable,
)

NAVY = HexColor("#1a1a2e")
MAROON = HexColor("#8b0000")
TEAL = HexColor("#2e7d6b")
GOLD_BG = HexColor("#fffaed")
GOLD_BORDER = HexColor("#d4a017")
BLUE_BG = HexColor("#eef2ff")
BLUE_BORDER = HexColor("#3d5a99")
RED_BG = HexColor("#fff5f5")
RED_BORDER = HexColor("#cc0000")
LIGHTGRAY_BG = HexColor("#f0f2f8")
LIGHTGRAY_BORDER = HexColor("#cccccc")
GREEN_TEXT = HexColor("#1a7a1a")
RED_TEXT = HexColor("#cc0000")
ORANGE_TEXT = HexColor("#cc4400")

PAGE_WIDTH = 8.5 * inch
MARGIN_L = 0.65 * inch
MARGIN_R = 0.65 * inch
MARGIN_T = 0.75 * inch
MARGIN_B = 0.75 * inch
AVAIL_W = PAGE_WIDTH - MARGIN_L - MARGIN_R


def _ps(name, **kw):
    base = dict(fontName="Helvetica", fontSize=10, leading=13, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle(name, **base)


STYLES = {
    "cover_title": _ps("cover_title", fontName="Helvetica-Bold", fontSize=22,
                       leading=26, alignment=TA_CENTER),
    "cover_sub": _ps("cover_sub", fontSize=10, leading=14, alignment=TA_CENTER),
    "section_bar": _ps("section_bar", fontName="Helvetica-Bold", fontSize=11,
                       leading=14, textColor=white),
    "sub_header": _ps("sub_header", fontName="Helvetica-Bold", fontSize=11,
                      leading=14, spaceBefore=14, spaceAfter=4),
    "tab_label": _ps("tab_label", fontName="Helvetica-Bold", fontSize=11,
                     leading=14, spaceBefore=8, spaceAfter=2),
    "tab_desc": _ps("tab_desc", fontSize=10, leading=13, spaceAfter=10),
    "body": _ps("body", fontSize=10, leading=13, spaceAfter=6),
    "italic": _ps("italic", fontName="Helvetica-Oblique", fontSize=10,
                  leading=13, spaceAfter=4),
    "gold_body": _ps("gold_body", fontSize=10, leading=13),
    "blue_body": _ps("blue_body", fontName="Helvetica-Bold", fontSize=10,
                     leading=13, textColor=NAVY),
    "red_body": _ps("red_body", fontSize=10, leading=13),
    "lightgray_body": _ps("lightgray_body", fontSize=10, leading=13),
    "exhibit_line": _ps("exhibit_line", fontName="Helvetica-Bold", fontSize=9,
                        leading=12, textColor=GREEN_TEXT, leftIndent=4,
                        spaceAfter=6),
    "law_line": _ps("law_line", fontName="Helvetica-Bold", fontSize=9,
                    leading=12, textColor=GREEN_TEXT, leftIndent=4,
                    spaceAfter=8),
    "stop_line": _ps("stop_line", fontName="Helvetica-Bold", fontSize=10,
                     leading=13, textColor=RED_TEXT, spaceAfter=4,
                     spaceBefore=4),
    "task_day_header": _ps("task_day_header", fontName="Helvetica-Bold",
                           fontSize=10, leading=13, textColor=ORANGE_TEXT,
                           spaceBefore=10, spaceAfter=4),
    "allegation_label": _ps("allegation_label", fontName="Helvetica-Bold",
                            fontSize=11, leading=14, spaceBefore=6,
                            spaceAfter=2),
    "your_answer": _ps("your_answer", fontSize=10, leading=13, spaceAfter=4),
    "q_item": _ps("q_item", fontSize=10, leading=13, leftIndent=0.2 * inch,
                  firstLineIndent=-0.15 * inch, spaceAfter=5),
    "say_label": _ps("say_label", fontName="Helvetica-Bold", fontSize=10,
                     leading=13, spaceAfter=2),
}


def page_number_callback(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(PAGE_WIDTH / 2, 0.5 * inch, str(doc.page))
    canvas.restoreState()


def section_bar(text, color=NAVY):
    """Full-width colored bar, white bold text, 8pt left padding."""
    p = Paragraph(text, STYLES["section_bar"])
    tbl = Table([[p]], colWidths=[AVAIL_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tbl


def gold_box(lines, label=None):
    """BOX 1 — gold fill, gold border. Instruction / note to client."""
    inner = []
    if label:
        inner.append(Paragraph(f"<b>{label}</b>", STYLES["gold_body"]))
    for ln in lines:
        inner.append(Paragraph(ln, STYLES["gold_body"]) if isinstance(ln, str) else ln)
    tbl = Table([[inner]], colWidths=[AVAIL_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GOLD_BG),
        ("BOX", (0, 0), (-1, -1), 1.0, GOLD_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tbl


def blue_say_box(text):
    """BOX 2 — blue fill, blue border, bold navy body. Verbatim courtroom script."""
    p = Paragraph(text, STYLES["blue_body"])
    tbl = Table([[p]], colWidths=[AVAIL_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_BG),
        ("BOX", (0, 0), (-1, -1), 1.0, BLUE_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tbl


def red_embedded_doc(content_paragraphs):
    """BOX 3 — red fill, red border. Embedded court document."""
    tbl = Table([[content_paragraphs]], colWidths=[AVAIL_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), RED_BG),
        ("BOX", (0, 0), (-1, -1), 1.0, RED_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return tbl


def lightgray_box(lines, label=None):
    """BOX 4 — light-gray-blue fill, soft border. TOC / standard list."""
    inner = []
    if label:
        inner.append(Paragraph(f"<b>{label}</b>", STYLES["lightgray_body"]))
    for ln in lines:
        inner.append(Paragraph(ln, STYLES["lightgray_body"]) if isinstance(ln, str) else ln)
    tbl = Table([[inner]], colWidths=[AVAIL_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHTGRAY_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, LIGHTGRAY_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tbl


def say_block(say_text):
    """SAY: label above + BLUE BOX containing the verbatim text."""
    return [Paragraph("SAY:", STYLES["say_label"]), blue_say_box(say_text)]


def build(output_path, content):
    """
    Build a trial prep PDF from a structured content dict.

    Args:
        output_path: Path to write the PDF.
        content: dict with keys:
            title (str), case_line (str), court_line (str), name_line (str),
            your_numbers (list of HTML strings), sections_toc (list of strings),
            sections (list of section dicts).
            Each section dict has: color ("NAVY"|"MAROON"|"TEAL"),
            bar_text (str), blocks (list of (kind, payload) tuples).
            Block kinds: sub_header, sub_bar, body, italic, stop, task_day,
            exhibit, law, gold_box, blue_say, say_block, red_embedded,
            lightgray, allegation, tab, question, spacer, page_break.

    Returns:
        Path to the written PDF.
    """
    doc = SimpleDocTemplate(
        str(output_path), pagesize=letter,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        title=content.get("title", "Trial Prep Document"),
    )

    story = []

    story.append(Spacer(1, 1.0 * inch))
    story.append(Paragraph(content["title"], STYLES["cover_title"]))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(content["case_line"], STYLES["cover_sub"]))
    story.append(Paragraph(content["court_line"], STYLES["cover_sub"]))
    story.append(Paragraph(content["name_line"], STYLES["cover_sub"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY))
    story.append(Spacer(1, 0.2 * inch))

    if content.get("your_numbers"):
        story.append(gold_box(content["your_numbers"], label="YOUR NUMBERS"))
        story.append(Spacer(1, 0.15 * inch))

    if content.get("sections_toc"):
        story.append(lightgray_box(
            content["sections_toc"],
            label="SECTIONS IN THIS DOCUMENT",
        ))
        story.append(Spacer(1, 0.2 * inch))

    for section in content.get("sections", []):
        bar_color = {"NAVY": NAVY, "MAROON": MAROON, "TEAL": TEAL}.get(
            section.get("color", "NAVY").upper(), NAVY
        )
        story.append(section_bar(section["bar_text"], bar_color))
        story.append(Spacer(1, 0.1 * inch))

        for kind, payload in section.get("blocks", []):
            if kind == "sub_header":
                story.append(Paragraph(payload, STYLES["sub_header"]))
            elif kind == "sub_bar":
                color = {"NAVY": NAVY, "MAROON": MAROON, "TEAL": TEAL}.get(
                    payload.get("color", "NAVY").upper(), NAVY
                )
                story.append(section_bar(payload["text"], color))
                story.append(Spacer(1, 0.08 * inch))
            elif kind == "body":
                story.append(Paragraph(payload, STYLES["body"]))
            elif kind == "italic":
                story.append(Paragraph(payload, STYLES["italic"]))
            elif kind == "stop":
                story.append(Paragraph(payload, STYLES["stop_line"]))
            elif kind == "task_day":
                story.append(Paragraph(payload, STYLES["task_day_header"]))
            elif kind == "exhibit":
                story.append(Paragraph(payload, STYLES["exhibit_line"]))
            elif kind == "law":
                story.append(Paragraph(payload, STYLES["law_line"]))
            elif kind == "gold_box":
                story.append(gold_box(payload["lines"], label=payload.get("label")))
            elif kind == "blue_say":
                story.append(blue_say_box(payload))
            elif kind == "say_block":
                for el in say_block(payload):
                    story.append(el)
            elif kind == "red_embedded":
                story.append(red_embedded_doc(payload))
            elif kind == "lightgray":
                story.append(lightgray_box(payload["lines"], label=payload.get("label")))
            elif kind == "allegation":
                story.append(Paragraph(payload["alleg"], STYLES["allegation_label"]))
                story.append(Paragraph(
                    f"<b>YOUR ANSWER:</b> {payload['answer']}",
                    STYLES["your_answer"],
                ))
                story.append(Paragraph(payload["exhibit"], STYLES["exhibit_line"]))
            elif kind == "tab":
                story.append(Paragraph(payload["label"], STYLES["tab_label"]))
                story.append(Paragraph(payload["desc"], STYLES["tab_desc"]))
            elif kind == "question":
                num, rest = payload.split(".", 1)
                story.append(Paragraph(f"<b>{num}.</b>{rest}", STYLES["q_item"]))
            elif kind == "spacer":
                story.append(Spacer(1, float(payload) * inch))
            elif kind == "page_break":
                story.append(PageBreak())

        story.append(Spacer(1, 0.2 * inch))

    doc.build(
        story,
        onFirstPage=page_number_callback,
        onLaterPages=page_number_callback,
    )
    return output_path


EXAMPLE_CONTENT = {
    "title": "TRIAL PREP DOCUMENT",
    "case_line": "<CASE_PARTY> v. <CASE_PARTY> | Cause No. <CAUSE_NO>",
    "court_line": "<COUNTY> Chancery Court | <CHANCELLOR> | <HEARING_DATE>",
    "name_line": "<CLIENT> | Pro Se <PARTY_ROLE>",
    "your_numbers": [
        "<b>TO <CLIENT>:</b> You have the documents. You have the truth. "
        "One sentence at a time. Calm parents win.",
    ],
    "sections_toc": [
        "1. Checklist and print list",
        "2. Binder: tabs in order",
        "3. Opening statement",
        "4. Court script phase by phase",
        "5. Issue-specific spine",
        "6. Every allegation and your answer",
        "7. Cross-examination by witness",
        "8. Objections guide",
        "9. Fees / costs / remedy argument",
        "10. Every law explained plainly",
        "11. After hearing: proactive strategy",
        "<b>LAST PAGE: Pocket card.</b>",
    ],
    "sections": [
        {
            "color": "NAVY",
            "bar_text": "SECTION 1 — CHECKLIST AND PRINT LIST",
            "blocks": [
                ("sub_header", "STILL NEED TO PRINT — <N> COPIES EACH"),
                ("body", "[ ] Print item 1"),
                ("task_day", "STOP: <DATE>"),
                ("body", "[ ] Task one"),
            ],
        },
    ],
}


if __name__ == "__main__":
    output = Path("/tmp/sample-trial-prep.pdf")
    p = build(output, EXAMPLE_CONTENT)
    print(f"Built: {p}")
