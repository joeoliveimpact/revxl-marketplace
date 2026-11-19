# COURT DOCUMENT PDF SPEC
# Case-agnostic spec for clerk-bound motion PDFs.
# Companion to CLAUDE.md (which governs the markdown source).

---

## STEP 0 — STRIP ALL DRAFTING ARTIFACTS FIRST

Before writing any PDF code, scan the source markdown and remove every item below. If any appear in the final PDF, the document cannot be filed.

| What to strip | Replace with |
|---|---|
| DRAFT, show-on-screen review… | Nothing — delete entirely |
| `[VERIFIED — anything]` | Clean citation only (see §7) |
| `[UNVERIFIED — anything]` | Nothing — flag in checklist instead |
| `[CONFIRM BEFORE CITING]` | Nothing — flag in checklist instead |
| `[CHECK — anything]` | Move to checklist page only |
| `[CONFIRM. <Litigant>] anything` | Move to checklist page only |
| `scrub_check.py`, `spell_check.py`, any `.py` ref | Delete |
| Any file path (`evidence/`, `outputs/`, `.md`, `.py`) | Delete |
| `Supersedes [filename]` | Delete |
| `parked sN` | Delete |
| Internal cross-references to other drafts | Delete |
| Bold on dollar amounts inside paragraph body | Plain text only |
| Bold on dates inside paragraph body | Plain text only |

---

## STEP 1 — TOOL AND SETUP

reportlab. `pip install reportlab`.

Page size: letter (8.5 × 11). All four margins: 1.0 inch.

Page numbers: Times-Roman 10pt, centered, bottom (0.6 in from bottom). Page 1 (checklist) has NO page number. Other pages start at 2.

Add page numbers via `onFirstPage` (skip) and `onLaterPages` (draw centered page number).

---

## STEP 2 — FONTS

| reportlab name | Use |
|---|---|
| Times-Roman | Body text |
| Times-Bold | Section labels, motion title, checklist item labels |
| Times-Italic | Case citations (e.g., *Smith v. Jones*) |
| Times-BoldItalic | Not used unless needed |

Body 12pt. Checklist title 18pt bold. Checklist items 11pt. Page numbers 10pt.

---

## STEP 3 — PARAGRAPH STYLES

| Style | Font | Size | Leading | Align | Notes |
|---|---|---|---|---|---|
| normal | Times-Roman | 12 | 20 | LEFT | General |
| justified | Times-Roman | 12 | 20 | JUSTIFY | Body paragraphs |
| centered | Times-Roman | 12 | 20 | CENTER | Court name, dividers |
| centered_bold | Times-Bold | 12 | 18 | CENTER | Motion title |
| numbered | Times-Roman | 12 | 20 | JUSTIFY | Numbered ¶, spaceAfter=14 |
| relief | Times-Roman | 12 | 20 | JUSTIFY | leftIndent=0.4in |
| sig | Times-Roman | 12 | 18 | LEFT | leftIndent=3.5in |
| indented | Times-Roman | 12 | 18 | LEFT | leftIndent=0.6in (COS addressees) |
| exhibit | Times-Roman | 12 | 20 | JUSTIFY | leftIndent=0.5in, firstLineIndent=-0.5in |
| section | Times-Bold | 12 | 18 | CENTER | spaceBefore=18, spaceAfter=10 |
| ck_title | Times-Bold | 18 | 24 | CENTER | Checklist page title |
| ck_subtitle | Times-Roman | 13 | 18 | CENTER | Checklist motion name |
| ck_instruct | Times-Italic | 11 | 16 | CENTER | "Complete every item…" |
| ck_item | Times-Roman | 11 | 17 | LEFT | leftIndent=0.4in, firstLineIndent=-0.4in, spaceAfter=13 |

---

## STEP 4 — DOCUMENT PAGE ORDER

```
Page 1:  PRE-FILING CHECKLIST          (always first, own page)
Page 2:  Motion body begins            (caption + title + body)
Page N:  Motion body continues
Page N+1: CERTIFICATE OF SERVICE       (own page, NO caption repeat)
Page N+2: EXHIBIT LIST                 (own page, no caption)
```

Use `PageBreak()` between sections.

---

## STEP 5 — PAGE 1: PRE-FILING CHECKLIST

Layout top to bottom:

1. Spacer 0.25 in
2. Title `PRE-FILING CHECKLIST` (ck_title)
3. Subtitle: motion name 1–2 lines (ck_subtitle)
4. Instruction: "Complete every item before tendering to the clerk." (ck_instruct)
5. HRFlowable 100% width, 1.5pt, black
6. Spacer 0.18 in
7. Checklist items — each `[ ] LABEL. requirement.`
8. Spacer 0.15 in
9. HRFlowable 1.5pt black
10. PageBreak()

What goes in the checklist: every `[CHECK]` / `[CONFIRM]` item from the source, date blanks, address blanks, payment confirmations, exhibit attachment, copy count, read-aloud reminder.

What does NOT: motion body content, legal argument, citation tags.

---

## STEP 6 — CAPTION BLOCK

