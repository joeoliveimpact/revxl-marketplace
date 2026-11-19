> 🧭 **METHOD IS UNIVERSAL — the named authorities are the Mississippi example.** The process in this file applies in every state. Where it names **Albright / Armstrong / Ferguson**, a **chancery/chancellor** court, **MRCP / UCCR / the MS Rules of Evidence**, or a Mississippi code section (§93-, §43-19-), that is the **Mississippi worked example** — for a non-MS case, apply the **resolved state-law profile** (its factors, its court, its rules; see `state-law-resolver.md`) instead, and never cite these Mississippi authorities in a non-MS case.

# Tools & Integrations — what the firm uses, and what it skips

> **Jurisdiction note (Clawyer):** this file was written for Mississippi family court. Outside Mississippi, or outside a family case, treat every rule number, case name, deadline, fee and form in it as an example of what to look up, not as your law. Family-law steps in it do not apply to other kinds of case. Confirm your own state's version first and tag anything unconfirmed `CONFIRM-BEFORE-CITING`.

The firm works with no extra tools, but it gets stronger when these are connected. All are **optional** — degrade
gracefully if absent. This is the result of surveying the available skills, plugins, and MCP connectors for what
actually helps a pro-se family-law litigant.

## ✅ High value — use whenever available

| Tool / skill | What it adds to the firm | Which specialist uses it |
|---|---|---|
| **Legal research engine** (e.g., Descrybe, CourtListener, a law-research MCP) | Look up + verify real case law, statutes, citations, and how a case has been treated — powers the "verify it yourself" standard | **Research Counsel** |
| **docx skill** | Turn a plain-language draft into a clean, filed-ready **Word document** (caption, numbered paragraphs, signature block) | **Drafting Counsel** |
| **pdf skill** | **Read/OCR scanned filings and orders** (so nothing is analyzed from a blurry image), and produce court-ready PDFs | **Records Analyst**, **Drafting Counsel**, **Markdown Maker** |
| **pdf-viewer** (fill-form, sign, annotate) | **Fill official court PDF forms**, place the user's **signature**, and **mark up** the other side's filings/orders | **Drafting Counsel**, **Order Integrity Reviewer** |
| **Calendar tool** | Put **hearing dates and deadlines** on the user's calendar automatically — pairs with the Docket Watcher | **Docket Watcher**, **Local-Procedure Clerk** |
| **Matter / chronology tool** (e.g., a litigation plugin) | Structured case-fact tracking + a sourced **timeline**, and computed candidate **deadlines** from filings | **Records Analyst**, **Docket Watcher** |
| **Web search** | Required for currency — any rule/statute/case/local rule/fee/form not certain from memory | **Research Counsel**, **Local-Procedure Clerk** |
| **Verbatim source fetch** — `scripts/fetch_law.py` (+ `references/legal-source-fetch.md`) | Read statutes, rules, and **local-rule PDFs** verbatim when web fetch / a statute host returns 403/500 — the firm's own work-around; use before reporting a source "blocked" | **Research Counsel**, **Local-Procedure Clerk** |

## 🟡 Situational — use when it fits

| Tool / skill | When it helps |
|---|---|
| **A topical NotebookLM notebook** | If the user has built one (e.g., a state family-law reference) — ask it questions, then **verify** answers against primary sources |
| **A task/issue board** (e.g., Linear) | Track action items across sessions (no sensitive case facts on it) |
| **Cloud file storage** (e.g., Google Drive) | Pull the user's case documents in for analysis |
| **A skill registry/installer** | Find and add new vetted legal skills over time |

## ❌ Skip for this firm
Marketing, sales, finance, data/analytics, design, operations, small-business, ads, brand-voice, offer/coaching, and
course-scraping skills are **not** family-law relevant — don't route to them. General desktop automation is overkill
unless a specific manual task truly needs it.

## Rule for all integrations
Tools are **leads, not authority.** Anything a tool returns about the law still runs through **citation discipline**
(verify to a primary/official source, tag certainty, never fabricate). A tool that's missing is never an excuse to
guess — say what you couldn't reach and give the next-best verified path.

## Open-source building blocks (found via web/GitHub research, 2026-05-23)
Mature, free/open-source projects this firm can build on or plug into. All need setup; verify coverage for the user's
specific court before relying on one.
- **docassemble** (docassemble.org, MIT) — open-source guided-interview + document-assembly engine (Python/YAML/Markdown)
  that outputs court-ready PDF/DOCX. Ideal for turning intake answers into filled motions/petitions/financial forms; has
  even been used to generate QDROs. Pairs with **Intake Counsel** + **Drafting Counsel**.
- **Suffolk LIT Lab — Document Assembly Line** (assemblyline.suffolklitlab.org, MIT) — open-source court-form automation,
  guided interviews, and e-filing tooling built specifically for self-represented litigants. Mine it for form patterns.
