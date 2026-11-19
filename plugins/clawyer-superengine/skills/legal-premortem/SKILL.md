---
name: legal-premortem
description: Red-team a legal move, document, or strategy before it leaves the workspace. Assume it already failed, then work backwards to find why. Use before sending a demand letter, filing anything, signing or countersigning, making a settlement offer, responding to opposing counsel, or committing to a legal approach — and any time the user says "premortem this", "poke holes", "what breaks", "red-team this", "how would they attack this", "should we actually do this". Produces P0–P3 findings with fixes; P0/P1 block the send.
---

# legal-premortem

Assume it is six months from now and this **failed** — the letter provoked a lawsuit, the motion got denied, the clause got construed against us, the strategy cost more than it recovered. Work backwards and find why, while it is still cheap to change.

> **Give a straight answer.** This is a working tool for the person running the matter, not a memo for someone else to review. Hedging is the failure mode: "consult an attorney" in place of an actual finding is a non-answer and wastes the run. Commit to a verdict, state the reasoning, name the confidence level, and be specific about what would change your mind. Where the law is genuinely unsettled or the outcome turns on discretion, say *that* precisely — which way it usually breaks, and what moves the odds — instead of retreating to a disclaimer.

## Pick the mode

| Mode | Fires when | Core question |
|---|---|---|
| **ACTION** | About to *do* something — send a demand, file, serve, sue, settle, terminate, report | What does this provoke, and can we live with it? |
| **DOCUMENT** | A draft exists — letter, motion, contract, policy, response | How does this read in hostile hands? |
| **APPROACH** | Choosing a strategy, before drafting | Is this the right fight, on the right ground, at the right time? |

More than one can apply. Run each that does.

## Ground rules

- **Real facts only.** Test the position we actually have, not the one we wish we had. If a finding depends on a fact not in the matter's `evidence/`, say so and mark it unproven. Never paper over a bad fact — that is what the other side is looking for.
- **Bad news early and blunt.** If the position is weak, the move is wrong, or the draft should not go out, say it in the first line. Softening it costs the user the one thing this skill exists to give them.
- **Verify, don't assume.** Cheap-to-check claims get checked: read the actual clause, the actual evidence file, the actual filing deadline. A premortem built on the draft's own assumptions is theater.
- **Cite or tag every legal proposition.** Each authority carries one of:
  - `VERIFIED-with-source` — read from primary source, cited
  - `CONFIRM-BEFORE-CITING` — believed correct, not yet source-checked
  - `UNVERIFIED-DO-NOT-FILE` — recalled from memory only
  **Untagged legal propositions do not ship.** If you cannot verify, use `legal-researcher` or NotebookLM before asserting.
- **Never counsel waiving a right** to make a document simpler or a negotiation smoother. Flag the waiver; let the user decide.
- **Argue the other side honestly.** The point is to lose here so we do not lose later.

## The hunt list

Work the ones that apply. Do not pad.

### Procedural / threshold — usually the fatal ones
- **Deadlines and clocks.** Statute of limitations, notice periods, response windows, cure periods. What date does this start, and did we already miss one?
- **Forum, jurisdiction, venue.** Right court, right county, correct amount-in-controversy tier. (Baseline: the `jurisdiction` block in `firm.config.json` — narrow per matter.)
- **Standing and capacity.** Right party suing, right party being sued, correct entity name.
- **Conditions precedent.** Did the contract require notice-and-cure, mediation, or a demand before this step? Skipping one is a free dismissal for them.
- **Service and form.** Method, timing, proof, required attachments, signature blocks, certificate of service.

### Blowback
- **What does this provoke?** Counterclaim, cross-motion, fee-shifting, sanctions, bar complaint, regulatory referral, retaliation against a third party.
- **Fee-shifting exposure.** Does any statute or clause here shift fees to the loser? That can invert the economics of a small claim entirely.
- **Cost vs. recovery.** Model the realistic win and subtract what getting there costs — time, money, filing fees, attention. A won case that costs more than it returns is a loss.
- **Escalation ratchet.** Does this foreclose a cheaper path we still want? Once a demand goes out, some doors close.

### The document read in hostile hands
- **Admissions.** Does this concede a fact, a debt, a duty, or a defect? Read every sentence as if it will be read aloud back to us.
- **Waiver.** Rights given up, deadlines accepted, positions abandoned by silence.
- **Ambiguity.** Any term two readers could read two ways gets construed against the drafter. Find those.
- **Defined-term drift.** A term defined in §1 and used loosely in §7.
- **Tone.** Anger, sarcasm, threats, or overclaiming — all of it becomes an exhibit. Would we want a judge reading this?
- **Overclaim.** The precise claim beats the broad one. A single overstatement discredits the accurate items around it.

### The position itself
- **The best version of their argument.** Write it out. If it is stronger than expected, that is the finding.
- **Our worst fact.** Name it. What do they do with it, and what is our answer?
- **Credibility.** Anything here that contradicts something we said or wrote earlier? Check the matter's `chronology.md` and `contradiction-log.md`.
- **Proof gaps.** Every assertion — can we actually prove it, with what, and is it admissible?
- **How the decision-maker reads this.** Not how we read it. Judges see this pattern constantly; what does this look like as the hundredth version of it?

## Steps

1. **Restate the move in one sentence** — what is about to happen, and what irreversible thing it causes.
2. **Load the ground truth** — the matter's `matter.md`, `chronology.md`, the governing document, and the specific evidence the position rests on. Do not premortem from memory of the conversation.
3. **Run the hunt list** for the applicable mode(s), verifying as you go.
4. **Write the other side's response** — a short, genuine version of how a competent opponent attacks this.
5. **Report findings** (format below).
6. **Fix the draft against P0/P1 findings before presenting it**, then tell the user exactly what changed and why.

## Output format

Numbered findings, worst first:

```
### P0-1 — [one-line statement of the defect]
**Severity:** P0
**Mode:** ACTION | DOCUMENT | APPROACH
**What breaks:** the concrete failure — who does what, and what it costs us
**Evidence:** what was read or checked, and what it showed (file, clause, date)
**Fix:** the specific change
```

| Severity | Meaning | Gate |
|---|---|---|
| **P0** | Fatal — this move fails, or creates worse exposure than it cures | **Blocks send** |
| **P1** | Serious — materially weakens the position or hands them an opening | **Blocks send** |
| **P2** | Should fix — sloppiness a careful reader will exploit | Fix if time |
| **P3** | Note — worth knowing, not worth holding for | Log it |

Close with:
- **Verdict:** SEND / SEND AFTER FIXES / DO NOT SEND — pick one, no fence-sitting
- **What changed in the draft** as a result
- **What we are knowingly accepting** — residual risk the user is choosing to take
- **NEXT ACTION:** one line

## The gate

**Nothing leaves the workspace with an open P0 or P1.** That covers sending, filing, serving, signing, posting, and giving a document to anyone outside. The user can override — explicitly, in conversation, with the risk stated back to them — and that override gets logged in the matter.

Clean run with no P0/P1 still reports: say what was checked and what came back clean. **Silence is not a pass.** A premortem that finds nothing must show its work, or it did not run.

## Related

- `breach-analyzer` — establishes the underlying position this stress-tests
- `legal-researcher` (agent) — resolve `CONFIRM-BEFORE-CITING` tags before shipping
- `contract-reviewer` (agent) — clause-level review of an inbound document
- `matter-status` — current posture before choosing an approach
