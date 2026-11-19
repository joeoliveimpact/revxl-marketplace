# ROLE-TO-TOOL-MAP.md — Template

> **Jurisdiction note (Clawyer):** this file was written for Mississippi family court. Outside Mississippi, or outside a family case, treat every rule number, case name, deadline, fee and form in it as an example of what to look up, not as your law. Family-law steps in it do not apply to other kinds of case. Confirm your own state's version first and tag anything unconfirmed `CONFIRM-BEFORE-CITING`.

> Every role × every tool category it actually drives. Lives at workspace root after install.
>
> **Read by:** any specialist auto-fire that needs to know its own toolkit. Chief of Staff reads at Step 0.4.
> **Updated by:** the firm, automatically, per the Firm Tooling Inventory Rule whenever any role or tool changes.
> **Pairs with:** `FIRM-TOOLING-INVENTORY.md` (master tool list), `CASE-FILE-INDEX.md` (role-to-file), `FIRM-PATHWAYS-MAP.md` (connective tissue), `MASTER-INDEX.md` (one-page firm map).

## Legend

- **MCPs** drawn from FIRM-TOOLING-INVENTORY MCP Connectors section. "ALL" means the role reads across every connected MCP.
- **Scripts** drawn from the workspace `scripts/` folder and the skill-bundled `scripts/` folder.
- **Python libs** named only when the role's workflow calls the library directly.
- **Notebooks** drawn from FIRM-TOOLING-INVENTORY NotebookLM Notebooks section. The placeholder names below match the standard 7-notebook starter set the firm builds during cold-start (see `cold-start.md`). Real names depend on the user's case.
- **Companion skills** drawn from Anthropic-bundled skills the firm auto-invokes plus any installed legal plugins.
- **External** is anything outside the workspace, the user's state court records portal, county clerk phone, federal resources, crisis lines.
- `n/a` means that tool category is not part of the role's standing workflow.

📍 **State-neutral.** This template references no specific state, court, judge, or case. The State-Law Resolver populates state-specific tools (research portals, statute mirrors, local rule PDFs) at the user's first session based on their case-profile.

---

## Strategy & Governance department

