---
name: custody-premortem
description: Red-team a custody move, filing, message, or strategy before it leaves the workspace. Assume it already failed and work backwards. Use before filing or responding to a custody/visitation petition, sending any message to the other parent or the Attorney for the Child, making an enforcement or modification move, calling CPS, submitting evidence about the other parent, or committing to a custody strategy — and any time the user says "premortem this", "how would they attack this", "should I file this", "should I send this", "red-team my custody plan". Produces P0–P3 findings; P0/P1 block the send. NY / Family Court baseline.
---

# custody-premortem

Assume it is the day after the hearing and **we lost ground** — the petition survived, the judge read us as the high-conflict parent, our own message became their best exhibit, the Attorney for the Child sided against us. Work backwards and find why, while it is still free to change.

> **Give a straight answer.** This is a working tool for the person litigating this case, not a memo for someone else to review. Hedging is the failure mode: "consult an attorney" in place of an actual finding is a non-answer and wastes the run. Commit to a verdict, state the reasoning, name the confidence level, and be specific about what would change your mind. Where the law is genuinely unsettled or the outcome turns on a judge's discretion, say *that* precisely — which way it usually breaks, and what moves the odds — instead of retreating to a disclaimer.

## The standard everything is measured against

**The child's best interests.** Not fairness to a parent, not who is right, not who has suffered more. Every finding below is scored against what a Family Court judge, applying that standard, does with it.

Two consequences that drive most of the findings in this skill:

1. **Winning behavior and sympathetic behavior are the same behavior.** The calm, documenting, relationship-fostering parent wins on the merits *and* looks like the better parent. There is rarely a tradeoff to manage.
2. **A parent who looks like they are litigating against the other parent rather than for the child loses altitude fast** — even when their facts are good.

## Safety overrides tactics

If a child faces genuine, present danger, that is not a strategic question and this skill does not treat it as one. Say so plainly and act on it. Everything below assumes we are past that question.

Conversely: **a report made because it is tactically useful is the single most destructive thing available here.** If a CPS call, an emergency application, or a safety allegation is being considered and the honest answer to "would we do this if it gained us nothing?" is no — that is a P0 finding, full stop.

## Ground rules

- **Real facts only.** Test the case we have. A manufactured or inflated narrative about the other parent is the fastest way to lose custody we currently hold — courts see it constantly and punish it. Mark anything unproven as unproven.
- **Our conduct gets the same scrutiny as theirs.** Run every lens against us first. Whatever we find, they will find.
- **Tag every legal proposition:** `VERIFIED-with-source` / `CONFIRM-BEFORE-CITING` / `UNVERIFIED-DO-NOT-FILE`. Untagged does not ship. Resolve via `legal-researcher` or the person's research notebook before asserting.
- **Never counsel waiving a right** — including parenting time — to reduce conflict. Flag it; the user decides.
- **The child is never an instrument.** No coaching, no interviewing, no using the child as messenger, courier, or witness. Any finding that depends on doing so is dead on arrival.

## The hunt list

### A. Threshold — is this move even available?
- **Modification requires a change in circumstances** since the existing order, material enough to warrant revisiting best interests. `CONFIRM-BEFORE-CITING`. What specifically changed, when, and can we prove the date?
- **Are they meeting that threshold, or just re-litigating?** If their petition is a rerun of facts already decided, that is a threshold defense — and a much cheaper win than a full best-interests trial.
- **Right vehicle.** Modification vs. enforcement vs. violation petition vs. emergency application — these are different filings with different standards. Using the wrong one wastes the move and signals inexperience.
- **Forum and posture.** The family court for the county in `firm.config.json`, unless a higher court's action controls. `CONFIRM-BEFORE-CITING`. Which court holds the existing order?
- **Deadlines.** Response windows, appearance dates, service requirements, any court-ordered deadline already running.

### B. The status quo — usually our strongest asset and our biggest blind spot
- **We currently hold custody. That is the thing to protect.** Any move that destabilizes a working arrangement invites the court to re-examine all of it. Ask directly: does this filing open a door we would rather keep shut?
- **Are we the moving party without needing to be?** Defending an existing order is a stronger posture than seeking to change one. If we are about to go on offense, justify why.
- **Delay analysis.** Time entrenches the status quo. Does moving fast help us, or does it help them?

### C. Willingness to foster the other parent's relationship — the factor that quietly decides cases
- **Gatekeeping.** Every denied visit, late exchange, unanswered request, unilateral schedule change, or "he didn't want to go." Each one is an exhibit against us, and this factor is weighed heavily. `CONFIRM-BEFORE-CITING` for your state's articulation.
- **Communication record.** Read our last 20 messages to the other parent as the judge will. Terse is fine. Cold is fine. Sarcastic, accusatory, or point-scoring is not.
- **Disparagement.** Anything said about the other parent within the child's hearing, or posted anywhere, or repeated by the child.
- **Are we doing the thing we are accusing them of?** Run this honestly. It is the most common own-goal in custody.

