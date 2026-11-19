# TRIAL PREP DOCUMENT PDF SPEC
# Case-agnostic — personal podium-bound PDF.
# Use this spec for: trial packets, hearing scripts, cross-examination
# guides, witness prep, and any personal preparation document.
#
# This is a DIFFERENT document type from court filings.
# Court filings use COURT-PDF-SPEC.md.
# Trial prep documents use THIS spec.
# Never mix the two.

---

## THE DIFFERENCE BETWEEN THESE TWO DOCUMENT TYPES

| Court Filing | Trial Prep Document |
|---|---|
| Goes to the clerk | Stays with the litigant |
| Plain Times-Roman throughout | Color, visual hierarchy |
| No color | Multiple colors by content type |
| Caption block required | No caption block |
| Certificate of Service | No Certificate of Service |
| Neutral tone | Direct, personal tone ("You", "SAY:") |
| COURT-PDF-SPEC.md | THIS spec |

---

## TOOL AND SETUP

reportlab. Install if needed: `pip install reportlab --break-system-packages`

Page size: letter (8.5 × 11 inches)
Margins: left 0.65in, right 0.65in, top 0.75in, bottom 0.75in
(Tighter than court filings — more content per page, easier to flip through.)

Page numbers: Helvetica 9pt, centered, bottom center (0.5in from bottom). Numbered on every page including page 1.

---

## COLOR PALETTE

Define these colors. Use them only for their designated purpose. Never substitute or improvise.

```
NAVY        = HexColor('#1a1a2e')   # Section header bars — dark navy
MAROON      = HexColor('#8b0000')   # Alert section headers (urgent topics)
TEAL        = HexColor('#2e7d6b')   # Witness 3 header (therapist or similar)
GOLD_BG     = HexColor('#fffaed')   # Instruction/note box fill
GOLD_BORDER = HexColor('#d4a017')   # Instruction/note box border
BLUE_BG     = HexColor('#eef2ff')   # SAY box fill
BLUE_BORDER = HexColor('#3d5a99')   # SAY box border
RED_BG      = HexColor('#fff5f5')   # Embedded document box fill
RED_BORDER  = HexColor('#cc0000')   # Embedded document box border
GREEN_TEXT  = HexColor('#1a7a1a')   # Exhibit references
RED_TEXT    = HexColor('#cc0000')   # STOP warnings, urgent callouts
ORANGE_TEXT = HexColor('#cc4400')   # Task day headers
```

---

## FONTS

| reportlab name | Use for |
|---|---|
| Helvetica-Bold | Section bar text (white on dark), sub-headers, bold labels |
| Helvetica | Body text, tab descriptions, Q&A |
| Helvetica-Oblique | Italics within body |

Sizes: body 10pt. Sub-headers 11pt bold. Section bar text 11pt bold white. Cover title 22pt bold. Cover subtitle lines 10pt. Page numbers 9pt.

---

## COVER PAGE

1. Spacer 1.0in
2. Title (document name) Helvetica-Bold 22pt centered
3. Spacer 0.1in
4. Case line, court line, name line, Helvetica 10pt centered, one per row
5. Spacer 0.2in
6. HRFlowable full width, 2pt, NAVY
7. Spacer 0.2in
8. YOUR NUMBERS box (GOLD box — see BOX TYPES)
9. Spacer 0.15in
10. SECTIONS IN THIS DOCUMENT box (BLUE box — see BOX TYPES)

The cover page does NOT use a PageBreak before Section 1. Section 1 begins immediately after the cover content.

---

## SECTION HEADER BARS

Every major section opens with a full-width dark bar. This is the primary visual anchor of the document.

- Table: 1 column, full available width
- Background: NAVY (or MAROON for alert sections, TEAL for therapist-style witness)
- Text: Helvetica-Bold 11pt, WHITE, left-padded 8pt
- Row height: 22pt minimum
- No border

Default bar color = NAVY. MAROON is reserved for alert sections (urgent topics). TEAL is reserved for the therapist witness header inside the cross-exam section.

Witness header bars (within the cross-exam section): W1 NAVY, W2 MAROON, W3 TEAL.

After every section bar: Spacer 0.1in.

---

## BOX TYPES

Five box types. Each signals a different kind of content. Use the correct box for the correct content every time.

### BOX 1 — GOLD BOX (Instruction / Note to the litigant)

Used for: personal notes, golden rules, "know this" reminders, timing instructions.

- Fill GOLD_BG, border 1pt GOLD_BORDER, padding 8pt all sides
- Text Helvetica 10pt black, left-aligned, bold labels where present

### BOX 2 — BLUE BOX (SAY — exact words to speak in court)

Used for: verbatim language to say to the judge, exact testimony, exact objection language.

- Fill BLUE_BG, border 1pt BLUE_BORDER, padding 8pt
- Text Helvetica-Bold 10pt NAVY color
- The "SAY:" prefix appears as a plain-text label ABOVE the box, Helvetica-Bold 10pt black

### BOX 3 — RED BOX (Embedded Court Document)

Used for: court documents embedded within the prep packet. Signals "this is a real document, not prep notes."

- Fill RED_BG, border 1pt RED_BORDER, padding 10pt
- Text Helvetica 10pt black, may contain internal bold headers

### BOX 4 — LIGHT GRAY / PLAIN BOX (Standard content list)

Used for: table of contents, binder tab lists, neutral information.

- Fill `#f0f2f8`, border 0.5pt `#cccccc`, padding 8pt
- Text Helvetica 10pt black

