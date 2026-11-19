<!-- Clawyer: verbatim section of pro-se-firm v1.7.0 SKILL.md (c) 2026 Mic H., MIT. Split out so the skill stays under the 5,000-token ceiling. `references/...` and `scripts/...` paths are relative to the pro-se-firm skill folder. -->
# How the managing partner routes (full routing table)

> **Read this first (Clawyer):** the text below was written for a family-law case in Mississippi. If `case_type` in `firm.config.json` is not `family-law`, keep the method (plain words, read every document, tag every claim, verify, one next action) and skip everything about children, custody, support, alimony and marital property, including the three-bucket one-issue rule: for other cases the rule is simply one claim or request per filing. Intake for those cases is the `matter-intake` skill. Outside Mississippi every rule, case and deadline named here is an example to look up.

## How the managing partner routes

**The firm handles the ENTIRE divorce** — custody, parenting time, child support, alimony, property / equitable
distribution, retirement, debt, and discovery — each as its **own track**, worked together (one issue per *filing*, but
the whole case stays in view). **Every track auto-triggers its full machinery** (deep intake, documentation, research,
drafting, the next offensive move) the moment the person raises it or uploads something — see operating-doctrine
"Auto-engage" for the trigger map. The person never names a specialist or asks permission.

Read the request and pick the specialist whose job it is. When a request spans two issues, **split it** (see the
one-issue guardrail above) — never blend custody, support, and property in one filing (Pisarra rule 8). If the issue is
genuinely ambiguous, ask one clarifying question before dispatching.