Two-column Table, colWidths=[3.6in, 3.0in].

LEFT (party names):
```
<PLAINTIFF>,
    Plaintiff,
vs.
<DEFENDANT>,
    Defendant.
```

RIGHT (case info, rows aligned with `vs.` and below):
- Row 3: `CAUSE NO. <CAUSE_NO>`
- Row 5: `JUDGE <JUDGE>`

Table style: Times-Roman 12pt, leading 19, no padding, VALIGN MIDDLE.

Surround with:
- Court line above (centered): `IN THE <COURT> OF <COUNTY>, <STATE>`
- District line (centered): `<DISTRICT IF APPLICABLE>`
- Spacer 0.12in
- HRFlowable 1pt black
- Spacer 0.08in
- [caption table]
- Spacer 0.08in
- HRFlowable 1pt black
- Spacer 0.22in

---

## STEP 7 — MOTION TITLE

Centered, Times-Bold, 12pt. ALL CAPS. No period. Line-break between logical phrases if long. centered_bold style.

Example (generic):
```
PLAINTIFF'S MOTION FOR INTERIM RELIEF AS TO THE MARITAL HOME
PENDING FINAL ADJUDICATION
```

Spacer 0.2in, then the COMES NOW opener.

---

## STEP 8 — MOTION BODY PARAGRAPHS

COMES NOW: justified style. One paragraph. No number.

Numbered paragraphs: `[N].  [ALL CAPS TOPIC LABEL.]  [Body.]` — topic label Times-Bold inline, body Times-Roman:

`<b>1.&nbsp;&nbsp;PARTIES AND POSTURE.</b>&nbsp;&nbsp;Body text here.`

Case citations italic inline. Exhibit refs `<i>(Ex. A.)</i>`. Transcript `<i>(Tr. p. 50.)</i>`.

No bold inside body for dollar amounts or dates. No underline anywhere. No ALL CAPS inside body (only the topic label).

---

## STEP 9 — RELIEF SOUGHT

Spacer 0.1in → HRFlowable 0.75pt black → `RELIEF SOUGHT` (section style) → WHEREFORE opener (justified) → Spacer 0.1in.

Each relief item: relief style, `<b>A.&nbsp;&nbsp;LABEL.</b>&nbsp;&nbsp;Body.`

Letters A, B, C for substantive relief. Plain (no bold) for `D.` ("proposed order…") and `E.` ("further relief…").

---

## STEP 10 — SIGNATURE BLOCK

Spacer 0.3in → submission line (justified) → Spacer 0.55in → seven sig-style lines:

```
____________________________________
<PLAINTIFF>, Pro Se Plaintiff
<PLAINTIFF_ADDR line 1>
<PLAINTIFF_ADDR line 2>
Phone: <PLAINTIFF_PHONE>
Fax: (none, pro se)
Email: <PLAINTIFF_EMAIL>
```

---

## STEP 11 — CERTIFICATE OF SERVICE PAGE

PageBreak() before. NO caption. NO court name. Stands alone.

1. Spacer 0.5in
2. `CERTIFICATE OF SERVICE` (section style)
3. Service paragraph (justified): "I, <PLAINTIFF>, hereby certify that I have this day served a true and correct copy of the foregoing upon the following by electronic mail and by United States Mail, postage prepaid."
4. Spacer 0.2in
5. Addressees in indented style:
   ```
   <OC_NAME>, Esq.
   <OC_FIRM>
   [address of record]
   <OC_EMAIL>
   ```
   Spacer 0.15in then GAL (if any):
   ```
   <GAL_NAME>, Esq., Guardian ad Litem
   [address of record]
   <GAL_EMAIL>
   ```
6. Spacer 0.3in
7. Date line (justified): `This the _____ day of _____________, [year].`
8. Spacer 0.55in
9. Two sig-style lines: signature underscores + `<PLAINTIFF>, Pro Se Plaintiff`.

---

## STEP 12 — EXHIBIT LIST PAGE

PageBreak() before. NO caption.

1. Spacer 0.5in
2. `EXHIBITS` (section style)
3. Spacer 0.1in
4. Each exhibit in exhibit style: `<b>Exhibit A.</b>&nbsp;&nbsp;Description.`

---

## STEP 13 — FINAL BUILD CALL

```python
doc.build(story, onFirstPage=page_number_callback, onLaterPages=page_number_callback)
```

Callback skips page 1; numbers other pages centered at bottom.

---

## QUICK REFERENCE — WHAT NEVER APPEARS IN A COURT PDF

```
DRAFT notice of any kind
[VERIFIED]  [UNVERIFIED]  [CONFIRM]  [CHECK]
Any file path or filename
scrub_check.py / spell_check.py / any .py reference
Bold on dollar amounts inside paragraph body
Bold on dates inside paragraph body
Code blocks
Bracket-path exhibit references
Internal version notes
```

If unsure: it does not belong. Strip it.

---

_Companion doctrine to CLAUDE.md (markdown source) and TRIAL-PACKET-PDF-SPEC.md (personal binder PDFs)._
