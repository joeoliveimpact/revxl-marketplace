"""
Court PDF builder per COURT-PDF-SPEC.md (case-agnostic).

Parameterized. Reads caption + parties + judge + cause number + signatory
contact from a config dict (or a YAML/JSON config file when installed in a
matter workspace). The installed instance points this at the matter's
case-profile data; the script itself contains no matter-specific facts.

Usage:
    from build_court_pdf import build_motion, MotionConfig, Caption, ChecklistItem,
        NumberedParagraph, ReliefItem, Exhibit, ServiceAddressee

    cfg = MotionConfig(
        caption=Caption(
            court_line_1="IN THE <COURT> OF <COUNTY>, <STATE>",
            court_line_2="<DISTRICT IF APPLICABLE>",
            plaintiff="<PLAINTIFF>",
            defendant="<DEFENDANT>",
            cause_no="<CAUSE_NO>",
            judge="<JUDGE>",
        ),
        motion_title_lines=["PLAINTIFF'S MOTION FOR INTERIM RELIEF"],
        checklist=[ChecklistItem("CONFIRM ORDER ENTRY.", "..."), ...],
        numbered_paragraphs=[NumberedParagraph("PARTIES AND POSTURE", "..."), ...],
        relief=[ReliefItem("A", "LABEL", "Body."), ...],
        signatory=Signatory(name="<PLAINTIFF>", address_lines=[...], phone=..., email=...),
        service=[ServiceAddressee(...), ...],
        exhibits=[Exhibit("A", "Description."), ...],
        output_path=Path("./outputs/Motion.pdf"),
    )
    build_motion(cfg)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable,
)


# -----------------------------------------------------------------------------
# Config dataclasses
# -----------------------------------------------------------------------------

@dataclass
class Caption:
    court_line_1: str          # e.g., "IN THE CHANCERY COURT OF <COUNTY>, <STATE>"
    court_line_2: str          # e.g., "FIRST JUDICIAL DISTRICT" or "" if N/A
    plaintiff: str
    defendant: str
    cause_no: str
    judge: str


@dataclass
class ChecklistItem:
    label: str
    body: str


@dataclass
class NumberedParagraph:
    label: str                 # ALL CAPS topic label
    body: str                  # body text (may contain inline <i> tags)


@dataclass
class ReliefItem:
    letter: str
    label: str
    body: str


@dataclass
class Signatory:
    name: str
    address_lines: list[str]   # one or more address lines
    phone: str
    email: str


@dataclass
class ServiceAddressee:
    name: str
    firm_or_role: str          # e.g., "Smith Law Firm" or "Guardian ad Litem"
    address_line: str          # "[address of record]" if unknown
    email: str


@dataclass
class Exhibit:
    letter: str
    description: str


@dataclass
class MotionConfig:
    caption: Caption
    motion_title_lines: list[str]
    checklist_motion_name_lines: list[str]
    checklist: list[ChecklistItem]
    comes_now_text: str        # standard "COMES NOW the Plaintiff, ..." opener
    numbered_paragraphs: list[NumberedParagraph]
    relief: list[ReliefItem]
    signatory: Signatory
    service: list[ServiceAddressee]
    service_paragraph: str     # "I, <PLAINTIFF>, hereby certify ..."
    exhibits: list[Exhibit]
    output_path: Path
    year: str = "____"


# -----------------------------------------------------------------------------
# Paragraph styles (locked per spec)
# -----------------------------------------------------------------------------

def _styles() -> dict:
    return {
        "normal": ParagraphStyle("normal", fontName="Times-Roman", fontSize=12, leading=20, alignment=TA_LEFT),
        "justified": ParagraphStyle("justified", fontName="Times-Roman", fontSize=12, leading=20, alignment=TA_JUSTIFY),
        "centered": ParagraphStyle("centered", fontName="Times-Roman", fontSize=12, leading=20, alignment=TA_CENTER),
        "centered_bold": ParagraphStyle("centered_bold", fontName="Times-Bold", fontSize=12, leading=18, alignment=TA_CENTER),
        "numbered": ParagraphStyle("numbered", fontName="Times-Roman", fontSize=12, leading=20, alignment=TA_JUSTIFY, spaceAfter=14),
        "relief": ParagraphStyle("relief", fontName="Times-Roman", fontSize=12, leading=20, alignment=TA_JUSTIFY, leftIndent=0.4 * inch, spaceAfter=10),
        "sig": ParagraphStyle("sig", fontName="Times-Roman", fontSize=12, leading=18, alignment=TA_LEFT, leftIndent=3.5 * inch),
        "indented": ParagraphStyle("indented", fontName="Times-Roman", fontSize=12, leading=18, alignment=TA_LEFT, leftIndent=0.6 * inch),
        "exhibit": ParagraphStyle("exhibit", fontName="Times-Roman", fontSize=12, leading=20, alignment=TA_JUSTIFY, leftIndent=0.5 * inch, firstLineIndent=-0.5 * inch, spaceAfter=8),
        "section": ParagraphStyle("section", fontName="Times-Bold", fontSize=12, leading=18, alignment=TA_CENTER, spaceBefore=18, spaceAfter=10),
        "ck_title": ParagraphStyle("ck_title", fontName="Times-Bold", fontSize=18, leading=24, alignment=TA_CENTER),
        "ck_subtitle": ParagraphStyle("ck_subtitle", fontName="Times-Roman", fontSize=13, leading=18, alignment=TA_CENTER),
        "ck_instruct": ParagraphStyle("ck_instruct", fontName="Times-Italic", fontSize=11, leading=16, alignment=TA_CENTER),
        "ck_item": ParagraphStyle("ck_item", fontName="Times-Roman", fontSize=11, leading=17, alignment=TA_LEFT, leftIndent=0.4 * inch, firstLineIndent=-0.4 * inch, spaceAfter=13),
    }


# -----------------------------------------------------------------------------
# Page-number callback (skips page 1)
# -----------------------------------------------------------------------------

def _page_number_callback(canvas, doc):
    if doc.page == 1:
        return  # checklist page: no number
    canvas.saveState()
    canvas.setFont("Times-Roman", 10)
    canvas.drawCentredString(4.25 * inch, 0.6 * inch, str(doc.page))
    canvas.restoreState()


# -----------------------------------------------------------------------------
# Section builders
# -----------------------------------------------------------------------------

def _checklist_page(S: dict, motion_name_lines: list[str], items: list[ChecklistItem]) -> list:
    e = [Spacer(1, 0.25 * inch), Paragraph("PRE-FILING CHECKLIST", S["ck_title"])]
    for line in motion_name_lines:
        e.append(Paragraph(line, S["ck_subtitle"]))
    e.append(Paragraph("Complete every item before tendering to the clerk.", S["ck_instruct"]))
    e.append(HRFlowable(width="100%", thickness=1.5, color="black"))
    e.append(Spacer(1, 0.18 * inch))
    for it in items:
        text = f"[ ] <b>{it.label}</b> {it.body}"
        e.append(Paragraph(text, S["ck_item"]))
    e.append(Spacer(1, 0.15 * inch))
    e.append(HRFlowable(width="100%", thickness=1.5, color="black"))
    e.append(PageBreak())
    return e


def _caption_block(S: dict, c: Caption) -> list:
    e = [Paragraph(c.court_line_1, S["centered"])]
    if c.court_line_2:
        e.append(Paragraph(c.court_line_2, S["centered"]))
    e.append(Spacer(1, 0.12 * inch))
    e.append(HRFlowable(width="100%", thickness=1, color="black"))
    e.append(Spacer(1, 0.08 * inch))

    left = [
        [f"{c.plaintiff},"], ["    Plaintiff,"], [""], ["vs."], [""],
        [f"{c.defendant},"], ["    Defendant."],
    ]
    right = [
        [""], [""], [f"CAUSE NO. {c.cause_no}"], [""],
        [f"JUDGE {c.judge}"], [""], [""],
    ]
    rows = [[Paragraph(l[0], S["normal"]), Paragraph(r[0], S["normal"])]
            for l, r in zip(left, right)]
    tbl = Table(rows, colWidths=[3.6 * inch, 3.0 * inch])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LEADING", (0, 0), (-1, -1), 19),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    e += [tbl, Spacer(1, 0.08 * inch),
          HRFlowable(width="100%", thickness=1, color="black"),
          Spacer(1, 0.22 * inch)]
    return e


def _signature_block(S: dict, sig: Signatory, year: str) -> list:
    e = [Spacer(1, 0.3 * inch),
         Paragraph(f"Respectfully submitted this the _____ day of _________________________, {year}.", S["justified"]),
         Spacer(1, 0.55 * inch),
         Paragraph("____________________________________", S["sig"]),
         Paragraph(f"{sig.name}, Pro Se Plaintiff", S["sig"])]
    for line in sig.address_lines:
        e.append(Paragraph(line, S["sig"]))
    e.append(Paragraph(f"Phone: {sig.phone}", S["sig"]))
    e.append(Paragraph("Fax: (none, pro se)", S["sig"]))
    e.append(Paragraph(f"Email: {sig.email}", S["sig"]))
    return e


def _certificate_of_service(S: dict, cfg: MotionConfig) -> list:
    e = [PageBreak(), Spacer(1, 0.5 * inch),
         Paragraph("CERTIFICATE OF SERVICE", S["section"]),
         Paragraph(cfg.service_paragraph, S["justified"]),
         Spacer(1, 0.2 * inch)]
    for i, addr in enumerate(cfg.service):
        if i > 0:
            e.append(Spacer(1, 0.15 * inch))
        e.append(Paragraph(f"{addr.name}", S["indented"]))
        e.append(Paragraph(addr.firm_or_role, S["indented"]))
        e.append(Paragraph(addr.address_line, S["indented"]))
        e.append(Paragraph(addr.email, S["indented"]))
    e.append(Spacer(1, 0.3 * inch))
    e.append(Paragraph(f"This the _____ day of _____________, {cfg.year}.", S["justified"]))
    e.append(Spacer(1, 0.55 * inch))
    e.append(Paragraph("____________________________________", S["sig"]))
    e.append(Paragraph(f"{cfg.signatory.name}, Pro Se Plaintiff", S["sig"]))
    return e


def _exhibit_list(S: dict, exhibits: list[Exhibit]) -> list:
    e = [PageBreak(), Spacer(1, 0.5 * inch),
         Paragraph("EXHIBITS", S["section"]),
         Spacer(1, 0.1 * inch)]
    for ex in exhibits:
        e.append(Paragraph(f"<b>Exhibit {ex.letter}.</b>  {ex.description}", S["exhibit"]))
    return e


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def build_motion(cfg: MotionConfig) -> Path:
    """Build the court PDF per spec. Returns the output path."""
    S = _styles()
    cfg.output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(cfg.output_path), pagesize=letter,
        leftMargin=1.0 * inch, rightMargin=1.0 * inch,
        topMargin=1.0 * inch, bottomMargin=1.0 * inch,
        title=" - ".join(cfg.motion_title_lines)[:120],
    )
    story = []
    story += _checklist_page(S, cfg.checklist_motion_name_lines, cfg.checklist)
    story += _caption_block(S, cfg.caption)
    title_html = "<br/>".join(cfg.motion_title_lines)
    story.append(Paragraph(title_html, S["centered_bold"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(cfg.comes_now_text, S["justified"]))
    story.append(Spacer(1, 0.15 * inch))
    for i, np in enumerate(cfg.numbered_paragraphs, start=1):
        story.append(Paragraph(
            f"<b>{i}.&nbsp;&nbsp;{np.label}.</b>  {np.body}",
            S["numbered"],
        ))
    story.append(Spacer(1, 0.1 * inch))
    story.append(HRFlowable(width="100%", thickness=0.75, color="black"))
    story.append(Paragraph("RELIEF SOUGHT", S["section"]))
    story.append(Paragraph(
        "WHEREFORE, Plaintiff respectfully requests that the Court enter an "
        "order providing the following relief.", S["justified"],
    ))
    story.append(Spacer(1, 0.1 * inch))
    for ri in cfg.relief:
        if ri.label:
            story.append(Paragraph(
                f"<b>{ri.letter}.&nbsp;&nbsp;{ri.label}.</b>  {ri.body}",
                S["relief"],
            ))
        else:
            story.append(Paragraph(f"{ri.letter}.&nbsp;&nbsp;{ri.body}", S["relief"]))
    story += _signature_block(S, cfg.signatory, cfg.year)
    story += _certificate_of_service(S, cfg)
    story += _exhibit_list(S, cfg.exhibits)
    doc.build(story, onFirstPage=_page_number_callback, onLaterPages=_page_number_callback)
    return cfg.output_path


if __name__ == "__main__":
    # Minimal placeholder demo so the script is runnable in CI.
    # The installed instance constructs a real MotionConfig from case-profile data.
    demo = MotionConfig(
        caption=Caption(
            court_line_1="IN THE <COURT> OF <COUNTY>, <STATE>",
            court_line_2="<DISTRICT IF APPLICABLE>",
            plaintiff="<PLAINTIFF>",
            defendant="<DEFENDANT>",
            cause_no="<CAUSE_NO>",
            judge="<JUDGE>",
        ),
        motion_title_lines=[
            "PLAINTIFF'S MOTION FOR INTERIM RELIEF",
            "PENDING FINAL ADJUDICATION",
        ],
        checklist_motion_name_lines=["Plaintiff's Motion for Interim Relief"],
        checklist=[
            ChecklistItem("FILL IN DATES.", "Replace all date blanks."),
            ChecklistItem("CONFIRM COPY COUNT.", "Call the clerk's office."),
            ChecklistItem("ATTACH EXHIBITS.", "Verify tab order."),
        ],
        comes_now_text=(
            "COMES NOW the Plaintiff, <PLAINTIFF>, pro se, and respectfully "
            "moves this Court for the following relief. In support, Plaintiff "
            "states as follows."
        ),
        numbered_paragraphs=[
            NumberedParagraph("PARTIES AND POSTURE", "Plaintiff and Defendant ..."),
        ],
        relief=[
            ReliefItem("A", "INTERIM RELIEF", "That the Court order ..."),
            ReliefItem("D", "", "That the Court enter the proposed order submitted concurrently."),
            ReliefItem("E", "", "Such other and further relief as the Court deems just and proper."),
        ],
        signatory=Signatory(
            name="<PLAINTIFF>",
            address_lines=["<ADDRESS LINE 1>", "<ADDRESS LINE 2>"],
            phone="<PHONE>", email="<EMAIL>",
        ),
        service=[
            ServiceAddressee("<OC_NAME>, Esq.", "<OC_FIRM>", "[address of record]", "<OC_EMAIL>"),
        ],
        service_paragraph=(
            "I, <PLAINTIFF>, hereby certify that I have this day served a true "
            "and correct copy of the foregoing upon the following by electronic "
            "mail and by United States Mail, postage prepaid."
        ),
        exhibits=[Exhibit("A", "Description of exhibit A.")],
        output_path=Path("./build_court_pdf_demo.pdf"),
        year="____",
    )
    p = build_motion(demo)
    print(f"Demo written: {p}")
