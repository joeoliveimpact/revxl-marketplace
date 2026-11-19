> 🧭 **METHOD IS UNIVERSAL — the named authorities are the Mississippi example.** The process in this file applies in every state. Where it names **Albright / Armstrong / Ferguson**, a **chancery/chancellor** court, **MRCP / UCCR / the MS Rules of Evidence**, or a Mississippi code section (§93-, §43-19-), that is the **Mississippi worked example** — for a non-MS case, apply the **resolved state-law profile** (its factors, its court, its rules; see `state-law-resolver.md`) instead, and never cite these Mississippi authorities in a non-MS case.

# Case Assurance — the persistent checklist that proves nothing falls through

> **Jurisdiction note (Clawyer):** this file was written for Mississippi family court. Outside Mississippi, or outside a family case, treat every rule number, case name, deadline, fee and form in it as an example of what to look up, not as your law. Family-law steps in it do not apply to other kinds of case. Confirm your own state's version first and tag anything unconfirmed `CONFIRM-BEFORE-CITING`.

This is how the firm answers the question every self-represented person is really asking:
**"how do I know everything that needs to be done is actually going to be done?"**

The Standing Loop's Case Status Board (`firm-operating-system.md` Part 1, step 2) holds the live picture *in the
conversation*. That is not enough on its own — a picture that only exists in chat is forgotten the moment the chat scrolls.
So the firm keeps a **single, persistent, on-disk checklist** that survives every session and is the **one source of
truth** for what is open. The person never has to hold the case in their head, and they never have to trust a black box —
they can see the whole list, and the firm can *prove* coverage on demand.

## The master file — the case checklist

Keep one plain-text file in the working directory (default name **`CASE-CHECKLIST.md`**; use whatever the person already
has if they name one). It is **canonical** — any other tracker the person uses (a Linear/Jira board, a notes app, a
handoff doc) becomes a **mirror synced from this file**, not a competing list. One truth, not five.

**Structure (top to bottom):**

1. **🔴 TIME-SENSITIVE / NEXT** — the few hottest items, always first: the next deadline, anything unanswered that the
   other side filed, the single next physical step. This is what surfaces on every check-in.
2. **By case area** — derived from the playbook, so the *categories themselves* can't be incomplete:
   - **Custody / parenting time / decision-making** (one line per **best-interest factor under the governing custody
     standard for the case's state** — Albright in Mississippi, see `albright-factors.md`; the state's own statutory/case
     factors elsewhere, flagged `[research <state>'s custody factors]` until verified)
   - **Child support / alimony** (income, the state's required financial-disclosure form — UCCR 8.05 in Mississippi — and
     earning capacity, under the governing support/alimony standard; Armstrong in Mississippi, see `armstrong-ferguson.md`)
   - **Property / marital home / retirement** (every asset and debt valued and traced under the state's property-division
     standard; equitable distribution under Ferguson in Mississippi)
   - **Discovery** (what to serve, what's due, the cutoff)
   - **Evidence / exhibits** (what proves each contested fact)
   - **Filings** (what's drafted, filed, pending the court)
   - **Deadlines** (every dated obligation, exact calendar date, local time)
   - **Real-world actions** (clerk calls, records to obtain — the things only the person can do)

   Add or drop areas to match the actual matter (paternity, protection order, guardianship, etc., per `scenario-catalog.md`).

3. Each item carries four things:
   - **Status:** ✅ done · 🔄 in progress · ⏳ waiting on you · ⬜ not started
   - **The one next step** (concrete, physical where possible)
   - **Owner:** firm or the person (so a stall is visibly *whose* stall)
   - **Due date** if any (exact calendar date)

**Item line format (keep it scannable):**
```
- [⏳ waiting on you] Get the optometry records (Rx date + refit) — call Dr. ___, ask for the full chart — Owner: you — due 2026-06-15
```

## The four mechanics that make "everything" true

1. **Derived, not remembered.** The area list comes from the playbook (`divorce-roadmap.md` for the filing sequence,
   `post-judgment-roadmap.md` after a decree, `scenario-catalog.md` for the full scenario map), plus the governing frame
   for each live issue. Completeness is defined by the roadmap, not by whether anyone remembered a category.

2. **One ledger.** Everything open lands here — deadlines, filings, the Information Ledger's "needs," the loose flags a
   document review turns up. Outside trackers mirror this file. When you update the case, update this file.

3. **Self-surfacing.** Every check-in (the opening "what's going on today?" and any "where are we?") **leads with the
   🔴 TIME-SENSITIVE / NEXT block** — never the whole list (a wall of items re-creates the overwhelm). The full list is one
   ask away ("show me everything").

4. **Honest ball-in-your-court.** Items the firm cannot finish itself are marked **⏳ waiting on you** with the exact thing
   to do, so a stalled item is visibly stalled, never silently lost. Pair with the **coverage audit** below so coverage is
   *provable*, not a feeling.

## The coverage audit (run on demand, and at session close)

This is the routine that *proves* nothing is missing. Run it when the person asks any form of "is everything covered? / am
I missing anything? / what's left?", and as part of the `session-closeout` skill.

1. **Re-derive the required set.** For each live issue, walk its playbook and governing frame and list what a complete case
   *should* contain (every best-interest factor under the state's governing custody standard — Albright in Mississippi,
   the state's own factors elsewhere; income + the financial-disclosure form + earning capacity; every marital asset/debt;
   the filing sequence to the next milestone; the deadlines the rules set).
2. **Match against the checklist.** For each required item, find its line and read its status.
3. **Flag the gaps.** Any required item with **no line at all** is the dangerous case — surface it: *"nothing is tracked for
   X — should there be?"* Add it (⬜ not started) once confirmed.
4. **Report coverage, provably.** Output a short table the person can trust:

   | Area | ✅ done | 🔄 in progress | ⏳ waiting on you | ⬜ not started |
   |---|---|---|---|---|

   Then the headline in plain words: *"Here is everything your case needs, and exactly where each piece stands. The things
   waiting on you are X and Y. Nothing else is unaccounted for."* If a required item was missing and you just added it, say so.

5. **End with one NEXT ACTION** — usually the top ⏳ or ⬜ item.

## Maintenance contract (so the file is always trustworthy)

A checklist is only worth trusting if it is current. Therefore:
- **Read it at the start of every task** (the Standing Loop loads it with the case).
- **Update it the moment any work finishes** — a background agent or companion that completes a piece (a drafted filing, a
  verified cite, a new docket deadline, a completed prep) **writes the result back to this file** before the turn ends. This
  is a hard step of the background-agent completion contract, not an optional nicety.
- **Reconcile at session close** — the `session-closeout` skill runs the coverage audit and leaves the file clean for next time.

## Discipline
- Runs under `operating-doctrine.md` and all firm-wide rules. The 🔴 block surfaces by default; the full list only on ask
  (anti-overwhelm). No case facts leak into any shipped skill file — this routine is generic; the **checklist file itself
  lives in the person's workspace**, not in the skill.
- The checklist never replaces honest assessment. A ✅ means the work is actually done to the firm's standard (cites
  verified, scrub passed, no `[DO NOT FILE]`), not merely attempted.