### D. Substance-abuse allegations — proof, staleness, and proportion
- **What is actually provable, and how recent?** Old conduct carries less weight than current capacity. A judge asks "what is true now."
- **Admissibility.** Hearsay, un-authenticated screenshots, third-party accounts, medical or treatment records that need a release or subpoena. What survives an objection?
- **Recovery cuts against us.** Documented treatment, testing, or sustained sobriety is legally meaningful and courts credit it. If they have it, our framing must account for it or we look like we are punishing recovery.
- **Proportion.** Are we asking for relief proportionate to the risk? Overreaching — seeking total cutoff where supervised or conditioned time fits the facts — reads as vindictive and costs credibility on the facts that *are* good.
- **Testing and conditions.** Is there a graduated remedy (testing, supervised exchange, conditioned parenting time) that gets the child protected without asking the court for something it will not grant?
- **Our own exposure.** Alcohol, cannabis, prescriptions, anything on our side that a symmetrical inquiry would surface.

### E. The Attorney for the Child, evaluators, and neutrals
- **Some states (New York is one) appoint an Attorney for the Child** — the child's lawyer, advocating the child's position, not a best-interests guardian in the Mississippi GAL sense. `CONFIRM-BEFORE-CITING`. **Do not import GAL assumptions from other jurisdictions.**
- **How does this move look to the AFC?** They talk to the child and they talk to the judge. Antagonizing them is expensive.
- **Forensic evaluation.** Is this move likely to trigger one? Do we want one? Evaluations are slow, expensive, intrusive, and unpredictable.
- **Anything we say to a neutral is going in a report.** Including the tone of it.

### F. Our own record, read hostile
- **Messages, email, social media, the parenting app.** Assume every one is an exhibit. Anything written in anger?
- **Recordings.** Legality first (`CONFIRM-BEFORE-CITING` on your state's consent rules), then wisdom — recording a child, or a conversation *with* the child in it, reads badly regardless of legality.
- **New partners, cohabitation, household composition, moves, schooling, medical decisions** — anything they can frame as instability.
- **Missed exchanges, missed appointments, missed school events** on our side.
- **Prior inconsistent statements.** Check `chronology.md` and `contradiction-log.md` before asserting anything.

### G. Blowback and economics
- **What does this provoke?** Cross-petition, modification request against us, enforcement, counter-allegations, an AFC position against us, a referral.
- **Fee exposure.** Can they seek counsel fees, and does anything here support a bad-faith finding against us? `CONFIRM-BEFORE-CITING`.
- **Cost vs. gain.** Model the realistic best outcome and subtract what reaching it costs — money, months, the child's stability, and our own capacity to keep functioning.
- **Escalation ratchet.** Does this close a settlement path we still want? Most custody matters resolve; a scorched filing can cost the stipulation that was available.

### H. How the judge reads it
- Write the two-sentence version a judge forms after reading our filing. If it is "here are two parents who cannot stop fighting," the filing has failed regardless of its contents.
- **The precise claim beats the broad one.** One overstatement discredits the accurate allegations sitting next to it.
- Would we want this read aloud, with the child old enough to hear it?

## Steps

1. **Restate the move in one sentence** and name the irreversible thing it causes.
2. **Load ground truth** — the existing order, `matter.md`, `chronology.md`, the specific evidence the position rests on, and the actual message thread if a message is in scope. Never premortem from memory of the conversation.
3. **Run our own conduct through C, D, F first.** Ours before theirs, always.
4. **Run the remaining lenses** that apply, verifying as you go.
5. **Write their best response** — a genuine version of how competent opposing counsel attacks this, plus the AFC's likely position.
6. **Report** (format below), then **fix P0/P1 before presenting**, and say what changed.

## Output format

```
### P0-1 — [one-line statement of the defect]
**Severity:** P0
**Lens:** A–H
**What breaks:** the concrete failure — what the court, the AFC, or the other side does with this
**Evidence:** what was read or checked (file, order paragraph, message date)
**Fix:** the specific change
```

| Severity | Meaning | Gate |
|---|---|---|
| **P0** | Fatal — risks the custody we hold, or is a move a judge punishes | **Blocks send** |
| **P1** | Serious — materially weakens us or hands them the better story | **Blocks send** |
| **P2** | Should fix — a careful opponent exploits it | Fix if time |
| **P3** | Note | Log it |

Close with:
- **Verdict:** SEND / SEND AFTER FIXES / DO NOT SEND — pick one, no fence-sitting
- **How this reads to the judge** — two sentences
- **How this reads to the Attorney for the Child** — one sentence
- **What we are knowingly accepting** — residual risk the user is choosing
- **NEXT ACTION:** one line

## The gate

**Nothing goes to the other parent, their counsel, the AFC, the court, or CPS with an open P0 or P1.** The user can override explicitly, with the risk stated back to them; the override gets logged in the matter.

A clean run still reports what it checked. **Silence is not a pass.**

## Related

- `legal-premortem` — the general-purpose version for non-custody legal work
- `legal-researcher` (agent) — resolve `CONFIRM-BEFORE-CITING` tags against your state's primary sources before anything ships
- `matter-status` — current posture before choosing an approach
- `evidence-intake` — get documents in and logged before premorteming a position built on them

---

**Standing note on the state-specific tags in this file.** This skill was first written for a New York family court. The state specifics above — change-in-circumstances threshold, the Attorney for the Child role, recording-consent rules, fee-shifting — are marked `CONFIRM-BEFORE-CITING` deliberately. They are written from general knowledge, not yet verified against primary sources. **Resolve them once against your own state's family-court statutes and case law, then update this file with `VERIFIED-with-source` and the citation.** Until that pass is done, do not quote them into anything that leaves the workspace.
