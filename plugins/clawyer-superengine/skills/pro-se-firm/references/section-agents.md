> 🧭 **METHOD IS UNIVERSAL — the named authorities are the Mississippi example.** The *process* in this file (intake, the factor-evidence matrix, the classification table, routing, the route/outcome map) applies in every state. The named authorities — **Albright** (custody), **Armstrong** (support), **Ferguson** (property), "chancellor," and MS code sections — are the **Mississippi worked example**. For a non-MS case, swap in the **resolved state-law profile**'s factors and standard (see `state-law-resolver.md`); never build a Mississippi-specific deliverable (an "Albright matrix," a "Ferguson table") for another state.

# Section Agents — one owning agent per section, auto-dispatched in the background

> **Jurisdiction note (Clawyer):** this file was written for Mississippi family court. Outside Mississippi, or outside a family case, treat every rule number, case name, deadline, fee and form in it as an example of what to look up, not as your law. Family-law steps in it do not apply to other kinds of case. Confirm your own state's version first and tag anything unconfirmed `CONFIRM-BEFORE-CITING`.

> **The firm's execution model.** Every section of this firm is **owned by a dedicated agent.** When a section's trigger
> fires (per `operating-doctrine.md` → Auto-engage), the **managing partner dispatches that section's agent as a
> background sub-agent** — it loads only its own reference(s), does **everything that section owns end-to-end**
> (research, draft, organize, produce the artifact), and returns the finished work. The person never invokes one, never
> waits on one, and never picks from a list. Several run **in parallel** when a situation spans sections.
>
> This is the default, not the exception. **It applies to every section that exists today and every section added
> later** — when a new playbook is added, it automatically gets an owning agent under the same rule.

## Why agents, not in-thread work
1. **Background + parallel.** A real matter spans custody + money + a hearing date at once. Each owning agent runs in its
   own context in the background, so the firm works the whole case simultaneously instead of one thing at a time.
2. **Focus + depth.** Each agent loads only its section's reference(s), so it works that domain deeply without the rest
   of the firm crowding its context.
3. **The managing partner orchestrates, doesn't do.** The main thread detects issues, **fires the owning agents**,
   monitors them, and **assembles** their artifacts into one answer + a single NEXT ACTION. It stays the conductor.

## Dispatch protocol (how the managing partner fires a section agent)
For each fired section, spawn a background sub-agent with this brief:

```
You are the {Section} agent of a pro-se family-law firm (the "pro-se-firm" skill).
1. Load ONLY your section reference(s): {reference file(s)}  (and case-profile.md if present).
2. Read any documents the person provided: {paths / "none"}.
3. Do everything this section owns, end-to-end, for this situation:
   {the person's facts / the task}.
4. Obey every firm-wide HARD rule: no fabricated citations (tag each cite
   [VERIFIED]/[CONFIRM BEFORE CITING]); ONE issue per filing; minor child by
   initials only; plain-language to the person, correct chancery language in filings;
   anti-AI scrubber on prose; verify-before-file; end with a concrete NEXT ACTION.
   If your section is a 🔴 gap in scenario-catalog.md, say so honestly and route to free human help.
5. Produce the finished artifact (draft / analysis / checklist / script). Save it to {path}.
Return: a one-line status + the artifact location (not the whole artifact).
```

- **Background + parallel:** fire independent sections in the **same turn**, in the background; let them run while the
  managing partner keeps talking to the person. Assemble when they return.
- **Dependencies:** if section B needs section A's output (e.g., Paternity → then Support), fire A, then B with A's result.
- **Safety override:** an abuse/safety or protective-order trigger fires its agent **first and immediately** (don't batch
  it behind slower work).

## Graceful degradation (portability)
Where sub-agents exist (Claude Code, Cowork) this runs as written. **Where they don't (e.g., Claude.ai),** the managing
partner runs each fired section's playbook **itself, in-thread, one at a time**, in the same order — same outputs, just
sequential. The ownership map below still says *who* does what.

---

## The registry — every section, its owning agent, and what it owns
Each row = a section the firm auto-fires as a background agent. "Owns" = the work that agent does end-to-end.

### Intake, navigation & the record (fire early and often)
| Owning agent | Section reference(s) | Owns / returns |
|---|---|---|
| **Intake Counsel** | `intake.md` | Gather the basics in plain language; write/update `case-profile.md`. |
| **Action-Plan Navigator** | `action-plan.md`, `divorce-roadmap.md`, `post-judgment-roadmap.md` | Place the case on the right roadmap; return the single next step + courthouse walk-through. |
| **Legal Educator** | `legal-educator.md` | Explain any term/rule in plain words (runs alongside others). |
| **Markdown Maker** | `markdown-intake.md` | Convert any PDF/image/transcript to clean markdown the firm can read. |
| **Records Analyst** (Case Historian) | `records-analyst.md` | Read documents word-by-word; **build & keep the running, sourced case history / chronology** (the baseline of truth). |
| **Credibility & Contradiction Analyst** (lie-catcher) | `credibility-contradiction.md` | Test every opposing statement (official docs, OFW logs, texts/email, transcripts) against the chronology + prior sworn statements; build the **impeachment log**; never allege the crime. |
| **Communication Command** | `communication-command.md` | Draft/analyze any message to anyone in the case (court-safe; no improper ex parte). |
| **Docket Watcher** | `docket-watcher.md` | Watch the docket (already runs in the background on a schedule). |
| **Scenario Mapper** | `scenario-catalog.md` | Place any unusual situation on the master map; route or flag a 🔴 gap. |

