---
name: matter-intake
description: Start a new legal matter in this workspace. Use when a new dispute, contract review, agreement, or engagement comes in — "open a matter", "new case", "intake this", or when a document arrives that kicks off work. Copies the matter template, interviews for the key facts, and fills matter.md + chronology.md.
---

# matter-intake

Stand up a new matter under `matters/` with everything wired so work can start immediately.

## When to use
A new dispute/engagement/review arrives, or the user says "open/start a matter", "new case", "intake this". If a document (PDF, Google Doc) came in, run `evidence-intake` on it first (or alongside) so the contract/letter is already in `evidence/`.

## Ground rules
- Ask before assuming on ambiguous facts. Don't over-build.
- **Sensitive facts → `matter.md`, never a task tracker.** A tracker gets the task and the matter folder name only.
- Dates **MM.DD.YY** everywhere. Jurisdiction baseline is the `jurisdiction` block in `firm.config.json` unless the matter says otherwise.

## Steps

**The first matter already has a folder.** Setup created `matters/<slug>/` (see `paths.matter_home` in `firm.config.json`) with blank templates. For that matter skip step 2 and fill the files in. Also copy the basics you learn into `case-profile.md`: `matter.md` is the working record, `case-profile.md` is the short summary every session loads.

1. **Name the matter.** Short kebab slug for the folder (e.g. `acme-unpaid-invoice`, `maple-street-lease`). Confirm with the user if unclear.

2. **Create the folder.** If `firm.config.json` is missing, run the `clawyer-setup` skill first. Otherwise run this yourself from the workspace root (the person never types it):

   `python "${CLAUDE_PLUGIN_ROOT}/scripts/clawyer_init.py" add-matter --name "<matter name>"`

   It copies the matter template into `matters/<slug>/` and never overwrites an existing folder.

3. **Interview — only what's needed** (cluster 1-3 questions/turn, don't dump all at once):
   - Type (money dispute defense/offense · contract review · NDA · privacy/T&C · vendor · other)
   - Our role (claimant / respondent / reviewer / drafter)
   - Counterparty (name, entity, contact)
   - Amount at stake, key deadlines
   - One-sentence goal / Definition of Done
   - Anything already promised or sent (admissions, payments) — flag these as exposure
   If the user dropped a document, pull as much as possible FROM it first and only ask for gaps.

4. **Fill `matter.md`** — Snapshot, Parties, Goal/DoD, Deadlines, Facts, Legal Basis/Flags, Open Questions. Note any admissions or approval-gate items. Surface obvious legal flags (e.g. a freelancer-payment law in the person's state, a statute of limitations, signature gaps), each tagged `CONFIRM-BEFORE-CITING` until checked.

5. **Seed `chronology.md`** with the events known so far (contract date, demand date, payments), each citing its evidence file.

6. **Task tracker, only if the person already uses one.** Add one item: title = matter + posture, no facts and no names beyond the matter name. Put its id in `matter.md`.

7. **Report**: folder path, the top 2-3 next actions, and anything that needs a licensed attorney.

## Definition of Done
Matter folder exists and is filled, chronology seeded, next actions surfaced.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `.clawyer/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text). This is a legal matter, so also never a party's name, a case
   number, a date from the case, an amount, or a single word from any document.
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin clawyer-superengine --plugin-version 0.1.1 --skill matter-intake --step '<step>' --error-line '<the error line>' --summary '<headline>' --body-file .clawyer/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