### BOX 5 — NO BOX (plain body text)

For everything that does not fit a box type above. Plain left-aligned text, no border, no fill.

---

## COLORED TEXT RULES

| Color | Use | Example |
|---|---|---|
| GREEN_TEXT | Exhibit references only | "EXHIBIT: Tab 1 — anger management certificate" |
| RED_TEXT | STOP warnings only | "STOP: Count 10 days from entry date" |
| ORANGE_TEXT | Task day headers only | "STOP: TONIGHT — SUNDAY" |

Green exhibit lines appear BELOW the relevant SAY box or answer block, indented 4pt, Helvetica-Bold 9pt. STOP warnings appear as standalone lines, Helvetica-Bold 10pt RED_TEXT, no box, full width.

---

## SUB-HEADERS (within sections)

Topic groups within a section.

Format: Helvetica-Bold 11pt, black, ALL CAPS. SpaceBefore 14pt, SpaceAfter 4pt. No box. No background. No border.

---

## TAB ENTRIES (binder section)

Tab label: Helvetica-Bold 11pt black. Description: Helvetica 10pt black, left-aligned, spaceAfter 10pt. No box, no indentation.

---

## CROSS-EXAMINATION QUESTIONS

Q1., Q2., etc. Each question one line or wraps naturally. Helvetica 10pt left-aligned. The "Q1." prefix Helvetica-Bold 10pt. SpaceAfter per question 5pt. Grouped under sub-headers (ALL CAPS topic). Indentation under sub-header 0.2in.

---

## PHASE ENTRIES (court-script section)

Phase header: Helvetica-Bold 11pt black ALL CAPS, SpaceBefore 14pt, SpaceAfter 6pt. Phase body: Helvetica 10pt plain. SAY blocks: BLUE BOX. Exhibit callouts after SAY: green Helvetica-Bold 9pt. Conditional instructions: Helvetica-Oblique 10pt followed by SAY blue box.

---

## ALLEGATION / ANSWER FORMAT

Allegation line: Helvetica-Bold 11pt black. YOUR ANSWER label: Helvetica-Bold 10pt black. Answer text: Helvetica 10pt. Exhibit line: GREEN_TEXT Helvetica-Bold 9pt. SpaceAfter each block 12pt. No box.

---

## OBJECTIONS GUIDE FORMAT

Objection type: Helvetica-Bold 11pt black ALL CAPS. When line: Helvetica-Oblique 10pt. SAY box: BLUE BOX with exact objection language. LAW line: Helvetica-Bold 9pt GREEN_TEXT (verification status conveyed by the green color, no inline tag). SpaceAfter each objection block 14pt.

---

## CHECKLIST ITEMS

Task day headers: RED_TEXT or ORANGE_TEXT Helvetica-Bold 10pt. Category headers: Helvetica-Bold 11pt black. Checklist items: Helvetica 10pt.

---

## SPACING RULES

| Between | Spacer |
|---|---|
| Section bar and first content | 0.1in |
| Sub-header and first item | 0.06in |
| Content blocks within a section | 0.08in |
| Major topic groups | 0.14in |
| Sections (before next section bar) | 0.2in |

Do NOT force page breaks between sections unless content length naturally pushes a new page. Let content flow continuously.

---

## WHAT NEVER APPEARS IN THIS DOCUMENT

Personal prep document. Stays with the litigant. Never filed. Still must not contain:

- `[VERIFIED]` / `[UNVERIFIED]` / `[CONFIRM]` / `[CHECK]` tags
- Internal file paths (folder names, `.md`, `.py` filenames)
- DRAFT notices
- Sweep-script names
- Panel Review sections or AI self-grading

Tone is personal and direct. "You", the litigant's first name, "SAY:" are appropriate. Coaching document, not a legal filing.

---

## COMPLETE BUILD ORDER

1. Cover page (title, case info, YOUR NUMBERS gold box, TOC blue box)
2. Section 1 — Checklist
3. Section 2 — Binder tabs
4. Section 3 — Opening statement (SAY boxes throughout)
5. Section 4 — Court script phase by phase
6. Section 5 — Alert-topic section (MAROON section bar)
7. Section 6 — Every allegation and your answer
8. Section 7 — Cross-examination (witness sub-sections, color-coded)
9. Section 8 — Objections guide
10. Section 9 — Fees section (optional)
11. Section 10 — Laws explained (optional)
12. Section 11 — After the ruling / strategy (optional)
13. Last page — Pocket card (if applicable)

Include only the sections relevant to the specific hearing or task.

---

## CRITICAL RULE — CITATION TAG HANDLING (refined doctrine)

The CITATION TAG handling matches the court PDF spec: STRIP before reportlab opens.

- COURT-PDF-SPEC.md: STEP 0 strips all `[VERIFIED]` / `[CONFIRM]` / `[UNVERIFIED]` tags because the PDF goes to the clerk.
- THIS spec: tags get the same strip treatment because the prep document is for the podium. Verification status lives in the LAW-line color (green = verified per source) rather than inline bracket tags. If a cite cannot be safely shown in the prep document without a `[CONFIRM]` flag, it does NOT belong in the prep document yet. Verify first or omit.

This is a change from earlier versions of this spec, which kept tags inline. Tags out for both filings AND prep documents now. The distinction between the two specs is visual genre (color + boxes + tone), not citation-tag handling.

---

_Refined 2026-05-28. Companion doctrine to CLAUDE.md (markdown source) and COURT-PDF-SPEC.md (clerk-bound filings)._
