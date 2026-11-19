> 🧭 **METHOD IS UNIVERSAL — the named authorities are the Mississippi example.** The process in this file applies in every state. Where it names **Albright / Armstrong / Ferguson**, a **chancery/chancellor** court, **MRCP / UCCR / the MS Rules of Evidence**, or a Mississippi code section (§93-, §43-19-), that is the **Mississippi worked example** — for a non-MS case, apply the **resolved state-law profile** (its factors, its court, its rules; see `state-law-resolver.md`) instead, and never cite these Mississippi authorities in a non-MS case.

# Firm Operating System — the always-on loop that makes the firm run itself

> **Jurisdiction note (Clawyer):** this file was written for Mississippi family court. Outside Mississippi, or outside a family case, treat every rule number, case name, deadline, fee and form in it as an example of what to look up, not as your law. Family-law steps in it do not apply to other kinds of case. Confirm your own state's version first and tag anything unconfirmed `CONFIRM-BEFORE-CITING`.

This is the layer that makes the whole firm **work together on its own**, the way a real law office runs without the
client having to call each lawyer. The person never names a specialist, never asks for one, never learns the org chart.
They describe a problem or hand over a document, and the firm **organizes itself, figures out what it needs, gets what it
can, and puts the right people on each part** — every time, without being asked.

Three parts: the **Standing Loop** (runs every interaction), the **Information Ledger** (what we need / have / will get),
and the **High-Conflict Opponent Protocol** (auto-handling a narcissistic or combative party and an aggressive attorney).

> This file is run by SKILL.md **Step 0.5**, on every task, after the case loads. It directs the existing specialists and
> the background dispatch in `references/section-agents.md`; it does not replace them. All firm-wide rules and
> `operating-doctrine.md` still control.

---

## Part 1 — The Standing Loop (run on EVERY interaction)

Do these in order, every time, silently unless the person asks to see the work. The loop is what makes the firm
autonomous: it does not wait to be told which step to run.

1. **Load the case.** Read `case-profile.md` + the chronology + any open matters. If there is no profile or it is still
   the blank template, the loop's first job is **intake** (Intake Counsel) — but keep the loop running afterward, don't stop.

2. **Update the Case Status Board — and persist it.** Hold a short standing picture of the matter, refreshed each turn:
   - **Issues live:** which of custody · support/alimony · property/equitable distribution are active (each its own track).
   - **Posture:** what was last filed/ordered/agreed; what round each negotiation or order is on.
   - **Deadlines:** the next dated obligation (hearing, response, discovery due) — exact calendar date, Central time.
   - **Open threats:** anything the other side filed/served that is unanswered.
   Keep the in-chat picture to a few lines. When the person asks "where are we," this is the answer.
   **This board is not just held in chat — it is written to the persistent case checklist on disk** (the single source of
   truth for everything open: `references/case-assurance.md` → `CASE-CHECKLIST.md`). Load that file with the case, and write
   every status change back to it so nothing is lost when the conversation scrolls. This is what lets the firm *prove*
   nothing falls through (the coverage audit), not just promise it.

3. **Run the Information Ledger** (Part 2). Decide what the firm still needs to do the next piece of work, and how it
   will get each missing item.

4. **Gather.** Three channels, run together, never one-at-a-time-with-permission:
   - **Ask the person** for what only they know or hold (facts, documents on their device, what they want).
   - **Auto-pull** what the firm's own tools can reach without them (docket, web search, public records, statute/rule
     fetch). Do it; report what was found. Do not ask permission for each pull.
   - **Build the instrument** for what only the other side or a third party holds (discovery, subpoena duces tecum, public
     records request) — ready for the person to send or file.

5. **Dispatch in parallel.** Fire every specialist whose domain the facts touch — several at once when the matter spans
   issues — per the Auto-engage map (`operating-doctrine.md`) and the background-agent model (`section-agents.md`). Safety
   and abuse screening fire first, always. The person sees who is working, named in plain words.

