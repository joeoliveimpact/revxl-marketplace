# CROSS-EXAMINATION-PROTOCOL.md — HOW THE FIRM BUILDS CROSS

> **Jurisdiction note (Clawyer):** this file was written for Mississippi family court. Outside Mississippi, or outside a family case, treat every rule number, case name, deadline, fee and form in it as an example of what to look up, not as your law. Family-law steps in it do not apply to other kinds of case. Confirm your own state's version first and tag anything unconfirmed `CONFIRM-BEFORE-CITING`.

# The method that turns prior testimony into ammunition instead of re-asking it.

> This file fixes the thing that was wrong before: questions that were weak, had no backing, and re-asked what the client already covered in earlier hearings.
> A real trial lawyer never re-asks. A real trial lawyer pulls what the witness already swore to and either builds on it or springs it as a trap.
> Output of this protocol is a per-witness cross packet built to TRIAL-PACKET-PDF-SPEC.md. Question formatting follows CLAUDE.md Rule 3.

-----

## THE CORE IDEA: COMPOUNDING CROSS, NOT REDUNDANT CROSS

Every question the firm builds does one of three jobs. If it does none of them, it does not go in the packet.

1. **NEW** — establishes a fact not yet on the record, in one short leading proposition.
1. **BUILD-ON** — takes something the witness already swore to in a prior hearing and uses it as the floor for a deeper question. *“You testified in December 2023 that you and the client split the school pickups. That was true then — correct? And nothing about that has changed — correct?”* The locked-in prior answer becomes the foundation for the next move.
1. **TRAP** — gets the witness to say something today, then springs the prior sworn statement that contradicts it. This is the kill shot, and the “prior statement” is the witness’s own testimony from an earlier hearing in this same case.

What the firm never does: re-ask an opener the witness already answered under oath. If it’s already on the record, the firm either builds on it or traps with it. Re-asking wastes the one thing the client can run out of — time at the podium.

-----

## THE GOVERNING TEST (the client's rule — every question must pass all four)

A question that fails any of these is cut or rewritten. This is the standing standard for every cross the firm builds.

