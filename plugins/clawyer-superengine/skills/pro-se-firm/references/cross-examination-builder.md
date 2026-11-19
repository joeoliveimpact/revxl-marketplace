# Cross-Examination Builder — continuous, every witness, treat-everybody-as-hostile

The firm operates a named **Cross-Examination Builder** specialist as a continuous role, not a deliverable. The Builder reads every transcript, OFW message, order, motion, declaration, screenshot, and audio transcript line-by-line, word-by-word. It extracts every contradiction, admission, gatekeeping moment, documented lie, and gap. It converts each into a numbered Q in May-6 format.

This role is auto-firing. Every transcript or evidence document the firm ingests routes through the Builder. The Builder never waits for "build cross-exam" to be requested.

## Treat-Everybody-As-Hostile Doctrine (locked)

Every potential witness — including friendly witnesses — gets a full cross-examination prep pack. Friendly witnesses turn. Memories degrade. Cross-pressure on the stand changes testimony. The firm prepares as if every person on the stand is adverse, then softens to direct examination for the ones who hold up.

The doctrine drives the 18-witness coverage scope at trial. No witness in the client's orbit is left without a cross prep pack.

## 18-witness coverage scope (Sept 1 trial)

The Builder maintains a per-witness cross-prep file for every witness in this list, color-coded per `TRIAL-PACKET-PDF-SPEC.md` Step 6 banner logic.

1. W1 the opposing party (primary hostile, navy)
2. W2 GAL the GAL (adversarial-critical, maroon)
3. W3 Therapist the child's therapist (third-party professional, green)
4. W4 Stepfather Ben (hostile-by-alliance, navy)
5. W5 Stepfather [witness] (hostile-by-alliance, navy)
6. W6 Kyle (third-party, green or navy per facts)
7. W7 Cardiology provider (third-party professional, green)
8. W8 EPS / electrophysiologist (third-party professional, green)
9. W9 PCP (third-party professional, green)
10. W10 Saint Martin East Elementary (third-party institutional, green)
11. W11 Forrest County MDCPS contact (third-party institutional, green)
12. W12 [witness] [witness] (clerk, neutral, default green)
13. W13 Keesler FCU records custodian (third-party institutional, green)
14. W14 Cellphone / GPS records custodian (third-party institutional, green)
15. W15 Anger-management program certifier (third-party institutional, green)
16. W16 [witness] (eyewitness, friendly but prep-as-hostile per doctrine, green softening to direct)
17. W17 Shane (reference letter signer, friendly but prep-as-hostile, green softening to direct)
18. W18 Defensive reserve witnesses pool (anyone the opposing party subpoenas, prep-as-hostile)

A witness slot stays in the pack even when the trial-day call is "do not call." The pack carries the cross prep in reserve in case the witness gets called by the other side.

## Volume targets

1. 50 to 100 numbered Qs per major witness (the opposing party, GAL the GAL, the child's therapist, Ben).
2. 25 to 50 numbered Qs per ancillary witness.
3. 15 to 25 numbered Qs per defensive-reserve witness.

The 9-agent overnight run produced 1,061 numbered Qs across 10 cross-exam build files. Synthesis folds them into the rebuilt `My Case/2026-09-01_FINAL-TRIAL/Trial-Packet.md` Section 7.

## May-6 format doctrine (RULES.md Doctrine #6)

1. Topic-banded blocks. ALL-CAPS theme header per band, not chronological order.
2. Foundation Qs first, payoff Q last in each band.
3. Leading questions ending "Correct?" / "Right?" / "Is that accurate?" Never open-ended.
4. One short sentence per Q then STOP.
5. Pre-instruction tag at the top of each witness section: "One question. Stop. Listen. Do not fill silence. Let her answers be the problem."
6. Closing payoff Q per band that locks the impeachment.
7. Tab # tagging so each Q's exhibit is one number away in the binder TOC.

GAL and expert-witness blocks default to the 8 sub-attacks (SOURCES, PROCEDURE, DAUBERT, SPECIFIC FINDINGS NOT VERIFIED, CONTINUITY, SCHEDULE-AND-HOSPITALIZATIONS, FEES, BIAS) unless the facts make one inapplicable.

## Output files and synthesis path

1. Working files at `outputs/working/cross-exam/Cross-Exam-Build_<Witness>__<date>.md` (post-reorg) or `outputs/case-organization/Cross-Exam-Build_*_s19.md` (pre-reorg, migrating).
2. Master index at `outputs/case-organization/Cross-Exam-Build_INDEX.md` rolls every witness up with Q counts and headline plays.
3. Synthesis lands in `My Case/2026-09-01_FINAL-TRIAL/Trial-Packet.md` Section 7, witness-by-witness, color-coded per the trial-packet spec.
4. Every Q is source-tagged. Every Q's exhibit is Tab-#-tagged.

## Verification gate

Every Q that names a person, quotes a document, or asserts a fact routes through the Hallucination Auditor before propagation. Every citation in a LAW: line routes through the Citation Discipline gate.

NEXT ACTION: When a new document lands, route it through the Builder, extract the contradictions and admissions, append the new numbered Qs to the matching witness file, and update the INDEX rollup.
