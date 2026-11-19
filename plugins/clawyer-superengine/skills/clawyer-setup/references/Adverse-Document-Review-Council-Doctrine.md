# Adverse-Document Review Council (ADRC) — 15-Agent QA-Debug Swarm

> Always-on firm capability. Auto-fires whenever the litigant uploads, pastes, photographs, or points to ANY document that came from the OTHER side — the opposing party, opposing counsel, the court (judge / clerk / court administrator), or a guardian ad litem / custody evaluator / neutral. The litigant never has to ask. The Chief of Staff owns the trigger and the triage.

## Why it exists
Opposing filings and court paper are crafted documents. One reader misses things — a buried contradiction, a reversed case cited as good law, a quiet math change, a clause that says more than the judge ruled, a right silently dropped, a deadline trap. A swarm of single-purpose reviewers does not. Treat the audit like a QA debug swarm: each agent is a linter checking one class of defect, and no agent passes silently.

## Step 0 — make it readable (always first)
Convert the upload to clean markdown (the firm's Markdown Maker / `to_markdown.py`; OCR for scanned PDFs) before any agent runs. You cannot audit what you cannot read.

## The 15 agents (each a single-purpose linter; each returns CLEAN + a coverage line, or findings)
- **A1 Ruling-Match** — order / proposed-order / judgment clauses vs. the actual ruling (the source of truth: the transcript, the adopted recommendation, the read-in agreement). FAILS on any clause that says more, less, or other than what was ruled.
- **A2 Internal-Consistency** — the document vs. itself: recital vs. decretal, paragraph vs. paragraph, defined-term drift, internal number/date conflicts.
- **A3 Record-Contradiction** — statements that contradict the existing record, prior orders, or the party's own prior sworn positions.
- **A4 Citation/Authority** — every legal cite: does it exist, is the name / reporter / year right, is it still good law (not reversed), does it hold what it is cited for.
- **A5 Math/Money** — every number, fee, split, percentage, and date computation; does each compute and match the source figure.
- **A6 Procedure/Service** — rule compliance: approval-as-to-form, ex parte limits, service, signature, notice, sealed-document handling, filing deadlines.
- **A7 Scope/Authority-Creep** — any clause claiming more authority or relief than was granted or pled (unlimited where it should be scoped; a temporary order deciding final-trial issues).
- **A8 Mischaracterization** — misstated facts, testimony, or record; false attributions; mislabels.
- **A9 Omission/Silent-Drop** — what should be there but is missing: a right or provision carried in a prior order that was quietly dropped; selective quotation; missing pages.
- **A10 Deadline/Clock** — every date that starts a clock or imposes an obligation on the litigant; compute each calendar deadline; route to the calendar.
- **A11 Manipulation/Tone** — DARVO, subject-changing, vague accusations, loaded framing, baiting (for messages and narrative); one-sided or asymmetric obligations (for a drafted order).
- **A12 Admissibility** — reliance on inadmissible material: un-cross-examined GAL / evaluator hearsay, un-authenticated exhibits, sealed-material exposure, opinion beyond competence.
- **A13 Mistake & Self-Defeating-Error** — plain errors anywhere, INCLUDING the other side's own mistakes the litigant can exploit (wrong dates, typos, broken cross-references, self-defeating admissions). Tag each HURTS-US / HELPS-US.
- **A14 Trap & Poison-Pill** — clauses engineered as traps: impossible-to-comply terms (a contempt trap, e.g. a device required to be worn "at all times," a payment due in an impossibly short window), buried waivers / concessions / releases, a false "agreed" label, broad catch-alls, one-way obligations dressed as mutual.
- **A15 Adversarial Red-Team / Dirty-Tricks** — the meta catch-all: model an aggressive, dishonest opposing counsel and ask "what is the trick here?" Buried changes between versions, over-drafting past the ruling, routing around a self-represented opponent, scope quietly broadened, rights quietly dropped, "errors" that all run one way.

## QA-debug-swarm mechanics
- **Severity:** P0 critical (a fabricated or reversed cite, a sealed breach, a deadline that could forfeit a right, a clause contradicting the ruling on a core issue) · P1 high · P2 medium · P3 cosmetic.
- **Finding format:** `[A#] SEVERITY | location | what is wrong | evidence (record / rule cite) | recommended action | route-to`.
- **No silent pass:** an agent with nothing to report returns `CLEAN — <coverage line>`.
- **Regression mode:** on any new version of the same document, re-run and diff against the prior findings, so a fixed problem cannot silently reappear and a newly slipped change is caught.
- **Dispatch:** the Chief dispatches the agents as parallel sub-agents (one lens each); sequential in-thread where parallel dispatch is unavailable; the safety, deadline (A10), and citation (A4) lenses run first.

## Chief of Staff — triage lead
Dedup overlapping findings, rank by severity, route each to the owning specialist, write the consolidated report to `outputs/working/forensic/Adverse-Doc-Review_<source>_<doc>_<date>.md`, calendar every deadline, and run the coverage audit (all 15 reported).

## Outbound / Own-Work Self-Audit Mode (belt and suspenders)
The same council also runs against the firm's OWN substantive work product — every motion, declaration, proposed order, discovery set, packet, and outbound message — BEFORE it ships, as a final gate on top of the Roundtable Protocol. The lenses re-point at the litigant's own draft (verify our cites, our math, our deadlines; catch traps we wrote against ourselves; A15 red-teams our draft as opposing counsel would attack it). Ship is blocked until P0 / P1 self-audit findings are cleared. Fires at the "ready to ship" gate, not on every intermediate edit.

## Standing instruction
The litigant never asks for the review. The moment a document from the other side lands, the Chief converts it and fires all 15. When the source is ambiguous, fire it anyway.

---
_Added v1.6.0 — case-agnostic. Companion to the Chief-Authority, Format-Compliance, and Citation-Discipline / Hallucination-Audit doctrines and to the Roundtable Protocol._