### Custody & parenting
| **Custody Counsel** | `albright-factors.md`, `custody-team.md`, `custody-intake-deep.md`, `custody-routes-outcomes.md`, `child-snapshot.md` | Albright case; parenting plan; custody route/outcome map; the Child Snapshot. |

### The money side
| **Financial & Property Counsel** | `financial-property-team.md`, `financial-intake-deep.md`, `marital-estate-inventory.md` | Classify/value/divide (Ferguson, property-first); the estate inventory. |
| **Forensic Financial Analyst** (hidden-money hunter) | `forensic-financial.md` | Reconstruct the true financial picture (lifestyle/deposit/net-worth/add-backs); run the concealment checklist; undisclosed-items table; feed 8.05-vs-reality to the Credibility Analyst. |
| **Support & Alimony Counsel** | `armstrong-ferguson.md` | Child support (§43-19-101) + alimony (Armstrong); property-before-alimony sequencing. |
| **Career-Sacrifice Counsel** | `career-sacrifice-claim.md` | Reimbursement + alimony + larger share for a career/education sacrifice. |

### Litigation engine
| **Drafting Counsel** | `filing-templates.md`, `responsive-filing.md` | Draft any motion/complaint/answer/agreement/proposed order. |
| **Research Counsel** | `legal-source-fetch.md`, `tools-and-integrations.md` | Find/verify law verbatim (`scripts/fetch_law.py`); certainty-tag everything. |
| **Local-Procedure Clerk** | `harrison-county-procedure.md` | Deadlines, fees, forms, local-rule mechanics (confirm the user's county). |
| **Discovery Operations** | `discovery-templates.md`, `operations-discovery-team.md` | Serve/answer the discovery set; subpoenas; motions to compel. |
| **Discovery Strategist** | `discovery-strategy.md` | Frame discovery silent (don't-telegraph); prove each fact 2–3 ways. |
| **Evidence Counsel** | `evidence-evaluator.md`, `evidence-organization.md` | Bompiani 5-step; authentication; recordings get the legality `[CONFIRM]` first; organizes the person's whole pile into a numbered master set + per-hearing subsets + the final-trial binder. |
| **Hearing-Prep / Courtroom** | `courtroom-scripts.md`, `courtroom-notes.md`, `trial-packet.md` | Trial Prep Binder; opening/closing; direct & cross; the person's testimony; the one-page hearing sheet + two-column live note-taking; assembles the all-in-one **Trial Packet** (witness-by-witness cross for every witness + allegation answers + pocket card). |
| **Courtroom Bulldog** | `courtroom-bulldog.md` | Hold the line in the moment; stop the steamroll; calm voice. |
| **Order Integrity Reviewer** | `order-integrity.md` | The three-way check on any proposed/entered order (never sign blind). |
| **Ambiguity Auditor** | `ambiguity-auditor.md` | Find vague/gray terms; draft specific replacement language. |
| **Response Arsenal** | `response-arsenal.md` | Every way to fight something filed/served; coordinated multi-front map. |
| **Adversarial Combat** | `adversarial-combat.md` | Refuse bait → pull contradictions → cross + filing when attacked. |
| **Negotiation Counsel** | `negotiation-counsel.md` | Run a deal + the redline-integrity (anti-sneak-edit) protocol. |
| **Problem-to-Proposal Counsel** | `problem-to-proposal.md` | Turn a complaint into a court-ready, provable solution. |
| **Case Campaign** | `proactive-offense.md` | Work backward from the goal; the next offensive move (always-on). |
| **Resolution & Investigation** | `resolution-investigation-team.md` | Settlement architecture + investigation bench. |
| **Strategy & Governance** | `strategy-governance-team.md` | Case theory, sequencing, firm governance. |

### Safety (fire first, immediately)
| **Abuse & Coercive-Control** | `abuse-coercive-control.md` | Safety-screen; prove the pattern (incl. financial); lock-in admissions; recovery. |
| **Protective-Order** | `protective-order.md` | §93-21 protection-order procedure: get / extend / drop / defend. |

### Separate family-law actions (their own bodies of law)
| **Paternity** | `paternity.md` | Establish/disestablish fatherhood (§93-9); then route custody/support. |
| **Grandparent / Third-Party Custody** | `grandparent-third-party-custody.md` | §93-16 visitation; natural-parent presumption for custody. |
| **Name-Change** | `name-change.md` | §93-17-1 name change / restoration / legitimation. |
| **Guardianship / Conservatorship** | `guardianship.md` | §93-20 guardian-of-person / conservator-of-estate of a minor. |

### Shared resources (no standalone agent — every agent may read these)
`operating-doctrine.md` (the rules), `field-tactics.md`, `starter-questions.md`, `start-here.md`, `case-profile-template.md`,
`tools-and-integrations.md`. These are consulted by the owning agents above, not dispatched on their own.

---

## The rule for future sections
Any new section/playbook added to the firm **is owned by an agent by default** — add its row to the registry above, give
it a trigger in `operating-doctrine.md` → Auto-engage, and it auto-dispatches as a background sub-agent under this same
protocol. No section is ever "just a file the main thread reads."

**NEXT ACTION (for the managing partner):** on any request, detect every implicated section, **dispatch each owning agent
as a background sub-agent in parallel** (safety first), then assemble their artifacts into one plain-language answer with a
single NEXT ACTION.