1. **TRAP ON THE TRUTH.** Every question traps the witness in a fact she cannot deny — either a known truth (her own sworn word, her own message, the Court's own finding) or a position that forces her to expose her own lie. She supplies the damage; we never argue it. If she can safely say "no" and walk away, the question isn't built right.

2. **PAINT THE PICTURE FOR THE JUDGE.** Every question is a brushstroke. Standing alone it locks one fact; in sequence it walks the chancellor to a conclusion the chancellor reaches herself. We never state the conclusion on cross — the picture states it. (CLAUDE.md Rule I: lock the fact and stop.)

3. **BUILD LEVERAGE.** Every locked fact must be usable after the answer — in the motion, in closing, in settlement, or as a credibility anchor. If a true answer gives us nothing to use, the question is wasted podium time.

4. **BUILD IN SEQUENCE.** Questions on the same topic compound — each one stands on the prior locked answer and moves one step deeper, or it builds toward the bigger picture of that topic. No scattered one-offs inside a topic. The order within a chapter is: the foundation facts first, the contradiction-lander next, so even if the client is cut off, the picture is already half-drawn and the trap is set.

The shape of a well-built topic block: **commit the safe facts → credit (build the wall) → confront/trap → the picture stands on its own.** Every block reads as a guided walk, not a list.

-----

## STEP ZERO: MINE THE TRANSCRIPTS FIRST

Before building a single question, the firm reads the prior sworn-testimony transcripts and indexes what each witness has already said under oath. The transcripts in this case:

- **11-10-2022**
- **12-12-2023**
- **3-2024**
- **5-06-2026**

For each witness who testified, the firm pulls every sworn statement and tags it: witness, date, transcript page/line, topic, and which Albright/Ferguson/Armstrong factor it touches. That index is the ammunition. Every BUILD-ON and every TRAP is drawn from it. The firm also cross-references the OFW record and the documents in the case file (via NotebookLM) for statements that contradict or support what the witness will likely say.

The Verification Partner confirms every transcript page/line cite against the actual transcript before it goes under a question. No cite goes in that hasn’t been checked.

-----

## THE GENERATION METHOD (run it per factor, per witness)

1. **Pick the factor.** A custody chapter is built around an Albright factor; a property chapter around a Ferguson factor; a support chapter around an Armstrong factor; a GAL or therapist chapter around competence and sourcing (below). State in one sentence the fact pattern that favors the client on that factor.
1. **Pull the mapped facts** from the record and the transcript index — each one tagged with its source (document + page/Bates, or transcript page/line, or OFW message number).
1. **Decide the job of each fact** — NEW, BUILD-ON, or TRAP. Anything already sworn becomes BUILD-ON or TRAP, never a re-ask.
1. **Write each as one fact, one leading question.** Short. Declarative. Ends in “correct?” or “isn’t that right?” Never an open question on cross. Never two facts in one question.
1. **Put the citation directly under the question** — the exhibit, the transcript page/line, the OFW number. This is the weapon. When the witness says “no,” the client reads the cite. The citation never gets separated from the question.
1. **Add the anticipated answer and the fallback.** One line: what the witness is expected to say, and what the client does if they dodge. *“Expected: ‘I don’t recall.’ If she dodges → read Exhibit __ into the record and ask again.”*
1. **Order by priority within the chapter** — the contradiction-landing question first, supporting questions after. If the client gets cut off, the point that matters is already on the record.
1. **Order the chapters by priority across the witness** — the chapters most likely to land, and most central to the case, go first. Cut-off insurance at both levels.

-----

## IMPEACHMENT: COMMIT, CREDIT, CONFRONT

Every TRAP runs this three-step sequence. It is the only safe way to spring a prior statement.

- **COMMIT** — lock the witness into today’s testimony with precise leading questions, so there is no wiggle room later. *“You’re saying you never denied the client his weekends — correct?”*
- **CREDIT** — build up the prior statement before revealing it, so the witness can’t wave it off. *“You filed sworn financial statements in this case — correct? You signed them — correct? You swore they were true — correct?”*
- **CONFRONT** — spring it. *“I’m showing you your sworn testimony from December 12, 2023, page 44. You testified there that the weekends were shared. That was under oath — correct?”*

Before any document or message is used this way, the firm lays the foundation to get it in (next section). Commit closes the doors. Credit builds the wall. Confront lands the blow. The firm never argues the inference on cross — it locks the fact and stops. The inference goes in the motion or in closing. (CLAUDE.md Rule I.)

-----

## GETTING A DOCUMENT OR MESSAGE IN (foundation)

A cross question that relies on an exhibit only works if the exhibit can come in. For each one, the packet carries the foundation steps:

- **Authentication** — establish what it is and who made it. For OFW/co-parenting messages and texts: the witness is a party to the exchange; the message carries the sender’s identity and distinctive content. For a document: identify it, who created it, when.
- **The witness’s own words and the witness’s own filings come in as substantive evidence** — a party’s own prior statement is not blocked as hearsay. The firm uses the opposing party’s own messages and her own sworn filings directly, both to impeach and as proof.
- **Prior sworn testimony** from an earlier hearing comes in to impeach and, when given under oath at a prior proceeding, as substantive evidence.

The packet states, under each exhibit-backed question, the one or two foundation questions that clear the exhibit before the confront. The Verification Partner confirms the authority for each foundation move is real and retrieved before it goes in the packet.

-----

## SEPARATE PACKETS, PER WITNESS — AND THE TWO-PACKET LESSON

The firm builds a separate cross packet for each witness, not one giant binder. This is the lesson from the May 6, 2026 hearing: the client walked in with two packets — one for the GAL, one for the housing issue — used both, and got through a lot but not everything. Separate, focused packets are what let the client pick up exactly the one they need and work it.

For the trial date in firm.config.json, three witness packets:

### [THE OPPOSING PARTY]

Chapters built around: the unilateral schedule change made without a court order; denial of access to medical and school information; the equitable-distribution facts (who paid the mortgage, the source of the down payment, any dissipation); the Albright facts (continuity of care before separation, primary-caregiver tasks, willingness to foster the relationship with the other parent); and pinning any allegation she cannot support — lock her into it, then show it appears nowhere in the OFW record or in any filing. Her own messages and her own sworn statements are the ammunition. Mine all four transcripts for what she has already sworn, and build-on or trap accordingly.

### [THE GAL / CUSTODY EVALUATOR]

Two chapters this witness always gets, on top of the substantive ones:

- **Competence chapter** — the limits of a lawyer-GAL rendering clinical or psychological opinions; what the GAL is and is not qualified to opine on.
- **Sourcing / thoroughness chapter** — who the GAL interviewed and who the GAL did not; reliance on one party’s submissions without independent verification; gaps in the investigation; failure to apply the full Albright analysis (especially continuity of care / primary-caregiver history before separation); and whether the GAL followed up on the client’s documented requests. Lead by eliciting the favorable parts of the report first, then prove what it left out with the record. Confirm whether the appointment was mandatory (abuse/neglect) or discretionary — it changes whether the chancellor must state reasons for rejecting the recommendation. Flag that for the Verification Partner to confirm from the appointment order.

### MIRANDA BEARSS (child’s therapist, LPC)

Chapters built around: the difference between a treating therapist and a forensic custody evaluator, and the limits on a treating clinician offering a custody or parenting-fitness opinion; what she did not do (never did a forensic evaluation, never observed the client with the child, never tested, never interviewed the client as a collateral); the one-sided inputs (her information about the client came from the opposing party and the child — the opinion is only as good as those inputs); who authorized disclosure of a minor’s session content; and the risk of coaching or one-parent influence.

-----

## WHAT THE FINISHED PACKET LOOKS LIKE

Built to TRIAL-PACKET-PDF-SPEC.md — colored section bars, the witness color-coding, the box types. For each chapter:

- A short heading naming the chapter’s one goal.
- The questions, numbered, one per line, one fact each (CLAUDE.md Rule 3).
- Under each question: the citation (exhibit / transcript page-line / OFW number), then a one-line anticipated answer + fallback.
- Conditional chapters boxed and labeled “deploy only if” (CLAUDE.md Rule 3), for questions that depend on something not yet in hand.
- Chapters and questions in priority order — cut-off insurance.

A reader should be able to point at any question and immediately put a hand on the document that proves it. That is the whole test.

-----

## WHAT CHANGES THE BUILD

If a witness’s role or appointment facts differ from what’s assumed (for example, the GAL’s appointment turns out to be discretionary, or a witness did not actually testify at one of the four hearings), the firm regenerates the affected chapters. If a new transcript or a new sworn filing comes in, it gets mined and folded in. The Verification Partner flags any cite it could not confirm, and that question does not go in until the cite is confirmed.

-----

# RESEARCH-BACKED UPGRADES (2026-08-01)

> **Nothing above is replaced.** The May-6 topic-band method that worked in court is the house method and stays exactly as written — ALL-CAPS band headers, foundation questions first, payoff question last, one short leading sentence then STOP, Tab # tagging, the pre-instruction tag at the top of the packet. RULES.md #6 still governs the format.
>
> **What follows is what an eight-lane research campaign (R1–R8) added on top of it**, sourced to the technique corpus at the `legal-sources/` folder. Every item below is a build requirement, not a suggestion.
>

## 1. THE ANSWER-SURVIVABILITY STANDARD — the new gate on every question

**Assume Chancellor the judge will let the witness explain any yes-or-no answer.** She does. The May-6 transcript shows her enforcing an **answer-first** rule herself — "Answer the question, first… And then you can tell us your concern" — which is the best possible version of this problem, because the fact banks BEFORE the explanation arrives. But it means a question whose whole value dies the moment the witness adds a sentence is a question that fails at this bench.

**The gate:** every question must survive the explanation. Build it on a document or a locked fact, so an explanation can add color but cannot retract the fact.

**Only two techniques survive that test intact.** They are the spine of every bank the firm builds:

1. **One new fact per question.** A question carrying one fact gives the witness nothing to explain.
2. **Document confrontation with the trigger question** (§3 below). She can explain what she *meant*; she cannot make the reading come out wrong.

This standard applies retroactively — the packet's existing 95-question the opposing party bank gets re-tested against it, Band 1 first.

## 2. FINDING BULLET — every chapter, no exceptions

**Every chapter carries a one-line note naming the proposed finding of fact its answers feed.** A bench trial may not include a closing argument; the artifact that decides this case is the **proposed findings of fact**. So each chapter is built backwards from the finding it is meant to produce.

**If a chapter cannot name its finding, it does not go in the packet.** (If a closing is allowed, the same bullet feeds it.)

## 3. "DID I READ THAT CORRECTLY?" — the house trigger question

**When a document is put to a witness, the client reads it aloud. The witness follows along silently on her own copy. Then one question, verbatim: "Did I read that correctly?"**

**Never hand the reading to the witness.** Five independent authorities converge on this. A witness reading her own damaging words will edit while reading, soften a clause, add commentary mid-sentence, or mumble it into background noise — and the reading is an unconstrained speaking turn handed to the person you are cross-examining.

**"Did I read that correctly?" is the only proper non-foundational question after a reading.** It asks about the *reading*, not the *fact*. The only truthful answers are "yes" or a correction of the reading. It produces a clean transcript line a chancellor can lift verbatim into a finding.

**What never follows it:** "Why did you write that?" "Do you stand by that?" "So you were lying then?" Read it, ask the trigger question, stop.

## 4. COMMIT / CREDIT / CONFRONT — now wired to the Mississippi rules

The three-step sequence above (§ IMPEACHMENT) is not merely good craft in Mississippi. It is expressly authorized, and the rule text is held verbatim in corpus file `07`:

- **MRE 613(a)** — "a party need not show it or disclose its contents to the witness." **Commit before confronting is lawful.** She gets no preview. On request, the document goes to her *lawyer*, not to her.
- **MRE 801(d)(2)** — her own messages, texts, emails, and sworn filings are **opposing-party statements**: not hearsay, no exception needed.
- **MRE 613(b)** — the explain-or-deny foundation for extrinsic evidence **expressly does not apply** to an opposing-party statement. Against the opposing party, there is no foundation to lay.
- **MRE 801(d)(1)(A)** — for **W2 and W3, who are not parties**, this is the rule that matters: a prior inconsistent statement given **under oath** at a hearing, proceeding, or deposition is **substantive** evidence. Unsworn prior statements by those two still run through 613(b). Always know which one you have before deciding how to use it.
- **MRE 611(b)** — Mississippi is wide open on scope: the court **may not** limit cross to the subject matter of the direct.

**⚠️ The 608(b) trap, and it is the one most likely to end a cross badly.** If the *only* purpose of a document is to show a witness has a bad character for truthfulness, the document is **inadmissible and the examiner is bound by her answer.** The escape is the **purpose**, not the paper: the same document is admissible for **contradiction, prior inconsistent statement, bias, or capacity** (MRE 402, 403, 616). **Every document chapter in this case already sits on one of those grounds — and none of them should ever be framed out loud as character evidence.** Never ask a question whose only payoff is "you are a liar." Ask the question whose payoff is "the document says something different."

**MRE 803(18) — the learned-treatise route for W2 and W3.** Get the witness to call the AFCC Model Standards / APA Guidelines a reliable authority, read ONE passage aloud, ask the trigger question, stop. The passage is **read into evidence, never handed up**. And it is **never** asserted that she "violated" a standard — those standards carry no force of law by their own terms. The frame is reliability, not truthfulness.

## 5. THE ESCALATION LADDER FOR A NON-RESPONSIVE WITNESS — bench-adapted

Three rungs. Climb them in order. **There is no fourth rung.**

1. **Repeat the question in identical words.** Same tone. No visible reaction to the dodge. The Court hears that it was not answered without the client having to say so.
2. **The verbal blackboard.** *"I'm going to ask that again, and I'll ask it the same way. My question was ___."* Never *"you didn't answer me"* — no characterizations.
3. **The court-reporter readback.** *"Your Honor, may I please have my question read back?"* Courteous, sparing. The evasion lands in a neutral third-party voice instead of the client's.

**Addressing the Court about an unresponsive witness is NEAR-PROHIBITED.** It is reserved for a witness who refuses to answer even after a readback. **Chancellor the judge runs this ladder herself** — the May-6 transcript shows her interrupting sua sponte ("Ma'am, see, that didn't answer the question"), re-asking the examiner's question for him, and overruling objections to force answers on cross ("Just answer the question… it's cross-examination"). 241 Court interventions in one hearing. Asking her to do what she is already doing spends credibility and buys nothing.

**The move that replaces rung four is silence.** Ask the clean one-fact question and stand still. The short beat after a non-responsive answer is the intervention window — it is where this chancellor steps in.

**Let short answers run, then bank them** with a flat "Okay." Polite interruption is reserved for answers doing real damage — new allegations, character attacks. A pro se father interrupting his ex-wife mid-sentence is a visual the firm spends only when the alternative is worse.

## 6. VOLUME AND SIZING — three ceilings

- **≤ 3 points per witness.** Not three chapters — three *points*. Everything else is support for one of the three.
- **Cross is never longer than the direct it answers.** A federal judge's standing bench rules state it; MRE 403 (undue delay, wasting time, needlessly cumulative) enforces it at a bench trial with a docket.
- **A chapter is fewer than 12 questions and has ONE goal.** More good facts than that means it is two chapters. **One question is never a chapter** — a lone fact has no context and is easy to walk back on redirect. **One chapter per page**, so a chapter mooted by the direct can be pulled without disturbing anything else.

RULES.md #6's volume targets (50–100 Qs per major witness) describe the **bank** the Builder generates. These ceilings describe what is **delivered at the podium**. Build wide, deliver narrow.

## 7. GRACEFUL RECOVERY — what to do when it goes wrong

- **The witness gives an answer you did not expect.** Do not chase it. Do not argue it. Move to the next page. The chapter that failed is one page; the packet is not.
- **You misread or misspoke.** *"I apologize — let me read that again."* Then read it correctly. An open palm and an apology; never a shaking finger, never a shaking head.
- **The witness says she does not understand.** Apologize and repeat. Courteous persistence is the posture that keeps a pro se father credible.
- **You lose the thread.** The readback (rung 3) is also a recovery tool, not only a control tool.
- **She gives you something better than you asked for.** Bank it with "Okay" and stop that chapter. Stop with a victory.

## 8. THE CRYING PROTOCOL

**Prevention first.** Convert any question that could be received as a personal attack into a document question. It is hard to cast a man as a bully while he is reading a witness her own written words.

**If she cries:**
- **Do not retreat.** Conceding the point after tears does not repair anything — the retreat is itself read as an admission that the question was improper.
- **Do not comfort.** No water, no tissues, no words of comfort. From a former spouse those read as performance.
- **Get quieter and slower.** Lower the volume. Slow the pace.
- **Finish the current chapter, then stop that chapter.** Bank the fact, then move on.
- **On any misunderstood question:** apologize and repeat.

**Decide before standing up** whether you are willing to insist on an answer from a sympathetic witness. If the answer is no, do not run an impeaching cross on that witness at all.

## 9. THE FORMAN UNIVERSAL QUESTION — the one sanctioned open question

**"Do you have anything good to say about my parenting?"**

The only open-ended question in the house method, because no answer can hurt:

- **"I don't know you"** → caps the weight of everything she said about the other parent. She can establish the opposing party is good; she cannot establish the opposing party is *better*.
- **"No"** → from a court-appointed neutral, after a documented investigative gap, that reads as bias, not judgment.
- **Anything good** → a concession from an adverse mouth.

**Deployment:** every the opposing party character witness; **W2 (GAL) — ASKED LAST**, after the methods-timeline has established the 29-month gap between the December 2023 interview and the May 1, 2026 report (the timeline is what converts a "no" into visible bias); **W3 (therapist)**, where the expected "I don't know him" caps her testimony. It is also the middle option for a character witness who did not damage us: ask it, then sit down.

**"No questions, Your Honor" is affirmatively persuasive** where the direct did not damage a contested finding. **Never silent on damaging testimony.**

**Inviting the Court in** — *"Your Honor, do you have any questions for the witness?"* — is adopted for **W2 only**. Never after the opposing party. Never after W3 unless her testimony went well for us.

## 10. THE FOUR PODIUM RULES (learned from a live judge-probe exchange)

Drawn from the May 6, 2026 certified transcript — this chancellor, this courtroom:

1. **She enforces answer-first sua sponte.** The fact banks before the explanation. Build for that: get the fact locked, let the explanation follow.
2. **She polices non-responsive answers herself** and re-asks the question for the examiner. Do not do her job for her.
3. **She overrules objections to force answers on cross.** The latitude is real — use it, and do not flinch when the other side objects.
4. **She is an active manager** — 241 interventions in one hearing. The correct posture is a clean question and a still body. Noise from the podium competes with a judge who is already running the room.

*(One local-practice row remains open: podium positioning — where the examiner stands. No courthouse calls. It goes to the client's own memory of the room at the walkthrough.)*

## 11. THREE STANDING WARNINGS

**JURISDICTION HYGIENE.** The technique corpus is built from Arizona, Massachusetts, Oklahoma, New York, North Carolina, South Carolina, Australian, and federal materials. **Techniques port. Citations do not.** No OK statute, NY procedure, NSW rule, SC jury framing, or federal rule number enters a the client's document. The Mississippi hooks are the verbatim MRE text in corpus file `07`.

**THE PSYCHOLOGY IS MOSTLY TRADITION.** Say it accurately or not at all. **Reactance** (the no-adjectives rule) is the one principle with a real empirical spine. **Chunking** traces to Miller (1956/1994) — cite him by name, never assert a specific item count. **Negativity bias** rests on a newspaper column and a press release: "advocacy tradition supported by popular-press accounts," never "per the research." **Primacy/recency** is jury-framed memory tradition and appears nowhere in the campaign's empirical anchor — keep "strong point early, clean exit" as plain good order and make no science claim. And every one of these studies is about **jurors**; whether a career chancellor is equally susceptible is an open question.

**NO GROUND-RULES SPEECH FOR THE OPPOSING PARTY.** The three-response ground-rules preamble (Yes / No / I can't answer yes-or-no) is **IN for the GAL and any expert** — a sitting judge says it builds credibility with the bench. It is **OUT for the opposing party.** A negotiated preamble with his ex-wife reads as fear and hands her the first move; control comes from question form alone. Also OUT with the opposing party: "Ma'am" as a pressure device, and the formal-name control move. Both stay IN for W2 and W3. Also OUT entirely: the easel/chalkboard (a jury device, theatrical before a chancellor), and the "perhaps you do not understand" teacher opener when addressed to the opposing party.

## 12. WHERE TO GO DEEPER

| Need | File |
|---|---|
| The whole doctrine, one file | `...\cross-examination-technique\00_MASTER-DOCTRINE_Cross-Examination-Mastery.md` |
| Younger's ten commandments — and when to break them | `01_YOUNGER_...` |
| Pozner & Dodd · MacCarthy · Mauet — the schools | `02_SCHOOLS_...` |
| **Document cross and impeachment by writing (the centerpiece)** | `03_READ-THEIR-OWN-WORDS_...` |
| Runaways, control, and recovery | `04_WITNESS-CONTROL_...` |
| **Bench-trial and family-law adaptations (the 17-row conversion table)** | `05_BENCH-TRIAL-AND-FAMILY-LAW_...` |
| GAL and therapist cross structures | `06_EXPERTS_...` |
| **The Mississippi rules, verbatim, with plain-language translation** | `07_MS-RULES-OF-CROSS_verbatim.md` |
| Failure modes and the one question too many | `08_FAILURE-MODES_...` |
| Applied to this case — band upgrades | `09_APPLIED_[case-name]_band-upgrades.md` |
| Every source, with its verification status | `SOURCES-LEDGER.md` |
| Plain-language summary of what changed and why | `UPGRADES-MEMO_what-changed-and-why.md` |
| Ask it a question | `python scripts/ask_notebook.py "<question>" --notebook cross_exam_mastery` |