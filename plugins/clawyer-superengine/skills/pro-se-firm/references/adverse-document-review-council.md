# Adverse-Document Review Council (ADRC)

> **Jurisdiction note (Clawyer):** this file was written for Mississippi family court. Outside Mississippi, or outside a family case, treat every rule number, case name, deadline, fee and form in it as an example of what to look up, not as your law. Family-law steps in it do not apply to other kinds of case. Confirm your own state's version first and tag anything unconfirmed `CONFIRM-BEFORE-CITING`.

> **A standing QA-debug swarm.** Every document that arrives from the OTHER side — the opposing party (the opposing party or their counsel), the Court (orders, judgments, notices, the Chancery Clerk, the Court Administrator), or the Guardian ad Litem (the GAL) — is run through a council of parallel review agents before the firm relies on it, responds to it, or lets the client act on it. Each agent is a single-purpose "linter" that checks the document for one class of defect. The Chief of Staff owns the trigger and the triage.
>
> **Why it exists (forensic standard):** opposing filings are crafted to mislead. The firm has already caught, by hand, a reversed case cited as good law (Crider COA opinion), a wrong party name, a fee math error ($3,460 vs the invoiced $3,440), an order that gave one parent "final authority over everything" when the GAL recommended medical and education only, a daily-call right silently dropped from a prior order, and a 10-day payment trap. One reader misses things. A swarm of single-purpose reviewers does not.
>
> **Lives in:** the mississippi skill references. Wired into `RULES.md` (Workspace Doctrine #7), `FIRM-PATHWAYS-MAP.md` (auto-fire block), `CASE-FILE-INDEX.md` (Roundtable panel), `MASTER-INDEX.md`.

## Auto-fire trigger (HARD RULE — no permission gate)

The council fires automatically the moment the client uploads, pastes, photographs, forwards, or points to ANY document that originates from:

- **The opposing party** — the opposing party or opposing counsel. Motions, responses, oppositions, proposed orders, redlines, discovery responses, 8.05 declarations, letters, emails, exhibits.
- **The Court** — the judge, the clerk of court, or the court administrator. Orders, temporary orders, judgments, notices, scheduling orders, docket entries.
- **The Guardian ad Litem** — the court-appointed GAL or evaluator. Reports, recommendations, supplements, invoices, correspondence.

the client never asks for the review. The Chief detects the source from what the client says, the filename, or the content, and fires the council. **When the source is ambiguous, fire it anyway** (catch-all). The review is not optional and it is not an offer.

## Step 0 — make it readable (always first)

A document cannot be audited from guesswork. Before the council runs, **Markdown Maker** converts the upload to clean markdown (`scripts/to_markdown.py`; OCR via `scripts/ocr_pdf.py` for scanned or image PDFs). The evidence trifecta applies: PDF copy into `evidence/<subfolder>/`, markdown beside it, and the document added to the relevant NotebookLM notebook.

## The council — 15 review agents (each a single-purpose linter)

Each agent runs independently and in parallel. Each returns either **CLEAN** (with a one-line coverage statement of what it read) or a list of **FINDINGS**. No agent passes silently. Like a test suite, every check reports its result.

**A1 — Ruling-Match Auditor** (Order Integrity Reviewer lens)
- For orders, proposed orders, judgments: compares the document clause by clause against the Source of Truth (the bench-ruling transcript, the adopted GAL recommendation, the read-in agreement).
- FAILS when a clause says more, less, or other than what was actually ruled. Classify each as expansion / addition / omission / alteration / catch-all creep.
- Evidence: verbatim Source-of-Truth quote with a pin cite next to the document's clause.
- Routes to: Order Integrity Reviewer → Order-Change-Ledger → Drafting Counsel.

**A2 — Internal-Consistency Auditor** (new lens)
- Document against itself. Recital vs decretal, paragraph vs paragraph, defined-term drift, "sole" vs "joint," numbers or dates that conflict inside the same document.
- FAILS when the document contradicts its own terms.
- Evidence: the two conflicting passages quoted side by side.
- Routes to: Drafting Counsel (objection / motion to amend).

**A3 — Record-Contradiction Auditor** (Credibility & Contradiction Analyst lens)
- Document against the EXISTING record. Prior orders, prior filings, transcripts, OFW, and the party's own prior sworn statements and 8.05s.
- FAILS when a statement contradicts the record or the party's prior position.
- Evidence: the record cite that contradicts it.
- Routes to: Contradiction-Impeachment-Log → Cross-Examination Builder.

**A4 — Citation & Authority Auditor** (Hallucination Auditor / Research Counsel lens)
- Every legal cite in the document. Does the case exist; is the name, reporter, and year right; is it still good law (not reversed); does it hold what it is cited for.
- FAILS on a fabricated, mis-cited, reversed, or mischaracterized authority. (This is the lens that catches a Crider-style reversed opinion or a Brooks-style wrong name.)
- Evidence: primary-source confirmation or the contradicting authority, with URL.
- Routes to: Research Counsel → Drafting Counsel (the counter-cite).

**A5 — Math & Money Auditor** (Forensic Financial Analyst lens)
- Every number. Fee totals, support math, equity splits, percentages, 8.05 figures, and date arithmetic.
- FAILS when a figure does not compute or contradicts a sworn or source figure.
- Evidence: the recomputation or the source figure.
- Routes to: Forensic Financial → Drafting Counsel.

**A6 — Procedure & Service Auditor** (Local-Procedure Clerk lens)
- Rule compliance. UCCR 5.03 approval-as-to-form, UCCR 3.08 ex parte, MRCP 5(b) service and acknowledgment, notice, Rule 81 summons, Rule 11 signature, sealed-document handling, filing deadlines.
- FAILS on a procedural defect the document commits, or a rule it gives the client grounds to raise.
- Evidence: the rule text (verified) + the defect.
- Routes to: Local-Procedure Clerk → Drafting Counsel.

**A7 — Scope & Authority-Creep Auditor** (Ambiguity Auditor + Order Integrity lens)
- Does the document claim more authority or relief than was granted or pled? Unlimited where it should be scoped (e.g., "final authority over everything"); relief beyond the pleadings; a temporary order deciding final-trial issues.
- FAILS when scope exceeds the grant, the pleadings, or the adopted recommendation.
- Evidence: the grant or pleading that bounds it.
- Routes to: Ambiguity Auditor → Drafting Counsel.

**A8 — Mischaracterization Auditor** (Records Analyst lens)
- Does it misstate facts, testimony, or the record? False attributions, spun summaries, mislabels (an Apple Watch called a "prescribed cardiac device"), inaccurate or selective quotes.
- FAILS on a factual assertion the record contradicts.
- Evidence: the accurate record quote.
- Routes to: Records Analyst → Cross-Examination Builder.

**A9 — Omission & Silent-Drop Auditor** (new lens — the "what's missing" linter)
- What should be there but is not? Rights or provisions dropped from a prior order (daily calls), omitted holiday consideration, selective quotation, missing pages or exhibits, conveniently absent context.
- FAILS on a material omission.
- Evidence: the prior order / record showing what was dropped.
- Routes to: Records Analyst → Drafting Counsel.

**A10 — Deadline & Clock Auditor** (Docket Watcher / Local-Procedure lens)
- Every date that starts or affects a clock or imposes an obligation on the client. Entry date → MRCP 59(e) / 52(b) / appeal clocks; response deadlines; compliance windows (e.g., a 10-day GAL-fee payment); Rule 81 return dates.
- FAILS when a deadline or obligation is present and not yet calendared.
- Evidence: the date in the document + the rule that runs from it.
- Routes to: Chief of Staff → CASE-CHECKLIST.md + calendar (every deadline gets an event).

**A11 — Manipulation & Tone Auditor** (Communication Command + Opposing-Party Communication Profile + High-Conflict Opponent Protocol lens)
- For messages, letters, and GAL narrative: DARVO (deny, attack, reverse victim and offender), subject-changing, vague accusations, partial "cooperative" non-answers, loaded framing, bait.
- FAILS on a manipulation tactic or an attempt to bait a reaction or mislead the reader. Separates argument from evidence.
- Evidence: the tactic named (never diagnose the person) + the passage.
- Routes to: Communication Command → Opposing-Party-Communication-Profile; do-not-take-the-bait note.

**A12 — Admissibility & Evidence Auditor** (Evidence Specialist + GAL Impeachment lens)
- Does the document rely on inadmissible material? GAL hearsay (McDonald), un-authenticated exhibits, sealed-material exposure, expert opinion beyond competence, best-evidence problems.
- FAILS on reliance on inadmissible or excludable material.
- Evidence: the evidence rule + the offending reliance.
- Routes to: Evidence Specialist / GAL Impeachment → Drafting Counsel (objection / motion to exclude).

**A13 — Mistake & Self-Defeating-Error Auditor** (Records Analyst + Credibility lens)
- Sweeps for plain errors anywhere in the document, including the other side's OWN mistakes the firm can exploit: wrong dates, mislabeled exhibits, citation typos, broken cross-references, undefined terms, gaps, and self-defeating admissions (a sentence in their filing that actually helps the client).
- FAILS on any error. Tags each HURTS-US (fix or object) or HELPS-US (preserve and exploit).
- Evidence: the error + the correct value, or the helpful admission quoted verbatim.
- Routes to: Drafting Counsel (build on a helpful admission) or the relevant lens owner (cure one that hurts).

**A14 — Trap & Poison-Pill Auditor** (the "what will this clause do to me later" linter)
- Hunts clauses engineered as traps: impossible-to-comply terms (a contempt trap, e.g. "worn at all times," "$1,720 within 10 days"); buried waivers, concessions, or releases; a false "agreed" label on something never agreed; broad catch-all language that sweeps in more than was intended; language that forecloses a future argument or locks in a bad position; a one-way obligation dressed as mutual.
- FAILS when a clause is built to make the client fail, waive, or concede later.
- Evidence: the trap mechanism spelled out (how it triggers contempt, waiver, or estoppel) + the neutralizing fix.
- Routes to: Drafting Counsel (strike or neutralize) + Ambiguity Auditor.

**A15 — Adversarial Red-Team / Dirty-Tricks Auditor** (High-Conflict Opponent Protocol lens — the meta catch-all)
- Models an aggressive, dishonest opposing counsel's full playbook and asks the question the other lenses do not: "what is the trick here?" Buried changes between versions, sandbagging, strategic ambiguity, mislabeling, ex parte routing, a selective or doctored record, gotcha service timing, overstating the ruling, slipping in relief that was denied, exploiting a pro se litigant's unfamiliarity with procedure.
- FAILS on any tactic, trick, or sharp practice, stated plainly as "here is what they are trying to pull."
- Evidence: the tactic named + how it would work if unchallenged.
- Routes to: Lead Trial Counsel + Response Arsenal + Chief of Staff (pattern flag → chancellor on a third occurrence).

## QA-debug-swarm mechanics

**Severity (bug-tracker scale).** Every finding carries one:
- **P0 / CRITICAL** — a fabricated or reversed cite, a sealed-document breach, a deadline that could forfeit a right, an order clause that contradicts the ruling on a core issue.
- **P1 / HIGH** — a material contradiction, scope-creep, a money math error, a mischaracterization of testimony.
- **P2 / MEDIUM** — an internal inconsistency, a material omission, an ambiguity, a manipulation tactic.
- **P3 / LOW** — cosmetic or harmless.

**Finding-report format (every agent, every finding):**
`[A#] FINDING n | SEVERITY | LOCATION (page / ¶) | WHAT IS WRONG | EVIDENCE (record or rule cite) | RECOMMENDED ACTION | ROUTE-TO`

**No silent pass.** An agent with nothing to report returns `[A#] CLEAN — read <what>, no findings.` so coverage is provable.

**Regression mode (re-run on every new version).** When a new version of the same document arrives (a redline, an amended order, a supplemented report), the council RE-RUNS and diffs against the prior version AND the prior findings, so a fixed problem cannot silently reappear and a newly slipped change is caught. This ties to the Order-Change-Ledger.

**Dispatch model.** Default: the Chief dispatches the 15 agents as parallel background sub-agents (Agent tool), one lens each, then assembles. For a large or complex document, a Workflow may run the swarm if the client opts into orchestration. Graceful degradation (Claude.ai or no parallel dispatch): run the 12 lenses in-thread, sequentially, same output. Safety and deadline lenses (A6, A10) and the citation lens (A4) run first so nothing time-sensitive waits.

## Chief of Staff — triage lead

After the agents report, the Chief:
1. **Dedups** overlapping findings (the same defect caught by two lenses becomes one ranked finding).
2. **Ranks** by severity (P0 first).
3. **Routes** each confirmed finding to the owning specialist per the agent's ROUTE-TO.
4. **Writes** the consolidated report to `outputs/working/forensic/Adverse-Doc-Review_<source>_<doc>_<date>.md`.
5. **Pushes** findings to the matching notebook: Opposing-Counsel Order-Integrity Patterns, GAL/Evaluator File, or Opposing-Party Sworn Inconsistencies.
6. **Updates** `CASE-CHECKLIST.md` and puts every A10 deadline on the calendar.
7. **Runs the auto-trigger audit** — confirms every one of the 15 agents actually fired and reported; re-fires any that did not.

## Consolidated report format

```
ADVERSE-DOC REVIEW — <doc title>
Source: <opposing party / court / GAL>   Received: <date>   Version: <n>
Coverage: 15/15 agents reported.

P0 / CRITICAL
  1. [A4] ...
P1 / HIGH
  ...
P2 / MEDIUM
  ...
CLEAN lenses: A2, A11 (coverage lines)

TOP 3 MOVES (Chief): 1) ... 2) ... 3) ...
Routed to: <specialists>.   Deadlines added: <dates>.
```

## Outbound / Own-Work Self-Audit Mode (belt and suspenders)

The same council also runs against the firm's OWN substantive work product before it ships — every motion, declaration, proposed order, discovery set, hearing packet, and outbound message — as a final gate on top of the Roundtable Protocol. The Roundtable is the belt; this self-audit is the suspenders.

In Outbound Mode the 15 lenses re-point at our own draft:
- A1 — does the draft do what we intend and match the record / ruling we are invoking?
- A2 / A5 / A13 — our own internal contradictions, math errors, typos, broken cross-references, wrong dates.
- A4 — every cite we make is [VERIFIED] to primary source (this is the Brooks-v-Roberts and Crider-reversed catch).
- A6 / A10 — our own procedure, service, signature, and every deadline we are subject to.
- A14 — did WE write a trap against ourselves: a self-defeating admission, an accidental waiver, an over-broad concession, an impossible commitment.
- A7 / A8 / A9 — did we overreach, misstate the record, or omit something we needed.
- A11 — does it read like a prepared human and stay court-safe (no AI tells, no bait, no improper ex parte).
- A15 — RED-TEAM OUR OWN DRAFT as opposing counsel would attack it: find their opposition and close it before she files it.

Trigger: fires when the firm finalizes a substantive artifact and BEFORE it is printed, filed, served, or sent — not on every intermediate edit. Findings route the same way (Chief triages, ranks, routes to the owning specialist) and **ship is blocked until P0 and P1 findings are cleared.** The self-audit is appended to the artifact's Panel Review block. Net effect: the firm reviews the other side's paper AND its own with the same 15-lens rigor.

## NEXT ACTION

On the next opposing-party / court / GAL document the client uploads, convert it to markdown, fire all 15 agents, and deliver the consolidated review report with a ranked findings list and the top 3 moves.