- **A2J Author** — guided-interview authoring used by courts/legal-aid for self-represented litigants.
- **Court-docket tooling:** Free Law Project **juriscraper** (github.com/freelawproject/juriscraper) and Big Local News
  **court-scraper** (github.com/biglocalnews/court-scraper) are scraper frameworks for U.S. court sites; **CourtListener**
  + **courtlistener-mcp** (github.com/khizar-anjum/courtlistener-mcp) expose docket data + alerts via MCP. ⚠️ **Caveat:**
  these focus on federal + appellate + some state courts — **county chancery/trial dockets (what this firm's Docket
  Watcher targets) usually are NOT covered**, so a site-specific scraper is still needed; use these for their patterns
  and for any court they do cover.
- **awesome-legaltech** (github.com/Vaquill-AI/awesome-legaltech) — curated index of open-source legaltech, AI models,
  MCP servers, and datasets; check here first when you need a new building block.

## Free primary-law sources (a pro se can use these directly, no subscription)
Use these for research and to **verify** any cite before it goes in a filing (citation discipline still binds — these are
leads; confirm the pinpoint against the official reporter/code). Verified via the Library of Congress free-case-law guide,
2026.
- **Google Scholar** (scholar.google.com, "Case law" mode) — free full-text search of federal **and** state case law.
- **CourtListener** (courtlistener.com, Free Law Project) — millions of opinions, updated daily, with **free alerts** on a
  court or topic (pairs with the Docket Watcher). MCP available (`courtlistener-mcp`).
- **Caselaw Access Project** (case.law, Harvard) — official, book-published U.S. case law (through June 2018); best for
  older/obscure precedent.
- **Cornell Legal Information Institute (LII)** (law.cornell.edu) — free U.S. Code, statutes, Supreme Court opinions, and
  the CFR, annotated.
- **Justia** (justia.com) — free case law, statutes, and regulations with summaries. (Note: Justia consumer pages can be
  Cloudflare-walled, see `legal-source-fetch.md` for the work-around.)
- For Mississippi primary law specifically, see also `legal-source-fetch.md` (FindLaw + official `courts.ms.gov` /
  legislature routes) and `scripts/fetch_law.py`.

## Free human legal help — ALWAYS offer this
The firm is **not a lawyer.** Point every user to the free human help that exists — the ethical baseline for a pro-se
tool. **Generic (any state):** the state's **Access-to-Justice commission**, the **legal-aid/legal-services** office, an
**ABA Free Legal Answers** site, the court's **self-help center**, and the **county law library** (often has local forms
and help). **National nonprofits (verified 2026):**
- **LawHelp.org** (lawhelp.org · /findforms) — finds the user's state legal-aid providers, court forms, and self-help.
- **LawHelp Interactive** (lawhelpinteractive.org, Pro Bono Net) — **free guided document assembly** for self-represented
  litigants (child support, custody, domestic violence, divorce); used in 47 states. Pairs with **Intake** + **Drafting**;
  check whether it has interviews for the user's state/court.
- **WomensLaw.org** (womenslaw.org, NNEDV) — plain-language domestic-violence + family-law legal info by state (for any
  gender, despite the name).
- **SRLN — Self-Represented Litigation Network** (srln.org) — self-help center locator + resources for people without a lawyer.
**Mississippi (the built-in spine):**
- **MS Access to Justice Commission** — msatjc.org (legal forms; family & children law) · 601-960-9581
- **MS Free Legal Answers** — MS.freelegalanswers.org (free civil legal Q&A, income-eligible)
- **MS Volunteer Lawyers Project** — 601-882-5001 (free family-law clinics: custody, support, visitation, uncontested
  divorce, guardianship)
- **MS Legal Services / online forms** — mslegalservices.org/online-legal-forms
- **Courts** — courts.ms.gov/Legal/CivilLegal.php
- **MS Dept. of Human Services — Child Support** — mdhs.ms.gov/childsupport/ + the **MDHS child-support calculator**
  (mdhs.ms.gov/child-support-calculator/) and the Guidelines PDF. Uses the §43-19-101 guideline (14/20/22/24/26% by number
  of children) [VERIFIED prior]. Good for a quick estimate; the firm still does the deviation analysis.
- **Mississippi Electronic Courts (MEC)** — courts.ms.gov/mec/. **Verified 2026, important for pro se:** as of **June 30,
  2025** e-filing is live statewide in **all 82 counties / all 188 trial courts + the appellate courts**. **BUT a pro-se
  (self-represented) litigant still files on PAPER — they cannot e-file through MEC.** A clerk **may** authorize a pro se to
  receive **NEFs (Notices of Electronic Filing)** so they get electronic notice of every filing in their case. Action: ask
  your chancery clerk to turn on NEF notifications for you (free case tracking; pairs with the **Docket Watcher**). This
  confirms the firm's paper-filing guidance, it is not out of date.
- **WomensLaw.org — Mississippi** (womenslaw.org/laws/ms) — plain-language MS custody/support/DV info.
- **Honest fact:** Mississippi has **no statewide approved fill-in-the-blank self-help forms** — so a user must follow
  chancery format (and check their **county law library** for any local forms). The firm's drafting fills this gap, but
  verify format against the local court.
