---
name: evidence-intake
description: Ingest a document into a matter — convert it to Markdown, file it in the matter's evidence folder, and log it to the chronology. Use when a PDF, Google Doc, image, or export arrives for a case ("add this doc", "ingest this", "here's the contract/letter/statement"). Handles the PDF→Markdown pipeline and keeps the case record current.
---

# evidence-intake

Turn an incoming document into clean, indexed, logged evidence.

## When to use
A file or link arrives for a matter: contract, demand letter, invoice, bank statement, message export, screenshot. Also the entry point for "convert this PDF".

## Ground rules
- **Convert, don't retype.** Run the bundled converter yourself: `python "${CLAUDE_PLUGIN_ROOT}/skills/pro-se-firm/scripts/to_markdown.py" "<file>" "<output folder>"`. It tries MarkItDown first and falls back to OCR for scans.
- Keep the **original** for the record; store the `.md` next to it in the matter's `evidence/`.
- Filename: `[Topic] - [Type] - MM.DD.YY.md` (e.g. `Acme Demand Letter - 06.24.26.md`).
- **Verify** the conversion (spot-check tables/figures/long text) before relying on it — converter font warnings are harmless, but garbled tables and interleaved columns are not.
- Don't send anything outward (approval gate).

## Steps

1. **Identify the matter.** Confirm which `matters/<slug>/` this belongs to (or run `matter-intake` first if it's a brand-new matter).

2. **Convert by source type:**
   - **PDF / DOCX / PPTX / XLSX / image / HTML** → the bundled converter, with `matters/<slug>/evidence` as the output folder.
   - **Google Doc/Sheet/Slides** → ask the person to download it as Word, Excel or PDF, then convert that file.
   - **Audio/video** → the converter skips these. Ask for a transcript, or say plainly that transcription is not part of this version.
   - **Pasted text** → write straight to a `.md` in evidence/.

3. **Verify** the `.md`: open it, confirm the substance came through. Note any conversion gaps in the file header.

4. **Log to `chronology.md`** — add a dated row for what the document represents (e.g. "Demand letter received"), citing the evidence filename.

5. **Flag relevance:**
   - If it shows counterparty breach/underperformance → note it in `breach-and-performance-log.md` (or run `breach-analyzer`).
   - If it's a payment/invoice → note it in `payment-history.md`.
   - If it contains an **admission or approval-gate item** → call it out to the user.

6. **Report** — what was filed (path), what it is, and which logs you updated.

## Definition of Done
Original + verified `.md` in the matter's `evidence/`, chronology updated, relevance flagged, user told what landed.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `.clawyer/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text). This is a legal matter, so also never a party's name, a case
   number, a date from the case, an amount, or a single word from any document.
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin clawyer-superengine --plugin-version 0.1.2 --skill evidence-intake --step '<step>' --error-line '<the error line>' --summary '<headline>' --body-file .clawyer/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