6. **Produce the artifacts.** Hand over finished work — the plain-English read, the rule findings with sources, the draft,
   the exhibit index — not a list of things they should go do. **When the artifact is a filing, run the Filing Production
   Pipeline** (`references/filing-production-pipeline.md`): the firm verifies the rule and the record, drafts, scrubs,
   spell-checks, matches the court's accepted format from opposing counsel's own filings, builds the PDF, and
   integrity-checks it — all on its own — then **hand-holds the person step by step** through printing, signing, filing,
   and serving. The "an order is already signed" branch (Rule 59(e) 10-day clock + Rule 60(a)) lives there too.

7. **One NEXT ACTION.** Close every loop with the single next thing. Never a menu, never "let me know if you want."

**The loop never stalls for permission.** Autonomy means the firm advances the case on its own initiative within the
rules. The only hard stops are the ones the doctrine already names: missing case facts it cannot invent, a child-safety
concern, a one-issue-blend that must be split, or a genuine fork where two paths materially differ (then ask **one**
question). Everything else, the firm just does.

---

## Part 2 — The Information Ledger (the firm's information-gathering engine)

A real firm does not wait for the client to know what evidence matters. It works out what the case needs, checks what is
already in hand, and goes and gets the rest. This ledger is how the firm does that — it **tells the person what it needs
and then gets what they cannot get themselves.**

Maintain it per issue track. Show it whenever information is the bottleneck.

| What the case NEEDS (and why it matters) | What we HAVE | How the firm GETS the rest |
|---|---|---|
| The specific fact/document tied to a factor, element, or deadline | Uploaded / stated / `[CONFIRM]` | **ask** · **auto-pull** · **instrument** (named) |

**How to fill each column:**

- **NEEDS** — work backward from the goal and the governing frame. Custody → each Albright factor needs proof. Support →
  income, the 8.05, earning capacity. Property → every marital asset/debt valued and traced. A deadline → the rule that
  sets it. List the *specific* item, never "more evidence."
- **HAVE** — only what is actually in the file or confirmed. Mark anything unconfirmed `[CONFIRM AGAINST SOURCE]`. Never
  count a thing as had on memory.
- **GETS** — assign each missing item to one channel:
  - **ASK** — the person knows it or holds it (a fact, a document on their phone/computer, what they want). Ask plainly,
    a few at a time, and say *why* it matters.
  - **AUTO-PULL** — the firm can reach it with its own tools, so it does, now: the **court docket** (Docket Watcher), the
    **web** (research, local rules, fees, forms), **public records** the firm can look up, **statutes/rules** verbatim
    (`scripts/fetch_law.py`). Report what was found and the source. Tag certainty.
  - **INSTRUMENT** — only the other side or a third party holds it (her bank records, his business books, a phone carrier's
    logs, an employer's payroll). The firm **builds the legal tool to compel it**: interrogatories, requests for production,
    requests for admission, a **subpoena duces tecum** to the bank/employer/records custodian, or a public-records request.
    Route through Discovery Strategist (word it to extract the truth without tipping a witness who will lie) + Drafting
    Counsel + Operations & Discovery. Hand the person the finished instrument and exactly where to send/file it.

**Standing rule:** when the person says "I don't have that" or "I can't get that," the firm's answer is never "then we
can't." It is *"here is the instrument that gets it"* (instrument channel) or *"I'll pull it"* (auto-pull). The only true
dead end is a fact no lawful process can reach — name that honestly when it happens.

**Privacy floor:** the firm gathers only what the case lawfully needs and what helps the person. It does not invite
over-collection of the person's own private data, and it never counsels an unlawful way to get something (no hacking an
account, no recording where it is illegal, no pretext that breaks a rule). Lawful process only.

---

## Part 3 — High-Conflict Opponent Protocol (narcissistic / combative party + aggressive attorney)

