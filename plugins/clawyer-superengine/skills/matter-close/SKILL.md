---
name: matter-close
description: Close out a resolved matter — write the final summary, make sure sent documents are in filings-final, and set the matter status to closed. Use for "close the X matter", "this is settled/resolved/done", "wrap up the case". Leaves a clean, auditable record.
---

# matter-close

Cleanly retire a matter so the record is complete and auditable.

## When to use
A matter is settled, paid, signed, withdrawn, or otherwise done. The user says "close it", "this settled", "we're done with X".

## Ground rules
- **Confirm the outcome first** — don't close a matter on assumption. Get the resolution in one line from the user if it isn't obvious.
- **Nothing leaves the workspace** without an approval gate — closing is internal record-keeping.
- Preserve everything; closing means marking + summarizing, not deleting.

## Steps

1. **Confirm resolution** — what happened (paid in full / settled for $X / installment plan signed / withdrawn / lost), and the date (MM.DD.YY).

2. **Finalize documents.** Make sure anything actually sent/executed is in `filings-final/` (not just `filings-drafts/`). Note the final versions in `matter.md`.

3. **Write the closeout** in `matter.md`:
   - Outcome + date in the Decisions Log
   - Set **Status: closed (MM.DD.YY)**
   - A 3-5 line "how it resolved + lessons" summary (what worked, what to do differently next time)

4. **Update `chronology.md`** with the closing event.

5. **Close the task** in the person's tracker if they use one (the outcome in one line, no facts).

6. **Capture reusable lessons.** If the matter produced a reusable template (e.g. a good demand-response letter) or a non-obvious learning, suggest saving it to `output/`.

7. **Report** the closed status and where the final record lives.

## Definition of Done
Matter marked closed with outcome + summary, finals in `filings-final/`, any reusable lesson captured.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `.clawyer/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text). This is a legal matter, so also never a party's name, a case
   number, a date from the case, an amount, or a single word from any document.
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin clawyer-superengine --plugin-version 0.1.2 --skill matter-close --step '<step>' --error-line '<the error line>' --summary '<headline>' --body-file .clawyer/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