| Role | MCPs | Scripts | Python libs | Notebooks | Companion skills | External |
|---|---|---|---|---|---|---|
| **Chief of Staff** (orchestrator, auto-trigger audit) | ALL (reads every connected MCP to route) | ALL (orchestrates) | n/a | ALL active notebooks | ALL companion skills (delegates) | n/a |
| **Lead Strategist** (owns case theory + filing sequence) | Linear (if installed) · Calendar (deadline anchors) | n/a | n/a | Case Files · Trial Packet Master | superpowers (planning, parallel-agent dispatch) | n/a |
| **Lead Trial Counsel** (leads floor team for the user's controlling hearing) | Calendar · Linear | n/a | n/a | Trial Packet Master · Case Files | docx · pdf | n/a |
| **Of Counsel / SME** (niche-trap spotter) | Descrybe Legal · WebSearch · WebFetch | n/a | n/a | The user's state-law reference notebook | law-student (legal-writing) · legal-builder-hub (registry browse) | The user's state-court public records portal · justia · law-school free-content mirrors |
| **Calm-Client Counselor** (Tier-1 translation + emotional regulation) | n/a | n/a | n/a | n/a | n/a | 988 · DV hotline 1-800-799-7233 (`references/crisis-resources.md`) |
| **Compliance / Ethics / Conflicts Officer** (citation integrity + forbidden-output gate) | Descrybe Legal (cite verification) | `scrub_check.py` · `scrub_fix.py` · `spell_check.py` · `check_no_pii.py` | n/a | The user's state-law reference notebook | n/a | n/a |
| **Records / Case Manager** (custodian, version control) | Linear · Google Drive | n/a | n/a | Case Files | litigation-legal (`chronology` · `matter-workspace`) | n/a |

## Operations & Discovery department

| Role | MCPs | Scripts | Python libs | Notebooks | Companion skills | External |
|---|---|---|---|---|---|---|
| **Paralegal / Case Organizer** | Google Drive · Linear | `to_markdown.py` · `ingest_prose_corpus.py` | pdfplumber · PyMuPDF | Case Files | xlsx (production log) · docx (filing packages) | n/a |
| **Legal Assistant** (formatting + correspondence log) | Gmail · Calendar | `scrub_check.py` · `scrub_fix.py` · `spell_check.py` | n/a | The user's local-rules notebook | docx · internal-comms | n/a |
| **Docketing / Calendar Clerk** | Calendar · Linear | `docket_watch.py` | n/a | The user's local-rules notebook | n/a | The user's county court docket portal |
| **Process-Service Coordinator** | n/a | n/a | n/a | The user's local-rules notebook | n/a | County sheriff civil process · certified mail tracking |
| **E-Discovery / ESI Lead** | Google Drive | `ocr_pdf.py` · `to_markdown.py` | PyMuPDF · pdfplumber | Case Files | pdf | n/a |
| **Document Review Lead** | Google Drive | `to_markdown.py` · `check_no_pii.py` | spaCy + en_core_web_lg · Presidio | Case Files | pdf · pdf-viewer | n/a |
| **Litigation Support / Trial Prep** | Linear · Calendar | `build_filing_pdf.py` · `scrub_check.py` | n/a | Trial Packet Master | docx · pdf · pdf-viewer | Court's PDF-form portal |
| **Evidence / Exhibit Manager** | Google Drive | `ocr_pdf.py` · `to_markdown.py` | PyMuPDF · pdfplumber | Trial Packet Master · Case Files | pdf · pdf-viewer (annotate/sign) | n/a |
| **Courthouse Navigator** (filing + service hand-holding) | Calendar · Gmail | n/a | n/a | The user's local-rules notebook | n/a | County clerk phone · public courthouse access info |

## Financial & Property department

| Role | MCPs | Scripts | Python libs | Notebooks | Companion skills | External |
|---|---|---|---|---|---|---|
| **Forensic Accountant** | Google Drive | `to_markdown.py` · `ocr_pdf.py` | pdfplumber · PyMuPDF · Presidio (redaction before sharing) | Case Files | xlsx (line-item analysis) · pdf | IRS transcript portal (user-driven) · BLS/O\*NET (earning capacity) |
| **Asset-Tracing Specialist** | Google Drive | n/a | n/a | Case Files | xlsx · litigation-legal (`claim-chart`) | IRS · state corporation registries · UCC filings portal |
| **Business Valuation** (prepare-for / respond-to, not be) | n/a | n/a | n/a | Case Files | xlsx | Industry-data sources cited in expert reports |
| **Real-Estate / Property Appraiser** (prepare-for / respond-to, not be) | n/a | n/a | n/a | Case Files | n/a | County property-records portal · Zillow / county assessor (context only) |
| **QDRO / Retirement** | Google Drive | n/a | n/a | Case Files · the user's state-law reference notebook | docx (QDRO drafts) | TSP · plan administrator portals (user-driven) |
| **Vocational / Earning-Capacity** | WebSearch · WebFetch | n/a | n/a | Case Files | xlsx (earning-capacity worksheet) | BLS · O\*NET · state labor stats |
| **Support & Child-Support Calc** | Descrybe Legal (statute) · Calendar | n/a | n/a | The user's state-law reference notebook | xlsx (worksheet) | State child-support calculator |
| **Tax Specialist** (compliance + filing-status implications) | Google Drive | n/a | n/a | Case Files | xlsx · docx | IRS publications · state DOR |

## Custody, Parenting & Mental-Health department

| Role | MCPs | Scripts | Python libs | Notebooks | Companion skills | External |
|---|---|---|---|---|---|---|
| **Custody Strategist** (factor-matrix builder) | Descrybe Legal · WebFetch | n/a | n/a | Case Files · Trial Packet Master · the user's state-law reference notebook | law-student (legal-writing) | n/a |
| **Parenting-Plan Drafter** | Calendar | `scrub_check.py` · `scrub_fix.py` | n/a | The user's state-law reference notebook | docx | n/a |
| **GAL Interaction Specialist** | Gmail (correspondence log) | n/a | n/a | The user's GAL-related notebook (if created) | n/a | n/a |
| **Custody-Evaluator Interaction** (prepare-for / respond-to, not be) | n/a | n/a | n/a | Case Files | n/a | Professional evaluator's CV/methodology |
| **Parenting-Coordinator Interaction** (prepare-for / respond-to) | n/a | n/a | n/a | Case Files | n/a | n/a |
| **Child-Specialist Interaction** (prepare-for / respond-to) | n/a | n/a | n/a | Case Files | n/a | n/a |

## Resolution & Investigation department

| Role | MCPs | Scripts | Python libs | Notebooks | Companion skills | External |
|---|---|---|---|---|---|---|
| **Settlement / Negotiation Counsel** | Gmail · Calendar | `scrub_check.py` · `scrub_fix.py` | n/a | Case Files · the user's order-integrity notebook (if created) | docx · internal-comms | n/a |
| **Mediator Interaction** (prepare-for, not be) | Calendar | n/a | n/a | Case Files | n/a | Mediator's published intake forms |
| **Order & Judgment Drafter** | n/a | `scrub_check.py` · `scrub_fix.py` · `build_filing_pdf.py` | n/a | The user's state-law reference notebook | docx · pdf | n/a |
| **Appellate / Post-Judgment** | Descrybe Legal · WebFetch | n/a | n/a | The user's state-law reference notebook | law-student (legal-writing) · litigation-legal (`brief-section-drafter`) | State appellate court rules · justia |
| **Enforcement / Contempt** (last resort) | Descrybe Legal · Calendar | n/a | n/a | The user's state-law reference notebook | docx | n/a |
| **Private-Investigator Coordination** (prepare-for / scope, not be) | n/a | n/a | n/a | Case Files | n/a | Licensed PI directories (user-driven) |
| **Digital-Forensics Coordination** (prepare-for / scope, not be) | n/a | n/a | n/a | Case Files | n/a | Licensed digital-forensics examiner directories |

## Core specialists (front-of-firm, named in the auto-fire table)

| Role | MCPs | Scripts | Python libs | Notebooks | Companion skills | External |
|---|---|---|---|---|---|---|
| **Intake Counsel** (front door) | n/a | n/a | n/a | n/a (writes case-profile.md) | n/a | n/a |
| **Legal Educator** (always-on Tier-1 translation) | Descrybe Legal | n/a | n/a | The user's state-law reference notebook | n/a | n/a |
| **Research Counsel** | Descrybe Legal · WebSearch · WebFetch | `fetch_law.py` | n/a | The user's state-law reference notebook · local-rules notebook | law-student (legal-writing) | The user's state court records portal · justia · law-school free-content mirrors · cornell-LII |
| **Drafting Counsel** | n/a | `scrub_check.py` · `scrub_fix.py` · `spell_check.py` · `build_filing_pdf.py` | n/a | Case Files · Trial Packet Master | docx · pdf | n/a |
| **Evidence Specialist** | Google Drive | `ocr_pdf.py` · `to_markdown.py` | PyMuPDF · pdfplumber · PaddleOCR (for image-heavy evidence) | Trial Packet Master · Case Files | pdf · pdf-viewer | n/a |
| **Hearing-Prep Coach** | Calendar | `scrub_check.py` | n/a | Trial Packet Master · Case Files | docx (printable scripts) · pdf | n/a |
| **Local-Procedure Clerk** | WebFetch | `fetch_law.py` | n/a | The user's local-rules notebook | n/a | County clerk phone · the court's local-rule PDF |
| **Records Analyst** (close reader + chronology) | Google Drive | `to_markdown.py` · `ocr_pdf.py` | pdfplumber · PyMuPDF · PaddleOCR | Case Files | litigation-legal (`chronology`) | n/a |
| **Order Integrity Reviewer** | n/a | n/a | n/a | The user's order-integrity notebook (if created) | docx (redline diffs) | n/a |
| **Communication Command** (every message) | Gmail · OFW (the user's co-parenting app, if any) | `scrub_check.py` · `scrub_fix.py` | Presidio (PII before sharing) | The user's communication-pattern notebook (if created) | internal-comms · docx | The user's co-parenting platform (if any) |
| **Credibility & Contradiction Analyst** | Google Drive | n/a | n/a | The user's contradictions notebook (if created) · Case Files | n/a | n/a |
| **Ambiguity Auditor** (gray-area finder in orders) | n/a | n/a | n/a | The user's order-integrity notebook (if created) | docx | n/a |
| **Action-Plan Navigator** | Calendar | n/a | n/a | The user's local-rules notebook | n/a | n/a |
| **Docket Watcher** | Calendar | `docket_watch.py` | n/a | The user's local-rules notebook | n/a | The user's county court docket portal · MEC / PACER / state equivalent |
| **Markdown Maker** | n/a | `to_markdown.py` · `ocr_pdf.py` | PyMuPDF · pdfplumber · PaddleOCR (image OCR) | n/a | pdf | n/a |
| **Case Assurance** (CASE-CHECKLIST keeper, coverage audit) | Linear | n/a | n/a | Case Files | n/a | n/a |
| **Problem-to-Proposal Counsel** | Calendar | n/a | n/a | Case Files | docx · litigation-legal (`brief-section-drafter`) | n/a |
| **Courtroom Bulldog** (hold-the-line floor coach) | n/a | n/a | n/a | Trial Packet Master | n/a | n/a |
| **Adversarial Combat** (truth-exposing cross + filings) | Descrybe Legal · WebFetch | n/a | n/a | Case Files · the user's contradictions notebook (if created) | law-student (legal-writing) | n/a |
| **Case Campaign** (proactive offense) | Linear · Calendar | n/a | n/a | Case Files | superpowers (planning) | n/a |
| **Discovery Strategist** (non-telegraphing question design) | Descrybe Legal | `fetch_law.py` | n/a | The user's state-law reference notebook | docx | n/a |
| **Response Arsenal** (multi-front fight back) | Descrybe Legal · WebFetch | n/a | n/a | Case Files | docx · law-student (legal-writing) | n/a |
| **Abuse & Coercive-Control Specialist** (safety-first) | Gmail (preserve threats) · Calendar | n/a | n/a | The user's abuse-evidence notebook (if created) | n/a | DV 1-800-799-7233 · 988 · state protective-order resources |
| **Career-Sacrifice Claim Counsel** | WebSearch · WebFetch | n/a | n/a | Case Files | xlsx (earning-capacity worksheet) | BLS · O\*NET |
| **Expert-Witness Coordinator** (own or respond-to expert) | n/a | n/a | n/a | Case Files | docx | Expert disclosure rules in the user's state |
| **Forensic Financial Analyst** (hidden-money sweep) | Google Drive | `to_markdown.py` · `ocr_pdf.py` | pdfplumber · PyMuPDF · Presidio | Case Files | xlsx (forensic worksheet) · pdf | IRS · state corporation registries |
| **Paternity** (facts-only-fire) | Descrybe Legal | n/a | n/a | The user's state-law reference notebook | n/a | State DNA-testing labs |
| **Grandparent / Third-Party Custody** (facts-only-fire) | Descrybe Legal | n/a | n/a | The user's state-law reference notebook | n/a | n/a |
| **Protective-Order** (facts-only-fire, safety-first) | Calendar | n/a | n/a | The user's state-law reference notebook | n/a | DV 1-800-799-7233 · 988 · county sheriff |
| **Name-Change** (facts-only-fire) | Descrybe Legal | n/a | n/a | The user's state-law reference notebook | docx | n/a |
| **Guardianship / Conservatorship** (facts-only-fire) | Descrybe Legal | n/a | n/a | The user's state-law reference notebook | docx | n/a |

---

## How to read this table

- "Reads" vs "Uses": every role can READ any notebook or file in the workspace, but the table lists what the role PRIMARILY drives in its workflow.
- A role with `n/a` everywhere still consults the firm's standing files (`case-profile.md`, `CASE-CHECKLIST.md`, etc.). The table marks tool DRIVING, not file access.
- Update protocol: when a new role is added or a new tool comes online, append a row or column here per the Firm Tooling Inventory Rule. The firm does this automatically when it detects an installation or addition.

## Notebook placeholders

The "notebook" column references seven slots that get populated during cold-start (`cold-start.md` → notebook creation step). Some users will have all seven. Some will skip a few. The role-to-tool map adapts at runtime, if a referenced notebook does not exist, the role works from the case files alone and the firm flags the gap in CASE-CHECKLIST.

The seven cold-start notebook slots:
1. Case Files (the canonical corpus, always built)
2. Trial Packet & Cross-Exam Master (built once the controlling-hearing date is known)
3. The user's state-law reference (Albright/Armstrong/Ferguson for Mississippi, the equivalent for other states, the State-Law Resolver populates this on cold-start)
4. The user's local-rules notebook (e.g., county chancery local rules)
5. The user's order-integrity notebook (built if a drafted-order pattern emerges)
6. The user's contradictions notebook (built if a contradiction ledger reaches 10+ entries)
7. The user's communication-pattern notebook (built if the other side's pattern reaches forensic-profile depth)

`cold-start.md` walks the user through each one.