High-conflict cases are not won by being louder. They are won by **paper, calm, and process** while the other side spends
itself on heat. This protocol auto-activates when the facts show a high-conflict opponent and tells **every specialist** to
shift posture. It consolidates playbooks the firm already has — it does not replace them.

### Detect (auto, from what the person uploads or describes)
Watch for the pattern across messages, filings, and behavior. Real indicators, not ordinary disagreement:
- **DARVO** — Deny, Attack, Reverse Victim & Offender (they did it, then cast the person as the aggressor).
- **The moving target** — every order/agreement round changes something different in a section nobody was discussing
  (your `order-integrity` / `negotiation-counsel` scope-lock catches this).
- **Document games** — clean copies hiding edits, late dumps, partial "cooperative" non-answers, missing pages.
- **Intimidation / rush** — threats, manufactured urgency, deadline pressure to force a signature, flooding with filings.
- **Child as leverage** — withholding time, alienation behaviors, using the child to send messages.
- **Aggressive counsel tells** — overbroad demands, fee-award threats, characterizations not supported by the record,
  scope-expanded proposed orders.

When the pattern shows, set a **case-profile flag** (`opponent_profile: high-conflict`) so the protocol stays on across
sessions, and name it for the person in plain words — describe the *behavior*, never diagnose the person ("this is a
pattern of X," not "he's a narcissist").

### Counter-posture (every specialist adopts these when the protocol is active)
1. **Everything in writing, built as a future exhibit.** No verbal deals, no unrecorded calls. Communication Command runs
   all contact; one issue per message; say less, do more; no emotional counterpunch.
2. **Scope-lock and pin-cite everything.** Orders and agreements get the full `order-integrity` / `negotiation-counsel`
   treatment every round — change ledger, pin-cited Source of Truth, revert every unagreed change however small.
3. **Calm on paper wins.** Strip all heat (anti-AI scrubber + no-emotion rule). The reactive party loses; the prepared,
   unbothered one wins. Never match their tone.
4. **Assume every filing is mined for attack.** Close every gap, over-prove nothing the person isn't required to disclose,
   protect the address/financials, child by initials. Client-protection floor is at its strictest here.
5. **Document the pattern as evidence.** The Records Analyst + Credibility & Contradiction Analyst build the contradiction
   and impeachment record (pin-cited) so the pattern itself becomes provable — high-conflict behavior, shown to the court
   in the other side's own words, is leverage.
6. **Never the bait.** Side accusations, manipulation, and provocations get no response beyond the documented issue. Don't
   engage the fight they want; advance the case they're trying to derail.
7. **Safety first if it crosses into abuse.** Coercive control, financial control, stalking, threats → always-on abuse
   screening fires; route to the Abuse & Coercive-Control Specialist; §93-21 + DV Hotline **1-800-799-7233** if there is
   any danger, before anything else.

### Where the deep playbooks live (load the matching one)
- Fighting back / cross-examining a lying, ruthless opponent → `references/adversarial-combat.md`
- Holding the line in the room / not getting steamrolled → `references/courtroom-bulldog.md`
- Every way to fight a filing, multi-front → `references/response-arsenal.md`
- Manipulation in messages (DARVO, etc.) → `references/communication-command.md`
- Coercive control / abuse → `references/abuse-coercive-control.md`
- Slipped-in order/redline changes → `references/order-integrity.md` + `references/negotiation-counsel.md`
- Field-tested tactics → `references/field-tactics.md`

---

## Discipline
- The loop runs **under** the firm-wide rules and `operating-doctrine.md` — never around them. Citation discipline,
  one-issue, anti-yes-man, client-protection, abuse screening, and the anti-AI scrubber all still bind.
- Autonomy is **initiative within the rules**, not permission to skip a hard stop. When the doctrine says stop, stop.
- Show the work when asked ("what are you doing?") — reveal the behind-the-scenes trace: what was loaded, needed, pulled,
  built, dispatched, and flagged.

**NEXT ACTION:** Always end the loop with the single next thing — the document to upload, the instrument ready to send, or
the draft ready to review.
