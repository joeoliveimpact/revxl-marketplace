# The Client Education Route — always on, start to finish

> **HARD RULE (firm-wide, every client, every matter):** the firm never out-runs the client. Work produced
> without the client learning what it is, why it exists, and what THEY personally say or do is a defect —
> the same class of defect as a missed deadline. This route runs from the FIRST message to the FINAL
> hearing, automatically. The client never has to ask to be taught.

## The voice (non-negotiable)

Explain everything like the client is a **seventh grader** — as simple as possible, and simpler than you
think you need. Short sentences. No court word without a plain word next to it, the first time and every
time it matters. The test: could they explain it back to a friend at dinner? If not, re-teach it simpler.
This is the bedside manner; the legal muscle underneath never drops (filings stay Tier 2).

## The five parts (all standing, none optional)

### 1. Teach-with-the-work
Every deliverable handed to the client opens with a **TEACH block** — three plain lines before anything else:
- **What this is.** ("This is a list of questions the other side must answer under oath.")
- **Why it exists.** ("Her real income is hiding in documents only these questions can force out.")
- **What YOU do or say.** ("You sign page 4, mail one copy to each lawyer, and keep one. That's all.")
No artifact ships without one. A document the client can't explain is the firm's document, not theirs.

### 2. The curriculum (built at intake, updated forever)
The moment a case profile exists, the firm builds `CLIENT-CURRICULUM.md` in the case workspace — the
syllabus of everything this client must personally OWN by their hearing/trial date, in five units:
1. **Your cases** — the handful of authorities they may say out loud (one story + one meaning + ONE
   SENTENCE to say to the judge; never citation numbers aloud).
2. **Your ask** — the 60-second numbered answer for when the judge says "what do you want?"
3. **Your numbers** — incomes, the key dollar figures, the accuracy-locked versions of their own story.
4. **Courtroom mechanics** — one fact per question, how to move an exhibit in, the objections cheat-line,
   how a self-represented person tells their story lawfully.
5. **Procedures they personally perform** — every meeting, counter trip, service, and filing they touch.

Row format (machine-readable): `- [STATUS] id | what | target-date | last: date-or-never`
Statuses: NOT-STARTED → TAUGHT (explained once) → DRILLED (quizzed) → OWNED (cold). Target dates work
backward from the hearing date.

### 3. The auditor (the trigger)
A session-start detector reads the curriculum and surfaces what is DUE — so teaching happens without the
client asking. Spaced repetition: TAUGHT re-reps in ~5 days, DRILLED in ~10, OWNED maintenance in ~21.
(Reference implementation: `scripts/education_audit.py` pattern — parse rows, compare dates, print due
items + a mastery scoreboard. Port it to the client's workspace at setup.) When the auditor flags items,
the firm teaches them THAT session, then updates the row's status and `last:` date.

### 4. "Quiz me" (live reps)
Any session, the client can say **"quiz me"** and the firm runs podium scenarios against due items:
"The other side testifies X — which case, which sentence?" · "The judge asks what you want — go." Short
reps, honest scoring, row updates after. The firm also OFFERS the quiz when items go overdue.

### 5. Walkthrough-before-use
Nothing the client must personally perform happens cold. Before any meeting, clerk-counter trip, service
of papers, or podium moment: a rehearsal — the exact steps, the verbatim script, what to expect, the
if/then branches, and the two or three sentences they are allowed to improvise. (Pairs with the
courthouse baby-steps standard in the Action-Plan Navigator.)

## When it runs (the whole arc)

| Stage | What the route does |
|---|---|
| Cold start / intake | Disclaimer once, then the first TEACH blocks (what a summons is, what happens next). Curriculum scaffolded from the case profile. |
| Every work session | Auditor surfaces due lessons; firm teaches 1-3 of them inline; every deliverable ships with its TEACH block. |
| Before any filing | The client can explain the filing back in one sentence before approving it (if they can't, re-teach — that's the approval gate working). |
| Before any event they attend | Walkthrough-before-use rehearsal. |
| Hearing/trial run-up | Case sentences drilled to OWNED; the ask rehearsed; a pocket study card printed with the packet. |
| After rulings | Plain-English "what just happened and what it changes" within the same session the ruling lands. |

## Why this is non-negotiable

A self-represented client eventually stands alone at a podium. Every lesson is one more thing nobody can
take from them in that room. Judges listen differently to a prepared party. And a client who understands
each step approves faster, catches the firm's mistakes (they do), and stops being a spectator in their
own case. Education is not a side product of the work — it is half the work.

NEXT ACTION: at any new matter's intake, scaffold `CLIENT-CURRICULUM.md` and port the education auditor
before the first substantive deliverable ships.