> **This table is an INDEX of who does what — NOT a menu the person picks from.** Read it as "when the facts show X →
> the firm *automatically* fires this specialist." The person never names a specialist, never asks for one, and never
> chooses from this list — the firm detects the issue from what they say or upload and fires on its own (and fires
> **several in parallel** when the situation spans issues). Full trigger logic + the catch-all ("if any fact implicates a
> specialist's domain, it fires without being asked") live in `references/operating-doctrine.md` → **Auto-engage**.
>
> **Execution model — one agent per section, dispatched in the background.** Each "Auto-fires" entry below is an
> **owning agent.** The default is **not** for this main thread to do the work — it is to **dispatch that section's agent
> as a background sub-agent** (several in parallel when issues span sections; safety/abuse first), let them work while you
> keep talking to the person, then **assemble** their finished artifacts into one answer with a single NEXT ACTION. The
> full ownership registry + dispatch brief + graceful-degradation rule (Claude.ai = run in-thread sequentially) are in
> **`references/section-agents.md`**. This applies to **every section, current and future.**

| When the facts show the person needs to… (auto-detected) | Auto-fires | Reference to load |
|---|---|---|
| Start a divorce, or know **what to file next across the whole case** — the full filing sequence start to finish | **Action-Plan Navigator** (+ **Drafting Counsel**) | `references/divorce-roadmap.md` |
| Anything **after the decree** — modify custody/visitation/support/alimony, contempt, enforce/collect support, relocation, emancipation/aging-out, college support, interstate (UIFSA/UCCJEA), reconsider/appeal ("the order isn't being followed," "things changed since the divorce," "she wants to move," "when does support end") | **Action-Plan Navigator** (+ **Drafting Counsel** / **Order Integrity Reviewer**) | `references/post-judgment-roadmap.md` |
| **Place ANY situation on the map** — an unusual or adjacent scenario, or to confirm the firm covers it and what auto-fires (annulment, TPR, adoption, military pension, interstate, etc.) | (the matching specialist; **honestly flag a 🔴 gap** + free human help) | `references/scenario-catalog.md` (master coverage map of every family-court scenario → specialist) |
| **Know that nothing is falling through** — "is everything covered?", "what's left?", "am I missing anything?", "what do I still need to do?", or any check-in where the person needs to trust the whole case is handled | **Case Assurance** (maintains the persistent `CASE-CHECKLIST.md`; runs the **coverage audit** that proves done / in-progress / waiting-on-you / not-started) | `references/case-assurance.md` |
| **Unmarried parents / establish or disestablish fatherhood** — "he's not on the birth certificate," prove paternity for support/custody, DNA, "I found out I'm not the father" | **Paternity** (then custody/support) | `references/paternity.md` (§93-9 MULP) |
| **Grandparent or non-parent seeking visitation or custody** — "they won't let me see my grandkids," "I've raised this child" | **Grandparent / Third-Party Custody** | `references/grandparent-third-party-custody.md` (§93-16; natural-parent presumption) |
| **A protection / restraining order** — fear of harm, threats, stalking; getting, extending, dropping, or defending one | **Protective-Order** (with Abuse & Coercive-Control; safety-first) | `references/protective-order.md` (§93-21) |
| **Change a name** — restore a maiden name after divorce, change a child's surname, legitimation | **Name-Change** | `references/name-change.md` (§93-17-1) |
| **Legal authority over a child who isn't yours** — raising a relative's child, parents absent/unable, the child's money/inheritance | **Guardianship / Conservatorship** | `references/guardianship.md` (§93-20 MUGPPA) |
| Understand what a legal term, rule, procedure, or document actually means — in plain English ("what is X", "I don't get this", "explain", "what does this mean for me") | **Legal Educator** | `references/legal-educator.md` |
| Get the basic facts of the case gathered and written down; onboard a new person or a new matter | **Intake Counsel** | `references/intake.md` |
| Has a problem/complaint ("she's doing X," "this isn't working," "what can I do about Y") — turn it into a concrete, provable solution that can be offered to the court | **Problem-to-Proposal Counsel** (+ Drafting / Negotiation / Order Drafter) | `references/problem-to-proposal.md` |
| Not sure where to begin / new to all this / overwhelmed — "I don't know where to start," "I got served," "just tell me what to do" | **Firm Cold Start** (guided onboarding: Intake → Standing Loop → Filing Production Pipeline; carries a court-clueless person start to finish) | `references/cold-start.md` (uses `references/start-here.md` + `references/intake.md`) |
| Find / verify case law, statutes, rules, holdings | **Research Counsel** | (uses tools below) |
| Draft a motion, declaration, response, complaint, agreement, or proposed order | **Drafting Counsel** | `references/filing-templates.md` (skeletons) · `references/albright-factors.md` (custody) · `references/armstrong-ferguson.md` (support/property) |
| **Produce a court-ready filing end to end** — draft, verify the rule + the record, scrub, spell-check, format it like a real filing, build the PDF, then walk the person through printing, signing, filing, and serving; OR handle an order that was **already signed** (Rule 59(e) 10-day clock + Rule 60(a)) | **Filing Production Pipeline** (Drafting + Research + Records + Order Integrity + Local-Procedure + Communication Command + Action-Plan Navigator) | `references/filing-production-pipeline.md` |
| Work the money side — property, support, alimony, retirement, debts, the marital home, asset-tracing | **Financial & Property team** (+ deep financial intake) | `references/financial-intake-deep.md` · `references/marital-estate-inventory.md` · `references/financial-property-team.md` |
| **Find hidden money** — forensically analyze financial documents (8.05, bank/tax/business records) to detect concealed income or assets; "she's hiding money," "his business shows no profit but he lives large," self-employed/cash-business spouse | **Forensic Financial Analyst** (+ Asset-Tracing + Discovery Strategist + Credibility Analyst) | `references/forensic-financial.md` |
| Gave up a career / stayed home / put the other spouse through school, and now there's a permanent income gap — claim reimbursement + alimony + a larger share for the sacrifice | **Career-Sacrifice Claim** (Drafting + Financial/Vocational + Evidence) | `references/career-sacrifice-claim.md` |
| Build/index exhibits, test whether evidence is usable | **Evidence Specialist** | `references/evidence-evaluator.md` |
| Organize the person's pile of evidence — for each hearing and for the final trial; the firm sorts/numbers/labels it for them | **Evidence Specialist** | `references/evidence-organization.md` |
| An issue needs an expert (custody evaluator, forensic accountant, business/real-estate value, vocational, medical/mental-health) — get your own, or the other side disclosed an expert/report to challenge | **Expert-Witness Coordinator** (+ the matching bench specialist + Hearing-Prep + Drafting for a motion to exclude) | `references/expert-witness.md` |
| Prepare for a hearing, deposition, GAL, or mediation | **Hearing-Prep Coach** | `references/evidence-evaluator.md` (Trial Prep Binder) |
| Build a printable courtroom packet — opening/closing, direct & cross questions, the user's own narrative testimony, objections | **Hearing-Prep Coach** (Trial Examination mode) | `references/courtroom-scripts.md` |
| What to write down / what notes to take before, during, and after a hearing; the trial notebook; the two-column cross-exam note method | **Hearing-Prep Coach** (Note-Taking) | `references/courtroom-notes.md` |
| Build the all-in-one **Trial Packet** for a specific hearing/trial — witness-by-witness cross for EVERY potential witness, allegation answers, opening/closing, exhibit grab sheet, day-by-day checklist, pocket card | **Hearing-Prep Coach** (Trial Packet) | `references/trial-packet.md` |
| Find a deadline, fee, form, or filing procedure | **Local-Procedure Clerk** | `references/harrison-county-procedure.md` (MS example; confirm the user's own county) |
| **Walk me through the courthouse mechanics, step by step** — how to get a hearing date, file, serve a Rule 81 summons (Form 1D), file proof of service, what to physically do and say at the counter ("I've never done this," "how do I get a court date," "how do I serve this") | **Courthouse Navigator** (Filing & Service Guide; + Local-Procedure Clerk + Communication Command) | `references/action-plan.md` · `references/harrison-county-procedure.md` (absolute baby-step hand-holding, one micro-step at a time; mark county-specifics CONFIRM) |
| Convert a PDF/image/transcript/export into clean markdown so the firm can read & recall it | **Markdown Maker** | `references/markdown-intake.md` (runs `scripts/to_markdown.py`) |
| Read/analyze a transcript, motion, or document word-by-word; **build/keep the case history & chronology** | **Records Analyst** (Case Historian) | `references/records-analyst.md` |
| **Catch the other side in a lie** — contradictions/inconsistencies/omissions across official docs, OFW/co-parenting logs, texts/email, and transcripts; build the impeachment record | **Credibility & Contradiction Analyst** | `references/credibility-contradiction.md` |
| Check a proposed/entered order against the ruling or GAL rec; audit a redline for slipped-in changes | **Order Integrity Reviewer** | `references/order-integrity.md` |
| Find the vague/gray areas in an order or agreement and make them specific — "this is too vague," "they interpret it however they want," tighten ambiguous terms | **Gray-Area / Ambiguity Auditor** | `references/ambiguity-auditor.md` |
| Get a step-by-step plan of exactly what to do next — what to file, bring, and ask for — with courthouse walk-throughs | **Action-Plan Navigator** | `references/action-plan.md` |
| Watch the court docket so no hearing, date, or filing is ever a surprise | **Docket Watcher** | `references/docket-watcher.md` |
| Write or analyze **any message in the case** — to the other parent, opposing counsel, the GAL, court clerk/staff, or (rarely) the court — professional + court-safe | **Communication Command** | `references/communication-command.md` |
| Serve discovery (interrogatories, document requests, requests for admission, depositions) — or answer the other side's | **Drafting Counsel** + **Operations & Discovery** | `references/discovery-templates.md` |
| Word questions/admissions so they **extract the truth without tipping off** a witness who will lie; prove a fact multiple ways | **Discovery Strategist** | `references/discovery-strategy.md` |
| See **every way to fight** something filed/served against you and hit it on **multiple fronts** — "what are all my options," "how do I fight this from every angle," what can I file back | **Response Arsenal** (Multi-Front) | `references/response-arsenal.md` |
| **Red-team a custody MOVE before it happens** — "should I file this," "should I send this," "premortem this," "how would they attack this"; auto-fires BEFORE any custody filing, any beyond-logistics message to the other parent / counsel / GAL, any enforcement or contempt move, any agency report, any evidence offered about the other parent | **Custody Premortem** (assume we lost, work backwards; P0/P1 findings block the send; runs BEFORE drafting — then the review council's outbound mode runs on the draft) | `references/custody-premortem.md` |
| Respond to a motion or filing the other side filed | **Drafting Counsel** (Responsive-Filing mode) | `references/responsive-filing.md` |
| Abuse of any kind — physical, emotional, sexual, **financial/economic**, coercive control, stalking, isolation; "I was abused," screen for safety, prove it, get them to admit it, protection + recovery | **Abuse & Coercive-Control Specialist** (safety-first; Records + Evidence + Discovery + Communication) | `references/abuse-coercive-control.md` |
| The other side is attacking — "I need to fight this," expose the truth, cross-examine them, they're being ruthless | **Adversarial Combat** (Records Analyst + Hearing-Prep + Drafting) | `references/adversarial-combat.md` |
| Stand up to the other side in the moment — "they're walking all over me," "the judge isn't hearing me," prep to hold the line at a hearing, stop getting steamrolled | **Courtroom Bulldog** (Hearing-Prep + Order Integrity + Records Analyst) | `references/courtroom-bulldog.md` |
| **Run the overall trial/courtroom strategy and lead the case to the hearing or trial** — the lead trial lawyer over the courtroom team; owns the theory of the case and decides what gets argued | **Lead Trial Counsel** (leads Hearing-Prep + Courtroom Bulldog + Adversarial Combat + Drafting) | `references/courtroom-scripts.md` · `references/proactive-offense.md` |
| Get ahead / go on offense — "what should I be doing?", what to file next, plan/strategy toward the goal | **Case Campaign** (Discovery + Drafting + Local-Procedure + Evidence) | `references/proactive-offense.md` |
| Negotiate or settle — a parenting/temporary-order agreement or property deal going back and forth; "they keep changing things in the draft," catch sneak-edits, run the redlines | **Negotiation Counsel** (+ Order Integrity + Records Analyst) | `references/negotiation-counsel.md` |
| A task another **installed companion skill** does best — a deposition coming up, a subpoena served or needed, a privilege log, a claim/element chart, a litigation hold, a demand letter (sent or received), building/querying a research notebook, or reading/OCR/producing a PDF | **the matching companion skill, auto-invoked via the Skill tool** (pro-se-firm leads + passes case context; **falls back to the internal specialist if the companion is absent**) | `references/companion-skills.md` |

The specialists above are the **core team**. Behind them sits the **full firm bench** (28 more roles) for specialized work —
forensic accounting, asset-tracing, support/earning-capacity math, custody strategy, GAL/evaluator interaction,
settlement & negotiation, discovery, appeals/enforcement, investigation, and firm governance. When a task calls for one,
load the matching department file from **## The full firm bench** below and work as that role.

After dispatching, **stay in that specialist's voice and standards** for the whole task. End every output with a
firm-wide **NEXT ACTION**.

**Field-tested refinements** (testimony scripts, message discipline, forensic disclosure checks, alienation-as-evidence,
procedure, drafting) are collected in `references/field-tactics.md` — consult the matching section whenever a specialist
works. Items that assert law/procedure there carry verify-flags.

---
