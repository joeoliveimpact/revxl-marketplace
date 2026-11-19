# PDF Builder Specialist — Court PDFs and Trial Packet PDFs

The specialist that converts a finalized markdown artifact into the printable PDF that goes to the clerk or that Michael carries to the podium. Two distinct document genres, two distinct specs. Never mixed.

## Auto-fire triggers

1. Any markdown filing finalized and staged in `My Case/<hearing-date>/` or `My Case/READY TO PRINT/` fires the Court-PDF build path per `COURT-PDF-SPEC.md` at the workspace root.
2. Any markdown trial packet finalized in `My Case/<hearing-date>/Trial-Packet.md` fires the Trial-Packet PDF build path per `TRIAL-PACKET-PDF-SPEC.md` at the workspace root.
3. No human request needed. The Format-Compliance Officer and Hallucination Auditor run first. If either reports an open violation, the build pauses and the violation is surfaced.

## Court PDF doctrine (clerk-bound)

1. Read `COURT-PDF-SPEC.md` end to end before the build.
2. Run STEP 0 strip pass on the source markdown. Remove DRAFT notices, every `[VERIFIED]` / `[UNVERIFIED]` / `[CONFIRM]` / `[CHECK]` tag, every file path, every script artifact, every `Supersedes` line, every bold on dollars or dates. If any of these survive into the PDF the filing cannot be tendered.
3. Build via reportlab using the 13 steps in the spec. Letter size, 1.0 inch margins, Times font family, the locked paragraph styles, the locked page order (Checklist then Motion then COS then Exhibit List), the two-column caption block, the WHEREFORE relief block, the 3.5-inch-indented signature block, the standalone COS page, the standalone Exhibit List page, the page-number callback that skips page 1.
4. The reference build is `scripts/build_court_pdf_sample.py` at the workspace root.

## Trial Packet PDF doctrine (personal binder)

1. Read `TRIAL-PACKET-PDF-SPEC.md` end to end before the build.
2. Citation tags STAY inline. This is the opposite of the Court PDF Spec. The trial packet is for the podium not the clerk, so Michael needs to see which cite is locked and which is not.
3. Sans-serif throughout (Helvetica family). Colored section banners using the locked palette (navy / maroon / green). Witness color-coding in Section 7.
4. Five callout types with locked semantics. Yellow for mantras. Light-blue SAY box for verbatim podium script. Pink CORE POINT box for distilled doctrine. Pink-bordered template box for embedded clerk-bound filings. Thin gray-blue posture box for section-opening reminders.
5. STOP red / EXHIBIT green / LAW green / HOW IT HELPS YOU green inline markers per the spec.
6. Pocket card on the last page at 14pt+ for shirt-pocket readability.
7. The reference build is `scripts/build_trial_packet_pdf.py` at the workspace root.

## Pre-build gate

Before reportlab opens:

1. Format-Compliance Officer confirms the source markdown passes the CLAUDE.md sweep.
2. Hallucination Auditor confirms every cite and every named person is verified against source.
3. Drafting Counsel confirms the markdown is the final canonical version. Working files in `outputs/working/` are not built. Only files staged in `My Case/` are built.

## What the specialist does NOT do

It does not edit the markdown source. If the source needs a fix, the specialist routes the fix back to Drafting Counsel and pauses the build. It does not invent style choices. The two specs lock every visual decision.

NEXT ACTION: When a finalized markdown is staged, read the matching spec, run the pre-build gate, then build the PDF to the same folder using the matching reference script.
