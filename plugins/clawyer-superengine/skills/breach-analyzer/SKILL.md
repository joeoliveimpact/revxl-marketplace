---
name: breach-analyzer
description: Map a matter's evidence to the governing contract — find where the counterparty (or we) breached or underperformed, tie each to a specific clause, and quantify the effect on money owed. Use for "analyze breaches", "did they breach", "build the defense file", "what clauses did they violate", or to populate a matter's breach-and-performance-log. Built for money disputes where performance is the leverage.
---

# breach-analyzer

Turn raw evidence into a clause-by-clause breach record that shrinks (or defends) the amount in dispute.

## When to use
A matter has a contract + some evidence, and you need to know: who failed to do what, which clause it violates, and what that does to the money. Especially: defending a payment demand by showing the counterparty didn't fully earn it.

## Which side are you on
Read `matter.md` for our role first. **Answering a demand:** the lever is what the other side did not fully earn. **Making the demand (we are owed):** the same clause map runs the other way: prove each thing we delivered, show the payment term that was missed, and find our own gaps before they do. Report a provable amount owed, not the invoice total.

## Ground rules
- **Real facts only.** Only log breaches supported by evidence in the matter. Never invent a breach to dodge an acknowledged debt — bad-faith fabrication backfires and can look like fraud. Flag weak/unsupported items as "needs evidence", don't assert them.
- **Answer straight.** Give the number and the position you actually believe the evidence supports, with the confidence level and what would move it. Do not hedge a weak breach into sounding strong, or a strong one into sounding uncertain.
- Cite the **evidence file + the contract clause** for every finding.

## Steps

1. **Load the governing contract** from the matter's `evidence/` (the `.md` conversion). Extract the obligations: deliverables, KPIs/SLAs, deadlines, payment terms, conduct/compliance duties, termination + cure mechanics, governing law.

2. **Inventory the evidence.** Read everything else in `evidence/` (messages, reports, CRM exports, payment records). Build a quick picture of what actually happened vs. what was promised.

3. **Map breaches to clauses.** For each failure:
   - What was required (quote the clause / KPI)
   - What actually happened (cite evidence)
   - Materiality (minor / material) and whether a cure notice was given (if the contract requires one)
   Distinguish **our** obligations from **theirs** — surface our exposure too, honestly.

4. **Quantify.** Translate performance gaps into money: which months/services were not fully earned, what that does to the claimed balance, any offset/counterclaim. Where a statute adds a multiplier (for example a freelancer-payment law that doubles the unpaid amount; confirm the person's state has one, `CONFIRM-BEFORE-CITING`), it applies only to what was **genuinely earned and unpaid**, so reducing "earned" is the lever.

5. **Write it up** in the matter's `breach-and-performance-log.md` (KPI failures, other breaches, cure-notice trail, net-effect theory). Keep the "real vs. needs-evidence" split explicit.

6. **Report** the bottom line: strongest breaches, the defensible true-owed number, weakest spots, and what evidence would strengthen the file.

## Definition of Done
`breach-and-performance-log.md` populated with evidence-cited, clause-tied findings; a quantified true-owed estimate; honest note of our own exposure; list of evidence gaps.

## Failure report (offer after any failure you can't fix in two tries)

Tell the client what went wrong in plain words, and whether anything was charged or changed. Then offer:
"Want me to send Joe a short report so he can fix it? You'll see exactly what's in it first."

1. With the Write tool, put the details in `.clawyer/reports/report-body.md`: what the client asked for, the step
   that failed, the command shape, and the error output. Never a key, and never the client's own content
   (their notes, contacts, messages, file text). This is a legal matter, so also never a party's name, a case
   number, a date from the case, an amount, or a single word from any document.
2. Draft it. Keep the summary short. Put the summary, step and error line in single quotes, drop any
   apostrophe from them, and use no script names:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" draft --plugin clawyer-superengine --plugin-version 0.1.0 --skill breach-analyzer --step '<step>' --error-line '<the error line>' --summary '<headline>' --body-file .clawyer/reports/report-body.md`

3. Show the client the exact preview it prints (between the PREVIEW lines) and ask: "Send this to Joe, or skip?"
4. Send, using the path after `DRAFT:`:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" send "<draft path>"`

`SENT` means Joe has it. `SAVED LOCALLY: <path>` means it couldn't be sent; tell the client where the file is
so they can email it to Joe. Skip instead:

`python "${CLAUDE_PLUGIN_ROOT}/scripts/report_to_joe.py" skip "<draft path>"`
